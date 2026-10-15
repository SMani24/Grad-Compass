# Paperclip mailbox

The temporary mailbox is `messages.local.md` in this directory. It is local and Git ignored. The user passes its location to Paperclip, which can append responses in the same file. Keep existing messages intact.

Each message has an ID, author, date with timezone, subject, and response section. Replies should refer to the message ID and identify any proposed contract change or blocker. Questions about applicant facts stay in the established private intake/review channel; this mailbox contains coordination only.

## Current verified status — 2026-10-13, Asia/Tehran

Read Dave's dated **2026-10-12 responses to APP-001 through APP-004**, followed by APP-005. His consolidated confirmation supersedes APP-004's stale enrichment/CV wording. Earlier messages remain intact as communication history.

Synthetic exchange implementation is authorized. On 2026-10-13 the user additionally authorized an end-to-end synthetic workflow in the app UI, using an explicit disposable database and isolated runtime. No university discovery, real-data producer/publishing/import, private transfer or new enrichment task is authorized or underway. Earlier instructions to continue discovery/delivery remain conditional on separately confirmed authorization.

## Ownership and review

Paperclip owns canonical profile work, CV generation, research evidence, factual acceptance and producer IDs/revisions. Alex's verification in GRA-38 confirms that the existing frozen Applicant Profile is approved, valid and immutable; prior enrichment/correction rounds are complete. No additional enrichment task is approved or underway. Any future changed revision requires its own evidence review, exact-version human approval and immutable freeze.

Riley's verification in GRA-39 confirms that the applicant-specific three-variant **v8 CV package is board accepted** against the existing approved frozen profile. This acceptance goes beyond the earlier Clean Academic design-direction approval. A future changed-profile rebuild requires separate authorization and review. Availability, review status and source revision remain separate facts; possession or draft viewing never implies approval.

The app consumes approved handoffs and displays their canonical status. Separately authorized draft viewing must retain a clear draft/unapproved label and source revision. The app does not introduce a competing profile/CV approval process. Its operational batch import decision remains distinct from Paperclip's factual acceptance.

Confirmed engineering split: **Codex owns subsequent application development and operational import decisions; Marry is the technical contact for exchange/importer compatibility.** GRA-37 verified all 16 delivered paths against operator commit `043d9d7`; the app team independently checked that they remain unchanged. The existing importer API is reused by the new synthetic UI consumer, with no production activation or real-data input. Coordinate with Marry before editing any shared importer/contract file. Exchange **1.0.0 remains unchanged**.

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

The synthetic UI feature does not expand production/private-data permissions. Existing local-file exclusions remain in force; the implementation does not modify the production database/configuration, Research Engine, frozen artifacts or CV outputs.

## Country-evidence proposal — APP-006, 2026-10-13

The latest app-only authorization adds synthetic promoted discovery and country exploration/personal decisions around the existing map. APP-006 asks Marry/Dave to review country/territory identifiers, evidence/review/revision conventions and a separately versioned future country-evidence supplement. Marry/Dave replied on 2026-10-15; APP-008 below reconciles the proposed synthetic supplement with the existing app fixture. No shared exchange change or producer implementation is activated.

The app demo uses its own clearly labelled invented country briefs and reserved example sources. Public exchange 1.0.0 and its importer remain unchanged. Country decisions are app-owned runtime state, separate from canonical factual acceptance and application stages. The user still relays mailbox messages manually. No real country transfer/research, private queue/artifacts or automatic agent invocation is authorized.

## Watchlist/request proposal — APP-007, 2026-10-15

The latest user authorization permits an app-owned **synthetic-only** watchlist/request/result/feedback pilot in isolated, Git-excluded runtime storage. Earlier blanket implementation restrictions now remain applicable to real data/private applicant transfers, not this new bounded synthetic milestone.

APP-007 was appended before implementation with minimal proposed private request/ack/result/feedback envelopes (draft 0.1.0), a separately versioned country-evidence supplement (draft 0.1.0), exact request/revision/digest bindings, immutable result history and app-owned preference/watchlist boundaries. Marry/Dave should review identifier conventions, producer ownership, versioning and approved private storage before producer integration is finalized. The current adapter accepts only app-generated invented responses; it is not an agreed real-data reader/writer.

Requests/preferences, personal notes/watchlist and immutable response/feedback records use marked synthetic `runtime/preview/research.sqlite`; manual exports use `research-handoff/` under the same ignored preview runtime. They do not contain or modify canonical profile/CV artifacts. The mailbox remains coordination only. Public exchange 1.0.0/importer files remain unchanged, with explicit operational promotion separate from producer factual acceptance. No automatic delivery, mailbox polling, agent invocation, real research transfer or deployment is included.

## APP-006/APP-007 reconciliation — 2026-10-15

Read Marry’s independent GRA-55 findings and Dave’s follow-up, then Codex’s **APP-008** in the local mailbox. Current status: **synthetic compatibility reviewed; gaps remain**. This supersedes older awaiting-response wording. Marry/Dave agreed a proposed synthetic private handoff and separate country-evidence supplement at 0.1.0; the existing app demo does not yet meet that wire format. Matching version numbers do not establish compatibility.

APP-008 names the unchanged fixture at app commit `9bfe9c6`, its source hash, test paths, the already-completed native round trip and a targeted disposable probe. It confirms concrete gaps in exact-byte external digests, duplicate-key rejection at browser/server boundaries, wire names, full revision/parent/finding bindings, partial-to-complete results, revision-bound factual review, UTC observations, public record revision associations and territory identities. The app’s canonical-field digest/history tests pass; exact-byte/complete-state compatibility is not claimed. This map increment does not replace or rebuild the already-passing demonstration.

Codex owns app/fixture changes; Marry should name any producer-owned example path before editing it and independently record the compatibility verdict. Any future shared importer/schema edit requires prior coordination; public exchange 1.0.0 remains unchanged. Real producer integration, real/private intake, production changes, artifact transfer, polling and automatic execution remain unapproved. The mailbox continues to carry coordination only.
