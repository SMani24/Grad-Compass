# Shared reader and export acceptance

APP-019. Verification completed 24 October; handoff recorded 25 October 2026.
Consumer implementation: `dd7be28`, `4f3a33f`, `13de9ac`, `9e784a3`.
Producer/review documentation: `251f63d`, `ede123b`.

## Reusable behavior

One composition service classifies substantive research, coverage, source context
and operational metadata without changing original document bytes or passage
identities. Overview, full report, PDF and detailed Markdown use that composition.
Coverage and version relationships belong in Report details; the selected edition's
actual bound review is authoritative, while older narrative statements remain
historical context. Unknown headings and partial findings remain readable.

The app owns the grouped public-source inventory, retaining distinct records,
locators, dates and supplied qualifications. Public narrative links without evidence
bindings remain explicitly unmapped. Detailed Markdown starts with substantive
research, retains original evidence context, and places transport/review identities
in an appendix. The reader PDF uses supplied concise text and natural pagination.
Annotations remain an explicit, off-by-default export option. Earlier generated
PDFs and their annotations are preserved when the renderer changes.

The [consumer template](../design/country-report-template.md) and
[handoff contract](../design/country-report-contract.md) define ownership and
compatible Markdown conventions. Marry owns the producer execution guide,
Discovery the editorial template, and Alex the independent review guide under
`grad-compass-research-engine/docs/`. No public exchange 1.0.0 or private schema
migration was required. Applicant implications are supplied research, never
inferred by a country-specific app branch.

## Real delivery and normal-app acceptance

Marry published the revised Germany and Canada packages notice-last under their
existing Main-Apply requests. Ordinary startup receipt received them; default,
country-card and country-selector navigation opened the intended prepared reports.

| Country | Existing request | Bound response | Selected report / overview | Recorded review |
| --- | --- | --- | --- | --- |
| Germany | `74c2ad44-3ab4-4646-b21f-e65417ac048e` | r3 | v11 / r11 | Canonical and reader bounded pass |
| Canada | `648f0137-a074-4173-a4ab-15be6c7dcdc3` | r2 | v11 / r11 | Canonical and reader bounded pass |
| Belgium regression | `41b6af76-f27e-4c58-a3a8-b835101658f0` | r2 | unchanged v3 / r3 | Existing canonical and reader pass |

Human approval remains unknown and underlying country findings remain pending.
Response delivery, country coverage, report preparation and exact-edition review
remain separate. The app-owner metadata bridge mechanically recorded Alex's
confirmed review in new immutable copies; Alex read them back and Marry released
and published them. Original documents, maps and metadata were retained.

The receiver correction permits bounded non-synthetic country-conditions revisions
on the same existing result sequence after a complete response. It validates exact
request/predecessor digests, fresh changed finding/record revisions and review
bindings. Other scopes and pinned synthetic restrictions remain intact.

## Evidence

- 155 Python tests and all three JavaScript regression files passed. Focused
  composition/revision tests cover partial legacy prose, nested administrative
  sections, rich source notes, source-table relationships, unmapped links, exact
  review/annotation/position identities, valid revisions and rejected bindings.
- Actual native Main-Apply PDF and Markdown downloads agree with selected
  content/origin hashes. A second native process produced identical receipts and
  downloads. Inbox/catalog errors were absent. Explicit historical findings remain
  accessible with honest labels.
- Two replay scans received zero new items with no errors. All 270 protected
  original artifact/overlay bytes and timestamps remained unchanged; research
  history was unchanged.
- All seven final PDF pages were visually inspected: Germany two, Canada two,
  Belgium three. Text remains selectable and within page bounds, source links are
  retained, and tables/branding remain readable. Standalone Markdown preserves
  substantive sections, public URLs, evidence references, dates, calculations and
  qualifications alongside compact current and historical provenance.
- An invented NZL package used normal receive/render/export paths in isolated
  storage, including missing imagery, partial coverage, sources, comment restart
  persistence and twelve width/text-size combinations. Revision/reading-position
  and nonempty annotation tests remain isolated. Main-Apply's owner annotations
  were not modified; its probe suppressed only reading-position writes.

Private evidence, screenshots, exact hashes and both example export types are
indexed in [the local acceptance record](../runtime/report-composition-review-2026-10-24/review.local.md).
They are excluded from Git. No private reports, research fixtures, annotations or
applicant artifacts are added by this acceptance note.

## Owner walkthrough

Reopen the normal **Grad Compass** desktop launcher, use **Main-Apply**, choose
Germany or Canada and select **Read country report**. Overview opens concise
research; Full report opens detailed content. Export offers reader PDF and detailed
Markdown for the selected package. Report details shows scope, actual review and
revision relationships. Historical findings remain available. No new request,
manual JSON import or agent invocation is needed to read these received reports.
