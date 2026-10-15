# Watchlist and manual research milestone · 2026-10-15

## Increment 1 — watchlist and private notes

Country details/cards/List now offer watch/unwatch independently of personal decisions. Countries mode has an All countries / My watchlist filter and multi-country research selection. Selection is shared between cards and List; filtering does not silently drop selected countries, while unwatching removes that country from the pending selection. Private notes are explicitly saved and survive unwatching.

State lives in a separately marked, Git-excluded `research.sqlite` under the marked synthetic preview runtime. The original map DB is read-only. Existing personal decisions remain in their separate state file. Unknown country/invalid watch/note payloads, linked files and unmarked state are rejected.

Demonstrated France with no universities → watch → private note → Shortlisted assessment → watch Canada → My watchlist → select both for research. App tests: 43 passing cases. Native navigation and watchlist checks passed. Local capture: `2026-10-15-research-watchlist.local.png`.

APP-007 was appended early to the manual mailbox with provisional private request/ack/result/feedback and separately versioned country-evidence proposals. APP-006 and APP-007 await Marry/Dave compatibility feedback. Only app-owned synthetic adapters are being implemented; public exchange/importer files are unchanged.

## Increment 2 — immutable requests and remembered preferences

The request form collects shared preferences inline on first use and shows a compact editable summary thereafter. Blank values remain unknown; countries/scope/limits/context stay request-specific. Successful deliberate submissions remember explicit shared values unless Only for this request is checked. Cancelled forms make no preference writes. Each request retains its own immutable snapshot and optional exact parent/result references. Retrying the same submission cannot duplicate or silently change a request.

Prepared requests remain local, without invented agent progress. A manual export creates an immutable request file in the ignored synthetic runtime and a minimal opaque-ID/state index. The copyable prompt points to the private file and exact request binding without echoing preferences/context. Original map DB/config/profile remain untouched. App-only synthetic acknowledgement/result/feedback persistence and versioned fixture adapters are scaffolded behind the provisional APP-007 proposal; their review interface follows in increment 3.

Demonstrated: first form cancelled → unknown preferences unchanged → first submitted request → reference-only private handoff → prefilled next form → cancelled edit unchanged → request-only alternative submission → autofill still uses remembered values. App tests: 47 passing cases. Captures: `2026-10-15-research-{first-request,request-handoff,prefilled-request}.local.png`.

## Increment 3 — explicit responses, findings, feedback and revisions

The request dialog now has optional manual-response controls, exact-binding previews and explicit receipt. Only deterministic app-generated synthetic envelopes are accepted. Real/custom data, unsupported versions, altered contents/digests, wrong request bindings and invalid revision order are refused. Preparing/loading a response does not acknowledge anything. Accepted/rejected/clarification states are explicit; the demo does not invent execution progress.

Results retain every immutable revision. Country findings populate country details with summary/funding/costs/work rules, sources, observed dates and unknowns; source history links back to the originating request/revision. Public institution/program references retain exchange batch/digest/UUID identity and use the unchanged importer. Only promoted facts enter discovery, with request-origin links inside the parent institution/program panels.

Finding-specific feedback exports a separate immutable private handoff. Refresh requests retain exact parent/result/finding references, current remembered preferences and request-specific comments. Feedback is not a permanent preference or evidence approval. Revised results show material before/after differences and preserve earlier findings/comments. A late duplicate old receipt cannot downgrade the latest evidence. Watchlist membership, notes and assessments remain independent.

### Complete synthetic round trip demonstrated

1. Watch France with no saved universities; save a private note and Shortlisted assessment. Watch Canada and select both countries.
2. Cancel an initial draft and verify unknown preferences remain unknown. Submit a university/program request with explicit intake/alternatives/routes/language/funding/limits. Export a reference-only handoff.
3. Verify the next form is prefilled, cancelled changes are not remembered, and a request-only intake exception leaves autofill unchanged.
4. Preview then explicitly receive an accepted acknowledgement. Receive four first-result findings (two country, one institution, one program); replay that response without adding a revision.
5. Save Canada funding feedback and prepare its private handoff. Save a follow-up request linked to that exact finding/revision, without changing country restrictions from feedback.
6. Receive result revision 2. Inspect eight material funding/cost/source/date changes. Reopen revision 1 and its original feedback.
7. Open the existing public import review from the result. Validate/stage, explicitly map, dry-run, approve eligible promotion and verify duplicate-free replay. Open the program's source request/result from its discovery panel.
8. Reopen France: the revised evidence is visible, and the watchlist, private note, Shortlisted decision and unreviewed evidence status are unchanged. Reload the page and verify both result revisions and personal state persist.

The full request/result flow was also checked at all four text sizes at 1440-wide desktop and minimum 390×640. Existing country layout checks covered intermediate 820 width, and existing university/history/keyboard/import checks also passed. Panels/dialogs scroll within the viewport; optional response controls collapse after findings arrive, and desktop request navigation stays available while results scroll. The camera-preservation check now waits for the original framing animation to settle before comparing geometry.

### Validation

- 50 application Python cases, 22 unchanged shared exchange cases, 15 JavaScript cases and three Qt input cases passed: **90 regression cases**.
- Native demonstrations passed: watchlist/request round trip and four-size layouts; country history/context/keyboard and responsive layouts; existing university readability/import/replay.
- Tests cover immutable snapshots/envelopes, success-only preference updates, request-only overrides, safe retries, unknown values, exact receipt bindings/digests/types, rejection/clarification, private reference exports, feedback lineage, result replay/history, unsafe paths/links, request/session/origin/Host checks and original map DB byte preservation.
- Protected production/config/cache, Research Engine, shared importer/exchange fingerprints were checked separately before publication. No production migration, real data transfer, profile/CV work or automatic agent execution occurred.

### Interactive visual review

Relaunch the desktop app, choose Countries, watch Canada and France, select My watchlist and check both for research. Follow the round trip above. Keep the shared-preference edit disclosure closed on the second request to judge whether the summary is compact enough. Try Map/List and history around country selection and Explore universities here. Inspect 150% text and the minimum window; scrolling is expected for larger forms/results.

All screenshots are local and ignored: `2026-10-15-research-watchlist.local.png`, `first-request`, `prefilled-request`, `request-handoff`, `first-results`, `feedback-handoff`, `follow-up-request`, `revised-changes`, `earlier-revision`, `country-result`, `request-mobile-large` and `results-mobile-large` with the same dated prefix and `.local.png` suffix.

### Remaining coordination boundary

APP-007 contains the proposed private and country-envelope formats and asks Marry/Dave about versioning, exact bindings, identifiers, ownership and approved private destinations. Compatibility feedback has not been incorporated into a finalized producer adapter. The current app-owned synthetic adapter intentionally refuses real/custom results. Real research/transfer, private applicant artifacts, live producer readers/writers, deployment, accounts, billing, faculty/outreach and automatic scheduling remain outside this milestone.
