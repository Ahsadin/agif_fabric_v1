"""Shared workspace helpers for the Phase 3 foundation."""

from __future__ import annotations

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

