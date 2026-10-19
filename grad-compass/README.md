# Grad Compass

A personal local application built around a Leaflet map, floating exploration/details panels, and separate **Countries / Universities** and **Map / List** controls. Python/pywebview, SQLite and plain HTML/CSS/JavaScript remain the stack. Product notes and manual Paperclip coordination live in [`../grad-compass-workspace/`](../grad-compass-workspace/README.md).

## Normal launch on Pop!_OS

Press **Super**, search for **Grad Compass**, and open it. The installed desktop entry already runs this launcher without flags, which now opens the persistent private local workspace. Close any older app window and reopen it after updating.

From the monorepo root:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py
```

Despite its retained filename, this command opens the normal local app. `--preview` explicitly opens the separate invented sample workspace. Smoke-test flags always use disposable sample storage.

The existing Personal profile uses Git-excluded `grad-compass-workspace/runtime/local/`. Additional profiles and the active-profile registry use the sibling `runtime/local-profiles/` directory. All data directories are owner-only, with marked local databases. The launcher reopens the last selected local profile. The legacy tracked database, configuration and image cache are not opened for application data. The loopback server uses a random port, session-protected mutations and validated Host/Origin headers; it stops when the window closes. Browser state and logs stay inside the private runtime. No public hosting or automatic agent execution is included.

The existing Python environment and Qt libraries have been verified. For a fresh checkout, create `grad-compass/envGradCompass/` and install `grad-compass/requirements.txt`. Desktop rendering needs a graphical session and the Linux Qt platform libraries. The HTTP layer uses Python's standard library; exchange validation uses jsonschema.

## Save and explore

Countries is the initial exploration mode in the normal app. A country polygon/card opens its details and frames the country. **Select countries** enables independent multi-selection without changing the filter, inspector or map framing. Purple dashed highlights distinguish selected countries from the blue active country. **Save selected**, **Clear**, **Done**, and a searchable keyboard-accessible country list remain available; panning and zooming work throughout.

**Saved countries**, **Save country**, and **Remove from saved** change membership only. Saving again preserves notes and decisions and never initiates research. Personal **Considering / Shortlisted / On hold / Excluded** decisions and private notes stay separate from factual review and application stages. Countries without universities remain selectable; empty results describe research coverage, not suitability.

**Explore universities here** retains country/map context while switching exploration. Universities appear in cards and List, with programs nested inside the parent institution. Stable external identities keep replay duplicate-free. Received records show their actual review state and source evidence; receiving a pending record does not mark it factually accepted or promote it into the legacy database.

Map markers require verified app-owned coordinates. Each location retains campus identity, source, locator, observation time, method and uncertainty. An unresolved university remains visible in cards/List without a fabricated pin. Country centroids and map camera centers are not campus locations. The first real run has five source-backed campus points; location observations do not approve university/program suitability.

Back/Forward, Alt+Left/Right and mouse side buttons restore workspace context. Escape closes details before clearing country context, and returns List to Map. Ctrl+W asks before closing the desktop window. **Settings → Text size** offers Standard, Comfortable, Large and Extra large; the choice persists locally. Panels scroll and controls wrap at narrow widths and larger sizes.

## Local profiles, university removal and reset

Close older app windows and reopen **Grad Compass** to load these controls.

- Open a university and choose **Remove university**. Confirmation explains that it and its programs will leave Map/List while original research stays in Requests. A backup is created first. The removal survives replay and relaunch; **Settings → Removed universities → Restore** brings the same stable identity and programs back.
- **Settings → Local profiles** creates an empty named profile and lets you switch explicitly. Current data is retained as **Personal**. Each profile has its own countries, notes, decisions, preferences, requests, results, feedback, removed universities, campus locations and text settings. The current profile is labelled in the exploration panel, including narrow windows. These are local workspaces; canonical Applicant Profiles are unchanged.
- **Settings → Reset app data → Reset this profile…** shows a current-data summary and requires typing **RESET**. Reset clears all active data in that profile, including saved selections, research/history and preferences. It preserves other profiles and saves a recovery backup first. Cancelling leaves data untouched. If data or incoming responses changed after the summary, review it again before confirming.
- Reset opens new empty storage atomically. Earlier files/backups remain recoverable; old inbox files and preview data are not silently imported again. This is a recoverable fresh start rather than secure erasure of disk/backups. **Settings → Recovery → Backups and reset recovery** shows the recovery locations. Restore into a new workspace with the command below.

Use a separate profile for exploratory manual testing. Automated checks use invented temporary workspaces and remove them afterward. No reset or university removal is executed against your own data during development. Prepared handoffs always name the active profile's request/inbox; return results to that exact profile. Switching/reset rotates the app session so a stale tab cannot submit into the new profile. If another app window changes the profile registry, close the older window and reopen.

## Manual research workflow

1. Save countries, choose **Select for research** on saved country cards, then **Research selected**. A request contains at most 20 countries, an explicit scope, institution/program count limits, contextual limits and preferences. It authorizes only its saved scope.
2. The first request collects intake/alternatives, degree routes, language, restrictions, funding priorities and shared research limits. Successful submissions remember explicit values. Later requests show an editable summary. **Only for this request** preserves the remembered values. Cancelling saves nothing; blank values remain unknown. Each request retains its original preference snapshot.
3. Submitting saves the immutable request immediately and opens **Requests & findings**. **Copy instructions for Dave** exports the exact request under the active profile's `research-handoff/` and copies its reference-only instructions. Invoke Dave manually with those instructions. Copying does not mark it acknowledged or start execution. If clipboard access is unavailable, the displayed text remains selectable.
4. Dave coordinates research, Alex's independent review and Marry's producer handoff. A returned transport contains `{body, sha256}`: the digest covers the exact UTF-8 body bytes. Acknowledgements/results bind the exact saved request revision/digest. Public associations bind unchanged exchange 1.0.0 batch and record revisions; private country evidence is separately versioned.
5. Dave/Marry deliver each acknowledgement, partial result and complete result to the exact profile inbox in the instructions. The app checks it on launch, when Requests opens and every five seconds while running, including when its browser is unfocused. Valid responses are recorded automatically and update progress/findings; **Results ready** opens the latest returned request from the map workspace. The display checks for new receipt state every three seconds and when focused. No response-file relay or upload is needed. A backup precedes new records; unchanged replay creates neither duplicate records nor repeated backups. Automatic receipt preserves actual review states and does not imply factual acceptance or authoritative promotion.
6. Invalid/conflicting finalized responses appear under **Incoming responses need attention** and the workspace's **Review delivery errors** action. Temporary/hidden writes are ignored; recently changing files wait to settle. Unsent feedback and note drafts are preserved when updates arrive. Requests with an open draft offer **Show latest results** rather than replacing that draft. Pending files and received history survive restart. **Refresh results** remains an optional immediate check; manual JSON selection/preview/receipt is under **Advanced / recovery: import response JSON**.
7. Inspect every country field finding, university/program, source locator/date, caveat and actual review state. Agent factual review, human approval, personal decisions and operational receipt remain distinct. Prior revisions remain available. Give finding-specific feedback and copy its instructions; **Request an update** creates an editable refresh request bound to its exact parent/result/finding revision. Submit and invoke Dave manually for subsequent execution.

Finalized delivery uses the existing `{body, sha256}` wire contract. Write and fsync a hidden temporary file inside the inbox, then publish it atomically under a unique non-hidden `.json` name; never modify a finalized file. Finalize referenced public batches under the same profile's `batches/` first. Marry owns the producer publisher and delivery compatibility; exchange 1.0.0 is unchanged. Only the inbox is polled, never the coordination mailbox or an agent executor.

The first manually invoked real request returned 28 country field findings, five universities and five programs for the bounded reviewed six-country dataset. Original pending exchange review, unknown human approval and caveats are preserved. Private result payloads and visual evidence remain outside Git; see the [local workflow review](../grad-compass-workspace/reviews/2026-10-16-local-workflow.md) for verification and local demonstration instructions.

There is no automatic 30-day stop, renewal requirement or cleanup of operational records. Saved countries, notes, preferences, requests, results and feedback persist. Existing personal state was copied non-destructively from the marked preview; previous invented requests remain available separately through **Settings → Sample history**. Samples never supply real-mode institution or country evidence. Canonical applicant profiles/CVs remain outside this integration.

## Backup and recovery

Backups are made on launch, before recording new incoming responses and on normal close. Unchanged polling/replay does not create more backups. **Settings → Save local backup** creates another snapshot. SQLite's backup API captures databases; hash inventories cover immutable handoffs, incoming packets, retained public batches, personal decisions, display preferences and the separate sample archive. Each profile has its own `backups/` directory and backups do not expire automatically. Settings shows its current backup directory; reset recovery points retain the earlier directory. Copy that private directory to owner-controlled backup media for protection against device loss; copies on the same disk cannot protect against disk failure.

Restore into a **new** directory; the restore tool checks member hashes, database integrity/scope, safe paths and handoff references, and refuses an existing destination:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/restore_local.py \
  grad-compass-workspace/runtime/local/backups/<snapshot> \
  grad-compass-workspace/runtime/local-restored

grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py \
  --local-dir grad-compass-workspace/runtime/local-restored
```

