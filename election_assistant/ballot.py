"""Ballot and candidate research service."""

from __future__ import annotations

from typing import Any


def all_issue_keys(ballot: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for candidate in ballot["candidates"]:
        for issue in candidate.get("issues", {}):
            if issue not in keys:
                keys.append(issue)
    return keys


def comparison_rows(ballot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for issue in all_issue_keys(ballot):
        rows.append(
            {
                "issue": issue,
                "positions": [
                    {
                        "candidate": candidate["name"],
                        "position": candidate.get("issues", {}).get(issue, "No sample statement listed."),
                    }
                    for candidate in ballot["candidates"]
                ],
            }
        )
    return rows
