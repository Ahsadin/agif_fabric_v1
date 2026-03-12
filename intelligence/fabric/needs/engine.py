"""Bounded need scoring skeleton adapted from the old background-agent patterns."""

from __future__ import annotations

from typing import Any

from intelligence.fabric.common import utc_now_iso


def score_foundation_needs(*, fabric_id: str, registered_blueprints: int, active_population_cap: int) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
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
    if active_population_cap <= registered_blueprints:
        signals.append(
            {
                "need_signal_id": f"{fabric_id}:overload-risk",
                "source_type": "fabric",
                "source_id": fabric_id,
                "signal_kind": "overload",
                "severity": 0.5,
                "evidence_ref": "phase3:population_caps",
                "proposed_action": "review_active_population_cap",
                "status": "open",
                "expires_at_utc": utc_now_iso(),
                "resolution_ref": None,
                "created_utc": utc_now_iso(),
            }
        )
    return {
        "signal_count": len(signals),
        "signals": signals,
    }

