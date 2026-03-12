#!/usr/bin/env python3
"""Deterministic local check for the Phase 3 foundation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(REPO_ROOT / "05_testing"),
        "-p",
        "test_phase3_foundation.py",
    ]
    result = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    if result.returncode != 0:
        return result.returncode
    print("AGIF_FABRIC_P3_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

