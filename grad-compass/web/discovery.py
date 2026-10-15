"""Read-only discovery projection of committed synthetic importer outcomes."""
import json

from web.exchange_workflow import BATCH_ID


def promoted_discovery(exchange):
    if exchange is None:
        return {}
    state = exchange.state(BATCH_ID)
    if not state["receipt"] or not state["receipt"]["promotion_committed"]:
        return {}
    local_institutions = {row["id"]: row for row in state["saved_institutions"]}
    local_programs = {row["id"]: row for row in state["saved_programs"]}
    details = {}
    parents = {}
    for row in state["institutions"]:
        if row["storage"] != "promoted":
            continue
        local_id = row["mapping"]["local_id"]
        identity = f"exchange-{local_id}"
        parents[row["record"]["id"]] = identity
        local = local_institutions[local_id]
        # Namespace IDs rather than merging unrelated databases by integer or name.
        university = {**local, "id": identity, "faculty_count": 0,
                      "status": local["status"] or "Researching", "synthetic": True,
                      "research": {"external_id": row["record"]["id"],
                                   "revision": row["record"]["record_revision"],
                                   "review": row["record"]["review"]["state"],
                                   "storage": "promoted", "facts": row["record"]["facts"]}}
        details.setdefault(identity, {"university": university, "professors": [], "tasks": [], "programs": []})
    for row in state["programs"]:
        if row["storage"] != "promoted":
            continue
        parent = parents.get(row["record"]["institution_id"])
        if parent is None:
            continue
        local = local_programs[row["mapping"]["local_id"]]
        details[parent]["programs"].append({"id": f"exchange-program-{local['id']}",
            "name": local["name"], "degree_level": local["degree_level"],
            "official_url": local["official_url"], "requirements": json.loads(local["requirements_json"]),
            "external_id": row["record"]["id"], "revision": row["record"]["record_revision"],
            "review": row["record"]["review"]["state"], "storage": "promoted"})
    return details


def overview(workspace, exchange):
    result = workspace.overview()
    promoted = promoted_discovery(exchange)
    result["universities"].extend(detail["university"] for detail in promoted.values())
    return result


def university(workspace, exchange, identity):
    if identity.startswith("exchange-"):
        result = promoted_discovery(exchange).get(identity)
        if result:
            result["research_results"] = workspace.research.links("institution",result["university"]["research"]["external_id"])
            for program in result["programs"]:
                program["research_results"] = workspace.research.links("program",program["external_id"])
        return result
    result = workspace.university(int(identity))
    if result is not None:
        result["programs"] = []
    return result
