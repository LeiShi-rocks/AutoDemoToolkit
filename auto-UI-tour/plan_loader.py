"""
Load a demo_plan.yaml file and return (Config, List[DemoStep]).

The YAML format is the human-editable source of truth for the demo.
See templates/demo_plan.yaml for a fully commented example.
"""

from pathlib import Path
from typing import List, Tuple

import yaml

from config import Config
from steps import DemoStep


def load_plan(plan_path: Path) -> Tuple[Config, List[DemoStep]]:
    data = yaml.safe_load(plan_path.read_text())

    # ── Config ────────────────────────────────────────────────────────────
    cfg_raw = data.get("config", {})
    res = cfg_raw.get("resolution", [1280, 800])
    config = Config(
        video_width=res[0],
        video_height=res[1],
    )
    if "app_port" in cfg_raw:
        config.app_port = int(cfg_raw["app_port"])
    if "voice" in cfg_raw:
        config.tts_voice = cfg_raw["voice"]
    if "llm_wait_ms" in cfg_raw:
        config.llm_wait_ms = int(cfg_raw["llm_wait_ms"])
    if "start_command" in cfg_raw:
        config.start_command = cfg_raw["start_command"] or None
    if "app_env" in cfg_raw and cfg_raw["app_env"]:
        config.app_env = {str(k): str(v) for k, v in cfg_raw["app_env"].items()}

    # app_url override: if the plan provides an explicit app_url that doesn't
    # match the port-derived default, honour the port portion of it.
    if "app_url" in cfg_raw:
        import urllib.parse
        parsed = urllib.parse.urlparse(cfg_raw["app_url"])
        if parsed.port:
            config.app_port = parsed.port

    # ── Segments → DemoStep list ──────────────────────────────────────────
    steps: List[DemoStep] = []
    for seg in data.get("segments", []):
        hl = seg.get("highlight", {}) or {}
        popover = hl.get("popover") or None

        steps.append(
            DemoStep(
                id=seg["id"],
                script=seg["narration"].strip(),
                action=seg["action"],
                action_args=seg.get("action_args") or {},
                driver_selector=hl.get("selector") or None,
                driver_popover=popover,
                pause_after=float(seg.get("pause_after", 1.5)),
            )
        )

    return config, steps


def plan_mode(plan_path: Path) -> str:
    """Return 'screenshot' or 'live' from the plan config."""
    data = yaml.safe_load(plan_path.read_text())
    return data.get("config", {}).get("mode", "screenshot")
