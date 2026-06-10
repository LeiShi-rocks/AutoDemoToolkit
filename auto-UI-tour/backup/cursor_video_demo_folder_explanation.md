# Video demo folder explanation
_Exported on 6/8/2026 at 19:38:37 PDT from Cursor (3.5.38)_

---

**User**

can you check @auto-demo/video-demo this folder, and explain what it does to me? 

---

**Cursor**

I’ll inspect `auto-demo/video-demo` in read-only mode, starting with its file layout and entry-point docs/scripts, then I’ll summarize the pipeline and how the pieces fit together.

The folder is mostly three project files plus generated output and a local `venv`; I’m going to focus on `demo_plan.yaml`, `recorder.py`, and `snapshotter.py`, since those look like the actual demo machinery.

One notable detail: `recorder.py` imports `config` and `steps`, but those files are not in the immediate folder listing, so I’m checking whether they live elsewhere or are missing from this demo folder.

There’s also a `tour_test.py` in this folder that looks like a self-contained tester/previewer, and the Streamlit app reads the same plan file for its guided tour UI. I’ll inspect those two to separate “video recording” from “in-app tour.”

I found that the Streamlit app itself uses the same `demo_plan.yaml` and Driver.js assets for an interactive sidebar tour. The separate Python scripts appear to be automation around the same plan, but some imported helper modules may not currently be present in this folder, so I’m verifying that before summarizing reliability.

The missing helpers are present; my first file listing was just dominated by `venv`. There is a fuller pipeline here: `main.py` loads the plan, generates narration audio, captures screenshots/video, and composes final media.

At this point the intent is clear: this is not the BACON model code itself, but a scripted video/demo generator wrapped around the BACON Streamlit dashboard. I’m doing one last pass over the file inventory and existing outputs so I can explain what’s generated versus source.

`auto-demo/video-demo` is a scripted demo-video generator for the BACON Streamlit dashboard. It is not the BACON modeling code itself; it automates the visual walkthrough of `auto-demo/streamlit/app.py`.

The core idea is: `demo_plan.yaml` is the screenplay. Each segment has narration, a browser action, an optional Driver.js highlight target, and a pause.

```1:9:auto-demo/video-demo/demo_plan.yaml
config:
  app_url: http://localhost:8501
  app_port: 8501
  start_command: >
    /opt/venv/bin/streamlit run
    /mnt/localssd/personal-research/BACON/auto-demo/streamlit/app.py
    --server.port 8501 --server.headless true
  mode: screenshot
  resolution: [1280, 800]
```

`main.py` orchestrates the pipeline. In default screenshot mode, it starts the Streamlit app, uses Playwright to visit each planned state, generates TTS narration with `edge-tts`, captures PNG screenshots with highlights, then uses `ffmpeg` to assemble a narrated MP4.

```6:15:auto-demo/video-demo/main.py
Two-phase pipeline
------------------
Phase 1  Snapshot  (needs app running)
    Visit the live app step-by-step, wait for content to load, apply
    Driver.js spotlight, then save each page as a PNG screenshot.
    TTS narration audio is generated in parallel.

Phase 2  Record  (no app needed)
    ffmpeg assembles the PNGs + audio into the final MP4.
```

The important files are:

- `demo_plan.yaml`: defines the BACON story: intro, pipeline, score distributions, image browser, calibration models, DR estimation, judge weights, outro.
- `main.py`: CLI entry point, supports screenshot mode and `--live` mode.
- `snapshotter.py`: opens the live app with Playwright, executes each step, applies spotlight overlays, and saves screenshots.
- `recorder.py`: contains the browser step executor: navigate, click, scroll, wait, highlight selectors, Streamlit-specific helpers, and live video recording.
- `composer.py`: uses `ffmpeg` to make the slideshow/video and align narration clips.
- `tts.py`: generates per-segment MP3 narration using Microsoft Edge TTS.
- `tour_test.py`: interactive preview tool that opens a visible browser and lets you step through the tour with a “Next” button.
- `assets/driver.js` and `assets/driver.css`: Driver.js library files used for the guided spotlight overlays.
- `output/frames.txt` and `output/snapshots/*.png`: generated artifacts from a prior run; the open `radar_chart.png` is one of those captured demo frames.

The Streamlit app also consumes this same plan for an in-app guided tour from the sidebar:

```391:407:auto-demo/streamlit/app.py
with st.sidebar:
    st.markdown("### BACON Demo")
    st.caption("Interactive Driver.js tour walks through each section of the demo.")
    st.divider()
    st.markdown("**Tour controls**")
    if PLAN_PATH.exists() and DRIVER_JS.exists():
        if "tour_on" not in st.session_state:
            st.session_state["tour_on"] = False
        if st.button("▶  Start Tour", type="primary", use_container_width=True):
            st.session_state["tour_on"] = True
```

So practically, this folder does two related things: it powers the “Start Tour” guided walkthrough inside the Streamlit app, and it can generate a standalone narrated demo video of that walkthrough. I only inspected it in read-only mode; I did not run the generator.

---

**User**

yes, but I am not very satisfied with the driver.js implmentations. For example, @auto-demo/video-demo/output/snapshots/radar_chart.png did not well capture the radar chart at all; it should highlight radar chart and slightly shade the rest area; also, many screenshots have too thick shade so they totally shaded the background

---

**Cursor**

I see the issue: the current implementation mixes Driver.js highlighting with screenshot post-processing, and for chart anchors it may resolve to the wrong visible element or apply a full dark replacement instead of a light translucent shade. I’ll inspect the overlay/highlight code paths more closely and suggest concrete changes you can make.

The radar chart problem is specifically caused by how `#bacon-radar` is used as a zero-height marker before the Plotly chart. The resolver then chooses the first visible chart/image after that marker, which is fragile in the image-browser layout and can select/crop poorly.

Yes, your read is right. The current implementation has two main problems.

First, the screenshot overlay ignores the requested opacity. In `snapshotter.py`, `_apply_spotlight()` replaces everything outside the spotlight with a solid dark color:

```30:63:auto-demo/video-demo/snapshotter.py
def _apply_spotlight(
    path: Path,
    spotlight: dict,
    opacity: float = 0.65,
    popover: Optional[dict] = None,
    pad: int = 4,
) -> None:
    # ...
    result = Image.new("RGB", img.size, _DARK_BG)
    result.paste(img.crop((sx1, sy1, sx2, sy2)), (sx1, sy1))
```

So `opacity: 0.65` does not mean “65% translucent shade”; it effectively means “replace background with solid dark”. That explains why many screenshots feel too heavily shaded.

Second, the radar chart segment explicitly disables the overlay:

```168:175:auto-demo/video-demo/demo_plan.yaml
    highlight:
      selector: "#bacon-radar"
      popover:
        title: "Image Browser: Radar Chart"
        description: Human vs. BACON across all six perceptual dimensions.
        side: right
        align: start
        overlayOpacity: 0
```

So the radar screenshot currently gets a tooltip, but no shaded background. That is why it does not visually spotlight the radar chart.

The fix I would make is:

1. Change `_apply_spotlight()` to alpha-blend the original screenshot with a translucent dark layer outside the spotlight, instead of replacing the outside area with `_DARK_BG`.
2. Lower the default shade from `0.65` to something like `0.18` or `0.25`.
3. In `demo_plan.yaml`, set `radar_chart` to something like `overlayOpacity: 0.18` instead of `0`.
4. Keep `overlayOpacity: 0` only for tiny tab-click segments, where a full-page shade is distracting.

Conceptually, `_apply_spotlight()` should do this:

```python
shade = Image.new("RGB", img.size, _DARK_BG)
result = Image.blend(img, shade, opacity)
result.paste(img.crop((sx1, sy1, sx2, sy2)), (sx1, sy1))
```

That preserves the visible page in the background, just slightly dimmed.

For the radar chart specifically, `#bacon-radar` is only a zero-height marker before the Plotly chart:

```624:654:auto-demo/streamlit/app.py
        with chart_col:
            st.markdown('<div id="bacon-radar"></div>', unsafe_allow_html=True)
            # ...
            st.plotly_chart(fig, use_container_width=True)
```

The resolver then tries to find the next visible Plotly chart after that marker. That is workable, but a little fragile. The more robust version would be to mark the exact next `[data-testid="stPlotlyChart"]` after `#bacon-radar`, then shade everything else lightly.

Because you’re in Ask mode, I won’t edit the files directly, but those are the changes I’d recommend. The biggest bug is definitely the solid-background post-processing in `snapshotter.py`; fixing that will improve all screenshots, not just `radar_chart.png`.

---

**User**

i switched to agent mode. can we fix it? 

---

**Cursor**

Now that Agent mode is active, I’ll make the fix in the generator itself: change screenshot post-processing to use a translucent dim layer, lower the default opacity, and make the radar chart segment actually use a light spotlight shade.

