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
from intelligence.fabric.domain import (
    execute_phase7_workflow,
    is_phase7_profile,
    phase7_workflow_identity,
    replay_phase7_workflow,
)
from intelligence.fabric.execution.bounded_executor import execute_foundation_workflow
from intelligence.fabric.governance.authority import AuthorityEngine
from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.metrics.reporting import build_status_metrics
from intelligence.fabric.memory.episodic_store import EpisodicStore
from intelligence.fabric.memory.manager import FabricMemoryManager
from intelligence.fabric.memory.suggestions_store import SuggestionsStore
from intelligence.fabric.needs.engine import NeedSignalManager, score_foundation_needs
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.routing import RoutingEngine
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
    FabricMemoryManager(store=store, state=state, config=config).refresh_hot_memory()
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

    config, _, registry, _ = load_fabric_bootstrap((REPO_ROOT / str(state["config_ref"])).resolve())
    lifecycle = FabricLifecycleManager(store=store, state=state, config=config, utility_profiles=registry["utility_profiles"])
    population = lifecycle.summary()
    state = store.load_state(state["fabric_id"])
    metrics = build_status_metrics(state)
    need_manager = NeedSignalManager(store=store, state=state, config=config)
    authority_engine = AuthorityEngine(store=store, state=state, config=config)
    routing_engine = RoutingEngine(store=store, state=state, config=config, registry=registry)
    memory_manager = FabricMemoryManager(store=store, state=state, config=config)
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
        "phase6": {
            "need_summary": need_manager.summary(),
            "routing_summary": routing_engine.summary(),
            "authority_summary": authority_engine.summary(),
            "utility_summary": lifecycle.evaluate_runtime_choices(),
            "memory_summary": memory_manager.summary(),
        },
        "last_run_ref": state.get("last_run_ref"),
        "last_replay_ref": state.get("last_replay_ref"),
    }


