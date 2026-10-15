"""Provisional app-only synthetic envelopes, independently versioned from exchange v1."""
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID, uuid5, NAMESPACE_URL

from web.country_evidence import COUNTRY_CODES
from web.exchange_workflow import BATCH_ID, FIXTURE_DIGEST

PRIVATE_VERSION = "0.1.0"
COUNTRY_VERSION = "0.1.0"
PREFERENCE_FIELDS = ("intake", "intake_alternatives", "degree_routes", "instruction_language",
                     "country_restrictions", "funding_priorities", "research_limits")
SCOPES = {"country_conditions": "Update country conditions", "universities_programs": "Find universities and programs",
          "refresh": "Refresh or follow up"}
NORTH = "11111111-1111-4111-8111-111111111111"
PROGRAM = "33333333-3333-4333-8333-333333333333"


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(compact(value).encode()).hexdigest()


def seal(value):
    return {**value, "digest": digest(value)}


def verify(value):
    if not isinstance(value, dict) or value.get("digest") != digest({key:item for key,item in value.items() if key != "digest"}):
        raise ValueError("The envelope's saved contents no longer match its digest")
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Choose an existing research item") from None
    return value


def text(value, maximum=2000):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Keep the research text within the displayed limit")
    return value.strip() or None


def request_values(payload):
    allowed = {"submission_key", "countries", "scope", "preferences", "remember_preferences", "limits", "context", "parent_request_id", "prior_results"}
    if not isinstance(payload, dict) or set(payload)-allowed:
        raise ValueError("Review the research request fields")
    identifier(payload.get("submission_key"))
    countries = payload.get("countries")
    if (not isinstance(countries, list) or not 1 <= len(countries) <= 20
        or any(not isinstance(code, str) or code not in COUNTRY_CODES for code in countries)
        or len(set(countries)) != len(countries)):
        raise ValueError("Select between 1 and 20 distinct countries for this request")
    if not isinstance(payload.get("scope"), str) or payload["scope"] not in SCOPES:
        raise ValueError("Choose a research scope")
    preferences = payload.get("preferences")
    if not isinstance(preferences, dict) or set(preferences)-set(PREFERENCE_FIELDS) or type(payload.get("remember_preferences")) is not bool:
        raise ValueError("Review your explicit shared preferences")
    preferences = {key:text(preferences.get(key),1200) for key in PREFERENCE_FIELDS}
    parent = payload.get("parent_request_id")
    if parent is not None: identifier(parent)
    references = payload.get("prior_results", [])
    if not isinstance(references, list) or len(references)>20 or any(not isinstance(ref,dict) or set(ref)!={"result_id","revision","digest","finding_id"} for ref in references):
        raise ValueError("Select a saved result or finding for the follow-up")
    if payload["scope"] == "refresh" and not parent:
        raise ValueError("Choose the previous request for this follow-up")
    return {"countries": countries, "scope":payload["scope"], "preferences":preferences,
            "limits":text(payload.get("limits")), "context":text(payload.get("context"),4000),
            "parent_request_id":parent, "prior_results":references}


def demo_response(request, choice):
    """Deterministic invented input bound to a local immutable request, never real facts."""
    binding = {"request_id":request["request_id"], "request_revision":request["revision"], "request_digest":request["digest"]}
    base = {"private_schema_version":PRIVATE_VERSION, "synthetic":True, "created_at":request["created_at"], **binding}
    if choice in ("accepted", "rejected", "needs_clarification"):
        return seal({**base, "envelope_kind":"acknowledgement", "ack_id":str(uuid5(NAMESPACE_URL,request["request_id"]+":ack")),
                     "state":choice, "execution_progress":None})
    if choice not in ("result-1", "result-2"):
        raise ValueError("Choose an app-owned synthetic response")
    revision = int(choice[-1])
    findings = []
    for code in request["countries"]:
        findings.append({"finding_id":"country:"+code, "kind":"country", "country_code":code,
            "country_schema_version":COUNTRY_VERSION, "source_revision":f"demo-{code}-r{revision}",
            "review_status":"unreviewed_demo", "summary":f"Invented {code} research scenario. Routes need checking against a real applicant's requirements.",
            "funding_routes":"Invented route A: a sample studentship to investigate." if revision==1 else "Invented route B replaces route A; eligibility remains unverified.",
            "costs":"No real cost estimate supplied." if revision==1 else "A revised invented cost scenario is available; actual fees and living costs remain unknown.",
            "work_rules":None, "observed_at":"2026-10-14" if revision==1 else "2026-10-15",
            "sources":[{"source_url":f"https://example.invalid/research/{code.lower()}/revision-{revision}","locator":"Invented country evidence — not an official source","observed_at":"2026-10-14" if revision==1 else "2026-10-15"}],
            "uncertainties":["All content is synthetic; no legal, funding or eligibility determination is made.","Work rules and actual costs are unknown."]})
    public_batch = None
    if request["scope"] in ("universities_programs", "refresh") and "CAN" in request["countries"]:
        public_batch = {"batch_id":BATCH_ID, "manifest_digest":FIXTURE_DIGEST}
        findings.extend([{"finding_id":"institution:"+NORTH,"kind":"institution","external_id":NORTH,"country_code":"CAN",
                          "name":"Example North University","summary":"The existing invented v1 institution, subject to separate import review."},
                         {"finding_id":"program:"+PROGRAM,"kind":"program","external_id":PROGRAM,"institution_id":NORTH,"country_code":"CAN",
                          "name":"MSc Example Studies","summary":"The existing invented v1 program under its explicit parent institution."}])
    return seal({**base, "envelope_kind":"result", "result_id":str(uuid5(NAMESPACE_URL,request["request_id"]+":result")),
                 "revision":revision,"previous_revision":revision-1 if revision>1 else None,
                 "completion":"partial", "findings":findings, "public_batch":public_batch})


def changes(previous, current):
    old = {item["finding_id"]:item for item in previous["findings"]} if previous else {}
    result = []
    for finding in current["findings"]:
        before = old.pop(finding["finding_id"],None)
        if before is None:
            result.append({"finding_id":finding["finding_id"],"field":"finding","before":None,"after":finding.get("name",finding.get("summary"))})
            continue
        for key in ("summary","funding_routes","costs","work_rules","uncertainties","sources","observed_at"):
            if before.get(key) != finding.get(key):
                result.append({"finding_id":finding["finding_id"],"field":key,"before":before.get(key),"after":finding.get(key)})
    for identity,finding in old.items():
        result.append({"finding_id":identity,"field":"finding","before":finding.get("name",finding.get("summary")),"after":None})
    return result
