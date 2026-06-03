import asyncio
import http.server
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Page

from config import Config
from steps import DemoStep

ASSETS_DIR = Path(__file__).parent / "assets"


async def page_settle(page, timeout: int = 5_000):
    """Wait for the page to reach a quiet state (network idle or short timeout)."""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        await asyncio.sleep(1)


def _start_snapshot_server(snapshot_dir: Path, port: int) -> threading.Thread:
    """Serve snapshot HTML files over HTTP so fonts from localhost load without CORS errors."""
    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(snapshot_dir), **kwargs)
        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return t


async def record_from_snapshots(
    steps: List[DemoStep],
    snapshots: Dict[str, Path],
    audio_data: Dict[str, dict],
    config: Config,
) -> Path:
    """
    Phase 2: Load pre-rendered HTML snapshots and record as video.

    Snapshots are served via a local HTTP server so fonts and icons fetched
    from the app origin are same-origin-safe (both localhost).
    No LLM or app calls are made — pure static HTML playback.
    Driver.js is injected fresh per step and uses smoothScroll to scroll the
    highlighted element into view before the spotlight appears.
    """
    config.video_dir.mkdir(parents=True, exist_ok=True)

    server_port = config.snapshot_server_port
    _start_snapshot_server(config.snapshot_dir, server_port)
    base_url = f"http://127.0.0.1:{server_port}"
    await asyncio.sleep(0.3)  # give the server a moment to bind

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                # Disable CORS so font/asset files from the app origin load
                # correctly when the snapshot page is served from a different
                # local port. Safe for local automation — no user data at risk.
                "--disable-web-security",
            ],
        )
        context = await browser.new_context(
            viewport={"width": config.video_width, "height": config.video_height},
            record_video_dir=str(config.video_dir),
            record_video_size={"width": config.video_width, "height": config.video_height},
        )
        page = await context.new_page()
        executor = StepExecutor(page, config)

        for step in steps:
            audio = audio_data.get(step.id, {})
            total_wait = audio.get("duration", 3.0) + step.pause_after

            print(f"  [{step.id}] ({total_wait:.1f}s)...")

            snapshot = snapshots.get(step.id)
            if snapshot and snapshot.exists():
                url = f"{base_url}/{snapshot.name}"
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_load_state("networkidle", timeout=10_000)

                # Re-inject driver.js (page.goto wipes the previous injection)
                executor._driver_injected = False
                if step.driver_selector:
                    await executor.driver_highlight(step.driver_selector, step.driver_popover)
                    await asyncio.sleep(0.8)  # let smoothScroll + fade-in settle

            await asyncio.sleep(total_wait)

            if step.driver_selector:
                await executor.driver_destroy()

        video = page.video
        await context.close()
        await browser.close()
        return Path(await video.path())


