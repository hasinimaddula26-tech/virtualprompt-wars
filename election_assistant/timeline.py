"""Deadline and calendar generation service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .utils import parse_dt, utc_now


def deadlines_within_24_months(jurisdiction: dict[str, Any]) -> list[dict[str, Any]]:
    limit = utc_now() + timedelta(days=730)
    deadlines = [item for item in jurisdiction["deadlines"] if parse_dt(item["date"]).astimezone(timezone.utc) <= limit]
    return sorted(deadlines, key=lambda item: parse_dt(item["date"]))


def days_until(date_value: str) -> int:
    target = parse_dt(date_value).astimezone(timezone.utc)
    delta = target - utc_now()
    return int(delta.total_seconds() // 86400) + (1 if delta.total_seconds() % 86400 > 0 else 0)


def is_critical(deadline: dict[str, Any]) -> bool:
    remaining = days_until(deadline["date"])
    return bool(deadline.get("critical")) or (0 <= remaining <= 14)


def next_deadline(jurisdiction: dict[str, Any]) -> dict[str, Any] | None:
    for deadline in deadlines_within_24_months(jurisdiction):
        if days_until(deadline["date"]) >= 0:
            return deadline
    return None


def ics_datetime(date_value: str | datetime) -> str:
    value = parse_dt(date_value) if isinstance(date_value, str) else date_value
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def calendar_event(deadline: dict[str, Any]) -> str:
    start = parse_dt(deadline["date"])
    end = start + timedelta(hours=1)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Election Process Assistant Python//EN",
        "BEGIN:VEVENT",
        f"UID:{deadline['id']}@election-process-assistant.local",
        f"DTSTAMP:{ics_datetime(utc_now())}",
        f"DTSTART:{ics_datetime(start)}",
        f"DTEND:{ics_datetime(end)}",
        f"SUMMARY:{deadline['title']}",
        f"DESCRIPTION:{deadline['description']}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines)
