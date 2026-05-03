"""Education, civic engagement, innovation, and organizer service."""

from __future__ import annotations

from typing import Any

from .seed_data import EDUCATION_MODULES, INNOVATIONS, ORGANIZER_TOOLKIT, PROCESS_IMPROVEMENTS
from .utils import iso_now


def mark_module_complete(state: dict[str, Any], module_id: str) -> None:
    state.setdefault("education_completed", {})[module_id] = iso_now()


def organizer_stats(state: dict[str, Any]) -> dict[str, Any]:
    batches = state.get("registration_batches", [])
    total = sum(int(batch.get("count", 0)) for batch in batches)
    return {"batches": len(batches), "registrations": total}


def add_registration_batch(state: dict[str, Any], label: str, count: int, jurisdiction_id: str) -> None:
    state.setdefault("registration_batches", []).insert(
        0,
        {
            "label": label,
            "count": max(1, int(count)),
            "jurisdiction": jurisdiction_id,
            "at": iso_now(),
        },
    )


def learning_model(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "modules": EDUCATION_MODULES,
        "innovations": INNOVATIONS,
        "process_improvements": PROCESS_IMPROVEMENTS,
        "organizer_toolkit": ORGANIZER_TOOLKIT,
        "completed": state.get("education_completed", {}),
        "organizer_stats": organizer_stats(state),
    }
