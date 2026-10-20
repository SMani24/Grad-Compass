"""Loopback-only synthetic map preview and opt-in disposable exchange workflow."""
import argparse
from contextlib import closing, nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import tempfile
import threading
from pathlib import Path
import re
import secrets
import sqlite3
import sys
from urllib.parse import urlsplit,parse_qs

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))
from core.paths import validate_data_directory

DEMO_MARKER = "grad-compass-app-demo-v1"
STATIC_FILES = {
    "/": (APP_ROOT / "web" / "index.html", "text/html; charset=utf-8"),
    "/styles.css": (APP_ROOT / "web" / "styles.css", "text/css; charset=utf-8"),
    "/local_ui.js": (APP_ROOT / "web" / "local_ui.js", "text/javascript; charset=utf-8"),
    "/app.js": (APP_ROOT / "web" / "app.js", "text/javascript; charset=utf-8"),
    "/research_review.js": (APP_ROOT / "web" / "research_review.js", "text/javascript; charset=utf-8"),
    "/research.js": (APP_ROOT / "web" / "research.js", "text/javascript; charset=utf-8"),
    "/research.css": (APP_ROOT / "web" / "research.css", "text/css; charset=utf-8"),
    "/settings.js": (APP_ROOT / "web" / "settings.js", "text/javascript; charset=utf-8"),
    "/panels.js": (APP_ROOT / "web" / "panels.js", "text/javascript; charset=utf-8"),
    "/panels.css": (APP_ROOT / "web" / "panels.css", "text/css; charset=utf-8"),
    "/country_report.js": (APP_ROOT / "web" / "country_report.js", "text/javascript; charset=utf-8"),
    "/country_report.css": (APP_ROOT / "web" / "country_report.css", "text/css; charset=utf-8"),
    "/report_reader.js": (APP_ROOT / "web" / "report_reader.js", "text/javascript; charset=utf-8"),
    "/report_reader.css": (APP_ROOT / "web" / "report_reader.css", "text/css; charset=utf-8"),
    "/report-assets.json": (APP_ROOT / "web" / "assets" / "countries.json", "application/json"),
    "/assets/belgium-grand-place.jpg": (APP_ROOT / "web" / "assets" / "belgium-grand-place.jpg", "image/jpeg"),
    "/assets/belgium-flag-small.svg": (APP_ROOT / "web" / "assets" / "belgium-flag-small.svg", "image/svg+xml"),
    "/assets/belgium-locator.png": (APP_ROOT / "web" / "assets" / "belgium-locator.png", "image/png"),
    "/exchange.js": (APP_ROOT / "web" / "exchange.js", "text/javascript; charset=utf-8"),
    "/exchange.css": (APP_ROOT / "web" / "exchange.css", "text/css; charset=utf-8"),
    "/vendor/leaflet.js": (APP_ROOT / "ui" / "vendor" / "leaflet.js", "text/javascript; charset=utf-8"),
    "/vendor/leaflet.css": (APP_ROOT / "ui" / "vendor" / "leaflet.css", "text/css; charset=utf-8"),
    "/flags.js": (APP_ROOT / "ui" / "js" / "flags.js", "text/javascript; charset=utf-8"),
}


