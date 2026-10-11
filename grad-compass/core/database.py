import sqlite3
from contextlib import closing
from core.paths import DB_PATH, CACHE_DIR, validate_database_path
from core.vault import delete_stored_file

SCHEMA_VERSION = 1


def _connect():
    conn = sqlite3.connect(validate_database_path(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    validate_database_path(DB_PATH)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect()) as conn, conn:
        cursor = conn.cursor()

        version = cursor.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise ValueError("Unsupported application database version")

        cursor.executescript("""
        BEGIN IMMEDIATE;
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

        columns = {row[1] for row in cursor.execute("PRAGMA table_info(universities)")}
        if "image_url" not in columns:
            cursor.execute("ALTER TABLE universities ADD COLUMN image_url TEXT")

        cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


# --- University Operations ---

def db_add_university(country_code, name, city, lat, lng, deadline, portal_url, image_url=None):
    code = (country_code or "UNKNOWN").strip().upper()
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO countries (code, name) VALUES (?, ?)", (code, code))
        c.execute(
            """INSERT INTO universities
               (country_code, name, city, latitude, longitude, deadline, portal_url, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, name, city, lat, lng, deadline, portal_url, image_url)
        )
        uni_id = c.lastrowid
        return uni_id

def db_get_university(uni_id):
    with closing(_connect()) as conn, conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM universities WHERE id = ?", (int(uni_id),))
        row = c.fetchone()
        return dict(row) if row else None

def db_get_universities_by_country(country_code):
    with closing(_connect()) as conn, conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM universities WHERE country_code = ? ORDER BY name ASC", (country_code.upper(),))
        rows = [dict(r) for r in c.fetchall()]
        return rows

def db_update_university(uni_id, name, city, lat, lng, deadline, portal_url, image_url=None):
    with closing(_connect()) as conn, conn:
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
        return True

def db_delete_university(uni_id):
    return db_delete_universities_batch([uni_id])

def _cleanup_unreferenced_files(stored_paths):
    # Metadata has already committed. Serialize against writers while checking references.
    with closing(_connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        for stored_path in set(stored_paths):
            referenced = conn.execute(
                "SELECT 1 FROM attachments WHERE stored_path = ? LIMIT 1", (stored_path,)
            ).fetchone()
            if not referenced:
                delete_stored_file(stored_path)


def db_delete_universities_batch(uni_ids):
    """Commit relational deletion before attempting contained file cleanup."""
    if not uni_ids:
        return {"country_code": None, "remaining": 0}
    clean_ids = [int(i) for i in uni_ids]
    placeholders = ",".join("?" * len(clean_ids))
    files = []
    with closing(_connect()) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            f"SELECT id, country_code FROM universities WHERE id IN ({placeholders}) ORDER BY id", clean_ids
        ).fetchall()
        country_code = rows[0]["country_code"] if rows else None
        actual_ids = [row["id"] for row in rows]
        files.extend(row[0] for row in conn.execute(
            f"SELECT stored_path FROM attachments WHERE parent_type='university' AND parent_id IN ({placeholders})", clean_ids
        ))
        prof_ids = [row[0] for row in conn.execute(
            f"SELECT id FROM professors WHERE university_id IN ({placeholders})", clean_ids
        )]
        if prof_ids:
            p_placeholders = ",".join("?" * len(prof_ids))
            files.extend(row[0] for row in conn.execute(
                f"SELECT stored_path FROM attachments WHERE parent_type='professor' AND parent_id IN ({p_placeholders})", prof_ids
            ))
            conn.execute(f"DELETE FROM attachments WHERE parent_type='professor' AND parent_id IN ({p_placeholders})", prof_ids)
            conn.execute(f"DELETE FROM tasks WHERE professor_id IN ({p_placeholders})", prof_ids)
        conn.execute(f"DELETE FROM attachments WHERE parent_type='university' AND parent_id IN ({placeholders})", clean_ids)
        conn.execute(f"DELETE FROM tasks WHERE university_id IN ({placeholders})", clean_ids)
        conn.execute(f"DELETE FROM professors WHERE university_id IN ({placeholders})", clean_ids)
        conn.execute(f"DELETE FROM universities WHERE id IN ({placeholders})", clean_ids)
        remaining = conn.execute("SELECT COUNT(*) FROM universities WHERE country_code=?", (country_code,)).fetchone()[0] if country_code else 0

    _cleanup_unreferenced_files(files)
    for uni_id in actual_ids:
        target = CACHE_DIR / f"{uni_id}.jpg"
        if not any(part.is_symlink() for part in (target, *target.parents)):
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass  # A leftover cache is safer than rolling back committed metadata.
    return {"country_code": country_code, "remaining": remaining}

def db_batch_update_university_status(uni_ids, status):
    if not uni_ids:
        return False
    clean_ids = [int(i) for i in uni_ids]
    placeholders = ",".join("?" * len(clean_ids))
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute(f"UPDATE universities SET status = ? WHERE id IN ({placeholders})", [status] + clean_ids)
        return True

def db_get_pipeline_universities():
    with closing(_connect()) as conn, conn:
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
        return rows

def db_update_university_status(uni_id, status):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute("UPDATE universities SET status = ? WHERE id = ?", (status, int(uni_id)))
        return True

def db_get_universities_missing_images():
    with closing(_connect()) as conn, conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, name, image_url FROM universities WHERE image_url IS NULL OR (image_url NOT LIKE 'cache/%' AND image_url NOT LIKE 'file:%')")
        rows = [dict(r) for r in c.fetchall()]
        return rows

def db_update_university_image(uni_id, local_path):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute("UPDATE universities SET image_url = ? WHERE id = ?", (local_path, int(uni_id)))
        return True

# --- Professor Operations ---

def db_add_professor(uni_id, name, email, research, status):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO professors (university_id, name, email, research_interests, outreach_status) VALUES (?, ?, ?, ?, ?)",
            (int(uni_id), name, email, research, status)
        )
        prof_id = c.lastrowid
        return prof_id

