# Product decisions

Accepted on 2026-10-09 (Asia/Tehran):

- End goal is a multi-user web service. Personal local use comes first; beta is invite-only.
- Discovery defaults to an interactive map. A list/table is a toggle, sharing filters and selected results.
- Support all degree levels and multiple intakes, with applications at program/intake level.
- Reuse the current approved profile and CV outputs. Paperclip retains original private artifacts and supplies a minimal approved handoff.
- Manual Paperclip handoff is sufficient. Requests can be separate private files, indexed for discovery; follow-ups preserve request lineage.
- In-app alerts must catch up on reopening and avoid duplicate notifications.
- CV generation requests must be independently lockable. Existing-artifact viewing is separate from generation entitlement.
- Keep Python, SQLite, Leaflet, and plain frontend code until concrete requirements justify changes.
- App development does not modify the Research Engine, exchange v1 schemas/fixtures, production DB/config/cache, frozen profiles, or CV originals.
- Git cleanup is authorized for generated app environment/bytecode files; original data and research history remain tracked as before.

Pending coordination: private artifact manifest, request acknowledgement/result association, applicant-specific match explanations, later faculty/email schemas. Product filters unsupported by exchange v1 require an agreed extension or remain explicitly unavailable.

Pending visual review: map workspace layout, filters, list toggle, result inspector, empty/loading/error states, narrow-window and larger-text behavior.
