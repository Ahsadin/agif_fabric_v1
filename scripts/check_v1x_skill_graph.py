#!/usr/bin/env python3
"""Verifier for Track B Gap 2 governed skill-graph proof."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_TABLE_DIR = REPO_ROOT / "06_outputs" / "result_tables"
EVIDENCE_PATH = REPO_ROOT / "05_testing" / "V1X_SKILL_GRAPH_EVIDENCE.md"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intelligence.fabric.benchmarking.v1x_skill_graph import (  # noqa: E402
    run_v1x_skill_graph_benchmark,
    write_v1x_skill_graph_result_tables,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        print(message, file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    test_command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(REPO_ROOT / "05_testing"),
        "-p",
        "test_v1x_skill_graph.py",
    ]
    test_result = subprocess.run(test_command, cwd=str(REPO_ROOT), check=False)
    if test_result.returncode != 0:
        return test_result.returncode

    results = run_v1x_skill_graph_benchmark()
    write_v1x_skill_graph_result_tables(results, output_dir=RESULT_TABLE_DIR)

    require(EVIDENCE_PATH.is_file(), "Gap 2 evidence note is missing.")
    require((RESULT_TABLE_DIR / "v1x_skill_graph_transfer.md").is_file(), "Gap 2 markdown result table is missing.")
    require((RESULT_TABLE_DIR / "v1x_skill_graph_transfer.json").is_file(), "Gap 2 JSON result table is missing.")

    acceptance = results["acceptance"]
    require(bool(acceptance["descriptor_graph_exists"]), "Gap 2 failed: descriptor graph does not exist or stayed empty.")
    require(bool(acceptance["transfer_approval_path_exists"]), "Gap 2 failed: transfer approval path is missing.")
    require(bool(acceptance["provenance_explicit"]), "Gap 2 failed: transferred descriptor provenance is incomplete.")
    require(
        bool(acceptance["low_quality_transfer_abstains_or_denied"]),
        "Gap 2 failed: low-quality transfer did not abstain or deny.",
    )
    require(
        bool(acceptance["cross_domain_requires_explicit_transfer_approval"]),
        "Gap 2 failed: cross-domain transfer did not require explicit transfer_approval.",
    )
    require(bool(acceptance["authority_veto_visible"]), "Gap 2 failed: authority veto visibility is missing.")
    require(bool(acceptance["retirement_visibility"]), "Gap 2 failed: retired descriptor visibility is missing.")
    require(bool(acceptance["useful_and_auditable"]), "Gap 2 failed: transfer path is not yet useful and auditable.")
    require(bool(acceptance["passed"]), "Gap 2 failed the combined acceptance gate.")

    summary = results["graph_summary"]
    require(summary["source_descriptor_count"] >= 3, "Gap 2 failed: expected at least three source descriptors in the graph.")
    require(summary["retired_source_descriptor_count"] >= 1, "Gap 2 failed: retired source descriptor count stayed at zero.")
    require(summary["approved_transfer_count"] >= 1, "Gap 2 failed: no transfer was approved.")
    require(summary["explicit_provenance_count"] >= 1, "Gap 2 failed: no explicit provenance bundle was materialized.")
    require(summary["relation_counts"].get("transfer_approval", 0) >= 1, "Gap 2 failed: no transfer_approval edge was recorded.")

    approved = next(item for item in results["transfer_requests"] if item["request_id"] == "approved_cross_domain_invoice_transfer")
    require(approved["status"] == "approved", "Gap 2 failed: the intended approved transfer did not pass.")
    require(
        approved["target_support_score"] > approved["baseline_support_score"],
        "Gap 2 failed: approved transfer did not improve target support.",
    )
    require(bool(approved["authority_review_id"]), "Gap 2 failed: approved transfer is missing its authority review.")
    require(bool(approved["audit_ready"]), "Gap 2 failed: approved transfer is not audit ready.")

    print("AGIF_FABRIC_V1X_G2_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
