# V1X Skill Graph Transfer Results

Locally verified deterministic benchmark summary for Track B Gap 2.

## Graph Summary

| Metric | Value |
| --- | --- |
| Source descriptor count | 3 |
| Retired source descriptor count | 1 |
| Transferred descriptor count | 1 |
| Graph edge count | 2 |
| Transfer approval edges | 1 |
| Explicit provenance count | 1 |

## Seeded Source Descriptors

| Seed | Descriptor ID | Source Domain | Memory Class | Trust | Provenance |
| --- | --- | --- | --- | ---: | ---: |
| finance_policy_northwind_invoice | desc_0001 | finance_ap | policy_useful_memory | 0.950 | 0.915 |
| finance_receipt_pattern | desc_0002 | finance_ap | pattern_memory | 0.760 | 0.840 |
| finance_legacy_invoice_pattern | desc_0003 | finance_ap | pattern_memory | 0.760 | 0.840 |

## Retired Source Visibility

| Seed | Descriptor ID | Memory ID | Decision Ref |
| --- | --- | --- | --- |
| finance_legacy_invoice_pattern | desc_0003 | mem_0003 | memory/decisions.json |

## Transfer Requests

| Request | Selected Source | Target Domain | Explicit Approval | Status | Quality | Baseline Support | Target Support | Review Ref |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| approved_cross_domain_invoice_transfer | desc_0001 | document_compliance | yes | approved | 0.940 | 0.250 | 0.955 | authority_00004 |
| abstained_low_quality_transfer | desc_0001 | document_compliance | yes | abstained | 0.440 | 0.250 | 0.250 | none |
| denied_missing_explicit_transfer_approval | desc_0001 | vendor_onboarding | no | denied | 0.940 | 0.250 | 0.250 | none |
| denied_out_of_boundary_transfer | desc_0001 | external_vendor_ops | yes | denied | 0.940 | 0.250 | 0.250 | authority_00005 |

## Materialized Provenance

| Transfer Descriptor | Source Descriptor | Source Memory | Source Payload Ref | Approval Ref | Target Domain |
| --- | --- | --- | --- | --- | --- |
| tdesc_0001 | desc_0001 | mem_0001 | memory/warm/payloads/mem_0001.json | authority_00004 | document_compliance |

## Acceptance

| Check | Passed |
| --- | --- |
| Descriptor graph exists | yes |
| Transfer approval path exists | yes |
| Provenance is explicit | yes |
| Low-quality transfer abstains or is denied | yes |
| Cross-domain transfer requires explicit approval | yes |
| Authority veto is visible | yes |
| Retirement is visible | yes |
| Transfer is useful and auditable | yes |
| Overall pass | yes |
