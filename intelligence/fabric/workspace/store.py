"""Shared workspace helpers for the AGIF fabric runtime."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_workspace_snapshot(
    *,
    workflow_id: str,
    workflow_payload: dict[str, Any],
    selected_blueprints: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "workflow_payload": workflow_payload,
        "selected_blueprints": selected_blueprints,
    }


def build_phase7_workspace(
    *,
    workflow_id: str,
    workflow_payload: dict[str, Any],
    benchmark_class: str,
    tissue_registry_ref: str,
) -> dict[str, Any]:
    return {
        "workspace_version": "agif.fabric.workspace.phase7.v1",
        "workflow_id": workflow_id,
        "workflow_payload": deepcopy(workflow_payload),
        "benchmark_class": benchmark_class,
        "tissue_registry_ref": tissue_registry_ref,
        "current_stage": "created",
        "tissues_used": [],
        "stage_history": [],
        "handoffs": [],
        "stage_outputs": {},
        "governance": {},
        "final_output": None,
    }


def record_phase7_stage(
    workspace: dict[str, Any],
    *,
    stage_id: str,
    tissue_id: str,
    cell_id: str,
    role_name: str,
    output: dict[str, Any],
    notes: list[str] | None = None,
) -> dict[str, Any]:
    updated = deepcopy(workspace)
    updated["current_stage"] = stage_id
    updated["stage_history"].append(
        {
            "stage_id": stage_id,
            "tissue_id": tissue_id,
            "cell_id": cell_id,
            "role_name": role_name,
            "notes": list(notes or []),
        }
    )
    updated["stage_outputs"][stage_id] = deepcopy(output)
    if tissue_id not in updated["tissues_used"]:
        updated["tissues_used"].append(tissue_id)
    return updated


def record_phase7_handoff(
    workspace: dict[str, Any],
    *,
    handoff_id: str,
    from_tissue: str,
    to_tissue: str,
    artifact_stage_id: str,
    artifact_summary: str,
) -> dict[str, Any]:
    updated = deepcopy(workspace)
    updated["handoffs"].append(
        {
            "handoff_id": handoff_id,
            "from_tissue": from_tissue,
            "to_tissue": to_tissue,
            "artifact_stage_id": artifact_stage_id,
            "artifact_summary": artifact_summary,
        }
    )
    return updated


def record_phase7_governance(
    workspace: dict[str, Any],
    *,
    governance_payload: dict[str, Any],
) -> dict[str, Any]:
    updated = deepcopy(workspace)
    updated["governance"] = deepcopy(governance_payload)
    return updated


def finalize_phase7_workspace(
    workspace: dict[str, Any],
    *,
    final_output: dict[str, Any],
) -> dict[str, Any]:
    updated = deepcopy(workspace)
    updated["current_stage"] = "complete"
    updated["final_output"] = deepcopy(final_output)
    return updated
