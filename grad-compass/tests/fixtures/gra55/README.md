# GRA-55 synthetic handoff fixture

This fixture supersedes the app-local canonical-field-digest example reviewed at `9bfe9c6`. All text, people/owner IDs and country evidence are invented. Institution/program associations refer only to the existing finalized synthetic exchange 1.0.0 example; they grant no import or factual acceptance.

`manifest.json` lists the six immutable UTF-8 envelopes in execution order and each envelope's exact-byte SHA-256. The manifest's own SHA-256 is:

```text
5dbb194c34e24550ee3c14fc8c0d73edf5c22da10dd4d0e25c0e969310d385d0
```

| File | Role |
| --- | --- |
| `request.json` | Request r1 with complete preference snapshot, explicit nulls and no applicant profile contents. |
| `acknowledgement.json` | Explicit accepted acknowledgement bound to request ID/revision/exact-byte digest. |
| `result-1.json` | Partial response with country findings and separate public record associations. |
| `result-2.json` | Complete scoped response, retaining unknowns, with exact prior result revision/digest and revised country/finding/source records. |
| `feedback.json` | Feedback on result r2 and its exact finding revision; it does not change preferences or evidence. |
| `refresh.json` | New request bound to the exact parent request and prior result/finding revisions; its own snapshot remains immutable. |

The manual transport agreed with Marry is `{body, sha256}`. `body` is the envelope's original UTF-8 JSON text, including its final newline; `sha256` is outside those envelope bytes. A file reference or this manifest carries the digest. There is no self-digest in any envelope. The app persists the transport without changing its body, exports those body bytes directly with a separate `.ref.json`, and validates byte hashes before strict JSON decoding. JSON formatting of the external reference is not part of the envelope digest; its duplicate keys are still rejected. An HTTP `{envelope: {body, sha256}}` receipt does not accept reserialized or changed pinned envelope bytes even if their digest is recomputed.

Wire names use `schema_version`, `request_revision`, `country_codes`, `preference_snapshot`, `acknowledged_at`, `issued_at`, `result_revision`, `previous_result_revision` and `previous_result_digest`. Each `prior_results` element uses `result_id`, `result_revision`, `result_digest`, `finding_id`, `finding_revision`. UI response aliases such as `revision`/`digest`/`preferences` and `_transport` are presentation metadata; they are absent from exchanged envelope bytes.

Country findings include stable country/finding identities and revisions, a typed `finding_ref`, evidence status/coverage/unknowns, source identity/revision, HTTPS source and page locator, UTC observations, and an agent factual review bound to the exact record/finding revision. Agent review is pending. A separate revision-bound human approval is **not requested**. A complete scoped result does not imply known facts, accepted evidence, human approval, a personal shortlist decision or operational promotion. Non-ISO territory aliases require separate mapping and are refused by this synthetic handoff.

Public associations use the actual validated synthetic batch manifest and institution/program record revisions, including the program's parent institution. They remain private associations, outside the unchanged exchange 1.0.0 schemas. Receipt never stages or promotes a batch.

From the repository root, reproduce and compare every committed byte without changing the fixture:

```sh
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/build_research_fixture.py
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass/tests -p 'test_research*.py' -v
```

The builder executes the sequence through the real app store in fresh disposable storage with fixed synthetic IDs/time. `--write` deliberately regenerates the example; a changed example needs a newly named revision and independent review. No existing runtime, production DB/configuration, applicant artifacts or producer files are used.

Focused tests reject changed bytes/serialization, duplicate keys in envelopes/references/uploads/HTTP, invalid UTF-8/non-finite JSON, wrong versions or real scope, invalid/terminal transitions, wrong parent/request/result/finding bindings, stale review/observation/source metadata and incorrect public record associations. Legacy app records retain their original bytes and digest interpretation; they are read-only history rather than corrected-contract inputs.
