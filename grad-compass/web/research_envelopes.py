"""App-owned synthetic 0.1.0 envelopes; hashes bind exact UTF-8 body bytes."""
from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import UUID, uuid5, NAMESPACE_URL

from web.country_evidence import COUNTRY_CODES
from web.exchange_workflow import BATCH_ID, FIXTURE_DIGEST, FIXTURE
from core import exchange_importer

PRIVATE_VERSION = "0.1.0"
COUNTRY_VERSION = "0.1.0"
PREFERENCE_FIELDS = ("intake", "intake_alternatives", "degree_routes", "instruction_language",
                     "country_restrictions", "funding_priorities", "research_limits")
SCOPES = {"country_conditions": "Update country conditions", "universities_programs": "Find universities and programs",
          "refresh": "Refresh or follow up"}
NORTH = "11111111-1111-4111-8111-111111111111"
PROGRAM = "33333333-3333-4333-8333-333333333333"


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(value):
    """Internal submission/legacy fingerprint; never an exchanged artifact digest."""
    return hashlib.sha256(compact(value).encode("utf-8")).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not accepted")
        result[key] = value
    return result


def loads(raw):
    def invalid_constant(value):
        raise ValueError("Non-finite JSON numbers are not accepted")
    try:
        if isinstance(raw, bytes): raw = raw.decode("utf-8", errors="strict")
        return json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError, TypeError):
        raise ValueError("Use valid UTF-8 JSON without duplicate keys") from None