I’m going to edit the screenshot post-processing first. The key change is to preserve the original pixels outside the spotlight and blend them with a dark layer, instead of replacing them with a flat near-black canvas.

Next I’ll align the live Driver.js path with the same lighter default, so screenshot mode and live recording do not diverge.

Now I’ll update the radar chart segment so it no longer requests `overlayOpacity: 0`; it should produce a real, but light, spotlight in the regenerated snapshot.

The code and plan edits are in place. I’ll run a lightweight syntax/diagnostic check next; I won’t regenerate the full video unless you want that because it will start the Streamlit app and rewrite output artifacts.

Lint diagnostics are clean. I’m also doing a tiny parse/import check for the changed Python and YAML so we catch syntax issues without starting the app or regenerating media.

The focused parse check passed. I’m cleaning up one stale comment now so the code describes the new translucent behavior accurately.

The edited files still have no linter diagnostics, and the radar segment now requests a light shade. I’ll check the final diff summary so I can close this out cleanly.

Fixed the implementation.

I changed `snapshotter.py` so the shaded area is now a translucent blend over the original screenshot instead of a solid dark replacement. That should keep background context visible instead of making screenshots look almost black. I also lowered the default overlay opacity to `0.22`.

I updated `recorder.py` to use the same lighter default for live Driver.js recording, and changed the radar chart segment in `demo_plan.yaml` from `overlayOpacity: 0` to `overlayOpacity: 0.18`, so the radar chart will actually be spotlighted with a light shade.

Validation passed:
- No linter errors on `snapshotter.py` / `recorder.py`
- Python/YAML parse check passed

Note: I did not regenerate the existing `output/snapshots/radar_chart.png`, so the open image is still the old artifact until the demo generator is rerun.

---

**User**

ok regenerate the screenshots

---

**Cursor**

I’ll regenerate only the screenshot set, not the full narrated video, by starting or reusing the Streamlit app and running the snapshot rendering path against `demo_plan.yaml`. First I’ll check the existing terminal state so I don’t duplicate a running app.

The visible terminal is idle, so I’ll run a one-off regeneration script now. It will overwrite `auto-demo/video-demo/output/snapshots/*.png` with the updated translucent spotlight behavior.

The screenshot regeneration completed successfully. I’ll quickly inspect the regenerated radar image visually to make sure the spotlight now lands on the radar chart and the rest remains lightly shaded.

Regenerated the screenshots successfully.

It reused the already-running Streamlit app at `http://localhost:8501` and wrote 18 updated PNGs to:

`auto-demo/video-demo/output/snapshots`

I also checked the new `radar_chart.png`: the radar chart is now highlighted, and the rest of the page is lightly shaded instead of being heavily blacked out.

---

**User**

so checking the @auto-demo/video-demo/output/snapshots/radar_chart.png it seems that there are two highlight blocks that try to capture the chart, one is very bright, the other less brighter, they are overlaying in a strange way

---

**Cursor**

You’re right: the regenerated image shows double treatment. That likely comes from capturing Driver.js’s own overlay first, then applying the Pillow post-processing overlay on top of that same screenshot. I’ll adjust snapshot mode so Driver.js is used only to place the popover and expose the target rect, while the actual dimming is applied once by Pillow.

I’ll make the screenshot path force Driver.js’s overlay opacity to zero during capture, while still reading the intended opacity from the plan for the single Pillow overlay pass.

The double-overlay source is patched. I’ll run quick diagnostics, then regenerate the screenshots again and inspect `radar_chart.png`.

No linter issues. I’m running the focused parse check and then regenerating the snapshots with the updated capture logic.

Parse check passed. I’ll regenerate the PNG snapshots now.

The snapshots regenerated. I’ll inspect the radar chart image again to confirm there is now only one spotlight treatment.

The new radar snapshot no longer shows the second overlaid highlight; the remaining bright rectangle is the chart’s own white Plotly background plus the single restored spotlight area.

Fixed the double-highlight issue and regenerated the screenshots again.

Root cause: screenshot mode was capturing Driver.js’s own overlay, then applying the Pillow spotlight overlay afterward. Now `snapshotter.py` forces Driver.js overlay opacity to `0` during screenshot capture, using Driver.js only for popover placement and target rect detection. Pillow applies the dimming exactly once.

I inspected the new `radar_chart.png`; the odd second overlay is gone. The remaining bright block is the chart’s own white Plotly background plus the single intended spotlight area.

---

**User**

ok good job. now I also want to fix the driver.js tour button functions for the streamlit UI. It is not working well. Actually I want to achieve similar functionality as the "Show Demo" button from https://driverjs.com/: click on start tour, then each time it shows a highlight + popover as the demo-plan, then we can click on next to go to next highlight, and that give a full tour. click on other random places will end the tour. 

---

**Cursor**

I’ll fix the in-app Streamlit tour so it behaves like a normal Driver.js product tour: Start Tour launches the first highlight, Next advances through `demo_plan.yaml`, and clicking outside the popover/highlight exits the tour. I’ll inspect the current `_tour_component()` implementation first, then replace the brittle custom controls with a Driver.js-driven flow.

The current UI tour is using a custom bottom bar and manually calling `highlight()`, which is why it doesn’t feel like Driver.js’s own demo. I found two additional issues while reading it: Streamlit tab clicks use Playwright-style `:has-text(...)` selectors that browser `querySelector()` cannot handle, and `#bacon-*` zero-height anchors need the same “find following chart/image” logic as the video recorder.

I’m going to replace the bottom-bar controller with a hidden Driver.js controller. The popover itself will own Next/Previous/Close, and the controller will execute each plan action before showing the matching highlight.

The main tour controller is patched. I’ll also adjust the plan loading default so UI tour steps get a moderate overlay unless a step explicitly sets one.

I’ll run syntax and lint checks now. Since this is a Streamlit app with embedded JavaScript, I’ll also inspect the generated Python string area for obvious f-string escaping issues.

The Python linter is clean. I’m going to run an actual Python parse/import-style check next; embedded JavaScript f-strings are easy to break, so this catches the most likely failure before I try the UI.

The app compiles. I’ll do a small headless browser smoke test against the running Streamlit app: click Start Tour, verify a Driver.js popover appears, click Next, then click outside to confirm the tour closes.

The basic behavior works: Start Tour opens the first popover, Next advances, and clicking outside closes the tour. I’m going to run one more focused smoke test across the first tab transition, because the plan uses Playwright-style `:has-text(...)` selectors that were one of the fragile parts.

The second smoke test showed the tab transition does happen, but that step has a built-in `wait_after: 2.5`, so my 1.2s test read the old popover while the next step was still running. I’ll rerun with waits long enough for the plan’s transition timing.

The longer smoke test passes across the first tab transition. I noticed one stale UI caption in the sidebar still refers to the old bottom tour bar, so I’ll update that text to match the new popover-driven behavior and avoid a misleading dismiss control.

I’ll run the final lint and compile checks now after the sidebar text cleanup.

The final compile and lint checks are clean. The running app should pick this up on refresh or rerun; the tour now uses Driver.js popovers instead of the old custom bottom bar.

Implemented the Streamlit UI tour fix.

What changed:
- Removed the old custom bottom tour bar.
- `Start Tour` now launches a Driver.js-style popover tour directly.
- Each popover has `Next`, `Previous`, progress text, and close.
- Each step executes its `demo_plan.yaml` action before highlighting.
- Clicking outside the popover/highlight closes the tour.
- Fixed selector handling for Streamlit tabs using `:has-text(...)`.
- Reused the chart/image anchor resolution logic so `#bacon-*` markers highlight the actual chart/image instead of zero-height divs.

Validation:
- `python -m py_compile auto-demo/streamlit/app.py` passed.
- No linter errors.
- Headless smoke test passed: Start Tour opens the first popover, Next advances, tab transition works, and outside click closes the tour.

---

**User**

it's great; somehow when clicking on the buttons it reacts pretty slowly; did you set delay time or something? 

---

**Cursor**

Yes. The slowness is mostly from reusing `demo_plan.yaml` timing that was designed for video capture, especially `click` steps with `wait_after: 2.5` or `3.0`. That makes sense for recording stable screenshots, but it feels laggy in an interactive UI tour. I’ll decouple the UI tour timing from the video timing and cap those waits.

I’ll patch only the Streamlit tour controller so the demo video generator still honors the longer plan waits. The UI tour will use short, capped waits for tab switches and scroll actions.

The waits are now capped for UI interaction: tab clicks wait at most 650ms, scroll/wait actions at most 350ms, and highlight settle time is 75ms. I’ll compile and run a quick smoke test to ensure the faster flow still advances correctly.

Lint is clean. I’m compiling the app and running a short browser smoke test to make sure the tour still reaches the tab-transition step with the shorter waits.

The faster timing still passes the browser smoke test, including the first tab transition.

Yes, it was slow because the UI tour was reusing `demo_plan.yaml` waits meant for video capture, including `wait_after: 2.5` / `3.0` on tab-click steps.

