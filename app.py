import os
import sys
import json
import sqlite3
import webview
from pathlib import Path
from core.database import (
    init_db, DB_PATH,
    db_add_university, db_get_universities_by_country,
    db_add_professor, db_get_professors,
    db_add_attachment, db_get_attachments, db_delete_attachment
)
from core.geocoder import geocode_institution
from core.vault import store_file, open_system_file

CONFIG_PATH = Path(__file__).resolve().parent / "data" / "config.json"
main_window = None

DEFAULT_CONFIG = {
    "window_width": 1340,
    "window_height": 860,
    "font_scale": "Normal",
    "map_zoom": 3.0
}

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(updates: dict):
    cfg = load_config()
    cfg.update(updates)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[Config Error] Failed to write config: {e}")

class GradCompassAPI:
    def get_config(self):
        return load_config()

    def save_settings(self, updates):
        if isinstance(updates, str):
            try:
                updates = json.loads(updates)
            except Exception:
                pass
        if isinstance(updates, dict):
            save_config(updates)
            return True
        return False

    def close_app(self):
        global main_window
        if main_window:
            on_window_closing()
            main_window.destroy()

    def get_active_countries(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT DISTINCT country_code FROM universities")
        rows = c.fetchall()
        conn.close()
        return [r[0] for r in rows if r[0]]

    def get_geojson_data(self):
        geojson_path = Path(__file__).resolve().parent / "ui" / "data" / "countries.geo.json"
        if not geojson_path.exists():
            return None
        with open(geojson_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def add_university(self, country_code, country_name, name, city, deadline, portal_url):
        lat, lng = geocode_institution(name, country_name, city)
        uni_id = db_add_university(country_code, name, city, lat, lng, deadline, portal_url)
        return {
            "id": uni_id,
            "name": name,
            "city": city,
            "latitude": lat,
            "longitude": lng,
            "geocoded": lat is not None
        }

    def get_universities(self, country_code):
        return db_get_universities_by_country(country_code)

    def add_professor(self, uni_id, name, email, research, status):
        prof_id = db_add_professor(uni_id, name, email, research, status)
        return {"id": prof_id, "name": name, "outreach_status": status}

    def get_professors(self, uni_id):
        return db_get_professors(uni_id)

    def pick_and_attach_file(self, parent_type, parent_id):
        global main_window
        file_types = ("All Accepted (*.pdf;*.docx;*.txt;*.png)", "PDF files (*.pdf)", "All files (*.*)")
        paths = main_window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if paths and len(paths) > 0:
            stored = store_file(paths[0], parent_type, parent_id)
            if stored:
                db_add_attachment(parent_type, parent_id, stored["file_name"], stored["stored_path"])
                return {"success": True, "file_name": stored["file_name"]}
        return {"success": False}

    def get_attachments(self, parent_type, parent_id):
        return db_get_attachments(parent_type, parent_id)

    def open_file(self, rel_path):
        return open_system_file(rel_path)

    def delete_attachment(self, attachment_id):
        return db_delete_attachment(attachment_id)

    def log(self, msg):
        print(f"[UI]: {msg}")
        return True

def on_window_closing():
    global main_window
    if main_window:
        try:
            save_config({
                "window_width": main_window.width,
                "window_height": main_window.height
            })
        except Exception:
            pass

def on_window_resized(width, height):
    save_config({
        "window_width": width,
        "window_height": height
    })

def main():
    global main_window
    init_db()
    cfg = load_config()
    api = GradCompassAPI()
    ui_entry = Path(__file__).resolve().parent / "ui" / "index.html"

    main_window = webview.create_window(
        title="Grad Compass",
        url=str(ui_entry),
        js_api=api,
        width=cfg.get("window_width", 1340),
        height=cfg.get("window_height", 860),
        min_size=(980, 680),
        background_color="#f8fafc"
    )

    main_window.events.closing += on_window_closing
    main_window.events.resized += on_window_resized

    webview.start(debug=False)

if __name__ == "__main__":
    main()