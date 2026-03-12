"""Status and evidence metrics for the Phase 3 foundation."""

from __future__ import annotations

from typing import Any


def build_status_metrics(state: dict[str, Any]) -> dict[str, Any]:
    registered = int(state.get("registered_blueprint_count", 0))
    active_population = int(state.get("active_population", 0))
    ratio = 0.0 if registered == 0 else round(active_population / float(registered), 6)
    return {
        "registered_blueprint_count": registered,
        "active_population": active_population,
        "run_count": int(state.get("run_count", 0)),
        "active_to_registered_ratio": ratio,
    }