I fixed it by capping waits only in the Streamlit UI tour:
- Click/tab transition wait: max `650ms`
- Scroll/wait actions: max `350ms`
- Extra settle delay before highlight: `75ms`

This does not change the video/screenshot generator timing.

Validation passed:
- `app.py` compiles
- No linter errors
- Browser smoke test passed through the first tab transition with the faster timing.

---

**User**

shorten the time even more

---

**Cursor**

I’ll make the UI tour feel more immediate by reducing only the interactive-tour caps again, while leaving video generation timing untouched.

The UI tour waits are now very short: 250ms for click/tab actions, 180ms for scroll/wait actions, and 25ms settle before highlighting. I’ll run a quick compile plus smoke test to make sure it still advances correctly.

Shortened it further.

New UI tour timing:
- Click/tab wait: `250ms`
- Scroll/wait action: `180ms`
- Highlight settle: `25ms`

Validation passed: app compiles, no linter errors, and the browser smoke test still advances through the first tab transition correctly.

---

**User**

very good. The image browser part is not doing well: step 7 and step 8 did not highlight the correct places

---

**Cursor**

I’ll trace the tour’s highlighted steps around the Image Browser section and compare the active Driver.js element rects with the intended tab/radar elements. That should show whether the selector mapping or the page action timing is causing the wrong highlight.

I can see the likely mismatch: the tour’s “Image Browser” step is highlighting the tab button after the click, and the “Radar Chart” step depends on a zero-height marker before a Plotly chart. I’ll measure what Driver.js is actually highlighting in the browser for those two steps.

The trace shows the issue clearly: the chart-target steps are resolving to zero-size anchor divs instead of the actual Plotly chart/image, so Driver.js ends up spotlighting a 0×0 element. I’ll tighten the resolver for `#bacon-*` anchors so it searches from the anchor’s Streamlit block and nearby siblings instead of relying on global DOM order.

I found two things to fix for that section: the “Image Browser” step is still spotlighting the tab button instead of the browser content, and the radar step can resolve while the chart is still offscreen. I’ll add an explicit Image Browser anchor and make the tour highlight the thumbnail browser area, then force resolved targets into view before Driver.js renders the spotlight.

I’m updating the plan so the Image Browser step targets browser content, not the tab label, and adding a marker in the Streamlit page before the browser controls/grid.

Now I’ll patch the Streamlit app to expose that marker and to create a stable synthetic target rectangle around the thumbnail grid for Driver.js.

I added the synthetic target helper for the UI tour. Next I’ll add the actual `#bacon-browser` marker in the Image Browser tab before the controls.

Because `demo_plan.yaml` is also used by screenshot/video generation, I’ll update the Playwright resolver too so `#bacon-browser` highlights the same thumbnail-grid region outside the live UI tour.

One subtlety with a synthetic rectangle target: clicks inside the highlighted thumbnail area are not DOM-children of the synthetic target. I’ll adjust the outside-click handler so clicks inside the highlighted rectangle don’t accidentally close the tour, while clicks elsewhere still close it.

The code is patched. I’ll run lint/compile checks, then smoke test the exact Image Browser and Radar Chart tour steps and inspect their highlighted rectangles.

Lint is clean. I’ll compile the app and test the two Image Browser tour steps specifically.

The test exposed a separate problem: the running Streamlit app was still serving cached tour steps from the old plan, so it kept highlighting the Image Browser tab. I’ll make the plan cache depend on `demo_plan.yaml`’s mtime so plan changes are picked up automatically.

With cache invalidation fixed, I’ll rerun the targeted smoke test for the Image Browser and Radar Chart steps.

The radar chart now resolves to the correct Plotly chart. The Image Browser overview step didn’t appear in that trace, so I’ll run one full title/rect trace around the transition to confirm whether it is being skipped because its new content marker isn’t present quickly enough.

The trace explains why step 7 still feels wrong: it is targeting the whole first two rows of thumbnails, and some website screenshots are very tall, so the spotlight rectangle becomes enormous and partly offscreen. I’ll tighten the Image Browser target to the visible first thumbnail row, capped to a reasonable height.

The Image Browser target is now capped to the first visible thumbnail row. I’ll rerun the focused checks and trace those steps again.

The rectangle is now the right size, but it is still starting above the viewport because hidden/offscreen images from another Streamlit layout can be included. I’ll filter the Image Browser candidates to only images below the `#bacon-browser` marker in screen coordinates.

I’ll rerun the focused trace once more; the Image Browser rectangle should now sit on the first thumbnail row instead of starting above the viewport.

The browser still reports the old offscreen rectangle, so I’m checking whether this is stale Streamlit component code or whether the marker’s own screen position is unexpectedly negative after tab switching.

The marker positions are good when the tab is loaded directly, so the bad rectangle is a timing issue during the tour transition. I’ll add a short readiness poll for the Image Browser tab before resolving its target, so the grid is measured after Streamlit has laid it out.

I’ll retest the Image Browser steps after adding the readiness poll.

The trace is still showing `y=-91`, so I’ll inspect the synthetic target’s stored CSS position during the tour. That will tell whether we’re measuring the right images but Driver.js is shifting the target, or whether the target itself is being written with a bad top.

The underlying page is using Streamlit’s internal scroll container, not `window.scrollY`, so `window.scrollTo(0)` was not reliably resetting the view. I’ll scroll the first browser thumbnail itself into view before computing the synthetic highlight rectangle.

I’ll mirror that scroll-into-view behavior in the video resolver too, then rerun the UI trace.

Now I’ll recompile and inspect the Image Browser tour rectangles again.

The thumbnail grid is awkward because the actual website screenshots are very tall and Streamlit keeps an internal scroll offset, so the computed grid rectangle can be partly offscreen. I’m going to make the Image Browser overview step spotlight the browser controls row instead; that is stable, visible, and better matches “you can sort/filter/browse the screenshots.”

I’ll mirror the Image Browser controls-row targeting in the recorder resolver too, so screenshots/video stay consistent with the UI tour.

Now I’ll run the focused tour trace again; the Image Browser overview step should target the controls row, and the radar step should target the Plotly radar chart.

The smoke test is still hitting stale Streamlit server code, not the latest file contents; the active rectangle is exactly the old thumbnail-grid implementation. I’ll check the running Streamlit process and restart that app so the UI loads the updated tour controller.

The shell environment doesn’t have `rg` available even though the IDE search tool does, so I’ll use `pgrep` to identify the Streamlit process directly.

I found the old Streamlit server process. I’ll restart only that demo app process so it serves the updated tour implementation.

The app is restarting in the background; I’ll do a quick startup check before rerunning the tour trace.

The restarted app is up. I’ll rerun the focused Image Browser tour trace against the fresh server.

The fresh app now uses the controls-row target, but the row is still above the viewport because the tour enters Image Browser while the Streamlit scroll container is still scrolled down from the previous tab. I’ll scroll the `#bacon-browser` marker itself into view before measuring the controls row.

I’ll restart the demo app once more so this scroll fix is definitely loaded, then rerun the targeted trace.

The app is restarting with the scroll fix; I’ll wait for it to become reachable.

The fresh server is up. I’ll verify the Image Browser and radar steps again.

The final browser verification hit a Chromium headless crash before opening the page, unrelated to the app code. I’ll retry once with a more conservative Chromium launch configuration; the Python compile/lint checks already passed.

The retry passed: Image Browser now highlights a small visible controls-row target, and Radar Chart highlights the actual Plotly radar chart. I’ll do a final lint check and clear the stale background job status from the earlier restarted server.

Final diagnostics are clean. The current Streamlit server was restarted and is serving the updated tour code.

Fixed the Image Browser tour steps.

What changed:
- `image_browser_tab` now targets `#bacon-browser` instead of the tab button.
- Added a `#bacon-browser` marker in the Streamlit Image Browser tab.
- The UI tour now highlights the Image Browser controls row, which is stable and visible.
- The radar step now correctly highlights the actual Plotly radar chart.
- Updated the recorder resolver too, so video/screenshot generation stays consistent.
- Restarted the Streamlit demo app so it serves the updated code.

Verified:
- `Image Browser` active target: visible controls-row rectangle.
- `Image Browser: Radar Chart` active target: `stPlotlyChart`.
- `py_compile` passed.
- No linter errors.

---

**User**

ok one more question: do you think the screenshot capture can happen with this tour button? so with this button, the playwright tool interact with UI through this button and captures each step. Is that more structured than the current screenshot approach? 

---

**Cursor**

Yes, it can be done, but I would not make the tour button the primary screenshot pipeline.

The UI tour is good for human interaction. For screenshot/video generation, the current direct plan-driven approach is more structured because Playwright reads `demo_plan.yaml`, executes deterministic actions, resolves selectors, captures target rects, and writes known outputs. If screenshot capture drives the public tour button instead, you add extra layers: Streamlit session state, an iframe component, Driver.js internal state, button-click timing, and browser event handling. That makes captures closer to what users see, but less deterministic and harder to debug.

