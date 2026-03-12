"""Local runtime state storage for the Phase 3 fabric foundation."""

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

