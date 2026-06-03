from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DemoStep:
    id: str
    script: str
    action: str
    action_args: dict = field(default_factory=dict)
    # Driver.js spotlight config.
    # driver_selector: CSS selector OR "expander:Keyword" to find a <details> by summary text.
    driver_selector: Optional[str] = None
    driver_popover: Optional[dict] = None  # keys: title, description, side, align
    pause_after: float = 1.5


# Project-specific DEMO_STEPS belong in your demo_plan.yaml, not here.
# Use the template at templates/demo_plan.yaml as a starting point.
