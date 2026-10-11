# Applicant workflow 1.1.0

This is an on-demand, local, agent-assisted implementation. Codex uses the [extraction prompt](../prompts/extract.md) to prepare proposed evidence mappings; Python deterministically validates them, maintains provenance, detects gaps/conflicts, renders the review, and enforces revision/freeze rules. No extra model API, external service, daemon or UI is used.

## Supported inputs and limits

UTF-8 `.txt` and `.md` have one-based line locators (exported as section/answer references). Values are verbatim strings unless the observation explicitly requests the narrow formatting normalization described below. Numerical wording and units stay unchanged. Keep numeric normalization as a separately reviewed future inference. Documents and explicit clarification answers are separate source kinds. Binary formats including PDF, scans, DOCX and images are inventoried as unreadable with a next action. No OCR or speculative extraction occurs. Supply an authorized, locally prepared readable text version, retaining the original and its relationship in the private intake manifest; page fidelity is not claimed by a text line locator. This release does not automatically transcribe PDFs. The export schema remains `1.0.0`; the workflow version changes the parser cache namespace.

A quote match proves textual presence, not semantic entailment. Alex reviews field/subject mappings; the user reviews the evidence-linked output. Required fields are selected for the objective, never assumed from a specific applicant's background. Files are limited to 20 MiB. Cache keys include bytes, format, source kind, extraction observations, schema and workflow versions. Changing one source reprocesses its dependent claims; conflicts and required gaps are recalculated cheaply. Prior source bytes, drafts and reviews remain immutable.

A document can contain an applicant's own report. Its `documented_fact` claim establishes that the report appears in the document, while `context` must state that the underlying appointment, term, proficiency, or historical status is self-reported and not independently certified. A separate required field can record that official verification is absent without erasing the reported value. Use distinct subjects for repeated dated records such as teaching terms. For fields that legitimately contain several values on one subject, the manifest may declare `repeatable_fields` entries with `subject_id` and `field`; these suppress automatic conflict creation for that exact pair. Do not mark a genuinely disputed single-value field repeatable. Duplicate required-gap declarations for one subject and field collapse to the last declaration.

## Private storage and intake

Follow [privacy.md](privacy.md), including separate confirmation of backup/sync exposure and human access before private intake. The only production root is `grad-compass-research-engine/private/`. Use owner-only directories/files. `check-storage` rechecks ownership, modes, symlinks, hardlinks, ACLs, Git tracking and ignore rules. Every read/write repeats containment checks. The single-user boundary assumes no hostile concurrent process running as the same OS user; filesystem protection is not multi-tenant isolation.

```sh
python3 grad-compass-research-engine/scripts/workflow.py check-storage
```

The adapter creates `cache/`, `sources/`, `candidates/` and `frozen/` under that same excluded root in addition to the original intake/profiles/reviews directories. Source snapshots are content-preserving and read-only. All data stays private. Do not upload reviews, manifests, sources or exports to Paperclip.

Place source files in `private/intake/documents/`; all files there must be listed. Place the control manifest at `private/intake/manifest.json`. `sources` entries contain `file` relative to intake, `kind` (`document` or `clarification`), and `observations`. Only explicit user answers are clarification sources. Example invented manifest:

```json
{
  "synthetic": true,
  "sources": [{
    "file": "documents/record.txt",
    "kind": "document",
    "observations": [{
      "subject_id": "degree-a",
      "field": "education.degree",
      "line": 1,
      "quote": "Award: BA in History",
      "value": "BA in History"
    }]
  }],
  "required": [{"subject_id": "applicant", "field": "preferences.location"}],
  "corrections": []
}
```

Use `synthetic: false` for a real applicant, never relabel private data as synthetic. The `--synthetic --root <scratch-root>` mode exists only for invented test data. The root must already exist with mode 0700. Production mode refuses arbitrary roots. Do not log manifest values or source filenames in issue comments.

An observation may add `end_line` for an inclusive multi-line range, `context` for a reviewed qualifier, and `normalization: "markdown_whitespace"`. The exact `quote` must occur within the source range before normalization. Normalization removes only balanced, single-line `**bold**`, `__bold__`, and single-backtick code markers, then collapses whitespace. Unmatched markers and longer marker runs stay literal. The value must occur in the resulting text; spelling, punctuation, dates, capitalization, units, and meanings are not rewritten. The claim context records the transformation and the need for semantic review. Original snapshots remain byte-for-byte unchanged.

```json
{
  "subject_id": "degree-a", "field": "education.degree",
  "line": 1, "end_line": 2,
  "quote": "**BA**\nin __History__", "value": "BA in History",
  "normalization": "markdown_whitespace",
  "context": "Degree wording only; date remains unverified."
}
```

A locally extracted PDF text source may name an earlier manifest entry with `derived_from`; the original must be a PDF and the derived file `.txt`. A user-supplied transcription instead uses `kind: "clarification"` with `transcription_of` naming an earlier source. Its assertions remain user reports and the unreadable original remains visible. The private review links each relationship to the original; relationship paths stay outside the profile export. A required-field entry may provide a specific `rationale` and `next_action` for an unknown instead of the generic prompt.

## Build, review and revise

