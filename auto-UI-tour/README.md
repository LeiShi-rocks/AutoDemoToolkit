# autodemo-toolkit

A minimal, reusable pipeline that turns a YAML demo plan into a narrated MP4 video of any web app. Point it at a Streamlit app, a React SPA, a plain HTML page, or a SaaS product — no code changes required.

## Quick start

```bash
# 1. Clone / copy the toolkit into your project
cp -r autodemo-toolkit/ myproject/

# 2. Install dependencies (creates venv, installs Playwright + ffmpeg check)
cd myproject/autodemo-toolkit
./setup.sh

# 3. Write your demo plan
cp templates/demo_plan.yaml my_demo.yaml
# Edit my_demo.yaml: set app_url, start_command, and add your segments

# 4. Record
./run.sh --plan my_demo.yaml
# Output: output/final/demo.mp4
```

## How it works

Two phases:

1. **Snapshot phase** — Playwright visits your running app, executes each step
   (navigate, click, scroll, type), applies a Driver.js spotlight highlight, and
   saves a PNG screenshot. Edge-TTS generates narration MP3s in parallel.

2. **Compose phase** — ffmpeg assembles the PNGs into a slideshow with 0.4s
   crossfades, then overlays the narration audio at the correct timestamps.
   No browser or app needed in this phase.

**Live mode** (`mode: live` or `--live`): Playwright records a `.webm` of the
live app in real time, then ffmpeg overlays the audio. Slower, but useful when
screenshots miss dynamic animations.

## Plan schema reference

```yaml
config:
  app_url: http://localhost:8501   # URL of your running app
  app_port: 8501                   # Port to health-check (derived from app_url if omitted)
  start_command: "npm start"       # Shell command to start the app (optional)
  app_env:                         # Extra env vars for the app process (optional)
    KEY: value
  mode: screenshot                 # screenshot (default) | live
  resolution: [1280, 800]
  voice: en-US-JennyNeural         # edge-tts voice (edge-tts --list-voices)
  llm_wait_ms: 20000               # Max ms to wait for async content

segments:
  - id: my_segment                 # Unique snake_case id
    narration: >
      What the voice says.
    action: <action_name>
    action_args:                   # Depends on action (see table below)
      key: value
    highlight:                     # Optional Driver.js spotlight
      selector: "css-selector"
      popover:
        title: Title
        description: One sentence.
        side: bottom               # top | bottom | left | right
        align: start               # start | center | end
    pause_after: 1.5               # Seconds to hold after narration ends
```

### Action reference

| Action | Args | Description |
|---|---|---|
| `navigate` | `url`, `wait_for` | Go to URL, optionally wait for CSS selector |
| `click` | `selector`, `wait_after` | Click first matching element |
| `type` | `selector`, `text`, `clear` | Type text into input/textarea |
| `scroll_top` | — | Smooth-scroll to top |
| `scroll_down` | `pixels` (default 300) | Scroll down N pixels |
| `scroll_to` | `selector` | Scroll element into view |
| `hover` | `selector` | Hover (reveals tooltips/menus) |
| `wait` | `seconds` | Explicit pause |
| `wait_for` | `selector` | Wait until element appears |
| `press_key` | `selector`, `key` | Press Enter, Tab, Escape, etc. |
| `select_option` | `selector`, `value`/`label`/`index` | Pick from `<select>` |

Streamlit-specific actions (`load_app`, `expand_section`, `select_first_experiment`,
`select_second_treatment`, `scroll_to_characteristics`) are implemented in
`recorder.py` and kept as reference for Streamlit-based projects.

### Highlight selectors

- Standard CSS: `"button.primary"`, `"#hero"`, `"[role='dialog']"`
- Expander shorthand: `"expander:Panel Title"` — finds `<details>` whose `<summary>` contains the text
- Omit `highlight:` entirely to show the full page without a spotlight

## Two recording modes

| | Screenshot mode (default) | Live mode |
|---|---|---|
| Speed | Fast — app only needed for Phase 1 | Slower — app must stay running |
| Quality | Pixel-perfect PNGs, crossfade transitions | Captures real animations |
| Reliability | High — no timing sensitivity | Depends on app response time |
| When to use | Almost always | Dynamic animations, real-time data |

Set `mode: screenshot` or `mode: live` in the plan config, or pass `--live` to `run.sh`.

## Adapting for a new project

1. Copy `templates/demo_plan.yaml` to your project
2. Set `app_url` and `start_command` for your app
3. Replace the example segments with steps that match your UI
4. Use browser DevTools to find the right CSS selectors for highlights
5. Run `./run.sh --plan your_plan.yaml --no-start` (with app already running) to iterate quickly

The toolkit itself needs no changes — all customization lives in the YAML plan.

## Requirements

- Python 3.9+
- ffmpeg (install separately: `brew install ffmpeg` or `sudo apt install ffmpeg`)
- Internet access for edge-tts (Microsoft Azure TTS, free, no API key needed)
- Chromium (installed automatically by `playwright install chromium`)
