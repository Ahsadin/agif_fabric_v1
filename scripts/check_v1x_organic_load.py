#!/usr/bin/env python3
"""Verifier for Track B Gap 1 organic split usefulness proof."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_TABLE_DIR = REPO_ROOT / "06_outputs" / "result_tables"
EVIDENCE_PATH = REPO_ROOT / "05_testing" / "V1X_ORGANIC_LOAD_EVIDENCE.md"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intelligence.fabric.benchmarking.v1x_organic_load import (  # noqa: E402
    run_v1x_organic_load_benchmark,
    write_v1x_organic_load_result_tables,
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
        "test_v1x_organic_load.py",
    ]
    test_result = subprocess.run(test_command, cwd=str(REPO_ROOT), check=False)
    if test_result.returncode != 0:
        return test_result.returncode

    results = run_v1x_organic_load_benchmark()
    write_v1x_organic_load_result_tables(results, output_dir=RESULT_TABLE_DIR)

    require(EVIDENCE_PATH.is_file(), "Gap 1 evidence note is missing.")
    require((RESULT_TABLE_DIR / "v1x_finance_organic_load.md").is_file(), "Gap 1 markdown result table is missing.")
    require((RESULT_TABLE_DIR / "v1x_finance_organic_load.json").is_file(), "Gap 1 JSON result table is missing.")

    acceptance = results["acceptance"]
    require(bool(acceptance["split_occurs_inside_stream"]), "Gap 1 failed: no organic split occurred inside the 40-case stream.")
    require(bool(acceptance["control_has_no_split_transition"]), "Gap 1 failed: the control run allowed a split transition.")
    require(bool(acceptance["same_case_sequence"]), "Gap 1 failed: elastic and control did not use the same ordered 40-case stream.")
    require(bool(acceptance["accuracy_preserved_or_improved"]), "Gap 1 failed: elastic accuracy regressed against control.")
    require(bool(acceptance["queue_or_latency_improved"]), "Gap 1 failed: elastic did not improve queue age or end-to-end latency.")
    require(bool(acceptance["population_returns_near_start"]), "Gap 1 failed: elastic active population did not return near the starting level.")
    require(bool(acceptance["usefulness_not_just_activity"]), "Gap 1 failed: a split happened but usefulness was not proven.")
    require(bool(acceptance["passed"]), "Gap 1 failed the combined acceptance gate.")

    elastic = results["runs"]["elastic"]
    control = results["runs"]["control"]
    require(elastic["split_event_count"] >= 1, "Gap 1 failed: elastic split count stayed at zero.")
    require(control["split_event_count"] == 0, "Gap 1 failed: control recorded a split event.")
    require(elastic["merge_event_count"] >= 1, "Gap 1 failed: elastic did not record a merge or return-to-steady structural outcome.")
    require(
        float(elastic["metrics"]["mean_queue_age_units"]) < float(control["metrics"]["mean_queue_age_units"]),
        "Gap 1 failed: elastic queue age did not improve against control.",
    )
    require(
        float(elastic["metrics"]["mean_end_to_end_latency_units"]) < float(control["metrics"]["mean_end_to_end_latency_units"]),
        "Gap 1 failed: elastic end-to-end latency did not improve against control.",
    )
    require(
        float(elastic["metrics"]["task_accuracy"]) >= float(control["metrics"]["task_accuracy"]),
        "Gap 1 failed: elastic accuracy must preserve or improve against control.",
    )
    require(
        int(elastic["population"]["after_settle"]["active_population"]) <= int(elastic["population"]["initial"]["active_population"]) + 1,
        "Gap 1 failed: elastic post-settle active population is not near the starting level.",
    )

    print("AGIF_FABRIC_V1X_G1_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
