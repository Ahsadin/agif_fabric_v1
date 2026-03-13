"""Local runtime state storage for the AGIF fabric runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from intelligence.fabric.common import (
    FabricError,
    load_json_file,
    repo_relative,
    resolve_state_root,
    write_json_atomic,
)


class FabricStateStore:
    """Stores bounded local fabric runtime state outside source control."""

    def __init__(self, root: Path | None = None):
        self.root = (root or resolve_state_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "current_fabric.json"

    def initialize(
        self,
        *,
        config: dict[str, Any],
        registry: dict[str, Any],
        config_path: Path,
        registry_path: Path,
        initialized_utc: str,
    ) -> dict[str, Any]:
        fabric_id = config["fabric_id"]
        fabric_dir = self.fabric_dir(fabric_id)
        fabric_dir.mkdir(parents=True, exist_ok=True)
        (fabric_dir / "workspace").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "runs").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "replays").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "evidence").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "lifecycle").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "lifecycle" / "snapshots").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "governance").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "needs").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "routing").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "memory").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "memory" / "hot" / "payloads").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "memory" / "warm" / "payloads").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "memory" / "cold" / "payloads").mkdir(parents=True, exist_ok=True)
        (fabric_dir / "memory" / "ephemeral" / "raw_logs").mkdir(parents=True, exist_ok=True)

        state = {
            "state_version": "agif.fabric.state.v1",
            "fabric_id": fabric_id,
            "proof_domain": config["proof_domain"],
            "status": "initialized",
            "initialized_utc": initialized_utc,
            "config_ref": repo_relative(config_path),
            "blueprint_registry_ref": repo_relative(registry_path),
            "registered_blueprint_count": len(registry["blueprints"]),
            "utility_profile_count": len(registry["utility_profiles"]),
            "active_population_cap": config["active_population_cap"],
            "logical_population_cap": config["logical_population_cap"],
            "steady_active_population_target": config["active_population_cap"],
            "burst_active_population_cap": min(
                int(config["logical_population_cap"]),
                int(config.get("governance_policy", {}).get("burst_active_population_cap", config["active_population_cap"] * 2)),
            ),
            "active_population": 0,
            "logical_population": 0,
            "dormant_population": 0,
            "retired_population": 0,
            "lineage_count": 0,
            "lifecycle_event_count": 0,
            "last_lifecycle_event_ref": None,
            "run_count": 0,
            "last_run_ref": None,
            "last_replay_ref": None,
        }
        write_json_atomic(self.state_path(fabric_id), state)
        write_json_atomic(
            self.current_path,
            {
                "fabric_id": fabric_id,
                "state_ref": repo_relative(self.state_path(fabric_id)),
            },
        )
        return state

    def load_current_state(self) -> dict[str, Any] | None:
        if not self.current_path.exists():
            return None
        pointer = load_json_file(
            self.current_path,
            not_found_code="FABRIC_NOT_INITIALIZED",
            invalid_code="STATE_INVALID",
            label="Current fabric pointer",
        )
        if not isinstance(pointer, dict) or "fabric_id" not in pointer:
            raise FabricError("STATE_INVALID", "Current fabric pointer is invalid.")
        return self.load_state(str(pointer["fabric_id"]))

    def load_state(self, fabric_id: str) -> dict[str, Any]:
        state = load_json_file(
            self.state_path(fabric_id),
            not_found_code="FABRIC_NOT_INITIALIZED",
            invalid_code="STATE_INVALID",
            label="Fabric state",
        )
        if not isinstance(state, dict):
            raise FabricError("STATE_INVALID", "Fabric state must be an object.")
        return state

    def save_state(self, state: dict[str, Any]) -> None:
        write_json_atomic(self.state_path(str(state["fabric_id"])), state)

    def fabric_dir(self, fabric_id: str) -> Path:
        return self.root / fabric_id

    def state_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "state.json"

    def workspace_path(self, fabric_id: str, workflow_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "workspace" / f"{workflow_id}.json"

    def run_path(self, fabric_id: str, workflow_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "runs" / f"{workflow_id}.json"

    def replay_path(self, fabric_id: str, replay_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "replays" / f"{replay_id}.json"

    def logical_population_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "lifecycle" / "logical_population.json"

    def runtime_states_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "lifecycle" / "runtime_states.json"

    def lifecycle_history_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "lifecycle" / "history.json"

    def lineage_ledger_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "lifecycle" / "lineage_ledger.json"

    def lifecycle_metrics_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "lifecycle" / "metrics.json"

    def lifecycle_snapshot_path(self, fabric_id: str, snapshot_name: str) -> Path:
        return self.fabric_dir(fabric_id) / "lifecycle" / "snapshots" / f"{snapshot_name}.json"

    def veto_log_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "governance" / "veto_log.json"

    def need_signals_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "needs" / "signals.json"

    def need_history_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "needs" / "history.json"

    def routing_decisions_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "routing" / "decisions.json"

    def authority_reviews_path(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "governance" / "authority_reviews.json"

    def memory_dir(self, fabric_id: str) -> Path:
        return self.fabric_dir(fabric_id) / "memory"

    def hot_memory_index_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "hot_index.json"

    def raw_log_index_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "raw_logs.json"

    def raw_log_payload_path(self, fabric_id: str, log_id: str) -> Path:
        return self.memory_dir(fabric_id) / "ephemeral" / "raw_logs" / f"{log_id}.json"

    def memory_candidates_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "candidates.json"

    def memory_decisions_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "decisions.json"

    def descriptor_store_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "descriptors.json"

    def promoted_memory_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "promoted.json"

    def memory_replay_store_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "replay_store.json"

    def memory_gc_log_path(self, fabric_id: str) -> Path:
        return self.memory_dir(fabric_id) / "gc_log.json"

    def memory_tier_payload_path(self, fabric_id: str, tier: str, payload_name: str) -> Path:
        return self.memory_dir(fabric_id) / tier / "payloads" / f"{payload_name}.json"

    def load_run_record(self, fabric_id: str, workflow_id: str) -> dict[str, Any]:
        record = load_json_file(
            self.run_path(fabric_id, workflow_id),
            not_found_code="RUN_RECORD_NOT_FOUND",
            invalid_code="RUN_RECORD_INVALID",
            label="Run record",
        )
        if not isinstance(record, dict):
            raise FabricError("RUN_RECORD_INVALID", "Run record must be an object.")
        return record
