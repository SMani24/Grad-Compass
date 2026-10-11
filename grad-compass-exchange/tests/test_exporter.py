import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import ROOT, validate_batch  # noqa: E402
from exporter import publish_synthetic_fixture  # noqa: E402


FIXTURE = ROOT / "examples" / "batch-66666666-6666-4666-8666-666666666666"


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.outbox = Path(self.temporary.name) / "outbox"
        self.outbox.mkdir()

    def test_valid_atomic_publish_and_identical_replay(self):
        target = publish_synthetic_fixture(self.outbox)
        manifest, institutions, programs = validate_batch(target)
        self.assertEqual((len(institutions), len(programs)), (2, 3))
        self.assertEqual(manifest["batch_id"], target.name.removeprefix("batch-"))
        self.assertEqual(publish_synthetic_fixture(self.outbox), target)
        self.assertEqual(len(list(self.outbox.iterdir())), 1)
        for name in ("institutions.jsonl", "programs.jsonl"):
            self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), manifest["sha256"][name])

    def test_interruption_leaves_no_final_batch(self):
        def interrupt():
            self.assertFalse(list(self.outbox.glob("batch-*")))
            raise RuntimeError("synthetic crash before rename")

        with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
            publish_synthetic_fixture(self.outbox, before_publish=interrupt)
        self.assertEqual(list(self.outbox.iterdir()), [])

    def test_changed_id_is_never_overwritten(self):
        target = publish_synthetic_fixture(self.outbox)
        original = (target / "manifest.json").read_bytes()
        (target / "manifest.json").write_bytes(original + b" ")
        with self.assertRaises(FileExistsError):
            publish_synthetic_fixture(self.outbox)
        self.assertEqual((target / "manifest.json").read_bytes(), original + b" ")

    def test_invalid_records_and_batch_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory) / FIXTURE.name
            shutil.copytree(FIXTURE, batch)

            def replace_file(name, records):
                data = b"".join(json.dumps(record, separators=(",", ":")).encode() + b"\n" for record in records)
                (batch / name).write_bytes(data)
                manifest = json.loads((batch / "manifest.json").read_bytes())
                manifest["sha256"][name] = hashlib.sha256(data).hexdigest()
                manifest["counts"]["institutions" if name.startswith("institutions") else "programs"] = len(records)
                (batch / "manifest.json").write_text(json.dumps(manifest))

            institutions = [json.loads(line) for line in (batch / "institutions.jsonl").read_text().splitlines()]
            programs = [json.loads(line) for line in (batch / "programs.jsonl").read_text().splitlines()]
            cases = []
            for field in ("applicant_profile", "cv", "professor_email", "private_notes"):
                rows = copy.deepcopy(institutions)
                rows[0][field] = "synthetic"
                cases.append(("institutions.jsonl", rows))
            rows = copy.deepcopy(institutions)
            rows[0]["facts"]["name"]["source_url"] = "file:///private"
            cases.append(("institutions.jsonl", rows))
            rows = copy.deepcopy(institutions)
            rows[0]["schema_version"] = "2.0.0"
            cases.append(("institutions.jsonl", rows))
            rows = copy.deepcopy(institutions)
            rows.append(copy.deepcopy(rows[0]))
            cases.append(("institutions.jsonl", rows))
            rows = copy.deepcopy(programs)
            rows[0]["institution_id"] = "99999999-9999-4999-8999-999999999999"
            cases.append(("programs.jsonl", rows))
            rows = copy.deepcopy(programs)
            rows[0]["review"]["bound_revision"] = rows[1]["record_revision"]
            cases.append(("programs.jsonl", rows))
            for name, rows in cases:
                with self.subTest(name=name, rows=rows[0].get("id")):
                    shutil.rmtree(batch)
                    shutil.copytree(FIXTURE, batch)
                    replace_file(name, rows)
                    with self.assertRaises((ValueError, ValidationError)):
                        validate_batch(batch)

    def test_tampering_missing_manifest_and_symlink_fail(self):
        target = publish_synthetic_fixture(self.outbox)
        (target / "programs.jsonl").write_bytes((target / "programs.jsonl").read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            validate_batch(target)
        (target / "manifest.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing or extra"):
            validate_batch(target)
        (target / "manifest.json").symlink_to(FIXTURE / "manifest.json")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            validate_batch(target)


if __name__ == "__main__":
    unittest.main()
