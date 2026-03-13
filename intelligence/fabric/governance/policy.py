"""Governance helpers for AGIF v1 lifecycle control."""

from __future__ import annotations

from typing import Any

from intelligence.fabric.common import (
    FabricError,
    ensure_exact_keys,
    ensure_non_empty_string,
    ensure_numeric,
    utc_now_iso,
)


NEED_SIGNAL_FIELDS = (
    "need_signal_id",
    "source_type",
    "source_id",
    "signal_kind",
    "severity",
    "evidence_ref",
    "proposed_action",
    "status",
    "expires_at_utc",
    "resolution_ref",
    "created_utc",
)

ALLOWED_SIGNAL_KINDS = {
    "overload",
    "uncertainty",
    "novelty",
    "redundancy",
    "memory_pressure",
    "trust_risk",
    "coordination_gap",
}


def ensure_governance_actor(actor: str | None, governance_policy: dict[str, Any]) -> str:
    candidate = actor or governance_policy.get("default_governance_approver") or "governance:phase4_local_board"
    return ensure_non_empty_string(candidate, "governance_actor", code="GOVERNANCE_INVALID")


def ensure_tissue_actor(actor: str | None, governance_policy: dict[str, Any], allowed_tissues: list[str]) -> str:
    if actor:
        return ensure_non_empty_string(actor, "tissue_actor", code="GOVERNANCE_INVALID")
    configured = governance_policy.get("default_tissue_coordinator")
    if configured:
        return ensure_non_empty_string(configured, "tissue_actor", code="GOVERNANCE_INVALID")
    if allowed_tissues:
        return f"tissue:{allowed_tissues[0]}:coordinator"
    raise FabricError("GOVERNANCE_INVALID", "A tissue coordinator is required for this action.")


def ensure_need_signal(signal: dict[str, Any] | None, *, action: str) -> dict[str, Any]:
    if not isinstance(signal, dict):
        raise FabricError("NEED_SIGNAL_INVALID", f"{action} requires a recorded NeedSignal object.")
    ensure_exact_keys(signal, NEED_SIGNAL_FIELDS, "NeedSignal", code="NEED_SIGNAL_INVALID")
    signal_kind = ensure_non_empty_string(signal["signal_kind"], "NeedSignal.signal_kind", code="NEED_SIGNAL_INVALID")
    if signal_kind not in ALLOWED_SIGNAL_KINDS:
        raise FabricError("NEED_SIGNAL_INVALID", f"NeedSignal.signal_kind must be one of: {','.join(sorted(ALLOWED_SIGNAL_KINDS))}.")
    return {
        "need_signal_id": ensure_non_empty_string(signal["need_signal_id"], "NeedSignal.need_signal_id", code="NEED_SIGNAL_INVALID"),
        "source_type": ensure_non_empty_string(signal["source_type"], "NeedSignal.source_type", code="NEED_SIGNAL_INVALID"),
        "source_id": ensure_non_empty_string(signal["source_id"], "NeedSignal.source_id", code="NEED_SIGNAL_INVALID"),
        "signal_kind": signal_kind,
        "severity": ensure_numeric(signal["severity"], "NeedSignal.severity", code="NEED_SIGNAL_INVALID"),
        "evidence_ref": ensure_non_empty_string(signal["evidence_ref"], "NeedSignal.evidence_ref", code="NEED_SIGNAL_INVALID"),
        "proposed_action": ensure_non_empty_string(
            signal["proposed_action"], "NeedSignal.proposed_action", code="NEED_SIGNAL_INVALID"
        ),
        "status": ensure_non_empty_string(signal["status"], "NeedSignal.status", code="NEED_SIGNAL_INVALID"),
        "expires_at_utc": ensure_non_empty_string(
            signal["expires_at_utc"], "NeedSignal.expires_at_utc", code="NEED_SIGNAL_INVALID"
        ),
        "resolution_ref": signal["resolution_ref"],
        "created_utc": ensure_non_empty_string(signal["created_utc"], "NeedSignal.created_utc", code="NEED_SIGNAL_INVALID"),
    }


def summarize_governance(
    governance_policy: dict[str, Any],
    *,
    steady_active_population_target: int | None = None,
    burst_active_population_cap: int | None = None,
) -> dict[str, Any]:
    return {
        "mode": governance_policy.get("mode", "phase4_governed_local_v1"),
        "approval_required_for": ["split", "merge", "quarantine_release", "retire"],
        "human_boundary": governance_policy.get("human_boundary", "document/workflow intelligence"),
        "default_governance_approver": ensure_governance_actor(None, governance_policy),
        "default_tissue_coordinator": governance_policy.get("default_tissue_coordinator", "tissue:finance_document_workflow:coordinator"),
        "steady_active_population_target": steady_active_population_target,
        "burst_active_population_cap": burst_active_population_cap,
        "governance_checked_utc": utc_now_iso(),
    }
