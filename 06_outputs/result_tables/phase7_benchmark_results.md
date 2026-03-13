# Phase 7 Benchmark Results

- Artifact note: runtime timestamp omitted and temp evidence paths normalized for deterministic reruns.

## Class Metrics

| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat_baseline | 0.625 | 1.000 | 0.000 | 0.000 | 0.400 |
| multi_cell_without_bounded_adaptation | 0.750 | 1.000 | 0.000 | 0.600 | 0.000 |
| multi_cell_with_bounded_adaptation | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |

## Case Comparison

| Case | Flat baseline | Multi-cell no adapt | Multi-cell with adapt | Descriptor reuse mattered | Why it mattered |
| --- | ---: | ---: | ---: | --- | --- |
| invoice_seed_reference | 0.875 | 1.000 | 1.000 | no | real tissues preserved a safer bounded path than the flat baseline |
| invoice_followup_alias | 0.500 | 0.375 | 1.000 | yes | reviewed descriptor reuse restored vendor or currency context from prior memory |
| invoice_followup_alias_repeat | 0.500 | 0.375 | 1.000 | yes | reviewed descriptor reuse restored vendor or currency context from prior memory |
| invoice_anomaly_hold | 0.625 | 1.000 | 1.000 | no | real tissues kept the document on hold instead of flat auto-release |
| invoice_total_mismatch_hold | 0.625 | 1.000 | 1.000 | no | real tissues kept the document on hold instead of flat auto-release |

## Resource And Control

| Benchmark class | Active/logical ratio | Runtime bytes | Retained memory delta bytes | Routing decisions/case | Authority reviews/case | Structural signal cases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| flat_baseline | 0.000 | 0 | 0 | 0.000 | 0.000 | 0 |
| multi_cell_without_bounded_adaptation | 0.909 | 1507328 | 4215 | 12.000 | 2.000 | 4 |
| multi_cell_with_bounded_adaptation | 0.909 | 1507328 | 5032 | 12.000 | 2.000 | 2 |

## Counterfactual Notes

| Case | Flat baseline missed | No adapt improved | With adapt improved |
| --- | --- | --- | --- |
| invoice_seed_reference | governance_action | improved governance_action | no material improvement |
| invoice_followup_alias | governance_action, normalized_currency, normalized_vendor, reviewer_status | no material improvement | improved final_status, governance_action, normalized_currency, normalized_vendor, reviewer_status |
| invoice_followup_alias_repeat | governance_action, normalized_currency, normalized_vendor, reviewer_status | no material improvement | improved final_status, governance_action, normalized_currency, normalized_vendor, reviewer_status |
| invoice_anomaly_hold | final_status, governance_action, reviewer_status | improved final_status, governance_action, reviewer_status | no material improvement |
| invoice_total_mismatch_hold | final_status, governance_action, reviewer_status | improved final_status, governance_action, reviewer_status | no material improvement |

## Tissue Analytics

| Benchmark class | Tissue | Usefulness | Stage workload | Handoffs | Anomaly burden | Governance burden | Reuse contribution |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_cell_without_bounded_adaptation | finance_intake_routing_tissue | 1.000 | 10 | 5 | 0 | 0 | 0 |
| multi_cell_without_bounded_adaptation | finance_extraction_tissue | 1.000 | 5 | 10 | 0 | 0 | 0 |
| multi_cell_without_bounded_adaptation | finance_validation_correction_tissue | 0.733 | 10 | 10 | 0 | 0 | 0 |
| multi_cell_without_bounded_adaptation | finance_anomaly_reviewer_tissue | 0.600 | 5 | 10 | 5 | 0 | 0 |
| multi_cell_without_bounded_adaptation | finance_workspace_governance_tissue | 0.600 | 10 | 10 | 0 | 4 | 0 |
| multi_cell_without_bounded_adaptation | finance_reporting_output_tissue | 0.600 | 10 | 5 | 0 | 0 | 0 |
| multi_cell_with_bounded_adaptation | finance_intake_routing_tissue | 1.000 | 10 | 5 | 0 | 0 | 0 |
| multi_cell_with_bounded_adaptation | finance_extraction_tissue | 1.000 | 5 | 10 | 0 | 0 | 0 |
| multi_cell_with_bounded_adaptation | finance_validation_correction_tissue | 1.000 | 10 | 10 | 0 | 0 | 2 |
| multi_cell_with_bounded_adaptation | finance_anomaly_reviewer_tissue | 1.000 | 5 | 10 | 3 | 0 | 0 |
| multi_cell_with_bounded_adaptation | finance_workspace_governance_tissue | 1.000 | 10 | 10 | 0 | 2 | 0 |
| multi_cell_with_bounded_adaptation | finance_reporting_output_tissue | 1.000 | 10 | 5 | 0 | 0 | 0 |

- Fabric beats baseline cases: `invoice_seed_reference, invoice_followup_alias, invoice_followup_alias_repeat, invoice_anomaly_hold, invoice_total_mismatch_hold`
- Descriptor-change cases: `invoice_followup_alias, invoice_followup_alias_repeat`
