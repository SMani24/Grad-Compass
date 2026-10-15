"""Marked app-owned synthetic research state; no producer access or agent execution."""
from contextlib import closing
import os
import sqlite3
import threading

from web.country_evidence import COUNTRY_CODES

MARKER = "grad-compass-research-demo-v1"


class ResearchWorkspace:
    def __init__(self, workspace):
        self.workspace = workspace
        self.directory = workspace.directory
        self.database = self.directory / "research.sqlite"
        self.lock = threading.RLock()
        with self.lock, closing(workspace.connect()):
            self._guard_paths()
            if not self.database.exists():
                descriptor = os.open(self.database, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                os.close(descriptor)
                with closing(sqlite3.connect(self.database)) as db, db:
                    db.executescript("""
                        CREATE TABLE app_research_guard(marker TEXT NOT NULL);
                        INSERT INTO app_research_guard VALUES('grad-compass-research-demo-v1');
                        CREATE TABLE country_personal(code TEXT PRIMARY KEY,
                            watched INTEGER NOT NULL DEFAULT 0 CHECK(watched IN (0,1)),
                            note TEXT NOT NULL DEFAULT '');
                    """)
            with closing(self.connect()):
                pass

    def _guard_paths(self):
        if any(path.is_symlink() for path in (self.directory, *self.directory.parents)):
            raise ValueError("Research state requires an unlinked synthetic workspace")
        for suffix in ("", "-wal", "-shm", "-journal"):
            path = type(self.database)(str(self.database) + suffix)
            if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1)):
                raise ValueError("Research state requires unlinked runtime files")

    def connect(self):
        with closing(self.workspace.connect()):
            pass
        self._guard_paths()
        if not self.database.is_file():
            raise ValueError("The synthetic research workspace is missing")
        db = sqlite3.connect(self.database.as_uri() + "?mode=rw", uri=True, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            if [row[0] for row in db.execute("SELECT marker FROM app_research_guard")] != [MARKER]:
                raise ValueError("A marked synthetic research workspace is required")
        except (sqlite3.Error, ValueError):
            db.close()
            raise ValueError("A marked synthetic research workspace is required") from None
        return db

    def snapshot(self):
        with self.lock, closing(self.connect()) as db:
            return {"synthetic": True, "countries": {row["code"]: {"watched": bool(row["watched"]), "note": row["note"]}
                    for row in db.execute("SELECT * FROM country_personal ORDER BY code")}}

    def save_country(self, payload):
        if (not isinstance(payload, dict) or not {"country_code"} < set(payload)
            or set(payload) - {"country_code", "watched", "note"}
            or not isinstance(payload["country_code"], str) or payload["country_code"] not in COUNTRY_CODES
            or ("watched" in payload and type(payload["watched"]) is not bool)
            or ("note" in payload and (not isinstance(payload["note"], str) or len(payload["note"]) > 4000))):
            raise ValueError("Choose a displayed country and a valid watchlist choice or note")
        with self.lock, closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT watched,note FROM country_personal WHERE code=?", (payload["country_code"],)).fetchone()
            watched = payload.get("watched", bool(previous["watched"]) if previous else False)
            note = payload.get("note", previous["note"] if previous else "")
            db.execute("INSERT INTO country_personal(code,watched,note) VALUES(?,?,?) ON CONFLICT(code) DO UPDATE SET watched=excluded.watched,note=excluded.note",
                       (payload["country_code"], int(watched), note))
        return self.snapshot()
