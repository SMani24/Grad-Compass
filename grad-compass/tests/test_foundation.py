"""Regression tests use invented files in an explicit temporary runtime only."""
import importlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grad-compass-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "runtime"
        env = patch.dict(os.environ, {"GRAD_COMPASS_DATA_DIR": str(self.root), "GRAD_COMPASS_OFFLINE": "1"})
        env.start()
        self.addCleanup(env.stop)
        self.paths = importlib.reload(importlib.import_module("core.paths"))
        self.vault = importlib.reload(importlib.import_module("core.vault"))
        self.db = importlib.reload(importlib.import_module("core.database"))
        self.assertTrue(self.db.DB_PATH.is_relative_to(self.root))
        self.assertNotEqual(self.db.DB_PATH, APP_ROOT / "data" / "grad_compass.db")
        self.db.init_db()

    def query(self, sql, values=()):
        conn = self.db._connect()
        try:
            with conn:
                return conn.execute(sql, values).fetchall()
        finally:
            conn.close()

    def university(self, name="Invented University"):
        return self.db.db_add_university("CAN", name, "Invented City", 0.0, 1.0, "2027-01-01", "https://example.invalid")

    def attachment(self, parent_id, content="invented file", kind="university"):
        source_dir = Path(self.temp.name) / ("source-" + str(len(list(Path(self.temp.name).glob('source-*')))))
        source_dir.mkdir()
        source = source_dir / "document.txt"
        source.write_text(content)
        stored = self.vault.store_file(str(source), kind, parent_id)
        self.db.db_add_attachment(kind, parent_id, stored["file_name"], stored["stored_path"])
        return stored, self.paths.FILE_ROOT / stored["stored_path"]

    def test_storage_isolated_and_foreign_keys_enabled(self):
        self.assertEqual(self.paths.CONFIG_PATH.parent, self.root)
        self.assertEqual(self.paths.CACHE_DIR, self.root / "cache" / "images")
        self.assertEqual(self.paths.VAULT_DIR, self.root / "vault")
        self.assertEqual(self.query("PRAGMA foreign_keys"), [(1,)])
        self.assertEqual(self.query("PRAGMA user_version"), [(1,)])
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.db_add_professor(999, "Invented Orphan", "", "", "Not Contacted")

    def test_university_delete_cleans_professor_only_tasks_and_documents(self):
        uni = self.university()
        other = self.university("Other Invented University")
        prof = self.db.db_add_professor(uni, "Invented Professor", "", "", "Not Contacted")
        self.db.db_add_task("Professor-only task", prof_id=prof)
        self.db.db_add_task("University task", uni_id=uni)
        self.db.db_add_task("Unrelated task", uni_id=other)
        _, file = self.attachment(prof, kind="professor")
        self.paths.CACHE_DIR.mkdir(parents=True)
        cache = self.paths.CACHE_DIR / f"{uni}.jpg"
        cache.write_bytes(b"invented cache bytes")
        self.db.db_delete_university(uni)
        self.assertFalse(file.exists())
        self.assertFalse(cache.exists())
        self.assertEqual(self.query("SELECT COUNT(*) FROM professors"), [(0,)])
        self.assertEqual(self.query("SELECT title FROM tasks"), [("Unrelated task",)])
        self.assertEqual(self.query("PRAGMA foreign_key_check"), [])
        self.assertIsNotNone(self.db.db_get_university(other))

    def test_professor_delete_preserves_other_contacts(self):
        uni = self.university()
        first = self.db.db_add_professor(uni, "First Invented Professor", "", "", "Not Contacted")
        second = self.db.db_add_professor(uni, "Second Invented Professor", "", "", "Not Contacted")
        self.db.db_add_task("First task", prof_id=first)
        self.db.db_add_task("Second task", prof_id=second)
        _, file = self.attachment(first, kind="professor")
        self.db.db_delete_professor(first)
        self.assertFalse(file.exists())
        self.assertEqual(self.query("SELECT professor_id FROM tasks"), [(second,)])
        self.assertEqual(self.query("SELECT id FROM professors"), [(second,)])

    def test_database_delete_failure_keeps_files_and_all_metadata(self):
        uni = self.university()
        _, file = self.attachment(uni)
        self.db.db_add_task("Preserved task", uni_id=uni)
        self.query("CREATE TRIGGER reject_delete BEFORE DELETE ON universities BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.db_delete_university(uni)
        self.assertTrue(file.is_file())
        self.assertEqual(self.query("SELECT COUNT(*) FROM attachments"), [(1,)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM tasks"), [(1,)])
        self.assertIsNotNone(self.db.db_get_university(uni))

    def test_same_filename_does_not_overwrite_an_attachment(self):
        uni = self.university()
        a, first = self.attachment(uni, "first invented content")
        b, second = self.attachment(uni, "second invented content")
        self.assertEqual(a["file_name"], b["file_name"])
        self.assertNotEqual(a["stored_path"], b["stored_path"])
        self.assertEqual(first.read_text(), "first invented content")
        self.assertEqual(second.read_text(), "second invented content")
        self.assertEqual(first.stat().st_mode & 0o777, 0o600)

    def test_shared_legacy_file_remains_until_last_attachment_is_deleted(self):
        uni = self.university()
        stored, file = self.attachment(uni)
        self.db.db_add_attachment("university", uni, stored["file_name"], stored["stored_path"])
        records = self.db.db_get_attachments("university", uni)
        self.db.db_delete_attachment(records[0]["id"])
        self.assertTrue(file.is_file())
        self.db.db_delete_attachment(records[1]["id"])
        self.assertFalse(file.exists())

    def test_vault_paths_do_not_open_or_delete_outside_files(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("invented outside content")
        for value in (str(outside), "../outside.txt", "config.json"):
            with self.subTest(path=value):
                self.assertFalse(self.vault.delete_stored_file(value))
                with patch.object(self.vault.subprocess, "run") as launch:
                    self.assertFalse(self.vault.open_system_file(value))
                    launch.assert_not_called()
        uni = self.university()
        self.db.db_add_attachment("university", uni, "bad path", str(outside))
        self.db.db_delete_university(uni)
        self.assertTrue(outside.is_file())

    def test_vault_rejects_symlink_and_invalid_parent(self):
        uni = self.university()
        _, original = self.attachment(uni)
        link = original.parent / "linked.txt"
        link.symlink_to(original)
        self.assertFalse(self.vault.delete_stored_file(str(link.relative_to(self.root))))
        self.assertTrue(original.is_file())
        for kind, parent in (("../escape", 1), ("university", "../escape"), ("professor", 0)):
            with self.assertRaises(ValueError):
                self.vault.store_file(str(original), kind, parent)

    def test_legacy_schema_and_values_survive_initialization(self):
        uni = self.university()
        prof = self.db.db_add_professor(uni, "Legacy Invented Professor", "", "", "Cold Emailed")
        self.query("ALTER TABLE countries ADD COLUMN notes TEXT")
        self.query("UPDATE countries SET notes='invented legacy country note'")
        self.query("ALTER TABLE professors ADD COLUMN last_contacted_date TEXT")
        self.query("UPDATE professors SET last_contacted_date='2026-10-01' WHERE id=?", (prof,))
        self.query("PRAGMA user_version=0")
        self.db.init_db()
        self.db.init_db()
        self.assertEqual(self.query("SELECT notes FROM countries"), [("invented legacy country note",)])
        self.assertEqual(self.query("SELECT last_contacted_date FROM professors WHERE id=?", (prof,)), [("2026-10-01",)])
        self.assertEqual(self.db.db_get_university(uni)["id"], uni)

    def test_image_column_is_added_to_old_schema(self):
        self.query("ALTER TABLE universities DROP COLUMN image_url")
        self.query("PRAGMA user_version=0")
        self.db.init_db()
        self.assertIn("image_url", {row[1] for row in self.query("PRAGMA table_info(universities)")})

    def test_unknown_schema_version_is_not_rewritten(self):
        self.query("PRAGMA user_version=99")
        with self.assertRaises(ValueError):
            self.db.init_db()
        self.assertEqual(self.query("PRAGMA user_version"), [(99,)])

    def test_database_substitution_is_rejected_before_open(self):
        outside = Path(self.temp.name) / "pretend-production.db"
        outside.write_bytes(b"must not be opened as sqlite")
        alias = self.root / "alias.db"
        alias.hardlink_to(outside)
        with patch.object(self.paths, "LEGACY_DB_PATH", outside):
            with self.assertRaises(ValueError):
                self.paths.validate_database_path(alias)
        alias.unlink()
        alias.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.paths.validate_database_path(alias)
        self.assertEqual(outside.read_bytes(), b"must not be opened as sqlite")

    def test_protected_runtime_roots_are_rejected(self):
        for directory in (APP_ROOT / "data", APP_ROOT / "data" / "nested", APP_ROOT.parent / "grad-compass-research-engine" / "private", APP_ROOT.parent / "grad-compass-exchange"):
            env = {**os.environ, "GRAD_COMPASS_DATA_DIR": str(directory)}
            result = subprocess.run([sys.executable, "-B", "-c", "import core.paths"], cwd=APP_ROOT, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Development storage must be separate", result.stderr)

    def test_offline_enrichment_makes_no_network_calls(self):
        geocoder = importlib.reload(importlib.import_module("core.geocoder"))
        with patch.object(geocoder.geolocator, "geocode") as lookup, patch.object(geocoder.urllib.request, "urlopen") as download:
            self.assertEqual(geocoder.geocode_institution("Invented", "Canada"), (None, None))
            self.assertIsNone(geocoder.fetch_and_cache_university_photo(1, "Invented"))
            lookup.assert_not_called()
            download.assert_not_called()
            self.assertFalse(self.paths.CACHE_DIR.exists())

    def test_configuration_writes_only_to_development_storage(self):
        app = importlib.reload(importlib.import_module("app"))
        self.assertEqual(app.CONFIG_PATH, self.paths.CONFIG_PATH)
        app.save_config({"font_scale": "Large"})
        self.assertEqual(app.load_config()["font_scale"], "Large")
        self.assertTrue(self.paths.CONFIG_PATH.is_file())

    def test_development_config_link_is_rejected_without_overwriting_target(self):
        app = importlib.reload(importlib.import_module("app"))
        outside = Path(self.temp.name) / "outside-config.json"
        outside.write_text('{"font_scale":"Normal"}')
        self.paths.CONFIG_PATH.symlink_to(outside)
        with self.assertRaises(ValueError):
            app.save_config({"font_scale": "Large"})
        self.assertEqual(outside.read_text(), '{"font_scale":"Normal"}')

    def test_demo_creation_uses_explicit_storage_and_refuses_overwrite(self):
        directory = Path(self.temp.name) / "demo"
        command = [sys.executable, "-B", str(APP_ROOT / "scripts" / "create_demo.py"), str(directory)]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        database = directory / "grad_compass.db"
        before = database.read_bytes()
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM universities").fetchone()[0], 3)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("existing data will not be replaced", second.stderr)
        self.assertEqual(database.read_bytes(), before)

    def test_migration_failure_rolls_back_created_tables_and_version(self):
        # A view occupying the legacy table name makes the additive upgrade fail.
        self.query("DROP TABLE attachments")
        self.query("DROP TABLE tasks")
        self.query("DROP TABLE professors")
        self.query("DROP TABLE universities")
        self.query("CREATE VIEW universities AS SELECT 'invented' AS name")
        self.query("PRAGMA user_version=0")
        with self.assertRaises(sqlite3.OperationalError):
            self.db.init_db()
        self.assertEqual(self.query("PRAGMA user_version"), [(0,)])
        self.assertEqual(self.query("SELECT name FROM sqlite_master WHERE type='table' AND name='professors'"), [])


if __name__ == "__main__":
    unittest.main()
