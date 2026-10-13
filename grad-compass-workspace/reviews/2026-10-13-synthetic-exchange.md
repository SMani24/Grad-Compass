# Synthetic exchange review — 2026-10-13

Open **Grad Compass → Research imports**. This is a bounded proof using the existing reviewed invented v1.0.0 batch and unchanged importer; only the separate disposable exchange database is writable.

## Demonstration

Select the finalized batch, validate/stage, inspect two institutions and three programs, explicitly map Example North University, review the dry run and check the operational approval box before promotion. Choose create-new to see one institution and one program record promoted while three pending records stay staged. Totals are two local institutions (including the seed) and one program. Replaying the same batch leaves the database bytes and counts unchanged.

The link-existing alternative preserves the seed institution's local name, location, deadline and status; the eligible program attaches to that chosen local institution. Source IDs, revisions, evidence references and producer review remain distinct from the operational decision. Claims with unknown/stale/expired outcomes remain in staging. No profile/CV workflow or private queue is involved.

## Review points

- Producer-accepted records start as staged; importing does not confer factual acceptance.
- Institutions and programs have separate tables and counters; each program retains its parent.
- No automatic matching or preselected mapping. Creating is deferred until approved promotion.
- A dry run shows before/after values, target parent and eligible intake claims without source writes.
- Missing accepted-institution mappings block approval. Mapping or freshness changes invalidate an earlier preview.
- Pending records remain visible after promotion, with reasons for being held.
- Reopening the dialog/app reloads the durable ledger. Replay shows zero new changes, rather than reporting historical promotions as new work.
- Escape closes the dialog; narrow screens keep the tables scrollable and the action controls usable.

## Verification

The native UI demonstration operated every visible step over the actual HTTP interface in a newly allocated temporary database. It verified separate record counts, blocked unmapped/unchecked approval, create-only-on-promotion, two promoted / three staged records and replay with no duplicates. The helper cleans up its own temporary database on exit; it does not reset the user-visible disposable workspace.

Backend regressions also cover mapping to an existing institution, byte-preserving replay and restart, source-data preservation during preview, changed mapping/freshness rejection, altered/real batch rejection, marker/hard-link rejection and same-app HTTP session enforcement. The shared contract/importer regression suite is run unchanged for compatibility.

Final checks passed: 31 app Python tests, 22 existing exchange tests, 13 JavaScript tests and three Qt input tests (69 total), plus the actual UI demonstration. Syntax, whitespace and dependency checks passed. All 146 protected production/cache/research/exchange/importer files match their pre-increment fingerprints; the 16 delivered paths remain identical to operator commit `043d9d7`.

Local synthetic screenshots live here as `2026-10-13-exchange-{staged,dry-run,replay}.local.png`. They are Git ignored. Product design remains open for visual feedback; this implementation does not activate real-data imports or shared hosting.
