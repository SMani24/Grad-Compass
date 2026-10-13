# Grad-Compass application

The existing desktop shell uses Python/pywebview, SQLite, Leaflet, and plain HTML/CSS/JS. Development is moving incrementally toward a map-first web service. Product decisions, plans, Paperclip coordination, and review notes live in [`../grad-compass-workspace/`](../grad-compass-workspace/README.md).

## Launch the map preview on Pop!_OS

Press **Super**, search for **Grad Compass**, and open it. The installed desktop entry opens the new map workspace in a Qt window without a terminal. It currently displays three invented universities so the layout can be reviewed before importing personal research results.

Escape moves up from university details to the country/filter view, then to the world view (and from the list to the map). Back/forward buttons, Alt+Left/Right and mouse side buttons restore the full workspace context. Ctrl+W closes the desktop app after a confirmation; cancellation keeps the window open.

The launcher uses `../grad-compass-workspace/runtime/preview/`, creates synthetic data only if that folder is new or empty, and refuses existing unmarked data. Its local server binds to a random loopback port and stops when the window closes. Browser storage and launch logs stay in that ignored runtime. The original application database and configuration are not used.

From a terminal, the same launcher is:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py
```

This checkout's Python, geopy, pywebview, QtPy, PyQt6, Qt WebEngine, jsonschema and Linux Qt platform libraries have been verified. For a fresh checkout, create `grad-compass/envGradCompass/` and install `grad-compass/requirements.txt` there. Desktop rendering requires a graphical session and the Qt platform's Linux libraries; the HTTP layer uses Python's standard library and the shared exchange validator uses jsonschema.

## Synthetic research imports

Open **Research imports** in the desktop workspace. The launcher explicitly configures the separate, disposable `../grad-compass-workspace/runtime/exchange-ui/exchange.sqlite` database and synthetic outbox. New/empty storage is initialized with its own scope markers; existing unmarked storage is refused. The map's preview database remains read-only and separate.

1. Select the finalized invented v1.0.0 batch and click **Validate & stage**. Inspect the separate institution/program tables, producer review states, evidence references and staging status.
2. For **Example North University**, explicitly choose **Create a new institution** or link **Existing Demo University**, then save the mapping. Pending reviews may stay unmapped; they will remain in staging.
3. Click **Review dry run**. Inspect before/after values, program-parent linkage, eligible intake claims and held records. The app runs the unchanged importer on a temporary database copy; this preview does not create rows in the source workspace.
4. Check the operational approval box and click **Approve & promote eligible records**. This approves an import operation, not producer facts. Mapping changes or changes in eligibility require a new preview.
5. Inspect outcomes, then click **Replay the same batch**. With the create-new choice, one institution and one program record are promoted; three records remain staged. The workspace totals are two local institutions (including the original seed) and one program. Replay reports zero new changes and no duplicates.

Only the reviewed bundled synthetic fixture is selectable in this increment. A schema-valid real batch is not sufficient input. Unknown/stale/expired requirement claims remain staged according to the unchanged importer; the default freshness window is 30 days. Map geocoding, applicant artifacts and the proposed private queue are outside this workflow.

To try the alternative mapping from a fresh disposable workspace, use `launch_preview.py --exchange-dir /tmp/grad-compass-exchange-alternative`. The app never deletes or resets an existing workspace automatically. Browser state/logs and exchange runtime files remain ignored.

An unattended UI demonstration uses a new temporary database, operates the visible controls, verifies replay and cleans up that owned temporary workspace:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py --exchange-smoke-test --review-screenshots grad-compass-workspace/reviews
```

The desktop entry generator emits checkout-specific paths without installing anything:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/prepare_desktop_entry.py /tmp/grad-compass.desktop
desktop-file-validate /tmp/grad-compass.desktop
```

On this machine, it is installed at `~/.local/share/applications/grad-compass.desktop`. A copy of the previous entry is retained in the ignored workspace runtime. Regenerate and reinstall the entry if the repository moves.

## Browser review

To review the same synthetic workspace in a regular browser:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/web/server.py --data-dir grad-compass-workspace/runtime/preview --exchange-dir grad-compass-workspace/runtime/exchange-ui --port 8765
```

Open `http://127.0.0.1:8765/`; stop the server with Ctrl+C. Search, country and stage filters work across both views. Select a university to inspect its metadata, saved contacts and linked tasks. Universities without coordinates remain visible in the results and list. The map is read-only; Research imports writes only its separately configured synthetic database. Real-data import, personal-data editing, authentication and deployment remain later increments.

## Isolated development

Run these commands from the monorepo root. The retained `envGradCompass` installation is local and ignored by Git.

Always set `GRAD_COMPASS_DATA_DIR` for development. It redirects the database, config, vault, and image cache to the specified runtime directory. Locations overlapping original data/cache, Research Engine, or exchange storage are rejected. Symlink and hard-link substitutions for the development database are rejected before opening it.

Use `GRAD_COMPASS_OFFLINE=1` to disable geocoding/photo downloads and the background asset worker. Existing desktop defaults remain for compatibility; development commands below never launch against them.

## Checks

```bash
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass/tests -v
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass-exchange/tests -v
node grad-compass/tests/country_drawer.test.cjs
node grad-compass/tests/web_discovery.test.cjs
QT_QPA_PLATFORM=offscreen grad-compass/envGradCompass/bin/python -B grad-compass/tests/check_desktop_controls.py -v
git diff --check
```

Python tests create and clean up their own invented temporary runtimes. Node uses its built-in test library and a small DOM/API double; no npm install is needed. Run the Node test file directly to display each regression case in this environment.

The separate Qt check sends real key and mouse events to isolated widgets. `launch_preview.py --smoke-test` additionally checks browser history, cross-country context, Escape hierarchy and grouped search in the synthetic desktop window, then closes automatically.

On a graphical desktop, `grad-compass/envGradCompass/bin/python -B grad-compass/tests/check_close_confirmation.py` checks the actual close dialog: it automatically cancels Ctrl+W once, verifies that the local server remains available, then confirms closure. Both GUI checks use only the synthetic preview.

## Synthetic desktop review

Create a new demo folder; the helper refuses nonempty directories:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/create_demo.py /tmp/grad-compass-demo
GRAD_COMPASS_DATA_DIR=/tmp/grad-compass-demo GRAD_COMPASS_OFFLINE=1 grad-compass/envGradCompass/bin/python -B grad-compass/app.py
```

This previews the legacy interface with three invented universities, one contact, and linked tasks. Campus positions are illustrative; no real applicant data or remote services are used. The GUI requires a graphical desktop. The test suite uses isolated files; a separate `launch_preview.py --smoke-test` checks the new Qt window and closes it automatically.

Check selecting a university, switching countries, and applying a batch action: only the current country's selected records should be affected. Also check same-named attachments remain separate. Missing-coordinate results remain listed even without a map pin.

## Preservation

The original `data/grad_compass.db`, `data/config.json`, cached images, and Research Engine/exchange artifacts are unchanged and retain their existing tracking. No production migration or private artifact transfer is included in the foundation increment. Existing approved profile/CV display is a later consumer feature; the synthetic exchange importer stays synthetic-only.
