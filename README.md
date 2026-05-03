---
title: Virtual Prompt War
emoji: 🗳️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Election Process Assistant

Python-first implementation of a smart election assistant built for a voter guidance persona. The app helps a user understand registration, deadlines, ballot research, polling access, and official next steps using country-aware logic with Google service integration where available.

## Challenge Submission

### Chosen Vertical

This submission is built around a **civic assistance / voter guidance** persona:

- A person needs help understanding election rules for their country or state
- The assistant adapts guidance based on country, jurisdiction, address, age, residency, and registration state
- The app prioritizes official election authority links before any manual or fallback guidance

### Approach And Logic

The solution uses a layered decision model:

1. Collect onboarding context such as country, state or region, address, age, citizenship, and residency.
2. Resolve a jurisdiction through a country adapter.
3. Use richer live or seeded data where available.
4. Fall back to structured official-source guidance when live ballot or polling data is unavailable.
5. Preserve session-specific ballot and polling refresh results locally in SQLite.

### How The Solution Works

- `election_assistant/data_sources.py` provides dynamic country and region adapters.
- `election_assistant/web.py` serves the WSGI application, form actions, API endpoints, and session flow.
- `election_assistant/render.py` renders accessible server-side HTML for dashboard, timeline, ballot, polling, guide, and support pages.
- `election_assistant/integrations.py` integrates Google Civic and Google Maps when configured.
- `election_assistant/state.py` stores isolated per-session application state in SQLite.

### Assumptions

- Official election authority sources are the source of truth for production voting decisions.
- Google Civic live ballot and polling support is only available for supported US addresses.
- For jurisdictions without live official feeds, the app should be explicit about coverage gaps instead of pretending exact booth or candidate data exists.
- Local SQLite persistence is acceptable for challenge evaluation and demo hosting.

### Why This Is Practical

- Supports India, all 50 US states, and generic international fallback flows.
- Produces a personalized voter guide with deadlines, polling details, and research notes.
- Uses official links and conservative fallback behavior for real-world safety.
- Works without a JavaScript SPA build pipeline, keeping deployment simple and maintainable.

## Run Locally

This workspace does not currently expose `python` on PATH, so use the bundled runtime:

```powershell
& 'C:\Users\vettrivel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' server.py --host 127.0.0.1 --port 4173
```

Open:

```text
http://127.0.0.1:4173/
```

## Hugging Face Space

This repository is configured as a Docker Space for `https://huggingface.co/spaces/vettri06/virtual_prompt_war`.

Build/runtime details:

- Container entrypoint: `python server.py --host 0.0.0.0 --port 7860`
- Docker configuration: `Dockerfile`
- Space port: `7860`
- Health endpoint: `/api/health`

Runtime state is stored in `storage/app_state.sqlite3` and isolated by the `epa_session` HTTP-only cookie. Country/jurisdiction adapter payloads are cached in `storage/data_source_cache.sqlite3`.

## Test

```powershell
& 'C:\Users\vettrivel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m compileall server.py election_assistant tests
& 'C:\Users\vettrivel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_python_app
```

## Optional Production Dependencies

The local workspace does not currently have third-party packages installed. `requirements.txt` lists the production packages recommended by the review:

```powershell
pip install -r requirements.txt
```

When `cryptography` is installed, the private vault uses Fernet with PBKDF2-HMAC-derived keys. Without it, the vault feature fails closed instead of using custom cryptography.

## Google Services

Set these environment variables to enable live Google-backed behavior:

```powershell
$env:GOOGLE_CIVIC_API_KEY='your-civic-api-key'
$env:GOOGLE_MAPS_EMBED_KEY='your-maps-embed-key'
```

Without keys, the app keeps using country adapter fallback data and Google Maps direction links. Google Civic is scoped to US jurisdictions only.

### Google Services Used

- **Google Civic Information API**
  Used for live US ballot and polling information when a supported address and API key are available.
- **Google Maps Directions**
  Used to generate directions links for confirmed polling destinations and official lookup flows.
- **Google Maps Embed**
  Used to render an embedded polling location map when an embed key is configured and the location is confirmed.

## Country Data

- `election_assistant/data_sources.py` is the country-aware adapter layer.
- `seed_data.py` remains the rich US fallback and shared metadata source.
- `data/countries/*.json` contains static country configs for non-US fallback coverage.
- Current built-in coverage includes India, all 50 US states, United Kingdom sample config, Canada sample config, EU sample config, and a generic other-country fallback.

## Notes

- Application workflows are implemented in Python under `election_assistant/`.
- The browser service worker files under `static/` are minimal PWA support files only.
- Election records are mock demonstration data and must be replaced with official election authority feeds before production use.
- Local SQLite runtime files under `storage/*.sqlite3` are ignored by git.

## Quality Signals

- Security headers are sent on application responses.
- CSRF protection is enforced on form actions.
- Private vault storage uses `cryptography` Fernet when the package is installed.
- Keyboard focus styles, skip links, and touch-friendly form controls are built in.
- Automated tests cover routing, security, fallback behavior, and adapter refresh logic.
