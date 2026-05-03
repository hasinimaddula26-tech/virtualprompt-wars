"""Polling location service."""

from __future__ import annotations

from typing import Any


def assigned_location(jurisdiction: dict[str, Any]) -> dict[str, Any]:
    return jurisdiction["polling"]["assigned"]


def alternatives_within_10_miles(jurisdiction: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        location
        for location in jurisdiction["polling"]["alternatives"]
        if float(location.get("distance_miles", 999)) <= 10
    ]
