"""Track B Gap 2 deterministic governed skill-graph benchmark."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from intelligence.fabric.common import load_json_file, utc_now_iso
from intelligence.fabric.descriptors import DescriptorGraphManager
from intelligence.fabric.benchmarking.phase7 import REPO_ROOT, _load_runtime_context, _run_cli


SUITE_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "v1x" / "skill_graph" / "transfer_suite.json"
CONFIG_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "v1x" / "skill_graph" / "minimal_fabric_config.json"
RESULT_JSON_NAME = "v1x_skill_graph_transfer.json"
RESULT_MARKDOWN_NAME = "v1x_skill_graph_transfer.md"


def run_v1x_skill_graph_benchmark() -> dict[str, Any]:
    suite = _load_suite()
    with tempfile.TemporaryDirectory() as tempdir:
        state_root = Path(tempdir) / "runtime_state"
        env = os.environ.copy()
        env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)
        _run_cli(env=env, args=["fabric", "init", str(CONFIG_PATH)])

        context = _load_runtime_context(config_path=CONFIG_PATH, state_root=state_root)
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
        seeded_by_id = {item["seed_id"]: item for item in seeded_descriptors}
        retired_descriptors = []
        for seed_id in suite.get("retire_after_seed", []):
            seeded = seeded_by_id[seed_id]
            retirement = memory.retire_memory(
                memory_id=seeded["memory_id"],
                reviewer_id=reviewer_id,
                reason="gap2_retired_seed_for_visibility",
            )
            retired_descriptors.append(
                {
                    "seed_id": seed_id,
                    "memory_id": retirement["memory_id"],
                    "descriptor_id": retirement["descriptor_id"],
                    "decision_ref": retirement["decision_ref"],
                }
            )

        graph_manager.sync_from_memory(memory_manager=memory)
        request_results = [
            graph_manager.request_transfer(request=request_spec, authority_engine=authority)
            for request_spec in suite["transfer_requests"]
        ]
        graph = graph_manager.load_graph()
        transfer_log = graph_manager.load_transfer_log()
        summary = graph_manager.summary()
        transfer_reviews = [
            review
            for review in authority.load_reviews()
            if str(review.get("action")) == "transfer_approval"
        ]
        acceptance = _build_acceptance(
            summary=summary,
            request_results=request_results,
        )
        return {
            "suite_id": suite["suite_id"],
            "created_utc": utc_now_iso(),
            "config_ref": str(CONFIG_PATH.relative_to(REPO_ROOT)),
            "graph_summary": summary,
            "seeded_descriptors": seeded_descriptors,
            "retired_descriptors": retired_descriptors,
            "transfer_requests": request_results,
            "transfer_reviews": transfer_reviews,
            "graph": graph,
            "transfer_log": transfer_log,
            "acceptance": acceptance,
        }


def write_v1x_skill_graph_result_tables(results: dict[str, Any], *, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / RESULT_JSON_NAME
    markdown_path = output_dir / RESULT_MARKDOWN_NAME
    artifact = _normalize_artifact_results(results)
    json_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = artifact["graph_summary"]
    transfer_rows = []
    for request in artifact["transfer_requests"]:
        transfer_rows.append(
            "| "
            + " | ".join(
                [
                    request["request_id"],
                    str(request["selected_source_descriptor_id"] or "none"),
                    request["target_domain"],
                    "yes" if request["explicit_transfer_approval"] else "no",
                    request["status"],
                    f"{request['transfer_quality_score']:.3f}",
                    f"{request['baseline_support_score']:.3f}",
                    f"{request['target_support_score']:.3f}",
                    str(request["authority_review_id"] or "none"),
                ]
            )
            + " |"
        )

    seed_rows = []
    for seed in artifact["seeded_descriptors"]:
        seed_rows.append(
            "| "
            + " | ".join(
                [
                    seed["seed_id"],
                    seed["descriptor_id"],
                    seed["source_domain"],
                    seed["memory_class"],
                    f"{seed['trust_score']:.3f}",
                    f"{seed['provenance_score']:.3f}",
                ]
            )
            + " |"
        )

    retired_rows = []
    for retired in artifact["retired_descriptors"]:
        retired_rows.append(
            "| "
            + " | ".join(
                [
                    retired["seed_id"],
                    retired["descriptor_id"],
                    retired["memory_id"],
                    retired["decision_ref"],
                ]
            )
            + " |"
        )
    if not retired_rows:
        retired_rows.append("| none | none | none | none |")

    provenance_rows = []
    for request in artifact["transfer_requests"]:
        materialized = request.get("materialized_transfer")
        if not isinstance(materialized, dict):
            continue
        provenance = materialized["provenance_bundle"]
        provenance_rows.append(
            "| "
            + " | ".join(
                [
                    materialized["transfer_descriptor_id"],
                    provenance["source_descriptor_id"],
                    str(provenance["source_memory_id"]),
                    str(provenance["source_payload_ref"]),
                    provenance["transfer_approval_ref"],
                    provenance["target_domain"],
                ]
            )
            + " |"
        )
    if not provenance_rows:
        provenance_rows.append("| none | none | none | none | none | none |")

    acceptance = artifact["acceptance"]
    markdown_lines = [
        "# V1X Skill Graph Transfer Results",
        "",
        "Locally verified deterministic benchmark summary for Track B Gap 2.",
        "",
        "## Graph Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Source descriptor count | {summary['source_descriptor_count']} |",
        f"| Retired source descriptor count | {summary['retired_source_descriptor_count']} |",
        f"| Transferred descriptor count | {summary['transferred_descriptor_count']} |",
        f"| Graph edge count | {summary['edge_count']} |",
        f"| Transfer approval edges | {summary['relation_counts'].get('transfer_approval', 0)} |",
        f"| Explicit provenance count | {summary['explicit_provenance_count']} |",
        "",
        "## Seeded Source Descriptors",
        "",
        "| Seed | Descriptor ID | Source Domain | Memory Class | Trust | Provenance |",
        "| --- | --- | --- | --- | ---: | ---: |",
        *seed_rows,
        "",
        "## Retired Source Visibility",
        "",
        "| Seed | Descriptor ID | Memory ID | Decision Ref |",
        "| --- | --- | --- | --- |",
        *retired_rows,
        "",
        "## Transfer Requests",
        "",
        "| Request | Selected Source | Target Domain | Explicit Approval | Status | Quality | Baseline Support | Target Support | Review Ref |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        *transfer_rows,
        "",
        "## Materialized Provenance",
        "",
        "| Transfer Descriptor | Source Descriptor | Source Memory | Source Payload Ref | Approval Ref | Target Domain |",
        "| --- | --- | --- | --- | --- | --- |",
        *provenance_rows,
        "",
        "## Acceptance",
        "",
        "| Check | Passed |",
        "| --- | --- |",
        f"| Descriptor graph exists | {'yes' if acceptance['descriptor_graph_exists'] else 'no'} |",
        f"| Transfer approval path exists | {'yes' if acceptance['transfer_approval_path_exists'] else 'no'} |",
        f"| Provenance is explicit | {'yes' if acceptance['provenance_explicit'] else 'no'} |",
        f"| Low-quality transfer abstains or is denied | {'yes' if acceptance['low_quality_transfer_abstains_or_denied'] else 'no'} |",
        f"| Cross-domain transfer requires explicit approval | {'yes' if acceptance['cross_domain_requires_explicit_transfer_approval'] else 'no'} |",
        f"| Authority veto is visible | {'yes' if acceptance['authority_veto_visible'] else 'no'} |",
        f"| Retirement is visible | {'yes' if acceptance['retirement_visibility'] else 'no'} |",
        f"| Transfer is useful and auditable | {'yes' if acceptance['useful_and_auditable'] else 'no'} |",
        f"| Overall pass | {'yes' if acceptance['passed'] else 'no'} |",
    ]
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _load_suite() -> dict[str, Any]:
    payload = load_json_file(
        SUITE_PATH,
        not_found_code="CONFIG_INVALID",
        invalid_code="CONFIG_INVALID",
        label="Track B Gap 2 suite",
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Gap 2 suite must be an object.")
    if not isinstance(payload.get("seed_descriptors"), list) or len(payload["seed_descriptors"]) < 3:
        raise RuntimeError("Gap 2 suite must define at least three seeded source descriptors.")
    if not isinstance(payload.get("transfer_requests"), list) or len(payload["transfer_requests"]) < 4:
        raise RuntimeError("Gap 2 suite must define at least four transfer requests.")
    return deepcopy(payload)


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
        reason=f"gap2_seed:{seed_spec['seed_id']}",
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


def _build_acceptance(
    *,
    summary: dict[str, Any],
    request_results: list[dict[str, Any]],
) -> dict[str, Any]:
    requests_by_id = {request["request_id"]: request for request in request_results}
    approved = requests_by_id["approved_cross_domain_invoice_transfer"]
    low_quality = requests_by_id["abstained_low_quality_transfer"]
    missing_explicit = requests_by_id["denied_missing_explicit_transfer_approval"]
    boundary_denied = requests_by_id["denied_out_of_boundary_transfer"]
    materialized = approved.get("materialized_transfer") or {}
    provenance = materialized.get("provenance_bundle") or {}

    acceptance = {
        "descriptor_graph_exists": summary["source_descriptor_count"] >= 3 and summary["edge_count"] >= 1,
        "transfer_approval_path_exists": approved["status"] == "approved"
        and approved["required_action"] == "transfer_approval"
        and bool(approved["authority_review_id"]),
        "provenance_explicit": all(
            bool(provenance.get(field_name))
            for field_name in (
                "source_descriptor_id",
                "source_memory_id",
                "source_payload_ref",
                "source_trust_ref",
                "transfer_descriptor_id",
                "transfer_approval_ref",
            )
        ),
        "low_quality_transfer_abstains_or_denied": low_quality["status"] in {"abstained", "denied"},
        "cross_domain_requires_explicit_transfer_approval": missing_explicit["status"] == "denied"
        and missing_explicit["decision_reason"] == "missing_explicit_transfer_approval",
        "authority_veto_visible": boundary_denied["status"] == "denied"
        and boundary_denied["authority_decision"] == "vetoed",
        "retirement_visibility": summary["retired_source_descriptor_count"] >= 1,
        "useful_and_auditable": approved["target_support_score"] > approved["baseline_support_score"]
        and bool(approved["audit_ready"])
        and summary["explicit_provenance_count"] >= 1,
    }
    acceptance["passed"] = all(acceptance.values())
    return acceptance


def _normalize_artifact_results(results: dict[str, Any]) -> dict[str, Any]:
    artifact = {
        "suite_id": results["suite_id"],
        "config_ref": results["config_ref"],
        "graph_summary": deepcopy(results["graph_summary"]),
        "seeded_descriptors": deepcopy(results["seeded_descriptors"]),
        "retired_descriptors": deepcopy(results["retired_descriptors"]),
        "transfer_requests": deepcopy(results["transfer_requests"]),
        "acceptance": deepcopy(results["acceptance"]),
    }
    for retired in artifact["retired_descriptors"]:
        retired["decision_ref"] = _normalize_ref(retired.get("decision_ref"))
    for request in artifact["transfer_requests"]:
        request.pop("created_utc", None)
        provenance = request.get("provenance_bundle")
        if isinstance(provenance, dict):
            provenance["source_payload_ref"] = _normalize_ref(provenance.get("source_payload_ref"))
        materialized = request.get("materialized_transfer")
        if isinstance(materialized, dict):
            materialized.pop("created_utc", None)
            materialized["provenance_bundle"]["source_payload_ref"] = _normalize_ref(
                materialized["provenance_bundle"].get("source_payload_ref")
            )
    return artifact


def _normalize_ref(value: Any) -> Any:
    if not isinstance(value, str) or value.strip() == "":
        return value
    path = Path(value)
    parts = list(path.parts)
    for marker in ("memory", "descriptors", "governance"):
        if marker in parts:
            return "/".join(parts[parts.index(marker) :])
    return str(path)
