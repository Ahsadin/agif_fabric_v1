# V1X Finance Organic Load Results

Locally verified deterministic benchmark summary for Track B Gap 1.

## Run Summary

| Run | Accuracy | Mean Queue Age | Mean End-To-End Latency | Split Events | Merge Events | Max Active Population | Active After Settle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| elastic | 0.725 | 0.300 | 8.050 | 1 | 1 | 11 | 0 |
| control | 0.725 | 16.800 | 24.550 | 0 | 0 | 10 | 0 |

## Elastic Split Events

| Seq | Case ID | Proposer | Approver | Lineage Chain | Pre Active | Post Active | Trigger Queue Age |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 6 | alias_006_northwind_high_value_a | tissue:finance_validation_correction_tissue:organic_monitor | governance:phase7_local_board | finance_correction_specialist -> finance_correction_specialist__child_001, finance_correction_specialist__child_002 | 10 | 11 | 4.000 |

## Control Split Decisions

| Seq | Case ID | Governance Outcome | Signal Kind | Signal Severity | Reason |
| --- | --- | --- | --- | ---: | --- |
| 6 | alias_006_northwind_high_value_a | split_disabled_by_governance | overload | 0.920 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 7 | alias_007_northwind_followup_e | split_disabled_by_governance | overload | 0.960 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 8 | alias_008_northwind_followup_f | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 9 | alias_009_northwind_high_value_b | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 10 | alias_010_northwind_followup_g | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 11 | alias_011_northwind_followup_h | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 12 | novelty_012_orbit_a | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 13 | novelty_013_fabrikam_a | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 14 | novelty_014_orbit_b | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 15 | novelty_015_fabrikam_b | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 16 | novelty_016_orbit_c | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 17 | alias_017_northwind_followup_i | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 18 | alias_018_northwind_followup_j | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 19 | alias_019_northwind_followup_k | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 20 | alias_020_northwind_high_value_c | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 21 | alias_021_northwind_followup_l | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 22 | alias_022_northwind_followup_m | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 23 | alias_023_northwind_followup_n | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 24 | alias_024_northwind_high_value_d | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 25 | alias_025_northwind_followup_o | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 26 | alias_026_northwind_followup_p | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 27 | novelty_027_fabrikam_c | split_disabled_by_governance | overload | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 28 | novelty_028_orbit_d | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 29 | novelty_029_fabrikam_d | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 30 | novelty_030_orbit_e | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 31 | novelty_031_fabrikam_e | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |
| 32 | recovery_032_northwind_clear_a | split_disabled_by_governance | novelty | 0.980 | organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap |

## Overhead Vs Usefulness

| Metric | Value |
| --- | --- |
| Elastic accuracy delta vs control | 0.000 |
| Queue age gain vs control | 16.500 |
| End-to-end latency gain vs control | 16.500 |
| Extra authority reviews in elastic | 2 |
| Extra lifecycle events in elastic | 5 |
| Extra correction worker units in elastic | 34 |
| Post-split elastic accuracy | 0.757 |
| Post-split control accuracy | 0.757 |

## Case Stream

