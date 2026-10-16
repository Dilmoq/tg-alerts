"""State tracking for alert firing/recovery transitions."""

from __future__ import annotations

import json
import pathlib


def load_state(state_path: pathlib.Path) -> set[str]:
    """Read previously firing alert keys."""
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return set()
    return {str(x) for x in data.get("firing", [])}


def save_state(state_path: pathlib.Path, firing: set[str]) -> None:
    """Persist the current firing set (mkdir'd, atomic-ish)."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"firing": sorted(firing)}), encoding="utf-8")
    tmp.replace(state_path)


def transitions(prev: set[str], now: set[str]) -> tuple[set[str], set[str]]:
    """Return (just_fired, just_recovered) comparing current vs previous."""
    return now - prev, prev - now
