# APP-018 reconciliation with Main-Apply

Date: 22 October 2026, Asia/Tehran. Implementation: `9ece7eeaacf0c802fb990e91841e9ce96b3712e6` (`Fix prepared report navigation`). This qualifies the earlier APP-018 completion record; the older messages and artifacts remain unchanged.

## What was actually present

Read-only inspection used active profile **Main-Apply**, storage `2f78c20c-9d04-410a-ad2c-c533160a5918`, and SQLite `mode=ro`. Catalog retention writes were disabled only for the initial inspection. Before changing app code, exact file hashes/timestamps and all five errors were preserved outside the profile in `runtime/app018-reconciliation-2026-10-22/before-inventory.local.json` and `before-catalog.local.json`.

Germany and Canada packages were already finalized, correctly bound, validated and received in this actual profile. They were not confined to disposable copies, rejected by the importer or hidden by stale catalog state:

| Country | Existing saved request | Bound response | Received metadata SHA-256 | Current selection |
| --- | --- | --- | --- | --- |
| Germany | `74c2ad44-3ab4-4646-b21f-e65417ac048e` | r2 | `7c16b4c1c2bc1bb178c18ddc9a074adba482fd0439a01018aa8b274e5fd9215e` | Report v3, reader r3, full canonical v3 |
| Canada | `648f0137-a074-4173-a4ab-15be6c7dcdc3` | r1 | `357ddfd68c29a3327815f40a812900b8417e7a2565db0b2c1aac0d29a7fd15e4` | Report v3, reader r3, full canonical v3 |

Each finalized package is under `reports/COUNTRY/deliveries/METADATA_SHA/metadata.local.json`; its `inbox/report-METADATA_SHA.json` notice and `report-receipts/METADATA_SHA.json` exist and bind the original request revision/digest. Canonical/reader exact digests and review records validate against those saved results. Both prepared report and overview factual dispositions are **accepted**, within the supplied country-conditions/finding-level scope. Canonical human approval remains Germany **unknown**, Canada **not_requested**; original inbox findings remain pending. No institution/program research or human approval is inferred.

The discrepancy was a request-selection bug. A newer request, `648f0137…`, includes Australia, Canada **and Germany**, but its Germany content has only received findings. Ordinary Germany navigation selected that newer request and never reached the prepared report on `74c2ad44…`. The prior native check opened the prepared request directly and missed the everyday country route. Rebinding the prepared package to the newer request would have been incorrect. Marry independently confirmed the same saved bindings and selection gap in APP-018; no new producer package, publication or research request was needed.

## Five attention items and their disposition

These were five catalog artifact errors displayed by the inbox indicator, not five rejected Germany/Canada responses. Their original files, bytes, timestamps and errors are retained.

| Item | Original error | Verified disposition |
| --- | --- | --- |
| `reports/BEL/maps/map-r0003-120e061a951c-pending/metadata.local.json` | `Unknown private report package version` | Separate map-sidecar bookkeeping was incorrectly scanned as a canonical package. Its safe filename, exact bytes, document identity and canonical/map bindings now validate as a reference-only artifact. Its own pending review remains pending. |
| `editorial-cache/0194844355ef92544c2b55ec75808d0eff5c60d05714fccf135a0d3ed50c3c6d/395c30543ee6a9de859b732260b21a4ae0a81baaf982892aa4134b2afdd2e41a/metadata.local.json` | `Editorial edition must bind the exact country, canonical parent and evidence map` | Retained Belgium reader r2 is valid against its original map r2. It is historical, not the selected reader r3. |
| `editorial-cache/0194844355ef92544c2b55ec75808d0eff5c60d05714fccf135a0d3ed50c3c6d/d0d486aa1e0d592c1f9ea8b8aa0900b3d2e2990f3661e9c34e075fc07f290809/metadata.local.json` | Same exact binding error | Retained detailed r2 is valid against its original map r2; preserved as history. |
| `reports/BEL/editions/detailed-r0002-6941ccd2f536-reviewed/metadata.local.json` | Same exact binding error | Producer copy of that valid historical detailed r2, checked against its own retained parent/map. |
| `reports/BEL/editions/reader-r0002-5f986e0119d7-reviewed/metadata.local.json` | Same exact binding error | Producer copy of that valid historical reader r2, checked against its own retained parent/map. |

The four r2 editorials bind canonical r3 `deb51ad6-cc82-4b94-8d5c-3e16a36b8f17` and map r2 `02d15cea-7e46-427c-bef3-0b452763a9f5`, SHA-256 `c1ccc4cbbc85620806fd49df23ff729b8f46de23d2dbeb195b321796931e2d38`. Earlier received metadata `2408f3f2988c81760671dea66dac97edf51be8e0b4a39c9c1fd894b7c6679536` retains that context. The updated map r3 legitimately changes the map binding without changing canonical text. Validating every older editorial against the current map was the bug.

