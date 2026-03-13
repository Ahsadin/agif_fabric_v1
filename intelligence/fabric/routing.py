"""Deterministic Phase 6 routing using descriptors, need pressure, and utility."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from intelligence.fabric.common import REPO_ROOT, load_json_file, repo_relative, write_json_atomic
from intelligence.fabric.governance.authority import AuthorityEngine
from intelligence.fabric.needs.engine import NeedSignalManager
from intelligence.fabric.state_store import FabricStateStore
from intelligence.fabric.utility import UtilityScorer, clamp_score, policy_risk_from_envelope, trust_score_from_ref


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
        promoted = [] if memory_manager is None else list(memory_manager.load_promoted_memories()["active"].values())
        candidate_contexts = self._build_candidate_contexts(logical_cells=logical_cells, runtime_states=runtime_states)
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
            authority_penalty = 0.0
            descriptor_usefulness = descriptor_info["score"]
            if descriptor_info["descriptor_refs"]:
                descriptor_need = self._first_need(needs_by_kind.get("trust_risk", []))
                review = authority_engine.evaluate_action(
                    action="descriptor_use",
                    proposer=f"routing:{workflow_id}",
                    need_signal=descriptor_need,
                    utility_evaluation={"utility_score": descriptor_info["score"], "threshold": 0.0},
                    policy_envelope=candidate["policy_envelope"],
                    trust_state={
                        "trust_ref": descriptor_info["trust_ref"],
                        "trust_score": descriptor_info["trust_score"],
                    },
                    rollback_ref=f"routing:reroute:{workflow_id}",
                    related_cells=[candidate["cell_id"]],
                    descriptor_refs=descriptor_info["descriptor_refs"],
                    metadata={"workflow_id": workflow_id, "candidate_id": candidate["cell_id"]},
                )
                authority_review_ids.append(review["review_id"])
                if review["approved"]:
                    approved_descriptor_refs.extend(descriptor_info["descriptor_refs"])
                else:
                    descriptor_usefulness = 0.0
                    authority_penalty = 0.18
                    if descriptor_need is not None:
                        need_manager.resolve_signal(
                            need_signal_id=str(descriptor_need["need_signal_id"]),
                            resolution_ref=review["review_id"],
                            status="vetoed",
                            actor="governance:authority",
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
            )
            total_score = clamp_score(
                (0.26 * role_fit)
                + (0.18 * descriptor_usefulness)
                + (0.12 * trust_score)
                + (0.11 * workspace_fit)
                + (0.10 * need_pressure)
                + (0.23 * float(utility_trace["utility_score"]))
                - (0.14 * current_load)
                - authority_penalty
            )
            candidate_scores.append(
                {
                    "cell_id": candidate["cell_id"],
                    "role_name": candidate["role_name"],
                    "runtime_state": candidate["runtime_state"],
                    "role_fit": clamp_score(role_fit),
                    "descriptor_usefulness": clamp_score(descriptor_usefulness),
                    "descriptor_refs": descriptor_info["descriptor_refs"],
                    "trust_score": trust_score,
                    "current_load": clamp_score(current_load),
                    "need_pressure": clamp_score(need_pressure),
                    "workspace_fit": clamp_score(workspace_fit),
                    "policy_risk": clamp_score(policy_risk),
                    "utility": utility_trace,
                    "authority_penalty": clamp_score(authority_penalty),
                    "total_score": total_score,
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
                    ),
                }
            )

        decision_id = f"routing_{len(self.load_decisions()) + 1:05d}"
        selected_cells = self._select_cells(candidate_scores=candidate_scores, needs_audit=needs_audit)
        decision = {
            "decision_id": decision_id,
            "workflow_id": workflow_id,
            "workflow_name": str(workflow_payload.get("workflow_name", "document_workflow")),
            "selected_cells": selected_cells,
            "candidate_scores": sorted(candidate_scores, key=lambda item: (-float(item["total_score"]), str(item["cell_id"]))),
            "need_signal_ids": [item["need_signal_id"] for item in active_signals],
            "generated_signal_ids": [item["need_signal_id"] for item in generated_signals],
            "descriptor_refs_used": sorted(set(approved_descriptor_refs)),
            "authority_review_ids": sorted(set(authority_review_ids)),
            "workspace_context": {
                "document_type": inputs.get("document_type"),
                "vendor_name": inputs.get("vendor_name"),
                "requires_audit": needs_audit,
            },
        }
        self._append_decision(decision)
        for review_id in sorted(set(authority_review_ids)):
            authority_engine.finalize_review(review_id, action_ref=decision_id, rollback_ref=f"routing:reroute:{decision_id}")
        self._resolve_routing_signals(
            need_manager=need_manager,
            decision=decision,
            needs_by_kind=needs_by_kind,
        )
        return decision

    def load_decisions(self) -> list[dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.routing_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.routing_decisions.v1", "entries": []},
        )
        return [deepcopy(item) for item in payload["entries"]]

    def summary(self) -> dict[str, Any]:
        decisions = self.load_decisions()
        selected_counts: dict[str, int] = {}
        for decision in decisions:
            for cell_id in decision.get("selected_cells", []):
                selected_counts[cell_id] = selected_counts.get(cell_id, 0) + 1
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

    def _build_candidate_contexts(
        self,
        *,
        logical_cells: dict[str, Any],
        runtime_states: dict[str, Any],
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
            contexts.append(
                {
                    "cell_id": cell_id,
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
        best_trust_ref = candidate["trust_ref"]
        best_trust_score = candidate["trust_score"]
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
            score = clamp_score(
                (0.34 * float(record.get("value_score", 0.0)))
                + (0.24 * float(record.get("trust_score", candidate["trust_score"])))
                + (0.18 * min(1.0, float(record.get("reuse_count", 0)) / 2.0))
                + (0.12 * scope_match)
                + (0.12 * payload_match)
            )
            if score > best_score:
                best_score = score
                best_refs = [str(record.get("descriptor_id"))]
                best_trust_ref = str(record.get("trust_ref", candidate["trust_ref"]))
                best_trust_score = float(record.get("trust_score", candidate["trust_score"]))
        return {
            "score": clamp_score(best_score),
            "descriptor_refs": best_refs,
            "trust_ref": best_trust_ref,
            "trust_score": clamp_score(best_trust_score),
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
    ) -> list[str]:
        reasons = [
            f"role_fit={clamp_score(role_fit)}",
            f"descriptor_usefulness={clamp_score(descriptor_info['score'])}",
            f"trust={clamp_score(trust_score)}",
            f"load={clamp_score(current_load)}",
            f"need_pressure={clamp_score(need_pressure)}",
            f"workspace_fit={clamp_score(workspace_fit)}",
            f"utility={clamp_score(utility_score)}",
        ]
        if authority_penalty > 0.0:
            reasons.append(f"authority_penalty={clamp_score(authority_penalty)}")
        if candidate["runtime_state"] == "dormant":
            reasons.append("reactivation_candidate")
        return reasons

    def _select_cells(self, *, candidate_scores: list[dict[str, Any]], needs_audit: bool) -> list[str]:
        if len(candidate_scores) <= 2:
            return [
                item["cell_id"]
                for item in sorted(candidate_scores, key=lambda item: str(item["cell_id"]))
                if float(item["total_score"]) > 0.1
            ]
        route_candidates = [item for item in candidate_scores if "router" in item["role_name"]]
        route_candidates.sort(key=lambda item: (-float(item["total_score"]), str(item["cell_id"])))
        selected: list[str] = []
        if route_candidates and float(route_candidates[0]["total_score"]) > 0.1:
            selected.append(route_candidates[0]["cell_id"])
        if needs_audit:
            audit_candidates = [
                item
                for item in candidate_scores
                if "audit" in item["role_name"] and item["cell_id"] not in selected
            ]
            audit_candidates.sort(key=lambda item: (-float(item["total_score"]), str(item["cell_id"])))
            if audit_candidates and float(audit_candidates[0]["total_score"]) > 0.1:
                selected.append(audit_candidates[0]["cell_id"])
        return selected

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
        if decision["selected_cells"]:
            for signal in needs_by_kind.get("novelty", []) + needs_by_kind.get("coordination_gap", []):
                need_manager.resolve_signal(
                    need_signal_id=str(signal["need_signal_id"]),
                    resolution_ref=decision["decision_id"],
                    status="resolved",
                    actor="routing:selection",
                )
        if len([item for item in decision["selected_cells"] if "audit" in item]) > 0:
            for signal in needs_by_kind.get("uncertainty", []):
                need_manager.resolve_signal(
                    need_signal_id=str(signal["need_signal_id"]),
                    resolution_ref=decision["decision_id"],
                    status="resolved",
                    actor="routing:audit_selection",
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
