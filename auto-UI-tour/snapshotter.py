"""
Phase 1: Pre-render PNG screenshots from the live app.

For each demo step:
  1. Execute the step action (navigate / click / expand) on the live app,
     waiting for any async content to finish rendering.
  2. Apply the Driver.js spotlight highlight.
  3. page.screenshot() — captures the exact rendered pixels: correct fonts,
     layout, charts, Driver.js overlay.

The screenshots are fed directly to ffmpeg in Phase 2 to build the video.
No rendering issues, no CORS, no hydration problems.
"""

import asyncio
from pathlib import Path
from typing import Dict, List

from playwright.async_api import async_playwright

from config import Config
from recorder import StepExecutor
from steps import DemoStep


async def render_snapshots(
    steps: List[DemoStep], config: Config
) -> Dict[str, Path]:
    """
    Visit the live app, apply Driver.js per step, take a PNG
    screenshot, and return {step_id: Path(screenshot.png)}.
    """
    config.snapshot_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            slow_mo=60,
        )
        page = await browser.new_page(
            viewport={"width": config.video_width, "height": config.video_height}
        )

        executor = StepExecutor(page, config)
        snapshots: Dict[str, Path] = {}

        for step in steps:
            print(f"  [{step.id}] rendering...", end=" ", flush=True)

            await executor.execute(step)

            if step.driver_selector:
                await executor.driver_highlight(step.driver_selector, step.driver_popover)
                await asyncio.sleep(0.5)

            out = config.snapshot_dir / f"{step.id}.png"
            await page.screenshot(path=str(out), full_page=False)

            if step.driver_selector:
                await executor.driver_destroy()

            snapshots[step.id] = out
            print(f"{out.stat().st_size // 1024}KB -> {out.name}")

        await browser.close()

    return snapshots
