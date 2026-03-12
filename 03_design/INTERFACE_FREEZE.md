# Interface Freeze

## Phase 2 Freeze Status
- Frozen on `2026-03-12` for Phase 2.
- No field may be added, removed, renamed, or repurposed after this freeze unless `DECISIONS.md` is updated first.
- These interfaces freeze architecture intent only. They do not prove implementation exists yet.

## Global Interface Rules
- Canonical machine-readable exchange format is bounded JSON.
- Success and failure output for CLI commands must stay fail-closed:
  - success: `{"ok":true,...}`
  - failure: `{"ok":false,"error":{...}}`
- `*_ref` fields are bounded string references to local workspace artifacts, payload files, or ledger entries.
- `*_utc` fields are UTC timestamps.
- Policy and cap fields are bounded JSON objects, not executable code.
- Resource byte and millisecond fields are integers.
- Score fields are bounded numeric scores, not free-text labels.

## `FabricConfig`
Frozen fields:
- `fabric_id`
- `proof_domain`
- `machine_profile`
- `active_population_cap`
- `logical_population_cap`
- `memory_caps`
- `storage_caps`
- `workspace_policy`
- `governance_policy`
- `need_signal_policy`
- `blueprint_registry_path`
- `benchmark_profile`

Frozen intent:
- `fabric_id`: stable fabric identity
- `proof_domain`: fixed v1 proof domain selector
- `machine_profile`: target machine and runtime envelope
- `active_population_cap`: cap on live instantiated cells
- `logical_population_cap`: cap on total known cells in the fabric
- `memory_caps`: bounded memory limits by tier and scope
- `storage_caps`: bounded disk limits by store and artifact class
- `workspace_policy`: allowed shared-workspace behavior
- `governance_policy`: approval, veto, quarantine, and replay rules
- `need_signal_policy`: allowed need-signal creation and handling rules
- `blueprint_registry_path`: local registry path for cell blueprints
- `benchmark_profile`: benchmark contract profile to use

## `CellBlueprint`
Frozen fields:
- `cell_id`
- `bundle_ref`
- `role_family`
- `role_name`
- `descriptor_kinds`
- `split_policy`
- `merge_policy`
- `trust_profile`
- `policy_envelope`
- `activation_cost_ms`
- `working_memory_bytes`
- `idle_memory_bytes`
- `descriptor_cache_bytes`
- `memory_tier`
- `utility_profile_ref`
- `allowed_tissues`

Frozen intent:
- `cell_id`: stable cell blueprint identity
- `bundle_ref`: local bundle or package reference for executable behavior
- `role_family`: bounded family this cell may refine within
- `role_name`: concrete role inside the family
- `descriptor_kinds`: descriptor types the cell may publish or consume
- `split_policy`: local split constraints
- `merge_policy`: local merge constraints
- `trust_profile`: trust assumptions and trust ancestry boundary
- `policy_envelope`: outer rules the cell cannot cross
- `activation_cost_ms`: expected activation cost budget
- `working_memory_bytes`: active-state working memory budget
- `idle_memory_bytes`: dormant-state retained budget
- `descriptor_cache_bytes`: descriptor cache budget
- `memory_tier`: default memory tier assignment for the cell
- `utility_profile_ref`: reference to a `CellUtilityProfile`
- `allowed_tissues`: tissues this blueprint may join

## `CellRuntimeState`
Frozen fields:
- `cell_id`
- `lineage_id`
- `runtime_state`
- `active_task_ref`
- `workspace_subscriptions`
- `loaded_descriptor_refs`
- `current_need_signals`
- `last_transition_ref`

Frozen intent:
- `cell_id`: runtime cell identity
- `lineage_id`: lineage identifier shared across inherited descendants
- `runtime_state`: current lifecycle state from the frozen state set
- `active_task_ref`: current task handle if active
- `workspace_subscriptions`: workspace channels or objects the cell is watching
- `loaded_descriptor_refs`: descriptors currently loaded into runtime context
- `current_need_signals`: open need-signal ids affecting this cell
- `last_transition_ref`: latest lifecycle or state-change record

## `DescriptorRecord`
Frozen fields:
- `descriptor_id`
- `producer_cell_id`
- `descriptor_kind`
- `task_scope`
- `cost_score`
- `confidence_score`
- `payload_ref`
- `storage_tier`
- `retention_policy`
- `trust_ref`
- `created_utc`
- `supersedes_descriptor_id`

Frozen intent:
- `descriptor_id`: stable descriptor identity
- `producer_cell_id`: producing cell
- `descriptor_kind`: category of reusable skill or knowledge record
- `task_scope`: task boundary where the descriptor is valid
- `cost_score`: cost estimate for reuse
- `confidence_score`: confidence estimate for reuse
- `payload_ref`: local payload reference
- `storage_tier`: hot, warm, or cold storage tier
- `retention_policy`: retention rule applied to this descriptor
- `trust_ref`: trust record or trust lineage reference
- `created_utc`: creation timestamp
- `supersedes_descriptor_id`: prior descriptor replaced by this one, if any

