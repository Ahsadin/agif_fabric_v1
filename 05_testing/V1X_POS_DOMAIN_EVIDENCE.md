# V1X POS Domain Evidence

## Purpose
- This note records the honest Track B Gap 3 proof target for the bounded POS domain and causal cross-domain transfer path.

## Gap 3 Frozen Acceptance Path
- Use exactly `5` deterministic POS cases.
- Run the transfer-enabled and control paths on the same `5` cases in the same order.
- Disable cross-domain transfer in the control run at the governance level.
- Count cross-domain influence only when there is explicit `transfer_approval`.
- Show at least one POS result that improves because of a finance-origin transferred descriptor.
- Keep the proof useful and auditable instead of turning it into a stub.

## Commands Run Locally
- `python3 -m unittest discover -s 05_testing -p 'test_v1x_pos_domain.py'`
- `python3 scripts/check_v1x_pos_domain.py`

## What Was Locally Verified
- The Gap 3 fixture suite is frozen at exactly `5` ordered POS cases under `fixtures/pos_operations/v1x/`.
- The transfer-enabled and control runs use the exact same `5` cases in the exact same order.
- The control config disables cross-domain transfer at the governance level through `cross_domain_transfer_enabled: false`.
- The control run records `3` governance-disabled transfer vetoes and `0` counted cross-domain influence events.
- The transfer-enabled run records:
  - `3` approved governed cross-domain transfers with explicit provenance
  - `1` missing-explicit-approval denial
  - `1` low-quality abstain
- Finance-origin descriptors causally improve `2` POS results:
  - `northwind_settlement_alias_hold`
  - `tailspin_refund_pattern_reused`
- The missing-explicit case stays non-influential:
  - case: `tailspin_refund_missing_explicit`
  - result: denied
  - counted cross-domain influence: `0`
- The low-quality case stays non-influential:
  - case: `unknown_vendor_low_quality_abstain`
  - result: abstained
  - counted cross-domain influence: `0`

## Result Snapshot
| Run | Mean case score | Approved transfers | Denied transfers | Abstained transfers | Counted influence | Governance-disabled vetoes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| transfer_enabled | `1.000` | `3` | `1` | `1` | `2` | `0` |
| control | `0.600` | `0` | `4` | `1` | `0` | `3` |

## Causal Improvement Cases
- `northwind_settlement_alias_hold`
  - control action: `manual_review`
  - transfer-enabled action: `hold_for_finance_review`
  - approval ref: `authority_00003`
- `tailspin_refund_pattern_reused`
  - control action: `approve_close`
  - transfer-enabled action: `manual_review`
  - approval ref: `authority_00005`

## Auditability Notes
- Every counted improvement carries:
  - source descriptor ID
  - source memory ID
  - source payload ref
  - transfer approval ref
- The control-only governance blocks are visible through authority veto conditions:
  - `cross_domain_transfer_disabled_by_governance`

## Outputs Written Locally
- `06_outputs/result_tables/v1x_pos_domain_transfer.md`
- `06_outputs/result_tables/v1x_pos_domain_transfer.json`

## Safety Checks Also Re-Run Locally Before Closure
- `python3 scripts/check_v1x_setup.py`
- `python3 scripts/check_v1x_skill_graph.py`
- `python3 scripts/check_phase9_closure.py`
- Root AGIF v1 progress still reads `600/600`

## Honest Caveats
- This proof is still limited to `5` deterministic POS cases.
- The support scores here are deterministic bounded scoring units, not wall-clock throughput measurements.
- This Gap 3 result does not reopen root AGIF v1 and does not change the root `600/600` closure record.
- This thread does not start bundle close and does not earn `AGIF_FABRIC_V1X_PASS`.
- This Gap 3 result still does not claim AGI or broad open-world generality.
