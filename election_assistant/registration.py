"""Registration and eligibility service."""

from __future__ import annotations

from datetime import date
from typing import Any


def eligibility(profile: dict[str, Any], jurisdiction: dict[str, Any]) -> dict[str, Any]:
    rules = jurisdiction["eligibility"]
    try:
        age = date.today().year - int(profile.get("birth_year", 0))
    except (TypeError, ValueError):
        age = -1
    issues: list[str] = []
    if age < rules["min_age"]:
        issues.append(f"Age is below {rules['min_age']}.")
    if rules.get("citizenship_required") and not profile.get("citizen"):
        issues.append("Citizenship requirement is not confirmed.")
    if not profile.get("resident"):
        issues.append(f"Residency in {jurisdiction['name']} is not confirmed.")
    return {
        "age": age if age >= 0 else "Unknown",
        "eligible": not issues,
        "issues": issues,
        "rule": rules["residency_rule"],
    }


def registration_status(profile: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    if profile.get("registered"):
        return "Registered by user confirmation"
    return jurisdiction["registration"]["status"]


def resolution_steps(jurisdiction: dict[str, Any]) -> list[str]:
    return [
        "Use exact legal name when checking registration.",
        "Update address after moving.",
        "Ask election officials about provisional ballot options.",
        "Use manual verification when official lookup data is unavailable.",
        jurisdiction["contacts"]["rights_restoration"],
        jurisdiction["contacts"]["official"],
        jurisdiction["contacts"]["hotline"],
    ]
