# Phase 7.5 Hardening Handoff

## Thread
- Thread ID: `phase75-hardening-2026-03-13`
- Scope: Phase 7.5 hardening only
- Project units after close: `525/600`

## What Closed
- Recovered the missing committed Phase 7 baseline cleanly before any hardening edits.
- Hardened the deterministic Phase 7 benchmark suite without starting Phase 8 or Phase 9.
- Added two more bounded Phase 7 finance cases:
  - `invoice_followup_alias_repeat`
  - `invoice_total_mismatch_hold`
- Strengthened the Phase 7 benchmark harness with:
  - workspace-backed tissue analytics
  - counterfactual case explanations
  - retained-memory and runtime-overhead deltas
  - explicit structural-pressure signals when split or merge remains unexecuted
- Updated the Phase 7 tests, check script, result tables, and project records.

## Local Verification
- `python3 scripts/check_phase7_benchmarks.py`
- Chained locally through that check:
  - `python3 scripts/check_phase6_routing_authority.py`
  - `python3 scripts/check_phase5_memory.py`
  - `python3 scripts/check_phase4_lifecycle.py`
  - `python3 scripts/check_phase3_foundation.py`

## Result Highlights
- Hardened benchmark class metrics:
  - flat baseline accuracy: `0.625`
  - multi-cell no-adapt accuracy: `0.750`
  - multi-cell with adaptation accuracy: `1.000`
- Descriptor reuse now changes two deterministic later cases:
  - `invoice_followup_alias`
  - `invoice_followup_alias_repeat`
- Governed tissue coordination still clearly beats the flat baseline on:
  - `invoice_anomaly_hold`
  - `invoice_total_mismatch_hold`
- Tissue analytics now expose:
  - validation and correction reuse contribution
  - anomaly burden
  - governance burden
  - tissue usefulness and handoff workload
- Resource reporting now exposes:
  - retained memory delta bytes
  - per-tier memory deltas
  - routing decisions per case
  - authority reviews per case
  - structural-pressure signal cases

## Remaining Weaknesses
- Split or merge still does not execute as a benchmarked event in Phase 7.5. The placeholder is now more explicit, but it is still a placeholder.
- Resource usage still comes from bounded AGIF runtime summaries, not a later-phase OS profiler.
- The suite remains short-run and deterministic by design. It does not claim Phase 8 soak coverage or Phase 9 reproducibility closure.

## Next-Thread Guardrails
- Do not increase project units above `525/600` unless the master plan changes.
- Do not silently change the frozen Phase 2 interfaces or the `runner/cell fabric` command contract.
- Do not treat the old repo as a runtime dependency.
- Do not start Phase 8 or Phase 9 work inside this hardening thread.
