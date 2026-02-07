# cognix.hud_components
from __future__ import annotations
from typing import Optional, Iterable
from cognix.theme_zen import CHECK, RUN, DOT, WARN, color, FG, ACCENT

def step_line(label: str, state: str, elapsed: Optional[str] = None) -> str:
    icon = { "done": CHECK, "running": RUN, "pending": DOT }.get(state, DOT)
    base = f"{icon} {label}"
    if elapsed:
        base = f"{base}  ({elapsed})"
    if state == "done":
        return color(base, ACCENT)
    return base

def lint_summary_line(ok: int, warn: int, fail: int) -> str:
    seg = f"OK {ok} / WARN {warn} / FAIL {fail}"
    return f"{WARN} Lint Summary   {seg}"

def diff_estimate_line(added: int, removed: int) -> str:
    return f"   Diff Estimate  +{added} / -{removed}"

def secrets_line(found: bool) -> str:
    return "   Secrets        found" if found else "   Secrets        none"

def recommendations_compact(items: Iterable[str], max_items: int = 3) -> str:
    """
    Compact recommendations to 1 line (max 3 items)
    
    Return value does not include "Recommendations:" (added by caller)
    """
    items = [x for i, x in enumerate(items) if i < max_items]
    if not items:
        return ""
    return " · ".join(items)

def next_menu_lines() -> str:
    return ("Next:\n"
            "  [1] Apply changes\n"
            "  [2] Reject\n"
            "  [3] Review details (preview / diff / lints)")