# Request execution without routine owner intervention

APP-029, 1 November 2026, Asia/Tehran. This implements the missing local public
asset operation; it does not grant an agent broader network or filesystem access.
Codex owns the app/service/helper; Marry owns producer compatibility/submission;
Ali owns research and asset provenance; Alex reviews; Dave coordinates and releases.

APP-030 adds the [local runtime reliability rules](local-runtime-reliability.md):
one native supervised controller on the app's existing port, pinned execution
environment, restrictive private-output umask, read-only storage preflight and
the supported saved-agent model probe before new task creation. Existing accepted
task recovery and receipt remain separate from new dispatch and factual review.

## Normal sequence

1. The owner explicitly confirms one bounded request in the app. The accepted
   outbox stores exact request/revision/digest, approved profile reference and task.
2. Dave routes preparation, asset acquisition, independent review and transport
   on existing request-bound tasks. Preparation readiness is independent of review.
   Ready findings/text must not wait for photograph acquisition where authorized
   partial receipt or independent text assessment is available.
3. Ali supplies an identified public original, source/license URLs, creator,
   license, caption and alt. Marry uses `scripts/enqueue_country_asset.py` against
   the existing handoff/task/exact assignee. No human upload or connection-discovery
   approval is needed for this app-owned operation. Source identity/rights are
   supplied evidence, not automatic app acceptance.
4. The normal app's managed worker reads finalized private `asset-jobs/requests/`
   packets. It validates exact request, country, company, parent and assignee;
   restricts network I/O to enumerated HTTPS image origins without redirects;
   limits bytes, image dimensions and time; and retains original bytes plus receipt.
5. A durable idempotent outcome event goes to the same existing asset task. The
   worker creates no issue or agent, invokes no research/retry endpoint and never
   releases content. Existing accepted execution continues from its new input.
6. Ali verifies exact bytes/provenance; Alex records independent exact dispositions;
   Marry validates immutable integration. Dave answers the existing agent-addressed
   exact release interaction promptly. No wait for publication needing that release.
7. Marry publishes normally. The app receives report/result notices automatically.
   Receipt/replay, preparation, coverage, factual review and human approval remain
   separate. No per-country developer-chat or desktop-test gate for unchanged data.

## Recovery is part of the protocol

The app must be running for retrieval and response receipt. Jobs pending while
closed resume on open. Paperclip unavailability queues task validation or outcome
notification; it does not mean research failed. Outcome delivery reconciles the
saved marker before resend, with deterministic request ID. Successful originals
are never re-downloaded; a restart recovers bytes written before their receipt.
Multiple app windows share an exclusive job lock. No network operation holds a
profile-transition lock, and a captured workspace never writes into another profile.

A source 403/429 is a terminal outcome for that job. Preserve its actual failure;
Dave/Ali choose an independently licensed alternate through the same helper and
existing task, without rotating credentials, bypassing limits or repeating the
denied URL. A request-country admits at most three candidates. A crashed retrieval
has at most two recorded attempts; ordinary HTTP failures are not automatically
retried. If all permitted routes fail, the app keeps a specific visible stage,
failure, owner and action. The system cannot promise remote hosts never fail.

Historical access questions are withdrawn by their requesters once real capability
and bytes resolve them. No fabricated human answer. New authority, privacy or
material applicant questions still escalate; known supported operations do not
require the owner to relay files. Explicit runtime restrictions remain in force.

A structured `provider_quota` stop is a provider-usage pause, not lost research or
another failed asset transfer. Keep the accepted request and all completed inputs;
Dave resumes only the interrupted existing step once the provider permits it.
Use a supported scheduled retry only when real provider policy/reset information
permits it. Never invent a reset time, bypass quotas, rotate accounts or run an
immediate retry loop. The app persistently names this condition after restart.

A pending interaction explicitly addressed to an agent with an agent-permitted
resolver policy is ordinary team progress, not a demand for owner supervision.
Requests distinguishes that wait from human-only gates, unreadable/unknown gates,
actual execution failures and prolonged lack of progress. This changes no review,
human approval, release or execution permission; only the displayed work state.

## Verified same-task handoffs

APP-032: Russia preparation finished but its readiness comment did not resume a
self-blocked delivery coordinator whose execution projection still selected an
older cancelled run. Resuming only the researcher was insufficient. A successful
same-task continuation with structured `resume: true` started the coordinator,
which validated the prepared inputs, published the existing result and verified
actual automatic receipt before routing independent review. No research was repeated.

