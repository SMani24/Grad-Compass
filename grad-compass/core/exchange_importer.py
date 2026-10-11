"""Manual, synthetic-only SQLite exchange importer draft.

No CLI or default database path is provided. Callers supply an explicit SQLite path.
This module never opens the application's DB_PATH or configuration.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import uuid
from datetime import date, datetime, timezone, timedelta
from jsonschema import ValidationError

EXCHANGE = Path(__file__).resolve().parents[2] / "grad-compass-exchange"
spec = importlib.util.spec_from_file_location("grad_compass_exchange_contract", EXCHANGE / "contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
FILES, _json_no_duplicates, validate_record = contract.FILES, contract._json_no_duplicates, contract.validate_record

APP_DB = (Path(__file__).resolve().parents[1] / "data/grad_compass.db").resolve()
SYNTHETIC_MARKER = "grad-compass-exchange-synthetic-test-v1"


def _db_path(path):
    if path is None or not str(path):
        raise ValueError("explicit synthetic SQLite database path required")
    path = Path(path)
    if path.resolve() == APP_DB or path.is_symlink() or not path.is_file():
        raise ValueError("database must be an existing synthetic SQLite file")
    if APP_DB.exists() and os.path.samefile(path, APP_DB):
        raise ValueError("application database path is forbidden")
    return path


def _connect(path):
    conn = sqlite3.connect(_db_path(path))
    try:
        # A compatible universities schema alone is not proof of a test database.
        marker = conn.execute("SELECT marker FROM exchange_synthetic_test_guard").fetchall()
        if marker != [(SYNTHETIC_MARKER,)]:
            raise ValueError("database is not marked as synthetic test data")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RuntimeError("foreign keys unavailable")
    except sqlite3.Error as exc:
        conn.close()
        raise ValueError("database is not marked as synthetic test data") from exc
    except (ValueError, RuntimeError):
        conn.close()
        raise
    return conn


def _read_batch(directory):
    try:
        return _read_batch_impl(directory)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, ValidationError):
        raise ValueError("batch validation failed") from None


def _read_batch_impl(directory):
    """Read fixed members through one directory descriptor with no-follow opens."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("batch must be a real finalized directory")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(directory, flags)
    try:
        names = set(os.listdir(fd))
        if names != set(FILES) | {"manifest.json"}:
            raise ValueError("incomplete or extra batch entries")
        data = {}
        for name in (*FILES, "manifest.json"):
            child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                info = os.fstat(child)
                if not stat.S_ISREG(info.st_mode) or info.st_size > 20_000_000:
                    raise ValueError("unsafe batch member")
                with os.fdopen(os.dup(child), "rb") as stream:
                    data[name] = stream.read(20_000_001)
                if len(data[name]) != info.st_size:
                    raise ValueError("batch changed during read")
            finally:
                os.close(child)
        manifest = _json_no_duplicates(data["manifest.json"])
        validate_record("batch", manifest)
        if directory.name.startswith("batch-") and directory.name != "batch-" + manifest["batch_id"]:
            raise ValueError("batch directory ID mismatch")
        groups = []
        for name, kind, count in zip(FILES, ("institution", "program"), ("institutions", "programs")):
            raw = data[name]
            if hashlib.sha256(raw).hexdigest() != manifest["sha256"][name]:
                raise ValueError("batch digest mismatch")
            if raw and not raw.endswith(b"\n"):
                raise ValueError("missing final newline")
            records = [_json_no_duplicates(line) for line in raw.splitlines()]
            if len(records) != manifest["counts"][count]:
                raise ValueError("batch count mismatch")
            seen = set()
            for record in records:
                validate_record(kind, record)
                if record["id"] in seen:
                    raise ValueError("duplicate record ID")
                seen.add(record["id"])
            groups.append(records)
        institutions, programs = groups
        ids = {item["id"] for item in institutions}
        if ids & {item["id"] for item in programs} or any(p["institution_id"] not in ids for p in programs):
            raise ValueError("invalid parent reference")
        digest = hashlib.sha256(data["manifest.json"]).hexdigest()
        return manifest, institutions, programs, digest
    finally:
        os.close(fd)


