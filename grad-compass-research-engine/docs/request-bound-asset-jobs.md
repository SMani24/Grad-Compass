# Request-bound country asset jobs

For future confirmed requests, use the normal app asset-job path for required public originals. This is the ordinary producer workflow, not a chat recovery service. Codex owns the app service, worker, helper, tests and design; Marry owns producer submission; Ali supplies candidate metadata and verifies delivered bytes; Alex independently reviews; Dave owns exact-version release.

From the repository root, run:

```sh
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/enqueue_country_asset.py \
  --handoff 'PROFILE/research-handoff/request-REQUEST_ID.json' \
  --country COUNTRY --task EXISTING_ASSET_TASK_UUID --assignee-agent ASSIGNED_AGENT_UUID \
  --original-url ORIGINAL_HTTPS_URL --source-url SOURCE_HTTPS_URL \
  --license-url LICENSE_HTTPS_URL --creator CREATOR --license LICENSE \
  --caption CAPTION --alt ALT
```

Replace placeholders with the accepted request's existing saved handoff and verified candidate metadata. Never invent rights or identity metadata. The helper validates exact handoff/ref bytes and country scope, binds the request revision/digest and named task/assignee, derives the stable UUID, and atomically finalizes the same profile's `asset-jobs/requests/JOB_UUID.json`. The app worker verifies the actual remote company, direct parent and exact assigned agent before network I/O. Use the helper, never hand-write IDs or packets. The sole schema is `grad-compass-asset-job-1`; body keys are `schema_version`, `job_id`, `request`, `country_code`, `task_id`, `assignee_agent_id`, `asset`, `created_at`. The app source is authoritative for limits. Identical replay preserves finalized bytes; conflicting finalized metadata is rejected.

Read back `{body,sha256}`, hash exact UTF-8 body bytes, and verify request/task/assignee/country and filename bindings. Asset packets never belong in the report inbox. Only the normal app worker retrieves originals; producers do not download, change permissions or bypass denied sources. Supported download origins initially are `images.pexels.com` and `upload.wikimedia.org`. App closed jobs resume on open; offline validation/callback waits for reconnect. A genuine denied-source outcome is terminal: retain its evidence, never repeat that URL, and select one independently licensed alternate on a supported origin within the existing asset task when authorized.

Record actual state or failure stage/cause and next owner/action. A successful immutable `receipt.json` supplies `original_path` relative to this profile root, original digest/size/image and supplied provenance. Verify those exact bytes before provenance/visual acceptance. Reconcile uncertain callback delivery before resend; completed originals must not be refetched. Retrieval is not rights acceptance, factual approval, independent review or release. Keep applicant data and credentials out of packets and shared artifacts. Preserve existing request, task, profile, result lineage and approval gates.
