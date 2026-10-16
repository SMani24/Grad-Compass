"""Reproduce the GRA-55 fixture in disposable storage; compare by default, --write to update."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP_ROOT))
from web import research_envelopes as envelopes
from web.research import ResearchWorkspace
from web.server import DemoWorkspace

FIXTURE = APP_ROOT / "tests/fixtures/gra55"
CREATED = "2026-10-15T12:30:00Z"


def build():
    with tempfile.TemporaryDirectory(prefix="grad-compass-gra55-fixture-") as temporary:
        root = Path(temporary)/"map"
        subprocess.run([sys.executable,"-B",str(APP_ROOT/"scripts/create_demo.py"),str(root)],check=True,capture_output=True)
        ids = iter(envelopes.opaque("gra55-"+kind) for kind in ("owner","request","refresh"))
        store = ResearchWorkspace(DemoWorkspace(root),clock=lambda:CREATED,id_factory=lambda:next(ids))
        payload={"submission_key":envelopes.opaque("gra55-submission"),"countries":["CAN","FRA"],"scope":"universities_programs",
                 "preferences":{"intake":"Fall 2027","funding_priorities":"Need funding"},"remember_preferences":True,
                 "limits":"Two examples per country","context":None,"parent_request_id":None,"prior_results":[]}
        request=store.submit(payload)["request"]
        ack=store.demo_response(request["request_id"],"accepted");store.receive(ack["_transport"])
        first=store.demo_response(request["request_id"],"result-1");store.receive(first["_transport"])
        complete=store.demo_response(request["request_id"],"result-2");store.receive(complete["_transport"])
        finding=complete["findings"][0]
        feedback=store.feedback(request["request_id"],complete["result_id"],2,finding["finding_id"],
            "Please refresh this invented funding scenario; this is not a saved preference.",envelopes.opaque("gra55-feedback"),
            request_revision=request["revision"],request_digest=request["digest"],result_digest=complete["digest"],finding_revision=finding["finding_revision"])
        ref={"result_id":complete["result_id"],"revision":2,"digest":complete["digest"],"finding_id":finding["finding_id"],"finding_revision":finding["finding_revision"]}
        refresh=store.submit({**payload,"submission_key":envelopes.opaque("gra55-refresh-submission"),"countries":["CAN"],"scope":"refresh",
            "parent_request_id":request["request_id"],"parent_request_revision":1,"parent_request_digest":request["digest"],
            "prior_results":[ref],"context":feedback["comment"],"remember_preferences":False})["request"]
        artifacts=dict(zip(("request","acknowledgement","result-1","result-2","feedback","refresh"),(request,ack,first,complete,feedback,refresh)))
        files={name+".json":value["_transport"]["body"].encode("utf-8") for name,value in artifacts.items()}
        manifest={"fixture":"gra55-synthetic-0.1.0","synthetic":True,"schema_version":"0.1.0",
                  "sequence":[name+".json" for name in artifacts],"sha256":{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}}
        files["manifest.json"]=(json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode("utf-8")
        return files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    files=build()
    if args.write:
        FIXTURE.mkdir(parents=True,exist_ok=True)
        for name,raw in files.items(): (FIXTURE/name).write_bytes(raw)
    else:
        for name,raw in files.items():
            if not (FIXTURE/name).is_file() or (FIXTURE/name).read_bytes()!=raw:
                raise SystemExit("Fixture differs: "+name)
    print("GRA-55 fixture "+("written" if args.write else "reproduced exactly")+"; manifest SHA-256 "+hashlib.sha256(files["manifest.json"]).hexdigest())


if __name__=="__main__":main()