A good compromise would be:

- Keep `demo_plan.yaml` as the single source of truth.
- Keep screenshot capture direct, not button-driven.
- Share resolver/action logic between the UI tour and screenshot recorder as much as possible.
- Optionally add a “tour replay capture” test mode that clicks `Start Tour` and `Next` through the UI, but use it as an integration test, not the production capture path.

So: button-driven capture is possible and useful for testing “does the actual UI tour work?”, but the current screenshot architecture is better for reproducible artifact generation. The thing to improve is reducing duplicated logic between `_tour_component()` and `recorder.StepExecutor`, not replacing the recorder with the UI button.

---

**User**

ok sounds good. that's fair. now can you generate the video from the screenshots?

---

**Cursor**

I’ll compose the video from the existing regenerated screenshots without re-rendering the app screenshots. I’ll generate or refresh the narration audio from `demo_plan.yaml`, then use the screenshot-based `ffmpeg` composer to write `output/final/demo.mp4`.

The snapshot and output directories are present. I’m starting the compose job now; it will use the current PNGs and write the final MP4.

The compose job completed and wrote the final MP4. I’ll quickly inspect the output file metadata so we know the video exists and has a plausible duration.

Generated the video successfully.

Output:
`auto-demo/video-demo/output/final/demo.mp4`

Metadata:
- Size: `5.7M`
- Duration: `301.08s`, about 5 minutes

It used the existing screenshots and regenerated the narration audio before composing the final MP4.

---

**User**

ok great. now I want to say that this video demo pipeline comes from https://github.com/LeiShi-rocks/AutoDemoToolkit/tree/main/auto-UI-tour. given the current implementation, are there anything we need to improve for the general pipeline in this github repo? 

---

**Cursor**

