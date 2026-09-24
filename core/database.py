import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "grad_compass.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = OFF;")

    cursor.executescript("""
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
        status TEXT DEFAULT 'Researching',
        image_url TEXT
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
        parent_type TEXT NOT NULL,
        parent_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        stored_path TEXT NOT NULL
    );
    """)

    try:
        cursor.execute("ALTER TABLE universities ADD COLUMN image_url TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

# --- University Operations ---

def db_add_university(country_code, name, city, lat, lng, deadline, portal_url, image_url=None):
    code = (country_code or "UNKNOWN").strip().upper()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO countries (code, name) VALUES (?, ?)", (code, code))
    c.execute(
        """INSERT INTO universities 
           (country_code, name, city, latitude, longitude, deadline, portal_url, image_url) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (code, name, city, lat, lng, deadline, portal_url, image_url)
    )
    uni_id = c.lastrowid
    conn.commit()
    conn.close()
    return uni_id

def db_get_university(uni_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM universities WHERE id = ?", (int(uni_id),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def db_get_universities_by_country(country_code):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM universities WHERE country_code = ? ORDER BY name ASC", (country_code.upper(),))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_update_university(uni_id, name, city, lat, lng, deadline, portal_url, image_url=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if image_url:
        c.execute("""
            UPDATE universities 
            SET name = ?, city = ?, latitude = ?, longitude = ?, deadline = ?, portal_url = ?, image_url = ?
            WHERE id = ?
        """, (name, city, lat, lng, deadline, portal_url, image_url, int(uni_id)))
    else:
        c.execute("""
            UPDATE universities 
            SET name = ?, city = ?, latitude = ?, longitude = ?, deadline = ?, portal_url = ?
            WHERE id = ?
        """, (name, city, lat, lng, deadline, portal_url, int(uni_id)))
    conn.commit()
    conn.close()
    return True

def db_delete_university(uni_id):
    return db_delete_universities_batch([uni_id])

def db_delete_universities_batch(uni_ids):
    """Batch deletes multiple universities, cascade-cleans tasks, professors, and on-disk files."""
    if not uni_ids:
        return {"country_code": None, "remaining": 0}

    clean_ids = [int(i) for i in uni_ids]
    placeholders = ",".join("?" * len(clean_ids))
    app_root = DB_PATH.parent.parent

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Find country code of first uni
    c.execute(f"SELECT country_code FROM universities WHERE id IN ({placeholders}) LIMIT 1", clean_ids)
    row = c.fetchone()
    country_code = row["country_code"] if row else None

    # 1. Fetch file paths for university documents
    c.execute(f"SELECT stored_path FROM attachments WHERE parent_type = 'university' AND parent_id IN ({placeholders})", clean_ids)
    uni_files = [r["stored_path"] for r in c.fetchall()]

    # 2. Fetch professor IDs and their attachments
    c.execute(f"SELECT id FROM professors WHERE university_id IN ({placeholders})", clean_ids)
    prof_ids = [r["id"] for r in c.fetchall()]
    prof_files = []
    if prof_ids:
        p_placeholders = ",".join("?" * len(prof_ids))
        c.execute(f"SELECT stored_path FROM attachments WHERE parent_type = 'professor' AND parent_id IN ({p_placeholders})", prof_ids)
        prof_files = [r["stored_path"] for r in c.fetchall()]

    # 3. Clean files from disk
    for rel_path in (uni_files + prof_files):
        target = app_root / rel_path
        if target.exists() and target.is_file():
            try:
                target.unlink()
            except Exception:
                pass

    # Clean local cached Wikipedia images
    for u_id in clean_ids:
        cached_img = app_root / "ui" / "cache" / "images" / f"{u_id}.jpg"
        if cached_img.exists() and cached_img.is_file():
            try:
                cached_img.unlink()
            except Exception:
                pass

    # 4. Clean database rows
    c.execute(f"DELETE FROM attachments WHERE parent_type = 'university' AND parent_id IN ({placeholders})", clean_ids)
    if prof_ids:
        c.execute(f"DELETE FROM attachments WHERE parent_type = 'professor' AND parent_id IN ({p_placeholders})", prof_ids)

    c.execute(f"DELETE FROM tasks WHERE university_id IN ({placeholders})", clean_ids)
    c.execute(f"DELETE FROM professors WHERE university_id IN ({placeholders})", clean_ids)
    c.execute(f"DELETE FROM universities WHERE id IN ({placeholders})", clean_ids)

    remaining_in_country = 0
    if country_code:
        c.execute("SELECT COUNT(*) as count FROM universities WHERE country_code = ?", (country_code,))
        remaining_in_country = c.fetchone()["count"]

    conn.commit()
    conn.close()
    return {"country_code": country_code, "remaining": remaining_in_country}

def db_batch_update_university_status(uni_ids, status):
    if not uni_ids:
        return False
    clean_ids = [int(i) for i in uni_ids]
    placeholders = ",".join("?" * len(clean_ids))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE universities SET status = ? WHERE id IN ({placeholders})", [status] + clean_ids)
    conn.commit()
    conn.close()
    return True

def db_get_pipeline_universities():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT u.*, c.name as country_name 
        FROM universities u
        LEFT JOIN countries c ON u.country_code = c.code
        ORDER BY CASE 
            WHEN u.deadline IS NULL OR u.deadline = '' THEN 1 
            ELSE 0 END, u.deadline ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_update_university_status(uni_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE universities SET status = ? WHERE id = ?", (status, int(uni_id)))
    conn.commit()
    conn.close()
    return True

def db_get_universities_missing_images():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, name, image_url FROM universities WHERE image_url IS NULL OR image_url NOT LIKE 'cache/%'")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_update_university_image(uni_id, local_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE universities SET image_url = ? WHERE id = ?", (local_path, int(uni_id)))
    conn.commit()
    conn.close()
    return True

# --- Professor Operations ---

def db_add_professor(uni_id, name, email, research, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO professors (university_id, name, email, research_interests, outreach_status) VALUES (?, ?, ?, ?, ?)",
        (int(uni_id), name, email, research, status)
    )
    prof_id = c.lastrowid
    conn.commit()
    conn.close()
    return prof_id

def db_get_professors(uni_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM professors WHERE university_id = ? ORDER BY id DESC", (int(uni_id),))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_update_professor(prof_id, name, email, research, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """UPDATE professors 
           SET name = ?, email = ?, research_interests = ?, outreach_status = ?
           WHERE id = ?""",
        (name, email, research, status, int(prof_id))
    )
    conn.commit()
    conn.close()
    return True

def db_delete_professor(prof_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    p_id = int(prof_id)

    c.execute("SELECT stored_path FROM attachments WHERE parent_type = 'professor' AND parent_id = ?", (p_id,))
    app_root = DB_PATH.parent.parent
    for r in c.fetchall():
        target = app_root / r["stored_path"]
        if target.exists() and target.is_file():
            try:
                target.unlink()
            except Exception:
                pass

    c.execute("DELETE FROM attachments WHERE parent_type = 'professor' AND parent_id = ?", (p_id,))
    c.execute("DELETE FROM tasks WHERE professor_id = ?", (p_id,))
    c.execute("DELETE FROM professors WHERE id = ?", (p_id,))

    conn.commit()
    conn.close()
    return True

def db_get_outreach_professors():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT p.*, u.name as university_name, u.country_code
        FROM professors p
        JOIN universities u ON p.university_id = u.id
        ORDER BY p.id DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_update_professor_status(prof_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE professors SET outreach_status = ? WHERE id = ?", (status, int(prof_id)))
    conn.commit()
    conn.close()
    return True

# --- Attachment Operations ---

def db_add_attachment(parent_type, parent_id, file_name, stored_path):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO attachments (parent_type, parent_id, file_name, stored_path) VALUES (?, ?, ?, ?)",
        (parent_type, int(parent_id), file_name, stored_path)
    )
    conn.commit()
    conn.close()

def db_get_attachments(parent_type, parent_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM attachments WHERE parent_type = ? AND parent_id = ?", (parent_type, int(parent_id)))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_delete_attachment(attachment_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT stored_path FROM attachments WHERE id = ?", (int(attachment_id),))
    row = c.fetchone()
    if row:
        app_root = DB_PATH.parent.parent
        target = app_root / row[0]
        if target.exists():
            target.unlink()
        c.execute("DELETE FROM attachments WHERE id = ?", (int(attachment_id),))
        conn.commit()
    conn.close()
    return True

# --- Task Operations ---

def db_add_task(title, due_date=None, uni_id=None, prof_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    u_id = int(uni_id) if uni_id else None
    p_id = int(prof_id) if prof_id else None
    c.execute(
        "INSERT INTO tasks (title, due_date, university_id, professor_id, is_completed) VALUES (?, ?, ?, ?, 0)",
        (title, due_date, u_id, p_id)
    )
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id

def db_get_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT t.*, u.name as uni_name, p.name as prof_name 
        FROM tasks t
        LEFT JOIN universities u ON t.university_id = u.id
        LEFT JOIN professors p ON t.professor_id = p.id
        ORDER BY t.is_completed ASC, CASE WHEN t.due_date IS NULL OR t.due_date = '' THEN 1 ELSE 0 END, t.due_date ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def db_toggle_task(task_id, is_completed):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (1 if is_completed else 0, int(task_id)))
    conn.commit()
    conn.close()
    return True

def db_delete_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
    conn.commit()
    conn.close()
    return True