# Phase 8 Real 72h Soak Summary

## Status

| Field | Value |
| --- | --- |
| Profile | `phase8_soak_72h` |
| Start | `2026-03-14T23:54:31Z` |
| End | `2026-03-17T23:58:40Z` |
| Duration | `72h 4m 9s` |
| Manifest status | `completed` |
| Machine | MSI soak machine |
| Completed cycles | `1690` |
| Evidence files | `1690` |
| Resume count | `1` |
| Resume recovery count | `0` in the final manifest bookkeeping |
| Stress lanes | `5/5 passed` |
| Result digest | `c14c4ab1161a0537045538e081ca595649423177d5829a8652a64a9e5900f469` |

## Machine Roles
- MacBook Air = main development, documentation, and primary target machine.
- MSI = soak machine for long-run endurance evidence.
- This real `72h` soak came from MSI artifacts imported into this repo.
- This summary does not claim MacBook Air-only long-run proof.

## Evidence Basis
- Locally verified from run files in this workspace:
  - `08_logs/phase8_soak/run_72h/run_manifest.json`
  - `08_logs/phase8_soak/run_72h/run_manifest_interrupt1_1622.json`
  - `08_logs/phase8_soak/run_72h/soak_stdout.log`
  - `08_logs/phase8_soak/run_72h/soak_stderr.log`
  - `08_logs/phase8_soak/run_72h/soak_stderr_resume1.log`
  - `08_logs/phase8_soak/run_72h/evidence/`
  - `08_logs/phase8_soak/run_72h/stress/`
  - `08_logs/phase8_soak/run_72h/longrun_runtime_state/`
- Context or inference:
  - "MSI soak machine" comes from the verified project state plus the Windows artifact paths captured in the run files, such as `E:\AGIF\agif_fabric_v1` and `C:\Python313`.

## Validity
- The run is valid as a completed real `72h` soak artifact set.
- Why:
  - manifest status is `completed`
  - completed cycle count is `1690`
  - there are `1690` cycle evidence files
  - cycle indexes are contiguous from `1` through `1690`
  - all five stress lanes report `passed`
- The one interruption was recoverable, not fatal:
  - `soak_stderr.log` records a `WinError 5` permission error while replacing `run_manifest.json`
  - the interrupted manifest stopped at cycle `1622`
  - the final manifest continues through cycle `1690` and finishes `completed`
- Honest caveat:
  - the final manifest leaves `resume_events` empty and `resume_recovery_count` at `0`
  - the resumed continuation is still locally visible from the interrupted manifest, the stderr logs, and the final completed manifest

## Key Metrics
- Approximate throughput:
  - `23.450` cycles per hour
  - `46.872` cases per hour
- Outcome quality:
  - average cycle score: `0.994434`
  - accepted cases: `1970`
  - hold cases: `1408`
- Descriptor reuse:
  - descriptor-opportunity cases: `1689`
  - reuse-backed opportunity cases: `1688`
  - reuse-backed average correctness: `0.979191`
  - cold non-reuse average correctness: `0.375`
  - governed reuse hold count: `281`
- Memory and resource bounds:
  - runtime memory stayed constant at `1507328` bytes
  - final retained memory bytes: `5866`
  - final reviewed descriptor count: `7`
  - final duplicate compression gain: `5411218` bytes
  - repo footprint measured locally: `477M`
- Need pressure:
  - final need signal count: `7`
  - final unresolved signal count: `0`

## What Stayed Strong
- Descriptor reuse remained useful across the full `72h` run.
  - `invoice_followup_alias` improved from one cold `0.375` hold to `844` later reuse-backed accepted runs with reuse-backed average correctness `1.0`
  - `invoice_followup_alias_repeat` stayed at `1.0` correctness across `563` reuse-backed runs
- Governance remained meaningful.
  - `invoice_high_value_alias_hold` was reuse-assisted but still held `281/281` times with average correctness `0.875`
  - safe follow-up cases still cleared normally, so governance did not freeze the whole fabric
- Memory stayed bounded and disciplined.
  - warm memory ended at `5866/8192` bytes
  - hot memory ended at `451/131072` bytes
  - ephemeral memory ended at `40833/131072` bytes
  - raw logs promoted to retained memory: `0`
- Pressure handling stayed clean after bootstrap.
  - only `1` cycle showed unresolved pressure
  - recurring unresolved pressure count stayed `0` across the whole run

## What Weakened Or Needs Honest Wording
- Memory usefulness efficiency softened.
  - average value per retained KiB moved from `0.351529` over the first `100` cycles to `0.342129` over the last `100`
  - this is a real softening, not a collapse
- The manifest-write interruption repeated.
  - the same `WinError 5` pattern from the `24h` run reappeared at cycle `1622`
- Resume bookkeeping stayed incomplete.
  - `resume_count` is `1`
  - `resume_events` is empty
  - `resume_recovery_count` stayed `0`
- Lifecycle elasticity should not be overstated from this run.
  - the repeated-cycle lane stayed structurally stable at `10` active and `1` dormant cell
  - split and merge proof still comes from the stress lanes, not from organic long-run structural change

## Drift Signals

| Signal | First 100 cycles | Last 100 cycles | Read |
| --- | ---: | ---: | --- |
| Average score | `0.988750` | `0.995000` | slightly stronger later |
| Descriptor reuse rate | `0.695000` | `0.710000` | stable to slightly higher |
| Memory reuse rate | `2.256531` | `2.844780` | higher later |
| Value per retained KiB | `0.351529` | `0.342129` | softened |
| Cycles with unresolved pressure | `1` total | `0` late | stabilized |

## Memory Signals
- Active descriptors stayed bounded at `7`.
- Archived descriptors reached `1969`, while only `7` stayed active.
- Final supersession rate reached `0.996457`.
- Final promotion rate was `0.369484`.
- Final reuse rate was `2.845142`.
- Final stale retirement rate was `0.0`.
- Read plainly: the memory system kept compact active state, reused retained knowledge heavily, and did not promote raw logs into long-term memory.

## Governance Signals
- Final long-run authority reviews: `7036`
- Final long-run approvals: `7036`
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

## Phase 8 Closure Read
- The locked Phase 8 gate is now met.
- Why:
  - bounded harness check passes locally
  - real `24h` soak is complete and analyzed
  - real `72h` soak is complete and analyzed
  - soak, replay, rollback, and quarantine checks all pass
  - runtime working set stayed far below `12 GB`
  - repo footprint stayed far below `35 GB`
- Result:
  - `AGIF_FABRIC_P8_PASS` is earned
  - recorded project progress now moves to `570/600`

## What This Run Proves Now
- A real `72h` soak completed on the MSI soak machine and was extracted cleanly into this repo.
- Descriptor reuse stayed useful over time and kept affecting real finance workflow outcomes across roughly three days.
- Governance remained active during reuse-heavy cases instead of being bypassed.
- Memory stayed bounded, compact, and review-disciplined during the observed `72h` window.
- Unresolved pressure stabilized instead of accumulating.
- The fabric remained meaningful, not just alive, because memory reuse and governance kept changing outcomes in a controlled way.
- This supports the AGIF philosophy of bounded, efficient, governed improvement inside the locked document/workflow proof domain.

## What Still Remains Outside This Proof
- MacBook Air-only long-run endurance
- full OS restart or lid-close continuity beyond checkpoint-boundary resume evidence
- spontaneous long-run split/merge usefulness outside the stress lanes
- AGI-like generality or broad open-world capability
- Phase 9 paper or reproducibility closure