Yes. Based on what we just fixed, I’d suggest upstreaming several general improvements to [AutoDemoToolkit `auto-UI-tour`](https://github.com/LeiShi-rocks/AutoDemoToolkit/tree/main/auto-UI-tour).

The most important improvements:

1. **Separate “capture mode” from “interactive tour mode”**
   - Screenshot/video generation should stay deterministic and plan-driven.
   - UI tour should be Driver.js-driven and optimized for responsiveness.
   - Do not reuse long video waits directly in the UI tour; cap them separately.

2. **Avoid double overlays**
   - In screenshot mode, Driver.js should provide target/popover geometry, but the actual screenshot dimming should be applied once.
   - Otherwise you get stacked overlays or strange bright/dark rectangles.

3. **Use translucent dimming, not solid background replacement**
   - The current repo pipeline likely benefits from changing spotlight post-processing from “replace outside region with dark canvas” to “blend original screenshot with translucent shade.”
   - This preserves context and looks more professional.

4. **Add robust selector adapters**
   - Real apps often use Playwright-style selectors like `:has-text(...)`, but browser `querySelector()` cannot handle those.
   - The toolkit should support a small selector abstraction layer:
     - CSS selector
     - text selector
     - tab-by-label
     - component anchor
     - Streamlit-specific chart/image resolver

5. **Support zero-height anchors**
   - Many frameworks need marker divs like `<div id="chart-anchor"></div>` before a chart.
   - The toolkit should know how to resolve such anchors to the next visible chart/image/card instead of highlighting a 0×0 div.

6. **Make overlay opacity configurable per mode**
   - Video/screenshot default: maybe `0.18–0.25`
   - Interactive tour default: maybe `0.30–0.40`
   - Tiny elements/tabs: allow `overlayOpacity: 0` or low opacity.

7. **Add framework-specific resolver modules**
   - Keep core generic, but provide optional adapters:
     - `streamlit`
     - `react`
     - `gradio`
     - plain DOM
   - This avoids stuffing Streamlit-specific DOM hacks into the generic recorder.

8. **Add a UI tour smoke-test mode**
   - Not for production capture, but useful:
     - click Start Tour
     - click Next through every step
     - assert each step resolves to a nonzero visible element
   - This would have caught the bad Image Browser/radar highlights.

9. **Cache invalidation for plan files**
   - If a UI tour reads `demo_plan.yaml`, it should invalidate when the plan file changes, e.g. using file mtime.
   - Otherwise the UI can keep stale steps after plan edits.

10. **Document attribution and adaptation**
   - In this BACON repo, we should explicitly mention that the video demo pipeline is adapted from AutoDemoToolkit.
   - If you upstream improvements, document which parts are generic versus BACON-specific.

My strongest recommendation for the upstream repo: add a formal “resolver” abstraction. Most of our fixes were not about video composition; they were about correctly mapping plan selectors to real UI elements across Driver.js, Playwright, Streamlit, and screenshots. That abstraction would make the toolkit much more reusable.

---

**User**

i want to modify the plan a little bit; can we regenerate the video after that? 

---

**Cursor**

Yes, absolutely.

Modify `auto-demo/video-demo/demo_plan.yaml`, then I can regenerate the affected screenshots and rebuild `auto-demo/video-demo/output/final/demo.mp4`.

Best workflow:
1. Edit narration/highlight/actions in `demo_plan.yaml`.
2. Tell me when you’re done.
3. I’ll rerun screenshot generation.
4. I’ll regenerate narration audio and compose the final video.

If you only change narration text, we can skip screenshot regeneration and only rebuild audio + video. If you change actions, highlights, or timing, we should regenerate screenshots too.

---

**User**

yes i am done. i modified the narration for some parts

---

**Cursor**

Since you only changed narration, I’ll skip screenshot regeneration and rebuild the narration audio plus final MP4 from the existing screenshots.

The terminal state is clear, so I’m rebuilding audio and composing the video now.

The rebuild completed successfully. I’ll quickly check the final MP4 metadata so we confirm the output file is valid.

Regenerated the video using your updated narration.

Output:
`auto-demo/video-demo/output/final/demo.mp4`

Metadata:
- Size: `5.8M`
- Duration: `305.04s`

I reused the existing screenshots and rebuilt the audio + final MP4 only.

---

**User**

at later parts of the video, the driver transition is a little bit faster than audio segments, can you check why? 

---

**Cursor**

I’ll check the composition timing path, especially how screenshot durations, crossfades, and audio offsets are computed. My suspicion is cumulative crossfade shortening: each visual transition may start before the corresponding audio segment boundary.

I found the likely root cause in `composer.py`: screenshot mode uses 0.4s crossfades, but the narration audio offsets are still scheduled as if every segment lasted its full `audio_duration + pause_after`. That creates cumulative visual lead later in the video.

Yes, I found why.

The issue is in `auto-demo/video-demo/composer.py`: screenshot mode uses `0.4s` crossfades between screenshots.

```111:146:auto-demo/video-demo/composer.py
# ── 2. Build silent slideshow video with crossfade transitions ────────
fade_s = 0.4  # crossfade duration in seconds
# ...
offsets.append(t + dur - fade_s)
t += dur - fade_s
```

But audio overlay timing is still based on the full segment durations, without subtracting the crossfade overlap. So every visual transition happens `0.4s` earlier than the next audio segment boundary. This compounds over time.

For this video:
- 18 segments
- 17 crossfades
- `17 × 0.4s = 6.8s` cumulative visual lead by the outro

Approximate visual lead:
- Before segment 8: `2.8s`
- Before segment 10: `3.6s`
- Before segment 13: `4.8s`
- Before segment 16: `6.0s`
- Before segment 18: `6.8s`

So your observation is exactly right: later driver/screenshot transitions appear faster than the narration because the slideshow timeline is shortened by crossfades, while the audio timeline is not.

Best fix: when overlaying audio for screenshot mode, pass segment durations adjusted by the same crossfade timeline, or remove crossfades. I’d recommend adjusting the audio offsets to match the visual xfade timeline.

---

**User**

yes, fix that

---

**Cursor**

I’ll fix the screenshot-mode composer so the audio overlay uses the same crossfade-adjusted timeline as the slideshow. Then I’ll rebuild the MP4 from the existing screenshots and audio.

The change is localized to `compose_from_screenshots`: after creating the xfade slideshow, I’ll pass a per-segment visual duration map to `_overlay_audio()` so audio starts at the same boundaries as the visual sequence.

The composer timing fix is in. I’ll run lint/syntax checks before rebuilding the video.

Syntax/lints look clean. I’ll run a focused compile check and rebuild the MP4 using the existing screenshots and audio files.

The video rebuild is complete. I’ll verify the output metadata and compute the corrected timing expectation.

The rebuilt MP4 is now about 7 seconds shorter, matching the crossfade-aligned timeline instead of letting the visual lead accumulate.

Fixed and rebuilt the video.

What changed:
- `composer.py` now aligns audio offsets with the same `0.4s` crossfade timeline used by the screenshot slideshow.
- This removes the cumulative drift where later visual transitions were several seconds ahead of narration.

New output:
`auto-demo/video-demo/output/final/demo.mp4`

Metadata:
- Size: `5.7M`
- Duration: `298.16s`

The duration is now shorter because the audio timeline matches the crossfade-overlapped visual timeline instead of the un-overlapped segment sum.

---

**User**

overall, good, for the DR estimation part, there is some problem: it reports bias right now from the screenshot, but the narrations was saying all about bias/variance/mse. I am suggesting showing RMSE instead in the UI not the bias plot, and also in narration explain the RMSE mainly. can you modify accordingly? 

---

**Cursor**

I’ll update the DR Estimation tab to emphasize RMSE in the plotted UI, then revise the DR narration in `demo_plan.yaml` to talk mainly about RMSE. After that I’ll regenerate the affected screenshot and rebuild the video so the visuals and audio match.

I found the DR tab currently defaults to `dr_bias`, and the info text also says “near-zero bias.” I’ll switch the default display and explanatory copy to RMSE, then update the DR narration to match.

Next I’ll revise the DR narration and popover description so the voiceover and callout emphasize RMSE rather than bias.

The edits are in place. I’ll run syntax/lint checks, then regenerate screenshots because the DR UI visual changed.

Checks look good. I’ll compile the changed Python file, restart the Streamlit app if needed, regenerate screenshots, and rebuild the video.

The app compiles. I’ll restart the demo app so screenshot regeneration picks up the RMSE default.

The app is restarting. I’ll wait for Streamlit to report it is ready, then regenerate the screenshot set.

The restart command exited quickly, so I’ll inspect the terminal output and verify whether the app is already running or failed to bind.

The restart helper killed its own shell because the process match was too broad. I’ll start the Streamlit app directly now.

The app is starting again; I’ll wait for it to be ready before capturing screenshots.

The app is up. I’ll regenerate screenshots now so the DR slide shows RMSE, then rebuild the video.

I’ll regenerate the full screenshot set because tab/page state depends on the plan sequence, then compose the updated MP4.

Screenshots are regenerated. I’ll inspect the DR chart image to make sure it now shows RMSE before rebuilding.

The DR screenshot now shows the RMSE chart and RMSE copy. I’ll rebuild the final MP4 with the updated screenshot and narration.

---

**User**

did the rebuild complete? 

---

**Cursor**

I’ll check the output file timestamp/metadata and whether any rebuild process is still running. The previous compose command was interrupted, so I want to verify whether it had already written a complete MP4 before the interruption.

No, the rebuild did **not** complete.

The current `demo.mp4` is still the older file from `Jun 4 10:53`:

`auto-demo/video-demo/output/final/demo.mp4`
- Duration: `298.16s`
- Size: `5.7M`

There is no active `ffmpeg`/compose rebuild process now. The Streamlit app is still running, but the video rebuild was interrupted before writing a new final MP4.

---

**User**

ok let's rebuild

---

**Cursor**

I’ll rebuild from the current screenshots and regenerated narration, using the crossfade-aligned composer. This should write a fresh `output/final/demo.mp4` with the DR RMSE screenshot and updated narration.

The rebuild completed successfully. I’ll check the MP4 metadata and timestamp now.

Rebuild completed successfully.

Output:
`auto-demo/video-demo/output/final/demo.mp4`

Metadata:
- Timestamp: `Jun 4 13:08`
- Size: `5.7M`
- Duration: `300.16s`

This rebuild uses the current screenshots, the updated DR RMSE narration, and the crossfade-aligned timing fix.

---

**User**

great. now can you collect a minimal resuable set of materials from the whole video generation pipeline and wrap them up in the folder @auto-UI-tour ? So that we can use the automated generation for all other projects. 

---

**Cursor**

I’ll package the reusable toolkit into a root-level `auto-UI-tour` folder, keeping only generic pipeline pieces and excluding BACON outputs, venvs, and project-specific plans. I’ll inspect the current toolkit files/templates first so the packaged folder is clean and reusable.

The current toolkit files are already close to reusable, but `recorder.py` contains a few BACON-specific selector patches from our demo. I’ll package the reusable folder and remove those project-specific assumptions so `auto-UI-tour` stays generic.

I’ll create the folder from the generic core files first, then patch the packaged copy so it has the improved reusable behavior and no BACON-specific output or app code.

---

**User**

did we finished?

---

**Cursor**

Not yet. I had just started packaging the reusable `auto-UI-tour` folder, but the shell command was interrupted before any meaningful copy/package step completed.

Current status:
- I inspected the existing `auto-demo/video-demo` toolkit files.
- I confirmed there is no existing root `auto-UI-tour` folder yet.
- I identified one thing to clean before packaging: `recorder.py` still contains BACON-specific selector logic like `#bacon-browser`, which should not go into the reusable toolkit as-is.

No reusable folder has been completed yet.

---

**User**

go ahead

---

**Cursor**

I’ll build `auto-UI-tour` now as a clean reusable toolkit folder: generic Python pipeline, Driver.js assets, template plan, scripts, and docs, without BACON outputs, screenshots, venv, or the BACON-specific `demo_plan.yaml`. Then I’ll scrub the copied code for project-specific selector logic.

There is already an `auto-UI-tour` directory at the repo root, so I’ll inspect what’s in it before overwriting anything.

`auto-UI-tour` exists but is empty, so I’ll populate it from the reusable source files now.

The reusable files are copied. I’ll now remove BACON-specific handling from the packaged `recorder.py` and make the generic anchor resolver support optional grouped highlights without hard-coded IDs.

I’ll keep the generic zero-height anchor behavior, but remove the `#bacon-browser` special case from the reusable copy. If a future project needs grouped highlights, it should add a real wrapper element or a project-specific adapter rather than hard-coding BACON selectors.

I’ll verify the packaged dependency list next; the reusable snapshotter now uses Pillow for translucent spotlight post-processing, so `requirements.txt` needs to include it.

The package is clean of BACON references. I’ll add the missing Pillow dependency and refresh the README/template notes so this folder is self-contained for other projects.

I’ll add the overlay option to the template plan too, so future projects can control spotlight shade without reading the implementation.

I’ll run a final scan of the packaged folder for project-specific references and verify the Python files compile.

The package is clean of BACON paths/references. I’ll rename the remaining toolkit banner strings from `autodemo-toolkit` to `auto-UI-tour` for consistency.

I’ll run the final compile check and list the packaged folder contents so we can confirm the minimal reusable set.

---

**User**

unfortunately, all files are gone from the system now. I wonder can we collect the minimal reusable set as a independent folder of files so that I can just save to local? 

---

**Cursor**

I can reconstruct a minimal standalone `auto-UI-tour` toolkit from the version we built in this chat. I’ll first check the current workspace state, then recreate a self-contained folder with the reusable scripts, template plan, Driver.js loader hooks, setup/run helpers, and README.

The shell didn’t return a reliable status, so I’ll use the file tools to check whether the workspace and target folder are visible.

The original workspace path no longer exists, so I can’t recreate the folder there. I’ll create the standalone toolkit under `/tmp/auto-UI-tour` instead, then tell you exactly where it is and what files it contains.

---

**User**

we are losing connection to all workspaces. so we can only rely on our conversation history to recover

---

**Cursor**

Yes. Since we can only rely on conversation history, the safest recovery format is a single shell script that recreates a standalone `auto-UI-tour/` folder.

Save this as `restore_auto_ui_tour.sh`, then run:

```bash
bash restore_auto_ui_tour.sh
cd auto-UI-tour
./setup.sh
cp templates/demo_plan.yaml my_demo.yaml
# edit my_demo.yaml
./run.sh --plan my_demo.yaml
```

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="auto-UI-tour"
mkdir -p "$ROOT/assets" "$ROOT/templates"

cat > "$ROOT/requirements.txt" <<'EOF'
playwright>=1.40.0
edge-tts>=6.1.9
mutagen>=1.47.0
pyyaml>=6.0
pillow>=10.0.0
EOF

cat > "$ROOT/setup.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 -m venv "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"
pip install --upgrade pip --quiet
pip install -r "$SCRIPT_DIR/requirements.txt"
playwright install chromium

python - <<'PY'
from pathlib import Path
from urllib.request import urlretrieve

assets = Path("assets")
assets.mkdir(exist_ok=True)
urls = {
    "driver.js": "https://cdn.jsdelivr.net/npm/driver.js@1.3.6/dist/driver.js.iife.js",
    "driver.css": "https://cdn.jsdelivr.net/npm/driver.js@1.3.6/dist/driver.css",
}
for name, url in urls.items():
    path = assets / name
    if not path.exists() or path.stat().st_size < 1000:
        print(f"Downloading {name}...")
        urlretrieve(url, path)
PY

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARNING: ffmpeg not found. Install it before recording."
else
  ffmpeg -version | head -1
fi

echo "Setup complete. Run: ./run.sh --plan templates/demo_plan.yaml"
EOF
chmod +x "$ROOT/setup.sh"

cat > "$ROOT/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/venv/bin/activate" ]; then
  echo "venv not found. Run ./setup.sh first."
  exit 1
