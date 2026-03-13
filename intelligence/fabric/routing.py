"""Deterministic Phase 6 routing using descriptors, need pressure, and utility."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from intelligence.fabric.common import REPO_ROOT, load_json_file, repo_relative, utc_now_iso, write_json_atomic
from intelligence.fabric.governance.authority import AuthorityEngine
from intelligence.fabric.needs.engine import NeedSignalManager
from intelligence.fabric.state_store import FabricStateStore
from intelligence.fabric.utility import (
    UtilityScorer,
    clamp_score,
    policy_risk_from_envelope,
    trust_score_from_ref,
    utility_band,
)


CONFIDENCE_BANDS = (
    (0.72, "strong"),
    (0.52, "moderate"),
    (0.32, "low"),
)


class RoutingEngine:
    """Routes workflow demand across logical cells using Phase 6 context."""

    def __init__(
        self,
        *,
        store: FabricStateStore,
        state: dict[str, Any],
        config: dict[str, Any],
        registry: dict[str, Any],
    ):
        self.store = store
        self.state = dict(state)
        self.config = config
        self.registry = registry
        self.fabric_id = str(state["fabric_id"])
        self.utility = UtilityScorer(registry.get("utility_profiles", {}))
        self.ensure_store()

    def ensure_store(self) -> None:
        self._load_or_initialize(
            self.store.routing_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.routing_decisions.v1", "entries": []},
        )
        self._load_or_initialize(
            self.store.routing_memory_path(self.fabric_id),
            {"schema_version": "agif.fabric.routing_memory.v1", "cell_stats": {}, "decision_outcomes": {}},
        )

    def route_workflow(
        self,
        *,
        workflow_id: str,
        workflow_payload: dict[str, Any],
        need_manager: NeedSignalManager,
        authority_engine: AuthorityEngine,
        memory_manager: Any | None = None,
    ) -> dict[str, Any]:
        logical_cells = self._load_logical_cells()
        runtime_states = self._load_runtime_states()
        lineage_metrics = self._load_lineage_metrics()
        routing_memory = self._load_routing_memory()
        promoted = [] if memory_manager is None else list(memory_manager.load_promoted_memories()["active"].values())
        candidate_contexts = self._build_candidate_contexts(
            logical_cells=logical_cells,
            runtime_states=runtime_states,
            lineage_metrics=lineage_metrics,
        )
        generated_signals = need_manager.record_generated_signals(
            workflow_id=workflow_id,
            workflow_payload=workflow_payload,
            candidate_contexts=candidate_contexts,
            promoted_memories=promoted,
        )
        active_signals = need_manager.active_signals()
        needs_by_kind = self._group_needs(active_signals)
        needs_route = True
        needs_audit = self._requires_audit(workflow_payload)
        candidate_scores: list[dict[str, Any]] = []
        approved_descriptor_refs: list[str] = []
        authority_review_ids: list[str] = []
        approved_descriptor_memory_ids: list[str] = []
        inputs = workflow_payload.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}
        for candidate in candidate_contexts:
            role_fit = self._role_fit(candidate=candidate, workflow_payload=workflow_payload, needs_route=needs_route, needs_audit=needs_audit)
            workspace_fit = self._workspace_fit(candidate=candidate, workflow_payload=workflow_payload)
            descriptor_info = self._descriptor_usefulness(
                candidate=candidate,
                workflow_payload=workflow_payload,
                promoted_memories=promoted,
            )
            trust_score = clamp_score(max(float(candidate["trust_score"]), float(descriptor_info["trust_score"])))
            current_load = self._current_load(candidate, workflow_id=workflow_id)
            need_pressure = self._need_support(candidate=candidate, needs_by_kind=needs_by_kind)
            policy_risk = policy_risk_from_envelope(candidate["policy_envelope"], action="route")
            route_memory_info = self._route_memory_feedback(
                routing_memory=routing_memory,
                cell_id=str(candidate["cell_id"]),
            )
            lineage_adjustment = self._lineage_adjustment(candidate=candidate)
            authority_penalty = 0.0
            descriptor_usefulness = descriptor_info["score"]
            if descriptor_info["descriptor_refs"]:
                descriptor_need = self._first_need(needs_by_kind.get("trust_risk", []))
                review = authority_engine.evaluate_action(
                    action="descriptor_use",
                    proposer=f"routing:{workflow_id}",
                    need_signal=descriptor_need,
                    utility_evaluation={
                        "utility_score": descriptor_info["score"],
                        "threshold": 0.0,
                    },
                    policy_envelope=candidate["policy_envelope"],
                    trust_state={
                        "trust_ref": descriptor_info["trust_ref"],
                        "trust_score": descriptor_info["trust_score"],
                    },
                    rollback_ref=f"routing:reroute:{workflow_id}",
                    related_cells=[candidate["cell_id"]],
                    descriptor_refs=descriptor_info["descriptor_refs"],
                    metadata={
                        "workflow_id": workflow_id,
                        "candidate_id": candidate["cell_id"],
                        "lineage_id": candidate["lineage_id"],
                        "lineage_usefulness_score": candidate["lineage_usefulness_score"],
                        "descriptor_provenance_score": descriptor_info["provenance_score"],
                    },
                )
                authority_review_ids.append(review["review_id"])
                if review["approved"]:
                    approved_descriptor_refs.extend(descriptor_info["descriptor_refs"])
                    approved_descriptor_memory_ids.extend(descriptor_info["memory_ids"])
                else:
                    descriptor_usefulness = 0.0
                    authority_penalty = 0.18
                    if descriptor_need is not None:
                        need_manager.resolve_signal(
                            need_signal_id=str(descriptor_need["need_signal_id"]),
                            resolution_ref=review["review_id"],
                            status="vetoed",
                            actor="governance:authority",
                            effectiveness_score=0.0,
                            quality="unresolved_recurring",
                            notes="descriptor use vetoed under low trust or weak provenance",
                        )

            utility_trace = self.utility.score_candidate(
                profile_ref=candidate["utility_profile_ref"],
                role_fit=role_fit,
                descriptor_usefulness=descriptor_usefulness,
                trust_score=trust_score,
                current_load=current_load,
                need_pressure=need_pressure,
                workspace_fit=workspace_fit,
                activation_cost_ms=int(candidate["activation_cost_ms"]),
                working_memory_bytes=int(candidate["working_memory_bytes"]),
                policy_risk=policy_risk,
                novelty_signal=self._novelty_signal(needs_by_kind),
                historical_feedback=route_memory_info["score"],
            )
            total_score = clamp_score(
                (0.24 * role_fit)
                + (0.16 * descriptor_usefulness)
                + (0.1 * descriptor_info["provenance_score"])
                + (0.11 * trust_score)
                + (0.1 * workspace_fit)
                + (0.08 * need_pressure)
                + (0.08 * route_memory_info["score"])
                + (0.04 * candidate["lineage_usefulness_score"])
                + (0.19 * float(utility_trace["utility_score"]))
                + lineage_adjustment
                - (0.14 * current_load)
                - authority_penalty
            )
            candidate_scores.append(
                {
                    "cell_id": candidate["cell_id"],
                    "lineage_id": candidate["lineage_id"],
                    "role_name": candidate["role_name"],
                    "runtime_state": candidate["runtime_state"],
                    "route_capable": candidate["route_capable"],
                    "audit_capable": candidate["audit_capable"],
                    "role_fit": clamp_score(role_fit),
                    "descriptor_usefulness": clamp_score(descriptor_usefulness),
                    "descriptor_refs": descriptor_info["descriptor_refs"],
                    "descriptor_memory_ids": descriptor_info["memory_ids"],
                    "descriptor_provenance": descriptor_info["provenance_score"],
                    "trust_score": trust_score,
                    "current_load": clamp_score(current_load),
                    "need_pressure": clamp_score(need_pressure),
                    "workspace_fit": clamp_score(workspace_fit),
                    "policy_risk": clamp_score(policy_risk),
                    "routing_memory": route_memory_info,
                    "lineage_usefulness_score": candidate["lineage_usefulness_score"],
                    "lineage_adjustment": clamp_score(lineage_adjustment) if lineage_adjustment >= 0 else round(lineage_adjustment, 6),
                    "utility": utility_trace,
                    "authority_penalty": clamp_score(authority_penalty),
                    "total_score": total_score,
                    "decision_band": utility_band(total_score),
                    "reasons": self._build_reasons(
                        candidate=candidate,
                        role_fit=role_fit,
                        descriptor_info=descriptor_info,
                        trust_score=trust_score,
                        current_load=current_load,
                        need_pressure=need_pressure,
                        workspace_fit=workspace_fit,
                        utility_score=float(utility_trace["utility_score"]),
                        authority_penalty=authority_penalty,
                        route_memory_info=route_memory_info,
                        lineage_adjustment=lineage_adjustment,
                    ),
                    "rejected_for": self._rejected_for(
                        total_score=total_score,
                        utility_trace=utility_trace,
                        current_load=current_load,
                        authority_penalty=authority_penalty,
                        route_capable=bool(candidate["route_capable"]),
                    ),
                }
            )

        decision_id = f"routing_{len(self.load_decisions()) + 1:05d}"
        selection = self._select_route(candidate_scores=candidate_scores, needs_audit=needs_audit)
        decision = {
            "decision_id": decision_id,
            "workflow_id": workflow_id,
            "workflow_name": str(workflow_payload.get("workflow_name", "document_workflow")),
            "route_cell_id": selection["route_cell_id"],
            "selected_cells": selection["selected_cells"],
            "selection_mode": selection["selection_mode"],
            "route_confidence": selection["route_confidence"],
            "confidence_band": selection["confidence_band"],
            "abstained": selection["selection_mode"] == "abstained",
            "escalated": selection["selection_mode"] == "escalated",
            "decision_reason": selection["decision_reason"],
            "escalation_target_cells": selection["escalation_target_cells"],
            "candidate_scores": sorted(candidate_scores, key=lambda item: (-float(item["total_score"]), str(item["cell_id"]))),
            "rejected_candidates": selection["rejected_candidates"],
            "need_signal_ids": [item["need_signal_id"] for item in active_signals],
            "generated_signal_ids": [item["need_signal_id"] for item in generated_signals],
            "descriptor_refs_used": sorted(set(approved_descriptor_refs)),
            "authority_review_ids": sorted(set(authority_review_ids)),
            "workspace_context": {
                "document_type": inputs.get("document_type"),
                "vendor_name": inputs.get("vendor_name"),
                "requires_audit": needs_audit,
            },
            "route_memory_context": {
                "selected_route_memory_score": selection["route_memory_score"],
                "selected_lineage_usefulness": selection["selected_lineage_usefulness"],
            },
        }
        self._append_decision(decision)
        self._record_decision_memory(
            decision_id=decision_id,
            route_cell_id=selection["route_cell_id"],
            selected_cells=selection["selected_cells"],
            route_confidence=selection["route_confidence"],
            confidence_band=selection["confidence_band"],
            selection_mode=selection["selection_mode"],
            descriptor_refs_used=decision["descriptor_refs_used"],
        )
        for review_id in sorted(set(authority_review_ids)):
            authority_engine.finalize_review(review_id, action_ref=decision_id, rollback_ref=f"routing:reroute:{decision_id}")
        if approved_descriptor_memory_ids and selection["route_cell_id"]:
            self._note_descriptor_use(memory_ids=approved_descriptor_memory_ids)
        self._resolve_routing_signals(
            need_manager=need_manager,
            decision=decision,
            needs_by_kind=needs_by_kind,
        )
        return decision

    def record_outcome(
        self,
        *,
        decision_id: str,
        outcome_kind: str,
        effectiveness_score: float,
        detail: str,
    ) -> dict[str, Any]:
        routing_memory = self._load_routing_memory()
        outcome = deepcopy(routing_memory["decision_outcomes"].get(decision_id))
        if outcome is None:
            return {"decision_id": decision_id, "updated": False}
        route_cell_id = outcome.get("route_cell_id")
        routing_memory["decision_outcomes"][decision_id] = {
            **outcome,
            "outcome_kind": outcome_kind,
            "effectiveness_score": clamp_score(effectiveness_score),
            "detail": detail,
            "updated_utc": utc_now_iso(),
        }
        if route_cell_id:
            stats = self._default_cell_stats(cell_id=str(route_cell_id))
            stats.update(deepcopy(routing_memory["cell_stats"].get(str(route_cell_id), {})))
            stats["selected_count"] = int(stats.get("selected_count", 0)) + 1
            if outcome_kind == "success":
                stats["success_count"] = int(stats.get("success_count", 0)) + 1
            elif outcome_kind == "weak_success":
                stats["weak_outcome_count"] = int(stats.get("weak_outcome_count", 0)) + 1
            else:
                stats["failure_count"] = int(stats.get("failure_count", 0)) + 1
            if outcome.get("descriptor_refs_used"):
                if outcome_kind == "success":
                    stats["reviewed_descriptor_success_count"] = int(stats.get("reviewed_descriptor_success_count", 0)) + 1
                else:
                    stats["reviewed_descriptor_failure_count"] = int(stats.get("reviewed_descriptor_failure_count", 0)) + 1
            stats["avg_effectiveness_score"] = self._rolling_average(
                current=float(stats.get("avg_effectiveness_score", 0.0)),
                sample_count=int(stats["selected_count"]),
                next_value=clamp_score(effectiveness_score),
            )
            stats["avg_confidence_score"] = self._rolling_average(
                current=float(stats.get("avg_confidence_score", 0.0)),
                sample_count=int(stats["selected_count"]),
                next_value=float(outcome.get("route_confidence", 0.0)),
            )
            stats["last_outcome_kind"] = outcome_kind
            stats["last_detail"] = detail
            routing_memory["cell_stats"][str(route_cell_id)] = stats
        write_json_atomic(self.store.routing_memory_path(self.fabric_id), routing_memory)
        self._attach_decision_outcome(
            decision_id=decision_id,
            outcome_kind=outcome_kind,
            effectiveness_score=effectiveness_score,
            detail=detail,
        )
        return {"decision_id": decision_id, "updated": True}

    def load_decisions(self) -> list[dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.routing_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.routing_decisions.v1", "entries": []},
        )
        return [deepcopy(item) for item in payload["entries"]]

    def summary(self) -> dict[str, Any]:
        decisions = self.load_decisions()
        memory = self._load_routing_memory()
        selected_counts: dict[str, int] = {}
        for decision in decisions:
            for cell_id in decision.get("selected_cells", []):
                selected_counts[cell_id] = selected_counts.get(cell_id, 0) + 1
        abstained_count = len([item for item in decisions if item.get("selection_mode") == "abstained"])
        escalated_count = len([item for item in decisions if item.get("selection_mode") == "escalated"])
        successful_outcomes = len(
            [
                item
                for item in memory["decision_outcomes"].values()
                if str(item.get("outcome_kind")) in {"success", "weak_success"}
            ]
        )
        return {
            "decision_count": len(decisions),
            "descriptor_use_count": len([item for item in decisions if item.get("descriptor_refs_used")]),
            "authority_checked_count": len([item for item in decisions if item.get("authority_review_ids")]),
            "deterministic_reason_count": len(
                [
                    item
                    for item in decisions
                    if all(bool(candidate.get("reasons")) for candidate in item.get("candidate_scores", []))
                ]
            ),
            "abstained_count": abstained_count,
            "escalated_count": escalated_count,
            "successful_outcome_count": successful_outcomes,
            "selected_cell_counts": selected_counts,
            "latest_decision_ref": None if len(decisions) == 0 else decisions[-1]["decision_id"],
        }

    def _append_decision(self, decision: dict[str, Any]) -> None:
        payload = self._load_or_initialize(
            self.store.routing_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.routing_decisions.v1", "entries": []},
        )
        payload["entries"].append(deepcopy(decision))
        write_json_atomic(self.store.routing_decisions_path(self.fabric_id), payload)

    def _load_logical_cells(self) -> dict[str, Any]:
        payload = load_json_file(
            self.store.logical_population_path(self.fabric_id),
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label="Logical population",
        )
        if not isinstance(payload, dict):
            return {}
        return payload.get("cells", {})

    def _load_runtime_states(self) -> dict[str, Any]:
        payload = load_json_file(
            self.store.runtime_states_path(self.fabric_id),
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label="Runtime states",
        )
        if not isinstance(payload, dict):
            return {}
        return payload.get("states", {})

    def _load_lineage_metrics(self) -> dict[str, Any]:
        payload = self._load_or_initialize(
            self.store.lifecycle_metrics_path(self.fabric_id),
            {"schema_version": "agif.fabric.lifecycle.metrics.v1", "lineages": {}, "structural": {}},
        )
        return deepcopy(payload.get("lineages", {}))

    def _load_routing_memory(self) -> dict[str, Any]:
        return self._load_or_initialize(
            self.store.routing_memory_path(self.fabric_id),
            {"schema_version": "agif.fabric.routing_memory.v1", "cell_stats": {}, "decision_outcomes": {}},
        )

    def _build_candidate_contexts(
        self,
        *,
        logical_cells: dict[str, Any],
        runtime_states: dict[str, Any],
        lineage_metrics: dict[str, Any],
    ) -> list[dict[str, Any]]:
        contexts: list[dict[str, Any]] = []
        for cell_id, record in sorted(logical_cells.items()):
            blueprint = record["blueprint"]
            runtime = runtime_states.get(cell_id, {})
            runtime_state = str(runtime.get("runtime_state", record.get("lifecycle_state", "dormant")))
            if runtime_state in {"retired", "consolidating", "split_pending"}:
                continue
            allowed_actions = blueprint.get("policy_envelope", {}).get("allowed_actions", [])
            if not isinstance(allowed_actions, list):
                allowed_actions = []
            trust_ref = str(blueprint.get("trust_profile", {}).get("baseline", "bounded_local_v1"))
            lineage_id = str(record.get("lineage_id", cell_id))
            lineage = deepcopy(lineage_metrics.get(lineage_id, {}))
            contexts.append(
                {
                    "cell_id": cell_id,
                    "lineage_id": lineage_id,
                    "role_name": blueprint["role_name"],
                    "role_family": blueprint["role_family"],
                    "utility_profile_ref": blueprint["utility_profile_ref"],
                    "policy_envelope": deepcopy(blueprint["policy_envelope"]),
                    "activation_cost_ms": int(blueprint["activation_cost_ms"]),
                    "working_memory_bytes": int(blueprint["working_memory_bytes"]),
                    "allowed_tissues": list(blueprint["allowed_tissues"]),
                    "runtime_state": runtime_state,
                    "active_task_ref": runtime.get("active_task_ref"),
                    "loaded_descriptor_refs": list(runtime.get("loaded_descriptor_refs", [])),
                    "current_need_signals": list(runtime.get("current_need_signals", [])),
                    "route_capable": ("route" in allowed_actions) or ("router" in blueprint["role_name"]),
                    "audit_capable": ("report" in allowed_actions) or ("audit" in blueprint["role_name"]),
                    "trust_ref": trust_ref,
                    "trust_score": trust_score_from_ref(trust_ref),
                    "lineage_usefulness_score": clamp_score(float(lineage.get("usefulness_score", 0.0))),
                    "lineage_last_reason": lineage.get("last_usefulness_reason"),
                }
            )
        return contexts

    def _role_fit(
        self,
        *,
        candidate: dict[str, Any],
        workflow_payload: dict[str, Any],
        needs_route: bool,
        needs_audit: bool,
    ) -> float:
        priority_mode = bool(workflow_payload.get("priority_mode"))
        score = 0.08
        if needs_route and candidate["route_capable"]:
            score += 0.62
        if needs_audit and candidate["audit_capable"]:
            score += 0.62
        if priority_mode and "priority" in candidate["cell_id"]:
            score += 0.15
        if not priority_mode and "priority" in candidate["cell_id"]:
            score -= 0.1
        if "finance_document_workflow" in candidate["allowed_tissues"]:
            score += 0.1
        return clamp_score(score)

    def _workspace_fit(self, *, candidate: dict[str, Any], workflow_payload: dict[str, Any]) -> float:
        score = 0.2 if "finance_document_workflow" in candidate["allowed_tissues"] else 0.0
        if bool(workflow_payload.get("priority_mode")) and "priority" in candidate["cell_id"]:
            score += 0.2
        if self._requires_audit(workflow_payload) and candidate["audit_capable"]:
            score += 0.35
        if not self._requires_audit(workflow_payload) and candidate["route_capable"]:
            score += 0.35
        return clamp_score(score)

    def _descriptor_usefulness(
        self,
        *,
        candidate: dict[str, Any],
        workflow_payload: dict[str, Any],
        promoted_memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        best_score = 0.0
        best_refs: list[str] = []
        best_memory_ids: list[str] = []
        best_trust_ref = candidate["trust_ref"]
        best_trust_score = candidate["trust_score"]
        best_provenance_score = 0.0
        inputs = workflow_payload.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}
        workflow_name = str(workflow_payload.get("workflow_name", "document_workflow"))
        for record in promoted_memories:
            if str(record.get("producer_cell_id")) != candidate["cell_id"]:
                continue
            task_scope = str(record.get("task_scope", ""))
            scope_match = 1.0 if task_scope.split(":", 1)[0] == workflow_name else 0.0
            payload_match = 0.0
            payload_ref = record.get("payload_ref")
            if isinstance(payload_ref, str):
                payload_path = self._resolve_repo_ref(payload_ref)
                if payload_path.exists():
                    payload = load_json_file(
                        payload_path,
                        not_found_code="STATE_INVALID",
                        invalid_code="STATE_INVALID",
                        label=f"Promoted memory payload {record.get('memory_id')}",
                    )
                    if isinstance(payload, dict):
                        payload_match = self._payload_match_score(payload=payload, inputs=inputs)
            provenance_score = clamp_score(
                (0.42 * float(record.get("trust_score", candidate["trust_score"])))
                + (0.18 * min(1.0, float(record.get("review_count", 0)) / 3.0))
                + (0.22 * min(1.0, float(record.get("usefulness_hits", 0)) / 3.0))
                + (0.18 * min(1.0, float(record.get("reuse_count", 0)) / 2.0))
            )
            score = clamp_score(
                (0.28 * float(record.get("value_score", 0.0)))
                + (0.2 * float(record.get("trust_score", candidate["trust_score"])))
                + (0.14 * min(1.0, float(record.get("reuse_count", 0)) / 2.0))
                + (0.12 * scope_match)
                + (0.12 * payload_match)
                + (0.14 * provenance_score)
            )
            if score > best_score:
                best_score = score
                best_refs = [str(record.get("descriptor_id"))]
                best_memory_ids = [str(record.get("memory_id"))]
                best_trust_ref = str(record.get("trust_ref", candidate["trust_ref"]))
                best_trust_score = float(record.get("trust_score", candidate["trust_score"]))
                best_provenance_score = provenance_score
        return {
            "score": clamp_score(best_score),
            "descriptor_refs": best_refs,
            "memory_ids": best_memory_ids,
            "trust_ref": best_trust_ref,
            "trust_score": clamp_score(best_trust_score),
            "provenance_score": clamp_score(best_provenance_score),
        }

    def _payload_match_score(self, *, payload: dict[str, Any], inputs: dict[str, Any]) -> float:
        if payload.get("workflow_name") and payload.get("workflow_name") == inputs.get("workflow_name"):
            base = 0.25
        else:
            base = 0.0
        summary_vector = payload.get("summary_vector", [])
        if not isinstance(summary_vector, list):
            summary_vector = []
        vendor = str(inputs.get("vendor_name", "")).strip().lower()
        document_type = str(inputs.get("document_type", "")).strip().lower()
        currency = str(inputs.get("currency", "")).strip().lower()
        matched = 0.0
        for token in summary_vector:
            normalized = str(token).strip().lower()
            if normalized and normalized in {vendor[:18], document_type[:12], currency[:8]}:
                matched += 0.2
        return clamp_score(base + matched)

    def _current_load(self, candidate: dict[str, Any], *, workflow_id: str) -> float:
        active_task_ref = candidate.get("active_task_ref")
        if candidate["runtime_state"] != "active":
            return 0.05 if candidate["runtime_state"] == "dormant" else 0.8
        if active_task_ref in {None, "", workflow_id}:
            return 0.1
        return 0.85

    def _need_support(self, *, candidate: dict[str, Any], needs_by_kind: dict[str, list[dict[str, Any]]]) -> float:
        support = 0.0
        if candidate["route_capable"]:
            support += sum(0.22 * float(item["severity"]) for item in needs_by_kind.get("coordination_gap", []))
            support += sum(0.18 * float(item["severity"]) for item in needs_by_kind.get("novelty", []))
        if candidate["audit_capable"]:
            support += sum(0.22 * float(item["severity"]) for item in needs_by_kind.get("uncertainty", []))
        if candidate["runtime_state"] == "dormant":
            support += sum(0.15 * float(item["severity"]) for item in needs_by_kind.get("coordination_gap", []))
        if candidate["runtime_state"] == "active":
            support -= sum(0.2 * float(item["severity"]) for item in needs_by_kind.get("overload", []))
        if candidate["trust_score"] < 0.6:
            support -= sum(0.25 * float(item["severity"]) for item in needs_by_kind.get("trust_risk", []))
        return clamp_score(support)

    def _build_reasons(
        self,
        *,
        candidate: dict[str, Any],
        role_fit: float,
        descriptor_info: dict[str, Any],
        trust_score: float,
        current_load: float,
        need_pressure: float,
        workspace_fit: float,
        utility_score: float,
        authority_penalty: float,
        route_memory_info: dict[str, Any],
        lineage_adjustment: float,
    ) -> list[str]:
        reasons = [
            f"role_fit={clamp_score(role_fit)}",
            f"descriptor_usefulness={clamp_score(descriptor_info['score'])}",
            f"descriptor_provenance={clamp_score(descriptor_info['provenance_score'])}",
            f"trust={clamp_score(trust_score)}",
            f"load={clamp_score(current_load)}",
            f"need_pressure={clamp_score(need_pressure)}",
            f"workspace_fit={clamp_score(workspace_fit)}",
            f"utility={clamp_score(utility_score)}",
            f"routing_memory={clamp_score(route_memory_info['score'])}",
            f"lineage_adjustment={round(lineage_adjustment, 6)}",
        ]
        if authority_penalty > 0.0:
            reasons.append(f"authority_penalty={clamp_score(authority_penalty)}")
        if candidate["runtime_state"] == "dormant":
            reasons.append("reactivation_candidate")
        if candidate.get("lineage_last_reason"):
            reasons.append(f"lineage_reason={candidate['lineage_last_reason']}")
        return reasons

    def _rejected_for(
        self,
        *,
        total_score: float,
        utility_trace: dict[str, Any],
        current_load: float,
        authority_penalty: float,
        route_capable: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not route_capable:
            reasons.append("not_route_capable")
        if total_score < 0.28:
            reasons.append("below_route_floor")
        if utility_trace["utility_band"] == "weak":
            reasons.append("weak_utility")
        if utility_trace["utility_band"] == "abstain":
            reasons.append("utility_abstain")
        if current_load >= 0.8:
            reasons.append("high_load")
        if authority_penalty > 0.0:
            reasons.append("authority_penalized")
        return reasons

    def _select_route(self, *, candidate_scores: list[dict[str, Any]], needs_audit: bool) -> dict[str, Any]:
        ranked = sorted(candidate_scores, key=lambda item: (-float(item["total_score"]), str(item["cell_id"])))
        benchmark_name = str(self.config.get("benchmark_profile", {}).get("name", ""))
        if not benchmark_name.startswith("phase6") and len(ranked) <= 2:
            selected_cells = sorted(item["cell_id"] for item in ranked if float(item["total_score"]) > 0.1)
            route_cell_id = None
            for item in ranked:
                if item["route_capable"] and item["cell_id"] in selected_cells:
                    route_cell_id = str(item["cell_id"])
                    break
            return {
                "route_cell_id": route_cell_id,
                "selected_cells": selected_cells,
                "selection_mode": "selected",
                "route_confidence": 0.74,
                "confidence_band": "strong",
                "decision_reason": "legacy bounded multi-cell routing preserved for pre-phase6 profiles",
                "escalation_target_cells": [],
                "rejected_candidates": self._summarize_rejections(ranked),
                "route_memory_score": 0.5,
                "selected_lineage_usefulness": 0.0 if route_cell_id is None else clamp_score(float(ranked[0]["lineage_usefulness_score"])),
            }
        route_candidates = [item for item in ranked if item["route_capable"]]
        audit_candidates = [item for item in ranked if item["audit_capable"] and item["cell_id"] not in {item.get("cell_id") for item in route_candidates[:1]}]
        top_route = None if not route_candidates else route_candidates[0]
        second_route_score = 0.0 if len(route_candidates) < 2 else float(route_candidates[1]["total_score"])
        if top_route is None:
            return {
                "route_cell_id": None,
                "selected_cells": [],
                "selection_mode": "abstained",
                "route_confidence": 0.0,
                "confidence_band": "abstain",
                "decision_reason": "no route-capable candidate remained available",
                "escalation_target_cells": [item["cell_id"] for item in audit_candidates[:1]],
                "rejected_candidates": self._summarize_rejections(ranked),
                "route_memory_score": 0.0,
                "selected_lineage_usefulness": 0.0,
            }
        route_confidence = self._route_confidence(top_route=top_route, second_route_score=second_route_score)
        confidence_band = self._confidence_band(route_confidence)
        route_floor = float(top_route["total_score"])
        selection_mode = "selected"
        decision_reason = f"selected {top_route['cell_id']} with {confidence_band} confidence"
        if route_floor < 0.28 or confidence_band == "abstain":
            selection_mode = "abstained"
            decision_reason = f"abstained because {top_route['cell_id']} stayed below the route floor"
        elif confidence_band == "low" or (top_route["decision_band"] == "weak" and route_floor < 0.35):
            selection_mode = "escalated"
            decision_reason = f"escalated because {top_route['cell_id']} was the best route but confidence stayed low"
        selected_cells: list[str] = []
        escalation_targets: list[str] = []
        if selection_mode == "selected":
            selected_cells.append(str(top_route["cell_id"]))
            if needs_audit:
                strong_audit = [item for item in ranked if item["audit_capable"] and float(item["total_score"]) >= 0.38 and item["cell_id"] not in selected_cells]
                if strong_audit:
                    selected_cells.append(str(strong_audit[0]["cell_id"]))
        else:
            escalation_targets = [item["cell_id"] for item in audit_candidates[:1]]
        return {
            "route_cell_id": None if selection_mode != "selected" else str(top_route["cell_id"]),
            "selected_cells": selected_cells,
            "selection_mode": selection_mode,
            "route_confidence": route_confidence,
            "confidence_band": confidence_band,
            "decision_reason": decision_reason,
            "escalation_target_cells": escalation_targets,
            "rejected_candidates": self._summarize_rejections(ranked),
            "route_memory_score": clamp_score(float(top_route["routing_memory"]["score"])),
            "selected_lineage_usefulness": clamp_score(float(top_route["lineage_usefulness_score"])),
        }

    def _route_confidence(self, *, top_route: dict[str, Any], second_route_score: float) -> float:
        margin = max(0.0, float(top_route["total_score"]) - second_route_score)
        confidence = clamp_score(
            0.28
            + (0.36 * float(top_route["total_score"]))
            + (0.1 * margin)
            + (0.16 * float(top_route["utility"]["utility_score"]))
            + (0.12 * float(top_route["trust_score"]))
            + (0.06 * float(top_route["descriptor_provenance"]))
            + (0.04 * float(top_route["lineage_usefulness_score"]))
        )
        return confidence

    def _confidence_band(self, confidence: float) -> str:
        normalized = clamp_score(confidence)
        for threshold, label in CONFIDENCE_BANDS:
            if normalized >= threshold:
                return label
        return "abstain"

    def _summarize_rejections(self, ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rejections: list[dict[str, Any]] = []
        for item in ranked[1:4]:
            rejections.append(
                {
                    "cell_id": item["cell_id"],
                    "total_score": item["total_score"],
                    "rejected_for": list(item.get("rejected_for", [])),
                }
            )
        return rejections

    def _requires_audit(self, workflow_payload: dict[str, Any]) -> bool:
        if bool(workflow_payload.get("requires_audit")):
            return True
        inputs = workflow_payload.get("inputs", {})
        if not isinstance(inputs, dict):
            return False
        if bool(inputs.get("requires_audit")):
            return True
        total_raw = str(inputs.get("total", "")).replace(",", "")
        try:
            return float(total_raw) >= 500.0
        except ValueError:
            return False

    def _resolve_routing_signals(
        self,
        *,
        need_manager: NeedSignalManager,
        decision: dict[str, Any],
        needs_by_kind: dict[str, list[dict[str, Any]]],
    ) -> None:
        confidence = float(decision.get("route_confidence", 0.0))
        route_quality = "resolved_well" if confidence >= 0.72 else "resolved_weakly"
        if decision["selection_mode"] == "selected":
            for signal in needs_by_kind.get("novelty", []) + needs_by_kind.get("coordination_gap", []):
                need_manager.resolve_signal(
                    need_signal_id=str(signal["need_signal_id"]),
                    resolution_ref=decision["decision_id"],
                    status="resolved",
                    actor="routing:selection",
                    effectiveness_score=confidence,
                    quality=route_quality,
                    notes=f"routing {route_quality} via {decision['route_cell_id']}",
                )
        else:
            for signal in needs_by_kind.get("novelty", []) + needs_by_kind.get("coordination_gap", []) + needs_by_kind.get("uncertainty", []):
                need_manager.resolve_signal(
                    need_signal_id=str(signal["need_signal_id"]),
                    resolution_ref=decision["decision_id"],
                    status="reviewed",
                    actor="routing:selection",
                    effectiveness_score=confidence,
                    quality="unresolved_recurring" if decision["selection_mode"] == "abstained" else "resolved_weakly",
                    notes=decision["decision_reason"],
                )
        if len([item for item in decision["selected_cells"] if "audit" in item]) > 0:
            for signal in needs_by_kind.get("uncertainty", []):
                need_manager.resolve_signal(
                    need_signal_id=str(signal["need_signal_id"]),
                    resolution_ref=decision["decision_id"],
                    status="resolved",
                    actor="routing:audit_selection",
                    effectiveness_score=max(confidence, 0.68),
                    quality="resolved_well" if confidence >= 0.52 else "resolved_weakly",
                    notes="audit-capable reviewer selected under uncertainty",
                )

    def _group_needs(self, needs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in needs:
            grouped.setdefault(str(item["signal_kind"]), []).append(item)
        return grouped

    def _novelty_signal(self, needs_by_kind: dict[str, list[dict[str, Any]]]) -> float:
        novelty = needs_by_kind.get("novelty", [])
        if not novelty:
            return 0.0
        return clamp_score(max(float(item["severity"]) for item in novelty))

    def _first_need(self, values: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not values:
            return None
        return deepcopy(sorted(values, key=lambda item: str(item["need_signal_id"]))[0])

    def _resolve_repo_ref(self, ref: str) -> Any:
        from pathlib import Path

        value = Path(ref)
        if value.is_absolute():
            return value.resolve()
        return (REPO_ROOT / ref).resolve()

    def _route_memory_feedback(self, *, routing_memory: dict[str, Any], cell_id: str) -> dict[str, Any]:
        stats = deepcopy(routing_memory["cell_stats"].get(cell_id, self._default_cell_stats(cell_id=cell_id)))
        if int(stats.get("selected_count", 0)) == 0:
            return {
                "score": 0.5,
                "selected_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_effectiveness_score": 0.0,
                "last_outcome_kind": None,
            }
        selected_count = max(1, int(stats.get("selected_count", 0)))
        descriptor_total = max(
            1,
            int(stats.get("reviewed_descriptor_success_count", 0)) + int(stats.get("reviewed_descriptor_failure_count", 0)),
        )
        success_rate = int(stats.get("success_count", 0)) / float(selected_count)
        weak_rate = int(stats.get("weak_outcome_count", 0)) / float(selected_count)
        failure_rate = int(stats.get("failure_count", 0)) / float(selected_count)
        descriptor_success_rate = int(stats.get("reviewed_descriptor_success_count", 0)) / float(descriptor_total)
        score = clamp_score(
            0.5
            + (0.28 * success_rate)
            + (0.1 * weak_rate)
            + (0.12 * float(stats.get("avg_effectiveness_score", 0.0)))
            + (0.08 * descriptor_success_rate)
            - (0.32 * failure_rate)
        )
        return {
            "score": score,
            "selected_count": int(stats.get("selected_count", 0)),
            "success_count": int(stats.get("success_count", 0)),
            "failure_count": int(stats.get("failure_count", 0)),
            "avg_effectiveness_score": float(stats.get("avg_effectiveness_score", 0.0)),
            "last_outcome_kind": stats.get("last_outcome_kind"),
        }

    def _lineage_adjustment(self, *, candidate: dict[str, Any]) -> float:
        score = float(candidate.get("lineage_usefulness_score", 0.0))
        return round((score - 0.25) * 0.08, 6)

    def _record_decision_memory(
        self,
        *,
        decision_id: str,
        route_cell_id: str | None,
        selected_cells: list[str],
        route_confidence: float,
        confidence_band: str,
        selection_mode: str,
        descriptor_refs_used: list[str],
    ) -> None:
        routing_memory = self._load_routing_memory()
        routing_memory["decision_outcomes"][decision_id] = {
            "decision_id": decision_id,
            "route_cell_id": route_cell_id,
            "selected_cells": list(selected_cells),
            "route_confidence": clamp_score(route_confidence),
            "confidence_band": confidence_band,
            "selection_mode": selection_mode,
            "descriptor_refs_used": list(descriptor_refs_used),
            "outcome_kind": "pending",
            "effectiveness_score": None,
            "detail": None,
            "updated_utc": utc_now_iso(),
        }
        if route_cell_id:
            stats = deepcopy(routing_memory["cell_stats"].get(route_cell_id, self._default_cell_stats(cell_id=route_cell_id)))
            stats["decision_count"] = int(stats.get("decision_count", 0)) + 1
            routing_memory["cell_stats"][route_cell_id] = stats
        write_json_atomic(self.store.routing_memory_path(self.fabric_id), routing_memory)

    def _attach_decision_outcome(
        self,
        *,
        decision_id: str,
        outcome_kind: str,
        effectiveness_score: float,
        detail: str,
    ) -> None:
        decisions = self._load_or_initialize(
            self.store.routing_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.routing_decisions.v1", "entries": []},
        )
        for entry in decisions["entries"]:
            if str(entry.get("decision_id")) != decision_id:
                continue
            entry["outcome"] = {
                "outcome_kind": outcome_kind,
                "effectiveness_score": clamp_score(effectiveness_score),
                "detail": detail,
            }
            break
        write_json_atomic(self.store.routing_decisions_path(self.fabric_id), decisions)

    def _note_descriptor_use(self, *, memory_ids: list[str]) -> None:
        promoted = self._load_or_initialize(
            self.store.promoted_memory_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.promoted.v1", "active": {}, "archived": {}},
        )
        changed = False
        for memory_id in memory_ids:
            record = promoted["active"].get(memory_id)
            if record is None:
                continue
            record["usefulness_hits"] = int(record.get("usefulness_hits", 0)) + 1
            changed = True
        if changed:
            write_json_atomic(self.store.promoted_memory_path(self.fabric_id), promoted)

    def _default_cell_stats(self, *, cell_id: str) -> dict[str, Any]:
        return {
            "cell_id": cell_id,
            "decision_count": 0,
            "selected_count": 0,
            "success_count": 0,
            "weak_outcome_count": 0,
            "failure_count": 0,
            "reviewed_descriptor_success_count": 0,
            "reviewed_descriptor_failure_count": 0,
            "avg_effectiveness_score": 0.0,
            "avg_confidence_score": 0.0,
            "last_outcome_kind": None,
            "last_detail": None,
        }

    def _rolling_average(self, *, current: float, sample_count: int, next_value: float) -> float:
        if sample_count <= 0:
            return clamp_score(next_value)
        prior_count = max(0, sample_count - 1)
        total = (current * prior_count) + next_value
        return round(total / float(sample_count), 6)

    def _load_or_initialize(self, path: Any, default_payload: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        value = load_json_file(
            path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label=repo_relative(path),
        )
        if not isinstance(value, dict):
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        return value
