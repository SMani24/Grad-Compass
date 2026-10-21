# Country report view 0.1 — 2026-10-20

This is an app-owned, read-only presentation format, implemented by `grad-compass/web/country_report.js`. It does not replace the private response 0.1.0 contract or exchange 1.0.0, change any received bytes, or establish factual acceptance. Legacy responses continue to render. No producer change is required in this increment.

## Minimum content projection

`projectCountryReport(result, request, country_code)` produces:

```json
{
  "schema_version": "app-report-view-0.1",
  "country_code": "CAN",
  "request_id": "saved request identity",
  "result_id": "saved result identity",
  "result_revision": 2,
  "result_digest": "exact received body digest",
  "report_date": "producer issued_at",
  "observations": ["finding observation time"],
  "applicable_academic_year": null,
  "sections": [{
    "id": "funding",
    "title": "Funding and what it covers",
    "blocks": [{
      "id": "country:CAN:conditions/funding_routes",
      "revision": "exact finding revision",
      "finding_id": "country:CAN:conditions",
      "field": "funding_routes",
      "text": "Exact received wording, including qualifications.",
      "observed_at": "finding observation time",
      "academic_year": null,
      "citation_scope": "finding",
      "sources": []
    }]
  }],
  "sources": []
}
```

Stable section IDs are `overview`, `study`, `funding`, `costs`, `work`, `timing`, `questions`, plus a source bibliography. Stable field/block IDs combine the existing finding ID and field path. Bind any citation, annotation or feedback to **result digest + finding ID/revision + block ID**. A stable field anchor alone does not prove that revised text is unchanged. Legacy uncertainty array positions are revision-local anchors; never move annotations between revisions by array position alone.

Original strings are rendered as text, never executable HTML. Missing sections and separately unspecified academic years remain unknown. Observation time, report issuance and requested intake are shown separately. Dates never imply current applicability. A complete bounded request does not imply exhaustive country coverage, completed university discovery, factual acceptance, or a personal shortlist decision.

The Belgium response supplies sources at finding level, with no exact per-claim source map. Its original qualifications and all supplied sources are retained. The view explicitly labels finding-level citations and links them from each supplied block; it does not invent precise claim-source associations. Its overview contains study/intake context; standalone route and application-timing sections explain the missing structured evidence and link back to that overview. This is a faithful legacy fallback, not a newly researched or approved report.

For a later agreed producer format, the smallest useful additions would be explicit stable section/claim IDs, exact claim-to-source references, and separately stated academic-year applicability. These are proposals only; Marry owns any response-compatible producer design and Dave/Alex own evidence/review. Do not add mandatory wire fields or alter current validation without coordination.

## Assets

`web/assets/countries.json` maps country codes to a local image path, descriptive alt text, creator credit, source URL, license/URL, photo date and exact file SHA-256. `belgium-grand-place.jpg` is an unmodified CC0 photograph by Romaine, from [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Brussels-Grand_Place.jpg). The photo depicts Grand Place, Brussels; it is decorative country context, not university/campus evidence. CSS supplies the modest header crop. No external image request is made while reading; absent/broken imagery uses the navy/teal flag fallback. Do not put applicant materials or private report payloads in this manifest or Git.

## Ownership and storage

Codex owns app projection/rendering, navigation, map panel controls, UI styles, assets and this document. Paperclip owns original claims, sources, factual acceptance and producer revisions; Marry owns wire compatibility. Existing response and exchange files remain unchanged. Country notes reuse the existing private note field; the optional rail is not a second canonical profile or factual approval process. Feedback uses the existing finding/revision binding; a block reference can be included in the comment without changing its schema.

Panel widths are app-owned `panel-widths.json` in each marked local profile. They are validated, backed up, reset with that profile, and never written to legacy configuration or browser-wide storage. Wide-window handles resize independently; narrow windows adapt without replacing preferred widths. Reading leaves the map mounted, preserving camera, selection and widths on return.