def identifier(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value: raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Choose an existing research item") from None
    return value


def digest_reference(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("Use the exact saved artifact digest")
    return value


def utc(value):
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00")):
        raise ValueError("Observation and review times must be UTC timestamps")
    try: datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: raise ValueError("Use a complete UTC timestamp") from None
    if "T" not in value: raise ValueError("Use a complete UTC timestamp")
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


def packet(value):
    body = compact(value) + "\n"
    return {"body":body, "sha256":hashlib.sha256(body.encode("utf-8")).hexdigest()}


def verify(transport, *, synthetic=True, max_bytes=180000):
    """Hash original bytes before decoding; never canonicalize an incoming body."""
    if not isinstance(transport, dict) or set(transport) != {"body", "sha256"} or not isinstance(transport["body"], str):
        raise ValueError("Use an exact-byte body and its separate SHA-256 reference")
    digest_reference(transport["sha256"])
    try: raw = transport["body"].encode("utf-8", errors="strict")
    except UnicodeError: raise ValueError("Use valid UTF-8 envelope bytes") from None
    if len(raw) > max_bytes or hashlib.sha256(raw).hexdigest() != transport["sha256"]:
        raise ValueError("The original envelope bytes no longer match their digest")
    value = loads(raw)
    if (not isinstance(value, dict) or value.get("synthetic") is not synthetic
        or value.get("schema_version") != PRIVATE_VERSION or "digest" in value or "_transport" in value):
        raise ValueError("Use a 0.1.0 envelope with the workspace’s authorized data scope")
    try:
        # UI aliases are outside exchanged bytes. Wire names are the agreed schema names.
        view = {**value, "digest":transport["sha256"], "_transport":transport}
        if value["envelope_kind"] == "request":
            view.update(revision=value["request_revision"], countries=value["country_codes"], preferences=value["preference_snapshot"],
                        prior_results=[{"result_id":r["result_id"],"revision":r["result_revision"],"digest":r["result_digest"],"finding_id":r["finding_id"],"finding_revision":r["finding_revision"]} for r in value["prior_results"]])
        elif value["envelope_kind"] == "result":
            view.update(revision=value["result_revision"], created_at=value["issued_at"])
            association = next(iter(value["public_associations"]), None)
            view["public_batch"] = {"batch_id":association["batch_id"], "manifest_digest":association["manifest_sha256"]} if association else None
        elif value["envelope_kind"] == "acknowledgement": view["created_at"] = value["acknowledged_at"]
        return view
    except (KeyError, TypeError):
        raise ValueError("The envelope is missing required typed fields") from None


def seal(value):
    return verify(packet(value), synthetic=value.get("synthetic") is True, max_bytes=4_000_000 if value.get("synthetic") is False else 180000)


def storage(value):
    return compact(value["_transport"])


def saved(raw, *, synthetic=True):
    value = loads(raw)
    if isinstance(value, dict) and set(value) == {"body", "sha256"}: return verify(value, synthetic=synthetic, max_bytes=4_000_000 if not synthetic else 180000)
    if not synthetic: raise ValueError("Operational records require exact-byte transport storage")
    # Preserve old synthetic history without changing its bytes or claiming new semantics.
    if (not isinstance(value, dict) or value.get("synthetic") is not True or value.get("private_schema_version") != PRIVATE_VERSION
        or value.get("envelope_kind") not in {"request","acknowledgement","result","feedback"}
        or value.get("digest") != fingerprint({k:v for k,v in value.items() if k != "digest"})):
        raise ValueError("The legacy synthetic record no longer matches its original fingerprint")
    return {**value, "legacy":True}


def text(value, maximum=2000):
    if value is None: return None
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Keep the research text within the displayed limit")
    return value.strip() or None


def request_values(payload):
    allowed = {"submission_key", "countries", "scope", "preferences", "remember_preferences", "limits", "context",
               "parent_request_id", "parent_request_revision", "parent_request_digest", "prior_results", "bounds"}
    if not isinstance(payload, dict) or set(payload)-allowed: raise ValueError("Review the research request fields")
    identifier(payload.get("submission_key"))
    countries = payload.get("countries")
    if (not isinstance(countries, list) or not 1 <= len(countries) <= 20
        or any(not isinstance(code, str) or code not in COUNTRY_CODES for code in countries)
        or len(set(countries)) != len(countries)):
        raise ValueError("Select between 1 and 20 distinct countries for this request")
    if any(not re.fullmatch(r"[A-Z]{3}", code) or code == "XKX" for code in countries):
        raise ValueError("This synthetic handoff requires assigned country codes; territory mappings need separate review")
    if not isinstance(payload.get("scope"), str) or payload["scope"] not in SCOPES: raise ValueError("Choose a research scope")
    preferences = payload.get("preferences")
    if not isinstance(preferences, dict) or set(preferences)-set(PREFERENCE_FIELDS) or type(payload.get("remember_preferences")) is not bool:
        raise ValueError("Review your explicit shared preferences")
    preferences = {key:text(preferences.get(key),1200) for key in PREFERENCE_FIELDS}
    parent = payload.get("parent_request_id")
    parent_revision, parent_digest = payload.get("parent_request_revision"), payload.get("parent_request_digest")
    if parent is not None:
        identifier(parent); digest_reference(parent_digest)
        if type(parent_revision) is not int or parent_revision < 1: raise ValueError("Bind the exact parent request revision")
    elif parent_revision is not None or parent_digest is not None: raise ValueError("Choose the parent for this request binding")
    references = payload.get("prior_results", [])
    fields = {"result_id","revision","digest","finding_id","finding_revision"}
    if not isinstance(references, list) or len(references)>20 or any(not isinstance(ref,dict) or set(ref)!=fields for ref in references):
        raise ValueError("Select an exact saved result and finding revision")
    if references and not parent: raise ValueError("Prior results must belong to the bound parent request")
    if payload["scope"] == "refresh" and not parent: raise ValueError("Choose the previous request for this follow-up")
    result = {"country_codes":countries, "scope":payload["scope"], "preference_snapshot":preferences,
            "limits":text(payload.get("limits")), "context":text(payload.get("context"),4000),
            "parent_request_id":parent, "parent_request_revision":parent_revision, "parent_request_digest":parent_digest, "prior_results":references}
    if "bounds" in payload:
        bounds=payload["bounds"]
        if not isinstance(bounds,dict) or set(bounds)!={"institutions","programs"} or any(type(v) is not int or not 0<=v<=200 for v in bounds.values()):
            raise ValueError("Set bounded institution/program counts between 0 and 200")
        result["bounds"]=bounds
    return result


def opaque(value):
    return str(uuid5(NAMESPACE_URL, "grad-compass-synthetic:" + value))


def public_associations():
    # Reuse the unchanged importer validator and finalized public fixture; no staging/import.
    manifest, institution_rows, program_rows, manifest_digest = exchange_importer._read_batch(FIXTURE)
    if manifest_digest != FIXTURE_DIGEST: raise ValueError("The pinned synthetic public manifest changed")
    institutions = {row["id"]:row for row in institution_rows}
    programs = {row["id"]:row for row in program_rows}
    institution = institutions[NORTH]; program = programs[PROGRAM]
    base = {"batch_id":BATCH_ID, "manifest_sha256":FIXTURE_DIGEST, "institution_id":NORTH,
            "institution_record_revision":institution["record_revision"]}
    return [base, {**base, "program_id":PROGRAM, "program_record_revision":program["record_revision"]}]


def demo_response(request, choice):
    if request.get("legacy"): raise ValueError("Legacy synthetic records are read-only; prepare a new request for the corrected handoff")
    binding = {"request_id":request["request_id"], "request_revision":request["revision"], "request_digest":request["digest"]}
    base = {"schema_version":PRIVATE_VERSION, "synthetic":True, **binding}
    if choice in ("accepted", "rejected", "needs_clarification"):
        return seal({**base, "envelope_kind":"acknowledgement", "acknowledged_at":request["created_at"],
                     "ack_id":opaque(request["request_id"]+":ack"), "state":choice, "execution_progress":None})
    if choice not in ("result-1", "result-2"): raise ValueError("Choose an app-owned synthetic response")
    revision = int(choice[-1]); findings = []
    observed = "2026-10-14T12:00:00Z" if revision==1 else "2026-10-15T12:00:00Z"
    for code in request["countries"]:
        record_id = opaque("country:"+code)
        record_revision = opaque(f"country:{code}:r{revision}")
        finding_revision = opaque(f"finding:{code}:r{revision}")
        findings.append({"finding_id":"country:"+code, "finding_revision":finding_revision,
            "kind":"country", "country_code":code, "country_schema_version":COUNTRY_VERSION,
            "country_record_id":record_id, "record_revision":record_revision, "source_revision":f"demo-{code}-r{revision}",
            "evidence_status":"unknown", "review_status":"pending",
            "human_approval":{"state":"not_requested","approver_id":None,"approved_at":None,
                              "country_record_id":record_id,"record_revision":record_revision,"finding_id":"country:"+code,"finding_revision":finding_revision},
            "review":{"kind":"agent_factual_review","reviewer_id":opaque("demo-reviewer"), "reviewed_at":observed, "decision":"pending",
                      "country_record_id":record_id, "record_revision":record_revision, "finding_id":"country:"+code, "finding_revision":finding_revision},
            "summary":f"Invented {code} research scenario. Routes need checking against a real applicant's requirements.",
            "funding_routes":"Invented route A: a sample studentship to investigate." if revision==1 else "Invented route B replaces route A; eligibility remains unverified.",
            "costs":"No real cost estimate supplied." if revision==1 else "A revised invented cost scenario is available; actual fees and living costs remain unknown.",
            "work_rules":None, "observed_at":observed, "coverage":"Synthetic scenario only; actual costs and work rules are unknown.",
            "sources":[{"source_id":opaque(f"source:{code}:r{revision}"), "source_revision":opaque(f"source-revision:{code}:r{revision}"),
                        "source_url":f"https://example.invalid/research/{code.lower()}/revision-{revision}",
                        "locator":"Invented country evidence — not an official source", "observed_at":observed}],
            "uncertainties":["All content is synthetic; no legal, funding or eligibility determination is made.","Work rules and actual costs are unknown."]})
    associations = []
    if request["scope"] in ("universities_programs", "refresh") and "CAN" in request["countries"]:
        associations = public_associations()
        findings.extend([{"finding_id":"institution:"+NORTH,"finding_revision":opaque(f"institution-finding:r{revision}"),"kind":"institution","external_id":NORTH,"country_code":"CAN",
                          "public_association":associations[0], "name":"Example North University","summary":"The existing invented v1 institution, subject to separate import review."},
                         {"finding_id":"program:"+PROGRAM,"finding_revision":opaque(f"program-finding:r{revision}"),"kind":"program","external_id":PROGRAM,"institution_id":NORTH,"country_code":"CAN",
                          "public_association":associations[1], "name":"MSc Example Studies","summary":"The existing invented v1 program under its explicit parent institution."}])
    for finding in findings:
        if finding["kind"] == "country":
            finding["finding_ref"] = {key:finding[key] for key in ("country_record_id","record_revision","finding_id","finding_revision","evidence_status","review_status")}
    previous = demo_response(request, "result-1") if revision == 2 else None
    return seal({**base, "envelope_kind":"result", "issued_at":request["created_at"], "result_id":opaque(request["request_id"]+":result"),
                 "result_revision":revision, "previous_result_revision":1 if previous else None,
                 "previous_result_digest":previous["digest"] if previous else None,
                 "completion":"partial" if revision==1 else "complete", "findings":findings, "public_associations":associations})


def validate_result(value):
    utc(value.get("issued_at"))
    if type(value.get("result_revision")) is not int or value["result_revision"] not in (1,2): raise ValueError("Use an exact result revision")
    if value.get("completion") not in ("partial","complete"): raise ValueError("Use a stated result completion")
    associations = public_associations() if value.get("public_associations") else []
    if value.get("public_associations") != associations: raise ValueError("Public record revisions must match the validated finalized synthetic batch")
    for finding in value["findings"]:
        identifier(finding.get("finding_revision"))
        if finding["kind"] != "country":
            association = finding.get("public_association")
            index = 0 if finding["kind"] == "institution" else 1
            if not associations or association != associations[index]: raise ValueError("Bind each public finding to its exact public record revision")
            if finding.get("external_id") != association["institution_id" if index==0 else "program_id"] or (index==1 and finding.get("institution_id")!=association["institution_id"]):
                raise ValueError("The public finding identity/parent must match its record association")
            continue
        for key in ("country_record_id","record_revision"): identifier(finding.get(key))
        if finding.get("country_schema_version") != COUNTRY_VERSION: raise ValueError("Unsupported country evidence version")
        if finding.get("finding_ref") != {key:finding.get(key) for key in ("country_record_id","record_revision","finding_id","finding_revision","evidence_status","review_status")}:
            raise ValueError("Bind each finding reference to its exact evidence/review revisions")
        utc(finding.get("observed_at"))
        review = finding.get("review", {})
        if review.get("decision") not in ("pending","accepted","rejected") or finding.get("review_status") != review.get("decision"):
            raise ValueError("Supply the actual revision-bound factual review status")
        for key in ("country_record_id","record_revision","finding_id","finding_revision"):
            if review.get(key) != finding.get(key): raise ValueError("The factual review does not bind this exact country/finding revision")
        if review.get("kind") != "agent_factual_review": raise ValueError("Keep agent factual review separate from human approval")
        identifier(review.get("reviewer_id")); utc(review.get("reviewed_at"))
        approval = finding.get("human_approval", {})
        if approval.get("state") != "not_requested" or approval.get("approver_id") is not None or approval.get("approved_at") is not None:
            raise ValueError("The invented fixture has no human approval")
        for key in ("country_record_id","record_revision","finding_id","finding_revision"):
            if approval.get(key) != finding.get(key): raise ValueError("Bind human approval status separately to the exact revision")
        if not finding.get("coverage") or not finding.get("uncertainties") or finding.get("evidence_status") not in ("unknown","supplied"):
            raise ValueError("Keep evidence coverage, unknowns and review status explicit")
        if not finding.get("sources"): raise ValueError("Supply source identities and page locators")
        for source in finding["sources"]:
            identifier(source.get("source_id")); identifier(source.get("source_revision")); utc(source.get("observed_at"))
            if not isinstance(source.get("source_url"), str) or not source["source_url"].startswith("https://example.invalid/") or not source.get("locator"):
                raise ValueError("Use the app-owned synthetic source with a page locator")


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
