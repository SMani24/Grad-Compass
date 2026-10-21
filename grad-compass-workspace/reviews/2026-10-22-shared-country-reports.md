# Shared country reports: delivery and reader verification

Date: 22 October 2026, Asia/Tehran. Implementation: `f84c91d43dc660197e78d6fa48208cc9ede8a120` (`Unify country report delivery`). This supersedes the separate prepared/legacy presentation paths at `7eb6242`. This work reused existing research and coordinated publication with Dave and Marry through APP-018 / GRA-87. No research rerun or additional request was submitted to agents.

## Concrete cause

| Stage | Belgium before this change | Germany / Canada before this change |
| --- | --- | --- |
| Saved request and response | Country-conditions request, received complete result r2 | Germany partial r1 / complete r2; Canada complete r1 |
| Payload | Country findings plus separately delivered package 0.1, canonical Markdown/map and editorial 0.1 sidecars | Country findings with granular fields and summaries; no ordinarily received prepared package |
| Reader route | `country_report.js::render` created the legacy page, then `report_reader.js::upgrade` replaced it when `report_packages.catalog` found a canonical package | Upgrade returned without a package, leaving the legacy page, generic opportunity/caveat filler and fewer controls |
| Mapping | Prepared sections were parsed from Markdown | The old JavaScript mapper recognized only seven exact field names; study/timing prose inside other summaries was not represented as a separately prepared section |
| Delivery and exports | Prepared delivery had been arranged for Belgium; PDF also had Belgium-specific assets/flag handling | The existing result publisher did not require report preparation/publication; a complete result alone did not supply editorial text, evidence map or report metadata |

These are data mapping, routing and delivery gaps. They do not justify a framework rewrite. The old pure JavaScript projection remains only as a compatibility export for existing callers/tests; it no longer renders a competing report page.

## Shared implementation and ownership

`web/report_model.py` defines app view 1.0. Validated prepared packages and immutable compatibility projections feed one reader, source dialog, reading-position service, version-bound annotations, Markdown export and PDF renderer. No country-specific reader branch is required. Photographs are optional; missing imagery keeps the same composition and controls with an explicit fallback. Shipped illustrative assets are distinguished from research acceptance; the unprovenanced Belgium locator is omitted without deleting its original files.

[The shared contract](../design/country-report-contract.md) documents actual producer package 0.2: detailed Markdown, separately written concise Markdown, structured original-source evidence map, seven-topic coverage, dates, exact saved request/result/finding/document bindings and separate canonical/reader review dispositions. Codex owns app normalization, presentation, exports, private overlays and the generic publisher; Marry owns producer compatibility; Discovery owns research/editorial text; Alex owns exact-version factual disposition; Dave owns execution/release. Human approval remains separate.

`publish_country_report.py` verifies the exported request and package, stages bounded unlinked files privately, rejects conflicts/unreferenced members, finalizes the whole directory and publishes the existing finalized report notice last. The normal inbox validates and retains it. A staged 0.2 directory alone cannot activate prepared-report discovery. Ordinary Dave handoff instructions now name this step. Existing canonical/editorial 0.1, response 0.1.0 and exchange 1.0.0 remain supported. There is no special per-country file installation, automatic agent execution or destructive migration.

A complete response is delivery status. Research coverage, report preparation, factual review, human approval, personal decisions and university discovery remain separate. Coverage explicitly represents supported findings, not investigated, investigated but unresolved, not yet published and not applicable. Older missing coverage stays unknown. Missing concise content explains the disabled Overview control and offers a follow-up draft; the available detailed/findings text remains readable and exportable. Empty editorial files cannot enable capabilities.

## Corrected real packages actually received

| Country | Bound result | Report / concise text | Metadata delivery | Current received disposition |
| --- | --- | --- | --- | --- |
| Belgium | r2; 21 source records | canonical v3 / reader r2 / detailed editorial r2 | `2408f3f2988c81760671dea66dac97edf51be8e0b4a39c9c1fd894b7c6679536` | Canonical and editorials pass; human unknown |
| Germany | r2; 12 source records | corrected canonical v3 / reader r3 | `7c16b4c1c2bc1bb178c18ddc9a074adba482fd0439a01018aa8b274e5fd9215e` | Canonical and reader accepted; canonical human unknown |
| Canada | r1; 5 source records | corrected canonical v3 / reader r3 | `357ddfd68c29a3327815f40a812900b8417e7a2565db0b2c1aac0d29a7fd15e4` | Canonical and reader accepted; canonical human not_requested |

