# Readability feedback · 2026-10-13

Antarctica is excluded from the discovery geometry, and the default map fits the useful latitude range. Other southern territories remain available. The bundled geographic data is unchanged.

Verified against the bundled GeoJSON with eight discovery tests and the native desktop smoke test, including map, list, details and navigation.

Settings now offers 100%, 115%, 130% and 150% text sizes. Typography uses root-relative units throughout the workspace and import dialog. Display preferences are stored atomically in the marked synthetic runtime, independently of the read-only map database. The preference survives reloads/relaunches; unsuccessful saves restore the previous size.

The floating header wraps, panel widths adjust within limits, panels/tables scroll, and list placement follows the actual header/filter height. Mobile map zoom buttons stay above the results panel.

Verification: 34 app Python tests, 22 unchanged exchange tests, 14 JavaScript tests and three Qt input tests passed (73 total). Native checks exercised every text size, reload persistence, widths 1440/1000/820/580/390, the minimum 390×640 window, details, Settings and research imports. At 150% in the smallest window, the exchange workflow promoted eligible records and replayed with zero new changes.

Review by launching Grad Compass and choosing Settings → Text size. Try Map/List, university details and Research imports at your preferred size. Local screenshots are `2026-10-13-exchange-readability-*.local.png` in this directory; they are deliberately excluded from Git.

Both completed entries were removed from `features_and_bugs.md`; its headings remain ready for new feedback. No production database/configuration, research artifacts or shared importer/contracts were changed.
