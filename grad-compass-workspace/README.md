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
| `runtime/` | Optional synthetic development data, never personal input. Git ignored. |

Keep tracked notes free of applicant facts, email contents, credentials, and private artifact paths. Real personal materials belong in a separately approved private runtime location outside source control. Do not add them to this workspace.

Read the local mailbox before research-related work. Append dated messages rather than overwriting either team's replies. The user manually tells Paperclip when the mailbox changes; there is no automated delivery or status polling.

## Feedback and delivery

The user maintains `../features_and_bugs.md` while using the application. Read it when asked and address one entry at a time. After implementation and verification, remove the completed entry and record its outcome in the review notes; Git history preserves the original feedback. New entries do not automatically authorize implementation or expand real-data permissions.

For each requested increment, run the relevant checks and provide a visual review when appropriate. Commit completed changes with a short, natural message and push to the configured GitHub remote so each increment can be reviewed and reverted. Preserve shared history; do not force-push. The manual mailbox and local preview artifacts keep their existing exclusions.

The active publication branch is `app-development-2026-10-11`. GitHub rejected the original local `main` history because an earlier commit contains an oversized generated Qt library. This publication branch starts from GitHub's existing `main` and records the current tracked files; the original local commits remain on `main`. Push subsequent increments to the publication branch until integration with GitHub `main` is agreed.
