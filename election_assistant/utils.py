"""Shared utility helpers."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STORAGE_DIR = ROOT / "storage"
STATIC_DIR = ROOT / "static"


def html(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def deep_copy(value: Any) -> Any:
    return deepcopy(value)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds")


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return deep_copy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deep_copy(default)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def bool_from_form(value: str | None) -> bool:
    return value in {"on", "true", "1", "yes", "y"}


def clean_text(value: Any, max_length: int = 500, allow_newlines: bool = False) -> str:
    text = str(value if value is not None else "")
    cleaned = []
    for char in text:
        if char in "\r\n\t":
            if allow_newlines:
                cleaned.append("\n" if char in "\r\n" else "\t")
            else:
                cleaned.append(" ")
        elif ord(char) >= 32:
            cleaned.append(char)
    return "".join(cleaned).strip()[:max_length]


def clean_choice(value: Any, allowed: set[str], default: str) -> str:
    candidate = clean_text(value, 80)
    return candidate if candidate in allowed else default


def list_html(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{html(item)}</li>" for item in items) + "</ul>"


def tag_html(items: list[str], css_class: str = "") -> str:
    return (
        '<div class="tag-row">'
        + "".join(f'<span class="tag {html(css_class)}">{html(item)}</span>' for item in items)
        + "</div>"
    )


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def first_present(mapping: dict[str, Any], key: str, default: Any = "") -> Any:
    value = mapping.get(key, default)
    return value if value not in (None, "") else default
