"""Bounded POS operations executor for Track B Gap 3."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from intelligence.fabric.utility import clamp_score


MANUAL_REVIEW_THRESHOLD = 0.5
FINANCE_HOLD_THRESHOLD = 0.9


def execute_pos_case(
    *,
    case_spec: dict[str, Any],
    transfer_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Runs one deterministic POS case with optional governed cross-domain support."""

    payload = deepcopy(case_spec.get("payload") or {})
    local_breakdown = _local_support_breakdown(payload=payload)
    local_support_score = clamp_score(sum(local_breakdown.values()))
    baseline_action = _action_from_support(local_support_score)

    transfer_considered = _transfer_is_considered(transfer_entry)
    transfer_support_score = 0.0
    if transfer_considered:
        transfer_support_score = clamp_score(float(transfer_entry.get("target_support_score", 0.0)))
    final_support_score = max(local_support_score, transfer_support_score)
    final_action = _action_from_support(final_support_score)
    decision_changed_by_transfer = transfer_considered and final_action != baseline_action
    counted_cross_domain_influence = (
        decision_changed_by_transfer
        and bool(transfer_entry)
        and bool(transfer_entry.get("explicit_transfer_approval", False))
    )

    truth = dict(case_spec.get("truth") or {})
    truth_action = str(truth.get("final_action", ""))
    case_score = 1.0 if final_action == truth_action else 0.0

    audit_bundle = None
    if transfer_considered and isinstance(transfer_entry, dict):
        provenance = dict(transfer_entry.get("provenance_bundle") or {})
        audit_bundle = {
            "source_descriptor_id": transfer_entry.get("selected_source_descriptor_id"),
            "source_domain": transfer_entry.get("source_domain"),
            "source_memory_id": provenance.get("source_memory_id"),
            "source_payload_ref": provenance.get("source_payload_ref"),
            "transfer_approval_ref": provenance.get("transfer_approval_ref"),
            "transfer_descriptor_id": provenance.get("transfer_descriptor_id"),
        }

    return {
        "case_id": str(case_spec.get("case_id", "")),
        "operation_type": str(case_spec.get("operation_type", "")),
        "local_support_score": round(local_support_score, 6),
        "transfer_support_score": round(transfer_support_score, 6),
        "final_support_score": round(final_support_score, 6),
        "baseline_action": baseline_action,
        "final_action": final_action,
        "truth_action": truth_action,
        "case_score": round(case_score, 6),
        "local_breakdown": {key: round(value, 6) for key, value in local_breakdown.items()},
        "transfer_considered": transfer_considered,
        "decision_changed_by_transfer": decision_changed_by_transfer,
        "counted_cross_domain_influence": counted_cross_domain_influence,
        "audit_bundle": audit_bundle,
    }


def _local_support_breakdown(*, payload: dict[str, Any]) -> dict[str, float]:
    drawer_variance_cents = abs(int(payload.get("drawer_variance_cents", 0)))
    duplicate_batch_refs = max(0, int(payload.get("duplicate_batch_refs", 0)))
    cross_store_reentry_count = max(0, int(payload.get("cross_store_reentry_count", 0)))
    alias_confidence = clamp_score(float(payload.get("alias_confidence", 0.0)))
    return {
        "base_signal": 0.22,
        "variance_signal": min(0.26, (drawer_variance_cents / 1000.0) * 0.24),
        "duplicate_signal": min(0.18, duplicate_batch_refs * 0.09),
        "manual_override_signal": 0.08 if bool(payload.get("manual_override_requested", False)) else 0.0,
        "tender_mismatch_signal": 0.12 if bool(payload.get("tender_mismatch", False)) else 0.0,
        "refund_signal": 0.1 if bool(payload.get("refund_without_receipt", False)) else 0.0,
        "cross_store_signal": min(0.1, cross_store_reentry_count * 0.05),
        "alias_signal": min(0.26, alias_confidence * 0.26),
        "employee_pin_discount": -0.08 if bool(payload.get("employee_pin_verified", False)) else 0.0,
    }


def _transfer_is_considered(transfer_entry: dict[str, Any] | None) -> bool:
    if not isinstance(transfer_entry, dict):
        return False
    return (
        transfer_entry.get("status") == "approved"
        and bool(transfer_entry.get("cross_domain", False))
        and bool(transfer_entry.get("explicit_transfer_approval", False))
        and bool(transfer_entry.get("audit_ready", False))
    )


def _action_from_support(support_score: float) -> str:
    if support_score >= FINANCE_HOLD_THRESHOLD:
        return "hold_for_finance_review"
    if support_score >= MANUAL_REVIEW_THRESHOLD:
        return "manual_review"
    return "approve_close"
