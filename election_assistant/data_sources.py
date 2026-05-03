"""Country-aware election data adapters.

The app uses one standard jurisdiction schema regardless of country. Adapters
can return live API data, static JSON community configs, or curated fallback
data while preserving the same shape for rendering and workflows.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from typing import Any, Protocol

from .seed_data import JURISDICTIONS as US_FALLBACKS
from .utils import ROOT, STORAGE_DIR, iso_now


COUNTRIES: dict[str, dict[str, str]] = {
    "IN": {
        "name": "India",
        "region_label": "State or union territory",
        "district_label": "Constituency or ward",
        "registration_id_label": "EPIC or voter ID reference",
        "authority": "Election Commission of India",
    },
    "US": {
        "name": "United States",
        "region_label": "State",
        "district_label": "District or precinct",
        "registration_id_label": "Registration lookup reference",
        "authority": "State and local election authorities",
    },
    "GB": {
        "name": "United Kingdom",
        "region_label": "Nation or council area",
        "district_label": "Constituency or ward",
        "registration_id_label": "Electoral register reference",
        "authority": "Electoral Commission and local councils",
    },
    "CA": {
        "name": "Canada",
        "region_label": "Province or territory",
        "district_label": "Riding",
        "registration_id_label": "Voter information reference",
        "authority": "Elections Canada and provincial agencies",
    },
    "EU": {
        "name": "European Union",
        "region_label": "Member country",
        "district_label": "Constituency or municipality",
        "registration_id_label": "Local voter register reference",
        "authority": "National electoral authorities",
    },
    "GLOBAL": {
        "name": "Other country",
        "region_label": "Region",
        "district_label": "Local voting area",
        "registration_id_label": "Local voter reference",
        "authority": "Local election authority",
    },
}


US_STATES: dict[str, str] = {
    "alabama": "Alabama",
    "alaska": "Alaska",
    "arizona": "Arizona",
    "arkansas": "Arkansas",
    "california": "California",
    "colorado": "Colorado",
    "connecticut": "Connecticut",
    "delaware": "Delaware",
    "florida": "Florida",
    "georgia": "Georgia",
    "hawaii": "Hawaii",
    "idaho": "Idaho",
    "illinois": "Illinois",
    "indiana": "Indiana",
    "iowa": "Iowa",
    "kansas": "Kansas",
    "kentucky": "Kentucky",
    "louisiana": "Louisiana",
    "maine": "Maine",
    "maryland": "Maryland",
    "massachusetts": "Massachusetts",
    "michigan": "Michigan",
    "minnesota": "Minnesota",
    "mississippi": "Mississippi",
    "missouri": "Missouri",
    "montana": "Montana",
    "nebraska": "Nebraska",
    "nevada": "Nevada",
    "new-hampshire": "New Hampshire",
    "new-jersey": "New Jersey",
    "new-mexico": "New Mexico",
    "new-york": "New York",
    "north-carolina": "North Carolina",
    "north-dakota": "North Dakota",
    "ohio": "Ohio",
    "oklahoma": "Oklahoma",
    "oregon": "Oregon",
    "pennsylvania": "Pennsylvania",
    "rhode-island": "Rhode Island",
    "south-carolina": "South Carolina",
    "south-dakota": "South Dakota",
    "tennessee": "Tennessee",
    "texas": "Texas",
    "utah": "Utah",
    "vermont": "Vermont",
    "virginia": "Virginia",
    "washington": "Washington",
    "west-virginia": "West Virginia",
    "wisconsin": "Wisconsin",
    "wyoming": "Wyoming",
}


GENERIC_STEPS = [
    {
        "id": "confirm-eligibility",
        "title": "Confirm eligibility",
        "estimated_time": "5 minutes",
        "documents": ["Age", "Citizenship or qualifying status", "Current residence"],
        "instructions": "Check the eligibility rules published by the relevant election authority.",
        "help": ["Rules vary by country and election type.", "Use official sources before taking action."],
    },
    {
        "id": "check-registration",
        "title": "Check registration or voter roll status",
        "estimated_time": "10 minutes",
        "documents": ["Name", "Address", "Local voter reference if available"],
        "instructions": "Use the official register, portal, or local election office contact route.",
        "help": ["Some countries register voters automatically.", "Others require advance registration."],
    },
    {
        "id": "choose-method",
        "title": "Choose a voting method",
        "estimated_time": "6 minutes",
        "documents": ["Polling information", "Postal or proxy voting rules", "Accessibility needs"],
        "instructions": "Compare in-person, postal, proxy, early, or absentee options where available.",
        "help": ["Available voting methods depend on the country and election type."],
    },
    {
        "id": "research-ballot",
        "title": "Review candidates and questions",
        "estimated_time": "20 minutes",
        "documents": ["Official candidate list", "Ballot sample", "Party or referendum materials"],
        "instructions": "Review official candidate, party, and referendum information.",
        "help": ["If live data is unavailable, record notes manually and verify with the authority."],
    },
    {
        "id": "vote-and-confirm",
        "title": "Vote and confirm next steps",
        "estimated_time": "10 minutes",
        "documents": ["Accepted identification", "Polling card if applicable", "Voter guide"],
        "instructions": "Cast the ballot and keep any tracking or receipt information where provided.",
        "help": ["Report access problems or intimidation immediately through official hotlines."],
    },
]

CACHE_PATH = STORAGE_DIR / "data_source_cache.sqlite3"
CACHE_VERSION = "global-election-adapters-v2"


class CountryAdapter(Protocol):
    country_code: str

    def list_regions(self) -> dict[str, str]:
        ...

    def get_jurisdiction(self, region: str) -> dict[str, Any]:
        ...

    def fetch_deadlines(self, region: str) -> list[dict[str, Any]]:
        ...

    def fetch_polling(self, region: str, address: str) -> dict[str, Any]:
        ...

    def fetch_candidates(self, region: str, address: str) -> dict[str, Any]:
        ...


def _generic_ballot(
    country_code: str,
    district: str,
    official_url: str,
    *,
    authority: str,
    district_label: str,
    coverage_note: str = "",
) -> dict[str, Any]:
    return {
        "district": district,
        "sample_ballot_url": official_url,
        "status": "manual_research_required",
        "coverage_note": coverage_note or f"Live {district_label.lower()} data is not configured for this jurisdiction.",
        "candidates": [
            {
                "id": "manual-candidate-notes",
                "race": district,
                "name": "Official candidate list",
                "party": authority,
                "website": official_url,
                "link_label": "Official candidate source",
                "statement": f"Use the official candidate list for {district} and add verified comparison notes below.",
                "issues": {
                    "Coverage": coverage_note or f"Live {district_label.lower()} candidate data is not configured for this jurisdiction.",
                    "Verification": "Use the official election authority before making voting decisions.",
                    "Notes": "Use the research notes area to record verified candidate comparisons.",
                },
                "source": f"{country_code} adapter fallback",
            }
        ],
        "measures": [
            {
                "id": "manual-measures",
                "title": "Official ballot questions and measures",
                "summary": "Check official local election authority materials for referendum, proposition, or measure text.",
                "fiscal_impact": "Record the official fiscal note or impact statement when available.",
                "arguments_for": "Record verified arguments from official materials.",
                "arguments_against": "Record verified arguments from official materials.",
                "source": f"{country_code} adapter fallback",
            }
        ],
    }


def _generic_polling(
    name: str,
    address: str,
    official_url: str,
    *,
    authority: str,
    lookup_note: str = "",
) -> dict[str, Any]:
    return {
        "assigned": {
            "name": name,
            "address": address,
            "status": "official_lookup_required",
            "hours": "Check official authority",
            "wait_minutes": "N/A",
            "parking": "Check local site information.",
            "transit": "Use map directions or local transit guidance.",
            "directions_url": official_url,
            "lookup_instructions": lookup_note or f"Use {authority} to confirm the assigned polling location for this address.",
            "accessibility": ["Check accessible entrance", "Ask for assistance options", "Confirm language support"],
            "languages": ["Check official authority for language support"],
            "source": authority,
        },
        "alternatives": [
            {
                "name": "Nearest election office",
                "distance_miles": 0,
                "hours": "Check official authority",
                "wait_minutes": "N/A",
                "status": "official_lookup_required",
                "source": authority,
            }
        ],
        "official_url": official_url,
    }


def _build_jurisdiction(
    *,
    country_code: str,
    region_id: str,
    name: str,
    timezone: str,
    official_url: str,
    registration_url: str,
    status_url: str,
    mail_tracking_url: str = "",
    registration_methods: list[str],
    required_documents: list[str],
    processing_time: str,
    fallback: str,
    residency_rule: str,
    deadlines: list[dict[str, Any]],
    ballot: dict[str, Any],
    polling: dict[str, Any],
    contacts: dict[str, str],
    process_steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    country = COUNTRIES[country_code]
    return {
        "country": country_code,
        "country_name": country["name"],
        "jurisdiction_id": region_id,
        "region_label": country["region_label"],
        "district_label": country["district_label"],
        "registration_id_label": country["registration_id_label"],
        "authority": country["authority"],
        "name": name,
        "timezone": timezone,
        "timezone_label": timezone,
        "official": {
            "elections_url": official_url,
            "registration_url": registration_url,
            "status_url": status_url,
            "mail_tracking_url": mail_tracking_url or status_url,
        },
        "registration": {
            "status": "Needs verification",
            "methods": registration_methods,
            "required_documents": required_documents,
            "processing_time": processing_time,
            "fallback": fallback,
        },
        "eligibility": {
            "min_age": 18,
            "preregister_age": 16,
            "citizenship_required": True,
            "residency_rule": residency_rule,
        },
        "deadlines": deadlines,
        "process_steps": process_steps or deepcopy(GENERIC_STEPS),
        "voting_methods": [
            {
                "id": "in-person",
                "name": "In-person voting",
                "available": True,
                "deadline": "Election day during posted polling hours",
                "requirements": "Bring any identification or polling notice required by the authority.",
                "procedure": "Visit the assigned polling location and follow local check-in rules.",
                "accessibility": "Confirm accessible entry, assistance, and language support before election day.",
            },
            {
                "id": "postal",
                "name": "Postal, proxy, or absentee voting",
                "available": True,
                "deadline": "Application and return deadlines vary by jurisdiction.",
                "requirements": "Eligibility and application rules are country-specific.",
                "procedure": "Apply through the official authority if this method is available.",
                "accessibility": "Ask the authority about remote or assisted voting options.",
            },
            {
                "id": "early",
                "name": "Advance or early voting",
                "available": True,
                "deadline": "Dates vary by election.",
                "requirements": "Confirm locations and dates with the election authority.",
                "procedure": "Use approved advance polling sites where offered.",
                "accessibility": "Check site accessibility before visiting.",
            },
        ],
        "ballot": ballot,
        "polling": polling,
        "contacts": contacts,
    }


class UnitedStatesAdapter:
    country_code = "US"

    def list_regions(self) -> dict[str, str]:
        return dict(US_STATES)

    def get_jurisdiction(self, region: str) -> dict[str, Any]:
        if region in US_FALLBACKS:
            selected = deepcopy(US_FALLBACKS[region])
            selected["country"] = "US"
            selected["country_name"] = "United States"
            selected["jurisdiction_id"] = region
            selected["region_label"] = "State"
            selected["district_label"] = "District or precinct"
            selected["registration_id_label"] = "Registration lookup reference"
            selected["authority"] = "State and local election authorities"
            return selected

        region = region if region in US_STATES else "california"
        name = US_STATES[region]
        official_url = "https://www.vote.gov/"
        return _build_jurisdiction(
            country_code="US",
            region_id=region,
            name=name,
            timezone="US local time",
            official_url=official_url,
            registration_url=official_url,
            status_url="https://www.usa.gov/confirm-voter-registration",
            mail_tracking_url=official_url,
            registration_methods=[
                "Use Vote.gov to reach the state registration portal",
                "Contact the state or local election office",
                "Check mail, in-person, and online options by state",
            ],
            required_documents=[
                "Name",
                "Residential address",
                "Date of birth",
                "State ID, driver license, or allowed alternative where required",
            ],
            processing_time="Varies by state and registration method",
            fallback="Use Vote.gov or the state election office for verified deadlines and procedures.",
            residency_rule="Must meet United States citizenship, age, and state residency requirements for the selected election.",
            deadlines=[
                {
                    "id": f"{region}-registration-check",
                    "title": "Confirm state registration deadline",
                    "date": "2026-10-05T17:00:00-05:00",
                    "category": "Registration",
                    "critical": True,
                    "description": "State-specific deadlines vary. Confirm current dates through the official state election office.",
                    "source": "US generic adapter",
                },
                {
                    "id": f"{region}-mail-ballot-check",
                    "title": "Confirm mail or absentee ballot deadlines",
                    "date": "2026-10-20T17:00:00-05:00",
                    "category": "Voting method",
                    "critical": False,
                    "description": "Request, return, witness, and ID rules vary by state.",
                    "source": "US generic adapter",
                },
                {
                    "id": f"{region}-early-vote-check",
                    "title": "Check early voting or drop box availability",
                    "date": "2026-10-27T17:00:00-05:00",
                    "category": "Early voting",
                    "critical": False,
                    "description": "Availability depends on state law and local election office plans.",
                    "source": "US generic adapter",
                },
                {
                    "id": f"{region}-election-day",
                    "title": "Election day planning target",
                    "date": "2026-11-03T19:00:00-05:00",
                    "category": "Election day",
                    "critical": True,
                    "description": "Confirm polling location, hours, identification rules, and ballot status before election day.",
                    "source": "US generic adapter",
                },
            ],
            ballot=_generic_ballot(
                "US",
                f"{name} district or precinct",
                official_url,
                authority=COUNTRIES["US"]["authority"],
                district_label=COUNTRIES["US"]["district_label"],
                coverage_note=f"Generic {name} coverage includes state-level guidance only. Local district, precinct, and measure details require the state or county election office.",
            ),
            polling=_generic_polling(
                "Assigned polling location lookup",
                f"{name}, United States",
                official_url,
                authority=COUNTRIES["US"]["authority"],
                lookup_note=f"The generic {name} adapter does not include polling-place assignments. Use the state or county lookup with your registered address.",
            ),
            contacts={
                "official": f"{name} election office",
                "hotline": "Election Protection hotline: 866-OUR-VOTE",
                "rights_restoration": "Check state-specific eligibility and rights restoration guidance.",
            },
        )

    def fetch_deadlines(self, region: str) -> list[dict[str, Any]]:
        return self.get_jurisdiction(region)["deadlines"]

    def fetch_polling(self, region: str, address: str) -> dict[str, Any]:
        return self.get_jurisdiction(region)["polling"]["assigned"]

    def fetch_candidates(self, region: str, address: str) -> dict[str, Any]:
        return self.get_jurisdiction(region)["ballot"]


class IndiaAdapter:
    country_code = "IN"
    # All 28 states + 8 union territories with assembly seat counts and Lok Sabha seats
    regions: dict[str, dict[str, Any]] = {
        "andhra-pradesh": {"name": "Andhra Pradesh", "assembly_seats": 175, "lok_sabha_seats": 25, "ceo_url": "https://ceoandhra.nic.in"},
        "arunachal-pradesh": {"name": "Arunachal Pradesh", "assembly_seats": 60, "lok_sabha_seats": 2, "ceo_url": "https://ceoarunachal.nic.in"},
        "assam": {"name": "Assam", "assembly_seats": 126, "lok_sabha_seats": 14, "ceo_url": "https://ceoassam.nic.in"},
        "bihar": {"name": "Bihar", "assembly_seats": 243, "lok_sabha_seats": 40, "ceo_url": "https://ceobihar.nic.in"},
        "chhattisgarh": {"name": "Chhattisgarh", "assembly_seats": 90, "lok_sabha_seats": 11, "ceo_url": "https://ceochhattisgarh.nic.in"},
        "goa": {"name": "Goa", "assembly_seats": 40, "lok_sabha_seats": 2, "ceo_url": "https://ceogoa.nic.in"},
        "gujarat": {"name": "Gujarat", "assembly_seats": 182, "lok_sabha_seats": 26, "ceo_url": "https://ceo.gujarat.gov.in"},
        "haryana": {"name": "Haryana", "assembly_seats": 90, "lok_sabha_seats": 10, "ceo_url": "https://ceoharyana.gov.in"},
        "himachal-pradesh": {"name": "Himachal Pradesh", "assembly_seats": 68, "lok_sabha_seats": 4, "ceo_url": "https://ceohimachal.nic.in"},
        "jharkhand": {"name": "Jharkhand", "assembly_seats": 81, "lok_sabha_seats": 14, "ceo_url": "https://jharkhand.gov.in/ceo"},
        "karnataka": {"name": "Karnataka", "assembly_seats": 224, "lok_sabha_seats": 28, "ceo_url": "https://ceo.karnataka.gov.in"},
        "kerala": {"name": "Kerala", "assembly_seats": 140, "lok_sabha_seats": 20, "ceo_url": "https://www.ceo.kerala.gov.in"},
        "madhya-pradesh": {"name": "Madhya Pradesh", "assembly_seats": 230, "lok_sabha_seats": 29, "ceo_url": "https://ceomadhyapradesh.nic.in"},
        "maharashtra": {"name": "Maharashtra", "assembly_seats": 288, "lok_sabha_seats": 48, "ceo_url": "https://ceo.maharashtra.gov.in"},
        "manipur": {"name": "Manipur", "assembly_seats": 60, "lok_sabha_seats": 2, "ceo_url": "https://ceomanipur.nic.in"},
        "meghalaya": {"name": "Meghalaya", "assembly_seats": 60, "lok_sabha_seats": 2, "ceo_url": "https://ceomeghalaya.nic.in"},
        "mizoram": {"name": "Mizoram", "assembly_seats": 40, "lok_sabha_seats": 1, "ceo_url": "https://ceomizoram.nic.in"},
        "nagaland": {"name": "Nagaland", "assembly_seats": 60, "lok_sabha_seats": 1, "ceo_url": "https://ceonagaland.nic.in"},
        "odisha": {"name": "Odisha", "assembly_seats": 147, "lok_sabha_seats": 21, "ceo_url": "https://ceoodisha.nic.in"},
        "punjab": {"name": "Punjab", "assembly_seats": 117, "lok_sabha_seats": 13, "ceo_url": "https://ceopunjab.nic.in"},
        "rajasthan": {"name": "Rajasthan", "assembly_seats": 200, "lok_sabha_seats": 25, "ceo_url": "https://ceorajasthan.nic.in"},
        "sikkim": {"name": "Sikkim", "assembly_seats": 32, "lok_sabha_seats": 1, "ceo_url": "https://ceosikkim.nic.in"},
        "tamil-nadu": {"name": "Tamil Nadu", "assembly_seats": 234, "lok_sabha_seats": 39, "ceo_url": "https://www.elections.tn.gov.in"},
        "telangana": {"name": "Telangana", "assembly_seats": 119, "lok_sabha_seats": 17, "ceo_url": "https://ceotelangana.nic.in"},
        "tripura": {"name": "Tripura", "assembly_seats": 60, "lok_sabha_seats": 2, "ceo_url": "https://ceotripura.nic.in"},
        "uttar-pradesh": {"name": "Uttar Pradesh", "assembly_seats": 403, "lok_sabha_seats": 80, "ceo_url": "https://ceouttarpradesh.nic.in"},
        "uttarakhand": {"name": "Uttarakhand", "assembly_seats": 70, "lok_sabha_seats": 5, "ceo_url": "https://ceouttarakhand.nic.in"},
        "west-bengal": {"name": "West Bengal", "assembly_seats": 294, "lok_sabha_seats": 42, "ceo_url": "https://ceowestbengal.nic.in"},
        # Union Territories
        "andaman-nicobar": {"name": "Andaman & Nicobar Islands", "assembly_seats": 0, "lok_sabha_seats": 1, "ceo_url": "https://www.andaman.gov.in", "is_ut": True},
        "chandigarh": {"name": "Chandigarh", "assembly_seats": 0, "lok_sabha_seats": 1, "ceo_url": "https://ceochandigarh.gov.in", "is_ut": True},
        "dadra-nagar-haveli-daman-diu": {"name": "Dadra & Nagar Haveli and Daman & Diu", "assembly_seats": 0, "lok_sabha_seats": 2, "ceo_url": "https://daman.nic.in", "is_ut": True},
        "delhi": {"name": "Delhi (NCT)", "assembly_seats": 70, "lok_sabha_seats": 7, "ceo_url": "https://ceodelhi.gov.in", "is_ut": True},
        "jammu-kashmir": {"name": "Jammu & Kashmir", "assembly_seats": 90, "lok_sabha_seats": 5, "ceo_url": "https://ceojk.nic.in", "is_ut": True},
        "ladakh": {"name": "Ladakh", "assembly_seats": 0, "lok_sabha_seats": 1, "ceo_url": "https://ladakh.nic.in", "is_ut": True},
        "lakshadweep": {"name": "Lakshadweep", "assembly_seats": 0, "lok_sabha_seats": 1, "ceo_url": "https://lakshadweep.gov.in", "is_ut": True},
        "puducherry": {"name": "Puducherry", "assembly_seats": 30, "lok_sabha_seats": 1, "ceo_url": "https://ceopuducherry.py.gov.in", "is_ut": True},
    }

    def list_regions(self) -> dict[str, str]:
        return {key: info["name"] for key, info in self.regions.items()}

    def get_jurisdiction(self, region: str) -> dict[str, Any]:
        if region not in self.regions:
            region = "tamil-nadu"
        info = self.regions[region]
        name = info["name"]
        ceo_url = info["ceo_url"]
        assembly_seats = info["assembly_seats"]
        lok_sabha_seats = info["lok_sabha_seats"]
        is_ut = info.get("is_ut", False)

        # Build India-specific process steps with real data
        process_steps = [
            {
                "id": "confirm-eligibility",
                "title": "Confirm eligibility",
                "estimated_time": "5 minutes",
                "documents": ["Proof of age (18+)", "Proof of Indian citizenship", f"Proof of ordinary residence in {name}"],
                "instructions": f"You must be an Indian citizen, 18 years or older, and ordinarily resident in a constituency of {name}.",
                "help": [
                    f"{name} has {assembly_seats} assembly constituencies and {lok_sabha_seats} Lok Sabha seats." if assembly_seats else f"{name} has {lok_sabha_seats} Lok Sabha seat(s). No state assembly.",
                    "NRIs can register as overseas electors under Form 6A.",
                ],
            },
            {
                "id": "check-registration",
                "title": "Check voter roll status (EPIC)",
                "estimated_time": "10 minutes",
                "documents": ["EPIC number (voter ID)", "Name and father's/mother's name", "Date of birth"],
                "instructions": "Search the electoral roll on the ECI voter portal or the CEO website.",
                "help": [
                    f"Search at: {ceo_url}",
                    "Use Form 6 for new registration, Form 8 for corrections.",
                    "Contact your local Booth Level Officer (BLO) for assistance.",
                ],
            },
            {
                "id": "choose-method",
                "title": "Understand voting method",
                "estimated_time": "3 minutes",
                "documents": ["EPIC or accepted photo ID", "Polling booth slip (optional)"],
                "instructions": "India uses in-person EVM voting at assigned polling booths. No postal voting for general voters.",
                "help": [
                    "Postal ballot is available for service voters, senior citizens 85+, and PwD voters.",
                    "VVPAT machines provide a paper audit trail.",
                ],
            },
            {
                "id": "research-ballot",
                "title": "Research candidates and parties",
                "estimated_time": "20 minutes",
                "documents": [f"Candidate list from {ceo_url}", "Affidavit disclosures on ECI website", "Party manifestos"],
                "instructions": "Review candidate affidavits (assets, criminal cases, education) published by the Election Commission.",
                "help": [
                    "Candidate affidavits are public records on the ECI website.",
                    "Use the NOTA option if you wish to reject all candidates.",
                ],
            },
            {
                "id": "vote-and-confirm",
                "title": "Vote on polling day",
                "estimated_time": "Variable",
                "documents": ["EPIC or any of 12 accepted photo IDs", "Polling booth slip"],
                "instructions": f"Visit your assigned polling booth in {name}. Polling hours are typically 7:00 AM to 6:00 PM.",
                "help": [
                    "Indelible ink is applied to your left index finger after voting.",
                    "Report any issue to the presiding officer or call 1950.",
                ],
            },
        ]

        # State-specific deadlines
        deadlines = [
            {
                "id": f"{region}-roll-revision",
                "title": f"Electoral roll revision — {name}",
                "date": "2026-09-30T17:00:00+05:30",
                "category": "Registration",
                "critical": True,
                "description": f"Verify your name in the {name} electoral roll. File Form 6 for inclusion or Form 8 for corrections.",
                "source": f"{name} CEO office schedule",
            },
            {
                "id": f"{region}-nomination",
                "title": "Candidate nomination period",
                "date": "2026-10-15T15:00:00+05:30",
                "category": "Candidate list",
                "critical": False,
                "description": f"Nomination filing, scrutiny, and withdrawal dates for {name} elections as per ECI notification.",
                "source": f"{name} CEO office schedule",
            },
            {
                "id": f"{region}-polling-day",
                "title": f"Polling day — {name}",
                "date": "2026-11-10T18:00:00+05:30",
                "category": "Polling",
                "critical": True,
                "description": f"Confirm your polling booth, carry accepted ID, and vote during polling hours in {name}.",
                "source": f"{name} CEO office schedule",
            },
            {
                "id": f"{region}-counting",
                "title": "Counting and results",
                "date": "2026-11-14T10:00:00+05:30",
                "category": "Results",
                "critical": False,
                "description": "EVM counting at designated centres. Results published on ECI website.",
                "source": "Election Commission of India",
            },
        ]

        # Type label
        region_type = "Union Territory" if is_ut else "State"

        ballot_district = f"{name} assembly constituency" if assembly_seats else f"{name} Lok Sabha constituency"
        seat_note = (
            f"{name} includes {assembly_seats} assembly constituencies and {lok_sabha_seats} Lok Sabha seats. Local body ward data is not configured in this adapter."
            if assembly_seats
            else f"{name} includes {lok_sabha_seats} Lok Sabha seat(s). State assembly or local ward data is not configured in this adapter."
        )
        ballot = _generic_ballot(
            "IN",
            ballot_district,
            ceo_url,
            authority="Election Commission of India and state CEO offices",
            district_label=COUNTRIES["IN"]["district_label"],
            coverage_note=seat_note,
        )
        # Add India-specific candidate entry form fields
        ballot["candidate_entry_fields"] = ["Candidate name", "Party or affiliation", "Race or office", "Website", "Research note"]

        return _build_jurisdiction(
            country_code="IN",
            region_id=region,
            name=name,
            timezone="Asia/Kolkata",
            official_url=ceo_url,
            registration_url="https://voters.eci.gov.in",
            status_url="https://electoralsearch.eci.gov.in",
            registration_methods=[
                "Online via National Voters' Service Portal (NVSP)",
                "Form 6 — new voter registration",
                "Form 8 — correction of entries",
                "Form 6A — overseas elector registration",
                "Booth Level Officer (BLO) door-to-door verification",
            ],
            required_documents=[
                "Proof of age (birth certificate, school certificate, passport)",
                f"Proof of ordinary residence in {name}",
                "Passport-size photograph",
                "EPIC number (if updating existing record)",
            ],
            processing_time="Processed during electoral roll revision cycles (typically January and July)",
            fallback=f"Contact the {name} CEO office or your local Electoral Registration Officer (ERO).",
            residency_rule=f"Must be an Indian citizen, 18 years or older, and ordinarily resident in a constituency of {name}.",
            deadlines=deadlines,
            process_steps=process_steps,
            ballot=ballot,
            polling=_generic_polling(
                "Assigned polling booth lookup",
                f"{name}, India",
                ceo_url,
                authority=f"{name} Chief Electoral Officer",
                lookup_note=f"Use the {name} CEO website, voter slip, or helpline 1950 to confirm the assigned polling booth for your enrolled address.",
            ),
            contacts={
                "official": f"{name} Chief Electoral Officer ({region_type})",
                "hotline": "National Election Helpline: 1950",
                "rights_restoration": f"Confirm eligibility through {name} CEO office or ECI portal.",
                "assembly_seats": str(assembly_seats),
                "lok_sabha_seats": str(lok_sabha_seats),
                "region_type": region_type,
            },
        )

    def fetch_deadlines(self, region: str) -> list[dict[str, Any]]:
        return self.get_jurisdiction(region)["deadlines"]

    def fetch_polling(self, region: str, address: str) -> dict[str, Any]:
        j = self.get_jurisdiction(region)
        assigned = dict(j["polling"]["assigned"])
        if address:
            from .integrations import google_maps_directions_url
            assigned["address"] = address
            assigned["directions_url"] = google_maps_directions_url(address)
        return assigned

    def fetch_candidates(self, region: str, address: str) -> dict[str, Any]:
        return self.get_jurisdiction(region)["ballot"]


class GenericCountryAdapter:
    def __init__(self, country_code: str) -> None:
        self.country_code = country_code

    def list_regions(self) -> dict[str, str]:
        config = _load_country_config(self.country_code)
        if config:
            return {key: value["name"] for key, value in config.get("regions", {}).items()}
        return {"national": COUNTRIES.get(self.country_code, COUNTRIES["GLOBAL"])["name"]}

    def get_jurisdiction(self, region: str) -> dict[str, Any]:
        config = _load_country_config(self.country_code)
        if config and region in config.get("regions", {}):
            return _from_config(self.country_code, region, config["regions"][region])
        country = COUNTRIES.get(self.country_code, COUNTRIES["GLOBAL"])
        region_name = self.list_regions().get(region, country["name"])
        official_url = "https://www.google.com/search?q=official+election+authority"
        return _build_jurisdiction(
            country_code=self.country_code if self.country_code in COUNTRIES else "GLOBAL",
            region_id=region or "national",
            name=region_name,
            timezone="UTC",
            official_url=official_url,
            registration_url=official_url,
            status_url=official_url,
            registration_methods=["Check the official election authority", "Contact the local registration office"],
            required_documents=["Age proof", "Residence proof", "Local identity document if required"],
            processing_time="Varies by jurisdiction",
            fallback="Use the official election authority for verified instructions.",
            residency_rule="Eligibility depends on the country, election type, citizenship status, and residence rules.",
            deadlines=[
                {
                    "id": f"{region or 'national'}-verify",
                    "title": "Verify official election dates",
                    "date": "2026-12-31T17:00:00+00:00",
                    "category": "Verification",
                    "critical": False,
                    "description": "No live adapter is configured. Confirm current dates with the official authority.",
                    "source": "Generic adapter",
                }
            ],
            ballot=_generic_ballot(
                country["name"],
                f"{region_name} voting area",
                official_url,
                authority=country["authority"],
                district_label=country["district_label"],
                coverage_note=f"{country['name']} fallback coverage is limited to high-level registration and voting guidance for {region_name}.",
            ),
            polling=_generic_polling(
                "Official polling place lookup",
                region_name,
                official_url,
                authority=country["authority"],
                lookup_note=f"Use the official election authority for {region_name} to confirm the assigned polling location and access details.",
            ),
            contacts={
                "official": f"{country['authority']}",
                "hotline": "Check official voter assistance contacts",
                "rights_restoration": "Check local law and official eligibility guidance.",
            },
        )

    def fetch_deadlines(self, region: str) -> list[dict[str, Any]]:
        return self.get_jurisdiction(region)["deadlines"]

    def fetch_polling(self, region: str, address: str) -> dict[str, Any]:
        return self.get_jurisdiction(region)["polling"]["assigned"]

    def fetch_candidates(self, region: str, address: str) -> dict[str, Any]:
        return self.get_jurisdiction(region)["ballot"]


ADAPTERS: dict[str, CountryAdapter] = {
    "US": UnitedStatesAdapter(),
    "IN": IndiaAdapter(),
    "GB": GenericCountryAdapter("GB"),
    "CA": GenericCountryAdapter("CA"),
    "EU": GenericCountryAdapter("EU"),
    "GLOBAL": GenericCountryAdapter("GLOBAL"),
}


def _load_country_config(country_code: str) -> dict[str, Any]:
    path = ROOT / "data" / "countries" / f"{country_code.lower()}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _connect_cache() -> sqlite3.Connection:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CACHE_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS jurisdiction_cache (
            country_code TEXT NOT NULL,
            region_id TEXT NOT NULL,
            version TEXT NOT NULL,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (country_code, region_id, version)
        )
        """
    )
    return connection