def command_run() -> dict[str, Any]:
    workflow_payload = _load_stdin_json()
    state, config, registry, store, lifecycle = _load_current_runtime_context()
    need_manager = NeedSignalManager(store=store, state=state, config=config)
    authority_engine = AuthorityEngine(store=store, state=state, config=config)
    routing_engine = RoutingEngine(store=store, state=state, config=config, registry=registry)
    memory_manager = FabricMemoryManager(store=store, state=state, config=config)

    if is_phase7_profile(config):
        workflow_id, _ = phase7_workflow_identity(workflow_payload)
        workspace_path = store.workspace_path(state["fabric_id"], workflow_id)
        execution = execute_phase7_workflow(
            workflow_payload=workflow_payload,
            config=config,
            registry=registry,
            lifecycle=lifecycle,
            memory_manager=memory_manager,
            need_manager=need_manager,
            authority_engine=authority_engine,
            routing_engine=routing_engine,
            workspace_ref=repo_relative(workspace_path),
        )
        write_json_atomic(workspace_path, execution["workspace_snapshot"])
        routing_decision = {
            "decision_id": execution["phase7"]["authority_review_ids"][0]
            if execution["phase7"]["authority_review_ids"]
            else "phase7:multi_stage",
            "selected_cells": list(execution["result"]["selected_cells"]),
            "selection_mode": "selected",
            "route_confidence": 0.84 if execution["result"]["final_status"] == "accepted" else 0.78,
            "benchmark_class": execution["phase7"]["benchmark_class"],
            "stage_decision_refs": [item["decision_ref"] for item in execution["trace"]],
        }
        activation = {
            "workflow_id": workflow_id,
            "activated_cells": list(execution["result"]["selected_cells"]),
            "reused_cells": [],
            "population": lifecycle.summary(),
        }
    else:
        execution = execute_foundation_workflow(
            workflow_payload=workflow_payload,
            blueprints=registry["blueprints"],
            proof_domain=config["proof_domain"],
        )
        workflow_id = execution["workflow_id"]
        routing_decision = routing_engine.route_workflow(
            workflow_id=workflow_id,
            workflow_payload=workflow_payload,
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory_manager=memory_manager,
        )
        activation = lifecycle.activate_for_workflow(
            cell_ids=list(routing_decision["selected_cells"]),
            workflow_id=workflow_id,
            authority_engine=authority_engine,
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
                if blueprint["cell_id"] in routing_decision["selected_cells"]
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
        "routing": routing_decision,
    }
    run_path = store.run_path(state["fabric_id"], workflow_id)
    write_json_atomic(run_path, run_record)
    lifecycle.set_active_task_refs(cell_ids=list(routing_decision["selected_cells"]), workflow_ref=workflow_id)
    if str(config.get("benchmark_profile", {}).get("name", "")).startswith("phase6"):
        lifecycle.apply_routing_context(
            cell_ids=list(routing_decision["selected_cells"]),
            workspace_ref=repo_relative(workspace_path),
            descriptor_refs=list(routing_decision.get("descriptor_refs_used", [])),
            need_signal_ids=list(routing_decision.get("need_signal_ids", [])),
        )

    episodic_store = EpisodicStore(store.fabric_dir(state["fabric_id"]) / "episodic_events.json")
    state = store.load_state(state["fabric_id"])
    state["run_count"] = int(state.get("run_count", 0)) + 1
    state["last_run_ref"] = repo_relative(run_path)
    store.save_state(state)
    memory_result = memory_manager.record_run(
        workflow_payload=workflow_payload,
        execution=execution,
        run_ref=repo_relative(run_path),
        workspace_ref=repo_relative(workspace_path),
        lifecycle_manager=lifecycle,
        routing_decision=routing_decision,
        authority_engine=authority_engine,
    )
    if is_phase7_profile(config):
        phase7_outcome_kind = "success" if execution["result"]["final_status"] in {"accepted", "hold"} else "failure"
        phase7_effectiveness = 0.88 if execution["result"]["final_status"] == "accepted" else 0.78
        for trace_entry in execution["trace"]:
            routing_engine.record_outcome(
                decision_id=str(trace_entry["decision_ref"]),
                outcome_kind=phase7_outcome_kind,
                effectiveness_score=phase7_effectiveness,
                detail=f"stage={trace_entry['stage_id']}; final_status={execution['result']['final_status']}",
            )
    else:
        routing_engine.record_outcome(
            decision_id=str(routing_decision["decision_id"]),
            outcome_kind=_routing_outcome_kind(routing_decision=routing_decision, memory_result=memory_result),
            effectiveness_score=_routing_effectiveness_score(routing_decision=routing_decision, memory_result=memory_result),
            detail=f"selection_mode={routing_decision['selection_mode']}; memory_decision={memory_result['decision']}",
        )
    episodic_store.append_event(
        {
            "event_kind": "phase7_run" if is_phase7_profile(config) else "phase6_run",
            "workflow_id": workflow_id,
            "run_ref": repo_relative(run_path),
            "memory_candidate_id": memory_result["candidate_id"],
            "memory_decision_ref": memory_result["decision_ref"],
            "routing_decision_ref": routing_decision["decision_id"],
        }
    )

    return {
        "command": "fabric run",
        "fabric_id": state["fabric_id"],
        "workflow_id": workflow_id,
        "proof_domain": state["proof_domain"],
        "workspace_ref": repo_relative(workspace_path),
        "run_ref": repo_relative(run_path),
        "output_digest": execution["output_digest"],
        "executor": execution["executor"],
        "trace": execution["trace"],
        "result": execution["result"],
        "routing": routing_decision,
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

    if is_phase7_profile(config):
        workflow_id, _ = phase7_workflow_identity(workflow_payload)
        prior_run = store.load_run_record(state["fabric_id"], workflow_id)
        replay_context = dict(prior_run.get("execution", {}).get("phase7", {}).get("replay_context", {}))
        execution = replay_phase7_workflow(
            workflow_payload=workflow_payload,
            proof_domain=config["proof_domain"],
            replay_context=replay_context,
        )
    else:
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
    _bound_replay_outputs(
        store=store,
        fabric_id=state["fabric_id"],
        max_files=max(1, int(config.get("memory_caps", {}).get("replay_files", 8))),
    )
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
    memory_manager = FabricMemoryManager(store=store, state=state, config=config)
    memory_summary = memory_manager.summary()
    memory_replay = memory_manager.replay_decisions()
    need_manager = NeedSignalManager(store=store, state=state, config=config)
    authority_engine = AuthorityEngine(store=store, state=state, config=config)
    routing_engine = RoutingEngine(store=store, state=state, config=config, registry=registry)
    phase6 = {
        "need_summary": need_manager.summary(),
        "routing_summary": routing_engine.summary(),
        "authority_summary": authority_engine.summary(),
        "utility_summary": lifecycle.evaluate_runtime_choices(),
    }
    earned_pass_tokens = ["AGIF_FABRIC_P3_PASS"]
    if (
        population["logical_population"] > population["active_population"]
        and lifecycle_replay["replay_match"]
        and population["within_burst_active_cap"]
        and population["within_runtime_working_set_cap"]
    ):
        earned_pass_tokens.append("AGIF_FABRIC_P4_PASS")
    if (
        lifecycle_replay["replay_match"]
        and population["within_runtime_working_set_cap"]
        and all(bool(value) for value in memory_summary["within_caps"].values())
        and memory_summary["raw_log_promoted_count"] == 0
        and memory_summary["cold_reference_integrity"]
        and memory_summary["bounded_replay_store"]
        and memory_replay["replay_match"]
    ):
        earned_pass_tokens.append("AGIF_FABRIC_P5_PASS")
    if (
        "AGIF_FABRIC_P5_PASS" in earned_pass_tokens
        and phase6["need_summary"]["active_signal_count"] >= 0
        and phase6["need_summary"]["traceable_resolution_count"] >= 1
        and phase6["need_summary"]["expired_signal_count"] >= 1
        and phase6["routing_summary"]["decision_count"] >= 1
        and phase6["routing_summary"]["deterministic_reason_count"] >= 1
        and phase6["authority_summary"]["review_count"] >= 1
        and phase6["authority_summary"]["approved_count"] >= 1
        and phase6["authority_summary"]["veto_count"] >= 1
    ):
        earned_pass_tokens.append("AGIF_FABRIC_P6_PASS")
    evidence_bundle = {
        "bundle_version": "agif.fabric.phase6.evidence.v1",
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
        "memory": memory_summary,
        "memory_replay": memory_replay,
        "phase6": phase6,
        "logical_population_ref": repo_relative(store.logical_population_path(state["fabric_id"])),
        "runtime_states_ref": repo_relative(store.runtime_states_path(state["fabric_id"])),
        "lifecycle_history_ref": repo_relative(store.lifecycle_history_path(state["fabric_id"])),
        "lineage_ledger_ref": repo_relative(store.lineage_ledger_path(state["fabric_id"])),
        "veto_log_ref": repo_relative(store.veto_log_path(state["fabric_id"])),
        "need_history_ref": repo_relative(store.need_history_path(state["fabric_id"])),
        "need_resolution_ref": repo_relative(store.need_resolution_path(state["fabric_id"])),
        "routing_decisions_ref": repo_relative(store.routing_decisions_path(state["fabric_id"])),
        "routing_memory_ref": repo_relative(store.routing_memory_path(state["fabric_id"])),
        "authority_reviews_ref": repo_relative(store.authority_reviews_path(state["fabric_id"])),
        "authority_patterns_ref": repo_relative(store.authority_patterns_path(state["fabric_id"])),
        "hot_memory_index_ref": repo_relative(store.hot_memory_index_path(state["fabric_id"])),
        "raw_log_index_ref": repo_relative(store.raw_log_index_path(state["fabric_id"])),
        "memory_candidates_ref": repo_relative(store.memory_candidates_path(state["fabric_id"])),
        "memory_decisions_ref": repo_relative(store.memory_decisions_path(state["fabric_id"])),
        "descriptor_store_ref": repo_relative(store.descriptor_store_path(state["fabric_id"])),
        "promoted_memory_ref": repo_relative(store.promoted_memory_path(state["fabric_id"])),
        "memory_replay_store_ref": repo_relative(store.memory_replay_store_path(state["fabric_id"])),
        "memory_gc_log_ref": repo_relative(store.memory_gc_log_path(state["fabric_id"])),
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
    lifecycle = FabricLifecycleManager(store=store, state=state, config=config, utility_profiles=registry["utility_profiles"])
    return state, config, registry, store, lifecycle


def _routing_outcome_kind(*, routing_decision: dict[str, Any], memory_result: dict[str, Any]) -> str:
    if str(routing_decision.get("selection_mode")) != "selected":
        return "failure"
    if str(memory_result.get("decision")) in {"promote", "compress"} and float(routing_decision.get("route_confidence", 0.0)) >= 0.68:
        return "success"
    return "weak_success"


def _routing_effectiveness_score(*, routing_decision: dict[str, Any], memory_result: dict[str, Any]) -> float:
    confidence = float(routing_decision.get("route_confidence", 0.0))
    decision = str(memory_result.get("decision", ""))
    if decision in {"promote", "compress"}:
        bonus = 0.12
    elif decision == "defer":
        bonus = 0.03
    else:
        bonus = -0.08
    return max(0.0, min(1.0, round(confidence + bonus, 6)))


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


def _bound_replay_outputs(*, store: FabricStateStore, fabric_id: str, max_files: int) -> None:
    replay_dir = store.fabric_dir(fabric_id) / "replays"
    paths = sorted(
        replay_dir.glob("*.json"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    overflow = len(paths) - max_files
    if overflow <= 0:
        return
    for path in paths[:overflow]:
        path.unlink()
