"""Importer tests use only an explicit temporary, invented SQLite database."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import exporter
spec = importlib.util.spec_from_file_location("exchange_importer", ROOT.parent / "grad-compass/core/exchange_importer.py")
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

FIXTURE = ROOT / "examples" / "batch-66666666-6666-4666-8666-666666666666"


class SyntheticImporterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-importer-")
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "synthetic.sqlite"
        self.assertTrue(self.db_path.parent.is_dir())
        self.assertNotEqual(self.db_path.resolve(), importer.APP_DB)
        self.assertFalse(self.db_path.exists())
        with sqlite3.connect(self.db_path) as db:
            db.executescript("""
            CREATE TABLE exchange_synthetic_test_guard(marker TEXT NOT NULL);
            INSERT INTO exchange_synthetic_test_guard VALUES('grad-compass-exchange-synthetic-test-v1');
            CREATE TABLE countries(code TEXT PRIMARY KEY,name TEXT NOT NULL);
            CREATE TABLE universities(id INTEGER PRIMARY KEY,country_code TEXT NOT NULL,name TEXT NOT NULL,city TEXT,
                latitude REAL,longitude REAL,portal_url TEXT,deadline TEXT,status TEXT,image_url TEXT);
            CREATE TABLE professors(id INTEGER PRIMARY KEY,university_id INTEGER,name TEXT);
            CREATE TABLE tasks(id INTEGER PRIMARY KEY,university_id INTEGER,title TEXT);
            CREATE TABLE attachments(id INTEGER PRIMARY KEY,parent_type TEXT,parent_id INTEGER,file_name TEXT,stored_path TEXT);
            CREATE TABLE applicant_profile(id INTEGER PRIMARY KEY,private_note TEXT);
            CREATE TABLE cv(id INTEGER PRIMARY KEY,private_note TEXT);
            INSERT INTO countries VALUES('CAN','Canada');
            INSERT INTO universities VALUES(7,'CAN','Local university','Local City',1.2,3.4,'https://local.example',
                '2028-01-01','Researching','cache/local.jpg');
            INSERT INTO professors VALUES(1,7,'Local professor');
            INSERT INTO tasks VALUES(1,7,'Local task');
            INSERT INTO attachments VALUES(1,'university',7,'local.pdf','private/local.pdf');
            INSERT INTO applicant_profile VALUES(1,'private profile');
            INSERT INTO cv VALUES(1,'private cv');
            """)
        importer.migrate(self.db_path)

    def _db(self):
        self.assertTrue(self.db_path.is_file())
        self.assertNotEqual(self.db_path.resolve(), importer.APP_DB)
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _stage_decide(self, directory=FIXTURE):
        diff = importer.dry_run(self.db_path, directory)
        importer.stage(self.db_path, directory)
        importer.decide(self.db_path, diff["batch_id"], diff["manifest_digest"], "synthetic-operator", approve=True)
        return diff

    def _batch(self, institutions=None, programs=None, batch_id="77777777-7777-4777-8777-777777777777"):
        """Construct a valid changed synthetic batch in this test's temporary directory."""
        directory = Path(self.tmp.name) / ("batch-" + batch_id)
        directory.mkdir()
        for name, records in (("institutions.jsonl",institutions),("programs.jsonl",programs)):
            if records is None:
                records = [json.loads(line) for line in (FIXTURE / name).read_text().splitlines()]
            (directory / name).write_bytes(b"".join((json.dumps(r,separators=(",",":")).encode()+b"\n") for r in records))
        manifest = json.loads((FIXTURE / "manifest.json").read_text())
        manifest["batch_id"] = batch_id
        manifest["sha256"] = {name: hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ("institutions.jsonl","programs.jsonl")}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return directory

    def test_path_guards_and_validation_before_write(self):
        with self.assertRaises(ValueError): importer.migrate(None)
        with self.assertRaises(ValueError): importer.migrate(importer.APP_DB)
        missing = Path(self.tmp.name) / "missing.sqlite"
        with self.assertRaises(ValueError): importer.migrate(missing)
        self.assertFalse(missing.exists())
        alternate = Path(self.tmp.name) / "alternate.sqlite"
        with sqlite3.connect(alternate) as db:
            db.execute("CREATE TABLE universities(id INTEGER, country_code TEXT, name TEXT, city TEXT, portal_url TEXT)")
        with self.assertRaisesRegex(ValueError, "synthetic test data"):
            importer.migrate(alternate)
        with sqlite3.connect(alternate) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='exchange_schema_meta'").fetchone())
        with self.assertRaises(ValueError): importer.stage(self.db_path, Path(self.tmp.name)/"missing")
        diff = importer.dry_run(self.db_path,FIXTURE)
        self.assertEqual(diff["received"],5)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM exchange_batches").fetchone()[0],0)

    def test_published_synthetic_batch_end_to_end(self):
        outbox = Path(self.tmp.name)/"outbox"
        outbox.mkdir()
        published = exporter.publish_synthetic_fixture(outbox)
        diff = importer.dry_run(self.db_path,published)
        importer.stage(self.db_path,published)
        importer.map_institution(self.db_path,diff["batch_id"],"11111111-1111-4111-8111-111111111111",local_id=7)
        importer.decide(self.db_path,diff["batch_id"],diff["manifest_digest"],"synthetic-operator",approve=True)
        result = importer.promote(self.db_path,diff["batch_id"],diff["manifest_digest"],now=importer.datetime(2026,10,9,tzinfo=importer.timezone.utc))
        self.assertEqual(result["received"],5)
        self.assertEqual(result["outcomes"]["promoted"],2)
        self.assertEqual(exporter.publish_synthetic_fixture(outbox),published)

    def test_replay_decision_promotion_crash_and_unaffected_rows(self):
        diff = self._stage_decide()
        before = importer.receipt(self.db_path,diff["batch_id"])
        self.assertEqual(before["outcomes"]["staged"],5)
        self.assertEqual(importer.stage(self.db_path,FIXTURE),before)
        importer.map_institution(self.db_path,diff["batch_id"],"11111111-1111-4111-8111-111111111111",local_id=7)
        with self.assertRaises(RuntimeError):
            importer.promote(self.db_path,diff["batch_id"],diff["manifest_digest"],
                             now=importer.datetime(2026,10,9,tzinfo=importer.timezone.utc),
                             after_commit=lambda: (_ for _ in ()).throw(RuntimeError("synthetic crash")))
        receipt = importer.receipt(self.db_path,diff["batch_id"])
        self.assertTrue(receipt["promotion_committed"])
        self.assertEqual(receipt["outcomes"]["promoted"],2)
        self.assertEqual(receipt["outcomes"]["skipped"],3)
        self.assertEqual(importer.promote(self.db_path,diff["batch_id"],diff["manifest_digest"]),receipt)
        receipt_dir = Path(self.tmp.name)/"receipts"
        receipt_dir.mkdir()
        written = importer.write_receipt(self.db_path,diff["batch_id"],receipt_dir)
        self.assertEqual(json.loads(written.read_text()),receipt)
        self.assertEqual(importer.write_receipt(self.db_path,diff["batch_id"],receipt_dir),written)
        with self._db() as db:
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(),[])
            self.assertEqual(db.execute("SELECT name,status,deadline,latitude,image_url FROM universities WHERE id=7").fetchone()[:],
                             ("Local university","Researching","2028-01-01",1.2,"cache/local.jpg"))
            self.assertEqual(db.execute("SELECT count(*) FROM programs").fetchone()[0],1)
            for table in ("professors","tasks","attachments","applicant_profile","cv"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0],1)
            requirements = json.loads(db.execute("SELECT requirements_json FROM programs").fetchone()[0])
            self.assertEqual([r["kind"] for r in requirements],["application_deadline"])

    def test_changed_digest_and_rollback(self):
        diff = self._stage_decide()
        directory = Path(self.tmp.name)/FIXTURE.name
        directory.mkdir()
        for name in ("institutions.jsonl","programs.jsonl","manifest.json"):
            (directory/name).write_bytes((FIXTURE/name).read_bytes())
        manifest = json.loads((directory/"manifest.json").read_text())
        manifest["created_at"] = "2026-10-10T00:00:00Z"
        (directory/"manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): importer.stage(self.db_path,directory)
        with self.assertRaises(ValueError): importer.promote(self.db_path,diff["batch_id"],"0"*64)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM programs").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM exchange_batches").fetchone()[0],1)

    def test_changed_facts_require_new_record_revision(self):
        importer.stage(self.db_path,FIXTURE)
        institutions = [json.loads(line) for line in (FIXTURE/"institutions.jsonl").read_text().splitlines()]
        institutions[0]["name"] = "Changed synthetic name"
        # Its source revision and review binding are deliberately unchanged.
        changed = self._batch(institutions=institutions)
        with self.assertRaisesRegex(ValueError,"revision reused"):
            importer.stage(self.db_path,changed)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM exchange_batches").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM exchange_record_revisions").fetchone()[0],5)

    def test_create_mapping_pending_conflict_stale_and_local_edit(self):
        institutions = [json.loads(line) for line in (FIXTURE/"institutions.jsonl").read_text().splitlines()]
        programs = [json.loads(line) for line in (FIXTURE/"programs.jsonl").read_text().splitlines()]
        programs[0]["requirements"][0]["observed_at"] = "2026-07-01T00:00:00Z"
        programs[0]["requirements"][1]["value"] = "synthetic funding"
        programs[0]["requirements"][1]["observed_at"] = "2026-07-01T00:00:00Z"
        directory = self._batch(institutions,programs)
        diff = self._stage_decide(directory)
        importer.map_institution(self.db_path,diff["batch_id"],institutions[0]["id"],create=True)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM universities").fetchone()[0],1)
        result = importer.promote(self.db_path,diff["batch_id"],diff["manifest_digest"],now=importer.datetime(2026,10,9,tzinfo=importer.timezone.utc))
        self.assertEqual(result["outcomes"]["promoted"],2)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM universities").fetchone()[0],2)
            self.assertEqual(json.loads(db.execute("SELECT requirements_json FROM programs").fetchone()[0]),[])
            outcomes = json.loads(db.execute("SELECT requirement_outcomes_json FROM exchange_staged_programs WHERE external_id=?", (programs[0]["id"],)).fetchone()[0])
            self.assertEqual(outcomes["application_deadline:2027-fall"],"stale")
            self.assertEqual(outcomes["funding:2027-fall"],"stale")
        # A later approved revision must not overwrite a local program edit.
        programs[0]["name"] = "Revised synthetic name"
        programs[0]["record_revision"] = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb9"
        programs[0]["review"]["bound_revision"] = programs[0]["record_revision"]
        with self._db() as db:
            db.execute("UPDATE programs SET name='Local program edit'")
        second = self._batch_second(institutions,programs)
        next_diff = self._stage_decide(second)
        result = importer.promote(self.db_path,next_diff["batch_id"],next_diff["manifest_digest"])
        self.assertEqual(result["outcomes"]["conflict"],1)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT name FROM programs").fetchone()[0],"Local program edit")

    def _batch_second(self, institutions, programs):
        return self._batch(institutions,programs,"88888888-8888-4888-8888-888888888888")

    def test_transaction_rollback_on_bad_mapping_and_foreign_keys(self):
        diff = self._stage_decide()
        with self.assertRaises(ValueError):
            importer.map_institution(self.db_path,diff["batch_id"],"11111111-1111-4111-8111-111111111111",local_id=999)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM exchange_id_map").fetchone()[0],0)
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0],1)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO programs(university_id,name,degree_level) VALUES(999,'bad','master')")

    def test_promotion_rolls_back_every_write_on_insert_failure(self):
        diff = self._stage_decide()
        importer.map_institution(self.db_path,diff["batch_id"],"11111111-1111-4111-8111-111111111111",create=True)
        with self._db() as db:
            db.execute("CREATE TRIGGER reject_synthetic_program BEFORE INSERT ON programs BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            importer.promote(self.db_path,diff["batch_id"],diff["manifest_digest"])
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM universities").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM programs").fetchone()[0],0)
            self.assertIsNone(db.execute("SELECT local_id FROM exchange_id_map WHERE kind='institution'").fetchone()[0])
            self.assertIsNone(db.execute("SELECT promoted_at FROM exchange_batches").fetchone()[0])
            self.assertEqual(db.execute("SELECT count(*) FROM exchange_staged_institutions WHERE outcome='staged'").fetchone()[0],2)

    def test_conflict_state_and_expired_intake_claim(self):
        institutions = [json.loads(line) for line in (FIXTURE/"institutions.jsonl").read_text().splitlines()]
        programs = [json.loads(line) for line in (FIXTURE/"programs.jsonl").read_text().splitlines()]
        institutions[0]["verification"] = "conflict"
        institutions[0]["review"] = {"state":"pending"}
        programs[0]["requirements"][0]["value"] = "2026-10-01"
        directory = self._batch(institutions,programs)
        diff = self._stage_decide(directory)
        result = importer.promote(self.db_path,diff["batch_id"],diff["manifest_digest"],now=importer.datetime(2026,10,9,tzinfo=importer.timezone.utc))
        self.assertEqual(result["outcomes"]["skipped"],4)
        self.assertEqual(result["outcomes"]["parent_mapping_required"],1)
        with self._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM programs").fetchone()[0],0)

    def test_expired_intake_claim_stays_staged(self):
        programs = [json.loads(line) for line in (FIXTURE/"programs.jsonl").read_text().splitlines()]
        programs[0]["requirements"][0]["value"] = "2026-10-01"
        directory = self._batch(programs=programs)
        diff = self._stage_decide(directory)
        importer.map_institution(self.db_path,diff["batch_id"],"11111111-1111-4111-8111-111111111111",local_id=7)
        importer.promote(self.db_path,diff["batch_id"],diff["manifest_digest"],now=importer.datetime(2026,10,9,tzinfo=importer.timezone.utc))
        with self._db() as db:
            claims = json.loads(db.execute("SELECT requirements_json FROM programs").fetchone()[0])
            self.assertEqual(claims,[])
            outcomes = json.loads(db.execute("SELECT requirement_outcomes_json FROM exchange_staged_programs WHERE external_id=?",(programs[0]["id"],)).fetchone()[0])
            self.assertEqual(outcomes["application_deadline:2027-fall"],"expired")


if __name__ == "__main__": unittest.main()
