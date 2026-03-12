# Lifecycle Model

## Phase 2 Freeze Status
- Frozen on `2026-03-12` for Phase 2.
- This document freezes lifecycle states, allowed structural transitions, and lineage rules before implementation starts.

## Frozen Lifecycle State Set
- `seed`
- `dormant`
- `active`
- `split_pending`
- `consolidating`
- `quarantined`
- `retired`

No other lifecycle states are allowed in v1 without a decision update.

## Frozen Meaning of Each State
| State | Frozen meaning | Budget effect |
| --- | --- | --- |
| `seed` | A cell identity or child candidate exists but is not yet admitted to the runnable logical population. | No active runtime budget. |
| `dormant` | The cell is known to the fabric and retains identity, lineage, and approved memory references, but is not currently instantiated. | Counts toward logical population, not active runtime population. |
| `active` | The cell is instantiated and may perform bounded work in its allowed tissue context. | Counts toward active runtime budget. |
| `split_pending` | The cell has an approved split in progress and is preparing children or a refined role distribution. | Continues to consume bounded active budget until split resolves. |
| `consolidating` | One or more cells are in merge preparation and conflict-aware consolidation. | Active work is limited to merge-safe consolidation tasks. |
| `quarantined` | The cell is isolated because of trust, policy, or rollback concern. | It cannot act on shared workflow tasks until cleared. |
| `retired` | The cell is permanently removed from future activation and remains only as lineage and evidence history. | No runtime budget. |

## Frozen Structural Transition Set
`LifecycleEvent.transition` is limited to:
- `seed_to_dormant`
- `dormant_to_active`
- `active_to_split_pending`
- `split_pending_to_active_children`
- `active_to_consolidating`
- `consolidating_to_dormant`
- `active_to_quarantined`
- `quarantined_to_dormant`
- `dormant_to_retired`

## Frozen Transition Rules

### `seed_to_dormant`
- Meaning: a new blueprint, imported cell, or approved child becomes a dormant logical member of the fabric
- Required records:
  - `proposer`
  - `approver`
  - `reason`
  - `rollback_ref`
- Result: the cell enters the logical population without consuming active runtime budget

### `dormant_to_active`
- Meaning: activation or reactivation into live runtime
- Allowed trigger types:
  - new workflow demand
  - renewed need pressure
  - planned benchmark activation
  - recovery or replay procedure
- Result: the cell enters live runtime under active caps

### `active_to_split_pending`
- Meaning: a split request has been approved and the parent cell is preparing refined children
- Required approval: governance approval
- Preconditions:
  - a recorded need signal justifies the split
  - policy and resource limits allow more active or logical members
  - the split stays within the same `role_family`

### `split_pending_to_active_children`
- Meaning: the split commits and one or more children become active
- Required inheritance:
  - lineage
  - role family
  - trust ancestry
  - descriptor eligibility
  - policy envelope
- Frozen child rule: children may refine inside the existing `role_family` only
- Frozen parent rule: the parent becomes the dormant lineage anchor unless a later governed retirement is recorded

### `active_to_consolidating`
- Meaning: a merge has been approved and the participating cells are now in conflict-aware consolidation
- Required approval: tissue coordinator plus governance co-approval
- Preconditions:
  - a recorded need signal justifies the merge
  - merge policy permits the cells to merge
  - no merge may proceed without conflict-aware consolidation

### `consolidating_to_dormant`
- Meaning: consolidation finished and the survivor is stored in dormant form
- Frozen survivor rule:
  - the surviving merged cell is placed in `dormant` first
  - reactivation requires a later `dormant_to_active` event
- Frozen retirement rule:
  - any merged-away cells must receive explicit `dormant_to_retired` records

### `active_to_quarantined`
- Meaning: the cell is isolated because of trust risk, policy breach, repeated rollback, or unsafe behavior concern
- Required authority: governance may trigger directly; cells and tissues may request it
- Result: the cell stops shared workflow action and descriptor publishing until cleared

### `quarantined_to_dormant`
- Meaning: review, replay, rollback, or human decision cleared the cell for non-active storage
- Result: the cell is not active yet, but it is no longer isolated

### `dormant_to_retired`
- Meaning: final retirement after obsolescence, merge completion, or governance-directed removal
- Result: the cell becomes terminal and cannot reactivate

## Hibernate and Reactivate Interpretation
Phase 2 must preserve hibernate and reactivate as first-class lifecycle concepts.

The frozen interpretation is:
- hibernate means return from live execution into the `dormant` state for resource or demand reasons
- reactivate means `dormant_to_active`

Because the frozen `LifecycleEvent.transition` list does not introduce a separate `active_to_dormant` enum, routine hibernation must be recorded through the lifecycle ledger using the bounded `reason` field and linked transition records without adding a new state or enum value.

## Frozen Split and Merge Rules
- split requires governance approval
- merge requires tissue coordinator plus governance co-approval
- children inherit lineage, role family, trust ancestry, descriptor eligibility, and policy envelope
- children may refine inside role family only
- no merge without conflict-aware consolidation
- no lineage rewrite without ledger record

## Frozen Lineage Rules
- `lineage_id` is the continuity handle for a family of related cells.
- Children created by split keep the inherited `lineage_id`.
- A split creates new `cell_id` values, not a new lineage.
- Merge does not silently rewrite lineage. If a surviving merged cell absorbs state from other cells, the ledger must preserve the ancestry trail.
- Retirement never deletes lineage history.

## Frozen Conflict-Aware Consolidation Rule
No merge is complete until consolidation explicitly checks:
- descriptor conflicts
- trust differences
- policy envelope conflicts
- rollback coverage
- payload reference validity

If those conflicts cannot be resolved safely, the merge must stop or move the participants to quarantine instead of forcing consolidation.

## Frozen Replay and Rollback Rule
Every structural change must have:
- `proposer`
- `approver`
- `reason`
- `rollback_ref`

Lifecycle replay must be able to reconstruct:
- which cell changed state
- why it changed state
- which authority approved it
- what lineage was affected
- how to reverse or contain the change when reversal is allowed

## Verification Status
- Locally verified:
  - lifecycle states, transition names, lineage rules, and split or merge rules are frozen in writing
  - the required authority links and rollback requirements are written clearly
- Assumed only:
  - actual lifecycle engine behavior
  - actual replay or rollback execution
