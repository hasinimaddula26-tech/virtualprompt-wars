"""Official integration layer with Google Civic API support and mock fallback."""

from __future__ import annotations

import json
import os
from time import perf_counter, sleep
from typing import Any, Callable
from urllib.parse import urlencode, quote_plus
from urllib.request import urlopen

from .seed_data import INTEGRATION_SCHEMAS
from .utils import iso_now


class IntegrationError(RuntimeError):
    pass


GOOGLE_CIVIC_BASE_URL = "https://www.googleapis.com/civicinfo/v2"


def validate(endpoint: str, payload: dict[str, Any]) -> list[str]:
    required = INTEGRATION_SCHEMAS.get(endpoint, [])
    return [field for field in required if payload.get(field) in (None, "")]


def log_call(state: dict[str, Any], endpoint: str, status: str, response_ms: int, message: str = "") -> None:
    state.setdefault("integration_logs", []).insert(
        0,
        {
            "endpoint": endpoint,
            "status": status,
            "response_ms": response_ms,
            "message": message,
            "at": iso_now(),
        },
    )
    state["integration_logs"] = state["integration_logs"][:50]


def retry_with_backoff(task: Callable[[int], Any], attempts: int = 3, base_delay: float = 0.05) -> Any:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return task(attempt)
        except Exception as error:  # noqa: BLE001 - this intentionally wraps adapter failures.
            last_error = error
            sleep(base_delay * (2**attempt))
    raise IntegrationError(str(last_error or "adapter failed"))


def google_civic_configured() -> bool:
    return bool(os.getenv("GOOGLE_CIVIC_API_KEY"))


def google_maps_embed_configured() -> bool:
    return bool(os.getenv("GOOGLE_MAPS_EMBED_KEY"))


def google_maps_directions_url(address: str) -> str:
    return f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(address)}"


def google_maps_embed_url(address: str) -> str:
    key = os.getenv("GOOGLE_MAPS_EMBED_KEY", "")
    return f"https://www.google.com/maps/embed/v1/place?{urlencode({'key': key, 'q': address})}" if key else ""


def google_voter_info(address: str, election_id: str = "") -> dict[str, Any]:
    key = os.getenv("GOOGLE_CIVIC_API_KEY", "")
    if not key:
        raise IntegrationError("GOOGLE_CIVIC_API_KEY is not configured.")
    params = {"address": address, "key": key, "officialOnly": "true"}
    if election_id:
        params["electionId"] = election_id
    url = f"{GOOGLE_CIVIC_BASE_URL}/voterinfo?{urlencode(params)}"
    with urlopen(url, timeout=5) as response:  # nosec B310 - configured official Google HTTPS endpoint.
        return json.loads(response.read().decode("utf-8"))


def _address_text(address: dict[str, Any]) -> str:
    parts = [
        address.get("line1", ""),
        address.get("line2", ""),
        address.get("city", ""),
        address.get("state", ""),
        address.get("zip", ""),
    ]
    return ", ".join(part for part in parts if part)


def google_polling_location(address: str) -> dict[str, Any]:
    info = google_voter_info(address)
    locations = info.get("pollingLocations") or info.get("earlyVoteSites") or info.get("dropOffLocations") or []
    if not locations:
        raise IntegrationError("Google Civic API returned no polling locations for this address.")
    location = locations[0]
    location_address = location.get("address", {})
    full_address = _address_text(location_address)
    return {
        "name": location.get("name") or location_address.get("locationName") or "Polling location",
        "address": full_address,
        "hours": location.get("pollingHours") or "See official source",
        "wait_minutes": "N/A",
        "parking": "See Google Civic location notes and local election authority guidance.",
        "transit": "Use Google Maps directions for transit options.",
        "directions_url": google_maps_directions_url(full_address),
        "accessibility": [location.get("notes") or "Accessibility details may be listed by the local election authority."],
        "languages": ["See official source"],
        "source": "Google Civic Information API",
    }


