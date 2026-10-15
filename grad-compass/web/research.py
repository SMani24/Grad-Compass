"""Marked app-owned synthetic research state; no producer access or agent execution."""
from contextlib import closing
import os
import json
import tempfile
from uuid import uuid4
import sqlite3
import threading

from web.country_evidence import COUNTRY_CODES
from web import research_envelopes as envelopes

MARKER = "grad-compass-research-demo-v1"


class ResearchWorkspace:
    def __init__(self, workspace):
        self.workspace = workspace
        self.directory = workspace.directory
        self.database = self.directory / "research.sqlite"
        self.lock = threading.RLock()
        with self.lock, closing(workspace.connect()):
            self._guard_paths()
            if not self.database.exists():
                descriptor = os.open(self.database, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                os.close(descriptor)
                with closing(sqlite3.connect(self.database)) as db, db:
                    db.executescript("""
                        CREATE TABLE app_research_guard(marker TEXT NOT NULL);
                        INSERT INTO app_research_guard VALUES('grad-compass-research-demo-v1');
                        CREATE TABLE country_personal(code TEXT PRIMARY KEY,
                            watched INTEGER NOT NULL DEFAULT 0 CHECK(watched IN (0,1)),
                            note TEXT NOT NULL DEFAULT '');
                    """)
            with closing(self.connect()) as db, db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS research_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS research_preferences(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS research_requests(id TEXT PRIMARY KEY,submission_key TEXT UNIQUE NOT NULL,
                        submission_digest TEXT NOT NULL,body TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS research_acks(id TEXT PRIMARY KEY,request_id TEXT NOT NULL UNIQUE REFERENCES research_requests(id),body TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS research_results(id TEXT NOT NULL,revision INTEGER NOT NULL,
                        request_id TEXT NOT NULL REFERENCES research_requests(id),body TEXT NOT NULL,received_at TEXT NOT NULL,
                        PRIMARY KEY(id,revision));
                    CREATE TABLE IF NOT EXISTS research_feedback(id TEXT PRIMARY KEY,request_id TEXT NOT NULL REFERENCES research_requests(id),
                        result_id TEXT NOT NULL,result_revision INTEGER NOT NULL,body TEXT NOT NULL,
                        FOREIGN KEY(result_id,result_revision) REFERENCES research_results(id,revision));
                """)
                db.execute("INSERT OR IGNORE INTO research_meta VALUES('owner_id',?)",(str(uuid4()),))
                for table in ("research_requests","research_acks","research_results","research_feedback"):
                    for action in ("UPDATE","DELETE"):
                        db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'Research envelopes are immutable'); END")

    def _guard_paths(self):
        if any(path.is_symlink() for path in (self.directory, *self.directory.parents)):
            raise ValueError("Research state requires an unlinked synthetic workspace")
        for suffix in ("", "-wal", "-shm", "-journal"):
            path = type(self.database)(str(self.database) + suffix)
            if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1)):
                raise ValueError("Research state requires unlinked runtime files")

    def connect(self):
        with closing(self.workspace.connect()):
            pass
        self._guard_paths()
        if not self.database.is_file():
            raise ValueError("The synthetic research workspace is missing")
        db = sqlite3.connect(self.database.as_uri() + "?mode=rw", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            if [row[0] for row in db.execute("SELECT marker FROM app_research_guard")] != [MARKER]:
                raise ValueError("A marked synthetic research workspace is required")
        except (sqlite3.Error, ValueError):
            db.close()
            raise ValueError("A marked synthetic research workspace is required") from None
        return db

    @staticmethod
    def _body(row):
        return envelopes.verify(json.loads(row["body"])) if row else None

    def snapshot(self):
        with self.lock, closing(self.connect()) as db:
            preference = db.execute("SELECT body FROM research_preferences WHERE id=1").fetchone()
            requests = []
            for row in db.execute("SELECT * FROM research_requests ORDER BY rowid DESC"):
                request = self._body(row)
                ack = self._body(db.execute("SELECT body FROM research_acks WHERE request_id=?",(request["request_id"],)).fetchone())
                count = db.execute("SELECT count(*) FROM research_results WHERE request_id=?",(request["request_id"],)).fetchone()[0]
                requests.append({"request_id":request["request_id"],"revision":request["revision"],"digest":request["digest"],
                    "scope":request["scope"],"countries":request["countries"],"created_at":request["created_at"],
                    "state":"results_received" if count else ack["state"] if ack else "prepared", "result_count":count,
                    "execution_progress":ack.get("execution_progress") if ack else None})
            return {"synthetic":True,"countries":{row["code"]:{"watched":bool(row["watched"]),"note":row["note"]}
                    for row in db.execute("SELECT * FROM country_personal ORDER BY code")},"requests":requests,
                    "has_preferences":preference is not None,
                    "preferences":json.loads(preference[0]) if preference else {key:None for key in envelopes.PREFERENCE_FIELDS}}

    def request(self, identity):
        envelopes.identifier(identity)
        with self.lock, closing(self.connect()) as db:
            request = self._body(db.execute("SELECT body FROM research_requests WHERE id=?",(identity,)).fetchone())
            if request is None:
                raise ValueError("The selected research request was not found")
            results = [self._body(row) for row in db.execute("SELECT body FROM research_results WHERE request_id=? ORDER BY revision",(identity,))]
            feedback = [self._body(row) for row in db.execute("SELECT body FROM research_feedback WHERE request_id=? ORDER BY rowid",(identity,))]
            ack = self._body(db.execute("SELECT body FROM research_acks WHERE request_id=?",(identity,)).fetchone())
            reviewed = []
            for index,result in enumerate(results):
                previous = results[index-1] if index else None
                if previous is None and request["prior_results"]:
                    ref = request["prior_results"][0]
                    previous = self._body(db.execute("SELECT body FROM research_results WHERE id=? AND revision=?",(ref["result_id"],ref["revision"])).fetchone())
                    if previous: previous={**previous,"findings":[finding for finding in previous["findings"] if finding["country_code"] in request["countries"]]}
                reviewed.append({"envelope":result,"changes":envelopes.changes(previous,result)})
            return {"request":request,"acknowledgement":ack,"results":reviewed,"feedback":feedback}

    def submit(self, payload):
        values = envelopes.request_values(payload)
        submission_digest = envelopes.digest({**values,"remember_preferences":payload["remember_preferences"]})
        with self.lock, closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM research_requests WHERE submission_key=?",(payload["submission_key"],)).fetchone()
            if previous:
                if previous["submission_digest"] != submission_digest:
                    raise ValueError("This submission was already saved with different contents; reopen the form")
                identity = previous["id"]
            else:
                if values["parent_request_id"] and not db.execute("SELECT 1 FROM research_requests WHERE id=?",(values["parent_request_id"],)).fetchone():
                    raise ValueError("Select an existing parent request")
                for ref in values["prior_results"]:
                    envelopes.identifier(ref["result_id"])
                    if type(ref["revision"]) is not int or not isinstance(ref["finding_id"],(str,type(None))):
                        raise ValueError("Select an exact saved result revision")
                    result = self._body(db.execute("SELECT body FROM research_results WHERE id=? AND revision=?",(ref["result_id"],ref["revision"])).fetchone())
                    if (not result or result["digest"] != ref["digest"] or result["request_id"] != values["parent_request_id"]
                        or (ref["finding_id"] and ref["finding_id"] not in {finding["finding_id"] for finding in result["findings"]})):
                        raise ValueError("The follow-up reference does not match a saved result")
                identity = str(uuid4())
                request = envelopes.seal({"private_schema_version":envelopes.PRIVATE_VERSION,"synthetic":True,"envelope_kind":"request",
                    "request_id":identity,"revision":1,"created_at":envelopes.now(),
                    "owner_id":db.execute("SELECT value FROM research_meta WHERE key='owner_id'").fetchone()[0],"profile_reference":None,**values})
                db.execute("INSERT INTO research_requests VALUES(?,?,?,?)",(identity,payload["submission_key"],submission_digest,envelopes.compact(request)))
                if payload["remember_preferences"]:
                    db.execute("INSERT INTO research_preferences VALUES(1,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",(envelopes.compact(values["preferences"]),))
        return self.request(identity)

    def save_country(self, payload):
        if (not isinstance(payload, dict) or not {"country_code"} < set(payload)
            or set(payload) - {"country_code", "watched", "note"}
            or not isinstance(payload["country_code"], str) or payload["country_code"] not in COUNTRY_CODES
            or ("watched" in payload and type(payload["watched"]) is not bool)
            or ("note" in payload and (not isinstance(payload["note"], str) or len(payload["note"]) > 4000))):
            raise ValueError("Choose a displayed country and a valid saved-country choice or note")
        with self.lock, closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT watched,note FROM country_personal WHERE code=?", (payload["country_code"],)).fetchone()
            watched = payload.get("watched", bool(previous["watched"]) if previous else False)
            note = payload.get("note", previous["note"] if previous else "")
            db.execute("INSERT INTO country_personal(code,watched,note) VALUES(?,?,?) ON CONFLICT(code) DO UPDATE SET watched=excluded.watched,note=excluded.note",
                       (payload["country_code"], int(watched), note))
        return self.snapshot()

    def save_countries(self, payload):
        """Save memberships together; leave existing notes and all other state intact."""
        countries = payload.get("countries") if isinstance(payload, dict) else None
        if (not isinstance(payload, dict) or set(payload) != {"countries"}
            or not isinstance(countries, list) or not 1 <= len(countries) <= len(COUNTRY_CODES)
            or any(not isinstance(code, str) or code not in COUNTRY_CODES for code in countries)
            or len(set(countries)) != len(countries)):
            raise ValueError("Select distinct countries from the map or country list")
        with self.lock, closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.executemany("INSERT INTO country_personal(code,watched,note) VALUES(?,1,'') "
                           "ON CONFLICT(code) DO UPDATE SET watched=1 WHERE watched=0",
                           [(code,) for code in countries])
        return self.snapshot()

    def _write_private_file(self, name, value, replace=False):
        root = self.directory / "research-handoff"
        if root.is_symlink():
            raise ValueError("Private handoffs cannot use linked storage")
        root.mkdir(mode=0o700, exist_ok=True)
        path = root / name
        if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1)):
            raise ValueError("Private handoffs require unlinked files")
        body = (envelopes.compact(value)+"\n").encode()
        if path.exists() and not replace:
            if path.read_bytes() != body:
                raise ValueError("An existing private handoff has different contents; it was preserved")
            return path
        descriptor,temporary=tempfile.mkstemp(prefix=".handoff-",dir=root)
        try:
            with os.fdopen(descriptor,"wb") as output: output.write(body)
            if replace: os.replace(temporary,path)
            else:
                # Exclusive publication: a concurrent exporter must never overwrite a file.
                try: os.link(temporary,path)
                except FileExistsError:
                    if path.is_symlink() or path.read_bytes()!=body:
                        raise ValueError("The private handoff changed during export") from None
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        return path

    def export(self, request_id, feedback_id=None):
        with self.lock, closing(self.connect()) as db:
            current=self.request(request_id)
            value=current["request"]
            kind="request"
            if feedback_id:
                envelopes.identifier(feedback_id)
                value=next((item for item in current["feedback"] if item["feedback_id"]==feedback_id),None)
                if value is None: raise ValueError("Select feedback from this request")
                kind="feedback"
            identity=value["request_id"] if kind=="request" else value["feedback_id"]
            path=self._write_private_file(kind+"-"+identity+".json",value)
            index={"synthetic":True,"requests":[{key:item[key] for key in ("request_id","revision","digest","state")} for item in self.snapshot()["requests"]]}
            self._write_private_file("index.json",index,replace=True)
            prompt=(f"Dave — synthetic app pilot only. Review the private {kind} file at {path}. "
                    f"Reference: {identity}; digest: {value['digest']}. "
                    f"Request: {request_id}, revision 1; request digest: {current['request']['digest']}. "
                    "Acknowledge the exact request revision/digest. No real research or automatic agents are authorized by this handoff. "
                    "Keep the private contents out of the public mailbox.")
            return {"prompt":prompt,"path":str(path),"digest":value["digest"],"kind":kind}

    def demo_response(self, request_id, choice):
        return envelopes.demo_response(self.request(request_id)["request"],choice)

    def receive(self, value):
        if not isinstance(value,dict) or value.get("synthetic") is not True or value.get("private_schema_version")!=envelopes.PRIVATE_VERSION:
            raise ValueError("Only app-owned synthetic responses are accepted in this pilot")
        envelopes.verify(value)
        request_id=value.get("request_id")
        current=self.request(request_id)
        request=current["request"]
        kind=value.get("envelope_kind")
        choice=value.get("state") if kind=="acknowledgement" else f"result-{value.get('revision')}" if kind=="result" else None
        expected=envelopes.demo_response(request,choice)
        if envelopes.compact(value)!=envelopes.compact(expected):
            raise ValueError("The response does not match this exact request and app-owned demo fixture")
        with self.lock, closing(self.connect()) as db,db:
            db.execute("BEGIN IMMEDIATE")
            if kind=="acknowledgement":
                previous=self._body(db.execute("SELECT body FROM research_acks WHERE request_id=?",(request_id,)).fetchone())
                if previous:
                    if previous!=value: raise ValueError("A different acknowledgement is already recorded; prepare a follow-up")
                    return {"changed":False,**self.request(request_id)}
                db.execute("INSERT INTO research_acks VALUES(?,?,?)",(value["ack_id"],request_id,envelopes.compact(value)))
            else:
                previous=self._body(db.execute("SELECT body FROM research_results WHERE id=? AND revision=?",(value["result_id"],value["revision"])).fetchone())
                if previous:
                    if previous!=value: raise ValueError("This result revision already has different contents")
                    return {"changed":False,**self.request(request_id)}
                ack=self._body(db.execute("SELECT body FROM research_acks WHERE request_id=?",(request_id,)).fetchone())
                if not ack or ack["state"]!="accepted": raise ValueError("Record an explicit accepted demo acknowledgement before results")
                if value["revision"]>1:
                    if not db.execute("SELECT 1 FROM research_results WHERE id=? AND revision=?",(value["result_id"],value["revision"]-1)).fetchone():
                        raise ValueError("Receive the earlier result revision first")
                    if not db.execute("SELECT 1 FROM research_feedback WHERE result_id=? AND result_revision=?",(value["result_id"],value["revision"]-1)).fetchone():
                        raise ValueError("Save feedback on the previous result before the revised demo response")
                db.execute("INSERT INTO research_results VALUES(?,?,?,?,?)",(value["result_id"],value["revision"],request_id,envelopes.compact(value),envelopes.now()))
        return {"changed":True,**self.request(request_id)}

    def feedback(self, request_id, result_id, revision, finding_id, comment, submission_key):
        envelopes.identifier(submission_key)
        current=self.request(request_id)
        result=next((item["envelope"] for item in current["results"] if item["envelope"]["result_id"]==result_id and item["envelope"]["revision"]==revision),None)
        if type(revision) is not int or not result or finding_id not in {finding["finding_id"] for finding in result["findings"]}:
            raise ValueError("Select a specific saved finding and result revision")
        comment=envelopes.text(comment,4000)
        if not comment: raise ValueError("Write feedback before saving")
        with self.lock,closing(self.connect()) as db,db:
            previous=self._body(db.execute("SELECT body FROM research_feedback WHERE id=?",(submission_key,)).fetchone())
            if previous:
                if (previous["request_id"],previous["result_id"],previous["result_revision"],previous["finding_id"],previous["comment"])!=(request_id,result_id,revision,finding_id,comment):
                    raise ValueError("This feedback submission was already saved with different contents")
                return previous
            value=envelopes.seal({"private_schema_version":envelopes.PRIVATE_VERSION,"synthetic":True,"envelope_kind":"feedback",
                "feedback_id":submission_key,"created_at":envelopes.now(),"request_id":request_id,"request_revision":1,
                "request_digest":current["request"]["digest"],"result_id":result_id,"result_revision":revision,
                "result_digest":result["digest"],"finding_id":finding_id,"comment":comment})
            db.execute("INSERT INTO research_feedback VALUES(?,?,?,?,?)",(submission_key,request_id,result_id,revision,envelopes.compact(value)))
        return value

    def latest_country(self, code):
        with self.lock,closing(self.connect()) as db:
            history=[]
            latest=None
            for row in db.execute("SELECT body FROM research_results ORDER BY rowid DESC"):
                result=self._body(row)
                finding=next((item for item in result["findings"] if item["kind"]=="country" and item["country_code"]==code),None)
                if finding:
                    origin={"request_id":result["request_id"],"result_id":result["result_id"],"revision":result["revision"],"digest":result["digest"],"finding_id":finding["finding_id"]}
                    history.append(origin)
                    if latest is None: latest={**finding,"origin":origin}
            return {**latest,"history":history} if latest else None

    def links(self, kind, external_id):
        with self.lock,closing(self.connect()) as db:
            links=[]
            for row in db.execute("SELECT body FROM research_results ORDER BY rowid DESC"):
                result=self._body(row)
                if result["public_batch"]!={"batch_id":envelopes.BATCH_ID,"manifest_digest":envelopes.FIXTURE_DIGEST}: continue
                for finding in result["findings"]:
                    if finding["kind"]==kind and finding.get("external_id")==external_id:
                        links.append({"request_id":result["request_id"],"result_id":result["result_id"],"revision":result["revision"],"digest":result["digest"],"finding_id":finding["finding_id"]})
            return links