def migrate(db_path):
    """Create exchange-owned schema on an explicit synthetic DB only."""
    with _connect(db_path) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(universities)")}
        if not {"id", "country_code", "name", "city", "portal_url"} <= columns:
            raise ValueError("unexpected universities schema")
        existing_meta = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exchange_schema_meta'").fetchone()
        if existing_meta:
            versions = [row[0] for row in db.execute("SELECT version FROM exchange_schema_meta")]
            if versions != [1]:
                raise ValueError("unsupported exchange schema version")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS exchange_schema_meta (
          version INTEGER PRIMARY KEY CHECK(version=1)
        );
        CREATE TABLE IF NOT EXISTS exchange_batches (
          batch_id TEXT PRIMARY KEY, digest TEXT NOT NULL, manifest_json TEXT NOT NULL,
          decision TEXT, operator_id TEXT, decided_at TEXT, promoted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS exchange_staged_institutions (
          batch_id TEXT NOT NULL REFERENCES exchange_batches(batch_id), external_id TEXT NOT NULL,
          revision TEXT NOT NULL, record_json TEXT NOT NULL, outcome TEXT NOT NULL DEFAULT 'staged',
          PRIMARY KEY(batch_id, external_id)
        );
        CREATE TABLE IF NOT EXISTS exchange_staged_programs (
          batch_id TEXT NOT NULL REFERENCES exchange_batches(batch_id), external_id TEXT NOT NULL,
          institution_external_id TEXT NOT NULL, revision TEXT NOT NULL, record_json TEXT NOT NULL,
          outcome TEXT NOT NULL DEFAULT 'staged', requirement_outcomes_json TEXT,
          PRIMARY KEY(batch_id, external_id),
          FOREIGN KEY(batch_id, institution_external_id) REFERENCES exchange_staged_institutions(batch_id, external_id)
        );
        CREATE TABLE IF NOT EXISTS exchange_id_map (
          kind TEXT NOT NULL CHECK(kind IN ('institution','program')), external_id TEXT NOT NULL,
          local_id INTEGER, source_snapshot_json TEXT, PRIMARY KEY(kind, external_id)
        );
        CREATE TABLE IF NOT EXISTS exchange_record_revisions (
          kind TEXT NOT NULL CHECK(kind IN ('institution','program')),
          external_id TEXT NOT NULL, revision TEXT NOT NULL, record_digest TEXT NOT NULL,
          PRIMARY KEY(kind, external_id, revision)
        );
        CREATE TABLE IF NOT EXISTS programs (
          id INTEGER PRIMARY KEY, university_id INTEGER NOT NULL REFERENCES universities(id),
          name TEXT NOT NULL, degree_level TEXT NOT NULL, official_url TEXT,
          requirements_json TEXT NOT NULL DEFAULT '[]'
        );
        """)
        db.execute("INSERT OR IGNORE INTO exchange_schema_meta(version) VALUES(1)")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("foreign key violation")


def _compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def dry_run(db_path, directory):
    manifest, institutions, programs, digest = _read_batch(directory)
    with _connect(db_path) as db:
        old = db.execute("SELECT digest FROM exchange_batches WHERE batch_id=?", (manifest["batch_id"],)).fetchone()
        if old and old[0] != digest:
            raise ValueError("batch ID reused with changed manifest digest")
        mapped = {row[0] for row in db.execute("SELECT external_id FROM exchange_id_map WHERE kind='institution'")}
    return {"batch_id": manifest["batch_id"], "manifest_digest": digest,
            "received": len(institutions) + len(programs),
            "institution_mapping_needed": [r["id"] for r in institutions if r["id"] not in mapped],
            "accepted_candidates": sum(r["review"]["state"] == "accepted" for r in institutions + programs),
            "pending_or_other": sum(r["review"]["state"] != "accepted" for r in institutions + programs)}


def stage(db_path, directory):
    manifest, institutions, programs, digest = _read_batch(directory)
    with _connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT digest FROM exchange_batches WHERE batch_id=?", (manifest["batch_id"],)).fetchone()
        if old:
            if old[0] != digest:
                raise ValueError("batch ID reused with changed bytes")
            return receipt(db_path, manifest["batch_id"])
        db.execute("INSERT INTO exchange_batches(batch_id,digest,manifest_json) VALUES(?,?,?)",
                   (manifest["batch_id"], digest, _compact(manifest)))
        for kind, records in (("institution",institutions),("program",programs)):
            for r in records:
                record_digest = hashlib.sha256(_compact(r).encode("utf-8")).hexdigest()
                old_revision = db.execute("SELECT record_digest FROM exchange_record_revisions WHERE kind=? AND external_id=? AND revision=?",
                                          (kind,r["id"],r["record_revision"])).fetchone()
                if old_revision and old_revision[0] != record_digest:
                    raise ValueError("record revision reused with changed facts")
                db.execute("INSERT OR IGNORE INTO exchange_record_revisions(kind,external_id,revision,record_digest) VALUES(?,?,?,?)",
                           (kind,r["id"],r["record_revision"],record_digest))
        for r in institutions:
            db.execute("INSERT INTO exchange_staged_institutions(batch_id,external_id,revision,record_json) VALUES(?,?,?,?)",
                       (manifest["batch_id"], r["id"], r["record_revision"], _compact(r)))
        for r in programs:
            db.execute("INSERT INTO exchange_staged_programs(batch_id,external_id,institution_external_id,revision,record_json) VALUES(?,?,?,?,?)",
                       (manifest["batch_id"], r["id"], r["institution_id"], r["record_revision"], _compact(r)))
    return receipt(db_path, manifest["batch_id"])


def decide(db_path, batch_id, digest, operator_id, *, approve):
    if not operator_id or not operator_id.strip():
        raise ValueError("operator identity required")
    with _connect(db_path) as db:
        row = db.execute("SELECT digest,decision FROM exchange_batches WHERE batch_id=?", (batch_id,)).fetchone()
        if not row or row[0] != digest:
            raise ValueError("decision requires staged exact manifest digest")
        decision = "approved" if approve else "rejected"
        if row[1] and row[1] != decision:
            raise ValueError("batch decision is immutable")
        db.execute("UPDATE exchange_batches SET decision=?,operator_id=?,decided_at=? WHERE batch_id=? AND decision IS NULL",
                   (decision, operator_id, datetime.now(timezone.utc).isoformat(), batch_id))


def map_institution(db_path, batch_id, external_id, *, local_id=None, create=False):
    if (local_id is None) == (not create):
        raise ValueError("choose exactly one explicit mapping action")
    with _connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT record_json FROM exchange_staged_institutions WHERE batch_id=? AND external_id=?", (batch_id, external_id)).fetchone()
        if not row:
            raise ValueError("institution is not staged")
        record = json.loads(row[0])
        prior = db.execute("SELECT local_id FROM exchange_id_map WHERE kind='institution' AND external_id=?", (external_id,)).fetchone()
        if prior:
            if local_id is not None and prior[0] != local_id:
                raise ValueError("institution mapping is immutable")
            return prior[0]
        if create:
            if record["review"]["state"] != "accepted" or record["verification"] != "source_checked":
                raise ValueError("cannot create from unaccepted institution")
            # Record the explicit create choice; insert only inside approved promotion.
            snapshot = _compact({"create": True})
        else:
            if not db.execute("SELECT 1 FROM universities WHERE id=?", (local_id,)).fetchone():
                raise ValueError("local university does not exist")
            snapshot = None  # Existing app row: mapping never overwrites its initial local values.
        db.execute("INSERT INTO exchange_id_map(kind,external_id,local_id,source_snapshot_json) VALUES('institution',?,?,?)",
                   (external_id, local_id, snapshot))
        return local_id


def _institution_fields(record):
    return {"country_code": record["country_code"], "name": record["name"],
            "city": record.get("city"), "portal_url": record.get("official_url")}


def _program_fields(record, university_id, requirements):
    return {"university_id": university_id, "name": record["name"], "degree_level": record["degree_level"],
            "official_url": record.get("official_url"), "requirements_json": _compact(requirements)}


def _eligible(record):
    return record["verification"] == "source_checked" and record["review"]["state"] == "accepted" and record["review"]["bound_revision"] == record["record_revision"]


def _requirements(record, now, max_age_days):
    accepted, outcomes = [], {}
    for claim in record["requirements"]:
        key = claim["kind"] + ":" + claim["intake"]
        observed = datetime.fromisoformat(claim["observed_at"].replace("Z", "+00:00"))
        if claim["value"] is None:
            outcome = "unknown"
        elif observed > now or now - observed > timedelta(days=max_age_days):
            outcome = "stale"
        elif claim["kind"] == "application_deadline" and date.fromisoformat(claim["value"]) < now.date():
            outcome = "expired"
        else:
            outcome = "promoted"
            accepted.append(claim)
        outcomes[key] = outcome
    return accepted, outcomes


def promote(db_path, batch_id, digest, *, now=None, max_age_days=30, after_commit=None):
    if not isinstance(max_age_days, int) or max_age_days < 0:
        raise ValueError("nonnegative freshness days required")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone-aware promotion time required")
    with _connect(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        batch = db.execute("SELECT digest,decision,promoted_at FROM exchange_batches WHERE batch_id=?", (batch_id,)).fetchone()
        if not batch or batch[0] != digest or batch[1] != "approved":
            raise ValueError("approved exact batch decision required")
        if batch[2]:
            return receipt(db_path, batch_id)
        for staged in db.execute("SELECT external_id,record_json FROM exchange_staged_institutions WHERE batch_id=?", (batch_id,)).fetchall():
            external_id, record = staged[0], json.loads(staged[1])
            mapping = db.execute("SELECT local_id,source_snapshot_json FROM exchange_id_map WHERE kind='institution' AND external_id=?", (external_id,)).fetchone()
            outcome = "skipped" if not _eligible(record) else "mapping_required" if not mapping else "promoted"
            if outcome == "promoted" and mapping[0] is None:
                db.execute("INSERT OR IGNORE INTO countries(code,name) VALUES(?,?)", (record["country_code"],record["country_code"]))
                fields = _institution_fields(record)
                cur = db.execute("INSERT INTO universities(country_code,name,city,portal_url) VALUES(?,?,?,?)", tuple(fields.values()))
                db.execute("UPDATE exchange_id_map SET local_id=?,source_snapshot_json=? WHERE kind='institution' AND external_id=?",
                           (cur.lastrowid,_compact(fields),external_id))
            elif outcome == "promoted":
                current = db.execute("SELECT country_code,name,city,portal_url FROM universities WHERE id=?", (mapping[0],)).fetchone()
                if not current:
                    outcome = "conflict"
                elif mapping[1] is not None:
                    old = json.loads(mapping[1])
                    if dict(current) != old:
                        outcome = "conflict"
                    else:
                        fields = _institution_fields(record)
                        db.execute("UPDATE universities SET country_code=?,name=?,city=?,portal_url=? WHERE id=?",
                                   (*fields.values(), mapping[0]))
                        db.execute("UPDATE exchange_id_map SET source_snapshot_json=? WHERE kind='institution' AND external_id=?",
                                   (_compact(fields), external_id))
            db.execute("UPDATE exchange_staged_institutions SET outcome=? WHERE batch_id=? AND external_id=?", (outcome,batch_id,external_id))
        for staged in db.execute("SELECT external_id,record_json FROM exchange_staged_programs WHERE batch_id=?", (batch_id,)).fetchall():
            external_id, record = staged[0], json.loads(staged[1])
            parent = db.execute("SELECT m.local_id,s.outcome FROM exchange_id_map m JOIN exchange_staged_institutions s ON s.external_id=m.external_id WHERE m.kind='institution' AND s.batch_id=? AND m.external_id=?", (batch_id, record["institution_id"])).fetchone()
            outcome = "skipped" if not _eligible(record) else "parent_mapping_required" if not parent or parent[1] != "promoted" else "promoted"
            requirement_outcomes = {}
            if outcome == "promoted":
                claims, requirement_outcomes = _requirements(record, now, max_age_days)
                fields = _program_fields(record, parent[0], claims)
                mapping = db.execute("SELECT local_id,source_snapshot_json FROM exchange_id_map WHERE kind='program' AND external_id=?", (external_id,)).fetchone()
                if mapping:
                    current = db.execute("SELECT university_id,name,degree_level,official_url,requirements_json FROM programs WHERE id=?", (mapping[0],)).fetchone()
                    if not current or dict(current) != json.loads(mapping[1]):
                        outcome = "conflict"
                    else:
                        db.execute("UPDATE programs SET university_id=?,name=?,degree_level=?,official_url=?,requirements_json=? WHERE id=?",
                                   (*fields.values(), mapping[0]))
                        db.execute("UPDATE exchange_id_map SET source_snapshot_json=? WHERE kind='program' AND external_id=?", (_compact(fields),external_id))
                else:
                    cur = db.execute("INSERT INTO programs(university_id,name,degree_level,official_url,requirements_json) VALUES(?,?,?,?,?)", tuple(fields.values()))
                    db.execute("INSERT INTO exchange_id_map(kind,external_id,local_id,source_snapshot_json) VALUES('program',?,?,?)", (external_id,cur.lastrowid,_compact(fields)))
            db.execute("UPDATE exchange_staged_programs SET outcome=?,requirement_outcomes_json=? WHERE batch_id=? AND external_id=?",
                       (outcome,_compact(requirement_outcomes),batch_id,external_id))
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("foreign key violation")
        db.execute("UPDATE exchange_batches SET promoted_at=? WHERE batch_id=?", (now.isoformat(), batch_id))
    if after_commit:
        after_commit()  # Test crash: ledger is already durable and receipt can be regenerated.
    return receipt(db_path, batch_id)


def receipt(db_path, batch_id):
    """Only identifiers, digests, decisions, and aggregate outcomes; no fact values."""
    with _connect(db_path) as db:
        batch = db.execute("SELECT digest,decision,promoted_at FROM exchange_batches WHERE batch_id=?", (batch_id,)).fetchone()
        if not batch:
            raise ValueError("unknown batch")
        rows = db.execute("SELECT outcome FROM exchange_staged_institutions WHERE batch_id=? UNION ALL SELECT outcome FROM exchange_staged_programs WHERE batch_id=?", (batch_id,batch_id)).fetchall()
        counts = {name: sum(r[0] == name for r in rows) for name in ("staged","promoted","skipped","conflict","mapping_required","parent_mapping_required")}
        return {"batch_id":batch_id,"manifest_digest":batch[0],"decision":batch[1],"promotion_committed":bool(batch[2]),
                "received":len(rows),"outcomes":counts}


def write_receipt(db_path, batch_id, directory):
    """Atomically publish a sanitized, reproducible receipt in an existing directory."""
    if str(uuid.UUID(batch_id)) != batch_id:
        raise ValueError("canonical batch UUID required")
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("receipt directory must exist and be real")
    payload = (_compact(receipt(db_path,batch_id)) + "\n").encode()
    final = directory / (batch_id + ".receipt.json")
    if final.exists() or final.is_symlink():
        if final.is_symlink() or final.read_bytes() != payload:
            raise ValueError("receipt path contains different bytes")
        return final
    descriptor, temporary = tempfile.mkstemp(prefix=".receipt-",dir=directory)
    try:
        with os.fdopen(descriptor,"wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary,final,follow_symlinks=False)
        except FileExistsError:
            if final.is_symlink() or final.read_bytes() != payload:
                raise ValueError("receipt path contains different bytes")
        dir_fd = os.open(directory,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return final
    finally:
        os.unlink(temporary)
