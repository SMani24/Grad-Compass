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
