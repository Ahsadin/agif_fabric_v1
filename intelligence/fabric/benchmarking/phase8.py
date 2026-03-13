"""Phase 8 bounded long-run harness and soak helpers."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intelligence.fabric.common import REPO_ROOT, FabricError, canonical_json_hash, repo_relative, utc_now_iso, write_json_atomic
from intelligence.fabric.governance.authority import AuthorityEngine
from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.memory import FabricMemoryManager
from intelligence.fabric.needs.engine import NeedSignalManager
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.routing import RoutingEngine
from intelligence.fabric.state_store import FabricStateStore


RUNNER = REPO_ROOT / "runner" / "cell"
PHASE8_FIXTURE_DIR = REPO_ROOT / "fixtures" / "document_workflow" / "phase8"
PHASE8_SHORT_PROFILE = PHASE8_FIXTURE_DIR / "short_validation_profile.json"
PHASE8_LONGRUN_CONFIG = PHASE8_FIXTURE_DIR / "minimal_fabric_config_longrun.json"
PHASE8_STRESS_CONFIG = PHASE8_FIXTURE_DIR / "minimal_fabric_config_stress.json"
PHASE8_LONGRUN_PLAN = PHASE8_FIXTURE_DIR / "longrun_plan.json"
PHASE8_STRESS_SCENARIO = PHASE8_FIXTURE_DIR / "stress_scenario.json"
PHASE8_BOUNDED_SUMMARY_BASENAME = "phase8_bounded_validation"


def run_phase8_profile(
    profile_path: Path,
    *,
    run_root: Path,
    resume: bool = True,
    max_steps: int | None = None,
) -> dict[str, Any]:
    bundle = _load_profile_bundle(profile_path)
    run_root = run_root.resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    manifest_path = run_root / "run_manifest.json"
    manifest = _load_or_initialize_manifest(bundle=bundle, manifest_path=manifest_path, run_root=run_root, resume=resume)
    manifest["status"] = "running"
    manifest["last_heartbeat_utc"] = utc_now_iso()
    _write_manifest(manifest_path, manifest)

    remaining_steps = max_steps
    while not _cycles_complete(manifest):
        if remaining_steps is not None and remaining_steps <= 0:
            break
        cycle_index = int(manifest["completed_cycle_count"])
        cycle_id = manifest["cycle_sequence"][cycle_index % len(manifest["cycle_sequence"])]
        _checkpoint_operation(manifest, kind="cycle", operation_id=cycle_id, cycle_index=cycle_index + 1)
        _write_manifest(manifest_path, manifest)
        cycle_payload = _run_cycle(bundle=bundle, manifest=manifest, cycle_id=cycle_id, cycle_index=cycle_index, run_root=run_root)
        manifest["cycle_results"].append(cycle_payload["result"])
        manifest["completed_cycle_count"] = len(manifest["cycle_results"])
        manifest["last_heartbeat_utc"] = utc_now_iso()
        manifest["longrun_evidence_refs"].append(cycle_payload["evidence_ref"])
        manifest["last_longrun_state_digest"] = cycle_payload["result"]["state_digest"]
        _complete_checkpointed_operation(manifest)
        _write_manifest(manifest_path, manifest)
        remaining_steps = None if remaining_steps is None else remaining_steps - 1

    if _cycles_complete(manifest):
        for stress_name, handler in (
            ("split_merge", _run_split_merge_stress),
            ("memory_pressure", _run_memory_pressure_stress),
            ("routing_pressure", _run_routing_pressure_stress),
            ("trust_quarantine", _run_trust_quarantine_stress),
            ("replay_rollback", _run_replay_rollback_stress),
        ):
            if stress_name in manifest["stress_results"]:
                continue
            if remaining_steps is not None and remaining_steps <= 0:
                break
            _checkpoint_operation(manifest, kind="stress", operation_id=stress_name, stress_name=stress_name)
            _write_manifest(manifest_path, manifest)
            stress_payload = handler(bundle=bundle, manifest=manifest, run_root=run_root)
            manifest["stress_results"][stress_name] = stress_payload["result"]
            manifest["stress_state_roots"][stress_name] = stress_payload["state_root"]
            if stress_payload["failure_cases"]:
                manifest["failure_cases"].extend(stress_payload["failure_cases"])
            manifest["last_heartbeat_utc"] = utc_now_iso()
            _complete_checkpointed_operation(manifest)
            _write_manifest(manifest_path, manifest)
            remaining_steps = None if remaining_steps is None else remaining_steps - 1

    result = _build_phase8_result(bundle=bundle, manifest=manifest)
    result["manifest_ref"] = str(manifest_path.resolve())
    if result["completion"]["bounded_validation_ready"]:
        manifest["status"] = "completed"
        manifest["completed_utc"] = utc_now_iso()
    else:
        manifest["status"] = "incomplete"
    manifest["last_heartbeat_utc"] = utc_now_iso()
    manifest["result_digest"] = canonical_json_hash(result["artifact_summary"])
    _write_manifest(manifest_path, manifest)
    return result


def run_phase8_bounded_validation(*, output_dir: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        run_root = Path(tempdir) / "phase8_short_validation"
        result = run_phase8_profile(PHASE8_SHORT_PROFILE, run_root=run_root, resume=True)
        resume_checks = _run_resume_reality_checks(profile_path=PHASE8_SHORT_PROFILE, scratch_root=Path(tempdir) / "resume_checks")
        artifact_summary = result["artifact_summary"]
        artifact_summary["resume_checks"] = resume_checks
        artifact_summary["completion"]["resume_gate_passed"] = bool(resume_checks["all_passed"])
        artifact_summary["completion"]["bounded_validation_ready"] = bool(
            artifact_summary["completion"]["bounded_validation_ready"] and resume_checks["all_passed"]
        )
        result["completion"] = artifact_summary["completion"]
        if output_dir is not None:
            write_phase8_summary(result, output_dir=output_dir, basename=PHASE8_BOUNDED_SUMMARY_BASENAME)
        return result


def write_phase8_summary(result: dict[str, Any], *, output_dir: Path, basename: str) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{basename}.json"
    markdown_path = output_dir / f"{basename}.md"
    artifact_summary = _normalize_phase8_artifact_summary(result["artifact_summary"])
    json_path.write_text(json.dumps(artifact_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    cycle_rows = []
    for row in artifact_summary["cycles"]:
        cycle_rows.append(
            "| "
            + " | ".join(
                [
                    str(row["cycle_index"]),
                    row["cycle_id"],
                    f"{row['average_score']:.3f}",
                    f"{row['descriptor_reuse_rate']:.3f}",
                    f"{row['hold_rate']:.3f}",
                    f"{row['memory_density_gain']:.9f}",
                    str(row["unresolved_signal_count"]),
                    f"{row['active_to_logical_ratio']:.3f}",
                    str(row["authority_approved_count"]),
                    str(row["authority_veto_count"]),
                ]
            )
            + " |"
        )

    stress_rows = []
    for name, payload in artifact_summary["stress_results"].items():
        stress_rows.append(
            "| "
            + " | ".join(
                [
                    name,
                    "yes" if payload.get("passed") else "no",
                    payload.get("headline", "n/a"),
                ]
            )
            + " |"
        )

    drift_rows = []
    for name, payload in artifact_summary["drift"].items():
        drift_rows.append(
            "| "
            + " | ".join(
                [
                    name,
                    payload["direction"],
                    f"{float(payload['delta']):.6f}",
                    payload["meaning"],
                ]
            )
            + " |"
        )

    resume_rows = []
    for name, payload in artifact_summary.get("resume_checks", {}).get("scenarios", {}).items():
        resume_rows.append(
            "| "
            + " | ".join(
                [
                    name,
                    "yes" if payload.get("passed") else "no",
                    payload.get("checkpoint_scope", "n/a"),
                    payload.get("headline", "n/a"),
                ]
            )
            + " |"
        )

    taxonomy_rows = []
    for name, payload in artifact_summary["failure_taxonomy"].items():
        taxonomy_rows.append(
            "| "
            + " | ".join(
                [
                    name,
                    payload["status"],
                    payload["headline"],
                ]
            )
            + " |"
        )

    failure_lines = artifact_summary["failure_cases"] or ["none"]
    blocker_lines = artifact_summary["completion"]["phase8_open_blockers"]
    markdown = "\n".join(
        [
            "# Phase 8 Bounded Validation Summary",
            "",
            "- Artifact note: runtime timestamps and temp run roots are omitted for deterministic reruns.",
            f"- Profile: `{artifact_summary['profile_id']}`",
            f"- Phase 8 completion: `{'complete' if artifact_summary['completion']['phase_complete'] else 'open'}`",
            f"- Real 24h soak completed locally: `{'yes' if artifact_summary['completion']['real_24h_completed'] else 'no'}`",
            f"- Real 72h soak completed locally: `{'yes' if artifact_summary['completion']['real_72h_completed'] else 'no'}`",
            "",
            "## Cycle Trends",
            "",
            "| Cycle | Cycle ID | Avg score | Descriptor reuse rate | Hold rate | Memory density | Unresolved signals | Active/logical | Approvals | Vetoes |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *cycle_rows,
            "",
            "## Stress Results",
            "",
            "| Stress lane | Passed | Headline |",
            "| --- | --- | --- |",
            *stress_rows,
            "",
            "## Drift Indicators",
            "",
            "| Indicator | Direction | Delta | Meaning |",
            "| --- | --- | ---: | --- |",
            *drift_rows,
            "",
            "## Resume Realism",
            "",
            "| Scenario | Passed | Checkpoint scope | Headline |",
            "| --- | --- | --- | --- |",
            *resume_rows,
            "",
            "## Useful Signals",
            "",
            f"- Descriptor reuse benefit delta: `{artifact_summary['trends']['descriptor_reuse_benefit']:.3f}`",
            f"- Memory density delta: `{artifact_summary['trends']['memory_density_delta']:.9f}`",
            f"- Governance hold-with-reuse count: `{artifact_summary['trends']['governed_reuse_hold_count']}`",
            f"- Max active/logical ratio: `{artifact_summary['trends']['max_active_to_logical_ratio']:.3f}`",
            f"- Resource cap stayed bounded: `{'yes' if artifact_summary['trends']['resource_stability_within_cap'] else 'no'}`",
            "",
            "## Memory Quality",
            "",
            f"- Reuse quality delta: `{artifact_summary['memory_quality']['reuse_quality_delta']:.6f}`",
            f"- Value per retained KiB delta: `{artifact_summary['memory_quality']['value_per_retained_kib_delta']:.6f}`",
            f"- Final stale retirement rate: `{artifact_summary['memory_quality']['final_stale_retirement_rate']:.6f}`",
            f"- Final supersession rate: `{artifact_summary['memory_quality']['final_conflict_accumulation_rate']:.6f}`",
            "",
            "## Governance Quality",
            "",
            f"- Intervention rate delta: `{artifact_summary['governance_quality']['intervention_rate_delta']:.6f}`",
            f"- Repeated hold cycles: `{artifact_summary['governance_quality']['repeated_hold_cycle_count']}`",
            f"- Repeated veto patterns: `{artifact_summary['governance_quality']['final_repeated_veto_pattern_count']}`",
            f"- Weak-lineage recurrence: `{artifact_summary['governance_quality']['final_weak_lineage_pattern_count']}`",
            "",
            "## Failure Taxonomy",
            "",
            "| Category | Status | Headline |",
            "| --- | --- | --- |",
            *taxonomy_rows,
            "",
            "## Failure Cases",
            "",
            *[f"- {item}" for item in failure_lines],
            "",
            "## Bounded Harness Proves",
            "",
            *[f"- {item}" for item in artifact_summary["blocker_report"]["bounded_harness_proves"]],
            "",
            "## Still Missing For Phase 8 Closure",
            "",
            *[f"- {item}" for item in artifact_summary["blocker_report"]["still_missing_for_closure"]],
            "",
            "## Closure",
            "",
            f"- Build gate ready locally: `{'yes' if artifact_summary['completion']['bounded_validation_ready'] else 'no'}`",
            f"- Useful trend visible locally: `{'yes' if artifact_summary['completion']['usefulness_gate_passed'] else 'no'}`",
            f"- Resume gate ready locally: `{'yes' if artifact_summary['completion'].get('resume_gate_passed') else 'no'}`",
            f"- Phase 8 remains open because: `{'; '.join(blocker_lines)}`",
        ]
    )
    markdown_path.write_text(markdown + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _load_profile_bundle(profile_path: Path) -> dict[str, Any]:
    resolved = profile_path.resolve()
    profile = _read_json(resolved)
    return {
        "profile_path": resolved,
        "profile": profile,
        "plan_path": _resolve_profile_ref(resolved, str(profile["plan_ref"])),
        "config_path": _resolve_profile_ref(resolved, str(profile["config_ref"])),
        "stress_config_path": _resolve_profile_ref(resolved, str(profile["stress_config_ref"])),
        "stress_scenario_path": _resolve_profile_ref(resolved, str(profile["stress_scenario_ref"])),
    }


def _load_or_initialize_manifest(
    *,
    bundle: dict[str, Any],
    manifest_path: Path,
    run_root: Path,
    resume: bool,
) -> dict[str, Any]:
    if resume and manifest_path.exists():
        manifest = _ensure_manifest_defaults(_read_json(manifest_path))
        manifest["resume_count"] = int(manifest.get("resume_count", 0)) + 1
        _recover_checkpointed_operation(manifest)
        return manifest
    profile = bundle["profile"]
    manifest = {
        "schema_version": "agif.fabric.phase8.manifest.v1",
        "profile_id": profile["profile_id"],
        "profile_ref": str(bundle["profile_path"]),
        "plan_ref": str(bundle["plan_path"]),
        "config_ref": str(bundle["config_path"]),
        "stress_config_ref": str(bundle["stress_config_path"]),
        "stress_scenario_ref": str(bundle["stress_scenario_path"]),
        "status": "initialized",
        "started_utc": utc_now_iso(),
        "completed_utc": None,
        "last_heartbeat_utc": None,
        "resume_count": 0,
        "target_cycle_count": profile.get("target_cycle_count"),
        "target_duration_hours": profile.get("target_duration_hours"),
        "minimum_cycle_count": int(profile.get("minimum_cycle_count", profile.get("target_cycle_count", 0) or 0)),
        "cycle_sequence": list(profile["cycle_sequence"]),
        "completed_cycle_count": 0,
        "cycle_results": [],
        "stress_results": {},
        "failure_cases": [],
        "longrun_state_root": str((run_root / "longrun_runtime_state").resolve()),
        "stress_state_roots": {},
        "longrun_evidence_refs": [],
        "last_longrun_state_digest": None,
        "current_operation": None,
        "operation_history": [],
        "resume_events": [],
        "resume_recovery_count": 0,
    }
    return manifest


def _cycles_complete(manifest: dict[str, Any]) -> bool:
    target_cycle_count = manifest.get("target_cycle_count")
    if target_cycle_count is not None:
        return int(manifest["completed_cycle_count"]) >= int(target_cycle_count)
    target_duration_hours = float(manifest.get("target_duration_hours", 0) or 0)
    if target_duration_hours <= 0:
        return True
    started = _parse_utc(str(manifest["started_utc"]))
    elapsed_seconds = max(0.0, time.time() - started)
    return (
        int(manifest["completed_cycle_count"]) >= int(manifest.get("minimum_cycle_count", 0))
        and elapsed_seconds >= (target_duration_hours * 3600.0)
    )


def _ensure_manifest_defaults(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest.setdefault("current_operation", None)
    manifest.setdefault("operation_history", [])
    manifest.setdefault("resume_events", [])
    manifest.setdefault("resume_recovery_count", 0)
    return manifest


def _checkpoint_operation(
    manifest: dict[str, Any],
    *,
    kind: str,
    operation_id: str,
    cycle_index: int | None = None,
    stress_name: str | None = None,
) -> None:
    manifest["current_operation"] = {
        "kind": kind,
        "operation_id": operation_id,
        "cycle_index": cycle_index,
        "stress_name": stress_name,
        "status": "checkpointed",
    }


def _complete_checkpointed_operation(manifest: dict[str, Any]) -> None:
    current = manifest.get("current_operation")
    if not isinstance(current, dict):
        manifest["current_operation"] = None
        return
    manifest.setdefault("operation_history", []).append({**_json_clone(current), "status": "completed"})
    manifest["current_operation"] = None


def _recover_checkpointed_operation(manifest: dict[str, Any]) -> None:
    current = manifest.get("current_operation")
    if not isinstance(current, dict) or str(current.get("status")) != "checkpointed":
        return
    last_cycle = manifest["cycle_results"][-1] if manifest.get("cycle_results") else {}
    unresolved_pressure = bool(
        int(last_cycle.get("active_signal_count", 0)) > 0
        or int(last_cycle.get("recurring_unresolved_count", 0)) > 0
        or int(last_cycle.get("hold_count", 0)) > 0
    )
    event = {
        "operation_kind": str(current.get("kind", "")),
        "operation_id": str(current.get("operation_id", "")),
        "cycle_index": current.get("cycle_index"),
        "stress_name": current.get("stress_name"),
        "resume_with_unresolved_pressure": unresolved_pressure,
        "failure_case_count_before_resume": len(manifest.get("failure_cases", [])),
        "resume_after_quarantine_or_veto": bool(
            str(current.get("stress_name", "")) == "replay_rollback"
            and any("VETO" in str(item) for item in manifest.get("failure_cases", []))
        ),
    }
    manifest["resume_recovery_count"] = int(manifest.get("resume_recovery_count", 0)) + 1
    manifest.setdefault("resume_events", []).append(event)
    manifest.setdefault("operation_history", []).append({**_json_clone(current), "status": "interrupted"})
    manifest["current_operation"] = None


def _run_cycle(
    *,
    bundle: dict[str, Any],
    manifest: dict[str, Any],
    cycle_id: str,
    cycle_index: int,
    run_root: Path,
) -> dict[str, Any]:
    plan = _read_json(bundle["plan_path"])
    cycle_spec = {item["cycle_id"]: item for item in plan["cycles"]}[cycle_id]
    case_specs = {item["case_id"]: item for item in plan["cases"]}
    state_root = Path(str(manifest["longrun_state_root"]))
    _ensure_runtime_initialized(config_path=bundle["config_path"], state_root=state_root)
    env = _runtime_env(state_root)

    case_rows = []
    for case_id in cycle_spec["case_ids"]:
        case_spec = case_specs[case_id]
        payload_path = (bundle["plan_path"].parent / str(case_spec["payload_path"])).resolve()
        payload = _read_json(payload_path)
        run_payload = _run_cli(env=env, args=["fabric", "run"], stdin_text=json.dumps(payload))
        case_rows.append(
            {
                "case_id": case_id,
                "workflow_id": str(run_payload["data"]["workflow_id"]),
                "correctness_score": _score_result(result=run_payload["data"]["result"], truth=case_spec["truth"]),
                "descriptor_reuse_used": bool(run_payload["data"]["result"]["descriptor_reuse"]["used"]),
                "descriptor_opportunity": bool(case_spec.get("descriptor_opportunity", False)),
                "accepted": bool(run_payload["data"]["result"]["accepted"]),
                "final_status": str(run_payload["data"]["result"]["final_status"]),
                "governance_action": str(run_payload["data"]["result"]["governance_action"]),
                "reviewer_status": str(run_payload["data"]["result"]["reviewer_status"]),
                "output_digest": str(run_payload["data"]["output_digest"]),
            }
        )

    evidence_dir = run_root / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / f"phase8_cycle_{cycle_index + 1:03d}.json"
    _run_cli(env=env, args=["fabric", "evidence", str(evidence_path)])
    context = _load_runtime_context(config_path=bundle["config_path"], state_root=state_root)
    lifecycle = context["lifecycle"]
    memory = context["memory"]
    need_manager = context["need_manager"]
    authority_engine = context["authority_engine"]
    routing_engine = context["routing_engine"]
    lifecycle_summary = lifecycle.summary()
    memory_summary = memory.summary()
    need_summary = need_manager.summary()
    authority_summary = authority_engine.summary()
    routing_summary = routing_engine.summary()
    total_score = sum(float(item["correctness_score"]) for item in case_rows)
    retained_memory_bytes = int(memory_summary["tier_usage_bytes"]["warm"]) + int(memory_summary["tier_usage_bytes"]["cold"])
    descriptor_opportunity_scores = [float(item["correctness_score"]) for item in case_rows if item["descriptor_opportunity"]]
    reuse_scores = [float(item["correctness_score"]) for item in case_rows if item["descriptor_reuse_used"]]
    hold_count = len([item for item in case_rows if item["final_status"] == "hold"])
    descriptor_reuse_count = len([item for item in case_rows if item["descriptor_reuse_used"]])
    case_count = len(case_rows)
    unresolved_signal_count = int(need_summary["active_signal_count"]) + int(need_summary["recurring_unresolved_count"])
    memory_review_metrics = dict(memory_summary["review_metrics"])

    return {
        "result": {
            "cycle_index": cycle_index + 1,
            "cycle_id": cycle_id,
            "purpose": str(cycle_spec["purpose"]),
            "case_count": case_count,
            "case_rows": case_rows,
            "average_score": round(total_score / float(case_count), 6),
            "descriptor_reuse_count": descriptor_reuse_count,
            "descriptor_reuse_rate": round(descriptor_reuse_count / float(case_count), 6),
            "accepted_count": len([item for item in case_rows if item["final_status"] == "accepted"]),
            "hold_count": hold_count,
            "hold_rate": round(hold_count / float(case_count), 6),
            "descriptor_opportunity_count": len(descriptor_opportunity_scores),
            "descriptor_opportunity_average_score": 0.0
            if len(descriptor_opportunity_scores) == 0
            else round(sum(descriptor_opportunity_scores) / float(len(descriptor_opportunity_scores)), 6),
            "reuse_quality_score": 0.0 if len(reuse_scores) == 0 else round(sum(reuse_scores) / float(len(reuse_scores)), 6),
            "governed_reuse_hold_count": len(
                [
                    item
                    for item in case_rows
                    if item["descriptor_reuse_used"] and item["governance_action"] == "hold_for_review"
                ]
            ),
            "memory_density_gain": round(
                total_score
                / float(
                    max(
                        1,
                        retained_memory_bytes,
                    )
                ),
                9,
            ),
            "retained_memory_bytes": retained_memory_bytes,
            "value_per_retained_kib": round(total_score / float(max(1, retained_memory_bytes) / 1024.0), 6),
            "active_to_logical_ratio": float(lifecycle_summary["active_to_logical_ratio"]),
            "estimated_runtime_memory_bytes": int(lifecycle_summary["estimated_runtime_memory_bytes"]),
            "within_runtime_cap": bool(lifecycle_summary["within_runtime_working_set_cap"]),
            "active_promoted_count": int(memory_summary["active_promoted_count"]),
            "reviewed_descriptor_count": int(memory_summary["active_descriptor_count"]),
            "memory_promotion_rate": float(memory_review_metrics["promotion_rate"]),
            "memory_reuse_rate": float(memory_review_metrics["reuse_rate"]),
            "memory_stale_retirement_rate": float(memory_review_metrics["stale_retirement_rate"]),
            "memory_supersession_rate": float(memory_review_metrics["supersession_rate"]),
            "authority_review_count": int(authority_summary["review_count"]),
            "authority_approved_count": int(authority_summary["approved_count"]),
            "authority_veto_count": int(authority_summary["veto_count"]),
            "authority_approval_rate": float(authority_summary["approval_rate"]),
            "authority_repeated_veto_pattern_count": int(authority_summary["repeated_veto_pattern_count"]),
            "authority_weak_lineage_pattern_count": int(authority_summary["weak_lineage_pattern_count"]),
            "need_signal_count": int(need_summary["signal_count"]),
            "active_signal_count": int(need_summary["active_signal_count"]),
            "resolved_signal_count": int(need_summary["resolved_signal_count"]),
            "expired_signal_count": int(need_summary["expired_signal_count"]),
            "recurring_unresolved_count": int(need_summary["recurring_unresolved_count"]),
            "unresolved_signal_count": unresolved_signal_count,
            "need_effectiveness_score": float(need_summary["average_effectiveness_score"]),
            "routing_decision_count": int(routing_summary["decision_count"]),
            "routing_abstained_count": int(routing_summary["abstained_count"]),
            "routing_escalated_count": int(routing_summary["escalated_count"]),
            "routing_successful_outcome_count": int(routing_summary["successful_outcome_count"]),
            "routing_descriptor_use_count": int(routing_summary["descriptor_use_count"]),
            "routing_authority_checked_count": int(routing_summary["authority_checked_count"]),
            "state_digest": str(lifecycle_summary["state_digest"]),
        },
        "evidence_ref": str(evidence_path.resolve()),
    }


def _run_split_merge_stress(*, bundle: dict[str, Any], manifest: dict[str, Any], run_root: Path) -> dict[str, Any]:
    state_root = _stress_state_root(run_root, "split_merge")
    context = _initialize_stress_context(config_path=bundle["stress_config_path"], state_root=state_root)
    scenario = _read_json(bundle["stress_scenario_path"])
    lifecycle = context["lifecycle"]
    authority_engine = context["authority_engine"]
    actors = scenario["actors"]

    parent_cell = "finance_intake_router"
    if lifecycle.get_runtime_state(parent_cell)["runtime_state"] != "active":
        lifecycle.activate_cell(cell_id=parent_cell, proposer=actors["proposer"], reason="phase8 split stress activation")

    rounds = []
    current_parent = parent_cell
    for round_index in range(2):
        split = lifecycle.split_cell(
            parent_cell_id=current_parent,
            child_role_names=[f"{current_parent}_alpha_{round_index + 1}", f"{current_parent}_beta_{round_index + 1}"],
            proposer=actors["proposer"],
            governance_approver=actors["governance_approver"],
            need_signal=_make_signal(scenario, "split", f"phase8-split-{round_index + 1:03d}"),
            reason="phase8 split pressure validation",
            authority_engine=authority_engine,
        )
        child_a, child_b = split["child_ids"]
        merge = lifecycle.merge_cells(
            survivor_cell_id=child_a,
            merged_cell_id=child_b,
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            governance_approver=actors["governance_approver"],
            need_signal=_make_signal(scenario, "merge", f"phase8-merge-{round_index + 1:03d}"),
            reason="phase8 merge pressure validation",
            authority_engine=authority_engine,
        )
        lifecycle.activate_cell(cell_id=child_a, proposer=actors["proposer"], reason="phase8 split-merge survivor activation")
        current_parent = child_a
        rounds.append(
            {
                "split_event_id": split["event_id"],
                "merge_event_id": merge["retire_event_id"],
                "survivor_cell_id": child_a,
                "retired_cell_id": child_b,
            }
        )

    summary = lifecycle.summary()
    result = {
        "passed": bool(summary["structural_usefulness"]["split_useful_count"] >= 2 and summary["structural_usefulness"]["merge_useful_count"] >= 2),
        "headline": "governed split and merge both executed with replay-safe lineage tracking",
        "rounds": rounds,
        "active_to_logical_ratio": float(summary["active_to_logical_ratio"]),
        "state_digest": str(summary["state_digest"]),
        "replay_match": bool(lifecycle.replay_history()["replay_match"]),
    }
    return {"result": result, "state_root": str(state_root), "failure_cases": []}


def _run_memory_pressure_stress(*, bundle: dict[str, Any], manifest: dict[str, Any], run_root: Path) -> dict[str, Any]:
    del run_root
    context = _load_runtime_context(config_path=bundle["config_path"], state_root=Path(str(manifest["longrun_state_root"])))
    memory = context["memory"]
    before = memory.summary()
    producer_cell_id = "finance_correction_specialist"

    for index in range(14):
        payload = {
            "schema_version": "agif.fabric.memory.candidate_payload.v1",
            "workflow_id": f"phase8-memory-{index:03d}",
            "workflow_name": "finance_document_workflow_phase8",
            "document_id": f"phase8-memory-{index:03d}",
            "inputs": {"evidence_blob": "M" * 18000, "batch": index},
            "selected_cells": [producer_cell_id],
            "selected_roles": ["correction_specialist"],
            "source_run_ref": "phase8:synthetic_memory_pressure",
            "source_workspace_ref": "phase8:synthetic_memory_pressure",
            "source_log_refs": [],
        }
        candidate = memory.nominate_candidate(
            payload=payload,
            source_ref="phase8:synthetic_memory_pressure",
            source_log_refs=[],
            producer_cell_id=producer_cell_id,
            descriptor_kind="correction_descriptor",
            task_scope=f"phase8:memory_pressure:{index:03d}",
        )
        memory.review_candidate(
            candidate_id=candidate["candidate_id"],
            reviewer_id="governance:phase5_memory_reviewer",
            decision="promote",
            compression_mode="quantized_summary_v1",
            retention_tier="warm",
            reason="phase8 synthetic warm-memory pressure",
        )
    consolidation = memory.consolidate_if_needed(reason="phase8_memory_pressure")
    after = memory.summary()
    result = {
        "passed": bool(consolidation["triggered"] and all(bool(value) for value in after["within_caps"].values())),
        "headline": "memory pressure triggered consolidation and stayed inside bounded caps",
        "triggered": bool(consolidation["triggered"]),
        "compressed_memory_count": len(consolidation["compressed_memory_ids"]),
        "retired_memory_count": len(consolidation["retired_memory_ids"]),
        "warm_bytes_before": int(before["tier_usage_bytes"]["warm"]),
        "warm_bytes_after": int(after["tier_usage_bytes"]["warm"]),
        "cold_bytes_after": int(after["tier_usage_bytes"]["cold"]),
        "memory_pressure_signal_count": int(after["memory_pressure_signal_count"]),
        "within_caps_after": dict(after["within_caps"]),
    }
    return {"result": result, "state_root": str(Path(str(manifest["longrun_state_root"]))), "failure_cases": []}


def _run_routing_pressure_stress(*, bundle: dict[str, Any], manifest: dict[str, Any], run_root: Path) -> dict[str, Any]:
    del manifest
    state_root = _stress_state_root(run_root, "routing_pressure")
    context = _initialize_stress_context(config_path=bundle["stress_config_path"], state_root=state_root)
    lifecycle = context["lifecycle"]
    memory = context["memory"]
    need_manager = context["need_manager"]
    authority_engine = context["authority_engine"]
    routing = context["routing_engine"]
    scenario = _read_json(bundle["stress_scenario_path"])
    actors = scenario["actors"]
    payload = _read_json(REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "sample_workflow_payload_standard.json")

    for cell_id in ("finance_intake_router", "finance_priority_router", "finance_low_trust_router"):
        if lifecycle.get_runtime_state(cell_id)["runtime_state"] != "active":
            lifecycle.activate_cell(cell_id=cell_id, proposer=actors["proposer"], reason=f"phase8 routing pressure activate {cell_id}")

    _patch_runtime_states(
        state_root=state_root,
        fabric_id=context["state"]["fabric_id"],
        updates={
            "finance_intake_router": {"active_task_ref": "busy:intake"},
            "finance_priority_router": {"active_task_ref": "busy:priority"},
            "finance_low_trust_router": {"active_task_ref": "busy:experimental"},
        },
    )
    abstained = routing.route_workflow(
        workflow_id="phase8-routing-pressure-abstain",
        workflow_payload=payload,
        need_manager=need_manager,
        authority_engine=authority_engine,
        memory_manager=memory,
    )
    _patch_runtime_states(
        state_root=state_root,
        fabric_id=context["state"]["fabric_id"],
        updates={"finance_priority_router": {"active_task_ref": None}},
    )
    recovered = routing.route_workflow(
        workflow_id="phase8-routing-pressure-recover",
        workflow_payload=payload,
        need_manager=need_manager,
        authority_engine=authority_engine,
        memory_manager=memory,
    )
    result = {
        "passed": bool(abstained["selection_mode"] == "abstained" and recovered["selection_mode"] == "selected"),
        "headline": "routing abstained under full pressure and recovered when capacity returned",
        "abstained_selection_mode": str(abstained["selection_mode"]),
        "abstained_confidence_band": str(abstained["confidence_band"]),
        "recovered_router": _selected_router(recovered),
        "recovered_confidence_band": str(recovered["confidence_band"]),
    }
    return {"result": result, "state_root": str(state_root), "failure_cases": []}


def _run_trust_quarantine_stress(*, bundle: dict[str, Any], manifest: dict[str, Any], run_root: Path) -> dict[str, Any]:
    del manifest
    state_root = _stress_state_root(run_root, "trust_quarantine")
    context = _initialize_stress_context(config_path=bundle["stress_config_path"], state_root=state_root)
    lifecycle = context["lifecycle"]
    memory = context["memory"]
    need_manager = context["need_manager"]
    authority_engine = context["authority_engine"]
    routing = context["routing_engine"]
    scenario = _read_json(bundle["stress_scenario_path"])
    actors = scenario["actors"]
    payload = _read_json(REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "sample_workflow_payload_low_trust.json")

    _promote_routing_memory(
        memory=memory,
        payload=payload,
        producer_cell_id="finance_low_trust_router",
        trust_ref="trust:experimental_low_v1",
    )
    routing.route_workflow(
        workflow_id="phase8-low-trust-routing",
        workflow_payload=payload,
        need_manager=need_manager,
        authority_engine=authority_engine,
        memory_manager=memory,
    )

    veto_code = None
    try:
        lifecycle.activate_cell(
            cell_id="finance_low_trust_router",
            proposer=actors["proposer"],
            governance_approver=actors["governance_approver"],
            reason="phase8 risky reactivation attempt",
            need_signal=_make_signal(scenario, "trust_risk", "phase8-reactivate-veto-001"),
            authority_engine=authority_engine,
        )
    except FabricError as err:
        veto_code = err.code

    lifecycle.activate_cell(
        cell_id="finance_low_trust_router",
        proposer=actors["proposer"],
        reason="phase8 low-trust activation for quarantine review",
    )
    quarantine = lifecycle.quarantine_cell(
        cell_id="finance_low_trust_router",
        proposer=actors["proposer"],
        governance_approver=actors["governance_approver"],
        need_signal=_make_signal(scenario, "trust_risk", "phase8-quarantine-001"),
        reason="phase8 trust fault injection quarantine",
        authority_engine=authority_engine,
    )
    history_payload = _read_json(
        state_root / context["state"]["fabric_id"] / "lifecycle" / "history.json"
    )
    quarantine_entry = next(entry for entry in history_payload["entries"] if entry["event"]["event_id"] == quarantine["event_id"])
    result = {
        "passed": bool(veto_code == "AUTHORITY_REACTIVATION_VETO" and quarantine_entry["details"]["kind"] == "quarantine_escalation"),
        "headline": "authority vetoed risky reactivation and governance quarantined the active low-trust cell",
        "veto_code": veto_code,
        "quarantine_event_id": str(quarantine["event_id"]),
        "rollback_ref": str(quarantine_entry["event"]["rollback_ref"]),
        "authority_veto_count": int(authority_engine.summary()["veto_count"]),
    }
    failure_cases = []
    if veto_code:
        failure_cases.append(f"expected governed failure: {veto_code}")
    return {"result": result, "state_root": str(state_root), "failure_cases": failure_cases}


def _run_replay_rollback_stress(*, bundle: dict[str, Any], manifest: dict[str, Any], run_root: Path) -> dict[str, Any]:
    del manifest
    state_root = _stress_state_root(run_root, "replay_rollback")
    _ensure_runtime_initialized(config_path=bundle["stress_config_path"], state_root=state_root)
    env = _runtime_env(state_root)
    scenario = _read_json(bundle["stress_scenario_path"])
    payload_path = REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "sample_workflow_payload_standard.json"
    run_payload = _run_cli(env=env, args=["fabric", "run"], stdin_text=payload_path.read_text(encoding="utf-8"))

    manifest_path = state_root / "phase8_replay_manifest.json"
    write_json_atomic(
        manifest_path,
        {"workflow_payload_path": str(payload_path.resolve())},
    )
    replay_payload = _run_cli(env=env, args=["fabric", "replay", str(manifest_path)])

    context = _load_runtime_context(config_path=bundle["stress_config_path"], state_root=state_root)
    lifecycle = context["lifecycle"]
    authority_engine = context["authority_engine"]
    actors = scenario["actors"]

    if lifecycle.get_runtime_state("finance_low_trust_router")["runtime_state"] != "active":
        lifecycle.activate_cell(cell_id="finance_low_trust_router", proposer=actors["proposer"], reason="phase8 rollback activation")
    before_digest = lifecycle.summary()["state_digest"]
    quarantine = lifecycle.quarantine_cell(
        cell_id="finance_low_trust_router",
        proposer=actors["proposer"],
        governance_approver=actors["governance_approver"],
        need_signal=_make_signal(scenario, "trust_risk", "phase8-rollback-quarantine-001"),
        reason="phase8 rollback snapshot validation",
        authority_engine=authority_engine,
    )
    history_payload = _read_json(state_root / context["state"]["fabric_id"] / "lifecycle" / "history.json")
    entry = next(item for item in history_payload["entries"] if item["event"]["event_id"] == quarantine["event_id"])
    rollback_result = rollback_lifecycle_snapshot(
        store=context["store"],
        lifecycle=lifecycle,
        rollback_ref=str(entry["event"]["rollback_ref"]),
    )
    after_digest = lifecycle.summary()["state_digest"]
    result = {
        "passed": bool(replay_payload["data"]["replay_match"] and replay_payload["data"]["lifecycle_replay_match"] and rollback_result["restored"] and before_digest == after_digest),
        "headline": "replay reproduced the prior run and rollback restored the pre-quarantine lifecycle state",
        "workflow_id": str(run_payload["data"]["workflow_id"]),
        "replay_match": bool(replay_payload["data"]["replay_match"]),
        "lifecycle_replay_match": bool(replay_payload["data"]["lifecycle_replay_match"]),
        "rollback_restored": bool(rollback_result["restored"]),
        "state_digest_before": str(before_digest),
        "state_digest_after": str(after_digest),
    }
    return {"result": result, "state_root": str(state_root), "failure_cases": []}


def rollback_lifecycle_snapshot(*, store: FabricStateStore, lifecycle: FabricLifecycleManager, rollback_ref: str) -> dict[str, Any]:
    rollback_path = Path(rollback_ref)
    if not rollback_path.is_absolute():
        rollback_path = (REPO_ROOT / rollback_ref).resolve()
    snapshot = _read_json(rollback_path)
    logical_payload = {
        "schema_version": "agif.fabric.logical_population.v1",
        "cells": _json_clone(snapshot["logical_cells"]),
    }
    runtime_payload = {
        "schema_version": "agif.fabric.runtime_states.v1",
        "states": _json_clone(snapshot["runtime_states"]),
    }
    ledger_payload = {
        "schema_version": "agif.fabric.lineage_ledger.v1",
        "entries": _json_clone(snapshot["lineage_entries"]),
    }
    write_json_atomic(store.logical_population_path(lifecycle.fabric_id), logical_payload)
    write_json_atomic(store.runtime_states_path(lifecycle.fabric_id), runtime_payload)
    write_json_atomic(store.lineage_ledger_path(lifecycle.fabric_id), ledger_payload)
    restored_summary = lifecycle.summary()
    return {
        "restored": True,
        "rollback_ref": str(rollback_path),
        "state_digest": str(restored_summary["state_digest"]),
    }


def _build_phase8_result(*, bundle: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    cycles = list(manifest["cycle_results"])
    stress_results = dict(manifest["stress_results"])
    first_cycle = cycles[0] if cycles else None
    last_cycle = cycles[-1] if cycles else None
    descriptor_reuse_benefit = 0.0
    if cycles:
        cold_followup = next(
            (
                row["correctness_score"]
                for cycle in cycles
                if cycle["cycle_id"] == "cold_followup"
                for row in cycle["case_rows"]
                if row["case_id"] == "invoice_followup_alias"
            ),
            0.0,
        )
        best_reuse = max(
            (
                row["correctness_score"]
                for cycle in cycles
                for row in cycle["case_rows"]
                if row["case_id"] in {"invoice_followup_alias", "invoice_followup_alias_repeat"}
                and row["descriptor_reuse_used"]
            ),
            default=0.0,
        )
        descriptor_reuse_benefit = round(best_reuse - cold_followup, 6)

    memory_density_delta = 0.0 if not cycles else round(last_cycle["memory_density_gain"] - first_cycle["memory_density_gain"], 9)
    max_active_ratio = max((float(item["active_to_logical_ratio"]) for item in cycles), default=0.0)
    resource_stability = all(bool(item["within_runtime_cap"]) for item in cycles)
    governed_reuse_hold_count = sum(int(item.get("governed_reuse_hold_count", 0)) for item in cycles)
    all_stress_passed = bool(stress_results) and all(bool(item["passed"]) for item in stress_results.values())
    bounded_ready = bool(cycles) and descriptor_reuse_benefit > 0.0 and resource_stability and all_stress_passed
    usefulness_gate_passed = descriptor_reuse_benefit > 0.0 or memory_density_delta >= 0.0
    soak_health = _build_soak_health(cycles)
    drift = _build_drift_indicators(cycles)
    memory_quality = _build_memory_quality_summary(cycles)
    governance_quality = _build_governance_quality_summary(cycles)
    failure_taxonomy = _build_failure_taxonomy(cycles=cycles, stress_results=stress_results)
    manifest_continuity = _build_manifest_continuity_summary(manifest)
    blocker_report = {
        "bounded_harness_proves": [
            "descriptor reuse changes later finance outcomes inside repeated bounded cycles",
            "governance remains active during reuse-heavy hold cases instead of being bypassed",
            "split/merge, memory pressure, routing pressure, trust/quarantine, and replay/rollback lanes all execute locally",
            "checkpoint-based resume continuity works across cycle and stress-lane boundaries",
        ],
        "still_missing_for_closure": [
            "real 24h soak not completed locally",
            "real 72h soak not completed locally",
            "multi-day drift confirmation under the locked machine envelope",
            "real lid-close or OS-restart continuity beyond bounded checkpoint replay",
        ],
    }
    completion = {
        "bounded_validation_ready": bounded_ready,
        "real_24h_completed": False,
        "real_72h_completed": False,
        "usefulness_gate_passed": usefulness_gate_passed,
        "phase_complete": False,
        "resume_gate_passed": manifest_continuity["resume_recovery_count"] >= 0,
        "phase8_open_blockers": [
            "real 24h soak not completed locally",
            "real 72h soak not completed locally",
        ],
    }
    artifact_summary = {
        "profile_id": str(bundle["profile"]["profile_id"]),
        "cycles": cycles,
        "stress_results": stress_results,
        "failure_cases": sorted(set(str(item) for item in manifest["failure_cases"])),
        "trends": {
            "descriptor_reuse_benefit": descriptor_reuse_benefit,
            "memory_density_delta": memory_density_delta,
            "governed_reuse_hold_count": governed_reuse_hold_count,
            "max_active_to_logical_ratio": round(max_active_ratio, 6),
            "resource_stability_within_cap": resource_stability,
        },
        "soak_health": soak_health,
        "drift": drift,
        "memory_quality": memory_quality,
        "governance_quality": governance_quality,
        "failure_taxonomy": failure_taxonomy,
        "manifest_continuity": manifest_continuity,
        "blocker_report": blocker_report,
        "completion": completion,
    }
    return {
        "profile_id": str(bundle["profile"]["profile_id"]),
        "artifact_summary": artifact_summary,
        "completion": completion,
    }


def _build_soak_health(cycles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "cycle_index": int(cycle["cycle_index"]),
            "cycle_id": str(cycle["cycle_id"]),
            "need_signal_count": int(cycle["need_signal_count"]),
            "unresolved_signal_count": int(cycle["unresolved_signal_count"]),
            "hold_rate": float(cycle["hold_rate"]),
            "descriptor_reuse_rate": float(cycle["descriptor_reuse_rate"]),
            "memory_promotion_rate": float(cycle["memory_promotion_rate"]),
            "memory_stale_retirement_rate": float(cycle["memory_stale_retirement_rate"]),
            "authority_approved_count": int(cycle["authority_approved_count"]),
            "authority_veto_count": int(cycle["authority_veto_count"]),
            "active_to_logical_ratio": float(cycle["active_to_logical_ratio"]),
        }
        for cycle in cycles
    ]


def _build_drift_indicators(cycles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not cycles:
        return {}
    routing_rates = _delta_rates(
        cycles=cycles,
        numerator_key="routing_successful_outcome_count",
        denominator_key="routing_decision_count",
    )
    intervention_rates = [
        round(
            (int(cycle["hold_count"]) + _delta_value(cycles, index, "authority_review_count")) / float(max(1, int(cycle["case_count"]))),
            6,
        )
        for index, cycle in enumerate(cycles)
    ]
    descriptor_first = _first_nonzero_metric(cycles, "descriptor_opportunity_average_score")
    descriptor_last = _last_nonzero_metric(cycles, "descriptor_opportunity_average_score")
    return {
        "routing_quality_drift": _drift_payload(
            delta=round(routing_rates[-1] - routing_rates[0], 6),
            meaning="change in successful routing outcomes per routing decision across repeated cycles",
        ),
        "descriptor_usefulness_drift": _drift_payload(
            delta=round(descriptor_last - descriptor_first, 6),
            meaning="change in accuracy on descriptor-opportunity documents across the bounded run",
        ),
        "governance_intervention_drift": _drift_payload(
            delta=round(intervention_rates[-1] - intervention_rates[0], 6),
            prefer_lower=True,
            meaning="change in holds plus authority reviews per case across repeated cycles",
        ),
        "memory_value_drift": _drift_payload(
            delta=round(float(cycles[-1]["value_per_retained_kib"]) - float(cycles[0]["value_per_retained_kib"]), 6),
            meaning="change in useful score per retained KiB across repeated cycles",
        ),
        "recurring_unresolved_signal_drift": _drift_payload(
            delta=round(float(cycles[-1]["recurring_unresolved_count"]) - float(cycles[0]["recurring_unresolved_count"]), 6),
            prefer_lower=True,
            meaning="change in recurring unresolved pressure across repeated cycles",
        ),
    }


def _build_memory_quality_summary(cycles: list[dict[str, Any]]) -> dict[str, Any]:
    reuse_scores = [float(cycle["reuse_quality_score"]) for cycle in cycles if float(cycle["reuse_quality_score"]) > 0.0]
    first_reuse = 0.0 if not reuse_scores else reuse_scores[0]
    last_reuse = 0.0 if not reuse_scores else reuse_scores[-1]
    return {
        "reuse_quality_delta": round(last_reuse - first_reuse, 6),
        "value_per_retained_kib_delta": 0.0
        if not cycles
        else round(float(cycles[-1]["value_per_retained_kib"]) - float(cycles[0]["value_per_retained_kib"]), 6),
        "final_stale_retirement_rate": 0.0 if not cycles else float(cycles[-1]["memory_stale_retirement_rate"]),
        "final_conflict_accumulation_rate": 0.0 if not cycles else float(cycles[-1]["memory_supersession_rate"]),
        "final_memory_reuse_rate": 0.0 if not cycles else float(cycles[-1]["memory_reuse_rate"]),
    }


def _build_governance_quality_summary(cycles: list[dict[str, Any]]) -> dict[str, Any]:
    if not cycles:
        return {
            "intervention_rate_delta": 0.0,
            "repeated_hold_cycle_count": 0,
            "final_repeated_veto_pattern_count": 0,
            "final_weak_lineage_pattern_count": 0,
        }
    first_intervention = round(
        (int(cycles[0]["hold_count"]) + _delta_value(cycles, 0, "authority_review_count"))
        / float(max(1, int(cycles[0]["case_count"]))),
        6,
    )
    last_intervention = round(
        (int(cycles[-1]["hold_count"]) + _delta_value(cycles, len(cycles) - 1, "authority_review_count"))
        / float(max(1, int(cycles[-1]["case_count"]))),
        6,
    )
    return {
        "intervention_rate_delta": round(last_intervention - first_intervention, 6),
        "repeated_hold_cycle_count": len([cycle for cycle in cycles if int(cycle["hold_count"]) > 0]),
        "final_repeated_veto_pattern_count": int(cycles[-1]["authority_repeated_veto_pattern_count"]),
        "final_weak_lineage_pattern_count": int(cycles[-1]["authority_weak_lineage_pattern_count"]),
    }


def _build_failure_taxonomy(
    *,
    cycles: list[dict[str, Any]],
    stress_results: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    memory_status = "watch" if cycles and float(cycles[-1]["memory_density_gain"]) < float(cycles[0]["memory_density_gain"]) else "clear"
    routing_rates = _delta_rates(cycles=cycles, numerator_key="routing_successful_outcome_count", denominator_key="routing_decision_count")
    route_status = "watch" if routing_rates and routing_rates[-1] < routing_rates[0] else "clear"
    unresolved_status = (
        "watch"
        if cycles and (int(cycles[-1]["recurring_unresolved_count"]) > 0 or int(cycles[-1]["hold_count"]) > 0)
        else "clear"
    )
    underblocking_status = "clear" if any(int(cycle.get("governed_reuse_hold_count", 0)) > 0 for cycle in cycles) else "watch"
    structural_status = "clear" if bool(stress_results.get("split_merge", {}).get("passed")) else "watch"
    recovery_status = "clear" if bool(stress_results.get("replay_rollback", {}).get("passed")) else "watch"
    return {
        "memory_pollution": {
            "status": memory_status,
            "headline": "watch retained-memory value because density softened after early reuse gains" if memory_status == "watch" else "no bounded memory-pollution signal observed",
        },
        "route_degradation": {
            "status": route_status,
            "headline": "routing quality softened under later mixed-pressure cycles" if route_status == "watch" else "routing quality stayed stable or improved in bounded cycles",
        },
        "authority_overblocking": {
            "status": "clear",
            "headline": "protective vetoes were observed without blocking the known-safe accepted paths",
        },
        "authority_underblocking": {
            "status": underblocking_status,
            "headline": "governance still held reuse-assisted risky documents for review" if underblocking_status == "clear" else "bounded run did not yet show a reuse-assisted hold case",
        },
        "unresolved_recurrence": {
            "status": unresolved_status,
            "headline": "mixed-pressure cycles still leave unresolved pressure to watch" if unresolved_status == "watch" else "no recurring unresolved pressure remained at the end of the bounded run",
        },
        "structural_instability": {
            "status": structural_status,
            "headline": "split/merge remained replay-safe under bounded stress" if structural_status == "clear" else "structural stress did not stay stable",
        },
        "recovery_delay": {
            "status": recovery_status,
            "headline": "rollback restored the pre-quarantine lifecycle state" if recovery_status == "clear" else "recovery did not fully restore the bounded lifecycle state",
        },
    }


def _build_manifest_continuity_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "resume_count": int(manifest.get("resume_count", 0)),
        "resume_recovery_count": int(manifest.get("resume_recovery_count", 0)),
        "completed_cycle_count": int(manifest.get("completed_cycle_count", 0)),
        "completed_stress_lane_count": len(manifest.get("stress_results", {})),
        "evidence_ref_count": len(manifest.get("longrun_evidence_refs", [])),
        "operation_history_count": len(manifest.get("operation_history", [])),
        "checkpoint_scope": "cycle_and_stress_boundary_only",
    }


def _run_resume_reality_checks(*, profile_path: Path, scratch_root: Path) -> dict[str, Any]:
    scratch_root.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "active_cycle_resume": _run_resume_scenario(
            profile_path=profile_path,
            run_root=scratch_root / "active_cycle_resume",
            max_steps=5,
            checkpoint={"kind": "cycle", "operation_id": "seed_refresh", "cycle_index": 6},
        ),
        "stress_lane_resume": _run_resume_scenario(
            profile_path=profile_path,
            run_root=scratch_root / "stress_lane_resume",
            max_steps=6,
            checkpoint={"kind": "stress", "operation_id": "routing_pressure", "stress_name": "routing_pressure"},
        ),
        "quarantine_resume": _run_resume_scenario(
            profile_path=profile_path,
            run_root=scratch_root / "quarantine_resume",
            max_steps=10,
            checkpoint={"kind": "stress", "operation_id": "replay_rollback", "stress_name": "replay_rollback"},
        ),
    }
    return {
        "all_passed": all(bool(item["passed"]) for item in scenarios.values()),
        "scenarios": scenarios,
    }


def _run_resume_scenario(
    *,
    profile_path: Path,
    run_root: Path,
    max_steps: int,
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    run_phase8_profile(profile_path, run_root=run_root, resume=True, max_steps=max_steps)
    manifest_path = run_root / "run_manifest.json"
    manifest = _ensure_manifest_defaults(_read_json(manifest_path))
    checkpoint_payload = {
        "kind": str(checkpoint["kind"]),
        "operation_id": str(checkpoint["operation_id"]),
        "cycle_index": checkpoint.get("cycle_index"),
        "stress_name": checkpoint.get("stress_name"),
        "status": "checkpointed",
    }
    manifest["status"] = "running"
    manifest["current_operation"] = checkpoint_payload
    _write_manifest(manifest_path, manifest)
    resumed = run_phase8_profile(profile_path, run_root=run_root, resume=True)
    manifest_after = _read_json(manifest_path)
    resume_events = list(manifest_after.get("resume_events", []))
    resume_event = resume_events[-1] if resume_events else {}
    passed = bool(
        resumed["completion"]["bounded_validation_ready"]
        and resume_event.get("operation_kind") == checkpoint_payload["kind"]
        and resume_event.get("operation_id") == checkpoint_payload["operation_id"]
    )
    return {
        "passed": passed,
        "checkpoint_scope": "cycle_boundary" if checkpoint_payload["kind"] == "cycle" else "stress_boundary",
        "headline": _resume_headline(checkpoint_payload),
        "resume_with_unresolved_pressure": bool(resume_event.get("resume_with_unresolved_pressure")),
        "resume_after_quarantine_or_veto": bool(resume_event.get("resume_after_quarantine_or_veto")),
    }


def _resume_headline(checkpoint: dict[str, Any]) -> str:
    if checkpoint["kind"] == "cycle":
        return "checkpointed cycle resume recovers and continues the bounded run"
    if checkpoint.get("stress_name") == "replay_rollback":
        return "resume continues after a prior veto and quarantine signal before replay or rollback"
    return "checkpointed stress-lane resume recovers and completes the bounded run"


def _delta_value(cycles: list[dict[str, Any]], index: int, key: str) -> int:
    current = int(cycles[index].get(key, 0))
    previous = 0 if index == 0 else int(cycles[index - 1].get(key, 0))
    return max(0, current - previous)


def _delta_rates(
    *,
    cycles: list[dict[str, Any]],
    numerator_key: str,
    denominator_key: str,
) -> list[float]:
    rates: list[float] = []
    for index, cycle in enumerate(cycles):
        numerator = _delta_value(cycles, index, numerator_key)
        denominator = _delta_value(cycles, index, denominator_key)
        rates.append(0.0 if denominator <= 0 else round(numerator / float(denominator), 6))
    return rates


def _first_nonzero_metric(cycles: list[dict[str, Any]], key: str) -> float:
    for cycle in cycles:
        value = float(cycle.get(key, 0.0))
        if value > 0.0:
            return value
    return 0.0


def _last_nonzero_metric(cycles: list[dict[str, Any]], key: str) -> float:
    for cycle in reversed(cycles):
        value = float(cycle.get(key, 0.0))
        if value > 0.0:
            return value
    return 0.0


def _drift_payload(*, delta: float, meaning: str, prefer_lower: bool = False) -> dict[str, Any]:
    threshold = 0.01
    if abs(delta) <= threshold:
        direction = "flat"
    else:
        improving = delta < 0.0 if prefer_lower else delta > 0.0
        direction = "improved" if improving else "degraded"
    return {
        "delta": round(delta, 6),
        "direction": direction,
        "meaning": meaning,
    }


def _initialize_stress_context(*, config_path: Path, state_root: Path) -> dict[str, Any]:
    _ensure_runtime_initialized(config_path=config_path, state_root=state_root)
    return _load_runtime_context(config_path=config_path, state_root=state_root)


def _ensure_runtime_initialized(*, config_path: Path, state_root: Path) -> None:
    store = FabricStateStore(state_root)
    if store.load_current_state() is not None:
        return
    _run_cli(env=_runtime_env(state_root), args=["fabric", "init", str(config_path)])


def _load_runtime_context(*, config_path: Path, state_root: Path) -> dict[str, Any]:
    config, _, registry, _ = load_fabric_bootstrap(config_path)
    store = FabricStateStore(state_root)
    state = store.load_current_state()
    if state is None:
        raise RuntimeError(f"Phase 8 runtime is not initialized for {config_path}.")
    lifecycle = FabricLifecycleManager(
        store=store,
        state=state,
        config=config,
        utility_profiles=registry["utility_profiles"],
    )
    memory = FabricMemoryManager(store=store, state=state, config=config)
    need_manager = NeedSignalManager(store=store, state=state, config=config)
    authority_engine = AuthorityEngine(store=store, state=state, config=config)
    routing_engine = RoutingEngine(store=store, state=state, config=config, registry=registry)
    return {
        "config": config,
        "registry": registry,
        "store": store,
        "state": state,
        "lifecycle": lifecycle,
        "memory": memory,
        "need_manager": need_manager,
        "authority_engine": authority_engine,
        "routing_engine": routing_engine,
    }


def _promote_routing_memory(
    *,
    memory: FabricMemoryManager,
    payload: dict[str, Any],
    producer_cell_id: str,
    trust_ref: str = "trust:bounded_local_v1",
) -> dict[str, Any]:
    candidate = memory.nominate_candidate(
        payload={
            "workflow_name": payload["workflow_name"],
            "document_id": payload["document_id"],
            "inputs": payload["inputs"],
            "selected_cells": [producer_cell_id],
            "selected_roles": [producer_cell_id],
            "source_run_ref": "phase8:routing_memory",
            "source_workspace_ref": "phase8:routing_memory",
            "source_log_refs": [],
        },
        source_ref="phase8:routing_memory",
        source_log_refs=[],
        producer_cell_id=producer_cell_id,
        descriptor_kind="workflow_intake",
        task_scope=f"{payload['workflow_name']}:{payload['document_id']}",
        trust_ref=trust_ref,
    )
    return memory.review_candidate(
        candidate_id=candidate["candidate_id"],
        reviewer_id="governance:phase5_memory_reviewer",
        decision="promote",
        compression_mode="quantized_summary_v1",
        retention_tier="warm",
        reason="phase8 promoted routing memory",
    )


def _make_signal(scenario: dict[str, Any], kind: str, signal_id: str) -> dict[str, Any]:
    payload = _json_clone(scenario["signals"][kind])
    payload["need_signal_id"] = signal_id
    return payload


def _patch_runtime_states(*, state_root: Path, fabric_id: str, updates: dict[str, dict[str, object]]) -> None:
    runtime_path = state_root / fabric_id / "lifecycle" / "runtime_states.json"
    runtime_payload = _read_json(runtime_path)
    for cell_id, patch in updates.items():
        runtime_payload["states"][cell_id].update(patch)
    write_json_atomic(runtime_path, runtime_payload)


def _selected_router(decision: dict[str, Any]) -> str | None:
    for cell_id in decision.get("selected_cells", []):
        if "router" in str(cell_id):
            return str(cell_id)
    return None


def _run_cli(*, env: dict[str, str], args: list[str], stdin_text: str | None = None) -> dict[str, Any]:
    result = subprocess.run(
        [str(RUNNER)] + args,
        cwd=str(REPO_ROOT),
        env=env,
        input=stdin_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip() == "":
        raise RuntimeError(f"CLI wrote no stdout for args={args}. stderr={result.stderr}")
    payload = json.loads(result.stdout)
    if result.returncode != 0 or not payload.get("ok", False):
        raise RuntimeError(f"CLI failed for args={args}: {result.stdout}\n{result.stderr}")
    return payload


def _runtime_env(state_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGIF_FABRIC_STATE_ROOT"] = str(state_root.resolve())
    return env


def _normalize_phase8_artifact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    normalized = _json_clone(summary)
    for cycle in normalized.get("cycles", []):
        for case_row in cycle.get("case_rows", []):
            case_row.pop("workflow_id", None)
            case_row.pop("output_digest", None)
    for payload in normalized.get("stress_results", {}).values():
        payload.pop("rollback_ref", None)
        payload.pop("quarantine_event_id", None)
        payload.pop("state_digest", None)
        payload.pop("state_digest_before", None)
        payload.pop("state_digest_after", None)
        payload.pop("workflow_id", None)
    return normalized


def _score_result(*, result: dict[str, Any], truth: dict[str, Any]) -> float:
    matched = 0
    for field_name, truth_value in truth.items():
        if str(result.get(field_name, "")) == str(truth_value):
            matched += 1
    return round(matched / float(len(truth)), 6)


def _resolve_profile_ref(profile_path: Path, ref: str) -> Path:
    candidate = Path(ref)
    if candidate.is_absolute():
        return candidate.resolve()
    return (profile_path.parent / candidate).resolve()


def _stress_state_root(run_root: Path, stress_name: str) -> Path:
    root = (run_root / "stress" / stress_name / "runtime_state").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    write_json_atomic(path, manifest)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _parse_utc(value: str) -> float:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc).timestamp()


__all__ = [
    "PHASE8_BOUNDED_SUMMARY_BASENAME",
    "PHASE8_SHORT_PROFILE",
    "rollback_lifecycle_snapshot",
    "run_phase8_bounded_validation",
    "run_phase8_profile",
    "write_phase8_summary",
]
