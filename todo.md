# TODO — Global Dynamic Election Support

Last updated: 2026-05-01

---

## ✅ Completed

### India Adapter (36 states/UTs)
- [x] All 28 states with assembly constituency counts and Lok Sabha seat counts
- [x] All 8 union territories with correct seat data
- [x] Official CEO website URL for each state/UT
- [x] India-specific process steps (EPIC, EVM, VVPAT, BLO, NOTA, Form 6/8/6A)
- [x] India-specific registration (NVSP, ERO, BLO verification)
- [x] State-specific deadlines (roll revision, nomination, polling, counting)
- [x] National Election Helpline 1950
- [x] Dynamic Google Maps directions from user's address

### United States Adapter (50 states)
- [x] All 50 states available in dropdown
- [x] Rich data for California, Texas, New York (candidates, measures, polling)
- [x] Generic Vote.gov fallback for remaining 47 states
- [x] Google Civic API integration for live polling + ballot data

### Global Support
- [x] Country selector in onboarding (India, US, UK, Canada, EU, Other)
- [x] JSON config system for community-contributed countries (`data/countries/`)
- [x] Generic adapter fallback for any unconfigured country
- [x] Standard jurisdiction schema across all countries
- [x] SQLite-cached jurisdiction payloads
- [x] Session-stored refreshed ballot and polling overrides per jurisdiction
- [x] Fallback ballot research copy now shows official-source guidance instead of misleading candidate placeholders
- [x] Fallback polling cards now mark unconfirmed polling locations as official lookup required

### Infrastructure
- [x] Multi-page routing (`/dashboard`, `/timeline`, `/polling`, etc.)
- [x] Onboarding flow with country → state → details
- [x] Google Maps embed + directions for confirmed polling destinations
- [x] CSRF, Fernet vault, session isolation
- [x] 18 passing tests
- [x] Admin view removed

---

## 🔧 Remaining (Requires External APIs/Contracts)

### India — Live Data
- [ ] Live ECI deadline feed or approved scraper for real election dates
- [ ] Booth-level polling data from CEO state websites
- [ ] NVSP voter ID search integration (if public API available)
- [ ] Ward-level data for local body elections (panchayat, municipal)
- [ ] Live candidate list from ECI nomination data

### United States — Expansion
- [ ] Address-to-state geocoding for automatic state detection
- [ ] Real state SOS deadline feeds for all 50 states
- [ ] Expand rich data beyond CA/TX/NY

### United Kingdom
- [ ] Electoral Commission API for registration and polling
- [ ] Postcode-based polling station lookup
- [ ] Council-level election data

### Canada
- [ ] Elections Canada federal election API
- [ ] Provincial election adapters
- [ ] Postal code to riding mapping

### European Union
- [ ] Country-specific adapters for member nations
- [ ] European Parliament election data

### Generic
- [ ] REST adapter with configurable URL + auth + JSON path mapping
- [ ] Multiple concurrent election calendars (federal + state + local)

---

## Verification

- [x] `python -m unittest tests.test_python_app` — 18/18 passed
- [x] India adapter returns 36 regions with seat counts
- [x] Tamil Nadu: 234 assembly, 39 Lok Sabha
- [x] Delhi: 70 assembly, 7 Lok Sabha (UT)
- [x] Onboarding redirects new users to `/setup`
- [x] Refreshed ballot and polling adapter results persist in session state
- [x] Fallback polling UI uses official lookup messaging when a precise booth is unavailable
- [x] Server runs on `http://127.0.0.1:4173/`
