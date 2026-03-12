# Progress Tracker

## Fixed Denominator
- Total project denominator: `600` units

## Counting Rule
- Progress units are awarded only when a full phase is closed against its acceptance gate.
- Partial work inside a later phase does not earn partial units unless the plan is updated explicitly.
- Placeholder files created early to satisfy the plan do not count as phase completion by themselves.

## Current Recorded Progress
- Completed units: `225`
- Progress now: `225/600`
- Percent complete: `37.5%`
- Basis: Phase 0 bootstrap, Phase 1 requirements freeze, Phase 2 architecture freeze, and Phase 3 runner and fabric foundation are complete.

## Verification Status
- Locally verified:
  - required project directories exist
  - required root source-of-truth files exist
  - required admin files exist
  - required planning files exist
  - locked phase weights are recorded exactly
  - no runtime code was added in this bootstrap thread
  - Phase 1 requirement files exist
  - scope, proof boundary, and falsification rules are written down
  - the finance workflow proof domain is explicitly bounded in writing
  - all six Phase 2 design docs exist in `03_design/`
  - the frozen interfaces are written clearly with the required field names
  - lifecycle states and transition rules are written clearly
  - the CLI contract is frozen in writing
  - the benchmark classes and metrics are frozen in writing
  - the Phase 2 gate checklist is marked complete
  - no runtime implementation files were changed in the Phase 2 thread
  - Phase 3 runner foundation exists locally
  - `runner/cell fabric init`, `run`, `status`, `replay`, and `evidence` exist locally
  - deterministic Phase 3 fixtures exist locally
  - `python3 scripts/check_phase3_foundation.py` passes locally
  - `AGIF_FABRIC_P3_PASS` is earned and recorded in `05_testing/PASS_TOKENS.md`
- Assumed only:
  - all later phases
  - runtime behavior beyond the Phase 3 foundation
  - benchmark outcomes
  - paper results

## Phase Status
| Phase | Units | Status |
| --- | --- | --- |
| Phase 0 | 20 | Complete and locally verified |
| Phase 1 | 40 | Complete and locally verified |
| Phase 2 | 80 | Complete and locally verified |
| Phase 3 | 85 | Complete and locally verified |
| Phase 4 | 80 | Not started |
| Phase 5 | 95 | Not started |
| Phase 6 | 65 | Not started |
| Phase 7 | 60 | Not started |
| Phase 8 | 45 | Not started |
| Phase 9 | 30 | Not started |
