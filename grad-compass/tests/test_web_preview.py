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
from types import SimpleNamespace

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

    def preference_request(self, payload, path="/api/display-preferences", **headers):
        handler = object.__new__(server.handler_for(self.workspace, session_token="test-session"))
        handler.path = path
        raw = json.dumps(payload).encode()
        handler.headers = {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json", "Content-Length": str(len(raw)),
            "X-Grad-Compass-Session": "test-session", **headers}
        handler.server = SimpleNamespace(server_port=8765)
        handler.rfile = io.BytesIO(raw)
        result = {}
        handler.respond = lambda status, payload: result.update(status=status, payload=payload)
        handler.do_POST()
        return result

    def test_display_preferences_persist_without_changing_database(self):
        digest = hashlib.sha256(self.workspace.database.read_bytes()).hexdigest()
        self.assertEqual(self.route("/api/display-preferences")["payload"]["text_size"], "standard")
        path = self.directory / "display-preferences.json"
        self.assertFalse(path.exists())
        for size in ("comfortable", "large", "extra-large", "standard"):
            self.assertEqual(self.preference_request({"text_size": size})["status"], 200)
            reopened = server.DemoWorkspace(self.directory)
            self.assertEqual(reopened.display_preferences(), {"text_size": size})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(hashlib.sha256(self.workspace.database.read_bytes()).hexdigest(), digest)
        self.assertEqual(self.route("/display-preferences.json")["status"], 404)

    def test_display_preferences_reject_invalid_and_cross_origin_writes(self):
        for payload in ({"text_size": "huge"}, {"text_size": None}, {"text_size": []},
                        {"text_size": "large", "file": "config.json"}, []):
            self.assertEqual(self.preference_request(payload)["status"], 409)
        for headers in ({"Origin": "https://example.com"}, {"Host": "example.com"},
                        {"X-Grad-Compass-Session": "wrong"}):
            self.assertEqual(self.preference_request({"text_size": "large"}, **headers)["status"], 403)
        self.assertFalse((self.directory / "display-preferences.json").exists())

    def test_display_preferences_refuse_links_and_changed_workspace(self):
        path = self.directory / "display-preferences.json"
        target = Path(self.temp.name) / "other.json"
        target.write_text('{"text_size":"standard"}')
        path.symlink_to(target)
        self.assertEqual(self.preference_request({"text_size": "large"})["status"], 409)
        self.assertEqual(target.read_text(), '{"text_size":"standard"}')
        path.unlink()
        import os
        os.link(target, path)
        self.assertEqual(self.preference_request({"text_size": "large"})["status"], 409)
        path.unlink()
        with sqlite3.connect(self.workspace.database) as connection:
            connection.execute("DELETE FROM app_synthetic_demo_guard")
        self.assertEqual(self.preference_request({"text_size": "large"})["status"], 409)
        self.assertFalse(path.exists())

    def test_country_evidence_empty_coverage_is_distinct_from_personal_decision(self):
        result = self.route("/api/countries/FRA")["payload"]
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["university_count"],0)
        self.assertEqual(result["review_status"],"unreviewed_demo")
        self.assertTrue(result["sources"])
        self.assertTrue(result["uncertainties"])
        digest = hashlib.sha256(self.workspace.database.read_bytes()).hexdigest()
        for decision in ("Considering", "Shortlisted", "On hold", "Excluded"):
            response = self.preference_request({"country_code":"FRA", "decision":decision}, path="/api/country-decisions")
            self.assertEqual(response["status"],200)
            self.assertEqual(server.DemoWorkspace(self.directory).country_decisions()["FRA"],decision)
            current = self.route("/api/countries/FRA")["payload"]
            self.assertEqual(current["decision"],decision)
            self.assertEqual(current["review_status"],result["review_status"])
            self.assertEqual(current["summary"],result["summary"])
        self.assertEqual(hashlib.sha256(self.workspace.database.read_bytes()).hexdigest(),digest)
        self.assertEqual(self.route("/api/countries/ATA")["status"],404)
        untouched = self.route("/api/countries/JPN")["payload"]
        self.assertEqual(untouched["review_status"],"not_researched")
        self.assertEqual(untouched["sources"],[])

    def test_country_decisions_preserve_other_choices_and_reject_unsafe_writes(self):
        path="/api/country-decisions"
        for code in ("CAN", "FRA"):
            self.assertEqual(self.preference_request({"country_code":code,"decision":"Considering"},path=path)["status"],200)
        for payload in ({"country_code":None,"decision":"Excluded"}, {"country_code":"CAN","decision":[]},
                        {"country_code":"ATA","decision":"Excluded"}, {"country_code":"CAN","decision":"accepted"},
                        {"country_code":"CAN","decision":"Excluded","review":"accepted"}):
            self.assertEqual(self.preference_request(payload,path=path)["status"],409)
        self.assertEqual(self.preference_request({"country_code":"CAN","decision":"Excluded"},path=path,Origin="https://example.com")["status"],403)
        self.assertEqual(self.workspace.country_decisions(),{"CAN":"Considering","FRA":"Considering"})
        self.preference_request({"country_code":"CAN","decision":""},path=path)
        self.assertEqual(self.workspace.country_decisions(),{"FRA":"Considering"})
        file=self.directory / "country-decisions.json"
        self.assertEqual(file.stat().st_mode & 0o777,0o600)
        file.unlink()
        target=Path(self.temp.name)/"other.json";target.write_text('{}')
        file.symlink_to(target)
        self.assertEqual(self.preference_request({"country_code":"CAN","decision":"Considering"},path=path)["status"],409)
        self.assertEqual(target.read_text(),'{}')
        file.unlink();file.write_text('{broken')
        self.assertEqual(self.preference_request({"country_code":"CAN","decision":"Considering"},path=path)["status"],409)
        self.assertEqual(file.read_text(),'{broken')

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