```sh
python3 grad-compass-research-engine/scripts/workflow.py build manifest.json
python3 grad-compass-research-engine/scripts/workflow.py build manifest-v2.json --parent REVISION_ID
```

Commands print only an opaque revision ID and cache counters. Exports are `private/profiles/REVISION_ID.json`; local HTML reviews are `private/reviews/REVISION_ID.html`. Open the review locally in a browser; evidence links resolve to immutable local source snapshots. HTML escapes all source-derived strings and loads no scripts or remote assets. The review shows all claim kinds, values, locators, alternatives, unresolved issues, next actions and additions/removals/changes.

The review groups claims by subject, with readable field labels, subject navigation, consolidated unresolved questions, and a concise change summary. A subject with one unambiguous documented or user-reported `*.title` uses that title for its heading and navigation; conflicting titles retain the subject label. Exact version identifiers and evidence metadata remain available in expandable sections. Change counts compare claim IDs; cache invalidation can therefore show unchanged wording as a removed and added claim. Only contained `sources/` and `intake/` paths become links.

To correct a claim, add a new clarification source containing the explicit answer, reference its exact line, and include `{"subject_id":"job-a","field":"experience.role","value":"Pastry supervisor"}` in `corrections`. Build with the parent revision. This selects the explicit answer in the new revision, while prior alternatives remain inspectable in the parent. Without a correction directive, differing answers remain conflicts. A later draft or candidate supersedes any unfrozen candidates for that profile.

If the human chooses a documented value without restating it, use a source-selection correction instead:

```json
{
  "subject_id": "job-a", "field": "experience.role", "value": "Pastry supervisor",
  "source_file": "documents/letter.md", "authority_file": "documents/answer.txt",
  "authority_line": 1, "authority_quote": "Use the role in the letter."
}
```

Both files must be in the manifest; the selected value must identify exactly one verified documentary claim, and the authority quote must occur at the stated line in a clarification source. The selected claim keeps its documented-fact type and documentary evidence. A separate `review.source_selection` user report links the exact clarification quote to the selected claim. Exported context uses the opaque source ID; original filenames stay in the private mapping. Duplicate correction targets fail. These checks verify textual presence and source kind, not whether the answer semantically authorizes the proposed choice: Alex and the human reviewer must check that relationship. Neither form of correction is profile approval.

## Exact-version approval and freeze

```sh
python3 grad-compass-research-engine/scripts/workflow.py candidate REVISION_ID --actor HUMAN_USER_ID
```

This creates an unapproved frozen candidate, its private HTML review, and a sanitized `candidates/CANDIDATE_ID.request.json`. The candidate's preallocated `approved_at` timestamp is part of the proposed approval metadata; actual decision time is recorded separately as receipt `resolved_at`. The candidate has no authority before acceptance. Do not alter either file.

Alex posts the request JSON as an actual `POST /api/issues/ISSUE_ID/interactions` with run audit headers, then sets the issue `in_review`. The request is human-only, addressed to the reviewer, and binds schema/profile/revision/version plus exact SHA-256. It asks whether the reviewed version, including visible unknowns, is reliable enough for discovery; it explicitly grants no later-stage permission. Review must be available through the authorized local channel. Do not attach it to the issue.

Requests explicitly include Paperclip's `allowDeclineReason: true` form default. For retained older requests that omitted it, receipt verification recognizes only the server-added boolean `true`; every other payload field must match exactly. This compatibility rule changes neither candidate bytes nor approval terms.

After the saved acceptance wakes Alex:

```sh
python3 grad-compass-research-engine/scripts/workflow.py freeze CANDIDATE_ID --issue ISSUE_ID --interaction INTERACTION_ID
```

The command reads the interaction from the run-authenticated Paperclip API. It verifies company/issue, human identity, human-only policy, accepted status/outcome, exact payload and digest, then exclusively reserves a frozen directory, writes the exact bytes and receipt read-only, and writes `COMPLETE` last. A saved board card that used the older text-bound confirmation form is accepted only when its full prompt names the candidate's exact version and SHA-256 and every other payload field matches that form; a generic acceptance cannot authorize freeze. Consumers require `COMPLETE`, successful `verify_receipt`, and the recorded human interaction. Pending/rejected/agent/wrong-version/cross-company/superseded approval fails. No receipt file supplied by an agent can authorize production freeze. Synthetic acceptance injection is library-only and rejected in private mode.

A filesystem owner can still chmod or alter files; hashes expose byte mutation, and receipt authenticity relies on the saved Paperclip human interaction. Interrupted freeze leaves an incomplete directory that consumers must reject; Alex investigates locally without destructive automatic cleanup. New corrections reference the prior revision, while frozen bytes remain unchanged. No frozen overwrite or automatic deletion exists.

## Focused verification

```sh
python3 grad-compass-research-engine/scripts/validate.py
python3 -m unittest discover -s grad-compass-research-engine/tests -v
```

Tests require `PAPERCLIP_RUN_SCRATCH_DIR` (or `PAPERCLIP_SCRATCH_DIR`) and use isolated synthetic subdirectories cleaned after each test. They never read real applicant files or invoke the live approval API. Real profile approval remains a T3 human gate.