## Canonical packages, PDF and annotations — 2026-10-20 continuation

The earlier field projection remains the fallback for received findings without a canonical package. A validated private package now takes precedence in the reading workspace. `web/report_packages.py` reads the existing producer-owned `reports/<country>/…/metadata.local.json` layout; `web/report_content.py` parses canonical Markdown and its evidence map into one allowlisted content tree. Both `web/report_reader.js` and `web/report_pdf.py` consume that same tree. No canonical wording, received result, factual review or producer file is rewritten by the app.

The existing package version remains `grad-compass-private-report-package-0.1`. The reader checks the exact request/country binding; canonical/evidence file hashes; producer result/finding revision when supplied; and exact canonical revision/hash, review record, time and scope for a non-pending factual disposition. Human approval is checked separately. Duplicate JSON keys, unsafe paths/links, missing or changed bytes, conflicting canonical revisions and mismatched bindings fail. Earlier validated versions remain readable when a later package is invalid or unavailable. A pending draft is viewable as pending; file availability is not agent acknowledgement or factual acceptance.

An optional announcement in the existing owner-private inbox uses the existing `{body, sha256}` exact-byte transport. Its decoded body is:

```json
{
  "schema_version": "grad-compass-report-delivery-0.1",
  "request_id": "existing saved request UUID",
  "request_revision": 1,
  "request_sha256": "exact saved request bytes",
  "metadata_path": "reports/CAN/report-id/revision-id/metadata.local.json",
  "metadata_sha256": "exact metadata-file bytes"
}
```

This announcement is a sidecar convention proposed to Marry through APP-014, not a new research response kind or exchange schema change. Publish complete package files before the finalized notice. Temporary/hidden writes are ignored, changed/invalid notices do not create research records, and replay does not duplicate history. The app also discovers already-prepared local packages for explicitly authorized draft viewing. Marry retains ownership of producer delivery and the final exact-bound disposition. Existing 0.1.0 responses work without this optional announcement.

App-owned storage is `report-cache/<canonical-key>/<metadata-digest>/` plus `report-annotations.json`, all under the active private profile. The canonical key binds report ID, canonical revision ID and canonical SHA-256. Retained canonical/evidence bytes, metadata, generated PDF editions and their hash inventories are immutable. A changed review can produce a new metadata/PDF edition without losing annotations on unchanged canonical content. PDF renderer upgrades retain earlier binaries so existing page annotations still open their original export. Backup/reset/profile isolation follow the existing local-workspace rules.

Each content block has a stable section/paragraph-or-cell reference derived from its text and occurrence within the exact canonical revision. Annotations store a private UUID, canonical key/hash, country/request reference, exact quote, comment and timestamps. Report selectors use block ID and Unicode code-point offsets. PDF selectors additionally use metadata edition, exact PDF SHA-256, zero-based page and exact page-text offsets; visible page numbers are one-based. Quotations are checked against the saved content, not trusted from the browser. Words/rectangles are derived from the retained PDF with Qt PDF. Earlier annotations are never automatically reanchored to a new canonical version; the UI marks other-version annotations as unreconciled.

Feedback preparation stores a private draft containing selected quotations and exact report/page references. Explicit saving uses the existing request/result/finding-bound feedback envelope. Follow-up preparation uses the existing bounded refresh form and request-only preference exceptions. No automatic sending, factual approval, preference edit or agent execution is introduced. Personal country notes remain separate and available on the map.

Codex owns the content parser, reader, app PDF exports, annotations, native download control and static app assets. Marry owns producer metadata/package publication and compatibility; Dave/Alex own canonical content and factual review. The original prepared producer delivery document and flag source remain their files; the app uses a copied flag asset. Locator provenance, extent, transformation, public-domain source and exact hashes are in `web/assets/countries.json`. It depicts country geography, never campuses. Conditional numbers come from canonical content; no applicant affordability or guaranteed-support graphic is inferred.

