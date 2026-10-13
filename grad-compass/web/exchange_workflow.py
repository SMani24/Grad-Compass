"""App consumer of the unchanged v1 importer, limited to its approved invented batch."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import threading

from core.paths import validate_data_directory
from core import exchange_importer as importer

EXCHANGE_ROOT = Path(__file__).resolve().parents[2] / "grad-compass-exchange"
FIXTURE = EXCHANGE_ROOT / "examples/batch-66666666-6666-4666-8666-666666666666"
BATCH_ID = "66666666-6666-4666-8666-666666666666"
UI_MARKER = "grad-compass-exchange-ui-v1"
# The reviewed fixture from operator commit 043d9d7; accepting a v1 schema alone
# would also accept real research, which is outside this consumer's scope.
FIXTURE_DIGEST = "38e84125163de1964cd1ec316a6c781342df4d6b5101f7fe128078a053c48a36"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class SyntheticExchangeWorkflow:
    def __init__(self, directory, clock=None):
        self.directory = validate_data_directory(directory)
        self.database = self.directory / "exchange.sqlite"
        self.outbox = self.directory / "outbox"
        self.batch = self.outbox / ("batch-" + BATCH_ID)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.lock = threading.RLock()
        self.previews = {}
        self.fixture = {name: (FIXTURE / name).read_bytes() for name in (*importer.FILES, "manifest.json")}
        if hashlib.sha256(self.fixture["manifest.json"]).hexdigest() != FIXTURE_DIGEST:
            raise ValueError("The approved synthetic fixture has changed")
        manifest = json.loads(self.fixture["manifest.json"])
        if any(hashlib.sha256(self.fixture[name]).hexdigest() != manifest["sha256"][name] for name in importer.FILES):
            raise ValueError("The approved synthetic fixture has changed")
        raw = Path(directory).expanduser().absolute()
        if any(part.is_symlink() for part in (raw, *raw.parents)):
            raise ValueError("Synthetic exchange storage cannot use linked directories")
        if not self.directory.exists() or (self.directory.is_dir() and not any(self.directory.iterdir())):
            self._initialize()
        with closing(self._reader()):
            pass
        self._read_fixture()

    def _initialize(self):
        self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        with self.database.open("xb"):
            pass
        self.database.chmod(0o600)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.executescript("""
                CREATE TABLE app_exchange_ui_guard(marker TEXT NOT NULL);
                INSERT INTO app_exchange_ui_guard VALUES('grad-compass-exchange-ui-v1');
                CREATE TABLE exchange_synthetic_test_guard(marker TEXT NOT NULL);
                INSERT INTO exchange_synthetic_test_guard VALUES('grad-compass-exchange-synthetic-test-v1');
                CREATE TABLE countries(code TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE universities(id INTEGER PRIMARY KEY, country_code TEXT NOT NULL,
                    name TEXT NOT NULL, city TEXT, portal_url TEXT, latitude REAL, longitude REAL,
                    deadline TEXT, status TEXT, image_url TEXT);
                INSERT INTO countries VALUES('CAN','Canada');
                INSERT INTO universities VALUES(1,'CAN','Existing Demo University','Demo City',
                    'https://example.invalid/local',NULL,NULL,'2030-01-01','Researching',NULL);
            """)
        importer.migrate(self.database)
        self.outbox.mkdir(mode=0o700)
        # Reuse the reviewed manifest-last synthetic publisher.
        sys.path.insert(0, str(EXCHANGE_ROOT))
        spec = importlib.util.spec_from_file_location("app_synthetic_exporter", EXCHANGE_ROOT / "exporter.py")
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        exporter.publish_synthetic_fixture(self.outbox)

    def _guard(self):
        if any(path.is_symlink() for path in (self.directory, *self.directory.parents)):
            raise ValueError("Synthetic exchange storage cannot use linked directories")
        if not self.database.is_file() or self.database.is_symlink() or self.database.stat().st_nlink != 1:
            raise ValueError("An unlinked disposable exchange database is required")
        for suffix in ("-wal", "-shm", "-journal"):
            path = Path(str(self.database) + suffix)
            if path.is_symlink() or (path.is_file() and path.stat().st_nlink != 1):
                raise ValueError("Linked database sidecars are not supported")

    def _reader(self, database=None):
        self._guard()
        connection = sqlite3.connect((database or self.database).as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        try:
            for table, marker in (("app_exchange_ui_guard", UI_MARKER), ("exchange_synthetic_test_guard", importer.SYNTHETIC_MARKER)):
                if [row[0] for row in connection.execute(f"SELECT marker FROM {table}")] != [marker]:
                    raise ValueError("An app-created disposable exchange workspace is required")
        except (sqlite3.Error, ValueError):
            connection.close()
            raise ValueError("An app-created disposable exchange workspace is required") from None
        return connection

    def _read_fixture(self):
        if self.outbox.is_symlink() or self.batch.is_symlink() or not self.batch.is_dir():
            raise ValueError("A finalized synthetic batch directory is required")
        if {entry.name for entry in self.batch.iterdir()} != set(self.fixture):
            raise ValueError("The finalized batch must contain exactly three exchange files")
        for name, expected in self.fixture.items():
            fd = os.open(self.batch / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                actual = stream.read(len(expected) + 1)
            if actual != expected:
                raise ValueError("Only the finalized approved invented fixture is permitted")

    @contextmanager
    def _batch_snapshot(self, batch_id):
        if batch_id != BATCH_ID:
            raise ValueError("Select a registered synthetic batch")
        self._read_fixture()
        # Pass an owned snapshot of verified invented bytes to the importer.
        # A file changed in the selectable outbox cannot become real input later.
        with tempfile.TemporaryDirectory(prefix=".batch-", dir=self.directory) as temporary:
            directory = Path(temporary) / ("batch-" + batch_id)
            directory.mkdir(mode=0o700)
            for name, data in self.fixture.items():
                (directory / name).write_bytes(data)
            yield directory

    def _fingerprint(self):
        self._guard()
        return hashlib.sha256(self.database.read_bytes()).hexdigest()

    def catalog(self):
        with self.lock, closing(self._reader()):
            return {"batches": [{"id": BATCH_ID, "label": "Invented v1 batch · 2 institutions / 3 programs",
                                 "directory": self.batch.name}], "freshness_days": 30}

    def _state(self, database=None):
        database = database or self.database
        with closing(self._reader(database)) as connection:
            batch = connection.execute("SELECT * FROM exchange_batches WHERE batch_id=?", (BATCH_ID,)).fetchone()
            institutions, programs = [], []
            for kind, destination in (("institution", institutions), ("program", programs)):
                table = "exchange_staged_institutions" if kind == "institution" else "exchange_staged_programs"
                for row in connection.execute(f"SELECT * FROM {table} WHERE batch_id=? ORDER BY external_id", (BATCH_ID,)):
                    record = json.loads(row["record_json"])
                    mapping = connection.execute("SELECT local_id,source_snapshot_json FROM exchange_id_map WHERE kind=? AND external_id=?", (kind, row["external_id"])).fetchone()
                    destination.append({"record": record, "outcome": row["outcome"],
                        "storage": "promoted" if row["outcome"] == "promoted" else "staged",
                        "mapping": None if mapping is None else {"local_id": mapping[0], "create": mapping[0] is None},
                        "requirements": json.loads(row["requirement_outcomes_json"] or "{}") if kind == "program" else {}})
            saved_institutions = [dict(row) for row in connection.execute("SELECT * FROM universities ORDER BY id")]
            saved_programs = [dict(row) for row in connection.execute("SELECT * FROM programs ORDER BY id")]
        return {"institutions": institutions, "programs": programs,
                "saved_institutions": saved_institutions, "saved_programs": saved_programs,
                "receipt": importer.receipt(database, BATCH_ID) if batch else None}

    def state(self, batch_id):
        with self.lock:
            if batch_id != BATCH_ID:
                raise ValueError("Select a registered synthetic batch")
            return self._state()

    def stage(self, batch_id):
        with self.lock, closing(self._reader()), self._batch_snapshot(batch_id) as directory:
            validation = importer.dry_run(self.database, directory)
            importer.stage(self.database, directory)
            self.previews.clear()
            return {**self._state(), "validation": validation}

    def map(self, batch_id, external_id, local_id=None, create=False):
        with self.lock, closing(self._reader()):
            if batch_id != BATCH_ID:
                raise ValueError("Select a registered synthetic batch")
            current = self._state()
            if current["receipt"] and current["receipt"]["promotion_committed"]:
                raise ValueError("This batch is already promoted; replay it to inspect unchanged outcomes")
            importer.map_institution(self.database, batch_id, external_id, local_id=local_id, create=create)
            self.previews.clear()
            return self._state()

    def _project(self, now):
        before = self._state()
        if before["receipt"] is None:
            raise ValueError("Validate and stage the batch first")
        with tempfile.TemporaryDirectory(prefix=".preview-", dir=self.directory) as temporary:
            shadow = Path(temporary) / "preview.sqlite"
            with closing(self._reader()) as source, closing(sqlite3.connect(shadow)) as target:
                source.backup(target)
            importer.decide(shadow, BATCH_ID, before["receipt"]["manifest_digest"], "synthetic-app-operator", approve=True)
            importer.promote(shadow, BATCH_ID, before["receipt"]["manifest_digest"], now=now, max_age_days=30)
            projected = self._state(shadow)
        changes = []
        for kind in ("institutions", "programs"):
            originals = {row["id"]: row for row in before["saved_" + kind]}
            for row in projected["saved_" + kind]:
                previous = originals.get(row["id"])
                if previous != row:
                    changes.append({"kind": kind, "action": "Create" if previous is None else "Update", "before": previous, "after": row})
        for row in projected["institutions"]:
            if row["outcome"] == "promoted" and row["mapping"]["local_id"] in {r["id"] for r in before["saved_institutions"]}:
                local_id = row["mapping"]["local_id"]
                previous = next(r for r in before["saved_institutions"] if r["id"] == local_id)
                target = next(r for r in projected["saved_institutions"] if r["id"] == local_id)
                changes.append({"kind": "institutions", "action": "Link existing (preserve local fields)",
                                "before": previous, "after": target})
        blocked = any(projected["receipt"]["outcomes"][key] for key in ("mapping_required", "parent_mapping_required", "conflict"))
        return {"changes": changes, "projected": projected, "ready": not blocked,
                "evaluated_at": now.isoformat(), "freshness_days": 30}

    @staticmethod
    def _projection_digest(projection):
        return digest({key: projection[key] for key in ("changes", "projected", "ready")})

    def preview(self, batch_id):
        with self.lock, closing(self._reader()), self._batch_snapshot(batch_id) as directory:
            current = self._state()
            if current["receipt"] and current["receipt"]["promotion_committed"]:
                raise ValueError("This batch is already promoted; use replay to verify unchanged outcomes")
            importer.dry_run(self.database, directory)
            projection = self._project(self.clock())
            token = secrets.token_urlsafe(24)
            self.previews = {token: (self._fingerprint(), self._projection_digest(projection))}
            return {**self._state(), "preview": {**projection, "id": token}}

    def promote(self, batch_id, preview_id, approved):
        with self.lock, closing(self._reader()), self._batch_snapshot(batch_id) as directory:
            if approved is not True:
                raise ValueError("Explicit operational approval is required")
            approved_preview = self.previews.get(preview_id)
            if approved_preview is None or approved_preview[0] != self._fingerprint():
                raise ValueError("The dry run has changed; review a fresh preview before approval")
            validation = importer.dry_run(self.database, directory)
            now = self.clock()
            projection = self._project(now)
            if not projection["ready"] or approved_preview[1] != self._projection_digest(projection):
                raise ValueError("Mappings or eligibility changed; review a fresh dry run")
            self.previews.clear()
            importer.decide(self.database, batch_id, validation["manifest_digest"], "synthetic-app-operator", approve=True)
            importer.promote(self.database, batch_id, validation["manifest_digest"], now=now, max_age_days=30)
            return self._state()

    def replay(self, batch_id):
        with self.lock, closing(self._reader()), self._batch_snapshot(batch_id) as directory:
            state = self._state()
            if not state["receipt"] or not state["receipt"]["promotion_committed"]:
                raise ValueError("Promote the batch before checking replay")
            before = self._fingerprint()
            importer.stage(self.database, directory)
            importer.promote(self.database, batch_id, state["receipt"]["manifest_digest"], now=self.clock())
            after = self._state()
            return {**after, "replay": {"no_changes": before == self._fingerprint(),
                "institutions": len(after["saved_institutions"]), "programs": len(after["saved_programs"])}}
