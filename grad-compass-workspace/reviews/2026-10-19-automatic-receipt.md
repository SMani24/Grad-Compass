# Automatic local response receipt — 2026-10-19

The user authorized inbox polling and automatic operational receipt, superseding the earlier blanket polling prohibition. Dave invocation stays manual. The app retains the existing private 0.1.0 bindings and public exchange 1.0.0 contract.

## Delivered behavior

- A managed server worker checks the active local profile's owner-private inbox every five seconds, independent of browser timer throttling. Launch and Requests-open also check. The worker stops with the server; profile switching/reset retain their session boundaries.
- Finalized acknowledgement, partial-result and complete-result transports reuse the existing exact-byte, duplicate-key, scope, request/revision/digest, public-batch and result-lineage validation. New records receive a backup first. Unchanged replay does not duplicate records or create repeated backups. A failed backup prevents receipt.
- Hidden/temporary files are ignored. Recently written files wait briefly to settle; a file that changes during its read is retried. Producers publish complete immutable transports atomically and finalize referenced batches before publishing a result. Stable malformed/conflicting files remain visible as errors and are retried without accepting invalid state. Pending files are recovered on restart.
- Requests show saved, acknowledged, partial-results and results-ready states. Actual reported execution progress is labelled as Dave's report. Receipt preserves agent factual-review and human-approval states and performs no authoritative promotion.
- The map workspace offers **Results ready** and **Review delivery errors**. Requests/findings update automatically. Open feedback drafts and unsent country notes are preserved; a pending draft offers **Show latest results** before replacing it. The accessible map-selection, profile/reset and text-size controls remain available.
- **Copy instructions for Dave** exports/copies the exact already-saved request's reference-only instructions, including that profile's inbox and finalized-delivery convention. It never records acknowledgement. The Qt clipboard uses a session-protected endpoint that only copies regenerated saved-request instructions; arbitrary text is rejected. The existing CSP stays unchanged. Selectable text remains the fallback.
- Manual JSON selection, preview and receipt remain closed by default under **Advanced / recovery: import response JSON**. There is no automatic agent execution, new approval stage, canonical profile/CV transfer, shared importer edit or production/legacy configuration change.

## Verification

- **92 app Python tests**, including nine automatic-receipt groups: acknowledgement/partial/final sequence; replay/restart/pending delivery; hidden/recent/changing files; digest/duplicate-key/unknown-request/conflict rejection; dependency retry/backup failure; periodic worker/profile isolation/shutdown; delivery instructions without acknowledgement; protected canonical clipboard copy; invalid request/prior-revision bindings. Earlier invalid-state and synthetic/real separation tests remain passing.
- **22 unchanged exchange tests**, both JavaScript regression files and syntax checks, and **four Qt input/clipboard checks** pass.
- Marry's two publisher tests pass against the app receiver, including atomic publication, replay, partial-to-complete sequence, restart, temporary-file exclusion, binding rejection and conflict preservation. Producer files were read/tested without app-team edits.
- Native temporary-data review passed copy instructions without acknowledgement, automatic acknowledgement/partial/final display, preserved unsent feedback and country note, visible invalid-file errors, narrow extra-large text, replay and reopen persistence. No agent was invoked for tests. Native removal/profile/reset review also passed all 12 width/text-size layouts.
- An isolated restore of the earlier manually invoked **real** run automatically received its original acknowledgement and complete result through the periodic worker: 38 findings, five institutions and five programs, with exact original transport bytes and inherited reviews/unknown human approval retained. Server/workspace restart preserved everything; replay made zero changes with zero errors. This was an explicitly historical delivery replay, not a new Dave execution. The restored runtime was disposed of afterward; original Personal and Main-Apply data were unchanged by that replay.
- All 146 protected tracked contents match the previous HEAD. Runtime, payloads, sidecars, browser state, logs, captures and coordination mailbox remain Git-excluded. Existing user/producer changes stay outside the app commit.

Local visual captures and the detailed historical-real receipt are under ignored `runtime/inbox-ui-review/`. Reproduce the native invented-data regression with:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/check_inbox_ui.py \
  --screenshots grad-compass-workspace/runtime/inbox-ui-review
```

## Live producer demonstration

The existing Main-Apply request was exported unchanged, and reference-only instructions were prepared for the owner's manual Dave invocation. The normal app is open and checking that profile's inbox. At this verification point, no acknowledgement/result has been delivered for that new request; its execution/results must not be inferred from the historical replay or the owner's acknowledgement of the instructions. APP-012 carries the exact private request reference and the request for Marry/Dave to confirm finalized delivery. The live returned-response demonstration remains dependent on their actual execution/delivery. No response-file relay is requested from the owner.
