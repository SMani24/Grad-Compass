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
