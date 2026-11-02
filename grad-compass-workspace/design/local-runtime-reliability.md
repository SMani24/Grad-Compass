# Local research execution and recovery

APP-030. Codex owns the app and local service integration; Marry owns producer
compatibility/private-output handling; Dave owns execution routing and release;
Alex owns independent content/asset review. This uses existing request, result,
report, receipt and task interfaces. Public exchange 1.0.0 is unchanged.

## One controller, explicit runtime

Use Paperclip's native user service, through `grad-compass/scripts/paperclip_runtime.py`:

```bash
grad-compass/scripts/paperclip_runtime.py service status --json
grad-compass/scripts/paperclip_runtime.py service logs --lines 80
grad-compass/scripts/paperclip_runtime.py service restart --json
```

The wrapper refuses planned restarts while any company has queued/running work,
or when that state cannot be verified. On an idle instance it also adds native
`--wait` for orderly finalization. Native draining settles/interrupts legacy work;
it does not promise natural completion of every active execution.
Actual testing showed non-draining restart orphaned this installation's legacy
executions despite a healthy server and empty native lost-run list. Do not infer
legacy adoption from service health or test it repeatedly on real research.
Do not start a separate
`npx paperclipai run` against the same instance. It can resolve an older bundled
Codex and fall forward to another HTTP port while sharing the same database.
The bootstrap refuses an occupied configured port before starting the native
controller. Verify the listener is the expected port and process after maintenance.
Do not interpret a healthy alternate port as the app's configured connection.

The owner-private `runtime/paperclip-service/launch.local.json` pins existing Node,
Paperclip entrypoint, instance config, app connection port and Codex home. Optional
allowlisted existing proxy/client settings preserve the working execution route;
no account tokens or model substitution are stored here. The bootstrap prepends
the chosen Node bin directory, applies umask 0077 and disables automatic doctor
repairs. Existing agent credentials/connection permissions remain authoritative.
An unavailable pinned executable is an explicit maintenance failure, not permission
to download or select another provider. Revalidate paths and native saved-agent
tests after any CLI/cache maintenance or upgrade.

The native systemd user service starts at login and restarts stopped controller
processes subject to its bounded start limit. Logout persistence/linger is not
enabled. Machine shutdown pauses local execution. No actual reboot is claimed by
a service restart check. Local service health alone does not establish agent/model
readiness, complete research, factual acceptance or delivery.

## Preflight before task creation

`web/storage_health.py` checks the approved profile's owning store without opening
applicant documents or repairing access. For the existing frozen-store layout it
checks the same seven guarded areas as the producer: intake, profiles, reviews,
cache, sources, candidates and frozen. Adjacent CV output policy is unchanged.
Unexpected ownership, symlinks/hard links, additional ACL grants, unreadable paths
and non-private permissions fail closed. The producer still independently validates
the exact canonical profile, human approval and request binding.

With `runtime_preflight: true` in a profile's private Paperclip connection, an
explicit dispatch also invokes Paperclip's supported saved-Dave environment probe
using his existing selected AI connection. It requires a successful configured-
model hello check, not merely a listening server or a cached model catalogue.
Raw probe/account diagnostics stay out of browser errors. A rejected or unverified
probe retains the immutable request as pending and creates no task. The user can
review/retry that same saved request after maintenance. An unavailable reference
at initial confirmation still requires reviewing a new draft revision with its
actual approved reference; no approval is inferred from repairing storage.

An uncertain earlier dispatch reconciles the exact accepted task first. Recovering
that receipt does not require another model probe or resend. The existing
company/idempotency transaction, private durable outbox, seven-day uncertainty
boundary and explicit retry policy remain in force. App open/reconnect never
creates a new research task.

## Persisted progression and ownership

| Stage | Required evidence | Continuation and recovery owner |
| --- | --- | --- |
| Confirmed request | Immutable request/reference/destination and durable dispatch key | App creates once after preflight; uncertain acceptance reconciles exact existing key/task. |
| Preparation | Verified approved profile/request reference; exact private editions and source mappings | Dave routes existing preparation; researcher preserves ready inputs. Dependency recovery belongs to its assigned technical owner. |
| Photograph | Bound finalized job and immutable byte/provenance receipt | Existing app asset worker resumes pending retrieval/callback after reopening; no repeat completed download. |
| Independent review | Actual exact-content/asset dispositions | Alex; corrections create new immutable versions, retaining earlier annotations and review history. |
| Release and delivery | Dave's actual exact-candidate release, validated package and finalized notices | Dave answers agent-owned release interaction; Marry publishes and checks actual app receipts/replay. |
| Receipt and inspection | Existing exact-byte inbox validation and selected report identities | App recovers finalized pending responses on open; execution completion remains separate from content/human review. |

Native task dependencies and saved interactions are the executable continuation
mechanism. Comments convey new evidence; repeating a waiting comment is not a
progress transition. After successful repair, the verifier records actual readiness
and the question's requester resolves/withdraws a satisfied gate through supported
controls. Never fabricate an owner answer, release or factual acceptance. Agent
run success can mean a blocker was documented, not that the request was fulfilled.

## Boundaries and acceptance

An owner-approved single historical review permission defect can be repaired by
the authorized maintenance operator without altering content or approval records.
No blanket chmod, automatic ACL removal, profile rewrite or agent permission
override is part of this implementation. Private writers must set restrictive
modes explicitly or inherit the service umask; the producer owns writer guidance.
Unknown security conditions remain real escalations.

Connection loss preserves last-known observations. Delayed progress is not a
confirmed failure. Real provider quotas are respected; no account rotation, model
substitution or unbounded retry is introduced. Existing durable Requests notices
retain stage, saved work and supported action. Historical attempts remain intact
after actual recovery and must not restore obsolete active warnings.

## Bounded administrative continuation

The normal app's managed status worker also runs `web/execution_recovery.py` after
fresh GET observations. It only continues an existing accepted exact-bound task
whose current run is explicitly interrupted with `orphaned_running_run`. It
verifies same-company request ancestry, current assignee, approved reference,
absence of open dependencies/questions/other recovery or scheduled retry, and
native runtime readiness before sending the supported same-task `resume:true`
input. Completed/cancelled tasks, generic adapter failures, model denial, quota
limits and substantive review/research failures never qualify. A resolved
decision permits reevaluation; it is not answered by this worker.

The profile-private durable ledger `execution-recovery.json` reserves each
attempt before mutation and retains receipt/history in backups. Deterministic
comment identity and receipt reconciliation recover lost acknowledgements.
The private connection explicitly opts in with `automatic_recovery_after`, an
activation timestamp, and `runtime_preflight: true`. Earlier historical failures
are not swept into the new policy. Each recovery probes the actual assigned
agent's selected runtime/account; new request dispatch probes Dave. Native
attempt limits also stop automatic continuation.
There are at most two administrative continuations per task and two transport
attempts per event. Reaching a bound exposes a concrete inspection action; no
new request or automatic account/model/permission change occurs. Multiple app
windows share an exclusive process lock. Local workers pause when the app closes
and reevaluate pending work after reopening; the Paperclip service itself remains
independent of the window. Actual review/release gates remain authoritative.

Focused isolated suites cover permissions, runtime/model rejection before create,
lost acknowledgement, concurrent dispatch, expired uncertainty, closed-app inbox
recovery, invalid/replayed responses, binding/isolation, offline callbacks, rate
limits and recovery versus historical failures. Real acceptance reuses Singapore's
existing request; capture actual prepared reports/receipt, normal desktop/restart,
duplicate-free replay and preservation before claiming that request fulfilled.
One successful request proves this path, not universal failure-free autonomy.
