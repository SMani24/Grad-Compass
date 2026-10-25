# APP-021 — ordinary workflow verification

25 October 2026. App implementation is delivered; **France's prepared-edition release remains blocked**. Do not interpret this checkpoint as completion of the entire coordinated handoff.

## Application changes

- Map selection opens the existing composer with its exact current scope. Save-only remains independent. Select-all states its filtered scope; saved countries have a persistent dotted green treatment, distinct focus/selection styles and accessible labels. Oversized scopes are shown completely and explicitly blocked by the existing request limit rather than truncated.
- Confirmation binds countries, stage, intake, limits, approved profile reference and destination. Only confirmation commits the immutable request before dispatch. The per-profile outbox is locked across processes and fsynced; offline drafts require explicit retry. Cancel does not invoke anything. Lost acknowledgement reuses the atomic server key and exact parsed bindings; uncertain attempts beyond seven days are reconciliation-only. Task receipt is separate from research acknowledgement.
- Settings → Exports has native Change/Open/Reset controls and a per-profile Downloads/GradCompass default. PDF/Markdown downloads start there, with a native per-export override; missing folders and collisions are handled without a repository fallback. Managed artifacts remain separate.
- Supplied coverage is parsed and qualified without creating prose or positional evidence mappings. Source titles/publishers survive old cached findings. Missing editions identify the next delivery stage. New photographic deliveries retain local hashes, captions, creator/source/licence and optional focal point. Screen credits expand below the photo; absent imagery uses a compact fallback.
- Later asset-only package metadata wins normal selection without overwriting accepted content or advancing replay order. Earlier metadata/PDF pins remain accessible. PDF renderer `country-reader-14` retains earlier files and accepts legacy caption-less photos using their supplied alternative text.

Shared contract: [ordinary-country-workflow.md](../design/ordinary-country-workflow.md). Producer guide: [ordinary-country-reports.md](../../grad-compass-research-engine/docs/ordinary-country-reports.md), supplied by Marry. Public exchange 1.0.0 is unchanged.

## Verification

The full regression run passed 175 Python tests before the final photo compatibility correction. Afterwards all six ordinary-handoff tests (including the new legacy-photo regression), 19 report-package tests and 19 JavaScript tests passed. Ten dispatch tests cover separate OS processes, failed fsync, offline/restart, cancellation, amendments, profile/destination conflicts, duplicate clicks, lost acknowledgements and expiry. No real agent was invoked as a test; physical power loss and live wake success are not claimed.

Normal Qt desktop and second-process restart receipts cover exact map scope, confirmation/cancel, offline pending/reconciliation to one fake task, export preferences/download routing, a previously unconfigured invented Chile package, whole-catalogue selection with individual exclusion, and narrow 150% text. Native directory selection was substituted in that harness; the application uses QFileDialog. All invented data remains isolated.

Main-Apply normal country cards/navigation selected the actually published Germany and Canada photographic packages, preserving their v11/r11 text/review identities. Belgium v3/r3 passes as regression. Native PDF/Markdown exports match after restart, zero-item replay reports no errors, all 269 original report files retain bytes/timestamps, and personal overlays/research are unchanged. Owner reading-position POSTs alone were suppressed by the probe; nonempty annotation/position persistence tests remain isolated. Human approval is unchanged.

All seven final prepared-report PDF pages were visually inspected, with text bounds, links and local asset hashes checked. Standalone Markdown retains every supplied substantive section, public source URL, edition hash and qualification. Private screenshots, exact request/package/export identities and receipts are indexed in `grad-compass-workspace/runtime/ordinary-workflow-review-2026-10-25/review.local.md`; none are tracked.

## France: concrete remaining dependency

The existing response r2 supplies a summary, sources and structured coverage; it does not contain the authored detailed/concise editions. Those editions exist separately but remain unpublished after a correction-required review. Parsing coverage cannot supply the missing prose. The seventeen source titles now render faithfully; unbound historical FRA references remain explicitly unbound. Interim findings/navigation/exports, restart and replay pass in actual Main-Apply.

Dave traced the stalled correction assignment to a stopped legacy execution with `recovery_needed` / `legacy_execution_requires_reconciliation`, inspect-only permitted actions and no active successor/retry. The supported continuation requires an authenticated Paperclip **board operator** to reconcile the observed execution outcome in the existing recovery interaction. Dave owns coordination; Ali owns the existing bounded corrections, Alex exact review, and Marry subsequent notice-last publication. No recovery bypass, duplicate request, factual acceptance or release was manufactured. Final France prepared-edition/photo acceptance remains open in APP-021.

Implementation commits: `97739bc` dispatch; `8824a5c` map/report/export integration; `78480d3` Marry's producer guide; `7176d0c` photo presentation and legacy PDF correction. Reopen the normal Grad Compass launcher with Main-Apply active to load the updated app.
