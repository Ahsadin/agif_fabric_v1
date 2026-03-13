#!/usr/bin/env python3
"""Run the Phase 8 soak harness with optional wakelock support."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from intelligence.fabric.benchmarking.phase8 import PHASE8_SHORT_PROFILE, run_phase8_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Phase 8 soak harness.")
    parser.add_argument(
        "--profile",
        default=str(PHASE8_SHORT_PROFILE),
        help="Path to the Phase 8 soak profile JSON.",
    )
    parser.add_argument(
        "--run-root",
        default=str(REPO_ROOT / "08_logs" / "phase8_soak" / "latest"),
        help="Directory used for the resumable manifest and runtime state.",
    )
    parser.add_argument(
        "--wakelock",
        choices=("auto", "caffeinate", "none"),
        default="auto",
        help="Use macOS caffeinate when available for long runs.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional cap used for bounded debugging or resume testing.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start a fresh run root instead of resuming an existing manifest.",
    )
    parser.add_argument(
        "--wakelock-active",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def maybe_reexec_with_caffeinate(args: argparse.Namespace) -> int | None:
    if args.wakelock == "none" or args.wakelock_active:
        return None
    caffeinate = shutil.which("caffeinate")
    if caffeinate is None:
        return None

    profile_name = Path(args.profile).name
    if args.wakelock == "auto" and "24h" not in profile_name and "72h" not in profile_name:
        return None

    command = [
        caffeinate,
        "-dimsu",
        sys.executable,
        str(Path(__file__).resolve()),
        "--profile",
        str(args.profile),
        "--run-root",
        str(args.run_root),
        "--wakelock",
        "none",
        "--wakelock-active",
    ]
    if args.max_steps is not None:
        command.extend(["--max-steps", str(args.max_steps)])
    if args.no_resume:
        command.append("--no-resume")
    result = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    return result.returncode


def main() -> int:
    args = parse_args()
    reexec_code = maybe_reexec_with_caffeinate(args)
    if reexec_code is not None:
        return reexec_code

    result = run_phase8_profile(
        Path(args.profile),
        run_root=Path(args.run_root),
        resume=not args.no_resume,
        max_steps=args.max_steps,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["completion"]["bounded_validation_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
