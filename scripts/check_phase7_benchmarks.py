#!/usr/bin/env python3
"""Deterministic local check for Phase 7 tissues, benchmarks, and regressions."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_TABLE_DIR = REPO_ROOT / "06_outputs" / "result_tables"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intelligence.fabric.benchmarking.phase7 import run_phase7_benchmarks, write_phase7_result_tables


def main() -> int:
    commands = [
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(REPO_ROOT / "05_testing"),
            "-p",
            "test_phase7_benchmarks.py",
        ],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase6_routing_authority.py")],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase5_memory.py")],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase4_lifecycle.py")],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase3_foundation.py")],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
        if result.returncode != 0:
            return result.returncode

    results = run_phase7_benchmarks()
    write_phase7_result_tables(results, output_dir=RESULT_TABLE_DIR)
    if not results["comparisons"]["usefulness_gate_passed"]:
        print("Phase 7 usefulness gate failed.", file=sys.stderr)
        return 1
    with_adapt = results["classes"]["multi_cell_with_bounded_adaptation"]["metrics"]
    if with_adapt["replay_determinism"] != 1.0:
        print("Phase 7 replay determinism check failed.", file=sys.stderr)
        return 1
    if with_adapt["descriptor_reuse_rate"] <= 0.0:
        print("Phase 7 descriptor reuse check failed.", file=sys.stderr)
        return 1
    if with_adapt["bounded_forgetting"] > 0.1:
        print("Phase 7 bounded forgetting threshold failed.", file=sys.stderr)
        return 1
    if with_adapt["resource_usage"]["retained_memory_delta_bytes"] <= 0:
        print("Phase 7 retained memory delta check failed.", file=sys.stderr)
        return 1
    if with_adapt["resource_usage"]["governance_overhead_share"] <= 0.0:
        print("Phase 7 governance overhead reporting check failed.", file=sys.stderr)
        return 1
    if "structural_signal_cases" not in with_adapt["split_merge_efficiency"]:
        print("Phase 7 structural signal check failed.", file=sys.stderr)
        return 1
    if "future_trigger" not in with_adapt["split_merge_efficiency"]:
        print("Phase 7 structural future trigger check failed.", file=sys.stderr)
        return 1
    with_adapt_analytics = results["classes"]["multi_cell_with_bounded_adaptation"]["analytics"]["tissues"]
    if with_adapt_analytics["finance_validation_correction_tissue"]["reuse_contribution"] <= 0:
        print("Phase 7 tissue reuse analytics check failed.", file=sys.stderr)
        return 1
    if not any(row.get("reason_summary") for row in results["comparisons"]["case_rows"]):
        print("Phase 7 comparison explanation check failed.", file=sys.stderr)
        return 1
    case_rows = {row["case_id"]: row for row in results["comparisons"]["case_rows"]}
    high_value_hold = case_rows.get("invoice_high_value_alias_hold")
    if high_value_hold is None:
        print("Phase 7.6 hardening case is missing.", file=sys.stderr)
        return 1
    if "desc_" not in str(high_value_hold.get("with_adapt_descriptor_detail", "")):
        print("Phase 7 descriptor custody detail check failed.", file=sys.stderr)
        return 1
    if "hold_for_review" not in str(high_value_hold.get("with_adapt_governance_detail", "")):
        print("Phase 7 governance custody detail check failed.", file=sys.stderr)
        return 1
    if "handoffs=" not in str(high_value_hold.get("with_adapt_route_of_custody", "")):
        print("Phase 7 route-of-custody detail check failed.", file=sys.stderr)
        return 1
    print("AGIF_FABRIC_P7_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
