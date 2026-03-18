"""Track B Gap 1 deterministic organic split benchmark."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from intelligence.fabric.common import load_json_file, repo_relative, utc_now_iso
from intelligence.fabric.benchmarking.phase7 import (
    REPO_ROOT,
    _load_runtime_context,
    _run_cli,
    _score_result,
)


SUITE_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "v1x" / "finance_organic_load" / "benchmark_sequence.json"
ELASTIC_CONFIG = REPO_ROOT / "fixtures" / "document_workflow" / "v1x" / "finance_organic_load" / "minimal_fabric_config_elastic.json"
CONTROL_CONFIG = REPO_ROOT / "fixtures" / "document_workflow" / "v1x" / "finance_organic_load" / "minimal_fabric_config_control.json"
RESULT_JSON_NAME = "v1x_finance_organic_load.json"
RESULT_MARKDOWN_NAME = "v1x_finance_organic_load.md"


def run_v1x_organic_load_benchmark() -> dict[str, Any]:
    suite = _load_suite()
    elastic = _run_stream(mode="elastic", config_path=ELASTIC_CONFIG, suite=suite)
    control = _run_stream(mode="control", config_path=CONTROL_CONFIG, suite=suite)
    comparison = _build_comparison(suite=suite, elastic=elastic, control=control)
    acceptance = {
        "split_occurs_inside_stream": bool(elastic["split_events"]),
        "control_has_no_split_transition": int(control["split_event_count"]) == 0,
        "same_case_sequence": elastic["case_ids"] == control["case_ids"],
        "accuracy_preserved_or_improved": float(elastic["metrics"]["task_accuracy"]) >= float(control["metrics"]["task_accuracy"]),
        "queue_or_latency_improved": (
            float(elastic["metrics"]["mean_queue_age_units"]) < float(control["metrics"]["mean_queue_age_units"])
            or float(elastic["metrics"]["mean_end_to_end_latency_units"]) < float(control["metrics"]["mean_end_to_end_latency_units"])
        ),
        "population_returns_near_start": bool(elastic["population"]["returned_near_start"]),
        "usefulness_not_just_activity": bool(comparison["usefulness_gate_passed"]),
    }
    acceptance["passed"] = all(acceptance.values())
    return {
        "suite_id": suite["suite_id"],
        "created_utc": utc_now_iso(),
        "suite_summary": {
            "case_count": len(suite["cases"]),
            "composition": deepcopy(suite["composition"]),
            "queue_model": deepcopy(suite["queue_model"]),
        },
        "runs": {
            "elastic": elastic,
            "control": control,
        },
        "comparison": comparison,
        "acceptance": acceptance,
    }


def write_v1x_organic_load_result_tables(results: dict[str, Any], *, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / RESULT_JSON_NAME
    markdown_path = output_dir / RESULT_MARKDOWN_NAME
    artifact = _normalize_artifact_results(results)
    json_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    elastic = artifact["runs"]["elastic"]
    control = artifact["runs"]["control"]
    comparison = artifact["comparison"]
    acceptance = artifact["acceptance"]

    run_rows = []
    for label, payload in (("elastic", elastic), ("control", control)):
        metrics = payload["metrics"]
        run_rows.append(
            "| "
            + " | ".join(
                [
                    label,
                    f"{metrics['task_accuracy']:.3f}",
                    f"{metrics['mean_queue_age_units']:.3f}",
                    f"{metrics['mean_end_to_end_latency_units']:.3f}",
                    str(payload["split_event_count"]),
                    str(payload["merge_event_count"]),
                    str(payload["population"]["max_active_population"]),
                    str(payload["population"]["after_settle"]["active_population"]),
                ]
            )
            + " |"
        )

    split_rows = []
    for event in elastic["split_events"]:
        split_rows.append(
            "| "
            + " | ".join(
                [
                    str(event["sequence_index"]),
                    event["case_id"],
                    event["proposer"],
                    event["approver"],
                    event["lineage_chain"],
                    str(event["pre_active_population"]),
                    str(event["post_active_population"]),
                    f"{event['trigger_queue_age_units']:.3f}",
                ]
            )
            + " |"
        )
    if not split_rows:
        split_rows.append("| none | none | none | none | none | 0 | 0 | 0.000 |")

    proposal_rows = []
    for proposal in control["split_proposals"]:
        proposal_rows.append(
            "| "
            + " | ".join(
                [
                    str(proposal["sequence_index"]),
                    proposal["case_id"],
                    proposal["governance_outcome"],
                    proposal["signal_kind"],
                    f"{proposal['signal_severity']:.3f}",
                    proposal["reason"],
                ]
            )
            + " |"
        )
    if not proposal_rows:
        proposal_rows.append("| none | none | none | none | 0.000 | none |")

    case_rows = []
    for elastic_case, control_case in zip(elastic["case_results"], control["case_results"], strict=True):
        case_rows.append(
            "| "
            + " | ".join(
                [
                    elastic_case["case_id"],
                    elastic_case["load_band"],
                    elastic_case["correction_selected_cell"],
                    str(elastic_case["queue_metrics"]["correction_worker_count"]),
                    f"{elastic_case['queue_metrics']['queue_age_units']:.3f}",
                    f"{control_case['queue_metrics']['queue_age_units']:.3f}",
                    f"{elastic_case['correctness_score']:.3f}",
                    f"{control_case['correctness_score']:.3f}",
                ]
            )
            + " |"
        )

    markdown_lines = [
        "# V1X Finance Organic Load Results",
        "",
        "Locally verified deterministic benchmark summary for Track B Gap 1.",
        "",
        "## Run Summary",
        "",
        "| Run | Accuracy | Mean Queue Age | Mean End-To-End Latency | Split Events | Merge Events | Max Active Population | Active After Settle |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *run_rows,
        "",
        "## Elastic Split Events",
        "",
        "| Seq | Case ID | Proposer | Approver | Lineage Chain | Pre Active | Post Active | Trigger Queue Age |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
        *split_rows,
        "",
        "## Control Split Decisions",
        "",
        "| Seq | Case ID | Governance Outcome | Signal Kind | Signal Severity | Reason |",
        "| --- | --- | --- | --- | ---: | --- |",
        *proposal_rows,
        "",
        "## Overhead Vs Usefulness",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Elastic accuracy delta vs control | {comparison['overhead_vs_usefulness']['accuracy_delta_vs_control']:.3f} |",
        f"| Queue age gain vs control | {comparison['overhead_vs_usefulness']['queue_age_gain_vs_control']:.3f} |",
        f"| End-to-end latency gain vs control | {comparison['overhead_vs_usefulness']['latency_gain_vs_control']:.3f} |",
        f"| Extra authority reviews in elastic | {comparison['overhead_vs_usefulness']['extra_authority_reviews']} |",
        f"| Extra lifecycle events in elastic | {comparison['overhead_vs_usefulness']['extra_lifecycle_events']} |",
        f"| Extra correction worker units in elastic | {comparison['overhead_vs_usefulness']['extra_correction_worker_units']} |",
        f"| Post-split elastic accuracy | {comparison['pre_post_accuracy']['elastic_post_split_accuracy']:.3f} |",
        f"| Post-split control accuracy | {comparison['pre_post_accuracy']['control_post_split_accuracy']:.3f} |",
        "",
        "## Case Stream",
        "",
        "| Case ID | Band | Elastic Correction Cell | Elastic Workers | Elastic Queue Age | Control Queue Age | Elastic Score | Control Score |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        *case_rows,
        "",
        "## Acceptance",
        "",
        "| Check | Passed |",
        "| --- | --- |",
        f"| Split occurs inside stream | {'yes' if acceptance['split_occurs_inside_stream'] else 'no'} |",
        f"| Control blocks split transitions | {'yes' if acceptance['control_has_no_split_transition'] else 'no'} |",
        f"| Same case sequence | {'yes' if acceptance['same_case_sequence'] else 'no'} |",
        f"| Accuracy preserved or improved | {'yes' if acceptance['accuracy_preserved_or_improved'] else 'no'} |",
        f"| Queue or latency improved | {'yes' if acceptance['queue_or_latency_improved'] else 'no'} |",
        f"| Active population returns near start | {'yes' if acceptance['population_returns_near_start'] else 'no'} |",
        f"| Usefulness gate passed | {'yes' if acceptance['usefulness_not_just_activity'] else 'no'} |",
        f"| Overall pass | {'yes' if acceptance['passed'] else 'no'} |",
    ]
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _load_suite() -> dict[str, Any]:
    payload = load_json_file(
        SUITE_PATH,
        not_found_code="CONFIG_INVALID",
        invalid_code="CONFIG_INVALID",
        label="Track B Gap 1 suite",
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Gap 1 suite must be an object.")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 40:
        raise RuntimeError("Gap 1 suite must contain exactly 40 ordered cases.")
    materialized_cases = []
    suite_dir = SUITE_PATH.parent
    for case_spec in cases:
        materialized = deepcopy(case_spec)
        payload_path = suite_dir / str(case_spec["payload_path"])
        base_payload = load_json_file(
            payload_path,
            not_found_code="CONFIG_INVALID",
            invalid_code="CONFIG_INVALID",
            label=f"Gap 1 payload {payload_path.name}",
        )
        if not isinstance(base_payload, dict):
            raise RuntimeError(f"Gap 1 payload must be an object: {payload_path}")
        materialized["payload"] = _deep_merge(base_payload, dict(case_spec.get("payload_overrides", {})))
        materialized["payload_path"] = repo_relative(payload_path)
        materialized_cases.append(materialized)
    return {
        "suite_id": str(payload["suite_id"]),
        "composition": deepcopy(payload["composition"]),
        "queue_model": deepcopy(payload["queue_model"]),
        "cases": materialized_cases,
    }


def _run_stream(*, mode: str, config_path: Path, suite: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        state_root = Path(tempdir) / "runtime_state"
        env = os.environ.copy()
        env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)
        _run_cli(env=env, args=["fabric", "init", str(config_path)])

        context = _load_runtime_context(config_path=config_path, state_root=state_root)
        config = context["config"]
        lifecycle = context["lifecycle"]
        initial_population = lifecycle.summary()
        initial_authority = context["authority_engine"].summary()
        initial_routing = context["routing_engine"].summary()
        initial_history_count = int(initial_population["lifecycle_event_count"])
        organic_profile = dict(config.get("benchmark_profile", {}).get("organic_load_profile", {}))
        split_enabled = bool(organic_profile.get("governance_split_enabled", False))
        split_parent_cell_id = str(organic_profile.get("split_parent_cell_id", "finance_correction_specialist"))
        split_child_role_names = list(organic_profile.get("split_child_role_names", []))
        queue_state = {"worker_available_ticks": []}
        base_units = int(suite["queue_model"]["base_end_to_end_units"])

        case_results: list[dict[str, Any]] = []
        split_events: list[dict[str, Any]] = []
        merge_events: list[dict[str, Any]] = []
        split_proposals: list[dict[str, Any]] = []
        split_case_index: int | None = None
        max_active_population = int(initial_population["active_population"])

        for case_spec in suite["cases"]:
            before_context = _load_runtime_context(config_path=config_path, state_root=state_root)
            before_population = before_context["lifecycle"].summary()
            correction_workers = _correction_worker_capacity(context=before_context, split_parent_cell_id=split_parent_cell_id)
            queue_metrics = _queue_case(
                queue_state=queue_state,
                arrival_tick=int(case_spec["arrival_tick"]),
                service_units=int(case_spec["correction_service_units"]),
                worker_count=correction_workers,
                base_end_to_end_units=base_units,
            )
            run_payload = _run_cli(
                env=env,
                args=["fabric", "run"],
                stdin_text=json.dumps(case_spec["payload"]),
            )
            result = dict(run_payload["data"]["result"])
            score = _score_result(result=result, truth=dict(case_spec["truth"]))
            after_context = _load_runtime_context(config_path=config_path, state_root=state_root)
            after_population = after_context["lifecycle"].summary()
            max_active_population = max(max_active_population, int(after_population["active_population"]))
            correction_selected_cell = _selected_stage_cell(run_payload["data"]["trace"], stage_id="correction")
            case_row = {
                "sequence_index": int(case_spec["sequence_index"]),
                "case_id": str(case_spec["case_id"]),
                "load_band": str(case_spec["load_band"]),
                "expected_governance": str(case_spec["expected_governance"]),
                "correctness_score": float(score),
                "correction_selected_cell": correction_selected_cell,
                "descriptor_reuse_eligible": bool(result.get("descriptor_reuse", {}).get("eligible")),
                "descriptor_reuse_used": bool(result.get("descriptor_reuse", {}).get("used")),
                "reviewer_status": str(result.get("reviewer_status", "")),
                "governance_action": str(result.get("governance_action", "")),
                "final_status": str(result.get("final_status", "")),
                "anomaly_count": int(result.get("anomaly_count", 0)),
                "queue_metrics": queue_metrics,
                "population_before_case": {
                    "active_population": int(before_population["active_population"]),
                    "logical_population": int(before_population["logical_population"]),
                },
                "population_after_case": {
                    "active_population": int(after_population["active_population"]),
                    "logical_population": int(after_population["logical_population"]),
                },
            }
            case_results.append(case_row)

            if split_case_index is None:
                proposal = _evaluate_split_proposal(
                    mode=mode,
                    case_results=case_results,
                    population=after_population,
                    split_enabled=split_enabled,
                    split_parent_cell_id=split_parent_cell_id,
                    split_child_role_names=split_child_role_names,
                    config_path=config_path,
                    state_root=state_root,
                )
                if proposal is not None:
                    split_proposals.append(proposal)
                    if proposal["approved"]:
                        split_case_index = int(proposal["sequence_index"])
                        split_events.append(proposal["event"])
                        max_active_population = max(
                            max_active_population,
                            int(proposal["event"]["post_active_population"]),
                        )

        post_stream_context = _load_runtime_context(config_path=config_path, state_root=state_root)
        post_stream_population = post_stream_context["lifecycle"].summary()
        merge_event = _merge_split_children_if_needed(
            context=post_stream_context,
            split_parent_cell_id=split_parent_cell_id,
        )
        if merge_event is not None:
            merge_events.append(merge_event)
        settle = _cool_down_population(context=_load_runtime_context(config_path=config_path, state_root=state_root))
        final_context = _load_runtime_context(config_path=config_path, state_root=state_root)
        final_population = final_context["lifecycle"].summary()
        final_authority = final_context["authority_engine"].summary()
        final_routing = final_context["routing_engine"].summary()
        split_transition_count = _count_history_transitions(
            context=final_context,
            transition="split_pending_to_active_children",
        )

        task_scores = [float(item["correctness_score"]) for item in case_results]
        queue_scores = [float(item["queue_metrics"]["queue_age_units"]) for item in case_results]
        latency_scores = [float(item["queue_metrics"]["end_to_end_latency_units"]) for item in case_results]
        pre_post_accuracy = _pre_post_metrics(case_results=case_results, split_case_index=split_case_index, key="correctness_score")
        pre_post_queue = _pre_post_metrics(case_results=case_results, split_case_index=split_case_index, key="queue_metrics.queue_age_units")

        return {
            "mode": mode,
            "config_ref": repo_relative(config_path),
            "split_governance_enabled": split_enabled,
            "case_ids": [str(item["case_id"]) for item in case_results],
            "case_results": case_results,
            "split_event_count": len(split_events),
            "merge_event_count": len(merge_events),
            "split_events": split_events,
            "merge_events": merge_events,
            "split_proposals": split_proposals,
            "split_case_index": split_case_index,
            "metrics": {
                "task_accuracy": _average(task_scores),
                "mean_queue_age_units": _average(queue_scores),
                "mean_end_to_end_latency_units": _average(latency_scores),
                "pre_split_accuracy": pre_post_accuracy["before"],
                "post_split_accuracy": pre_post_accuracy["after"],
                "pre_split_queue_age_units": pre_post_queue["before"],
                "post_split_queue_age_units": pre_post_queue["after"],
            },
            "population": {
                "initial": _population_snapshot(initial_population),
                "after_stream": _population_snapshot(post_stream_population),
                "after_settle": _population_snapshot(final_population),
                "max_active_population": max_active_population,
                "returned_near_start": int(final_population["active_population"]) <= int(initial_population["active_population"]) + 1,
            },
            "overhead": {
                "lifecycle_event_delta": int(final_population["lifecycle_event_count"]) - initial_history_count,
                "authority_review_delta": int(final_authority["review_count"]) - int(initial_authority["review_count"]),
                "routing_decision_delta": int(final_routing["decision_count"]) - int(initial_routing["decision_count"]),
                "correction_worker_units": sum(int(item["queue_metrics"]["correction_worker_count"]) for item in case_results),
                "split_transition_count": split_transition_count,
                "settle_hibernated_cells": settle["hibernated_cells"],
            },
        }


def _build_comparison(*, suite: dict[str, Any], elastic: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    split_index = elastic["split_case_index"]
    elastic_post_accuracy = _safe_post_split_metric(elastic, "post_split_accuracy")
    control_post_accuracy = _safe_post_split_metric(control, "post_split_accuracy", split_index=split_index)
    elastic_post_queue = _safe_post_split_metric(elastic, "post_split_queue_age_units")
    control_post_queue = _safe_post_split_metric(control, "post_split_queue_age_units", split_index=split_index)
    elastic_post_latency = _post_split_latency(elastic, split_index=split_index)
    control_post_latency = _post_split_latency(control, split_index=split_index)
    overhead_vs_usefulness = {
        "accuracy_delta_vs_control": round(float(elastic["metrics"]["task_accuracy"]) - float(control["metrics"]["task_accuracy"]), 6),
        "queue_age_gain_vs_control": round(float(control["metrics"]["mean_queue_age_units"]) - float(elastic["metrics"]["mean_queue_age_units"]), 6),
        "latency_gain_vs_control": round(float(control["metrics"]["mean_end_to_end_latency_units"]) - float(elastic["metrics"]["mean_end_to_end_latency_units"]), 6),
        "extra_authority_reviews": int(elastic["overhead"]["authority_review_delta"]) - int(control["overhead"]["authority_review_delta"]),
        "extra_lifecycle_events": int(elastic["overhead"]["lifecycle_event_delta"]) - int(control["overhead"]["lifecycle_event_delta"]),
        "extra_correction_worker_units": int(elastic["overhead"]["correction_worker_units"]) - int(control["overhead"]["correction_worker_units"]),
        "post_split_queue_gain_vs_control": round(control_post_queue - elastic_post_queue, 6),
        "post_split_latency_gain_vs_control": round(control_post_latency - elastic_post_latency, 6),
    }
    usefulness_gate_passed = bool(elastic["split_events"]) and (
        overhead_vs_usefulness["post_split_queue_gain_vs_control"] > 0.0
        or overhead_vs_usefulness["post_split_latency_gain_vs_control"] > 0.0
    ) and elastic_post_accuracy >= control_post_accuracy
    return {
        "same_case_sequence": elastic["case_ids"] == control["case_ids"] == [str(item["case_id"]) for item in suite["cases"]],
        "pre_post_accuracy": {
            "elastic_post_split_accuracy": elastic_post_accuracy,
            "control_post_split_accuracy": control_post_accuracy,
        },
        "pre_post_queue_age": {
            "elastic_post_split_queue_age": elastic_post_queue,
            "control_post_split_queue_age": control_post_queue,
            "elastic_post_split_latency": elastic_post_latency,
            "control_post_split_latency": control_post_latency,
        },
        "overhead_vs_usefulness": overhead_vs_usefulness,
        "usefulness_gate_passed": usefulness_gate_passed,
    }


def _evaluate_split_proposal(
    *,
    mode: str,
    case_results: list[dict[str, Any]],
    population: dict[str, Any],
    split_enabled: bool,
    split_parent_cell_id: str,
    split_child_role_names: list[str],
    config_path: Path,
    state_root: Path,
) -> dict[str, Any] | None:
    if len(case_results) < 6:
        return None
    current_case = case_results[-1]
    recent = case_results[-5:]
    heavy_count = len([item for item in recent if item["load_band"] != "recovery_tail"])
    pressure_count = len(
        [
            item
            for item in recent
            if item["descriptor_reuse_eligible"] or item["reviewer_status"] == "review_required"
        ]
    )
    if heavy_count < 4 or pressure_count < 4:
        return None
    if float(current_case["queue_metrics"]["queue_age_units"]) < 2.0:
        return None
    if int(population["active_population"]) < int(population["steady_active_population_target"]):
        return None

    novelty_recent = len([item for item in recent if item["load_band"] == "novelty_heavy"])
    signal_kind = "novelty" if novelty_recent >= 2 else "overload"
    signal_severity = round(min(0.98, 0.76 + (0.04 * float(current_case["queue_metrics"]["queue_age_units"]))), 3)
    reason = (
        "organic correction pressure exceeded the deterministic queue threshold while the active population sat at the steady cap"
    )
    proposal = {
        "sequence_index": int(current_case["sequence_index"]),
        "case_id": str(current_case["case_id"]),
        "reason": reason,
        "signal_kind": signal_kind,
        "signal_severity": signal_severity,
        "governance_outcome": "approved" if split_enabled else "split_disabled_by_governance",
        "approved": split_enabled,
    }
    if not split_enabled:
        return proposal

    context = _load_runtime_context(config_path=config_path, state_root=state_root)
    lifecycle = context["lifecycle"]
    authority = context["authority_engine"]
    pre_population = lifecycle.summary()
    split = lifecycle.split_cell(
        parent_cell_id=split_parent_cell_id,
        child_role_names=split_child_role_names,
        proposer="tissue:finance_validation_correction_tissue:organic_monitor",
        governance_approver=str(context["config"]["governance_policy"]["default_governance_approver"]),
        need_signal={
            "need_signal_id": f"v1x-split-{current_case['sequence_index']:03d}",
            "source_type": "tissue",
            "source_id": "finance_validation_correction_tissue",
            "signal_kind": signal_kind,
            "severity": signal_severity,
            "evidence_ref": f"v1x:organic_load:{current_case['case_id']}:queue_age={current_case['queue_metrics']['queue_age_units']}",
            "proposed_action": "review_organic_split",
            "status": "open",
            "expires_at_utc": "2099-01-01T00:00:00Z",
            "resolution_ref": None,
            "created_utc": "2099-01-01T00:00:00Z"
        },
        reason=reason,
        authority_engine=authority,
    )
    event_entry = _history_entry_for_event(
        context=_load_runtime_context(config_path=config_path, state_root=state_root),
        event_id=str(split["event_id"]),
    )
    child_ids = list(split["child_ids"])
    proposal["event"] = {
        "sequence_index": int(current_case["sequence_index"]),
        "case_id": str(current_case["case_id"]),
        "event_id": str(split["event_id"]),
        "proposer": "tissue:finance_validation_correction_tissue:organic_monitor",
        "approver": str(context["config"]["governance_policy"]["default_governance_approver"]),
        "lineage_id": str(split["lineage_id"]),
        "lineage_chain": f"{split_parent_cell_id} -> {', '.join(child_ids)}",
        "child_ids": child_ids,
        "pre_active_population": int(pre_population["active_population"]),
        "post_active_population": int(split["population"]["active_population"]),
        "pre_logical_population": int(pre_population["logical_population"]),
        "post_logical_population": int(split["population"]["logical_population"]),
        "trigger_queue_age_units": float(current_case["queue_metrics"]["queue_age_units"]),
        "split_proposer": "tissue:finance_validation_correction_tissue:organic_monitor",
        "split_approver": str(context["config"]["governance_policy"]["default_governance_approver"]),
        "history_transition": "" if event_entry is None else str(event_entry["event"]["transition"]),
    }
    return proposal


def _merge_split_children_if_needed(*, context: dict[str, Any], split_parent_cell_id: str) -> dict[str, Any] | None:
    lifecycle = context["lifecycle"]
    active_children = sorted(
        cell_id
        for cell_id in lifecycle.list_active_cells()
        if cell_id.startswith(f"{split_parent_cell_id}__child_")
    )
    if len(active_children) < 2:
        return None
    pre_population = lifecycle.summary()
    merge = lifecycle.merge_cells(
        survivor_cell_id=active_children[0],
        merged_cell_id=active_children[1],
        proposer="tissue:finance_validation_correction_tissue:organic_monitor",
        tissue_approver=str(context["config"]["governance_policy"]["default_tissue_coordinator"]),
        governance_approver=str(context["config"]["governance_policy"]["default_governance_approver"]),
        need_signal={
            "need_signal_id": "v1x-merge-post-stream",
            "source_type": "tissue",
            "source_id": "finance_validation_correction_tissue",
            "signal_kind": "redundancy",
            "severity": 0.82,
            "evidence_ref": "v1x:organic_load:post_stream_recovery_tail",
            "proposed_action": "merge_back_to_steady",
            "status": "open",
            "expires_at_utc": "2099-01-01T00:00:00Z",
            "resolution_ref": None,
            "created_utc": "2099-01-01T00:00:00Z"
        },
        reason="recovery-tail workload removed the extra correction pressure and the split branch returned to steady state",
        authority_engine=context["authority_engine"],
    )
    post_population = lifecycle.summary()
    return {
        "survivor_cell_id": str(merge["survivor_cell_id"]),
        "retired_cell_id": str(merge["retired_cell_id"]),
        "retire_event_id": str(merge["retire_event_id"]),
        "proposer": "tissue:finance_validation_correction_tissue:organic_monitor",
        "approver": (
            f"{context['config']['governance_policy']['default_tissue_coordinator']}"
            f"+{context['config']['governance_policy']['default_governance_approver']}"
        ),
        "lineage_chain": f"{active_children[0]} + {active_children[1]} -> {merge['survivor_cell_id']}",
        "pre_active_population": int(pre_population["active_population"]),
        "post_active_population": int(post_population["active_population"]),
    }


def _cool_down_population(*, context: dict[str, Any]) -> dict[str, Any]:
    lifecycle = context["lifecycle"]
    hibernated: list[str] = []
    for cell_id in list(lifecycle.list_active_cells()):
        lifecycle.hibernate_cell(
            cell_id=cell_id,
            proposer="fabric:v1x_gap1_cooldown",
            tissue_approver=str(context["config"]["governance_policy"]["default_tissue_coordinator"]),
            reason="Gap 1 deterministic recovery cooldown after the organic load stream",
            normalize_after=False,
        )
        hibernated.append(cell_id)
    return {"hibernated_cells": hibernated}


def _queue_case(
    *,
    queue_state: dict[str, Any],
    arrival_tick: int,
    service_units: int,
    worker_count: int,
    base_end_to_end_units: int,
) -> dict[str, Any]:
    available = list(queue_state.get("worker_available_ticks", []))
    while len(available) < max(1, worker_count):
        available.append(arrival_tick)
    available = sorted(int(item) for item in available[: max(1, worker_count)])
    selected_index = min(range(len(available)), key=lambda index: available[index])
    service_start_tick = max(arrival_tick, int(available[selected_index]))
    queue_age_units = max(0, service_start_tick - arrival_tick)
    completion_tick = service_start_tick + service_units
    available[selected_index] = completion_tick
    queue_state["worker_available_ticks"] = available
    return {
        "arrival_tick": int(arrival_tick),
        "correction_worker_count": max(1, int(worker_count)),
        "service_start_tick": int(service_start_tick),
        "completion_tick": int(completion_tick),
        "queue_age_units": float(queue_age_units),
        "end_to_end_latency_units": float(queue_age_units + service_units + base_end_to_end_units),
    }


def _correction_worker_capacity(*, context: dict[str, Any], split_parent_cell_id: str) -> int:
    active_children = [
        cell_id
        for cell_id in context["lifecycle"].list_active_cells()
        if cell_id.startswith(f"{split_parent_cell_id}__child_")
    ]
    if active_children:
        return len(active_children)
    return 1


def _history_entry_for_event(*, context: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    history = load_json_file(
        context["store"].lifecycle_history_path(context["state"]["fabric_id"]),
        not_found_code="STATE_INVALID",
        invalid_code="STATE_INVALID",
        label="Gap 1 lifecycle history",
    )
    if not isinstance(history, dict):
        return None
    for entry in reversed(list(history.get("entries", []))):
        event = entry.get("event", {})
        if str(event.get("event_id")) == event_id:
            return deepcopy(entry)
    return None


def _count_history_transitions(*, context: dict[str, Any], transition: str) -> int:
    history = load_json_file(
        context["store"].lifecycle_history_path(context["state"]["fabric_id"]),
        not_found_code="STATE_INVALID",
        invalid_code="STATE_INVALID",
        label="Gap 1 lifecycle history",
    )
    if not isinstance(history, dict):
        return 0
    return len([1 for entry in history.get("entries", []) if str(entry.get("event", {}).get("transition")) == transition])


def _selected_stage_cell(trace: list[dict[str, Any]], *, stage_id: str) -> str:
    for item in trace:
        if str(item.get("stage_id")) == stage_id:
            return str(item.get("cell_id", ""))
    return ""


def _population_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "active_population": int(summary["active_population"]),
        "logical_population": int(summary["logical_population"]),
        "steady_active_population_target": int(summary["steady_active_population_target"]),
        "burst_active_population_cap": int(summary["burst_active_population_cap"]),
    }


def _pre_post_metrics(*, case_results: list[dict[str, Any]], split_case_index: int | None, key: str) -> dict[str, float]:
    if split_case_index is None:
        values = [_pluck_metric(item, key) for item in case_results]
        average = _average(values)
        return {"before": average, "after": average}
    before_values = [_pluck_metric(item, key) for item in case_results[:split_case_index]]
    after_values = [_pluck_metric(item, key) for item in case_results[split_case_index:]]
    return {"before": _average(before_values), "after": _average(after_values)}


def _pluck_metric(item: dict[str, Any], key: str) -> float:
    value: Any = item
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
    return float(value or 0.0)


def _safe_post_split_metric(payload: dict[str, Any], metric_name: str, *, split_index: int | None = None) -> float:
    if split_index is None:
        split_index = payload.get("split_case_index")
    return _pre_post_metrics(
        case_results=payload["case_results"],
        split_case_index=split_index,
        key={
            "post_split_accuracy": "correctness_score",
            "post_split_queue_age_units": "queue_metrics.queue_age_units",
        }[metric_name],
    )["after"]


def _post_split_latency(payload: dict[str, Any], *, split_index: int | None) -> float:
    return _pre_post_metrics(
        case_results=payload["case_results"],
        split_case_index=split_index,
        key="queue_metrics.end_to_end_latency_units",
    )["after"]


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / float(len(values)), 6)


def _normalize_artifact_results(results: dict[str, Any]) -> dict[str, Any]:
    artifact = deepcopy(results)
    artifact.pop("created_utc", None)
    return artifact


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(dict(merged[key]), value)
        else:
            merged[key] = deepcopy(value)
    return merged