def google_ballot_information(address: str) -> dict[str, Any]:
    info = google_voter_info(address)
    contests = info.get("contests", [])
    candidates = []
    measures = []
    for contest in contests:
        if contest.get("referendumTitle"):
            measures.append(
                {
                    "id": contest.get("id", contest.get("referendumTitle", "measure")),
                    "title": contest.get("referendumTitle", "Referendum"),
                    "summary": contest.get("referendumSubtitle") or contest.get("office", "Referendum details"),
                    "fiscal_impact": "See official source.",
                    "arguments_for": contest.get("referendumProStatement", "See official source."),
                    "arguments_against": contest.get("referendumConStatement", "See official source."),
                    "source": "Google Civic Information API",
                }
            )
        for candidate in contest.get("candidates", []):
            candidates.append(
                {
                    "id": candidate.get("name", "").lower().replace(" ", "-") or "candidate",
                    "race": contest.get("office", "Contest"),
                    "name": candidate.get("name", "Candidate"),
                    "party": candidate.get("party", "Not listed"),
                    "website": candidate.get("candidateUrl") or "https://developers.google.com/civic-information",
                    "statement": "Candidate information returned by Google Civic API.",
                    "issues": {},
                    "source": "Google Civic Information API",
                }
            )
    if not candidates and not measures:
        raise IntegrationError("Google Civic API returned no contest data for this address.")
    return {
        "district": info.get("normalizedInput", {}).get("line1", "Google Civic district"),
        "sample_ballot_url": "https://developers.google.com/civic-information",
        "candidates": candidates,
        "measures": measures or [
            {
                "id": "no-measures-listed",
                "title": "No measures listed by Google Civic API",
                "summary": "Check the official local election authority.",
                "fiscal_impact": "Not listed.",
                "arguments_for": "Not listed.",
                "arguments_against": "Not listed.",
                "source": "Google Civic Information API",
            }
        ],
    }


def call_adapter(
    state: dict[str, Any],
    jurisdictions: dict[str, Any],
    endpoint: str,
    payload: dict[str, Any],
) -> Any:
    started = perf_counter()
    missing = validate(endpoint, payload)
    if missing:
        response_ms = round((perf_counter() - started) * 1000)
        log_call(state, endpoint, "schema-error", response_ms, f"Missing {', '.join(missing)}")
        raise IntegrationError(f"Missing required fields: {', '.join(missing)}")

    def task(_: int) -> Any:
        jurisdiction = jurisdictions[payload["jurisdiction"]]
        use_google_civic = jurisdiction.get("country") == "US" and google_civic_configured()
        if use_google_civic and endpoint == "polling_location":
            return google_polling_location(payload["address"])
        if use_google_civic and endpoint == "ballot_information":
            return google_ballot_information(payload.get("address") or jurisdiction["polling"]["assigned"]["address"])
        if endpoint == "registration_status":
            return {
                "status": "Registered" if payload.get("registered") else "No active registration found in mock adapter",
                "official_url": jurisdiction["official"]["status_url"],
                "source": "official jurisdiction link",
            }
        if endpoint == "polling_location":
            result = dict(jurisdiction["polling"]["assigned"])
            if result.get("status", "confirmed") == "confirmed":
                result["directions_url"] = google_maps_directions_url(result["address"])
            else:
                result["lookup_address"] = payload.get("address", "")
                result["lookup_instructions"] = (
                    f"{result.get('lookup_instructions', 'Check the official election authority.')}"
                    f" Registered or home address used for lookup: {payload.get('address', 'not provided')}."
                )
                result["directions_url"] = jurisdiction["official"]["elections_url"]
            result["source"] = "country adapter fallback data"
            return result
        if endpoint == "ballot_information":
            result = dict(jurisdiction["ballot"])
            if payload.get("address"):
                result["lookup_address"] = payload["address"]
            result["source"] = "country adapter fallback data"
            return result
        raise IntegrationError(f"Unknown endpoint: {endpoint}")

    result = retry_with_backoff(task)
    response_ms = round((perf_counter() - started) * 1000)
    source = result.get("source", "mock fallback data") if isinstance(result, dict) else "unknown"
    log_call(state, endpoint, "ok", response_ms, f"Adapter response source: {source}")
    return result