For each prepared-input handoff, the responsible coordinator must inspect the
target's current assignment, questions, dependencies, recovery and live execution.
If a stopped or self-blocked existing target is permitted to continue, use its
supported same-task structured resume input with deterministic identity and verify
both input receipt and the native run claim/current execution. A comment or a
successful earlier run alone is not proof that the next stage started. Reconcile
an uncertain acknowledgement before resending; never interrupt an active run or
blindly retry a denied transition. A genuine human, review, release, provider or
dependency gate remains in force and must yield its exact error/owner/action.

Preparation closure must not be a prerequisite for a coordinator's receipt when
the preparer is waiting for that receipt. Keep independent review, release and
final publication as distinct actual transitions. Dave owns continuation routing;
Marry owns exact validation/publication/consumer-receipt evidence. Codex owns app
display and future generated handoff wording. The app adds no background agent
invocation and does not manufacture completion or acceptance.

The displayed stage prefers a genuinely working coordinator/reviewer over an
idle deeper preparer. Actual failed/recovery states and unanswered decision gates
retain priority. A normal team wait is not a new failure; prior attempts remain
in history. Verify automatic receipt and the next claimed stage, then final
publication and request completion before claiming end-to-end recovery.

APP-033: when multiple steps are stopped, an actual execution failure (including
provider quota) takes display priority over an administrative assignment-change
cancellation on another step. The cancellation remains available in history and
still needs reconciliation if it is not superseded; it is never automatically
treated as successful delivery. Stage priority changes no native task/run state,
review, approval or retry permission. A transient SQLite read lock is separately
rechecked through a bounded read-only receipt lookup before claiming receipt is
missing. Existing finalized packets must never be republished or imported directly
merely because the first receipt query was busy.

Paperclip can also select an unstarted `issue_assignee_changed` notification run
addressed to another agent after the actual owner's successful run. The consumer
reconciles that cancellation only from exact same-task/run/agent identities,
explicit `startedAt: null`, matching cancelled status/error, the current owner's
latest completed successful run and readable interaction records. Real newer
owner failures, unknown/live attempts, active recovery and pending human/unknown
gates reject this reconciliation. The raw cancelled run remains in history;
outstanding task/review/approval states still govern progress and completion.
Closed-task cancellation rules cannot bypass current-owner verification.
Reconciliation of that notification never marks an open request root complete,
even when reports are already available; tracked fulfilment still requires the
root's actual completed state.

## Private files and exact bindings

`web/asset_jobs.py` defines `grad-compass-asset-job-1`. The helper finalizes
`{body,sha256}` using original UTF-8 bytes and a stable UUID derived from request,
country and URL. Required body fields: schema_version, job_id, request, country_code,
task_id, assignee_agent_id, asset, created_at. The asset contains original_url,
source_url, license_url, creator, license, caption and alt. Finalized input changes
are conflicts, not updates. Use the helper instead of constructing IDs by hand.

The worker verifies current accepted root binding and its assigned direct child
before retrieval/callback. Current supported download origins are
`images.pexels.com` and `upload.wikimedia.org`. Other references are not fetched by
this service. No general-purpose HTTP endpoint is exposed. Originals are limited
to 12 MB, 40 million pixels, JPEG/PNG/WebP; redirects and nonstandard ports are denied.

`asset-jobs/jobs/JOB/state.json` retains attempt history. Successful `receipt.json`
binds exact input/asset/original hashes and dimensions, with `original_path` relative
to the owning profile. `event.json` retains callback disposition. Backups include
jobs/receipts/originals and skip unfinished hidden files. All data is Git-excluded.
Existing result transport, report package 0.2 and public exchange 1.0.0 are unchanged.

## Acceptance

Isolated tests cover normal retrieval/event, replay, restart, interrupted writes,
offline task validation, lost callback acknowledgement, access/rate-limit denial,
malformed bytes/digests/duplicate keys, cross-profile/scope/assignee bindings,
concurrent windows, image limits, tampered original/receipt and backup recovery.
The actual existing Sweden request proves automatic service-to-agent-to-publication
continuation; fixture work remains in disposable stores. Keep actual receipts and
remaining blockers distinct from readiness or documentation claims.
