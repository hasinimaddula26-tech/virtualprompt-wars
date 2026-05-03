# Implementation Plan: Election Process Assistant

## Source Analysis

- The actionable requirements source is `.kiro/specs/election-process-assistant/requirements.md`.
- The previous static JavaScript implementation has been removed at the user's request.
- This plan now targets a Python-first implementation with no Node.js runtime, package manager, or JavaScript application logic.

## Definition of Done

The implementation is complete only when:

1. Every requirement from 1 through 20 has a Python-backed workflow, service, or route.
2. User-facing pages are rendered by Python.
3. Data loading, timeline calculation, registration guidance, voter guide generation, feedback, analytics, integrations, security behavior, and export generation are implemented in Python.
4. Any unavoidable browser-standard files are limited to static assets. The service worker is a tiny PWA cache file only; it contains no application workflow logic.
5. Every deleted, created, or modified file is tracked in `progress.md`.
6. Python tests and local HTTP checks pass before final delivery.
7. The app can run locally with the bundled Python runtime and standard library only.

## Python Technical Approach

- Use the Python standard library for the local runnable version and list production dependencies in `requirements.txt`.
- Implement a WSGI application served locally with `wsgiref.simple_server`; use FastAPI/Uvicorn from `requirements.txt` for the next production ASGI migration.
- Use Python route handling for pages, forms, downloads, status lookups, guide generation, analytics, feedback, incidents, organizer tools, and admin views.
- Keep state in SQLite under `storage/app_state.sqlite3`, isolated by an HTTP-only session cookie.
- Protect all POST actions with session-bound CSRF tokens.
- Keep `election_assistant/seed_data.py` as rich US fallback data and shared metadata.
- Use `election_assistant/data_sources.py` for country-aware jurisdiction loading, adapter selection, JSON country configs, and SQLite jurisdiction caching.
- Render HTML with Python helpers in `election_assistant/render.py`.
- Use Python services for each domain area:
  - `timeline.py`
  - `data_sources.py`
  - `registration.py`
  - `voting.py`
  - `ballot.py`
  - `polling.py`
  - `documents.py`
  - `feedback.py`
  - `analytics.py`
  - `integrations.py`
  - `security.py`
  - `education.py`
- Add optional Google Civic API and Google Maps hooks controlled by `GOOGLE_CIVIC_API_KEY` and `GOOGLE_MAPS_EMBED_KEY`.
- Add a Python smoke test suite in `tests/test_python_app.py`.
- Add static CSS and SVG assets in `static/`.

## Requirement Coverage Checklist

### Requirement 1: Interactive Election Process Navigation

- Render a step-by-step Python page.
- Persist completion state in the session's SQLite state row.
- Show completed, current, and upcoming states.
- Include details, required documents, estimated time, contextual help, and ARIA-friendly controls.

### Requirement 2: Personalized Timeline and Deadline Management

- Calculate jurisdiction deadlines in Python.
- Sort deadlines chronologically and show days remaining.
- Highlight deadlines within 14 days.
- Generate `.ics` calendar files in Python.
- Show reminder schedules and timezone labels.

### Requirement 3: Voter Registration Guidance and Tracking

- Determine status from Python profile state.
- Render jurisdiction-specific methods, official links, required documents, eligibility rules, processing time, and fallback instructions.
- Simulate official registration lookup through the Python integration layer.

### Requirement 4: Multi-Language and Accessibility Support

- Support English, Spanish, Chinese, Vietnamese, Korean, Tagalog, Arabic, French, Russian, and Portuguese.
- Persist selected language and text-size settings.
- Render landmarks, skip link, keyboard-friendly controls, contrast-conscious design, scalable text, and screen-reader mode.

### Requirement 5: Voting Method Education and Comparison

- Render all voting methods available for the selected jurisdiction.
- Compare deadlines, requirements, procedures, and accessibility.
- Show detailed instructions, mail tracking, early voting info, absentee criteria, and wait-time fields.

### Requirement 6: Ballot Information and Candidate Research

- Retrieve ballot data from the active country adapter, using US seed fallback, JSON country config, Google Civic where configured for US, or manual fallback notes.
- Render candidate details, party, websites, statements, measures, fiscal impact, arguments, and citations.
- Persist local research notes and include them in guide exports.

### Requirement 7: Real-Time Notifications and Updates

