# Applicant profile integration contract 1.0.0

## Consumer boundary

`schemas/applicant-profile-1.0.0.schema.json` is JSON Schema Draft 2020-12. Consumers pin exact `schema_version`, `profile_id`, `revision_id` and `version_name`. Reject unsupported versions; do not coerce unknown fields or reinterpret claim kinds. Schema changes use semantic versioning: incompatible meaning/required-field changes increment major, additive optional changes minor, clarifications patch. Each released schema remains immutable. Migrations create new revisions and preserve source/revision mappings; approval never transfers implicitly.

An export contains opaque IDs, revision lineage, sources, claims, issues, lifecycle and approval metadata. No private storage paths or document bodies are included. Private exports are still private data. A claim `field` is a stable dot-separated domain key, e.g. `education.degree`, `education.discipline`, `education.gpa`, `experience.role`, `skills.language`, `preferences.location`, `preferences.budget`, `goals.career`. Multiple claims may share a field; consumers must preserve IDs and must not select one by array order. `subject_id` groups facts belonging to the same degree/job/project without assuming a particular applicant background. Use typed scalar values; complex records are groups of claims. Preserve units, scale, institution wording and date precision in separate fields or `context`. Do not normalize grades across grading systems without an explicit inference and method.

### Project and publication detail

Rich evidence belongs in the exported `claims`, grouped by the stable `subject_id` of its project or publication. It must not exist only in review prose or a summary. These field families are domain conventions within schema 1.0.0, not required fields for every applicant:

| Subject | Example fields | Interpretation |
| --- | --- | --- |
| Project | `projects.title`, `projects.contribution.*`, `projects.methods.*`, `projects.tools`, `projects.decisions.*`, `projects.results.*`, `projects.limitations.*` | Separate what the source describes from the applicant's specifically evidenced contribution. |
| Project | `projects.source_described_skills`, `projects.source_described_relevance` | Preserve the source's wording and qualifications; these are not independent skill assessments or inferred personal interests. |
| Publication | `publications.title`, `publications.status`, `publications.doi`, `publications.research_summary`, `publications.applicant_contribution` | Keep bibliographic status, research content, and applicant contribution as distinct evidence-linked claims. |

Consumers must carry `kind`, `context`, `evidence`, `related_claim_ids`, `rationale`, and `next_action` with the values they display or consume. A project-level method does not by itself establish that the applicant performed it, designed it, or owns the result. Authorship does not prove a particular contribution. Do not turn source-described relevance into a career goal or preference. If contribution or ownership is unclear, preserve that qualification and an unknown where needed; do not fill the gap from a title, course, coauthor list, or broad summary. Preserve reported versus verified status and experimental limitations when producing any downstream summary.

## Claim and evidence conventions

| Kind | Meaning | Required support |
| --- | --- | --- |
| `documented_fact` | What supplied evidence states, not independent verification | At least one document reference |
| `user_report` | Applicant assertion | Clarification source reference |
| `preference` | Explicit personal choice | Clarification source reference; never inferred from documents |
| `inference` | Explicit derived interpretation, not fact | Referenced input claim IDs and visible rationale |
| `conflict` | Competing claims cannot yet be reconciled | At least two alternative claim IDs; null value and next action |
| `unknown` | Missing, unreadable or ambiguous information | Null value, reason and next action |

All important assertions carry evidence references. Each evidence entry names a source and a locator: `page`, `section`, `answer`, or `unavailable`; page numbers are one-based. If precise location is unavailable, record why rather than inventing it. Sources distinguish documents and clarification answers, with content digest, readability state and capture timestamp. A clarification answer is an immutable source; later answers become new sources. Synthetic sources have `synthetic: true`; no actual applicant facts appear in examples.

Uncertainty is first-class. `issues` identify affected claims, `missing`, `unreadable`, `ambiguous`, or `conflict`, and a concrete next action. Source readability must be `readable`, `partial`, or `unreadable`; partial sources can support only actually readable claims. Unknown values are JSON null, never fabricated defaults or empty strings. Preferences, financial limits, geography, career goals and relocation choices must be supplied explicitly by the human; factual evidence cannot establish them. These choices use `preferences.*` or `goals.*` keys and only `preference` or `unknown` kinds. Do not hide a choice inference behind a factual key.

## Review and clarification format

Generate a private readable review containing exact schema/profile/revision/name, lifecycle, and every claim's ID, field, kind, value, source locator and uncertainty. Grouped claim cards or a table may present these details; expandable metadata must remain accessible. Include all conflicts and unknowns, consolidated questions, a change summary relative to the parent revision, and approval scope. Source links resolve locally through the private manifest; exports use only IDs. `examples/review.md` demonstrates this format using invented data. Never replace missing evidence with plausible facts or silently resolve conflicting values. Corrections preserve prior revisions and source history.

## Revision and immutable human approval

Drafts are editable working objects. A review candidate receives a unique `revision_id` and `version_name`. Approval is a two-part protocol to avoid self-referential hashes: present the exact frozen candidate bytes locally, compute SHA-256 of those bytes, and bind a human-only saved confirmation to profile ID, revision ID, version name, schema version and digest. No private contents enter the interaction. A private external receipt records the human decision and reliability-for-discovery statement; `approval` in the export contains its preallocated opaque receipt ID, human actor ID and timestamp. If these metadata change, regenerate the candidate and seek approval of its new digest. A candidate with `status: frozen` is not authoritative until the receipt verifies its exact bytes and an explicit human acceptance exists. Silence, an agent decision, schema validity or a synthetic approval does not establish approval.

After acceptance store the exact bytes with exclusive-create/no-overwrite semantics and a separate receipt; make them read-only where supported. Hash verification detects mutation but is not a substitute for authorization. Consumers require both export and matching receipt before treating a version as approved. Rejected or superseded candidates remain unapproved. Any correction creates a new revision with `parent_revision_id`; previous approved bytes and receipts remain unchanged. Unresolved unknowns may remain in a frozen profile only when clearly presented and explicitly accepted by the user as reliable enough. Approval authorizes this version only, not discovery, research, ranking or outreach.

T1 defines and validates exports and lifecycle constraints. T2 must implement actual parsing, review rendering, clarification, cache invalidation, revisions, receipt verification and exclusive freeze, with synthetic tests. T3 must remain incomplete until the human approves the exact real frozen profile and considers it reliable enough for discovery; no real documents are processed in T1.
