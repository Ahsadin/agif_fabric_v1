# Phase 8 Long-Run Evidence

## Purpose
This note records three kinds of Phase 8 evidence:
- locally verified bounded harness evidence
- locally inspected real `24h` soak artifacts imported into this workspace
- locally inspected real `72h` soak artifacts imported into this workspace

This note now supports honest Phase 8 closure.

## Machine Roles
- MacBook Air = main development, documentation, and primary target machine.
- MSI = soak machine for long-run endurance evidence.
- The real `24h` and real `72h` soak evidence in this repo came from MSI artifacts.
- Do not describe the imported `24h` or `72h` soak as MacBook Air-only long-run proof.

## Canonical MSI Soak Machine Note
- The explicit machine provenance for the imported long-run runs now lives at `05_testing/MSI_SOAK_MACHINE_NOTE.md`.
- That note records the MSI hardware, Windows environment, Python version, power settings, before-soak verification facts, run roots, artifact sizes, and honest limits.
- It also records the Windows project path `E:\AGIF\agif_fabric_v1` as provenance evidence only, not as a MacBook claim.

## Deterministic Harness Check
- Command run locally: `python3 scripts/check_phase8_soak.py`
- Result: pass
- Harness readiness token: `AGIF_FABRIC_P8_HARNESS_READY`
- Phase pass token: `AGIF_FABRIC_P8_PASS` earned on `2026-03-18`

## Regression Chain Also Run Locally
- `python3 scripts/check_phase7_benchmarks.py`
- `python3 scripts/check_phase6_routing_authority.py`
- `python3 scripts/check_phase5_memory.py`
- `python3 scripts/check_phase4_lifecycle.py`
- `python3 scripts/check_phase3_foundation.py`

## What Was Locally Verified From The Bounded Harness
- A dedicated Phase 8 harness exists with deterministic fixtures under `fixtures/document_workflow/phase8/`.
- The harness supports:
  - repeated finance workflow cycles
  - resumable run manifests
  - bounded stress lanes
  - normalized output summaries
  - long-run profiles for later real `24h` and `72h` execution
- The bounded local validation shows:
  - cold followup alias cycle starts at correctness `0.375`
  - later reviewed-descriptor reuse reaches correctness `1.000`
  - measured descriptor reuse benefit delta: `0.625`
- The bounded local validation also exercises:
  - governed split and merge stress with replay-safe lineage tracking
  - memory saturation pressure with bounded consolidation staying inside caps
  - routing pressure abstain-and-recover behavior
  - trust-risk reactivation veto and quarantine escalation
  - replay plus rollback recovery using recorded lifecycle snapshots
- The bounded validation summaries live at:
  - `06_outputs/run_summaries/phase8_bounded_validation.md`
  - `06_outputs/run_summaries/phase8_bounded_validation.json`

## Real 24h Evidence Basis
- Locally inspected artifact roots:
  - `08_logs/phase8_soak/run_24h/run_manifest.json`
  - `08_logs/phase8_soak/run_24h/run_manifest_interrupt1_240.json`
  - `08_logs/phase8_soak/run_24h/soak_stdout.log`
  - `08_logs/phase8_soak/run_24h/soak_stderr.log`
  - `08_logs/phase8_soak/run_24h/soak_stderr_resume1.log`
  - `08_logs/phase8_soak/run_24h/evidence/`
  - `08_logs/phase8_soak/run_24h/stress/`
- Dedicated real `24h` summary outputs:
  - `06_outputs/run_summaries/phase8_real_24h_soak.md`
  - `06_outputs/run_summaries/phase8_real_24h_soak.json`
- Canonical provenance note:
  - `05_testing/MSI_SOAK_MACHINE_NOTE.md` records the explicit MSI hardware, Windows, interpreter, and power-setting details for this imported run

## Real 24h Soak Validity
- Run profile: `phase8_soak_24h`
- Started: `2026-03-13T20:05:45Z`
- Completed: `2026-03-14T20:08:22Z`
- Duration: `24h 2m 37s`
- Final manifest status: `completed`
- Completed cycles: `989`
- Evidence files present: `989`
- Cycle indexes: contiguous from `1` through `989`
- Stress lanes: all `5` passed
- Resume count: `1`
- Resume recovery count: `1`
- Result digest: `7a13490cdf21bf32a88b8a3d664fa43c84587eac01846a11d40680d3252d2575`
- Recovered interruption observed honestly:
  - `soak_stderr_resume1.log` records `WinError 5` while replacing `run_manifest.json`
  - the interrupted manifest stopped at cycle `240`
  - the final manifest shows recovery and completion after that point

