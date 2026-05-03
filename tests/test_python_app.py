from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import unittest
import uuid

from election_assistant import APP_VERSION
from election_assistant.data_sources import get_jurisdiction, list_countries, list_regions
from election_assistant.documents import guide_html, guide_text, organizer_toolkit_text
from election_assistant.integrations import call_adapter, google_maps_directions_url
from election_assistant.registration import eligibility
from election_assistant.render import current_jurisdiction, render_app
from election_assistant.security import cryptography_available, open_vault, password_is_valid, seal_vault
from election_assistant.seed_data import JURISDICTIONS, LANGUAGES, ORGANIZER_TOOLKIT
from election_assistant.state import DEFAULT_STATE, StateStore
from election_assistant.timeline import calendar_event, deadlines_within_24_months
from election_assistant.web import ElectionApp


ROOT = Path(__file__).resolve().parent.parent
PYTHON = "python"


class PythonAppSmokeTests(unittest.TestCase):
    def make_state(self):
        state = deepcopy(DEFAULT_STATE)
        state["csrf_token"] = "test-token"
        return state

    def make_store(self):
        path = ROOT / "storage" / f"test_state_{uuid.uuid4().hex}.sqlite3"
        self.addCleanup(lambda: path.exists() and path.unlink())
        return StateStore(path)

    def test_python_version_marker(self):
        self.assertIn("python", APP_VERSION)

    def test_all_required_languages_are_present(self):
        self.assertEqual(len(LANGUAGES), 10)
        self.assertEqual(
            {item["code"] for item in LANGUAGES},
            {"en", "es", "zh", "vi", "ko", "tl", "ar", "fr", "ru", "pt"},
        )

    def test_seed_data_covers_core_jurisdiction_workflows(self):
        self.assertGreaterEqual(len(JURISDICTIONS), 3)
        for jurisdiction in JURISDICTIONS.values():
            self.assertGreaterEqual(len(jurisdiction["deadlines"]), 4)
            self.assertGreaterEqual(len(jurisdiction["process_steps"]), 5)
            self.assertGreaterEqual(len(jurisdiction["voting_methods"]), 3)
            self.assertGreaterEqual(len(jurisdiction["ballot"]["candidates"]), 2)
            self.assertGreaterEqual(len(jurisdiction["ballot"]["measures"]), 1)
            self.assertGreaterEqual(len(jurisdiction["polling"]["assigned"]["accessibility"]), 3)

    def test_country_data_sources_cover_india_and_generic_regions(self):
        countries = dict(list_countries())
        self.assertIn("India", countries.values())
        self.assertIn("United Kingdom", countries.values())

        us_regions = list_regions("US")
        self.assertGreaterEqual(len(us_regions), 50)
        montana = get_jurisdiction("US", "montana")
        self.assertEqual(montana["country"], "US")
        self.assertEqual(montana["name"], "Montana")
        self.assertIn("vote.gov", montana["official"]["registration_url"])

        india_regions = list_regions("IN")
        self.assertIn("tamil-nadu", india_regions)
        tamil_nadu = get_jurisdiction("IN", "tamil-nadu")
        self.assertEqual(tamil_nadu["country"], "IN")
        self.assertEqual(tamil_nadu["country_name"], "India")
        self.assertEqual(tamil_nadu["timezone"], "Asia/Kolkata")
        self.assertEqual(tamil_nadu["contacts"]["hotline"], "National Election Helpline: 1950")
        self.assertIn("voters.eci.gov.in", tamil_nadu["official"]["registration_url"])
        self.assertGreaterEqual(len(tamil_nadu["deadlines"]), 4)
        self.assertGreaterEqual(len(tamil_nadu["process_steps"]), 5)
        self.assertEqual(tamil_nadu["ballot"]["candidates"][0]["name"], "Official candidate list")
        self.assertIn("assembly constituencies", tamil_nadu["ballot"]["coverage_note"])

        uk_regions = list_regions("GB")
        self.assertIn("england", uk_regions)
        england = get_jurisdiction("GB", "england")
        self.assertEqual(england["country"], "GB")
        self.assertIn("polling place", england["polling"]["assigned"]["name"].lower())

    def test_rendered_python_page_maps_all_requirements_and_csrf(self):
        state = self.make_state()
        state["onboarded"] = True
        covered = set()
        for page_id in ["dashboard", "process", "timeline", "registration", "voting",
                         "ballot", "polling", "eligibility", "guide", "support", "learning"]:
            page = render_app(state, [], page_id)
            self.assertIn("<main", page)
            self.assertIn('name="_csrf_token"', page)
            marker = 'data-requirement="'
            offset = 0
            while marker in page[offset:]:
                start = page.index(marker, offset) + len(marker)
                end = page.index('"', start)
                for value in page[start:end].split(","):
                    covered.add(int(value.strip()))
                offset = end
        # Dashboard page checks
        dashboard = render_app(state, [], "dashboard")
        self.assertIn("role=\"banner\"", dashboard)
        self.assertIn("skip-link", dashboard)
        self.assertNotIn("<script>alert", dashboard)
        self.assertEqual(covered, set(range(1, 21)))

        setup_state = self.make_state()
        setup_state["country_code"] = "IN"
        setup_state["jurisdiction_id"] = "tamil-nadu"
        setup = render_app(setup_state, [], "setup")
        self.assertIn('name="country_code"', setup)
        self.assertIn("India", setup)
        self.assertIn("Tamil Nadu", setup)

        district = JURISDICTIONS["california"]["ballot"]["district"]
        state["manual_candidates"] = {
            district: [
                {
                    "id": "manual-1",
                    "race": district,
                    "name": "Manual Candidate",
                    "party": "Local listing",
                    "website": "https://example.org",
                    "statement": "Added for a jurisdiction without live candidate data.",
                    "issues": {"Manual note": "Verify source"},
                    "source": "Manual local note",
                }
            ]
        }
        ballot_page = render_app(state, [], "ballot")
        self.assertIn("Manual Candidate", ballot_page)
        self.assertIn("/action/add-candidate#ballot", ballot_page)

    def test_render_hides_placeholder_candidate_when_manual_notes_exist_for_fallback_ballot(self):
        state = self.make_state()
        state["onboarded"] = True
        state["country_code"] = "IN"
        state["jurisdiction_id"] = "tamil-nadu"
        district = get_jurisdiction("IN", "tamil-nadu")["ballot"]["district"]
        state["manual_candidates"] = {
            district: [
                {
                    "id": "manual-1",
                    "race": district,
                    "name": "Local Research Candidate",
                    "party": "Independent",
                    "website": "https://example.org/local-research-candidate",
                    "statement": "Verified from the official candidate list.",
                    "issues": {"Verification": "Checked against the CEO candidate filing."},
                    "source": "Manual local note",
                }
            ]
        }
        ballot_page = render_app(state, [], "ballot")
        self.assertIn("Local Research Candidate", ballot_page)
        self.assertNotIn("Official candidate list", ballot_page)
        self.assertIn("Add two or more verified candidates", ballot_page)

    def test_current_jurisdiction_merges_saved_override_data(self):
        state = self.make_state()
        state["country_code"] = "IN"
        state["jurisdiction_id"] = "tamil-nadu"
        state["jurisdiction_overrides"] = {
            "IN:tamil-nadu": {
                "polling": {
                    "assigned": {
                        "name": "Custom polling lookup result",
                        "address": "Chennai, Tamil Nadu",
                        "status": "official_lookup_required",
                        "hours": "Check official authority",
                        "wait_minutes": "N/A",
                        "parking": "Check local site information.",
                        "transit": "Use map directions or local transit guidance.",
                        "lookup_instructions": "Use the official booth finder for this address.",
                        "accessibility": ["Check accessible entrance"],
                        "languages": ["Check official authority for language support"],
                    }
                }
            }
        }
        jurisdiction = current_jurisdiction(state)
        self.assertEqual(jurisdiction["polling"]["assigned"]["name"], "Custom polling lookup result")
        self.assertEqual(jurisdiction["polling"]["assigned"]["address"], "Chennai, Tamil Nadu")

    def test_refresh_action_stores_adapter_results_for_current_jurisdiction(self):
        app = ElectionApp(self.make_store())
        state = self.make_state()
        state["onboarded"] = True
        state["country_code"] = "IN"
        state["jurisdiction_id"] = "tamil-nadu"
        app.handle_action("/action/refresh-data", {}, state)
        override = state["jurisdiction_overrides"]["IN:tamil-nadu"]
        self.assertIn("ballot", override)
        self.assertEqual(override["polling"]["assigned"]["status"], "official_lookup_required")
        self.assertIn("country adapter fallback data", override["polling"]["assigned"]["source"])

    def test_polling_page_uses_official_lookup_copy_for_unconfirmed_locations(self):
        state = self.make_state()
        state["onboarded"] = True
        state["country_code"] = "IN"
        state["jurisdiction_id"] = "tamil-nadu"
        polling_page = render_app(state, [], "polling")
        self.assertIn("Check official authority", polling_page)
        self.assertIn("Official lookup required", polling_page)
        self.assertNotIn("Open Google Maps directions", polling_page)

    def test_sqlite_state_isolates_sessions(self):
        store = self.make_store()
        alpha = store.load("alpha")
        beta = store.load("beta")
        alpha["profile"]["address"] = "1 Alpha Way"
        beta["profile"]["address"] = "2 Beta Way"
        store.save(alpha)
        store.save(beta)
        self.assertEqual(store.load("alpha")["profile"]["address"], "1 Alpha Way")
        self.assertEqual(store.load("beta")["profile"]["address"], "2 Beta Way")
        self.assertNotEqual(store.load("alpha")["csrf_token"], store.load("beta")["csrf_token"])

    def test_registration_eligibility_unit_cases(self):
        state = self.make_state()
        jurisdiction = JURISDICTIONS["california"]
        self.assertTrue(eligibility(state["profile"], jurisdiction)["eligible"])
        state["profile"]["citizen"] = False
        result = eligibility(state["profile"], jurisdiction)
        self.assertFalse(result["eligible"])
        self.assertIn("Citizenship", " ".join(result["issues"]))

    def test_deadlines_and_ics_export(self):
        jurisdiction = JURISDICTIONS["california"]
        deadlines = deadlines_within_24_months(jurisdiction)
        self.assertEqual(deadlines, sorted(deadlines, key=lambda item: item["date"]))
        ics = calendar_event(deadlines[0])
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn(deadlines[0]["title"], ics)

    def test_document_exports_are_python_generated(self):
        state = self.make_state()
        jurisdiction = JURISDICTIONS["california"]
        html = guide_html(state, jurisdiction)
        text = guide_text(state, jurisdiction)
        toolkit = organizer_toolkit_text(jurisdiction, ORGANIZER_TOOLKIT)
        self.assertIn("Personalized voter guide", html)
        self.assertIn("Personalized voter guide", text)
        self.assertIn("Registration Drive Toolkit", toolkit)

    def test_security_policy_and_no_custom_crypto(self):
        state = self.make_state()
        state["research_notes"] = {"Sample District 12": "Compare candidate housing plans."}
        self.assertTrue(password_is_valid("StrongPass123!"))
        self.assertFalse(password_is_valid("weak"))
        source = (ROOT / "election_assistant" / "security.py").read_text(encoding="utf-8")
        self.assertNotIn("SBOX", source)
        self.assertNotIn("aes256_encrypt_block", source)
        if cryptography_available():
            seal_vault(state, "VeryStrongPassphrase123!")
            self.assertEqual(state["vault"]["library"], "cryptography")
            state["research_notes"] = {}
            opened = open_vault(state, "VeryStrongPassphrase123!")
            self.assertEqual(opened["research_notes"]["Sample District 12"], "Compare candidate housing plans.")
        else:
            with self.assertRaises(RuntimeError):
                seal_vault(state, "VeryStrongPassphrase123!")

    def test_integration_adapter_logs_validated_calls_and_maps_link(self):
        state = self.make_state()
        response = call_adapter(
            state,
            JURISDICTIONS,
            "registration_status",
            {
                "jurisdiction": "california",
                "name": "Local user",
                "birth_year": 1992,
                "address": "100 Civic Harbor Way",
            },
        )
        self.assertIn("status", response)
        self.assertEqual(state["integration_logs"][0]["status"], "ok")
        self.assertIn("google.com/maps/dir", google_maps_directions_url("100 Civic Harbor Way"))

    def test_wsgi_get_and_csrf_post_flow(self):
        app = ElectionApp(self.make_store())
        status_headers = {}

        def start_response(status, headers):
            status_headers["status"] = status
            status_headers["headers"] = headers

        # New user gets redirected to /setup
        b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/", "QUERY_STRING": "",
                       "wsgi.input": BytesIO(b""), "CONTENT_LENGTH": "0"}, start_response))
        self.assertTrue(status_headers["status"].startswith("303"))
        cookie = next(value for key, value in status_headers["headers"] if key == "Set-Cookie")

        # GET /setup returns 200 with onboarding form
        body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/setup", "QUERY_STRING": "",
                              "HTTP_COOKIE": cookie, "HTTP_ACCEPT_LANGUAGE": "en-IN,en;q=0.8",
                              "wsgi.input": BytesIO(b""), "CONTENT_LENGTH": "0"},
                             start_response)).decode("utf-8")
        self.assertTrue(status_headers["status"].startswith("200"))
        self.assertIn("Set up your election assistant", body)
        self.assertIn("India", body)
        self.assertIn("Tamil Nadu", body)
        token_marker = 'name="_csrf_token" value="'
        token_start = body.index(token_marker) + len(token_marker)
        token_end = body.index('"', token_start)
        token = body[token_start:token_end]

        # POST onboarding with a non-US country and dynamic region.
        encoded = (
            f"_csrf_token={token}&country_code=IN&jurisdiction_id=tamil-nadu"
            "&address=1+Test+St&birth_year=1990&citizen=on&resident=on"
        ).encode("utf-8")
        status_headers.clear()
        app({"REQUEST_METHOD": "POST", "PATH_INFO": "/action/onboard", "QUERY_STRING": "",
             "HTTP_COOKIE": cookie, "wsgi.input": BytesIO(encoded), "CONTENT_LENGTH": str(len(encoded))},
            start_response)
        self.assertTrue(status_headers["status"].startswith("303"))

        status_body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/status", "QUERY_STRING": "",
                                     "HTTP_COOKIE": cookie, "wsgi.input": BytesIO(b""), "CONTENT_LENGTH": "0"},
                                    start_response)).decode("utf-8")
        status_payload = json.loads(status_body)
        self.assertEqual(status_payload["country"], "India")
        self.assertEqual(status_payload["jurisdiction"], "Tamil Nadu")

        health_body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/health", "QUERY_STRING": "",
                                     "HTTP_COOKIE": cookie, "wsgi.input": BytesIO(b""), "CONTENT_LENGTH": "0"},
                                    start_response)).decode("utf-8")
        health_payload = json.loads(health_body)
        self.assertEqual(health_payload["status"], "ok")
        self.assertGreaterEqual(health_payload["country_count"], 6)

        header_map = dict(status_headers["headers"])
        self.assertEqual(header_map["X-Content-Type-Options"], "nosniff")
        self.assertEqual(header_map["Referrer-Policy"], "no-referrer")
        self.assertEqual(header_map["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", header_map["Content-Security-Policy"])

    def test_wsgi_rejects_missing_csrf(self):
        app = ElectionApp(self.make_store())
        status_headers = {}

        def start_response(status, headers):
            status_headers["status"] = status
            status_headers["headers"] = headers

        app(
            {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/action/feedback",
                "QUERY_STRING": "",
                "wsgi.input": BytesIO(b"page=Smoke&category=usability&message=Route+check"),
                "CONTENT_LENGTH": "49",
            },
            start_response,
        )
        self.assertTrue(status_headers["status"].startswith("303"))

    def test_static_manifest_and_no_node_implementation_files(self):
        manifest = json.loads((ROOT / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["display"], "standalone")
        for removed in [
            "app.js",
            "package.json",
            "tools/dev-server.mjs",
            "tests/smoke-check.mjs",
            "data/election-data.json",
        ]:
            self.assertFalse((ROOT / removed).exists(), f"{removed} should have been removed")

    def test_requirements_match_runtime_stack(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("cryptography", requirements)
        self.assertIn("python-dotenv", requirements)
        self.assertNotIn("fastapi", requirements)
        self.assertNotIn("sqlalchemy", requirements)


if __name__ == "__main__":
    unittest.main()
