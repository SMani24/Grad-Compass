# Paperclip mailbox

The temporary mailbox is `messages.local.md` in this directory. It is local and Git ignored. The user passes its location to Paperclip, which can append responses in the same file. Keep existing messages intact.

Each message has an ID, author, date with timezone, subject, and response section. Replies should refer to the message ID and identify any proposed contract change or blocker. Questions about applicant facts stay in the established private intake/review channel; this mailbox contains coordination only.

## Current clarification — 2026-10-11, Asia/Tehran

Read **APP-004** in the mailbox for the current clarification of APP-001 through APP-003. Earlier messages remain intact as communication history; APP-004 supersedes conflicting authorization assumptions and artifact-status wording.

Synthetic exchange implementation is authorized. This mailbox does not establish authorization for university discovery, real-data publishing/importing, private transfers, production changes, or new research stages. Dave should confirm the actual authorized work, existing engineering ownership and delivery blockers before action. Earlier instructions to keep discovery progressing, publish a first delivery or continue delivering are conditional on separately confirmed authorization.

## Ownership and review

Paperclip owns canonical profile enrichment, CV generation, research evidence, factual acceptance and producer IDs/revisions. The existing frozen Applicant Profile is approved and immutable. A separate enrichment revision is planned for missing research appointments, teaching, coursework, contacts, publications and other supported categories; it requires its own approval/freeze gate.

The current CV package is **unapproved**. The adapted **Clean Academic CV design direction** is approved; the next applicant-specific rebuild waits for an approved enriched profile. Availability, review status and source revision are separate facts. A file's existence, transfer or draft viewing does not imply approval.

The app consumes approved handoffs and displays their canonical status. Separately authorized draft viewing must retain a clear draft/unapproved label and source revision. The app does not introduce a competing profile/CV approval process. Its operational batch import decision remains distinct from Paperclip's factual acceptance.

Proposed engineering split, pending Dave/Marry confirmation: **Codex owns subsequent application development; Marry is the technical contact for exchange compatibility.** APP-004 inventories the existing delivery in commit `043d9d7`: v1 schemas, validator, synthetic exporter/fixtures/tests and the app-side synthetic importer draft. The importer is a manual API, not connected to either app interface, and is not authorized for real data. Confirm outstanding work before overlapping edits; coordinate changes to shared files, importer compatibility and schemas before editing them. Exchange **1.0.0 remains unchanged** under this request.

## Three separate handoffs

| Location | Purpose and boundary |
| --- | --- |
| `messages.local.md` | Manual coordination messages and replies only; no personal materials. The user informs the other team of updates. |
| `grad-compass-exchange/` | Public institution/program batches under unchanged v1.0.0; current publisher is synthetic-only. Real-data publishing/importing requires separate authorization. |
| Separately approved private runtime storage | Applicant artifacts and private requests/results; no transfer, location or format is authorized by the mailbox. |

Private queue and manifest shapes in APP-001 through APP-003 remain proposals until agreed and separately authorized. A suggested runtime path is not permission to create or populate it. No polling, automatic agent invocation or automatic delivery is requested.

## Local-file exclusions checked — 2026-10-11

`grad-compass-workspace/.gitignore` excludes this mailbox through `/paperclip/*.local.md`, the entire `/runtime/` tree (including preview databases, SQLite sidecars, browser state and launch logs), and `/reviews/*.local.*` screenshots/notes. Local screenshots must use that naming convention. Checks with `git check-ignore --no-index` confirmed representative paths; none of these workspace local artifacts is tracked. The app and exchange also have targeted SQLite/sidecar exclusions. These are location-specific rules, not a repository-wide exclusion of every log or screenshot.

Already-tracked exceptions, identified from filenames only: `grad-compass/data/grad_compass.db`, `grad-compass/data/config.json` and four files under `grad-compass/ui/cache/` remain tracked despite their ignore rules. Treat the database/configuration and potentially personal cache as sensitive; contents were not inspected. Nine logs under `grad-compass-research-engine/cv/synthetic/build-v6/`, `build-v7/` and `build-v8/` are also tracked; their paths identify synthetic build output, and their contents were not inspected. No paths under `grad-compass-research-engine/private/` are tracked.

This documentation update does not change exclusions, tracking, file locations or Git history. It does not modify production databases/configuration, the Research Engine, frozen artifacts or CV outputs.
