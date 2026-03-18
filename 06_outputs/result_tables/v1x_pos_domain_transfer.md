# V1X POS Domain Transfer Results

Locally verified deterministic benchmark summary for Track B Gap 3.

## Run Summary

| Run | Cross-Domain Transfer Enabled | Mean Case Score | Approved Transfers | Denied Transfers | Abstained Transfers | Counted Influence | Governance-Disabled Vetoes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| transfer_enabled | yes | 1.000 | 3 | 1 | 1 | 2 | 0 |
| control | no | 0.600 | 0 | 4 | 1 | 0 | 3 |

## Case Comparison

| Case ID | Control Action | Control Score | Enabled Action | Enabled Score | Enabled Transfer Status | Explicit Approval | Counted Influence | Approval Ref |
| --- | --- | ---: | --- | ---: | --- | --- | --- | --- |
| northwind_settlement_alias_hold | manual_review | 0.000 | hold_for_finance_review | 1.000 | approved | yes | yes | authority_00003 |
| northwind_settlement_known_repeat_hold | hold_for_finance_review | 1.000 | hold_for_finance_review | 1.000 | approved | yes | no | authority_00004 |
| tailspin_refund_missing_explicit | manual_review | 1.000 | manual_review | 1.000 | denied | no | no | none |
| unknown_vendor_low_quality_abstain | approve_close | 1.000 | approve_close | 1.000 | abstained | yes | no | none |
| tailspin_refund_pattern_reused | approve_close | 0.000 | manual_review | 1.000 | approved | yes | yes | authority_00005 |

## Enabled Audit Trail

| Case ID | Transfer Status | Source Descriptor | Source Domain | Review Ref | Veto Conditions | Source Payload Ref | Transfer Approval Ref |
| --- | --- | --- | --- | --- | --- | --- | --- |
| northwind_settlement_alias_hold | approved | desc_0001 | finance_ap | authority_00003 | none | memory/warm/payloads/mem_0001.json | authority_00003 |
| northwind_settlement_known_repeat_hold | approved | desc_0001 | finance_ap | authority_00004 | none | memory/warm/payloads/mem_0001.json | authority_00004 |
| tailspin_refund_missing_explicit | denied | desc_0002 | finance_ap | none | none | none | none |
| unknown_vendor_low_quality_abstain | abstained | desc_0001 | finance_ap | none | none | none | none |
| tailspin_refund_pattern_reused | approved | desc_0002 | finance_ap | authority_00005 | none | memory/warm/payloads/mem_0002.json | authority_00005 |

## Acceptance

| Check | Passed |
| --- | --- |
| Bounded 5-case POS suite is frozen | yes |
| Same case sequence in both runs | yes |
| Control disables transfer at governance | yes |
| Finance-origin descriptor improves a POS result | yes |
| Cross-domain influence requires explicit approval | yes |
| POS proof is useful and auditable | yes |
| Overall pass | yes |

## Causal Improvement Cases

| Improved Case IDs |
| --- |
| northwind_settlement_alias_hold, tailspin_refund_pattern_reused |
