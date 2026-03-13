# Phase 8 Bounded Validation Summary

- Artifact note: runtime timestamps and temp run roots are omitted for deterministic reruns.
- Profile: `phase8_short_validation`
- Phase 8 completion: `open`
- Real 24h soak completed locally: `no`
- Real 72h soak completed locally: `no`

## Cycle Trends

| Cycle | Cycle ID | Avg score | Descriptor reuse | Accepted | Hold | Memory density | Active/logical | Runtime bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | cold_followup | 0.375 | 0 | 0 | 1 | 0.000429553 | 0.909 | 1507328 |
| 2 | seed_then_followup | 1.000 | 1 | 2 | 0 | 0.000783392 | 0.909 | 1507328 |
| 3 | repeat_followup | 1.000 | 1 | 1 | 0 | 0.000291886 | 0.909 | 1507328 |
| 4 | governed_holds | 1.000 | 0 | 0 | 2 | 0.000386473 | 0.909 | 1507328 |
| 5 | reuse_mix | 0.583 | 0 | 0 | 3 | 0.000338164 | 0.909 | 1507328 |
| 6 | seed_refresh | 1.000 | 0 | 1 | 1 | 0.000386324 | 0.909 | 1507328 |

## Stress Results

| Stress lane | Passed | Headline |
| --- | --- | --- |
| split_merge | yes | governed split and merge both executed with replay-safe lineage tracking |
| memory_pressure | yes | memory pressure triggered consolidation and stayed inside bounded caps |
| routing_pressure | yes | routing abstained under full pressure and recovered when capacity returned |
| trust_quarantine | yes | authority vetoed risky reactivation and governance quarantined the active low-trust cell |
| replay_rollback | yes | replay reproduced the prior run and rollback restored the pre-quarantine lifecycle state |

## Useful Signals

- Descriptor reuse benefit delta: `0.625`
- Memory density delta: `-0.000043229`
- Max active/logical ratio: `0.909`
- Resource cap stayed bounded: `yes`

## Failure Cases

- expected governed failure: AUTHORITY_REACTIVATION_VETO

## Closure

- Build gate ready locally: `yes`
- Useful trend visible locally: `yes`
- Phase 8 remains open because: `real 24h soak not completed locally; real 72h soak not completed locally`
