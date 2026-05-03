"""SQLite-backed per-session state management."""

from __future__ import annotations

from copy import deepcopy
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any

from .security import new_csrf_token
from .utils import STORAGE_DIR, iso_now


STATE_DB_PATH = STORAGE_DIR / "app_state.sqlite3"
DEFAULT_SESSION_ID = "local-dev"

DEFAULT_STATE: dict[str, Any] = {
    "country_code": "US",
    "jurisdiction_id": "california",
    "language": "en",
    "text_scale": 100,
    "screen_reader": False,
    "profile": {
        "country_code": "US",
        "address": "100 Civic Harbor Way",
        "birth_year": 1992,
        "citizen": True,
        "resident": True,
        "registered": False,
        "user_type": "anonymous",
    },
    "completed_steps": {},
    "selected_method_id": "",
    "research_notes": {},
    "manual_candidates": {},
    "jurisdiction_overrides": {},
    "notification_preferences": {
        "enabled": False,
        "channels": ["email"],
        "intervals": [30, 7, 1],
        "categories": ["deadlines", "ballot", "system"],
    },
    "feedback": [],
    "incidents": [],
    "analytics": {
        "events": [],
        "satisfaction": 4,
    },
    "education_completed": {},
    "registration_batches": [],
    "offline_queue": [],
    "integration_logs": [],
    "login_attempts": [],
    "session": {
        "authenticated": False,
        "expires_at": "",
    },
    "flash": [],
    "vault": {},
    "onboarded": False,
    "locale_country_suggested": False,
    "csrf_token": "",
    "generated_guide_at": "",
    "created_at": "",
    "updated_at": "",
}


def merge_defaults(default: Any, loaded: Any) -> Any:
    if isinstance(default, dict):
        result = deepcopy(default)
        if isinstance(loaded, dict):
            for key, value in loaded.items():
                result[key] = merge_defaults(default.get(key), value) if key in default else value
        return result
    if isinstance(default, list):
        return loaded if isinstance(loaded, list) else deepcopy(default)
    return loaded if loaded is not None else deepcopy(default)


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


class StateStore:
    def __init__(self, path: Path = STATE_DB_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at)"
            )
            connection.commit()

    def normalize_session_id(self, session_id: str | None) -> str:
        return session_id or DEFAULT_SESSION_ID

    def load(self, session_id: str | None = None) -> dict[str, Any]:
        session_id = self.normalize_session_id(session_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        loaded = json.loads(row["state_json"]) if row else {}
        state = merge_defaults(DEFAULT_STATE, loaded)
        state["_session_id"] = session_id
        if not state["created_at"]:
            state["created_at"] = iso_now()
        if not state.get("csrf_token"):
            state["csrf_token"] = new_csrf_token()
        if row is None:
            self.save(state, session_id)
        return state

    def save(self, state: dict[str, Any], session_id: str | None = None) -> None:
        session_id = self.normalize_session_id(session_id or state.get("_session_id"))
        state["_session_id"] = session_id
        state["updated_at"] = iso_now()
        payload = {key: value for key, value in state.items() if key != "_session_id"}
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO sessions (session_id, state_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    json.dumps(payload, indent=2, sort_keys=True),
                    state["created_at"],
                    state["updated_at"],
                ),
            )
            connection.commit()

    def delete(self, session_id: str | None = None) -> None:
        session_id = self.normalize_session_id(session_id)
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            connection.commit()

    def flash(self, state: dict[str, Any], message: str) -> None:
        state.setdefault("flash", []).append(message)
        self.save(state)

    def pop_flash(self, state: dict[str, Any]) -> list[str]:
        messages = list(state.get("flash", []))
        state["flash"] = []
        self.save(state)
        return messages