async def record_demo(
    steps: List[DemoStep], audio_data: Dict[str, dict], config: Config
) -> Tuple[Path, Dict[str, float]]:
    """Record the browser session as a video. Returns (path, segment_durations)."""
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

            seg_dur = action_time + remaining
            segment_durations[step.id] = seg_dur

            if abs(action_time - audio_duration) > 0.5:
                print(
                    f"    [{step.id}] timing note: action={action_time:.2f}s "
                    f"audio={audio_duration:.2f}s segment={seg_dur:.2f}s"
                )

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

    async def execute(self, step: DemoStep):
        handler = getattr(self, f"_action_{step.action}", None)
        if handler is None:
            print(f"    (no handler for '{step.action}')")
            return
        await handler(**step.action_args)

    # ── Driver.js ────────────────────────────────────────────────────────────

    async def _inject_driver_js(self):
        """Inject driver.js CSS + JS into the live page (once per session)."""
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
        """Spotlight an element with a Driver.js overlay."""
        try:
            await self._inject_driver_js()
            resolved = await self._resolve_selector(selector)
            if resolved is None:
                print(f"    (driver: element not found for '{selector}')")
                return
            await self.page.evaluate(
                """({ selector, popover }) => {
                    try {
                        if (window.__demoDriver) window.__demoDriver.destroy();
                        const driverFn = window.driver.js.driver;
                        window.__demoDriver = driverFn({
                            overlayColor: 'rgba(0,0,0,0.65)',
                            overlayOpacity: 0.65,
                            smoothScroll: true,
                            allowClose: false,
                            showButtons: [],
                            popoverClass: 'demo-popover',
                        });
                        window.__demoDriver.highlight({
                            element: selector,
                            popover: popover || undefined,
                        });
                    } catch (e) {
                        console.error('[driver highlight]', e.message);
                    }
                }""",
                {"selector": resolved, "popover": popover},
            )
        except Exception as e:
            print(f"    (driver_highlight error: {e})")

    async def driver_destroy(self):
        """Tear down driver.js overlay and clean up temp ids."""
        try:
            await self.page.evaluate("""
                (function() {
                    if (window.__demoDriver) {
                        window.__demoDriver.destroy();
                        window.__demoDriver = null;
                    }
                    const el = document.getElementById('__demo_spotlight');
                    if (el) el.removeAttribute('id');
                })();
            """)
        except Exception:
            pass

    async def _resolve_selector(self, selector: str) -> Optional[str]:
        """
        Resolve a selector to a CSS string usable by Driver.js.
        Supports "expander:Keyword Text" to find a <details> by its summary text.
        """
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
        # Retry up to 3 times in case the element is briefly absent during re-render
        for attempt in range(3):
            try:
                found = await self.page.evaluate(js, keyword)
                if found:
                    return "#__demo_spotlight"
                if attempt < 2:
                    await asyncio.sleep(0.5)
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(0.5)
        return None

    # ── Generic actions (work with any web app) ──────────────────────────────

    async def _action_navigate(self, url: str, wait_for: str = None, timeout: int = 15_000):
        """Navigate to any URL and optionally wait for a CSS selector to appear."""
        await self.page.goto(url, wait_until="domcontentloaded")
        if wait_for:
            try:
                await self.page.wait_for_selector(wait_for, timeout=timeout)
            except Exception:
                pass
        await page_settle(self.page)
        await self._inject_driver_js()

    async def _action_click(self, selector: str, wait_after: float = 0.5):
        """Click the first element matching selector."""
        try:
            el = self.page.locator(selector).first
            await el.scroll_into_view_if_needed()
            await el.click()
            await asyncio.sleep(wait_after)
            await page_settle(self.page)
        except Exception as e:
            print(f"    warning: click('{selector}'): {e}")

    async def _action_type(self, selector: str, text: str,
                           clear: bool = True, delay: int = 40):
        """Type text into an input/textarea."""
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
        """Smooth-scroll to the top of the page."""
        await self.page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(0.4)

    async def _action_scroll_down(self, pixels: int = 300):
        """Scroll down by a fixed number of pixels."""
        await self.page.evaluate(
            f"window.scrollBy({{top: {pixels}, behavior: 'smooth'}})"
        )
        await asyncio.sleep(0.4)

    async def _action_scroll_to(self, selector: str):
        """Scroll the element matching selector into view."""
        try:
            await self.page.locator(selector).first.scroll_into_view_if_needed()
            await asyncio.sleep(0.4)
        except Exception as e:
            print(f"    warning: scroll_to('{selector}'): {e}")

    async def _action_hover(self, selector: str):
        """Move the mouse over an element (useful for revealing tooltips/menus)."""
        try:
            await self.page.locator(selector).first.hover()
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"    warning: hover('{selector}'): {e}")

    async def _action_wait(self, seconds: float = 1.0):
        """Pause for the given number of seconds."""
        await asyncio.sleep(seconds)

    async def _action_wait_for(self, selector: str, timeout: int = 15_000):
        """Wait until selector appears in the DOM."""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            print(f"    warning: wait_for('{selector}'): {e}")

    async def _action_press_key(self, selector: str, key: str):
        """Press a keyboard key while selector has focus (e.g. 'Enter', 'Tab')."""
        try:
            await self.page.locator(selector).first.press(key)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"    warning: press_key('{selector}', '{key}'): {e}")

    async def _action_select_option(self, selector: str,
                                    value: str = None, index: int = None, label: str = None):
        """Select an <option> inside a <select> element."""
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

    # ── Streamlit/ExperimentationHub-specific actions ────────────────────────
    # These are kept as reference implementations for Streamlit-based apps.
    # Copy and adapt them in your own project as needed.

    async def _wait_ready(self, timeout: int = 8_000):
        """Wait for Streamlit's status widget to disappear (signals render complete)."""
        try:
            await self.page.wait_for_selector(
                "[data-testid='stStatusWidget']", state="hidden", timeout=timeout
            )
        except Exception:
            await asyncio.sleep(2)

    async def _action_load_app(self):
        """Streamlit-specific: navigate to the configured app URL and wait for the sidebar."""
        await self._action_navigate(
            url=self.config.app_url,
            wait_for="section[data-testid='stSidebar']",
            timeout=15_000,
        )
        await self._wait_ready(timeout=self.config.llm_wait_ms)
        await asyncio.sleep(1)
        await self.page.evaluate("window.scrollTo(0, 0)")

    async def _action_scroll_to_characteristics(self):
        """Streamlit-specific: scroll down slightly after the Content panel."""
        await self.page.evaluate("window.scrollBy({top: 200, behavior: 'smooth'})")
        await asyncio.sleep(0.4)

    async def _action_select_first_experiment(self):
        """Streamlit-specific: select the first experiment in the selectbox."""
        await self._action_select_experiment(index=0)

    async def _action_select_experiment(self, index: int = 0, label: str = None):
        """Select a Streamlit selectbox option by index or visible label text."""
        try:
            selectbox = self.page.locator("[data-testid='stSelectbox']").first
            await selectbox.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await selectbox.click()
            try:
                await self.page.wait_for_selector("[role='option']", timeout=5000)
            except Exception:
                print(f"    warning: select_experiment: dropdown never opened")
                return
            result = await self.page.evaluate(
                """({ index, label }) => {
                    const opts = [...document.querySelectorAll('[role="option"]')];
                    const texts = opts.map(o => o.textContent.trim());
                    const target = label
                        ? opts.find(o => o.textContent.trim() === label)
                        : opts[index];
                    if (!target) return { clicked: false, found: texts };
                    target.click();
                    return { clicked: true, found: texts };
                }""",
                {"index": index, "label": label},
            )
            if not result["clicked"]:
                print(f"    warning: select_experiment: option not found. Available: {result['found']}")
                return
            await self._wait_ready(timeout=self.config.llm_wait_ms)
            self._driver_injected = False
            await self._inject_driver_js()
        except Exception as e:
            print(f"    warning: select_experiment: {e}")

    async def _action_select_second_treatment(self):
        """
        Streamlit-specific: select the first non-baseline treatment.
        Streamlit radio labels: nth(0) = group header, nth(1) = baseline (Control),
        nth(2+) = non-baseline treatments. Click nth(2) to select the first non-baseline.
        """
        try:
            labels = self.page.locator("[data-testid='stRadio'] label")
            count = await labels.count()
            if count >= 3:
                target = labels.nth(2)
                await target.scroll_into_view_if_needed()
                await target.click()
                try:
                    await self.page.wait_for_function(
                        "() => document.querySelectorAll('details summary').length >= 5",
                        timeout=self.config.llm_wait_ms,
                    )
                    await asyncio.sleep(8)
                except Exception:
                    await asyncio.sleep(15)
                self._driver_injected = False
                await self._inject_driver_js()
            elif count == 2:
                print("    (only one treatment option; skipping switch)")
        except Exception as e:
            print(f"    warning: select_second_treatment: {e}")

    async def _action_expand_section(self, keyword: str):
        """Streamlit-specific: open a <details> expander whose summary contains keyword."""
        try:
            summaries = self.page.locator("details summary")
            count = await summaries.count()
            for i in range(count):
                text = await summaries.nth(i).inner_text()
                if keyword.lower() in text.lower():
                    await summaries.nth(i).scroll_into_view_if_needed()
                    await asyncio.sleep(0.3)
                    details = summaries.nth(i).locator("..")
                    if await details.get_attribute("open") is None:
                        await summaries.nth(i).click()
                        await asyncio.sleep(0.6)
                    await self.page.evaluate(
                        "window.scrollBy({top: 200, behavior: 'smooth'})"
                    )
                    await asyncio.sleep(0.5)
                    break
        except Exception as e:
            print(f"    warning: expand_section('{keyword}'): {e}")
