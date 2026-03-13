# Phase 7 Tissues And Benchmark Evidence

## Purpose
This note records the local verification used to close Phase 7 for the finance domain tissues and the frozen benchmark classes.

## Deterministic Check
- Command run locally: `python3 scripts/check_phase7_benchmarks.py`
- Result: pass
- Pass token: `AGIF_FABRIC_P7_PASS`

## Regression Chain Also Run Locally
- `python3 scripts/check_phase6_routing_authority.py`
- `python3 scripts/check_phase5_memory.py`
- `python3 scripts/check_phase4_lifecycle.py`
- `python3 scripts/check_phase3_foundation.py`

## What Was Locally Verified
- Real finance tissues now exist in runtime assets and are used in the bounded workflow path:
  - `finance_intake_routing_tissue`
  - `finance_extraction_tissue`
  - `finance_validation_correction_tissue`
  - `finance_anomaly_reviewer_tissue`
  - `finance_workspace_governance_tissue`
  - `finance_reporting_output_tissue`
- The finance workflow now runs end to end through real tissue stages with explicit handoffs:
  - intake classification
  - intake routing
  - extraction
  - normalization
  - correction
  - anomaly review
  - workspace guard
  - governance review
  - reporting
  - output formatting
- Tissue execution uses the existing AGIF layers rather than bypassing them:
  - lifecycle activation and runtime task refs
  - shared workspace state and handoff tracking
  - need-signal recording and resolution
  - authority review for descriptor reuse and reviewer hold decisions
  - reviewed memory promotion and reuse
  - routing decisions for stage-level cell selection
- All three frozen benchmark classes now run deterministically against the same Phase 7 finance cases:
  - flat baseline
  - multi-cell fabric without bounded adaptation
  - multi-cell fabric with bounded adaptation and descriptor sharing
- Replay determinism for the benchmark flow was locally verified by rerunning each benchmark class on fresh local state roots and confirming matching output digests.
- A deterministic follow-up case now shows descriptor reuse changing a later result:
  - case: `invoice_followup_alias`
  - no-adaptation score: `0.375`
  - bounded-adaptation score: `1.000`
  - visible change: prior reviewed correction memory restored the canonical vendor and currency and avoided an unnecessary reviewer hold
- Governed coordination now shows a useful difference from the flat baseline:
  - case: `invoice_anomaly_hold`
  - flat baseline score: `0.625`
  - multi-cell no-adaptation score: `1.000`
  - visible change: anomaly review and governance kept the workflow on hold instead of releasing it
- Result summaries were written locally to:
  - `06_outputs/result_tables/phase7_benchmark_results.md`
  - `06_outputs/result_tables/phase7_benchmark_results.json`

## Phase 7 Result Snapshot
| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat baseline | `0.667` | `1.000` | `0.000` | `0.000` | `0.333` |
| multi-cell fabric without bounded adaptation | `0.792` | `1.000` | `0.000` | `0.667` | `0.000` |
| multi-cell fabric with bounded adaptation | `1.000` | `1.000` | `1.000` | `1.000` | `0.000` |

## Metric Coverage Notes
- Fully measured locally in Phase 7:
  - task accuracy / correctness
  - replay determinism for the benchmark flow
  - descriptor reuse rate
  - improvement from prior descriptors
  - active/logical population ratio
  - governance success rate
  - resource usage
  - bounded forgetting
  - unsafe/misaligned action rate
- Bounded placeholder in Phase 7:
  - split/merge efficiency
    - no benchmark case intentionally triggered a governed split or merge event
    - the result table therefore reports a placeholder value based on lifecycle structural counters instead of claiming a real split/merge benchmark result
- Partial local proxy in Phase 7:
  - memory density gain
    - measured from useful benchmark accuracy relative to retained warm and cold bytes
    - strong enough for Phase 7 comparison
    - not yet a later-phase reproducibility-grade density study

## Remaining Weaknesses
- Split/merge efficiency is still a placeholder metric because the Phase 7 benchmark cases do not intentionally drive governed structural reorganization.
- The benchmark replay claim is based on repeated fresh-state reruns of the same deterministic suite, not on a later-phase long-horizon replay package.
- Memory density gain is measured with a bounded local proxy rather than a full later-phase evidence bundle analysis.
- Phase 7 stays intentionally short-run and deterministic; it does not claim Phase 8 soak behavior, long-run growth stability, or Phase 9 paper/reproducibility closure.

## Assumed Only
- long-run soak behavior beyond the deterministic local checks
- benchmark behavior under larger or noisier finance case sets
- governed split/merge usefulness under sustained structural pressure
- Phase 8 and Phase 9 deliverables
