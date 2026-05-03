"""WSGI routes for the Python Election Process Assistant."""

from __future__ import annotations

from copy import deepcopy
from http import HTTPStatus
from http.cookies import SimpleCookie
from io import BytesIO
import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from . import APP_NAME
from .analytics import track
from .documents import guide_html, guide_text, organizer_toolkit_text
from .education import add_registration_batch, mark_module_complete
from .feedback import submit_feedback, submit_incident
from .data_sources import COUNTRIES, default_region, list_regions
from .integrations import IntegrationError, call_adapter
from .registration import registration_status
from .render import current_jurisdiction, render_app
from .security import (
    authenticate_session,
    csrf_is_valid,
    enforce_session_timeout,
    login_blocked,
    open_vault,
    password_is_valid,
    record_failed_login,
    seal_vault,
)
from .seed_data import LANGUAGES, ORGANIZER_TOOLKIT
from .state import DEFAULT_STATE, StateStore, new_session_id
from .timeline import calendar_event, deadlines_within_24_months
from .utils import STATIC_DIR, bool_from_form, clamp_int, clean_choice, clean_text, html, iso_now


MIME_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".svg": "image/svg+xml; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".ics": "text/calendar; charset=utf-8",
}

SESSION_COOKIE = "epa_session"

LOCALE_COUNTRY_HINTS = {
    "AU": "GLOBAL",
    "CA": "CA",
    "DE": "EU",
    "ES": "EU",
    "FR": "EU",
    "GB": "GB",
    "IE": "EU",
    "IN": "IN",
    "IT": "EU",
    "NL": "EU",
    "UK": "GB",
    "US": "US",
}


