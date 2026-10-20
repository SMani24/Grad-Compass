# Development progress

## 2026-10-09 — first increment

- Read-only audit and product interview completed; incremental development approved.
- Dedicated planning and local Paperclip mailbox prepared.
- Git cleanup completed in `c9e6f52` (`Tidy repo and plan app development`): generated app environment/bytecode files untracked, retained on disk; no source rollback.
- Foundation implemented: explicit runtime paths and offline mode; contained vault files with collision-free storage; foreign-key enforcement and transaction-managed connections; metadata-first deletion; versioned additive initialization; country selection pruning and stale-load handling.
- Synthetic demo creation and isolated desktop review commands documented in the application README.
- Verification: 18 Python regression cases and 6 JavaScript controller cases passed. Python syntax and whitespace checks passed. Fingerprints of 145 protected production/cache/research/exchange files match the pre-development snapshot.
- The GUI has not been launched against real data. Remaining audit findings (HTML rendering, history, enrichment, accessibility) stay on the backlog for subsequent interface work.
- Next visual checkpoint: map-first web workspace with list toggle and shared inspector.

No real-data transfer or deployment has occurred. The local mailbox is ready for the user to pass to Paperclip.

## 2026-10-09 — map workspace and desktop launch

- Added a plain HTML/CSS/JS browser workspace: dominant map, list toggle, common filters, university inspector, saved contacts and linked tasks. Missing-coordinate universities remain accessible.
- Added a standard-library HTTP preview with explicit static routes, read-only database access, a synthetic marker checked on every connection, and loopback-only binding. Research-data import and real-user service access remain future increments.
- Added a Qt desktop launcher for this preview. It creates only new/empty synthetic runtime storage, opens a private browser window and stops its server on close.
- Found that the existing Pop!_OS desktop entry used obsolete pre-monorepo paths. Installed a corrected entry with a compass icon; retained the previous file in the ignored runtime. The user can launch via Super → Grad Compass.
- Verified installed Python/Qt dependencies and included the Qt dependencies in the reproducible requirements file. No upgrades or system package changes were needed.
- Verification: 24 Python cases, 10 JavaScript cases, dependency consistency, native desktop rendering, HTTP smoke checks and Chrome map/list/mobile review passed. All 145 protected-file fingerprints remained unchanged.
- Screenshots, review instructions and limitations are organized under `reviews/`. The first layout review remains open for user feedback.

Paperclip requests remain in the local mailbox, with no replies at this checkpoint. The next research integration increment depends on reviewing their response and the agreed exchange ownership boundaries; no profile/CV artifacts have been relocated or regenerated.

## 2026-10-13 — verified coordination and synthetic exchange UI

- Read Dave's consolidated 2026-10-12 responses. Current notes now record the valid approved frozen profile, board-accepted applicant-specific v8 CV and absence of any approved/active additional enrichment task. Historical mailbox messages are preserved; APP-005 acknowledges the corrected status and bounded app scope.
- Independently compared the 16 shared exchange/importer paths with operator commit `043d9d7`: unchanged. Marry remains the compatibility contact. The app consumer reuses public importer operations and reviewed publisher without editing shared files or schemas.
- Added Research imports: registered finalized invented batch selection, structural validation/staging, separate institution/program tables, explicit mappings, a reviewed dry run, operational approval, eligible promotion and visible outcomes/replay.
- Added an isolated, marked `exchange-ui/exchange.sqlite` workspace. It is separate from both the map's preview DB and production. Only the pinned reviewed invented fixture is accepted. Promotion preview uses the actual importer in a temporary copy, avoiding duplicate eligibility logic.
- Verification: 31 app Python tests, the unchanged 22-test shared exchange suite, 13 JavaScript tests and three Qt input tests passed (69 total). Dependency consistency, syntax and whitespace checks passed. The native UI demonstrated the whole workflow, including replay with zero new changes. All 146 protected-file fingerprints match the pre-increment snapshot; the 16 delivered shared paths still match `043d9d7`. Visual review is recorded in `reviews/2026-10-13-synthetic-exchange.md`.

