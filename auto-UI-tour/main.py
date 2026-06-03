"""
Automated Demo Generator — autodemo-toolkit

Works with any web app: Streamlit, React, plain HTML, SaaS products, etc.

Two-phase pipeline
------------------
Phase 1  Snapshot  (needs app running)
    Visit the live app step-by-step, wait for content to load, apply
    Driver.js spotlight, then save each page as a PNG screenshot.
    TTS narration audio is generated in parallel.

Phase 2  Record  (no app needed)
    ffmpeg assembles the PNGs + audio into the final MP4.
    No live app calls — instant, reproducible.

Live mode (--live flag):
    Playwright records the live app directly, then ffmpeg overlays audio.

Audio generation runs in parallel with Phase 1.

Usage
-----
    python main.py --plan my_demo.yaml
    python main.py --plan my_demo.yaml --live
    python main.py --plan my_demo.yaml --no-start  # app already running
    python main.py --plan my_demo.yaml --port 3000

Output
------
    output/final/demo.mp4
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from config import Config
from plan_loader import load_plan, plan_mode
from tts import generate_audio_files
from snapshotter import render_snapshots
from recorder import record_demo, record_from_snapshots
from composer import compose_video, compose_from_screenshots


# ── App lifecycle ─────────────────────────────────────────────────────────────


def _is_running(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except Exception:
        return False


def start_app(config: Config) -> subprocess.Popen:
    """
    Start the target app as a subprocess using config.start_command.
    The process is started in config.project_root with config.app_env merged
    into the current environment.
    """
    if not config.start_command:
        print(
            "Error: no start_command configured. Either:\n"
            "  • Set start_command in your plan YAML under config:\n"
            "      start_command: \"npm start\"\n"
            "  • Or start the app manually and use --no-start."
        )
        sys.exit(1)

    env = {**os.environ, **config.app_env}
    print(f"  Starting app: {config.start_command}")
    return subprocess.Popen(
        config.start_command,
        shell=True,
        cwd=str(config.project_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def wait_for_app(url: str, timeout: int):
    print(f"  Waiting for app at {url} (up to {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_running(url):
            print("  App is ready.")
            return
        time.sleep(1)
    raise TimeoutError(f"App did not become available within {timeout}s")


# ── Pipeline modes ─────────────────────────────────────────────────────────


async def run_snapshot_mode(config: Config, start: bool, steps=None):
    """
    Default mode: pre-render PNG screenshots, then compose video with ffmpeg.
    The app is only needed during Phase 1 (screenshot capture).
    """
    config.ensure_dirs()

    print("\n=== autodemo-toolkit — Demo Generator (snapshot mode) ===\n")
    print(f"  App URL    : {config.app_url}")
    print(f"  Resolution : {config.video_width}x{config.video_height}")
    print(f"  TTS voice  : {config.tts_voice}")
    print(f"  Segments   : {len(steps)}")
    print()

    proc = None
    if start:
        if _is_running(config.app_url):
            print(f"App already running at {config.app_url}")
        else:
            proc = start_app(config)
            try:
                wait_for_app(config.app_url, config.app_startup_timeout)
            except TimeoutError as exc:
                print(f"Error: {exc}")
                if proc:
                    proc.terminate()
                sys.exit(1)
    else:
        if not _is_running(config.app_url):
            print(
                f"Error: app not running at {config.app_url}. "
                "Start it first or omit --no-start."
            )
            sys.exit(1)
        print(f"Using existing app at {config.app_url}")

    try:
        # Phase 1: screenshots + TTS audio run concurrently
        print("\n[1/2] Rendering screenshots + generating audio in parallel...")
        snapshots, audio_data = await asyncio.gather(
            render_snapshots(steps, config),
            generate_audio_files(steps, config),
        )
        total = sum(a["duration"] + s.pause_after for s, a in zip(steps, audio_data.values()))
        print(f"\n  Screenshots : {len(snapshots)} PNGs in {config.snapshot_dir}")
        print(f"  Audio       : {len(audio_data)} clips, ~{total:.0f}s total")

    finally:
        if proc is not None:
            print("\nStopping app...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    print("\n[2/2] Composing final video from screenshots + audio (ffmpeg)...")
    output = compose_from_screenshots(snapshots, audio_data, steps, config)
    print(f"\nDone!  ->  {output}\n")


async def run_live_mode(config: Config, start: bool, steps=None):
    """
    Live mode: record directly from the running app (single Playwright session).
    Slower than snapshot mode — the app must stay running throughout.
    """
    config.ensure_dirs()

    print("\n=== autodemo-toolkit — Demo Generator (live mode) ===\n")

    proc = None
    if start:
        if not _is_running(config.app_url):
            proc = start_app(config)
            try:
                wait_for_app(config.app_url, config.app_startup_timeout)
            except TimeoutError as exc:
                print(f"Error: {exc}")
                if proc:
                    proc.terminate()
                sys.exit(1)

    try:
        print("\n[1/3] Generating narration audio...")
        audio_data = await generate_audio_files(steps, config)

        print("\n[2/3] Recording demo video (live Playwright)...")
        video_path, segment_durations = await record_demo(steps, audio_data, config)

        print("\n[3/3] Composing final video...")
        output = compose_video(video_path, audio_data, steps, config,
                               segment_durations=segment_durations)
        print(f"\nDone!  ->  {output}\n")

    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


# ── Entry point ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Generate an automated demo video.")
    parser.add_argument("--plan", default=None,
                        help="Path to a demo_plan.yaml")
    parser.add_argument("--port", type=int, default=None,
                        help="Override app port from the plan")
    parser.add_argument("--no-start", action="store_true",
                        help="Skip starting the app (assume it's already running)")
    parser.add_argument("--live", action="store_true",
                        help="Record from live app instead of pre-rendered snapshots")
    args = parser.parse_args()

    # Plan file is required
    if args.plan:
        plan_path = Path(args.plan)
    else:
        default_plan = Path(__file__).parent / "demo_plan.yaml"
        if default_plan.exists():
            plan_path = default_plan
        else:
            print("Error: no plan file found. Provide --plan <path> or create demo_plan.yaml.")
            print("See templates/demo_plan.yaml for an example.")
            sys.exit(1)

    config, steps = load_plan(plan_path)
    use_live = args.live or plan_mode(plan_path) == "live"
    print(f"  Plan: {plan_path.name} ({len(steps)} segments)")

    if args.port is not None:
        config.app_port = args.port

    if use_live:
        asyncio.run(run_live_mode(config, start=not args.no_start, steps=steps))
    else:
        asyncio.run(run_snapshot_mode(config, start=not args.no_start, steps=steps))


if __name__ == "__main__":
    main()
