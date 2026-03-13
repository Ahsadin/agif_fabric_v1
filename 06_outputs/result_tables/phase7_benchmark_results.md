# Phase 7 Benchmark Results

- Generated UTC: `2026-03-13T08:49:44Z`

## Class Metrics

| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| flat_baseline | 0.667 | 1.000 | 0.000 | 0.000 | 0.333 |
| multi_cell_without_bounded_adaptation | 0.792 | 1.000 | 0.000 | 0.667 | 0.000 |
| multi_cell_with_bounded_adaptation | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |

## Case Comparison

| Case | Flat baseline | Multi-cell no adapt | Multi-cell with adapt | Descriptor reuse mattered |
| --- | ---: | ---: | ---: | --- |
| invoice_seed_reference | 0.875 | 1.000 | 1.000 | no |
| invoice_followup_alias | 0.500 | 0.375 | 1.000 | yes |
| invoice_anomaly_hold | 0.625 | 1.000 | 1.000 | no |

- Fabric beats baseline cases: `invoice_seed_reference, invoice_followup_alias, invoice_anomaly_hold`
- Descriptor-change cases: `invoice_followup_alias`
