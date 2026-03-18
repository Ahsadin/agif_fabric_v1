# V1X Organic Load Evidence

## Purpose
- This note records the local verification used to close Track B Gap 1 without reopening the closed root AGIF v1 phase history.
- The proof target here is narrow:
  - one deterministic finance stream of `40` cases
  - one elastic run
  - one governance-disabled no-split control run
  - same case order, same tissues, same active start, same caps

## Commands Run Locally
- `python3 -m unittest discover -s 05_testing -p 'test_v1x_organic_load.py'`
- `python3 scripts/check_v1x_organic_load.py`

## What Was Locally Verified
- The Track B Gap 1 fixture stream is frozen at exactly `40` ordered cases under `fixtures/document_workflow/v1x/finance_organic_load/`.
- The frozen mix is:
  - `20` alias-heavy
  - `10` novelty-heavy
  - `10` recovery-tail
- The elastic and control runs use the exact same ordered `40`-case stream.
- Both runs start from the same dormant state and use the same steady active cap `10` and burst cap `12`.
- The control run keeps bounded adaptation enabled but disables split at the governance level.
- One organically triggered, authority-approved split occurs inside the deterministic stream:
  - case: `alias_006_northwind_high_value_a`
  - proposer: `tissue:finance_validation_correction_tissue:organic_monitor`
  - approver: `governance:phase7_local_board`
  - lineage chain: `finance_correction_specialist -> finance_correction_specialist__child_001, finance_correction_specialist__child_002`
  - active population changed from `10` to `11`
  - logical population changed from `11` to `13`
- After the split, the finance workflow actually uses the split child inside the correction stage:
  - first post-split child use: `alias_007_northwind_followup_e`
  - selected correction cell: `finance_correction_specialist__child_001`
- The elastic run later records a merge during post-stream recovery:
  - survivor: `finance_correction_specialist__child_001`
  - retired branch: `finance_correction_specialist__child_002`
  - active population changed from `11` to `9`
- The elastic run then cools all remaining active cells back to `0`, which matches the starting active level.

## Result Snapshot
| Run | Accuracy | Mean queue age | Mean end-to-end latency | Split events | Merge events | Max active population | Active after settle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| elastic | `0.725` | `0.300` | `8.050` | `1` | `1` | `11` | `0` |
| control | `0.725` | `16.800` | `24.550` | `0` | `0` | `10` | `0` |

## Usefulness Signal
- Post-split accuracy stayed flat versus control:
  - elastic post-split accuracy: `0.757353`
  - control post-split accuracy: `0.757353`
- Post-split queue age improved materially:
  - elastic post-split queue age: `0.058824`
  - control post-split queue age: `19.470588`
- Post-split end-to-end latency improved materially:
  - elastic post-split latency: `7.823529`
  - control post-split latency: `27.235294`
- Overhead versus usefulness remained favorable:
  - extra authority reviews in elastic: `2`
  - extra lifecycle events in elastic: `5`
  - extra correction worker units in elastic: `34`
  - mean queue-age gain versus control: `16.500`
  - mean latency gain versus control: `16.500`

## Important Metric Interpretation
- The queue-age and end-to-end latency numbers are locally verified deterministic queue-model units, not measured wall-clock latency.
- The queue model is frozen in the Gap 1 fixture set and uses the same arrival timing for both runs.
- The only capacity difference allowed in that model is the governance-approved elastic split in the correction stage.

## Outputs Written Locally
- `06_outputs/result_tables/v1x_finance_organic_load.md`
- `06_outputs/result_tables/v1x_finance_organic_load.json`

## Safety Checks Also Re-Run Locally Before Closure
- `python3 scripts/check_v1x_setup.py`
- `python3 scripts/check_phase9_closure.py`
- Root AGIF v1 progress still reads `600/600`

## Honest Caveats
- This proof is still limited to the bounded finance workflow domain.
- The queue-age and latency improvement here is a deterministic modeled workload-pressure comparison, not a hardware-timed throughput benchmark.
- This Gap 1 result does not change the closed root AGIF v1 claim set.
- This Gap 1 result does not claim AGI, open-world generality, or proof outside the finance workflow benchmark path.
