# Operational local workflow — 2026-10-16

The user's local operational authorization supersedes the earlier preview-only scope. The normal desktop entry opens persistent owner-private local storage. Production SQLite/configuration/cache, public exchange 1.0.0, shared importer files and applicant profile/CV artifacts remain unchanged.

## Delivered behavior

- Existing map workspace, floating panels, independent Countries/Universities and Map/List controls, saved-country multi-selection, keyboard/history navigation and four text sizes remain in place.
- Preserved existing saved memberships, notes, decisions, preferences and display settings without modifying the old preview. Invented requests/results remain accessible through a separate read-only Sample history panel; invented institution/country evidence never supplies real discovery.
- Real requests require explicit country/scope/count bounds. Preferences are remembered on successful submission, with editable summaries and request-only exceptions. Exact request/preference snapshots and parent/result/finding references remain immutable.
- Manual handoffs identify private files and exact-byte SHA-256 references. The user manually invokes Dave. The app reads returned inbox files only on startup or explicit Refresh results; file preview/explicit receipt is also available. It never invokes agents.
- All received country field findings are displayed, with sources, locators, UTC observations, caveats and actual review/human-approval states. Universities/programs retain distinct stable identities. Actual receipt is separate from factual acceptance or legacy database promotion.
- App-owned locations retain campus identity, primary source, locator, observation time, method and uncertainty. Unresolved universities remain visible without pins. Verified campus/building points are used for markers; map camera centers and country centroids are excluded.
- Operational data has no automatic expiry or renewal gate. Owner-private snapshots and verified restore into a new workspace preserve history and personal state.

## Actual end-to-end evidence

The user confirmed manually invoking Dave for the first saved, bounded request. Marry returned an accepted acknowledgement followed by a request-bound complete result from the already-reviewed six-country/five-university/five-program evidence. App receipt, rather than producer preview alone, succeeded.

The app displays **28 country field findings, five universities and five programs**. Pending exchange review, unknown human approval and source caveats remain intact. Five campus points were separately verified from primary university/government location evidence. Coordinate observations do not accept other factual claims or applicant suitability.

Replaying the exact acknowledgement and result reports **zero changes and zero errors**, with stable university/program IDs. The normal UI demonstrates country findings, nested programs, source evidence, remembered preferences/bounds and separate sample history. Reopening retains saved state.

An actual local backup was restored into a **new** private workspace. Request/results, exact export digests, saved countries/notes/preferences, personal decisions, text settings and five university/program/location projections compared equal. The original runtime remained in place. A private recovery receipt records the snapshot and restored workspace; neither payloads nor private screenshots are committed.

The first request's inherited reference-sidecar bug was corrected: real exports now use `synthetic:false`. Original incorrect references/manifests were retained in a private correction audit; the request bytes, ID, revision and digest were unchanged. Restored re-export verifies the same digest.

## Validation

- 75 application Python tests, including 12 focused operational groups: exact bytes/scope/parser rejection, real references, permanent persistence, acknowledgement/result/feedback/refresh, exact revision bindings, public association/count limits, candidate scope, retained batch bytes, location provenance, old-preview preservation, session guards, backups and corruption/link/path rejection.
- 22 unchanged exchange tests; existing GRA-55 reproducible fixture remains exact.
- Both JavaScript regression files and JavaScript syntax checks.
- Three Qt shortcut/input tests.
- Native actual-data review: five verified markers, 38 returned findings, university/program evidence, remembered preferences/bounds, separate sample archive, Map/List, reload, and 12 combinations of 1440/820/390 width and four text sizes. No personal state or requests were changed by this review.
- The original disposable map-selection regression checks keyboard polygons, camera/filter/detail preservation, pan/zoom, repeat save, retained notes/decisions, accessible list alternative and history/layout behavior. Its focus probe now waits for actual window-manager activation before checking the keyboard outline.

## Review on this machine

Open **Grad Compass** from Pop!_OS, or run from the monorepo root:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py
```

1. In Countries, choose Saved countries, then inspect a country with returned research. Inspect its field findings, source links, caveats and personal decision separately.
2. Use Explore universities here. Inspect university details, verified campus-location provenance and the program nested inside its institution. Switch Map/List and navigate Back/Forward.
3. Open Requests and inspect the first real request, accepted acknowledgement and complete returned result. Give feedback or Request an update only when intended; submission prepares a bounded local handoff and does not invoke Dave.
4. Settings provides text size, local backup and separate read-only sample history. See the [application guide](../../grad-compass/README.md) for restore-to-new-workspace commands.

Owner-private screenshots and a detailed local demonstration are under the operational runtime's `reviews/` directory. The read-only reproduction script is `grad-compass/scripts/check_local_ui.py`. No automatic execution, public hosting, outreach, faculty research or profile/CV transfer is included.
