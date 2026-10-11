"""Read-only preview tests; no sockets or private data are needed for routing tests."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

APP_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("grad_compass_web_preview",APP_ROOT / "web" / "server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class WebPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grad-compass-web-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "demo"
        subprocess.run([sys.executable,"-B",str(APP_ROOT/"scripts/create_demo.py"),str(self.directory)],check=True,capture_output=True)
        self.workspace = server.DemoWorkspace(self.directory)

    def route(self, path, method="GET"):
        handler = object.__new__(server.handler_for(self.workspace))
        handler.path = path
        result = {}
        def respond(status, payload, content_type="application/json; charset=utf-8"):
            result.update(status=status,payload=payload,content_type=content_type)
        handler.respond = respond
        getattr(handler,"do_" + method)()
        return result

    def test_overview_and_details_return_linked_synthetic_records(self):
        overview = self.route("/api/workspace")
        self.assertEqual(overview["status"],200)
        self.assertTrue(overview["payload"]["synthetic"])
        self.assertEqual(len(overview["payload"]["universities"]),3)
        detail = self.route("/api/universities/1")
        self.assertEqual(len(detail["payload"]["professors"]),1)
        self.assertEqual(len(detail["payload"]["tasks"]),2)
        self.assertEqual(self.route("/api/universities/999")["status"],404)

    def test_static_allowlist_does_not_expose_runtime_or_research_files(self):
        self.assertEqual(self.route("/")["status"],200)
        for path in ("/data/grad_compass.db","/private/profile.json","/../data/config.json","/%2e%2e/private/profile.json","/server.py","/api/universities/1%20OR%201=1"):
            self.assertEqual(self.route(path)["status"],404)

    def test_requests_are_read_only_and_preserve_database_bytes(self):
        database = self.directory / "grad_compass.db"
        digest = hashlib.sha256(database.read_bytes()).hexdigest()
        for method in ("POST","PUT","PATCH","DELETE"):
            self.assertEqual(self.route("/api/universities/1",method)["status"],405)
        self.route("/api/workspace")
        self.route("/api/universities/1")
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(),digest)
        with self.workspace.connect() as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM universities")
        connection.close()

    def test_unmarked_or_changed_workspace_is_refused(self):
        with sqlite3.connect(self.directory/"grad_compass.db") as connection:
            connection.execute("DELETE FROM app_synthetic_demo_guard")
        self.assertEqual(self.route("/api/workspace")["status"],500)
        with self.assertRaises(ValueError):server.DemoWorkspace(self.directory)
        with self.assertRaises(ValueError):server.DemoWorkspace(APP_ROOT/"data")

    def test_missing_workspace_does_not_create_a_database(self):
        path = Path(self.temp.name)/"missing"
        with self.assertRaises(ValueError):server.DemoWorkspace(path)
        self.assertFalse(path.exists())

    def test_response_headers_restrict_content_and_cross_origin_access(self):
        handler = object.__new__(server.handler_for(self.workspace))
        headers = {}
        handler.send_response = lambda status: headers.update(status=status)
        handler.send_header = lambda key,value: headers.update({key:value})
        handler.end_headers = lambda:None
        handler.wfile = io.BytesIO()
        handler.respond(200,{"example":"invented"})
        self.assertEqual(headers["X-Content-Type-Options"],"nosniff")
        self.assertEqual(headers["Cache-Control"],"no-store")
        self.assertIn("script-src 'self'",headers["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin",headers)
        self.assertEqual(json.loads(handler.wfile.getvalue()),{"example":"invented"})


if __name__ == "__main__":unittest.main()