def _cache_get(country_code: str, region_id: str) -> dict[str, Any] | None:
    with _connect_cache() as connection:
        row = connection.execute(
            """
            SELECT payload
            FROM jurisdiction_cache
            WHERE country_code = ? AND region_id = ? AND version = ?
            """,
            (country_code, region_id, CACHE_VERSION),
        ).fetchone()
    return json.loads(row[0]) if row else None


def _cache_set(country_code: str, region_id: str, payload: dict[str, Any]) -> None:
    with _connect_cache() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO jurisdiction_cache (country_code, region_id, version, payload, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (country_code, region_id, CACHE_VERSION, json.dumps(payload, sort_keys=True), iso_now()),
        )


def _from_config(country_code: str, region: str, config: dict[str, Any]) -> dict[str, Any]:
    country = COUNTRIES.get(country_code, COUNTRIES["GLOBAL"])
    official_url = config.get("official_url", "https://www.google.com/search?q=official+election+authority")
    return _build_jurisdiction(
        country_code=country_code if country_code in COUNTRIES else "GLOBAL",
        region_id=region,
        name=config.get("name", country["name"]),
        timezone=config.get("timezone", "UTC"),
        official_url=official_url,
        registration_url=config.get("registration_url", official_url),
        status_url=config.get("status_url", official_url),
        registration_methods=config.get("registration", {}).get("methods", ["Check official registration guidance"]),
        required_documents=config.get("registration", {}).get("required_documents", ["Check official source"]),
        processing_time=config.get("registration", {}).get("processing_time", "Varies"),
        fallback=config.get("registration", {}).get("fallback", "Contact the official election authority."),
        residency_rule=config.get("eligibility", {}).get("residency_rule", "Check official eligibility rules."),
        deadlines=config.get("deadlines", []),
        ballot=config.get(
            "ballot",
            _generic_ballot(
                country_code,
                config.get("name", region),
                official_url,
                authority=country["authority"],
                district_label=country["district_label"],
                coverage_note=f"{config.get('name', region)} uses configured fallback guidance until a live ballot feed is connected.",
            ),
        ),
        polling=config.get(
            "polling",
            _generic_polling(
                "Official polling place lookup",
                config.get("name", region),
                official_url,
                authority=country["authority"],
                lookup_note=f"Use the official authority for {config.get('name', region)} to confirm polling location, hours, and access details.",
            ),
        ),
        contacts=config.get(
            "contacts",
            {
                "official": country["authority"],
                "hotline": "Check official voter assistance contacts",
                "rights_restoration": "Check official eligibility guidance.",
            },
        ),
    )


def get_country_adapter(country_code: str) -> CountryAdapter:
    return ADAPTERS.get(country_code, ADAPTERS["GLOBAL"])


def list_countries() -> list[tuple[str, str]]:
    return [(code, details["name"]) for code, details in COUNTRIES.items()]


def list_regions(country_code: str) -> dict[str, str]:
    return get_country_adapter(country_code).list_regions()


def default_region(country_code: str) -> str:
    regions = list_regions(country_code)
    return next(iter(regions), "national")


def get_jurisdiction(country_code: str, region: str) -> dict[str, Any]:
    adapter = get_country_adapter(country_code)
    cache_country = country_code if country_code in COUNTRIES else "GLOBAL"
    cache_region = region or default_region(cache_country)
    cached = _cache_get(cache_country, cache_region)
    if cached:
        return cached
    jurisdiction = adapter.get_jurisdiction(cache_region)
    _cache_set(cache_country, jurisdiction.get("jurisdiction_id", cache_region), jurisdiction)
    return jurisdiction
