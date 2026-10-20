# Country reader refinements

The map remains the exploration workspace. Country details now place the dated report action first, university exploration second, and removal inside Country actions. Research review, discovery and personal decisions remain independent. Both panel handles are subtle dividers with their existing pointer, keyboard, reset and remembered-width behavior.

The report workspace uses more of the window, supports a collapsible saved-request sidebar, Comfortable/Wide prose widths and compact section navigation. Tables use the available width. Closing the annotation rail releases its space. App-owned profile preferences and exact-version passage positions are backed up and restored independently of research and annotations.

The selected canonical version supplies a concise reader PDF and a complete portable Markdown export. The current reader fallback selects complete canonical passages rather than inventing a new editorial summary. Markdown includes the verbatim report and evidence map, dated public finding-level sources, qualifications, scope/review and stable passage locators; private annotations require an explicit checkbox. Its public evidence and text are embedded rather than depending on local files. Old PDFs and annotations stay immutable and readable. The optional producer concise-document addition and ownership split are documented in `design/country-reports.md` and APP-015; it awaits compatibility agreement and actual producer wording, without blocking the current extract fallback.

The prior screenshot's research-result r2 and canonical-report v1 were independent identifiers. A genuine canonical v2 arrived during this task. The reader and both export names/content now identify the selected canonical report, with the result relationship explained in a secondary disclosure. Choosing v1 still exports v1. Actual delivered canonical review remains pending; human approval remains unknown. No disposition is inferred from viewing or exporting.

Code revision: `5a0138e` (Refine country reports and exports).

## Verification

* 118 Python tests pass, including focused export precision/privacy, exact selected-version PDF retention, reading preference validation/restart/backup/profile isolation and protected write checks. All three JavaScript regression files and syntax checks pass; installed dependencies are consistent.
* The actual normal Main-Apply launcher passed country controls, sidebar/width/section navigation, annotation-space recovery, native PDF/Markdown downloads, PDF source navigation, narrow large text and exact map return. Research snapshots, decisions, display preferences and annotations were unchanged. Temporary reader-width/sidebar choices were restored; automatic reading positions and app PDF cache are expected private app state.
* Marked disposable copies passed the same layout/export controls at twelve width/text-size combinations, explicit optional annotation export, v1/v2 export selection, map/reading return and a separate restart restoring sidebar/width/passage. Screen/PDF highlighting, edited comments, feedback/follow-up preparation and exact PDF locations also passed a separate full native check and restart. No new owner request or agent execution was created by these checks.
* The current reader PDF has three visually inspected pages, 24 external source links and 37 internal evidence links. Selectable text remains within page bounds, the qualified cost table is readable, and citation destinations survive page numbering. Older eight-page exports remain in their original cache.

A repeated test first assumed a fresh sidebar preference and later selected an empty DOM text node left by an existing highlight. The harness now sets its own initial preferences only in the marked copy and selects a nonempty text node. These were repeatability fixes; final native runs passed. No owner data was cleared for testing.

Private screenshots, downloaded reports, hashes and preservation receipts are under `runtime/reader-refinement-review/` and excluded from Git. The normal-desktop files are labelled `2026-10-20-normal-reader-…`; annotation checks have a separate evidence directory. Disposable profile copies and their registries are removed after verification. Existing mailbox/README and feature-file edits from other work are not part of this change.
