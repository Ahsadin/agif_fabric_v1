"""Elastic lifecycle and lineage controls for AGIF v1 Phase 4."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from intelligence.fabric.common import (
    FabricError,
    canonical_json_hash,
    ensure_non_empty_string,
    load_json_file,
    repo_relative,
    utc_now_iso,
    write_json_atomic,
)
from intelligence.fabric.governance.policy import (
    ensure_governance_actor,
    ensure_need_signal,
    ensure_tissue_actor,
    summarize_governance,
)
from intelligence.fabric.state_store import FabricStateStore


RUNTIME_CONSUMING_STATES = {"active", "split_pending", "consolidating", "quarantined"}
DORMANT_STATE = "dormant"
RETIRED_STATE = "retired"
ACTIVE_STATE = "active"
SPLIT_PENDING_STATE = "split_pending"
CONSOLIDATING_STATE = "consolidating"


class FabricLifecycleManager:
    """Manages dormant cells, active runtime cells, lineage, and replay-safe history."""

    def __init__(
        self,
        *,
        store: FabricStateStore,
        state: dict[str, Any],
        config: dict[str, Any],
    ):
        self.store = store
        self.state = dict(state)
        self.config = config
        self.fabric_id = str(state["fabric_id"])

    @property
    def steady_active_target(self) -> int:
        return int(self.state.get("steady_active_population_target", self.config["active_population_cap"]))

    @property
    def burst_active_cap(self) -> int:
        configured = self.config.get("governance_policy", {}).get("burst_active_population_cap", self.steady_active_target * 2)
        return min(int(self.config["logical_population_cap"]), max(self.steady_active_target, int(configured)))

    def bootstrap_population(self, *, registry: dict[str, Any], initialized_utc: str | None = None) -> dict[str, Any]:
        logical = self._load_or_initialize(
            self.store.logical_population_path(self.fabric_id),
            {"schema_version": "agif.fabric.logical_population.v1", "cells": {}},
        )
        if logical["cells"]:
            return self.summary()

        runtime = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        history = self._load_or_initialize(
            self.store.lifecycle_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.lifecycle_history.v1", "entries": []},
        )
        ledger = self._load_or_initialize(
            self.store.lineage_ledger_path(self.fabric_id),
            {"schema_version": "agif.fabric.lineage_ledger.v1", "entries": []},
        )
        self._load_or_initialize(
            self.store.veto_log_path(self.fabric_id),
            {"schema_version": "agif.fabric.veto_log.v1", "entries": []},
        )
        self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )

        created_utc = initialized_utc or utc_now_iso()
        for blueprint in registry["blueprints"]:
            lineage_id = self._root_lineage_id(blueprint["cell_id"])
            logical_record = self._build_logical_record(
                blueprint=blueprint,
                lineage_id=lineage_id,
                lifecycle_state=DORMANT_STATE,
                parent_cell_id=None,
                ancestor_cell_ids=[],
                source_blueprint_cell_id=blueprint["cell_id"],
                source_role_name=blueprint["role_name"],
                merged_from_cell_ids=[],
                trust_ancestry=None,
            )
            runtime_record = self._build_runtime_state(
                cell_id=blueprint["cell_id"],
                lineage_id=lineage_id,
                runtime_state=DORMANT_STATE,
                last_transition_ref=None,
            )
            ledger_entry = self._build_lineage_entry(
                ledger=ledger,
                lineage_id=lineage_id,
                cell_id=blueprint["cell_id"],
                action="seed_blueprint",
                event_id="pending",
                parent_cell_id=None,
                note="blueprint admitted to dormant logical population",
            )
            self._record_transition(
                logical=logical,
                runtime=runtime,
                history=history,
                ledger=ledger,
                transition="seed_to_dormant",
                cell_id=blueprint["cell_id"],
                lineage_id=lineage_id,
                proposer="fabric:init",
                approver="governance:bootstrap",
                reason="bootstrap dormant blueprint admission",
                created_utc=created_utc,
                logical_after={blueprint["cell_id"]: logical_record},
                runtime_after={blueprint["cell_id"]: runtime_record},
                lineage_entries=[ledger_entry],
                details={
                    "kind": "bootstrap_seed",
                    "registered_blueprint_id": blueprint["cell_id"],
                },
            )

        return self.summary()

    def summary(self) -> dict[str, Any]:
        logical = self._load_or_initialize(
            self.store.logical_population_path(self.fabric_id),
            {"schema_version": "agif.fabric.logical_population.v1", "cells": {}},
        )
        runtime = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        history = self._load_or_initialize(
            self.store.lifecycle_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.lifecycle_history.v1", "entries": []},
        )
        ledger = self._load_or_initialize(
            self.store.lineage_ledger_path(self.fabric_id),
            {"schema_version": "agif.fabric.lineage_ledger.v1", "entries": []},
        )
        vetoes = self._load_or_initialize(
            self.store.veto_log_path(self.fabric_id),
            {"schema_version": "agif.fabric.veto_log.v1", "entries": []},
        )

        logical_cells = logical["cells"]
        runtime_states = runtime["states"]
        active_population = self._count_active(runtime_states)
        dormant_population = len([item for item in runtime_states.values() if item["runtime_state"] == DORMANT_STATE])
        retired_population = len([item for item in runtime_states.values() if item["runtime_state"] == RETIRED_STATE])
        estimated_runtime_memory_bytes = 0
        estimated_idle_memory_bytes = 0
        for cell_id, record in logical_cells.items():
            blueprint = record["blueprint"]
            runtime_state = runtime_states.get(cell_id, {}).get("runtime_state", DORMANT_STATE)
            if runtime_state in RUNTIME_CONSUMING_STATES:
                estimated_runtime_memory_bytes += int(blueprint["working_memory_bytes"]) + int(blueprint["descriptor_cache_bytes"])
            elif runtime_state == DORMANT_STATE:
                estimated_idle_memory_bytes += int(blueprint["idle_memory_bytes"])

        runtime_working_set_cap_bytes = int(self.config["storage_caps"]["runtime_working_set_gb"]) * (1024**3)
        summary = {
            "logical_population": len(logical_cells),
            "active_population": active_population,
            "dormant_population": dormant_population,
            "retired_population": retired_population,
            "steady_active_population_target": self.steady_active_target,
            "burst_active_population_cap": self.burst_active_cap,
            "logical_population_cap": int(self.config["logical_population_cap"]),
            "lineage_count": len({item["lineage_id"] for item in logical_cells.values()}),
            "lifecycle_event_count": len(history["entries"]),
            "lineage_entry_count": len(ledger["entries"]),
            "veto_count": len(vetoes["entries"]),
            "estimated_runtime_memory_bytes": estimated_runtime_memory_bytes,
            "estimated_idle_memory_bytes": estimated_idle_memory_bytes,
            "within_runtime_working_set_cap": estimated_runtime_memory_bytes <= runtime_working_set_cap_bytes,
            "within_logical_population_cap": len(logical_cells) <= int(self.config["logical_population_cap"]),
            "within_burst_active_cap": active_population <= self.burst_active_cap,
            "active_to_logical_ratio": 0.0
            if not logical_cells
            else round(active_population / float(len(logical_cells)), 6),
            "state_digest": self._state_digest(logical_cells, runtime_states),
            "last_lifecycle_event_ref": history["entries"][-1]["event"]["event_id"] if history["entries"] else None,
        }
        self._refresh_state(summary)
        return summary

    def governance_summary(self) -> dict[str, Any]:
        return summarize_governance(
            self.config["governance_policy"],
            steady_active_population_target=self.steady_active_target,
            burst_active_population_cap=self.burst_active_cap,
        )

    def get_cell_record(self, cell_id: str) -> dict[str, Any]:
        logical = self._load_or_initialize(
            self.store.logical_population_path(self.fabric_id),
            {"schema_version": "agif.fabric.logical_population.v1", "cells": {}},
        )
        record = logical["cells"].get(cell_id)
        if record is None:
            raise FabricError("CELL_NOT_FOUND", f"Unknown logical cell: {cell_id}.")
        return deepcopy(record)

    def get_runtime_state(self, cell_id: str) -> dict[str, Any]:
        runtime = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        record = runtime["states"].get(cell_id)
        if record is None:
            raise FabricError("CELL_NOT_FOUND", f"Unknown runtime cell: {cell_id}.")
        return deepcopy(record)

    def list_active_cells(self) -> list[str]:
        runtime = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        return sorted(
            cell_id
            for cell_id, record in runtime["states"].items()
            if record["runtime_state"] in RUNTIME_CONSUMING_STATES
        )

    def activate_cell(
        self,
        *,
        cell_id: str,
        proposer: str,
        reason: str,
        tissue_approver: str | None = None,
        governance_approver: str | None = None,
        workflow_ref: str | None = None,
        allow_burst: bool = False,
        need_signal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logical, runtime, history, ledger = self._load_runtime_bundle()
        logical_record = self._require_cell(logical, cell_id)
        runtime_record = self._require_runtime_cell(runtime, cell_id)
        current_state = runtime_record["runtime_state"]
        if current_state != DORMANT_STATE:
            raise FabricError("LIFECYCLE_INVALID", f"Cell {cell_id} must be dormant before activation.")

        active_population = self._count_active(runtime["states"])
        use_burst = allow_burst or active_population >= self.steady_active_target
        if active_population >= self.burst_active_cap:
            self._raise_veto(
                action="activate",
                code="ACTIVE_CAP_EXCEEDED",
                message=f"Activation would exceed the burst active population cap for {cell_id}.",
                proposer=proposer,
                related_cells=[cell_id],
                reason=reason,
            )
        approver = (
            ensure_governance_actor(governance_approver, self.config["governance_policy"])
            if use_burst
            else ensure_tissue_actor(tissue_approver, self.config["governance_policy"], logical_record["blueprint"]["allowed_tissues"])
        )
        if need_signal is not None:
            self.register_need_signal(signal=need_signal)

        updated_logical = deepcopy(logical_record)
        updated_logical["lifecycle_state"] = ACTIVE_STATE
        updated_runtime = deepcopy(runtime_record)
        updated_runtime["runtime_state"] = ACTIVE_STATE
        updated_runtime["active_task_ref"] = workflow_ref
        if need_signal is not None:
            updated_runtime["current_need_signals"] = self._append_unique(
                updated_runtime["current_need_signals"], str(need_signal["need_signal_id"])
            )

        entry = self._build_lineage_entry(
            ledger=ledger,
            lineage_id=logical_record["lineage_id"],
            cell_id=cell_id,
            action="reactivate" if logical_record["activation_count"] > 0 else "activate",
            event_id="pending",
            parent_cell_id=logical_record["parent_cell_id"],
            note=reason,
        )
        event = self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="dormant_to_active",
            cell_id=cell_id,
            lineage_id=logical_record["lineage_id"],
            proposer=proposer,
            approver=approver,
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after={
                cell_id: {
                    **updated_logical,
                    "activation_count": int(logical_record["activation_count"]) + 1,
                }
            },
            runtime_after={cell_id: updated_runtime},
            lineage_entries=[entry],
            details={
                "kind": "activation",
                "workflow_ref": workflow_ref,
                "allow_burst": use_burst,
                "need_signal_id": None if need_signal is None else need_signal["need_signal_id"],
            },
        )
        return {
            "event_id": event["event_id"],
            "cell_id": cell_id,
            "runtime_state": ACTIVE_STATE,
            "active_population": self.summary()["active_population"],
        }

    def activate_for_workflow(self, *, cell_ids: list[str], workflow_id: str) -> dict[str, Any]:
        activated: list[str] = []
        reused: list[str] = []
        for cell_id in cell_ids:
            runtime_state = self.get_runtime_state(cell_id)
            if runtime_state["runtime_state"] == ACTIVE_STATE:
                reused.append(cell_id)
            else:
                self.activate_cell(
                    cell_id=cell_id,
                    proposer="fabric:workflow",
                    reason=f"workflow demand activation for {workflow_id}",
                    workflow_ref=workflow_id,
                )
                activated.append(cell_id)
        self.set_active_task_refs(cell_ids=cell_ids, workflow_ref=workflow_id)
        return {
            "workflow_id": workflow_id,
            "activated_cells": activated,
            "reused_cells": reused,
            "population": self.summary(),
        }

    def set_active_task_refs(self, *, cell_ids: list[str], workflow_ref: str | None) -> None:
        runtime = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        changed = False
        for cell_id in cell_ids:
            record = runtime["states"].get(cell_id)
            if record is None or record["runtime_state"] not in RUNTIME_CONSUMING_STATES:
                continue
            if record["active_task_ref"] != workflow_ref:
                record["active_task_ref"] = workflow_ref
                changed = True
        if changed:
            write_json_atomic(self.store.runtime_states_path(self.fabric_id), runtime)
            self.summary()

    def split_cell(
        self,
        *,
        parent_cell_id: str,
        child_role_names: list[str],
        proposer: str,
        governance_approver: str | None,
        need_signal: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        logical, runtime, history, ledger = self._load_runtime_bundle()
        parent_record = self._require_cell(logical, parent_cell_id)
        parent_runtime = self._require_runtime_cell(runtime, parent_cell_id)
        if parent_runtime["runtime_state"] != ACTIVE_STATE:
            raise FabricError("LIFECYCLE_INVALID", f"Split requires an active parent cell: {parent_cell_id}.")
        if not bool(parent_record["blueprint"]["split_policy"].get("allowed", False)):
            self._raise_veto(
                action="split",
                code="SPLIT_NOT_ALLOWED",
                message=f"Split is not allowed for {parent_cell_id}.",
                proposer=proposer,
                related_cells=[parent_cell_id],
                reason=reason,
            )

        max_children = int(parent_record["blueprint"]["split_policy"].get("max_children", 0))
        if len(child_role_names) == 0 or len(child_role_names) > max_children:
            raise FabricError("SPLIT_INVALID", f"Split for {parent_cell_id} requires between 1 and {max_children} children.")
        governance_actor = ensure_governance_actor(governance_approver, self.config["governance_policy"])
        signal = ensure_need_signal(need_signal, action="split")
        self.register_need_signal(signal=signal)

        current_logical_population = len(logical["cells"])
        if current_logical_population + len(child_role_names) > int(self.config["logical_population_cap"]):
            self._raise_veto(
                action="split",
                code="LOGICAL_CAP_EXCEEDED",
                message=f"Split would exceed the logical population cap for {parent_cell_id}.",
                proposer=proposer,
                related_cells=[parent_cell_id],
                reason=reason,
            )

        projected_active_population = self._count_active(runtime["states"]) + len(child_role_names) - 1
        if projected_active_population > self.burst_active_cap:
            self._raise_veto(
                action="split",
                code="ACTIVE_CAP_EXCEEDED",
                message=f"Split would exceed the burst active population cap for {parent_cell_id}.",
                proposer=proposer,
                related_cells=[parent_cell_id],
                reason=reason,
            )

        split_pending_logical = deepcopy(parent_record)
        split_pending_logical["lifecycle_state"] = SPLIT_PENDING_STATE
        split_pending_runtime = deepcopy(parent_runtime)
        split_pending_runtime["runtime_state"] = SPLIT_PENDING_STATE
        split_pending_runtime["current_need_signals"] = self._append_unique(
            split_pending_runtime["current_need_signals"], str(signal["need_signal_id"])
        )
        self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="active_to_split_pending",
            cell_id=parent_cell_id,
            lineage_id=parent_record["lineage_id"],
            proposer=proposer,
            approver=governance_actor,
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after={parent_cell_id: split_pending_logical},
            runtime_after={parent_cell_id: split_pending_runtime},
            lineage_entries=[
                self._build_lineage_entry(
                    ledger=ledger,
                    lineage_id=parent_record["lineage_id"],
                    cell_id=parent_cell_id,
                    action="split_pending",
                    event_id="pending",
                    parent_cell_id=parent_record["parent_cell_id"],
                    note=reason,
                )
            ],
            details={
                "kind": "split_pending",
                "need_signal_id": signal["need_signal_id"],
                "requested_children": len(child_role_names),
            },
        )

        logical, runtime, history, ledger = self._load_runtime_bundle()
        parent_record = self._require_cell(logical, parent_cell_id)
        parent_runtime = self._require_runtime_cell(runtime, parent_cell_id)
        child_ids = self._next_child_ids(
            parent_cell_id=parent_cell_id,
            lineage_id=parent_record["lineage_id"],
            child_count=len(child_role_names),
            logical=logical,
        )
        logical_after: dict[str, Any] = {}
        runtime_after: dict[str, Any] = {}
        lineage_entries: list[dict[str, Any]] = []
        parent_dormant = deepcopy(parent_record)
        parent_dormant["lifecycle_state"] = DORMANT_STATE
        logical_after[parent_cell_id] = parent_dormant
        parent_runtime_after = deepcopy(parent_runtime)
        parent_runtime_after["runtime_state"] = DORMANT_STATE
        parent_runtime_after["active_task_ref"] = None
        runtime_after[parent_cell_id] = parent_runtime_after
        lineage_entries.append(
            self._build_lineage_entry(
                ledger=ledger,
                lineage_id=parent_record["lineage_id"],
                cell_id=parent_cell_id,
                action="split_anchor",
                event_id="pending",
                parent_cell_id=parent_record["parent_cell_id"],
                note="parent preserved as dormant lineage anchor after split",
            )
        )
        for child_id, child_role_name in zip(child_ids, child_role_names, strict=True):
            child_blueprint = deepcopy(parent_record["blueprint"])
            child_blueprint["cell_id"] = child_id
            child_blueprint["role_name"] = ensure_non_empty_string(child_role_name, "child_role_name", code="SPLIT_INVALID")
            child_logical = self._build_logical_record(
                blueprint=child_blueprint,
                lineage_id=parent_record["lineage_id"],
                lifecycle_state=ACTIVE_STATE,
                parent_cell_id=parent_cell_id,
                ancestor_cell_ids=parent_record["ancestor_cell_ids"] + [parent_cell_id],
                source_blueprint_cell_id=parent_record["source_blueprint_cell_id"],
                source_role_name=parent_record["source_role_name"],
                merged_from_cell_ids=[],
                trust_ancestry=parent_record["trust_ancestry"],
            )
            child_runtime = self._build_runtime_state(
                cell_id=child_id,
                lineage_id=parent_record["lineage_id"],
                runtime_state=ACTIVE_STATE,
                last_transition_ref=None,
                active_task_ref=parent_runtime["active_task_ref"],
                workspace_subscriptions=parent_runtime["workspace_subscriptions"],
                loaded_descriptor_refs=parent_runtime["loaded_descriptor_refs"],
                current_need_signals=[signal["need_signal_id"]],
            )
            logical_after[child_id] = child_logical
            runtime_after[child_id] = child_runtime
            lineage_entries.append(
                self._build_lineage_entry(
                    ledger=ledger,
                    lineage_id=parent_record["lineage_id"],
                    cell_id=child_id,
                    action="split_child",
                    event_id="pending",
                    parent_cell_id=parent_cell_id,
                    note=f"child created from {parent_cell_id}",
                )
            )

        event = self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="split_pending_to_active_children",
            cell_id=parent_cell_id,
            lineage_id=parent_record["lineage_id"],
            proposer=proposer,
            approver=governance_actor,
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after=logical_after,
            runtime_after=runtime_after,
            lineage_entries=lineage_entries,
            details={
                "kind": "split_commit",
                "need_signal_id": signal["need_signal_id"],
                "child_ids": child_ids,
                "child_role_names": child_role_names,
            },
        )
        return {
            "event_id": event["event_id"],
            "parent_cell_id": parent_cell_id,
            "child_ids": child_ids,
            "lineage_id": parent_record["lineage_id"],
            "population": self.summary(),
        }

    def merge_cells(
        self,
        *,
        survivor_cell_id: str,
        merged_cell_id: str,
        proposer: str,
        tissue_approver: str | None,
        governance_approver: str | None,
        need_signal: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        logical, runtime, history, ledger = self._load_runtime_bundle()
        survivor = self._require_cell(logical, survivor_cell_id)
        merged = self._require_cell(logical, merged_cell_id)
        survivor_runtime = self._require_runtime_cell(runtime, survivor_cell_id)
        merged_runtime = self._require_runtime_cell(runtime, merged_cell_id)
        if survivor_runtime["runtime_state"] != ACTIVE_STATE or merged_runtime["runtime_state"] != ACTIVE_STATE:
            raise FabricError("LIFECYCLE_INVALID", "Merge requires both cells to be active.")
        if not bool(survivor["blueprint"]["merge_policy"].get("allowed", False)) or not bool(
            merged["blueprint"]["merge_policy"].get("allowed", False)
        ):
            self._raise_veto(
                action="merge",
                code="MERGE_NOT_ALLOWED",
                message=f"Merge policy does not allow {survivor_cell_id} and {merged_cell_id}.",
                proposer=proposer,
                related_cells=[survivor_cell_id, merged_cell_id],
                reason=reason,
            )
        conflicts = self._collect_merge_conflicts(survivor, merged, survivor_runtime, merged_runtime)
        if conflicts:
            self._raise_veto(
                action="merge",
                code="MERGE_CONFLICT",
                message=f"Merge blocked by conflict-aware consolidation checks: {', '.join(conflicts)}.",
                proposer=proposer,
                related_cells=[survivor_cell_id, merged_cell_id],
                reason=reason,
            )

        tissue_actor = ensure_tissue_actor(tissue_approver, self.config["governance_policy"], survivor["blueprint"]["allowed_tissues"])
        governance_actor = ensure_governance_actor(governance_approver, self.config["governance_policy"])
        signal = ensure_need_signal(need_signal, action="merge")
        self.register_need_signal(signal=signal)

        for cell_id, record in ((survivor_cell_id, survivor), (merged_cell_id, merged)):
            logical_after = {cell_id: {**deepcopy(record), "lifecycle_state": CONSOLIDATING_STATE}}
            runtime_after = {cell_id: {**deepcopy(runtime["states"][cell_id]), "runtime_state": CONSOLIDATING_STATE}}
            self._record_transition(
                logical=logical,
                runtime=runtime,
                history=history,
                ledger=ledger,
                transition="active_to_consolidating",
                cell_id=cell_id,
                lineage_id=record["lineage_id"],
                proposer=proposer,
                approver=f"{tissue_actor}+{governance_actor}",
                reason=reason,
                created_utc=utc_now_iso(),
                logical_after=logical_after,
                runtime_after=runtime_after,
                lineage_entries=[
                    self._build_lineage_entry(
                        ledger=ledger,
                        lineage_id=record["lineage_id"],
                        cell_id=cell_id,
                        action="merge_consolidating",
                        event_id="pending",
                        parent_cell_id=record["parent_cell_id"],
                        note=reason,
                    )
                ],
                details={
                    "kind": "merge_consolidating",
                    "need_signal_id": signal["need_signal_id"],
                    "partner_cell_id": merged_cell_id if cell_id == survivor_cell_id else survivor_cell_id,
                },
            )
            logical, runtime, history, ledger = self._load_runtime_bundle()

        survivor = self._require_cell(logical, survivor_cell_id)
        merged = self._require_cell(logical, merged_cell_id)
        survivor_runtime = self._require_runtime_cell(runtime, survivor_cell_id)
        merged_runtime = self._require_runtime_cell(runtime, merged_cell_id)

        survivor_after = deepcopy(survivor)
        survivor_after["lifecycle_state"] = DORMANT_STATE
        survivor_after["merged_from_cell_ids"] = sorted(
            set(survivor["merged_from_cell_ids"] + [merged_cell_id] + merged["merged_from_cell_ids"])
        )
        survivor_after["ancestor_cell_ids"] = sorted(set(survivor["ancestor_cell_ids"] + merged["ancestor_cell_ids"]))
        survivor_after["trust_ancestry"] = deepcopy(survivor["trust_ancestry"] + merged["trust_ancestry"])
        survivor_runtime_after = deepcopy(survivor_runtime)
        survivor_runtime_after["runtime_state"] = DORMANT_STATE
        survivor_runtime_after["active_task_ref"] = None
        self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="consolidating_to_dormant",
            cell_id=survivor_cell_id,
            lineage_id=survivor["lineage_id"],
            proposer=proposer,
            approver=f"{tissue_actor}+{governance_actor}",
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after={survivor_cell_id: survivor_after},
            runtime_after={survivor_cell_id: survivor_runtime_after},
            lineage_entries=[
                self._build_lineage_entry(
                    ledger=ledger,
                    lineage_id=survivor["lineage_id"],
                    cell_id=survivor_cell_id,
                    action="merge_survivor_dormant",
                    event_id="pending",
                    parent_cell_id=survivor["parent_cell_id"],
                    note=f"survivor stored dormant after merge with {merged_cell_id}",
                )
            ],
            details={
                "kind": "merge_survivor",
                "need_signal_id": signal["need_signal_id"],
                "merged_cell_id": merged_cell_id,
            },
        )
        logical, runtime, history, ledger = self._load_runtime_bundle()
        merged = self._require_cell(logical, merged_cell_id)
        merged_runtime = self._require_runtime_cell(runtime, merged_cell_id)
        merged_dormant = deepcopy(merged)
        merged_dormant["lifecycle_state"] = DORMANT_STATE
        merged_runtime_after = deepcopy(merged_runtime)
        merged_runtime_after["runtime_state"] = DORMANT_STATE
        merged_runtime_after["active_task_ref"] = None
        self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="consolidating_to_dormant",
            cell_id=merged_cell_id,
            lineage_id=merged["lineage_id"],
            proposer=proposer,
            approver=f"{tissue_actor}+{governance_actor}",
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after={merged_cell_id: merged_dormant},
            runtime_after={merged_cell_id: merged_runtime_after},
            lineage_entries=[
                self._build_lineage_entry(
                    ledger=ledger,
                    lineage_id=merged["lineage_id"],
                    cell_id=merged_cell_id,
                    action="merge_source_dormant",
                    event_id="pending",
                    parent_cell_id=merged["parent_cell_id"],
                    note=f"merged source parked dormant before retirement into {survivor_cell_id}",
                )
            ],
            details={
                "kind": "merge_source_dormant",
                "need_signal_id": signal["need_signal_id"],
                "survivor_cell_id": survivor_cell_id,
            },
        )
        result = self.retire_cell(
            cell_id=merged_cell_id,
            proposer=proposer,
            governance_approver=governance_actor,
            reason=f"retire merged source after consolidation into {survivor_cell_id}",
            normalize_after=False,
        )
        self._auto_return_to_steady(
            proposer="fabric:auto_consolidation",
            approver=tissue_actor,
            reason="auto return from burst to steady state after consolidation",
        )
        return {
            "survivor_cell_id": survivor_cell_id,
            "retired_cell_id": merged_cell_id,
            "retire_event_id": result["event_id"],
            "population": self.summary(),
        }

    def hibernate_cell(
        self,
        *,
        cell_id: str,
        proposer: str,
        tissue_approver: str | None,
        reason: str,
        normalize_after: bool = True,
    ) -> dict[str, Any]:
        logical, runtime, history, ledger = self._load_runtime_bundle()
        logical_record = self._require_cell(logical, cell_id)
        runtime_record = self._require_runtime_cell(runtime, cell_id)
        if runtime_record["runtime_state"] != ACTIVE_STATE:
            raise FabricError("LIFECYCLE_INVALID", f"Hibernate requires an active cell: {cell_id}.")
        tissue_actor = ensure_tissue_actor(tissue_approver, self.config["governance_policy"], logical_record["blueprint"]["allowed_tissues"])

        self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="active_to_consolidating",
            cell_id=cell_id,
            lineage_id=logical_record["lineage_id"],
            proposer=proposer,
            approver=tissue_actor,
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after={cell_id: {**deepcopy(logical_record), "lifecycle_state": CONSOLIDATING_STATE}},
            runtime_after={cell_id: {**deepcopy(runtime_record), "runtime_state": CONSOLIDATING_STATE}},
            lineage_entries=[
                self._build_lineage_entry(
                    ledger=ledger,
                    lineage_id=logical_record["lineage_id"],
                    cell_id=cell_id,
                    action="hibernate_consolidating",
                    event_id="pending",
                    parent_cell_id=logical_record["parent_cell_id"],
                    note=reason,
                )
            ],
            details={"kind": "hibernate_consolidating"},
        )
        logical, runtime, history, ledger = self._load_runtime_bundle()
        logical_record = self._require_cell(logical, cell_id)
        runtime_record = self._require_runtime_cell(runtime, cell_id)
        event = self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="consolidating_to_dormant",
            cell_id=cell_id,
            lineage_id=logical_record["lineage_id"],
            proposer=proposer,
            approver=tissue_actor,
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after={cell_id: {**deepcopy(logical_record), "lifecycle_state": DORMANT_STATE}},
            runtime_after={
                cell_id: {
                    **deepcopy(runtime_record),
                    "runtime_state": DORMANT_STATE,
                    "active_task_ref": None,
                }
            },
            lineage_entries=[
                self._build_lineage_entry(
                    ledger=ledger,
                    lineage_id=logical_record["lineage_id"],
                    cell_id=cell_id,
                    action="hibernate_dormant",
                    event_id="pending",
                    parent_cell_id=logical_record["parent_cell_id"],
                    note=reason,
                )
            ],
            details={"kind": "hibernate_dormant"},
        )
        if normalize_after:
            self._auto_return_to_steady(
                proposer="fabric:auto_consolidation",
                approver=tissue_actor,
                reason="auto return from burst to steady state after consolidation",
            )
        return {
            "event_id": event["event_id"],
            "cell_id": cell_id,
            "runtime_state": DORMANT_STATE,
            "population": self.summary(),
        }

    def retire_cell(
        self,
        *,
        cell_id: str,
        proposer: str,
        governance_approver: str | None,
        reason: str,
        normalize_after: bool = True,
    ) -> dict[str, Any]:
        logical, runtime, history, ledger = self._load_runtime_bundle()
        logical_record = self._require_cell(logical, cell_id)
        runtime_record = self._require_runtime_cell(runtime, cell_id)
        if runtime_record["runtime_state"] != DORMANT_STATE:
            raise FabricError("LIFECYCLE_INVALID", f"Retirement requires a dormant cell: {cell_id}.")
        governance_actor = ensure_governance_actor(governance_approver, self.config["governance_policy"])
        retired_logical = deepcopy(logical_record)
        retired_logical["lifecycle_state"] = RETIRED_STATE
        retired_logical["retired_utc"] = utc_now_iso()
        retired_runtime = deepcopy(runtime_record)
        retired_runtime["runtime_state"] = RETIRED_STATE
        event = self._record_transition(
            logical=logical,
            runtime=runtime,
            history=history,
            ledger=ledger,
            transition="dormant_to_retired",
            cell_id=cell_id,
            lineage_id=logical_record["lineage_id"],
            proposer=proposer,
            approver=governance_actor,
            reason=reason,
            created_utc=utc_now_iso(),
            logical_after={cell_id: retired_logical},
            runtime_after={cell_id: retired_runtime},
            lineage_entries=[
                self._build_lineage_entry(
                    ledger=ledger,
                    lineage_id=logical_record["lineage_id"],
                    cell_id=cell_id,
                    action="retire",
                    event_id="pending",
                    parent_cell_id=logical_record["parent_cell_id"],
                    note=reason,
                )
            ],
            details={"kind": "retire"},
        )
        if normalize_after:
            self._auto_return_to_steady(
                proposer="fabric:auto_consolidation",
                approver=governance_actor,
                reason="auto return from burst to steady state after consolidation",
            )
        return {
            "event_id": event["event_id"],
            "cell_id": cell_id,
            "runtime_state": RETIRED_STATE,
            "population": self.summary(),
        }

    def replay_history(self) -> dict[str, Any]:
        history = self._load_or_initialize(
            self.store.lifecycle_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.lifecycle_history.v1", "entries": []},
        )
        logical_state: dict[str, Any] = {}
        runtime_state: dict[str, Any] = {}
        lineage_entries: list[dict[str, Any]] = []

        for entry in history["entries"]:
            details = entry["details"]
            for cell_id, payload in details["logical_after"].items():
                if payload is None:
                    logical_state.pop(cell_id, None)
                else:
                    logical_state[cell_id] = deepcopy(payload)
            for cell_id, payload in details["runtime_after"].items():
                if payload is None:
                    runtime_state.pop(cell_id, None)
                else:
                    runtime_state[cell_id] = deepcopy(payload)
            for ledger_entry in details["lineage_entries_added"]:
                lineage_entries.append(deepcopy(ledger_entry))

        current_logical = self._load_or_initialize(
            self.store.logical_population_path(self.fabric_id),
            {"schema_version": "agif.fabric.logical_population.v1", "cells": {}},
        )
        current_runtime = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        replay_digest = self._state_digest(logical_state, runtime_state)
        current_digest = self._state_digest(current_logical["cells"], current_runtime["states"])
        return {
            "event_count": len(history["entries"]),
            "lineage_entry_count": len(lineage_entries),
            "replay_digest": replay_digest,
            "current_digest": current_digest,
            "replay_match": replay_digest == current_digest,
        }

    def register_need_signal(self, *, signal: dict[str, Any]) -> dict[str, Any]:
        normalized = ensure_need_signal(signal, action="record")
        signals = self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )
        signals["signals"][normalized["need_signal_id"]] = normalized
        write_json_atomic(self.store.need_signals_path(self.fabric_id), signals)
        return normalized

    def load_need_signals(self) -> list[dict[str, Any]]:
        signals = self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )
        return [deepcopy(item) for _, item in sorted(signals["signals"].items())]

    def load_veto_log(self) -> list[dict[str, Any]]:
        vetoes = self._load_or_initialize(
            self.store.veto_log_path(self.fabric_id),
            {"schema_version": "agif.fabric.veto_log.v1", "entries": []},
        )
        return [deepcopy(item) for item in vetoes["entries"]]

    def _auto_return_to_steady(self, *, proposer: str, approver: str, reason: str) -> None:
        active_cells = self.list_active_cells()
        overflow = len(active_cells) - self.steady_active_target
        if overflow <= 0:
            return
        for cell_id in active_cells[:overflow]:
            self.hibernate_cell(
                cell_id=cell_id,
                proposer=proposer,
                tissue_approver=approver,
                reason=reason,
                normalize_after=False,
            )

    def _load_runtime_bundle(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        logical = self._load_or_initialize(
            self.store.logical_population_path(self.fabric_id),
            {"schema_version": "agif.fabric.logical_population.v1", "cells": {}},
        )
        runtime = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        history = self._load_or_initialize(
            self.store.lifecycle_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.lifecycle_history.v1", "entries": []},
        )
        ledger = self._load_or_initialize(
            self.store.lineage_ledger_path(self.fabric_id),
            {"schema_version": "agif.fabric.lineage_ledger.v1", "entries": []},
        )
        return logical, runtime, history, ledger

    def _record_transition(
        self,
        *,
        logical: dict[str, Any],
        runtime: dict[str, Any],
        history: dict[str, Any],
        ledger: dict[str, Any],
        transition: str,
        cell_id: str,
        lineage_id: str,
        proposer: str,
        approver: str,
        reason: str,
        created_utc: str,
        logical_after: dict[str, dict[str, Any] | None],
        runtime_after: dict[str, dict[str, Any] | None],
        lineage_entries: list[dict[str, Any]],
        details: dict[str, Any],
    ) -> dict[str, Any]:
        entry_index = len(history["entries"]) + 1
        snapshot_name = f"snapshot_{entry_index:05d}_pre"
        snapshot_path = self.store.lifecycle_snapshot_path(self.fabric_id, snapshot_name)
        snapshot_payload = {
            "snapshot_version": "agif.fabric.lifecycle_snapshot.v1",
            "created_utc": created_utc,
            "logical_cells": logical["cells"],
            "runtime_states": runtime["states"],
            "lineage_entries": ledger["entries"],
        }
        write_json_atomic(snapshot_path, snapshot_payload)

        event_id = f"lifecycle_{entry_index:05d}"
        rollback_ref = repo_relative(snapshot_path)
        event = {
            "event_id": event_id,
            "cell_id": cell_id,
            "lineage_id": lineage_id,
            "transition": transition,
            "reason": reason,
            "proposer": proposer,
            "approver": approver,
            "veto_ref": None,
            "rollback_ref": rollback_ref,
            "created_utc": created_utc,
        }

        logical_before = {key: deepcopy(logical["cells"].get(key)) for key in logical_after}
        runtime_before = {key: deepcopy(runtime["states"].get(key)) for key in runtime_after}
        normalized_logical_after: dict[str, dict[str, Any] | None] = {}
        for key, payload in logical_after.items():
            if payload is None:
                logical["cells"].pop(key, None)
                normalized_logical_after[key] = None
            else:
                normalized_payload = deepcopy(payload)
                logical["cells"][key] = normalized_payload
                normalized_logical_after[key] = deepcopy(normalized_payload)
        normalized_runtime_after: dict[str, dict[str, Any] | None] = {}
        for key, payload in runtime_after.items():
            if payload is None:
                runtime["states"].pop(key, None)
                normalized_runtime_after[key] = None
            else:
                normalized = deepcopy(payload)
                normalized["last_transition_ref"] = event_id
                runtime["states"][key] = normalized
                normalized_runtime_after[key] = deepcopy(normalized)

        normalized_entries: list[dict[str, Any]] = []
        for raw_entry in lineage_entries:
            entry = deepcopy(raw_entry)
            entry["entry_id"] = f"lineage_{len(ledger['entries']) + len(normalized_entries) + 1:05d}"
            entry["event_id"] = event_id
            normalized_entries.append(entry)
        ledger["entries"].extend(normalized_entries)

        history["entries"].append(
            {
                "history_id": f"history_{entry_index:05d}",
                "event": event,
                "details": {
                    "logical_before": logical_before,
                    "logical_after": normalized_logical_after,
                    "runtime_before": runtime_before,
                    "runtime_after": normalized_runtime_after,
                    "lineage_entries_added": normalized_entries,
                    **details,
                },
                "state_digest_after": self._state_digest(logical["cells"], runtime["states"]),
            }
        )

        write_json_atomic(self.store.logical_population_path(self.fabric_id), logical)
        write_json_atomic(self.store.runtime_states_path(self.fabric_id), runtime)
        write_json_atomic(self.store.lineage_ledger_path(self.fabric_id), ledger)
        write_json_atomic(self.store.lifecycle_history_path(self.fabric_id), history)
        self.summary()
        return event

    def _build_logical_record(
        self,
        *,
        blueprint: dict[str, Any],
        lineage_id: str,
        lifecycle_state: str,
        parent_cell_id: str | None,
        ancestor_cell_ids: list[str],
        source_blueprint_cell_id: str,
        source_role_name: str,
        merged_from_cell_ids: list[str],
        trust_ancestry: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return {
            "cell_id": blueprint["cell_id"],
            "lineage_id": lineage_id,
            "lifecycle_state": lifecycle_state,
            "blueprint": deepcopy(blueprint),
            "descriptor_eligibility": list(blueprint["descriptor_kinds"]),
            "policy_envelope": deepcopy(blueprint["policy_envelope"]),
            "trust_ancestry": deepcopy(trust_ancestry) if trust_ancestry is not None else [deepcopy(blueprint["trust_profile"])],
            "parent_cell_id": parent_cell_id,
            "ancestor_cell_ids": list(ancestor_cell_ids),
            "source_blueprint_cell_id": source_blueprint_cell_id,
            "source_role_name": source_role_name,
            "merged_from_cell_ids": list(merged_from_cell_ids),
            "activation_count": 0,
            "retired_utc": None,
        }

    def _build_runtime_state(
        self,
        *,
        cell_id: str,
        lineage_id: str,
        runtime_state: str,
        last_transition_ref: str | None,
        active_task_ref: str | None = None,
        workspace_subscriptions: list[str] | None = None,
        loaded_descriptor_refs: list[str] | None = None,
        current_need_signals: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "cell_id": cell_id,
            "lineage_id": lineage_id,
            "runtime_state": runtime_state,
            "active_task_ref": active_task_ref,
            "workspace_subscriptions": sorted(workspace_subscriptions or []),
            "loaded_descriptor_refs": sorted(loaded_descriptor_refs or []),
            "current_need_signals": sorted(current_need_signals or []),
            "last_transition_ref": last_transition_ref,
        }

    def _build_lineage_entry(
        self,
        *,
        ledger: dict[str, Any],
        lineage_id: str,
        cell_id: str,
        action: str,
        event_id: str,
        parent_cell_id: str | None,
        note: str,
    ) -> dict[str, Any]:
        return {
            "entry_id": f"lineage_{len(ledger['entries']) + 1:05d}",
            "lineage_id": lineage_id,
            "cell_id": cell_id,
            "event_id": event_id,
            "action": action,
            "parent_cell_id": parent_cell_id,
            "note": note,
            "created_utc": utc_now_iso(),
        }

    def _collect_merge_conflicts(
        self,
        survivor: dict[str, Any],
        merged: dict[str, Any],
        survivor_runtime: dict[str, Any],
        merged_runtime: dict[str, Any],
    ) -> list[str]:
        conflicts: list[str] = []
        if survivor["blueprint"]["role_family"] != merged["blueprint"]["role_family"]:
            conflicts.append("role_family")
        if sorted(survivor["blueprint"]["descriptor_kinds"]) != sorted(merged["blueprint"]["descriptor_kinds"]):
            conflicts.append("descriptor_kinds")
        if canonical_json_hash(survivor["blueprint"]["trust_profile"]) != canonical_json_hash(merged["blueprint"]["trust_profile"]):
            conflicts.append("trust_profile")
        if canonical_json_hash(survivor["blueprint"]["policy_envelope"]) != canonical_json_hash(
            merged["blueprint"]["policy_envelope"]
        ):
            conflicts.append("policy_envelope")
        if not survivor["lineage_id"] or not merged["lineage_id"]:
            conflicts.append("lineage_missing")
        if not survivor["blueprint"].get("bundle_ref") or not merged["blueprint"].get("bundle_ref"):
            conflicts.append("payload_ref_validity")
        if not survivor_runtime.get("last_transition_ref") or not merged_runtime.get("last_transition_ref"):
            conflicts.append("rollback_coverage")
        return conflicts

    def _next_child_ids(
        self,
        *,
        parent_cell_id: str,
        lineage_id: str,
        child_count: int,
        logical: dict[str, Any],
    ) -> list[str]:
        lineage_cells = [
            cell_id
            for cell_id, record in logical["cells"].items()
            if record["lineage_id"] == lineage_id and "__child_" in cell_id
        ]
        next_index = len(lineage_cells) + 1
        child_ids: list[str] = []
        for offset in range(child_count):
            child_ids.append(f"{parent_cell_id}__child_{next_index + offset:03d}")
        return child_ids

    def _raise_veto(
        self,
        *,
        action: str,
        code: str,
        message: str,
        proposer: str,
        related_cells: list[str],
        reason: str,
    ) -> None:
        vetoes = self._load_or_initialize(
            self.store.veto_log_path(self.fabric_id),
            {"schema_version": "agif.fabric.veto_log.v1", "entries": []},
        )
        veto_id = f"veto_{len(vetoes['entries']) + 1:05d}"
        vetoes["entries"].append(
            {
                "veto_id": veto_id,
                "action": action,
                "code": code,
                "message": message,
                "proposer": proposer,
                "related_cells": list(related_cells),
                "reason": reason,
                "created_utc": utc_now_iso(),
            }
        )
        write_json_atomic(self.store.veto_log_path(self.fabric_id), vetoes)
        raise FabricError(code, f"{message} (veto_ref={veto_id})")

    def _refresh_state(self, summary: dict[str, Any]) -> None:
        self.state["steady_active_population_target"] = summary["steady_active_population_target"]
        self.state["burst_active_population_cap"] = summary["burst_active_population_cap"]
        self.state["active_population"] = summary["active_population"]
        self.state["logical_population"] = summary["logical_population"]
        self.state["dormant_population"] = summary["dormant_population"]
        self.state["retired_population"] = summary["retired_population"]
        self.state["lineage_count"] = summary["lineage_count"]
        self.state["lifecycle_event_count"] = summary["lifecycle_event_count"]
        self.state["last_lifecycle_event_ref"] = summary["last_lifecycle_event_ref"]
        self.store.save_state(self.state)

    def _require_cell(self, logical: dict[str, Any], cell_id: str) -> dict[str, Any]:
        record = logical["cells"].get(cell_id)
        if record is None:
            raise FabricError("CELL_NOT_FOUND", f"Unknown logical cell: {cell_id}.")
        return record

    def _require_runtime_cell(self, runtime: dict[str, Any], cell_id: str) -> dict[str, Any]:
        record = runtime["states"].get(cell_id)
        if record is None:
            raise FabricError("CELL_NOT_FOUND", f"Unknown runtime cell: {cell_id}.")
        return record

    def _count_active(self, runtime_states: dict[str, dict[str, Any]]) -> int:
        return len([item for item in runtime_states.values() if item["runtime_state"] in RUNTIME_CONSUMING_STATES])

    def _root_lineage_id(self, cell_id: str) -> str:
        return f"lineage::{cell_id}"

    def _append_unique(self, values: list[str], item: str) -> list[str]:
        return sorted(set(values + [item]))

    def _state_digest(self, logical_cells: dict[str, Any], runtime_states: dict[str, Any]) -> str:
        structural_runtime = {
            cell_id: {
                "cell_id": record["cell_id"],
                "lineage_id": record["lineage_id"],
                "runtime_state": record["runtime_state"],
                "current_need_signals": list(record["current_need_signals"]),
                "last_transition_ref": record["last_transition_ref"],
            }
            for cell_id, record in sorted(runtime_states.items())
        }
        return canonical_json_hash({"logical": logical_cells, "runtime": structural_runtime})

    def _load_or_initialize(self, path: Any, default_payload: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        value = load_json_file(
            path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label=str(path.name),
        )
        if not isinstance(value, dict):
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        return value
