"""Open the persistent local map workspace; --preview opens separate sample data."""
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import tempfile
import time

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
PREVIEW_DIR = REPO_ROOT / "grad-compass-workspace" / "runtime" / "preview"
LOCAL_DIR = REPO_ROOT / "grad-compass-workspace" / "runtime" / "local"
EXCHANGE_DIR = REPO_ROOT / "grad-compass-workspace" / "runtime" / "exchange-ui"
sys.path.insert(0, str(APP_ROOT))


def prepare_workspace(preview_directory=PREVIEW_DIR):
    from core.paths import validate_data_directory
    from web.server import DemoWorkspace

    directory = validate_data_directory(preview_directory)
    if preview_directory.is_symlink():
        raise ValueError("Preview storage must not be a symbolic link")
    if not directory.exists() or (directory.is_dir() and not any(directory.iterdir())):
        subprocess.run(
            [sys.executable, "-B", str(APP_ROOT / "scripts" / "create_demo.py"), str(directory)],
            check=True,
        )
    # Refuse an existing unmarked database; never repurpose original user data.
    DemoWorkspace(directory)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="open the separate synthetic sample workspace")
    parser.add_argument("--local-dir",type=Path,default=LOCAL_DIR,help="persistent private local workspace")
    parser.add_argument("--smoke-test", action="store_true", help="verify rendering and close automatically")
    parser.add_argument("--selection-smoke-test", action="store_true", help="verify map country multi-selection in disposable storage")
    parser.add_argument("--research-smoke-test", action="store_true", help="demonstrate a synthetic manual research round trip")
    parser.add_argument("--country-smoke-test", action="store_true", help="demonstrate country exploration in disposable storage")
    parser.add_argument("--readability-smoke-test", action="store_true", help="check text sizes in a new disposable workspace")
    parser.add_argument("--exchange-dir", type=Path, default=EXCHANGE_DIR, help="disposable synthetic exchange workspace")
    parser.add_argument("--exchange-smoke-test", action="store_true", help="demonstrate the exchange UI in a new disposable database, then close")
    parser.add_argument("--review-screenshots", type=Path, help="optional synthetic review screenshot directory")
    args = parser.parse_args()
    if args.review_screenshots and not (args.exchange_smoke_test or args.readability_smoke_test or args.country_smoke_test or args.research_smoke_test or args.selection_smoke_test):
        parser.error("--review-screenshots requires an exchange or readability smoke test")
    temporary_preview = tempfile.TemporaryDirectory(prefix="grad-compass-readability-") if (args.smoke_test or args.exchange_smoke_test or args.readability_smoke_test or args.country_smoke_test or args.research_smoke_test or args.selection_smoke_test) else None
    if temporary_preview:
        args.smoke_test = True
    temporary_exchange = tempfile.TemporaryDirectory(prefix="grad-compass-exchange-ui-check-") if (args.smoke_test or args.exchange_smoke_test or args.readability_smoke_test or args.country_smoke_test or args.research_smoke_test or args.selection_smoke_test) else None
    if temporary_exchange:
        args.smoke_test = True
    local_mode=not args.smoke_test and not args.preview
    if local_mode:
        from web.local import LocalWorkspace
        workspace=LocalWorkspace(args.local_dir,PREVIEW_DIR)
        directory=workspace.directory
    else:
        directory = prepare_workspace(Path(temporary_preview.name) / "preview" if temporary_preview else PREVIEW_DIR)
    logging.basicConfig(filename=directory / "launcher.log", level=logging.WARNING)
    os.environ["QT_API"] = "pyqt6"
    import webview
    from web.server import create_server

    if local_mode:
        from web.local import create_local_server
        server=create_local_server(workspace,port=0)
    else:
        server = create_server(directory, port=0, exchange_directory=Path(temporary_exchange.name) if temporary_exchange else args.exchange_dir)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    result = {"passed": False}
    try:
        window = webview.create_window(
            "Grad Compass" if local_mode else "Grad Compass — Sample workspace",
            f"http://127.0.0.1:{server.server_port}/",
            width=1440,
            height=960,
            min_size=(390, 640),
            background_color="#f6f8fa",
            confirm_close=not args.smoke_test,
            localization={"global.quitConfirmation": "Close Grad Compass?"},
        )
        from desktop_controls import DesktopControls
        controls = DesktopControls(window)
        capture = None
        if args.review_screenshots:
            from core.paths import validate_data_directory
            from preview_capture import PreviewCapture
            capture = PreviewCapture(window, validate_data_directory(args.review_screenshots), prefix="2026-10-15-selection-" if args.selection_smoke_test else "2026-10-15-research-" if args.research_smoke_test else "2026-10-13-exchange-")

        def started():
            controls.install_requested.emit()
            if not controls.installed.wait(10):
                logging.error("Desktop shortcut setup did not complete")
            if args.smoke_test:
                smoke_test()

        def smoke_test():
            try:
                if not window.events.loaded.wait(20):
                    raise RuntimeError("Desktop page did not load")
                stop_at = time.monotonic() + 20
                while time.monotonic() < stop_at:
                    # run_js executes this fixed Qt smoke probe without CSP-blocked eval.
                    rendered = json.loads(window.run_js("""JSON.stringify({
                        cards: document.querySelectorAll('.university-card').length,
                        pins: document.querySelectorAll('.leaflet-overlay-pane path[fill="#087ba4"]').length,
                        map: !!document.querySelector('.leaflet-container'),
                        antarctica: !!document.querySelector('[data-country="ANTARCTICA"],[data-country="ATA"]'),
                        width: document.getElementById('map').getBoundingClientRect().width,
                        height: document.getElementById('map').getBoundingClientRect().height,
                        viewportWidth: innerWidth,
                        viewportHeight: innerHeight,
                        error: !document.getElementById('error').hidden
                    })"""))
                    if rendered and rendered["cards"] == 3 and rendered["pins"] == 2 and rendered["map"] and not rendered["error"]:
                        if rendered["antarctica"]:
                            raise RuntimeError("Antarctica must not be rendered in the discovery map")
                        if rendered["width"] != rendered["viewportWidth"] or rendered["height"] != rendered["viewportHeight"]:
                            raise RuntimeError("Map does not fill the workspace viewport")
                        break
                    time.sleep(0.2)
                else:
                    raise RuntimeError("Desktop workspace did not render its synthetic results")
                # Window-manager focus can arrive after page load. Check the real focused style.
                window.restore()
                focus_deadline=time.monotonic()+5
                while time.monotonic()<focus_deadline:
                    focus=json.loads(window.run_js("""
                        document.getElementById('search').focus();
                        JSON.stringify({active:document.hasFocus(),outline:getComputedStyle(document.getElementById('search')).outlineWidth})
                    """))
                    if focus['active'] and focus['outline']=='3px':break
                    time.sleep(.1)
                else:
                    raise RuntimeError("Keyboard focus styling did not render")
                window.run_js("""
                    document.getElementById('country').value = 'FRA';
                    document.getElementById('country').dispatchEvent(new Event('change'));
                    document.querySelector('[data-country="FRA"]').focus();
                """)
                country = json.loads(window.run_js("""JSON.stringify({
                    selected: document.querySelector('[data-country="FRA"]').getAttribute('aria-pressed'),
                    fill: document.querySelector('[data-country="FRA"]').getAttribute('fill'),
                    outline: getComputedStyle(document.querySelector('[data-country="FRA"]')).outlineStyle,
                    results: document.querySelectorAll('.university-card').length
                })"""))
                if country != {"selected": "true", "fill": "#85c2d4", "outline": "none", "results": 0}:
                    raise RuntimeError("Selected country did not highlight along its shape")
                window.run_js("document.getElementById('country').value = ''; document.getElementById('country').dispatchEvent(new Event('change'));")
                window.run_js("document.getElementById('list-view').click(); document.querySelector('.university-card').click();")
                stop_at = time.monotonic() + 20
                while time.monotonic() < stop_at:
                    detail = json.loads(window.run_js("""JSON.stringify({
                        list: document.getElementById('list-view').getAttribute('aria-pressed'),
                        title: document.querySelector('#inspector h2')?.textContent,
                        contacts: document.querySelectorAll('#inspector .detail-card').length,
                        tasks: document.querySelectorAll('#inspector .task-line').length
                    })"""))
                    if detail["list"] == "true" and detail.get("title") == "Northbridge Example University" and detail["contacts"] == 1 and detail["tasks"] == 2:
                        from preview_checks import verify_navigation
                        verify_navigation(window)
                        if args.exchange_smoke_test:
                            from exchange_checks import verify_exchange
                            verify_exchange(window, capture.save if capture else None)
                        if args.readability_smoke_test:
                            from readability_checks import verify_readability
                            verify_readability(window, directory, capture.save if capture else None)
                        if args.country_smoke_test:
                            from country_checks import verify_countries
                            verify_countries(window, capture.save if capture else None)
                        if args.selection_smoke_test:
                            from selection_checks import verify_country_selection
                            verify_country_selection(window, capture.save if capture else None)
                        if args.research_smoke_test:
                            from research_checks import verify_research
                            verify_research(window, capture.save if capture else None)
                        result["passed"] = True
                        print("Desktop smoke test passed: map pins, focus styling, list toggle and university details.", flush=True)
                        return
                    time.sleep(0.2)
                raise RuntimeError("List or university inspector did not render")
            except Exception as error:
                logging.exception("Desktop smoke test failed")
                print(f"Desktop smoke check failed: {error}", file=sys.stderr, flush=True)
            finally:
                window.destroy()

        webview.start(
            func=started,
            gui="qt",
            private_mode=True,
            storage_path=str(directory / "browser"),
            icon=str(APP_ROOT / "ui" / "assets" / "grad-compass.svg"),
        )
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
        if local_mode:workspace.backup()
        if temporary_exchange:
            temporary_exchange.cleanup()
        if temporary_preview:
            temporary_preview.cleanup()
    if args.smoke_test and not result["passed"]:
        raise SystemExit("Desktop smoke test failed; see the synthetic runtime's launcher.log")


if __name__ == "__main__":
    main()
