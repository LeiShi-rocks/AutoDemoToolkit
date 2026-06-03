# /demo-gen — Record a demo video from a plan file

Execute the full demo recording pipeline for any web app and produce
`autodemo/output/final/demo.mp4`.

## What this skill does

Reads a `demo_plan.yaml`, starts the target app if needed, renders screenshots
and narration audio in parallel, then composes the final video.
Works with any plan produced by `/demo-plan` — Streamlit, React, SaaS, anything.

## How to invoke

```
/demo-gen
/demo-gen --plan autodemo/my_plan.yaml
/demo-gen --plan plans/eurobet_demo.yaml --live
/demo-gen --no-start   # if the app is already running
```

Parse these from the user message:
- `--plan <path>`      — plan YAML to use (default: `autodemo/demo_plan.yaml`)
- `--live`             — live Playwright recording instead of screenshots
- `--no-start`         — skip starting the app (assume it's running)
- `--customer <name>`  — override DEMO_CUSTOMER (Experimentation Hub only)

## Steps Claude should follow

### 1. Validate

- Plan file exists; if not → suggest `/demo-plan` first
- `autodemo/venv/` exists; if not → tell user to run `autodemo/setup.sh`
- `ffmpeg` available: `which ffmpeg`
- If the plan's `config.mode` is `live`, warn that it's slower (LLM calls run live)

### 2. Run

Execute from the `autodemo/` directory:
```bash
cd /path/to/repo/autodemo
source venv/bin/activate
python main.py --plan <plan_path> [--live] [--no-start] [--customer <name>]
```

Stream all output to the user so they can see progress.

### 3. Report

On success:
- Output path of the video
- Duration and file size (`ffprobe` or `ls -lh`)

On failure:
- Show the last 30 lines of output
- Diagnose the most likely cause:
  - Port in use → app already running, suggest `--no-start`
  - Streamlit not found → point to project venv
  - Driver.js element not found → selector in plan may need updating
  - ffmpeg error → show the filter chain error, suggest checking the plan

## How the pipeline works

```
demo_plan.yaml
      │
      ▼
plan_loader.py  →  Config + List[DemoStep]
      │
      ├──[screenshot mode]──────────────────────────────────────┐
      │   Phase 1 (parallel):                                   │
      │     • Playwright visits app, executes actions,          │
      │       applies Driver.js highlight → PNG per segment     │
      │     • edge-tts generates MP3 per segment                │
      │   Streamlit stops after Phase 1                         │
      │   Phase 2 (ffmpeg only, no browser):                    │
      │     • Slideshow from PNGs with 0.4s crossfade           │
      │     • Audio overlaid at cumulative timestamps           │
      │                                                         │
      └──[live mode]────────────────────────────────────────────┤
          Phase 1: edge-tts generates audio                     │
          Phase 2: single Playwright session records .webm,     │
                   executing all actions live in sequence       │
          Phase 3: ffmpeg overlays audio on video               │
                                                                │
                           ▼                                    │
              autodemo/output/final/demo.mp4  ◄─────────────────┘
```

## Timing model

Each segment's duration in the video = `audio_clip_duration + pause_after`.
The narration plays first; the screen holds for `pause_after` seconds after it ends.
Adjust `pause_after` in the plan YAML to give viewers more or less time on each screen.

## Output location

`autodemo/output/final/demo.mp4`

Intermediate files (can be reused if you re-run with `--no-start`):
- `autodemo/output/snapshots/` — per-segment PNGs
- `autodemo/output/audio/`     — per-segment MP3s
- `autodemo/output/video/`     — raw `.webm` (live mode only)