## Reader editions and portable exports — APP-015, 2026-10-20

The reading workspace now uses the available window for tables and figures while constraining prose independently: Comfortable is approximately 70 characters, Wide approximately 92, constrained by the actual viewport. The saved-request sidebar collapses; section navigation is a compact toolbar selector. Closing annotations releases its width. Map resize handles are quiet edge dividers with a 20-pixel pointer target, a stronger hover/focus/drag indicator, and the existing keyboard/reset behavior.

`report-reading.json` is an app-owned private profile preference, included in ordinary backups. It stores width, sidebar visibility and reading positions keyed by exact canonical content key. Positions use a stable passage ID plus pixel offset, rather than a window-size-dependent document offset; a top-of-document position is also supported. Writes are debounced, flushed on navigation and restored after images/layout. These preferences neither modify research history nor travel to agents. Existing annotations, PDF inventories and canonical keys are unchanged.

### Implemented exports

The selected canonical report and metadata edition determine both exports. The research result revision is a separate identifier. In the Belgium handoff, result r2 initially supplied report v1; a genuine replacement report v2 arrived subsequently. The reader labels report versions explicitly and explains the relationship in a secondary “About versions and exports” disclosure. A renderer name is an app layout/cache identifier, never a factual report version.

* **Reader PDF:** `web/report_pdf.py`, renderer `country-reader-2`. Until producer concise copy is agreed and delivered, the fallback selects complete current canonical at-a-glance passages, the qualified regional cost table and its explanation, and the first three timing/next questions. It does not paraphrase new factual assertions. It includes dates, scope, actual review, historical/unknown/conditional distinctions and linked editorial source references. Other reports without that editorial structure retain their complete content as a fallback. The full source-map text and all omitted detail remain in the Markdown companion. Old detailed PDFs and old reader renderers stay immutable and retrievable by digest, including through their original page annotations.
* **Detailed Markdown:** `web/report_export.py`. The entire canonical Markdown and editorial evidence map are included verbatim, followed by bound public finding-level source records, observation dates, complete passage text with stable locators and exact report/review/result provenance. This retains calculations, applicable years, regional differences, unresolved conflicts and source qualifications. All public source URLs are present; the original map's obsolete sibling filename and internal coordination links remain historical context, not dependencies. Its content and public evidence are embedded in the file. It does not manufacture a precise claim-to-source mapping where the producer supplied only topic or finding-level associations. Local operational metadata paths are omitted. Personal annotations are excluded by default; a labelled checkbox explicitly includes only the selected report version's saved annotations in a separately named Markdown export. PDF exports keep annotations separate.

Example names: `belgium-country-report-2026-10-20-v2-reader.pdf`, `belgium-country-report-2026-10-20-v2-detailed.md`, and `…-v2-detailed-with-annotations.md`. Choosing report v1 exports v1, without overwriting its internal immutable cache or reanchoring annotations. The same-origin native download handler permits only these report PDF/Markdown routes and preserves the server's descriptive filename.

### Small optional producer addition — proposed, not activated

Keep private report-package 0.1, private responses 0.1.0 and public exchange 1.0.0 compatible. The smallest proposed addition is an optional `reader_document` metadata reference alongside `canonical_document` and `evidence_map`:

```json
{
  "reader_document": {
    "relative_path": "country-reader-r0001.md",
    "sha256": "exact UTF-8 reader document hash",
    "revision_id": "editorial revision UUID",
    "revision_number": 1,
    "canonical_revision_id": "exact detailed canonical revision UUID",
    "canonical_sha256": "exact detailed canonical bytes hash",
    "evidence_map_sha256": "exact accompanying evidence map hash",
    "passage_map": {
      "opportunities-1": ["existing-canonical-section/text-hash/occurrence"]
    },
    "factual_review": {
      "state": "pending"
    },
    "human_approval": {"state": "unknown"}
  }
}
```

