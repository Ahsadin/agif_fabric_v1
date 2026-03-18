"""Phase 7 finance tissue execution and flat benchmark helpers."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from intelligence.fabric.common import (
    FabricError,
    REPO_ROOT,
    canonical_json_hash,
    load_json_file,
    repo_relative,
    utc_now_iso,
    write_json_atomic,
)
from intelligence.fabric.workspace.store import (
    build_phase7_workspace,
    finalize_phase7_workspace,
    record_phase7_governance,
    record_phase7_handoff,
    record_phase7_stage,
)


PHASE7_EXECUTOR_VERSION = "agif.fabric.phase7.domain.v1"
PHASE7_ENGINE_VERSION = "phase7"
PHASE7_TISSUE_REGISTRY_DEFAULT = REPO_ROOT / "cells" / "finance_workflow" / "tissue_registry_phase7.json"
KNOWN_COST_CENTERS = {"FIN-OPS", "AP-TEAM", "TRAVEL-OPS"}
STAGE_SEQUENCE = (
    ("intake_classification", "finance_intake_routing_tissue"),
    ("intake_routing", "finance_intake_routing_tissue"),
    ("extraction", "finance_extraction_tissue"),
    ("normalization", "finance_validation_correction_tissue"),
    ("correction", "finance_validation_correction_tissue"),
    ("anomaly_review", "finance_anomaly_reviewer_tissue"),
    ("workspace_guard", "finance_workspace_governance_tissue"),
    ("governance_review", "finance_workspace_governance_tissue"),
    ("reporting", "finance_reporting_output_tissue"),
    ("output_formatting", "finance_reporting_output_tissue"),
)


def is_phase7_profile(config: dict[str, Any]) -> bool:
    return str(config.get("benchmark_profile", {}).get("name", "")).startswith("phase7")


def phase7_workflow_identity(workflow_payload: dict[str, Any]) -> tuple[str, str]:
    digest = canonical_json_hash(workflow_payload)
    return f"wf_{digest[:16]}", digest


def load_phase7_tissue_registry(config: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    profile = config.get("benchmark_profile", {})
    reference = str(profile.get("tissue_registry_path", "")).strip()
    if reference:
        path = (REPO_ROOT / reference).resolve()
    else:
        path = PHASE7_TISSUE_REGISTRY_DEFAULT
    payload = load_json_file(
        path,
        not_found_code="CONFIG_INVALID",
        invalid_code="CONFIG_INVALID",
        label="Phase 7 tissue registry",
    )
    if not isinstance(payload, dict):
        raise FabricError("CONFIG_INVALID", "Phase 7 tissue registry must be an object.")
    tissues = payload.get("tissues")
    if not isinstance(tissues, list) or len(tissues) == 0:
        raise FabricError("CONFIG_INVALID", "Phase 7 tissue registry must contain tissues.")
    return payload, path


def is_v1x_organic_load_profile(config: dict[str, Any]) -> bool:
    profile = config.get("benchmark_profile", {}).get("organic_load_profile", {})
    return bool(profile.get("enabled", False))


def _resolve_runtime_blueprint(
    *,
    blueprint_map: dict[str, dict[str, Any]],
    lifecycle: Any,
    cell_id: str,
) -> dict[str, Any]:
    blueprint = blueprint_map.get(cell_id)
    if blueprint is not None:
        return blueprint
    record = lifecycle.get_cell_record(cell_id)
    runtime_blueprint = record.get("blueprint")
    if not isinstance(runtime_blueprint, dict):
        raise FabricError("STATE_INVALID", f"Runtime blueprint is missing for {cell_id}.")
    return runtime_blueprint


def _organic_stage_candidate_override(
    *,
    config: dict[str, Any],
    lifecycle: Any,
    stage_id: str,
) -> list[str] | None:
    if not is_v1x_organic_load_profile(config) or stage_id != "correction":
        return None
    organic_profile = dict(config.get("benchmark_profile", {}).get("organic_load_profile", {}))
    parent_cell_id = str(organic_profile.get("split_parent_cell_id", "")).strip()
    if not parent_cell_id:
        return None
    prefix = f"{parent_cell_id}__child_"
    active_children = sorted(cell_id for cell_id in lifecycle.list_active_cells() if cell_id.startswith(prefix))
    return active_children or None


def execute_phase7_workflow(
    *,
    workflow_payload: dict[str, Any],
    config: dict[str, Any],
    registry: dict[str, Any],
    lifecycle: Any,
    memory_manager: Any,
    need_manager: Any,
    authority_engine: Any,
    routing_engine: Any,
    workspace_ref: str,
) -> dict[str, Any]:
    workflow_id, input_digest = phase7_workflow_identity(workflow_payload)
    tissue_registry, tissue_registry_path = load_phase7_tissue_registry(config)
    benchmark_profile = dict(config.get("benchmark_profile", {}))
    benchmark_class = str(benchmark_profile.get("class_name", "multi_cell_with_bounded_adaptation"))
    adaptation_enabled = bool(benchmark_profile.get("adaptation_enabled", False))
    blueprint_map = {item["cell_id"]: item for item in registry.get("blueprints", [])}
    workspace = build_phase7_workspace(
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        benchmark_class=benchmark_class,
        tissue_registry_ref=repo_relative(tissue_registry_path),
    )
    trace: list[dict[str, Any]] = []
    selected_cells: list[str] = []
    selected_roles: list[str] = []
    all_need_signal_ids: list[str] = []
    all_authority_review_ids: list[str] = []
    descriptor_use_ids: list[str] = []
    promoted_memory_ids: list[str] = []
    correction_descriptor_payloads: list[dict[str, Any]] = []
    context: dict[str, Any] = {
        "document_class": "",
        "extraction_profile": "",
        "handoff_count": 0,
        "anomalies": [],
        "reviewer_status": "clear",
        "governance_action": "",
    }

    stage_to_tissue = {stage_id: tissue_id for stage_id, tissue_id in STAGE_SEQUENCE}

    classification_decision = routing_engine.route_tissue_stage(
        stage_id="intake_classification",
        tissue_id=stage_to_tissue["intake_classification"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
    )
    classifier_cell = _require_selected_cell(classification_decision, stage_id="intake_classification")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=classification_decision,
    )
    classification = _classify_document(workflow_payload)
    context.update(classification)
    selected_cells.append(classifier_cell)
    selected_roles.append(str(blueprint_map[classifier_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="intake_classification",
        tissue_id=stage_to_tissue["intake_classification"],
        cell_id=classifier_cell,
        role_name=str(blueprint_map[classifier_cell]["role_name"]),
        output=classification,
        notes=[classification_decision["decision_reason"]],
    )
    trace.append(_trace_entry(classification_decision, classifier_cell, classification))
    all_need_signal_ids.extend(classification_decision.get("need_signal_ids", []))

    routing_decision = routing_engine.route_tissue_stage(
        stage_id="intake_routing",
        tissue_id=stage_to_tissue["intake_routing"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
    )
    router_cell = _require_selected_cell(routing_decision, stage_id="intake_routing")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=routing_decision,
    )
    routed = _route_document(workflow_payload=workflow_payload, classification=classification)
    context.update(routed)
    selected_cells.append(router_cell)
    selected_roles.append(str(blueprint_map[router_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="intake_routing",
        tissue_id=stage_to_tissue["intake_routing"],
        cell_id=router_cell,
        role_name=str(blueprint_map[router_cell]["role_name"]),
        output=routed,
        notes=[routing_decision["decision_reason"]],
    )
    trace.append(_trace_entry(routing_decision, router_cell, routed))
    all_need_signal_ids.extend(routing_decision.get("need_signal_ids", []))
    workspace = record_phase7_handoff(
        workspace,
        handoff_id="handoff_001",
        from_tissue="finance_intake_routing_tissue",
        to_tissue="finance_extraction_tissue",
        artifact_stage_id="intake_routing",
        artifact_summary=str(routed["extraction_profile"]),
    )
    context["handoff_count"] = 1

    extraction_candidates = [str(routed["target_cell_id"])]
    extraction_decision = routing_engine.route_tissue_stage(
        stage_id="extraction",
        tissue_id=stage_to_tissue["extraction"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
        candidate_cell_ids=extraction_candidates,
    )
    extractor_cell = _require_selected_cell(extraction_decision, stage_id="extraction")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=extraction_decision,
    )
    extracted = _extract_fields(workflow_payload=workflow_payload, extraction_profile=str(routed["extraction_profile"]))
    context.update(extracted)
    selected_cells.append(extractor_cell)
    selected_roles.append(str(blueprint_map[extractor_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="extraction",
        tissue_id=stage_to_tissue["extraction"],
        cell_id=extractor_cell,
        role_name=str(blueprint_map[extractor_cell]["role_name"]),
        output=extracted,
        notes=[extraction_decision["decision_reason"]],
    )
    trace.append(_trace_entry(extraction_decision, extractor_cell, extracted))
    all_need_signal_ids.extend(extraction_decision.get("need_signal_ids", []))
    uncertainty_signal = None
    if extracted["missing_fields"]:
        uncertainty_signal = _record_domain_signal(
            need_manager=need_manager,
            workflow_id=workflow_id,
            source_id=workflow_id,
            signal_kind="uncertainty",
            severity=min(1.0, 0.44 + (0.12 * len(extracted["missing_fields"]))),
            evidence_ref=f"phase7:{workflow_id}:missing:{','.join(extracted['missing_fields'])}",
            proposed_action="bounded_correction_review",
        )
        all_need_signal_ids.append(str(uncertainty_signal["need_signal_id"]))
    workspace = record_phase7_handoff(
        workspace,
        handoff_id="handoff_002",
        from_tissue="finance_extraction_tissue",
        to_tissue="finance_validation_correction_tissue",
        artifact_stage_id="extraction",
        artifact_summary="raw extracted fields",
    )
    context["handoff_count"] = 2

    normalization_decision = routing_engine.route_tissue_stage(
        stage_id="normalization",
        tissue_id=stage_to_tissue["normalization"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
    )
    normalizer_cell = _require_selected_cell(normalization_decision, stage_id="normalization")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=normalization_decision,
    )
    normalized = _normalize_fields(extracted)
    context["normalized_fields"] = normalized["normalized_fields"]
    selected_cells.append(normalizer_cell)
    selected_roles.append(str(blueprint_map[normalizer_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="normalization",
        tissue_id=stage_to_tissue["normalization"],
        cell_id=normalizer_cell,
        role_name=str(blueprint_map[normalizer_cell]["role_name"]),
        output=normalized,
        notes=[normalization_decision["decision_reason"]],
    )
    trace.append(_trace_entry(normalization_decision, normalizer_cell, normalized))
    all_need_signal_ids.extend(normalization_decision.get("need_signal_ids", []))

    correction_decision = routing_engine.route_tissue_stage(
        stage_id="correction",
        tissue_id=stage_to_tissue["correction"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
        candidate_cell_ids=_organic_stage_candidate_override(
            config=config,
            lifecycle=lifecycle,
            stage_id="correction",
        ),
    )
    correction_cell = _require_selected_cell(correction_decision, stage_id="correction")
    correction_blueprint = _resolve_runtime_blueprint(
        blueprint_map=blueprint_map,
        lifecycle=lifecycle,
        cell_id=correction_cell,
    )
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=correction_decision,
    )
    correction = _apply_corrections(
        workflow_payload=workflow_payload,
        normalized_fields=deepcopy(normalized["normalized_fields"]),
        benchmark_class=benchmark_class,
        adaptation_enabled=adaptation_enabled,
        memory_manager=memory_manager,
        authority_engine=authority_engine,
        proposer_cell_id=correction_cell,
        policy_envelope=correction_blueprint["policy_envelope"],
        trust_ref=str(correction_blueprint["trust_profile"].get("baseline")),
        workflow_id=workflow_id,
        triggering_signal=uncertainty_signal,
    )
    context["normalized_fields"] = correction["normalized_fields"]
    context["descriptor_reuse"] = correction["descriptor_reuse"]
    selected_cells.append(correction_cell)
    selected_roles.append(str(correction_blueprint["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="correction",
        tissue_id=stage_to_tissue["correction"],
        cell_id=correction_cell,
        role_name=str(correction_blueprint["role_name"]),
        output=correction,
        notes=[correction_decision["decision_reason"]],
    )
    trace.append(_trace_entry(correction_decision, correction_cell, correction))
    all_need_signal_ids.extend(correction_decision.get("need_signal_ids", []))
    all_authority_review_ids.extend(correction["authority_review_ids"])
    descriptor_use_ids.extend(correction["descriptor_refs_used"])
    correction_descriptor_payloads.extend(correction["replay_descriptor_payloads"])
    workspace = record_phase7_handoff(
        workspace,
        handoff_id="handoff_003",
        from_tissue="finance_validation_correction_tissue",
        to_tissue="finance_anomaly_reviewer_tissue",
        artifact_stage_id="correction",
        artifact_summary="normalized finance fields",
    )
    context["handoff_count"] = 3

    anomaly_decision = routing_engine.route_tissue_stage(
        stage_id="anomaly_review",
        tissue_id=stage_to_tissue["anomaly_review"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
    )
    anomaly_cell = _require_selected_cell(anomaly_decision, stage_id="anomaly_review")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=anomaly_decision,
    )
    anomaly = _detect_anomalies(correction["normalized_fields"])
    context["anomalies"] = anomaly["anomalies"]
    context["reviewer_status"] = anomaly["reviewer_status"]
    selected_cells.append(anomaly_cell)
    selected_roles.append(str(blueprint_map[anomaly_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="anomaly_review",
        tissue_id=stage_to_tissue["anomaly_review"],
        cell_id=anomaly_cell,
        role_name=str(blueprint_map[anomaly_cell]["role_name"]),
        output=anomaly,
        notes=[anomaly_decision["decision_reason"]],
    )
    trace.append(_trace_entry(anomaly_decision, anomaly_cell, anomaly))
    all_need_signal_ids.extend(anomaly_decision.get("need_signal_ids", []))
    governance_signal = None
    if anomaly["reviewer_status"] == "review_required":
        governance_signal = _record_domain_signal(
            need_manager=need_manager,
            workflow_id=workflow_id,
            source_id=anomaly_cell,
            signal_kind="trust_risk",
            severity=max(0.72, float(anomaly["anomaly_score"])),
            evidence_ref=f"phase7:{workflow_id}:anomaly:{len(anomaly['anomalies'])}",
            proposed_action="governed_hold_or_release",
        )
        all_need_signal_ids.append(str(governance_signal["need_signal_id"]))
    workspace = record_phase7_handoff(
        workspace,
        handoff_id="handoff_004",
        from_tissue="finance_anomaly_reviewer_tissue",
        to_tissue="finance_workspace_governance_tissue",
        artifact_stage_id="anomaly_review",
        artifact_summary=f"reviewer_status={anomaly['reviewer_status']}",
    )
    context["handoff_count"] = 4

    workspace_guard_decision = routing_engine.route_tissue_stage(
        stage_id="workspace_guard",
        tissue_id=stage_to_tissue["workspace_guard"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
        candidate_cell_ids=["finance_workspace_guard"],
    )
    workspace_guard_cell = _require_selected_cell(workspace_guard_decision, stage_id="workspace_guard")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=workspace_guard_decision,
    )
    workspace_check = _workspace_check(workspace)
    context["workspace_ok"] = workspace_check["workspace_ok"]
    selected_cells.append(workspace_guard_cell)
    selected_roles.append(str(blueprint_map[workspace_guard_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="workspace_guard",
        tissue_id=stage_to_tissue["workspace_guard"],
        cell_id=workspace_guard_cell,
        role_name=str(blueprint_map[workspace_guard_cell]["role_name"]),
        output=workspace_check,
        notes=[workspace_guard_decision["decision_reason"]],
    )
    trace.append(_trace_entry(workspace_guard_decision, workspace_guard_cell, workspace_check))
    all_need_signal_ids.extend(workspace_guard_decision.get("need_signal_ids", []))
    if not workspace_check["workspace_ok"]:
        governance_signal = _record_domain_signal(
            need_manager=need_manager,
            workflow_id=workflow_id,
            source_id=workspace_guard_cell,
            signal_kind="coordination_gap",
            severity=0.84,
            evidence_ref=f"phase7:{workflow_id}:workspace_guard",
            proposed_action="halt_release_until_workspace_complete",
        )
        all_need_signal_ids.append(str(governance_signal["need_signal_id"]))

    governance_decision = routing_engine.route_tissue_stage(
        stage_id="governance_review",
        tissue_id=stage_to_tissue["governance_review"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
        candidate_cell_ids=["finance_governance_coordinator"],
    )
    governance_cell = _require_selected_cell(governance_decision, stage_id="governance_review")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=governance_decision,
    )
    governance = _governance_review(
        authority_engine=authority_engine,
        proposer_cell_id=governance_cell,
        policy_envelope=blueprint_map[governance_cell]["policy_envelope"],
        trust_ref=str(blueprint_map[governance_cell]["trust_profile"].get("baseline")),
        workflow_id=workflow_id,
        need_signal=governance_signal,
        anomaly=anomaly,
        workspace_check=workspace_check,
    )
    context["governance_action"] = governance["governance_action"]
    selected_cells.append(governance_cell)
    selected_roles.append(str(blueprint_map[governance_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="governance_review",
        tissue_id=stage_to_tissue["governance_review"],
        cell_id=governance_cell,
        role_name=str(blueprint_map[governance_cell]["role_name"]),
        output=governance,
        notes=[governance_decision["decision_reason"]],
    )
    workspace = record_phase7_governance(workspace, governance_payload=governance)
    trace.append(_trace_entry(governance_decision, governance_cell, governance))
    all_need_signal_ids.extend(governance_decision.get("need_signal_ids", []))
    all_authority_review_ids.extend(governance["authority_review_ids"])
    if governance_signal is not None:
        need_manager.resolve_signal(
            need_signal_id=str(governance_signal["need_signal_id"]),
            resolution_ref=governance.get("authority_review_ids", [governance["governance_action"]])[0],
            status="resolved" if governance["final_status"] != "blocked" else "vetoed",
            actor="governance:phase7",
            effectiveness_score=0.88 if governance["final_status"] == "hold" else 0.72,
            quality="resolved_well" if governance["final_status"] == "hold" else "resolved_weakly",
            notes=governance["governance_action"],
        )
    workspace = record_phase7_handoff(
        workspace,
        handoff_id="handoff_005",
        from_tissue="finance_workspace_governance_tissue",
        to_tissue="finance_reporting_output_tissue",
        artifact_stage_id="governance_review",
        artifact_summary=governance["governance_action"],
    )
    context["handoff_count"] = 5

    reporting_decision = routing_engine.route_tissue_stage(
        stage_id="reporting",
        tissue_id=stage_to_tissue["reporting"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
        candidate_cell_ids=["finance_audit_reporter"],
    )
    reporter_cell = _require_selected_cell(reporting_decision, stage_id="reporting")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=reporting_decision,
    )
    report = _build_report(
        workflow_payload=workflow_payload,
        benchmark_class=benchmark_class,
        classification=classification,
        correction=correction,
        anomaly=anomaly,
        governance=governance,
        workspace_check=workspace_check,
    )
    selected_cells.append(reporter_cell)
    selected_roles.append(str(blueprint_map[reporter_cell]["role_name"]))
    workspace = record_phase7_stage(
        workspace,
        stage_id="reporting",
        tissue_id=stage_to_tissue["reporting"],
        cell_id=reporter_cell,
        role_name=str(blueprint_map[reporter_cell]["role_name"]),
        output=report,
        notes=[reporting_decision["decision_reason"]],
    )
    trace.append(_trace_entry(reporting_decision, reporter_cell, report))
    all_need_signal_ids.extend(reporting_decision.get("need_signal_ids", []))

    formatter_decision = routing_engine.route_tissue_stage(
        stage_id="output_formatting",
        tissue_id=stage_to_tissue["output_formatting"],
        workflow_id=workflow_id,
        workflow_payload=workflow_payload,
        workspace_context=context,
        need_manager=need_manager,
        candidate_cell_ids=["finance_output_formatter"],
    )
    formatter_cell = _require_selected_cell(formatter_decision, stage_id="output_formatting")
    _activate_stage_cell(
        lifecycle=lifecycle,
        authority_engine=authority_engine,
        workflow_id=workflow_id,
        workspace_ref=workspace_ref,
        decision=formatter_decision,
    )
    selected_cells.append(formatter_cell)
    selected_roles.append(str(blueprint_map[formatter_cell]["role_name"]))
    final_result = _format_output(
        workflow_payload=workflow_payload,
        proof_domain=str(config["proof_domain"]),
        benchmark_class=benchmark_class,
        classification=classification,
        routed=routed,
        correction=correction,
        anomaly=anomaly,
        governance=governance,
        report=report,
        selected_cells=selected_cells,
        selected_roles=selected_roles,
        input_digest=input_digest,
        tissues_used=list(workspace["tissues_used"]) + [stage_to_tissue["output_formatting"]],
        handoff_count=int(context["handoff_count"]),
    )
    workspace = record_phase7_stage(
        workspace,
        stage_id="output_formatting",
        tissue_id=stage_to_tissue["output_formatting"],
        cell_id=formatter_cell,
        role_name=str(blueprint_map[formatter_cell]["role_name"]),
        output={"final_status": final_result["final_status"]},
        notes=[formatter_decision["decision_reason"]],
    )
    trace.append(_trace_entry(formatter_decision, formatter_cell, {"final_status": final_result["final_status"]}))
    all_need_signal_ids.extend(formatter_decision.get("need_signal_ids", []))
    workspace = finalize_phase7_workspace(workspace, final_output=final_result)

    memory_review = _record_correction_memory(
        memory_manager=memory_manager,
        authority_engine=authority_engine,
        workflow_payload=workflow_payload,
        benchmark_class=benchmark_class,
        normalized_fields=correction["normalized_fields"],
        final_status=final_result["final_status"],
    )
    if memory_review["memory_id"] is not None:
        promoted_memory_ids.append(str(memory_review["memory_id"]))
    if uncertainty_signal is not None and correction["descriptor_reuse"]["used"]:
        need_manager.resolve_signal(
            need_signal_id=str(uncertainty_signal["need_signal_id"]),
            resolution_ref=correction["descriptor_reuse"]["descriptor_id"] or "phase7:correction",
            status="resolved",
            actor="correction:phase7",
            effectiveness_score=0.82,
            quality="resolved_well",
            notes="descriptor-backed correction completed",
        )
    lifecycle.set_active_task_refs(cell_ids=sorted(set(selected_cells)), workflow_ref=None)

    result = {
        "executor": {
            "config_version": PHASE7_EXECUTOR_VERSION,
            "engine_version": PHASE7_ENGINE_VERSION,
            "stage_count": len(trace),
        },
        "workflow_id": workflow_id,
        "output_digest": canonical_json_hash(final_result),
        "trace": trace,
        "result": final_result,
        "workspace_snapshot": workspace,
        "phase7": {
            "benchmark_class": benchmark_class,
            "tissue_registry_ref": repo_relative(tissue_registry_path),
            "tissues_used": sorted(set(workspace["tissues_used"])),
            "handoff_count": len(workspace["handoffs"]),
            "authority_review_ids": sorted(set(all_authority_review_ids)),
            "need_signal_ids": sorted(set(all_need_signal_ids)),
            "descriptor_refs_used": sorted(set(descriptor_use_ids)),
            "promoted_memory_ids": promoted_memory_ids,
            "replay_context": {
                "benchmark_class": benchmark_class,
                "selected_cells_by_stage": {
                    entry["stage_id"]: entry["cell_id"] for entry in trace
                },
                "selected_cells": sorted(set(selected_cells)),
                "selected_roles": sorted(set(selected_roles)),
                "descriptor_payloads": correction_descriptor_payloads,
                "governance_action": governance["governance_action"],
                "handoff_count": len(workspace["handoffs"]),
                "tissues_used": sorted(set(workspace["tissues_used"])),
            },
        },
    }
    return result


def replay_phase7_workflow(
    *,
    workflow_payload: dict[str, Any],
    proof_domain: str,
    replay_context: dict[str, Any],
) -> dict[str, Any]:
    workflow_id, input_digest = phase7_workflow_identity(workflow_payload)
    classification = _classify_document(workflow_payload)
    routed = _route_document(workflow_payload=workflow_payload, classification=classification)
    extracted = _extract_fields(workflow_payload=workflow_payload, extraction_profile=str(routed["extraction_profile"]))
    normalized = _normalize_fields(extracted)
    correction = _apply_corrections_from_payloads(
        normalized_fields=deepcopy(normalized["normalized_fields"]),
        descriptor_payloads=list(replay_context.get("descriptor_payloads", [])),
    )
    anomaly = _detect_anomalies(correction["normalized_fields"])
    governance_action = str(replay_context.get("governance_action", "approved_release"))
    governance = {
        "governance_action": governance_action,
        "final_status": "hold" if governance_action == "hold_for_review" else "accepted",
    }
    report = _build_report(
        workflow_payload=workflow_payload,
        benchmark_class=str(replay_context.get("benchmark_class", "multi_cell_with_bounded_adaptation")),
        classification=classification,
        correction=correction,
        anomaly=anomaly,
        governance=governance,
        workspace_check={"workspace_ok": True, "missing_handoffs": []},
    )
    result = _format_output(
        workflow_payload=workflow_payload,
        proof_domain=proof_domain,
        benchmark_class=str(replay_context.get("benchmark_class", "multi_cell_with_bounded_adaptation")),
        classification=classification,
        routed=routed,
        correction=correction,
        anomaly=anomaly,
        governance=governance,
        report=report,
        selected_cells=list(replay_context.get("selected_cells", [])),
        selected_roles=list(replay_context.get("selected_roles", [])),
        input_digest=input_digest,
        tissues_used=list(
            replay_context.get(
                "tissues_used",
                [
                    "finance_intake_routing_tissue",
                    "finance_extraction_tissue",
                    "finance_validation_correction_tissue",
                    "finance_anomaly_reviewer_tissue",
                    "finance_workspace_governance_tissue",
                    "finance_reporting_output_tissue",
                ],
            )
        ),
        handoff_count=int(replay_context.get("handoff_count", 5)),
    )
    return {
        "executor": {
            "config_version": PHASE7_EXECUTOR_VERSION,
            "engine_version": f"{PHASE7_ENGINE_VERSION}-replay",
            "stage_count": len(STAGE_SEQUENCE),
        },
        "workflow_id": workflow_id,
        "output_digest": canonical_json_hash(result),
        "trace": [],
        "result": result,
    }


def run_flat_baseline_workflow(
    *,
    workflow_payload: dict[str, Any],
    proof_domain: str,
) -> dict[str, Any]:
    workflow_id, input_digest = phase7_workflow_identity(workflow_payload)
    classification = _classify_document(workflow_payload)
    routed = _route_document(workflow_payload=workflow_payload, classification=classification)
    extracted = _extract_fields(workflow_payload=workflow_payload, extraction_profile=str(routed["extraction_profile"]))
    normalized = _normalize_fields(extracted)
    anomaly = _detect_anomalies(normalized["normalized_fields"])
    governance = {
        "governance_action": "not_applicable",
        "final_status": "accepted",
    }
    report = {
        "summary": "Flat baseline completed a single bounded pass without real tissues, reviewer hold, or descriptor reuse.",
        "evidence_points": [
            "flat_baseline",
            classification["document_class"],
            routed["extraction_profile"],
        ],
    }
    result = {
        "accepted": True,
        "workflow_name": str(workflow_payload.get("workflow_name", "document_workflow")),
        "document_id": workflow_payload.get("document_id"),
        "proof_domain": proof_domain,
        "benchmark_class": "flat_baseline",
        "input_digest": input_digest,
        "selected_cells": [],
        "selected_roles": [],
        "tissues_used": [],
        "handoff_count": 0,
        "document_class": classification["document_class"],
        "extraction_profile": routed["extraction_profile"],
        "normalized_vendor": str(normalized["normalized_fields"].get("vendor_name", "")),
        "normalized_currency": str(normalized["normalized_fields"].get("currency", "")),
        "normalized_total": str(normalized["normalized_fields"].get("total", "")),
        "reviewer_status": "clear" if not anomaly["anomalies"] else "clear_without_review",
        "governance_action": governance["governance_action"],
        "final_status": governance["final_status"],
        "anomaly_count": len(anomaly["anomalies"]),
        "descriptor_reuse": {
            "eligible": False,
            "used": False,
            "memory_id": None,
            "descriptor_id": None,
        },
        "report_summary": report["summary"],
    }
    return {
        "executor": {
            "config_version": PHASE7_EXECUTOR_VERSION,
            "engine_version": "phase7-flat-baseline",
            "stage_count": 4,
        },
        "workflow_id": workflow_id,
        "output_digest": canonical_json_hash(result),
        "trace": [],
        "result": result,
    }


def _trace_entry(decision: dict[str, Any], cell_id: str, output: dict[str, Any]) -> dict[str, Any]:
    summary_keys = sorted(output.keys())[:5]
    return {
        "stage_id": decision["stage_id"],
        "tissue_id": decision["tissue_id"],
        "cell_id": cell_id,
        "decision_ref": decision["decision_id"],
        "selection_mode": decision["selection_mode"],
        "output_keys": summary_keys,
    }


def _require_selected_cell(decision: dict[str, Any], *, stage_id: str) -> str:
    selected = str(decision.get("selected_cell_id") or "")
    if not selected:
        raise FabricError("ROUTING_FAILED", f"Phase 7 routing failed for stage: {stage_id}.")
    return selected


def _activate_stage_cell(
    *,
    lifecycle: Any,
    authority_engine: Any,
    workflow_id: str,
    workspace_ref: str,
    decision: dict[str, Any],
) -> None:
    if not decision.get("selected_cells"):
        return
    lifecycle.activate_for_workflow(
        cell_ids=list(decision["selected_cells"]),
        workflow_id=workflow_id,
        authority_engine=authority_engine,
    )
    lifecycle.apply_routing_context(
        cell_ids=list(decision["selected_cells"]),
        workspace_ref=workspace_ref,
        descriptor_refs=list(decision.get("descriptor_refs_used", [])),
        need_signal_ids=list(decision.get("need_signal_ids", [])),
    )


def _classify_document(workflow_payload: dict[str, Any]) -> dict[str, Any]:
    inputs = workflow_payload.get("inputs", {})
    if not isinstance(inputs, dict):
        inputs = {}
    document_type = str(inputs.get("document_type", "")).strip().lower()
    if document_type in {"invoice", "vendor_invoice"} or str(inputs.get("invoice_number", "")).strip():
        document_class = "vendor_invoice"
    elif document_type in {"receipt", "expense_receipt"}:
        document_class = "expense_receipt"
    else:
        document_class = "unknown_document"
    return {
        "document_class": document_class,
        "classification_reason": f"document_type={document_type or 'missing'}",
    }


def _route_document(*, workflow_payload: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    inputs = workflow_payload.get("inputs", {})
    if not isinstance(inputs, dict):
        inputs = {}
    document_class = str(classification["document_class"])
    if document_class == "expense_receipt":
        extraction_profile = "receipt_extraction"
        target_cell_id = "finance_receipt_extractor"
    else:
        extraction_profile = "invoice_extraction"
        target_cell_id = "finance_invoice_extractor"
    priority_band = "review" if _safe_float(inputs.get("total")) >= 5000 else "standard"
    return {
        "extraction_profile": extraction_profile,
        "priority_band": priority_band,
        "target_cell_id": target_cell_id,
    }


def _extract_fields(*, workflow_payload: dict[str, Any], extraction_profile: str) -> dict[str, Any]:
    inputs = workflow_payload.get("inputs", {})
    if not isinstance(inputs, dict):
        inputs = {}
    extracted_fields = {
        "document_type": str(inputs.get("document_type", "")).strip().lower(),
        "vendor_name": str(inputs.get("vendor_name", "")).strip(),
        "invoice_number": str(inputs.get("invoice_number", "")).strip(),
        "invoice_date": str(inputs.get("invoice_date", "")).strip(),
        "due_date": str(inputs.get("due_date", "")).strip(),
        "currency": str(inputs.get("currency", "")).strip(),
        "subtotal": str(inputs.get("subtotal", "")).strip(),
        "tax": str(inputs.get("tax", "")).strip(),
        "total": str(inputs.get("total", "")).strip(),
        "payment_terms": str(inputs.get("payment_terms", "")).strip(),
        "cost_center": str(inputs.get("cost_center", "")).strip(),
        "ocr_quality": str(inputs.get("ocr_quality", "")).strip().lower(),
        "source_channel": str(inputs.get("source_channel", "")).strip(),
    }
    required_fields = ["vendor_name", "invoice_date", "total"]
    if extraction_profile == "invoice_extraction":
        required_fields.extend(["invoice_number", "currency"])
    missing_fields = sorted(
        field_name
        for field_name in required_fields
        if str(extracted_fields.get(field_name, "")).strip() == ""
    )
    quality_map = {"high": 0.92, "medium": 0.72, "low": 0.55}
    extraction_confidence = quality_map.get(extracted_fields["ocr_quality"], 0.68) - (0.08 * len(missing_fields))
    return {
        "extracted_fields": extracted_fields,
        "missing_fields": missing_fields,
        "extraction_confidence": round(max(0.0, min(1.0, extraction_confidence)), 6),
    }


def _normalize_fields(extracted: dict[str, Any]) -> dict[str, Any]:
    fields = deepcopy(extracted["extracted_fields"])
    normalized = {
        "document_type": _canonical_document_type(fields.get("document_type")),
        "vendor_name": _clean_vendor_name(str(fields.get("vendor_name", ""))),
        "invoice_number": str(fields.get("invoice_number", "")).strip().upper(),
        "invoice_date": _normalize_date(str(fields.get("invoice_date", ""))),
        "due_date": _normalize_date(str(fields.get("due_date", ""))),
        "currency": str(fields.get("currency", "")).strip().upper(),
        "subtotal": _normalize_amount(str(fields.get("subtotal", ""))),
        "tax": _normalize_amount(str(fields.get("tax", ""))),
        "total": _normalize_amount(str(fields.get("total", ""))),
        "payment_terms": str(fields.get("payment_terms", "")).strip(),
        "payment_term_days": _parse_payment_term_days(str(fields.get("payment_terms", "")).strip()),
        "cost_center": str(fields.get("cost_center", "")).strip().upper(),
        "ocr_quality": str(fields.get("ocr_quality", "")).strip().lower(),
        "source_channel": str(fields.get("source_channel", "")).strip(),
    }
    return {
        "normalized_fields": normalized,
        "normalization_notes": [
            f"invoice_date={normalized['invoice_date'] or 'missing'}",
            f"due_date={normalized['due_date'] or 'missing'}",
            f"currency={normalized['currency'] or 'missing'}",
        ],
    }


def _apply_corrections(
    *,
    workflow_payload: dict[str, Any],
    normalized_fields: dict[str, Any],
    benchmark_class: str,
    adaptation_enabled: bool,
    memory_manager: Any,
    authority_engine: Any,
    proposer_cell_id: str,
    policy_envelope: dict[str, Any],
    trust_ref: str,
    workflow_id: str,
    triggering_signal: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate = _find_matching_correction_memory(
        memory_manager=memory_manager,
        workflow_payload=workflow_payload,
        normalized_fields=normalized_fields,
    )
    authority_review_ids: list[str] = []
    descriptor_refs_used: list[str] = []
    replay_descriptor_payloads: list[dict[str, Any]] = []
    corrected = deepcopy(normalized_fields)
    notes: list[str] = []
    descriptor_reuse = {
        "eligible": candidate is not None,
        "used": False,
        "memory_id": None,
        "descriptor_id": None,
    }
    if adaptation_enabled and candidate is not None:
        authority_review = authority_engine.evaluate_action(
            action="descriptor_use",
            proposer=proposer_cell_id,
            need_signal=triggering_signal,
            utility_evaluation={
                "utility_score": 0.78,
                "threshold": 0.28,
            },
            policy_envelope=policy_envelope,
            trust_state={
                "trust_ref": candidate["record"].get("trust_ref"),
                "trust_score": float(candidate["record"].get("trust_score", 0.76)),
            },
            rollback_ref=f"phase7:correction:{workflow_id}",
            related_cells=[proposer_cell_id],
            descriptor_refs=[str(candidate["record"].get("descriptor_id"))],
            metadata={
                "workflow_id": workflow_id,
                "lineage_id": proposer_cell_id,
                "descriptor_provenance_score": min(1.0, float(candidate["record"].get("trust_score", 0.76))),
            },
        )
        authority_review_ids.append(str(authority_review["review_id"]))
        if authority_review["approved"]:
            corrected["vendor_name"] = str(candidate["payload"].get("normalized_vendor", corrected["vendor_name"]))
            if not corrected.get("currency"):
                corrected["currency"] = str(candidate["payload"].get("default_currency", ""))
            if not corrected.get("due_date") and corrected.get("invoice_date"):
                term_days = int(candidate["payload"].get("default_payment_term_days", 0))
                if term_days > 0:
                    corrected["due_date"] = _offset_date(str(corrected["invoice_date"]), term_days)
            descriptor_reuse = {
                "eligible": True,
                "used": True,
                "memory_id": str(candidate["record"].get("memory_id")),
                "descriptor_id": str(candidate["record"].get("descriptor_id")),
            }
            descriptor_refs_used.append(str(candidate["record"].get("descriptor_id")))
            replay_descriptor_payloads.append(deepcopy(candidate["payload"]))
            memory_manager.record_descriptor_reuse(memory_ids=[str(candidate["record"].get("memory_id"))])
            authority_engine.finalize_review(
                str(authority_review["review_id"]),
                action_ref=f"{workflow_id}:correction",
                rollback_ref=f"phase7:correction:{workflow_id}",
            )
            notes.append("descriptor-backed correction applied")
        else:
            notes.append("descriptor reuse was vetoed")
    if not corrected.get("due_date") and corrected.get("invoice_date") and corrected.get("payment_term_days", 0) > 0:
        corrected["due_date"] = _offset_date(str(corrected["invoice_date"]), int(corrected["payment_term_days"]))
        notes.append("due_date derived from payment terms")
    if corrected.get("currency"):
        corrected["currency"] = str(corrected["currency"]).upper()
    return {
        "normalized_fields": corrected,
        "correction_notes": notes,
        "descriptor_reuse": descriptor_reuse,
        "authority_review_ids": authority_review_ids,
        "descriptor_refs_used": descriptor_refs_used,
        "replay_descriptor_payloads": replay_descriptor_payloads,
        "benchmark_class": benchmark_class,
    }


def _apply_corrections_from_payloads(
    *,
    normalized_fields: dict[str, Any],
    descriptor_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    corrected = deepcopy(normalized_fields)
    if descriptor_payloads:
        payload = descriptor_payloads[0]
        corrected["vendor_name"] = str(payload.get("normalized_vendor", corrected["vendor_name"]))
        if not corrected.get("currency"):
            corrected["currency"] = str(payload.get("default_currency", ""))
        if not corrected.get("due_date") and corrected.get("invoice_date"):
            term_days = int(payload.get("default_payment_term_days", 0))
            if term_days > 0:
                corrected["due_date"] = _offset_date(str(corrected["invoice_date"]), term_days)
    return {
        "normalized_fields": corrected,
        "descriptor_reuse": {
            "eligible": bool(descriptor_payloads),
            "used": bool(descriptor_payloads),
            "memory_id": None,
            "descriptor_id": None,
        },
    }


def _detect_anomalies(normalized_fields: dict[str, Any]) -> dict[str, Any]:
    anomalies: list[str] = []
    subtotal = _safe_float(normalized_fields.get("subtotal"))
    tax = _safe_float(normalized_fields.get("tax"))
    total = _safe_float(normalized_fields.get("total"))
    if total and abs((subtotal + tax) - total) > 0.01:
        anomalies.append("total_mismatch")
    if total >= 5000:
        anomalies.append("amount_exceeds_auto_approval_limit")
    if not str(normalized_fields.get("currency", "")).strip():
        anomalies.append("missing_currency")
    if not str(normalized_fields.get("vendor_name", "")).strip():
        anomalies.append("missing_vendor")
    if str(normalized_fields.get("cost_center", "")).strip().upper() not in KNOWN_COST_CENTERS:
        anomalies.append("unknown_cost_center")
    anomaly_score = min(1.0, 0.22 * len(anomalies) + (0.2 if total >= 5000 else 0.0))
    reviewer_status = "review_required" if anomalies else "clear"
    return {
        "anomalies": anomalies,
        "anomaly_score": round(anomaly_score, 6),
        "reviewer_status": reviewer_status,
    }


def _workspace_check(workspace: dict[str, Any]) -> dict[str, Any]:
    stage_outputs = workspace.get("stage_outputs", {})
    required_stages = {"intake_routing", "extraction", "correction", "anomaly_review"}
    missing = sorted(stage for stage in required_stages if stage not in stage_outputs)
    return {
        "workspace_ok": len(missing) == 0,
        "missing_handoffs": missing,
    }


def _governance_review(
    *,
    authority_engine: Any,
    proposer_cell_id: str,
    policy_envelope: dict[str, Any],
    trust_ref: str,
    workflow_id: str,
    need_signal: dict[str, Any] | None,
    anomaly: dict[str, Any],
    workspace_check: dict[str, Any],
) -> dict[str, Any]:
    authority_review_ids: list[str] = []
    if anomaly["reviewer_status"] == "review_required" or not workspace_check["workspace_ok"]:
        review = authority_engine.evaluate_action(
            action="quarantine_escalation",
            proposer=proposer_cell_id,
            need_signal=need_signal,
            utility_evaluation={
                "utility_score": max(0.35, float(anomaly["anomaly_score"])),
                "threshold": 0.3,
            },
            policy_envelope=policy_envelope,
            trust_state={
                "trust_ref": trust_ref,
                "trust_score": 0.95 if "policy" in trust_ref else 0.76,
            },
            rollback_ref=f"phase7:governance:{workflow_id}",
            related_cells=[proposer_cell_id],
            metadata={
                "workflow_id": workflow_id,
                "lineage_id": proposer_cell_id,
                "lineage_usefulness_score": 0.4,
            },
        )
        authority_review_ids.append(str(review["review_id"]))
        authority_engine.finalize_review(
            str(review["review_id"]),
            action_ref=f"{workflow_id}:governance",
            rollback_ref=f"phase7:governance:{workflow_id}",
        )
        if review["approved"]:
            return {
                "governance_action": "hold_for_review",
                "final_status": "hold",
                "authority_review_ids": authority_review_ids,
            }
        return {
            "governance_action": "blocked_by_veto",
            "final_status": "blocked",
            "authority_review_ids": authority_review_ids,
        }
    return {
        "governance_action": "approved_release",
        "final_status": "accepted",
        "authority_review_ids": authority_review_ids,
    }


def _build_report(
    *,
    workflow_payload: dict[str, Any],
    benchmark_class: str,
    classification: dict[str, Any],
    correction: dict[str, Any],
    anomaly: dict[str, Any],
    governance: dict[str, Any],
    workspace_check: dict[str, Any],
) -> dict[str, Any]:
    summary = (
        f"{benchmark_class} processed {workflow_payload.get('document_id')} as {classification['document_class']} "
        f"and finished {governance['final_status']} with governance action {governance['governance_action']}."
    )
    evidence_points = [
        f"descriptor_reuse={correction['descriptor_reuse']['used']}",
        f"descriptor_id={correction['descriptor_reuse']['descriptor_id'] or 'none'}",
        f"anomaly_count={len(anomaly['anomalies'])}",
        f"authority_reviews={len(correction['authority_review_ids']) + len(governance['authority_review_ids'])}",
        f"workspace_ok={workspace_check['workspace_ok']}",
    ]
    custody_notes = [
        f"classified_as={classification['document_class']}",
        "correction="
        + (
            f"descriptor:{correction['descriptor_reuse']['descriptor_id']}"
            if correction["descriptor_reuse"]["used"]
            else "local_only"
        ),
        f"anomaly_review={','.join(anomaly['anomalies']) or 'none'}",
        f"governance={governance['governance_action']}",
    ]
    confidence_factors = [
        f"support=descriptor_reuse:{correction['descriptor_reuse']['used']}",
        f"support=workspace_complete:{workspace_check['workspace_ok']}",
        f"drag=anomaly_count:{len(anomaly['anomalies'])}",
    ]
    return {
        "summary": summary,
        "evidence_points": evidence_points,
        "custody_notes": custody_notes,
        "confidence_factors": confidence_factors,
    }


def _format_output(
    *,
    workflow_payload: dict[str, Any],
    proof_domain: str,
    benchmark_class: str,
    classification: dict[str, Any],
    routed: dict[str, Any],
    correction: dict[str, Any],
    anomaly: dict[str, Any],
    governance: dict[str, Any],
    report: dict[str, Any],
    selected_cells: list[str],
    selected_roles: list[str],
    input_digest: str,
    tissues_used: list[str],
    handoff_count: int,
) -> dict[str, Any]:
    normalized_fields = correction["normalized_fields"]
    final_status = str(governance["final_status"])
    return {
        "accepted": final_status == "accepted",
        "workflow_name": str(workflow_payload.get("workflow_name", "document_workflow")),
        "document_id": workflow_payload.get("document_id"),
        "proof_domain": proof_domain,
        "benchmark_class": benchmark_class,
        "input_digest": input_digest,
        "selected_cells": sorted(set(selected_cells)),
        "selected_roles": sorted(set(selected_roles)),
        "tissues_used": sorted(set(tissues_used)),
        "handoff_count": handoff_count,
        "document_class": classification["document_class"],
        "extraction_profile": routed["extraction_profile"],
        "normalized_vendor": str(normalized_fields.get("vendor_name", "")),
        "normalized_currency": str(normalized_fields.get("currency", "")),
        "normalized_total": str(normalized_fields.get("total", "")),
        "reviewer_status": anomaly["reviewer_status"],
        "governance_action": governance["governance_action"],
        "final_status": final_status,
        "anomaly_count": len(anomaly["anomalies"]),
        "descriptor_reuse": deepcopy(correction["descriptor_reuse"]),
        "report_summary": report["summary"],
    }


def _record_domain_signal(
    *,
    need_manager: Any,
    workflow_id: str,
    source_id: str,
    signal_kind: str,
    severity: float,
    evidence_ref: str,
    proposed_action: str,
) -> dict[str, Any]:
    created_utc = utc_now_iso()
    expires_at_utc = _future_utc(seconds=max(300, int(getattr(need_manager, "default_ttl_seconds", 900))))
    return need_manager.record_signal(
        signal={
            "need_signal_id": f"{workflow_id}:{signal_kind}:{canonical_json_hash([source_id, evidence_ref])[:8]}",
            "source_type": "tissue",
            "source_id": source_id,
            "signal_kind": signal_kind,
            "severity": severity,
            "evidence_ref": evidence_ref,
            "proposed_action": proposed_action,
            "status": "open",
            "expires_at_utc": expires_at_utc,
            "resolution_ref": None,
            "created_utc": created_utc,
        },
        actor=f"phase7:{workflow_id}",
    )


def _record_correction_memory(
    *,
    memory_manager: Any,
    authority_engine: Any,
    workflow_payload: dict[str, Any],
    benchmark_class: str,
    normalized_fields: dict[str, Any],
    final_status: str,
) -> dict[str, Any]:
    if final_status != "accepted":
        return {"memory_id": None, "descriptor_id": None}
    payload = {
        "workflow_name": str(workflow_payload.get("workflow_name", "document_workflow")),
        "document_id": workflow_payload.get("document_id"),
        "inputs": dict(workflow_payload.get("inputs", {})),
        "selected_cells": ["finance_correction_specialist"],
        "summary_vector": [
            _vendor_signature(str(normalized_fields.get("vendor_name", "")))[:18],
            str(normalized_fields.get("document_type", ""))[:12],
            str(normalized_fields.get("currency", ""))[:8],
        ],
        "normalized_vendor": str(normalized_fields.get("vendor_name", "")),
        "default_currency": str(normalized_fields.get("currency", "")),
        "default_payment_term_days": int(normalized_fields.get("payment_term_days", 0)),
    }
    candidate = memory_manager.nominate_candidate(
        payload=payload,
        source_ref=f"phase7:{workflow_payload.get('document_id')}",
        source_log_refs=[],
        producer_cell_id="finance_correction_specialist",
        descriptor_kind="correction_memory",
        task_scope=f"{workflow_payload.get('workflow_name', 'document_workflow')}:{_vendor_signature(str(normalized_fields.get('vendor_name', '')))}",
        trust_ref="trust:bounded_local_v1",
    )
    if benchmark_class == "multi_cell_with_bounded_adaptation":
        review = memory_manager.review_candidate(
            candidate_id=candidate["candidate_id"],
            reviewer_id="governance:phase5_memory_reviewer",
            decision="promote",
            compression_mode="quantized_summary_v1",
            retention_tier="warm",
            reason="phase7 reviewed correction memory",
            authority_engine=None,
        )
    else:
        review = memory_manager.review_candidate(
            candidate_id=candidate["candidate_id"],
            reviewer_id="governance:phase5_memory_reviewer",
            decision="defer",
            compression_mode="review_buffer_v1",
            retention_tier="hot",
            reason="phase7 no-adaptation class keeps correction memory non-reusable",
            authority_engine=authority_engine,
        )
    if review.get("memory_id") is not None:
        promoted = memory_manager.load_promoted_memories()
        record = promoted["active"].get(str(review["memory_id"]))
        if isinstance(record, dict) and isinstance(record.get("payload_ref"), str):
            payload_path = _resolve_repo_ref(str(record["payload_ref"]))
            payload_value = load_json_file(
                payload_path,
                not_found_code="MEMORY_INVALID",
                invalid_code="MEMORY_INVALID",
                label=f"Phase 7 promoted correction memory {review['memory_id']}",
            )
            if isinstance(payload_value, dict):
                payload_value["normalized_vendor"] = str(normalized_fields.get("vendor_name", ""))
                payload_value["default_currency"] = str(normalized_fields.get("currency", ""))
                payload_value["default_payment_term_days"] = int(normalized_fields.get("payment_term_days", 0))
                write_json_atomic(payload_path, payload_value)
    return {
        "memory_id": review.get("memory_id"),
        "descriptor_id": review.get("descriptor_id"),
    }


def _find_matching_correction_memory(
    *,
    memory_manager: Any,
    workflow_payload: dict[str, Any],
    normalized_fields: dict[str, Any],
) -> dict[str, Any] | None:
    promoted = memory_manager.load_promoted_memories()
    active = list(promoted.get("active", {}).values())
    vendor_signature = _vendor_signature(str(normalized_fields.get("vendor_name", "")))
    best: dict[str, Any] | None = None
    best_score = 0.0
    for record in active:
        if str(record.get("producer_cell_id")) != "finance_correction_specialist":
            continue
        payload_ref = record.get("payload_ref")
        if not isinstance(payload_ref, str):
            continue
        payload_path = _resolve_repo_ref(payload_ref)
        if not payload_path.exists():
            continue
        payload = load_json_file(
            payload_path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label=f"Phase 7 correction memory {record.get('memory_id')}",
        )
        if not isinstance(payload, dict):
            continue
        summary_vector = payload.get("summary_vector", [])
        if not isinstance(summary_vector, list):
            summary_vector = []
        score = 0.0
        stored_signature = _vendor_signature(str(summary_vector[0])) if summary_vector else ""
        normalized_vendor_signature = _vendor_signature(str(payload.get("normalized_vendor", "")))
        if vendor_signature and (
            vendor_signature[:12] == stored_signature[:12]
            or vendor_signature[:12] == normalized_vendor_signature[:12]
        ):
            score += 0.72
        if str(payload.get("default_currency", "")).strip().upper() == str(normalized_fields.get("currency", "")).strip().upper():
            score += 0.08
        if int(payload.get("default_payment_term_days", 0)) > 0:
            score += 0.1
        score += min(0.1, float(record.get("trust_score", 0.76)) * 0.1)
        if score < 0.5:
            continue
        if score > best_score:
            best_score = score
            best = {
                "record": deepcopy(record),
                "payload": deepcopy(payload),
            }
    return best


def _clean_vendor_name(raw_vendor: str) -> str:
    pieces = " ".join(raw_vendor.replace(",", " ").split()).strip()
    if not pieces:
        return ""
    normalized_parts: list[str] = []
    for part in pieces.split():
        lower = part.lower()
        if lower == "gmbh":
            normalized_parts.append("GmbH")
        elif lower == "ltd":
            normalized_parts.append("Ltd")
        elif lower == "llc":
            normalized_parts.append("LLC")
        elif part.isupper():
            normalized_parts.append(part)
        else:
            normalized_parts.append(part.capitalize())
    return " ".join(normalized_parts)


def _canonical_document_type(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"invoice", "vendor_invoice"}:
        return "invoice"
    if normalized in {"receipt", "expense_receipt"}:
        return "receipt"
    return normalized


def _normalize_amount(raw_amount: str) -> str:
    value = _safe_float(raw_amount)
    if value == 0.0 and str(raw_amount).strip() in {"", "0", "0.0", "0.00"}:
        return "0.00" if str(raw_amount).strip() else ""
    if value == 0.0 and str(raw_amount).strip() == "":
        return ""
    return f"{value:.2f}"


def _normalize_date(raw_date: str) -> str:
    normalized = raw_date.strip()
    if not normalized:
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(normalized, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _offset_date(date_text: str, days: int) -> str:
    if not date_text:
        return ""
    try:
        return (datetime.strptime(date_text, "%Y-%m-%d") + timedelta(days=int(days))).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _parse_payment_term_days(payment_terms: str) -> int:
    digits = "".join(ch for ch in payment_terms if ch.isdigit())
    if not digits:
        return 0
    return int(digits)


def _safe_float(value: Any) -> float:
    raw = str(value or "").replace(",", "").strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _future_utc(*, seconds: int) -> str:
    now = datetime.now(tz=timezone.utc).replace(microsecond=0)
    return (now + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def _resolve_repo_ref(reference: str) -> Path:
    path = Path(reference)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / reference).resolve()


def _vendor_signature(raw_vendor: str) -> str:
    normalized = raw_vendor.lower().replace("0", "o").replace("1", "i")
    return "".join(ch for ch in normalized if ch.isalnum() or ch == " ").strip()
