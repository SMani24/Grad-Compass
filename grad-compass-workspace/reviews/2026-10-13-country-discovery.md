# Map discovery increments · 2026-10-13

## 1. Promoted synthetic research in discovery

A read-only app projection connects committed importer outcomes to cards/List and university details. Namespaced local identities preserve existing map IDs and producer IDs/revisions without merging separate databases by name. Only promoted institutions and their promoted programs are projected; the unreferenced seed and staged records stay out. Coordinates are never guessed from country/city. The v1 fixture therefore adds a card/table row and program details, with no new pin.

Demonstrated in disposable map/exchange storage before beginning the exploration selector: select → stage → explicit mapping → dry run → approve → institution appears in cards/List → program opens in its parent details → replay preserves four distinct discovery IDs and makes no duplicate changes. Existing country/history/selection checks passed. App suite: 37 Python cases; JavaScript suites: 14 cases. Local screenshot: `2026-10-13-exchange-promoted-discovery.local.png`.

APP-006 in the ignored mailbox proposes country-evidence compatibility requirements to Marry/Dave. It requests a separately versioned future envelope; it does not change public exchange 1.0.0 or authorize real data. The user bridges the mailbox manually.

## 2. Independent exploration and presentation choices

Added Countries / Universities inside the existing left panel, while Map/List remains in the floating top bar. Universities remains the initial exploration mode. Countries can be searched by name/code, selected from cards or polygons, framed on the map, and compared in List. A zero-university country remains present; counts describe saved coverage rather than suitability. Mode, view, filters and selection participate in existing history. Application-stage filters are hidden in Countries mode.

Demonstrated this increment before adding country evidence: Countries → France card → framed/highlighted country with zero saved universities → List → Universities → Back/Forward restores exploration/presentation/country context. Existing native navigation checks and nine discovery JavaScript cases passed. Local captures: `2026-10-13-exchange-countries-{map,list}.local.png`.

## 3. Country evidence and personal decisions

Country cards/polygons now open country details in the existing right panel. App-owned invented briefs for Canada, Germany and France show summaries, reserved example sources, observation/revision metadata and explicit uncertainties. Other displayed countries report missing research; no producer status is invented. Demo evidence is labelled unreviewed and does not constitute a real country-data handoff.

Personal decisions (Considering, Shortlisted, On hold, Excluded) are saved separately in an ignored `country-decisions.json` within the marked preview runtime, using atomic writes and a lock. Reads do not create it. Unlinked-path checks and session/origin/payload validation apply. Decisions do not modify evidence review, application stages, importer data or map DB bytes. Excluded countries remain selectable.

Demonstrated before adding the country-to-university action: France card/polygon → evidence → Shortlisted → mode history restores details and choice → genuine page reload retains choice → Excluded still leaves country accessible. App Python suite: 39 cases; JavaScript suites: 15 cases; Qt input suite: three cases. Local capture: `2026-10-13-exchange-country-evidence.local.png`.
