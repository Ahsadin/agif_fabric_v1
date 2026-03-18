#!/usr/bin/env python3
"""One-command local check for Phase 9 closure and package integrity."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE7_ARTIFACTS = [
    REPO_ROOT / "06_outputs" / "result_tables" / "phase7_benchmark_results.md",
    REPO_ROOT / "06_outputs" / "result_tables" / "phase7_benchmark_results.json",
]
PHASE8_BOUNDED_ARTIFACTS = [
    REPO_ROOT / "06_outputs" / "run_summaries" / "phase8_bounded_validation.md",
    REPO_ROOT / "06_outputs" / "run_summaries" / "phase8_bounded_validation.json",
]
REQUIRED_FILES = [
    REPO_ROOT / "PROJECT_README.md",
    REPO_ROOT / "02_requirements" / "PROOF_BOUNDARY.md",
    REPO_ROOT / "02_requirements" / "FALSIFICATION_THRESHOLDS.md",
    REPO_ROOT / "05_testing" / "PHASE8_LONGRUN_EVIDENCE.md",
    REPO_ROOT / "05_testing" / "PHASE9_CLOSURE_EVIDENCE.md",
    REPO_ROOT / "06_outputs" / "evidence_bundle_manifests" / "phase9_claims_to_evidence_matrix.md",
    REPO_ROOT / "06_outputs" / "evidence_bundle_manifests" / "phase9_reproducibility_package.md",
    REPO_ROOT / "06_outputs" / "paper_drafts" / "README.md",
    REPO_ROOT / "06_outputs" / "run_summaries" / "phase8_bounded_validation.md",
    REPO_ROOT / "06_outputs" / "run_summaries" / "phase8_bounded_validation.json",
    REPO_ROOT / "06_outputs" / "run_summaries" / "phase8_real_24h_soak.md",
    REPO_ROOT / "06_outputs" / "run_summaries" / "phase8_real_72h_soak.md",
    REPO_ROOT / "08_logs" / "phase8_soak" / "run_24h" / "run_manifest.json",
    REPO_ROOT / "08_logs" / "phase8_soak" / "run_72h" / "run_manifest.json",
]
TEXT_CHECKS = {
    REPO_ROOT / "05_testing" / "PHASE9_CLOSURE_EVIDENCE.md": [
        "AGIF_FABRIC_P9_PASS",
        "MacBook Air",
        "MSI",
        "python3 scripts/check_phase9_closure.py",
    ],
    REPO_ROOT / "06_outputs" / "evidence_bundle_manifests" / "phase9_claims_to_evidence_matrix.md": [
        "backed locally + MSI artifact inspection",
        "explicit limitation",
        "explicit non-claim",
    ],
    REPO_ROOT / "06_outputs" / "evidence_bundle_manifests" / "phase9_reproducibility_package.md": [
        "python3 scripts/check_phase9_closure.py",
        "MacBook Air = development, documentation, benchmark, and primary target machine.",
        "MSI = imported long-run soak evidence machine.",
        "https://github.com/Ahsadin/agif_fabric_v1",
    ],
    REPO_ROOT / "06_outputs" / "paper_drafts" / "README.md": [
        "intentionally omitted from this public repo",
        "published later",
    ],
}
IMPORTED_RUN_EXPECTATIONS = {
    "run_24h": {
        "expected_cycles": 989,
        "resume_count": 1,
        "resume_recovery_count": 1,
        "expect_resume_events": True,
    },
    "run_72h": {
        "expected_cycles": 1690,
        "resume_count": 1,
        "resume_recovery_count": 0,
        "expect_resume_events": False,
    },
}
SIZE_LIMIT_BYTES = 35 * 1024 * 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        print(message, file=sys.stderr)
        raise SystemExit(1)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def snapshot_files(paths: list[Path]) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in paths}


def restore_files(snapshots: dict[Path, bytes]) -> None:
    for path, content in snapshots.items():
        path.write_bytes(content)


def check_required_files() -> None:
    for path in REQUIRED_FILES:
        require(path.is_file(), f"Missing required file: {path.relative_to(REPO_ROOT)}")
        require(path.stat().st_size > 0, f"Required file is empty: {path.relative_to(REPO_ROOT)}")


def check_required_text() -> None:
    for path, snippets in TEXT_CHECKS.items():
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            require(snippet in text, f"Missing required text in {path.relative_to(REPO_ROOT)}: {snippet}")


def check_repo_size() -> None:
    result = subprocess.run(
        ["du", "-sk", str(REPO_ROOT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    require(result.returncode == 0, "Could not measure repo size with du.")
    size_kib = int(result.stdout.split()[0])
    size_bytes = size_kib * 1024
    require(
        size_bytes <= SIZE_LIMIT_BYTES,
        f"Repo footprint exceeds the 35 GB limit: {size_bytes} bytes.",
    )


def check_phase7_determinism() -> None:
    baseline_hashes: dict[str, str] | None = None
    for _ in range(2):
        run_command([sys.executable, str(REPO_ROOT / "scripts" / "check_phase7_benchmarks.py")])
        current_hashes = {str(path.relative_to(REPO_ROOT)): file_hash(path) for path in PHASE7_ARTIFACTS}
        if baseline_hashes is None:
            baseline_hashes = current_hashes
        else:
            require(current_hashes == baseline_hashes, "Phase 7 result hashes changed across repeated reruns.")


def check_imported_runs() -> None:
    for run_name, expected in IMPORTED_RUN_EXPECTATIONS.items():
        run_root = REPO_ROOT / "08_logs" / "phase8_soak" / run_name
        manifest = json.loads((run_root / "run_manifest.json").read_text(encoding="utf-8"))
        require(manifest.get("status") == "completed", f"{run_name} manifest status is not completed.")
        require(
            manifest.get("completed_cycle_count") == expected["expected_cycles"],
            f"{run_name} completed cycle count is unexpected.",
        )
        require(manifest.get("resume_count") == expected["resume_count"], f"{run_name} resume count is unexpected.")
        require(
            manifest.get("resume_recovery_count") == expected["resume_recovery_count"],
            f"{run_name} resume recovery count is unexpected.",
        )
        resume_events = manifest.get("resume_events") or []
        if expected["expect_resume_events"]:
            require(bool(resume_events), f"{run_name} is missing expected resume events.")
        else:
            require(not resume_events, f"{run_name} unexpectedly records resume events.")

        evidence_dir = run_root / "evidence"
        evidence_numbers = sorted(
            int(path.stem.rsplit("_", 1)[-1]) for path in evidence_dir.glob("phase8_cycle_*.json")
        )
        expected_numbers = list(range(1, expected["expected_cycles"] + 1))
        require(evidence_numbers == expected_numbers, f"{run_name} evidence files are missing or not contiguous.")

        stress_results = manifest.get("stress_results") or {}
        require(stress_results, f"{run_name} stress results are missing.")
        for lane_name, lane_summary in stress_results.items():
            require(lane_summary.get("passed") is True, f"{run_name} stress lane did not pass: {lane_name}")


def main() -> int:
    check_required_files()
    check_required_text()
    phase8_snapshots = snapshot_files(PHASE8_BOUNDED_ARTIFACTS)
    try:
        run_command([sys.executable, str(REPO_ROOT / "scripts" / "check_phase8_soak.py")])
    finally:
        restore_files(phase8_snapshots)
    check_phase7_determinism()
    check_imported_runs()
    check_repo_size()
    print("AGIF_FABRIC_P9_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
