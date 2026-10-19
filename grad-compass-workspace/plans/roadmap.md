# Agreed development roadmap

Approved direction: map-first web service, initially used locally by its owner, then invite-only beta. Work proceeds in reviewable increments; first personal use needs the complete application workflow before launch.

| Order | Increment | Acceptance criteria |
| --- | --- | --- |
| 1 | Development foundation | Isolated DB/config/vault/cache; legacy-schema preservation tests; safe selection/deletion/file handling; no production changes. |
| 2 | Web shell and discovery | Small Python HTTP layer; preserve Leaflet/plain JS; map default; list toggle; shared filters/inspector; establish user ownership before shared hosting. |
| 3 | University/program delivery | Existing v1 exchange checks and staging; explicit mapping and preview/approval; provenance and unknown/stale states; keep unlocated results accessible. |
| 4 | Existing profile/CV viewer | Consume exact approved copies and receipts/build metadata; do not regenerate completed work; download/display returned PDFs. |
| 5 | Requests/manual handoff | Structured brief plus free text; one immutable private file per submission/follow-up; generated index/prompt; explicit acknowledgements and result links. |
| 6 | Applications/tasks/alerts | Program-plus-intake applications; linked documents/tasks; catch-up checks on open/focus and periodically; persistent alert dismissal and deduplication. |
| 7 | Faculty/outreach | Agreed faculty contract; investigation requests; pasted email/reply threads; explicit follow-up dates; email draft review. |
| 8 | CV/email requests | Paperclip generates artifacts; preserve revisions; backend entitlement controls CV request creation/export; no billing integration yet. |
| 9 | Invite-only beta | Authentication; account isolation; deployment; restore verification; invitations; explicit real-data/deployment approval. |

Deferred: bring-your-own Codex, mailbox connectors, public signup, payments, unattended email delivery, automated Paperclip integration, and database replacement without a demonstrated need.

## Increment workflow

1. Define behavior and acceptance criteria in these notes.
2. Implement using invented fixtures and explicit development storage.
3. Run focused regression and contract checks.
4. Supply a visual review where behavior or appearance changes.
5. Incorporate feedback before the next product-facing increment.

Tests never point to the original application database or private Research Engine data. A production migration, private-artifact transfer, or deployment is a separate reviewed operation. Preserve original row IDs, legacy fields, and source/revision mappings when designing migrations.

## Current bounded increment — 2026-10-13

Increment 3 is authorized as an end-to-end **synthetic** app UI workflow only. It reuses unchanged exchange 1.0.0 and its importer on an explicitly marked disposable database, with selection, validation/staging, explicit institution mapping, simulated dry-run changes, operational approval, eligible promotion and idempotent replay. Real discovery, real publishing/importing and activation on production storage remain outside this increment.

Dave's verified status supersedes stale enrichment/CV assumptions: the existing frozen profile remains valid, the applicant-specific v8 CV package is board accepted, and no additional enrichment task is approved or underway. Increment 4 still needs a separately approved private artifact handoff; increment 5's queue/manifests remain proposals. No regeneration or private transfer is needed to complete this synthetic proof.

## Synthetic watchlist/request pilot — 2026-10-15

The user authorized the bounded app portion of increment 5: country watchlist/private notes, multi-selection, inline remembered preferences, immutable requests/manual handoffs, explicit synthetic acknowledgements/results, feedback/follow-ups and revision review. The complete synthetic round trip is demonstrated and tested around the existing map, floating panels and Map/List toggle.

This is an app-owned synthetic pilot using provisional, separately versioned private/country formats proposed in APP-007. It does not finalize a producer contract or authorize real country/research/applicant transfers. Exchange 1.0.0 remains unchanged and public facts still pass its existing mapping/dry-run/promotion safeguards. Live producer integration waits for compatibility/ownership/private-location agreement and separately authorized scope. Other roadmap increments retain their previous boundaries.

## Map selection and producer compatibility — 2026-10-15

The map now supports an independent temporary multi-country save selection, with a compact floating toolbar and searchable checkbox alternative. Saved-country wording reuses existing membership storage and retains notes/decisions; research initiation remains explicit and separate. See `reviews/2026-10-15-country-selection.md` for the native demonstration and visual review.

APP-008 incorporates Marry/Dave's reviewed synthetic handoff proposal and supplies the existing fixture/test evidence. The app demonstration passes, while proposed-format compatibility still has documented byte/parser/revision/review/completion/association/territory gaps. A future separately scoped adapter correction should reuse the existing fixture and add targeted missing contract cases rather than reconstruct the UI demonstration. Marry’s independent passing verdict must precede a verified-compatibility claim. Real producer activation/private intake and public 1.0.0 changes remain outside the current scope.

## Operational local milestone — 2026-10-16

The user superseded preview-only scope for the persistent personal workflow. Real request/ack/result receipt, field-specific country evidence, institution/program discovery, source-backed app-owned campus points, feedback/refresh bindings and restore-to-new-workspace are delivered using the existing reviewed first dataset. Normal launch uses private persistent local storage, preserves previous personal state and separates samples. No automatic expiry/renewal or agent execution exists. See `reviews/2026-10-16-local-workflow.md` for the actual manually invoked round trip and checks. New research still requires a bounded submitted request and manual Dave invocation; the other roadmap increments remain deferred until authorized.

## Personal-use cleanup controls — 2026-10-16

Delivered user-requested university removal/restoration, independent local profiles and a confirmed recoverable reset in Settings. This enables a fresh personal workspace while keeping testing separate. See `reviews/2026-10-16-profiles-reset.md`. No new research workflow, canonical profile/CV work, shared contract change or automatic execution is added.
