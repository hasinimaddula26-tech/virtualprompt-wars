"""Local anonymized analytics service."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .timeline import deadlines_within_24_months
from .utils import iso_now


def track(state: dict[str, Any], name: str, detail: dict[str, Any] | None = None) -> None:
    event = {
        "name": name,
        "detail": detail or {},
        "at": iso_now(),
        "anonymous": True,
    }
    state.setdefault("analytics", {}).setdefault("events", []).insert(0, event)
    state["analytics"]["events"] = state["analytics"]["events"][:250]


def completion_stats(state: dict[str, Any], jurisdiction: dict[str, Any]) -> dict[str, int]:
    steps = jurisdiction["process_steps"]
    complete = sum(1 for step in steps if state.get("completed_steps", {}).get(step["id"]))
    total = len(steps)
    percent = round((complete / total) * 100) if total else 0
    return {"complete": complete, "total": total, "percent": percent}


def usage_summary(state: dict[str, Any], jurisdiction: dict[str, Any]) -> dict[str, Any]:
    events = state.get("analytics", {}).get("events", [])
    by_name = Counter(event["name"] for event in events)
    stats = completion_stats(state, jurisdiction)
    deadlines = deadlines_within_24_months(jurisdiction)
    drop_off = "No drop-off detected"
    for step in jurisdiction["process_steps"]:
        if not state.get("completed_steps", {}).get(step["id"]):
            drop_off = f"Next unfinished step: {step['title']}"
            break
    return {
        "event_count": len(events),
        "by_name": dict(by_name),
        "completion_rate": stats["percent"],
        "deadline_adherence_rate": min(100, round((stats["complete"] / max(1, len(deadlines))) * 100)),
        "satisfaction": state.get("analytics", {}).get("satisfaction", 4),
        "drop_off": drop_off,
    }
