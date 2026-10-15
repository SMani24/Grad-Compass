# Saved countries and map multi-selection · 2026-10-15

## Behavior and review

Use **Select countries** above the map. Click/tap polygons or use Enter/Space on the active polygon to toggle countries. Purple fill and a dashed purple outline identify this temporary save selection; the ordinary active-country highlight remains blue. The count, **Save selected**, **Clear**, **Choose from list**, and **Done** float above the map. Pan/zoom remain available. The searchable checkbox dialog provides a keyboard-accessible alternative independent of map positioning, exploration mode and location filters.

Selecting and saving preserve the location filter, open details, map camera, URL/history, personal notes, decisions and the separate research-request selection. Saving does not create research requests or acknowledgements. **Clear** empties the temporary selection. **Done** or Escape exits and discards unsaved selection; Escape from the list dialog returns to the same selection. Ordinary country selection/framing resumes on Done. Selection survives Map/List presentation changes within the page, but is intentionally not persisted on reload.

The interface now uses **Saved countries**, **Save country**, **Save selected**, and **Remove from saved**. Existing membership storage (`watched`), note fields and old bookmarked watchlist parameters remain compatible; no migration or membership reset is involved. Bulk saving is one transaction and sets only membership. Already-saved countries are unchanged, and a failed transaction leaves no partial memberships. Personal decision and factual review remain separate.

The toolbar wraps at narrow widths and enlarged text sizes. Panel offsets follow its measured height; the map itself keeps its full viewport and camera. The inactive map control is hidden in List presentation so the existing narrow List space is preserved. The toolbar remains available during an active selection, including its accessible list alternative. Dialogs and narrow panels scroll as needed.

## Verification

- **53 application Python tests passed**, including new atomic/repeat bulk saving, preexisting note/decision preservation, restart, invalid payload/rollback and session-protected HTTP tests.
- Both JavaScript regression files pass. JavaScript syntax and Git whitespace checks pass.
- Native synthetic UI demonstration passed: ordinary university rendering/details, existing history/keyboard behavior, country exploration/empty-country handoff, multi-selection, accepted save/replay, existing note/decision preservation, separate research selection, unchanged URL/filter/inspector/camera, map zoom and keyboard panning, accessible checkbox dialog and ordinary selection after Done.
- Existing country/responsive checks and new toolbar/list checks cover all four text sizes at **1440, 820 and 390 pixels**, including **390×640**. No body overflow or toolbar overlap; tested controls remain reachable. The native check uses fresh temporary map/exchange/research state and removes it on exit.
- The earlier complete research demonstration was reused as evidence rather than rebuilt for compatibility coordination.

Reproduce from the repository root:

```sh
grad-compass/envGradCompass/bin/python -B -m unittest discover -s grad-compass/tests -q
node --test grad-compass/tests/*.test.cjs
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py --selection-smoke-test --country-smoke-test --review-screenshots grad-compass-workspace/reviews
```

Local, ignored screenshots:

- [Saved countries on the map](2026-10-15-selection-map-saved-countries.local.png)
- [Minimum window, extra-large text](2026-10-15-selection-narrow-large-map.local.png)
- [Accessible country list, extra-large text](2026-10-15-selection-narrow-large-country-list.local.png)

## Coordination status correction

Marry/Dave's latest APP-006/APP-007 replies supersede earlier pending-response wording. **Synthetic compatibility reviewed; gaps remain.** APP-008 in the ignored manual mailbox identifies the existing deterministic fixture (`web/research_envelopes.py`, unchanged from `9bfe9c6`), validation rules, named tests and previous native round-trip evidence. It confirms exact-byte digest/duplicate-key gaps with a small disposable probe rather than rebuilding the demonstration.

The current adapter hashes canonical fields with an embedded digest; it does not verify a digest of complete exported bytes. Changed serialization still verifies, and a direct duplicate-key receipt probe returned HTTP 200. Other gaps include wire names, previous-result/parent/finding revision bindings, partial-only result revisions, country record/review provenance, date-only observations, public record revision associations and territory mapping. These are documented failures of the proposed compatibility gate, not passing negative tests. No producer schema or envelope redesign is included in this map increment. Marry is asked to confirm the inventory and transport/reference layout before a separately scoped app-adapter alignment.

Codex owns app development and consumer fixtures; Marry owns compatibility and any separately named producer example; Paperclip owns factual acceptance. Public exchange 1.0.0/importer, production data/configuration/cache, Research Engine and applicant artifacts remain untouched. Real/private intake, producer activation and automatic execution remain outside scope. The mailbox and screenshots remain ignored; source changes and these development notes are versioned.
