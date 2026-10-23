# Shared country reports and ordinary private delivery

Version: **2026-10-21 / app report view 1.0 / private package 0.2**. Codex owns the consumer, view, exports, private overlay and generic publisher. Marry owns producer compatibility; Dave owns execution/release coordination; Discovery owns research and editorial text; Alex owns exact-edition factual disposition. Human approval is separate. The app adds no competing approval process or agent executor.

## Why the interfaces diverged

At app `7eb6242`, `country_report.js::render` built an older finding-only page. `report_reader.js::upgrade` replaced it only when `report_packages.catalog` found a separately prepared canonical package. Belgium had package 0.1 and standalone editorial 0.1 deliveries; Germany and Canada had result findings without those packages. Their complete response envelopes therefore never activated prepared-report capabilities. The old JavaScript mapper recognized a small set of exact fields and added generic opportunity/obstacle/caveat counts; newer summaries contained study/timing prose without separate fields. The response publisher did not require the report package step. PDF assets/flag/filenames also singled out Belgium. This is a missing normalized model and delivery requirement, not evidence that the app needs a framework or OOP rewrite.

## One validated app view

`web/report_model.py` emits `grad-compass-country-report-view-1.0`. `report_packages` validates prepared packages and exact result bindings; `report_projection` adapts retained received findings without editing their bytes. Both feed the same reader, sources, annotations and export services.

The view includes identity/version labels, original result delivery completion, report/concise preparation, seven coverage topics, exact-document factual review, original finding reviews, human approval, source precision, optional offline visuals and capabilities with reasons. Coverage is one of `supported_finding`, `not_investigated`, `investigated_unresolved`, `not_yet_published`, `not_applicable`; old missing coverage is explicitly `unknown`. It never turns absent fields into evidence that research was or was not done. Country facts, regions and qualifications remain supplied content.

Legacy projections are explicitly **received findings**, not prepared reports or concise editions. They retain immutable exact-source inventories under private `report-projections/` and preserve original findings/review records. A missing concise edition disables Overview with an explanation and follow-up action; available findings remain readable, annotatable and exportable as findings/full content. A PDF is not falsely labelled a concise edition when none exists. No generic filler replaces missing content.

## Actual producer package 0.2

The accepted representation adapts the immutable producer format already supplied on GRA-85. The early proposal for an `editions` list of separate sidecars is superseded for 0.2. Existing 0.1 canonical packages and standalone editorial sidecars remain readable unchanged.

A directory contains `metadata.local.json`, canonical **complete detailed** Markdown, concise reader Markdown and its evidence map, plus optional named assets. Metadata keeps these existing fields:

- `schema_version: grad-compass-private-report-package-0.2`, opaque `report_id`, country code and optional preparation status.
- `request`: saved `id`, `revision`, exact UTF-8 `sha256`.
- `producer_result`: received `id`, `revision`, exact body digest and `finding_revision`. `finding_id` is recommended; if omitted, country plus exact finding revision must identify exactly one finding in that exact result. Ambiguity is rejected.
- `canonical_document`: opaque document ID, immutable revision ID/positive number, relative path and exact SHA-256. This is the complete detailed text; a second identical detailed file is not required.
- `evidence_map`: immutable revision ID, relative path, media type and exact SHA-256.
- `reader_editorial`: immutable revision ID/positive number, relative path/hash, exact parent canonical revision/hash and evidence-map revision/hash, with its own factual review. It is an independently supplied concise text, never an app-generated substitute.
- `coverage`: all seven keys `overview`, `study`, `funding`, `costs`, `work`, `timing`, `questions`. Each has `state`, nonempty `detail`, explicit `applicable_year` (string or null), and `evidence_refs`. Supported coverage requires supplied references. Optional `section_ids` must name actual canonical sections.
- `source_citation_scope`: `finding`, `topic`, or the producer's precise `finding_level_with_unreviewed_editorial_topic_mapping`. These are preserved as their actual precision, not promoted to audited claim-level support.
- Separate `canonical_factual_review` and `human_approval`. Pending/unknown report review confers no acceptance. A non-pending disposition requires the exact canonical revision/hash, review record, time and scope. Human `not_requested` is retained as that state; approval/other substantive dispositions require their own exact binding. Inline reader review has equivalent exact reader-document bindings. Missing reader human approval is unknown.
- Report preparation date either `report_date` or an explicitly stated “prepared DD Month YYYY” in the delivered report. Source observations and applicable years remain independent.

The structured evidence map is `grad-compass-private-report-evidence-map-0.2`, with country, citation scope, original observation date, `sources` keyed by stable public reference labels, and the identical seven-topic `coverage`. Source records must exactly match sources on the bound received finding. Labels such as `DEU-01`, `CAN-01` or an unconfigured country's labels are data, not hard-coded parsers. Existing Markdown `E01` maps remain supported for package 0.1. All references must resolve; topic mappings do not invent finer claim support. JSON duplicate keys are rejected.

