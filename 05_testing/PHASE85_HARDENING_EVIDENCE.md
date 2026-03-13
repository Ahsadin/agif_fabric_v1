# Phase 8.5 Hardening Evidence

## Purpose
This note records the bounded local verification used to harden the already-open Phase 8 soak and evidence layer without claiming full Phase 8 closure, without earning `AGIF_FABRIC_P8_PASS`, and without raising project progress above `525/600`.

## Phase 7.6 Reconciliation First
- Locally verified in this thread before Phase 8.5 edits:
  - committed Phase 7.6 work already exists in `03fbda5`
  - `git status --short` was clean
  - `python3 scripts/check_phase7_benchmarks.py` passed locally
  - rerunning the Phase 7 benchmark check still left the tracked Phase 7 result files clean locally
- Phase 7.6 state used here: `State B`
  - work already existed
  - work was already committed
  - work was re-verified locally in this thread

## Deterministic Hardening Check
- Command run locally: `python3 scripts/check_phase8_soak.py`
- Result: pass
- Harness readiness token re-verified: `AGIF_FABRIC_P8_HARNESS_READY`
- Phase pass token: not earned

## Regression Chain Also Run Locally
- `python3 scripts/check_phase7_benchmarks.py`
- `python3 scripts/check_phase6_routing_authority.py`
- `python3 scripts/check_phase5_memory.py`
- `python3 scripts/check_phase4_lifecycle.py`
- `python3 scripts/check_phase3_foundation.py`

## What Was Hardened Locally
- Strengthened soak-health visibility over repeated cycles with:
  - descriptor reuse rate over time
  - hold rate over time
  - unresolved pressure counts over time
  - authority approval and veto counts over time
  - memory promotion and stale-retirement signals over time
  - active/logical population ratio over time
- Added bounded drift indicators for:
  - descriptor usefulness
  - routing quality
  - governance intervention
  - memory value per retained KiB
  - recurring unresolved pressure
- Strengthened resume realism with bounded checkpoint-resume checks for:
  - cycle-boundary resume
  - stress-lane resume
  - resume after prior veto and quarantine pressure
- Reconciled Phase 8 with the committed Phase 7.6 benchmark suite by adding:
  - `invoice_high_value_alias_hold`
  - this now shows a reuse-assisted high-value hold inside the long-run repeated mix
- Added clearer long-run analysis with:
  - memory-quality summaries
  - governance-quality summaries
  - failure taxonomy categories
  - clearer blocker reporting for why Phase 8 stays open

## Hardened Bounded Snapshot
| Signal | Locally observed value |
| --- | --- |
| Descriptor reuse benefit delta | `0.625` |
| Descriptor usefulness drift | `0.583333` |
| Governance hold-with-reuse count | `1` |
| Memory value drift | `-0.101407` |
| Resume scenarios passed | `yes` |
| Resource cap stayed bounded | `yes` |

## New Useful Findings
- The bounded long-run layer is now more informative than the earlier harness-only summary because it shows one concrete Phase 7.6-aligned pattern locally:
  - reviewed descriptor reuse improved the high-value alias document
  - governance still kept that document on hold
  - reuse did not bypass the safety hold
- The bounded run also now shows two honest watch areas:
  - memory value softened after the earliest reuse-heavy cycles
  - mixed-pressure cycles still leave unresolved pressure worth watching before real 24h and 72h closure

## Honest Resume Scope
- The new resume checks are locally verified at checkpoint boundaries only:
  - cycle boundary
  - stress-lane boundary
- This is useful and real for the current bounded harness.
- It is not the same as proving a full mid-case crash or full OS restart recovery path.

## Why Phase 8 Still Stays Open
- Real `24h` soak evidence was not completed locally in this thread.
- Real `72h` soak evidence was not completed locally in this thread.
- `AGIF_FABRIC_P8_PASS` is therefore still not earned.
- Project progress stays `525/600`.

## Remaining Weaknesses
- The current resume proof is checkpoint-boundary only, not a full mid-case crash proof.
- Memory value per retained KiB still softens after the strongest early reuse gains.
- The bounded summary is stronger now, but it still does not replace real 24h and 72h machine-time evidence.

## Assumed Only
- real 24h soak completion
- real 72h soak completion
- full Phase 8 closure against the locked falsification thresholds
- Phase 9 paper and reproducibility closure