def db_get_professors(uni_id):
    with closing(_connect()) as conn, conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM professors WHERE university_id = ? ORDER BY id DESC", (int(uni_id),))
        rows = [dict(r) for r in c.fetchall()]
        return rows

def db_update_professor(prof_id, name, email, research, status):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute(
            """UPDATE professors
               SET name = ?, email = ?, research_interests = ?, outreach_status = ?
               WHERE id = ?""",
            (name, email, research, status, int(prof_id))
        )
        return True

def db_delete_professor(prof_id):
    p_id = int(prof_id)
    with closing(_connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        files = [row[0] for row in conn.execute(
            "SELECT stored_path FROM attachments WHERE parent_type='professor' AND parent_id=?", (p_id,)
        )]
        conn.execute("DELETE FROM attachments WHERE parent_type='professor' AND parent_id=?", (p_id,))
        conn.execute("DELETE FROM tasks WHERE professor_id=?", (p_id,))
        conn.execute("DELETE FROM professors WHERE id=?", (p_id,))
    _cleanup_unreferenced_files(files)
    return True

def db_get_outreach_professors():
    with closing(_connect()) as conn, conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT p.*, u.name as university_name, u.country_code
            FROM professors p
            JOIN universities u ON p.university_id = u.id
            ORDER BY p.id DESC
        """)
        rows = [dict(r) for r in c.fetchall()]
        return rows

def db_update_professor_status(prof_id, status):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute("UPDATE professors SET outreach_status = ? WHERE id = ?", (status, int(prof_id)))
        return True

# --- Attachment Operations ---

def db_add_attachment(parent_type, parent_id, file_name, stored_path):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO attachments (parent_type, parent_id, file_name, stored_path) VALUES (?, ?, ?, ?)",
            (parent_type, int(parent_id), file_name, stored_path)
        )

def db_get_attachments(parent_type, parent_id):
    with closing(_connect()) as conn, conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM attachments WHERE parent_type = ? AND parent_id = ?", (parent_type, int(parent_id)))
        rows = [dict(r) for r in c.fetchall()]
        return rows

def db_delete_attachment(attachment_id):
    with closing(_connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT stored_path FROM attachments WHERE id=?", (int(attachment_id),)).fetchone()
        conn.execute("DELETE FROM attachments WHERE id=?", (int(attachment_id),))
    if row:
        _cleanup_unreferenced_files([row[0]])
    return True

# --- Task Operations ---

def db_add_task(title, due_date=None, uni_id=None, prof_id=None):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        u_id = int(uni_id) if uni_id else None
        p_id = int(prof_id) if prof_id else None
        c.execute(
            "INSERT INTO tasks (title, due_date, university_id, professor_id, is_completed) VALUES (?, ?, ?, ?, 0)",
            (title, due_date, u_id, p_id)
        )
        task_id = c.lastrowid
        return task_id

def db_get_tasks():
    with closing(_connect()) as conn, conn:
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
        return rows

def db_toggle_task(task_id, is_completed):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (1 if is_completed else 0, int(task_id)))
        return True

def db_delete_task(task_id):
    with closing(_connect()) as conn, conn:
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
        return True
