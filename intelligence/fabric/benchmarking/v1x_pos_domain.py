"""Track B Gap 3 bounded POS-domain benchmark with governed causal transfer."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from intelligence.fabric.common import load_json_file, utc_now_iso
from intelligence.fabric.benchmarking.phase7 import REPO_ROOT, _load_runtime_context, _run_cli
from intelligence.fabric.descriptors import DescriptorGraphManager
from intelligence.fabric.domain import execute_pos_case


SUITE_PATH = REPO_ROOT / "fixtures" / "pos_operations" / "v1x" / "gap3_pos_suite.json"
ENABLED_CONFIG = REPO_ROOT / "fixtures" / "pos_operations" / "v1x" / "minimal_fabric_config_transfer_enabled.json"
CONTROL_CONFIG = REPO_ROOT / "fixtures" / "pos_operations" / "v1x" / "minimal_fabric_config_control.json"
RESULT_JSON_NAME = "v1x_pos_domain_transfer.json"
RESULT_MARKDOWN_NAME = "v1x_pos_domain_transfer.md"


def run_v1x_pos_domain_benchmark() -> dict[str, Any]:
    suite = _load_suite()
    enabled = _run_suite(mode="transfer_enabled", config_path=ENABLED_CONFIG, suite=suite)
    control = _run_suite(mode="control", config_path=CONTROL_CONFIG, suite=suite)
    comparison = _build_comparison(enabled=enabled, control=control)
    acceptance = _build_acceptance(suite=suite, enabled=enabled, control=control, comparison=comparison)
    return {
        "suite_id": suite["suite_id"],
        "created_utc": utc_now_iso(),
        "suite_summary": {
            "case_count": len(suite["cases"]),
            "case_ids": [str(case["case_id"]) for case in suite["cases"]],
            "seed_count": len(suite["seed_descriptors"]),
        },
        "runs": {
            "transfer_enabled": enabled,
            "control": control,
        },
        "comparison": comparison,
        "acceptance": acceptance,
    }


def write_v1x_pos_domain_result_tables(results: dict[str, Any], *, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / RESULT_JSON_NAME
    markdown_path = output_dir / RESULT_MARKDOWN_NAME
    artifact = _normalize_artifact_results(results)
    json_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    enabled = artifact["runs"]["transfer_enabled"]
    control = artifact["runs"]["control"]
    comparison = artifact["comparison"]
    acceptance = artifact["acceptance"]

    run_rows = []
    for label, payload in (("transfer_enabled", enabled), ("control", control)):
        metrics = payload["metrics"]
        run_rows.append(
            "| "
            + " | ".join(
                [
                    label,
                    "yes" if payload["cross_domain_transfer_enabled"] else "no",
                    f"{metrics['mean_case_score']:.3f}",
                    str(metrics["approved_transfer_count"]),
                    str(metrics["denied_transfer_count"]),
                    str(metrics["abstained_transfer_count"]),
                    str(metrics["counted_cross_domain_influence_count"]),
                    str(metrics["governance_disabled_veto_count"]),
                ]
            )
            + " |"
        )

    case_rows = []
    for row in comparison["case_rows"]:
        case_rows.append(
            "| "
            + " | ".join(
                [
                    row["case_id"],
                    row["control_action"],
                    f"{row['control_score']:.3f}",
                    row["enabled_action"],
                    f"{row['enabled_score']:.3f}",
                    row["enabled_transfer_status"],
                    "yes" if row["enabled_explicit_transfer_approval"] else "no",
                    "yes" if row["enabled_counted_cross_domain_influence"] else "no",
                    str(row["enabled_transfer_approval_ref"] or "none"),
                ]
            )
            + " |"
        )

    enabled_audit_rows = []
    for case in enabled["case_results"]:
        enabled_audit_rows.append(
            "| "
            + " | ".join(
                [
                    case["case_id"],
                    str(case["transfer_status"] or "none"),
                    str(case["selected_source_descriptor_id"] or "none"),
                    str(case["source_domain"] or "none"),
                    str(case["authority_review_id"] or "none"),
                    ",".join(case["authority_veto_conditions"]) if case["authority_veto_conditions"] else "none",
                    str(case["source_payload_ref"] or "none"),
                    str(case["transfer_approval_ref"] or "none"),
                ]
            )
            + " |"
        )

    markdown_lines = [
        "# V1X POS Domain Transfer Results",
        "",
        "Locally verified deterministic benchmark summary for Track B Gap 3.",
        "",
        "## Run Summary",
        "",
        "| Run | Cross-Domain Transfer Enabled | Mean Case Score | Approved Transfers | Denied Transfers | Abstained Transfers | Counted Influence | Governance-Disabled Vetoes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *run_rows,
        "",
        "## Case Comparison",
        "",
        "| Case ID | Control Action | Control Score | Enabled Action | Enabled Score | Enabled Transfer Status | Explicit Approval | Counted Influence | Approval Ref |",
        "| --- | --- | ---: | --- | ---: | --- | --- | --- | --- |",
        *case_rows,
        "",
        "## Enabled Audit Trail",
        "",
        "| Case ID | Transfer Status | Source Descriptor | Source Domain | Review Ref | Veto Conditions | Source Payload Ref | Transfer Approval Ref |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *enabled_audit_rows,
        "",
        "## Acceptance",
        "",
        "| Check | Passed |",
        "| --- | --- |",
        f"| Bounded 5-case POS suite is frozen | {'yes' if acceptance['bounded_pos_suite_frozen'] else 'no'} |",
        f"| Same case sequence in both runs | {'yes' if acceptance['same_case_sequence'] else 'no'} |",
        f"| Control disables transfer at governance | {'yes' if acceptance['control_disables_transfer_at_governance'] else 'no'} |",
        f"| Finance-origin descriptor improves a POS result | {'yes' if acceptance['finance_origin_descriptor_improves_pos_result'] else 'no'} |",
        f"| Cross-domain influence requires explicit approval | {'yes' if acceptance['cross_domain_influence_requires_explicit_transfer_approval'] else 'no'} |",
        f"| POS proof is useful and auditable | {'yes' if acceptance['useful_and_auditable'] else 'no'} |",
        f"| Overall pass | {'yes' if acceptance['passed'] else 'no'} |",
        "",
        "## Causal Improvement Cases",
        "",
        "| Improved Case IDs |",
        "| --- |",
        f"| {', '.join(comparison['improved_case_ids']) if comparison['improved_case_ids'] else 'none'} |",
    ]
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _load_suite() -> dict[str, Any]:
    payload = load_json_file(
        SUITE_PATH,
        not_found_code="CONFIG_INVALID",
        invalid_code="CONFIG_INVALID",
        label="Track B Gap 3 suite",
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Gap 3 suite must be an object.")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 5:
        raise RuntimeError("Gap 3 suite must contain exactly five ordered POS cases.")
    if not isinstance(payload.get("seed_descriptors"), list) or len(payload["seed_descriptors"]) < 2:
        raise RuntimeError("Gap 3 suite must define at least two finance seed descriptors.")
    return deepcopy(payload)


def _run_suite(*, mode: str, config_path: Path, suite: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        state_root = Path(tempdir) / "runtime_state"
        env = os.environ.copy()
        env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)
        _run_cli(env=env, args=["fabric", "init", str(config_path)])

        context = _load_runtime_context(config_path=config_path, state_root=state_root)
        memory = context["memory"]
        authority = context["authority_engine"]
        graph_manager = DescriptorGraphManager(
            store=context["store"],
            state=context["state"],
            config=context["config"],
        )

        reviewer_id = str(
            context["config"].get("governance_policy", {}).get("default_memory_reviewer")
            or context["config"].get("governance_policy", {}).get("default_governance_approver")
            or "governance:phase5_memory_reviewer"
        )
        seeded_descriptors = [
            _seed_descriptor(
                memory=memory,
                authority=authority,
                reviewer_id=reviewer_id,
                seed_spec=seed_spec,
            )
            for seed_spec in suite["seed_descriptors"]
        ]
        graph_manager.sync_from_memory(memory_manager=memory)

        case_results: list[dict[str, Any]] = []
        for case_spec in suite["cases"]:
            transfer_request = deepcopy(case_spec.get("transfer_request")) if isinstance(case_spec.get("transfer_request"), dict) else None
            transfer_entry = None
            authority_review = None
            if transfer_request is not None:
                transfer_entry = graph_manager.request_transfer(request=transfer_request, authority_engine=authority)
                authority_review = _find_review(authority=authority, review_id=transfer_entry.get("authority_review_id"))
            case_result = execute_pos_case(case_spec=case_spec, transfer_entry=transfer_entry)
            case_result.update(
                {
                    "sequence_index": int(case_spec["sequence_index"]),
                    "transfer_request_id": None if transfer_request is None else str(transfer_request["request_id"]),
                    "explicit_transfer_approval": False if transfer_request is None else bool(transfer_request.get("explicit_transfer_approval", False)),
                    "target_domain": None if transfer_request is None else str(transfer_request.get("target_domain", "")),
                    "transfer_status": None if transfer_entry is None else str(transfer_entry.get("status")),
                    "transfer_quality_score": 0.0 if transfer_entry is None else float(transfer_entry.get("transfer_quality_score", 0.0)),
                    "baseline_support_score": None if transfer_entry is None else float(transfer_entry.get("baseline_support_score", 0.0)),
                    "target_support_score": None if transfer_entry is None else float(transfer_entry.get("target_support_score", 0.0)),
                    "selected_source_descriptor_id": None if transfer_entry is None else transfer_entry.get("selected_source_descriptor_id"),
                    "source_domain": None if transfer_entry is None else transfer_entry.get("source_domain"),
                    "authority_review_id": None if transfer_entry is None else transfer_entry.get("authority_review_id"),
                    "authority_decision": None if transfer_entry is None else transfer_entry.get("authority_decision"),
                    "authority_veto_conditions": [] if authority_review is None else list(authority_review.get("veto_conditions", [])),
                    "source_payload_ref": None
                    if not isinstance(case_result.get("audit_bundle"), dict)
                    else case_result["audit_bundle"].get("source_payload_ref"),
                    "transfer_approval_ref": None
                    if not isinstance(case_result.get("audit_bundle"), dict)
                    else case_result["audit_bundle"].get("transfer_approval_ref"),
                }
            )
            case_results.append(case_result)

        graph_summary = graph_manager.summary()
        metrics = _build_run_metrics(case_results=case_results, graph_summary=graph_summary)
        return {
            "mode": mode,
            "config_ref": str(config_path.relative_to(REPO_ROOT)),
            "cross_domain_transfer_enabled": bool(context["config"].get("governance_policy", {}).get("cross_domain_transfer_enabled", True)),
            "seeded_descriptors": seeded_descriptors,
            "case_ids": [str(case["case_id"]) for case in suite["cases"]],
            "case_results": case_results,
            "graph_summary": graph_summary,
            "metrics": metrics,
        }


def _build_run_metrics(*, case_results: list[dict[str, Any]], graph_summary: dict[str, Any]) -> dict[str, Any]:
    total_cases = len(case_results)
    mean_case_score = 0.0 if total_cases == 0 else round(
        sum(float(case["case_score"]) for case in case_results) / float(total_cases),
        6,
    )
    governance_disabled_veto_count = len(
        [
            case
            for case in case_results
            if "cross_domain_transfer_disabled_by_governance" in case.get("authority_veto_conditions", [])
        ]
    )
    audit_ready_case_count = len([case for case in case_results if isinstance(case.get("audit_bundle"), dict)])
    counted_cross_domain_influence_count = len(
        [case for case in case_results if bool(case.get("counted_cross_domain_influence", False))]
    )
    return {
        "mean_case_score": mean_case_score,
        "approved_transfer_count": int(graph_summary["approved_transfer_count"]),
        "denied_transfer_count": int(graph_summary["denied_transfer_count"]),
        "abstained_transfer_count": int(graph_summary["abstained_transfer_count"]),
        "audit_ready_case_count": audit_ready_case_count,
        "counted_cross_domain_influence_count": counted_cross_domain_influence_count,
        "governance_disabled_veto_count": governance_disabled_veto_count,
    }


def _build_comparison(*, enabled: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    improved_case_ids: list[str] = []
    for enabled_case, control_case in zip(enabled["case_results"], control["case_results"], strict=True):
        row = {
            "case_id": enabled_case["case_id"],
            "control_action": control_case["final_action"],
            "control_score": float(control_case["case_score"]),
            "enabled_action": enabled_case["final_action"],
            "enabled_score": float(enabled_case["case_score"]),
            "enabled_transfer_status": str(enabled_case["transfer_status"] or "none"),
            "enabled_explicit_transfer_approval": bool(enabled_case["explicit_transfer_approval"]),
            "enabled_counted_cross_domain_influence": bool(enabled_case["counted_cross_domain_influence"]),
            "enabled_transfer_approval_ref": enabled_case["transfer_approval_ref"],
            "score_delta_vs_control": round(float(enabled_case["case_score"]) - float(control_case["case_score"]), 6),
        }
        rows.append(row)
        if (
            row["score_delta_vs_control"] > 0.0
            and bool(enabled_case["counted_cross_domain_influence"])
            and str(enabled_case["source_domain"]).startswith("finance")
        ):
            improved_case_ids.append(str(enabled_case["case_id"]))
    return {
        "case_rows": rows,
        "improved_case_ids": improved_case_ids,
        "mean_score_delta_vs_control": round(
            float(enabled["metrics"]["mean_case_score"]) - float(control["metrics"]["mean_case_score"]),
            6,
        ),
    }


def _build_acceptance(
    *,
    suite: dict[str, Any],
    enabled: dict[str, Any],
    control: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    missing_explicit_case = next(case for case in enabled["case_results"] if case["case_id"] == "tailspin_refund_missing_explicit")
    improved_case = next(case for case in enabled["case_results"] if case["case_id"] == "northwind_settlement_alias_hold")
    acceptance = {
        "bounded_pos_suite_frozen": len(suite["cases"]) == 5,
        "same_case_sequence": enabled["case_ids"] == control["case_ids"] == [str(case["case_id"]) for case in suite["cases"]],
        "control_disables_transfer_at_governance": (
            not control["cross_domain_transfer_enabled"]
            and int(control["metrics"]["governance_disabled_veto_count"]) >= 1
            and int(control["metrics"]["counted_cross_domain_influence_count"]) == 0
        ),
        "finance_origin_descriptor_improves_pos_result": (
            improved_case["case_score"] > next(case for case in control["case_results"] if case["case_id"] == improved_case["case_id"])["case_score"]
            and bool(improved_case["counted_cross_domain_influence"])
            and str(improved_case["source_domain"]).startswith("finance")
            and bool(improved_case["transfer_approval_ref"])
        ),
        "cross_domain_influence_requires_explicit_transfer_approval": (
            all(
                (not bool(case["counted_cross_domain_influence"])) or bool(case["explicit_transfer_approval"])
                for case in enabled["case_results"]
            )
            and missing_explicit_case["transfer_status"] == "denied"
            and not bool(missing_explicit_case["counted_cross_domain_influence"])
        ),
        "useful_and_auditable": (
            int(enabled["metrics"]["audit_ready_case_count"]) >= 1
            and int(enabled["metrics"]["approved_transfer_count"]) >= 1
            and len(comparison["improved_case_ids"]) >= 1
            and float(comparison["mean_score_delta_vs_control"]) > 0.0
        ),
    }
    acceptance["passed"] = all(acceptance.values())
    return acceptance


def _seed_descriptor(
    *,
    memory: Any,
    authority: Any,
    reviewer_id: str,
    seed_spec: dict[str, Any],
) -> dict[str, Any]:
    candidate = memory.nominate_candidate(
        payload=deepcopy(seed_spec["payload"]),
        source_ref=str(seed_spec["source_ref"]),
        source_log_refs=list(seed_spec.get("source_log_refs", [])),
        producer_cell_id=str(seed_spec["producer_cell_id"]),
        descriptor_kind=str(seed_spec["descriptor_kind"]),
        task_scope=str(seed_spec["task_scope"]),
        trust_ref=str(seed_spec.get("trust_ref", "trust:bounded_local_v1")),
    )
    review = memory.review_candidate(
        candidate_id=candidate["candidate_id"],
        reviewer_id=reviewer_id,
        decision="promote",
        compression_mode="quantized_summary_v1",
        retention_tier="warm",
        reason=f"gap3_seed:{seed_spec['seed_id']}",
        authority_engine=authority,
    )
    descriptors = memory.load_descriptors()
    promoted = memory.load_promoted_memories()
    descriptor_record = descriptors["active"][review["descriptor_id"]]
    promoted_record = promoted["active"][review["memory_id"]]
    source_domain = str(seed_spec["task_scope"]).split(":", 1)[0]
    trust_score = float(promoted_record.get("trust_score", 0.0))
    confidence_score = float(descriptor_record.get("confidence_score", 0.0))
    value_score = float(promoted_record.get("value_score", 0.0))
    provenance_score = round(
        min(
            1.0,
            (0.35 * trust_score)
            + (0.25 * confidence_score)
            + (0.2 * value_score)
            + 0.1
            + 0.1,
        ),
        6,
    )
    return {
        "seed_id": str(seed_spec["seed_id"]),
        "candidate_id": candidate["candidate_id"],
        "memory_id": review["memory_id"],
        "descriptor_id": review["descriptor_id"],
        "source_domain": source_domain,
        "memory_class": str(promoted_record.get("memory_class", "")),
        "trust_score": trust_score,
        "provenance_score": provenance_score,
    }


def _find_review(*, authority: Any, review_id: Any) -> dict[str, Any] | None:
    if not isinstance(review_id, str) or review_id.strip() == "":
        return None
    for review in authority.load_reviews():
        if str(review.get("review_id")) == review_id:
            return deepcopy(review)
    return None


def _normalize_artifact_results(results: dict[str, Any]) -> dict[str, Any]:
    artifact = {
        "suite_id": results["suite_id"],
        "suite_summary": deepcopy(results["suite_summary"]),
        "runs": deepcopy(results["runs"]),
        "comparison": deepcopy(results["comparison"]),
        "acceptance": deepcopy(results["acceptance"]),
    }
    for run in artifact["runs"].values():
        for case in run["case_results"]:
            for field_name in ("source_payload_ref", "transfer_approval_ref"):
                case[field_name] = _normalize_ref(case.get(field_name))
            case["audit_bundle"] = _normalize_audit_bundle(case.get("audit_bundle"))
        for seeded in run["seeded_descriptors"]:
            seeded.pop("candidate_id", None)
    return artifact


def _normalize_audit_bundle(bundle: Any) -> Any:
    if not isinstance(bundle, dict):
        return bundle
    normalized = deepcopy(bundle)
    normalized["source_payload_ref"] = _normalize_ref(normalized.get("source_payload_ref"))
    return normalized


def _normalize_ref(value: Any) -> Any:
    if not isinstance(value, str) or value.strip() == "":
        return value
    path = Path(value)
    parts = list(path.parts)
    for marker in ("memory", "descriptors", "governance"):
        if marker in parts:
            return "/".join(parts[parts.index(marker) :])
    return str(path)
