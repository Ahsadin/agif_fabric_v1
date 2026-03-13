# Phase 8 Long-Run Evidence

## Purpose
This note records the local verification completed for the Phase 8 soak harness and bounded long-run validation pass.

This note does **not** claim that Phase 8 is fully closed.

## Deterministic Harness Check
- Command run locally: `python3 scripts/check_phase8_soak.py`
- Result: pass
- Harness readiness token: `AGIF_FABRIC_P8_HARNESS_READY`
- Phase pass token: not earned

## Regression Chain Also Run Locally
- `python3 scripts/check_phase7_benchmarks.py`
- `python3 scripts/check_phase6_routing_authority.py`
- `python3 scripts/check_phase5_memory.py`
- `python3 scripts/check_phase4_lifecycle.py`
- `python3 scripts/check_phase3_foundation.py`

## What Was Locally Verified
- A dedicated Phase 8 harness now exists with deterministic fixtures under `fixtures/document_workflow/phase8/`.
- The harness supports:
  - repeated finance workflow cycles
  - resumable run manifests
  - bounded stress lanes
  - normalized output summaries
  - `caffeinate`-ready long-run profiles for later real 24h and 72h execution
- The bounded local validation now exercises repeated workflow learning cycles against the real finance Phase 7 tissue path:
  - cold followup alias cycle starts at correctness `0.375`
  - later reviewed-descriptor reuse reaches correctness `1.000`
  - measured descriptor reuse benefit delta: `0.625`
- The bounded local validation also exercises:
  - governed split and merge stress with replay-safe lineage tracking
  - memory saturation pressure with bounded consolidation staying inside caps
  - routing pressure abstain-and-recover behavior
  - trust-risk reactivation veto and quarantine escalation
  - replay plus rollback recovery using recorded lifecycle snapshots
- The current bounded validation summaries were written locally to:
  - `06_outputs/run_summaries/phase8_bounded_validation.md`
  - `06_outputs/run_summaries/phase8_bounded_validation.json`

## Bounded Validation Snapshot
| Signal | Locally observed value |
| --- | --- |
| Descriptor reuse benefit delta | `0.625` |
| Max active/logical ratio in repeated cycles | `0.909` |
| Runtime bytes during repeated cycles | `1507328` |
| Resource cap stayed bounded | `yes` |
| Memory pressure lane passed | `yes` |
| Routing pressure lane passed | `yes` |
| Trust/quarantine lane passed | `yes` |
| Replay/rollback lane passed | `yes` |

## Failure Cases Recorded Honestly
- Expected governed failure: `AUTHORITY_REACTIVATION_VETO`
  - the low-trust router reactivation path was blocked before unsafe reuse
- The `reuse_mix` cycle still shows hold behavior on alias-heavy documents after other pressure accumulated.
  - this is useful evidence for bounded governance pressure
  - it is not yet enough to call Phase 8 complete

## Why Phase 8 Stays Open
- Real `24h` soak evidence was not completed locally in this thread.
- Real `72h` soak evidence was not completed locally in this thread.
- `AGIF_FABRIC_P8_PASS` is therefore not earned.
- Project progress stays `525/600`.

## Remaining Weaknesses
- The current proof is still a bounded short-run validation, not a completed long-duration soak.
- The current bounded summary shows a useful descriptor-reuse trend, but memory density does not yet show a monotonic improvement claim across every repeated cycle.
- The harness is ready for real long soaks, but lid-close, restart, and multi-day continuity are still assumed until the actual 24h and 72h runs are executed locally.

## Assumed Only
- real 24h soak completion
- real 72h soak completion
- full Phase 8 closure against the locked falsification thresholds
- Phase 9 paper and reproducibility closure
