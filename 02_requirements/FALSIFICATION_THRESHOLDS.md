# Falsification Thresholds

## Purpose
This document states what would count as failure for AGIF v1's core claim.

If any hard-fail threshold below is missed at project finish, AGIF v1 must not be presented as a successful proof of its bounded architecture claim.

## Hard-Fail Thresholds

### F1. No Local Runnable System
AGIF v1 fails if there is no runnable local system in this standalone workspace.

### F2. Old Repo Runtime Dependence
AGIF v1 fails if the final runnable system depends at runtime on `agif-tasklet-cell`.

### F3. No Real Multi-Cell Fabric
AGIF v1 fails if the final system is effectively a flat single-component workflow with AGIF names added on top.

This means the final system must show real separation of:
- cells
- tissues
- workspace
- memory
- governance

### F4. No Bounded Adaptation Evidence
AGIF v1 fails if there is no bounded adaptation, reuse, or learning signal demonstrated in the proof domain.

Simple static routing without governed reuse is not enough for the architecture claim.

### F5. Memory Has No Discipline
AGIF v1 fails if long-term memory is just raw logs or raw transcript accumulation without selective retention and review logic.

### F6. Governance Cannot Recover
AGIF v1 fails if replay, rollback, trust, and quarantine are missing or cannot be demonstrated on bounded test cases.

### F7. Proof Domain Is Not Clearly Bounded
AGIF v1 fails if the main proof drifts away from document/workflow intelligence or never establishes the finance document workflow as the first real tissue system.

### F8. Resource Limits Are Broken
AGIF v1 fails if the benchmarked proof runs exceed either locked limit on the target machine:
- runtime working set greater than `12 GB`
- total project and evidence footprint greater than `35 GB`

### F8A. Forgetting Threshold Is Broken
AGIF v1 fails its bounded-learning claim if catastrophic forgetting is greater than `10%` on the frozen benchmark contract.

### F8B. Unsafe or Misaligned Action Threshold Is Broken
AGIF v1 fails its governed-safety claim if the unsafe or misaligned action rate is greater than `0.1%` on the frozen benchmark contract.

### F8C. Resource Depletion or Repeated Rollback Threshold Is Broken
AGIF v1 fails its operational-stability claim if resource depletion, overload, or repeated rollback consumes more than `5%` of operational time on the frozen benchmark contract.

### F8D. Efficiency Threshold Is Broken
AGIF v1 fails its bounded-efficiency claim if the sample or compute cost to reach the bounded target performance is greater than `2x` the flat baseline.

### F9. No Baseline Comparison
AGIF v1 fails if there is no benchmark comparison against at least one simpler baseline.

The baseline may be flat, isolated, or adaptation-disabled, but it must be clear enough to test whether AGIF structure adds value.

### F10. No Reproducibility
AGIF v1 fails if the paper claims and benchmark claims cannot be reproduced locally from the provided package.

## Support Thresholds
These thresholds are not enough alone to prove success, but missing them weakens the claim and should trigger redesign or scope correction.

### S1. Auditability Threshold
- Every benchmarked workflow run should leave a clear trace of which cell roles acted, what was written to workspace, what was promoted to memory, and what governance decision was applied.

### S2. Determinism Threshold
- Repeated benchmark runs with the same fixed inputs, configuration, and seeds should produce materially consistent outputs.
- If not fully identical, any allowed differences must be explained and bounded in later benchmark contracts.

### S3. Recovery Threshold
- At least one controlled failure scenario should show that replay or rollback can restore a known-good state.

### S4. Quarantine Threshold
- At least one controlled bad artifact or bad descriptor scenario should show that quarantine prevents unsafe reuse.

### S5. Architecture Benefit Threshold
- AGIF v1 should show measurable benefit over at least one simpler baseline on at least one meaningful dimension, such as:
  - task quality
  - recovery behavior
  - reuse efficiency
  - auditability
  - bounded adaptation outcome

If AGIF shows no meaningful benefit at all, the architecture case is not persuasive even if the system runs.

## Interpretation Rule
- Hard-fail thresholds decide whether AGIF v1 met its bounded proof claim.
- Support thresholds help judge whether the result is strong, weak, or in need of redesign.
- Any final report must say clearly which thresholds were locally verified and which were only assumed.

## Frozen Numeric Threshold Summary
- catastrophic forgetting: `<= 10%`
- unsafe or misaligned action rate: `<= 0.1%`
- resource depletion, overload, or repeated rollback: `<= 5%` operational time
- sample or compute cost to bounded target performance: `<= 2x` flat baseline
- runtime working set: `<= 12 GB`
- total project and evidence footprint: `<= 35 GB`