## `NeedSignal`
Frozen fields:
- `need_signal_id`
- `source_type`
- `source_id`
- `signal_kind`
- `severity`
- `evidence_ref`
- `proposed_action`
- `status`
- `expires_at_utc`
- `resolution_ref`
- `created_utc`

Frozen allowed `signal_kind` values:
- `overload`
- `uncertainty`
- `novelty`
- `redundancy`
- `memory_pressure`
- `trust_risk`
- `coordination_gap`

Frozen intent:
- `need_signal_id`: stable signal identity
- `source_type`: cell, tissue, governance, benchmark, or other bounded source class
- `source_id`: concrete source id
- `signal_kind`: one of the frozen allowed kinds above
- `severity`: bounded intensity score
- `evidence_ref`: evidence supporting the signal
- `proposed_action`: requested response
- `status`: open handling status
- `expires_at_utc`: expiration time if unresolved
- `resolution_ref`: reference to how the signal was resolved
- `created_utc`: creation time

## `LifecycleEvent`
Frozen fields:
- `event_id`
- `cell_id`
- `lineage_id`
- `transition`
- `reason`
- `proposer`
- `approver`
- `veto_ref`
- `rollback_ref`
- `created_utc`

Frozen allowed `transition` values:
- `seed_to_dormant`
- `dormant_to_active`
- `active_to_split_pending`
- `split_pending_to_active_children`
- `active_to_consolidating`
- `consolidating_to_dormant`
- `active_to_quarantined`
- `quarantined_to_dormant`
- `dormant_to_retired`

Frozen intent:
- `event_id`: stable event identity
- `cell_id`: primary cell affected by the transition
- `lineage_id`: lineage the event belongs to
- `transition`: one of the frozen values above
- `reason`: bounded explanation of why the transition happened
- `proposer`: actor that proposed the change
- `approver`: actor that approved the change
- `veto_ref`: veto record if the transition was blocked or constrained
- `rollback_ref`: rollback path if reversal is possible
- `created_utc`: creation time

## `MemoryPromotionDecision`
Frozen fields:
- `candidate_id`
- `reviewer_id`
- `decision`
- `compression_mode`
- `retention_tier`
- `reason`
- `rollback_ref`
- `created_utc`

Frozen allowed `decision` values:
- `reject`
- `defer`
- `promote`
- `compress`
- `retire`

Frozen intent:
- `candidate_id`: descriptor or memory candidate under review
- `reviewer_id`: reviewing cell or governance unit
- `decision`: one of the frozen allowed values above
- `compression_mode`: named compression mode applied or requested
- `retention_tier`: hot, warm, or cold tier target
- `reason`: bounded explanation
- `rollback_ref`: reversal record if applicable
- `created_utc`: creation time

## `CellUtilityProfile`
Frozen fields:
- `reward_weight`
- `novelty_weight`
- `resource_cost_weight`
- `trust_penalty_weight`
- `policy_penalty_weight`
- `split_threshold`
- `merge_threshold`
- `hibernate_threshold`
- `reactivate_threshold`

Frozen intent:
- `reward_weight`: value for successful useful work
- `novelty_weight`: value for genuinely new useful descriptors or paths
- `resource_cost_weight`: penalty for resource use
- `trust_penalty_weight`: penalty for low-trust conditions
- `policy_penalty_weight`: penalty for policy risk
- `split_threshold`: utility level that justifies split evaluation
- `merge_threshold`: utility level that justifies merge evaluation
- `hibernate_threshold`: low-value threshold for dormancy pressure
- `reactivate_threshold`: demand threshold for reactivation pressure

## Frozen Lifecycle State Set
`CellRuntimeState.runtime_state` is limited to:
- `seed`
- `dormant`
- `active`
- `split_pending`
- `consolidating`
- `quarantined`
- `retired`

No other lifecycle states are allowed in v1 without a recorded decision update.

## Frozen CLI Contract
The CLI surface is frozen now so Phase 3 can implement against it without later reinterpretation.

### `runner/cell fabric init`
- input: config path argument
- stdin: not required
- stdout: bounded JSON
- side effect: initializes local fabric state

### `runner/cell fabric run`
- input: workflow payload on stdin
- stdout: result JSON on stdout
- side effect: may update local workspace, memory candidates, and evidence refs under policy

### `runner/cell fabric status`
- input: no stdin
- stdout: bounded JSON on stdout
- side effect: none required

### `runner/cell fabric replay`
- input: replay manifest path argument
- stdin: not required
- stdout: replay result JSON on stdout
- side effect: may materialize replay evidence in bounded local paths

### `runner/cell fabric evidence`
- input: output path argument
- stdin: not required
- stdout: pass or fail JSON on stdout
- side effect: writes evidence bundle at the requested path

Frozen CLI rules:
- stdout must remain bounded JSON only
- unbounded logs or traces must not be printed to stdout
- human-readable diagnostics belong in stderr or referenced output files
- all command failures must use the fail-closed JSON form

## Verification Status
- Locally verified:
  - all frozen interfaces are now written explicitly in this workspace
  - the required field names, lifecycle state set, CLI contract, need-signal taxonomy, and allowed decision or transition values are written clearly
- Assumed only:
  - schema validation code
  - CLI implementation behavior
