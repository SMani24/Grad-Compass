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
