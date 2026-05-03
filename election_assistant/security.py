"""Security, privacy, password policy, rate limiting, and vault integration.

The production review explicitly called out custom cryptography as a critical
risk. This module therefore does not implement encryption primitives itself.
When the optional `cryptography` package is installed, private vault data is
sealed with Fernet using a PBKDF2-HMAC-derived key. Without that dependency the
vault feature is disabled with an explicit error instead of falling back to
home-grown crypto.
"""

from __future__ import annotations

import base64
from datetime import timedelta
import json
import secrets
from typing import Any

try:  # Optional production dependency, declared in requirements.txt.
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:  # pragma: no cover - exercised indirectly in this workspace.
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment]
    PBKDF2HMAC = None  # type: ignore[assignment]
    hashes = None  # type: ignore[assignment]

from .utils import iso_now, parse_dt, utc_now

SESSION_MINUTES = 30
FAILED_LOGIN_WINDOW_MINUTES = 15
MAX_FAILED_ATTEMPTS = 5
VAULT_ITERATIONS = 390_000


def cryptography_available() -> bool:
    return Fernet is not None and PBKDF2HMAC is not None and hashes is not None


def password_is_valid(password: str) -> bool:
    return (
        len(password) >= 12
        and any(char.islower() for char in password)
        and any(char.isupper() for char in password)
        and any(char.isdigit() for char in password)
        and any(not char.isalnum() for char in password)
    )


def login_blocked(state: dict[str, Any]) -> bool:
    cutoff = utc_now() - timedelta(minutes=FAILED_LOGIN_WINDOW_MINUTES)
    attempts = [value for value in state.get("login_attempts", []) if parse_dt(value) >= cutoff]
    state["login_attempts"] = attempts
    return len(attempts) >= MAX_FAILED_ATTEMPTS


def record_failed_login(state: dict[str, Any]) -> None:
    state.setdefault("login_attempts", []).append(iso_now())


def authenticate_session(state: dict[str, Any]) -> None:
    state["session"] = {
        "authenticated": True,
        "expires_at": (utc_now() + timedelta(minutes=SESSION_MINUTES)).isoformat(timespec="seconds"),
    }
    state["profile"]["user_type"] = "registered"
    state["login_attempts"] = []


def enforce_session_timeout(state: dict[str, Any]) -> bool:
    session = state.get("session", {})
    if not session.get("authenticated"):
        return False
    expires = session.get("expires_at")
    if expires and parse_dt(expires) < utc_now():
        state["session"] = {"authenticated": False, "expires_at": ""}
        state["profile"]["user_type"] = "anonymous"
        return True
    return False


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_is_valid(state: dict[str, Any], token: str) -> bool:
    expected = state.get("csrf_token", "")
    return bool(expected and token and secrets.compare_digest(expected, token))


def _derive_fernet_key(passphrase: str, salt: bytes, iterations: int) -> bytes:
    if not cryptography_available():
        raise RuntimeError(
            "Private vault encryption requires the optional 'cryptography' package. "
            "Install project requirements before enabling this production feature."
        )
    kdf = PBKDF2HMAC(  # type: ignore[operator]
        algorithm=hashes.SHA256(),  # type: ignore[union-attr]
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def seal_vault(state: dict[str, Any], passphrase: str) -> dict[str, Any]:
    if len(passphrase) < 12:
        raise ValueError("Vault passphrase must be at least 12 characters.")
    salt = secrets.token_bytes(16)
    key = _derive_fernet_key(passphrase, salt, VAULT_ITERATIONS)
    private_data = {
        "address": state.get("profile", {}).get("address", ""),
        "research_notes": state.get("research_notes", {}),
        "feedback_contacts": [
            {"page": item.get("page"), "contact": item.get("contact"), "at": item.get("at")}
            for item in state.get("feedback", [])
            if item.get("contact")
        ],
    }
    token = Fernet(key).encrypt(json.dumps(private_data, sort_keys=True).encode("utf-8"))  # type: ignore[operator]
    vault = {
        "algorithm": "Fernet-AES128-CBC-HMAC-SHA256",
        "library": "cryptography",
        "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": VAULT_ITERATIONS,
        "salt": base64.b64encode(salt).decode("ascii"),
        "token": token.decode("ascii"),
        "sealed_at": iso_now(),
    }
    state["vault"] = vault
    return vault


def open_vault(state: dict[str, Any], passphrase: str) -> dict[str, Any]:
    vault = state.get("vault") or {}
    if not vault:
        raise ValueError("No local vault is stored.")
    try:
        salt = base64.b64decode(vault["salt"])
        key = _derive_fernet_key(passphrase, salt, int(vault["iterations"]))
        plaintext = Fernet(key).decrypt(vault["token"].encode("ascii"))  # type: ignore[operator]
    except InvalidToken as error:
        raise ValueError("Vault authentication failed.") from error
    private_data = json.loads(plaintext.decode("utf-8"))
    state.setdefault("profile", {})["address"] = private_data.get("address", state.get("profile", {}).get("address", ""))
    state["research_notes"] = private_data.get("research_notes", {})
    return private_data
