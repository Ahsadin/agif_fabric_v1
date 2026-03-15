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

## Real 24h Soak Result
- A real 24h soak run is now present locally under:
  - `08_logs/phase8_soak/run_24h/`
- Source machine for this run:
  - MSI soak machine
- Run profile:
  - `phase8_soak_24h`
- Target duration:
  - `24` hours
- Started:
  - `2026-03-13T20:05:45Z`
- Completed:
  - `2026-03-14T20:08:22Z`
- Final manifest status:
  - `completed`
- Completed cycle count:
  - `989`
- Resume count:
  - `1`
- Resume recovery count:
  - `1`
- Result digest:
  - `7a13490cdf21bf32a88b8a3d664fa43c84587eac01846a11d40680d3252d2575`
- Failure cases still recorded honestly:
  - `expected governed failure: AUTHORITY_REACTIVATION_VETO`

## Why Phase 8 Stays Open
- Real `24h` soak evidence is now completed locally and extracted into the project.
- Real `72h` soak evidence is still not completed locally.
- `AGIF_FABRIC_P8_PASS` is therefore not earned.
- Project progress stays `525/600`.

## Remaining Weaknesses
- The current proof now includes a real completed `24h` soak, but not yet the real `72h` soak needed for honest Phase 8 closure.
- The current bounded summary shows a useful descriptor-reuse trend, but memory density does not yet show a monotonic improvement claim across every repeated cycle.
- The harness and resume path are now exercised by a completed `24h` run, but multi-day continuity is still not proven until the actual `72h` run completes locally.

## Assumed Only
- real 72h soak completion
- full Phase 8 closure against the locked falsification thresholds
- Phase 9 paper and reproducibility closure
