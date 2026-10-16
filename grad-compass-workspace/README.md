# Application development workspace

This is the dedicated space for Grad-Compass product decisions, research-team coordination, plans, assets, and review notes. Application code stays in `../grad-compass/`.

| Location | Purpose |
| --- | --- |
| `../features_and_bugs.md` | User-maintained feedback queue; review and address entries one at a time when requested. |
| `paperclip/messages.local.md` | Temporary two-way mailbox; Paperclip appends replies here. Git ignored. |
| `paperclip/README.md` | Mailbox protocol and ownership boundaries. |
| `plans/roadmap.md` | Agreed incremental feature backlog and acceptance criteria. |
| `notes/decisions.md` | Accepted product choices and deferred decisions. |
| `notes/audit.md` | Findings from the initial read-only audit. |
| `notes/progress.md` | Completed work, verification, and the next review checkpoint. |
| `assets/README.md` | Asset organization and source/licensing rules. |
| `reviews/README.md` | Visual review workflow. |
| `runtime/` | Approved owner-private persistent local runtime, backups and separate synthetic development storage. Git ignored. |

Keep tracked notes free of applicant facts, email contents, credentials, and private artifact paths. The user has approved the persistent private local runtime for requests, preferences, controlled research results and app-owned locations. Applicant profile/CV transfer remains outside this authorization; keep those artifacts in their existing owned storage.

Read the local mailbox before research-related work. Append dated messages rather than overwriting either team's replies. The user manually tells Paperclip when the mailbox changes; there is no automated delivery or status polling.

## Feedback and delivery

The user maintains `../features_and_bugs.md` while using the application. Read it when asked and address one entry at a time. After implementation and verification, remove the completed entry and record its outcome in the review notes; Git history preserves the original feedback. New entries do not automatically authorize implementation or expand real-data permissions.

For each requested increment, run the relevant checks and provide a visual review when appropriate. Commit completed changes with a short, natural message and push to the configured GitHub remote so each increment can be reviewed and reverted. Preserve shared history; do not force-push. The manual mailbox and local preview artifacts keep their existing exclusions.

The active publication branch is `app-development-2026-10-11`. GitHub rejected the original local `main` history because an earlier commit contains an oversized generated Qt library. This publication branch starts from GitHub's existing `main` and records the current tracked files; the original local commits remain on `main`. Push subsequent increments to the publication branch until integration with GitHub `main` is agreed.

## Operational local workflow — 2026-10-16

The user superseded the preview-only restriction with persistent local request/result integration and a manually invoked first real request. The normal desktop launcher now opens this local workflow. See the [application guide](../grad-compass/README.md) and [verified review](reviews/2026-10-16-local-workflow.md). Earlier dated synthetic-only notes describe earlier authorization; they do not override this explicit update. Exchange 1.0.0 and its synthetic SQLite promoter remain unchanged. No automatic agent invocation, profile/CV transfer, production migration or public hosting is included.
