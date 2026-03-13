# Phase 7.6 Hardening Evidence

## Purpose
This note records the local verification used to harden the already-closed Phase 7 finance-domain tissues and benchmark system without changing the frozen Phase 2 command surface, without starting Phase 8 soak closure, and without raising progress above `525/600`.

## Deterministic Check
- Command run locally: `python3 scripts/check_phase7_benchmarks.py`
- Result: pass
- Phase pass token re-verified: `AGIF_FABRIC_P7_PASS`

## Regression Chain Also Run Locally
- `python3 scripts/check_phase6_routing_authority.py`
- `python3 scripts/check_phase5_memory.py`
- `python3 scripts/check_phase4_lifecycle.py`
- `python3 scripts/check_phase3_foundation.py`

## What Was Hardened Locally
- Reconciled a real correction-memory reuse weakness:
  - stored correction-memory vendor signatures are now normalized with the same bounded OCR alias cleanup used for live finance inputs
  - this keeps reviewed descriptor reuse available after quantized supersession instead of dropping reuse silently on later alias-heavy cases
- Expanded the deterministic Phase 7 finance suite from five to six bounded cases with:
  - `invoice_high_value_alias_hold`
  - this case is useful because bounded adaptation improves normalized vendor and currency while governance still keeps the workflow on hold for safety
- Strengthened the benchmark outputs with:
  - per-case route-of-custody summaries
  - explicit descriptor and retained-memory detail
  - confidence-aware outcome summaries with support and drag reasons
  - adaptation tradeoff metrics
  - more explicit structural-pressure explanations and future-trigger notes
  - stronger tissue workload, usefulness, and intervention reporting

## Hardened Result Snapshot
| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat baseline | `0.583` | `1.000` | `0.000` | `0.000` | `0.500` |
| multi-cell fabric without bounded adaptation | `0.750` | `1.000` | `0.000` | `0.667` | `0.000` |
| multi-cell fabric with bounded adaptation | `1.000` | `1.000` | `1.000` | `1.000` | `0.000` |

## Stronger Usefulness Evidence
- Descriptor reuse now changes three later deterministic results locally:
  - `invoice_followup_alias`
  - `invoice_followup_alias_repeat`
  - `invoice_high_value_alias_hold`
- The new `invoice_high_value_alias_hold` case makes the coordination path more useful, not just different:
  - the flat baseline auto-releases an unsafe result
  - the no-adaptation fabric keeps the workflow on hold, but leaves the alias-heavy vendor and currency unresolved
  - bounded adaptation reuses reviewed correction memory to restore vendor and currency while governance still keeps the hold in place
- This shows two visible Phase 7.6 facts at once:
  - descriptor reuse improves later document state
  - governance remains active and does not get bypassed by correction memory

## Route-Of-Custody And Confidence Evidence
- The benchmark result tables now show per-case tissue custody through:
  - intake/routing
  - extraction
  - validation/correction
  - anomaly/reviewer
  - workspace/governance
  - reporting/output
- Example local route-of-custody signal for `invoice_high_value_alias_hold`:
  - descriptor detail: `desc_0005` from `mem_0005`
  - retained state: `warm` tier, `595` bytes, `reuse_count=2`
  - need-resolution trail: `uncertainty -> desc_0005 (resolved_well)` and `trust_risk -> authority_00007 (resolved_well)`
  - final confidence summary: `guarded confidence (0.712) with outcome hold/review_required`

## Tissue Analytics Highlights
- Multi-cell with bounded adaptation:
  - `validation/correction`
    - usefulness rate: `1.000`
    - reuse contribution: `3`
    - intervention cases: `3`
  - `workspace/governance`
    - usefulness rate: `1.000`
    - governance burden: `3`
    - intervention cases: `3`
  - `anomaly/reviewer`
    - usefulness rate: `1.000`
    - anomaly burden: `4`
- Multi-cell without bounded adaptation:
  - `validation/correction`
    - usefulness rate: `0.667`
    - reuse contribution: `0`
    - intervention cases: `3`
  - `workspace/governance`
    - usefulness rate: `0.667`
    - governance burden: `5`

## Resource And Tradeoff Highlights
- Multi-cell without bounded adaptation:
  - retained memory delta: `5058` bytes
  - retained memory delta per case: `843.0` bytes
  - governance overhead share: `0.171`
  - structural signal cases: `5`
- Multi-cell with bounded adaptation:
  - retained memory delta: `5877` bytes
  - retained memory delta per case: `979.5` bytes
  - governance overhead share: `0.200`
  - structural signal cases: `3`
- Adaptation tradeoff from no-adapt to with-adapt:
  - accuracy gain: `0.250`
  - extra retained memory cost: `819` bytes
  - accuracy gain per retained KiB: `0.312576`
  - extra authority overhead per case: `0.333`

## Structural-Adaptation Status
- Split or merge still does not execute as a measured benchmark event in Phase 7.6.
- The placeholder is now more explicit and locally verified:
  - with adaptation, structural signal cases are:
    - `invoice_anomaly_hold`
    - `invoice_high_value_alias_hold`
    - `invoice_total_mismatch_hold`
  - current no-action reason:
    - reviewer and governance pressure appeared
    - active population stayed at `10/24`
    - lifecycle split counters remained zero
  - current future trigger:
    - repeated reviewer pressure plus active population at or above `24` with non-zero lifecycle split counters

## Remaining Weaknesses
- Split or merge still remains placeholder-heavy in the Phase 7 benchmark flow. The Phase 7.6 pass makes that placeholder more explicit and honest, but it does not claim a real split or merge efficiency result.
- Resource reporting still comes from bounded AGIF runtime summaries, not a later-phase OS profiler.
- The suite is still intentionally short-run and deterministic. This note does not claim Phase 8 soak completion or Phase 9 paper-grade reproducibility.