The concise Markdown uses stable explicit editorial paragraph IDs, for example an `<!-- passage: opportunities-1 -->` marker preceding a paragraph. Dave/Discovery provide engaging concise wording, essential conditions, opportunities, obstacles, unknowns and next steps. The mapping binds editorial passages to detailed canonical block IDs (available in the portable export); it records editorial lineage rather than inventing factual support. A non-pending editorial review must name its own exact editorial revision/hash, record, time and scope, separately from canonical review and human approval. The draft shape above requires Marry's compatibility confirmation before producer adoption or consumer activation. No undelivered summary is treated as approved or silently substituted into the app.

Marry owns metadata/package/notice delivery and compatibility, Dave/Discovery own both research and editorial wording, Alex owns factual review, and Codex owns consumer validation/rendering/export/cache. A new concise revision, changed parent binding or review record is a new immutable package edition. Retain earlier report/PDF versions and private annotations. No rewrite of shared importer files or exchange schemas is needed. The current exact canonical package remains usable while this optional concise addition is discussed; the tested extract fallback is already implemented.

## Received editorial sidecars — APP-016, 2026-10-20

The delivered format is a pair of standalone `grad-compass-private-editorial-edition-0.1` sidecars under `reports/<country>/editions/…/metadata.local.json`. This is the implemented adapter; APP-015's optional `reader_document` reference remains a historical proposal and is not required or activated. The user's integration request authorizes viewing the delivered drafts with their actual disposition. It does not change producer ownership or factual acceptance.

Each sidecar names `edition` (`reader` or `detailed`), country, report date, positive revision number, document revision UUID, filename and exact UTF-8 SHA-256. `parent_canonical_revision_id`/`parent_canonical_sha256` and `evidence_map_revision_id`/`evidence_map_sha256` must match the selected canonical package. Factual review and human approval remain separate. Pending/unknown review is displayed literally. A non-pending editorial review must bind `document_revision_id` and `document_sha256`, with its review record, time and scope; a non-unknown human disposition requires its own exact document binding and approval record. It never changes canonical review or the original finding's review.

`web/report_editions.py` validates exact bytes, duplicate keys, paths, parent/map/country bindings and immutable revision conflicts. Original producer files are untouched. App snapshots live in profile-private `editorial-cache/<canonical-key>/<metadata-sha>/document.md` and `metadata.local.json`, and are included in ordinary backups. Older validated editions work offline when the source sidecar is unavailable. Existing inbox checks also discover finalized local sidecars; their IDs participate in the existing results-update indicator. A new edition offers an explicit update action instead of replacing an active draft. No new agent invocation, producer queue or shared exchange schema is introduced.

The concise edition opens as **Overview**. **Read full report** opens the delivered detailed edition. If no editorial sidecar exists for an earlier canonical version, that canonical report remains readable. Section navigation reflects the current document. Compact inline E references open an accessible source dialog; details remain available in the source section and detailed research. The references preserve their literal passage text and the producer's topic-mapping precision. Opening sources does not start research or imply approval.

An editorial annotation uses the existing private overlay with `view: editorial`, its exact retained document metadata ID, block ID, Unicode offsets and exact quote. Canonical selectors remain `view: report`; old PDF selectors retain their original PDF digest/edition/page. New prose never inherits old highlights. Returning to an older annotation opens its retained document; earlier-edition notes are identified explicitly. Reading positions use the canonical key plus exact editorial ID; original canonical reading-position entries remain intact. Jumps account for actual toolbar height and cancel pending automatic restoration, so navigation cannot be overwritten by a delayed restore.

Both export links pin the selected canonical metadata edition and the exact reader/detailed IDs. New deliveries cannot alter an export already selected on screen. Changing canonical version updates both links and resets private annotation inclusion off. PDF cache names include the reader metadata ID; older renderers and page annotations remain usable. Filenames include canonical version and editorial revision/ID, for example `…-v2-reader-r1-<edition-id>.pdf` and `…-v2-detailed-r1-<edition-id>.md`.

