# Test Matrix

## Current Local Checks

| Phase | Check | Command | Status |
| --- | --- | --- | --- |
| Phase 3 | Runner and fabric foundation flow | `python3 scripts/check_phase3_foundation.py` | Passed locally on `2026-03-12` |
| Phase 4 | Elastic lifecycle and lineage | `python3 scripts/check_phase4_lifecycle.py` | Passed locally on `2026-03-13` |

## Phase 3 Coverage
- invalid config fails closed
- `runner/cell fabric init` registers the local fabric and blueprints
- `runner/cell fabric status` reports initialized state
- `runner/cell fabric run` accepts workflow JSON on stdin and returns bounded JSON on stdout
- `runner/cell fabric replay` replays the stored deterministic run path
- `runner/cell fabric evidence` writes an evidence bundle and returns pass or fail JSON

## Phase 3 Evidence Note
- `05_testing/PHASE3_FOUNDATION_EVIDENCE.md`

## Phase 4 Coverage
- dormant blueprint storage and activation
- governed split and child inheritance
- governed merge and fail-closed invalid merge veto
- hibernate, reactivate, and retire
- lineage ledger and rollback snapshot history
- burst active population to `48` with automatic return to `24`
- deterministic lifecycle replay

## Phase 4 Evidence Note
- `05_testing/PHASE4_LIFECYCLE_EVIDENCE.md`

## Mandatory Test Groups from the Plan
- interface and schema tests
- lifecycle transition tests
- memory review, promotion, and rejection tests
- routing and need-signal tests
- authority, veto, and approval tests
- benchmark tests
- resource-cap tests
- replay and rollback tests
- soak tests
- evidence-package verification tests
