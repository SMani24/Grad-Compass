# Grad-Compass research exchange v1

This directory holds the manually operated, one-way public institution/program exchange contract. `schemas/` and `examples/` are tracked. The invented batch has exactly two institutions and three programs. It contains no applicant or CV data and must never be replaced with real records in tracked fixtures.

## Wire shape

Each finalized batch directory contains only `institutions.jsonl`, `programs.jsonl`, and `manifest.json`. Each JSONL line is one UTF-8 object followed by a newline. The manifest names those two fixed files and records exact-byte SHA-256 digests and line counts. A batch ID is immutable: replay of identical bytes is allowed; a reused ID with different bytes is an error. Exporters publish the manifest last and atomically rename a fully fsynced staging directory on the same filesystem. Importers read finalized directories only, reject unsafe paths and symlinks, and verify hashes, counts, schema, IDs, and references before writing to any database.

`institution`, `program`, `requirement`, and `batch` schemas are pinned to `1.0.0` and closed. Unknown fields and unsupported versions fail. UUIDs are opaque and stable across renames; the private producer registry owns their mapping. Programs reference institution UUIDs within the same batch. No local SQLite row ID or name-derived match crosses the boundary. The exported field allowlist is the exact properties in each entity schema. In particular, applicant profiles, CVs, professor contact information, outreach state, attachments, local IDs, notes, and credentials have no wire field.

Every non-null exported factual field has `facts.<field>` with an HTTPS source URL, a short page locator, and a UTC observation time. Intake requirement claims carry that evidence directly and use an explicit `YYYY-season` intake. A `null` requirement value means unknown. A record's accepted or rejected review includes an opaque reviewer ID, UTC review time, and `bound_revision` equal to `record_revision`. Any factual change needs a new revision and fresh research review. `source_checked` means the reviewer checked the cited source; it does not mean an institution endorsed the claim. Pending, rejected, unverified, and conflicting records can be received and staged, but cannot be promoted as accepted facts. Institution and program reviews are independent.

The importer requires a separate operational decision tied to the batch ID and manifest digest after a validated dry run. That decision is not a second factual review. The app must calculate intake claim freshness at promotion, never trust a serialized `freshness` label, and leave stale, unknown, or expired requirements staged. The pilot default for deadline and funding evidence is **30 days**; the importer must take this as a configurable policy value. No age limit is embedded in the schemas. An explicit intake deadline in the past is expired for that intake. The existing university-level deadline is outside this contract.

## Version policy and validation

The producer emits `1.0.0`. Consumers must explicitly list supported versions; they must reject any unlisted version rather than drop fields. Adding an optional field requires a coordinated minor schema and consumer update because objects are closed. Changing required fields or their meaning requires a major version and migration plan.

Run the focused contract checks with `python3 -m pip install -r grad-compass-exchange/requirements-dev.txt` in an isolated environment, then `python3 -m unittest discover -s grad-compass-exchange/tests -v`. `contract.py` provides read-only schema, review-binding, hash, count, parent-ID, and basic path-shape checks. It is not an importer, promotion authority, adversarial path-safety boundary, or real-data approval.

## Manual synthetic publish

Run `python3 grad-compass-exchange/exporter.py /path/to/existing/outbox` only after installing the development dependency above. The command accepts an output directory only; its input is fixed to the tracked invented five-record fixture. It validates the fixture, writes and fsyncs the two data files in a temporary directory under the outbox, writes and fsyncs the manifest last, then uses Linux `renameat2(RENAME_NOREPLACE)` and fsyncs the outbox directory. It fails closed if atomic no-replace rename is unavailable. An identical batch ID and identical bytes replay without a write; changed or invalid contents under the same ID fail. An interruption before rename leaves no finalized batch. This publisher never reads the research engine or application database, and it does not authorize a real-data export.

`contract.validate_batch` checks closed schemas, review bindings, provenance, exact file hashes and counts, unique IDs, parent references, filenames, symlinks, and complete three-file directories. Consumers handling directories writable by another process still need descriptor-based no-follow reads to close path substitution races before any database write.

## Local private paths

Exchange `outbox/`, `receipts/`, `registry/`, `private/`, and `staging/` are Git ignored, as are SQLite files and sidecars inside this exchange. The app's `data/` DB, config, vault, backups, and UI cache have targeted future ignore rules. Existing tracked DB/config/cache files remain tracked despite these rules; no untracking, relocation, or production file change is authorized by this stage. Store any future private material only in an approved access-controlled intake location. No production export or import is authorized here.

## Synthetic importer draft (app side)

The importer requires the test-only `exchange_synthetic_test_guard` row created by the synthetic test fixture. A compatible `universities` schema alone does not qualify a database; missing files, the application DB path, and hard links to that DB fail closed. The marker is a scope guard for this draft, not authorization to operate on production or copied private data.

`../grad-compass/core/exchange_importer.py` is a manual API draft. It requires an explicit, existing SQLite path and rejects the app's real `data/grad_compass.db` path. There is no scheduler, UI integration, or production migration command. The reviewer can inspect `migrate`, `dry_run`, `stage`, `map_institution`, `decide`, `promote`, `receipt`, and `write_receipt` in that order. `dry_run` validates the finalized directory and returns a digest and mapping needs without writing. `migrate` adds only version 1 exchange-owned tables and a separate `programs` table to the supplied synthetic database. `stage` records all valid review states transactionally. `map_institution` requires an explicit existing university ID or a create choice; the create choice inserts a university only during approved promotion. `decide` binds one operator decision to the batch ID and manifest digest. `promote` rechecks that decision and computes requirement freshness using the supplied UTC promotion time and configurable `max_age_days` (default 30). The returned receipt contains only batch ID, digest, decision and aggregate outcomes. The durable ledger can regenerate the same receipt after a post-commit crash; `write_receipt` publishes it atomically in an explicitly supplied receipt directory.

Existing university mappings initially preserve all local fields. Source-created university updates require its last source-owned snapshot to match the current row; program updates use the same conflict check. Promotion leaves app-owned status, deadline, coordinates, images and unrelated tables untouched. Pending, rejected, unverified, conflicting and parent-unmapped records stay staged. Unknown, stale or expired intake claims remain in staging and are omitted from authoritative program requirements. Importer connections enable foreign keys. This draft does not authorize real-data import or production migration.

Run the importer checks after installing `requirements-dev.txt` in an isolated environment:

```sh
python3 -m unittest discover -s grad-compass-exchange/tests -p 'test_importer.py' -v
```

Each importer test builds an explicit temporary synthetic SQLite file and checks that it cannot resolve to the real app DB. The test suite never reads application data.
