"""Committed research discovery without copying or writing the map database."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))
from web.server import DemoWorkspace
from web.exchange_workflow import BATCH_ID, SyntheticExchangeWorkflow
from web.discovery import overview, university

INSTITUTION = "11111111-1111-4111-8111-111111111111"


class DiscoveryExchangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        subprocess.run([sys.executable, "-B", str(APP_ROOT / "scripts/create_demo.py"), str(root / "map")], check=True, capture_output=True)
        self.workspace = DemoWorkspace(root / "map")
        self.exchange = SyntheticExchangeWorkflow(root / "exchange", clock=lambda: datetime(2026,10,13,tzinfo=timezone.utc))
        self.map_digest = hashlib.sha256(self.workspace.database.read_bytes()).hexdigest()

    def promote(self, create=True):
        self.exchange.stage(BATCH_ID)
        self.exchange.map(BATCH_ID, INSTITUTION, create=create, local_id=None if create else 1)
        preview = self.exchange.preview(BATCH_ID)
        self.exchange.promote(BATCH_ID, preview["preview"]["id"], True)

    def test_staging_and_dry_run_do_not_appear_in_discovery(self):
        self.assertEqual(len(overview(self.workspace, self.exchange)["universities"]), 3)
        self.exchange.stage(BATCH_ID)
        self.exchange.map(BATCH_ID, INSTITUTION, create=True)
        self.exchange.preview(BATCH_ID)
        self.assertEqual(len(overview(self.workspace, self.exchange)["universities"]), 3)
        self.assertIsNone(university(self.workspace, self.exchange, "exchange-2"))

    def test_committed_records_have_stable_identity_parent_and_no_fabricated_coordinates(self):
        self.promote()
        rows = overview(self.workspace, self.exchange)["universities"]
        self.assertEqual(len(rows), 4)
        detail = university(self.workspace, self.exchange, "exchange-2")
        self.assertEqual(detail["university"]["name"], "Example North University")
        self.assertIsNone(detail["university"]["latitude"])
        self.assertIsNone(detail["university"]["longitude"])
        self.assertEqual(detail["university"]["status"], "Researching")
        self.assertEqual(detail["university"]["research"]["review"], "accepted")
        self.assertEqual([p["name"] for p in detail["programs"]], ["MSc Example Studies"])
        self.assertEqual(len(detail["programs"][0]["requirements"]), 1)
        self.assertEqual(detail["programs"][0]["requirements"][0]["kind"], "application_deadline")
        for _ in range(2):
            self.assertTrue(self.exchange.replay(BATCH_ID)["replay"]["no_changes"])
            self.assertEqual(overview(self.workspace, self.exchange)["universities"], rows)
            self.assertEqual(university(self.workspace, self.exchange, "exchange-2"), detail)
        reopened = SyntheticExchangeWorkflow(self.exchange.directory)
        self.assertEqual(university(self.workspace, reopened, "exchange-2"), detail)
        self.assertEqual(hashlib.sha256(self.workspace.database.read_bytes()).hexdigest(), self.map_digest)

    def test_existing_mapping_is_distinct_from_same_integer_in_map_database(self):
        self.promote(create=False)
        rows = overview(self.workspace, self.exchange)["universities"]
        self.assertEqual(len({row["id"] for row in rows}), 4)
        self.assertEqual(university(self.workspace, self.exchange, "exchange-1")["university"]["name"], "Existing Demo University")
        self.assertEqual(university(self.workspace, self.exchange, "1")["university"]["name"], "Northbridge Example University")

    def test_country_decision_is_independent_of_promoted_research_and_application_stage(self):
        from web.country_evidence import detail
        self.promote()
        before = overview(self.workspace,self.exchange)
        exchange_digest = hashlib.sha256(self.exchange.database.read_bytes()).hexdigest()
        self.workspace.country_decisions("CAN", "Excluded")
        self.assertEqual(overview(self.workspace,self.exchange),before)
        self.assertEqual(detail(self.workspace,self.exchange,"CAN")["decision"],"Excluded")
        self.assertEqual(detail(self.workspace,self.exchange,"CAN")["university_count"],3)
        promoted = university(self.workspace,self.exchange,"exchange-2")["university"]
        self.assertEqual(promoted["research"]["review"],"accepted")
        self.assertEqual(promoted["status"],"Researching")
        self.assertEqual(hashlib.sha256(self.exchange.database.read_bytes()).hexdigest(),exchange_digest)
        self.assertEqual(hashlib.sha256(self.workspace.database.read_bytes()).hexdigest(),self.map_digest)
