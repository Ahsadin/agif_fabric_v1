"""CLI for the AGIF Phase 3 fabric foundation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from intelligence.fabric.common import (
    FabricError,
    REPO_ROOT,
    canonical_json_hash,
    ensure_non_empty_string,
    load_json_file,
    repo_relative,
    utc_now_iso,
    write_json_atomic,
)
from intelligence.fabric.execution.bounded_executor import execute_foundation_workflow
from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.metrics.reporting import build_status_metrics
from intelligence.fabric.memory.episodic_store import EpisodicStore
from intelligence.fabric.memory.suggestions_store import SuggestionsStore
from intelligence.fabric.needs.engine import score_foundation_needs
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.state_store import FabricStateStore
from intelligence.fabric.workspace.store import build_workspace_snapshot


USAGE = (
    "runner/cell fabric init <config_path>",
    "runner/cell fabric run",
    "runner/cell fabric status",
    "runner/cell fabric replay <replay_manifest_path>",
    "runner/cell fabric evidence <output_path>",
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        payload = dispatch(args)
    except FabricError as err:
        sys.stdout.write(_json_line({"ok": False, "error": {"code": err.code, "message": err.message}}))
        return err.exit_code
    except Exception as err:  # pragma: no cover - fail-closed guardrail
        sys.stdout.write(
            _json_line(
                {
                    "ok": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Unexpected internal error: {err}",
                    },
                }
            )
        )
        return 1

    sys.stdout.write(_json_line({"ok": True, "data": payload}))
    return 0


def dispatch(args: list[str]) -> dict[str, Any]:
    if len(args) < 2 or args[0] != "fabric":
        raise FabricError("USAGE_INVALID", f"Usage: {' | '.join(USAGE)}", exit_code=2)

    command = args[1]
    if command == "init":
        if len(args) != 3:
            raise FabricError("USAGE_INVALID", "fabric init requires exactly one config path.", exit_code=2)
        return command_init(Path(args[2]))
    if command == "run":
        if len(args) != 2:
            raise FabricError("USAGE_INVALID", "fabric run does not accept positional arguments.", exit_code=2)
        return command_run()
    if command == "status":
        if len(args) != 2:
            raise FabricError("USAGE_INVALID", "fabric status does not accept positional arguments.", exit_code=2)
        return command_status()
    if command == "replay":
        if len(args) != 3:
            raise FabricError("USAGE_INVALID", "fabric replay requires exactly one manifest path.", exit_code=2)
        return command_replay(Path(args[2]))
    if command == "evidence":
        if len(args) != 3:
            raise FabricError("USAGE_INVALID", "fabric evidence requires exactly one output path.", exit_code=2)
        return command_evidence(Path(args[2]))
    raise FabricError("USAGE_INVALID", f"Unknown fabric command: {command}.", exit_code=2)


def command_init(config_path: Path) -> dict[str, Any]:
    config, resolved_config_path, registry, registry_path = load_fabric_bootstrap(config_path)
    store = FabricStateStore()
    state = store.initialize(
        config=config,
        registry=registry,
        config_path=resolved_config_path,
        registry_path=registry_path,
        initialized_utc=utc_now_iso(),
    )
    lifecycle = FabricLifecycleManager(store=store, state=state, config=config).bootstrap_population(
        registry=registry,
        initialized_utc=state["initialized_utc"],
    )
    return {
        "command": "fabric init",
        "fabric_id": config["fabric_id"],
        "proof_domain": config["proof_domain"],
        "registered_blueprints": len(registry["blueprints"]),
        "utility_profiles": len(registry["utility_profiles"]),
        "state_ref": repo_relative(store.state_path(config["fabric_id"])),
        "config_ref": repo_relative(resolved_config_path),
        "blueprint_registry_ref": repo_relative(registry_path),
        "status": state["status"],
        "population": lifecycle,
    }


def command_status() -> dict[str, Any]:
    store = FabricStateStore()
    state = store.load_current_state()
    if state is None:
        return {
            "command": "fabric status",
            "initialized": False,
            "state_root": repo_relative(store.root),
        }

    config, _, _, _ = load_fabric_bootstrap((REPO_ROOT / str(state["config_ref"])).resolve())
    lifecycle = FabricLifecycleManager(store=store, state=state, config=config)
    population = lifecycle.summary()
    state = store.load_state(state["fabric_id"])
    metrics = build_status_metrics(state)
    needs = score_foundation_needs(
        fabric_id=state["fabric_id"],
        registered_blueprints=int(state["registered_blueprint_count"]),
        active_population_cap=int(state["active_population_cap"]),
        logical_population=population["logical_population"],
        active_population=population["active_population"],
        burst_active_population_cap=population["burst_active_population_cap"],
    )
    suggestions_store = SuggestionsStore(store.fabric_dir(state["fabric_id"]) / "suggestions.json")
    return {
        "command": "fabric status",
        "initialized": True,
        "fabric_id": state["fabric_id"],
        "proof_domain": state["proof_domain"],
        "status": state["status"],
        "config_ref": state["config_ref"],
        "blueprint_registry_ref": state["blueprint_registry_ref"],
        "metrics": metrics,
        "needs": needs,
        "recorded_need_signals": lifecycle.load_need_signals(),
        "active_suggestions": suggestions_store.count_active(),
        "governance": lifecycle.governance_summary(),
        "population": population,
        "last_run_ref": state.get("last_run_ref"),
        "last_replay_ref": state.get("last_replay_ref"),
    }


def command_run() -> dict[str, Any]:
    workflow_payload = _load_stdin_json()
    state, config, registry, store, lifecycle = _load_current_runtime_context()

    execution = execute_foundation_workflow(
        workflow_payload=workflow_payload,
        blueprints=registry["blueprints"],
        proof_domain=config["proof_domain"],
    )
    workflow_id = execution["workflow_id"]
    activation = lifecycle.activate_for_workflow(
        cell_ids=list(execution["result"]["selected_cells"]),
        workflow_id=workflow_id,
    )
    workspace_snapshot = build_workspace_snapshot(
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        selected_blueprints=[
            {
                "cell_id": blueprint["cell_id"],
                "role_name": blueprint["role_name"],
                "role_family": blueprint["role_family"],
            }
            for blueprint in registry["blueprints"]
        ],
    )
    workspace_path = store.workspace_path(state["fabric_id"], workflow_id)
    write_json_atomic(workspace_path, workspace_snapshot)

    run_record = {
        "workflow_id": workflow_id,
        "created_utc": utc_now_iso(),
        "input_digest": canonical_json_hash(workflow_payload),
        "workspace_ref": repo_relative(workspace_path),
        "execution": execution,
    }
    run_path = store.run_path(state["fabric_id"], workflow_id)
    write_json_atomic(run_path, run_record)
    lifecycle.set_active_task_refs(cell_ids=list(execution["result"]["selected_cells"]), workflow_ref=None)

    episodic_store = EpisodicStore(store.fabric_dir(state["fabric_id"]) / "episodic_events.json")
    episodic_store.append_event(
        {
            "event_kind": "phase3_run",
            "workflow_id": workflow_id,
            "run_ref": repo_relative(run_path),
        }
    )

    state = store.load_state(state["fabric_id"])
    state["run_count"] = int(state.get("run_count", 0)) + 1
    state["last_run_ref"] = repo_relative(run_path)
    store.save_state(state)

    return {
        "command": "fabric run",
        "fabric_id": state["fabric_id"],
        "workflow_id": workflow_id,
        "proof_domain": state["proof_domain"],
        "workspace_ref": repo_relative(workspace_path),
        "run_ref": repo_relative(run_path),
        "executor": execution["executor"],
        "trace": execution["trace"],
        "result": execution["result"],
        "activation": activation,
        "governance": lifecycle.governance_summary(),
        "population": lifecycle.summary(),
    }


def command_replay(manifest_path: Path) -> dict[str, Any]:
    state, config, registry, store, lifecycle = _load_current_runtime_context()
    manifest_raw = load_json_file(
        manifest_path.resolve(),
        not_found_code="REPLAY_MANIFEST_NOT_FOUND",
        invalid_code="REPLAY_MANIFEST_INVALID",
        label="Replay manifest",
    )
    if not isinstance(manifest_raw, dict):
        raise FabricError("REPLAY_MANIFEST_INVALID", "Replay manifest must be an object.")

    workflow_payload_ref = ensure_non_empty_string(
        manifest_raw.get("workflow_payload_path"),
        "Replay manifest workflow_payload_path",
        code="REPLAY_MANIFEST_INVALID",
    )
    workflow_payload_path = (manifest_path.resolve().parent / workflow_payload_ref).resolve()
    workflow_payload = load_json_file(
        workflow_payload_path,
        not_found_code="INPUT_NOT_FOUND",
        invalid_code="INPUT_INVALID_JSON",
        label="Replay workflow payload",
    )
    if not isinstance(workflow_payload, dict):
        raise FabricError("INPUT_INVALID_JSON", "Replay workflow payload must be an object.")

    execution = execute_foundation_workflow(
        workflow_payload=workflow_payload,
        blueprints=registry["blueprints"],
        proof_domain=config["proof_domain"],
    )
    workflow_id = execution["workflow_id"]
    prior_run = store.load_run_record(state["fabric_id"], workflow_id)
    replay_match = prior_run.get("execution", {}).get("output_digest") == execution["output_digest"]

    replay_record = {
        "replay_id": f"replay_{workflow_id}",
        "workflow_id": workflow_id,
        "created_utc": utc_now_iso(),
        "manifest_ref": repo_relative(manifest_path.resolve()),
        "replay_match": replay_match,
        "execution": execution,
    }
    replay_path = store.replay_path(state["fabric_id"], f"replay_{workflow_id}")
    write_json_atomic(replay_path, replay_record)
    state["last_replay_ref"] = repo_relative(replay_path)
    store.save_state(state)
    lifecycle_replay = lifecycle.replay_history()

    return {
        "command": "fabric replay",
        "fabric_id": state["fabric_id"],
        "workflow_id": workflow_id,
        "replay_match": replay_match,
        "lifecycle_replay_match": lifecycle_replay["replay_match"],
        "replay_ref": repo_relative(replay_path),
        "trace": execution["trace"],
        "output_digest": execution["output_digest"],
    }


def command_evidence(output_path: Path) -> dict[str, Any]:
    state, config, registry, store, lifecycle = _load_current_runtime_context()
    status_payload = command_status()
    population = lifecycle.summary()
    lifecycle_replay = lifecycle.replay_history()
    earned_pass_tokens = ["AGIF_FABRIC_P3_PASS"]
    if (
        population["logical_population"] > population["active_population"]
        and lifecycle_replay["replay_match"]
        and population["within_burst_active_cap"]
        and population["within_runtime_working_set_cap"]
    ):
        earned_pass_tokens.append("AGIF_FABRIC_P4_PASS")
    evidence_bundle = {
        "bundle_version": "agif.fabric.phase4.evidence.v1",
        "created_utc": utc_now_iso(),
        "pass_token": "AGIF_FABRIC_P3_PASS",
        "earned_pass_tokens": earned_pass_tokens,
        "fabric_id": state["fabric_id"],
        "proof_domain": config["proof_domain"],
        "config_ref": state["config_ref"],
        "blueprint_registry_ref": state["blueprint_registry_ref"],
        "registered_blueprints": [item["cell_id"] for item in registry["blueprints"]],
        "status": status_payload,
        "population": population,
        "lifecycle_replay": lifecycle_replay,
        "logical_population_ref": repo_relative(store.logical_population_path(state["fabric_id"])),
        "runtime_states_ref": repo_relative(store.runtime_states_path(state["fabric_id"])),
        "lifecycle_history_ref": repo_relative(store.lifecycle_history_path(state["fabric_id"])),
        "lineage_ledger_ref": repo_relative(store.lineage_ledger_path(state["fabric_id"])),
        "veto_log_ref": repo_relative(store.veto_log_path(state["fabric_id"])),
    }
    write_json_atomic(output_path.resolve(), evidence_bundle)
    return {
        "command": "fabric evidence",
        "fabric_id": state["fabric_id"],
        "pass": True,
        "earned_pass_tokens": earned_pass_tokens,
        "evidence_ref": repo_relative(output_path.resolve()),
        "registered_blueprint_count": len(registry["blueprints"]),
    }


def _load_current_runtime_context() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    FabricStateStore,
    FabricLifecycleManager,
]:
    store = FabricStateStore()
    state = store.load_current_state()
    if state is None:
        raise FabricError("FABRIC_NOT_INITIALIZED", "Fabric is not initialized.")
    config_ref = Path(str(state["config_ref"]))
    if not config_ref.is_absolute():
        config_ref = (REPO_ROOT / config_ref).resolve()
    config, _, registry, _ = load_fabric_bootstrap(config_ref)
    lifecycle = FabricLifecycleManager(store=store, state=state, config=config)
    return state, config, registry, store, lifecycle


def _load_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if raw.strip() == "":
        raise FabricError("INPUT_INVALID_JSON", "Workflow payload is required on stdin.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as err:
        raise FabricError(
            "INPUT_INVALID_JSON",
            f"Workflow payload JSON invalid at line {err.lineno} column {err.colno}.",
        ) from err
    if not isinstance(value, dict):
        raise FabricError("INPUT_INVALID_JSON", "Workflow payload must be a JSON object.")
    return value


def _json_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
