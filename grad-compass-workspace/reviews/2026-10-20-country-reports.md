# Country workspace and report review — 2026-10-20

This app increment reuses received research. No request, research execution, factual acceptance, shared contract/importer edit or applicant transfer was performed. Exchange 1.0.0 and private response 0.1.0 remain unchanged. The other pending mailbox README and features file edits are outside this delivery.

## Changes

- Reproduced the personal decision failure as HTTP 403: the old UI supplied the session header but omitted the managed profile header. The existing protected POST helper supplies both. Saving disables the chooser, success updates cards/details, and an error restores the previous choice with a clear message. Existing storage and decisions are preserved.
- Country cards/details separate report availability, factual review, university discovery and personal decisions. Complete bounded results never imply exhaustive coverage. The Belgium country report remains available with pending factual review and unknown human approval while university discovery has not started.
- Independent desktop panel handles support actual pointer dragging, keyboard increments, Home/End, double-click reset and Settings reset. Validated per-profile widths are backed up and survive restart; responsive clamping does not overwrite preferred widths. The map invalidates its size during resizing.
- The report is a full-window reading destination with country/request navigation, latest revision first, section outline, fact cards, original evidence/caveats, optional personal-note rail and collapsed secondary request/revision/recovery controls. The map remains mounted for an exact return. Block feedback uses the existing finding/revision binding with a stable field reference in the comment.
- An offline CC0 Brussels image, flag and navy/teal fallback support the reusable design. Image provenance and hash are in `web/assets/countries.json`. No external image fetch occurs while reading. The minimum app projection and ownership are documented in `design/country-reports.md` and APP-013.

## Verification

Passed 96 application Python tests, 22 unchanged exchange tests, two unchanged producer publisher tests, all three JavaScript regression files, JavaScript syntax checks and whitespace checks. Four focused new application tests cover the original 403, correct protected save, restart/profile isolation, independent layout persistence/recovery and endpoint validation. Three report projection cases cover faithful wording, missing sections/date separation and stable revision-bound references.

Native Qt checks ran in the working desktop session, without repeating the failed offscreen renderer. `scripts/check_country_workspace.py` used an explicitly marked, owner-private disposable restore of existing research. It exercised both real pointer drags, keyboard resizing, save success, injected error rollback, card/detail consistency, note saving, latest revision and all 21 Belgium sources. Returning to the map preserved camera transform, location/selection and panel widths exactly. All 12 combinations of 1440/820/390-pixel widths and the four supported text scales (1/1.15/1.3/1.5) passed overflow/navigation checks. A separate fresh process verified saved decisions, notes and widths, Settings reset, unchanged research history and the broken-image fallback. Profile isolation is also covered through the managed HTTP handler.

The existing native inbox regression passed automatic acknowledgement/partial/final updates, draft protection, errors, replay and reopen with the new report UI. A separate read-only run through the normal Main-Apply launcher captured the actual Belgium report and inspected a revision-bound funding-feedback draft without submission. Before/after research, personal decisions and text preferences were equal. Original received packets were not rewritten. The disposable review workspace is removed after verification; private evidence is retained.

## Normal-desktop visual evidence

Files under the Git-excluded `runtime/country-workspace-review/`:

- `2026-10-20-normal-country-map.local.png`: normal map, country statuses, decision and handles.
- `2026-10-20-normal-belgium-report.local.png`: full report header, review states and date distinctions.
- `2026-10-20-normal-funding-sources.local.png`: reading typography and finding-level citation controls.
- `2026-10-20-normal-narrow-report.local.png`: 390-pixel report at the largest text scale.
- `2026-10-20-map-panels-and-decision.local.png`: isolated native resize/save exercise.
- `2026-10-20-restart-persistent-report.local.png` and `2026-10-20-restart-image-fallback.local.png`: fresh-process persistence and fallback.

The normal desktop capture is display evidence, not independent factual approval of the research. It does not submit feedback or change personal preferences. Screenshots contain private research and stay outside Git.

## Content limits

Belgium's sources currently bind to the whole finding. Each block links those original sources with that limitation stated; exact claim-to-source citations are not fabricated. Standalone study and application-timing structure was not supplied, so those sections are unknown with links to the original overview. Original dated terms remain intact. Academic-year applicability is not inferred from requested intake, observation date or report issuance. Future producer improvements remain a compatibility discussion with Marry; no new mandatory fields or approval workflow were introduced.

Close older windows and reopen the installed Grad Compass entry, or run `grad-compass/envGradCompass/bin/python -B grad-compass/scripts/launch_preview.py`. Read the country report from country details; use Back to map to return.
