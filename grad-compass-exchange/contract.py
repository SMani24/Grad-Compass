"""Read-only v1 exchange contract checks; no application or private-data access."""

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parent
SCHEMAS = {
    kind: json.loads((ROOT / "schemas" / f"{kind}-1.0.0.schema.json").read_text())
    for kind in ("institution", "program", "requirement", "batch")
}
VALIDATORS = {
    kind: Draft202012Validator(schema, format_checker=FormatChecker())
    for kind, schema in SCHEMAS.items()
}
FILES = ("institutions.jsonl", "programs.jsonl")


def validate_record(kind, record):
    VALIDATORS[kind].validate(record)
    if kind not in ("institution", "program"):
        return
    review = record["review"]
    if review["state"] != "pending" and review["bound_revision"] != record["record_revision"]:
        raise ValueError("review is bound to another record revision")
    for field in ("name", "country_code", "city", "degree_level", "official_url"):
        if field in record and record[field] is not None and field not in record["facts"]:
            raise ValueError(f"missing provenance for {field}")
    for field in record["facts"]:
        if record.get(field) is None:
            raise ValueError(f"provenance without a value for {field}")
    if kind == "program":
        seen = set()
        for requirement in record["requirements"]:
            key = (requirement["kind"], requirement["intake"])
            if key in seen:
                raise ValueError("duplicate intake requirement")
            seen.add(key)


def _json_no_duplicates(data):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique_pairs)


def validate_batch(directory):
    """Validate a synthetic or finalized batch without writing anywhere."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("batch must be a real directory")
    if {entry.name for entry in directory.iterdir()} != set(FILES) | {"manifest.json"}:
        raise ValueError("batch has missing or extra entries")
    for filename in (*FILES, "manifest.json"):
        path = directory / filename
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"unsafe batch entry: {filename}")
    manifest = _json_no_duplicates((directory / "manifest.json").read_bytes())
    validate_record("batch", manifest)
    if directory.name.startswith("batch-") and directory.name != f'batch-{manifest["batch_id"]}':
        raise ValueError("batch directory ID mismatch")
    collections = []
    for filename, kind, count_key in zip(FILES, ("institution", "program"), ("institutions", "programs")):
        data = (directory / filename).read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["sha256"][filename]:
            raise ValueError(f"digest mismatch for {filename}")
        if data and not data.endswith(b"\n"):
            raise ValueError(f"missing final newline in {filename}")
        records = [_json_no_duplicates(line) for line in data.splitlines()]
        if len(records) != manifest["counts"][count_key]:
            raise ValueError(f"count mismatch for {filename}")
        ids = set()
        for record in records:
            validate_record(kind, record)
            if record["id"] in ids:
                raise ValueError(f"duplicate {kind} ID")
            ids.add(record["id"])
        collections.append(records)
    institutions, programs = collections
    institution_ids = {record["id"] for record in institutions}
    if institution_ids & {record["id"] for record in programs}:
        raise ValueError("ID reused across record types")
    if any(record["institution_id"] not in institution_ids for record in programs):
        raise ValueError("orphan program ID")
    return manifest, institutions, programs
