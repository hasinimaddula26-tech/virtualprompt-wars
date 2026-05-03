"""Server-side HTML rendering."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .analytics import completion_stats
from .ballot import comparison_rows
from .data_sources import COUNTRIES, get_jurisdiction, list_countries, list_regions
from .education import learning_model
from .feedback import analyze_feedback
from .integrations import google_maps_embed_configured, google_maps_embed_url, google_maps_directions_url
from .polling import alternatives_within_10_miles, assigned_location
from .registration import eligibility, registration_status, resolution_steps
from .security import cryptography_available
from .seed_data import INCIDENT_TYPES, LANGUAGES, META, TRANSLATIONS
from .timeline import days_until, deadlines_within_24_months, is_critical, next_deadline
from .utils import html, list_html, tag_html
from .voting import selected_method


def tr(state: dict[str, Any], key: str) -> str:
    language = state.get("language", "en")
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


def _override_key(state: dict[str, Any]) -> str:
    return f"{state.get('country_code', 'US')}:{state.get('jurisdiction_id', '')}"


def _merge_nested(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _merge_nested(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def current_jurisdiction(state: dict[str, Any]) -> dict[str, Any]:
    jurisdiction = deepcopy(get_jurisdiction(state.get("country_code", "US"), state.get("jurisdiction_id", "")))
    override = state.get("jurisdiction_overrides", {}).get(_override_key(state), {})
    if override:
        jurisdiction = _merge_nested(jurisdiction, override)
    return jurisdiction


def current_language(state: dict[str, Any]) -> dict[str, Any]:
    return next((item for item in LANGUAGES if item["code"] == state.get("language")), LANGUAGES[0])


def options(items: list[tuple[str, str]], selected: str) -> str:
    return "".join(
        f'<option value="{html(value)}"{" selected" if value == selected else ""}>{html(label)}</option>'
        for value, label in items
    )


def flash_html(messages: list[str]) -> str:
    if not messages:
        return ""
    return '<div class="status-alert" role="status" aria-live="polite">' + "<br>".join(html(message) for message in messages) + "</div>"


def _nav_link(label: str, page_id: str, current: str) -> str:
    active = ' class="nav-active"' if page_id == current else ""
    return f'<a href="/{page_id}"{active}>{html(label)}</a>'


def _is_placeholder_candidate(candidate: dict[str, Any]) -> bool:
    return candidate.get("id") == "manual-candidate-notes"


def _coverage_summary(jurisdiction: dict[str, Any]) -> str:
    if jurisdiction.get("country") == "IN":
        assembly = jurisdiction.get("contacts", {}).get("assembly_seats")
        lok_sabha = jurisdiction.get("contacts", {}).get("lok_sabha_seats")
        if assembly and assembly != "0":
            return (
                f"{jurisdiction['name']} includes {assembly} assembly constituencies and "
                f"{lok_sabha} Lok Sabha seats. Local ward coverage still requires official sources."
            )
        return (
            f"{jurisdiction['name']} includes {lok_sabha} Lok Sabha seat(s). "
            "State assembly or local ward coverage still requires official sources."
        )
    return f"{jurisdiction['country_name']} coverage is tailored to {jurisdiction['name']} using the configured {jurisdiction.get('district_label', 'district').lower()} label."


def render_onboarding(state: dict[str, Any]) -> str:
    country_code = state.get("country_code", "US")
    country = COUNTRIES.get(country_code, COUNTRIES["US"])
    jurisdiction_options = [(key, value) for key, value in list_regions(country_code).items()]
    return f"""
    <section class="section-band dashboard-band" aria-labelledby="setupTitle">
      <div class="section-inner setup-inner">
        <div class="section-heading">
          <p class="eyebrow">Welcome</p>
          <h2 id="setupTitle">Set up your election assistant</h2>
        </div>
        <p class="setup-copy">Choose your country and voting area to tailor deadlines, registration guidance, ballot research, and polling details.</p>
        <form method="post" action="/action/onboard" class="panel field-group">
          <label>Country
            <select name="country_code">{options(list_countries(), country_code)}</select>
          </label>
          <label>{html(country['region_label'])}
            <select name="jurisdiction_id">{options(jurisdiction_options, state.get("jurisdiction_id", "california"))}</select>
          </label>
          <label>Street address <input name="address" type="text" autocomplete="street-address" value="{html(state['profile']['address'])}" required></label>
          <label>Birth year <input name="birth_year" type="number" min="1900" max="2026" value="{html(state['profile']['birth_year'])}" required></label>
          <label class="switch-row"><input name="citizen" type="checkbox" checked> I am a citizen</label>
          <label class="switch-row"><input name="resident" type="checkbox" checked> I am a resident of this voting area</label>
          <label class="switch-row"><input name="registered" type="checkbox"> I am already registered to vote</label>
          <button type="submit">Get started</button>
        </form>
      </div>
    </section>
    """


PAGES = {
    "dashboard": ("Dashboard", lambda s, j, m: render_dashboard(s, j, m)),
    "process": ("Process", lambda s, j, m: render_process(s, j)),
    "timeline": ("Timeline", lambda s, j, m: render_timeline(s, j)),
    "registration": ("Registration", lambda s, j, m: render_registration(s, j)),
    "voting": ("Voting", lambda s, j, m: render_voting(s, j)),
    "ballot": ("Ballot", lambda s, j, m: render_ballot(s, j)),
    "polling": ("Polling", lambda s, j, m: render_polling(s, j)),
    "eligibility": ("Security", lambda s, j, m: render_eligibility_security(s, j)),
    "guide": ("Guide", lambda s, j, m: render_guide(s, j)),
    "support": ("Support", lambda s, j, m: render_support(s, j)),
    "learning": ("Learning", lambda s, j, m: render_learning(s, j)),
}


def render_app(state: dict[str, Any], messages: list[str], page: str = "dashboard") -> str:
    jurisdiction = current_jurisdiction(state)
    language = current_language(state)
    scale = int(state.get("text_scale", 100))
    body_class = "screen-reader-mode" if state.get("screen_reader") else ""

    if page == "setup":
        content = render_onboarding(state)
        nav_html = ""
    else:
        if page not in PAGES:
            page = "dashboard"
        _, renderer = PAGES[page]
        content = renderer(state, jurisdiction, messages)
        nav_items = " ".join(_nav_link(label, pid, page) for pid, (label, _) in PAGES.items())
        nav_html = f'<nav class="section-nav" aria-label="Primary sections">{nav_items}</nav>'

    result = f"""<!doctype html>
