"""Authority review and approval records for Phase 6 governed actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from intelligence.fabric.common import load_json_file, utc_now_iso, write_json_atomic
from intelligence.fabric.governance.policy import ensure_governance_actor
from intelligence.fabric.state_store import FabricStateStore
from intelligence.fabric.utility import clamp_score, policy_risk_from_envelope, trust_score_from_ref


class AuthorityEngine:
    """Records approvals and vetoes for higher-risk runtime actions."""

    def __init__(
        self,
        *,
        store: FabricStateStore,
        state: dict[str, Any],
        config: dict[str, Any],
    ):
        self.store = store
        self.state = dict(state)
        self.config = config
        self.fabric_id = str(state["fabric_id"])
        self.policy = dict(config.get("governance_policy", {}))
        self.descriptor_trust_floor = float(self.policy.get("descriptor_trust_floor", 0.6))
        self.memory_runtime_trust_floor = float(self.policy.get("memory_runtime_trust_floor", 0.6))
        self.risky_reactivation_trust_floor = float(self.policy.get("risky_reactivation_trust_floor", 0.6))
        self.ensure_store()

    def ensure_store(self) -> None:
        self._load_or_initialize(
            self.store.authority_reviews_path(self.fabric_id),
            {"schema_version": "agif.fabric.authority_reviews.v1", "entries": []},
        )

    def load_reviews(self) -> list[dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.authority_reviews_path(self.fabric_id),
            {"schema_version": "agif.fabric.authority_reviews.v1", "entries": []},
        )
        return [deepcopy(item) for item in payload["entries"]]

    def evaluate_action(
        self,
        *,
        action: str,
        proposer: str,
        need_signal: dict[str, Any] | None,
        utility_evaluation: dict[str, Any] | None,
        policy_envelope: dict[str, Any],
        trust_state: dict[str, Any] | None,
        rollback_ref: str | None,
        related_cells: list[str] | None = None,
        descriptor_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        approver: str | None = None,
    ) -> dict[str, Any]:
        entries = self._load_or_initialize(
            self.store.authority_reviews_path(self.fabric_id),
            {"schema_version": "agif.fabric.authority_reviews.v1", "entries": []},
        )
        trust_state = dict(trust_state or {})
        descriptor_refs = sorted(descriptor_refs or [])
        metadata = deepcopy(metadata or {})
        utility_evaluation = deepcopy(utility_evaluation or {})
        trust_score = clamp_score(
            float(trust_state.get("trust_score", trust_score_from_ref(str(trust_state.get("trust_ref", "")))))
        )
        policy_risk = clamp_score(policy_risk_from_envelope(policy_envelope, action=action))
        utility_score = clamp_score(float(utility_evaluation.get("utility_score", utility_evaluation.get("score", 0.0))))
        utility_threshold = float(utility_evaluation.get("threshold", 0.0))
        veto_conditions: list[str] = []

        if action in {"split_follow_through", "merge_follow_through", "quarantine_escalation"} and need_signal is None:
            veto_conditions.append("missing_need_signal")
        if action in {"split_follow_through", "merge_follow_through", "quarantine_escalation"} and not rollback_ref:
            veto_conditions.append("missing_rollback_path")
        if action == "descriptor_use" and descriptor_refs and trust_score < self.descriptor_trust_floor:
            veto_conditions.append("descriptor_low_trust")
        if action == "memory_runtime_influence" and trust_score < self.memory_runtime_trust_floor:
            veto_conditions.append("memory_low_trust")
        if action == "reactivate" and trust_score < self.risky_reactivation_trust_floor:
            veto_conditions.append("reactivation_low_trust")
        if action == "quarantine_escalation" and str((need_signal or {}).get("signal_kind")) not in {"trust_risk", "uncertainty"}:
            veto_conditions.append("quarantine_without_risk_signal")
        if policy_risk >= 0.8:
            veto_conditions.append("policy_boundary_risk")
        if utility_threshold > 0.0 and utility_score < utility_threshold:
            veto_conditions.append("utility_below_threshold")

        reviewer = ensure_governance_actor(approver, self.policy)
        review_id = f"authority_{len(entries['entries']) + 1:05d}"
        review = {
            "review_id": review_id,
            "action": action,
            "decision": "approved" if len(veto_conditions) == 0 else "vetoed",
            "proposer": proposer,
            "reviewer": reviewer,
            "need_signal_id": None if need_signal is None else str(need_signal["need_signal_id"]),
            "policy_envelope": deepcopy(policy_envelope),
            "trust_state": {
                "trust_ref": trust_state.get("trust_ref"),
                "trust_score": trust_score,
            },
            "utility_score": utility_score,
            "utility_threshold": round(utility_threshold, 6),
            "policy_risk": policy_risk,
            "veto_conditions": veto_conditions,
            "rollback_ref": rollback_ref,
            "action_ref": None,
            "related_cells": sorted(related_cells or []),
            "descriptor_refs": descriptor_refs,
            "metadata": metadata,
            "created_utc": utc_now_iso(),
            "finalized_utc": None,
        }
        entries["entries"].append(review)
        write_json_atomic(self.store.authority_reviews_path(self.fabric_id), entries)
        return {**deepcopy(review), "approved": len(veto_conditions) == 0}

    def finalize_review(self, review_id: str, *, action_ref: str, rollback_ref: str | None = None) -> dict[str, Any]:
        payload = self._load_or_initialize(
            self.store.authority_reviews_path(self.fabric_id),
            {"schema_version": "agif.fabric.authority_reviews.v1", "entries": []},
        )
        updated: dict[str, Any] | None = None
        for entry in payload["entries"]:
            if str(entry.get("review_id")) != review_id:
                continue
            entry["action_ref"] = action_ref
            if rollback_ref:
                entry["rollback_ref"] = rollback_ref
            entry["finalized_utc"] = utc_now_iso()
            updated = deepcopy(entry)
            break
        if updated is None:
            return {"review_id": review_id, "updated": False}
        write_json_atomic(self.store.authority_reviews_path(self.fabric_id), payload)
        return {**updated, "updated": True}

    def summary(self) -> dict[str, Any]:
        reviews = self.load_reviews()
        by_action: dict[str, dict[str, int]] = {}
        for item in reviews:
            action = str(item["action"])
            action_bucket = by_action.setdefault(action, {"approved": 0, "vetoed": 0})
            action_bucket[str(item["decision"])] += 1
        approved_count = len([item for item in reviews if item["decision"] == "approved"])
        veto_count = len([item for item in reviews if item["decision"] == "vetoed"])
        finalized_count = len([item for item in reviews if item.get("action_ref")])
        return {
            "review_count": len(reviews),
            "approved_count": approved_count,
            "veto_count": veto_count,
            "finalized_count": finalized_count,
            "approval_rate": 0.0 if len(reviews) == 0 else round(approved_count / float(len(reviews)), 6),
            "outcomes_by_action": by_action,
            "latest_review_ref": None if len(reviews) == 0 else reviews[-1]["review_id"],
        }

    def _load_or_initialize(self, path: Any, default_payload: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        value = load_json_file(
            path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label=str(path.name),
        )
        if not isinstance(value, dict):
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        return value