## Real 24h Analysis Snapshot
- Descriptor reuse remained useful across the full `24h` run.
  - descriptor-opportunity cases: `990`
  - reuse-backed opportunity cases: `989`
  - reuse-backed average correctness: `0.979146`
  - the one cold non-reuse opportunity stayed at `0.375`
- Governance stayed useful instead of being bypassed.
  - `invoice_high_value_alias_hold` was reuse-assisted but still held `165/165` times with average correctness `0.875`
  - safe follow-up cases were still accepted
- Memory stayed bounded and disciplined.
  - runtime memory stayed constant at `1507328` bytes
  - final warm memory usage: `5866/8192` bytes
  - final hot memory usage: `451/131072` bytes
  - final ephemeral usage: `40833/131072` bytes
  - raw logs promoted into retained memory: `0`
- Unresolved pressure stabilized.
  - only the first bootstrap cycle had unresolved pressure
  - recurring unresolved count stayed `0` across the full run

## Real 72h Evidence Basis
- Locally inspected artifact roots:
  - `08_logs/phase8_soak/run_72h/run_manifest.json`
  - `08_logs/phase8_soak/run_72h/run_manifest_interrupt1_1622.json`
  - `08_logs/phase8_soak/run_72h/soak_stdout.log`
  - `08_logs/phase8_soak/run_72h/soak_stderr.log`
  - `08_logs/phase8_soak/run_72h/soak_stderr_resume1.log`
  - `08_logs/phase8_soak/run_72h/evidence/`
  - `08_logs/phase8_soak/run_72h/stress/`
  - `08_logs/phase8_soak/run_72h/longrun_runtime_state/`
- Dedicated real `72h` summary outputs:
  - `06_outputs/run_summaries/phase8_real_72h_soak.md`
  - `06_outputs/run_summaries/phase8_real_72h_soak.json`
- Canonical provenance note:
  - `05_testing/MSI_SOAK_MACHINE_NOTE.md` records the explicit MSI hardware, Windows, interpreter, and power-setting details for this imported run

## Real 72h Soak Validity
- Run profile: `phase8_soak_72h`
- Started: `2026-03-14T23:54:31Z`
- Completed: `2026-03-17T23:58:40Z`
- Duration: `72h 4m 9s`
- Final manifest status: `completed`
- Completed cycles: `1690`
- Evidence files present: `1690`
- Cycle indexes: contiguous from `1` through `1690`
- Stress lanes: all `5` passed
- Resume count: `1`
- Result digest: `c14c4ab1161a0537045538e081ca595649423177d5829a8652a64a9e5900f469`
- Recovered interruption observed honestly:
  - `soak_stderr.log` records `WinError 5` while replacing `run_manifest.json`
  - the interrupted manifest stopped at cycle `1622`
  - the final manifest continues through cycle `1690` and finishes `completed`
- Honest bookkeeping caveat:
  - the final manifest leaves `resume_events` empty
  - the final manifest leaves `resume_recovery_count` at `0`
  - the resumed continuation is still locally visible from the interrupted manifest, the stderr logs, and the final completed manifest

## Real 72h Analysis

### What Stayed Strong
- Descriptor reuse remained useful across the full `72h` run.
  - descriptor-opportunity cases: `1689`
  - reuse-backed opportunity cases: `1688`
  - reuse-backed average correctness: `0.979191`
  - the one cold non-reuse opportunity stayed at `0.375`
- The alias-heavy correction path stayed genuinely useful over time.
  - `invoice_followup_alias` improved from one cold hold to `844` later reuse-backed accepted runs with reuse-backed average correctness `1.0`
  - `invoice_followup_alias_repeat` stayed at `1.0` correctness across `563` reuse-backed runs
- Governance stayed useful instead of being bypassed.
  - `invoice_high_value_alias_hold` was reuse-assisted but still held `281/281` times with average correctness `0.875`
  - safe follow-up cases were still accepted, so governance did not become globally blocking
- Memory stayed bounded and disciplined.
  - runtime memory stayed constant at `1507328` bytes
  - final warm memory usage: `5866/8192` bytes
  - final hot memory usage: `451/131072` bytes
  - final ephemeral usage: `40833/131072` bytes
  - raw logs promoted into retained memory: `0`
  - duplicate compression gain reached `5411218` bytes
- Unresolved pressure stayed contained.
  - only the first bootstrap cycle had unresolved pressure
  - recurring unresolved count stayed `0` across the full run

### What Weakened Or Needs Honest Wording
- Memory usefulness efficiency softened rather than improving further.
  - first `100` cycles average value per retained KiB: `0.351529`
  - last `100` cycles average value per retained KiB: `0.342129`
