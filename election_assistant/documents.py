"""Voter guide and printable document generation."""

from __future__ import annotations

from typing import Any

from .registration import eligibility, registration_status
from .timeline import deadlines_within_24_months
from .utils import html, iso_now


def guide_model(state: dict[str, Any], jurisdiction: dict[str, Any]) -> dict[str, Any]:
    generated_at = iso_now()
    state["generated_guide_at"] = generated_at
    ballot = jurisdiction["ballot"]
    return {
        "generated_at": generated_at,
        "jurisdiction": jurisdiction,
        "profile": state["profile"],
        "eligibility": eligibility(state["profile"], jurisdiction),
        "registration_status": registration_status(state["profile"], jurisdiction),
        "deadlines": deadlines_within_24_months(jurisdiction),
        "polling": jurisdiction["polling"]["assigned"],
        "ballot": ballot,
        "notes": state.get("research_notes", {}).get(ballot["district"], ""),
        "completed_steps": state.get("completed_steps", {}),
    }


def guide_html(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    model = guide_model(state, jurisdiction)
    steps = jurisdiction["process_steps"]
    candidates = model["ballot"]["candidates"]
    measures = model["ballot"]["measures"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Personalized Voter Guide</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #102326; line-height: 1.5; }}
    h1, h2 {{ color: #12343b; }}
    .box {{ border: 1px solid #d9e2df; padding: 12px; margin: 12px 0; }}
    @media print {{ .box {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <h1>Personalized voter guide</h1>
  <p><strong>Generated:</strong> {html(model["generated_at"])}</p>
  <div class="box">
    <h2>Readiness</h2>
    <p><strong>Jurisdiction:</strong> {html(jurisdiction["name"])}</p>
    <p><strong>Registration:</strong> {html(model["registration_status"])}</p>
    <p><strong>Eligibility:</strong> {"Meets current criteria" if model["eligibility"]["eligible"] else "Needs resolution"}</p>
  </div>
  <div class="box">
    <h2>Checklist</h2>
    <ul>
      {"".join(f"<li>{'[x]' if model['completed_steps'].get(step['id']) else '[ ]'} {html(step['title'])}</li>" for step in steps)}
    </ul>
  </div>
  <div class="box">
    <h2>Deadlines</h2>
    <ul>
      {"".join(f"<li>{html(deadline['title'])}: {html(deadline['date'])}</li>" for deadline in model["deadlines"])}
    </ul>
  </div>
  <div class="box">
    <h2>Polling location</h2>
    <p>{html(model["polling"]["name"])} · {html(model["polling"]["address"])} · {html(model["polling"]["hours"])}</p>
  </div>
  <div class="box">
    <h2>Ballot summary</h2>
    <ul>
      {"".join(f"<li>{html(candidate['race'])}: {html(candidate['name'])} ({html(candidate['party'])})</li>" for candidate in candidates)}
      {"".join(f"<li>{html(measure['title'])}: {html(measure['summary'])}</li>" for measure in measures)}
    </ul>
  </div>
  <div class="box">
    <h2>Saved notes</h2>
    <p>{html(model["notes"] or "No private notes saved.")}</p>
  </div>
  <div class="box">
    <h2>Official resources</h2>
    <p>{html(jurisdiction["official"]["elections_url"])}</p>
    <p>{html(jurisdiction["contacts"]["official"])} · {html(jurisdiction["contacts"]["hotline"])}</p>
  </div>
</body>
</html>"""


def guide_text(state: dict[str, Any], jurisdiction: dict[str, Any]) -> str:
    model = guide_model(state, jurisdiction)
    lines = [
        "Personalized voter guide",
        f"Generated: {model['generated_at']}",
        f"Jurisdiction: {jurisdiction['name']}",
        f"Registration: {model['registration_status']}",
        f"Eligibility: {'Meets current criteria' if model['eligibility']['eligible'] else 'Needs resolution'}",
        "",
        "Checklist:",
    ]
    for step in jurisdiction["process_steps"]:
        lines.append(f"{'[x]' if model['completed_steps'].get(step['id']) else '[ ]'} {step['title']}")
    lines.append("")
    lines.append("Deadlines:")
    for deadline in model["deadlines"]:
        lines.append(f"- {deadline['title']}: {deadline['date']}")
    lines.extend(
        [
            "",
            "Polling location:",
            f"{model['polling']['name']} - {model['polling']['address']} - {model['polling']['hours']}",
            "",
            "Ballot summary:",
        ]
    )
    for candidate in model["ballot"]["candidates"]:
        lines.append(f"- {candidate['race']}: {candidate['name']} ({candidate['party']})")
    for measure in model["ballot"]["measures"]:
        lines.append(f"- {measure['title']}: {measure['summary']}")
    lines.extend(["", "Saved notes:", model["notes"] or "No private notes saved.", "", "Contacts:", jurisdiction["contacts"]["official"], jurisdiction["contacts"]["hotline"]])
    return "\n".join(lines)


def organizer_toolkit_text(jurisdiction: dict[str, Any], toolkit: dict[str, Any]) -> str:
    lines = [
        "Election Process Assistant - Registration Drive Toolkit",
        f"Jurisdiction: {jurisdiction['name']}",
        "",
        "Best practices:",
        *[f"- {item}" for item in toolkit["best_practices"]],
        "",
        "Legal requirements:",
        *[f"- {item}" for item in toolkit["legal_requirements"]],
        "",
        "Printable materials:",
        *[f"- {item}" for item in toolkit["materials"]],
        "",
        f"Official registration portal: {jurisdiction['official']['registration_url']}",
    ]
    return "\n".join(lines)
