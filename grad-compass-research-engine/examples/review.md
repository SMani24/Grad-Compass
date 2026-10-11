# Synthetic applicant A — review

Schema: 1.0.0 · Profile: synthetic-a · Revision: revision-a1 · Name: synthetic-a-v1 · State: draft

All contents are invented. This is a format example, not an actual applicant review.

| Claim | Field | Kind | Value | Evidence / derivation |
| --- | --- | --- | --- | --- |
| degree | education.degree | documented_fact | Bachelor of History | src-transcript, page 1 |
| year-a | education.completion_year | documented_fact | 2024 | src-transcript, page 1 |
| year-b | education.completion_year | documented_fact | 2023 | src-cv, Education section |
| year-conflict | education.completion_year | conflict | Unknown | year-a disagrees with year-b |
| location | preferences.delivery | preference | remote | src-answer, answer 1 |
| budget | preferences.budget | unknown | Not supplied | No explicit answer |
| recency | education.recent_completion | inference | true | Either reported year is within five years of 2026; this does not resolve the year |

Consolidated questions: Which completion year is correct, and what evidence supports it? If budget is needed for a later authorized purpose, what budget and currency should be recorded? No financial preference has been inferred.

Unresolved: conflicting completion dates; missing budget. No prior revision. Approval is pending; this draft authorizes no later activity.

# Synthetic applicant B — revision example

Schema: 1.0.0 · Profile: synthetic-b · Revision: revision-b2 · Parent: revision-b1 · Name: synthetic-b-v2 · State: frozen synthetic candidate

| Claim | Field | Kind | Value | Evidence |
| --- | --- | --- | --- | --- |
| degree-b | education.degree | user_report | Diploma in Culinary Arts | src-answer-b, answer 1 |
| role-b | experience.role | user_report | Pastry supervisor | src-correction, answer 1 |
| grade-b | education.grade | unknown | Not supplied | Transcript missing; request it if grade is required |

Change: role corrected from Kitchen supervisor to Pastry supervisor. The prior draft remains unchanged. Grade remains unknown and is explicitly accepted only within this invented approval scenario. `approval-receipt.json` binds the exact bytes of `applicant-b-frozen.json` and records a simulated human acceptance; no real approval exists. Scope is profile only, with no discovery authorization.