Private queue/manifests and artifact transfers remain proposals outside this implementation; no discovery, real-data import, production migration, profile enrichment or CV rebuild was performed.

## 2026-10-13 — readability feedback

- Completed both entries in `features_and_bugs.md`: exclude Antarctica at the map consumer and add persistent Settings text sizes (100–150%). Finished entries are removed; headings remain for further feedback.
- Kept app typography, details and research dialogs consistent; header/panel layouts adapt to larger text and mobile zoom controls remain reachable.
- Verification: 73 automated regression cases and native UI checks for four sizes, reload persistence, intermediate/minimum widths and the synthetic exchange workflow with duplicate-free replay. Review notes and local screenshots are under `reviews/2026-10-13-readability.md`.
- Display preferences are confined to ignored synthetic runtime storage. Production data/configuration, Research Engine, approved profile/CV artifacts and shared exchange/importer files remain unchanged.

## 2026-10-13 — map-based country exploration

- Connected committed eligible synthetic institutions/programs to discovery through a read-only projection. Distinct namespaced IDs preserve base IDs, producer identities/revisions and replay stability; unlocated results remain accessible without fabricated markers. Programs stay under explicitly mapped institutions.
- Added Countries / Universities to the left panel, independent of Map/List. Country cards/polygons frame the geography and open the existing right inspector. App-owned invented summaries/sources/uncertainties are labelled unreviewed; unsupported countries show missing research.
- Saved personal country decisions in separate ignored preview state. Considering/Shortlisted/On hold/Excluded do not change factual review, application stages or import eligibility; Excluded remains accessible.
- Added Explore universities here with preserved country/view/map position and explicit empty coverage. History, keyboard/Escape, text-size settings and narrow layouts are retained.
- Demonstrated each increment before expanding it. Final checks: 80 automated regressions plus native import/discovery/replay, country evidence/decision persistence, context handoff and four-size responsive demonstrations. See `reviews/2026-10-13-country-discovery.md`.
- APP-006 proposes a future country-evidence handoff to Marry/Dave, awaiting their response. Exchange 1.0.0/importer, producer ownership and manual mailbox boundaries remain unchanged. No real data, private transfers, production changes or automatic agents are included.

## 2026-10-15 — country watchlists and manual research round trip

- Added watch/unwatch and optional private notes to country details/cards/List, a watchlist filter and multi-country research selection within the map panel. Personal assessments remain separate and survive updates/unwatching.
- Added first-request inline preference collection, compact editable autofill, success-only remembering, request-only exceptions and immutable per-request snapshots. Request-specific scope/countries/limits/context stay independent; canonical profile/CV artifacts are untouched.
- Added local request/feedback handoff exports referencing private files/digests without repeating sensitive contents. Local preparation is separate from explicit acknowledgement; no agent progress is fabricated.
- Added provisional synthetic-only response receipt, request-linked country evidence, public institution/program origin links through unchanged importer safeguards, finding feedback, exact follow-up lineage and immutable result revisions/material changes.
- Demonstrated the full round trip, including cancelled forms, autofill, exception, acknowledgement/results, feedback, revision 2, old revision/feedback, public promotion/replay and personal state after reload. Four-size desktop/mobile request/result checks and existing country/university navigation checks passed.
- Verification: 90 regressions (50 app Python, 22 unchanged shared exchange, 15 JavaScript, three Qt input), native demonstrations and local visual captures. See `reviews/2026-10-15-watchlist-research.md`.
- APP-007 was published early in the ignored manual mailbox. Producer compatibility and real/private destination authorization remain pending; app-owned synthetic adapters are not a finalized producer integration. No real data, production changes, private artifact transfer, deployment, account/billing/faculty/outreach work or automatic execution is included.