PDF renderer `country-reader-6` uses the received concise text, omits only introductory/technical binding/source-guide repetition, and provides a compact linked source appendix. The branding row gives the flag explicit dimensions. A modest portrait inset preserves the photographic subject with its credit. Tables repeat headers across pages; headings reserve room for the first row without moving entire tables to a new page. Exact canonical/editorial hashes are also in PDF properties; the printed shared-origin line stays short. No agent/workflow instructions are inserted into the reader edition.

Detailed Markdown includes the complete delivered detailed text, complete evidence map, all bound public source records/observation dates and stable passage references. Historical internal lineage links are labelled as identifiers rather than external dependencies. It retains regional categories, applicable years, caveats, calculations and unresolved questions without inventing claim-level support. Exact version/review provenance is embedded. Personal annotations require an explicit checkbox and are excluded by default.

Codex owns this consumer, layout, exports and private overlays. Dave/Discovery own both editorial texts and research; Alex owns factual review; Marry owns producer compatibility/publication and delivery metadata. Public exchange 1.0.0, private research response 0.1.0, canonical history, legacy DB/configuration and applicant artifacts remain unchanged.

## Reader composition and catalogue drafts — 2026-10-21

The reader uses one composition instead of independently centred headings and prose. Each section's heading, paragraphs, lists and qualifications share a left edge. Comfortable uses a 46-rem prose measure within a 64-rem composition; Wide uses 60/78 rem. Tables can use that composition's wider area and scroll inside their own labelled region on small screens. The first section and credited locator form a deliberate overview grid; the locator becomes a compact secondary row when the available reading column narrows. Annotation space is reclaimed when closed. These are screen-layout preferences, not new document editions or PDF renderers.

The compact header shows country, report version/date, requested intake and the actual canonical/current-edition review states. Report details retains observation/review dates, human approval, both editorial review states, canonical/export relationships and exact technical provenance. Funding/cost qualifications stay beside the relevant tables. Contextual research help explains the unchanged manual Dave invocation and automatic receipt.

The toolbar groups Overview / Full report / PDF, section navigation, annotations, Export and Reading options. Export contains reader PDF, detailed Markdown and the explicit optional private-annotation inclusion; Reading options contains Comfortable/Wide and older canonical versions. Highlight/Comment appear for a valid text selection, including keyboard-created selections. The contextual buttons remain keyboard focusable; Alt+H/Alt+M act on the selected passage while focus is in the reader. Sticky offsets use the measured toolbar height. Existing document-bound reading positions, source references and annotation selectors remain unchanged.

Explore countries now keeps a separate private research draft for all catalogue countries **and territories**, including unsaved entries. Select all matching uses the complete filtered catalogue, not visible cards or table rows. Individual exclusions, filter changes, outside-filter counts and Clear selection operate on that draft alone. Map saving selection, saved membership, notes, personal decisions and focused map country remain separate.

Codex owns `web/research_selection.py` and the profile-local, Git-excluded `research-selection.json` (`{"countries":["BEL", "…"]}`). The existing guarded app endpoint `/api/research/draft-selection` saves it atomically; `/api/research` returns it as `draft_selection`. Research's reentrant lock also protects this file during snapshots/backups. Backups include it and recovery restores it. No research envelope, producer file or exchange 1.0.0 contract changes.

Research selected transfers the entire draft into the existing request composer and displays its count and full scrollable scope. The current handoff still accepts at most 20 assigned country codes; some catalogue territory identifiers need producer mapping agreement. Larger/unsupported scopes remain intact in the draft, with a clear explanation and submission disabled. There is no silent truncation or automatic splitting/execution. Broader research remains a later explicit request. Marry owns any future delivery-limit/mapping agreement; this interface increment does not activate it.
