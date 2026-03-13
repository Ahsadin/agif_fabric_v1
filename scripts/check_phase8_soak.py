#!/usr/bin/env python3
"""Bounded local check for the Phase 8 soak harness and regressions."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "06_outputs" / "run_summaries"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intelligence.fabric.benchmarking.phase8 import run_phase8_bounded_validation


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
            "test_phase8_soak.py",
        ],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase7_benchmarks.py")],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
        if result.returncode != 0:
            return result.returncode

    validation = run_phase8_bounded_validation(output_dir=OUTPUT_DIR)
    completion = validation["completion"]
    if not completion["bounded_validation_ready"]:
        print("Phase 8 bounded validation is not ready.", file=sys.stderr)
        return 1
    print("AGIF_FABRIC_P8_HARNESS_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
