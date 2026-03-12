"""Governance summaries for the Phase 3 foundation."""

from __future__ import annotations

from typing import Any


def summarize_governance(governance_policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": governance_policy.get("mode", "phase3_governed_local_v1"),
        "approval_required_for": ["split", "merge", "quarantine_release", "retire"],
        "human_boundary": governance_policy.get("human_boundary", "document/workflow intelligence"),
    }

