import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "grad_compass.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS countries (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS universities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_code TEXT NOT NULL,
        name TEXT NOT NULL,
        city TEXT,
        latitude REAL,
        longitude REAL,
        portal_url TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'Researching'
    );

    CREATE TABLE IF NOT EXISTS professors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id INTEGER NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        email TEXT,
        lab_website TEXT,
        research_interests TEXT,
        outreach_status TEXT DEFAULT 'Not Contacted'
    );

    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_type TEXT NOT NULL,      -- 'university' or 'professor'
        parent_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        stored_path TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def db_add_university(country_code, name, city, lat, lng, deadline, portal_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO universities (country_code, name, city, latitude, longitude, deadline, portal_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (country_code, name, city, lat, lng, deadline, portal_url)
    )
    uni_id = c.lastrowid
    conn.commit()
    conn.close()
    return uni_id

def db_get_universities_by_country(country_code):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM universities WHERE country_code = ? ORDER BY name ASC", (country_code,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_add_professor(uni_id, name, email, research, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO professors (university_id, name, email, research_interests, outreach_status) VALUES (?, ?, ?, ?, ?)",
        (uni_id, name, email, research, status)
    )
    prof_id = c.lastrowid
    conn.commit()
    conn.close()
    return prof_id

def db_get_professors(uni_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM professors WHERE university_id = ? ORDER BY id DESC", (uni_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_add_attachment(parent_type, parent_id, file_name, stored_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO attachments (parent_type, parent_id, file_name, stored_path) VALUES (?, ?, ?, ?)",
        (parent_type, parent_id, file_name, stored_path)
    )
    conn.commit()
    conn.close()

def db_get_attachments(parent_type, parent_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM attachments WHERE parent_type = ? AND parent_id = ?", (parent_type, parent_id))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_delete_attachment(attachment_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT stored_path FROM attachments WHERE id = ?", (attachment_id,))
    row = c.fetchone()
    if row:
        app_root = DB_PATH.parent.parent
        target = app_root / row[0]
        if target.exists():
            target.unlink()
        c.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        conn.commit()
    conn.close()
    return True