Germany/Canada `revision-0004` are immutable **metadata editions** of the corrected r3 texts, not report v4. Their canonical hashes are respectively `c86dd0eeb368ecc8562fd6451f81f589fd7eaf207f34234e05d4afe36ae144e1` and `7a1272a74dd35436df49fbbb9cd4c039bcfdc64f471e721d3fdc0d81d0d8df00`. Metadata binds Alex's GRA-91 review revision `34412e32-d8e6-4e31-95d0-d7d22087e4be`, recorded `2026-10-21T15:44:27.005Z`. Dave's GRA-85 release comment `f498238a-16af-4099-97f9-716b98582507` authorizes publication of the exact reviewed texts.

All three were received through their existing saved requests and normal private inbox. Germany/Canada final metadata is under `reports/COUNTRY/deliveries/METADATA_SHA/metadata.local.json`; the corresponding finalized notice is `inbox/report-METADATA_SHA.json`. Earlier pending metadata deliveries remain intact. Original finding-level reviews remain pending; source-artifact or prepared-text reviews do not silently approve those findings. Missing reader-specific human approval remains unknown, distinct from canonical human status. The app does not manufacture a claim-level evidence map.

Producer text contains drafting-era awaiting-review statements. These immutable passages remain faithful to the accepted bytes; current exact-bound dispositions are shown separately. Codex reported this wording to Dave/Marry, rather than rewriting accepted research. The known Germany insurance correction and Canada's explicitly uninvestigated award coverage are present in the received corrected text and coverage.

## Verification

- **142 Python tests passed**, including 11 shared-report cases. Focused shared-report tests were repeated after the final empty-edition/coverage validation guards. Three JavaScript regression files, all JavaScript syntax checks, Python parsing and `git diff --check` pass.
- Invented NZL fixture (`tests/report_fixtures.py`) passed normal acknowledgement/result/package inbox receipt, the shared reader, PDF/Markdown, source access, missing imagery, annotations, replay, backup/restore and restart. It has all five explicit coverage states and no real country claims. The same unconfigured package passed a native Qt desktop demonstration in its own disposable profile.
- A separate invented partial FRA response, without a prepared package, passed the same desktop reader/source/annotation/export path. Overview is disabled with its actual missing-publication reason; its PDF is labelled received findings rather than a fabricated concise edition.
- Rejections cover malformed request/result/finding/reader bindings, incorrect evidence/source records, missing coverage, duplicate JSON keys, unsupported precision, missing exact review/approval bindings, empty editions, conflicting immutable revisions, symlinks and unexpected members. Existing invalid-state and unauthorized payload rejections continue passing.
- New review metadata invalidates the validated catalog cache, supersedes pending display metadata for unchanged canonical text, and preserves the original metadata bytes and exact annotations. New content revisions retain earlier annotations as unreconciled. Distinct source revisions with the same source ID are preserved.
- Normal Main-Apply inbox replay and a fresh `LocalWorkspace` restart preserved **177 existing files byte-for-byte and timestamp-for-timestamp**, with research history and personal decisions unchanged. Replayed publication returned `published: false`; inbox errors were empty. Private receipt evidence is `runtime/shared-report-review/owner-replay-restart.local.json`.
- Native desktop BEL/DEU/CAN checks used an explicitly marked private copy of those exact received packages: same controls, Overview/Full/PDF, source references and public links, consistent section alignment/tables, missing-photo fallback, version-bound comment and a second process restoring the comment. Twelve layouts (1440/820/390 pixels × 1/1.15/1.3/1.5 text scale) fit without document overflow. Screenshots were inspected, including fixing missing-image caption contrast and the narrow fallback flag.
- A separate read-only **actual Main-Apply** native desktop run opened all three exact reviewed selections and downloaded PDF/Markdown through Qt and the normal routes. Personal overlay bytes and research history were unchanged; QA suppressed only reading-position POSTs, since position writes were tested in disposable copies. No owner annotation was created. A second native process reopened the same exact report/editorial selections and produced byte-identical native downloads, with all personal overlays unchanged; `normal-receipt.local.json` and `normal-restart.local.json` agree. Current reviewed owner versions have zero annotations, so no owner comment persistence is claimed; nonempty annotation restart was verified separately in the disposable copy. `normal-downloads/` contains the actual exports.
- All **nine final PDF pages** were visually inspected; rendered pages from the actual Main-Apply download hashes are pixel-identical to those inspected pages: no clipping, readable repeating table headers and page numbers; all words are selectable and inside page bounds. Belgium/Germany/Canada PDFs have respectively 28/24/10 public links and 25/3/5 internal links. Detailed Markdown includes the full supplied detailed text and evidence map, all 21/12/5 original public source records and their observation dates, full URLs, coverage, qualifications, unresolved questions, version/review provenance and passage locators. Annotations are excluded by default. Final export inventories are private. The `final/` directory holds isolated-copy exports; `normal-downloads/` holds the actual Main-Apply native downloads. Their PDF hashes differ because separate immutable generated artifacts contain generation metadata; their selected content/review bindings and Markdown bytes agree.
- The 190-file initial protection inventory has no missing files; legacy DB/config, tracked Research Engine and exchange content match. One pre-existing Belgium report index acquired a producer update; it was not rolled back. Owner saved selections, notes, preferences, annotations and report history were not replaced by test fixtures. Test comments and invented requests exist only in marked disposable copies; private artifacts remain Git-excluded.

