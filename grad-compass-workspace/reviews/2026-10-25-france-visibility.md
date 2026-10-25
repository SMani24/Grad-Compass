# France visibility repair

The France request was present in Main-Apply, France was still saved, and both
partial r1 and complete r2 had been received automatically. No data was lost.

Two app compatibility assumptions prevented access:

1. `report_projection.build` joined coverage values as strings. The operational
   contract accepts structured non-null JSON; France r2 supplied an object. The
   resulting TypeError escaped report catalog construction and prevented research
   state from loading. Marry's reviewed GRA-105 patch preserves legacy strings and
   serializes other accepted JSON deterministically, without inferring coverage.
2. `country_evidence.detail` indexed an optional top-level `source_revision`.
   Operational country records bind `record_revision`; source revisions belong
   to individual evidence records. France omitted the optional legacy field, so
   its country-detail endpoint raised KeyError. The app now uses the actual
   country record revision, with the historical source-revision fallback.

Synthetic tests cover structured/text coverage, received history, restart, reading,
PDF export and an actual country-detail HTTP request without the optional field.
They preserve original response and review/approval values. The country-detail
test verifies multiple findings, exact identities, zero universities and unchanged
research history. The two projection tests, nineteen report-package tests, five
country-workspace tests and thirteen web-preview tests pass (39 total).

Normal-desktop Main-Apply verification opens France through Saved countries and
the map/card details, then reads received result r2 and its findings PDF. Both r1
and r2 remain in history; replay receives zero duplicate responses. A second
native process verifies reopening. Personal overlays and research history are
unchanged. Only reading-position POSTs were suppressed in the owner probe; no
test annotation or research request was added to Main-Apply.

The independently reviewed prepared France package is a separate handoff. At
inspection it had `needs_correction`, human `not_requested`, and no finalized
report notice. Making received findings readable does not release that package.
Dave and Marry were contacted on the existing GRA-101/GRA-104/GRA-105 issues:
the researcher owns bounded corrections, Alex exact re-review, and Marry normal
publication after the actual disposition. No new owner request is needed.

Private screenshots, the native probe, receipts and findings exports are in
`grad-compass-workspace/runtime/france-visibility-review-2026-10-25/`, excluded
from Git. No producer, exchange, legacy database/configuration, private applicant
artifact or immutable received payload was edited. Unrelated work remains unstaged.

Close and reopen the normal Grad Compass launcher to load the corrected Python
handlers. Use Main-Apply → Countries → Saved countries → France → Read received
findings. A completed response describes delivery; the polished report remains
unpublished until its correction/review/publication handoff finishes.
