# T1 verification — 2026-10-01

Executed from the monorepo root, with writes limited to the research-engine subproject.

- `python3 grad-compass-research-engine/scripts/validate.py`: PASS, three synthetic exports; digest-bound receipt and preserved parent revision; fifteen invalid cases rejected.
- Negative cases: dangling evidence, document-derived preference, fabricated unknown, underspecified conflict, missing inference inputs, unexpected export fields, frozen-without-approval metadata, self-parent, page zero, duplicate claim IDs, unreadable evidence asserted as fact, inferred personal choice, changed frozen bytes, wrong approval target, and rejected approval.
- `git check-ignore` confirmed representative intake, profile and hidden review paths are excluded by the subproject rule. `git ls-files grad-compass-research-engine/private` returned no tracked files.
- Empty private root and all three subdirectories verified as owned by the current user, mode 0700 and not symlinks. No real applicant material created or read.
- `git diff --check` passed. Root-level pre-existing untracked `AGENTS.md` was left untouched; sibling application unchanged.

This verifies the T1 contract and synthetic exports, not T2 extraction/freeze implementation or T3 readiness. Reverify ACLs, existing backup/sync behavior, filesystem containment and user access to private review before any later authorized real intake. Receipt validation here demonstrates binding against a simulated human receipt; authenticating actual human approval through Paperclip belongs to T2/T3.

## T2 workflow verification — 2026-10-01

`python3 -m unittest discover -s grad-compass-research-engine/tests -v`: 10 integration tests passed. The tests use only invented inputs in run-owned scratch and cover:

- Different academic and work backgrounds; unknown choices/grades; line-linked factual evidence.
- Source conflicts; clarification-backed correction; unchanged parent bytes and revision lineage.
- Explicit preference answers; rejected document-derived preferences.
- Unchanged-input cache reuse; selective invalidation and retained source snapshots.
- Unsupported sources, unmapped text, missing inventory, and wrong quote/line/value rejection.
- Path traversal, symlink and overly broad mode rejection; private-root containment.
- HTML escaping and inert source instructions.
- Human-only acceptance, exact-byte binding, company/actor checks, supersession, exclusive freeze, read-only output and post-freeze revision.

The existing T1 command also passes: three exports and 15 rejected invalid cases. No private applicant documents were read. Live approval was not fabricated or exercised: production freeze reads a real saved Paperclip interaction, while synthetic tests inject explicit test-only responses. PDF/OCR support is intentionally absent and visibly reported.

Inspect [generated synthetic review](../examples/workflow-review.html), [generated export](../examples/workflow-output.json), and its source snapshots in `examples/workflow-sources/`. The review includes a source disagreement and unanswered preference/grade questions. See [workflow guide](workflow.md) for CLI usage and limitations.

## Workflow 1.1.0 focused verification — 2026-10-07

Recovered and verified the interrupted reusable evidence/review work. Schema 1.0.0 and production approval semantics remain unchanged. `python3 -m unittest discover -s grad-compass-research-engine/tests -v` passes all 18 synthetic integration tests; the existing export validator still passes three exports and rejects all 15 invalid cases.

Additional coverage includes exact multi-line ranges, narrowly scoped formatting normalization and rejection of altered quotes/values/ranges, observation context, clarification-authorized documentary selection, rejection of missing or falsified selection authority, user transcription with preserved original unreadability, specific gap rationale, grouped static review, escaped metadata and titles, contained source links, and workflow-version cache invalidation. Original snapshots, parent revisions, and approval/receipt checks remain covered. Source-selection context uses opaque source IDs instead of filenames.

The [new synthetic review example](../examples/evidence-review/README.md) contains the input manifests, original synthetic text, immutable snapshots, initial conflict, revised profile and grouped local reviews. It demonstrates project method/result/limitation claims, unknown applicant contribution and location preference, and a separate user-report claim authorizing the selected documentary value. No real private file was read during this verification or included in the example.

Limits: deterministic checks establish textual presence, not semantic support or authentic intent. The agent and human must review proposed subject/field assignments and selection authority. Multi-line normalization changes formatting only; it performs no OCR, semantic conversion, inferred preference or ownership attribution. Claim-ID change counts can include cache-version churn. The private pilot and exact-version approval remain separate unfinished work.
