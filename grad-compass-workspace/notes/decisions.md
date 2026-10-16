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

## Verified coordination and authorized increment — 2026-10-13

Dave's consolidated 2026-10-12 replies confirm Marry's GRA-37 verification of the synthetic exchange/importer delivery against operator commit `043d9d7`. The existing approved frozen profile remains valid and immutable (GRA-38); the applicant-specific v8 CV package is board accepted against that profile (GRA-39). No further enrichment task is approved or underway. These facts supersede the stale planned-enrichment/unapproved-CV assumptions in APP-004; exact private identity/receipt references remain in the local mailbox and canonical producer workflow.

Codex owns app development and operational import decisions; Marry is the technical contact for shared exchange/importer compatibility. Paperclip retains factual acceptance and canonical profile/CV ownership. Shared files are unchanged; coordinate with Marry before any overlapping edits.

The user authorized an end-to-end synthetic exchange workflow through the app UI: select a finalized invented batch, validate/stage, explicitly map institutions, inspect a dry run, approve eligible promotion, inspect outcomes and verify replay. Use a separately marked disposable SQLite workspace. Reuse unchanged v1.0.0 and its importer; keep institution/program identities and staged/promoted states distinct. No real-data import, production migration, discovery, private queue or artifact transfer is included.

## Watchlist/manual research milestone — 2026-10-15

The user authorized synthetic app-owned watchlists, private notes, batch country selection, request preparation/manual handoff, remembered explicit preferences, acknowledgement/result receipt, finding feedback, follow-ups and revision review around the existing map workspace. This supersedes earlier “no private queue implementation” wording only for the bounded synthetic app pilot; no real transfer or producer deployment is authorized.

Watchlist membership, assessment, notes, factual review and operational import remain separate. Preference memory changes only after a successful explicit submission unless request-only is chosen; cancellation and casual feedback never change remembered restrictions. Each request freezes its exact snapshot. App preferences never modify the canonical Applicant Profile.

APP-007 proposes private envelopes 0.1.0 and independently versioned country evidence 0.1.0 for compatibility review. App-generated fixtures may exercise these provisional adapters; exchange 1.0.0 and its importer remain unchanged. The app does not poll the mailbox, infer agent progress, invoke agents or mark manual handoffs delivered without a response.

## Saved countries and compatibility clarification — 2026-10-15

“Saved countries” is interface wording over the existing membership field; it needs no migration. Ephemeral map selection, personal saved membership, research-request selection, personal decisions and factual review are distinct. Bulk save changes membership only and preserves notes/decisions even for existing memberships. Done discards unsaved selection; saving/selection never initiates research. An accessible country checkbox list complements polygon selection.

Marry/Dave's APP-006/APP-007 replies have been read and reconciled in APP-008. The existing `9bfe9c6` deterministic fixture and native demonstration remain the app evidence. Producer compatibility is **reviewed with gaps**, not verified: exact-byte external digests, duplicate JSON keys, wire fields, revision/review provenance, completion, timestamps, public revision associations and territory mappings need alignment. No competing evidence/profile/CV review gate, protocol migration, producer activation or shared exchange change is authorized by this map work. Coordinate any shared edits with Marry first.

## Persistent personal operation — 2026-10-16

The user authorizes the normal local app to prepare bounded real requests and consume manually returned research in owner-private, Git-excluded runtime storage. Existing reviewed evidence supplies the first real run; subsequent execution requires explicit request submission and manual invocation of Dave. No automatic expiry, renewal or agent invocation applies. Codex owns app/launch experience; Marry owns producer compatibility, Dave coordination, Discovery Researcher research and Alex independent review. Receipt, factual review, human approval and personal decisions remain separate. Locations are app-owned source-backed campus observations; unresolved institutions remain accessible. Legacy database/configuration, profile/CV transfer, outreach, faculty expansion and hosting remain outside scope.
