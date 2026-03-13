# Phase 7.5 Hardening Evidence

## Purpose
This note records the local verification used to harden the already-closed Phase 7 benchmark system without changing the project units or starting Phase 8.

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
- The deterministic Phase 7 finance suite was expanded from three cases to five bounded cases.
- Added harder deterministic cases:
  - `invoice_followup_alias_repeat`
    - a second descriptor-reuse case
    - harder OCR alias and missing-currency path
  - `invoice_total_mismatch_hold`
    - a correction-sensitive arithmetic anomaly case
    - useful for reviewer and governance comparison
- The benchmark outputs now include explicit counterfactual notes for each case:
  - what the flat baseline missed
  - what the multi-cell no-adaptation class improved
  - what bounded adaptation improved
- Tissue-level analytics are now recorded from the real workspace and stage outputs:
  - tissue usefulness rate
  - stage workload
  - handoff counts
  - anomaly burden
  - governance burden
  - descriptor reuse contribution
- Resource reporting is now stronger but still bounded:
  - retained memory delta bytes
  - per-tier memory deltas
  - active population cost estimate
  - routing decisions per case
  - authority reviews per case
  - need signals per case
- Split or merge still does not execute as a benchmarked event in Phase 7, but the placeholder is now more explicit:
  - structural-pressure signal cases are listed directly
  - candidate tissues for future governed split review are named when pressure appears

## Hardened Result Snapshot
| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat baseline | `0.625` | `1.000` | `0.000` | `0.000` | `0.400` |
| multi-cell fabric without bounded adaptation | `0.750` | `1.000` | `0.000` | `0.600` | `0.000` |
| multi-cell fabric with bounded adaptation | `1.000` | `1.000` | `1.000` | `1.000` | `0.000` |

## Stronger Usefulness Evidence
- Descriptor reuse now changes two later deterministic results locally:
  - `invoice_followup_alias`
  - `invoice_followup_alias_repeat`
- In both cases:
  - the flat baseline missed vendor and currency normalization and released the workflow anyway
  - the no-adaptation fabric preserved tissue coordination but still held for review
  - bounded adaptation reused reviewed correction memory and returned the workflow to the correct accepted state
- Governed tissue coordination still clearly beats the flat baseline on hold behavior:
  - `invoice_anomaly_hold`
  - `invoice_total_mismatch_hold`
- In both hold cases the flat baseline auto-released a risky output, while the tissue path kept the workflow on hold for review.

## Tissue Analytics Highlights
- Multi-cell with bounded adaptation:
  - `finance_validation_correction_tissue`
    - usefulness rate: `1.000`
    - reuse contribution: `2`
  - `finance_workspace_governance_tissue`
    - usefulness rate: `1.000`
    - governance burden: `2`
  - `finance_anomaly_reviewer_tissue`
    - usefulness rate: `1.000`
    - anomaly burden: `3`
- Multi-cell without bounded adaptation:
  - `finance_validation_correction_tissue`
    - usefulness rate: `0.733`
    - reuse contribution: `0`
  - `finance_workspace_governance_tissue`
    - usefulness rate: `0.600`
    - governance burden: `4`

## Resource Highlights
- Multi-cell without bounded adaptation:
  - retained memory delta: `4215` bytes
  - routing decisions per case: `12.0`
  - authority reviews per case: `2.0`
  - structural-pressure signal cases: `4`
- Multi-cell with bounded adaptation:
  - retained memory delta: `5032` bytes
  - routing decisions per case: `12.0`
  - authority reviews per case: `2.0`
  - structural-pressure signal cases: `2`
- These values stay inside the bounded local Phase 7 proof and do not claim full OS-level profiling.

## Remaining Weaknesses
- Split or merge still remains unexecuted in the Phase 7 benchmark flow. The hardening pass improves the placeholder by naming signal cases and candidate tissues, but it does not claim a real split or merge efficiency result.
- Resource usage still uses bounded runtime summaries from the AGIF layers, not a later-phase OS profiler or full reproducibility package.
- The suite is still intentionally short-run and deterministic. It does not claim Phase 8 soak coverage, long-run growth stability, or Phase 9 paper-grade reproducibility.
