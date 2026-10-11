import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contract import ROOT, SCHEMAS, validate_batch, validate_record  # noqa: E402
from jsonschema import ValidationError, Draft202012Validator  # noqa: E402


EXAMPLE = ROOT / "examples" / "batch-66666666-6666-4666-8666-666666666666"


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.institutions, cls.programs = validate_batch(EXAMPLE)

    def test_schemas_are_valid_and_five_synthetic_records_validate(self):
        for schema in SCHEMAS.values():
            Draft202012Validator.check_schema(schema)
        self.assertEqual((len(self.institutions), len(self.programs)), (2, 3))
        self.assertEqual(len(self.programs[0]["requirements"]), 2)
        self.assertIsNone(self.programs[0]["requirements"][1]["value"])

    def test_unknown_and_private_fields_fail_closed(self):
        for field in ("applicant_profile", "cv", "professor_email", "local_university_id", "private_notes"):
            record = copy.deepcopy(self.institutions[0])
            record[field] = "synthetic"
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_record("institution", record)
        record = copy.deepcopy(self.programs[0])
        record["facts"]["applicant_profile"] = record["facts"]["name"]
        with self.assertRaises(ValidationError):
            validate_record("program", record)

    def test_unsupported_versions_and_manifest_shape_fail(self):
        for kind, value in (("institution", self.institutions[0]), ("program", self.programs[0]), ("batch", self.manifest)):
            record = copy.deepcopy(value)
            record["schema_version"] = "2.0.0"
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                validate_record(kind, record)
        manifest = copy.deepcopy(self.manifest)
        manifest["institution_file"] = "../private.jsonl"
        with self.assertRaises(ValidationError):
            validate_record("batch", manifest)

    def test_provenance_and_review_binding_fail(self):
        record = copy.deepcopy(self.institutions[0])
        del record["facts"]["name"]
        with self.assertRaises((ValidationError, ValueError)):
            validate_record("institution", record)
        record = copy.deepcopy(self.institutions[0])
        record["review"]["bound_revision"] = self.institutions[1]["record_revision"]
        with self.assertRaises(ValueError):
            validate_record("institution", record)
        record = copy.deepcopy(self.programs[0])
        record["requirements"][0]["source_url"] = "file:///private"
        with self.assertRaises(ValidationError):
            validate_record("program", record)
        record = copy.deepcopy(self.programs[0])
        del record["requirements"][0]["observed_at"]
        with self.assertRaises(ValidationError):
            validate_record("program", record)

    def test_requirement_semantics_and_review_state(self):
        record = copy.deepcopy(self.programs[0])
        record["requirements"].append(copy.deepcopy(record["requirements"][0]))
        with self.assertRaises(ValueError):
            validate_record("program", record)
        record = copy.deepcopy(self.programs[1])
        record["review"]["state"] = "accepted"
        with self.assertRaises(ValidationError):
            validate_record("program", record)

    def test_manifest_hashes_and_parent_ids(self):
        self.assertEqual(self.manifest["institution_file"], "institutions.jsonl")
        self.assertEqual(self.manifest["program_file"], "programs.jsonl")
        self.assertEqual({r["institution_id"] for r in self.programs}, {r["id"] for r in self.institutions})

    def test_tamper_and_orphan_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            batch = Path(temporary) / "batch"
            shutil.copytree(EXAMPLE, batch)
            path = batch / "programs.jsonl"
            path.write_bytes(path.read_bytes().replace(b"MSc Example Studies", b"MSc Altered Studies"))
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                validate_batch(batch)

            records = [json.loads(line) for line in path.read_text().splitlines()]
            records[0]["institution_id"] = "99999999-9999-4999-8999-999999999999"
            data = "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records).encode()
            path.write_bytes(data)
            manifest = json.loads((batch / "manifest.json").read_text())
            manifest["sha256"]["programs.jsonl"] = hashlib.sha256(data).hexdigest()
            (batch / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "orphan program ID"):
                validate_batch(batch)


if __name__ == "__main__":
    unittest.main()
