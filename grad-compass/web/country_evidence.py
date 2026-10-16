"""App-owned invented country evidence; not a producer contract or real-data handoff."""
import json
from pathlib import Path
import re

from web.discovery import overview

DECISIONS = ("Considering", "Shortlisted", "On hold", "Excluded")
# Existing bundled geometry uses -99 for these names. Reuse its established flag aliases.
ALIASES = {"France": "FRA", "Norway": "NOR", "Kosovo": "XKX", "Northern Cyprus": "CYP"}


def country_codes():
    geometry = json.loads((Path(__file__).resolve().parents[1] / "ui/data/countries.geo.json").read_text())
    codes = set()
    for feature in geometry["features"]:
        properties = feature["properties"]
        name = properties["name"]
        code = properties.get("ISO3166-1-Alpha-3", "")
        if name.lower() == "antarctica" or code == "ATA":
            continue
        codes.add(code if re.fullmatch("[A-Z]{3}", code) else ALIASES.get(name, re.sub("[^A-Z0-9]", "_", name.upper())))
    return frozenset(codes)


COUNTRY_CODES = country_codes()
SUMMARIES = {
    "CAN": "Invented scenario: sample graduate routes have been identified for further investigation. Funding and entry requirements have not been established.",
    "DEU": "Invented scenario: a sample research route is being explored. Program language, intake availability and funding require further evidence.",
    "FRA": "Invented scenario: country-level exploration has started, but no universities are saved here yet. This gap does not establish whether the country suits an applicant.",
}


def detail(workspace, exchange, code):
    if code not in COUNTRY_CODES:
        return None
    operational=getattr(workspace,"operational",False)
    supplied = code in SUMMARIES and not operational
    result = {"code": code, "synthetic": not operational, "revision": f"app-country-demo-{code}-r1" if supplied else None,
        "review_status": "unreviewed_demo" if supplied else "not_researched",
        "coverage": "partial" if supplied else "not_researched",
        "summary": SUMMARIES[code] if supplied else "No country research has been received yet. You can save this country and request research.",
        "sources": [{"source_url": f"https://example.invalid/country-demo/{code.lower()}",
                     "locator": "Invented country briefing · demonstration only", "observed_at": "2026-10-13"}] if supplied else [],
        "uncertainties": ["No real eligibility, visa, tuition or funding evidence is supplied.",
                          "Saved university counts describe coverage, not applicant suitability."],
        "decision": workspace.country_decisions().get(code, ""),
        "university_count": sum(row["country_code"] == code for row in overview(workspace, exchange)["universities"])}

    latest = workspace.research.latest_country(code)
    if latest:
        result.update({key:latest.get(key) for key in ("summary","sources","uncertainties","review_status","funding_routes","costs","work_rules","observed_at")})
        if "findings" in latest:result["findings"]=latest["findings"]
        result.update({key:latest[key] for key in ("country_record_id","record_revision","finding_id","finding_revision","review","human_approval","evidence_status","finding_ref") if key in latest})
        result.update(revision=latest["source_revision"],origin=latest["origin"],history=latest["history"],coverage="partial")
    else:
        result.update(funding_routes=None,costs=None,work_rules=None,observed_at=None,history=[])
    return result
