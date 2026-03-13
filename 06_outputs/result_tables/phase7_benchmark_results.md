# Phase 7 Benchmark Results

- Artifact note: runtime timestamp omitted and temp evidence paths normalized for deterministic reruns.

## Class Metrics

| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat_baseline | 0.583 | 1.000 | 0.000 | 0.000 | 0.500 |
| multi_cell_without_bounded_adaptation | 0.750 | 1.000 | 0.000 | 0.667 | 0.000 |
| multi_cell_with_bounded_adaptation | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |

## Case Comparison

| Case | Flat baseline | Multi-cell no adapt | Multi-cell with adapt | Descriptor reuse mattered | With adapt confidence | Why it mattered |
| --- | ---: | ---: | ---: | --- | --- | --- |
| invoice_seed_reference | 0.875 | 1.000 | 1.000 | no | high confidence (0.864) with outcome accepted/clear | real tissues preserved a safer bounded path than the flat baseline |
| invoice_followup_alias | 0.500 | 0.375 | 1.000 | yes | high confidence (0.848) with outcome accepted/clear | reviewed descriptor reuse restored bounded context from prior memory: desc_0001 from mem_0001; warm tier, 597 bytes; reuse_count=1, trust=0.76; approved by authority_00002; restored normalized_vendor, normalized_currency, derived_due_date |
| invoice_followup_alias_repeat | 0.500 | 0.375 | 1.000 | yes | guarded confidence (0.771) with outcome accepted/clear | reviewed descriptor reuse restored bounded context from prior memory: desc_0003 from mem_0003; warm tier, 595 bytes; reuse_count=1, trust=0.76; approved by authority_00004; restored normalized_vendor, normalized_currency, derived_due_date |
| invoice_high_value_alias_hold | 0.375 | 0.750 | 1.000 | yes | guarded confidence (0.712) with outcome hold/review_required | real tissues kept the document on hold instead of flat auto-release; reviewed descriptor reuse restored bounded context from prior memory: desc_0005 from mem_0005; warm tier, 595 bytes; reuse_count=2, trust=0.76; approved by authority_00006; restored normalized_vendor, normalized_currency, derived_due_date; governance stayed active after correction instead of silently auto-releasing |
| invoice_anomaly_hold | 0.625 | 1.000 | 1.000 | no | guarded confidence (0.744) with outcome hold/review_required | real tissues kept the document on hold instead of flat auto-release |
| invoice_total_mismatch_hold | 0.625 | 1.000 | 1.000 | no | high confidence (0.804) with outcome hold/review_required | real tissues kept the document on hold instead of flat auto-release |

## Resource And Control

| Benchmark class | Active/logical ratio | Runtime bytes | Retained memory delta bytes | Retained/case bytes | Routing decisions/case | Authority reviews/case | Governance overhead share | Structural signal cases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flat_baseline | 0.000 | 0 | 0 | 0.0 | 0.000 | 0.000 | 0.000 | 0 |
| multi_cell_without_bounded_adaptation | 0.909 | 1507328 | 5058 | 843.0 | 11.667 | 2.000 | 0.171 | 5 |
| multi_cell_with_bounded_adaptation | 0.909 | 1507328 | 5877 | 979.5 | 11.667 | 2.333 | 0.200 | 3 |

## Adaptation Tradeoffs

| Comparison | Accuracy gain | Retained memory cost bytes | Accuracy gain per retained KiB | Authority overhead delta/case |
| --- | ---: | ---: | ---: | ---: |
| flat -> no_adapt | 0.167 | 5058 | 0.033742 | 2.000 |
| no_adapt -> with_adapt | 0.250 | 819 | 0.312576 | 0.333 |

## Counterfactual Notes

| Case | Flat baseline missed | No adapt improved | With adapt improved |
| --- | --- | --- | --- |
| invoice_seed_reference | governance_action | improved governance_action | no material improvement |
| invoice_followup_alias | governance_action, normalized_currency, normalized_vendor, reviewer_status | no material improvement | improved final_status, governance_action, normalized_currency, normalized_vendor, reviewer_status |
| invoice_followup_alias_repeat | governance_action, normalized_currency, normalized_vendor, reviewer_status | no material improvement | improved final_status, governance_action, normalized_currency, normalized_vendor, reviewer_status |
| invoice_high_value_alias_hold | final_status, governance_action, normalized_currency, normalized_vendor, reviewer_status | improved final_status, governance_action, reviewer_status | improved normalized_currency, normalized_vendor |
| invoice_anomaly_hold | final_status, governance_action, reviewer_status | improved final_status, governance_action, reviewer_status | no material improvement |
| invoice_total_mismatch_hold | final_status, governance_action, reviewer_status | improved final_status, governance_action, reviewer_status | no material improvement |

## Route Of Custody

