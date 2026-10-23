# Reader and export composition

APP-019 · 23 October 2026 · `grad-compass-report-composition-1.0`.

This is a compatible Markdown composition convention for existing private package 0.2, notice 0.1, response 0.1.0 and standalone editorial 0.1. Public exchange 1.0.0 is unchanged. No extra wire field, country installation step or inferred applicant profile is needed.

## Ownership

| Material | Owner | Consumer behavior |
| --- | --- | --- |
| Detailed research, concise narrative, applicant implications, cost/funding comparisons, questions | Discovery, coordinated by Dave | Render supplied content; never synthesize an edition or eligibility conclusion |
| Source records, locators, dates, applicable years, coverage, evidence precision | Discovery; Marry validates exact handoff bindings | Preserve qualifications and reference relationships |
| Independent exact-edition research/editorial dispositions | Alex | Read the selected document's version-bound receipt, not historical narrative assertions |
| Release and current metadata delivery | Dave / Marry | Validate and receive automatically; receipt is not factual or human acceptance |
| Source-list rendering, composition, screen/PDF/Markdown, private annotations | Codex | One public source inventory per rendition; inline references open supplied mappings |
| Request preferences and approved profile/brief resolution | Dave's private workflow | Consume supplied implications; never copy private intake/briefs into exports |

Producer execution contract: `grad-compass-research-engine/docs/ordinary-country-reports.md` (Marry). Discovery owns its actual research/editorial templates; Alex owns independent review instructions. This consumer convention supplements those documents, not their editorial judgment.

## Minimal content

A normal package supplies complete detailed Markdown in `canonical_document`, separately written concise Markdown in `reader_editorial`, a structured evidence map with exact original finding source records, all seven coverage topics, dates, exact request/result/finding/document/map bindings and actual review/human states. Existing field validation rejects missing structural fields and invalid references. A populated schema does not establish useful research, applicant relevance or readability.

Both editions share the canonical origin, but have independent exact hashes and receipts. Supply applicant implications only where the brief supports them; otherwise state the affected uncertainty. National/regional facts, degree types, costs and conditions belong in data. No Germany/Canada/Belgium title branch exists in composition.

Suggested substantive outline (adapt to actual scope; not a required section count):

```markdown
# Country report

## At a glance
Useful findings, main opportunities and obstacles, and their implications. [ABC-01]

## Cost and funding comparison
Supported comparison with currency, period, coverage, conditions and next checks.

## Study routes and language
Evidence → request relevance → conditions → next action.

## Work and residence conditions
## Application timing
## Questions and next steps
```

Keep applicable years, observed guidance versus target-year unknowns, funding conditions, calculations and unresolved conflicts beside their claims. Do not put raw coverage codes, current workflow instructions, UUIDs or hashes in reader prose. Avoid repeating full source records: use existing inline `[ABC-01]` / `[E01]` references. The consumer owns the single rendered source list. Sources remain at their actual supplied finding/topic precision, never promoted to claim-level support.

Explicit operational headings `Coverage`, `Seven-topic coverage`, `Research coverage`, `Sources`, `Source guide`, `Sources and evidence precision`, `Source guide and evidence precision`, `Evidence map binding`, `Report context`, `Technical provenance`, `Technical details`, `Report details` are secondary. Subheadings inherit the operational role until a heading of the same/higher level. Unknown headings remain substantive. Legacy preambles are retained as historical context. Heading-derived section IDs and existing text-derived block IDs do not change when presentation changes.

## Shared renditions

`web/report_composition.py` derives the versioned roles from immutable Markdown; `report_content.py` retains all blocks and attaches composition/source inventory. Screen and PDF render the same substantive sections, preserving supplied order and references. Coverage is in Report details, using human labels. Current review uses the selected exact document receipt; canonical/edition differences, scope, historical review and human approval remain accessible in details. Legacy source-context paragraphs are explicitly historical, not a second current status.

The PDF uses the producer's concise edition, a modest optional image/flag, compact current review/date and natural pagination. It appends one deduplicated source list and brief report details. Missing imagery is valid. It does not pad to a target page count. New renderer versions produce new cached PDFs; old PDF hashes/pages and annotations remain available.

Detailed Markdown starts with original substantive Markdown, then one inventory of full public URLs and distinct original source records. Evidence references retain topic/locator/qualification relationships and refer to that inventory. A compact appendix retains operational context, all stable passage IDs, coverage, observation/version/review provenance and applicable historical evidence-map notes. This is an export projection, not a rewrite of canonical bytes. Full original payloads remain private and immutable. Annotation export is an explicit off-by-default choice, bound to the selected report/version.

New immutable content creates a new revision; old annotations and reading positions stay attached to their exact original version. Content is not silently retagged or transferred. No automatic agent invocation or additional approval stage is introduced.
