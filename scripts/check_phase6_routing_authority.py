#!/usr/bin/env python3
"""Deterministic local check for Phase 6 and Phase 6.5 routing, utility, need signals, and authority."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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
            "test_phase6_routing_authority.py",
        ],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase5_memory.py")],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase4_lifecycle.py")],
        [sys.executable, str(REPO_ROOT / "scripts" / "check_phase3_foundation.py")],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
        if result.returncode != 0:
            return result.returncode
    print("AGIF_FABRIC_P6_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
