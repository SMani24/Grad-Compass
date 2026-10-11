"""Read-only, loopback-only browser preview of explicitly marked synthetic data."""
import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))
from core.paths import validate_data_directory

DEMO_MARKER = "grad-compass-app-demo-v1"
STATIC_FILES = {
    "/": (APP_ROOT / "web" / "index.html", "text/html; charset=utf-8"),
    "/styles.css": (APP_ROOT / "web" / "styles.css", "text/css; charset=utf-8"),
    "/app.js": (APP_ROOT / "web" / "app.js", "text/javascript; charset=utf-8"),
    "/vendor/leaflet.js": (APP_ROOT / "ui" / "vendor" / "leaflet.js", "text/javascript; charset=utf-8"),
    "/vendor/leaflet.css": (APP_ROOT / "ui" / "vendor" / "leaflet.css", "text/css; charset=utf-8"),
    "/flags.js": (APP_ROOT / "ui" / "js" / "flags.js", "text/javascript; charset=utf-8"),
}


class DemoWorkspace:
    def __init__(self, directory):
        self.directory = validate_data_directory(directory)
        self.database = self.directory / "grad_compass.db"
        with closing(self.connect()) as connection:
            pass

    def connect(self):
        if self.database.is_symlink() or not self.database.is_file() or self.database.stat().st_nlink != 1:
            raise ValueError("Preview requires an existing, unlinked synthetic database")
        if self.database.resolve().parent != self.directory:
            raise ValueError("Preview database is outside its workspace")
        connection = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            marker = connection.execute("SELECT marker FROM app_synthetic_demo_guard").fetchall()
            if [row[0] for row in marker] != [DEMO_MARKER]:
                raise ValueError("Preview requires a marked synthetic workspace")
        except (sqlite3.Error,ValueError):
            connection.close()
            raise ValueError("Preview requires a workspace created by create_demo.py") from None
        return connection

    def overview(self):
        with closing(self.connect()) as connection:
            universities = [dict(row) for row in connection.execute("""
                SELECT u.id,u.name,u.country_code,u.city,u.latitude,u.longitude,u.deadline,u.status,u.portal_url,
                       (SELECT COUNT(*) FROM professors p WHERE p.university_id=u.id) AS faculty_count
                FROM universities u ORDER BY u.name
            """)]
            return {"synthetic": True, "universities": universities}

    def university(self, university_id):
        with closing(self.connect()) as connection:
            university = connection.execute("""
                SELECT id,name,country_code,city,latitude,longitude,deadline,status,portal_url
                FROM universities WHERE id=?
            """, (university_id,)).fetchone()
            if not university:
                return None
            professors = [dict(row) for row in connection.execute("""
                SELECT id,name,email,research_interests,outreach_status FROM professors WHERE university_id=? ORDER BY name
            """, (university_id,))]
            tasks = [dict(row) for row in connection.execute("""
                SELECT DISTINCT t.id,t.title,t.due_date,t.is_completed FROM tasks t
                LEFT JOIN professors p ON p.id=t.professor_id
                WHERE t.university_id=? OR p.university_id=? ORDER BY t.is_completed,t.due_date,t.id
            """, (university_id,university_id))]
            return {"university":dict(university), "professors":professors, "tasks":tasks}


def handler_for(workspace):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Do not log query strings, private request contents, or local paths.

        def respond(self, status, payload, content_type="application/json; charset=utf-8"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
            try:
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Closing the desktop window can cancel an in-flight map response.

        def do_GET(self):
            route = urlsplit(self.path).path
            try:
                if route in STATIC_FILES:
                    filename, content_type = STATIC_FILES[route]
                    return self.respond(200,filename.read_bytes(),content_type)
                if route == "/api/map":
                    return self.respond(200,(APP_ROOT/"ui/data/countries.geo.json").read_bytes())
                if route == "/api/workspace":
                    return self.respond(200,workspace.overview())
                match = re.fullmatch(r"/api/universities/([1-9][0-9]{0,9})",route)
                if match:
                    result = workspace.university(int(match[1]))
                    return self.respond(200,result) if result else self.respond(404,{"error":"University not found"})
                return self.respond(404,{"error":"Not found"})
            except (OSError,ValueError,sqlite3.Error):
                self.respond(500,{"error":"Could not load the preview workspace"})

        def do_POST(self):
            self.respond(405,{"error":"This preview is read-only"})

        do_PUT = do_PATCH = do_DELETE = do_POST

    return Handler


def create_server(directory, port=8765):
    workspace = DemoWorkspace(directory)
    return ThreadingHTTPServer(("127.0.0.1",port),handler_for(workspace))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir",type=Path,required=True)
    parser.add_argument("--port",type=int,default=8765)
    args = parser.parse_args()
    try:
        server = create_server(args.data_dir,args.port)
    except (ValueError,OSError) as error:
        parser.error(str(error))
    print(f"Local synthetic preview: http://127.0.0.1:{server.server_port}",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
