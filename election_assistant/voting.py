"""Voting method service."""

from __future__ import annotations

from typing import Any


def selected_method(state: dict[str, Any], jurisdiction: dict[str, Any]) -> dict[str, Any]:
    methods = jurisdiction["voting_methods"]
    selected_id = state.get("selected_method_id")
    return next((method for method in methods if method["id"] == selected_id), methods[0])


def method_summary(jurisdiction: dict[str, Any]) -> list[dict[str, Any]]:
    return list(jurisdiction["voting_methods"])
