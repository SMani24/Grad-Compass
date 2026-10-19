# Local response inbox contract

This is the owner-private local workflow for a saved Grad Compass request. The applicant saves a request and copies its instructions to Dave; Dave is invoked manually. Saving or copying is not an acknowledgement. The application never invokes an agent.

Each exported request is `PROFILE/research-handoff/request-REQUEST_ID.json`, with a matching `.ref.json` holding its exact SHA-256. Its response destination is **that same profile's** `PROFILE/inbox/`. The profile is the parent of `research-handoff`; do not use a hard-coded global inbox or a different profile. No applicant profile, CV, private source document, or credential belongs in a response, comment, or public artifact.

Dave's execution should publish each completed acknowledgement, partial result, and final result as soon as it is ready. The response must be an exact-byte `{ "body": "...", "sha256": "..." }` JSON transport. `body` is a UTF-8 research envelope with `schema_version: "0.1.0"`, `synthetic: false`, and the saved `request_id`, `request_revision`, and `request_digest`. An acknowledgement states `accepted`, `rejected`, or `needs_clarification`; accepted acknowledgement precedes results. Results use `completion: "partial"` or `"complete"`, and each later revision binds its predecessor's revision and digest. Preserve actual factual review and human approval states; receipt alone grants neither.

After composing and reviewing an existing transport file, publish it as an execution step:

```sh
grad-compass/envGradCompass/bin/python grad-compass-research-engine/scripts/publish_local_response.py \
  --handoff 'PROFILE/research-handoff/request-REQUEST_ID.json' \
  --response 'OWNER_PRIVATE_COMPLETED_TRANSPORT.json'
```

Run from the repository root; replace the two quoted arguments with real owner-private local paths. The command reads the matching saved request and reference, validates the completed response against the operational app contract, and writes a unique `response-…json` file to that profile's inbox. It writes through a hidden `.tmp` file, flushes and syncs it, then publishes an immutable name with an exclusive link. Repeating the same command with identical bytes reports `Already published`. A conflicting response remains visible as an inbox error for investigation. The publisher never imports a response into the app directly and never fabricates an acknowledgement or result.

Finalize any referenced public exchange batch under the same profile's `batches/` before publishing its result. The app checks the inbox on open, on Requests open, and periodically while running; it ignores hidden unfinished files and validates completed packets against its saved request and batch records. It keeps the received state in the local database, including across restart. Manual JSON import remains an Advanced recovery path. If the app reports an invalid packet or conflict, Dave should correct the producer artifact and publish a new, valid transport without editing the existing finalized file. A wrong-profile request/response pairing is rejected.

## Operational limit

Dave must still be manually invoked and must execute this publication step for every processed response. There is no background research executor or remote delivery service. The owner-private paths must be accessible to Dave's actual execution environment; copying instructions alone does not verify that access or trigger delivery. If Dave cannot access that path, pause the execution handoff and resolve the access boundary with the owner without copying private material into a shared channel.
