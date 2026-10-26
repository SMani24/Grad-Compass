# Requests, execution observations and recovery

APP-022, 26 October 2026. Codex owns application code and private observation storage. Dave owns execution routing and coordination; Marry owns producer compatibility and delivery; Discovery owns research, Alex exact-content review. Public exchange 1.0.0, research transport 0.1.0 and report-package compatibility stay unchanged.

## Independent authorities

| Concern | Authority |
|---|---|
| Confirmed scope, preferences and lineage | Immutable app request/export |
| Task creation receipt and unsent attempts | Per-profile dispatch outbox |
| Current execution, blockers and recovery capability | Supported Paperclip issue/execution projections |
| Accepted research acknowledgement and findings | Bound, validated private inbox transports |
| Prepared report availability | Validated request-bound report catalogue |
| Factual review and human approval | Exact content-version receipts; never inferred from task status |

An accepted task remains in **All requests** even when it leaves Pending dispatch. Manual historical requests also remain visible; their task association is never guessed by country or title. Accepted request editing requires an explicit amendment, preserving earlier scope/history. Existing request bindings are not rewritten to correct a suspected country-name mistake.

## Status reads and persistence

`web/request_tracking.py` consumes GET issue, issue/execution and issue/runs. It follows only explicit blocker identities in the bound task's company. Root task ID, company, assignee, exact marker line and parsed immutable request/profile/destination bindings must agree. Run rows require exact `contextIssueId`, agent and current run identity. Related or successful sibling runs cannot conceal the failing step.

Only allowlisted execution/attempt/recovery fields reach the browser or `request-tracking.json` (`grad-compass-request-tracking-1`). Raw stderr, logs, descriptions, credentials and applicant-profile content are excluded. Recognized structured, exact-run system diagnostics map to safe application wording. Optional privileged diagnostic failure cannot hide a confirmed execution failure. Unreadable steps retain their last known observation.

The app checks on startup, when Requests opens, on returning to the app, through explicit Refresh status and a 60-second server timer. These are **GET-only** operations against Paperclip. A five-second browser read displays the private cache. Refresh operations coalesce locally; network reads do not hold the workspace state lock. Each profile owns its cache, observation history, dispatch events and backup copy. Restart/reconnection never invokes research.

Failed refresh records last attempted and last successful check separately, preserving the last known state. A network timeout is not confirmed execution failure. Thirty minutes without reported activity produces an explained delay, not a terminal conclusion. A Paperclip scheduled retry remains distinct from an exhausted failed step. A completed orchestration run does not imply research, delivery or report completion.

Inbox errors associate with a request only through an existing request identity parsed from the envelope, never its filename. Validation is still required for acceptance. Current delivery errors and their resolution observations persist without deleting or rewriting original transports/results. Unknown malformed files remain visible as unassociated problems. Findings received and prepared editions available are separate labels; per-country review details retain actual dispositions.

## Safe recovery boundary

Unaccepted requests retain review/edit/confirm/reconcile/cancel. Lost dispatch acknowledgements use the existing atomic idempotency and retention rules. Accepted entries have no create/retry-dispatch control; the saved-request reader links to current execution/recovery instead of inviting another manual invocation of the original request. Follow-ups remain separate explicit requests with lineage and confirmation.

Marry's GRA-114 compatibility readback verified the read APIs, but did **not** establish a conditional exhausted-run retry endpoint with expected-run/action enforcement, fine-grained caller gates and an atomic one-active execution guarantee. Therefore the supported accepted-task action is **Resume / recover in Paperclip**, linking the exact failing step through the producer-confirmed company-prefixed route (for example `/GRA/issues/GRA-111`). Bare UUID aliases are not assumed. It requires the operator's explicit decision through Paperclip's current recovery interface; the app cannot bypass trust setup, usage budgets or human-only reconciliation. The recovery link is not proof of runtime repair or resumed execution.

Do not activate an application POST recovery adapter until Marry verifies those guarantees and the exact caller/capability contract. A generic status mutation, agent wake, duplicate issue or new country request is not a substitute. Execution failure details and saved-work inventory belong with the task; Dave coordinates the named operator, Marry supports runtime diagnosis/delivery, and the existing producer/review/release gates remain.

## Checks

`tests/test_request_tracking.py` uses actual urllib against isolated fake HTTP: later failure, unavailable service, delayed updates, scheduled versus exhausted retries, optional diagnostic denial, malformed status, wrong bindings/agent/context, restart, missing delivery repair, successful report receipt, history/backup/profile isolation and lost acknowledgement. Existing dispatch process-contention tests preserve one task. `scripts/check_request_tracking.py` requires marked disposable storage or explicit Main-Apply owner mode; owner checks preserve original records/overlays and never invoke an agent. Normal-desktop screenshots and actual request identities stay in Git-excluded runtime evidence.
