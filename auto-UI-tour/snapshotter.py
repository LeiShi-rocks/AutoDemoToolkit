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

                # Force Driver.js overlay to 0 during capture to avoid double overlay;
                # Pillow applies the dimming exactly once below.
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