SECURITY_HEADERS = [
    ("Referrer-Policy", "no-referrer"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Permissions-Policy", "geolocation=(), microphone=(), camera=()"),
    (
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' https://www.googleapis.com; "
        "frame-src https://www.google.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'",
    ),
]


class Response:
    def __init__(
        self,
        body: str | bytes = b"",
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "text/html; charset=utf-8",
        headers: list[tuple[str, str]] | None = None,
    ) -> None:
        self.raw = body.encode("utf-8") if isinstance(body, str) else body
        self.status = status
        self.headers = headers or []
        self.headers.extend(
            [
                ("Content-Type", content_type),
                ("Content-Length", str(len(self.raw))),
                ("Cache-Control", "no-store"),
                *SECURITY_HEADERS,
            ]
        )


class ElectionApp:
    def __init__(self, store: StateStore | None = None) -> None:
        self.store = store or StateStore()

    def __call__(self, environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        request = Request(environ)
        session_id, set_cookie = self.resolve_session(request)
        try:
            response = self.dispatch(request, session_id)
        except Exception as error:  # noqa: BLE001 - the app should return a safe response.
            state = self.store.load(session_id)
            self.store.flash(state, f"Unexpected server error: {html(error)}")
            response = self.redirect("/")
        if set_cookie:
            response.headers.append(("Set-Cookie", self.session_cookie(session_id)))
        start_response(f"{response.status.value} {response.status.phrase}", response.headers)
        return [response.raw]

    def resolve_session(self, request: "Request") -> tuple[str, bool]:
        cookie_header = request.environ.get("HTTP_COOKIE", "")
        cookies = SimpleCookie(cookie_header)
        morsel = cookies.get(SESSION_COOKIE)
        if morsel and morsel.value:
            return morsel.value, False
        return new_session_id(), True

    @staticmethod
    def session_cookie(session_id: str) -> str:
        return f"{SESSION_COOKIE}={session_id}; Path=/; HttpOnly; SameSite=Lax"

    @staticmethod
    def redirect(target: str) -> Response:
        return Response(b"", HTTPStatus.SEE_OTHER, headers=[("Location", target)])

    def dispatch(self, request: "Request", session_id: str) -> Response:
        if request.path.startswith("/static/"):
            return self.serve_static(request.path)
        if request.method == "POST":
            return self.handle_post(request, session_id)
        return self.handle_get(request, session_id)

    def load_state(self, session_id: str) -> dict[str, Any]:
        state = self.store.load(session_id)
        if enforce_session_timeout(state):
            self.store.flash(state, "Authenticated session timed out after 30 minutes of inactivity.")
        return state

    def handle_get(self, request: "Request", session_id: str) -> Response:
        state = self.load_state(session_id)
        if not state.get("onboarded") and self.apply_locale_country_suggestion(state, request.environ.get("HTTP_ACCEPT_LANGUAGE", "")):
            self.store.save(state)
        if request.path == "/download/ics":
            return self.download_ics(state, request.query)
        if request.path == "/download/guide.html":
            body = guide_html(state, current_jurisdiction(state))
            self.store.save(state)
            return Response(
                body,
                content_type="text/html; charset=utf-8",
                headers=[("Content-Disposition", 'attachment; filename="personalized-voter-guide.html"')],
            )
        if request.path == "/download/guide.txt":
            body = guide_text(state, current_jurisdiction(state))
            self.store.save(state)
            return Response(
                body,
                content_type="text/plain; charset=utf-8",
                headers=[("Content-Disposition", 'attachment; filename="personalized-voter-guide.txt"')],
            )
        if request.path == "/download/organizer-toolkit.txt":
            body = organizer_toolkit_text(current_jurisdiction(state), ORGANIZER_TOOLKIT)
            return Response(
                body,
                content_type="text/plain; charset=utf-8",
                headers=[("Content-Disposition", 'attachment; filename="registration-drive-toolkit.txt"')],
            )
        if request.path == "/api/status":
            payload = {
                "app": APP_NAME,
                "country": current_jurisdiction(state).get("country_name", ""),
                "jurisdiction": current_jurisdiction(state)["name"],
                "state_saved": bool(state.get("updated_at")),
                "session_isolated": True,
                "storage": "sqlite",
            }
            return Response(json.dumps(payload), content_type="application/json; charset=utf-8")
        if request.path == "/api/health":
            payload = {
                "status": "ok",
                "app": APP_NAME,
                "country_count": len(COUNTRIES),
                "jurisdiction": current_jurisdiction(state)["name"],
                "storage": "sqlite",
            }
            return Response(json.dumps(payload), content_type="application/json; charset=utf-8")
        # Onboarding redirect for new users
        if not state.get("onboarded") and request.path != "/setup":
            return self.redirect("/setup")
        page = request.path.lstrip("/") or "dashboard"
        messages = self.store.pop_flash(state)
        track(state, "page_view", {"path": page})
        self.store.save(state)
        return Response(render_app(state, messages, page))

    def handle_post(self, request: "Request", session_id: str) -> Response:
        state = self.load_state(session_id)
        form = request.form()
        if not csrf_is_valid(state, one(form, "_csrf_token")):
            self.store.flash(state, "Security check failed. Refresh the page and try again.")
            return self.redirect("/")
        try:
            self.handle_action(request.path, form, state)
        except Exception as error:  # noqa: BLE001 - user-visible action errors.
            self.store.flash(state, f"Action could not be completed: {error}")
        # Redirect to dashboard after onboarding
        if request.path == "/action/onboard":
            return self.redirect("/dashboard")
        return self.redirect("/")

    def handle_action(self, path: str, form: dict[str, list[str]], state: dict[str, Any]) -> None:
        if path == "/action/settings":
            self.apply_country_region(form, state)
            state["language"] = clean_choice(
                one(form, "language", state["language"]),
                {item["code"] for item in LANGUAGES},
                state["language"],
            )
            state["text_scale"] = clamp_int(one(form, "text_scale"), 100, 100, 200)
            state["screen_reader"] = bool_from_form(one(form, "screen_reader"))
            track(
                state,
                "settings_saved",
                {"country": state["country_code"], "jurisdiction": state["jurisdiction_id"], "language": state["language"]},
            )
            self.store.flash(state, "Settings saved.")
        elif path == "/action/profile":
            profile = state["profile"]
            profile["address"] = clean_text(one(form, "address", profile["address"]), 220)
            profile["birth_year"] = clamp_int(one(form, "birth_year"), profile["birth_year"], 1900, 2026)
            profile["user_type"] = clean_choice(
                one(form, "user_type", profile["user_type"]),
                {"anonymous", "registered", "organizer", "researcher"},
                "anonymous",
            )
            profile["citizen"] = bool_from_form(one(form, "citizen"))
            profile["resident"] = bool_from_form(one(form, "resident"))
            profile["registered"] = bool_from_form(one(form, "registered"))
            track(state, "profile_saved", {"jurisdiction": state["jurisdiction_id"]})
            self.store.flash(state, "Profile saved.")
        elif path == "/action/step":
            allowed_steps = {step["id"] for step in current_jurisdiction(state)["process_steps"]}
            step_id = clean_choice(one(form, "step_id"), allowed_steps, "")
            if not step_id:
                raise ValueError("Unknown process step.")
            state.setdefault("completed_steps", {})[step_id] = not state.setdefault("completed_steps", {}).get(step_id, False)
            track(state, "step_toggled", {"step": step_id})
            self.store.flash(state, "Process step updated.")
        elif path == "/action/notifications":
            allowed_channels = {"email", "sms", "push"}
            allowed_intervals = {"30", "7", "1"}
            allowed_categories = {"deadlines", "ballot", "system"}
            state["notification_preferences"] = {
                "enabled": bool_from_form(one(form, "enabled")),
                "channels": [item for item in form.get("channels", []) if item in allowed_channels],
                "intervals": [int(value) for value in form.get("intervals", []) if value in allowed_intervals],
                "categories": [item for item in form.get("categories", []) if item in allowed_categories],
            }
            track(state, "notifications_saved", state["notification_preferences"])
            self.store.flash(state, "Notification preferences saved. Delivery is simulated locally.")
        elif path == "/action/method":
            method_ids = {method["id"] for method in current_jurisdiction(state)["voting_methods"]}
            state["selected_method_id"] = clean_choice(one(form, "method_id"), method_ids, "")
            track(state, "voting_method_selected", {"method": state["selected_method_id"]})
            self.store.flash(state, "Voting method selected.")
        elif path == "/action/notes":
            district = clean_text(one(form, "district"), 160)
            state.setdefault("research_notes", {})[district] = clean_text(one(form, "notes"), 4000, allow_newlines=True)
            track(state, "research_notes_saved", {"district": district})
            self.store.flash(state, "Research notes saved.")
        elif path == "/action/add-candidate":
            district = clean_text(one(form, "district"), 160) or current_jurisdiction(state)["ballot"]["district"]
            candidate_name = clean_text(one(form, "name"), 160)
            if not candidate_name:
                raise ValueError("Candidate name is required.")
            statement = clean_text(one(form, "statement"), 1200, allow_newlines=True)
            website = clean_text(one(form, "website"), 300)
            if not website.startswith(("http://", "https://")):
                website = current_jurisdiction(state)["official"]["elections_url"]
            candidates = state.setdefault("manual_candidates", {}).setdefault(district, [])
            candidates.append(
                {
                    "id": f"manual-{len(candidates) + 1}",
                    "race": clean_text(one(form, "race"), 160) or district,
                    "name": candidate_name,
                    "party": clean_text(one(form, "party"), 120) or "Local listing",
                    "website": website,
                    "statement": statement or "Manual research note.",
                    "issues": {"Manual note": statement or "Verify this candidate through an official source."},
                    "source": "Manual local note",
                }
            )
            track(state, "manual_candidate_added", {"district": district})
            self.store.flash(state, "Candidate note added locally.")
        elif path == "/action/feedback":
            entry = submit_feedback(
                state,
                clean_text(one(form, "page"), 120),
                clean_choice(one(form, "category"), {"usability", "content-error", "feature-request", "process-pain-point"}, "usability"),
                clean_text(one(form, "message"), 3000, allow_newlines=True),
                clean_text(one(form, "contact"), 240),
            )
            track(state, "feedback_submitted", {"category": entry["category"], "page": entry["page"]})
            self.store.flash(state, "Feedback submitted. Content errors are flagged for review within 24 hours.")
        elif path == "/action/incident":
            entry = submit_incident(
                state,
                clean_text(one(form, "type"), 80),
                clean_text(one(form, "location"), 180),
                clean_text(one(form, "details"), 3000, allow_newlines=True),
            )
            track(state, "incident_reported", {"type": entry["type"], "critical": entry["critical"]})
            self.store.flash(state, f"{entry['guidance']} {'Critical incident marked for 15-minute escalation.' if entry['critical'] else ''}")
        elif path == "/action/batch":
            add_registration_batch(
                state,
                clean_text(one(form, "label"), 140),
                clamp_int(one(form, "count", "1"), 1, 1, 100000),
                state["jurisdiction_id"],
            )
            track(state, "registration_batch_added", {"count": one(form, "count", "1")})
            self.store.flash(state, "Registration drive batch tracked.")
        elif path == "/action/complete-module":
            mark_module_complete(state, clean_text(one(form, "module_id"), 120))
            track(state, "education_completed", {"module": one(form, "module_id")})
            self.store.flash(state, "Educational module completed.")
        elif path == "/action/password":
            password = one(form, "password")
            if login_blocked(state):
                self.store.flash(state, "Login simulation is rate limited after five failed attempts in 15 minutes.")
            elif password_is_valid(password):
                authenticate_session(state)
                track(state, "password_policy_passed")
                self.store.flash(state, "Password policy passed. Registered account simulation enabled.")
            else:
                record_failed_login(state)
                self.store.flash(state, "Password does not meet policy. Failed attempt recorded.")
        elif path == "/action/seal-vault":
            seal_vault(state, one(form, "passphrase"))
            track(state, "vault_sealed")
            self.store.flash(state, "Private data sealed with cryptography/Fernet.")
        elif path == "/action/open-vault":
            open_vault(state, one(form, "passphrase"))
            track(state, "vault_opened")
            self.store.flash(state, "Private vault opened for this session.")
        elif path == "/action/delete-account":
            session_id = state.get("_session_id")
            self.store.delete(session_id)
            state.clear()
            state.update(deepcopy(DEFAULT_STATE))
            state["_session_id"] = session_id
            state["csrf_token"] = state.get("csrf_token") or ""
            self.store.flash(state, "Local account data deleted.")
            return
        elif path == "/action/lookup-registration":
            payload = {
                "jurisdiction": state["jurisdiction_id"],
                "name": "Local user",
                "birth_year": state["profile"]["birth_year"],
                "address": state["profile"]["address"],
                "registered": state["profile"].get("registered"),
            }
            try:
                result = call_adapter(state, self.selected_jurisdictions(state), "registration_status", payload)
                self.store.flash(state, f"{result['status']}. Verify at {result['official_url']}")
            except IntegrationError as error:
                self.store.flash(state, f"Manual verification needed: {error}. {current_jurisdiction(state)['contacts']['official']}")
            track(state, "registration_lookup", {"status": registration_status(state["profile"], current_jurisdiction(state))})
        elif path == "/action/refresh-data":
            jurisdictions = self.selected_jurisdictions(state)
            polling = call_adapter(
                state,
                jurisdictions,
                "polling_location",
                {"jurisdiction": state["jurisdiction_id"], "address": state["profile"]["address"]},
            )
            ballot = call_adapter(
                state,
                jurisdictions,
                "ballot_information",
                {
                    "jurisdiction": state["jurisdiction_id"],
                    "district": current_jurisdiction(state)["ballot"]["district"],
                    "address": state["profile"]["address"],
                },
            )
            override_key = f"{state['country_code']}:{state['jurisdiction_id']}"
            state.setdefault("jurisdiction_overrides", {})[override_key] = {
                "polling": {"assigned": polling, "refreshed_at": iso_now()},
                "ballot": ballot,
            }
            track(state, "official_data_refreshed")
            self.store.flash(state, "Official-data adapter refreshed. Updated ballot and polling details are stored for this jurisdiction. US regions use Google Civic when GOOGLE_CIVIC_API_KEY is configured.")
        elif path == "/action/onboard":
            self.apply_country_region(form, state)
            profile = state["profile"]
            profile["address"] = clean_text(one(form, "address", profile["address"]), 220)
            profile["birth_year"] = clamp_int(one(form, "birth_year"), profile["birth_year"], 1900, 2026)
            profile["citizen"] = bool_from_form(one(form, "citizen"))
            profile["resident"] = bool_from_form(one(form, "resident"))
            profile["registered"] = bool_from_form(one(form, "registered"))
            profile["country_code"] = state["country_code"]
            state["onboarded"] = True
            track(state, "onboarding_completed", {"country": state["country_code"], "jurisdiction": state["jurisdiction_id"]})
            self.store.flash(state, "Welcome! Your personalized dashboard is ready.")
        else:
            self.store.flash(state, f"Unknown action: {html(path)}")
        self.store.save(state)

    @staticmethod
    def selected_jurisdictions(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        jurisdiction = current_jurisdiction(state)
        return {state["jurisdiction_id"]: jurisdiction}

    @staticmethod
    def apply_country_region(form: dict[str, list[str]], state: dict[str, Any]) -> None:
        current_country = state.get("country_code", "US")
        country_code = clean_choice(one(form, "country_code", current_country), set(COUNTRIES), current_country)
        regions = list_regions(country_code)
        fallback_region = state.get("jurisdiction_id") if state.get("country_code") == country_code else default_region(country_code)
        region_id = clean_choice(one(form, "jurisdiction_id", fallback_region), set(regions), default_region(country_code))
        state["country_code"] = country_code
        state["jurisdiction_id"] = region_id
        state.setdefault("profile", {})["country_code"] = country_code
        state["locale_country_suggested"] = True

    @staticmethod
    def apply_locale_country_suggestion(state: dict[str, Any], accept_language: str) -> bool:
        if state.get("locale_country_suggested"):
            return False
        country_code = country_from_accept_language(accept_language)
        if not country_code:
            return False
        state["country_code"] = country_code
        state["jurisdiction_id"] = default_region(country_code)
        state.setdefault("profile", {})["country_code"] = country_code
        state["locale_country_suggested"] = True
        return True

    def download_ics(self, state: dict[str, Any], query: dict[str, list[str]]) -> Response:
        requested = clean_text(query.get("id", [""])[0], 120)
        deadline = next((item for item in deadlines_within_24_months(current_jurisdiction(state)) if item["id"] == requested), None)
        if not deadline:
            return Response("Not found", HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8")
        track(state, "ics_downloaded", {"deadline": requested})
        self.store.save(state)
        return Response(
            calendar_event(deadline),
            content_type="text/calendar; charset=utf-8",
            headers=[("Content-Disposition", f'attachment; filename="{requested}.ics"')],
        )

    @staticmethod
    def serve_static(path: str) -> Response:
        parts = [part for part in path.removeprefix("/static/").split("/") if part]
        file_path = (STATIC_DIR.joinpath(*parts)).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists() or not file_path.is_file():
            return Response("Not found", HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8")
        content_type = MIME_TYPES.get(file_path.suffix, "application/octet-stream")
        raw = file_path.read_bytes()
        return Response(raw, content_type=content_type)


class Request:
    def __init__(self, environ: dict[str, Any]) -> None:
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/") or "/"
        self.query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)

    def form(self) -> dict[str, list[str]]:
        length = int(self.environ.get("CONTENT_LENGTH") or "0")
        body = self.environ["wsgi.input"].read(length).decode("utf-8") if length else ""
        return parse_qs(body, keep_blank_values=True)


def one(form: dict[str, list[str]], key: str, default: str = "") -> str:
    return form.get(key, [default])[0]


def country_from_accept_language(header: str) -> str:
    for language in header.split(","):
        tag = language.split(";", 1)[0].strip()
        parts = tag.replace("_", "-").split("-")
        if len(parts) < 2:
            continue
        region = parts[-1].upper()
        country_code = LOCALE_COUNTRY_HINTS.get(region)
        if country_code in COUNTRIES:
            return country_code
    return ""


def run_server(host: str = "127.0.0.1", port: int = 4173) -> None:
    app = ElectionApp()
    with make_server(host, port, app) as server:
        print(f"{APP_NAME} WSGI server running at http://{host}:{port}/")
        server.serve_forever()
