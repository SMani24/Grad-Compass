import os
import sys
import json
import sqlite3
import webview
from pathlib import Path
from core.database import init_db, DB_PATH

class GradCompassAPI:
    """Methods exposed directly to the JavaScript UI via window.pywebview.api"""

    def get_active_countries(self):
        """Returns ISO codes of countries that have universities logged."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT country_code FROM universities")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows if r[0]]

    def get_geojson_data(self):
        """Reads local vector boundaries directly, bypassing browser CORS."""
        geojson_path = Path(__file__).resolve().parent / "ui" / "data" / "countries.geo.json"
        if not geojson_path.exists():
            print(f"[Error] GeoJSON file missing at: {geojson_path}")
            return None
        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Error] Failed to parse GeoJSON: {e}")
            return None

    def log(self, message):
        print(f"[UI]: {message}")
        return True

def main():
    init_db()

    api = GradCompassAPI()
    ui_entry = Path(__file__).resolve().parent / "ui" / "index.html"

    window = webview.create_window(
        title="Grad Compass",
        url=str(ui_entry),
        js_api=api,
        width=1340,
        height=860,
        min_size=(980, 680),
        background_color="#f8fafc"
    )

    webview.start(debug=False)

if __name__ == "__main__":
    main()