## Saved countries and map multi-selection — 2026-10-15

- Added temporary polygon multi-selection with purple dashed highlights, count, Save selected/Clear/Done and a searchable accessible checkbox alternative. Location, open details, camera and history remain unchanged by selection/save; pan/zoom and ordinary navigation remain available.
- Standardized UI wording to Saved countries/Save country/Remove from saved. Existing `watched` memberships, notes and decisions remain intact without migration. Bulk save is atomic, replay-safe and does not submit research or modify the separate research selection.
- Verification: 53 app Python tests, JavaScript regressions, native selection plus country/history/layout checks at all four sizes and 1440/820/390 widths. Review: `reviews/2026-10-15-country-selection.md`; captures are local and ignored.
- Read latest APP-006/APP-007 replies; APP-008 supplies the unchanged `9bfe9c6` fixture, test/round-trip evidence and concrete proposed-format gaps. Correct status: **synthetic compatibility reviewed; gaps remain**. Canonical-field digest tests passing does not prove exact-file-byte digest or duplicate-key rejection. The existing synthetic demo was reused; no producer/shared schema work or real intake was activated.

## GRA-55 correction delivered — 2026-10-16

- Implemented Marry's APP-009 agreed exact-byte `{body, sha256}` transport, strict duplicate-key decoding at every input boundary, partial/complete results, exact parent/result/finding bindings, revision-bound agent review separate from human approval, UTC source observations and validated public record revision associations. Existing legacy envelopes stay readable and unchanged; new receipt/export uses the corrected format.
- Reproducible fixture: `grad-compass/tests/fixtures/gra55/manifest.json`, SHA-256 `5dbb194c34e24550ee3c14fc8c0d73edf5c22da10dd4d0e25c0e969310d385d0`. It supersedes the app-local fixture reviewed at `9bfe9c6`. The builder executes the complete store sequence in disposable storage and compares exact committed bytes.
- Passed 63 application Python tests (including 10 focused contract rejection/fixture groups), 22 unchanged exchange tests, both JavaScript regression files, three Qt input tests, native corrected research/file/import/replay checks and the preserved map-selection regression at all text sizes. All 146 protected tracked contents match HEAD.
- See `reviews/2026-10-16-gra55-corrections.md` and the final APP-009 delivery reference for the named commit/review request. Local verification is complete; Marry owns the independent compatibility verdict on that revision. No producer activation, real intake/import, production/configuration change or profile/CV work is included. The other team's concurrent mailbox README addition is left outside the app commit.

## Operational local workflow delivered — 2026-10-16

The user explicitly authorized persistent local producer/consumer handoff and the reviewed first real dataset, superseding preview-only restrictions. Dave was manually invoked by the user; the app actually received the bound acknowledgement and complete result and displays 28 country field findings, five universities and five programs. Actual pending review, unknown human approval and caveats remain intact. Five campus points have app-owned primary-source provenance and uncertainty. Replaying both packets makes no duplicate changes.

The normal desktop launcher now selects private persistent local storage, preserves prior personal state, and keeps invented history separate. There is no expiry/renewal gate or automatic invocation. Exact received batches are retained independently of the intake folder. Snapshot/recovery into a new workspace was verified against the real local data, with original request bytes and state equal. Scope-aware export sidecars fix the inherited synthetic flag without rewriting requests; original bad references were retained privately for audit.

Passed 75 app tests, 22 unchanged exchange tests, both JavaScript regressions/syntax checks, three Qt shortcut checks and the actual-data desktop review across 12 size layouts. See `reviews/2026-10-16-local-workflow.md` and the app README for launch, handoff and recovery. Private payloads/screenshots/receipts are excluded from Git. Shared importer/contracts and legacy data/configuration remain unchanged; Marry retains producer compatibility ownership. The other team's pending mailbox README addition remains outside the app commit.

## University removal, local profiles and reset — 2026-10-16

