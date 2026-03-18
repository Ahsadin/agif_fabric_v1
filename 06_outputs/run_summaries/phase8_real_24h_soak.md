# Phase 8 Real 24h Soak Summary

## Status

| Field | Value |
| --- | --- |
| Profile | `phase8_soak_24h` |
| Start | `2026-03-13T20:05:45Z` |
| End | `2026-03-14T20:08:22Z` |
| Duration | `24h 2m 37s` |
| Manifest status | `completed` |
| Machine | MSI soak machine |
| Completed cycles | `989` |
| Evidence files | `989` |
| Resume count | `1` |
| Resume recovery count | `1` |
| Stress lanes | `5/5 passed` |
| Result digest | `7a13490cdf21bf32a88b8a3d664fa43c84587eac01846a11d40680d3252d2575` |

## Machine Roles
- MacBook Air = main development, documentation, and primary target machine.
- MSI = soak machine for long-run endurance evidence.
- This real `24h` soak came from MSI artifacts imported into this repo.
- This summary does not claim MacBook Air-only long-run proof.

## Evidence Basis
- Locally verified from run files in this workspace:
  - `08_logs/phase8_soak/run_24h/run_manifest.json`
  - `08_logs/phase8_soak/run_24h/run_manifest_interrupt1_240.json`
  - `08_logs/phase8_soak/run_24h/soak_stdout.log`
  - `08_logs/phase8_soak/run_24h/soak_stderr.log`
  - `08_logs/phase8_soak/run_24h/soak_stderr_resume1.log`
  - `08_logs/phase8_soak/run_24h/evidence/`
  - `08_logs/phase8_soak/run_24h/stress/`
- Canonical provenance note:
  - `05_testing/MSI_SOAK_MACHINE_NOTE.md` records the explicit MSI hardware, Windows environment, Python version, power settings, and honest limits for this run family.

## Validity
- The run is valid as a completed real `24h` soak artifact set.
- Why:
  - manifest status is `completed`
  - completed cycle count is `989`
  - there are `989` cycle evidence files
  - cycle indexes are contiguous from `1` through `989`
  - all five stress lanes report `passed`
- The one interruption was recoverable, not fatal:
  - `soak_stderr_resume1.log` records a `WinError 5` permission error while replacing `run_manifest.json`
  - the interrupted manifest stopped at cycle `240`
  - the final manifest records `resume_count: 1` and `resume_recovery_count: 1`
  - the resumed run completed all `989` cycles
- Honest limit:
  - this proves one recovered checkpoint-boundary interruption
  - it does not prove full OS restart or lid-close recovery

## Key Metrics
- Approximate throughput:
  - `41.134` cycles per hour
  - `82.267` cases per hour
- Outcome quality:
  - average cycle score: `0.994154`
  - accepted cases: `1153`
  - hold cases: `825`
- Descriptor reuse:
  - descriptor-opportunity cases: `990`
  - reuse-backed opportunity cases: `989`
  - reuse-backed average correctness: `0.979146`
  - cold non-reuse average correctness: `0.375`
  - governed reuse hold count: `165`
- Memory and resource bounds:
  - runtime memory stayed constant at `1507328` bytes
  - final retained memory bytes: `5866`
  - final reviewed descriptor count: `7`
  - final duplicate compression gain: `3168394` bytes
- Need pressure:
  - final need signal count: `7`
  - final unresolved signal count: `0`

## What Stayed Strong
- Descriptor reuse remained useful across the full `24h` run.
  - `invoice_followup_alias` improved from one cold `0.375` hold to `494` later reuse-backed accepted runs with average correctness `0.998737`
  - `invoice_followup_alias_repeat` stayed at `1.0` correctness across `330` reuse-backed runs
- Governance remained meaningful.
  - `invoice_high_value_alias_hold` was reuse-assisted but still held `165/165` times with average correctness `0.875`
  - safe follow-up cases still cleared normally, so governance did not freeze the whole fabric
- Memory stayed bounded and disciplined.
  - warm memory ended at `5866/8192` bytes
  - hot memory ended at `451/131072` bytes
  - ephemeral memory ended at `40833/131072` bytes
  - raw logs promoted to retained memory: `0`
- Pressure handling stayed clean after bootstrap.
  - only `1` cycle showed unresolved pressure
  - recurring unresolved pressure count stayed `0` across the whole run

