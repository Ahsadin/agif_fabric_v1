"""Deterministic Phase 7 benchmark harness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from intelligence.fabric.common import repo_relative, utc_now_iso
from intelligence.fabric.domain.finance import run_flat_baseline_workflow
from intelligence.fabric.governance.authority import AuthorityEngine
from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.memory import FabricMemoryManager
from intelligence.fabric.needs.engine import NeedSignalManager
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.routing import RoutingEngine
from intelligence.fabric.state_store import FabricStateStore


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPO_ROOT / "runner" / "cell"
SUITE_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "benchmark_suite.json"
NO_ADAPT_CONFIG = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "minimal_fabric_config_no_adaptation.json"
WITH_ADAPT_CONFIG = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "minimal_fabric_config_with_adaptation.json"
TISSUE_ORDER = [
    "finance_intake_routing_tissue",
    "finance_extraction_tissue",
    "finance_validation_correction_tissue",
    "finance_anomaly_reviewer_tissue",
    "finance_workspace_governance_tissue",
    "finance_reporting_output_tissue",
]
TISSUE_TRUTH_FIELDS = {
    "finance_intake_routing_tissue": ["document_class", "extraction_profile"],
    "finance_extraction_tissue": ["normalized_total"],
    "finance_validation_correction_tissue": ["normalized_vendor", "normalized_currency", "normalized_total"],
    "finance_anomaly_reviewer_tissue": ["reviewer_status"],
    "finance_workspace_governance_tissue": ["governance_action", "final_status"],
    "finance_reporting_output_tissue": ["final_status"],
}
TISSUE_LABELS = {
    "finance_intake_routing_tissue": "intake/routing",
    "finance_extraction_tissue": "extraction",
    "finance_validation_correction_tissue": "validation/correction",
    "finance_anomaly_reviewer_tissue": "anomaly/reviewer",
    "finance_workspace_governance_tissue": "workspace/governance",
    "finance_reporting_output_tissue": "reporting/output",
}


def run_phase7_benchmarks() -> dict[str, Any]:
    suite = _load_suite()
    baseline_pass_one = _run_flat_suite(suite)
    baseline_pass_two = _run_flat_suite(suite)
    no_adapt_pass_one = _run_fabric_suite(config_path=NO_ADAPT_CONFIG, suite=suite)
    no_adapt_pass_two = _run_fabric_suite(config_path=NO_ADAPT_CONFIG, suite=suite)
    with_adapt_pass_one = _run_fabric_suite(config_path=WITH_ADAPT_CONFIG, suite=suite)
    with_adapt_pass_two = _run_fabric_suite(config_path=WITH_ADAPT_CONFIG, suite=suite)
    cold_followups = {
        case_spec["case_id"]: _run_fabric_single_case(
            config_path=WITH_ADAPT_CONFIG,
            case_spec=case_spec,
        )
        for case_spec in _descriptor_opportunity_cases(suite)
    }

    baseline_summary = _summarize_flat_runs(
        suite=suite,
        pass_one=baseline_pass_one,
        pass_two=baseline_pass_two,
    )
    no_adapt_summary = _summarize_fabric_runs(
        suite=suite,
        config_path=NO_ADAPT_CONFIG,
        pass_one=no_adapt_pass_one,
        pass_two=no_adapt_pass_two,
        cold_followup_scores=None,
    )
    with_adapt_summary = _summarize_fabric_runs(
        suite=suite,
        config_path=WITH_ADAPT_CONFIG,
        pass_one=with_adapt_pass_one,
        pass_two=with_adapt_pass_two,
        cold_followup_scores={
            case_id: float(payload["case_score"])
            for case_id, payload in cold_followups.items()
        },
    )

    comparison_rows = []
    descriptor_change_cases: list[str] = []
    fabric_beats_baseline_cases: list[str] = []
    for index, case_spec in enumerate(suite["cases"]):
        baseline_case = baseline_summary["case_results"][index]
        no_adapt_case = no_adapt_summary["case_results"][index]
        with_adapt_case = with_adapt_summary["case_results"][index]
        comparison_rows.append(
            {
                "case_id": case_spec["case_id"],
                "flat_baseline_score": baseline_case["correctness_score"],
                "multi_cell_no_adapt_score": no_adapt_case["correctness_score"],
                "multi_cell_with_adapt_score": with_adapt_case["correctness_score"],
                "with_adapt_descriptor_reuse": bool(with_adapt_case["descriptor_reuse"]["used"]),
                "flat_mismatches": _truth_mismatches(result=baseline_case["result"], truth=case_spec["truth"]),
                "no_adapt_mismatches": _truth_mismatches(result=no_adapt_case["result"], truth=case_spec["truth"]),
                "with_adapt_mismatches": _truth_mismatches(result=with_adapt_case["result"], truth=case_spec["truth"]),
            }
        )
        comparison_rows[-1].update(
            _counterfactual_notes(
                case_spec=case_spec,
                baseline_case=baseline_case,
                no_adapt_case=no_adapt_case,
                with_adapt_case=with_adapt_case,
            )
        )
        if (
            max(no_adapt_case["correctness_score"], with_adapt_case["correctness_score"])
            > baseline_case["correctness_score"]
        ):
            fabric_beats_baseline_cases.append(str(case_spec["case_id"]))
        if (
            bool(case_spec.get("descriptor_opportunity"))
            and bool(with_adapt_case["descriptor_reuse"]["used"])
            and with_adapt_case["correctness_score"] > no_adapt_case["correctness_score"]
        ):
            descriptor_change_cases.append(str(case_spec["case_id"]))

    return {
        "suite_id": suite["suite_id"],
        "created_utc": utc_now_iso(),
        "classes": {
            "flat_baseline": baseline_summary,
            "multi_cell_without_bounded_adaptation": no_adapt_summary,
            "multi_cell_with_bounded_adaptation": with_adapt_summary,
        },
        "comparisons": {
            "case_rows": comparison_rows,
            "fabric_beats_baseline_cases": fabric_beats_baseline_cases,
            "descriptor_change_cases": descriptor_change_cases,
            "resource_tradeoffs": _resource_tradeoffs(
                baseline_summary=baseline_summary,
                no_adapt_summary=no_adapt_summary,
                with_adapt_summary=with_adapt_summary,
            ),
            "usefulness_gate_passed": bool(fabric_beats_baseline_cases) and bool(descriptor_change_cases),
        },
    }


def write_phase7_result_tables(results: dict[str, Any], *, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "phase7_benchmark_results.json"
    markdown_path = output_dir / "phase7_benchmark_results.md"
    artifact_results = _normalize_phase7_artifact_results(results)
    json_path.write_text(json.dumps(artifact_results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    class_rows = []
    for class_name, payload in artifact_results["classes"].items():
        resource_usage = payload["metrics"]["resource_usage"]
        split_merge = payload["metrics"]["split_merge_efficiency"]
        class_rows.append(
            "| "
            + " | ".join(
                [
                    class_name,
                    f"{payload['metrics']['task_accuracy']:.3f}",
                    f"{payload['metrics']['replay_determinism']:.3f}",
                    f"{payload['metrics']['descriptor_reuse_rate']:.3f}",
                    f"{payload['metrics']['governance_success_rate']:.3f}",
                    f"{payload['metrics']['unsafe_action_rate']:.3f}",
                ]
            )
            + " |"
        )
    resource_rows = []
    for class_name, payload in artifact_results["classes"].items():
        resource_usage = payload["metrics"]["resource_usage"]
        split_merge = payload["metrics"]["split_merge_efficiency"]
        resource_rows.append(
            "| "
            + " | ".join(
                [
                    class_name,
                    f"{payload['metrics']['active_logical_population_ratio']:.3f}",
                    str(resource_usage["estimated_runtime_memory_bytes"]),
                    str(resource_usage["retained_memory_delta_bytes"]),
                    str(resource_usage["retained_memory_delta_per_case_bytes"]),
                    f"{resource_usage['routing_decisions_per_case']:.3f}",
                    f"{resource_usage['authority_reviews_per_case']:.3f}",
                    f"{resource_usage['governance_overhead_share']:.3f}",
                    str(split_merge["structural_signal_count"]),
                ]
            )
            + " |"
        )
    case_rows = []
    for row in artifact_results["comparisons"]["case_rows"]:
        case_rows.append(
            "| "
            + " | ".join(
                [
                    row["case_id"],
                    f"{row['flat_baseline_score']:.3f}",
                    f"{row['multi_cell_no_adapt_score']:.3f}",
                    f"{row['multi_cell_with_adapt_score']:.3f}",
                    "yes" if row["with_adapt_descriptor_reuse"] else "no",
                    row["with_adapt_confidence"],
                    row["reason_summary"],
                ]
            )
            + " |"
        )
    counterfactual_rows = []
    for row in artifact_results["comparisons"]["case_rows"]:
        counterfactual_rows.append(
            "| "
            + " | ".join(
                [
                    row["case_id"],
                    row["flat_baseline_missed"],
                    row["no_adapt_improved"],
                    row["with_adapt_improved"],
                ]
            )
            + " |"
        )
    route_rows = []
    for row in artifact_results["comparisons"]["case_rows"]:
        route_rows.append(
            "| "
            + " | ".join(
                [
                    row["case_id"],
                    row["outcome_trail"],
                    row["with_adapt_route_of_custody"],
                    row["with_adapt_governance_detail"],
                ]
            )
            + " |"
        )
    descriptor_rows = []
    for row in artifact_results["comparisons"]["case_rows"]:
        if not row["with_adapt_descriptor_reuse"]:
            continue
        descriptor_rows.append(
            "| "
            + " | ".join(
                [
                    row["case_id"],
                    row["with_adapt_descriptor_detail"],
                    row["with_adapt_improved"],
                    row["with_adapt_need_resolution"],
                ]
            )
            + " |"
        )
    tradeoff_rows = []
    for row in artifact_results["comparisons"]["resource_tradeoffs"]["rows"]:
        tradeoff_rows.append(
            "| "
            + " | ".join(
                [
                    row["comparison"],
                    f"{row['accuracy_gain']:.3f}",
                    str(row["retained_memory_cost_bytes"]),
                    f"{row['accuracy_gain_per_retained_kib']:.6f}",
                    f"{row['authority_overhead_delta_per_case']:.3f}",
                ]
            )
            + " |"
        )
    structural_rows = []
    for class_name in (
        "flat_baseline",
        "multi_cell_without_bounded_adaptation",
        "multi_cell_with_bounded_adaptation",
    ):
        split_merge = artifact_results["classes"][class_name]["metrics"]["split_merge_efficiency"]
        structural_rows.append(
            "| "
            + " | ".join(
                [
                    class_name,
                    "yes" if split_merge["measured"] else "no",
                    str(split_merge["structural_signal_count"]),
                    split_merge["detail"],
                    split_merge["future_trigger"],
                ]
            )
            + " |"
        )
    tissue_rows = []
    for class_name in ("multi_cell_without_bounded_adaptation", "multi_cell_with_bounded_adaptation"):
        tissues = artifact_results["classes"][class_name]["analytics"]["tissues"]
        for tissue_id in TISSUE_ORDER:
            payload = tissues[tissue_id]
            tissue_rows.append(
                "| "
                + " | ".join(
                    [
                        class_name,
                        TISSUE_LABELS.get(tissue_id, tissue_id),
                        f"{payload['usefulness_rate']:.3f}",
                        f"{payload['workload_share']:.3f}",
                        str(payload["useful_case_count"]),
                        str(payload["stage_count"]),
                        str(payload["handoff_in_count"] + payload["handoff_out_count"]),
                        str(payload["intervention_case_count"]),
                        str(payload["anomaly_burden"]),
                        str(payload["governance_burden"]),
                        str(payload["reuse_contribution"]),
                    ]
                )
                + " |"
            )
    markdown = "\n".join(
        [
            "# Phase 7 Benchmark Results",
            "",
            "- Artifact note: runtime timestamp omitted and temp evidence paths normalized for deterministic reruns.",
            "",
            "## Class Metrics",
            "",
            "| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *class_rows,
            "",
            "## Case Comparison",
            "",
            "| Case | Flat baseline | Multi-cell no adapt | Multi-cell with adapt | Descriptor reuse mattered | With adapt confidence | Why it mattered |",
            "| --- | ---: | ---: | ---: | --- | --- | --- |",
            *case_rows,
            "",
            "## Resource And Control",
            "",
            "| Benchmark class | Active/logical ratio | Runtime bytes | Retained memory delta bytes | Retained/case bytes | Routing decisions/case | Authority reviews/case | Governance overhead share | Structural signal cases |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *resource_rows,
            "",
            "## Adaptation Tradeoffs",
            "",
            "| Comparison | Accuracy gain | Retained memory cost bytes | Accuracy gain per retained KiB | Authority overhead delta/case |",
            "| --- | ---: | ---: | ---: | ---: |",
            *tradeoff_rows,
            "",
            "## Counterfactual Notes",
            "",
            "| Case | Flat baseline missed | No adapt improved | With adapt improved |",
            "| --- | --- | --- | --- |",
            *counterfactual_rows,
            "",
            "## Route Of Custody",
            "",
            "| Case | Outcome trail | With adapt tissue custody | Governance detail |",
            "| --- | --- | --- | --- |",
            *route_rows,
            "",
            "## Descriptor Reuse Evidence",
            "",
            "| Case | Descriptor and retained state | Prevented errors or lifts | Need resolution trail |",
            "| --- | --- | --- | --- |",
            *(descriptor_rows or ["| none | none | none | none |"]),
            "",
            "## Structural Pressure",
            "",
            "| Benchmark class | Measured split/merge | Structural signal cases | Why no action or what was measured | Future trigger |",
            "| --- | --- | ---: | --- | --- |",
            *structural_rows,
            "",
            "## Tissue Analytics",
            "",
            "| Benchmark class | Tissue | Usefulness | Workload share | Useful cases | Stage workload | Handoffs | Intervention cases | Anomaly burden | Governance burden | Reuse contribution |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *tissue_rows,
            "",
            f"- Fabric beats baseline cases: `{', '.join(artifact_results['comparisons']['fabric_beats_baseline_cases'])}`",
            f"- Descriptor-change cases: `{', '.join(artifact_results['comparisons']['descriptor_change_cases'])}`",
        ]
    )
    markdown_path.write_text(markdown + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _normalize_phase7_artifact_results(results: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(results)
    normalized.pop("created_utc", None)
    for payload in normalized.get("classes", {}).values():
        status_refs = payload.get("status_refs")
        if not isinstance(status_refs, dict):
            continue
        evidence_path = status_refs.get("evidence_path")
        if evidence_path:
            status_refs["evidence_path"] = _normalize_phase7_ephemeral_path(evidence_path)
    return normalized


def _normalize_phase7_ephemeral_path(path_value: Any) -> str:
    basename = Path(str(path_value)).name or "phase7_evidence.json"
    return f"<temporary>/{basename}"


def _load_suite() -> dict[str, Any]:
    payload = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    payload["cases"] = [
        {
            **case_spec,
            "payload": json.loads((SUITE_PATH.parent / case_spec["payload_path"]).read_text(encoding="utf-8")),
        }
        for case_spec in payload["cases"]
    ]
    return payload


def _descriptor_opportunity_cases(suite: dict[str, Any]) -> list[dict[str, Any]]:
    matches = [case_spec for case_spec in suite["cases"] if bool(case_spec.get("descriptor_opportunity"))]
    if not matches:
        raise RuntimeError("Phase 7 suite is missing a descriptor opportunity case.")
    return matches


def _run_flat_suite(suite: dict[str, Any]) -> dict[str, Any]:
    case_results = []
    digests = []
    for case_spec in suite["cases"]:
        execution = run_flat_baseline_workflow(
            workflow_payload=case_spec["payload"],
            proof_domain="document/workflow intelligence",
        )
        result = execution["result"]
        score = _score_result(result=result, truth=case_spec["truth"])
        case_results.append(
            {
                "case_id": case_spec["case_id"],
                "result": result,
                "correctness_score": score,
                "output_digest": execution["output_digest"],
                "descriptor_reuse": deepcopy(result["descriptor_reuse"]),
            }
        )
        digests.append(str(execution["output_digest"]))
    forgetting_probe = run_flat_baseline_workflow(
        workflow_payload=suite["cases"][0]["payload"],
        proof_domain="document/workflow intelligence",
    )
    forgetting_score = _score_result(result=forgetting_probe["result"], truth=suite["cases"][0]["truth"])
    return {
        "case_results": case_results,
        "digests": digests,
        "forgetting_probe_score": forgetting_score,
    }


def _run_fabric_suite(*, config_path: Path, suite: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        state_root = Path(tempdir) / "runtime_state"
        env = os.environ.copy()
        env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)
        _run_cli(env=env, args=["fabric", "init", str(config_path)])
        initial_context = _load_runtime_context(config_path=config_path, state_root=state_root)
        initial_population = initial_context["lifecycle"].summary()
        initial_memory_summary = initial_context["memory"].summary()
        initial_need_summary = initial_context["need_manager"].summary()
        initial_authority_summary = initial_context["authority_engine"].summary()
        initial_routing_summary = initial_context["routing_engine"].summary()
        case_results = []
        digests = []
        for case_spec in suite["cases"]:
            payload = _run_cli(
                env=env,
                args=["fabric", "run"],
                stdin_text=json.dumps(case_spec["payload"]),
            )
            result = payload["data"]["result"]
            score = _score_result(result=result, truth=case_spec["truth"])
            workspace_path = _resolve_workspace_path(payload["data"]["workspace_ref"])
            case_results.append(
                {
                    "case_id": case_spec["case_id"],
                    "result": result,
                    "correctness_score": score,
                    "output_digest": str(payload["data"]["output_digest"]),
                    "descriptor_reuse": deepcopy(result["descriptor_reuse"]),
                    "trace": deepcopy(payload["data"]["trace"]),
                    "workspace": json.loads(workspace_path.read_text(encoding="utf-8")),
                }
            )
            digests.append(str(payload["data"]["output_digest"]))
        forgetting_probe_payload = _run_cli(
            env=env,
            args=["fabric", "run"],
            stdin_text=json.dumps(suite["cases"][0]["payload"]),
        )
        forgetting_probe_score = _score_result(
            result=forgetting_probe_payload["data"]["result"],
            truth=suite["cases"][0]["truth"],
        )
        context = _load_runtime_context(config_path=config_path, state_root=state_root)
        lifecycle = context["lifecycle"]
        memory = context["memory"]
        need_manager = context["need_manager"]
        authority = context["authority_engine"]
        routing = context["routing_engine"]
        status_payload = _run_cli(env=env, args=["fabric", "status"])
        evidence_path = Path(tempdir) / "phase7_evidence.json"
        _run_cli(env=env, args=["fabric", "evidence", str(evidence_path)])
        return {
            "case_results": case_results,
            "digests": digests,
            "forgetting_probe_score": forgetting_probe_score,
            "status": status_payload["data"],
            "initial_population": initial_population,
            "initial_memory_summary": initial_memory_summary,
            "initial_need_summary": initial_need_summary,
            "initial_authority_summary": initial_authority_summary,
            "initial_routing_summary": initial_routing_summary,
            "population": lifecycle.summary(),
            "memory_summary": memory.summary(),
            "promoted_memories": memory.load_promoted_memories(),
            "need_summary": need_manager.summary(),
            "authority_summary": authority.summary(),
            "authority_reviews": authority.load_reviews(),
            "routing_summary": routing.summary(),
            "evidence_path": evidence_path,
        }


def _run_fabric_single_case(*, config_path: Path, case_spec: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        state_root = Path(tempdir) / "runtime_state"
        env = os.environ.copy()
        env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)
        _run_cli(env=env, args=["fabric", "init", str(config_path)])
        payload = _run_cli(
            env=env,
            args=["fabric", "run"],
            stdin_text=json.dumps(case_spec["payload"]),
        )
        return {
            "case_score": _score_result(result=payload["data"]["result"], truth=case_spec["truth"]),
            "output_digest": str(payload["data"]["output_digest"]),
        }


def _enrich_fabric_case_results(
    *,
    case_results: list[dict[str, Any]],
    suite_cases: list[dict[str, Any]],
    promoted_memories: dict[str, Any],
    authority_reviews: list[dict[str, Any]],
    need_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    promoted_index = _index_promoted_memories(promoted_memories)
    review_index = {str(item["review_id"]): deepcopy(item) for item in authority_reviews}
    resolution_outcomes = {
        str(key): deepcopy(value)
        for key, value in dict(need_summary.get("resolution_outcomes", {})).items()
    }
    enriched: list[dict[str, Any]] = []
    for case_result, case_spec in zip(case_results, suite_cases):
        enriched.append(
            {
                **case_result,
                "analysis": _build_fabric_case_analysis(
                    case_result=case_result,
                    case_spec=case_spec,
                    promoted_index=promoted_index,
                    review_index=review_index,
                    resolution_outcomes=resolution_outcomes,
                ),
            }
        )
    return enriched


def _index_promoted_memories(promoted_memories: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for bucket_name in ("active", "archived"):
        bucket = dict(promoted_memories.get(bucket_name, {}))
        for memory_id, record in bucket.items():
            materialized = deepcopy(record)
            materialized["bucket"] = bucket_name
            index[str(materialized.get("memory_id", memory_id))] = materialized
    return index


def _build_fabric_case_analysis(
    *,
    case_result: dict[str, Any],
    case_spec: dict[str, Any],
    promoted_index: dict[str, dict[str, Any]],
    review_index: dict[str, dict[str, Any]],
    resolution_outcomes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    workspace = dict(case_result.get("workspace", {}))
    stage_outputs = dict(workspace.get("stage_outputs", {}))
    stage_history = list(workspace.get("stage_history", []))
    handoffs = list(workspace.get("handoffs", []))
    extraction = dict(stage_outputs.get("extraction", {}))
    correction = dict(stage_outputs.get("correction", {}))
    anomaly = dict(stage_outputs.get("anomaly_review", {}))
    governance = dict(stage_outputs.get("governance_review", {}))
    reporting = dict(stage_outputs.get("reporting", {}))
    descriptor_reuse = dict(correction.get("descriptor_reuse", {}))
    memory_record = None
    memory_id = descriptor_reuse.get("memory_id")
    if memory_id is not None:
        memory_record = promoted_index.get(str(memory_id))
    correction_reviews = _review_summaries(
        review_ids=list(correction.get("authority_review_ids", [])),
        review_index=review_index,
    )
    governance_reviews = _review_summaries(
        review_ids=list(governance.get("authority_review_ids", [])),
        review_index=review_index,
    )
    confidence = _confidence_analysis(
        result=case_result["result"],
        case_spec=case_spec,
        extraction=extraction,
        correction=correction,
        anomaly=anomaly,
        governance=governance,
        workspace_ok=bool(stage_outputs.get("workspace_guard", {}).get("workspace_ok", True)),
    )
    route_of_custody = _route_of_custody_analysis(
        result=case_result["result"],
        stage_history=stage_history,
        handoffs=handoffs,
        extraction=extraction,
        correction=correction,
        anomaly=anomaly,
        governance=governance,
        reporting=reporting,
        correction_reviews=correction_reviews,
        governance_reviews=governance_reviews,
    )
    descriptor_detail = _descriptor_reuse_analysis(
        extraction=extraction,
        correction=correction,
        descriptor_reuse=descriptor_reuse,
        memory_record=memory_record,
        correction_reviews=correction_reviews,
    )
    need_resolution = _need_resolution_analysis(
        workflow_id=str(workspace.get("workflow_id", "")),
        resolution_outcomes=resolution_outcomes,
    )
    return {
        "route_of_custody": route_of_custody,
        "confidence": confidence,
        "descriptor_reuse_detail": descriptor_detail,
        "governance_control": {
            "action": str(governance.get("governance_action", case_result["result"].get("governance_action", ""))),
            "authority_review_ids": list(governance.get("authority_review_ids", [])),
            "summary": _governance_summary(
                governance=governance,
                governance_reviews=governance_reviews,
            ),
        },
        "need_resolution": need_resolution,
    }


def _review_summaries(
    *,
    review_ids: list[str],
    review_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for review_id in review_ids:
        review = review_index.get(str(review_id))
        if review is None:
            continue
        summaries.append(
            {
                "review_id": str(review["review_id"]),
                "action": str(review.get("action", "")),
                "decision": str(review.get("decision", "")),
                "trust_band": str(review.get("trust_state", {}).get("trust_band", "unknown")),
                "notes": list(review.get("decision_notes", [])),
            }
        )
    return summaries


def _confidence_analysis(
    *,
    result: dict[str, Any],
    case_spec: dict[str, Any],
    extraction: dict[str, Any],
    correction: dict[str, Any],
    anomaly: dict[str, Any],
    governance: dict[str, Any],
    workspace_ok: bool,
) -> dict[str, Any]:
    extraction_confidence = float(extraction.get("extraction_confidence", 0.0))
    missing_fields = [str(item) for item in extraction.get("missing_fields", [])]
    anomalies = [str(item) for item in anomaly.get("anomalies", [])]
    descriptor_used = bool(correction.get("descriptor_reuse", {}).get("used"))
    support_reasons: list[str] = []
    drag_reasons: list[str] = []
    if extraction_confidence >= 0.85:
        support_reasons.append("extraction tissue had high OCR support")
    elif extraction_confidence >= 0.6:
        support_reasons.append("extraction tissue had bounded but usable OCR support")
    else:
        drag_reasons.append("extraction tissue started from low OCR support")
    if missing_fields:
        drag_reasons.append("extraction left gaps in " + ", ".join(missing_fields))
    if descriptor_used:
        support_reasons.append("validation/correction reused reviewed prior descriptor state")
    elif correction.get("correction_notes"):
        support_reasons.append("validation/correction repaired bounded field gaps")
    if anomalies:
        drag_reasons.append("anomaly/reviewer raised " + ", ".join(anomalies))
    else:
        support_reasons.append("anomaly/reviewer cleared the document")
    governance_action = str(governance.get("governance_action", result.get("governance_action", "")))
    final_status = str(governance.get("final_status", result.get("final_status", "")))
    if final_status == "hold" and anomalies:
        support_reasons.append("workspace/governance kept release on hold under anomaly pressure")
    elif governance_action == "approved_release" and not anomalies:
        support_reasons.append("workspace/governance released after clear reviewer state")
    if not workspace_ok:
        drag_reasons.append("workspace/governance saw incomplete custody state")
    base_score = 0.25 + (0.45 * extraction_confidence)
    if descriptor_used:
        base_score += 0.18
    if workspace_ok:
        base_score += 0.08
    if final_status == "accepted" and not anomalies:
        base_score += 0.12
    if final_status == "hold" and anomalies:
        base_score += 0.12
    base_score -= 0.07 * len(missing_fields)
    base_score -= 0.06 * len(anomalies)
    score = max(0.05, min(0.99, round(base_score, 6)))
    if score >= 0.8:
        label = "high"
    elif score >= 0.6:
        label = "guarded"
    else:
        label = "fragile"
    return {
        "outcome_state": {
            "final_status": str(result.get("final_status", "")),
            "reviewer_status": str(result.get("reviewer_status", "")),
            "governance_action": str(result.get("governance_action", "")),
        },
        "score": score,
        "label": label,
        "support_reasons": support_reasons,
        "drag_reasons": drag_reasons,
        "summary": (
            f"{label} confidence ({score:.3f}) with outcome "
            f"{result.get('final_status')}/{result.get('reviewer_status')}"
        ),
        "truth_match": {
            "final_status": str(result.get("final_status", "")) == str(case_spec["truth"]["final_status"]),
            "governance_action": str(result.get("governance_action", "")) == str(case_spec["expected_governance"]),
        },
    }


def _route_of_custody_analysis(
    *,
    result: dict[str, Any],
    stage_history: list[dict[str, Any]],
    handoffs: list[dict[str, Any]],
    extraction: dict[str, Any],
    correction: dict[str, Any],
    anomaly: dict[str, Any],
    governance: dict[str, Any],
    reporting: dict[str, Any],
    correction_reviews: list[dict[str, Any]],
    governance_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    tissue_sequence: list[str] = []
    for entry in stage_history:
        tissue_label = TISSUE_LABELS.get(str(entry.get("tissue_id", "")), str(entry.get("tissue_id", "")))
        if not tissue_sequence or tissue_sequence[-1] != tissue_label:
            tissue_sequence.append(tissue_label)
    descriptor_reuse = dict(correction.get("descriptor_reuse", {}))
    critical_steps = [
        "intake/routing classified vendor_invoice and selected invoice_extraction",
        "extraction captured "
        + (
            "complete invoice fields"
            if not extraction.get("missing_fields")
            else "bounded gaps: " + ", ".join(str(item) for item in extraction.get("missing_fields", []))
        ),
        "validation/correction "
        + (
            f"reused {descriptor_reuse.get('descriptor_id')} after authority "
            f"{correction_reviews[0]['review_id']}"
            if descriptor_reuse.get("used") and correction_reviews
            else (
                "reused prior reviewed descriptor state"
                if descriptor_reuse.get("used")
                else "stayed local to current document state"
            )
        ),
        "anomaly/reviewer "
        + (
            "flagged " + ", ".join(str(item) for item in anomaly.get("anomalies", []))
            if anomaly.get("anomalies")
            else "cleared the document"
        ),
        "workspace/governance "
        + (
            f"{governance.get('governance_action')} via {governance_reviews[0]['review_id']}"
            if governance_reviews
            else str(governance.get("governance_action", "approved_release"))
        ),
        "reporting/output wrote bounded summary and final status "
        + str(result.get("final_status", "")),
    ]
    return {
        "tissue_sequence": tissue_sequence,
        "handoff_count": len(handoffs),
        "critical_steps": critical_steps,
        "summary": " -> ".join(tissue_sequence) + f"; handoffs={len(handoffs)}",
        "reporting_notes": list(reporting.get("custody_notes", [])),
    }


def _descriptor_reuse_analysis(
    *,
    extraction: dict[str, Any],
    correction: dict[str, Any],
    descriptor_reuse: dict[str, Any],
    memory_record: dict[str, Any] | None,
    correction_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    used = bool(descriptor_reuse.get("used"))
    raw_fields = dict(extraction.get("extracted_fields", {}))
    corrected_fields = dict(correction.get("normalized_fields", {}))
    restored_fields: list[str] = []
    if str(raw_fields.get("vendor_name", "")) != str(corrected_fields.get("vendor_name", "")):
        restored_fields.append("normalized_vendor")
    if str(raw_fields.get("currency", "")) != str(corrected_fields.get("currency", "")):
        restored_fields.append("normalized_currency")
    if str(raw_fields.get("due_date", "")) != str(corrected_fields.get("due_date", "")):
        restored_fields.append("derived_due_date")
    if not used:
        if descriptor_reuse.get("eligible"):
            summary = "descriptor candidate existed but was not reused"
        else:
            summary = "no reviewed descriptor artifact was available"
        return {
            "used": False,
            "summary": summary,
            "restored_fields": restored_fields,
        }
    summary_parts = [
        f"{descriptor_reuse.get('descriptor_id')} from {descriptor_reuse.get('memory_id')}",
    ]
    if memory_record is not None:
        summary_parts.append(
            f"{memory_record.get('retention_tier')} tier, {int(memory_record.get('payload_bytes', 0))} bytes"
        )
        summary_parts.append(
            f"reuse_count={int(memory_record.get('reuse_count', 0))}, trust={float(memory_record.get('trust_score', 0.0)):.2f}"
        )
    if correction_reviews:
        summary_parts.append(f"approved by {correction_reviews[0]['review_id']}")
    if restored_fields:
        summary_parts.append("restored " + ", ".join(restored_fields))
    return {
        "used": True,
        "descriptor_id": str(descriptor_reuse.get("descriptor_id")),
        "memory_id": str(descriptor_reuse.get("memory_id")),
        "memory_class": None if memory_record is None else str(memory_record.get("memory_class")),
        "retention_tier": None if memory_record is None else str(memory_record.get("retention_tier")),
        "payload_bytes": 0 if memory_record is None else int(memory_record.get("payload_bytes", 0)),
        "reuse_count": 0 if memory_record is None else int(memory_record.get("reuse_count", 0)),
        "trust_score": 0.0 if memory_record is None else float(memory_record.get("trust_score", 0.0)),
        "review_count": 0 if memory_record is None else int(memory_record.get("review_count", 0)),
        "restored_fields": restored_fields,
        "summary": "; ".join(summary_parts),
    }


def _governance_summary(
    *,
    governance: dict[str, Any],
    governance_reviews: list[dict[str, Any]],
) -> str:
    action = str(governance.get("governance_action", "approved_release"))
    if not governance_reviews:
        if action == "approved_release":
            return "bounded release completed without extra authority review"
        return f"{action} without stored authority review detail"
    review = governance_reviews[0]
    return (
        f"{action} via {review['review_id']} "
        f"({review['decision']}, trust_band={review['trust_band']})"
    )


def _need_resolution_analysis(
    *,
    workflow_id: str,
    resolution_outcomes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    matches = [
        deepcopy(value)
        for value in resolution_outcomes.values()
        if str(value.get("need_signal_id", "")).startswith(f"{workflow_id}:")
    ]
    matches.sort(key=lambda item: str(item.get("need_signal_id", "")))
    summaries = [
        f"{item.get('signal_kind')} -> {item.get('resolution_ref')} ({item.get('resolution_quality')})"
        for item in matches
    ]
    return {
        "count": len(matches),
        "summaries": summaries,
        "summary": "none" if not summaries else "; ".join(summaries),
    }


def _summarize_flat_runs(
    *,
    suite: dict[str, Any],
    pass_one: dict[str, Any],
    pass_two: dict[str, Any],
) -> dict[str, Any]:
    case_results = pass_one["case_results"]
    scores = [float(item["correctness_score"]) for item in case_results]
    replay_determinism = _digest_match_rate(pass_one["digests"], pass_two["digests"])
    unsafe_rate = _unsafe_rate(case_results, suite["cases"])
    governance_rate = _governance_success_rate(case_results, suite["cases"])
    return {
        "case_results": case_results,
        "metrics": {
            "task_accuracy": _average(scores),
            "replay_determinism": replay_determinism,
            "descriptor_reuse_rate": 0.0,
            "improvement_from_prior_descriptors": 0.0,
            "memory_density_gain": 0.0,
            "active_logical_population_ratio": 0.0,
            "split_merge_efficiency": {
                "measured": False,
                "value": 0.0,
                "detail": "flat baseline has no split or merge path",
                "structural_signal_count": 0,
                "structural_signal_cases": [],
                "candidate_tissues": [],
                "pressure_ratio": 0.0,
                "no_action_reason": "flat baseline has no lifecycle-managed population to split or merge",
                "future_trigger": "not applicable until the benchmark uses a governed fabric population",
            },
            "governance_success_rate": governance_rate,
            "resource_usage": {
                "estimated_runtime_memory_bytes": 0,
                "estimated_idle_memory_bytes": 0,
                "memory_tier_usage_bytes": {"hot": 0, "warm": 0, "cold": 0, "ephemeral": 0},
                "memory_tier_delta_bytes": {"hot": 0, "warm": 0, "cold": 0, "ephemeral": 0},
                "retained_memory_delta_bytes": 0,
                "retained_memory_delta_per_case_bytes": 0.0,
                "active_population": 0,
                "logical_population": 0,
                "active_population_cost_bytes": 0.0,
                "retained_memory_value_density": 0.0,
                "within_runtime_working_set_cap": True,
                "memory_within_caps": {"hot": True, "warm": True, "cold": True, "ephemeral": True},
                "routing_decision_count": 0,
                "routing_decisions_per_case": 0.0,
                "authority_review_count": 0,
                "authority_reviews_per_case": 0.0,
                "governance_overhead_share": 0.0,
                "need_signal_count": 0,
                "need_signals_per_case": 0.0,
                "average_need_effectiveness": 0.0,
                "runtime_memory_delta_bytes": 0,
            },
            "bounded_forgetting": 0.0,
            "unsafe_action_rate": unsafe_rate,
        },
        "analytics": {"tissues": {}},
    }


def _summarize_fabric_runs(
    *,
    suite: dict[str, Any],
    config_path: Path,
    pass_one: dict[str, Any],
    pass_two: dict[str, Any],
    cold_followup_scores: dict[str, float] | None,
) -> dict[str, Any]:
    case_results = pass_one["case_results"]
    scores = [float(item["correctness_score"]) for item in case_results]
    eligible_cases = [
        item for item in case_results if bool(item["descriptor_reuse"]["eligible"])
    ]
    used_cases = [item for item in eligible_cases if bool(item["descriptor_reuse"]["used"])]
    forgetting_loss = max(0.0, case_results[0]["correctness_score"] - pass_one["forgetting_probe_score"])
    population = pass_one["population"]
    memory_summary = pass_one["memory_summary"]
    structural = population.get("structural_usefulness", {})
    split_merge_events = int(structural.get("split_useful_count", 0)) + int(structural.get("merge_useful_count", 0))
    cold_followup_scores = dict(cold_followup_scores or {})
    descriptor_gain_samples = [
        float(item["correctness_score"]) - float(cold_followup_scores[item["case_id"]])
        for item in eligible_cases
        if item["case_id"] in cold_followup_scores
    ]
    split_merge_signal = _split_merge_signal(
        case_results=case_results,
        split_merge_events=split_merge_events,
        population=population,
        authority_summary=pass_one["authority_summary"],
    )
    case_results = _enrich_fabric_case_results(
        case_results=case_results,
        suite_cases=suite["cases"],
        promoted_memories=pass_one["promoted_memories"],
        authority_reviews=pass_one["authority_reviews"],
        need_summary=pass_one["need_summary"],
    )
    return {
        "case_results": case_results,
        "metrics": {
            "task_accuracy": _average(scores),
            "replay_determinism": _digest_match_rate(pass_one["digests"], pass_two["digests"]),
            "descriptor_reuse_rate": 0.0
            if len(eligible_cases) == 0
            else round(len(used_cases) / float(len(eligible_cases)), 6),
            "improvement_from_prior_descriptors": 0.0
            if len(descriptor_gain_samples) == 0
            else round(sum(descriptor_gain_samples) / float(len(descriptor_gain_samples)), 6),
            "memory_density_gain": round(
                sum(scores)
                / float(
                    max(
                        1,
                        int(memory_summary["tier_usage_bytes"]["warm"]) + int(memory_summary["tier_usage_bytes"]["cold"]),
                    )
                ),
                9,
            ),
            "active_logical_population_ratio": float(population.get("active_to_logical_ratio", 0.0)),
            "split_merge_efficiency": split_merge_signal,
            "governance_success_rate": _governance_success_rate(case_results, suite["cases"]),
            "resource_usage": _resource_usage(
                population=population,
                initial_population=pass_one["initial_population"],
                memory_summary=memory_summary,
                initial_memory_summary=pass_one["initial_memory_summary"],
                routing_summary=pass_one["routing_summary"],
                initial_routing_summary=pass_one["initial_routing_summary"],
                authority_summary=pass_one["authority_summary"],
                initial_authority_summary=pass_one["initial_authority_summary"],
                need_summary=pass_one["need_summary"],
                initial_need_summary=pass_one["initial_need_summary"],
                case_count=len(case_results),
            ),
            "bounded_forgetting": round(forgetting_loss, 6),
            "unsafe_action_rate": _unsafe_rate(case_results, suite["cases"]),
        },
        "analytics": {
            "tissues": _tissue_analytics(case_results=case_results, suite_cases=suite["cases"]),
        },
        "status_refs": {
            "config_path": repo_relative(config_path),
            "evidence_path": str(pass_one["evidence_path"]),
        },
    }


def _governance_success_rate(case_results: list[dict[str, Any]], suite_cases: list[dict[str, Any]]) -> float:
    matches = 0
    for result_item, case_spec in zip(case_results, suite_cases):
        if str(result_item["result"].get("governance_action")) == str(case_spec["expected_governance"]):
            matches += 1
    return round(matches / float(len(case_results)), 6)


def _unsafe_rate(case_results: list[dict[str, Any]], suite_cases: list[dict[str, Any]]) -> float:
    unsafe = 0
    for result_item, case_spec in zip(case_results, suite_cases):
        truth_final = str(case_spec["truth"]["final_status"])
        observed_final = str(result_item["result"].get("final_status"))
        if truth_final == "hold" and observed_final == "accepted":
            unsafe += 1
    return round(unsafe / float(len(case_results)), 6)


def _score_result(*, result: dict[str, Any], truth: dict[str, Any]) -> float:
    matched = 0
    for field_name, truth_value in truth.items():
        if str(result.get(field_name, "")) == str(truth_value):
            matched += 1
    return round(matched / float(len(truth)), 6)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / float(len(values)), 6)


def _digest_match_rate(left: list[str], right: list[str]) -> float:
    if len(left) != len(right) or len(left) == 0:
        return 0.0
    matches = len([1 for l_item, r_item in zip(left, right) if str(l_item) == str(r_item)])
    return round(matches / float(len(left)), 6)


def _load_runtime_context(*, config_path: Path, state_root: Path) -> dict[str, Any]:
    config, _, registry, _ = load_fabric_bootstrap(config_path)
    store = FabricStateStore(state_root)
    state = store.load_current_state()
    if state is None:
        raise RuntimeError("Fabric state was not initialized.")
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


def _run_cli(
    *,
    env: dict[str, str],
    args: list[str],
    stdin_text: str | None = None,
) -> dict[str, Any]:
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


def deepcopy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _resolve_workspace_path(workspace_ref: str) -> Path:
    path = Path(str(workspace_ref))
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _truth_mismatches(*, result: dict[str, Any], truth: dict[str, Any]) -> list[str]:
    return sorted(
        field_name
        for field_name, truth_value in truth.items()
        if str(result.get(field_name, "")) != str(truth_value)
    )


def _counterfactual_notes(
    *,
    case_spec: dict[str, Any],
    baseline_case: dict[str, Any],
    no_adapt_case: dict[str, Any],
    with_adapt_case: dict[str, Any],
) -> dict[str, str]:
    flat_mismatches = _truth_mismatches(result=baseline_case["result"], truth=case_spec["truth"])
    no_adapt_mismatches = _truth_mismatches(result=no_adapt_case["result"], truth=case_spec["truth"])
    with_adapt_mismatches = _truth_mismatches(result=with_adapt_case["result"], truth=case_spec["truth"])
    no_adapt_analysis = dict(no_adapt_case.get("analysis", {}))
    with_adapt_analysis = dict(with_adapt_case.get("analysis", {}))
    with_adapt_descriptor = dict(with_adapt_analysis.get("descriptor_reuse_detail", {}))
    with_adapt_confidence = dict(with_adapt_analysis.get("confidence", {}))
    reason_parts: list[str] = []
    if no_adapt_case["correctness_score"] > baseline_case["correctness_score"]:
        if str(case_spec["truth"]["final_status"]) == "hold":
            reason_parts.append("real tissues kept the document on hold instead of flat auto-release")
        else:
            reason_parts.append("real tissues preserved a safer bounded path than the flat baseline")
    if (
        bool(with_adapt_case["descriptor_reuse"]["used"])
        and with_adapt_case["correctness_score"] > no_adapt_case["correctness_score"]
    ):
        reason_parts.append(
            "reviewed descriptor reuse restored bounded context from prior memory: "
            + with_adapt_descriptor.get("summary", "descriptor-backed correction")
        )
    elif bool(with_adapt_case["descriptor_reuse"]["used"]):
        reason_parts.append("descriptor reuse improved document state without overriding governance")
    if (
        str(with_adapt_case["result"].get("final_status")) == "hold"
        and bool(with_adapt_case["descriptor_reuse"]["used"])
    ):
        reason_parts.append("governance stayed active after correction instead of silently auto-releasing")
    if not reason_parts:
        reason_parts.append("all classes behaved the same on this case")
    return {
        "flat_baseline_missed": "none" if not flat_mismatches else ", ".join(flat_mismatches),
        "no_adapt_improved": _improvement_note(
            improved_case=no_adapt_case,
            prior_case=baseline_case,
            prior_mismatches=flat_mismatches,
        ),
        "with_adapt_improved": _improvement_note(
            improved_case=with_adapt_case,
            prior_case=no_adapt_case,
            prior_mismatches=no_adapt_mismatches,
        ),
        "reason_summary": "; ".join(reason_parts),
        "with_adapt_residual_mismatches": "none" if not with_adapt_mismatches else ", ".join(with_adapt_mismatches),
        "outcome_trail": "; ".join(
            [
                f"flat={baseline_case['result'].get('final_status')}/{baseline_case['result'].get('reviewer_status')}",
                f"no_adapt={no_adapt_case['result'].get('final_status')}/{no_adapt_case['result'].get('reviewer_status')}",
                f"with_adapt={with_adapt_case['result'].get('final_status')}/{with_adapt_case['result'].get('reviewer_status')}",
            ]
        ),
        "with_adapt_confidence": str(with_adapt_confidence.get("summary", "n/a")),
        "with_adapt_route_of_custody": str(
            dict(with_adapt_analysis.get("route_of_custody", {})).get("summary", "n/a")
        ),
        "with_adapt_descriptor_detail": str(with_adapt_descriptor.get("summary", "none")),
        "with_adapt_governance_detail": str(
            dict(with_adapt_analysis.get("governance_control", {})).get("summary", "n/a")
        ),
        "with_adapt_need_resolution": str(
            dict(with_adapt_analysis.get("need_resolution", {})).get("summary", "none")
        ),
        "with_adapt_support_reasons": "; ".join(with_adapt_confidence.get("support_reasons", [])),
        "with_adapt_drag_reasons": "; ".join(with_adapt_confidence.get("drag_reasons", [])),
        "no_adapt_route_of_custody": str(
            dict(no_adapt_analysis.get("route_of_custody", {})).get("summary", "n/a")
        ),
    }


def _improvement_note(
    *,
    improved_case: dict[str, Any],
    prior_case: dict[str, Any],
    prior_mismatches: list[str],
) -> str:
    if float(improved_case["correctness_score"]) <= float(prior_case["correctness_score"]):
        return "no material improvement"
    improved_fields = sorted(
        field_name
        for field_name in prior_mismatches
        if str(improved_case["result"].get(field_name, "")) != str(prior_case["result"].get(field_name, ""))
    )
    return "improved " + ", ".join(improved_fields or ["bounded workflow outcome"])


def _resource_usage(
    *,
    population: dict[str, Any],
    initial_population: dict[str, Any],
    memory_summary: dict[str, Any],
    initial_memory_summary: dict[str, Any],
    routing_summary: dict[str, Any],
    initial_routing_summary: dict[str, Any],
    authority_summary: dict[str, Any],
    initial_authority_summary: dict[str, Any],
    need_summary: dict[str, Any],
    initial_need_summary: dict[str, Any],
    case_count: int,
) -> dict[str, Any]:
    tier_delta_bytes = {
        tier: int(memory_summary["tier_usage_bytes"].get(tier, 0)) - int(initial_memory_summary["tier_usage_bytes"].get(tier, 0))
        for tier in ("hot", "warm", "cold", "ephemeral")
    }
    active_population = int(population.get("active_population", 0))
    routing_decisions = int(routing_summary.get("decision_count", 0)) - int(initial_routing_summary.get("decision_count", 0))
    authority_reviews = int(authority_summary.get("review_count", 0)) - int(initial_authority_summary.get("review_count", 0))
    need_signals = int(need_summary.get("signal_count", 0)) - int(initial_need_summary.get("signal_count", 0))
    retained_delta = int(tier_delta_bytes["warm"]) + int(tier_delta_bytes["cold"])
    return {
        "estimated_runtime_memory_bytes": int(population.get("estimated_runtime_memory_bytes", 0)),
        "estimated_idle_memory_bytes": int(population.get("estimated_idle_memory_bytes", 0)),
        "memory_tier_usage_bytes": deepcopy(memory_summary["tier_usage_bytes"]),
        "memory_tier_delta_bytes": tier_delta_bytes,
        "retained_memory_delta_bytes": retained_delta,
        "retained_memory_delta_per_case_bytes": round(retained_delta / float(max(1, case_count)), 3),
        "active_population": active_population,
        "logical_population": int(population.get("logical_population", 0)),
        "active_population_cost_bytes": 0.0
        if active_population == 0
        else round(float(population.get("estimated_runtime_memory_bytes", 0)) / float(active_population), 3),
        "retained_memory_value_density": 0.0
        if retained_delta <= 0
        else round(
            float(population.get("active_to_logical_ratio", 0.0))
            / float(max(1, retained_delta)),
            9,
        ),
        "within_runtime_working_set_cap": bool(population.get("within_runtime_working_set_cap", False)),
        "memory_within_caps": deepcopy(memory_summary["within_caps"]),
        "routing_decision_count": routing_decisions,
        "routing_decisions_per_case": round(routing_decisions / float(max(1, case_count)), 6),
        "authority_review_count": authority_reviews,
        "authority_reviews_per_case": round(authority_reviews / float(max(1, case_count)), 6),
        "governance_overhead_share": 0.0
        if routing_decisions == 0
        else round(authority_reviews / float(max(1, routing_decisions)), 6),
        "need_signal_count": need_signals,
        "need_signals_per_case": round(need_signals / float(max(1, case_count)), 6),
        "average_need_effectiveness": float(need_summary.get("average_effectiveness_score", 0.0)),
        "runtime_memory_delta_bytes": int(population.get("estimated_runtime_memory_bytes", 0))
        - int(initial_population.get("estimated_runtime_memory_bytes", 0)),
    }


def _tissue_analytics(
    *,
    case_results: list[dict[str, Any]],
    suite_cases: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {
        tissue_id: {
            "case_count": 0,
            "stage_count": 0,
            "handoff_in_count": 0,
            "handoff_out_count": 0,
            "usefulness_total": 0.0,
            "useful_case_count": 0,
            "intervention_case_count": 0,
            "anomaly_burden": 0,
            "governance_burden": 0,
            "reuse_contribution": 0,
        }
        for tissue_id in TISSUE_ORDER
    }
    total_stage_count = 0
    for case_result, case_spec in zip(case_results, suite_cases):
        workspace = case_result.get("workspace", {})
        result = case_result["result"]
        stage_history = list(workspace.get("stage_history", []))
        handoffs = list(workspace.get("handoffs", []))
        stage_outputs = dict(workspace.get("stage_outputs", {}))
        total_stage_count += len(stage_history)
        tissues_used = set(workspace.get("tissues_used", []))
        for tissue_id in tissues_used:
            bucket = buckets[tissue_id]
            bucket["case_count"] += 1
            linked_fields = TISSUE_TRUTH_FIELDS.get(tissue_id, [])
            usefulness = _field_accuracy(result=result, truth=case_spec["truth"], fields=linked_fields)
            bucket["usefulness_total"] += usefulness
            if usefulness >= 1.0:
                bucket["useful_case_count"] += 1
        for stage in stage_history:
            bucket = buckets[str(stage["tissue_id"])]
            bucket["stage_count"] += 1
        for handoff in handoffs:
            buckets[str(handoff["from_tissue"])]["handoff_out_count"] += 1
            buckets[str(handoff["to_tissue"])]["handoff_in_count"] += 1
        anomaly_output = dict(stage_outputs.get("anomaly_review", {}))
        buckets["finance_anomaly_reviewer_tissue"]["anomaly_burden"] += len(anomaly_output.get("anomalies", []))
        if anomaly_output.get("anomalies"):
            buckets["finance_anomaly_reviewer_tissue"]["intervention_case_count"] += 1
        governance_output = dict(stage_outputs.get("governance_review", {}))
        buckets["finance_workspace_governance_tissue"]["governance_burden"] += len(
            governance_output.get("authority_review_ids", [])
        )
        if governance_output.get("authority_review_ids") or governance_output.get("governance_action") != "approved_release":
            buckets["finance_workspace_governance_tissue"]["intervention_case_count"] += 1
        correction_output = dict(stage_outputs.get("correction", {}))
        if bool(correction_output.get("descriptor_reuse", {}).get("used")):
            buckets["finance_validation_correction_tissue"]["reuse_contribution"] += 1
            buckets["finance_validation_correction_tissue"]["intervention_case_count"] += 1
        elif correction_output.get("correction_notes"):
            buckets["finance_validation_correction_tissue"]["intervention_case_count"] += 1
        report_output = dict(stage_outputs.get("reporting", {}))
        if report_output.get("custody_notes"):
            buckets["finance_reporting_output_tissue"]["intervention_case_count"] += 1
    analytics: dict[str, dict[str, Any]] = {}
    for tissue_id in TISSUE_ORDER:
        bucket = buckets[tissue_id]
        analytics[tissue_id] = {
            "case_count": bucket["case_count"],
            "stage_count": bucket["stage_count"],
            "handoff_in_count": bucket["handoff_in_count"],
            "handoff_out_count": bucket["handoff_out_count"],
            "workload_share": 0.0
            if total_stage_count == 0
            else round(bucket["stage_count"] / float(total_stage_count), 6),
            "useful_case_count": bucket["useful_case_count"],
            "usefulness_rate": 0.0
            if bucket["case_count"] == 0
            else round(bucket["usefulness_total"] / float(bucket["case_count"]), 6),
            "anomaly_burden": bucket["anomaly_burden"],
            "governance_burden": bucket["governance_burden"],
            "reuse_contribution": bucket["reuse_contribution"],
            "intervention_case_count": bucket["intervention_case_count"],
        }
    return analytics


def _field_accuracy(*, result: dict[str, Any], truth: dict[str, Any], fields: list[str]) -> float:
    if not fields:
        return 0.0
    matches = 0
    for field_name in fields:
        if str(result.get(field_name, "")) == str(truth.get(field_name, "")):
            matches += 1
    return round(matches / float(len(fields)), 6)


def _resource_tradeoffs(
    *,
    baseline_summary: dict[str, Any],
    no_adapt_summary: dict[str, Any],
    with_adapt_summary: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    comparisons = [
        ("flat -> no_adapt", baseline_summary, no_adapt_summary),
        ("no_adapt -> with_adapt", no_adapt_summary, with_adapt_summary),
    ]
    for label, left, right in comparisons:
        left_accuracy = float(left["metrics"]["task_accuracy"])
        right_accuracy = float(right["metrics"]["task_accuracy"])
        left_resource = dict(left["metrics"]["resource_usage"])
        right_resource = dict(right["metrics"]["resource_usage"])
        retained_cost = max(
            0,
            int(right_resource.get("retained_memory_delta_bytes", 0))
            - int(left_resource.get("retained_memory_delta_bytes", 0)),
        )
        gain = round(right_accuracy - left_accuracy, 6)
        rows.append(
            {
                "comparison": label,
                "accuracy_gain": gain,
                "retained_memory_cost_bytes": retained_cost,
                "accuracy_gain_per_retained_kib": 0.0
                if retained_cost <= 0
                else round(gain / float(retained_cost / 1024.0), 9),
                "authority_overhead_delta_per_case": round(
                    float(right_resource.get("authority_reviews_per_case", 0.0))
                    - float(left_resource.get("authority_reviews_per_case", 0.0)),
                    6,
                ),
            }
        )
    return {"rows": rows}


def _split_merge_signal(
    *,
    case_results: list[dict[str, Any]],
    split_merge_events: int,
    population: dict[str, Any],
    authority_summary: dict[str, Any],
) -> dict[str, Any]:
    structural_signal_cases = sorted(
        case_result["case_id"]
        for case_result in case_results
        if str(case_result["result"].get("reviewer_status")) == "review_required"
        or int(case_result["result"].get("anomaly_count", 0)) >= 2
    )
    active_population = int(population.get("active_population", 0))
    steady_target = int(population.get("steady_active_population_target", 0))
    pressure_ratio = 0.0 if steady_target == 0 else round(active_population / float(max(1, steady_target)), 6)
    future_trigger = (
        "governed split becomes relevant when repeated reviewer pressure coincides with active population at or above "
        f"{steady_target} and lifecycle split counters move above zero"
    )
    if split_merge_events > 0:
        return {
            "measured": True,
            "value": round(split_merge_events / float(len(case_results)), 6),
            "detail": "measured from lifecycle structural counters",
            "structural_signal_count": len(structural_signal_cases),
            "structural_signal_cases": structural_signal_cases,
            "candidate_tissues": ["finance_anomaly_reviewer_tissue", "finance_workspace_governance_tissue"],
            "pressure_ratio": pressure_ratio,
            "no_action_reason": "",
            "future_trigger": future_trigger,
        }
    return {
        "measured": False,
        "value": 0.0,
        "detail": (
            "no governed split or merge executed; reviewer and governance pressure appeared, "
            f"but active population stayed at {active_population}/{steady_target} and split counters remained zero"
        ),
        "structural_signal_count": len(structural_signal_cases),
        "structural_signal_cases": structural_signal_cases,
        "candidate_tissues": []
        if not structural_signal_cases
        else ["finance_anomaly_reviewer_tissue", "finance_workspace_governance_tissue"],
        "pressure_ratio": pressure_ratio,
        "no_action_reason": (
            "pressure stayed bounded inside existing tissues, no lifecycle split/merge action was approved, "
            f"and authority review volume stayed at {int(authority_summary.get('review_count', 0))}"
        ),
        "future_trigger": future_trigger,
    }
