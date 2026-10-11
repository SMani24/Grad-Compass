# Development progress

## 2026-10-09 — first increment

- Read-only audit and product interview completed; incremental development approved.
- Dedicated planning and local Paperclip mailbox prepared.
- Git cleanup completed in `c9e6f52` (`Tidy repo and plan app development`): generated app environment/bytecode files untracked, retained on disk; no source rollback.
- Foundation implemented: explicit runtime paths and offline mode; contained vault files with collision-free storage; foreign-key enforcement and transaction-managed connections; metadata-first deletion; versioned additive initialization; country selection pruning and stale-load handling.
- Synthetic demo creation and isolated desktop review commands documented in the application README.
- Verification: 18 Python regression cases and 6 JavaScript controller cases passed. Python syntax and whitespace checks passed. Fingerprints of 145 protected production/cache/research/exchange files match the pre-development snapshot.
- The GUI has not been launched against real data. Remaining audit findings (HTML rendering, history, enrichment, accessibility) stay on the backlog for subsequent interface work.
- Next visual checkpoint: map-first web workspace with list toggle and shared inspector.

No real-data transfer or deployment has occurred. The local mailbox is ready for the user to pass to Paperclip.

## 2026-10-09 — map workspace and desktop launch

- Added a plain HTML/CSS/JS browser workspace: dominant map, list toggle, common filters, university inspector, saved contacts and linked tasks. Missing-coordinate universities remain accessible.
- Added a standard-library HTTP preview with explicit static routes, read-only database access, a synthetic marker checked on every connection, and loopback-only binding. Research-data import and real-user service access remain future increments.
- Added a Qt desktop launcher for this preview. It creates only new/empty synthetic runtime storage, opens a private browser window and stops its server on close.
- Found that the existing Pop!_OS desktop entry used obsolete pre-monorepo paths. Installed a corrected entry with a compass icon; retained the previous file in the ignored runtime. The user can launch via Super → Grad Compass.
- Verified installed Python/Qt dependencies and included the Qt dependencies in the reproducible requirements file. No upgrades or system package changes were needed.
- Verification: 24 Python cases, 10 JavaScript cases, dependency consistency, native desktop rendering, HTTP smoke checks and Chrome map/list/mobile review passed. All 145 protected-file fingerprints remained unchanged.
- Screenshots, review instructions and limitations are organized under `reviews/`. The first layout review remains open for user feedback.

Paperclip requests remain in the local mailbox, with no replies at this checkpoint. The next research integration increment depends on reviewing their response and the agreed exchange ownership boundaries; no profile/CV artifacts have been relocated or regenerated.
