"""App consumer tests with disposable invented databases and finalized fixture copies."""
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))
from web.exchange_workflow import BATCH_ID, SyntheticExchangeWorkflow
from web.server import handler_for

INSTITUTION = "11111111-1111-4111-8111-111111111111"


class ExchangeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="grad-compass-workflow-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        self.workflow = SyntheticExchangeWorkflow(Path(self.temporary.name) / "exchange", clock=lambda: self.now)

    def fingerprint(self):
        return hashlib.sha256(self.workflow.database.read_bytes()).hexdigest()

    def mapped(self, create=True):
        self.workflow.stage(BATCH_ID)
        self.workflow.map(BATCH_ID, INSTITUTION, create=create, local_id=None if create else 1)
        return self.workflow.preview(BATCH_ID)

    def test_end_to_end_create_promote_and_replay_has_no_duplicate_or_byte_changes(self):
        preview = self.mapped()
        self.assertTrue(preview["preview"]["ready"])
        self.assertEqual([change["kind"] for change in preview["preview"]["changes"]], ["institutions", "programs"])
        self.assertEqual(len(preview["saved_institutions"]), 1, "Dry run must not create rows in the source DB")
        result = self.workflow.promote(BATCH_ID, preview["preview"]["id"], True)
        self.assertEqual(len(result["saved_institutions"]), 2)
        self.assertEqual(len(result["saved_programs"]), 1)
        self.assertEqual(result["receipt"]["outcomes"]["promoted"], 2)
        self.assertEqual(result["receipt"]["outcomes"]["skipped"], 3)
        self.assertEqual(result["programs"][0]["requirements"]["funding:2027-fall"], "unknown")
        self.assertEqual(result["programs"][0]["requirements"]["application_deadline:2027-fall"], "promoted")
        before = self.fingerprint()
        for _ in range(2):
            replay = self.workflow.replay(BATCH_ID)
            self.assertTrue(replay["replay"]["no_changes"])
            self.assertEqual(replay["replay"]["institutions"], 2)
            self.assertEqual(replay["replay"]["programs"], 1)
        self.assertEqual(self.fingerprint(), before)
        reopened = SyntheticExchangeWorkflow(self.workflow.directory, clock=lambda: self.now)
        self.assertTrue(reopened.state(BATCH_ID)["receipt"]["promotion_committed"])

    def test_existing_mapping_keeps_local_fields_and_pending_records_staged(self):
        original = self.workflow.state(BATCH_ID)["saved_institutions"][0]
        preview = self.mapped(create=False)
        self.assertIn("Link existing", preview["preview"]["changes"][-1]["action"])
        self.assertEqual(preview["preview"]["changes"][-1]["before"], preview["preview"]["changes"][-1]["after"])
        result = self.workflow.promote(BATCH_ID, preview["preview"]["id"], True)
        self.assertEqual(result["saved_institutions"], [original])
        self.assertEqual(result["institutions"][1]["storage"], "staged")
        self.assertTrue(all(row["storage"] == "staged" for row in result["programs"][1:]))

    def test_missing_mapping_and_explicit_approval_are_enforced(self):
        self.workflow.stage(BATCH_ID)
        fingerprint = self.fingerprint()
        preview = self.workflow.preview(BATCH_ID)
        self.assertEqual(self.fingerprint(), fingerprint)
        self.assertFalse(preview["preview"]["ready"])
        with self.assertRaises(ValueError):
            self.workflow.promote(BATCH_ID, preview["preview"]["id"], True)
        preview = self.mapped()
        with self.assertRaises(ValueError):
            self.workflow.promote(BATCH_ID, preview["preview"]["id"], False)
        self.assertIsNone(self.workflow.state(BATCH_ID)["receipt"]["decision"])

    def test_mapping_change_invalidates_dry_run_and_freshness_is_rechecked(self):
        self.workflow.stage(BATCH_ID)
        old = self.workflow.preview(BATCH_ID)
        self.workflow.map(BATCH_ID, INSTITUTION, create=True)
        with self.assertRaises(ValueError): self.workflow.promote(BATCH_ID, old["preview"]["id"], True)
        ready = self.workflow.preview(BATCH_ID)
        self.now += timedelta(days=60)
        with self.assertRaises(ValueError): self.workflow.promote(BATCH_ID, ready["preview"]["id"], True)
        stale = self.workflow.preview(BATCH_ID)
        self.assertEqual(stale["preview"]["projected"]["programs"][0]["requirements"]["application_deadline:2027-fall"], "stale")

    def test_real_or_modified_batches_and_unsafe_workspaces_are_rejected(self):
        with self.assertRaises(ValueError): self.workflow.stage("/private/real-batch")
        with self.assertRaises(ValueError): SyntheticExchangeWorkflow(APP_ROOT / "data")
        original = self.workflow.batch / "institutions.jsonl"
        original.write_bytes(original.read_bytes().replace(b"Example North", b"Changed North"))
        with self.assertRaises(ValueError): self.workflow.stage(BATCH_ID)
        self.assertIsNone(self.workflow.state(BATCH_ID)["receipt"])
        unmarked = Path(self.temporary.name) / "unmarked"
        unmarked.mkdir()
        (unmarked / "exchange.sqlite").write_bytes(b"existing file")
        with self.assertRaises(ValueError): SyntheticExchangeWorkflow(unmarked)
        self.assertEqual((unmarked / "exchange.sqlite").read_bytes(), b"existing file")

    def test_marker_and_hard_link_substitution_are_rejected_before_mutation(self):
        with sqlite3.connect(self.workflow.database) as connection:
            connection.execute("DELETE FROM app_exchange_ui_guard")
        with self.assertRaises(ValueError): self.workflow.stage(BATCH_ID)
        with sqlite3.connect(self.workflow.database) as connection:
            connection.execute("INSERT INTO app_exchange_ui_guard VALUES('grad-compass-exchange-ui-v1')")
        import os
        os.link(self.workflow.database, Path(self.temporary.name) / "linked.sqlite")
        with self.assertRaises(ValueError): self.workflow.stage(BATCH_ID)

    def route(self, path, payload, **headers):
        handler = object.__new__(handler_for(None, self.workflow, "test-session"))
        handler.path = path
        raw = json.dumps(payload).encode()
        handler.headers = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "Content-Type": "application/json", "Content-Length": str(len(raw)), "X-Grad-Compass-Session": "test-session", **headers}
        handler.server = SimpleNamespace(server_port=8765)
        handler.rfile = io.BytesIO(raw)
        result = {}
        handler.respond = lambda status, payload: result.update(status=status, payload=payload)
        handler.do_POST()
        return result

    def test_http_boundary_requires_app_session_and_known_action_payloads(self):
        path = "/api/exchange/stage"
        before = self.fingerprint()
        self.assertEqual(self.route(path, {"batch_id": BATCH_ID}, Origin="https://other.example")["status"], 403)
        self.assertEqual(self.route(path, {"batch_id": BATCH_ID}, **{"X-Grad-Compass-Session": "wrong"})["status"], 403)
        self.assertEqual(self.route(path, {"batch_id": BATCH_ID, "database": "/private/real.sqlite"})["status"], 409)
        self.assertEqual(self.fingerprint(), before)
        self.assertEqual(self.route(path, {"batch_id": BATCH_ID})["status"], 200)


if __name__ == "__main__":
    unittest.main()