<html lang="{html(language['code'])}" dir="{html(language['dir'])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#12343b">
  <title>Election Process Assistant</title>
  <link rel="manifest" href="/static/manifest.webmanifest">
  <link rel="icon" href="/static/assets/icon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/static/styles.css">
  <style>:root {{ --font-scale: {scale / 100:.2f}; }}</style>
  <script src="/static/pwa-register.js" defer></script>
</head>
<body class="{body_class}">
  <a class="skip-link" href="#main">Skip to main content</a>
  <header class="app-header" role="banner">
    <div class="brand">
      <img src="/static/assets/icon.svg" alt="" width="48" height="48">
      <div>
        <p class="eyebrow">{html(tr(state, "kicker"))}</p>
        <h1>Election Process Assistant</h1>
      </div>
    </div>
    {render_settings_form(state) if page != "setup" else ""}
  </header>
  {nav_html}
  <main id="main" tabindex="-1">
    {flash_html(messages) if page != "dashboard" else ""}
    {content}
  </main>
  <footer class="app-footer">
    <p>{html(META['data_boundary'])}</p>
    <p>Local civic guidance workspace. Offline cache target: {html(META['cache_limit_mb'])} MB</p>
  </footer>
</body>
</html>"""
    return add_csrf_fields(result, state.get("csrf_token", ""))


def add_csrf_fields(page: str, token: str) -> str:
    field = f'<input type="hidden" name="_csrf_token" value="{html(token)}">'
    return re.sub(r'(<form\b[^>]*method="post"[^>]*>)', rf'\1{field}', page)


def render_settings_form(state: dict[str, Any]) -> str:
    country_code = state.get("country_code", "US")
    country = COUNTRIES.get(country_code, COUNTRIES["US"])
    jurisdiction_options = [(key, value) for key, value in list_regions(country_code).items()]
    language_options = [(item["code"], item["label"]) for item in LANGUAGES]
    return f"""
    <form method="post" action="/action/settings" class="control-panel" aria-label="Personalization controls">
      <label>Country
        <select name="country_code">{options(list_countries(), country_code)}</select>
      </label>
      <label>{html(country['region_label'])}
        <select name="jurisdiction_id">{options(jurisdiction_options, state.get("jurisdiction_id", "california"))}</select>
      </label>
      <label>Language
        <select name="language">{options(language_options, state.get("language", "en"))}</select>
      </label>
      <label>Text size
        <input name="text_scale" type="range" min="100" max="200" step="10" value="{html(state.get('text_scale', 100))}">
      </label>
      <label class="switch-row">
        <input name="screen_reader" type="checkbox"{" checked" if state.get("screen_reader") else ""}>
        Screen reader mode
      </label>
      <button type="submit">Apply</button>
    </form>
    """


def render_dashboard(state: dict[str, Any], jurisdiction: dict[str, Any], messages: list[str]) -> str:
    stats = completion_stats(state, jurisdiction)
    deadline = next_deadline(jurisdiction)
    remaining = days_until(deadline["date"]) if deadline else "N/A"
    return f"""
    <section id="dashboard" class="section-band dashboard-band" data-requirement="1,2,3,4,7,13,15,17" aria-labelledby="dashboardTitle">
      <div class="section-inner">
        <div class="section-heading">
          <p class="eyebrow">{html(tr(state, "kicker"))}</p>
          <h2 id="dashboardTitle">{html(tr(state, "workspace"))}</h2>
        </div>
        {flash_html(messages)}
        <div class="dashboard-grid">
          <div class="panel">
            <h3>Personal profile</h3>
            <form method="post" action="/action/profile#dashboard" class="field-group">
              <label>Street address <input name="address" type="text" autocomplete="street-address" value="{html(state['profile']['address'])}"></label>
              <div class="field-grid">
                <label>Birth year <input name="birth_year" type="number" min="1900" max="2026" value="{html(state['profile']['birth_year'])}"></label>
                <label>User type
                  <select name="user_type">
                    {options([("anonymous", "Anonymous user"), ("registered", "Registered account"), ("organizer", "Registration drive organizer"), ("researcher", "Policy researcher")], state['profile'].get('user_type', 'anonymous'))}
                  </select>
                </label>
              </div>
              <label class="switch-row"><input name="citizen" type="checkbox"{" checked" if state['profile'].get('citizen') else ""}> Citizen</label>
              <label class="switch-row"><input name="resident" type="checkbox"{" checked" if state['profile'].get('resident') else ""}> Resident of this {html(jurisdiction.get('district_label', 'voting area')).lower()}</label>
              <label class="switch-row"><input name="registered" type="checkbox"{" checked" if state['profile'].get('registered') else ""}> Registration already confirmed</label>
              <button type="submit">Save profile</button>
            </form>
          </div>
          <div class="panel">
            <h3>Readiness snapshot</h3>
            <div class="metric-row">
              <div class="metric"><strong>{stats['percent']}%</strong>process complete</div>
              <div class="metric"><strong>{html(remaining)}</strong>days to next deadline</div>
              <div class="metric"><strong>{len(state.get('offline_queue', []))}</strong>queued offline actions</div>
            </div>
            <div class="progress-track" aria-label="Election process progress">
              <div class="progress-fill" style="width: {stats['percent']}%"></div>
            </div>
            <p>{html(jurisdiction['name'])}, {html(jurisdiction.get('country_name', ''))} deadlines are shown in {html(jurisdiction['timezone_label'])}. {html(tr(state, "mock"))}</p>
            <form method="post" action="/action/lookup-registration#dashboard" class="action-row">
              <button type="submit">Check registration status</button>
              <a class="button secondary" href="#guide">Generate guide</a>
            </form>
          </div>
          <figure class="visual-panel" aria-labelledby="visualTitle">
            <img src="/static/assets/civic-map.svg" alt="Map-style illustration of polling places, deadlines, and voter guide checkpoints">
            <figcaption id="visualTitle">Election tasks, deadlines, and voting options in one focused workspace.</figcaption>
          </figure>
        </div>
      </div>
    </section>
    """


def render_process(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    steps = jurisdiction["process_steps"]
    first_open = next((step["id"] for step in steps if not state.get("completed_steps", {}).get(step["id"])), "")
    cards = []
    for index, step in enumerate(steps, start=1):
        complete = bool(state.get("completed_steps", {}).get(step["id"]))
        current = step["id"] == first_open
        status = "Complete" if complete else "Current" if current else "Upcoming"
        cards.append(f"""
        <article class="panel step-card {'complete' if complete else ''} {'current' if current else ''}">
          <div class="tag-row"><span class="tag">{html(status)}</span><span class="tag">Step {index}</span><span class="tag">{html(step['estimated_time'])}</span></div>
          <h3>{html(step['title'])}</h3>
          <p>{html(step['instructions'])}</p>
          <details><summary>Required documents and contextual help</summary>
            <h4>Documents</h4>{list_html(step['documents'])}
            <h4>Common issues</h4>{list_html(step['help'])}
          </details>
          <form method="post" action="/action/step#process" class="action-row">
            <input type="hidden" name="step_id" value="{html(step['id'])}">
            <button type="submit">{'Mark incomplete' if complete else 'Mark complete'}</button>
          </form>
        </article>
        """)
    return f"""
    <section id="process" class="section-band" data-requirement="1" aria-labelledby="processTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Interactive guide</p><h2 id="processTitle">Step-by-step election process</h2></div>
        <div class="step-list">{''.join(cards)}</div>
      </div>
    </section>
    """


def render_timeline(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    items = []
    for deadline in deadlines_within_24_months(jurisdiction):
        remaining = days_until(deadline["date"])
        critical = is_critical(deadline)
        items.append(f"""
        <article class="timeline-item {'deadline-critical' if critical else ''}">
          <div><div class="timeline-date">{html(deadline['date'])}</div><span class="tag {'critical' if critical else ''}">{remaining if remaining >= 0 else abs(remaining)} days {'remaining' if remaining >= 0 else 'past'}</span></div>
          <div>
            <h3>{html(deadline['title'])}</h3>
            <p>{html(deadline['description'])}</p>
            <div class="tag-row"><span class="tag">{html(deadline['category'])}</span><span class="tag neutral">{html(deadline['source'])}</span></div>
            <a class="button secondary" href="/download/ics?id={html(deadline['id'])}">Add to calendar</a>
          </div>
        </article>
        """)
    prefs = state["notification_preferences"]
    return f"""
    <section id="timeline" class="section-band muted-band" data-requirement="2,7" aria-labelledby="timelineTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Deadlines and reminders</p><h2 id="timelineTitle">Personalized timeline</h2></div>
        <div class="two-column">
          <div class="timeline-list">{''.join(items)}</div>
          <div class="panel">
            <h3>Notification preferences</h3>
            <p>Registered users receive reminders at configured intervals. Critical deadlines also get a final 48-hour reminder notice.</p>
            <form method="post" action="/action/notifications#timeline" class="field-group">
              <label class="switch-row"><input name="enabled" type="checkbox"{" checked" if prefs.get("enabled") else ""}> Enable reminders</label>
              <div class="field-grid">
                {checkboxes("channels", ["email", "sms", "push"], prefs.get("channels", []))}
              </div>
              <div class="field-grid">
                {checkboxes("intervals", ["30", "7", "1"], [str(item) for item in prefs.get("intervals", [])])}
              </div>
              <div class="field-grid">
                {checkboxes("categories", ["deadlines", "ballot", "system"], prefs.get("categories", []))}
              </div>
              <button type="submit">Save notification preferences</button>
            </form>
            <p>Local data timestamp: {html(META['last_updated'])}. Valid official source changes refresh through the Python integration adapter.</p>
          </div>
        </div>
      </div>
    </section>
    """


def checkboxes(name: str, values: list[str], selected: list[str]) -> str:
    return "".join(
        f'<label class="switch-row"><input name="{html(name)}" value="{html(value)}" type="checkbox"{" checked" if value in selected else ""}> {html(value.title())}</label>'
        for value in values
    )


def render_registration(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    result = eligibility(state["profile"], jurisdiction)
    reg = jurisdiction["registration"]
    return f"""
    <section id="registration" class="section-band" data-requirement="3,9" aria-labelledby="registrationTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Registration tracker</p><h2 id="registrationTitle">Registration guidance and status</h2></div>
        <div class="two-column">
          <div class="panel">
            <h3>Status and methods</h3>
            <p><span class="tag {'success' if state['profile'].get('registered') else 'critical'}">{html(registration_status(state['profile'], jurisdiction))}</span></p>
            <h4>Registration methods</h4>{list_html(reg['methods'])}
            <h4>Required information</h4>{list_html(reg['required_documents'])}
            <p><strong>Processing:</strong> {html(reg['processing_time'])}</p>
            <a class="button" href="{html(jurisdiction['official']['registration_url'])}" target="_blank" rel="noreferrer">Official registration portal</a>
            <p>{html(reg['fallback'])}</p>
          </div>
          <div class="panel">
            <h3>Eligibility validation</h3>
            <p>Calculated age: <strong>{html(result['age'])}</strong></p>
            <p><span class="tag {'success' if result['eligible'] else 'critical'}">{'Eligibility criteria met' if result['eligible'] else 'Needs resolution'}</span></p>
            {list_html(result['issues']) if result['issues'] else ''}
            <p>{html(result['rule'])}</p>
            <details open><summary>Problem resolution</summary>{list_html(resolution_steps(jurisdiction))}</details>
          </div>
        </div>
      </div>
    </section>
    """


def render_voting(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    selected = selected_method(state, jurisdiction)
    rows = "".join(
        f"""
        <tr>
          <td>
            <form method="post" action="/action/method#voting">
              <input type="hidden" name="method_id" value="{html(method['id'])}">
              <button type="submit" class="secondary">{html(method['name'])}</button>
            </form>
          </td>
          <td>{html(method['deadline'])}</td>
          <td>{html(method['requirements'])}</td>
          <td>{html(method['procedure'])}</td>
          <td>{html(method['accessibility'])}</td>
        </tr>
        """
        for method in jurisdiction["voting_methods"]
    )
    tracking = selected.get("tracking", "")
    return f"""
    <section id="voting" class="section-band muted-band" data-requirement="5" aria-labelledby="votingTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Voting methods</p><h2 id="votingTitle">Compare ways to vote</h2></div>
        <div class="table-wrap"><table><caption>Voting method comparison for {html(jurisdiction['name'])}</caption>
          <thead><tr><th>Method</th><th>Deadline</th><th>Requirements</th><th>Procedure</th><th>Accessibility</th></tr></thead>
          <tbody>{rows}</tbody>
        </table></div>
        <article class="method-card">
          <h3>{html(selected['name'])}</h3>
          <p>{html(selected['procedure'])}</p>
          <p>{html(selected['requirements'])}</p>
          <p>{html(selected['accessibility'])}</p>
          {f'<p><a href="{html(jurisdiction["official"]["mail_tracking_url"])}" target="_blank" rel="noreferrer">{html(tracking)}</a></p>' if tracking else ''}
        </article>
      </div>
    </section>
    """


def render_ballot(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    ballot = jurisdiction["ballot"]
    ballot_view = dict(ballot)
    manual_candidates = state.get("manual_candidates", {}).get(ballot["district"], [])
    base_candidates = ballot["candidates"]
    if manual_candidates and all(_is_placeholder_candidate(candidate) for candidate in base_candidates):
        ballot_view["candidates"] = manual_candidates
    else:
        ballot_view["candidates"] = base_candidates + manual_candidates
    candidate_cards = "".join(
        f"""
        <article class="card">
          <h3>{html(candidate['name'])}</h3>
          <p><strong>{html(candidate['race'])}</strong> · {html(candidate['party'])}</p>
          <p>{html(candidate['statement'])}</p>
          <a href="{html(candidate['website'])}" target="_blank" rel="noreferrer">{html(candidate.get('link_label', 'Candidate website'))}</a>
          <p><span class="tag neutral">{html(candidate['source'])}</span></p>
        </article>
        """
        for candidate in ballot_view["candidates"]
    )
    comparison = comparison_rows(ballot_view)
    rows = "".join(
        "<tr><th>{}</th>{}</tr>".format(
            html(row["issue"]),
            "".join(f"<td>{html(position['position'])}</td>" for position in row["positions"]),
        )
        for row in comparison
    )
    measures = "".join(
        f"""
        <details open><summary>{html(measure['title'])}</summary>
          <p>{html(measure['summary'])}</p>
          <p><strong>Fiscal impact:</strong> {html(measure['fiscal_impact'])}</p>
          <p><strong>For:</strong> {html(measure['arguments_for'])}</p>
          <p><strong>Against:</strong> {html(measure['arguments_against'])}</p>
          <p><span class="tag neutral">{html(measure['source'])}</span></p>
        </details>
        """
        for measure in ballot["measures"]
    )
    note = state.get("research_notes", {}).get(ballot["district"], "")
    comparison_headers = "".join(f"<th>{html(candidate['name'])}</th>" for candidate in ballot_view["candidates"])
    comparison_table = (
        f'<div class="table-wrap"><table><caption>Candidate position comparison</caption><thead><tr><th>Issue</th>{comparison_headers}</tr></thead><tbody>{rows}</tbody></table></div>'
        if len(ballot_view["candidates"]) > 1 and comparison
        else '<p><strong>Candidate position comparison:</strong> Add two or more verified candidates to compare notes side by side.</p>'
    )
    return f"""
    <section id="ballot" class="section-band" data-requirement="6" aria-labelledby="ballotTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Ballot research</p><h2 id="ballotTitle">Candidates and measures</h2></div>
        <div class="two-column">
          <div>
            <div class="panel">
              <p><strong>{html(jurisdiction.get('district_label', 'District'))}:</strong> {html(ballot['district'])}</p>
              <p><strong>Coverage:</strong> {html(ballot.get('coverage_note') or _coverage_summary(jurisdiction))}</p>
              <p><strong>Verification:</strong> Use {html(jurisdiction['authority'])} or the official sample ballot source before making voting decisions.</p>
            </div>
            <div class="card-grid">{candidate_cards}</div>
            {comparison_table}
          </div>
          <div class="panel">
            <h3>Measures and research notes</h3>
            {measures}
            <form method="post" action="/action/notes#ballot" class="field-group">
              <input type="hidden" name="district" value="{html(ballot['district'])}">
              <label>Private research notes <textarea name="notes" rows="7">{html(note)}</textarea></label>
              <button type="submit">Save notes locally</button>
            </form>
            <form method="post" action="/action/add-candidate#ballot" class="field-group candidate-form">
              <input type="hidden" name="district" value="{html(ballot['district'])}">
              <div class="field-grid">
                <label>Candidate name <input name="name" type="text" required></label>
                <label>Party or affiliation <input name="party" type="text" value="Independent or local listing"></label>
              </div>
              <label>Race or office <input name="race" type="text" value="{html(ballot['district'])}"></label>
              <label>Website <input name="website" type="text" value="{html(ballot['sample_ballot_url'])}"></label>
              <label>Research note <textarea name="statement" rows="4" required></textarea></label>
              <button type="submit" class="secondary">Add candidate note</button>
            </form>
            <p><a href="{html(ballot['sample_ballot_url'])}" target="_blank" rel="noreferrer">Official sample ballot source</a></p>
          </div>
        </div>
      </div>
    </section>
    """


def render_polling(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    assigned = assigned_location(jurisdiction)
    alternatives = alternatives_within_10_miles(jurisdiction)
    location_confirmed = assigned.get("status", "confirmed") == "confirmed"
    directions_url = google_maps_directions_url(assigned["address"]) if location_confirmed else jurisdiction["official"]["elections_url"]
    embed_url = google_maps_embed_url(assigned["address"]) if location_confirmed else ""
    map_visual = (
        f'<iframe title="Google map for {html(assigned["name"])}" src="{html(embed_url)}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>'
        if location_confirmed and google_maps_embed_configured()
        else '<div class="map-canvas"><span class="map-pin" aria-hidden="true"></span><p>Use the official election authority to confirm the assigned polling location.</p></div>'
    )
    alt_cards = "".join(
        (
            f'<article class="card"><h3>{html(location["name"])}</h3><p>{html(location["distance_miles"])} miles away · {html(location["hours"])}</p><span class="tag">{html(location["wait_minutes"])} minute wait</span></article>'
            if location_confirmed
            else f'<article class="card"><h3>{html(location["name"])}</h3><p>{html(location["hours"])}</p><span class="tag">{html(location.get("source", jurisdiction["authority"]))}</span></article>'
        )
        for location in alternatives
    )
    location_details = (
        f'<div class="metric-row"><div class="metric"><strong>{html(assigned["hours"])}</strong>hours</div><div class="metric"><strong>{html(assigned["wait_minutes"])} min</strong>wait estimate</div></div>'
        if location_confirmed
        else f'<p><strong>Status:</strong> Official lookup required</p><p>{html(assigned.get("lookup_instructions", "Check the official election authority for your assigned polling location."))}</p>'
    )
    location_action = "Open Google Maps directions" if location_confirmed else "Check official authority"
    return f"""
    <section id="polling" class="section-band muted-band" data-requirement="8" aria-labelledby="pollingTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Polling finder</p><h2 id="pollingTitle">Locations, wait times, and access</h2></div>
        <div class="two-column">
          <div class="map-card" aria-label="Polling location map panel">{map_visual}<footer><strong>{html(assigned['name'])}</strong><p>{html(assigned['address'])}</p><a href="{html(directions_url)}" target="_blank" rel="noreferrer">{location_action}</a></footer></div>
          <div class="panel">
            <h3>Assigned location</h3>
            <p><strong>Coverage:</strong> {html(_coverage_summary(jurisdiction))}</p>
            {location_details}
            <p><strong>Parking:</strong> {html(assigned['parking'])}</p>
            <p><strong>Transit:</strong> {html(assigned['transit'])}</p>
            <h4>Accessibility features</h4>{tag_html(assigned['accessibility'], 'success')}
            <h4>Language assistance</h4>{tag_html(assigned['languages'], 'neutral')}
          </div>
        </div>
        <div class="card-grid">{alt_cards}</div>
      </div>
    </section>
    """


def render_eligibility_security(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    result = eligibility(state["profile"], jurisdiction)
    vault = state.get("vault", {})
    return f"""
    <section id="eligibility" class="section-band" data-requirement="9,14,15" aria-labelledby="eligibilityTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Eligibility and privacy</p><h2 id="eligibilityTitle">Verify eligibility and protect data</h2></div>
        <div class="two-column">
          <div class="panel">
            <h3>Eligibility result</h3>
            <p><span class="tag {'success' if result['eligible'] else 'critical'}">{'Eligible based on current profile' if result['eligible'] else 'Eligibility issue found'}</span></p>
            {list_html(result['issues']) if result['issues'] else ''}
            <details open><summary>Resolution guidance</summary>{list_html(resolution_steps(jurisdiction))}</details>
          </div>
          <div class="panel">
            <h3>Security and privacy controls</h3>
            <form method="post" action="/action/password#eligibility" class="field-group">
              <label>Password simulation <input name="password" type="password" autocomplete="new-password"></label>
              <p>Requires at least 12 characters with uppercase, lowercase, number, and symbol. Failed attempts are rate-limited.</p>
              <button type="submit">Validate password policy</button>
            </form>
            <form method="post" action="/action/seal-vault#eligibility" class="field-group">
              <label>Vault passphrase <input name="passphrase" type="password" autocomplete="current-password"></label>
              <button type="submit"{" disabled" if not cryptography_available() else ""}>Seal private data with cryptography/Fernet</button>
            </form>
            <form method="post" action="/action/open-vault#eligibility" class="field-group">
              <label>Open vault passphrase <input name="passphrase" type="password" autocomplete="current-password"></label>
              <button type="submit" class="secondary"{" disabled" if not vault else ""}>Open vault</button>
            </form>
            <p><span class="tag neutral">{html(vault.get('algorithm', 'Vault encryption requires optional cryptography package') if not cryptography_available() else vault.get('algorithm', 'No local vault stored'))}</span></p>
            <form method="post" action="/action/delete-account#dashboard"><button type="submit" class="warning">Delete local account data</button></form>
          </div>
        </div>
      </div>
    </section>
    """


def render_guide(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    return f"""
    <section id="guide" class="section-band muted-band" data-requirement="10,13" aria-labelledby="guideTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Document generator</p><h2 id="guideTitle">Personalized voter guide</h2></div>
        <div class="two-column">
          <div class="panel">
            <h3>Export options</h3>
            <p>The Python document generator includes registration status, deadlines, polling location, ballot summaries, checklist state, and saved notes.</p>
            <div class="action-row">
              <a class="button" href="/download/guide.html">Download HTML</a>
              <a class="button secondary" href="/download/guide.txt">Download text</a>
            </div>
            <div class="qr-tile" aria-label="QR-style official resource marker"><span>Official links</span></div>
            <p><a href="{html(jurisdiction['official']['elections_url'])}" target="_blank" rel="noreferrer">Official election resources</a></p>
            <p>Use the browser print command for the print-optimized guide layout. PWA offline access caches the app shell after first visit and keeps cached content within {html(META['cache_limit_mb'])} MB.</p>
          </div>
          <div class="guide-preview">
            <h3>Guide preview</h3>
            <p><strong>Registration:</strong> {html(registration_status(state['profile'], jurisdiction))}</p>
            <p><strong>Polling place:</strong> {html(jurisdiction['polling']['assigned']['name'])}</p>
            <p><strong>{html(jurisdiction.get('district_label', 'District'))}:</strong> {html(jurisdiction['ballot']['district'])}</p>
            <p><strong>Last generated:</strong> {html(state.get('generated_guide_at') or 'Not generated yet')}</p>
          </div>
        </div>
      </div>
    </section>
    """


def render_support(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    analysis = analyze_feedback(state)
    incident_options = [(item["id"], item["label"]) for item in INCIDENT_TYPES]
    return f"""
    <section id="support" class="section-band" data-requirement="11,12,20" aria-labelledby="supportTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Feedback and incident support</p><h2 id="supportTitle">Tell us what needs attention</h2></div>
        <div class="two-column">
          <form method="post" action="/action/feedback#support" class="panel field-group">
            <h3>Feedback collector</h3>
            <div class="field-grid"><label>Page <input name="page" type="text" value="General"></label><label>Category <select name="category">{options([("usability", "Usability issue"), ("content-error", "Content error"), ("feature-request", "Feature request"), ("process-pain-point", "Process pain point")], "usability")}</select></label></div>
            <label>Feedback <textarea name="message" rows="5" required></textarea></label>
            <label>Optional contact <input name="contact" type="email" autocomplete="email"></label>
            <button type="submit">Submit feedback</button>
          </form>
          <form method="post" action="/action/incident#support" class="panel field-group">
            <h3>Election day incident report</h3>
            <label>Issue type <select name="type">{options(incident_options, "long-wait")}</select></label>
            <label>Location <input name="location" type="text" value="{html(jurisdiction['polling']['assigned']['name'])}"></label>
            <label>Details <textarea name="details" rows="5" required></textarea></label>
            <button type="submit">Report incident</button>
          </form>
        </div>
        <div class="card-grid">
          <article class="card"><h3>Feedback trend</h3><p>{analysis['total']} submissions captured. {analysis['flagged']} flagged for review within 24 hours.</p>{tag_html([f"{key}: {value}" for key, value in analysis['category_counts'].items()], 'neutral')}</article>
          <article class="card"><h3>Incident escalation</h3><p>{analysis['incident_count']} reports. Critical reports show hotline guidance and 15-minute escalation messaging.</p><p>{html(jurisdiction['contacts']['hotline'])}</p></article>
          <article class="card"><h3>Pattern detection</h3><p>{html(analysis['patterns'] or 'No repeated-location pattern yet.')}</p></article>
        </div>
      </div>
    </section>
    """


def render_learning(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    model = learning_model(state)
    modules = "".join(
        f"""
        <article class="card">
          <h4>{html(module['title'])}</h4>
          <p>{html(module['summary'])}</p>
          <p><span class="tag">{html(module['audience'])}</span> <span class="tag neutral">{html(module['duration'])}</span></p>
          <details><summary>Caption transcript</summary><p>{html(module['transcript'])}</p></details>
          <form method="post" action="/action/complete-module#learning"><input type="hidden" name="module_id" value="{html(module['id'])}"><button type="submit" class="secondary">{'Completed' if module['id'] in model['completed'] else 'Mark complete'}</button></form>
        </article>
        """
        for module in model["modules"]
    )
    innovations = "".join(
        f'<article class="card"><h4>{html(item["title"])}</h4><p><strong>Benefits:</strong> {html(item["benefits"])}</p><p><strong>Challenges:</strong> {html(item["challenges"])}</p><p><strong>Example:</strong> {html(item["example"])}</p><p>{html(item["advocacy"])}</p></article>'
        for item in model["innovations"]
    )
    stats = model["organizer_stats"]
    return f"""
    <section id="learning" class="section-band muted-band" data-requirement="16,18,19" aria-labelledby="learningTitle">
      <div class="section-inner">
        <div class="section-heading"><p class="eyebrow">Education and organizing</p><h2 id="learningTitle">Civic learning, reform, and drive tools</h2></div>
        <div class="three-column">
          <div><h3>Educational modules</h3>{modules}</div>
          <div><h3>Voting method innovation</h3>{innovations}<article class="card"><h4>Process improvement proposals</h4>{list_html(model['process_improvements'])}</article></div>
          <div>
            <h3>Registration drive support</h3>
            <article class="card"><h4>Organizer toolkit</h4>{list_html(model['organizer_toolkit']['best_practices'])}{tag_html(model['organizer_toolkit']['materials'], 'neutral')}<a class="button secondary" href="/download/organizer-toolkit.txt">Download printable toolkit</a></article>
            <form method="post" action="/action/batch#learning" class="card field-group"><h4>Batch tracking</h4><label>Batch label <input name="label" type="text" required></label><label>Forms submitted <input name="count" type="number" min="1" value="1" required></label><button type="submit">Add batch</button></form>
            <article class="card"><h4>Aggregate stats</h4><p>{stats['registrations']} registrations tracked across {stats['batches']} batches.</p></article>
          </div>
        </div>
      </div>
    </section>
    """
