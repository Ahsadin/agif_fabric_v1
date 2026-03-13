"""Utility scoring helpers for Phase 6 routing and governed runtime choices."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_UTILITY_PROFILE = {
    "reward_weight": 1.0,
    "novelty_weight": 0.4,
    "resource_cost_weight": 0.3,
    "trust_penalty_weight": 0.6,
    "policy_penalty_weight": 0.8,
    "split_threshold": 0.9,
    "merge_threshold": 0.35,
    "hibernate_threshold": 0.2,
    "reactivate_threshold": 0.55,
}

UTILITY_BANDS = (
    (0.75, "attractive"),
    (0.5, "acceptable"),
    (0.25, "weak"),
)


def clamp_score(value: float) -> float:
    return round(min(1.0, max(0.0, float(value))), 6)


def utility_band(score: float) -> str:
    normalized = clamp_score(score)
    for threshold, label in UTILITY_BANDS:
        if normalized >= threshold:
            return label
    return "abstain"


def trust_score_from_ref(trust_ref: str) -> float:
    normalized = str(trust_ref)
    if "experimental" in normalized:
        return 0.35
    if "policy" in normalized:
        return 0.95
    if "bounded_local" in normalized:
        return 0.76
    return 0.6


def policy_risk_from_envelope(policy_envelope: dict[str, Any], *, action: str) -> float:
    allowed_actions = policy_envelope.get("allowed_actions", [])
    if not isinstance(allowed_actions, list):
        allowed_actions = []
    boundary = str(policy_envelope.get("human_boundary", ""))
    if boundary and "document/workflow" not in boundary:
        return 1.0
    if action in {"route", "descriptor_use"} and "route" not in allowed_actions and "summarize" not in allowed_actions:
        return 0.85
    if action in {"report", "audit"} and "report" not in allowed_actions and "summarize" not in allowed_actions:
        return 0.85
    return 0.05


class UtilityScorer:
    """Scores routing candidates and structural actions using frozen utility profiles."""

    def __init__(self, utility_profiles: dict[str, dict[str, Any]] | None = None):
        self.utility_profiles = deepcopy(utility_profiles or {})

    def resolve_profile(self, profile_ref: str | None) -> dict[str, float]:
        if profile_ref and profile_ref in self.utility_profiles:
            return {
                key: float(self.utility_profiles[profile_ref].get(key, DEFAULT_UTILITY_PROFILE[key]))
                for key in DEFAULT_UTILITY_PROFILE
            }
        return deepcopy(DEFAULT_UTILITY_PROFILE)

    def score_candidate(
        self,
        *,
        profile_ref: str | None,
        role_fit: float,
        descriptor_usefulness: float,
        trust_score: float,
        current_load: float,
        need_pressure: float,
        workspace_fit: float,
        activation_cost_ms: int,
        working_memory_bytes: int,
        policy_risk: float,
        novelty_signal: float = 0.0,
        historical_feedback: float = 0.0,
    ) -> dict[str, Any]:
        profile = self.resolve_profile(profile_ref)
        resource_cost = clamp_score(
            (float(activation_cost_ms) / 120.0) * 0.45 + (float(working_memory_bytes) / 262144.0) * 0.55
        )
        reward_signal = clamp_score(
            (0.42 * role_fit) + (0.24 * descriptor_usefulness) + (0.18 * workspace_fit) + (0.16 * max(0.0, need_pressure))
        )
        novelty_component = clamp_score((0.65 * novelty_signal) + (0.35 * descriptor_usefulness))
        score = clamp_score(
            (profile["reward_weight"] * reward_signal)
            + (profile["novelty_weight"] * novelty_component)
            - (profile["resource_cost_weight"] * resource_cost)
            - (profile["trust_penalty_weight"] * (1.0 - trust_score))
            - (profile["policy_penalty_weight"] * policy_risk)
            - (0.18 * current_load)
            + (0.14 * clamp_score(historical_feedback))
        )
        return {
            "profile_ref": profile_ref or "default",
            "profile": profile,
            "reward_signal": reward_signal,
            "novelty_signal": clamp_score(novelty_signal),
            "descriptor_usefulness": clamp_score(descriptor_usefulness),
            "workspace_fit": clamp_score(workspace_fit),
            "need_pressure": clamp_score(need_pressure),
            "resource_cost": resource_cost,
            "trust_score": clamp_score(trust_score),
            "policy_risk": clamp_score(policy_risk),
            "current_load": clamp_score(current_load),
            "historical_feedback": clamp_score(historical_feedback),
            "utility_score": score,
            "utility_band": utility_band(score),
        }

    def score_structural_action(
        self,
        *,
        action: str,
        profile_ref: str | None,
        need_severity: float,
        trust_score: float,
        policy_risk: float,
        resource_cost: float,
        contextual_gain: float,
        historical_feedback: float = 0.0,
    ) -> dict[str, Any]:
        profile = self.resolve_profile(profile_ref)
        base_signal = clamp_score((0.58 * need_severity) + (0.42 * contextual_gain))
        score = clamp_score(
            base_signal
            + (0.25 * need_severity)
            + (0.15 * contextual_gain)
            - (0.15 * resource_cost)
            - (0.1 * (1.0 - trust_score))
            - (0.08 * policy_risk)
            + (0.1 * clamp_score(historical_feedback))
        )
        if action == "split":
            threshold = profile["split_threshold"]
            attractive = score >= threshold
        elif action == "merge":
            threshold = profile["merge_threshold"]
            attractive = score >= threshold
        else:
            threshold = 0.5
            attractive = score >= threshold
        return {
            "action": action,
            "profile_ref": profile_ref or "default",
            "profile": profile,
            "base_signal": base_signal,
            "need_severity": clamp_score(need_severity),
            "contextual_gain": clamp_score(contextual_gain),
            "resource_cost": clamp_score(resource_cost),
            "trust_score": clamp_score(trust_score),
            "policy_risk": clamp_score(policy_risk),
            "historical_feedback": clamp_score(historical_feedback),
            "utility_score": score,
            "threshold": round(float(threshold), 6),
            "attractive": attractive,
            "utility_band": utility_band(score),
        }

    def evaluate_runtime_choice(
        self,
        *,
        profile_ref: str | None,
        runtime_state: str,
        demand_score: float,
        current_load: float,
        need_pressure: float,
        trust_score: float,
        policy_risk: float,
        activation_cost_ms: int,
        working_memory_bytes: int,
        historical_feedback: float = 0.0,
    ) -> dict[str, Any]:
        scored = self.score_candidate(
            profile_ref=profile_ref,
            role_fit=demand_score,
            descriptor_usefulness=max(0.0, need_pressure),
            trust_score=trust_score,
            current_load=current_load,
            need_pressure=need_pressure,
            workspace_fit=demand_score,
            activation_cost_ms=activation_cost_ms,
            working_memory_bytes=working_memory_bytes,
            policy_risk=policy_risk,
            novelty_signal=max(0.0, need_pressure),
            historical_feedback=historical_feedback,
        )
        profile = scored["profile"]
        utility_score = float(scored["utility_score"])
        if runtime_state == "active":
            recommended = "hibernate" if utility_score <= float(profile["hibernate_threshold"]) else "stay_active"
            threshold = float(profile["hibernate_threshold"])
        elif runtime_state == "dormant":
            recommended = "reactivate" if utility_score >= float(profile["reactivate_threshold"]) else "stay_dormant"
            threshold = float(profile["reactivate_threshold"])
        elif runtime_state == "quarantined":
            recommended = "hold_quarantine"
            threshold = 1.0
        else:
            recommended = "hold"
            threshold = 1.0
        return {
            **scored,
            "runtime_state": runtime_state,
            "demand_score": clamp_score(demand_score),
            "recommended_action": recommended,
            "threshold": round(threshold, 6),
            "utility_band": utility_band(utility_score),
        }
