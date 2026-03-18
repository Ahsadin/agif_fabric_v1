# Progress Tracker

## Fixed Denominator
- Total extension denominator: `130`

## Phase Weights
| Extension gate | Units | Status |
| --- | --- | --- |
| Setup and freeze | 15 | Complete and locally verified |
| Gap 1 organic split or merge proof | 35 | Not yet earned |
| Gap 2 skill graph and transfer-governance proof | 35 | Not yet earned |
| Gap 3 POS domain and cross-domain transfer proof | 45 | Not yet earned |

## Counting Rule
- Units are awarded only when the full gate for that extension block is closed.
- Creating scaffolding and plans does not earn units by itself.
- Root AGIF v1 progress remains frozen at `600/600` and must not be changed by this tracker.

## Current Recorded Progress
- Completed units: `15`
- Progress now: `15/130`
- Percent complete: `11.5%`
- Basis: the setup-and-freeze gate is closed because the Track B docs now freeze the denominator, token set, dependency order, root tracker isolation, Gap 1 start rules, and Gap 3 comparison rules, and `python3 scripts/check_v1x_setup.py` passes locally.

## Current Status
- Project scaffold exists.
- Local source-of-truth files are mutually consistent.
- `AGIF_FABRIC_V1X_SETUP_PASS` is earned.
- Root AGIF v1 remains frozen at `600/600`.
