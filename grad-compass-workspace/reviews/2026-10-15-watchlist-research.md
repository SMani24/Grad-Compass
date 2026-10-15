# Watchlist and manual research milestone · 2026-10-15

## Increment 1 — watchlist and private notes

Country details/cards/List now offer watch/unwatch independently of personal decisions. Countries mode has an All countries / My watchlist filter and multi-country research selection. Selection is shared between cards and List; filtering does not silently drop selected countries, while unwatching removes that country from the pending selection. Private notes are explicitly saved and survive unwatching.

State lives in a separately marked, Git-excluded `research.sqlite` under the marked synthetic preview runtime. The original map DB is read-only. Existing personal decisions remain in their separate state file. Unknown country/invalid watch/note payloads, linked files and unmarked state are rejected.

Demonstrated France with no universities → watch → private note → Shortlisted assessment → watch Canada → My watchlist → select both for research. App tests: 43 passing cases. Native navigation and watchlist checks passed. Local capture: `2026-10-15-research-watchlist.local.png`.

APP-007 was appended early to the manual mailbox with provisional private request/ack/result/feedback and separately versioned country-evidence proposals. APP-006 and APP-007 await Marry/Dave compatibility feedback. Only app-owned synthetic adapters are being implemented; public exchange/importer files are unchanged.

## Increment 2 — immutable requests and remembered preferences

The request form collects shared preferences inline on first use and shows a compact editable summary thereafter. Blank values remain unknown; countries/scope/limits/context stay request-specific. Successful deliberate submissions remember explicit shared values unless Only for this request is checked. Cancelled forms make no preference writes. Each request retains its own immutable snapshot and optional exact parent/result references. Retrying the same submission cannot duplicate or silently change a request.

Prepared requests remain local, without invented agent progress. A manual export creates an immutable request file in the ignored synthetic runtime and a minimal opaque-ID/state index. The copyable prompt points to the private file and exact request binding without echoing preferences/context. Original map DB/config/profile remain untouched. App-only synthetic acknowledgement/result/feedback persistence and versioned fixture adapters are scaffolded behind the provisional APP-007 proposal; their review interface follows in increment 3.

Demonstrated: first form cancelled → unknown preferences unchanged → first submitted request → reference-only private handoff → prefilled next form → cancelled edit unchanged → request-only alternative submission → autofill still uses remembered values. App tests: 47 passing cases. Captures: `2026-10-15-research-{first-request,request-handoff,prefilled-request}.local.png`.
