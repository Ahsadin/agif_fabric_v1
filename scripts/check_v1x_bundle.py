#!/usr/bin/env python3
"""Ordered verifier for Track B post-closure bundle closure."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_TABLE_DIR = REPO_ROOT / "06_outputs" / "result_tables"
EVIDENCE_PATH = REPO_ROOT / "05_testing" / "V1X_BUNDLE_CLOSURE_EVIDENCE.md"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intelligence.fabric.benchmarking.v1x_bundle import (  # noqa: E402
    REQUIRED_COMMAND_SPECS,
    run_v1x_bundle_benchmark,
    write_v1x_bundle_result_tables,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        print(message, file=sys.stderr)
        raise SystemExit(1)


def run_command(command: str, expected_token: str) -> dict[str, str | int]:
    result = subprocess.run(
        command.split(),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        raise SystemExit(result.returncode)
    require(expected_token in result.stdout, f"Missing expected token after running `{command}`: {expected_token}")
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    command_log = [
        run_command(spec["command"], spec["expected_token"])
        for spec in REQUIRED_COMMAND_SPECS
    ]

    results = run_v1x_bundle_benchmark(command_log=command_log)
    write_v1x_bundle_result_tables(results, output_dir=RESULT_TABLE_DIR)

    require(EVIDENCE_PATH.is_file(), "Bundle closure evidence note is missing.")
    require((RESULT_TABLE_DIR / "v1x_bundle_closure.md").is_file(), "Bundle markdown result table is missing.")
    require((RESULT_TABLE_DIR / "v1x_bundle_closure.json").is_file(), "Bundle JSON result table is missing.")
    require(bool(results["acceptance"]["passed"]), "Track B bundle closure failed the combined acceptance gate.")

    print("AGIF_FABRIC_V1X_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