class DemoWorkspace:
    def __init__(self, directory):
        self.directory = validate_data_directory(directory)
        self.database = self.directory / "grad_compass.db"
        self.state_lock = threading.RLock()
        self._research = None
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

    def display_preferences(self, size=None):
        """Persist display choices only in the marked, disposable app workspace."""
        with closing(self.connect()):
            pass
        path = self.directory / "display-preferences.json"
        if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1)):
            raise ValueError("Display preferences must be an unlinked workspace file")
        sizes = {"standard", "comfortable", "large", "extra-large"}
        if size is None:
            if not path.exists():
                return {"text_size": "standard"}
            try:
                saved = json.loads(path.read_text())
                if not isinstance(saved, dict) or saved.get("text_size") not in sizes:
                    raise ValueError("Invalid saved display preferences")
                return {"text_size": saved["text_size"]}
            except (json.JSONDecodeError, TypeError):
                raise ValueError("Invalid saved display preferences") from None
        if not isinstance(size, str) or size not in sizes:
            raise ValueError("Choose an available text size")
        descriptor, temporary = tempfile.mkstemp(prefix=".display-", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w") as output:
                json.dump({"text_size": size}, output)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return {"text_size": size}

    def country_decisions(self, code=None, decision=None):
        from web.country_evidence import COUNTRY_CODES, DECISIONS
        with self.state_lock, closing(self.connect()):
            if any(path.is_symlink() for path in (self.directory, *self.directory.parents)):
                raise ValueError("Personal decisions require an unlinked synthetic workspace")
            path = self.directory / "country-decisions.json"
            if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1)):
                raise ValueError("Personal decisions require an unlinked workspace file")
            saved = {}
            if path.exists():
                if path.stat().st_size > 65536:
                    raise ValueError("Invalid saved country decisions")
                try:
                    saved = json.loads(path.read_text())
                    if not isinstance(saved, dict) or any(key not in COUNTRY_CODES or value not in DECISIONS for key,value in saved.items()):
                        raise ValueError("Invalid saved country decisions")
                except (json.JSONDecodeError, TypeError):
                    raise ValueError("Invalid saved country decisions") from None
            if code is None:
                return saved
            if not isinstance(code, str) or code not in COUNTRY_CODES or not isinstance(decision, str) or decision not in (*DECISIONS, ""):
                raise ValueError("Choose a displayed country and personal decision")
            if decision:
                saved[code] = decision
            else:
                saved.pop(code, None)
            descriptor, temporary = tempfile.mkstemp(prefix=".country-decisions-", dir=self.directory)
            try:
                with os.fdopen(descriptor, "w") as output:
                    json.dump(saved, output)
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return saved

    @property
    def research(self):
        with self.state_lock:
            if self._research is None:
                from web.research import ResearchWorkspace
                self._research = ResearchWorkspace(self)
            return self._research

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


