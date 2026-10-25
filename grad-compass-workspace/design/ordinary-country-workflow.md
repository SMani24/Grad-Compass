# Ordinary country delivery and confirmed dispatch

APP-021. Consumer owner: Codex. Producer/compatibility: Marry. Execution: Dave;
research/editorial/photograph provenance: Discovery; exact content review: Alex.
Public exchange 1.0.0 stays unchanged. Existing private package 0.2, evidence map
0.2, editorial 0.1 and finalized notices remain compatible.

## Research and report readiness

A result's `completion` describes response delivery, not report readiness.
An ordinary country request also needs canonical detailed Markdown, independently
written concise Markdown, the exact canonical/edition/evidence/result bindings,
seven-topic coverage and actual separate canonical/edition/human receipts.
Use the existing consumer contract and Marry's ordinary-country producer guide.
The consumer never constructs a concise edition or missing prose from a coverage
label. Interim findings stay readable; Dave owns preparation/review/publication.

Structured finding `coverage` can use the same seven topic keys and explained
state/detail/applicable_year/evidence_refs values as prepared package metadata.
Legacy free text remains scope text. Malformed structured statements get explicit
validation notes and unknown coverage. Missing topics remain unknown. An incoming
reference such as `FRA-01` must not be mapped to a source array by its position:
without an explicit received evidence-key binding it remains visibly unbound.
Prepared evidence-map keys bind their exact original source records as before.
A coverage statement does not prove exhaustive research or factual acceptance.

Source title and publisher are preserved where supplied; locator, URL, observation
date, source revision and qualifications are retained. The consumer owns rendering
one grouped source inventory; writers supply references instead of another list.
Retained original source-context documents remain available without rewriting them.

## Ordinary photographic asset

Use existing `assets[]` entries: kind `photo`, relative_path, exact byte sha256,
media_type (JPEG/PNG), caption, alt, credit, source_url and license. The sha256
is the stable local asset identity; originals are retained privately/offline.
Compatible optional additions: `creator`, HTTPS `license_url`, and `crop` with
numeric `x`/`y` in [0,1] specifying the focal point. Screen and PDF use that focal
point with layout-appropriate aspect ratios. Credits/source/license links and the
crop/resize notice accompany the image. A flag is a separate decorative element.
No quantitative/locational research claim is inferred from a photograph.

Optional metadata `asset_delivery` has `state` available/unavailable/not_yet_published
and `reason` for missing delivery. Available requires a bundled photo; a missing
photo needs a concrete reason, not silent success. Historical packages without the
addition remain readable with a compact photo-unavailable fallback. New ordinary
producer acceptance requires the photo or a recorded retrieval/licensing failure.
Discovery sources accurate, legally reusable material; Marry validates its exact
membership and publishes a new immutable package notice, preserving prior versions
and annotations. Codex handles safe decode, local retention, rendering and export.

## Explicit confirmed dispatch

Confirmation shows exact countries, stage, intake, resource/scope limits and the
approved Applicant Profile reference (IDs, digest, human approval receipt only).
Cancellation cannot invoke an agent. The app persists a digest-bound draft before confirmation, then stores the exact immutable request
and export before making an invocation attempt. Server-only local connection
configuration and optional environment token never enter JavaScript or exports.

`POST /api/companies/{companyId}/issues`, assigned to Dave, is the supported local
Paperclip creation endpoint. The installed server accepts `idempotencyKey`, takes
a PostgreSQL company/key advisory transaction lock, and records the issue/key in
the same transaction. Key retention is **seven days**. Use the same digest-bound
key on every retry, independently of title matching. Local outbox operations also
hold a cross-process exclusive lock and fsync state before sending. Store returned
task ID separately from Dave's research acknowledgement and content review.

Lost-ack retries reconcile the exact request marker and use that same atomic key.
After a seven-day uncertain attempt, reconcile only; do not create another task
if no exact match can be established. No background/reconnect dispatch. Pending
requests persist until explicit retry/cancel. Only unattempted pending drafts are
editable; confirmation creates a new explicit draft revision/immutable replacement
request with lineage, retaining prior history. Uncertain tasks must reconcile first;
accepted work uses an explicit follow-up/amendment, never an in-place edit.

## Acceptance

Use isolated fake Paperclip HTTP transport for unavailable service, cancellation,
concurrent clicks, lost acknowledgement, restart, revision and profile isolation.
No real agent task is created by those checks. Verify an unconfigured-country
package and partial findings through normal receipt/render/export. For Main-Apply,
receive the existing France authored/reviewed package and DEU/CAN photographs
normally, check both editions/coverage/source titles/images/native exports and
restart/replay, preserve all original private bytes and actual review states.

Later asset/review metadata for the same canonical content is ordered by an
app-owned immutable-receipt sequence (`report-delivery-order.json`), after exact
canonical revision/review time. Replay never bumps the sequence; earlier metadata
and cached PDFs remain selectable through their exact pins. This adds no producer
wire field. Ordinary backups retain this sequence, the pending outbox, export
preferences and the server-only connection/reference settings.