The original workspace remains in place. An explicit `--local-dir` uses a separate profile registry next to that directory and never copies the normal preview into it. Do not copy research or applicant payloads into tracked source files. This workflow does not transfer profile/CV artifacts, send outreach, investigate faculty or automatically call agents.

## Sample workspace and regression review

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py --preview
```

The separate marked `runtime/preview/` contains invented map data, evidence and app-generated synthetic responses. **Research imports** uses another disposable exchange database and the unchanged synthetic importer. Its stages remain explicit: select finalized batch, validate/stage, map institutions, inspect dry run, approve eligible promotion, inspect outcomes and replay. Institutions/programs stay distinct; only promoted records enter synthetic discovery, while held records remain staged.

The reproducible corrected private handoff fixture is [`tests/fixtures/gra55/`](tests/fixtures/gra55/). Marry independently passed app commit `fac818c`; it superseded the earlier `9bfe9c6` demonstration. Legacy sample envelopes remain read-only rather than being rewritten as corrected artifacts. The real adapter is app-owned; shared exchange schemas/importer files require coordination with Marry before editing.

Review notes: [country selection](../grad-compass-workspace/reviews/2026-10-15-country-selection.md), [synthetic research](../grad-compass-workspace/reviews/2026-10-15-watchlist-research.md), [GRA-55 corrections](../grad-compass-workspace/reviews/2026-10-16-gra55-corrections.md).

## Checks

From the monorepo root:

```bash
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass/tests -v
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass-exchange/tests -v
node --test grad-compass/tests/web_discovery.test.cjs grad-compass/tests/country_drawer.test.cjs
QT_QPA_PLATFORM=offscreen grad-compass/envGradCompass/bin/python -B grad-compass/tests/check_desktop_controls.py -v
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py --selection-smoke-test
git diff --check
```

These checks use invented temporary storage. No npm install is needed. The read-only real demonstration below requires the already-received first result; it checks all five verified markers, country findings, programs, remembered preferences/bounds, separate sample archive, reopen persistence and 12 window/text-size layouts without submitting research or changing personal state:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/check_local_ui.py
```

Its screenshots stay in the private runtime. Additional sample demonstrations use `--research-smoke-test`, `--country-smoke-test`, `--exchange-smoke-test`, or `--readability-smoke-test`; optional `--review-screenshots grad-compass-workspace/reviews` saves Git-excluded sample images.

The legacy `app.py` shell remains available only for explicit isolated development with `GRAD_COMPASS_DATA_DIR` and `GRAD_COMPASS_OFFLINE=1`. The normal launcher above is the supported local workflow and never falls back to legacy data.

To review removal, restore, profile isolation, typed reset, cancellation, recovery and all 12 supported settings/map-selection layouts without touching personal data:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/check_profile_ui.py
```

This uses only invented temporary records and cleans up its storage. Optional screenshots may be saved with `--screenshots grad-compass-workspace/runtime/profile-ui-review`.

To verify automatic receipt, copy instructions, partial/final updates, draft protection, visible invalid-file errors and reopen persistence using invented temporary records:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/check_inbox_ui.py \
  --screenshots grad-compass-workspace/runtime/inbox-ui-review
```
