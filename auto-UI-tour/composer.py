import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from config import Config
from steps import DemoStep


def _overlay_audio(
    video_path: Path,
    audio_data: Dict[str, dict],
    steps: List[DemoStep],
    config: Config,
    output_path: Path,
    segment_durations: Optional[Dict[str, float]] = None,
) -> Path:
    timeline = []
    current_t = 0.0

    for step in steps:
        audio = audio_data.get(step.id)
        if not audio:
            continue
        timeline.append((audio["path"], current_t))
        if segment_durations is not None:
            current_t += segment_durations.get(step.id, audio["duration"] + step.pause_after)
        else:
            current_t += audio["duration"] + step.pause_after

    if not timeline:
        subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-c:v", "copy", str(output_path)], check=True)
        return output_path

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]
    for audio_path, _ in timeline:
        cmd += ["-i", str(audio_path)]

    filter_parts = []
    for idx, (_, start_s) in enumerate(timeline):
        delay_ms = int(start_s * 1000)
        filter_parts.append(f"[{idx + 1}:a]adelay={delay_ms}|{delay_ms}[a{idx}]")

    if len(timeline) == 1:
        filter_complex = filter_parts[0].replace("[a0]", "[aout]")
    else:
        mix = "".join(f"[a{i}]" for i in range(len(timeline)))
        filter_complex = ";".join(filter_parts) + f";{mix}amix=inputs={len(timeline)}:normalize=0[aout]"

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
        print(result.stderr[-800:])
        raise RuntimeError(f"ffmpeg exited with code {result.returncode}")
    return output_path


def compose_from_screenshots(
    snapshots: Dict[str, Path],
    audio_data: Dict[str, dict],
    steps: List[DemoStep],
    config: Config,
) -> Path:
    config.final_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.final_dir / "demo.mp4"
    slideshow_path = config.output_dir / "slideshow.mp4"
    fade_s = 0.4

    valid = [(s, audio_data.get(s.id, {})) for s in steps if snapshots.get(s.id, Path()).exists()]
    n = len(valid)
    if n == 0:
        raise RuntimeError("No screenshots to compose")

    if n == 1:
        s, a = valid[0]
        dur = a.get("duration", 3.0) + s.pause_after
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-t", f"{dur:.4f}",
                "-i", str(snapshots[s.id].absolute()),
                "-vf", f"fps=25,scale={config.video_width}:{config.video_height}:flags=lanczos",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
                str(slideshow_path),
            ],
            capture_output=True, text=True,
        )
    else:
        inputs = []
        for idx, (s, a) in enumerate(valid):
            dur = a.get("duration", 3.0) + s.pause_after
            if idx == n - 1:
                dur += (n - 1) * fade_s
            inputs += ["-loop", "1", "-t", f"{dur:.4f}", "-i", str(snapshots[s.id].absolute())]

        offsets = []
        t = 0.0
        for i, (s, a) in enumerate(valid):
            dur = a.get("duration", 3.0) + s.pause_after
            if i < n - 1:
                offsets.append(t + dur - fade_s)
            t += dur - fade_s

        filter_parts = []
        prev = "0"
        for i in range(1, n):
            out = f"v{i}"
            filter_parts.append(
                f"[{prev}][{i}]xfade=transition=fade:duration={fade_s}:offset={offsets[i-1]:.4f}[{out}]"
            )
            prev = out
        filter_parts.append(
            f"[{prev}]scale={config.video_width}:{config.video_height}:flags=lanczos,fps=25[vout]"
        )

        result = subprocess.run(
            ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", ";".join(filter_parts),
                "-map", "[vout]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
                str(slideshow_path),
            ],
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        print(result.stderr[-800:])
        raise RuntimeError("ffmpeg slideshow failed")

    # Build crossfade-adjusted segment durations so audio offsets match visual timeline.
    segment_durations = {}
    for idx, (step, audio) in enumerate(valid):
        duration = audio.get("duration", 3.0) + step.pause_after
        if idx < n - 1:
            duration -= fade_s
        segment_durations[step.id] = duration

    return _overlay_audio(
        slideshow_path,
        audio_data,
        [s for s, _ in valid],
        config,
        output_path,
        segment_durations=segment_durations,
    )


def compose_video(
    video_path: Path,
    audio_data: Dict[str, dict],
    steps: List[DemoStep],
    config: Config,
    segment_durations: Optional[Dict[str, float]] = None,
) -> Path:
    config.final_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.final_dir / "demo.mp4"
    return _overlay_audio(video_path, audio_data, steps, config, output_path, segment_durations)