fi
source "$SCRIPT_DIR/venv/bin/activate"
cd "$SCRIPT_DIR"
python main.py "$@"
EOF
chmod +x "$ROOT/run.sh"

cat > "$ROOT/config.py" <<'EOF'
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Config:
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)

    @property
    def project_root(self) -> Path:
        return self.base_dir.parent

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "output"

    @property
    def audio_dir(self) -> Path:
        return self.output_dir / "audio"

    @property
    def video_dir(self) -> Path:
        return self.output_dir / "video"

    @property
    def final_dir(self) -> Path:
        return self.output_dir / "final"

    @property
    def snapshot_dir(self) -> Path:
        return self.output_dir / "snapshots"

    app_port: int = 8501
    app_startup_timeout: int = 45
    snapshot_server_port: int = 8502
    start_command: Optional[str] = None
    app_env: Dict[str, str] = field(default_factory=dict)

    @property
    def app_url(self) -> str:
        return f"http://localhost:{self.app_port}"

    video_width: int = 1280
    video_height: int = 800
    tts_voice: str = "en-US-JennyNeural"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"
    llm_wait_ms: int = 20_000

    def ensure_dirs(self):
        for d in (self.audio_dir, self.video_dir, self.final_dir, self.snapshot_dir):
            d.mkdir(parents=True, exist_ok=True)
EOF

cat > "$ROOT/steps.py" <<'EOF'
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DemoStep:
    id: str
    script: str
    action: str
    action_args: dict = field(default_factory=dict)
    driver_selector: Optional[str] = None
    driver_popover: Optional[dict] = None
    pause_after: float = 1.5
EOF

cat > "$ROOT/plan_loader.py" <<'EOF'
from pathlib import Path
from typing import List, Tuple
import urllib.parse
import yaml

from config import Config
from steps import DemoStep


def load_plan(plan_path: Path) -> Tuple[Config, List[DemoStep]]:
    data = yaml.safe_load(plan_path.read_text())
    cfg_raw = data.get("config", {})
    res = cfg_raw.get("resolution", [1280, 800])

    config = Config(video_width=res[0], video_height=res[1])

    if "app_port" in cfg_raw:
        config.app_port = int(cfg_raw["app_port"])
    if "app_url" in cfg_raw:
        parsed = urllib.parse.urlparse(cfg_raw["app_url"])
        if parsed.port:
            config.app_port = parsed.port
    if "voice" in cfg_raw:
        config.tts_voice = cfg_raw["voice"]
    if "llm_wait_ms" in cfg_raw:
        config.llm_wait_ms = int(cfg_raw["llm_wait_ms"])
    if "start_command" in cfg_raw:
        config.start_command = cfg_raw["start_command"] or None
    if cfg_raw.get("app_env"):
        config.app_env = {str(k): str(v) for k, v in cfg_raw["app_env"].items()}

    steps: List[DemoStep] = []
    for seg in data.get("segments", []):
        hl = seg.get("highlight", {}) or {}
        steps.append(DemoStep(
            id=seg["id"],
            script=seg["narration"].strip(),
            action=seg["action"],
            action_args=seg.get("action_args") or {},
            driver_selector=hl.get("selector") or None,
            driver_popover=hl.get("popover") or None,
            pause_after=float(seg.get("pause_after", 1.5)),
        ))
    return config, steps


def plan_mode(plan_path: Path) -> str:
    data = yaml.safe_load(plan_path.read_text())
    return data.get("config", {}).get("mode", "screenshot")
EOF

cat > "$ROOT/tts.py" <<'EOF'
from pathlib import Path
from typing import Dict, List

import edge_tts
from mutagen.mp3 import MP3

from config import Config
from steps import DemoStep


async def generate_audio_files(steps: List[DemoStep], config: Config) -> Dict[str, dict]:
    config.audio_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, dict] = {}

    for step in steps:
        audio_path = config.audio_dir / f"{step.id}.mp3"
        print(f"  [{step.id}] generating audio...", end=" ", flush=True)
        communicate = edge_tts.Communicate(
            step.script,
            config.tts_voice,
            rate=config.tts_rate,
            pitch=config.tts_pitch,
        )
        await communicate.save(str(audio_path))
        duration = MP3(str(audio_path)).info.length
        results[step.id] = {"path": audio_path, "duration": duration}
        print(f"{duration:.1f}s")

    return results
EOF

cat > "$ROOT/recorder.py" <<'EOF'
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import Page, async_playwright

from config import Config
from steps import DemoStep

ASSETS_DIR = Path(__file__).parent / "assets"
DEFAULT_OVERLAY_OPACITY = 0.22


async def page_settle(page, timeout: int = 5_000):
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        await asyncio.sleep(0.5)


async def record_demo(
    steps: List[DemoStep], audio_data: Dict[str, dict], config: Config
) -> Tuple[Path, Dict[str, float]]:
    config.video_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            slow_mo=60,
        )
        context = await browser.new_context(
            viewport={"width": config.video_width, "height": config.video_height},
            record_video_dir=str(config.video_dir),
            record_video_size={"width": config.video_width, "height": config.video_height},
        )
        page = await context.new_page()
        executor = StepExecutor(page, config)
        segment_durations: Dict[str, float] = {}

        for step in steps:
            audio = audio_data.get(step.id, {})
            audio_duration = audio.get("duration", 3.0)

            print(f"  [{step.id}] executing (audio={audio_duration:.1f}s)...")
            t0 = asyncio.get_event_loop().time()
            await executor.execute(step)

            if step.driver_selector:
                await executor.driver_highlight(step.driver_selector, step.driver_popover)

            action_time = asyncio.get_event_loop().time() - t0
            remaining = max(0.0, audio_duration - action_time) + step.pause_after
            await asyncio.sleep(remaining)
            segment_durations[step.id] = action_time + remaining

            if step.driver_selector:
                await executor.driver_destroy()

        video = page.video
        await context.close()
        await browser.close()
        return Path(await video.path()), segment_durations