def handler_for(workspace, exchange=None, session_token=None, profiles=None, clipboard=None):
    initial_workspace=workspace
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Do not log query strings, private request contents, or local paths.

        def respond(self, status, payload, content_type="application/json; charset=utf-8",filename=None):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Referrer-Policy","no-referrer")
            if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
            try:
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Closing the desktop window can cancel an in-flight map response.

        def do_GET(self):
            try:
                with profiles.request_context() if profiles else nullcontext():return self._get()
            except ValueError as error:return self.respond(409,{'error':str(error)})

        def _get(self):
            workspace=profiles.workspace if profiles else initial_workspace
            session_token=profiles.session_token if profiles else initial_token
            route = urlsplit(self.path).path
            if hasattr(self, "server") and self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                return self.respond(403,{"error":"Open the local app address to read this workspace"})
            try:
                if route in STATIC_FILES:
                    filename, content_type = STATIC_FILES[route]
                    return self.respond(200,filename.read_bytes(),content_type)
                if route == "/api/map":
                    return self.respond(200,(APP_ROOT/"ui/data/countries.geo.json").read_bytes())
                if route == "/api/workspace":
                    from web.discovery import overview
                    return self.respond(200,{**overview(workspace, exchange), "country_decisions": workspace.country_decisions(), "research": workspace.research.snapshot(), "session": session_token, "receipt": getattr(workspace,"last_receipt",None), "profiles":profiles.snapshot() if profiles else None})
                if route == "/api/local/removed" and getattr(workspace,"operational",False):
                    return self.respond(200,{"universities":workspace.removed_universities()})
                if route == "/api/local/inbox" and getattr(workspace,"operational",False):
                    from web.inbox import receiver_for
                    return self.respond(200,{**receiver_for(workspace).status(),'session':session_token})
                if route == "/api/local/reset-preview" and profiles:
                    return self.respond(200,profiles.reset_preview())
                if route == "/api/local/history" and getattr(workspace,"operational",False):
                    return self.respond(200,workspace.archived_requests())
                archive_match = re.fullmatch(r"/api/local/history/([a-f0-9-]{36})",route)
                if archive_match and getattr(workspace,"operational",False):
                    result=workspace.archived_requests(archive_match[1])
                    return self.respond(200,result) if result else self.respond(404,{"error":"Archived request not found"})
                request_match = re.fullmatch(r"/api/research/requests/([a-f0-9-]{36})",route)
                if request_match:
                    return self.respond(200,workspace.research.request(request_match[1]))
                if route == "/api/research":
                    return self.respond(200,{**workspace.research.snapshot(), "session": session_token})
                if route.startswith('/api/reports') and getattr(workspace,'operational',False):
                    from web import report_packages as packages
                    query=parse_qs(urlsplit(self.path).query)
                    if route=='/api/reports':
                        catalog=packages.catalog(workspace,query.get('request_id',[None])[0])
                        return self.respond(200,{'reports':[packages.public(r) for r in catalog['reports']],'errors':catalog['errors']})
                    if route=='/api/reports/reading':
                        from web.report_reading import preferences as reading_preferences
                        return self.respond(200,reading_preferences(workspace))
                    match=re.fullmatch(r'/api/reports/([a-f0-9]{64})/(annotations|pdf|page|image|markdown)',route)
                    if match:
                        key,operation=match.groups()
                        if operation=='annotations':return self.respond(200,packages.annotations(workspace,key))
                        from web.report_pdf import ensure_pdf,page_data
                        report=packages.get(workspace,key,query.get('edition',[None])[0])
                        if operation=='markdown':
                            from web.report_export import markdown,filename
                            choice=query.get('annotations',['0'])[0]
                            if choice not in ('0','1'):raise ValueError('Choose whether to include personal annotations')
                            return self.respond(200,markdown(workspace,report,choice=='1'),'text/markdown; charset=utf-8',filename(report,'-detailed'+('-with-annotations' if choice=='1' else '')+'.md'))
                        if operation=='pdf':
                            pdf=ensure_pdf(workspace,report,query.get('pdf_sha256',[None])[0])
                            return self.respond(200,pdf['path'].read_bytes(),'application/pdf',pdf['filename'])
                        page=int(query.get('page',['0'])[0])
                        return self.respond(200,page_data(workspace,report,page,operation=='image',query.get('pdf_sha256',[None])[0]),'image/png' if operation=='image' else 'application/json; charset=utf-8')
                if route == '/api/panel-widths':
                    from web.panels import preferences as panel_widths
                    return self.respond(200,{**panel_widths(workspace),'session':session_token})
                if route == "/api/display-preferences":
                    return self.respond(200, {**workspace.display_preferences(), "session": session_token})
                if route == "/api/exchange":
                    result = exchange.catalog() if exchange else {"batches": []}
                    return self.respond(200, {**result, "enabled": exchange is not None, "session": session_token})
                if route.startswith("/api/exchange/state/") and exchange:
                    return self.respond(200, exchange.state(route.removeprefix("/api/exchange/state/")))
                country = re.fullmatch(r"/api/countries/([A-Z0-9_]{1,80})", route)
                if country:
                    from web.country_evidence import detail
                    result = detail(workspace, exchange, country[1])
                    return self.respond(200,result) if result else self.respond(404,{"error":"Country not found"})
                match = re.fullmatch(r"/api/universities/((?:exchange-)?[1-9][0-9]{0,9}|local-[a-f0-9-]{36})",route)
                if match:
                    from web.discovery import university
                    result = university(workspace, exchange, match[1])
                    return self.respond(200,result) if result else self.respond(404,{"error":"University not found"})
                return self.respond(404,{"error":"Not found"})
            except (OSError,ValueError,sqlite3.Error):
                self.respond(500,{"error":"Could not load the workspace"})

        def do_POST(self):
            try:
                with profiles.request_context() if profiles else nullcontext():return self._post()
            except ValueError as error:return self.respond(409,{'error':str(error)})

        def _post(self):
            workspace=profiles.workspace if profiles else initial_workspace
            session_token=profiles.session_token if profiles else initial_token
            route = urlsplit(self.path).path
            actions = {"stage", "map", "preview", "promote", "replay"}
            action = route.removeprefix("/api/exchange/")
            research_actions = {"country","save-countries","submit","export","demo-response","preview-response","receive","feedback"}
            research_action = route.removeprefix("/api/research/")
            research_operation = research_action in research_actions and route == "/api/research/"+research_action
            personal_decision = route == "/api/country-decisions"
            local_action = route.removeprefix("/api/local/")
            local_operation = getattr(workspace,"operational",False) and local_action in ('refresh','backup','remove-university','restore-university','copy-instructions') and route=='/api/local/'+local_action
            profile_operation=profiles is not None and route in ('/api/local/profiles/create','/api/local/profiles/switch','/api/local/reset')
            preferences = route == "/api/display-preferences"
            layout = route == '/api/panel-widths'
            report_operation = getattr(workspace,'operational',False) and route in ('/api/reports/annotate','/api/reports/draft','/api/reports/reading')
            if not (report_operation or layout or preferences or personal_decision or research_operation or local_operation or profile_operation) and (not exchange or action not in actions or route != "/api/exchange/" + action):
                return self.respond(405,{"error":"This endpoint is read-only"})
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (self.headers.get("Host") != origin.removeprefix("http://")
                or self.headers.get("Origin", origin) != origin
                or (profiles is not None and self.headers.get('X-Grad-Compass-Workspace')!=session_token)
                or not session_token
                or not secrets.compare_digest(self.headers.get("X-Grad-Compass-Session", ""), session_token or "")):
                return self.respond(403, {"error": "Use this app session to save workspace changes"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= (8_000_000 if getattr(workspace,"operational",False) and research_operation else 196608 if research_operation else 16384) or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("A small JSON request is required")
                from web.research_envelopes import loads
                payload = loads(self.rfile.read(length))
                if report_operation:
                    if route.endswith('/reading'):
                        from web.report_reading import preferences as reading_preferences
                        return self.respond(200,reading_preferences(workspace,payload))
                    from web import report_packages as packages
                    return self.respond(200,packages.save_annotation(workspace,payload) if route.endswith('/annotate') else packages.prepare_draft(workspace,payload))
                if layout:
                    from web.panels import preferences as panel_widths
                    return self.respond(200,panel_widths(workspace,payload))
                if profile_operation:
                    if not isinstance(payload,dict):raise ValueError('Review the local profile action')
                    fields={'/api/local/profiles/create':{'name'},'/api/local/profiles/switch':{'profile_id'},'/api/local/reset':{'profile_id','token','confirmation'}}[route]
                    if set(payload)!=fields:raise ValueError('Review the local profile action')
                    if route.endswith('/create'):result=profiles.create(payload['name'])
                    elif route.endswith('/switch'):result=profiles.switch(payload['profile_id'])
                    else:result=profiles.reset(**payload)
                    return self.respond(200,result)
                if local_operation:
                    if local_action=='copy-instructions':
                        if not isinstance(payload,dict) or not {'request_id'}<=set(payload)<= {'request_id','feedback_id'}:raise ValueError('Choose the saved request instructions')
                        if clipboard is None:raise ValueError('Select and copy the displayed instructions in this window')
                        exported=workspace.research.export(**payload)
                        clipboard.copy_text(exported['prompt'])
                        return self.respond(200,{'copied':True})
                    if local_action in ('remove-university','restore-university'):
                        if not isinstance(payload,dict) or set(payload)!={'id'}:raise ValueError('Choose a university in this profile')
                        method=workspace.remove_university if local_action=='remove-university' else workspace.restore_university
                        return self.respond(200,method(payload['id']))
                    if payload != {}:raise ValueError("Use the local workspace action without extra fields")
                    if local_action == "backup":return self.respond(200,workspace.backup())
                    from web.inbox import receiver_for
                    return self.respond(200,receiver_for(workspace).check())
                if research_operation:
                    if not isinstance(payload,dict): raise ValueError("Review the research form fields")
                    if research_action == "country": result = workspace.research.save_country(payload)
                    elif research_action == "save-countries": result = workspace.research.save_countries(payload)
                    elif research_action == "submit": result = workspace.research.submit(payload)
                    else:
                        allowed = {"export":{"request_id","feedback_id"},"demo-response":{"request_id","choice"},
                                   "preview-response":{"transport_json"},"receive":{"envelope"},"feedback":{"request_id","request_revision","request_digest","result_id","result_digest","revision","finding_id","finding_revision","comment","submission_key"}}[research_action]
                        required = allowed - ({"feedback_id"} if research_action=="export" else set())
                        if set(payload)-allowed or not required <= set(payload): raise ValueError("Review the selected research item")
                        method = {"export":"export","demo-response":"demo_response","preview-response":"preview_response","receive":"receive","feedback":"feedback"}[research_action]
                        result = getattr(workspace.research,method)(**payload) if research_action!="receive" else workspace.research.receive(payload["envelope"])
                    return self.respond(200,result)
                if personal_decision:
                    if not isinstance(payload, dict) or set(payload) != {"country_code", "decision"} or not isinstance(payload["country_code"], str) or not isinstance(payload["decision"], str):
                        raise ValueError("Choose a displayed country and personal decision")
                    return self.respond(200, {"country_decisions": workspace.country_decisions(payload["country_code"], payload["decision"])})
                if preferences:
                    if not isinstance(payload, dict) or set(payload) != {"text_size"} or not isinstance(payload["text_size"], str):
                        raise ValueError("Choose an available text size")
                    return self.respond(200, workspace.display_preferences(payload["text_size"]))
                allowed = {"batch_id"} | {"map": {"external_id", "local_id", "create"},
                    "promote": {"preview_id", "approved"}}.get(action, set())
                if not isinstance(payload, dict) or set(payload) - allowed or not isinstance(payload.get("batch_id"), str):
                    raise ValueError("Invalid synthetic exchange request")
                if action == "map":
                    if not isinstance(payload.get("external_id"), str) or type(payload.get("create", False)) is not bool:
                        raise ValueError("Select an explicit institution mapping")
                    if payload.get("local_id") is not None and type(payload["local_id"]) is not int:
                        raise ValueError("Select a local institution ID")
                if action == "promote" and not isinstance(payload.get("preview_id"), str):
                    raise ValueError("Review a dry run before approval")
                return self.respond(200, getattr(exchange, action)(**payload))
            except (TypeError, json.JSONDecodeError):
                return self.respond(400, {"error": "Invalid app request"})
            except ValueError as error:
                return self.respond(409, {"error": str(error)})
            except (OSError, sqlite3.Error):
                return self.respond(500, {"error": "Could not complete the workspace operation"})

        def do_PUT(self):
            self.respond(405, {"error": "Use the explicit exchange workflow actions"})

        do_PATCH = do_DELETE = do_PUT

    initial_token=session_token
    return Handler


def create_server(directory, port=8765, exchange_directory=None):
    workspace = DemoWorkspace(directory)
    exchange = None
    if exchange_directory is not None:
        from web.exchange_workflow import SyntheticExchangeWorkflow
        exchange = SyntheticExchangeWorkflow(exchange_directory)
    return ThreadingHTTPServer(("127.0.0.1",port),handler_for(workspace, exchange, secrets.token_urlsafe(24)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir",type=Path,required=True)
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--exchange-dir", type=Path, help="explicit disposable synthetic exchange workspace")
    args = parser.parse_args()
    try:
        server = create_server(args.data_dir,args.port, args.exchange_dir)
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
