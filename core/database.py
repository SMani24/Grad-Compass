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
        code TEXT PRIMARY KEY,          -- ISO 3166-1 alpha-3 code (e.g., 'DEU', 'USA', 'CHE')
        name TEXT NOT NULL,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS universities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_code TEXT NOT NULL REFERENCES countries(code) ON DELETE CASCADE,
        name TEXT NOT NULL,
        city TEXT,
        latitude REAL,
        longitude REAL,
        portal_url TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'Researching'  -- 'Researching', 'Applying', 'Submitted', 'Accepted', 'Rejected'
    );

    CREATE TABLE IF NOT EXISTS professors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id INTEGER NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        email TEXT,
        lab_website TEXT,
        research_interests TEXT,
        outreach_status TEXT DEFAULT 'Not Contacted', -- 'Not Contacted', 'Contacted', 'Follow-up Needed', 'Meeting Scheduled'
        last_contacted_date TEXT
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
        professor_id INTEGER REFERENCES professors(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        due_date TEXT,
        is_completed INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_type TEXT NOT NULL,      -- 'country', 'university', 'professor'
        parent_id TEXT NOT NULL,        -- Matches country code or university/prof ID
        file_name TEXT NOT NULL,
        stored_path TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")