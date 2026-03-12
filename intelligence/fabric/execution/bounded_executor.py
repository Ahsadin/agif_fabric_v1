"""Deterministic bounded executor adapted from the old reasoning-engine patterns."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from intelligence.fabric.common import FabricError, canonical_json_hash, ensure_non_empty_string


CONFIG_VERSION = "agif.fabric.phase3.executor.v1"
ENGINE_VERSION = "phase3"
MAX_STEPS = 4
MAX_STEP_TIMEOUT_MS = 200
GLOBAL_BUDGET_MS = 1000

STATUS_OK = "OK"
STATUS_TIMEOUT = "STEP_TIMEOUT"

STEP_IDS = (
    "validate_payload",
    "compute_workflow_id",
    "plan_registered_blueprints",
    "finalize_output",
)


@dataclass
class StepResult:
    payload: dict[str, Any]
    note: str


ExecutorStep = Callable[[dict[str, Any]], StepResult]


def get_default_executor_config() -> dict[str, Any]:
    return {
        "config_version": CONFIG_VERSION,
        "engine_version": ENGINE_VERSION,
        "steps": [
            {"id": "validate_payload", "timeout_ms": 100, "enabled": True},
            {"id": "compute_workflow_id", "timeout_ms": 100, "enabled": True},
            {"id": "plan_registered_blueprints", "timeout_ms": 100, "enabled": True},
            {"id": "finalize_output", "timeout_ms": 100, "enabled": True},
        ],
    }


def execute_foundation_workflow(
    *,
    workflow_payload: dict[str, Any],
    blueprints: list[dict[str, Any]],
    proof_domain: str,
) -> dict[str, Any]:
    config = get_default_executor_config()
    current_payload: dict[str, Any] = {
        "workflow_payload": workflow_payload,
        "blueprints": blueprints,
        "proof_domain": proof_domain,
    }

    trace: list[dict[str, Any]] = []
    budget_used_ms = 0
    step_handlers: dict[str, ExecutorStep] = {
        "validate_payload": _validate_payload,
        "compute_workflow_id": _compute_workflow_id,
        "plan_registered_blueprints": _plan_registered_blueprints,
        "finalize_output": _finalize_output,
    }

    for step in config["steps"]:
        step_id = str(step["id"])
        if step_id not in STEP_IDS:
            raise FabricError("EXECUTION_INVALID", f"Unexpected executor step: {step_id}.")
        if budget_used_ms >= GLOBAL_BUDGET_MS:
            raise FabricError("LIMIT_EXCEEDED", "Global execution budget exceeded.")

        started = time.perf_counter()
        result = step_handlers[step_id](current_payload)
        duration_ms = max(0, int(round((time.perf_counter() - started) * 1000)))
        budget_used_ms += duration_ms

        if duration_ms > int(step["timeout_ms"]):
            raise FabricError("LIMIT_EXCEEDED", f"Execution step timed out: {step_id}.")

        current_payload = result.payload
        trace.append(
            {
                "step_id": step_id,
                "status": STATUS_OK,
                "duration_ms": duration_ms,
                "note": result.note,
            }
        )

    output = current_payload["result"]
    return {
        "executor": {
            "config_version": CONFIG_VERSION,
            "engine_version": ENGINE_VERSION,
            "global_budget_ms": GLOBAL_BUDGET_MS,
            "budget_used_ms": budget_used_ms,
        },
        "workflow_id": current_payload["workflow_id"],
        "output_digest": canonical_json_hash(output),
        "trace": trace,
        "result": output,
    }


def _validate_payload(payload: dict[str, Any]) -> StepResult:
    workflow_payload = payload["workflow_payload"]
    if not isinstance(workflow_payload, dict):
        raise FabricError("INPUT_INVALID_JSON", "Workflow payload must be a JSON object.")

    workflow_name_raw = workflow_payload.get("workflow_name", "document_workflow")
    workflow_name = ensure_non_empty_string(workflow_name_raw, "workflow_name", code="INPUT_INVALID_JSON")
    normalized = dict(payload)
    normalized["workflow_payload"] = dict(workflow_payload)
    normalized["workflow_payload"]["workflow_name"] = workflow_name
    return StepResult(payload=normalized, note="workflow payload validated")


def _compute_workflow_id(payload: dict[str, Any]) -> StepResult:
    workflow_payload = payload["workflow_payload"]
    workflow_digest = canonical_json_hash(workflow_payload)
    normalized = dict(payload)
    normalized["input_digest"] = workflow_digest
    normalized["workflow_id"] = f"wf_{workflow_digest[:16]}"
    return StepResult(payload=normalized, note="workflow identity derived from canonical payload hash")


def _plan_registered_blueprints(payload: dict[str, Any]) -> StepResult:
    selected = [
        {
            "cell_id": item["cell_id"],
            "role_family": item["role_family"],
            "role_name": item["role_name"],
            "bundle_ref": item["bundle_ref"],
        }
        for item in sorted(payload["blueprints"], key=lambda entry: entry["cell_id"])
    ]
    normalized = dict(payload)
    normalized["selected_blueprints"] = selected
    return StepResult(payload=normalized, note="registered blueprints mapped into deterministic execution plan")


def _finalize_output(payload: dict[str, Any]) -> StepResult:
    workflow_payload = payload["workflow_payload"]
    result = {
        "accepted": True,
        "workflow_name": workflow_payload["workflow_name"],
        "document_id": workflow_payload.get("document_id"),
        "proof_domain": payload["proof_domain"],
        "input_digest": payload["input_digest"],
        "selected_cells": [item["cell_id"] for item in payload["selected_blueprints"]],
        "selected_roles": [item["role_name"] for item in payload["selected_blueprints"]],
        "payload_keys": sorted(workflow_payload.keys()),
    }
    normalized = dict(payload)
    normalized["result"] = result
    return StepResult(payload=normalized, note="bounded foundation output finalized")