Added confirmed university removal with backup and Settings restoration; removal hides its programs and survives replay while retaining original research. Added independent empty local profiles, persistent explicit switching and a visible active-profile label. Added a Settings reset with current-data summary, typed RESET, stale-state rejection, backup-first failure handling and atomic transition to empty storage. Prior data/recovery snapshots remain recoverable, other profiles remain untouched, and old inbox/preview data cannot silently return. Profiles are workspace containers, not canonical Applicant Profiles.

Passed 83 app tests, 22 exchange tests, JavaScript regressions/syntax checks, three Qt input tests and a native invented-data removal/profile/reset/recovery demonstration across 12 settings/reset/map-selection layouts. Automated test storage is disposable and cleaned up. Personal data was not reset or removed during development; all 146 protected tracked files match the previous HEAD. Review: `reviews/2026-10-16-profiles-reset.md`. APP-011 informs Marry/Dave of per-profile handoff paths without any contract change. The unrelated pending mailbox README edit remains outside this app commit.

Final continuation verification on 2026-10-19 reran the 83/22 Python tests, JavaScript regressions/syntax checks, three Qt input checks and the native temporary-data demonstration successfully. All 12 settings/reset/map-selection layouts passed; cancellation, recovery, independent profiles and intact original Personal test state were verified. Review captures stay ignored. This increment is ready for normal-launch use without clearing personal data during development.

## Automatic operational response receipt — 2026-10-19

Implemented the newly authorized launch/Requests-open/periodic inbox receipt in the normal local app, with a five-second server worker, automatic acknowledgement/partial/final findings display, Results ready and delivery-error controls, draft preservation and Advanced manual-import recovery. Copy instructions for Dave now copies the already-saved request's exact per-profile handoff without acknowledging it. A protected native clipboard action fixes the installed Qt clipboard issue without changing the CSP. Dave invocation remains manual and all factual/approval states remain intact.

Passed 92 application tests, 22 unchanged exchange tests, both JavaScript regressions/syntax checks, four Qt input/clipboard checks, the native receipt/draft/error/reopen demonstration and all 12 removal/profile/reset layouts. Marry's two publisher tests pass against the receiver. A disposable restore automatically received the exact earlier real acknowledgement/result (38 findings, five institutions/five programs), preserved transport/review state across server restart and replayed with zero duplicate changes/errors. The restore was cleaned up; neither personal profile was reset or used for invented testing. See `reviews/2026-10-19-automatic-receipt.md`.

APP-012 coordinates atomic finalized delivery to the exact active-profile inbox. The existing Main-Apply request was exported unchanged for manual invocation; at this point it has no returned acknowledgement/results. The normal app is monitoring it. The historical real replay does not establish a new execution; the live demonstration awaits actual Dave/Marry delivery. Shared contracts/importer, all 146 protected tracked contents, and unrelated user/producer work remain unchanged by the app team.

## Country interface and report workspace — 2026-10-20

Fixed the reproduced managed-profile decision-save 403 without changing storage or weakening protection. Added independent remembered map-panel resizing and a full-window country-report reader with latest-first navigation, original evidence, caveats, dates, personal notes and secondary revision/recovery controls. Country report availability, factual review, university discovery and personal decisions now have separate labels. Existing Belgium content is reused faithfully; missing structured sections and exact claim-source links remain explicitly unknown. No new research or producer/schema change was made.

Passed 96 app tests, 22 exchange tests, two producer publisher tests, three JavaScript regression files, native pointer/keyboard resizing, save/error rollback, profile isolation, fresh-process persistence, exact map return, image fallback, all 12 width/text-scale combinations and the existing automatic-receipt desktop regression. Normal Main-Apply captures were read-only; private research, decisions and text preferences remained equal. Review: `reviews/2026-10-20-country-reports.md`; app-owned format and ownership: `design/country-reports.md`, coordinated through APP-013. Test-only copies are disposable; captures/audits remain Git-excluded.
