#!/usr/bin/env python3
"""Minimal verifier for Track B setup-and-freeze closure."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRACK_B_ROOT = REPO_ROOT / "projects" / "agif_v1_postclosure_extensions"

REQUIRED_FILES = [
    TRACK_B_ROOT / "PROJECT_README.md",
    TRACK_B_ROOT / "DECISIONS.md",
    TRACK_B_ROOT / "CHANGELOG.md",
    TRACK_B_ROOT / "01_plan" / "PROGRESS_TRACKER.md",
    TRACK_B_ROOT / "01_plan" / "PHASE_GATE_CHECKLIST.md",
    TRACK_B_ROOT / "02_requirements" / "TRACK_B_SCOPE_AND_GATES.md",
    TRACK_B_ROOT / "05_testing" / "PASS_TOKENS.md",
    TRACK_B_ROOT / "05_testing" / "TRACK_B_SETUP_FREEZE_EVIDENCE.md",
]

TEXT_CHECKS = {
    TRACK_B_ROOT / "PROJECT_README.md": [
        "separate post-closure extension work",
        "Root AGIF v1 remains closed at `600/600`.",
        "Track B progress must never be counted inside the root AGIF v1 tracker.",
        "Total extension denominator: `130`",
        "setup and freeze: `15`",
        "organic split or merge proof: `35`",
        "skill graph and transfer-governance proof: `35`",
        "second bounded proof domain and cross-domain transfer proof: `45`",
        "Final bundle verifier must run in order: Gap 1, then Gap 2, then Gap 3.",
        "If no organic split occurs inside the `40`-case stream, the Gap 1 acceptance gate fails.",
        "Cross-domain influence counts only when there is explicit `transfer_approval`.",
        "`AGIF_FABRIC_V1X_SETUP_PASS` is earned.",
    ],
    TRACK_B_ROOT / "02_requirements" / "TRACK_B_SCOPE_AND_GATES.md": [
        "Bundle close must run the proofs in order: Gap 1, then Gap 2, then Gap 3.",
        "The elastic run and the no-split control run use the same `40`-case sequence in the same order.",
        "No fake stress-mode switch is allowed inside the stream.",
        "If no organic split occurs inside the `40`-case stream, the Gap 1 acceptance gate fails.",
        "The control run disables cross-domain transfer at the governance level.",
        "The transfer-enabled run uses the same `5`-case suite in the same order.",
        "explicit `transfer_approval`",
    ],
    TRACK_B_ROOT / "01_plan" / "PROGRESS_TRACKER.md": [
        "Total extension denominator: `130`",
        "| Setup and freeze | 15 | Complete and locally verified |",
        "`AGIF_FABRIC_V1X_SETUP_PASS` is earned.",
        "Root AGIF v1 remains frozen at `600/600`.",
    ],
    TRACK_B_ROOT / "01_plan" / "PHASE_GATE_CHECKLIST.md": [
        "- [x] project-local source-of-truth files exist",
        "- [x] fixed denominator `130` is recorded locally",
        "- [x] extension tokens are recorded locally",
        "- [x] final bundle verifier order is frozen as Gap 1 -> Gap 2 -> Gap 3",
        "- [x] `python3 scripts/check_v1x_setup.py` passes locally",
        "- [x] `AGIF_FABRIC_V1X_SETUP_PASS` is earned honestly",
    ],
    TRACK_B_ROOT / "05_testing" / "PASS_TOKENS.md": [
        "## Current Earned Tokens",
        "- `AGIF_FABRIC_V1X_SETUP_PASS`",
    ],
    TRACK_B_ROOT / "05_testing" / "TRACK_B_SETUP_FREEZE_EVIDENCE.md": [
        "`python3 scripts/check_v1x_setup.py`",
        "`AGIF_FABRIC_V1X_SETUP_PASS`",
        "No Gap 1 runtime, benchmark, or proof result is claimed here.",
    ],
    REPO_ROOT / "01_plan" / "PROGRESS_TRACKER.md": [
        "Progress now: `600/600`",
    ],
}


def require(condition: bool, message: str) -> None:
    if not condition:
        print(message, file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    for path in REQUIRED_FILES:
        require(path.is_file(), f"Missing required file: {path.relative_to(REPO_ROOT)}")
        require(path.stat().st_size > 0, f"Required file is empty: {path.relative_to(REPO_ROOT)}")

    for path, snippets in TEXT_CHECKS.items():
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            require(snippet in text, f"Missing required text in {path.relative_to(REPO_ROOT)}: {snippet}")

    print("AGIF_FABRIC_V1X_SETUP_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