## What Weakened Or Needs Watching
- Memory usefulness efficiency softened slightly.
  - average value per retained KiB moved from `0.351529` over the first `100` cycles to `0.347148` over the last `100`
  - this is a watch item, not a failure
- The recovered interruption should still be treated as a watch item.
  - it recovered cleanly this time
  - it should not repeat during the live `72h` soak
- Lifecycle elasticity should not be overstated from this run.
  - the repeated-cycle lane stayed structurally stable at `10` active and `1` dormant cell
  - split and merge proof still comes from the stress lanes, not from organic long-run structural change

## Drift Signals

| Signal | First 100 cycles | Last 100 cycles | Read |
| --- | ---: | ---: | --- |
| Average score | `0.988750` | `0.994687` | slightly stronger later |
| Descriptor reuse rate | `0.695000` | `0.707500` | stable to slightly higher |
| Memory reuse rate | `2.256531` | `2.839226` | higher later |
| Value per retained KiB | `0.351529` | `0.347148` | slight softening |
| Cycles with unresolved pressure | `1` total | `0` late | stabilized |

## Memory Signals
- Active descriptors stayed bounded at `7`.
- Archived descriptors reached `1152`, while only `7` stayed active.
- Final supersession rate reached `0.993103`.
- Final promotion rate was `0.370134`.
- Final reuse rate was `2.841242`.
- Final stale retirement rate was `0.0`.
- Read plainly: the memory system kept compact active state, reused retained knowledge heavily, and did not promote raw logs into long-term memory.

## Governance Signals
- Final long-run authority reviews: `4124`
- Final long-run approvals: `4124`
- Final long-run vetoes inside the repeated-cycle lane: `0`
- Repeated veto pattern count: `0`
- Weak-lineage pattern count: `0`
- Stress-lane governance still mattered:
  - `trust_quarantine` passed
  - risky reactivation was vetoed with `AUTHORITY_REACTIVATION_VETO`
  - authority veto count in that stress lane: `2`

## Lifecycle Signals
- Repeated-cycle population stayed stable:
  - active population: `10`
  - dormant population: `1`
  - logical population: `11`
  - active/logical ratio: `0.909091`
- Long-run repeated cycles did not show uncontrolled split, merge, or oscillation.
- Stress-lane lifecycle proof stayed intact:
  - `split_merge` passed with two governed split/merge rounds
  - `replay_rollback` passed and restored the pre-quarantine state

## What This Run Proves Now
- A real `24h` soak completed on the MSI soak machine and was extracted cleanly into this repo.
- Descriptor reuse stayed useful over time and kept affecting real finance workflow outcomes.
- Governance remained active during reuse-heavy cases instead of being bypassed.
- Memory stayed bounded, compact, and review-disciplined during the observed `24h` window.
- Unresolved pressure stabilized instead of accumulating.
- The fabric remained meaningful, not just alive, because memory reuse and governance kept changing outcomes in a controlled way.
- This supports the AGIF philosophy of bounded, efficient, governed improvement inside the locked document/workflow proof domain.

## What Was Still Open At 24h Analysis Time
- At the time of this `24h` summary, Phase 8 was still open because the real `72h` soak was not finished and extracted yet.
- At the time of this `24h` summary, `AGIF_FABRIC_P8_PASS` was still not earned.
- At the time of this `24h` summary, progress stayed `525/600`.
- This run does not prove:
  - MacBook Air-only long-run endurance
  - multi-day drift behavior beyond about one day
  - full OS restart or lid-close continuity
  - spontaneous long-run split/merge usefulness outside the stress lanes

## Later Closure Note
- Later update on `2026-03-18`:
  - the real `72h` soak completed on the MSI soak machine
  - Phase 8 closed honestly
  - `AGIF_FABRIC_P8_PASS` was earned
  - recorded progress moved to `570/600`
  - the canonical machine-provenance note now lives at `05_testing/MSI_SOAK_MACHINE_NOTE.md`

## 72h Watch Items That Were Later Checked
- watch during `72h` soak: memory value per retained KiB
- watch during `72h` soak: repeat of the manifest-write interruption
- watch during `72h` soak: unresolved pressure recurrence after the `24h` mark
- watch during `72h` soak: whether governance stays correct on the high-value alias hold without becoming more conservative on safe reuse-backed followups
