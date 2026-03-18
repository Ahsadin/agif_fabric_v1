#!/usr/bin/env python3
"""Verifier for Track B Gap 3 bounded POS-domain causal transfer proof."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_TABLE_DIR = REPO_ROOT / "06_outputs" / "result_tables"
EVIDENCE_PATH = REPO_ROOT / "05_testing" / "V1X_POS_DOMAIN_EVIDENCE.md"
ROOT_PROGRESS_PATH = REPO_ROOT / "01_plan" / "PROGRESS_TRACKER.md"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intelligence.fabric.benchmarking.v1x_pos_domain import (  # noqa: E402
    run_v1x_pos_domain_benchmark,
    write_v1x_pos_domain_result_tables,
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
        "test_v1x_pos_domain.py",
    ]
    test_result = subprocess.run(test_command, cwd=str(REPO_ROOT), check=False)
    if test_result.returncode != 0:
        return test_result.returncode

    results = run_v1x_pos_domain_benchmark()
    write_v1x_pos_domain_result_tables(results, output_dir=RESULT_TABLE_DIR)

    require(EVIDENCE_PATH.is_file(), "Gap 3 evidence note is missing.")
    require((RESULT_TABLE_DIR / "v1x_pos_domain_transfer.md").is_file(), "Gap 3 markdown result table is missing.")
    require((RESULT_TABLE_DIR / "v1x_pos_domain_transfer.json").is_file(), "Gap 3 JSON result table is missing.")
    require("Progress now: `600/600`" in ROOT_PROGRESS_PATH.read_text(encoding="utf-8"), "Root AGIF v1 progress changed.")

    acceptance = results["acceptance"]
    require(bool(acceptance["bounded_pos_suite_frozen"]), "Gap 3 failed: POS suite is not frozen at five cases.")
    require(bool(acceptance["same_case_sequence"]), "Gap 3 failed: transfer-enabled and control runs diverged in case order.")
    require(
        bool(acceptance["control_disables_transfer_at_governance"]),
        "Gap 3 failed: control run did not disable cross-domain transfer at governance.",
    )
    require(
        bool(acceptance["finance_origin_descriptor_improves_pos_result"]),
        "Gap 3 failed: finance-origin descriptor did not improve a POS result.",
    )
    require(
        bool(acceptance["cross_domain_influence_requires_explicit_transfer_approval"]),
        "Gap 3 failed: cross-domain influence did not stay behind explicit transfer approval.",
    )
    require(bool(acceptance["useful_and_auditable"]), "Gap 3 failed: POS proof is not yet useful and auditable.")
    require(bool(acceptance["passed"]), "Gap 3 failed the combined acceptance gate.")

    enabled = results["runs"]["transfer_enabled"]
    control = results["runs"]["control"]
    comparison = results["comparison"]
    require(enabled["case_ids"] == control["case_ids"], "Gap 3 failed: same 5-case sequence was not preserved.")
    require(enabled["metrics"]["approved_transfer_count"] >= 1, "Gap 3 failed: no governed cross-domain transfer was approved.")
    require(
        control["metrics"]["governance_disabled_veto_count"] >= 1,
        "Gap 3 failed: governance-disabled control recorded no transfer veto.",
    )
    require(
        control["metrics"]["counted_cross_domain_influence_count"] == 0,
        "Gap 3 failed: control run still counted cross-domain influence.",
    )
    require(
        "northwind_settlement_alias_hold" in comparison["improved_case_ids"],
        "Gap 3 failed: expected Northwind POS causality case did not improve.",
    )

    print("AGIF_FABRIC_V1X_G3_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