## Owner walkthrough and local evidence

Reopen the normal **Grad Compass** desktop launcher. In **Main-Apply**, choose Belgium, Germany or Canada, then **Read country report**. The same workspace offers Overview, Full report, PDF, Sources, Annotations and Export; Report details separates actual disposition, coverage and revision types. Older received results remain available in secondary history. Countries with only findings now open this same reader with a specific preparation explanation.

Local screenshots and example exports are under `grad-compass-workspace/runtime/shared-report-review/` (deliberately excluded from Git):

- `2026-10-21-shared-restart-bel-overview.local.png`
- `2026-10-21-shared-restart-deu-overview.local.png`
- `2026-10-21-shared-restart-can-overview.local.png`
- `2026-10-21-shared-restart-can-full-table.local.png`
- `2026-10-21-shared-restart-can-width-390-large-text.local.png`
- `synthetic/2026-10-21-shared-nzl-overview.local.png`
- `partial/2026-10-21-shared-fra-overview.local.png`
- `2026-10-22-normal-bel-overview.local.png`, `…-deu-overview.local.png` and `…-can-overview.local.png` are actual Main-Apply screenshots; the corresponding `normal-restart` captures reopen the same selections.
- `normal-downloads/` contains the three actual Main-Apply PDFs and detailed Markdown exports, with exact hashes in `normal-receipt.local.json`. `final/` retains the earlier isolated-copy examples with its own immutable inventory. PDF renderer `country-reader-8` is an app layout/cache identifier, not a report or response version.

The native harness `scripts/check_shared_reports.py` refuses unmarked personal storage; it deliberately writes comments only in a disposable copy. Use `--countries NZL` for the invented prepared fixture, `--countries FRA --findings` for a partial compatibility view and `--restart` for a second-process annotation check. No failed offscreen rendering approach was repeated.

Actual Main-Apply native export hashes (22 October 2026):

| Country | PDF SHA-256 | Detailed Markdown SHA-256 |
| --- | --- | --- |
| BEL | `6b68d018d3ab8a0880d881090647001ce02cbe5f8029ae075baccdd85a23228e` | `7e02c9f80a15a7a360769f16098db1959175609670a5467de7e618e4ec22f0f4` |
| CAN | `9fcd1dce6e2c4529ad1646ef009b8cbaec9a12d2c1308e0b10fcf220b9148f0f` | `b583b71e95432036aa73b89b6568e808c3a43c6af2a4c6480a0d78f0c81f436e` |
| DEU | `68056c52497c2cd07627240e5d6e09185454aadaf154f72df6609664d19e0d18` | `fda9ed4fb7f88167179b46a4c4c520001c1cf32c17e384c61db245354cdbde55` |
