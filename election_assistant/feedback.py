"""Feedback, incident reporting, and pain-point analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .seed_data import INCIDENT_TYPES
from .utils import iso_now


def submit_feedback(state: dict[str, Any], page: str, category: str, message: str, contact: str = "") -> dict[str, Any]:
    entry = {
        "page": page or "General",
        "category": category or "usability",
        "message": message,
        "contact": contact,
        "at": iso_now(),
        "flagged_for_review": category == "content-error" or any(
            word in message.lower() for word in ["wrong", "error", "broken", "unsafe"]
        ),
    }
    state.setdefault("feedback", []).insert(0, entry)
    return entry


def incident_type(type_id: str) -> dict[str, Any]:
    return next((item for item in INCIDENT_TYPES if item["id"] == type_id), INCIDENT_TYPES[0])


def submit_incident(state: dict[str, Any], type_id: str, location: str, details: str) -> dict[str, Any]:
    kind = incident_type(type_id)
    entry = {
        "type": type_id,
        "label": kind["label"],
        "location": location,
        "details": details,
        "guidance": kind["guidance"],
        "critical": bool(kind.get("critical")),
        "escalate_within_minutes": 15 if kind.get("critical") else None,
        "at": iso_now(),
    }
    state.setdefault("incidents", []).insert(0, entry)
    submit_feedback(state, "Election day support", "process-pain-point", f"{kind['label']}: {details}")
    return entry


def analyze_feedback(state: dict[str, Any]) -> dict[str, Any]:
    feedback = state.get("feedback", [])
    category_counts = Counter(item.get("category", "uncategorized") for item in feedback)
    flagged = sum(1 for item in feedback if item.get("flagged_for_review"))
    locations: dict[str, int] = defaultdict(int)
    for incident in state.get("incidents", []):
        locations[incident.get("location", "Unknown")] += 1
    patterns = [
        {"location": location, "count": count}
        for location, count in sorted(locations.items(), key=lambda item: item[1], reverse=True)
        if count >= 2
    ]
    return {
        "total": len(feedback),
        "category_counts": dict(category_counts),
        "flagged": flagged,
        "incident_count": len(state.get("incidents", [])),
        "patterns": patterns,
    }
