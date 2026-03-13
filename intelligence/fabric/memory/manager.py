"""Reviewed memory, consolidation, and bounded growth controls for AGIF v1 Phase 5."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from intelligence.fabric.common import (
    FabricError,
    canonical_json_bytes,
    canonical_json_hash,
    ensure_exact_keys,
    ensure_non_empty_string,
    load_json_file,
    repo_relative,
    utc_now_iso,
    write_json_atomic,
)
from intelligence.fabric.state_store import FabricStateStore


ALLOWED_TIERS = {"hot", "warm", "cold"}
ALLOWED_DECISIONS = {"reject", "defer", "promote", "compress", "retire"}
DECISION_FIELDS = (
    "candidate_id",
    "reviewer_id",
    "decision",
    "compression_mode",
    "retention_tier",
    "reason",
    "rollback_ref",
    "created_utc",
)
DESCRIPTOR_FIELDS = (
    "descriptor_id",
    "producer_cell_id",
    "descriptor_kind",
    "task_scope",
    "cost_score",
    "confidence_score",
    "payload_ref",
    "storage_tier",
    "retention_policy",
    "trust_ref",
    "created_utc",
    "supersedes_descriptor_id",
)
MEMORY_CLASS_NAMES = {
    "correction_memory",
    "pattern_memory",
    "routing_useful_memory",
    "failure_memory",
    "policy_useful_memory",
}


class FabricMemoryManager:
    """Manages reviewed memory tiers, promotion decisions, and bounded retention."""

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
        self.memory_caps = self._memory_caps()
        self.default_reviewer_id = ensure_non_empty_string(
            self.config.get("governance_policy", {}).get("default_memory_reviewer")
            or self.config.get("governance_policy", {}).get("default_governance_approver")
            or "governance:phase5_memory_reviewer",
            "default_memory_reviewer",
            code="MEMORY_INVALID",
        )
        self.ensure_store()

    def ensure_store(self) -> None:
        self.store.memory_dir(self.fabric_id).mkdir(parents=True, exist_ok=True)
        self.store.memory_tier_payload_path(self.fabric_id, "hot", "placeholder").parent.mkdir(parents=True, exist_ok=True)
        self.store.memory_tier_payload_path(self.fabric_id, "warm", "placeholder").parent.mkdir(parents=True, exist_ok=True)
        self.store.memory_tier_payload_path(self.fabric_id, "cold", "placeholder").parent.mkdir(parents=True, exist_ok=True)
        self.store.raw_log_payload_path(self.fabric_id, "placeholder").parent.mkdir(parents=True, exist_ok=True)
        self._load_or_initialize(
            self.store.hot_memory_index_path(self.fabric_id),
            {
                "schema_version": "agif.fabric.memory.hot_index.v1",
                "workspace_refs": [],
                "current_task_refs": [],
                "live_runtime_state_ref": repo_relative(self.store.runtime_states_path(self.fabric_id)),
                "review_buffer_candidate_ids": [],
                "updated_utc": utc_now_iso(),
            },
        )
        self._load_or_initialize(
            self.store.raw_log_index_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.raw_logs.v1", "entries": []},
        )
        self._load_or_initialize(
            self.store.memory_candidates_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.candidates.v1", "entries": {}},
        )
        self._load_or_initialize(
            self.store.memory_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.decisions.v1", "entries": []},
        )
        self._load_or_initialize(
            self.store.descriptor_store_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.descriptors.v1", "active": {}, "archived": {}},
        )
        self._load_or_initialize(
            self.store.promoted_memory_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.promoted.v1", "active": {}, "archived": {}},
        )
        self._load_or_initialize(
            self.store.memory_replay_store_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.replay_store.v1", "entries": []},
        )
        self._load_or_initialize(
            self.store.memory_gc_log_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.gc_log.v1", "entries": []},
        )
        self.refresh_hot_memory()

    def record_run(
        self,
        *,
        workflow_payload: dict[str, Any],
        execution: dict[str, Any],
        run_ref: str,
        workspace_ref: str,
        lifecycle_manager: Any | None = None,
        routing_decision: dict[str, Any] | None = None,
        authority_engine: Any | None = None,
    ) -> dict[str, Any]:
        raw_log = self.record_raw_log(
            workflow_payload=workflow_payload,
            execution=execution,
            run_ref=run_ref,
            workspace_ref=workspace_ref,
        )
        candidate = self.nominate_run_candidate(
            workflow_payload=workflow_payload,
            execution=execution,
            run_ref=run_ref,
            workspace_ref=workspace_ref,
            raw_log_ref=raw_log["payload_ref"],
            selected_cells_override=None if routing_decision is None else list(routing_decision.get("selected_cells", [])),
        )
        default_review = self._default_review_decision(candidate["candidate_id"])
        review = self.review_candidate(
            candidate_id=candidate["candidate_id"],
            reviewer_id=self.default_reviewer_id,
            decision=default_review["decision"],
            compression_mode=default_review["compression_mode"],
            retention_tier=default_review["retention_tier"],
            reason=default_review["reason"],
            lifecycle_manager=lifecycle_manager,
            authority_engine=authority_engine,
        )
        consolidation = self.consolidate_if_needed(
            lifecycle_manager=lifecycle_manager,
            reason="post_run_memory_pressure_review",
        )
        gc_result = self.garbage_collect(
            reason="post_run_memory_gc",
            lifecycle_manager=lifecycle_manager,
        )
        self.refresh_hot_memory()
        return {
            "raw_log_id": raw_log["log_id"],
            "candidate_id": candidate["candidate_id"],
            "decision": review["decision"],
            "decision_ref": review["decision_ref"],
            "promoted_memory_id": review.get("memory_id"),
            "descriptor_id": review.get("descriptor_id"),
            "consolidation_triggered": consolidation["triggered"],
            "gc_removed_payloads": gc_result["removed_payload_count"],
        }

    def record_raw_log(
        self,
        *,
        workflow_payload: dict[str, Any],
        execution: dict[str, Any],
        run_ref: str,
        workspace_ref: str,
    ) -> dict[str, Any]:
        raw_logs = self._load_or_initialize(
            self.store.raw_log_index_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.raw_logs.v1", "entries": []},
        )
        log_id = self._next_numeric_id("log", [str(item.get("log_id", "")) for item in raw_logs["entries"]])
        payload = {
            "schema_version": "agif.fabric.memory.raw_log.v1",
            "event_kind": "workflow_run",
            "workflow_id": execution["workflow_id"],
            "workflow_payload": workflow_payload,
            "trace": execution["trace"],
            "output_digest": execution["output_digest"],
            "run_ref": run_ref,
            "workspace_ref": workspace_ref,
            "created_utc": utc_now_iso(),
        }
        payload_path = self.store.raw_log_payload_path(self.fabric_id, log_id)
        write_json_atomic(payload_path, payload)
        entry = {
            "log_id": log_id,
            "workflow_id": execution["workflow_id"],
            "payload_ref": repo_relative(payload_path),
            "payload_bytes": len(canonical_json_bytes(payload)),
            "created_utc": payload["created_utc"],
        }
        raw_logs["entries"].append(entry)
        write_json_atomic(self.store.raw_log_index_path(self.fabric_id), raw_logs)
        self._prune_raw_logs()
        return entry

    def nominate_run_candidate(
        self,
        *,
        workflow_payload: dict[str, Any],
        execution: dict[str, Any],
        run_ref: str,
        workspace_ref: str,
        raw_log_ref: str,
        selected_cells_override: list[str] | None = None,
    ) -> dict[str, Any]:
        selected_cells = (
            list(selected_cells_override)
            if selected_cells_override is not None and len(selected_cells_override) > 0
            else list(execution.get("result", {}).get("selected_cells", []))
        )
        producer_cell_id = "finance_intake_router" if "finance_intake_router" in selected_cells else (
            selected_cells[0] if selected_cells else "fabric:memory_curator"
        )
        descriptor_kind = "workflow_intake" if producer_cell_id == "finance_intake_router" else "audit_summary"
        workflow_name = str(workflow_payload.get("workflow_name", "document_workflow"))
        document_id = workflow_payload.get("document_id", "unknown")
        task_scope = f"{workflow_name}:{document_id}"
        candidate_payload = {
            "schema_version": "agif.fabric.memory.candidate_payload.v1",
            "workflow_id": execution["workflow_id"],
            "workflow_name": workflow_payload.get("workflow_name"),
            "document_id": workflow_payload.get("document_id"),
            "inputs": workflow_payload.get("inputs", {}),
            "selected_cells": selected_cells,
            "selected_roles": execution.get("result", {}).get("selected_roles", []),
            "input_digest": execution.get("result", {}).get("input_digest"),
            "output_digest": execution.get("output_digest"),
            "source_run_ref": run_ref,
            "source_workspace_ref": workspace_ref,
            "source_log_refs": [raw_log_ref],
        }
        return self.nominate_candidate(
            payload=candidate_payload,
            source_ref=run_ref,
            source_log_refs=[raw_log_ref],
            producer_cell_id=producer_cell_id,
            descriptor_kind=descriptor_kind,
            task_scope=task_scope,
        )

    def nominate_candidate(
        self,
        *,
        payload: dict[str, Any],
        source_ref: str,
        source_log_refs: list[str],
        producer_cell_id: str,
        descriptor_kind: str,
        task_scope: str,
        trust_ref: str = "trust:bounded_local_v1",
    ) -> dict[str, Any]:
        ensure_non_empty_string(source_ref, "candidate.source_ref", code="MEMORY_INVALID")
        candidates = self._load_or_initialize(
            self.store.memory_candidates_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.candidates.v1", "entries": {}},
        )
        candidate_id = self._next_numeric_id("cand", list(candidates["entries"].keys()))
        payload_path = self.store.memory_tier_payload_path(self.fabric_id, "hot", candidate_id)
        write_json_atomic(payload_path, payload)
        review_ready, review_reason = self._validate_candidate_payload(payload)
        assessment = self._assess_candidate_value(
            candidate_payload=payload,
            producer_cell_id=producer_cell_id,
            descriptor_kind=descriptor_kind,
            task_scope=task_scope,
            trust_ref=trust_ref,
            review_ready=review_ready,
        )
        record = {
            "candidate_id": candidate_id,
            "candidate_kind": "memory_candidate",
            "source_ref": source_ref,
            "source_log_refs": list(source_log_refs),
            "producer_cell_id": ensure_non_empty_string(
                producer_cell_id,
                "candidate.producer_cell_id",
                code="MEMORY_INVALID",
            ),
            "descriptor_kind": ensure_non_empty_string(
                descriptor_kind,
                "candidate.descriptor_kind",
                code="MEMORY_INVALID",
            ),
            "task_scope": ensure_non_empty_string(task_scope, "candidate.task_scope", code="MEMORY_INVALID"),
            "memory_key": self._memory_key(producer_cell_id=producer_cell_id, descriptor_kind=descriptor_kind, task_scope=task_scope),
            "payload_ref": repo_relative(payload_path),
            "payload_digest": canonical_json_hash(payload),
            "status": "pending",
            "trust_ref": trust_ref,
            "created_utc": utc_now_iso(),
            "review_ready": review_ready,
            "review_reason": review_reason,
            "memory_class": assessment["memory_class"],
            "value_score": assessment["value_score"],
            "review_scores": assessment["scores"],
            "assessment_reason": assessment["reason"],
        }
        candidates["entries"][candidate_id] = record
        write_json_atomic(self.store.memory_candidates_path(self.fabric_id), candidates)
        self.refresh_hot_memory()
        return deepcopy(record)

    def review_candidate(
        self,
        *,
        candidate_id: str,
        reviewer_id: str,
        decision: str,
        compression_mode: str | None = None,
        retention_tier: str | None = None,
        reason: str,
        lifecycle_manager: Any | None = None,
        authority_engine: Any | None = None,
    ) -> dict[str, Any]:
        normalized_decision = ensure_non_empty_string(decision, "MemoryPromotionDecision.decision", code="MEMORY_INVALID")
        if normalized_decision not in ALLOWED_DECISIONS:
            raise FabricError("MEMORY_INVALID", f"Unsupported memory review decision: {normalized_decision}.")
        candidates = self._load_or_initialize(
            self.store.memory_candidates_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.candidates.v1", "entries": {}},
        )
        candidate = deepcopy(candidates["entries"].get(candidate_id))
        if candidate is None:
            raise FabricError("MEMORY_NOT_FOUND", f"Unknown memory candidate: {candidate_id}.")

        chosen_tier = retention_tier or ("hot" if normalized_decision in {"reject", "defer"} else "warm")
        chosen_mode = compression_mode or self._default_compression_mode(normalized_decision, chosen_tier)
        authority_review = None
        if authority_engine is not None and normalized_decision in {"promote", "compress"}:
            authority_review = authority_engine.evaluate_action(
                action="memory_runtime_influence",
                proposer=reviewer_id,
                need_signal=None,
                utility_evaluation={
                    "utility_score": float(candidate.get("value_score", 0.0)),
                    "threshold": 0.55 if str(candidate.get("memory_class")) == "routing_useful_memory" else 0.38,
                },
                policy_envelope={
                    "allowed_actions": ["route"] if str(candidate.get("memory_class")) == "routing_useful_memory" else ["summarize"],
                    "human_boundary": self.config.get("governance_policy", {}).get("human_boundary", "document/workflow intelligence"),
                },
                trust_state={
                    "trust_ref": candidate.get("trust_ref"),
                    "trust_score": float(candidate.get("review_scores", {}).get("trust_score", self._trust_score(str(candidate.get("trust_ref", ""))))),
                },
                rollback_ref=f"memory:review:{candidate_id}",
                related_cells=[str(candidate.get("producer_cell_id"))],
                metadata={
                    "decision": normalized_decision,
                    "memory_class": candidate.get("memory_class"),
                    "candidate_id": candidate_id,
                },
            )
            if not authority_review["approved"]:
                normalized_decision = "defer"
                chosen_tier = "hot"
                chosen_mode = "review_buffer_v1"
                reason = f"{reason}; authority kept runtime influence provisional"
        decision_record = self._build_decision(
            candidate_id=candidate_id,
            reviewer_id=reviewer_id,
            decision=normalized_decision,
            compression_mode=chosen_mode,
            retention_tier=chosen_tier,
            reason=reason,
        )
        replay_snapshot = {
            "candidate": deepcopy(candidate),
            "before_digest": self._active_state_digest(),
        }

        result: dict[str, Any]
        if normalized_decision == "reject":
            candidate["status"] = "rejected"
            self._clear_candidate_payload(candidate)
            self._record_lifecycle_memory_outcome(
                lifecycle_manager=lifecycle_manager,
                candidate=candidate,
                outcome_kind="reject",
                detail=str(reason),
            )
            result = {"candidate_id": candidate_id}
        elif normalized_decision == "defer":
            candidate["status"] = "deferred"
            self._record_lifecycle_memory_outcome(
                lifecycle_manager=lifecycle_manager,
                candidate=candidate,
                outcome_kind="defer",
                detail=str(reason),
            )
            result = {"candidate_id": candidate_id}
        elif normalized_decision in {"promote", "compress"}:
            if normalized_decision == "compress" and chosen_tier == "cold":
                self._record_memory_pressure_signal(
                    lifecycle_manager=lifecycle_manager,
                    severity=1.0,
                    status="resolved",
                    resolution_ref=f"memory:direct-cold-compression:{candidate_id}",
                )
            result = self._promote_candidate(
                candidate=candidate,
                decision=decision_record,
                lifecycle_manager=lifecycle_manager,
            )
            candidate["status"] = "compressed" if normalized_decision == "compress" else "promoted"
            candidate["result_memory_id"] = result.get("memory_id")
            candidate["result_descriptor_id"] = result.get("descriptor_id")
            self._clear_candidate_payload(candidate)
        else:
            candidate["status"] = "retired"
            self._clear_candidate_payload(candidate)
            result = {"candidate_id": candidate_id}

        candidates["entries"][candidate_id] = candidate
        write_json_atomic(self.store.memory_candidates_path(self.fabric_id), candidates)
        decision_ref = self._append_decision(decision_record)
        after_digest = self._active_state_digest()
        self._append_replay_entry(
            {
                "decision": decision_record,
                "decision_ref": decision_ref,
                "candidate_snapshot": replay_snapshot["candidate"],
                "before_digest": replay_snapshot["before_digest"],
                "after_digest": after_digest,
                "result_memory_id": result.get("memory_id"),
                "result_descriptor_id": result.get("descriptor_id"),
                "created_utc": decision_record["created_utc"],
            }
        )
        if authority_engine is not None and authority_review is not None:
            authority_engine.finalize_review(authority_review["review_id"], action_ref=decision_ref, rollback_ref=decision_ref)
        self.refresh_hot_memory()
        return {
            "candidate_id": candidate_id,
            "decision": normalized_decision,
            "decision_ref": decision_ref,
            "memory_id": result.get("memory_id"),
            "descriptor_id": result.get("descriptor_id"),
        }

    def retire_memory(
        self,
        *,
        memory_id: str,
        reviewer_id: str,
        reason: str,
    ) -> dict[str, Any]:
        promoted = self._load_or_initialize(
            self.store.promoted_memory_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.promoted.v1", "active": {}, "archived": {}},
        )
        memory_record = deepcopy(promoted["active"].get(memory_id))
        if memory_record is None:
            raise FabricError("MEMORY_NOT_FOUND", f"Unknown promoted memory: {memory_id}.")
        decision_record = self._build_decision(
            candidate_id=memory_id,
            reviewer_id=reviewer_id,
            decision="retire",
            compression_mode="retire_review_v1",
            retention_tier=str(memory_record["retention_tier"]),
            reason=reason,
        )
        before_digest = self._active_state_digest()
        self._archive_memory(memory_id=memory_id, archived_reason=reason)
        decision_ref = self._append_decision(decision_record)
        after_digest = self._active_state_digest()
        self._append_replay_entry(
            {
                "decision": decision_record,
                "decision_ref": decision_ref,
                "candidate_snapshot": memory_record,
                "before_digest": before_digest,
                "after_digest": after_digest,
                "result_memory_id": memory_id,
                "result_descriptor_id": memory_record["descriptor_id"],
                "created_utc": decision_record["created_utc"],
            }
        )
        self.refresh_hot_memory()
        return {
            "memory_id": memory_id,
            "descriptor_id": memory_record["descriptor_id"],
            "decision_ref": decision_ref,
        }

    def consolidate_if_needed(
        self,
        *,
        lifecycle_manager: Any | None = None,
        reason: str,
    ) -> dict[str, Any]:
        summary = self.summary()
        warm_ratio = summary["tier_usage_bytes"]["warm"] / float(self.memory_caps["warm_bytes"])
        cold_ratio = summary["tier_usage_bytes"]["cold"] / float(self.memory_caps["cold_bytes"])
        raw_ratio = summary["tier_usage_bytes"]["ephemeral"] / float(self.memory_caps["raw_log_bytes"])
        peak_ratio = max(warm_ratio, cold_ratio, raw_ratio)
        if peak_ratio <= 1.0:
            return {"triggered": False, "compressed_memory_ids": [], "retired_memory_ids": []}

        self._record_memory_pressure_signal(
            lifecycle_manager=lifecycle_manager,
            severity=min(1.0, round(peak_ratio, 3)),
            status="open",
            resolution_ref=None,
        )

        compressed_memory_ids: list[str] = []
        retired_memory_ids: list[str] = []
        while self.summary()["tier_usage_bytes"]["warm"] > self.memory_caps["warm_bytes"]:
            target = self._select_pressure_target(tier="warm", allow_high_trust=False)
            if target is None:
                break
            self._compress_existing_memory(
                memory_id=target["memory_id"],
                reviewer_id=self.default_reviewer_id,
                reason="memory pressure compressed low-value warm memory into colder storage",
                target_tier="cold",
                compression_mode="quantized_cold_v1",
            )
            compressed_memory_ids.append(target["memory_id"])

        self.garbage_collect(reason="memory_pressure_cleanup", lifecycle_manager=lifecycle_manager)
        while self.summary()["tier_usage_bytes"]["cold"] > self.memory_caps["cold_bytes"]:
            target = self._select_pressure_target(tier="cold", allow_high_trust=False)
            if target is None:
                break
            self.retire_memory(
                memory_id=target["memory_id"],
                reviewer_id=self.default_reviewer_id,
                reason="low_value_stale_cold_retirement",
            )
            retired_memory_ids.append(target["memory_id"])
            self.garbage_collect(reason="post_retire_cold_gc", lifecycle_manager=lifecycle_manager)

        self._record_memory_pressure_signal(
            lifecycle_manager=lifecycle_manager,
            severity=min(1.0, round(peak_ratio, 3)),
            status="resolved",
            resolution_ref=f"memory:consolidated:{utc_now_iso()}",
        )
        self.refresh_hot_memory()
        return {
            "triggered": True,
            "compressed_memory_ids": compressed_memory_ids,
            "retired_memory_ids": retired_memory_ids,
        }

    def garbage_collect(
        self,
        *,
        reason: str,
        lifecycle_manager: Any | None = None,
    ) -> dict[str, Any]:
        del lifecycle_manager
        promoted = self._load_or_initialize(
            self.store.promoted_memory_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.promoted.v1", "active": {}, "archived": {}},
        )
        descriptors = self._load_or_initialize(
            self.store.descriptor_store_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.descriptors.v1", "active": {}, "archived": {}},
        )
        protected_payload_refs = set()
        for record in promoted["active"].values():
            protected_payload_refs.add(str(record["payload_ref"]))
        for record in descriptors["active"].values():
            protected_payload_refs.add(str(record["payload_ref"]))

        removed_payloads: list[str] = []
        for memory_id, archived in list(promoted["archived"].items()):
            payload_ref = archived.get("payload_ref")
            if not isinstance(payload_ref, str) or payload_ref in protected_payload_refs:
                continue
            payload_path = self._resolve_repo_ref(payload_ref)
            if payload_path.exists():
                payload_path.unlink()
            archived["retired_payload_ref"] = payload_ref
            archived["payload_ref"] = None
            archived["payload_retired_utc"] = utc_now_iso()
            promoted["archived"][memory_id] = archived
            removed_payloads.append(payload_ref)
        write_json_atomic(self.store.promoted_memory_path(self.fabric_id), promoted)

        removed_raw_logs = self._prune_raw_logs()
        replay_store = self._load_or_initialize(
            self.store.memory_replay_store_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.replay_store.v1", "entries": []},
        )
        if len(replay_store["entries"]) > self.memory_caps["replay_entries"]:
            replay_store["entries"] = replay_store["entries"][-self.memory_caps["replay_entries"] :]
            write_json_atomic(self.store.memory_replay_store_path(self.fabric_id), replay_store)

        gc_log = self._load_or_initialize(
            self.store.memory_gc_log_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.gc_log.v1", "entries": []},
        )
        gc_log["entries"].append(
            {
                "created_utc": utc_now_iso(),
                "reason": reason,
                "removed_payload_refs": removed_payloads,
                "removed_raw_logs": removed_raw_logs,
            }
        )
        gc_log["entries"] = gc_log["entries"][-self.memory_caps["replay_entries"] :]
        write_json_atomic(self.store.memory_gc_log_path(self.fabric_id), gc_log)
        self.refresh_hot_memory()
        return {
            "removed_payload_count": len(removed_payloads),
            "removed_raw_log_count": len(removed_raw_logs),
            "removed_payload_refs": removed_payloads,
        }

    def refresh_hot_memory(self) -> dict[str, Any]:
        candidates = self.load_candidates()
        runtime_states = self._load_or_initialize(
            self.store.runtime_states_path(self.fabric_id),
            {"schema_version": "agif.fabric.runtime_states.v1", "states": {}},
        )
        current_task_refs = sorted(
            {
                str(record["active_task_ref"])
                for record in runtime_states["states"].values()
                if record.get("active_task_ref")
            }
        )
        workspace_refs = []
        for task_ref in current_task_refs:
            workspace_path = self.store.workspace_path(self.fabric_id, task_ref)
            if workspace_path.exists():
                workspace_refs.append(repo_relative(workspace_path))

        payload = {
            "schema_version": "agif.fabric.memory.hot_index.v1",
            "workspace_refs": workspace_refs,
            "current_task_refs": current_task_refs,
            "live_runtime_state_ref": repo_relative(self.store.runtime_states_path(self.fabric_id)),
            "review_buffer_candidate_ids": sorted(
                candidate_id
                for candidate_id, record in candidates.items()
                if record.get("status") in {"pending", "deferred"} and record.get("payload_ref")
            ),
            "updated_utc": utc_now_iso(),
        }
        write_json_atomic(self.store.hot_memory_index_path(self.fabric_id), payload)
        return payload

    def load_raw_logs(self) -> list[dict[str, Any]]:
        raw_logs = self._load_or_initialize(
            self.store.raw_log_index_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.raw_logs.v1", "entries": []},
        )
        return [deepcopy(item) for item in raw_logs["entries"]]

    def load_candidates(self) -> dict[str, dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.memory_candidates_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.candidates.v1", "entries": {}},
        )
        return {key: deepcopy(value) for key, value in payload["entries"].items()}

    def load_decisions(self) -> list[dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.memory_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.decisions.v1", "entries": []},
        )
        return [deepcopy(item) for item in payload["entries"]]

    def load_descriptors(self) -> dict[str, Any]:
        return self._load_or_initialize(
            self.store.descriptor_store_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.descriptors.v1", "active": {}, "archived": {}},
        )

    def load_promoted_memories(self) -> dict[str, Any]:
        return self._load_or_initialize(
            self.store.promoted_memory_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.promoted.v1", "active": {}, "archived": {}},
        )

    def record_descriptor_reuse(self, *, memory_ids: list[str]) -> None:
        promoted = self.load_promoted_memories()
        changed = False
        for memory_id in memory_ids:
            record = promoted["active"].get(memory_id)
            if record is None:
                continue
            record["reuse_count"] = int(record.get("reuse_count", 0)) + 1
            record["usefulness_hits"] = int(record.get("usefulness_hits", 0)) + 1
            changed = True
        if changed:
            write_json_atomic(self.store.promoted_memory_path(self.fabric_id), promoted)

    def replay_decisions(self) -> dict[str, Any]:
        replay_store = self._load_or_initialize(
            self.store.memory_replay_store_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.replay_store.v1", "entries": []},
        )
        entries = replay_store["entries"]
        last_after_digest = entries[-1]["after_digest"] if entries else self._active_state_digest()
        current_digest = self._active_state_digest()
        traceable = True
        for entry in entries:
            try:
                self._validate_decision(entry["decision"])
            except FabricError:
                traceable = False
                break
        return {
            "entry_count": len(entries),
            "bounded": len(entries) <= self.memory_caps["replay_entries"],
            "traceable": traceable,
            "replay_match": traceable and last_after_digest == current_digest,
            "last_after_digest": last_after_digest,
            "current_digest": current_digest,
        }

    def summary(self) -> dict[str, Any]:
        hot_index = self._load_or_initialize(
            self.store.hot_memory_index_path(self.fabric_id),
            {
                "schema_version": "agif.fabric.memory.hot_index.v1",
                "workspace_refs": [],
                "current_task_refs": [],
                "live_runtime_state_ref": repo_relative(self.store.runtime_states_path(self.fabric_id)),
                "review_buffer_candidate_ids": [],
                "updated_utc": utc_now_iso(),
            },
        )
        descriptors = self.load_descriptors()
        promoted = self.load_promoted_memories()
        raw_logs = self.load_raw_logs()
        replay = self.replay_decisions()
        tier_usage_bytes = {
            "hot": self._tier_usage_bytes("hot") + len(canonical_json_bytes(hot_index)),
            "warm": self._tier_usage_bytes("warm"),
            "cold": self._tier_usage_bytes("cold"),
            "ephemeral": sum(int(item.get("payload_bytes", 0)) for item in raw_logs),
        }
        cold_reference_integrity = True
        for descriptor in descriptors["active"].values():
            if descriptor["storage_tier"] == "cold":
                payload_path = self._resolve_repo_ref(descriptor["payload_ref"])
                if not payload_path.exists():
                    cold_reference_integrity = False
                    break
        raw_log_refs = {item["payload_ref"] for item in raw_logs}
        promoted_payload_refs = {
            str(record["payload_ref"])
            for record in promoted["active"].values()
            if isinstance(record.get("payload_ref"), str)
        }
        decisions = self.load_decisions()
        active_records = list(promoted["active"].values())
        archived_records = list(promoted["archived"].values())
        total_review_actions = len([item for item in decisions if item["decision"] in {"reject", "defer", "promote", "compress"}])
        promoted_count = len([item for item in decisions if item["decision"] == "promote"])
        deferred_count = len([item for item in decisions if item["decision"] == "defer"])
        rejected_count = len([item for item in decisions if item["decision"] == "reject"])
        duplicate_reuse_events = sum(int(record.get("reuse_count", 0)) for record in active_records + archived_records)
        duplicate_gain_bytes = sum(
            int(record.get("duplicate_compression_gain_bytes", 0))
            for record in active_records + archived_records
        )
        supersession_count = len(
            [
                record
                for record in active_records + archived_records
                if record.get("supersedes_memory_id") is not None
            ]
        )
        stale_retirement_count = len(
            [
                item
                for item in decisions
                if item["decision"] == "retire" and str(item["reason"]) == "low_value_stale_cold_retirement"
            ]
        )
        class_counts = {
            name: len([record for record in active_records if record.get("memory_class") == name])
            for name in sorted(MEMORY_CLASS_NAMES)
        }
        pressure_priority = {
            str(record["memory_id"]): round(self._retention_priority(record), 6)
            for record in active_records
        }
        needs = self._load_optional_need_signals()
        return {
            "tier_usage_bytes": tier_usage_bytes,
            "tier_caps_bytes": {
                "hot": self.memory_caps["hot_bytes"],
                "warm": self.memory_caps["warm_bytes"],
                "cold": self.memory_caps["cold_bytes"],
                "ephemeral": self.memory_caps["raw_log_bytes"],
            },
            "within_caps": {
                "hot": tier_usage_bytes["hot"] <= self.memory_caps["hot_bytes"],
                "warm": tier_usage_bytes["warm"] <= self.memory_caps["warm_bytes"],
                "cold": tier_usage_bytes["cold"] <= self.memory_caps["cold_bytes"],
                "ephemeral": tier_usage_bytes["ephemeral"] <= self.memory_caps["raw_log_bytes"],
            },
            "active_descriptor_count": len(descriptors["active"]),
            "archived_descriptor_count": len(descriptors["archived"]),
            "active_promoted_count": len(promoted["active"]),
            "archived_promoted_count": len(promoted["archived"]),
            "raw_log_count": len(raw_logs),
            "pending_review_count": len(
                [item for item in self.load_candidates().values() if item.get("status") in {"pending", "deferred"}]
            ),
            "memory_pressure_signal_count": len([item for item in needs if item.get("signal_kind") == "memory_pressure"]),
            "cold_reference_integrity": cold_reference_integrity,
            "raw_log_promoted_count": len(raw_log_refs & promoted_payload_refs),
            "bounded_replay_store": replay["bounded"],
            "memory_class_counts": class_counts,
            "review_metrics": {
                "promotion_rate": 0.0 if total_review_actions == 0 else round(promoted_count / float(total_review_actions), 6),
                "defer_rate": 0.0 if total_review_actions == 0 else round(deferred_count / float(total_review_actions), 6),
                "reject_rate": 0.0 if total_review_actions == 0 else round(rejected_count / float(total_review_actions), 6),
                "reuse_rate": 0.0
                if (len(active_records) + len(archived_records)) == 0
                else round(duplicate_reuse_events / float(len(active_records) + len(archived_records)), 6),
                "supersession_rate": 0.0
                if max(1, promoted_count) == 0
                else round(supersession_count / float(max(1, promoted_count)), 6),
                "duplicate_compression_gain_bytes": duplicate_gain_bytes,
                "stale_retirement_rate": 0.0
                if len([item for item in decisions if item["decision"] == "retire"]) == 0
                else round(
                    stale_retirement_count
                    / float(len([item for item in decisions if item["decision"] == "retire"])),
                    6,
                ),
            },
            "retention_priorities": pressure_priority,
            "state_digest": self._active_state_digest(),
        }

    def _promote_candidate(
        self,
        *,
        candidate: dict[str, Any],
        decision: dict[str, Any],
        lifecycle_manager: Any | None = None,
    ) -> dict[str, Any]:
        candidate_payload = self._load_payload_ref(candidate.get("payload_ref"), code="MEMORY_INVALID")
        if decision["decision"] == "promote" and not bool(candidate.get("review_ready")):
            raise FabricError("MEMORY_INVALID", "A candidate that failed review readiness cannot be promoted.")

        target_payload = self._build_promoted_payload(
            candidate=candidate,
            candidate_payload=candidate_payload,
            retention_tier=decision["retention_tier"],
            compression_mode=decision["compression_mode"],
        )
        payload_digest = canonical_json_hash(target_payload)
        payload_bytes = len(canonical_json_bytes(target_payload))
        projected_usage = self._tier_usage_bytes(decision["retention_tier"]) + payload_bytes
        if projected_usage > self.memory_caps[f"{decision['retention_tier']}_bytes"]:
            self._record_memory_pressure_signal(
                lifecycle_manager=lifecycle_manager,
                severity=min(
                    1.0,
                    round(projected_usage / float(self.memory_caps[f"{decision['retention_tier']}_bytes"]), 3),
                ),
                status="open",
                resolution_ref=None,
            )

        descriptors = self.load_descriptors()
        promoted = self.load_promoted_memories()
        active_memory = self._find_active_memory_by_key(promoted["active"], candidate["memory_key"])
        if active_memory is not None:
            active_payload = self._load_payload_ref(active_memory["payload_ref"], code="MEMORY_INVALID")
            if active_memory["payload_digest"] == payload_digest or (
                self._payload_semantic_digest(active_payload) == self._payload_semantic_digest(target_payload)
            ):
                active_memory["last_reviewed_utc"] = utc_now_iso()
                active_memory["review_count"] = int(active_memory.get("review_count", 0)) + 1
                active_memory["reuse_count"] = int(active_memory.get("reuse_count", 0)) + 1
                active_memory["usefulness_hits"] = int(active_memory.get("usefulness_hits", 0)) + 1
                active_memory["last_reused_utc"] = utc_now_iso()
                active_memory["duplicate_compression_gain_bytes"] = int(active_memory.get("duplicate_compression_gain_bytes", 0)) + len(
                    canonical_json_bytes(candidate_payload)
                )
                promoted["active"][active_memory["memory_id"]] = active_memory
                write_json_atomic(self.store.promoted_memory_path(self.fabric_id), promoted)
                self._record_lifecycle_memory_outcome(
                    lifecycle_manager=lifecycle_manager,
                    candidate=candidate,
                    outcome_kind="reuse",
                    detail="duplicate reviewed memory reused existing promoted artifact",
                )
                return {
                    "memory_id": active_memory["memory_id"],
                    "descriptor_id": active_memory["descriptor_id"],
                }

        superseded_descriptor_id = None
        superseded_memory_id = None
        supersession_delta = None
        if active_memory is not None:
            superseded_descriptor_id = active_memory["descriptor_id"]
            superseded_memory_id = active_memory["memory_id"]
            prior_payload = self._load_payload_ref(active_memory["payload_ref"], code="MEMORY_INVALID")
            supersession_delta = self._build_supersession_delta(prior_payload=prior_payload, next_payload=target_payload)
            self._archive_memory(
                memory_id=active_memory["memory_id"],
                archived_reason="superseded by reviewed promoted memory",
            )
            descriptors = self.load_descriptors()
            promoted = self.load_promoted_memories()

        descriptor_id = self._next_numeric_id("desc", list(descriptors["active"].keys()) + list(descriptors["archived"].keys()))
        memory_id = self._next_numeric_id("mem", list(promoted["active"].keys()) + list(promoted["archived"].keys()))
        payload_path = self.store.memory_tier_payload_path(self.fabric_id, decision["retention_tier"], memory_id)
        write_json_atomic(payload_path, target_payload)
        descriptor = self._build_descriptor(
            descriptor_id=descriptor_id,
            candidate=candidate,
            payload_ref=repo_relative(payload_path),
            retention_tier=decision["retention_tier"],
            supersedes_descriptor_id=superseded_descriptor_id,
        )
        promoted_record = {
            "memory_id": memory_id,
            "candidate_id": candidate["candidate_id"],
            "descriptor_id": descriptor_id,
            "producer_cell_id": candidate["producer_cell_id"],
            "descriptor_kind": candidate["descriptor_kind"],
            "task_scope": candidate["task_scope"],
            "memory_key": candidate["memory_key"],
            "payload_ref": repo_relative(payload_path),
            "payload_digest": payload_digest,
            "payload_bytes": payload_bytes,
            "retention_tier": decision["retention_tier"],
            "compression_mode": decision["compression_mode"],
            "trust_ref": candidate["trust_ref"],
            "trust_score": self._trust_score(candidate["trust_ref"]),
            "memory_class": candidate.get("memory_class"),
            "value_score": float(candidate.get("value_score", 0.0)),
            "review_scores": deepcopy(candidate.get("review_scores", {})),
            "created_utc": utc_now_iso(),
            "source_ref": candidate["source_ref"],
            "source_log_refs": list(candidate["source_log_refs"]),
            "supersedes_memory_id": superseded_memory_id,
            "supersession_delta": supersession_delta,
            "review_count": 1,
            "reuse_count": 0,
            "usefulness_hits": 0,
            "duplicate_compression_gain_bytes": 0,
        }
        descriptors["active"][descriptor_id] = descriptor
        promoted["active"][memory_id] = promoted_record
        write_json_atomic(self.store.descriptor_store_path(self.fabric_id), descriptors)
        write_json_atomic(self.store.promoted_memory_path(self.fabric_id), promoted)
        self._record_lifecycle_memory_outcome(
            lifecycle_manager=lifecycle_manager,
            candidate=candidate,
            outcome_kind="promote",
            detail=str(decision["reason"]),
        )
        return {"memory_id": memory_id, "descriptor_id": descriptor_id}

    def _compress_existing_memory(
        self,
        *,
        memory_id: str,
        reviewer_id: str,
        reason: str,
        target_tier: str,
        compression_mode: str,
    ) -> dict[str, Any]:
        promoted = self.load_promoted_memories()
        descriptors = self.load_descriptors()
        memory_record = deepcopy(promoted["active"].get(memory_id))
        if memory_record is None:
            raise FabricError("MEMORY_NOT_FOUND", f"Unknown promoted memory: {memory_id}.")
        descriptor = deepcopy(descriptors["active"].get(memory_record["descriptor_id"]))
        if descriptor is None:
            raise FabricError("MEMORY_INVALID", f"Promoted memory {memory_id} is missing its active descriptor.")

        current_payload = self._load_payload_ref(memory_record["payload_ref"], code="MEMORY_INVALID")
        compressed_payload = self._compress_payload_for_tier(
            payload=current_payload,
            retention_tier=target_tier,
        )
        new_digest = canonical_json_hash(compressed_payload)
        new_path = self.store.memory_tier_payload_path(self.fabric_id, target_tier, memory_id)
        old_path = self._resolve_repo_ref(memory_record["payload_ref"])
        decision_record = self._build_decision(
            candidate_id=memory_id,
            reviewer_id=reviewer_id,
            decision="compress",
            compression_mode=compression_mode,
            retention_tier=target_tier,
            reason=reason,
        )
        before_digest = self._active_state_digest()
        write_json_atomic(new_path, compressed_payload)
        if old_path.exists() and old_path.resolve() != new_path.resolve():
            old_path.unlink()
        memory_record["payload_ref"] = repo_relative(new_path)
        memory_record["payload_digest"] = new_digest
        memory_record["payload_bytes"] = len(canonical_json_bytes(compressed_payload))
        memory_record["retention_tier"] = target_tier
        memory_record["compression_mode"] = compression_mode
        memory_record["review_count"] = int(memory_record.get("review_count", 0)) + 1
        promoted["active"][memory_id] = memory_record

        descriptor["payload_ref"] = repo_relative(new_path)
        descriptor["storage_tier"] = target_tier
        descriptors["active"][descriptor["descriptor_id"]] = descriptor
        write_json_atomic(self.store.promoted_memory_path(self.fabric_id), promoted)
        write_json_atomic(self.store.descriptor_store_path(self.fabric_id), descriptors)

        decision_ref = self._append_decision(decision_record)
        after_digest = self._active_state_digest()
        self._append_replay_entry(
            {
                "decision": decision_record,
                "decision_ref": decision_ref,
                "candidate_snapshot": memory_record,
                "before_digest": before_digest,
                "after_digest": after_digest,
                "result_memory_id": memory_id,
                "result_descriptor_id": descriptor["descriptor_id"],
                "created_utc": decision_record["created_utc"],
            }
        )
        return {"memory_id": memory_id, "descriptor_id": descriptor["descriptor_id"]}

    def _archive_memory(self, *, memory_id: str, archived_reason: str) -> None:
        promoted = self.load_promoted_memories()
        descriptors = self.load_descriptors()
        memory_record = promoted["active"].pop(memory_id, None)
        if memory_record is None:
            raise FabricError("MEMORY_NOT_FOUND", f"Unknown promoted memory: {memory_id}.")
        descriptor_record = descriptors["active"].pop(memory_record["descriptor_id"], None)
        if descriptor_record is None:
            raise FabricError("MEMORY_INVALID", f"Descriptor missing for memory: {memory_id}.")
        promoted["archived"][memory_id] = {
            **memory_record,
            "archived_utc": utc_now_iso(),
            "archived_reason": archived_reason,
        }
        descriptors["archived"][descriptor_record["descriptor_id"]] = {
            "record": descriptor_record,
            "archived_utc": utc_now_iso(),
            "archived_reason": archived_reason,
        }
        write_json_atomic(self.store.promoted_memory_path(self.fabric_id), promoted)
        write_json_atomic(self.store.descriptor_store_path(self.fabric_id), descriptors)

    def _build_promoted_payload(
        self,
        *,
        candidate: dict[str, Any],
        candidate_payload: dict[str, Any],
        retention_tier: str,
        compression_mode: str,
    ) -> dict[str, Any]:
        inputs = candidate_payload.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}
        base = {
            "schema_version": "agif.fabric.memory.quantized_summary.v1",
            "task_scope": candidate["task_scope"],
            "workflow_id": candidate_payload.get("workflow_id"),
            "workflow_name": candidate_payload.get("workflow_name"),
            "document_id": candidate_payload.get("document_id"),
            "producer_cell_id": candidate["producer_cell_id"],
            "descriptor_kind": candidate["descriptor_kind"],
            "memory_class": candidate.get("memory_class"),
            "summary_vector": [
                self._quantize_text(inputs.get("vendor_name"), limit=18),
                self._quantize_text(inputs.get("document_type"), limit=12),
                self._quantize_text(inputs.get("currency"), limit=8),
                self._quantize_total(inputs.get("total")),
            ],
            "reuse_hints": {
                "vendor_token": self._quantize_text(inputs.get("vendor_name"), limit=8),
                "document_type": self._quantize_text(inputs.get("document_type"), limit=8),
                "routing_hint": "router" if any("router" in str(item) for item in candidate_payload.get("selected_cells", [])) else "local",
            },
            "source_run_ref": candidate_payload.get("source_run_ref"),
            "compression_mode": compression_mode,
            "retention_tier": retention_tier,
        }
        return self._compress_payload_for_tier(payload=base, retention_tier=retention_tier)

    def _compress_payload_for_tier(self, *, payload: dict[str, Any], retention_tier: str) -> dict[str, Any]:
        if retention_tier == "cold":
            return {
                "schema_version": "agif.fabric.memory.quantized_cold.v1",
                "task_scope": payload.get("task_scope"),
                "document_id": payload.get("document_id"),
                "workflow_name": payload.get("workflow_name"),
                "descriptor_kind": payload.get("descriptor_kind"),
                "memory_class": payload.get("memory_class"),
                "summary_vector": list(payload.get("summary_vector", []))[:4],
                "prototype_hint": (payload.get("reuse_hints") or {}).get("document_type"),
                "source_run_ref": payload.get("source_run_ref"),
                "compression_mode": payload.get("compression_mode"),
            }
        return dict(payload)

    def _build_descriptor(
        self,
        *,
        descriptor_id: str,
        candidate: dict[str, Any],
        payload_ref: str,
        retention_tier: str,
        supersedes_descriptor_id: str | None,
    ) -> dict[str, Any]:
        descriptor = {
            "descriptor_id": descriptor_id,
            "producer_cell_id": candidate["producer_cell_id"],
            "descriptor_kind": candidate["descriptor_kind"],
            "task_scope": candidate["task_scope"],
            "cost_score": 0.2 if retention_tier == "warm" else 0.1,
            "confidence_score": 0.8 if candidate["review_ready"] else 0.3,
            "payload_ref": payload_ref,
            "storage_tier": retention_tier,
            "retention_policy": "phase5_reviewed_memory_v1",
            "trust_ref": candidate["trust_ref"],
            "created_utc": utc_now_iso(),
            "supersedes_descriptor_id": supersedes_descriptor_id,
        }
        self._validate_descriptor(descriptor)
        return descriptor

    def _default_review_decision(self, candidate_id: str) -> dict[str, str]:
        candidates = self.load_candidates()
        candidate = candidates.get(candidate_id)
        if candidate is None:
            raise FabricError("MEMORY_NOT_FOUND", f"Unknown memory candidate: {candidate_id}.")
        if not bool(candidate.get("review_ready")):
            return {
                "decision": "reject",
                "compression_mode": "review_reject_v1",
                "retention_tier": "hot",
                "reason": str(candidate.get("review_reason", "candidate failed reviewed memory checks")),
            }
        payload = self._load_payload_ref(candidate["payload_ref"], code="MEMORY_INVALID")
        warm_payload = self._build_promoted_payload(
            candidate=candidate,
            candidate_payload=payload,
            retention_tier="warm",
            compression_mode="quantized_summary_v1",
        )
        review_scores = dict(candidate.get("review_scores") or {})
        value_score = float(candidate.get("value_score", 0.0))
        promoted = self.load_promoted_memories()
        active_memory = self._find_active_memory_by_key(promoted["active"], candidate["memory_key"])
        if active_memory is not None and active_memory["payload_digest"] == canonical_json_hash(warm_payload):
            return {
                "decision": "compress",
                "compression_mode": "quantized_dedup_v1",
                "retention_tier": str(active_memory["retention_tier"]),
                "reason": "duplicate candidate consolidated into existing reviewed memory",
            }
        if active_memory is not None:
            existing_trust = float(active_memory.get("trust_score", self._trust_score(str(active_memory.get("trust_ref", "")))))
            existing_value = float(active_memory.get("value_score", 0.0))
            candidate_trust = float(review_scores.get("trust_score", 0.0))
            if existing_trust > candidate_trust and value_score <= existing_value + 0.12:
                return {
                    "decision": "defer" if value_score >= 0.45 else "reject",
                    "compression_mode": "review_buffer_v1" if value_score >= 0.45 else "review_reject_v1",
                    "retention_tier": "hot",
                    "reason": "conflicting candidate could override a higher-trust reviewed memory",
                }
            if float(review_scores.get("conflict_risk", 0.0)) >= 0.65 and (
                value_score >= 0.65 and candidate_trust >= existing_trust
            ):
                if self._tier_usage_bytes("warm") + len(canonical_json_bytes(warm_payload)) > self.memory_caps["warm_bytes"]:
                    return {
                        "decision": "compress",
                        "compression_mode": "quantized_cold_v1",
                        "retention_tier": "cold",
                        "reason": "high-value conflicting candidate superseded existing memory under warm pressure",
                    }
                return {
                    "decision": "promote",
                    "compression_mode": "quantized_summary_v1",
                    "retention_tier": "warm",
                    "reason": "high-value conflicting candidate superseded an older memory with equal trust",
                }
        if value_score < 0.38:
            return {
                "decision": "reject",
                "compression_mode": "review_reject_v1",
                "retention_tier": "hot",
                "reason": "candidate value score is too low for durable reviewed memory",
            }
        if value_score < 0.6 or float(review_scores.get("conflict_risk", 0.0)) >= 0.65:
            return {
                "decision": "defer",
                "compression_mode": "review_buffer_v1",
                "retention_tier": "hot",
                "reason": "candidate needs more evidence because value is provisional or conflict risk is elevated",
            }

        projected_warm = self._tier_usage_bytes("warm") + len(canonical_json_bytes(warm_payload))
        if projected_warm > self.memory_caps["warm_bytes"]:
            return {
                "decision": "compress",
                "compression_mode": "quantized_cold_v1",
                "retention_tier": "cold",
                "reason": "memory pressure preserved a high-value candidate by promoting it directly into cold compressed storage",
            }
        return {
            "decision": "promote",
            "compression_mode": "quantized_summary_v1",
            "retention_tier": "warm",
            "reason": "reviewed candidate cleared novelty, usefulness, trust, and reuse scoring for warm retention",
        }

    def _validate_candidate_payload(self, payload: dict[str, Any]) -> tuple[bool, str]:
        workflow_name = payload.get("workflow_name")
        document_id = payload.get("document_id")
        inputs = payload.get("inputs")
        selected_cells = payload.get("selected_cells")
        if not isinstance(workflow_name, str) or workflow_name.strip() == "":
            return False, "candidate is missing workflow_name"
        if not isinstance(document_id, str) or document_id.strip() == "":
            return False, "candidate is missing document_id"
        if not isinstance(inputs, dict) or len(inputs) == 0:
            return False, "candidate is missing structured inputs"
        if not isinstance(selected_cells, list) or len(selected_cells) == 0:
            return False, "candidate is missing selected cell context"
        return True, "candidate passed reviewed memory readiness"

    def _assess_candidate_value(
        self,
        *,
        candidate_payload: dict[str, Any],
        producer_cell_id: str,
        descriptor_kind: str,
        task_scope: str,
        trust_ref: str,
        review_ready: bool,
    ) -> dict[str, Any]:
        inputs = candidate_payload.get("inputs")
        if not isinstance(inputs, dict):
            inputs = {}
        selected_cells = candidate_payload.get("selected_cells")
        if not isinstance(selected_cells, list):
            selected_cells = []
        memory_key = self._memory_key(
            producer_cell_id=producer_cell_id,
            descriptor_kind=descriptor_kind,
            task_scope=task_scope,
        )
        promoted = self.load_promoted_memories()
        active_memory = self._find_active_memory_by_key(promoted["active"], memory_key)
        warm_candidate = self._compress_payload_for_tier(
            payload={
                "task_scope": task_scope,
                "workflow_name": candidate_payload.get("workflow_name"),
                "document_id": candidate_payload.get("document_id"),
                "descriptor_kind": descriptor_kind,
                "summary_vector": [
                    self._quantize_text(inputs.get("vendor_name"), limit=18),
                    self._quantize_text(inputs.get("document_type"), limit=12),
                    self._quantize_text(inputs.get("currency"), limit=8),
                    self._quantize_total(inputs.get("total")),
                ],
                "reuse_hints": {
                    "document_type": self._quantize_text(inputs.get("document_type"), limit=8),
                },
                "value_profile": [],
            },
            retention_tier="warm",
        )
        warm_digest = canonical_json_hash(warm_candidate)
        novelty_score = 0.9
        conflict_risk = 0.0
        if active_memory is not None:
            if active_memory["payload_digest"] == warm_digest:
                novelty_score = 0.05
                conflict_risk = 0.05
            else:
                novelty_score = 0.48
                active_trust = float(active_memory.get("trust_score", self._trust_score(str(active_memory.get("trust_ref", "")))))
                candidate_trust = self._trust_score(trust_ref)
                conflict_risk = 0.75 if active_trust >= candidate_trust else 0.45
        usefulness_score = min(
            1.0,
            0.2
            + (0.2 if self._quantize_text(inputs.get("vendor_name"), limit=18) else 0.0)
            + (0.2 if self._quantize_text(inputs.get("document_type"), limit=12) else 0.0)
            + (0.15 if self._quantize_text(inputs.get("currency"), limit=8) else 0.0)
            + (0.15 if self._quantize_total(inputs.get("total")) else 0.0)
            + (0.1 if len(selected_cells) > 0 else 0.0),
        )
        trust_score = self._trust_score(trust_ref)
        reuse_potential = min(
            1.0,
            0.35
            + (0.2 if self._quantize_text(inputs.get("document_type"), limit=12) else 0.0)
            + (0.2 if self._quantize_text(inputs.get("vendor_name"), limit=18) else 0.0)
            + (0.15 if any("router" in str(item) for item in selected_cells) else 0.0),
        )
        raw_bytes = len(canonical_json_bytes(candidate_payload))
        warm_bytes = len(canonical_json_bytes(warm_candidate))
        compression_gain = 0.0 if raw_bytes <= 0 else round(max(0.0, 1.0 - (warm_bytes / float(raw_bytes))), 6)
        memory_class = self._classify_memory_type(
            payload=candidate_payload,
            descriptor_kind=descriptor_kind,
            producer_cell_id=producer_cell_id,
        )
        value_score = max(
            0.0,
            min(
                1.0,
                round(
                    (0.28 * novelty_score)
                    + (0.24 * usefulness_score)
                    + (0.18 * trust_score)
                    + (0.18 * reuse_potential)
                    + (0.12 * compression_gain)
                    - (0.2 * conflict_risk)
                    + (0.05 if review_ready else -0.2),
                    6,
                ),
            ),
        )
        reason = "candidate scored for novelty, usefulness, trust, reuse, compression, and conflict risk"
        return {
            "memory_class": memory_class,
            "value_score": value_score,
            "reason": reason,
            "scores": {
                "novelty_score": round(novelty_score, 6),
                "usefulness_score": round(usefulness_score, 6),
                "trust_score": round(trust_score, 6),
                "reuse_potential": round(reuse_potential, 6),
                "compression_gain": compression_gain,
                "conflict_risk": round(conflict_risk, 6),
            },
        }

    def _classify_memory_type(
        self,
        *,
        payload: dict[str, Any],
        descriptor_kind: str,
        producer_cell_id: str,
    ) -> str:
        inputs = payload.get("inputs")
        if not isinstance(inputs, dict):
            inputs = {}
        if any(key.startswith("policy_") for key in inputs.keys()) or "policy" in descriptor_kind:
            return "policy_useful_memory"
        if "correction_of" in inputs:
            return "correction_memory"
        if any(key.startswith("failure_") or key.startswith("error_") for key in inputs.keys()):
            return "failure_memory"
        if "router" in producer_cell_id or any("router" in str(item) for item in payload.get("selected_cells", [])):
            return "routing_useful_memory"
        return "pattern_memory"

    def _trust_score(self, trust_ref: str) -> float:
        if "experimental" in trust_ref:
            return 0.35
        if "policy" in trust_ref:
            return 0.95
        if "bounded_local" in trust_ref:
            return 0.76
        return 0.6

    def _retention_priority(self, record: dict[str, Any]) -> float:
        trust_score = float(record.get("trust_score", self._trust_score(str(record.get("trust_ref", "")))))
        value_score = float(record.get("value_score", 0.0))
        reuse_score = min(1.0, float(record.get("reuse_count", 0)) / 3.0)
        policy_bonus = 0.2 if str(record.get("memory_class")) == "policy_useful_memory" else 0.0
        return round((0.4 * trust_score) + (0.35 * value_score) + (0.15 * reuse_score) + policy_bonus, 6)

    def _select_pressure_target(self, *, tier: str, allow_high_trust: bool) -> dict[str, Any] | None:
        promoted = self.load_promoted_memories()
        matches = [
            deepcopy(record)
            for record in promoted["active"].values()
            if str(record.get("retention_tier")) == tier
        ]
        if not allow_high_trust:
            filtered = [
                record
                for record in matches
                if float(record.get("trust_score", self._trust_score(str(record.get("trust_ref", ""))))) < 0.9
                and str(record.get("memory_class")) != "policy_useful_memory"
            ]
            if filtered:
                matches = filtered
        if not matches:
            return None
        matches.sort(
            key=lambda item: (
                self._retention_priority(item),
                float(item.get("value_score", 0.0)),
                float(item.get("trust_score", self._trust_score(str(item.get("trust_ref", ""))))),
                str(item.get("created_utc", "")),
                str(item.get("memory_id", "")),
            )
        )
        return matches[0]

    def _build_supersession_delta(self, *, prior_payload: dict[str, Any], next_payload: dict[str, Any]) -> dict[str, Any]:
        prior_vector = list(prior_payload.get("summary_vector", []))
        next_vector = list(next_payload.get("summary_vector", []))
        changes = [
            index
            for index, (before, after) in enumerate(zip(prior_vector, next_vector, strict=False))
            if before != after
        ]
        return {
            "changed_vector_slots": changes,
            "prior_digest": canonical_json_hash(prior_payload),
            "next_digest": canonical_json_hash(next_payload),
        }

    def _record_lifecycle_memory_outcome(
        self,
        *,
        lifecycle_manager: Any | None,
        candidate: dict[str, Any],
        outcome_kind: str,
        detail: str,
    ) -> None:
        if lifecycle_manager is None or not hasattr(lifecycle_manager, "record_memory_outcome"):
            return
        lifecycle_manager.record_memory_outcome(
            producer_cell_id=str(candidate["producer_cell_id"]),
            outcome_kind=outcome_kind,
            value_score=float(candidate.get("value_score", 0.0)),
            memory_class=str(candidate.get("memory_class", "pattern_memory")),
            detail=ensure_non_empty_string(detail, "memory lifecycle detail", code="MEMORY_INVALID"),
        )

    def _payload_semantic_digest(self, payload: dict[str, Any]) -> str:
        normalized = dict(payload)
        normalized.pop("compression_mode", None)
        return canonical_json_hash(normalized)

    def _validate_decision(self, decision: dict[str, Any]) -> None:
        ensure_exact_keys(decision, DECISION_FIELDS, "MemoryPromotionDecision", code="MEMORY_INVALID")
        decision_name = ensure_non_empty_string(decision["decision"], "MemoryPromotionDecision.decision", code="MEMORY_INVALID")
        if decision_name not in ALLOWED_DECISIONS:
            raise FabricError("MEMORY_INVALID", f"Unsupported MemoryPromotionDecision.decision: {decision_name}.")
        retention_tier = ensure_non_empty_string(
            decision["retention_tier"],
            "MemoryPromotionDecision.retention_tier",
            code="MEMORY_INVALID",
        )
        if retention_tier not in ALLOWED_TIERS:
            raise FabricError("MEMORY_INVALID", f"Unsupported MemoryPromotionDecision.retention_tier: {retention_tier}.")
        ensure_non_empty_string(decision["candidate_id"], "MemoryPromotionDecision.candidate_id", code="MEMORY_INVALID")
        ensure_non_empty_string(decision["reviewer_id"], "MemoryPromotionDecision.reviewer_id", code="MEMORY_INVALID")
        ensure_non_empty_string(
            decision["compression_mode"],
            "MemoryPromotionDecision.compression_mode",
            code="MEMORY_INVALID",
        )
        ensure_non_empty_string(decision["reason"], "MemoryPromotionDecision.reason", code="MEMORY_INVALID")
        ensure_non_empty_string(decision["rollback_ref"], "MemoryPromotionDecision.rollback_ref", code="MEMORY_INVALID")
        ensure_non_empty_string(decision["created_utc"], "MemoryPromotionDecision.created_utc", code="MEMORY_INVALID")

    def _validate_descriptor(self, descriptor: dict[str, Any]) -> None:
        ensure_exact_keys(descriptor, DESCRIPTOR_FIELDS, "DescriptorRecord", code="MEMORY_INVALID")
        storage_tier = ensure_non_empty_string(descriptor["storage_tier"], "DescriptorRecord.storage_tier", code="MEMORY_INVALID")
        if storage_tier not in ALLOWED_TIERS:
            raise FabricError("MEMORY_INVALID", f"Unsupported DescriptorRecord.storage_tier: {storage_tier}.")

    def _build_decision(
        self,
        *,
        candidate_id: str,
        reviewer_id: str,
        decision: str,
        compression_mode: str,
        retention_tier: str,
        reason: str,
    ) -> dict[str, Any]:
        record = {
            "candidate_id": ensure_non_empty_string(
                candidate_id,
                "MemoryPromotionDecision.candidate_id",
                code="MEMORY_INVALID",
            ),
            "reviewer_id": ensure_non_empty_string(
                reviewer_id,
                "MemoryPromotionDecision.reviewer_id",
                code="MEMORY_INVALID",
            ),
            "decision": ensure_non_empty_string(
                decision,
                "MemoryPromotionDecision.decision",
                code="MEMORY_INVALID",
            ),
            "compression_mode": ensure_non_empty_string(
                compression_mode,
                "MemoryPromotionDecision.compression_mode",
                code="MEMORY_INVALID",
            ),
            "retention_tier": ensure_non_empty_string(
                retention_tier,
                "MemoryPromotionDecision.retention_tier",
                code="MEMORY_INVALID",
            ),
            "reason": ensure_non_empty_string(reason, "MemoryPromotionDecision.reason", code="MEMORY_INVALID"),
            "rollback_ref": f"memory:rollback:{candidate_id}:{decision}",
            "created_utc": utc_now_iso(),
        }
        self._validate_decision(record)
        return record

    def _append_decision(self, decision: dict[str, Any]) -> str:
        self._validate_decision(decision)
        payload = self._load_or_initialize(
            self.store.memory_decisions_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.decisions.v1", "entries": []},
        )
        payload["entries"].append(decision)
        write_json_atomic(self.store.memory_decisions_path(self.fabric_id), payload)
        return repo_relative(self.store.memory_decisions_path(self.fabric_id))

    def _append_replay_entry(self, entry: dict[str, Any]) -> None:
        payload = self._load_or_initialize(
            self.store.memory_replay_store_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.replay_store.v1", "entries": []},
        )
        payload["entries"].append(entry)
        payload["entries"] = payload["entries"][-self.memory_caps["replay_entries"] :]
        write_json_atomic(self.store.memory_replay_store_path(self.fabric_id), payload)

    def _record_memory_pressure_signal(
        self,
        *,
        lifecycle_manager: Any | None,
        severity: float,
        status: str,
        resolution_ref: str | None,
    ) -> None:
        if lifecycle_manager is None:
            return
        lifecycle_manager.register_need_signal(
            signal={
                "need_signal_id": f"{self.fabric_id}:memory-pressure",
                "source_type": "fabric",
                "source_id": self.fabric_id,
                "signal_kind": "memory_pressure",
                "severity": severity,
                "evidence_ref": repo_relative(self.store.memory_decisions_path(self.fabric_id)),
                "proposed_action": "consolidate_reviewed_memory",
                "status": status,
                "expires_at_utc": utc_now_iso(),
                "resolution_ref": resolution_ref,
                "created_utc": utc_now_iso(),
            }
        )

    def _clear_candidate_payload(self, candidate: dict[str, Any]) -> None:
        payload_ref = candidate.get("payload_ref")
        if isinstance(payload_ref, str):
            payload_path = self._resolve_repo_ref(payload_ref)
            if payload_path.exists():
                payload_path.unlink()
        candidate["payload_ref"] = None

    def _prune_raw_logs(self) -> list[str]:
        raw_logs = self._load_or_initialize(
            self.store.raw_log_index_path(self.fabric_id),
            {"schema_version": "agif.fabric.memory.raw_logs.v1", "entries": []},
        )
        protected_refs = {
            ref
            for record in self.load_candidates().values()
            if record.get("status") in {"pending", "deferred"}
            for ref in record.get("source_log_refs", [])
        }
        removed: list[str] = []
        while (
            len(raw_logs["entries"]) > self.memory_caps["raw_log_entries"]
            or sum(int(item.get("payload_bytes", 0)) for item in raw_logs["entries"]) > self.memory_caps["raw_log_bytes"]
        ):
            removable_index = None
            for index, item in enumerate(raw_logs["entries"]):
                if item["payload_ref"] not in protected_refs:
                    removable_index = index
                    break
            if removable_index is None:
                break
            item = raw_logs["entries"].pop(removable_index)
            payload_path = self._resolve_repo_ref(item["payload_ref"])
            if payload_path.exists():
                payload_path.unlink()
            removed.append(item["payload_ref"])
        write_json_atomic(self.store.raw_log_index_path(self.fabric_id), raw_logs)
        return removed

    def _load_optional_need_signals(self) -> list[dict[str, Any]]:
        path = self.store.need_signals_path(self.fabric_id)
        if not path.exists():
            return []
        payload = load_json_file(
            path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label="Need signals",
        )
        if not isinstance(payload, dict):
            return []
        signals = payload.get("signals", {})
        if not isinstance(signals, dict):
            return []
        return [deepcopy(item) for _, item in sorted(signals.items()) if isinstance(item, dict)]

    def _active_state_digest(self) -> str:
        descriptors = self.load_descriptors()
        promoted = self.load_promoted_memories()
        normalized = {
            "descriptors": [
                {
                    "descriptor_id": item["descriptor_id"],
                    "descriptor_kind": item["descriptor_kind"],
                    "task_scope": item["task_scope"],
                    "payload_ref": item["payload_ref"],
                    "storage_tier": item["storage_tier"],
                    "supersedes_descriptor_id": item["supersedes_descriptor_id"],
                }
                for _, item in sorted(descriptors["active"].items())
            ],
            "promoted": [
                {
                    "memory_id": item["memory_id"],
                    "descriptor_id": item["descriptor_id"],
                    "memory_key": item["memory_key"],
                    "payload_digest": item["payload_digest"],
                    "retention_tier": item["retention_tier"],
                    "compression_mode": item["compression_mode"],
                    "supersedes_memory_id": item["supersedes_memory_id"],
                    "memory_class": item.get("memory_class"),
                    "value_score": item.get("value_score"),
                    "trust_score": item.get("trust_score"),
                    "reuse_count": item.get("reuse_count", 0),
                }
                for _, item in sorted(promoted["active"].items())
            ],
        }
        return canonical_json_hash(normalized)

    def _tier_usage_bytes(self, tier: str) -> int:
        payload_dir = self.store.memory_tier_payload_path(self.fabric_id, tier, "placeholder").parent
        total = 0
        for path in sorted(payload_dir.glob("*.json")):
            try:
                total += len(path.read_bytes())
            except OSError:
                continue
        return total

    def _find_active_memory_by_key(self, active: dict[str, Any], memory_key: str) -> dict[str, Any] | None:
        for _, record in sorted(active.items()):
            if record.get("memory_key") == memory_key:
                return deepcopy(record)
        return None

    def _oldest_active_memory(self, *, tier: str) -> dict[str, Any] | None:
        promoted = self.load_promoted_memories()
        matches = [
            record
            for record in promoted["active"].values()
            if str(record.get("retention_tier")) == tier
        ]
        if not matches:
            return None
        matches.sort(key=lambda item: (str(item.get("created_utc", "")), str(item.get("memory_id", ""))))
        return deepcopy(matches[0])

    def _memory_key(self, *, producer_cell_id: str, descriptor_kind: str, task_scope: str) -> str:
        return f"{producer_cell_id}:{descriptor_kind}:{task_scope}"

    def _memory_caps(self) -> dict[str, int]:
        caps = self.config.get("memory_caps", {})
        hot_bytes = max(1024, int(caps.get("hot_bytes", 1024 * 1024)))
        warm_bytes = max(1024, int(caps.get("warm_bytes", 4 * 1024 * 1024)))
        cold_bytes = max(1024, int(caps.get("cold_bytes", 16 * 1024 * 1024)))
        return {
            "hot_bytes": hot_bytes,
            "warm_bytes": warm_bytes,
            "cold_bytes": cold_bytes,
            "raw_log_bytes": max(1024, int(caps.get("raw_log_bytes", min(hot_bytes, 256 * 1024)))),
            "raw_log_entries": max(1, int(caps.get("raw_log_entries", 8))),
            "replay_entries": max(1, int(caps.get("replay_entries", 12))),
            "replay_files": max(1, int(caps.get("replay_files", 8))),
        }

    def _resolve_repo_ref(self, reference: str) -> Path:
        path = Path(reference)
        if path.is_absolute():
            return path.resolve()
        repo_root = Path(__file__).resolve().parents[3]
        return (repo_root / path).resolve()

    def _load_payload_ref(self, reference: Any, *, code: str) -> dict[str, Any]:
        if not isinstance(reference, str) or reference.strip() == "":
            raise FabricError(code, "Payload reference is required.")
        return load_json_file(
            self._resolve_repo_ref(reference),
            not_found_code=code,
            invalid_code=code,
            label="Memory payload",
        )

    def _quantize_text(self, value: Any, *, limit: int) -> str | None:
        if not isinstance(value, str):
            return None
        return value.strip().lower()[:limit] or None

    def _quantize_total(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned[:12] or None
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
        return None

    def _default_compression_mode(self, decision: str, tier: str) -> str:
        if decision == "defer":
            return "review_buffer_v1"
        if decision == "reject":
            return "review_reject_v1"
        if decision == "retire":
            return "retire_review_v1"
        if tier == "cold":
            return "quantized_cold_v1"
        return "quantized_summary_v1"

    def _next_numeric_id(self, prefix: str, existing_ids: list[str]) -> str:
        max_seen = 0
        marker = f"{prefix}_"
        for existing in existing_ids:
            if not existing.startswith(marker):
                continue
            suffix = existing[len(marker) :]
            if suffix.isdigit():
                max_seen = max(max_seen, int(suffix))
        return f"{prefix}_{max_seen + 1:04d}"

    def _load_or_initialize(self, path: Path, default_payload: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        payload = load_json_file(
            path,
            not_found_code="STATE_INVALID",
            invalid_code="STATE_INVALID",
            label=str(path.name),
        )
        if not isinstance(payload, dict):
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        return payload
