# APP-022 — request tracking and recovery

26 October 2026. Reopen the normal Grad Compass launcher, keep Main-Apply selected and open **Requests** in the top bar. All requests includes saved, dispatched, failed, completed and cancelled history. Pending dispatch is a filter, not the entire history. Reports & findings remains the reading workspace.

## Observed diagnosis

The latest actual app-dispatched request in this workspace is **France**, not Spain. Read-only inspection of both registered profile stores, dispatch outboxes, the current draft country selection and Paperclip issue search found no Spain request. The naming discrepancy was raised with the owner; no request was relabelled or recreated.

For the existing failed request, task creation and Dave's delegation succeeded. The bound accepted acknowledgement was delivered and imported. The researcher then failed to start because its working directory was not trusted; two scheduled retries also failed, exhausting three attempts. The structured execution projection records a failed step and board-owned recovery. This was an execution setup failure, not an unavailable app connection, rejected result import or lost acknowledgement.

Marry independently verified one saved request, one acknowledgement and zero results, with no matching brief/editions/package in the inspected stores. Broader producer-private locations remain unverified. Older France reports bind another request and cannot be silently reassociated. Original diagnostic receipts, exact identities, review inventory and screenshots remain in the Git-excluded private evidence index.

The app previously observed only the initial task receipt. Its Pending label/count covered unsent dispatches and did not track subsequent execution. It also depended on a late initialization event for that shortcut. The new persistent tracking path observes accepted tasks independently and initializes on workspace load.

## Working user flow

- Requests shows country, scope/intake, created/updated/check times, current step, saved-work count, report availability and available actions. Search and All / Needs attention / Pending / In progress / Reports available filters retain the full underlying history.
- Failed execution produces a persistent map notice and request entry, with safe explanation, saved-work status, exact task/recovery links and expandable observed attempts. Last-known state survives restart. Unavailable status refresh and prolonged lack of progress are explained separately from confirmed failure; scheduled retries are distinguished from exhaustion.
- Refresh status performs only supported reads. Inbox receipt remains automatic. Request-scoped delivery failures and their resolution observations are retained. Prepared reports, source review and human approval remain separate from execution or response completion.
- Unaccepted work retains explicit review/edit/reconcile/retry/cancel. Accepted work links to the exact existing Paperclip recovery step through its company-prefixed route. The original reader no longer invites a second manual dispatch of a recorded app request; explicit follow-ups retain lineage and confirmation.

## Recovery limitation and ownership

Dave/Marry's GRA-114 readback did not verify a safe conditional exhausted-run retry API or one-active execution guarantee. The app therefore offers **Resume / recover in Paperclip**, with instructions and named ownership, rather than a speculative recovery POST. A Paperclip board operator must repair the assigned workspace using supported configuration and preserve trust checks, then explicitly choose capability-checked recovery of the original owner. Dave coordinates, Marry supports diagnosis/delivery, Discovery researches and Alex reviews. No trust bypass, usage reset, duplicate request, recovery decision or real agent invocation was performed by these checks. Runtime restoration remains unresolved; app visibility is not a claim of research recovery.

Contract/ownership: [request-tracking.md](../design/request-tracking.md). Existing public exchange, research transports and immutable reports remain compatible.

## Verification

All 189 Python regression tests (including 13 request-tracking tests) and 19 JavaScript checks pass. Tracking tests cover later failure, unavailable service before/after observation, lost acknowledgement, delayed progress, scheduled/exhausted retries, wrong task/run/agent/context, optional privileged diagnostic denial, malformed status, restart, missing delivery repair, successful report receipt, backup and profile/session isolation. Exact counts and named revision are also recorded in the private index and APP-022 handoff.

Normal Qt desktop checks cover accepted failure → offline retained notice → second-process restart → resumed status → delivery error → final report receipt, with one fake task and no real agent. Main-Apply checks preserve existing request/result/dispatch bytes, personal overlays and original report/inbox/handoff files, while recording the actual failed request and recovery link. Wide and 390px/150% layouts are inspected. Screenshots, private diagnostic identities and machine receipts: `grad-compass-workspace/runtime/request-tracking-review-2026-10-26/review.local.md`.
