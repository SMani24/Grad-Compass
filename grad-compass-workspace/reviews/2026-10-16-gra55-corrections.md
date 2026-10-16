# GRA-55 synthetic handoff corrections · 2026-10-16

The corrected implementation supersedes the canonical-field-digest adapter reviewed at `9bfe9c6`, while preserving `5606825` map selection. It uses Marry's explicitly agreed APP-009 `{body, sha256}` transport. Codex owns these app corrections; no shared exchange/importer or producer files were edited. Independent compatibility acceptance remains Marry's decision on the final named commit.

## Corrected behavior

- Hash the exact UTF-8 envelope body before decoding, persist it unchanged, and export the same bytes with a separate digest reference. The body has no self-digest. Recomputed hashes cannot authorize changed or reserialized pinned fixture bytes.
- Reject duplicate keys at HTTP, external transport/reference, nested envelope and file-upload boundaries. The browser passes original upload text to strict server validation rather than parsing/re-emitting it. Preview records no acknowledgement or progress.
- Demonstrate request → accepted acknowledgement → partial result → complete result → feedback on the complete finding → refresh. The complete revision binds its exact predecessor revision/digest; old results and feedback stay immutable and replay cannot duplicate/downgrade them.
- Validate parent request ID/revision/digest, prior result ID/revision/digest and finding ID/revision against the actual saved artifacts, including country/request ownership and cross-request mismatches. Feedback validates all corresponding bindings. Unknown preferences remain explicit; comments do not become standing preferences.
- Supply stable country/record/finding revisions and references, source identity/revision/HTTPS locator, UTC observations, evidence coverage/unknowns and exact revision-bound review. Pending **agent factual review** is separate from **human approval not requested**, personal decisions and operational import.
- Associate public findings with the existing validated finalized synthetic batch manifest and exact institution/program record revisions/parent UUIDs. Exchange 1.0.0 is unchanged and operational mapping/promotion remains separate.
- Keep legacy marked app history readable with its original bytes and fingerprint semantics. Do not migrate/reinterpret it as the corrected contract; new-protocol export/response/refresh requires a new request. Saved memberships, notes and decisions require no migration.

A small responsive correction caps the narrow List filter panel and bases the table offset on its visible height. This keeps comparison rows reachable at 150% text after saved-country status messages appear; the map-selection toolbar and map camera behavior are preserved.

## Exact reproducible fixture

`grad-compass/tests/fixtures/gra55/manifest.json` has SHA-256:

```text
5dbb194c34e24550ee3c14fc8c0d73edf5c22da10dd4d0e25c0e969310d385d0
```

The manifest lists six envelope files and their exact hashes. `scripts/build_research_fixture.py` executes the store with fixed invented IDs/time in new temporary databases and compares every byte against the committed fixture. Its default invocation does not rewrite files. `tests/fixtures/gra55/README.md` documents wire fields, references, scope and reproduction. This is the existing app scenario corrected for the verified mismatches, not a new research-workflow feature.

## Test and visual evidence

Passed: **63 app Python tests**, including **10 focused contract groups**, **22 unchanged exchange tests**, both JavaScript regression files and three Qt input tests. The fixture reproduced exactly. All **146 protected tracked files** match HEAD.

The app regression suite includes focused contract rejection groups for altered bytes/serialization with original or recomputed hashes; duplicate keys in all parser boundaries; invalid UTF-8/non-finite JSON and malformed fields; stale/cross-request parent/result/finding bindings; feedback revision mismatch; missing/wrong country, source, review and observation metadata; wrong public record revisions/parent/manifest; unauthorized real scope; unsupported versions and terminal/invalid state transitions. Store/export byte equality, fixture reproduction, immutable history, retry/replay and legacy state preservation are also checked.

The native research UI proof passed explicit acknowledgement, exact-byte file preview, duplicate-key file rejection before receipt, partial/complete results, complete-result feedback/refresh, immutable old revision viewing, public import/replay, country review labels, preference safety and reload. Four text sizes at desktop and 390×640 passed. The separate native map-selection regression covers camera/filter/details/history, pan/zoom, keyboard, saved-state replay, the accessible country list and all four text sizes at 1440/820/390 widths. Local screenshot names retain the existing dated research/selection prefixes and remain ignored.

Reproduce from the repository root:

```sh
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/build_research_fixture.py
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass/tests -q
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass-exchange/tests -q
node --test grad-compass/tests/*.test.cjs
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py --research-smoke-test
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py --selection-smoke-test
```

The mailbox carries the final commit, manifest/hash references and concise verification results for Marry's independent review. The other team's concurrent workspace README addition is preserved and excluded from the app commit. Production database/configuration/cache, Research Engine and approved artifacts remain outside this task; real producer activation/intake is still unauthorized.
