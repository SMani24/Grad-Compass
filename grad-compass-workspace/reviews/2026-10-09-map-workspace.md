# Map workspace review

## Scope

The first browser interface keeps the map as the main exploration surface, with a list toggle, shared search/country/stage filters, and a university inspector. It uses the existing bundled country geometry and Leaflet rather than adding a frontend framework or remote map service.

The view is a local, read-only synthetic checkpoint. It does not yet consume Research Engine deliveries or expose the original database. Authentication, invitations, editing, applicant materials, CV requests, research requests and catch-up reminders remain on the agreed roadmap. This checkpoint does not imply approval of the design.

## Launch and review

On this Pop!_OS machine: press Super, search **Grad Compass**, and open it. The desktop launcher opens the new interface and shuts down its local server on close. Terminal and browser alternatives are in the application README.

Review these states:

- Explore the map, zoom and select a university pin.
- Switch to the list and open a university's details.
- Combine country, application stage and text filters.
- Find the university without coordinates; it should remain accessible.
- Read saved contacts and the university's linked tasks, including the faculty follow-up task.
- Close the inspector with its button or Escape and navigate the controls by keyboard.
- Resize the window to inspect the narrow layout.

The sample deadlines and campus locations are invented. External sample links deliberately use `example.invalid`.

## Verification

24 Python regression cases and 10 JavaScript cases passed. HTTP smoke checks covered static assets, the bundled map, workspace/detail responses, and rejected writes. Chrome headless checks covered map, list/inspector and mobile layouts. A native Qt window smoke check rendered the map and three sample results, then exited successfully. Dependency consistency and installed desktop-entry validation passed.

A browser rendering check also verified that an HTML-shaped university name remained plain text and a JavaScript portal URL produced no external link. The fixture was restored afterward. Fingerprints of all 145 protected production/cache/research/exchange files matched their original snapshot.

Screenshots use invented data and are local, ignored artifacts: `2026-10-09-map.local.png`, `2026-10-09-list.local.png`, and `2026-10-09-mobile.local.png` in this directory. Automated coverage does not replace the user's keyboard, usability and visual review.

## Feedback pending

The user's first feedback was that the application could not be launched. The obsolete desktop paths have now been corrected and the native launcher added. Layout preferences remain pending: map space, result density, inspector content and overall visual direction should guide the next interface increment.
