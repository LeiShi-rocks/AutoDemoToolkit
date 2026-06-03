# /demo-plan — Generate a segment-based demo plan for any web UI

Generate a `demo_plan.yaml` that drives the autodemo recording pipeline.
Works for any web application — Streamlit, React, plain HTML, SaaS products, etc.

## What this skill does

Reads the user's description of what to demonstrate, optionally inspects the
target URL or source code, then writes a segment-by-segment plan YAML.
Each segment = one narration clip + one screenshot (or video clip in live mode).

The human edits the YAML before recording — change narration, reorder segments,
swap highlights — without touching any code.

## How to invoke

```
/demo-plan https://myapp.com "show how to create a new report"
/demo-plan --url http://localhost:8501 --desc "A/B test analysis walkthrough" --out plans/abt_demo.yaml
/demo-plan --customer eurobet   # for Experimentation Hub: uses customer-specific config
```

Parse these loose arguments from the user message:
- First bare URL → the app URL (used in `navigate` action of the first segment)
- Free-text description → what the demo should cover
- `--customer <name>` → Experimentation Hub shortcut (sets customer + default URL)
- `--out <path>` → output path (default: `autodemo/demo_plan.yaml`)
- `--live` → set `mode: live` in the plan config

## Steps Claude should follow

### 1. Understand the target UI

If a URL is given and you can inspect source code:
- Read relevant UI component files to understand what panels/pages/flows exist
- Note the CSS selectors or ARIA roles for key interactive elements

If no source code access, work from the description alone and use generic selectors.

### 2. Design the segments

Think like a product marketer giving a 2-minute tour:
- **Intro segment**: navigate to the app, orient the viewer (what is this?)
- **Core flow segments**: walk through the key feature being demonstrated
  step by step; each segment = one focused UI state with one thing to explain
- **Detail segments**: expand or click into anything that needs closer attention
- **Outro segment**: scroll back to top, wrap up with a call to action

Keep each narration under 3 sentences. Total demo: 10–15 segments, ~2 minutes.

### 3. Choose the right action for each segment

**General actions (work with any web app):**

| action | action_args | what it does |
|---|---|---|
| `navigate` | `url`, `wait_for` (optional CSS selector) | Go to a URL, optionally wait for element |
| `click` | `selector`, `wait_after` (default 0.5s) | Click first matching element |
| `type` | `selector`, `text`, `clear` (default true) | Type text into input/textarea |
| `scroll_top` | — | Smooth-scroll to top of page |
| `scroll_to` | `selector` | Scroll element into view |
| `scroll_down` | `pixels` (default 300) | Scroll down by N pixels |
| `hover` | `selector` | Hover over element (reveals menus/tooltips) |
| `wait` | `seconds` | Explicit pause |
| `wait_for` | `selector` | Wait until element appears |
| `press_key` | `selector`, `key` | Press Enter, Tab, Escape, etc. |
| `select_option` | `selector`, `value`/`label`/`index` | Pick from `<select>` |

**Streamlit-specific actions (Experimentation Hub only):**

| action | what it does |
|---|---|
| `load_app` | Navigate to the Streamlit URL and wait for the sidebar |
| `select_first_experiment` | Open selectbox, pick first experiment |
| `select_second_treatment` | Click the first non-baseline treatment radio |
| `expand_section` + `action_args: {keyword: "Panel Title"}` | Open a `<details>` expander by text |
| `scroll_to_characteristics` | Scroll down slightly after content panel |

### 4. Choose highlight selectors

The `highlight.selector` field targets what Driver.js spotlights in the screenshot:

- Standard CSS selector: `"button.primary"`, `"#hero-section"`, `"nav"`, `".modal"`
- ARIA-based: `"[role='dialog']"`, `"[aria-label='Search']"`
- Expander pattern: `"expander:Panel Title"` — finds `<details>` whose `<summary>` contains the text
- Omit `highlight:` entirely for segments where the full page should be visible

The `popover.side` can be `top`, `bottom`, `left`, or `right`.

### 5. Write the plan file

Output a valid YAML file. Use `>` block scalars for multi-line narration.

**Schema:**
```yaml
config:
  mode: screenshot       # screenshot | live
  resolution: [1280, 800]
  voice: en-US-JennyNeural   # any edge-tts voice name

segments:
  - id: unique_snake_case_id
    narration: >
      What the AI voice says for this segment. Keep it natural and concise.
    action: action_name
    action_args:           # optional, depends on action
      key: value
    highlight:             # optional
      selector: "css-selector-or-expander:Text"
      popover:
        title: Short Title
        description: One sentence description.
        side: bottom       # top | bottom | left | right
        align: start       # start | center | end  (optional)
    pause_after: 1.5       # seconds to hold after narration ends
```

### 6. Report

- Print the output path and count of segments
- Show a one-line summary of each segment (id + first 60 chars of narration)
- Remind the user: edit narration freely, then run `/demo-gen` to record
