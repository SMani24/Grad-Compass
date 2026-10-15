"""Synthetic watchlist/request state, isolated from production and canonical artifacts."""
from contextlib import closing
import hashlib
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

APP_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP_ROOT))
from web.server import DemoWorkspace
from web.research import ResearchWorkspace


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="grad-compass-research-check-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"map"
        subprocess.run([sys.executable,"-B",str(APP_ROOT/"scripts/create_demo.py"),str(self.root)],check=True,capture_output=True)
        self.workspace=DemoWorkspace(self.root)
        self.store=self.workspace.research
        self.before=hashlib.sha256(self.workspace.database.read_bytes()).hexdigest()

    def test_watchlist_note_and_assessment_are_independent_and_survive_restart(self):
        self.workspace.country_decisions("FRA","Excluded")
        self.store.save_country({"country_code":"FRA","note":"An explicit personal note"})
        self.store.save_country({"country_code":"FRA","watched":True})
        self.store.save_country({"country_code":"CAN","watched":True})
        reopened=ResearchWorkspace(DemoWorkspace(self.root))
        self.assertTrue(reopened.snapshot()["countries"]["FRA"]["watched"])
        reopened.save_country({"country_code":"FRA","watched":False})
        self.assertEqual(reopened.snapshot()["countries"]["FRA"],{"watched":False,"note":"An explicit personal note"})
        self.assertTrue(reopened.snapshot()["countries"]["CAN"]["watched"])
        self.assertEqual(self.workspace.country_decisions()["FRA"],"Excluded")
        self.assertEqual(hashlib.sha256(self.workspace.database.read_bytes()).hexdigest(),self.before)
        self.assertEqual(self.store.database.stat().st_mode & 0o777,0o600)

    def test_invalid_countries_flags_and_notes_do_not_write(self):
        for payload in ({"country_code":"ATA","watched":True},{"country_code":"FRA","watched":1},
                        {"country_code":"FRA","note":"x"*4001},{"country_code":"FRA","review":"accepted"},
                        {"country_code":"FRA"},[],{"country_code":None,"watched":True}):
            with self.assertRaises(ValueError): self.store.save_country(payload)
        self.assertEqual(self.store.snapshot()["countries"],{})

    def test_unmarked_or_linked_state_and_removed_preview_marker_are_refused(self):
        with closing(sqlite3.connect(self.store.database)) as db,db:
            db.execute("DELETE FROM app_research_guard")
        with self.assertRaises(ValueError): self.store.snapshot()
        with closing(sqlite3.connect(self.store.database)) as db,db:
            db.execute("INSERT INTO app_research_guard VALUES('grad-compass-research-demo-v1')")
        import os
        linked=Path(self.temp.name)/"linked.sqlite"
        os.link(self.store.database,linked)
        with self.assertRaises(ValueError): self.store.save_country({"country_code":"FRA","watched":True})
        linked.unlink()
        with closing(sqlite3.connect(self.workspace.database)) as db,db:
            db.execute("DELETE FROM app_synthetic_demo_guard")
        with self.assertRaises(ValueError): self.store.snapshot()

    def submission(self,**changes):
        from uuid import uuid4
        return {"submission_key":str(uuid4()),"countries":["CAN","FRA"],"scope":"universities_programs",
                "preferences":{"intake":"Fall 2027","funding_priorities":"Need funding"},"remember_preferences":True,
                "limits":"Two examples per country","context":None,"parent_request_id":None,"prior_results":[],**changes}

    def test_successful_submission_remembers_explicit_values_and_freezes_old_snapshots(self):
        payload=self.submission()
        first=self.store.submit(payload)["request"]
        self.assertIsNone(first["preferences"]["country_restrictions"])
        self.assertIsNone(first["profile_reference"])
        self.assertEqual(self.store.submit(payload)["request"],first,"Retry must not duplicate or rewrite a request")
        snapshot=self.store.snapshot()
        self.assertEqual(snapshot["preferences"]["intake"],"Fall 2027")
        self.assertEqual(snapshot["requests"][0]["state"],"prepared")
        self.store.submit(self.submission(preferences={"intake":"Spring 2028"},remember_preferences=False))
        self.assertEqual(self.store.snapshot()["preferences"]["intake"],"Fall 2027")
        self.store.submit(self.submission(preferences={"intake":"Fall 2029","degree_routes":"Master or PhD"}))
        self.assertEqual(self.store.snapshot()["preferences"]["intake"],"Fall 2029")
        self.assertEqual(self.store.request(first["request_id"])["request"],first)
        with closing(self.store.connect()) as db:
            with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE research_requests SET body='{}'")

    def test_invalid_submission_and_ambiguous_retry_do_not_change_remembered_values(self):
        payload=self.submission()
        self.store.submit(payload)
        before=self.store.snapshot()
        for changes in ({"countries":[]},{"scope":"faculty"},{"preferences":{"invented":"restriction"}},
                        {"remember_preferences":"yes"},{"scope":"refresh","parent_request_id":None},
                        {"prior_results":[{"result_id":"unknown"}]}):
            with self.assertRaises(ValueError):self.store.submit(self.submission(**changes))
        with self.assertRaises(ValueError):self.store.submit({**payload,"context":"Changed after the same submission key"})
        self.assertEqual(self.store.snapshot(),before)

    def test_private_handoff_is_immutable_and_prompt_does_not_repeat_preferences(self):
        request=self.store.submit(self.submission(context="SENSITIVE_CONTEXT",preferences={"intake":"PRIVATE_INTAKE"}))["request"]
        exported=self.store.export(request["request_id"])
        from web.research_envelopes import verify
        import json
        file=Path(exported["path"])
        self.assertEqual(verify(json.loads(file.read_text())),request)
        self.assertEqual(file.stat().st_mode & 0o777,0o600)
        self.assertNotIn("PRIVATE_INTAKE",exported["prompt"])
        self.assertNotIn("SENSITIVE_CONTEXT",exported["prompt"])
        self.assertEqual(self.store.export(request["request_id"]),exported)
        index=json.loads((file.parent/"index.json").read_text())
        self.assertNotIn("preferences",str(index))
        file.write_text("existing private contents")
        with self.assertRaises(ValueError):self.store.export(request["request_id"])
        self.assertEqual(file.read_text(),"existing private contents")

    def test_bound_receipts_revision_history_feedback_and_replay_preserve_personal_state(self):
        from uuid import uuid4
        from web.country_evidence import detail
        request=self.store.submit(self.submission())["request"]
        identity=request["request_id"]
        self.store.save_country({"country_code":"CAN","watched":True,"note":"Keep this note"})
        self.workspace.country_decisions("CAN","On hold")
        result1=self.store.demo_response(identity,"result-1")
        with self.assertRaises(ValueError):self.store.receive(result1)
        ack=self.store.demo_response(identity,"accepted")
        self.assertEqual(self.store.snapshot()["requests"][0]["state"],"prepared","Preparing a response must not acknowledge a request")
        self.store.receive(ack)
        self.assertIsNone(self.store.snapshot()["requests"][0]["execution_progress"])
        with self.assertRaises(ValueError):self.store.receive({**result1,"request_digest":"wrong"})
        with self.assertRaises(ValueError):self.store.receive({**result1,"synthetic":False})
        self.store.receive(result1)
        result2=self.store.demo_response(identity,"result-2")
        with self.assertRaises(ValueError):self.store.receive(result2)
        feedback=self.store.feedback(identity,result1["result_id"],1,"country:CAN","Please check the funding route",str(uuid4()))
        self.assertEqual(self.store.export(identity,feedback["feedback_id"])["kind"],"feedback")
        self.store.receive(result2)
        snapshot=self.store.snapshot()
        self.assertFalse(self.store.receive(result2)["changed"])
        self.assertEqual(self.store.snapshot(),snapshot)
        current=self.store.request(identity)
        self.assertEqual(current["results"][0]["envelope"],result1)
        self.assertEqual(current["results"][1]["envelope"],result2)
        self.assertIn("funding_routes",[change["field"] for change in current["results"][1]["changes"]])
        self.assertEqual(detail(self.workspace,None,"CAN")["revision"],"demo-CAN-r2")
        self.assertEqual(detail(self.workspace,None,"CAN")["decision"],"On hold")
        self.assertEqual(self.store.snapshot()["countries"]["CAN"],{"watched":True,"note":"Keep this note"})
        self.assertEqual(hashlib.sha256(self.workspace.database.read_bytes()).hexdigest(),self.before)
        ref={"result_id":result2["result_id"],"revision":2,"digest":result2["digest"],"finding_id":"country:CAN"}
        follow=self.store.submit(self.submission(scope="refresh",parent_request_id=identity,prior_results=[ref]))["request"]
        self.assertEqual(follow["prior_results"],[ref])
        with closing(self.store.connect()) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute("DELETE FROM research_results")

    def test_response_bindings_versions_exact_types_and_old_replay_cannot_downgrade_evidence(self):
        from uuid import uuid4
        from web.research_envelopes import seal
        request=self.store.submit(self.submission())["request"]
        identity=request["request_id"]
        ack=self.store.demo_response(identity,"accepted")
        for invalid in ({**ack,"request_revision":True},{**ack,"private_schema_version":"1.0.0"},
                        {**ack,"request_digest":"0"*64},{**ack,"execution_progress":"running"}):
            with self.assertRaises(ValueError):self.store.receive(invalid)
        self.assertEqual(self.store.snapshot()["requests"][0]["state"],"prepared")
        self.store.receive(ack)
        self.assertFalse(self.store.receive(ack)["changed"])
        before_prefs=self.store.snapshot()["preferences"]
        first=self.store.demo_response(identity,"result-1")
        forged={key:value for key,value in first.items() if key!="digest"}
        forged["findings"]=[{**first["findings"][0],"funding_routes":"An unapproved arbitrary real claim"}]
        with self.assertRaises(ValueError):self.store.receive(seal(forged))
        self.store.receive(first)
        with self.assertRaises(ValueError):self.store.feedback(identity,first["result_id"],1,"country:ATA","Wrong finding",str(uuid4()))
        key=str(uuid4())
        saved=self.store.feedback(identity,first["result_id"],1,"country:CAN","Only funding routes please",key)
        self.assertEqual(self.store.feedback(identity,first["result_id"],1,"country:CAN","Only funding routes please",key),saved)
        with self.assertRaises(ValueError):self.store.feedback(identity,first["result_id"],1,"country:CAN","Changed comment",key)
        self.store.receive(self.store.demo_response(identity,"result-2"))
        self.assertFalse(self.store.receive(first)["changed"])
        self.assertEqual(self.store.latest_country("CAN")["source_revision"],"demo-CAN-r2")
        self.assertEqual(self.store.snapshot()["preferences"],before_prefs)

    def test_explicit_rejection_and_clarification_do_not_claim_execution(self):
        for state in ("rejected","needs_clarification"):
            request=self.store.submit(self.submission())["request"]
            self.store.receive(self.store.demo_response(request["request_id"],state))
            row=next(item for item in self.store.snapshot()["requests"] if item["request_id"]==request["request_id"])
            self.assertEqual(row["state"],state)
            self.assertIsNone(row["execution_progress"])
            with self.assertRaises(ValueError):self.store.receive(self.store.demo_response(request["request_id"],"result-1"))