Optional `assets` entries have kind (`photo`, `flag`, `locator`, `figure`), safe relative path, exact hash, PNG/JPEG media type, alt text, caption, creator/credit, public source URL and license. Images are bounded and retained privately for offline access. A missing image is valid and uses the same reader layout with an explicit availability fallback. A shipped illustrative photo is not labelled producer factual acceptance. An unreviewed locator/quantitative figure must not acquire a review claim from the report's text review.

## Publication and receipt

After preparation and the actual review/release disposition, the producer runs:

```sh
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/publish_country_report.py \
  --handoff 'PROFILE/research-handoff/request-UUID.json' \
  --package 'FINALIZED_PRIVATE_DIRECTORY'
```

`--check` performs the same validation without publishing finalized files or a notice. The normal command verifies the saved handoff/reference, copies only bounded unlinked package members into hidden private staging, validates exact bytes/request/result/finding/reader/evidence/coverage/review bindings and immutable revision conflicts, then finalizes the entire directory under `PROFILE/reports/COUNTRY/deliveries/METADATA_SHA/`. Unreferenced files are rejected. It publishes the existing exact-byte `{body,sha256}` **report notice 0.1 last**, with the final metadata path/hash. Neither command invokes research or grants factual acceptance.

The normal app's existing inbox receiver validates the finalized notice, retains immutable content/editions/assets and an exact private receipt, and updates the shared catalog. Merely placing a 0.2 draft under `reports/` does not publish it: no validated receipt means it is excluded from the reader. Replay preserves file bytes, timestamps/history and annotations; restart rediscovers received versions. Failures show their actual validation reason. Hidden unfinished writes are ignored. Producers publish progress acknowledgements/partial/final results independently; response `completion: complete` never promises complete coverage or finished report preparation.

For an ordinary country-conditions request, Dave's generated instructions now require both response delivery and this report-package step. No owner file installation or country-specific code change is involved. Public exchange **1.0.0**, private responses **0.1.0**, report notices **0.1**, existing **0.1 packages/editorials**, original source bytes and earlier annotated artifacts stay compatible. No destructive migration is performed.

## Executable acceptance fixture

`tests/report_fixtures.py` creates an invented **NZL** request/result/package with source label `TEST-01`, no configured images and all five explicit coverage states. `tests/test_shared_reports.py` uses the normal finalized inbox for acknowledgement/result/package receipt, then checks one model, exports, source access, annotations, replay, recovery/restart and rejection cases. It does not use real research or private applicant files. Run with:

```sh
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass/tests -p test_shared_reports.py -v
```

Real acceptance additionally requires the corrected Germany/Canada package revisions, their actual dispositions/release, normal receipt and desktop reading/export evidence alongside Belgium. Passing the invented fixture alone does not complete that delivery.


## APP-018 display reconciliation — 22 October 2026

Ordinary country-card and country-selector navigation prefers a valid prepared report across the active profile’s existing requests and shows its actual source request. This does not rebind that report to a newer request. Explicit request/result history remains scoped to the selected request and response revision. Within that scope, normal reading prefers the latest valid prepared version; historical findings explain their exact scope and can return to an existing prepared report without preparing another request.

Editorial compatibility includes the complete `(country, canonical revision/hash, evidence-map revision/hash)` tuple. A later evidence-map edition can retain the same canonical text. Earlier editorials remain valid only against their own retained tuple, with their original citations, exports and annotations. Unknown tuples and corrupt historical bytes still fail validation. Historical status is not an exception to digest checks.

Producer bookkeeping metadata under `reports/COUNTRY/maps/` is a separate reference-only artifact, not an ordinary canonical package. The existing unversioned sidecar is checked for a positive revision, document identity, safe filename/exact digest and a matching received canonical/map tuple. Its supplied review state is retained; classification does not promote a pending map or replace the report package’s exact review record. No public exchange, producer or response schema changes are required.

## APP-019 composition ownership — 23 October 2026

[Reader/export template](country-report-template.md) defines the compatible Markdown heading convention and `grad-compass-report-composition-1.0` projection. Discovery supplies both research editions and their request-relevant implications; Codex renders one public source inventory from the exact bound map/records. Coverage and operational metadata are secondary, with human labels; original bytes, passage IDs and earlier exports remain immutable. Current review comes from the selected exact document receipt. Historical source-context assertions are explicitly historical, with narrower evidence scope retained. Existing package/response/notice/exchange versions and structural validation are unchanged; editorial usefulness remains Dave/Alex's responsibility. Marry confirmed the convention on GRA-99. The producer workflow is documented in its owned `docs/ordinary-country-reports.md`; these consumer changes do not replace it.
