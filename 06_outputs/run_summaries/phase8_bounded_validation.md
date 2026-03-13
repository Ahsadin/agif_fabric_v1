# Phase 8 Bounded Validation Summary

- Artifact note: runtime timestamps and temp run roots are omitted for deterministic reruns.
- Profile: `phase8_short_validation`
- Phase 8 completion: `open`
- Real 24h soak completed locally: `no`
- Real 72h soak completed locally: `no`

## Cycle Trends

| Cycle | Cycle ID | Avg score | Descriptor reuse rate | Hold rate | Memory density | Unresolved signals | Active/logical | Approvals | Vetoes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | cold_followup | 0.375 | 0.000 | 1.000 | 0.000429553 | 1 | 0.909 | 2 | 0 |
| 2 | seed_then_followup | 1.000 | 0.500 | 0.000 | 0.000783392 | 0 | 0.909 | 5 | 0 |
| 3 | repeat_followup | 1.000 | 1.000 | 0.000 | 0.000291886 | 0 | 0.909 | 7 | 0 |
| 4 | governed_holds | 1.000 | 0.000 | 1.000 | 0.000386473 | 0 | 0.909 | 11 | 0 |
| 5 | reuse_mix | 0.969 | 0.750 | 0.500 | 0.000640602 | 0 | 0.909 | 20 | 0 |
| 6 | seed_refresh | 1.000 | 0.500 | 0.500 | 0.000330524 | 0 | 0.909 | 24 | 0 |

## Stress Results

| Stress lane | Passed | Headline |
| --- | --- | --- |
| split_merge | yes | governed split and merge both executed with replay-safe lineage tracking |
| memory_pressure | yes | memory pressure triggered consolidation and stayed inside bounded caps |
| routing_pressure | yes | routing abstained under full pressure and recovered when capacity returned |
| trust_quarantine | yes | authority vetoed risky reactivation and governance quarantined the active low-trust cell |
| replay_rollback | yes | replay reproduced the prior run and rollback restored the pre-quarantine lifecycle state |

## Drift Indicators

| Indicator | Direction | Delta | Meaning |
| --- | --- | ---: | --- |
| routing_quality_drift | flat | 0.000000 | change in successful routing outcomes per routing decision across repeated cycles |
| descriptor_usefulness_drift | improved | 0.583333 | change in accuracy on descriptor-opportunity documents across the bounded run |
| governance_intervention_drift | improved | -0.500000 | change in holds plus authority reviews per case across repeated cycles |
| memory_value_drift | degraded | -0.101407 | change in useful score per retained KiB across repeated cycles |
| recurring_unresolved_signal_drift | flat | 0.000000 | change in recurring unresolved pressure across repeated cycles |

## Resume Realism

| Scenario | Passed | Checkpoint scope | Headline |
| --- | --- | --- | --- |
| active_cycle_resume | yes | cycle_boundary | checkpointed cycle resume recovers and continues the bounded run |
| stress_lane_resume | yes | stress_boundary | checkpointed stress-lane resume recovers and completes the bounded run |
| quarantine_resume | yes | stress_boundary | resume continues after a prior veto and quarantine signal before replay or rollback |

## Useful Signals

- Descriptor reuse benefit delta: `0.625`
- Memory density delta: `-0.000099029`
- Governance hold-with-reuse count: `1`
- Max active/logical ratio: `0.909`
- Resource cap stayed bounded: `yes`

## Memory Quality

- Reuse quality delta: `0.000000`
- Value per retained KiB delta: `-0.101407`
- Final stale retirement rate: `0.000000`
- Final supersession rate: `0.416667`

## Governance Quality

- Intervention rate delta: `-0.500000`
- Repeated hold cycles: `4`
- Repeated veto patterns: `0`
- Weak-lineage recurrence: `0`

## Failure Taxonomy

| Category | Status | Headline |
| --- | --- | --- |
| memory_pollution | watch | watch retained-memory value because density softened after early reuse gains |
| route_degradation | clear | routing quality stayed stable or improved in bounded cycles |
| authority_overblocking | clear | protective vetoes were observed without blocking the known-safe accepted paths |
| authority_underblocking | clear | governance still held reuse-assisted risky documents for review |
| unresolved_recurrence | watch | mixed-pressure cycles still leave unresolved pressure to watch |
| structural_instability | clear | split/merge remained replay-safe under bounded stress |
| recovery_delay | clear | rollback restored the pre-quarantine lifecycle state |

## Failure Cases

- expected governed failure: AUTHORITY_REACTIVATION_VETO

## Bounded Harness Proves

- descriptor reuse changes later finance outcomes inside repeated bounded cycles
- governance remains active during reuse-heavy hold cases instead of being bypassed
- split/merge, memory pressure, routing pressure, trust/quarantine, and replay/rollback lanes all execute locally
- checkpoint-based resume continuity works across cycle and stress-lane boundaries

## Still Missing For Phase 8 Closure

- real 24h soak not completed locally
- real 72h soak not completed locally
- multi-day drift confirmation under the locked machine envelope
- real lid-close or OS-restart continuity beyond bounded checkpoint replay

## Closure

- Build gate ready locally: `yes`
- Useful trend visible locally: `yes`
- Resume gate ready locally: `yes`
- Phase 8 remains open because: `real 24h soak not completed locally; real 72h soak not completed locally`