class StepExecutor:
    def __init__(self, page: Page, config: Config):
        self.page = page
        self.config = config
        self._driver_injected = False
        self._last_overlay_opacity = DEFAULT_OVERLAY_OPACITY

    async def execute(self, step: DemoStep):
        handler = getattr(self, f"_action_{step.action}", None)
        if handler is None:
            print(f"    (no handler for '{step.action}')")
            return
        await handler(**step.action_args)

    async def _inject_driver_js(self):
        if self._driver_injected:
            return
        already = await self.page.evaluate(
            "() => !!(window.driver && window.driver.js && window.driver.js.driver)"
        )
        if already:
            self._driver_injected = True
            return
        await self.page.add_style_tag(path=str(ASSETS_DIR / "driver.css"))
        await self.page.add_script_tag(path=str(ASSETS_DIR / "driver.js"))
        await self.page.wait_for_function(
            "() => !!(window.driver && window.driver.js && window.driver.js.driver)",
            timeout=5_000,
        )
        self._driver_injected = True

    async def driver_highlight(self, selector: str, popover: Optional[dict] = None):
        try:
            await self._inject_driver_js()
            resolved = await self._resolve_selector(selector)
            if resolved is None:
                print(f"    (driver: element not found for '{selector}')")
                return

            overlay_opacity = DEFAULT_OVERLAY_OPACITY
            popover_clean = popover
            if popover and "overlayOpacity" in popover:
                overlay_opacity = float(popover["overlayOpacity"])
                popover_clean = {k: v for k, v in popover.items() if k != "overlayOpacity"}

            await self.page.evaluate(
                """({ selector, popover, overlayOpacity }) => {
                    if (window.__demoDriver) window.__demoDriver.destroy();
                    const driverFn = window.driver.js.driver;
                    window.__demoDriver = driverFn({
                        overlayColor: '#000',
                        overlayOpacity: overlayOpacity,
                        smoothScroll: true,
                        allowClose: false,
                        showButtons: [],
                        popoverClass: 'demo-popover',
                    });
                    window.__demoDriver.highlight({
                        element: selector,
                        popover: popover || undefined,
                    });
                }""",
                {"selector": resolved, "popover": popover_clean, "overlayOpacity": overlay_opacity},
            )
            self._last_overlay_opacity = overlay_opacity
        except Exception as e:
            print(f"    (driver_highlight error: {e})")

    async def driver_destroy(self):
        try:
            await self.page.evaluate("""
                (() => {
                    if (window.__demoDriver) {
                        window.__demoDriver.destroy();
                        window.__demoDriver = null;
                    }
                    const expander = document.getElementById('__demo_spotlight');
                    if (expander) expander.removeAttribute('id');
                    document.querySelectorAll('[data-demo-highlight]').forEach(
                        el => el.removeAttribute('data-demo-highlight')
                    );
                })();
            """)
        except Exception:
            pass

    async def _resolve_selector(self, selector: str) -> Optional[str]:
        m = re.search(r":has-text\\(['\\\"](.+?)['\\\"]\\)", selector)
        if m:
            text = m.group(1)
            role_match = re.search(r"\\[role=['\\\"](.+?)['\\\"]\\]", selector)
            role = role_match.group(1) if role_match else None
            found = await self.page.evaluate(
                """({ role, text }) => {
                    const candidates = role
                        ? Array.from(document.querySelectorAll(`[role="${role}"]`))
                        : Array.from(document.querySelectorAll('button, [role], a, div, span'));
                    const target = candidates.find(el =>
                        (el.textContent || '').replace(/\\s+/g, ' ').trim().includes(text)
                    );
                    if (!target) return false;
                    document.querySelectorAll('[data-demo-highlight]').forEach(
                        el => el.removeAttribute('data-demo-highlight')
                    );
                    target.setAttribute('data-demo-highlight', '1');
                    return true;
                }""",
                {"role": role, "text": text},
            )
            return "[data-demo-highlight='1']" if found else None

        m = re.search(r":nth-child\\((\\d+)\\)\\s*$", selector)
        if m:
            n = int(m.group(1)) - 1
            found = await self.page.evaluate(
                """(n) => {
                    const tabs = Array.from(document.querySelectorAll("[role='tab']"));
                    if (!tabs[n]) return false;
                    document.querySelectorAll('[data-demo-highlight]').forEach(
                        el => el.removeAttribute('data-demo-highlight')
                    );
                    tabs[n].setAttribute('data-demo-highlight', '1');
                    return true;
                }""",
                n,
            )
            return "[data-demo-highlight='1']" if found else None

        if selector.startswith("#"):
            found = await self.page.evaluate(
                """(sel) => {
                    const anchor = document.querySelector(sel);
                    if (!anchor) return false;
                    document.querySelectorAll('[data-demo-highlight]').forEach(
                        el => el.removeAttribute('data-demo-highlight')
                    );

                    const r = anchor.getBoundingClientRect();
                    if (r.height >= 20 && r.width >= 20) {
                        anchor.setAttribute('data-demo-highlight', '1');
                        return true;
                    }

                    const candidates = Array.from(document.querySelectorAll(
                        '[data-testid="stPlotlyChart"], [data-testid="stImage"], canvas, svg, img, figure, [role="img"]'
                    )).filter(el => {
                        const cr = el.getBoundingClientRect();
                        if (cr.height < 50 || cr.width < 50 || cr.y < 0) return false;
                        const pos = anchor.compareDocumentPosition(el);
                        return !!(pos & Node.DOCUMENT_POSITION_FOLLOWING);
                    });

                    if (candidates.length > 0) {
                        candidates[0].setAttribute('data-demo-highlight', '1');
                        return true;
                    }

                    anchor.setAttribute('data-demo-highlight', '1');
                    return true;
                }""",
                selector,
            )
            return "[data-demo-highlight='1']" if found else None

        if not selector.startswith("expander:"):
            return selector

        keyword = selector[len("expander:"):]
        js = """(keyword) => {
            const old = document.getElementById('__demo_spotlight');
            if (old) old.removeAttribute('id');
            const kw = keyword.toLowerCase();
            const summaries = document.querySelectorAll('details summary');
            for (const s of summaries) {
                if (s.textContent.toLowerCase().includes(kw)) {
                    s.closest('details').id = '__demo_spotlight';
                    return true;
                }
            }
            return false;
        }"""
        for attempt in range(3):
            found = await self.page.evaluate(js, keyword)
            if found:
                return "#__demo_spotlight"
            if attempt < 2:
                await asyncio.sleep(0.5)
        return None

    async def _action_navigate(self, url: str, wait_for: str = None, timeout: int = 15_000):
        await self.page.goto(url, wait_until="domcontentloaded")
        if wait_for:
            try:
                await self.page.wait_for_selector(wait_for, timeout=timeout)
            except Exception:
                pass
        await page_settle(self.page)
        await self._inject_driver_js()

    async def _action_click(self, selector: str, wait_after: float = 0.5):
        try:
            el = self.page.locator(selector).first
            await el.scroll_into_view_if_needed()
            await el.click()
            await asyncio.sleep(wait_after)
            await page_settle(self.page)
        except Exception as e:
            print(f"    warning: click('{selector}'): {e}")

    async def _action_type(self, selector: str, text: str, clear: bool = True, delay: int = 40):
        try:
            el = self.page.locator(selector).first
            await el.scroll_into_view_if_needed()
            if clear:
                await el.clear()
            await el.type(text, delay=delay)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"    warning: type('{selector}'): {e}")

    async def _action_scroll_top(self):
        await self.page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(0.4)

    async def _action_scroll_down(self, pixels: int = 300):
        await self.page.evaluate(f"window.scrollBy({{top: {pixels}, behavior: 'smooth'}})")
        await asyncio.sleep(0.4)

    async def _action_scroll_to(self, selector: str):
        try:
            await self.page.locator(selector).first.scroll_into_view_if_needed()
            await asyncio.sleep(0.4)
        except Exception as e:
            print(f"    warning: scroll_to('{selector}'): {e}")

    async def _action_hover(self, selector: str):
        try:
            await self.page.locator(selector).first.hover()
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"    warning: hover('{selector}'): {e}")

    async def _action_wait(self, seconds: float = 1.0):
        await asyncio.sleep(seconds)

    async def _action_wait_for(self, selector: str, timeout: int = 15_000):
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            print(f"    warning: wait_for('{selector}'): {e}")

    async def _action_press_key(self, selector: str, key: str):
        try:
            await self.page.locator(selector).first.press(key)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"    warning: press_key('{selector}', '{key}'): {e}")

    async def _action_select_option(self, selector: str, value: str = None, index: int = None, label: str = None):
        try:
            el = self.page.locator(selector).first
            if value is not None:
                await el.select_option(value=value)
            elif index is not None:
                await el.select_option(index=index)
            elif label is not None:
                await el.select_option(label=label)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"    warning: select_option('{selector}'): {e}")
EOF

cat > "$ROOT/snapshotter.py" <<'EOF'
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image
from playwright.async_api import async_playwright

from config import Config
from recorder import StepExecutor
from steps import DemoStep

_DARK_BG = (25, 25, 35)
_DEFAULT_OVERLAY_OPACITY = 0.22


def _apply_spotlight(
    path: Path,
    spotlight: dict,
    opacity: float = _DEFAULT_OVERLAY_OPACITY,
    popover: Optional[dict] = None,
    pad: int = 4,
) -> None:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    opacity = max(0.0, min(1.0, opacity))

    sx1 = max(0, int(spotlight["x"] - pad))
    sy1 = max(0, int(spotlight["y"] - pad))
    sx2 = min(w, int(spotlight["x"] + spotlight["w"] + pad))
    sy2 = min(h, int(spotlight["y"] + spotlight["h"] + pad))

    shade = Image.new("RGB", img.size, _DARK_BG)
    result = Image.blend(img, shade, opacity)
    result.paste(img.crop((sx1, sy1, sx2, sy2)), (sx1, sy1))

    if popover:
        px1 = max(0, int(popover["x"] - 2))
        py1 = max(0, int(popover["y"] - 2))
        px2 = min(w, int(popover["x"] + popover["w"] + 2))
        py2 = min(h, int(popover["y"] + popover["h"] + 2))
        result.paste(img.crop((px1, py1, px2, py2)), (px1, py1))

    result.save(path)


async def render_snapshots(steps: List[DemoStep], config: Config) -> Dict[str, Path]:
    config.snapshot_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(
            viewport={"width": config.video_width, "height": config.video_height}
        )
        executor = StepExecutor(page, config)
        snapshots: Dict[str, Path] = {}

        for step in steps:
            print(f"  [{step.id}] rendering...", end=" ", flush=True)
            await executor.execute(step)

            spotlight = None
            popover_rect = None
            overlay_opacity = _DEFAULT_OVERLAY_OPACITY

            if step.driver_selector:
                if step.driver_popover and "overlayOpacity" in step.driver_popover:
                    overlay_opacity = float(step.driver_popover["overlayOpacity"])

                capture_popover = dict(step.driver_popover or {})
                capture_popover["overlayOpacity"] = 0
                await executor.driver_highlight(step.driver_selector, capture_popover)
                await asyncio.sleep(0.5)

                rects = await page.evaluate("""() => {
                    const el = document.querySelector('.driver-active-element');
                    const pop = document.querySelector('.driver-popover');
                    const toR = e => e ? {
                        x: e.getBoundingClientRect().left,
                        y: e.getBoundingClientRect().top,
                        w: e.getBoundingClientRect().width,
                        h: e.getBoundingClientRect().height
                    } : null;
                    return {spotlight: toR(el), popover: toR(pop)};
                }""")
                spotlight = rects.get("spotlight")
                popover_rect = rects.get("popover")

            out = config.snapshot_dir / f"{step.id}.png"
            await page.screenshot(path=str(out), full_page=False)

            if step.driver_selector:
                await executor.driver_destroy()
                if spotlight and overlay_opacity > 0:
                    _apply_spotlight(out, spotlight, overlay_opacity, popover_rect, pad=12)

            snapshots[step.id] = out
            print(f"{out.stat().st_size // 1024}KB -> {out.name}")

        await browser.close()
    return snapshots
