"""Bounded need scoring for lifecycle and population pressure."""

from __future__ import annotations

from typing import Any

from intelligence.fabric.common import utc_now_iso


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
                "expires_at_utc": utc_now_iso(),
                "resolution_ref": None,
                "created_utc": utc_now_iso(),
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
                "expires_at_utc": utc_now_iso(),
                "resolution_ref": None,
                "created_utc": utc_now_iso(),
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
                "expires_at_utc": utc_now_iso(),
                "resolution_ref": None,
                "created_utc": utc_now_iso(),
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
                "expires_at_utc": utc_now_iso(),
                "resolution_ref": None,
                "created_utc": utc_now_iso(),
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
