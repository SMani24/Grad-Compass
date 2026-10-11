"""Open the map workspace in a desktop window using synthetic data only."""
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
PREVIEW_DIR = REPO_ROOT / "grad-compass-workspace" / "runtime" / "preview"
sys.path.insert(0, str(APP_ROOT))


def prepare_workspace():
    from core.paths import validate_data_directory
    from web.server import DemoWorkspace

    directory = validate_data_directory(PREVIEW_DIR)
    if PREVIEW_DIR.is_symlink():
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
    parser.add_argument("--smoke-test", action="store_true", help="verify rendering and close automatically")
    args = parser.parse_args()
    directory = prepare_workspace()
    logging.basicConfig(filename=directory / "launcher.log", level=logging.WARNING)
    os.environ["QT_API"] = "pyqt6"
    import webview
    from web.server import create_server

    server = create_server(directory, port=0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    result = {"passed": False}
    try:
        window = webview.create_window(
            "Grad Compass — Map preview",
            f"http://127.0.0.1:{server.server_port}/",
            width=1440,
            height=960,
            min_size=(390, 640),
            background_color="#f6f8fa",
        )

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
                        error: !document.getElementById('error').hidden
                    })"""))
                    if rendered and rendered["cards"] == 3 and rendered["pins"] == 2 and rendered["map"] and not rendered["error"]:
                        break
                    time.sleep(0.2)
                else:
                    raise RuntimeError("Desktop workspace did not render its synthetic results")
                focus = json.loads(window.run_js("""
                    document.getElementById('search').focus();
                    JSON.stringify({outline: getComputedStyle(document.getElementById('search')).outlineWidth})
                """))
                if focus["outline"] != "3px":
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
                        result["passed"] = True
                        print("Desktop smoke test passed: map pins, focus styling, list toggle and university details.", flush=True)
                        return
                    time.sleep(0.2)
                raise RuntimeError("List or university inspector did not render")
            except Exception:
                logging.exception("Desktop smoke test failed")
            finally:
                window.destroy()

        webview.start(
            func=smoke_test if args.smoke_test else None,
            gui="qt",
            private_mode=True,
            storage_path=str(directory / "browser"),
            icon=str(APP_ROOT / "ui" / "assets" / "grad-compass.svg"),
        )
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    if args.smoke_test and not result["passed"]:
        raise SystemExit("Desktop smoke test failed; see the synthetic runtime's launcher.log")


if __name__ == "__main__":
    main()