Historical validation now resolves the full country/canonical/map tuple. An unknown tuple, changed digest or corrupt historical file still raises a diagnostic. Focused rejection tests prove that classification does not merely suppress warnings. Original annotations, citations and pinned exports use the historical map context; mixed-map export pins are rejected. The reference-only map sidecar is not promoted into a factual acceptance record. Current Main-Apply inbox checks report **zero errors**, with **zero new research records** on replay. Exact per-item readback is in private `attention-dispositions.local.json`.

## Everyday selection and reader changes

Country cards, the primary country action, the report country selector and the default Requests entry point use available prepared reports, with their actual source request. Explicit request/result history remains exact. Within a saved request, ordinary reading prefers the latest valid prepared package, while explicitly choosing r1 still opens r1 findings. A historical/other-request findings view can return directly to an existing prepared report without opening a new request composer.

The reader identifies its saved-request reference, response revision and editorial revision near the report title. A compatibility view reports **Received findings loaded for this saved result**, never “Original canonical report loaded.” Generated `Finding field: …` labels are inside collapsed Finding metadata details; original projection bytes and passage identities remain intact. Source dialogs use the selected document’s own evidence map.

## Actual Main-Apply acceptance

`grad-compass/scripts/check_main_apply_reports.py` opens the normal Qt reader against the existing active Main-Apply profile. It clicks the ordinary Requests control and country cards, then **Read country report**, changes the country selector, opens explicit Germany r1 history, returns through **Open prepared country report**, views PDF and downloads native PDF/Markdown through the normal routes. It does not force prepared request IDs as the navigation input.

The final first-process and second-process receipts, `normal.local.json` and `restart.local.json`, agree exactly on selected request, report/package/editorial identities, actual review states, PDF/Markdown hashes and annotation readback. Current selected owner versions have zero annotations; no owner annotation was added and no nonempty owner annotation persistence is claimed. Real personal overlay bytes and research history remain unchanged. QA suppresses only reading-position POSTs; normal private position/annotation writes and retained-map behavior are tested in isolated temporary profiles.

| Country | Native reader PDF SHA-256 | Detailed Markdown SHA-256 |
| --- | --- | --- |
| Germany | `68056c52497c2cd07627240e5d6e09185454aadaf154f72df6609664d19e0d18` | `fda9ed4fb7f88167179b46a4c4c520001c1cf32c17e384c61db245354cdbde55` |
| Canada | `9fcd1dce6e2c4529ad1646ef009b8cbaec9a12d2c1308e0b10fcf220b9148f0f` | `b583b71e95432036aa73b89b6568e808c3a43c6af2a4c6480a0d78f0c81f436e` |
| Corrected Belgium r3 | `f080840ade200212c22b90190fa0f6fe3d0f2ee964aa340448fae99904356135` | `973f029e8bc521dd6c39e54ab753a86f3cbb121809f4a1f9e7d83718bf503d0d` |

Germany/Canada native exports match their prepared packages, include the complete supplied detailed text/evidence map in Markdown and retain the actual dispositions. All three PDFs are selectable three-page documents with source links. Their saved manifests bind the selected canonical revision/hash and metadata edition. These report/export bytes are private and Git-excluded.

For APP-014 / GRA-94, the normal Belgium selection is corrected metadata `59d85e64588216609569427989c9b27374d0e4ba5669694bb2339ebe4aeab470`, canonical r3 `deb51ad6-cc82-4b94-8d5c-3e16a36b8f17` / `f38e80dbdd173e87e9012a7dce20f2b331cae1ba0d5796f31ee33844b81440d5`, reader r3 `3f7821c68324f25513783e7def6c23f44bb3b3364679372d73a11d37efd53a66`, detailed r3 `5cc0290f4ccd7b64cd94bdba6d14db85dee7a715c18f815c01217a925db628bf`. Displayed factual review is **pass**, human **unknown**. The unverified locator is omitted. Historical r2 errors no longer block or warn on this valid selected r3; their actual older context remains available. This supersedes the earlier r2 native receipt for the current selection without altering it.

Verification: **145 Python tests** and **three JavaScript regression files** pass, including prepared-versus-newer-findings selection, explicit historical selection, no request rebinding, evidence-map changes, historical annotations/pinned exports, map-sidecar classification, corrupt-history rejection and the existing invalid-state/payload cases. Syntax and diff checks pass. All **222 original captured Main-Apply files** preserve both bytes and timestamps. Normal inbox replay plus fresh workspace restart creates zero duplicate research records. No test fixture was placed in Main-Apply; legacy tracked DB/configuration, producer/importer files and exchange 1.0.0 are unchanged.

Normal-desktop screenshots, native exports, manifests, before/after diagnostics and a clickable local review index are under `grad-compass-workspace/runtime/app018-reconciliation-2026-10-22/`. The screenshots were visually inspected after waiting for Qt to paint the completed DOM; intermediate loading frames are not completion evidence. Reopen the normal desktop launcher after closing older app windows so the updated Python consumer is loaded.
