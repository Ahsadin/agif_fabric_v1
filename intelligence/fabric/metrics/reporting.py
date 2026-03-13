"""Status and evidence metrics for the fabric runtime."""

from __future__ import annotations

from typing import Any


def build_status_metrics(state: dict[str, Any]) -> dict[str, Any]:
    registered = int(state.get("registered_blueprint_count", 0))
    logical_population = int(state.get("logical_population", registered))
    active_population = int(state.get("active_population", 0))
    ratio = 0.0 if logical_population == 0 else round(active_population / float(logical_population), 6)
    return {
        "registered_blueprint_count": registered,
        "logical_population": logical_population,
        "active_population": active_population,
        "dormant_population": int(state.get("dormant_population", 0)),
        "retired_population": int(state.get("retired_population", 0)),
        "run_count": int(state.get("run_count", 0)),
        "steady_active_population_target": int(state.get("steady_active_population_target", state.get("active_population_cap", 0))),
        "burst_active_population_cap": int(state.get("burst_active_population_cap", state.get("active_population_cap", 0))),
        "lineage_count": int(state.get("lineage_count", 0)),
        "lifecycle_event_count": int(state.get("lifecycle_event_count", 0)),
        "last_lifecycle_event_ref": state.get("last_lifecycle_event_ref"),
        "active_to_logical_ratio": ratio,
    }
