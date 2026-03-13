"""Authority review and approval records for Phase 6 governed actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from intelligence.fabric.common import load_json_file, utc_now_iso, write_json_atomic
from intelligence.fabric.governance.policy import ensure_governance_actor
from intelligence.fabric.state_store import FabricStateStore
from intelligence.fabric.utility import clamp_score, policy_risk_from_envelope, trust_score_from_ref


HIGH_RISK_ACTIONS = {
    "descriptor_use",
    "memory_runtime_influence",
    "merge_follow_through",
    "quarantine_escalation",
    "reactivate",
    "split_follow_through",
}


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
        self._load_or_initialize(
            self.store.authority_patterns_path(self.fabric_id),
            {
                "schema_version": "agif.fabric.authority_patterns.v1",
                "actions": {},
                "proposers": {},
                "trust_bands": {},
                "lineages": {},
                "veto_patterns": {},
            },
        )

    def load_reviews(self) -> list[dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.authority_reviews_path(self.fabric_id),
            {"schema_version": "agif.fabric.authority_reviews.v1", "entries": []},
        )
        return [deepcopy(item) for item in payload["entries"]]

    def load_patterns(self) -> dict[str, Any]:
        payload = self._load_or_initialize(
            self.store.authority_patterns_path(self.fabric_id),
            {
                "schema_version": "agif.fabric.authority_patterns.v1",
                "actions": {},
                "proposers": {},
                "trust_bands": {},
                "lineages": {},
                "veto_patterns": {},
            },
        )
        return deepcopy(payload)

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
        patterns = self._load_or_initialize(
            self.store.authority_patterns_path(self.fabric_id),
            {
                "schema_version": "agif.fabric.authority_patterns.v1",
                "actions": {},
                "proposers": {},
                "trust_bands": {},
                "lineages": {},
                "veto_patterns": {},
            },
        )
        trust_state = dict(trust_state or {})
        descriptor_refs = sorted(descriptor_refs or [])
        metadata = deepcopy(metadata or {})
        utility_evaluation = deepcopy(utility_evaluation or {})
        trust_score = clamp_score(
            float(trust_state.get("trust_score", trust_score_from_ref(str(trust_state.get("trust_ref", "")))))
        )
        trust_band = self._trust_band(trust_score)
        policy_risk = clamp_score(policy_risk_from_envelope(policy_envelope, action=action))
        utility_score = clamp_score(float(utility_evaluation.get("utility_score", utility_evaluation.get("score", 0.0))))
        utility_threshold = float(utility_evaluation.get("threshold", 0.0))
        lineage_id = str(metadata.get("lineage_id", ""))
        lineage_usefulness_score = clamp_score(float(metadata.get("lineage_usefulness_score", 0.0)))
        descriptor_provenance_score = clamp_score(float(metadata.get("descriptor_provenance_score", 0.0)))
        history_context = self._history_context(
            patterns=patterns,
            action=action,
            proposer=proposer,
            trust_band=trust_band,
            lineage_id=lineage_id,
        )
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
        if (
            history_context["proposer_veto_count"] >= 1
            and action in {"reactivate", "split_follow_through", "merge_follow_through"}
        ):
            veto_conditions.append("repeated_veto_pattern")
        if history_context["trust_band_veto_count"] > history_context["trust_band_approved_count"] and action in {
            "descriptor_use",
            "memory_runtime_influence",
            "reactivate",
        }:
            veto_conditions.append("trust_band_under_review")
        if lineage_id and lineage_usefulness_score < 0.12 and history_context["lineage_veto_count"] >= 1 and action in {
            "descriptor_use",
            "reactivate",
            "split_follow_through",
        }:
            veto_conditions.append("weak_lineage_branch")
        if action == "descriptor_use" and descriptor_refs and descriptor_provenance_score < 0.3 and trust_band == "low":
            veto_conditions.append("descriptor_provenance_weak")

        reviewer = ensure_governance_actor(approver, self.policy)
        review_id = f"authority_{len(entries['entries']) + 1:05d}"
        approved = len(veto_conditions) == 0
        decision_notes = self._decision_notes(
            action=action,
            approved=approved,
            need_signal=need_signal,
            history_context=history_context,
            descriptor_provenance_score=descriptor_provenance_score,
            lineage_usefulness_score=lineage_usefulness_score,
            trust_band=trust_band,
            rollback_ref=rollback_ref,
        )
        review = {
            "review_id": review_id,
            "action": action,
            "decision": "approved" if approved else "vetoed",
            "proposer": proposer,
            "reviewer": reviewer,
            "need_signal_id": None if need_signal is None else str(need_signal["need_signal_id"]),
            "policy_envelope": deepcopy(policy_envelope),
            "trust_state": {
                "trust_ref": trust_state.get("trust_ref"),
                "trust_score": trust_score,
                "trust_band": trust_band,
            },
            "utility_score": utility_score,
            "utility_threshold": round(utility_threshold, 6),
            "policy_risk": policy_risk,
            "veto_conditions": veto_conditions,
            "history_context": history_context,
            "decision_notes": decision_notes,
            "rollback_ref": rollback_ref,
            "rollback_ready": bool(rollback_ref),
            "action_ref": None,
            "related_cells": sorted(related_cells or []),
            "descriptor_refs": descriptor_refs,
            "metadata": metadata,
            "created_utc": utc_now_iso(),
            "finalized_utc": None,
        }
        entries["entries"].append(review)
        write_json_atomic(self.store.authority_reviews_path(self.fabric_id), entries)
        self._update_patterns(patterns=patterns, review=review)
        write_json_atomic(self.store.authority_patterns_path(self.fabric_id), patterns)
        return {**deepcopy(review), "approved": approved}

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
        patterns = self.load_patterns()
        by_action: dict[str, dict[str, int]] = {}
        by_trust_band: dict[str, dict[str, int]] = {}
        for item in reviews:
            action = str(item["action"])
            action_bucket = by_action.setdefault(action, {"approved": 0, "vetoed": 0})
            action_bucket[str(item["decision"])] += 1
            trust_band = str(item.get("trust_state", {}).get("trust_band", "unknown"))
            trust_bucket = by_trust_band.setdefault(trust_band, {"approved": 0, "vetoed": 0})
            trust_bucket[str(item["decision"])] += 1
        approved_count = len([item for item in reviews if item["decision"] == "approved"])
        veto_count = len([item for item in reviews if item["decision"] == "vetoed"])
        finalized_count = len([item for item in reviews if item.get("action_ref")])
        repeated_veto_pattern_count = int(patterns.get("veto_patterns", {}).get("repeated_veto_pattern", 0))
        weak_lineage_pattern_count = int(patterns.get("veto_patterns", {}).get("weak_lineage_branch", 0))
        return {
            "review_count": len(reviews),
            "approved_count": approved_count,
            "veto_count": veto_count,
            "finalized_count": finalized_count,
            "approval_rate": 0.0 if len(reviews) == 0 else round(approved_count / float(len(reviews)), 6),
            "outcomes_by_action": by_action,
            "outcomes_by_trust_band": by_trust_band,
            "repeated_veto_pattern_count": repeated_veto_pattern_count,
            "weak_lineage_pattern_count": weak_lineage_pattern_count,
            "lineages_under_review": len(
                [item for item in patterns.get("lineages", {}).values() if int(item.get("vetoed", 0)) > 0]
            ),
            "latest_review_ref": None if len(reviews) == 0 else reviews[-1]["review_id"],
        }

    def _decision_notes(
        self,
        *,
        action: str,
        approved: bool,
        need_signal: dict[str, Any] | None,
        history_context: dict[str, Any],
        descriptor_provenance_score: float,
        lineage_usefulness_score: float,
        trust_band: str,
        rollback_ref: str | None,
    ) -> list[str]:
        notes = [
            f"action={action}",
            f"decision={'approved' if approved else 'vetoed'}",
            f"need_signal={None if need_signal is None else need_signal['need_signal_id']}",
            f"trust_band={trust_band}",
            f"rollback_ready={bool(rollback_ref)}",
            f"prior_action_vetoes={history_context['action_veto_count']}",
            f"prior_proposer_vetoes={history_context['proposer_veto_count']}",
        ]
        if descriptor_provenance_score > 0.0:
            notes.append(f"descriptor_provenance={descriptor_provenance_score}")
        if lineage_usefulness_score > 0.0 or history_context["lineage_veto_count"] > 0:
            notes.append(f"lineage_usefulness={lineage_usefulness_score}")
        return notes

    def _history_context(
        self,
        *,
        patterns: dict[str, Any],
        action: str,
        proposer: str,
        trust_band: str,
        lineage_id: str,
    ) -> dict[str, int | str]:
        action_stats = self._bucket(patterns["actions"].get(action))
        proposer_stats = self._bucket(patterns["proposers"].get(f"{proposer}|{action}"))
        trust_stats = self._bucket(patterns["trust_bands"].get(f"{trust_band}|{action}"))
        lineage_stats = self._bucket(patterns["lineages"].get(lineage_id)) if lineage_id else self._bucket(None)
        return {
            "action_review_count": int(action_stats["review_count"]),
            "action_veto_count": int(action_stats["vetoed"]),
            "proposer_review_count": int(proposer_stats["review_count"]),
            "proposer_veto_count": int(proposer_stats["vetoed"]),
            "trust_band_review_count": int(trust_stats["review_count"]),
            "trust_band_approved_count": int(trust_stats["approved"]),
            "trust_band_veto_count": int(trust_stats["vetoed"]),
            "lineage_review_count": int(lineage_stats["review_count"]),
            "lineage_veto_count": int(lineage_stats["vetoed"]),
            "lineage_id": lineage_id,
        }

    def _update_patterns(self, *, patterns: dict[str, Any], review: dict[str, Any]) -> None:
        decision = str(review["decision"])
        action = str(review["action"])
        proposer_key = f"{review['proposer']}|{action}"
        trust_band = str(review.get("trust_state", {}).get("trust_band", "unknown"))
        trust_key = f"{trust_band}|{action}"
        lineage_id = str(review.get("metadata", {}).get("lineage_id", ""))
        self._increment_bucket(patterns["actions"], action, review["review_id"], decision)
        self._increment_bucket(patterns["proposers"], proposer_key, review["review_id"], decision)
        self._increment_bucket(patterns["trust_bands"], trust_key, review["review_id"], decision)
        if lineage_id:
            self._increment_bucket(patterns["lineages"], lineage_id, review["review_id"], decision)
        for condition in review.get("veto_conditions", []):
            patterns["veto_patterns"][str(condition)] = int(patterns["veto_patterns"].get(str(condition), 0)) + 1

    def _increment_bucket(
        self,
        container: dict[str, Any],
        key: str,
        review_id: str,
        decision: str,
    ) -> None:
        bucket = self._bucket(container.get(key))
        bucket["review_count"] = int(bucket["review_count"]) + 1
        bucket[str(decision)] = int(bucket[str(decision)]) + 1
        bucket["latest_review_ref"] = review_id
        container[key] = bucket

    def _bucket(self, value: dict[str, Any] | None) -> dict[str, Any]:
        base = {"review_count": 0, "approved": 0, "vetoed": 0, "latest_review_ref": None}
        if not isinstance(value, dict):
            return base
        return {
            "review_count": int(value.get("review_count", 0)),
            "approved": int(value.get("approved", 0)),
            "vetoed": int(value.get("vetoed", 0)),
            "latest_review_ref": value.get("latest_review_ref"),
        }

    def _trust_band(self, trust_score: float) -> str:
        if trust_score >= 0.8:
            return "high"
        if trust_score >= 0.6:
            return "guarded"
        return "low"

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
