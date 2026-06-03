import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from config import Config
from steps import DemoStep


# ── Shared audio-overlay logic ─────────────────────────────────────────────


def _overlay_audio(
    video_path: Path,
    audio_data: Dict[str, dict],
    steps: List[DemoStep],
    config: Config,
    output_path: Path,
    segment_durations: Optional[Dict[str, float]] = None,
) -> Path:
    """
    Place each narration audio clip at its correct timestamp and mix them
    onto the video track, producing a final MP4.
    """
    # Build (audio_path, start_seconds) timeline
    timeline: List[tuple] = []
    current_t = 0.0
    for step in steps:
        audio = audio_data.get(step.id)
        if audio:
            timeline.append((audio["path"], current_t))
            if segment_durations is not None:
                current_t += segment_durations.get(step.id, audio["duration"] + step.pause_after)
            else:
                current_t += audio["duration"] + step.pause_after

    if not timeline:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-c:v", "copy", str(output_path)],
            check=True,
        )
        return output_path

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]
    for audio_path, _ in timeline:
        cmd += ["-i", str(audio_path)]

    filter_parts = []
    for idx, (_, start_s) in enumerate(timeline):
        delay_ms = int(start_s * 1000)
        filter_parts.append(f"[{idx + 1}:a]adelay={delay_ms}|{delay_ms}[a{idx}]")

    n = len(timeline)
    if n == 1:
        filter_complex = filter_parts[0].replace("[a0]", "[aout]")
    else:
        mix = "".join(f"[a{i}]" for i in range(n))
        filter_complex = ";".join(filter_parts) + f";{mix}amix=inputs={n}:normalize=0[aout]"

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg stderr:\n{result.stderr[-600:]}")
        raise RuntimeError(f"ffmpeg exited with code {result.returncode}")

    return output_path


# ── Screenshot-based composition (snapshot mode) ───────────────────────────


def compose_from_screenshots(
    snapshots: Dict[str, Path],
    audio_data: Dict[str, dict],
    steps: List[DemoStep],
    config: Config,
) -> Path:
    """
    Build the final MP4 from PNG screenshots + narration audio.
    No app or Playwright needed — pure ffmpeg.

    Each screenshot is shown for exactly (audio_duration + pause_after) seconds,
    matching the narration timing produced in Phase 1.
    """
    config.final_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.final_dir / "demo.mp4"

    # ── 1. Build ffmpeg concat input file ─────────────────────────────────
    concat_path = config.output_dir / "frames.txt"
    with open(concat_path, "w") as f:
        for step in steps:
            png = snapshots.get(step.id)
            audio = audio_data.get(step.id, {})
            duration = audio.get("duration", 3.0) + step.pause_after
            if png and png.exists():
                f.write(f"file '{png.absolute()}'\n")
                f.write(f"duration {duration:.4f}\n")
        # ffmpeg concat requires the last file to appear twice (no trailing duration)
        last_png = snapshots.get(steps[-1].id)
        if last_png and last_png.exists():
            f.write(f"file '{last_png.absolute()}'\n")

    # ── 2. Build silent slideshow video with crossfade transitions ────────
    slideshow_path = config.output_dir / "slideshow.mp4"
    print(f"  Building slideshow from {len(snapshots)} screenshots (with crossfades)...")

    fade_s = 0.4  # crossfade duration in seconds
    valid = [(s, audio_data.get(s.id, {})) for s in steps if snapshots.get(s.id, Path()).exists()]
    n = len(valid)

    if n <= 1:
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path),
             "-vf", f"fps=25,scale={config.video_width}:{config.video_height}:flags=lanczos",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", str(slideshow_path)],
            capture_output=True, text=True,
        )
    else:
        inputs = []
        for idx, step in enumerate(valid):
            s, a = step
            dur = a.get("duration", 3.0) + s.pause_after
            # Compensate on the last frame so the video outlasts the audio
            # and -shortest doesn't cut the outro narration.
            if idx == len(valid) - 1:
                dur += (n - 1) * fade_s
            inputs += ["-loop", "1", "-t", f"{dur:.4f}",
                       "-i", str(snapshots[s.id].absolute())]

        # xfade chain: [0][1]xfade=offset=T0[v01]; [v01][2]xfade=offset=T1[v012]; ...
        filter_parts = []
        offsets = []
        t = 0.0
        for i, (s, a) in enumerate(valid):
            dur = a.get("duration", 3.0) + s.pause_after
            if i < n - 1:
                offsets.append(t + dur - fade_s)
            t += dur - fade_s

        prev = "0"
        for i in range(1, n):
            out = f"v{i}"
            filter_parts.append(
                f"[{prev}][{i}]xfade=transition=fade:duration={fade_s}"
                f":offset={offsets[i-1]:.4f}[{out}]"
            )
            prev = out

        filter_parts.append(
            f"[{prev}]scale={config.video_width}:{config.video_height}"
            f":flags=lanczos,fps=25[vout]"
        )
        filter_complex = ";".join(filter_parts)

        result = subprocess.run(
            ["ffmpeg", "-y"] + inputs +
            ["-filter_complex", filter_complex,
             "-map", "[vout]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
             str(slideshow_path)],
            capture_output=True, text=True,
        )

    if result.returncode != 0:
        print(f"  ffmpeg stderr:\n{result.stderr[-800:]}")
        raise RuntimeError("ffmpeg slideshow failed")

    # ── 3. Overlay audio ──────────────────────────────────────────────────
    print(f"  Overlaying {len(audio_data)} audio clips...")
    return _overlay_audio(slideshow_path, audio_data, steps, config, output_path)


# ── Playwright-webm composition (live mode) ────────────────────────────────


def compose_video(
    video_path: Path,
    audio_data: Dict[str, dict],
    steps: List[DemoStep],
    config: Config,
    segment_durations: Optional[Dict[str, float]] = None,
) -> Path:
    """Compose a Playwright-recorded .webm + narration audio -> MP4 (--live mode)."""
    config.final_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.final_dir / "demo.mp4"
    print(f"  ffmpeg composing {len(audio_data)} audio clips + video...")
    return _overlay_audio(video_path, audio_data, steps, config, output_path,
                          segment_durations=segment_durations)
