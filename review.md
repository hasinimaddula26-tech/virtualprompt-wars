# Code Review — Election Process Assistant

## Status: 18/18 Tests Passing ✅

---

## Architecture

| Layer | Technology | Status |
|-------|-----------|--------|
| Server | WSGI + `wsgiref` | ✅ Running |
| State | SQLite per-session | ✅ Isolated |
| Data | Country adapters + SQLite cache | ✅ Dynamic |
| Security | Fernet vault, CSRF, rate limiting | ✅ Production-grade |
| APIs | Google Civic, Google Maps | ✅ Configured |

---

## Country Support

| Country | Adapter | Regions | Data Quality |
|---------|---------|---------|-------------|
| 🇮🇳 India | `IndiaAdapter` | **All 36 states/UTs** | Assembly seats, Lok Sabha seats, CEO URLs, ECI forms, 1950 helpline |
| 🇺🇸 United States | `UnitedStatesAdapter` | **All 50 states** | 3 rich (CA, TX, NY) + 47 via Vote.gov fallback |
| 🇬🇧 United Kingdom | `GenericCountryAdapter` | JSON config | Community-editable `data/countries/gb.json` |
| 🇨🇦 Canada | `GenericCountryAdapter` | JSON config | Community-editable `data/countries/ca.json` |
| 🇪🇺 European Union | `GenericCountryAdapter` | JSON config | Community-editable `data/countries/eu.json` |
| 🌍 Any other | `GenericCountryAdapter` | Fallback | Generic steps + manual notes |

### India Adapter — Detail Level

| State/UT | Assembly Seats | Lok Sabha Seats | CEO URL |
|----------|---------------|-----------------|---------|
| Tamil Nadu | 234 | 39 | elections.tn.gov.in |
| Uttar Pradesh | 403 | 80 | ceouttarpradesh.nic.in |
| Maharashtra | 288 | 48 | ceo.maharashtra.gov.in |
| West Bengal | 294 | 42 | ceowestbengal.nic.in |
| Karnataka | 224 | 28 | ceo.karnataka.gov.in |
| Delhi (NCT) | 70 | 7 | ceodelhi.gov.in |
| ... and 30 more | ✅ | ✅ | ✅ |

---

## Dynamic Features

| Feature | How It Works |
|---------|-------------|
| **Onboarding** | `/setup` → collects country, state, address, birth year, citizenship |
| **Jurisdiction data** | Loaded from adapter on demand, cached in SQLite |
| **Polling location** | Confirmed locations open Google Maps; fallback jurisdictions clearly require official lookup |
| **Maps embed** | Google Maps iframe when `GOOGLE_MAPS_EMBED_KEY` set |
| **Ballot data** | Google Civic API for US; refreshed adapter results persist in session state; fallback copy points to official sources |
| **Process steps** | Country-specific (India: EVM/VVPAT, EPIC, BLO, NOTA) |
| **Multi-page routing** | `/dashboard`, `/timeline`, `/polling`, etc. — one section per page |

---

## What Works

- ✅ All 36 Indian states/UTs with real constituency counts
- ✅ India-specific: EPIC, Form 6/8/6A, BLO, NVSP, ECI affidavits, NOTA
- ✅ Session-backed adapter refresh for ballot and polling data
- ✅ Fallback polling UI no longer presents unconfirmed locations as real assigned booths
- ✅ Fallback ballot UI now emphasizes official candidate and measure sources
- ✅ Google Maps embed iframe for confirmed polling locations
- ✅ Per-country process steps (not generic placeholders)
- ✅ Multi-page navigation with active page highlighting
- ✅ CSRF on all forms, session isolation, Fernet vault
- ✅ No admin view — clean user-facing interface

## What Needs External APIs

- ⚠️ India: live ECI deadline feed (requires scraper or official API)
- ⚠️ India: booth-level polling data from CEO websites
- ⚠️ India: NVSP voter ID search integration
- ⚠️ India: local-body ward datasets are still not built in
- ⚠️ US: auto-detect state from address via geocoding
- ⚠️ UK/Canada/EU: production election authority APIs

---

## API Configuration (`.env`)

```
GOOGLE_CIVIC_API_KEY=<your key>    # US polling + ballot data
GOOGLE_MAPS_EMBED_KEY=<your key>   # Map iframe for any country
```

## File Summary

| File | Lines | Purpose |
|------|-------|---------|
| `data_sources.py` | 815 | Country adapters (IN: 36 regions, US: 50 states, generic) |
| `render.py` | 680 | Multi-page HTML rendering |
| `web.py` | 450 | WSGI routing + onboarding + actions |
| `integrations.py` | 208 | Google Civic API + Maps + mock fallback |
| `seed_data.py` | 558 | Rich US data (CA, TX, NY) + shared metadata |
| `state.py` | 170 | SQLite session store |
| `security.py` | 149 | Fernet vault, CSRF, rate limiting |
| `tests/` | 230 | 14 smoke tests |
