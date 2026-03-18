"""Track B ordered bundle summary for post-closure extension closure."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from intelligence.fabric.common import load_json_file, repo_relative, utc_now_iso
from intelligence.fabric.benchmarking.phase7 import REPO_ROOT


TRACK_B_ROOT = REPO_ROOT / "projects" / "agif_v1_postclosure_extensions"
RESULT_TABLE_DIR = REPO_ROOT / "06_outputs" / "result_tables"
ORGANIC_RESULT_PATH = RESULT_TABLE_DIR / "v1x_finance_organic_load.json"
SKILL_RESULT_PATH = RESULT_TABLE_DIR / "v1x_skill_graph_transfer.json"
POS_RESULT_PATH = RESULT_TABLE_DIR / "v1x_pos_domain_transfer.json"
ROOT_PROGRESS_PATH = REPO_ROOT / "01_plan" / "PROGRESS_TRACKER.md"
ROOT_PASS_TOKENS_PATH = REPO_ROOT / "05_testing" / "PASS_TOKENS.md"
ROOT_PHASE9_EVIDENCE_PATH = REPO_ROOT / "05_testing" / "PHASE9_CLOSURE_EVIDENCE.md"
TRACK_B_PROGRESS_PATH = TRACK_B_ROOT / "01_plan" / "PROGRESS_TRACKER.md"
TRACK_B_PASS_TOKENS_PATH = TRACK_B_ROOT / "05_testing" / "PASS_TOKENS.md"
TRACK_B_CHECKLIST_PATH = TRACK_B_ROOT / "01_plan" / "PHASE_GATE_CHECKLIST.md"
TRACK_B_README_PATH = TRACK_B_ROOT / "PROJECT_README.md"
BUNDLE_EVIDENCE_PATH = REPO_ROOT / "05_testing" / "V1X_BUNDLE_CLOSURE_EVIDENCE.md"
RESULT_JSON_NAME = "v1x_bundle_closure.json"
RESULT_MARKDOWN_NAME = "v1x_bundle_closure.md"

TRACK_B_TOKENS = [
    "AGIF_FABRIC_V1X_SETUP_PASS",
    "AGIF_FABRIC_V1X_G1_PASS",
    "AGIF_FABRIC_V1X_G2_PASS",
    "AGIF_FABRIC_V1X_G3_PASS",
    "AGIF_FABRIC_V1X_PASS",
]

REQUIRED_COMMAND_SPECS = [
    {
        "step_id": "setup_prerequisite",
        "label": "Setup prerequisite",
        "command": "python3 scripts/check_v1x_setup.py",
        "expected_token": "AGIF_FABRIC_V1X_SETUP_PASS",
    },
    {
        "step_id": "gap_1",
        "label": "Gap 1 organic load",
        "command": "python3 scripts/check_v1x_organic_load.py",
        "expected_token": "AGIF_FABRIC_V1X_G1_PASS",
    },
    {
        "step_id": "gap_2",
        "label": "Gap 2 skill graph",
        "command": "python3 scripts/check_v1x_skill_graph.py",
        "expected_token": "AGIF_FABRIC_V1X_G2_PASS",
    },
    {
        "step_id": "gap_3",
        "label": "Gap 3 POS domain",
        "command": "python3 scripts/check_v1x_pos_domain.py",
        "expected_token": "AGIF_FABRIC_V1X_G3_PASS",
    },
    {
        "step_id": "root_phase9",
        "label": "Root Phase 9 closure re-check",
        "command": "python3 scripts/check_phase9_closure.py",
        "expected_token": "AGIF_FABRIC_P9_PASS",
    },
]


def run_v1x_bundle_benchmark(*, command_log: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    organic = load_json_file(
        ORGANIC_RESULT_PATH,
        not_found_code="CONFIG_INVALID",
        invalid_code="CONFIG_INVALID",
        label="Track B Gap 1 result table",
    )
    skill = load_json_file(
        SKILL_RESULT_PATH,
        not_found_code="CONFIG_INVALID",
        invalid_code="CONFIG_INVALID",
        label="Track B Gap 2 result table",
    )
    pos = load_json_file(
        POS_RESULT_PATH,
        not_found_code="CONFIG_INVALID",
        invalid_code="CONFIG_INVALID",
        label="Track B Gap 3 result table",
    )

    root_progress_text = ROOT_PROGRESS_PATH.read_text(encoding="utf-8")
    root_tokens_text = ROOT_PASS_TOKENS_PATH.read_text(encoding="utf-8")
    root_phase9_text = ROOT_PHASE9_EVIDENCE_PATH.read_text(encoding="utf-8")
    track_b_progress_text = TRACK_B_PROGRESS_PATH.read_text(encoding="utf-8")
    track_b_tokens_text = TRACK_B_PASS_TOKENS_PATH.read_text(encoding="utf-8")
    track_b_checklist_text = TRACK_B_CHECKLIST_PATH.read_text(encoding="utf-8")
    track_b_readme_text = TRACK_B_README_PATH.read_text(encoding="utf-8")
    bundle_evidence_text = BUNDLE_EVIDENCE_PATH.read_text(encoding="utf-8")

    command_chain = _build_command_chain(command_log or [])
    gap_chain = _build_gap_chain(organic=organic, skill=skill, pos=pos)
    root_recheck = _build_root_recheck(
        root_progress_text=root_progress_text,
        root_tokens_text=root_tokens_text,
        root_phase9_text=root_phase9_text,
    )
    track_b_record_status = _build_track_b_record_status(
        track_b_progress_text=track_b_progress_text,
        track_b_tokens_text=track_b_tokens_text,
        track_b_checklist_text=track_b_checklist_text,
        track_b_readme_text=track_b_readme_text,
        bundle_evidence_text=bundle_evidence_text,
    )
    acceptance = _build_acceptance(
        command_chain=command_chain,
        gap_chain=gap_chain,
        root_recheck=root_recheck,
        track_b_record_status=track_b_record_status,
        command_log_length=len(command_log or []),
    )
    return {
        "bundle_id": "agif_fabric_v1x_bundle",
        "created_utc": utc_now_iso(),
        "command_chain": command_chain,
        "gap_chain": gap_chain,
        "root_recheck": root_recheck,
        "track_b_record_status": track_b_record_status,
        "acceptance": acceptance,
    }


def write_v1x_bundle_result_tables(results: dict[str, Any], *, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / RESULT_JSON_NAME
    markdown_path = output_dir / RESULT_MARKDOWN_NAME
    artifact = _normalize_artifact_results(results)
    json_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    command_rows = []
    for entry in artifact["command_chain"]:
        command_rows.append(
            "| "
            + " | ".join(
                [
                    str(entry["order"]),
                    entry["label"],
                    entry["command"],
                    entry["expected_token"],
                    str(entry["returncode"]),
                    "yes" if entry["matched_expected_order"] else "no",
                    "yes" if entry["expected_token_present"] else "no",
                    str(entry["last_stdout_line"] or "none"),
                ]
            )
            + " |"
        )

    gap_rows = []
    for gap in artifact["gap_chain"]:
        support = gap["support"]
        support_text = ", ".join(f"{key}={value}" for key, value in support.items())
        gap_rows.append(
            "| "
            + " | ".join(
                [
                    str(gap["order"]),
                    gap["label"],
                    gap["required_token"],
                    "yes" if gap["accepted"] else "no",
                    support_text,
                    gap["result_ref"],
                    gap["evidence_ref"],
                ]
            )
            + " |"
        )

    root_rows = []
    for label, passed in (
        ("Root Phase 9 token is still recorded", artifact["root_recheck"]["phase9_token_recorded"]),
        ("Root Phase 9 evidence still points at local closure command", artifact["root_recheck"]["phase9_evidence_mentions_command"]),
        ("Root progress still reads 600/600", artifact["root_recheck"]["root_progress_still_600_of_600"]),
        ("Root pass-token file excludes Track B tokens", artifact["root_recheck"]["root_tokens_exclude_track_b_tokens"]),
    ):
        root_rows.append(f"| {label} | {'yes' if passed else 'no'} |")

    track_b_rows = []
    for label, passed in (
        ("Track B progress still reads 130/130", artifact["track_b_record_status"]["progress_still_130_of_130"]),
        ("Track B pass-token file records setup through bundle", artifact["track_b_record_status"]["all_track_b_tokens_recorded"]),
        ("Bundle checklist is fully checked", artifact["track_b_record_status"]["bundle_checklist_closed"]),
        ("Track B README records bundle closure", artifact["track_b_record_status"]["bundle_readme_closed"]),
        ("Bundle evidence note records local closure", artifact["track_b_record_status"]["bundle_evidence_recorded"]),
    ):
        track_b_rows.append(f"| {label} | {'yes' if passed else 'no'} |")

    acceptance = artifact["acceptance"]
    markdown_lines = [
        "# V1X Bundle Closure Results",
        "",
        "Locally verified ordered bundle summary for the Track B post-closure extension chain.",
        "",
        "## Ordered Command Chain",
        "",
        "| Order | Step | Command | Expected Token | Return Code | Expected Order | Token Seen | Last Stdout Line |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
        *command_rows,
        "",
        "## Gap Chain",
        "",
        "| Order | Gate | Required Token | Accepted | Key Support | Result Ref | Evidence Ref |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *gap_rows,
        "",
        "## Root Re-Check",
        "",
        "| Check | Passed |",
        "| --- | --- |",
        *root_rows,
        "",
        "## Track B Record Status",
        "",
        "| Check | Passed |",
        "| --- | --- |",
        *track_b_rows,
        "",
        "## Acceptance",
        "",
        "| Check | Passed |",
        "| --- | --- |",
        f"| Exact ordered command chain re-ran locally | {'yes' if acceptance['ordered_command_chain_passed'] else 'no'} |",
        f"| Setup prerequisite remains recorded | {'yes' if acceptance['setup_prerequisite_recorded'] else 'no'} |",
        f"| Gap 1 -> Gap 2 -> Gap 3 chain passes | {'yes' if acceptance['ordered_gap_chain_passed'] else 'no'} |",
        f"| Root AGIF v1 closure re-check passes | {'yes' if acceptance['root_closure_rechecked'] else 'no'} |",
        f"| Root AGIF v1 progress still reads 600/600 | {'yes' if acceptance['root_progress_still_600_of_600'] else 'no'} |",
        f"| Root pass tokens stay isolated from Track B tokens | {'yes' if acceptance['root_tokens_still_isolated'] else 'no'} |",
        f"| Track B progress still reads 130/130 | {'yes' if acceptance['track_b_progress_still_130_of_130'] else 'no'} |",
        f"| Track B local closure record is complete | {'yes' if acceptance['track_b_closure_record_complete'] else 'no'} |",
        f"| Overall pass | {'yes' if acceptance['passed'] else 'no'} |",
    ]
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _build_command_chain(command_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    command_chain: list[dict[str, Any]] = []
    for index, spec in enumerate(REQUIRED_COMMAND_SPECS):
        raw = command_log[index] if index < len(command_log) else {}
        stdout = str(raw.get("stdout") or "")
        stderr = str(raw.get("stderr") or "")
        token_lines = [line.strip() for line in stdout.splitlines() if "AGIF_" in line]
        last_stdout_line = _last_non_empty_line(stdout)
        command = str(raw.get("command") or "")
        returncode = int(raw.get("returncode", -1))
        command_chain.append(
            {
                "order": index + 1,
                "step_id": spec["step_id"],
                "label": spec["label"],
                "command": command,
                "expected_command": spec["command"],
                "expected_token": spec["expected_token"],
                "returncode": returncode,
                "matched_expected_order": command == spec["command"],
                "expected_token_present": spec["expected_token"] in stdout,
                "stdout_token_lines": token_lines,
                "last_stdout_line": last_stdout_line,
                "stderr_last_line": _last_non_empty_line(stderr),
            }
        )
    return command_chain


def _build_gap_chain(*, organic: dict[str, Any], skill: dict[str, Any], pos: dict[str, Any]) -> list[dict[str, Any]]:
    organic_support = {
        "case_count": organic["suite_summary"]["case_count"],
        "split_event_count": organic["runs"]["elastic"]["split_event_count"],
        "merge_event_count": organic["runs"]["elastic"]["merge_event_count"],
        "queue_age_gain_vs_control": round(
            float(organic["runs"]["control"]["metrics"]["mean_queue_age_units"])
            - float(organic["runs"]["elastic"]["metrics"]["mean_queue_age_units"]),
            6,
        ),
        "latency_gain_vs_control": round(
            float(organic["runs"]["control"]["metrics"]["mean_end_to_end_latency_units"])
            - float(organic["runs"]["elastic"]["metrics"]["mean_end_to_end_latency_units"]),
            6,
        ),
    }
    skill_support = {
        "source_descriptor_count": skill["graph_summary"]["source_descriptor_count"],
        "retired_source_descriptor_count": skill["graph_summary"]["retired_source_descriptor_count"],
        "approved_transfer_count": skill["graph_summary"]["approved_transfer_count"],
        "denied_transfer_count": skill["graph_summary"]["denied_transfer_count"],
        "abstained_transfer_count": skill["graph_summary"]["abstained_transfer_count"],
        "explicit_provenance_count": skill["graph_summary"]["explicit_provenance_count"],
    }
    pos_support = {
        "case_count": pos["suite_summary"]["case_count"],
        "approved_transfer_count": pos["runs"]["transfer_enabled"]["metrics"]["approved_transfer_count"],
        "counted_influence_count": pos["runs"]["transfer_enabled"]["metrics"]["counted_cross_domain_influence_count"],
        "control_governance_disabled_veto_count": pos["runs"]["control"]["metrics"]["governance_disabled_veto_count"],
        "improved_case_ids": ",".join(pos["comparison"]["improved_case_ids"]) or "none",
    }
    return [
        {
            "order": 1,
            "gate_id": "gap_1",
            "label": "Gap 1 organic load",
            "required_token": "AGIF_FABRIC_V1X_G1_PASS",
            "accepted": bool(organic["acceptance"]["passed"]),
            "support": organic_support,
            "result_ref": repo_relative(ORGANIC_RESULT_PATH),
            "evidence_ref": repo_relative(REPO_ROOT / "05_testing" / "V1X_ORGANIC_LOAD_EVIDENCE.md"),
        },
        {
            "order": 2,
            "gate_id": "gap_2",
            "label": "Gap 2 skill graph",
            "required_token": "AGIF_FABRIC_V1X_G2_PASS",
            "accepted": bool(skill["acceptance"]["passed"]),
            "support": skill_support,
            "result_ref": repo_relative(SKILL_RESULT_PATH),
            "evidence_ref": repo_relative(REPO_ROOT / "05_testing" / "V1X_SKILL_GRAPH_EVIDENCE.md"),
        },
        {
            "order": 3,
            "gate_id": "gap_3",
            "label": "Gap 3 POS domain",
            "required_token": "AGIF_FABRIC_V1X_G3_PASS",
            "accepted": bool(pos["acceptance"]["passed"]),
            "support": pos_support,
            "result_ref": repo_relative(POS_RESULT_PATH),
            "evidence_ref": repo_relative(REPO_ROOT / "05_testing" / "V1X_POS_DOMAIN_EVIDENCE.md"),
        },
    ]


def _build_root_recheck(
    *,
    root_progress_text: str,
    root_tokens_text: str,
    root_phase9_text: str,
) -> dict[str, Any]:
    return {
        "progress_value": "600/600" if "Progress now: `600/600`" in root_progress_text else "unexpected",
        "phase9_token_recorded": "AGIF_FABRIC_P9_PASS" in root_tokens_text,
        "phase9_evidence_mentions_command": "python3 scripts/check_phase9_closure.py" in root_phase9_text,
        "root_progress_still_600_of_600": "Progress now: `600/600`" in root_progress_text,
        "root_tokens_exclude_track_b_tokens": all(token not in root_tokens_text for token in TRACK_B_TOKENS),
    }


def _build_track_b_record_status(
    *,
    track_b_progress_text: str,
    track_b_tokens_text: str,
    track_b_checklist_text: str,
    track_b_readme_text: str,
    bundle_evidence_text: str,
) -> dict[str, Any]:
    bundle_checklist_closed = all(
        snippet in track_b_checklist_text
        for snippet in (
            "- [x] ordered extension chain passes",
            "- [x] root AGIF v1 closure still passes",
            "- [x] root AGIF v1 progress still reads `600/600`",
            "- [x] `AGIF_FABRIC_V1X_PASS` is earned honestly",
        )
    )
    all_track_b_tokens_recorded = all(token in track_b_tokens_text for token in TRACK_B_TOKENS)
    bundle_readme_closed = all(
        snippet in track_b_readme_text
        for snippet in (
            "Final bundle close is now locally verified.",
            "`AGIF_FABRIC_V1X_PASS` is earned honestly.",
            "Current extension progress remains `130/130`.",
            "`python3 scripts/check_v1x_bundle.py` passes locally.",
        )
    )
    bundle_evidence_recorded = all(
        snippet in bundle_evidence_text
        for snippet in (
            "`python3 scripts/check_v1x_bundle.py`",
            "`AGIF_FABRIC_V1X_PASS`",
            "Root AGIF v1 remains closed at `600/600`.",
        )
    )
    return {
        "progress_still_130_of_130": "Progress now: `130/130`" in track_b_progress_text,
        "all_track_b_tokens_recorded": all_track_b_tokens_recorded,
        "bundle_checklist_closed": bundle_checklist_closed,
        "bundle_readme_closed": bundle_readme_closed,
        "bundle_evidence_recorded": bundle_evidence_recorded,
    }


def _build_acceptance(
    *,
    command_chain: list[dict[str, Any]],
    gap_chain: list[dict[str, Any]],
    root_recheck: dict[str, Any],
    track_b_record_status: dict[str, Any],
    command_log_length: int,
) -> dict[str, Any]:
    ordered_command_chain_passed = (
        command_log_length == len(REQUIRED_COMMAND_SPECS)
        and all(
            entry["matched_expected_order"] and entry["returncode"] == 0 and entry["expected_token_present"]
            for entry in command_chain
        )
    )
    setup_prerequisite_recorded = ordered_command_chain_passed and command_chain[0]["expected_token_present"]
    ordered_gap_chain_passed = all(gap["accepted"] for gap in gap_chain)
    root_closure_rechecked = (
        ordered_command_chain_passed
        and command_chain[-1]["expected_token_present"]
        and root_recheck["phase9_token_recorded"]
        and root_recheck["phase9_evidence_mentions_command"]
    )
    track_b_closure_record_complete = all(track_b_record_status.values())
    acceptance = {
        "ordered_command_chain_passed": ordered_command_chain_passed,
        "setup_prerequisite_recorded": setup_prerequisite_recorded,
        "ordered_gap_chain_passed": ordered_gap_chain_passed,
        "root_closure_rechecked": root_closure_rechecked,
        "root_progress_still_600_of_600": root_recheck["root_progress_still_600_of_600"],
        "root_tokens_still_isolated": root_recheck["root_tokens_exclude_track_b_tokens"],
        "track_b_progress_still_130_of_130": track_b_record_status["progress_still_130_of_130"],
        "track_b_closure_record_complete": track_b_closure_record_complete,
    }
    acceptance["passed"] = all(acceptance.values())
    return acceptance


def _normalize_artifact_results(results: dict[str, Any]) -> dict[str, Any]:
    artifact = deepcopy(results)
    artifact.pop("created_utc", None)
    return artifact


def _last_non_empty_line(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    return lines[-1]
