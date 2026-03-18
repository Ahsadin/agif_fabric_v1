"""Governed skill-graph and transfer approval helpers for Track B Gap 2."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from intelligence.fabric.common import load_json_file, utc_now_iso, write_json_atomic
from intelligence.fabric.state_store import FabricStateStore
from intelligence.fabric.utility import clamp_score, trust_score_from_ref


GRAPH_SCHEMA_VERSION = "agif.fabric.descriptors.skill_graph.v1"
TRANSFER_SCHEMA_VERSION = "agif.fabric.descriptors.transfer_log.v1"


class DescriptorGraphManager:
    """Builds an auditable descriptor graph and governs transfer approvals."""

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
        self.transfer_quality_floor = float(self.policy.get("transfer_quality_floor", 0.72))
        self.transfer_abstain_floor = float(self.policy.get("transfer_abstain_floor", 0.48))
        self.cross_domain_provenance_floor = float(self.policy.get("cross_domain_provenance_floor", 0.45))
        self.ensure_store()

    def ensure_store(self) -> None:
        self._load_or_initialize(
            self.store.descriptor_graph_path(self.fabric_id),
            {
                "schema_version": GRAPH_SCHEMA_VERSION,
                "synced_utc": None,
                "nodes": {},
                "edges": {},
            },
        )
        self._load_or_initialize(
            self.store.descriptor_transfer_log_path(self.fabric_id),
            {
                "schema_version": TRANSFER_SCHEMA_VERSION,
                "entries": [],
                "materialized_transfers": {},
            },
        )

    def load_graph(self) -> dict[str, Any]:
        return self._load_or_initialize(
            self.store.descriptor_graph_path(self.fabric_id),
            {
                "schema_version": GRAPH_SCHEMA_VERSION,
                "synced_utc": None,
                "nodes": {},
                "edges": {},
            },
        )

    def load_transfer_log(self) -> dict[str, Any]:
        return self._load_or_initialize(
            self.store.descriptor_transfer_log_path(self.fabric_id),
            {
                "schema_version": TRANSFER_SCHEMA_VERSION,
                "entries": [],
                "materialized_transfers": {},
            },
        )

    def sync_from_memory(self, *, memory_manager: Any) -> dict[str, Any]:
        descriptors = memory_manager.load_descriptors()
        promoted = memory_manager.load_promoted_memories()
        active_memories = {
            str(record["descriptor_id"]): deepcopy(record)
            for record in promoted["active"].values()
        }
        archived_memories = {
            str(record["descriptor_id"]): deepcopy(record)
            for record in promoted["archived"].values()
        }

        nodes: dict[str, dict[str, Any]] = {}
        for descriptor_id, record in sorted(descriptors["active"].items()):
            nodes[f"source::{descriptor_id}"] = self._build_source_node(
                descriptor_id=descriptor_id,
                descriptor_record=record,
                promoted_record=active_memories.get(str(descriptor_id)),
                status="active",
                archived_meta=None,
            )
        for descriptor_id, archived in sorted(descriptors["archived"].items()):
            nodes[f"source::{descriptor_id}"] = self._build_source_node(
                descriptor_id=descriptor_id,
                descriptor_record=archived["record"],
                promoted_record=archived_memories.get(str(descriptor_id)),
                status="retired",
                archived_meta=archived,
            )

        edges: dict[str, dict[str, Any]] = {}
        source_nodes = [node for node in nodes.values() if node["node_type"] == "source_descriptor"]
        for left_index in range(len(source_nodes)):
            for right_index in range(left_index + 1, len(source_nodes)):
                left = source_nodes[left_index]
                right = source_nodes[right_index]
                for relation, weight in self._matching_relations(left=left, right=right):
                    edge_id = f"edge::{relation}::{left['node_id']}::{right['node_id']}"
                    edges[edge_id] = {
                        "edge_id": edge_id,
                        "from_node_id": left["node_id"],
                        "to_node_id": right["node_id"],
                        "relation": relation,
                        "weight": weight,
                        "created_utc": utc_now_iso(),
                    }

        transfer_log = self.load_transfer_log()
        for materialized in transfer_log["materialized_transfers"].values():
            transfer_node = self._build_transfer_node(materialized)
            nodes[transfer_node["node_id"]] = transfer_node
            transfer_edge = self._transfer_edge(materialized)
            edges[transfer_edge["edge_id"]] = transfer_edge

        graph = {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "synced_utc": utc_now_iso(),
            "nodes": nodes,
            "edges": edges,
        }
        write_json_atomic(self.store.descriptor_graph_path(self.fabric_id), graph)
        return deepcopy(graph)

    def request_transfer(
        self,
        *,
        request: dict[str, Any],
        authority_engine: Any,
    ) -> dict[str, Any]:
        graph = self.load_graph()
        transfer_log = self.load_transfer_log()
        request_id = str(request.get("request_id") or self._next_numeric_id("request", [item["request_id"] for item in transfer_log["entries"]]))
        selected_source = self._select_source(graph=graph, request=request)
        baseline_support_score = self._baseline_support_score(request=request)

        if selected_source is None:
            entry = self._build_transfer_entry(
                request_id=request_id,
                request=request,
                selected_source=None,
                status="abstained",
                decision_reason="no_eligible_source_descriptor",
                transfer_quality_score=0.0,
                baseline_support_score=baseline_support_score,
                target_support_score=baseline_support_score,
                quality_breakdown={},
                authority_review=None,
                materialized_transfer=None,
            )
            self._append_transfer_entry(transfer_log=transfer_log, entry=entry)
            return entry

        if selected_source["status"] != "active":
            entry = self._build_transfer_entry(
                request_id=request_id,
                request=request,
                selected_source=selected_source,
                status="denied",
                decision_reason="source_descriptor_retired",
                transfer_quality_score=0.0,
                baseline_support_score=baseline_support_score,
                target_support_score=baseline_support_score,
                quality_breakdown={},
                authority_review=None,
                materialized_transfer=None,
            )
            self._append_transfer_entry(transfer_log=transfer_log, entry=entry)
            return entry

        cross_domain = bool(request.get("cross_domain", False))
        if not cross_domain:
            cross_domain = self._normalize_text(request.get("target_domain"), limit=64) != self._normalize_text(
                selected_source.get("source_domain"), limit=64
            )
        transfer_quality_score, quality_breakdown = self._score_transfer_candidate(
            source_node=selected_source,
            request=request,
            cross_domain=cross_domain,
        )
        if transfer_quality_score < self.transfer_abstain_floor:
            entry = self._build_transfer_entry(
                request_id=request_id,
                request=request,
                selected_source=selected_source,
                status="abstained",
                decision_reason="transfer_quality_below_abstain_floor",
                transfer_quality_score=transfer_quality_score,
                baseline_support_score=baseline_support_score,
                target_support_score=baseline_support_score,
                quality_breakdown=quality_breakdown,
                authority_review=None,
                materialized_transfer=None,
            )
            self._append_transfer_entry(transfer_log=transfer_log, entry=entry)
            return entry

        explicit_transfer_approval = bool(request.get("explicit_transfer_approval", False))
        if cross_domain and not explicit_transfer_approval:
            entry = self._build_transfer_entry(
                request_id=request_id,
                request=request,
                selected_source=selected_source,
                status="denied",
                decision_reason="missing_explicit_transfer_approval",
                transfer_quality_score=transfer_quality_score,
                baseline_support_score=baseline_support_score,
                target_support_score=baseline_support_score,
                quality_breakdown=quality_breakdown,
                authority_review=None,
                materialized_transfer=None,
            )
            self._append_transfer_entry(transfer_log=transfer_log, entry=entry)
            return entry

        authority_review = authority_engine.evaluate_action(
            action="transfer_approval",
            proposer=str(request.get("proposer") or self.policy.get("default_tissue_coordinator") or "tissue:descriptor_transfer"),
            need_signal=None,
            utility_evaluation={
                "utility_score": transfer_quality_score,
                "threshold": self.transfer_quality_floor,
            },
            policy_envelope=deepcopy(
                request.get(
                    "policy_envelope",
                    {
                        "allowed_actions": ["transfer", "summarize"],
                        "human_boundary": self.policy.get("human_boundary", "document/workflow intelligence"),
                    },
                )
            ),
            trust_state={
                "trust_ref": selected_source["trust_ref"],
                "trust_score": selected_source["trust_score"],
            },
            rollback_ref=f"descriptor_transfer:{request_id}",
            descriptor_refs=[selected_source["descriptor_id"]],
            related_cells=[selected_source["producer_cell_id"], str(request.get("target_cell_id") or "target:unknown")],
            metadata={
                "lineage_id": selected_source["descriptor_id"],
                "cross_domain": cross_domain,
                "explicit_transfer_approval": explicit_transfer_approval,
                "descriptor_provenance_score": selected_source["provenance_score"],
                "transfer_quality_score": transfer_quality_score,
                "source_domain": selected_source["source_domain"],
                "target_domain": str(request.get("target_domain")),
                "source_memory_id": selected_source.get("memory_id"),
                "source_payload_ref": selected_source["payload_ref"],
            },
        )

        if not authority_review["approved"]:
            entry = self._build_transfer_entry(
                request_id=request_id,
                request=request,
                selected_source=selected_source,
                status="denied",
                decision_reason="authority_vetoed_transfer",
                transfer_quality_score=transfer_quality_score,
                baseline_support_score=baseline_support_score,
                target_support_score=baseline_support_score,
                quality_breakdown=quality_breakdown,
                authority_review=authority_review,
                materialized_transfer=None,
            )
            self._append_transfer_entry(transfer_log=transfer_log, entry=entry)
            return entry

        materialized_transfer = self._materialize_transfer(
            transfer_log=transfer_log,
            request_id=request_id,
            request=request,
            selected_source=selected_source,
            transfer_quality_score=transfer_quality_score,
            baseline_support_score=baseline_support_score,
            authority_review=authority_review,
        )
        authority_engine.finalize_review(
            authority_review["review_id"],
            action_ref=materialized_transfer["transfer_id"],
            rollback_ref=f"descriptor_transfer:{request_id}",
        )
        self._apply_materialized_transfer(graph=graph, materialized_transfer=materialized_transfer)
        write_json_atomic(self.store.descriptor_graph_path(self.fabric_id), graph)
        entry = self._build_transfer_entry(
            request_id=request_id,
            request=request,
            selected_source=selected_source,
            status="approved",
            decision_reason="transfer_approved",
            transfer_quality_score=transfer_quality_score,
            baseline_support_score=baseline_support_score,
            target_support_score=materialized_transfer["target_support_score"],
            quality_breakdown=quality_breakdown,
            authority_review=authority_review,
            materialized_transfer=materialized_transfer,
        )
        self._append_transfer_entry(transfer_log=transfer_log, entry=entry)
        return entry

    def summary(self) -> dict[str, Any]:
        graph = self.load_graph()
        transfer_log = self.load_transfer_log()
        nodes = list(graph["nodes"].values())
        source_nodes = [node for node in nodes if node["node_type"] == "source_descriptor"]
        transfer_nodes = [node for node in nodes if node["node_type"] == "transferred_descriptor"]
        retired_source_nodes = [node for node in source_nodes if node["status"] == "retired"]
        relation_counts: dict[str, int] = {}
        for edge in graph["edges"].values():
            relation = str(edge["relation"])
            relation_counts[relation] = relation_counts.get(relation, 0) + 1
        entries = transfer_log["entries"]
        approved_entries = [entry for entry in entries if entry["status"] == "approved"]
        denied_entries = [entry for entry in entries if entry["status"] == "denied"]
        abstained_entries = [entry for entry in entries if entry["status"] == "abstained"]
        explicit_provenance_count = len(
            [
                entry
                for entry in approved_entries
                if self._has_explicit_provenance(entry.get("provenance_bundle"))
            ]
        )
        return {
            "source_descriptor_count": len(source_nodes),
            "active_source_descriptor_count": len([node for node in source_nodes if node["status"] == "active"]),
            "retired_source_descriptor_count": len(retired_source_nodes),
            "retired_source_descriptor_ids": sorted(node["descriptor_id"] for node in retired_source_nodes),
            "transferred_descriptor_count": len(transfer_nodes),
            "edge_count": len(graph["edges"]),
            "relation_counts": relation_counts,
            "transfer_request_count": len(entries),
            "approved_transfer_count": len(approved_entries),
            "denied_transfer_count": len(denied_entries),
            "abstained_transfer_count": len(abstained_entries),
            "explicit_provenance_count": explicit_provenance_count,
            "latest_transfer_ref": None if not entries else entries[-1]["request_id"],
        }

    def _build_source_node(
        self,
        *,
        descriptor_id: str,
        descriptor_record: dict[str, Any],
        promoted_record: dict[str, Any] | None,
        status: str,
        archived_meta: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload = self._load_payload_if_exists(descriptor_record.get("payload_ref"))
        reuse_hints = dict(payload.get("reuse_hints") or {})
        trust_score = clamp_score(
            float(promoted_record.get("trust_score", trust_score_from_ref(str(descriptor_record.get("trust_ref", "")))))
            if promoted_record is not None
            else trust_score_from_ref(str(descriptor_record.get("trust_ref", "")))
        )
        value_score = clamp_score(0.0 if promoted_record is None else float(promoted_record.get("value_score", 0.0)))
        confidence_score = clamp_score(float(descriptor_record.get("confidence_score", 0.0)))
        provenance_bundle = {
            "source_descriptor_id": descriptor_id,
            "source_memory_id": None if promoted_record is None else promoted_record.get("memory_id"),
            "source_payload_ref": descriptor_record.get("payload_ref"),
            "source_ref": None if promoted_record is None else promoted_record.get("source_ref"),
            "source_log_refs": [] if promoted_record is None else list(promoted_record.get("source_log_refs", [])),
            "source_trust_ref": descriptor_record.get("trust_ref"),
            "source_trust_score": trust_score,
            "source_review_scores": {} if promoted_record is None else deepcopy(promoted_record.get("review_scores", {})),
            "reuse_hints": deepcopy(reuse_hints),
            "summary_vector": list(payload.get("summary_vector", []))[:4],
        }
        provenance_score = self._provenance_score(
            trust_score=trust_score,
            confidence_score=confidence_score,
            value_score=value_score,
            payload_ref=descriptor_record.get("payload_ref"),
            source_ref=None if promoted_record is None else promoted_record.get("source_ref"),
        )
        return {
            "node_id": f"source::{descriptor_id}",
            "node_type": "source_descriptor",
            "descriptor_id": descriptor_id,
            "status": status,
            "source_domain": self._infer_domain(str(descriptor_record.get("task_scope", ""))),
            "producer_cell_id": str(descriptor_record.get("producer_cell_id", "")),
            "descriptor_kind": str(descriptor_record.get("descriptor_kind", "")),
            "task_scope": str(descriptor_record.get("task_scope", "")),
            "memory_id": None if promoted_record is None else promoted_record.get("memory_id"),
            "memory_class": None if promoted_record is None else promoted_record.get("memory_class"),
            "trust_ref": str(descriptor_record.get("trust_ref", "")),
            "trust_score": trust_score,
            "confidence_score": confidence_score,
            "value_score": value_score,
            "reuse_count": 0 if promoted_record is None else int(promoted_record.get("reuse_count", 0)),
            "usefulness_hits": 0 if promoted_record is None else int(promoted_record.get("usefulness_hits", 0)),
            "payload_ref": str(descriptor_record.get("payload_ref", "")),
            "reuse_hints": deepcopy(reuse_hints),
            "summary_vector": list(payload.get("summary_vector", []))[:4],
            "provenance_score": provenance_score,
            "created_utc": str(descriptor_record.get("created_utc", "")),
            "retired_utc": None if archived_meta is None else archived_meta.get("archived_utc"),
            "archived_reason": None if archived_meta is None else archived_meta.get("archived_reason"),
            "provenance_bundle": provenance_bundle,
        }

    def _build_transfer_node(self, materialized_transfer: dict[str, Any]) -> dict[str, Any]:
        return {
            "node_id": f"transfer::{materialized_transfer['transfer_descriptor_id']}",
            "node_type": "transferred_descriptor",
            "descriptor_id": materialized_transfer["transfer_descriptor_id"],
            "status": materialized_transfer["status"],
            "source_domain": materialized_transfer["source_domain"],
            "target_domain": materialized_transfer["target_domain"],
            "target_cell_id": materialized_transfer["target_cell_id"],
            "source_descriptor_id": materialized_transfer["source_descriptor_id"],
            "transfer_id": materialized_transfer["transfer_id"],
            "transfer_quality_score": materialized_transfer["transfer_quality_score"],
            "baseline_support_score": materialized_transfer["baseline_support_score"],
            "target_support_score": materialized_transfer["target_support_score"],
            "transfer_approval_ref": materialized_transfer["transfer_approval_ref"],
            "created_utc": materialized_transfer["created_utc"],
            "provenance_bundle": deepcopy(materialized_transfer["provenance_bundle"]),
        }

    def _matching_relations(self, *, left: dict[str, Any], right: dict[str, Any]) -> list[tuple[str, float]]:
        relations: list[tuple[str, float]] = []
        left_hints = dict(left.get("reuse_hints", {}))
        right_hints = dict(right.get("reuse_hints", {}))
        if left_hints.get("document_type") and left_hints.get("document_type") == right_hints.get("document_type"):
            relations.append(("shared_document_type", 1.0))
        if left_hints.get("vendor_token") and left_hints.get("vendor_token") == right_hints.get("vendor_token"):
            relations.append(("shared_vendor_token", 1.0))
        if left.get("producer_cell_id") and left.get("producer_cell_id") == right.get("producer_cell_id"):
            relations.append(("shared_producer_cell", 0.5))
        return relations

    def _select_source(self, *, graph: dict[str, Any], request: dict[str, Any]) -> dict[str, Any] | None:
        source_descriptor_id = request.get("source_descriptor_id")
        source_nodes = [
            deepcopy(node)
            for node in graph["nodes"].values()
            if node["node_type"] == "source_descriptor"
        ]
        if source_descriptor_id:
            for node in source_nodes:
                if str(node["descriptor_id"]) == str(source_descriptor_id):
                    return node
            return None
        best_node: dict[str, Any] | None = None
        best_score = -1.0
        for node in source_nodes:
            if node["status"] != "active":
                continue
            score, _ = self._score_transfer_candidate(
                source_node=node,
                request=request,
                cross_domain=bool(request.get("cross_domain", False)),
            )
            if score > best_score:
                best_score = score
                best_node = node
        return best_node

    def _score_transfer_candidate(
        self,
        *,
        source_node: dict[str, Any],
        request: dict[str, Any],
        cross_domain: bool,
    ) -> tuple[float, dict[str, float]]:
        target_hints = dict(request.get("target_hints") or {})
        source_hints = dict(source_node.get("reuse_hints", {}))
        document_match = 1.0 if (
            self._normalize_text(target_hints.get("document_type"), limit=8)
            and self._normalize_text(target_hints.get("document_type"), limit=8) == self._normalize_text(source_hints.get("document_type"), limit=8)
        ) else 0.0
        vendor_match = 1.0 if (
            self._normalize_text(target_hints.get("vendor_token"), limit=8)
            and self._normalize_text(target_hints.get("vendor_token"), limit=8) == self._normalize_text(source_hints.get("vendor_token"), limit=8)
        ) else 0.0
        policy_readiness = 1.0 if str(source_node.get("memory_class")) == "policy_useful_memory" else (
            0.45 if str(source_node.get("memory_class")) == "routing_useful_memory" else 0.25
        )
        cross_domain_readiness = 1.0 if not cross_domain else (
            1.0 if str(source_node.get("memory_class")) in {"policy_useful_memory", "routing_useful_memory"} else 0.4
        )
        reuse_signal = min(1.0, int(source_node.get("reuse_count", 0)) / 3.0)
        breakdown = {
            "document_match": document_match,
            "vendor_match": vendor_match,
            "trust_score": clamp_score(float(source_node.get("trust_score", 0.0))),
            "confidence_score": clamp_score(float(source_node.get("confidence_score", 0.0))),
            "value_score": clamp_score(float(source_node.get("value_score", 0.0))),
            "cross_domain_readiness": clamp_score(cross_domain_readiness),
            "policy_readiness": clamp_score(policy_readiness),
            "reuse_signal": clamp_score(reuse_signal),
        }
        score = clamp_score(
            (0.28 * breakdown["document_match"])
            + (0.22 * breakdown["vendor_match"])
            + (0.18 * breakdown["trust_score"])
            + (0.12 * breakdown["confidence_score"])
            + (0.08 * breakdown["value_score"])
            + (0.07 * breakdown["cross_domain_readiness"])
            + (0.03 * breakdown["policy_readiness"])
            + (0.02 * breakdown["reuse_signal"])
        )
        return score, breakdown

    def _baseline_support_score(self, *, request: dict[str, Any]) -> float:
        target_hints = dict(request.get("target_hints") or {})
        base = 0.15
        if self._normalize_text(target_hints.get("document_type"), limit=8):
            base += 0.05
        if self._normalize_text(target_hints.get("vendor_token"), limit=8):
            base += 0.05
        return clamp_score(base)

    def _build_transfer_entry(
        self,
        *,
        request_id: str,
        request: dict[str, Any],
        selected_source: dict[str, Any] | None,
        status: str,
        decision_reason: str,
        transfer_quality_score: float,
        baseline_support_score: float,
        target_support_score: float,
        quality_breakdown: dict[str, float],
        authority_review: dict[str, Any] | None,
        materialized_transfer: dict[str, Any] | None,
    ) -> dict[str, Any]:
        cross_domain = bool(request.get("cross_domain", False))
        if selected_source is not None and not cross_domain:
            cross_domain = self._normalize_text(request.get("target_domain"), limit=64) != self._normalize_text(
                selected_source.get("source_domain"), limit=64
            )
        provenance_bundle = None
        if materialized_transfer is not None:
            provenance_bundle = deepcopy(materialized_transfer["provenance_bundle"])
        elif selected_source is not None:
            provenance_bundle = deepcopy(selected_source["provenance_bundle"])
        return {
            "request_id": request_id,
            "requested_source_descriptor_id": request.get("source_descriptor_id"),
            "selected_source_descriptor_id": None if selected_source is None else selected_source["descriptor_id"],
            "source_domain": None if selected_source is None else selected_source["source_domain"],
            "target_domain": str(request.get("target_domain", "")),
            "target_cell_id": str(request.get("target_cell_id", "")),
            "cross_domain": cross_domain,
            "explicit_transfer_approval": bool(request.get("explicit_transfer_approval", False)),
            "required_action": "transfer_approval" if cross_domain else "descriptor_use",
            "status": status,
            "decision_reason": decision_reason,
            "transfer_quality_score": clamp_score(transfer_quality_score),
            "baseline_support_score": clamp_score(baseline_support_score),
            "target_support_score": clamp_score(target_support_score),
            "quality_breakdown": deepcopy(quality_breakdown),
            "authority_review_id": None if authority_review is None else authority_review["review_id"],
            "authority_decision": None if authority_review is None else authority_review["decision"],
            "approval_required": cross_domain,
            "materialized_transfer_id": None if materialized_transfer is None else materialized_transfer["transfer_id"],
            "materialized_transfer": None if materialized_transfer is None else deepcopy(materialized_transfer),
            "provenance_bundle": provenance_bundle,
            "audit_ready": materialized_transfer is not None and self._has_explicit_provenance(provenance_bundle),
            "created_utc": utc_now_iso(),
        }

    def _materialize_transfer(
        self,
        *,
        transfer_log: dict[str, Any],
        request_id: str,
        request: dict[str, Any],
        selected_source: dict[str, Any],
        transfer_quality_score: float,
        baseline_support_score: float,
        authority_review: dict[str, Any],
    ) -> dict[str, Any]:
        transfer_ids = list(transfer_log["materialized_transfers"].keys())
        transfer_id = self._next_numeric_id("transfer", transfer_ids)
        transfer_descriptor_id = self._next_numeric_id(
            "tdesc",
            [str(item.get("transfer_descriptor_id", "")) for item in transfer_log["materialized_transfers"].values()],
        )
        target_support_score = clamp_score(baseline_support_score + (0.75 * transfer_quality_score))
        provenance_bundle = deepcopy(selected_source["provenance_bundle"])
        provenance_bundle.update(
            {
                "transfer_request_id": request_id,
                "transfer_descriptor_id": transfer_descriptor_id,
                "transfer_approval_ref": authority_review["review_id"],
                "target_domain": str(request.get("target_domain", "")),
                "target_cell_id": str(request.get("target_cell_id", "")),
                "cross_domain": bool(request.get("cross_domain", False))
                or self._normalize_text(request.get("target_domain"), limit=64) != self._normalize_text(selected_source.get("source_domain"), limit=64),
                "explicit_transfer_approval": bool(request.get("explicit_transfer_approval", False)),
            }
        )
        materialized_transfer = {
            "transfer_id": transfer_id,
            "transfer_descriptor_id": transfer_descriptor_id,
            "source_descriptor_id": selected_source["descriptor_id"],
            "source_memory_id": selected_source.get("memory_id"),
            "source_domain": selected_source["source_domain"],
            "target_domain": str(request.get("target_domain", "")),
            "target_cell_id": str(request.get("target_cell_id", "")),
            "status": "active",
            "transfer_approval_ref": authority_review["review_id"],
            "transfer_quality_score": clamp_score(transfer_quality_score),
            "baseline_support_score": clamp_score(baseline_support_score),
            "target_support_score": target_support_score,
            "provenance_bundle": provenance_bundle,
            "created_utc": utc_now_iso(),
        }
        transfer_log["materialized_transfers"][transfer_id] = materialized_transfer
        write_json_atomic(self.store.descriptor_transfer_log_path(self.fabric_id), transfer_log)
        return deepcopy(materialized_transfer)

    def _append_transfer_entry(self, *, transfer_log: dict[str, Any], entry: dict[str, Any]) -> None:
        transfer_log["entries"].append(entry)
        write_json_atomic(self.store.descriptor_transfer_log_path(self.fabric_id), transfer_log)

    def _apply_materialized_transfer(self, *, graph: dict[str, Any], materialized_transfer: dict[str, Any]) -> None:
        transfer_node = self._build_transfer_node(materialized_transfer)
        graph["nodes"][transfer_node["node_id"]] = transfer_node
        transfer_edge = self._transfer_edge(materialized_transfer)
        graph["edges"][transfer_edge["edge_id"]] = transfer_edge
        graph["synced_utc"] = utc_now_iso()

    def _transfer_edge(self, materialized_transfer: dict[str, Any]) -> dict[str, Any]:
        edge_id = f"edge::transfer_approval::source::{materialized_transfer['source_descriptor_id']}::transfer::{materialized_transfer['transfer_descriptor_id']}"
        return {
            "edge_id": edge_id,
            "from_node_id": f"source::{materialized_transfer['source_descriptor_id']}",
            "to_node_id": f"transfer::{materialized_transfer['transfer_descriptor_id']}",
            "relation": "transfer_approval",
            "weight": clamp_score(materialized_transfer["transfer_quality_score"]),
            "created_utc": materialized_transfer["created_utc"],
        }

    def _provenance_score(
        self,
        *,
        trust_score: float,
        confidence_score: float,
        value_score: float,
        payload_ref: Any,
        source_ref: Any,
    ) -> float:
        return clamp_score(
            (0.35 * clamp_score(trust_score))
            + (0.25 * clamp_score(confidence_score))
            + (0.2 * clamp_score(value_score))
            + (0.1 if isinstance(payload_ref, str) and payload_ref.strip() else 0.0)
            + (0.1 if isinstance(source_ref, str) and source_ref.strip() else 0.0)
        )

    def _has_explicit_provenance(self, provenance_bundle: Any) -> bool:
        if not isinstance(provenance_bundle, dict):
            return False
        required_fields = {
            "source_descriptor_id",
            "source_memory_id",
            "source_payload_ref",
            "source_trust_ref",
            "transfer_descriptor_id",
            "transfer_approval_ref",
        }
        return all(bool(provenance_bundle.get(field_name)) for field_name in required_fields)

    def _infer_domain(self, task_scope: str) -> str:
        normalized = str(task_scope).strip()
        if ":" in normalized:
            return normalized.split(":", 1)[0]
        if "/" in normalized:
            return normalized.split("/", 1)[0]
        return normalized or "unknown"

    def _load_payload_if_exists(self, reference: Any) -> dict[str, Any]:
        if not isinstance(reference, str) or reference.strip() == "":
            return {}
        path = Path(reference)
        if not path.is_absolute():
            path = self._repo_root() / reference
        if not path.exists() or not path.is_file():
            return {}
        payload = load_json_file(
            path,
            not_found_code="DESCRIPTOR_GRAPH_INVALID",
            invalid_code="DESCRIPTOR_GRAPH_INVALID",
            label="Descriptor payload",
        )
        if not isinstance(payload, dict):
            return {}
        return payload

    def _load_or_initialize(self, path: Path, default_payload: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        payload = load_json_file(
            path,
            not_found_code="DESCRIPTOR_GRAPH_INVALID",
            invalid_code="DESCRIPTOR_GRAPH_INVALID",
            label="Descriptor graph store",
        )
        if not isinstance(payload, dict):
            write_json_atomic(path, default_payload)
            return deepcopy(default_payload)
        return deepcopy(payload)

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def _next_numeric_id(self, prefix: str, existing_ids: list[str]) -> str:
        max_seen = 0
        marker = f"{prefix}_"
        for existing in existing_ids:
            if not str(existing).startswith(marker):
                continue
            suffix = str(existing)[len(marker) :]
            if suffix.isdigit():
                max_seen = max(max_seen, int(suffix))
        return f"{prefix}_{max_seen + 1:04d}"

    def _normalize_text(self, value: Any, *, limit: int) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()[:limit]
        return normalized or None