| Case | Outcome trail | With adapt tissue custody | Governance detail |
| --- | --- | --- | --- |
| invoice_seed_reference | flat=accepted/clear; no_adapt=accepted/clear; with_adapt=accepted/clear | intake/routing -> extraction -> validation/correction -> anomaly/reviewer -> workspace/governance -> reporting/output; handoffs=5 | bounded release completed without extra authority review |
| invoice_followup_alias | flat=accepted/clear_without_review; no_adapt=hold/review_required; with_adapt=accepted/clear | intake/routing -> extraction -> validation/correction -> anomaly/reviewer -> workspace/governance -> reporting/output; handoffs=5 | bounded release completed without extra authority review |
| invoice_followup_alias_repeat | flat=accepted/clear_without_review; no_adapt=hold/review_required; with_adapt=accepted/clear | intake/routing -> extraction -> validation/correction -> anomaly/reviewer -> workspace/governance -> reporting/output; handoffs=5 | bounded release completed without extra authority review |
| invoice_high_value_alias_hold | flat=accepted/clear_without_review; no_adapt=hold/review_required; with_adapt=hold/review_required | intake/routing -> extraction -> validation/correction -> anomaly/reviewer -> workspace/governance -> reporting/output; handoffs=5 | hold_for_review via authority_00007 (approved, trust_band=high) |
| invoice_anomaly_hold | flat=accepted/clear_without_review; no_adapt=hold/review_required; with_adapt=hold/review_required | intake/routing -> extraction -> validation/correction -> anomaly/reviewer -> workspace/governance -> reporting/output; handoffs=5 | hold_for_review via authority_00009 (approved, trust_band=high) |
| invoice_total_mismatch_hold | flat=accepted/clear_without_review; no_adapt=hold/review_required; with_adapt=hold/review_required | intake/routing -> extraction -> validation/correction -> anomaly/reviewer -> workspace/governance -> reporting/output; handoffs=5 | hold_for_review via authority_00011 (approved, trust_band=high) |

## Descriptor Reuse Evidence

| Case | Descriptor and retained state | Prevented errors or lifts | Need resolution trail |
| --- | --- | --- | --- |
| invoice_followup_alias | desc_0001 from mem_0001; warm tier, 597 bytes; reuse_count=1, trust=0.76; approved by authority_00002; restored normalized_vendor, normalized_currency, derived_due_date | improved final_status, governance_action, normalized_currency, normalized_vendor, reviewer_status | uncertainty -> desc_0001 (resolved_well) |
| invoice_followup_alias_repeat | desc_0003 from mem_0003; warm tier, 595 bytes; reuse_count=1, trust=0.76; approved by authority_00004; restored normalized_vendor, normalized_currency, derived_due_date | improved final_status, governance_action, normalized_currency, normalized_vendor, reviewer_status | uncertainty -> desc_0003 (resolved_well) |
| invoice_high_value_alias_hold | desc_0005 from mem_0005; warm tier, 595 bytes; reuse_count=2, trust=0.76; approved by authority_00006; restored normalized_vendor, normalized_currency, derived_due_date | improved normalized_currency, normalized_vendor | trust_risk -> authority_00007 (resolved_well); uncertainty -> desc_0005 (resolved_well) |

## Structural Pressure

| Benchmark class | Measured split/merge | Structural signal cases | Why no action or what was measured | Future trigger |
| --- | --- | ---: | --- | --- |
| flat_baseline | no | 0 | flat baseline has no split or merge path | not applicable until the benchmark uses a governed fabric population |
| multi_cell_without_bounded_adaptation | no | 5 | no governed split or merge executed; reviewer and governance pressure appeared, but active population stayed at 10/24 and split counters remained zero | governed split becomes relevant when repeated reviewer pressure coincides with active population at or above 24 and lifecycle split counters move above zero |
| multi_cell_with_bounded_adaptation | no | 3 | no governed split or merge executed; reviewer and governance pressure appeared, but active population stayed at 10/24 and split counters remained zero | governed split becomes relevant when repeated reviewer pressure coincides with active population at or above 24 and lifecycle split counters move above zero |

## Tissue Analytics

| Benchmark class | Tissue | Usefulness | Workload share | Useful cases | Stage workload | Handoffs | Intervention cases | Anomaly burden | Governance burden | Reuse contribution |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_cell_without_bounded_adaptation | intake/routing | 1.000 | 0.200 | 6 | 12 | 6 | 0 | 0 | 0 | 0 |
| multi_cell_without_bounded_adaptation | extraction | 1.000 | 0.100 | 6 | 6 | 12 | 0 | 0 | 0 | 0 |
| multi_cell_without_bounded_adaptation | validation/correction | 0.667 | 0.200 | 3 | 12 | 12 | 3 | 0 | 0 | 0 |
| multi_cell_without_bounded_adaptation | anomaly/reviewer | 0.667 | 0.100 | 4 | 6 | 12 | 5 | 7 | 0 | 0 |
| multi_cell_without_bounded_adaptation | workspace/governance | 0.667 | 0.200 | 4 | 12 | 12 | 5 | 0 | 5 | 0 |
| multi_cell_without_bounded_adaptation | reporting/output | 0.667 | 0.200 | 4 | 12 | 6 | 6 | 0 | 0 | 0 |
| multi_cell_with_bounded_adaptation | intake/routing | 1.000 | 0.200 | 6 | 12 | 6 | 0 | 0 | 0 | 0 |
| multi_cell_with_bounded_adaptation | extraction | 1.000 | 0.100 | 6 | 6 | 12 | 0 | 0 | 0 | 0 |
| multi_cell_with_bounded_adaptation | validation/correction | 1.000 | 0.200 | 6 | 12 | 12 | 3 | 0 | 0 | 3 |
| multi_cell_with_bounded_adaptation | anomaly/reviewer | 1.000 | 0.100 | 6 | 6 | 12 | 3 | 4 | 0 | 0 |
| multi_cell_with_bounded_adaptation | workspace/governance | 1.000 | 0.200 | 6 | 12 | 12 | 3 | 0 | 3 | 0 |
| multi_cell_with_bounded_adaptation | reporting/output | 1.000 | 0.200 | 6 | 12 | 6 | 6 | 0 | 0 | 0 |

- Fabric beats baseline cases: `invoice_seed_reference, invoice_followup_alias, invoice_followup_alias_repeat, invoice_high_value_alias_hold, invoice_anomaly_hold, invoice_total_mismatch_hold`
- Descriptor-change cases: `invoice_followup_alias, invoice_followup_alias_repeat, invoice_high_value_alias_hold`