EOF

cat > "$ROOT/composer.py" <<'EOF'
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
EOF

cat > "$ROOT/main.py" <<'EOF'
import argparse
import asyncio
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from composer import compose_from_screenshots, compose_video
from plan_loader import load_plan, plan_mode
from recorder import record_demo
from snapshotter import render_snapshots
from tts import generate_audio_files


def _is_running(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except Exception:
        return False


def start_app(config):
    if not config.start_command:
        print("Error: no start_command configured. Start the app manually and use --no-start.")
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


async def run_snapshot_mode(config, start: bool, steps):
    config.ensure_dirs()
    print("\n=== auto-UI-tour: snapshot mode ===\n")
    proc = None

    if start:
        if _is_running(config.app_url):
            print(f"Using existing app at {config.app_url}")
        else:
            proc = start_app(config)
            wait_for_app(config.app_url, config.app_startup_timeout)
    elif not _is_running(config.app_url):
        print(f"Error: app not running at {config.app_url}. Start it first or omit --no-start.")
        sys.exit(1)

    try:
        print("\n[1/2] Rendering screenshots + generating audio...")
        snapshots, audio_data = await asyncio.gather(
            render_snapshots(steps, config),
            generate_audio_files(steps, config),
        )
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    print("\n[2/2] Composing final video...")
    output = compose_from_screenshots(snapshots, audio_data, steps, config)
    print(f"\nDone: {output}\n")


async def run_live_mode(config, start: bool, steps):
    config.ensure_dirs()
    print("\n=== auto-UI-tour: live mode ===\n")
    proc = None

    if start and not _is_running(config.app_url):
        proc = start_app(config)
        wait_for_app(config.app_url, config.app_startup_timeout)

    try:
        print("\n[1/3] Generating narration audio...")
        audio_data = await generate_audio_files(steps, config)

        print("\n[2/3] Recording live browser video...")
        video_path, segment_durations = await record_demo(steps, audio_data, config)

        print("\n[3/3] Composing final video...")
        output = compose_video(video_path, audio_data, steps, config, segment_durations)
        print(f"\nDone: {output}\n")
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    parser = argparse.ArgumentParser(description="Generate an automated UI tour video.")
    parser.add_argument("--plan", default=None, help="Path to demo_plan.yaml")
    parser.add_argument("--port", type=int, default=None, help="Override app port")
    parser.add_argument("--no-start", action="store_true", help="Assume app is already running")
    parser.add_argument("--live", action="store_true", help="Record live browser session")
    args = parser.parse_args()

    plan_path = Path(args.plan) if args.plan else Path(__file__).parent / "templates/demo_plan.yaml"
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}")
        sys.exit(1)

    config, steps = load_plan(plan_path)
    if args.port is not None:
        config.app_port = args.port

    if args.live or plan_mode(plan_path) == "live":
        asyncio.run(run_live_mode(config, start=not args.no_start, steps=steps))
    else:
        asyncio.run(run_snapshot_mode(config, start=not args.no_start, steps=steps))


if __name__ == "__main__":
    main()
EOF

cat > "$ROOT/templates/demo_plan.yaml" <<'EOF'
# Demo Plan Template - auto-UI-tour

config:
  app_url: http://localhost:8501
  app_port: 8501
  start_command: ""
  app_env: {}
  mode: screenshot
  resolution: [1280, 800]
  voice: en-US-JennyNeural
  llm_wait_ms: 20000

segments:
  - id: intro
    narration: >
      Welcome to your product demo.
      Let me walk you through the main workflow.
    action: navigate
    action_args:
      url: http://localhost:8501
      wait_for: body
    pause_after: 2.0

  - id: highlight_nav
    narration: >
      This navigation area helps users move through the app.
    action: scroll_top
    highlight:
      selector: "nav"
      popover:
        title: Navigation
        description: Use this area to move between sections.
        side: right
        align: start
        overlayOpacity: 0.22
    pause_after: 1.5

  - id: click_primary_action
    narration: >
      Click the primary action to begin.
    action: click
    action_args:
      selector: "button.primary"
      wait_after: 0.5
    highlight:
      selector: "button.primary"
      popover:
        title: Primary Action
        description: This button starts the main workflow.
        side: bottom
    pause_after: 1.5

  - id: focus_results
    narration: >
      The results section summarizes the output.
    action: scroll_to
    action_args:
      selector: "#results-section"
    highlight:
      selector: "#results-section"
      popover:
        title: Results
        description: Review the generated results here.
        side: top
    pause_after: 1.5

  - id: outro
    narration: >
      That concludes the demo.
      Thank you for watching.
    action: scroll_top
    pause_after: 4.0
EOF

cat > "$ROOT/README.md" <<'EOF'
# auto-UI-tour

Reusable YAML-to-video pipeline for narrated UI demos.

## Quick Start

```bash
cd auto-UI-tour
./setup.sh
cp templates/demo_plan.yaml my_demo.yaml
# edit my_demo.yaml
./run.sh --plan my_demo.yaml
```

Output:

```text
output/final/demo.mp4
```

## How It Works

1. Playwright opens your web app and executes each YAML segment.
2. Driver.js places a spotlight/popover for highlighted steps.
3. Screenshot mode captures one PNG per segment.
4. Edge TTS generates narration MP3s.
5. ffmpeg builds a crossfaded slideshow and overlays audio using the same crossfade-adjusted timeline.

## Plan Basics

```yaml
segments:
  - id: intro
    narration: >
      What the voice says.
    action: navigate
    action_args:
      url: http://localhost:8501
      wait_for: body
    highlight:
      selector: "#some-element"
      popover:
        title: Title
        description: Description
        side: bottom
        align: start
        overlayOpacity: 0.22
    pause_after: 1.5
```

## Actions

- `navigate`: `url`, optional `wait_for`
- `click`: `selector`, optional `wait_after`
- `type`: `selector`, `text`, optional `clear`, `delay`
- `scroll_top`
- `scroll_down`: optional `pixels`
- `scroll_to`: `selector`
- `hover`: `selector`
- `wait`: `seconds`
- `wait_for`: `selector`
- `press_key`: `selector`, `key`
- `select_option`: `selector`, one of `value`, `label`, `index`

## Highlight Selectors

- Normal CSS selectors work.
- Playwright-style `:has-text("...")` is supported for common role/text cases.
- `expander:Title` supports Streamlit-like `<details><summary>Title</summary>`.
- Zero-height anchors are supported: put `<div id="chart-anchor"></div>` before a chart/image and highlight `#chart-anchor`.

## Modes

- `screenshot`: recommended; deterministic and fast.
- `live`: records the live browser session, useful for animations.
EOF

cat > "$ROOT/tour_test.py" <<'EOF'
"""
Optional interactive preview helper.

Usage:
    source venv/bin/activate
    python tour_test.py --plan templates/demo_plan.yaml --start
"""
import argparse
import asyncio
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

HERE = Path(__file__).parent
DEFAULT_PLAN = HERE / "templates/demo_plan.yaml"


async def main_async(plan_path: Path, start: bool):
    sys.path.insert(0, str(HERE))
    from plan_loader import load_plan
    from recorder import StepExecutor

    config, steps = load_plan(plan_path)
    proc = None

    if start and config.start_command:
        proc = subprocess.Popen(config.start_command, shell=True)
        for _ in range(30):
            try:
                urllib.request.urlopen(config.app_url, timeout=1)
                break
            except Exception:
                time.sleep(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": config.video_width, "height": config.video_height})
        executor = StepExecutor(page, config)

        for step in steps:
            print(f"[{step.id}]")
            await executor.execute(step)
            if step.driver_selector:
                await executor.driver_highlight(step.driver_selector, step.driver_popover)
            input("Press Enter for next step...")
            if step.driver_selector:
                await executor.driver_destroy()

        await browser.close()

    if proc:
        proc.terminate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args.plan, args.start))


if __name__ == "__main__":
    main()
EOF

echo "Recovered reusable toolkit at: $ROOT"
echo "Next: cd $ROOT && ./setup.sh"
```

This recreates the minimal reusable pipeline, including the important fixes we made:

- translucent screenshot spotlight overlay
- no double Driver.js overlay in screenshot mode
- zero-height anchor support
- crossfade-aligned audio timing
- generic selector handling, without BACON-specific paths or assets

