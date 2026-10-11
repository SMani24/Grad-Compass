# Initial audit

The initial audit was read-only. The desktop application uses pywebview, SQLite, Leaflet, local GeoJSON, Python geocoding/photo helpers, and modular plain HTML/CSS/JS. It supports university/faculty CRUD, batch actions, attachments, tasks, an admissions board, settings, and navigation history.

## Confirmed issues

- Selections leak across countries; batch actions can operate on invisible records.
- Connections do not enforce foreign keys; deleting a university misses professor-only tasks.
- Vault files with the same basename overwrite each other.
- File deletion precedes DB commit; stored paths are not constrained to the vault.
- User strings enter HTML templates without escaping.
- History lacks complete country context and stores stale university objects.
- Startup migrations are unversioned. Existing DB has extra country notes, professor contact-date fields, and older attachment metadata that must be preserved.
- Dates are displayed, but reminders/follow-up scheduling are absent.
- Task associations and lab website fields are not exposed in the UI.
- Network enrichment blocks saves; image invalidation and missing-file repair are incomplete.
- Old `styles.css` duplicates the active split stylesheets; larger-text/responsive/accessibility work remains.
- No application regression suite existed. Exchange has synthetic contract/export/import tests.

## Preservation boundaries

Original DB/config/cache and all Research Engine/exchange files stay unchanged during development. The existing synthetic-only importer is deliberately not a production import command. No raw applicant documents are needed for foundation or UI tests.

## Git review

At the start of implementation the working tree was clean. Git tracked 5,626 app virtual-environment files and four app bytecode files. Remove these generated paths from the index only, retain the installed environment on disk, and correct targeted ignore rules. No source rollback is warranted. Keep the existing user note `tmp.txt` intact.
