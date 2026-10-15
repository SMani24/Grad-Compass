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