- Persist notification settings in Python state.
- Support email, SMS, push, categories, and reminder intervals.
- Simulate update notices and immediate disable behavior.

### Requirement 8: Polling Location Finder with Real-Time Information

- Render assigned polling location, address, directions link, hours, wait time, parking, transit, accessibility, language support, and alternative locations within 10 miles from the selected country adapter.

### Requirement 9: Eligibility Verification and Problem Resolution

- Verify age, citizenship, and residency in Python.
- Explain failed criteria and show resolution steps, voting rights restoration notes, official contacts, and hotline details.

### Requirement 10: Personalized Voter Guide Generation

- Generate personalized guide HTML and plain text in Python.
- Generate printable guide layout and QR-style official resource tile.
- Include checklist, status, deadlines, polling place, ballot summary, notes, and contacts.

### Requirement 11: Feedback Collection and Pain Point Identification

- Render feedback forms on major pages.
- Capture page, category, message, timestamp, and optional contact.
- Flag content errors and produce trend summaries in Python.

### Requirement 12: Usage Analytics and System Improvement

- Track anonymized local events in Python state.
- Show page usage, completion, deadline adherence proxy, satisfaction score, feedback trends, and drop-off signals.

### Requirement 13: Offline Access and Progressive Web App

- Add web manifest and service worker static files.
- Render an offline status notice and queueable-action explanation.
- Cache essential app shell files and document cache-size policy.

### Requirement 14: Integration with Official Election Systems

- Implement Python mock adapters for registration status, polling locations, and ballot information.
- Validate schemas, log requests, use retry with exponential backoff, and show fallback notices.

### Requirement 15: Security and Privacy Protection

- Do not collect SSN or driver license values.
- Validate password complexity in Python.
- Rate-limit failed login attempts.
- Enforce a 30-minute authenticated session timeout.
- Provide local account deletion.
- Use a Python local vault with PBKDF2-HMAC and Fernet-like authenticated encryption fallback using standard-library HMAC and XOR stream derivation for prototype storage, with clear production guidance to use audited cryptography.

### Requirement 16: Educational Content and Civic Engagement

- Render educational modules, transcripts, completion state, voting rights context, volunteer opportunities, and election worker information.

### Requirement 17: Mobile-First Responsive Design

- Use mobile-first CSS from 320px upward.
- Provide touch-friendly controls, compact layouts, responsive grids, print support, and orientation-safe content.

### Requirement 18: Innovative Voting Method Proposals

- Render ranked choice, approval, and STAR voting explainers.
- Include benefits, challenges, examples, modernization proposals, advocacy resources, and reform tracking placeholders.

### Requirement 19: Voter Registration Drive Support

- Render organizer toolkit, printable materials, QR-style links, batch tracking, multilingual options, legal guidance, and aggregate stats.

### Requirement 20: Election Day Support and Incident Reporting

- Render election day dashboard, incident forms, categorization, immediate guidance, escalation messaging, hotline/legal resources, pattern detection, and election day reminder settings.

## Build Phases

### Phase 1: Replace Current Implementation

- Stop the old Node server.
- Delete the JavaScript/Node implementation files.
- Update `implimentation_plan.md` and `progress.md`.

### Phase 2: Python Skeleton

- Create `election_assistant/` package.
- Create `server.py`.
- Add static assets and manifest.
- Add storage directory placeholder and SQLite-backed state.

### Phase 3: Python Domain Services

- Implement seed data, SQLite state management, timelines, registration, eligibility, voting, ballot, polling, guide exports, feedback, analytics, integration adapters, security, CSRF, and education services.

### Phase 4: Python Rendering and Routes

- Render all user pages server-side.
- Add POST actions for progress, settings, profile, notifications, feedback, incidents, notes, batch tracking, password validation, vault operations, data refresh, and account deletion.
- Add download routes for ICS, HTML guide, plain text guide, and organizer toolkit.

### Phase 5: PWA and Static Assets

- Add `static/styles.css`, `static/assets/icon.svg`, `static/assets/civic-map.svg`, `static/manifest.webmanifest`, and `static/service-worker.js`.
- Keep PWA script minimal and static only.

### Phase 6: Verification

- Add Python smoke tests.
- Compile all Python files.
- Run tests with bundled Python.
- Start the Python server and verify HTTP responses.
- Record every result in `progress.md`.