| Case ID | Band | Elastic Correction Cell | Elastic Workers | Elastic Queue Age | Control Queue Age | Elastic Score | Control Score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| recovery_001_seed_northwind | recovery_tail | finance_correction_specialist | 1 | 0.000 | 0.000 | 1.000 | 1.000 |
| alias_002_northwind_followup_a | alias_heavy | finance_correction_specialist | 1 | 0.000 | 0.000 | 0.375 | 0.375 |
| alias_003_northwind_followup_b | alias_heavy | finance_correction_specialist | 1 | 1.000 | 1.000 | 0.375 | 0.375 |
| alias_004_northwind_followup_c | alias_heavy | finance_correction_specialist | 1 | 2.000 | 2.000 | 0.375 | 0.375 |
| alias_005_northwind_followup_d | alias_heavy | finance_correction_specialist | 1 | 3.000 | 3.000 | 0.375 | 0.375 |
| alias_006_northwind_high_value_a | alias_heavy | finance_correction_specialist | 1 | 4.000 | 4.000 | 0.750 | 0.750 |
| alias_007_northwind_followup_e | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 5.000 | 0.375 | 0.375 |
| alias_008_northwind_followup_f | alias_heavy | finance_correction_specialist__child_001 | 2 | 1.000 | 6.000 | 0.375 | 0.375 |
| alias_009_northwind_high_value_b | alias_heavy | finance_correction_specialist__child_001 | 2 | 1.000 | 7.000 | 0.750 | 0.750 |
| alias_010_northwind_followup_g | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 8.000 | 0.375 | 0.375 |
| alias_011_northwind_followup_h | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 9.000 | 0.375 | 0.375 |
| novelty_012_orbit_a | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 10.000 | 1.000 | 1.000 |
| novelty_013_fabrikam_a | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 12.000 | 1.000 | 1.000 |
| novelty_014_orbit_b | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 14.000 | 1.000 | 1.000 |
| novelty_015_fabrikam_b | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 16.000 | 1.000 | 1.000 |
| novelty_016_orbit_c | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 18.000 | 1.000 | 1.000 |
| alias_017_northwind_followup_i | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 20.000 | 0.375 | 0.375 |
| alias_018_northwind_followup_j | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 21.000 | 0.375 | 0.375 |
| alias_019_northwind_followup_k | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 22.000 | 0.375 | 0.375 |
| alias_020_northwind_high_value_c | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 23.000 | 0.750 | 0.750 |
| alias_021_northwind_followup_l | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 24.000 | 0.375 | 0.375 |
| alias_022_northwind_followup_m | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 25.000 | 0.375 | 0.375 |
| alias_023_northwind_followup_n | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 26.000 | 0.375 | 0.375 |
| alias_024_northwind_high_value_d | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 27.000 | 0.750 | 0.750 |
| alias_025_northwind_followup_o | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 28.000 | 0.375 | 0.375 |
| alias_026_northwind_followup_p | alias_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 29.000 | 0.375 | 0.375 |
| novelty_027_fabrikam_c | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 30.000 | 1.000 | 1.000 |
| novelty_028_orbit_d | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 30.000 | 1.000 | 1.000 |
| novelty_029_fabrikam_d | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 30.000 | 1.000 | 1.000 |
| novelty_030_orbit_e | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 30.000 | 1.000 | 1.000 |
| novelty_031_fabrikam_e | novelty_heavy | finance_correction_specialist__child_001 | 2 | 0.000 | 30.000 | 1.000 | 1.000 |
| recovery_032_northwind_clear_a | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 30.000 | 1.000 | 1.000 |
| recovery_033_fabrikam_clear_a | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 27.000 | 1.000 | 1.000 |
| recovery_034_northwind_clear_b | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 24.000 | 1.000 | 1.000 |
| recovery_035_fabrikam_clear_b | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 21.000 | 1.000 | 1.000 |
| recovery_036_northwind_clear_c | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 18.000 | 1.000 | 1.000 |
| recovery_037_fabrikam_clear_c | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 15.000 | 1.000 | 1.000 |
| recovery_038_northwind_clear_d | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 12.000 | 1.000 | 1.000 |
| recovery_039_northwind_clear_e | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 9.000 | 1.000 | 1.000 |
| recovery_040_northwind_clear_f | recovery_tail | finance_correction_specialist__child_001 | 2 | 0.000 | 6.000 | 1.000 | 1.000 |

## Acceptance

| Check | Passed |
| --- | --- |
| Split occurs inside stream | yes |
| Control blocks split transitions | yes |
| Same case sequence | yes |
| Accuracy preserved or improved | yes |
| Queue or latency improved | yes |
| Active population returns near start | yes |
| Usefulness gate passed | yes |
| Overall pass | yes |