- The manifest-write interruption repeated.
  - the same `WinError 5` pattern seen in the `24h` run reappeared at cycle `1622`
- Resume bookkeeping stayed incomplete.
  - `resume_count` is `1`
  - `resume_events` is empty
  - `resume_recovery_count` stayed `0`
- Lifecycle elasticity should not be overstated from the repeated-cycle lane.
  - long-run cycles stayed structurally stable at `10` active and `1` dormant cell
  - split and merge proof still comes from the stress lanes

### Drift Signals

| Signal | First 100 cycles | Last 100 cycles | Read |
| --- | ---: | ---: | --- |
| Average score | `0.988750` | `0.995000` | slightly stronger later |
| Descriptor reuse rate | `0.695000` | `0.710000` | stable to slightly higher |
| Memory reuse rate | `2.256531` | `2.844780` | higher later |
| Value per retained KiB | `0.351529` | `0.342129` | softened |
| Cycles with unresolved pressure | `1` total | `0` late | stabilized |

### Memory Signals
- Final active descriptors: `7`
- Final archived descriptors: `1969`
- Final promotion rate: `0.369484`
- Final reuse rate: `2.845142`
- Final supersession rate: `0.996457`
- Final stale retirement rate: `0.0`
- Raw log promoted count: `0`
- Duplicate compression gain: `5411218` bytes
- Read plainly: retained memory stayed compact, heavily reused, and review-disciplined over the full `72h` window.

### Governance Signals
- Final long-run authority reviews: `7036`
- Final long-run approvals: `7036`
- Final long-run vetoes inside the repeated-cycle lane: `0`
- Governed reuse hold count: `281`
- Repeated veto pattern count: `0`
- Weak-lineage pattern count: `0`
- Stress-lane governance remained real:
  - `trust_quarantine` passed
  - risky reactivation was vetoed with `AUTHORITY_REACTIVATION_VETO`
  - authority veto count in that stress lane: `2`

### Lifecycle Signals
- Repeated-cycle population stayed stable:
  - active population: `10`
  - dormant population: `1`
  - logical population: `11`
  - active/logical ratio: `0.909091`
- No long-run split/merge thrash was observed in the repeated-cycle lane.
- Stress-lane lifecycle proof stayed intact:
  - `split_merge` passed with two governed split/merge rounds
  - `replay_rollback` passed and restored the pre-quarantine lifecycle state

## Outcome Of The 24h Watch Items
- watch outcome: value per retained KiB softened further, but did not collapse.
  - by thirds, average value per retained KiB was `0.347138`, `0.344886`, and `0.345474`
- watch outcome: the manifest-write interruption did repeat once.
  - this is a real caveat and should stay documented
- watch outcome: unresolved pressure stayed near zero after bootstrap.
- watch outcome: governance stayed correct on the high-value alias hold without becoming more conservative on safe reuse-backed followups.

## Phase 8 Gate Read
- Real `24h` soak evidence complete: `yes`
- Real `72h` soak evidence complete: `yes`
- Soak, replay, rollback, and quarantine checks pass locally: `yes`
- Runtime working set remained at or below `12 GB`: `yes`
  - repeated-cycle runtime stayed at `1507328` bytes
- Total project and evidence footprint remained at or below `35 GB`: `yes`
  - repo footprint measured locally at `477M`
- Result:
  - the Phase 8 exit gate is met
  - `AGIF_FABRIC_P8_PASS` is earned
  - recorded project progress now moves to `570/600`

## What Phase 8 Now Proves
- A real multi-day soak completed on the MSI soak machine and was extracted cleanly into this repo.
- Descriptor reuse remained useful across repeated finance workflow cycles over roughly three days.
- Governance remained active during reuse-heavy cases instead of being bypassed.
- Memory stayed bounded, compact, and review-disciplined during the observed `72h` window.
- Unresolved pressure did not accumulate.
- The fabric remained meaningful, not just alive, because reviewed memory and governance kept changing outcomes through the full observed window.
- This supports the AGIF philosophy of bounded, efficient, governed improvement inside the locked document/workflow proof domain.

## What Still Does Not Prove
- MacBook Air-only long-run endurance
- full lid-close or OS-restart continuity beyond checkpoint-boundary resume evidence
- spontaneous long-run split/merge usefulness outside the stress lanes
- AGI-like generality or broad open-world capability
- final published paper status

## Assumed Only
- MacBook Air-only long-run endurance
- final published paper status
- benchmark outcomes beyond the committed finance-domain proof set
