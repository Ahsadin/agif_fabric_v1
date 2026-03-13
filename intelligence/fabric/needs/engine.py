"""Need generation, expiry, and resolution helpers for Phase 6."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from intelligence.fabric.common import load_json_file, utc_now_iso, write_json_atomic
from intelligence.fabric.governance.policy import ensure_need_signal
from intelligence.fabric.state_store import FabricStateStore
from intelligence.fabric.utility import clamp_score, trust_score_from_ref


DEFAULT_KIND_WEIGHTS = {
    "overload": 1.0,
    "uncertainty": 0.95,
    "novelty": 0.9,
    "redundancy": 0.8,
    "memory_pressure": 1.0,
    "trust_risk": 1.0,
    "coordination_gap": 0.9,
}

ACTIVE_SIGNAL_STATUSES = {"open", "reviewed"}


def score_foundation_needs(
    *,
    fabric_id: str,
    registered_blueprints: int,
    active_population_cap: int,
    logical_population: int | None = None,
    active_population: int = 0,
    burst_active_population_cap: int | None = None,
) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    logical_count = registered_blueprints if logical_population is None else int(logical_population)
    burst_cap = active_population_cap * 2 if burst_active_population_cap is None else int(burst_active_population_cap)
    now_utc = utc_now_iso()
    if registered_blueprints < 2:
        signals.append(
            {
                "need_signal_id": f"{fabric_id}:coordination-gap",
                "source_type": "fabric",
                "source_id": fabric_id,
                "signal_kind": "coordination_gap",
                "severity": 0.6,
                "evidence_ref": "phase3:registered_blueprints",
                "proposed_action": "register_more_blueprints",
                "status": "open",
                "expires_at_utc": now_utc,
                "resolution_ref": None,
                "created_utc": now_utc,
            }
        )
    if active_population >= active_population_cap:
        signals.append(
            {
                "need_signal_id": f"{fabric_id}:overload-risk",
                "source_type": "fabric",
                "source_id": fabric_id,
                "signal_kind": "overload",
                "severity": 0.5,
                "evidence_ref": "phase3:population_caps",
                "proposed_action": "review_split_or_hibernate",
                "status": "open",
                "expires_at_utc": now_utc,
                "resolution_ref": None,
                "created_utc": now_utc,
            }
        )
    if active_population > active_population_cap:
        signals.append(
            {
                "need_signal_id": f"{fabric_id}:burst-consolidation",
                "source_type": "fabric",
                "source_id": fabric_id,
                "signal_kind": "redundancy",
                "severity": 0.7,
                "evidence_ref": "phase4:burst_population",
                "proposed_action": "consolidate_to_steady_state",
                "status": "open",
                "expires_at_utc": now_utc,
                "resolution_ref": None,
                "created_utc": now_utc,
            }
        )
    if logical_count <= active_population:
        signals.append(
            {
                "need_signal_id": f"{fabric_id}:logical-growth-gap",
                "source_type": "fabric",
                "source_id": fabric_id,
                "signal_kind": "coordination_gap",
                "severity": 0.55,
                "evidence_ref": "phase4:logical_vs_active_population",
                "proposed_action": "grow_dormant_population",
                "status": "open",
                "expires_at_utc": now_utc,
                "resolution_ref": None,
                "created_utc": now_utc,
            }
        )
    return {
        "signal_count": len(signals),
        "registered_blueprints": registered_blueprints,
        "logical_population": logical_count,
        "active_population": active_population,
        "steady_active_population_target": active_population_cap,
        "burst_active_population_cap": burst_cap,
        "signals": signals,
    }


class NeedSignalManager:
    """Keeps need signals bounded, expiring, and traceable."""

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
        self.policy = dict(config.get("need_signal_policy", {}))
        self.default_ttl_seconds = max(60, int(self.policy.get("default_signal_ttl_seconds", 900)))
        configured_weights = self.policy.get("kind_weights", {})
        self.kind_weights = {
            kind: float(configured_weights.get(kind, DEFAULT_KIND_WEIGHTS[kind]))
            for kind in DEFAULT_KIND_WEIGHTS
        }
        self.ensure_store()

    def ensure_store(self) -> None:
        self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )
        self._load_or_initialize(
            self.store.need_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_history.v1", "entries": []},
        )

    def record_signal(self, *, signal: dict[str, Any], actor: str = "fabric:need_manager") -> dict[str, Any]:
        normalized = self._normalize_signal(signal)
        signals = self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )
        history = self._load_or_initialize(
            self.store.need_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_history.v1", "entries": []},
        )
        event = "created" if normalized["need_signal_id"] not in signals["signals"] else "updated"
        signals["signals"][normalized["need_signal_id"]] = normalized
        self._append_history(
            history,
            need_signal_id=normalized["need_signal_id"],
            event=event,
            status=normalized["status"],
            actor=actor,
            resolution_ref=normalized["resolution_ref"],
            detail=normalized["proposed_action"],
        )
        write_json_atomic(self.store.need_signals_path(self.fabric_id), signals)
        write_json_atomic(self.store.need_history_path(self.fabric_id), history)
        return deepcopy(normalized)

    def record_generated_signals(
        self,
        *,
        workflow_id: str,
        workflow_payload: dict[str, Any],
        candidate_contexts: list[dict[str, Any]],
        promoted_memories: list[dict[str, Any]],
        now_utc: str | None = None,
    ) -> list[dict[str, Any]]:
        current = self.expire_signals(now_utc=now_utc)
        del current
        generated = self.generate_runtime_signals(
            workflow_id=workflow_id,
            workflow_payload=workflow_payload,
            candidate_contexts=candidate_contexts,
            promoted_memories=promoted_memories,
            now_utc=now_utc,
        )
        return [self.record_signal(signal=item, actor=f"routing:{workflow_id}") for item in generated]

    def generate_runtime_signals(
        self,
        *,
        workflow_id: str,
        workflow_payload: dict[str, Any],
        candidate_contexts: list[dict[str, Any]],
        promoted_memories: list[dict[str, Any]],
        now_utc: str | None = None,
    ) -> list[dict[str, Any]]:
        timestamp = now_utc or utc_now_iso()
        expires_at = self._future_utc(timestamp, seconds=self.default_ttl_seconds)
        inputs = workflow_payload.get("inputs", {})
        if not isinstance(inputs, dict):
            inputs = {}
        workflow_name = str(workflow_payload.get("workflow_name", "document_workflow"))
        route_candidates = [item for item in candidate_contexts if item.get("route_capable")]
        low_trust_candidates = [
            item
            for item in candidate_contexts
            if float(item.get("trust_score", trust_score_from_ref(str(item.get("trust_ref", ""))))) < 0.6
        ]
        matching_memories = [
            item
            for item in promoted_memories
            if str(item.get("task_scope", "")).split(":", 1)[0] == workflow_name
        ]
        signals: list[dict[str, Any]] = []
        if any(str(item.get("active_task_ref")) not in {"", "None", workflow_id} for item in route_candidates):
            signals.append(
                self._make_signal(
                    signal_kind="overload",
                    source_type="tissue",
                    source_id="finance_document_workflow",
                    severity=0.8,
                    evidence_ref=f"routing:{workflow_id}:active_load",
                    proposed_action="route_around_busy_cell",
                    created_utc=timestamp,
                    expires_at_utc=expires_at,
                )
            )
        missing_fields = [
            key for key in ("document_type", "vendor_name", "total", "currency") if not str(inputs.get(key, "")).strip()
        ]
        if missing_fields:
            signals.append(
                self._make_signal(
                    signal_kind="uncertainty",
                    source_type="workflow",
                    source_id=workflow_id,
                    severity=min(1.0, 0.45 + (0.12 * len(missing_fields))),
                    evidence_ref=f"routing:{workflow_id}:missing:{','.join(sorted(missing_fields))}",
                    proposed_action="route_to_higher_context_review",
                    created_utc=timestamp,
                    expires_at_utc=expires_at,
                )
            )
        if len(matching_memories) == 0:
            signals.append(
                self._make_signal(
                    signal_kind="novelty",
                    source_type="workflow",
                    source_id=workflow_id,
                    severity=0.72,
                    evidence_ref=f"routing:{workflow_id}:no_reviewed_descriptor_match",
                    proposed_action="prefer_novelty_tolerant_router",
                    created_utc=timestamp,
                    expires_at_utc=expires_at,
                )
            )
        if len(route_candidates) > 1:
            signals.append(
                self._make_signal(
                    signal_kind="redundancy",
                    source_type="tissue",
                    source_id="finance_document_workflow",
                    severity=min(1.0, 0.35 + (0.1 * (len(route_candidates) - 1))),
                    evidence_ref=f"routing:{workflow_id}:router_overlap",
                    proposed_action="select_highest_utility_router",
                    created_utc=timestamp,
                    expires_at_utc=expires_at,
                )
            )
        if low_trust_candidates:
            signals.append(
                self._make_signal(
                    signal_kind="trust_risk",
                    source_type="tissue",
                    source_id="finance_document_workflow",
                    severity=0.78,
                    evidence_ref=f"routing:{workflow_id}:low_trust_candidates",
                    proposed_action="govern_descriptor_use",
                    created_utc=timestamp,
                    expires_at_utc=expires_at,
                )
            )
        if not route_candidates:
            signals.append(
                self._make_signal(
                    signal_kind="coordination_gap",
                    source_type="fabric",
                    source_id=self.fabric_id,
                    severity=0.9,
                    evidence_ref=f"routing:{workflow_id}:no_route_candidate",
                    proposed_action="reactivate_or_split_router",
                    created_utc=timestamp,
                    expires_at_utc=expires_at,
                )
            )
        return generated_with_ids(workflow_id=workflow_id, base_signals=signals)

    def expire_signals(self, *, now_utc: str | None = None) -> list[dict[str, Any]]:
        signals = self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )
        history = self._load_or_initialize(
            self.store.need_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_history.v1", "entries": []},
        )
        changed = False
        timestamp = now_utc or utc_now_iso()
        for record in signals["signals"].values():
            if record["status"] not in ACTIVE_SIGNAL_STATUSES:
                continue
            if self._parse_utc(record["expires_at_utc"]) <= self._parse_utc(timestamp):
                record["status"] = "expired"
                if record["resolution_ref"] is None:
                    record["resolution_ref"] = f"need:expired:{record['need_signal_id']}"
                self._append_history(
                    history,
                    need_signal_id=record["need_signal_id"],
                    event="expired",
                    status="expired",
                    actor="fabric:need_manager",
                    resolution_ref=record["resolution_ref"],
                    detail="expired before resolution",
                )
                changed = True
        if changed:
            write_json_atomic(self.store.need_signals_path(self.fabric_id), signals)
            write_json_atomic(self.store.need_history_path(self.fabric_id), history)
        return self.load_signals()

    def resolve_signal(
        self,
        *,
        need_signal_id: str,
        resolution_ref: str,
        status: str = "resolved",
        actor: str = "fabric:need_manager",
    ) -> dict[str, Any]:
        signals = self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )
        history = self._load_or_initialize(
            self.store.need_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_history.v1", "entries": []},
        )
        record = deepcopy(signals["signals"].get(need_signal_id))
        if record is None:
            return {"updated": False, "need_signal_id": need_signal_id}
        record["status"] = status
        record["resolution_ref"] = resolution_ref
        signals["signals"][need_signal_id] = record
        self._append_history(
            history,
            need_signal_id=need_signal_id,
            event=status,
            status=status,
            actor=actor,
            resolution_ref=resolution_ref,
            detail="resolution recorded",
        )
        write_json_atomic(self.store.need_signals_path(self.fabric_id), signals)
        write_json_atomic(self.store.need_history_path(self.fabric_id), history)
        return {**record, "updated": True}

    def load_signals(self) -> list[dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.need_signals_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_signals.v1", "signals": {}},
        )
        return [deepcopy(item) for _, item in sorted(payload["signals"].items())]

    def load_history(self) -> list[dict[str, Any]]:
        payload = self._load_or_initialize(
            self.store.need_history_path(self.fabric_id),
            {"schema_version": "agif.fabric.need_history.v1", "entries": []},
        )
        return [deepcopy(item) for item in payload["entries"]]

    def active_signals(self, *, now_utc: str | None = None) -> list[dict[str, Any]]:
        self.expire_signals(now_utc=now_utc)
        return [item for item in self.load_signals() if item["status"] in ACTIVE_SIGNAL_STATUSES]

    def summary(self, *, now_utc: str | None = None) -> dict[str, Any]:
        signals = self.load_signals() if now_utc is None else self.expire_signals(now_utc=now_utc)
        history = self.load_history()
        active = [item for item in signals if item["status"] in ACTIVE_SIGNAL_STATUSES]
        by_kind: dict[str, dict[str, int]] = {}
        for item in signals:
            kind = str(item["signal_kind"])
            kind_bucket = by_kind.setdefault(kind, {"active": 0, "resolved": 0, "expired": 0, "other": 0})
            if item["status"] in ACTIVE_SIGNAL_STATUSES:
                kind_bucket["active"] += 1
            elif item["status"] == "resolved":
                kind_bucket["resolved"] += 1
            elif item["status"] == "expired":
                kind_bucket["expired"] += 1
            else:
                kind_bucket["other"] += 1
        return {
            "signal_count": len(signals),
            "active_signal_count": len(active),
            "resolved_signal_count": len([item for item in signals if item["status"] == "resolved"]),
            "expired_signal_count": len([item for item in signals if item["status"] == "expired"]),
            "traceable_resolution_count": len([item for item in signals if item.get("resolution_ref")]),
            "history_entry_count": len(history),
            "active_signals": active,
            "by_kind": by_kind,
            "latest_signal_ref": None if len(signals) == 0 else signals[-1]["need_signal_id"],
        }

    def _normalize_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        normalized = ensure_need_signal(signal, action="record")
        normalized["severity"] = clamp_score(float(normalized["severity"]) * self.kind_weights[normalized["signal_kind"]])
        return normalized

    def _make_signal(
        self,
        *,
        signal_kind: str,
        source_type: str,
        source_id: str,
        severity: float,
        evidence_ref: str,
        proposed_action: str,
        created_utc: str,
        expires_at_utc: str,
    ) -> dict[str, Any]:
        return {
            "need_signal_id": "pending",
            "source_type": source_type,
            "source_id": source_id,
            "signal_kind": signal_kind,
            "severity": clamp_score(severity),
            "evidence_ref": evidence_ref,
            "proposed_action": proposed_action,
            "status": "open",
            "expires_at_utc": expires_at_utc,
            "resolution_ref": None,
            "created_utc": created_utc,
        }

    def _append_history(
        self,
        history: dict[str, Any],
        *,
        need_signal_id: str,
        event: str,
        status: str,
        actor: str,
        resolution_ref: str | None,
        detail: str,
    ) -> None:
        history["entries"].append(
            {
                "entry_id": f"need_history_{len(history['entries']) + 1:05d}",
                "need_signal_id": need_signal_id,
                "event": event,
                "status": status,
                "actor": actor,
                "resolution_ref": resolution_ref,
                "detail": detail,
                "created_utc": utc_now_iso(),
            }
        )

    def _future_utc(self, base_utc: str, *, seconds: int) -> str:
        return (self._parse_utc(base_utc) + timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _parse_utc(self, value: str) -> datetime:
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)

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


def generated_with_ids(*, workflow_id: str, base_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for index, item in enumerate(base_signals, start=1):
        signal = deepcopy(item)
        signal["need_signal_id"] = f"need:{workflow_id}:{index:02d}:{signal['signal_kind']}"
        signals.append(signal)
    return signals
