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
