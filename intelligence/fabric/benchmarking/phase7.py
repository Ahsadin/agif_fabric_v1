"""Deterministic Phase 7 benchmark harness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from intelligence.fabric.common import utc_now_iso
from intelligence.fabric.domain.finance import run_flat_baseline_workflow
from intelligence.fabric.governance.authority import AuthorityEngine
from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.memory import FabricMemoryManager
from intelligence.fabric.needs.engine import NeedSignalManager
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.routing import RoutingEngine
from intelligence.fabric.state_store import FabricStateStore


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPO_ROOT / "runner" / "cell"
SUITE_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "benchmark_suite.json"
NO_ADAPT_CONFIG = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "minimal_fabric_config_no_adaptation.json"
WITH_ADAPT_CONFIG = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "minimal_fabric_config_with_adaptation.json"


def run_phase7_benchmarks() -> dict[str, Any]:
    suite = _load_suite()
    baseline_pass_one = _run_flat_suite(suite)
    baseline_pass_two = _run_flat_suite(suite)
    no_adapt_pass_one = _run_fabric_suite(config_path=NO_ADAPT_CONFIG, suite=suite)
    no_adapt_pass_two = _run_fabric_suite(config_path=NO_ADAPT_CONFIG, suite=suite)
    with_adapt_pass_one = _run_fabric_suite(config_path=WITH_ADAPT_CONFIG, suite=suite)
    with_adapt_pass_two = _run_fabric_suite(config_path=WITH_ADAPT_CONFIG, suite=suite)
    cold_followup = _run_fabric_single_case(
        config_path=WITH_ADAPT_CONFIG,
        case_spec=_followup_case(suite),
    )

    baseline_summary = _summarize_flat_runs(
        suite=suite,
        pass_one=baseline_pass_one,
        pass_two=baseline_pass_two,
    )
    no_adapt_summary = _summarize_fabric_runs(
        suite=suite,
        config_path=NO_ADAPT_CONFIG,
        pass_one=no_adapt_pass_one,
        pass_two=no_adapt_pass_two,
        cold_followup_score=None,
    )
    with_adapt_summary = _summarize_fabric_runs(
        suite=suite,
        config_path=WITH_ADAPT_CONFIG,
        pass_one=with_adapt_pass_one,
        pass_two=with_adapt_pass_two,
        cold_followup_score=float(cold_followup["case_score"]),
    )

    comparison_rows = []
    descriptor_change_cases: list[str] = []
    fabric_beats_baseline_cases: list[str] = []
    for index, case_spec in enumerate(suite["cases"]):
        baseline_case = baseline_summary["case_results"][index]
        no_adapt_case = no_adapt_summary["case_results"][index]
        with_adapt_case = with_adapt_summary["case_results"][index]
        comparison_rows.append(
            {
                "case_id": case_spec["case_id"],
                "flat_baseline_score": baseline_case["correctness_score"],
                "multi_cell_no_adapt_score": no_adapt_case["correctness_score"],
                "multi_cell_with_adapt_score": with_adapt_case["correctness_score"],
                "with_adapt_descriptor_reuse": bool(with_adapt_case["descriptor_reuse"]["used"]),
            }
        )
        if (
            max(no_adapt_case["correctness_score"], with_adapt_case["correctness_score"])
            > baseline_case["correctness_score"]
        ):
            fabric_beats_baseline_cases.append(str(case_spec["case_id"]))
        if (
            bool(case_spec.get("descriptor_opportunity"))
            and bool(with_adapt_case["descriptor_reuse"]["used"])
            and with_adapt_case["correctness_score"] > no_adapt_case["correctness_score"]
        ):
            descriptor_change_cases.append(str(case_spec["case_id"]))

    return {
        "suite_id": suite["suite_id"],
        "created_utc": utc_now_iso(),
        "classes": {
            "flat_baseline": baseline_summary,
            "multi_cell_without_bounded_adaptation": no_adapt_summary,
            "multi_cell_with_bounded_adaptation": with_adapt_summary,
        },
        "comparisons": {
            "case_rows": comparison_rows,
            "fabric_beats_baseline_cases": fabric_beats_baseline_cases,
            "descriptor_change_cases": descriptor_change_cases,
            "usefulness_gate_passed": bool(fabric_beats_baseline_cases) and bool(descriptor_change_cases),
        },
    }


def write_phase7_result_tables(results: dict[str, Any], *, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "phase7_benchmark_results.json"
    markdown_path = output_dir / "phase7_benchmark_results.md"
    json_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    class_rows = []
    for class_name, payload in results["classes"].items():
        class_rows.append(
            "| "
            + " | ".join(
                [
                    class_name,
                    f"{payload['metrics']['task_accuracy']:.3f}",
                    f"{payload['metrics']['replay_determinism']:.3f}",
                    f"{payload['metrics']['descriptor_reuse_rate']:.3f}",
                    f"{payload['metrics']['governance_success_rate']:.3f}",
                    f"{payload['metrics']['unsafe_action_rate']:.3f}",
                ]
            )
            + " |"
        )
    case_rows = []
    for row in results["comparisons"]["case_rows"]:
        case_rows.append(
            "| "
            + " | ".join(
                [
                    row["case_id"],
                    f"{row['flat_baseline_score']:.3f}",
                    f"{row['multi_cell_no_adapt_score']:.3f}",
                    f"{row['multi_cell_with_adapt_score']:.3f}",
                    "yes" if row["with_adapt_descriptor_reuse"] else "no",
                ]
            )
            + " |"
        )
    markdown = "\n".join(
        [
            "# Phase 7 Benchmark Results",
            "",
            f"- Generated UTC: `{results['created_utc']}`",
            "",
            "## Class Metrics",
            "",
            "| Benchmark class | Accuracy | Replay determinism | Descriptor reuse | Governance success | Unsafe rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            *class_rows,
            "",
            "## Case Comparison",
            "",
            "| Case | Flat baseline | Multi-cell no adapt | Multi-cell with adapt | Descriptor reuse mattered |",
            "| --- | ---: | ---: | ---: | --- |",
            *case_rows,
            "",
            f"- Fabric beats baseline cases: `{', '.join(results['comparisons']['fabric_beats_baseline_cases'])}`",
            f"- Descriptor-change cases: `{', '.join(results['comparisons']['descriptor_change_cases'])}`",
        ]
    )
    markdown_path.write_text(markdown + "\n", encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _load_suite() -> dict[str, Any]:
    payload = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    payload["cases"] = [
        {
            **case_spec,
            "payload": json.loads((SUITE_PATH.parent / case_spec["payload_path"]).read_text(encoding="utf-8")),
        }
        for case_spec in payload["cases"]
    ]
    return payload


def _followup_case(suite: dict[str, Any]) -> dict[str, Any]:
    for case_spec in suite["cases"]:
        if bool(case_spec.get("descriptor_opportunity")):
            return case_spec
    raise RuntimeError("Phase 7 suite is missing a descriptor opportunity case.")


def _run_flat_suite(suite: dict[str, Any]) -> dict[str, Any]:
    case_results = []
    digests = []
    for case_spec in suite["cases"]:
        execution = run_flat_baseline_workflow(
            workflow_payload=case_spec["payload"],
            proof_domain="document/workflow intelligence",
        )
        result = execution["result"]
        score = _score_result(result=result, truth=case_spec["truth"])
        case_results.append(
            {
                "case_id": case_spec["case_id"],
                "result": result,
                "correctness_score": score,
                "output_digest": execution["output_digest"],
                "descriptor_reuse": deepcopy(result["descriptor_reuse"]),
            }
        )
        digests.append(str(execution["output_digest"]))
    forgetting_probe = run_flat_baseline_workflow(
        workflow_payload=suite["cases"][0]["payload"],
        proof_domain="document/workflow intelligence",
    )
    forgetting_score = _score_result(result=forgetting_probe["result"], truth=suite["cases"][0]["truth"])
    return {
        "case_results": case_results,
        "digests": digests,
        "forgetting_probe_score": forgetting_score,
    }


def _run_fabric_suite(*, config_path: Path, suite: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        state_root = Path(tempdir) / "runtime_state"
        env = os.environ.copy()
        env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)
        _run_cli(env=env, args=["fabric", "init", str(config_path)])
        case_results = []
        digests = []
        for case_spec in suite["cases"]:
            payload = _run_cli(
                env=env,
                args=["fabric", "run"],
                stdin_text=json.dumps(case_spec["payload"]),
            )
            result = payload["data"]["result"]
            score = _score_result(result=result, truth=case_spec["truth"])
            case_results.append(
                {
                    "case_id": case_spec["case_id"],
                    "result": result,
                    "correctness_score": score,
                    "output_digest": str(payload["data"]["output_digest"]),
                    "descriptor_reuse": deepcopy(result["descriptor_reuse"]),
                }
            )
            digests.append(str(payload["data"]["output_digest"]))
        forgetting_probe_payload = _run_cli(
            env=env,
            args=["fabric", "run"],
            stdin_text=json.dumps(suite["cases"][0]["payload"]),
        )
        forgetting_probe_score = _score_result(
            result=forgetting_probe_payload["data"]["result"],
            truth=suite["cases"][0]["truth"],
        )
        context = _load_runtime_context(config_path=config_path, state_root=state_root)
        lifecycle = context["lifecycle"]
        memory = context["memory"]
        need_manager = context["need_manager"]
        authority = context["authority_engine"]
        routing = context["routing_engine"]
        status_payload = _run_cli(env=env, args=["fabric", "status"])
        evidence_path = Path(tempdir) / "phase7_evidence.json"
        _run_cli(env=env, args=["fabric", "evidence", str(evidence_path)])
        return {
            "case_results": case_results,
            "digests": digests,
            "forgetting_probe_score": forgetting_probe_score,
            "status": status_payload["data"],
            "population": lifecycle.summary(),
            "memory_summary": memory.summary(),
            "need_summary": need_manager.summary(),
            "authority_summary": authority.summary(),
            "routing_summary": routing.summary(),
            "evidence_path": evidence_path,
        }


def _run_fabric_single_case(*, config_path: Path, case_spec: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tempdir:
        state_root = Path(tempdir) / "runtime_state"
        env = os.environ.copy()
        env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)
        _run_cli(env=env, args=["fabric", "init", str(config_path)])
        payload = _run_cli(
            env=env,
            args=["fabric", "run"],
            stdin_text=json.dumps(case_spec["payload"]),
        )
        return {
            "case_score": _score_result(result=payload["data"]["result"], truth=case_spec["truth"]),
            "output_digest": str(payload["data"]["output_digest"]),
        }


def _summarize_flat_runs(
    *,
    suite: dict[str, Any],
    pass_one: dict[str, Any],
    pass_two: dict[str, Any],
) -> dict[str, Any]:
    case_results = pass_one["case_results"]
    scores = [float(item["correctness_score"]) for item in case_results]
    replay_determinism = _digest_match_rate(pass_one["digests"], pass_two["digests"])
    unsafe_rate = _unsafe_rate(case_results, suite["cases"])
    governance_rate = _governance_success_rate(case_results, suite["cases"])
    return {
        "case_results": case_results,
        "metrics": {
            "task_accuracy": _average(scores),
            "replay_determinism": replay_determinism,
            "descriptor_reuse_rate": 0.0,
            "improvement_from_prior_descriptors": 0.0,
            "memory_density_gain": 0.0,
            "active_logical_population_ratio": 0.0,
            "split_merge_efficiency": {
                "measured": False,
                "value": 0.0,
                "detail": "flat baseline has no split or merge path",
            },
            "governance_success_rate": governance_rate,
            "resource_usage": {
                "estimated_runtime_memory_bytes": 0,
                "memory_tier_usage_bytes": {"hot": 0, "warm": 0, "cold": 0, "ephemeral": 0},
            },
            "bounded_forgetting": 0.0,
            "unsafe_action_rate": unsafe_rate,
        },
    }


def _summarize_fabric_runs(
    *,
    suite: dict[str, Any],
    config_path: Path,
    pass_one: dict[str, Any],
    pass_two: dict[str, Any],
    cold_followup_score: float | None,
) -> dict[str, Any]:
    case_results = pass_one["case_results"]
    scores = [float(item["correctness_score"]) for item in case_results]
    eligible_cases = [
        item for item in case_results if bool(item["descriptor_reuse"]["eligible"])
    ]
    used_cases = [item for item in eligible_cases if bool(item["descriptor_reuse"]["used"])]
    followup_case = _followup_case(suite)
    warmed_followup = next(item for item in case_results if item["case_id"] == followup_case["case_id"])
    forgetting_loss = max(0.0, case_results[0]["correctness_score"] - pass_one["forgetting_probe_score"])
    population = pass_one["population"]
    memory_summary = pass_one["memory_summary"]
    structural = population.get("structural_usefulness", {})
    split_merge_events = int(structural.get("split_useful_count", 0)) + int(structural.get("merge_useful_count", 0))
    return {
        "case_results": case_results,
        "metrics": {
            "task_accuracy": _average(scores),
            "replay_determinism": _digest_match_rate(pass_one["digests"], pass_two["digests"]),
            "descriptor_reuse_rate": 0.0
            if len(eligible_cases) == 0
            else round(len(used_cases) / float(len(eligible_cases)), 6),
            "improvement_from_prior_descriptors": 0.0
            if cold_followup_score is None
            else round(float(warmed_followup["correctness_score"]) - float(cold_followup_score), 6),
            "memory_density_gain": round(
                sum(scores)
                / float(
                    max(
                        1,
                        int(memory_summary["tier_usage_bytes"]["warm"]) + int(memory_summary["tier_usage_bytes"]["cold"]),
                    )
                ),
                9,
            ),
            "active_logical_population_ratio": float(population.get("active_to_logical_ratio", 0.0)),
            "split_merge_efficiency": {
                "measured": split_merge_events > 0,
                "value": 0.0 if split_merge_events == 0 else round(split_merge_events / float(len(case_results)), 6),
                "detail": "placeholder metric uses lifecycle structural counters because Phase 7 did not trigger a benchmarked split or merge event"
                if split_merge_events == 0
                else "measured from lifecycle structural counters",
            },
            "governance_success_rate": _governance_success_rate(case_results, suite["cases"]),
            "resource_usage": {
                "estimated_runtime_memory_bytes": int(population.get("estimated_runtime_memory_bytes", 0)),
                "memory_tier_usage_bytes": deepcopy(memory_summary["tier_usage_bytes"]),
            },
            "bounded_forgetting": round(forgetting_loss, 6),
            "unsafe_action_rate": _unsafe_rate(case_results, suite["cases"]),
        },
        "status_refs": {
            "config_path": str(config_path),
            "evidence_path": str(pass_one["evidence_path"]),
        },
    }


def _governance_success_rate(case_results: list[dict[str, Any]], suite_cases: list[dict[str, Any]]) -> float:
    matches = 0
    for result_item, case_spec in zip(case_results, suite_cases):
        if str(result_item["result"].get("governance_action")) == str(case_spec["expected_governance"]):
            matches += 1
    return round(matches / float(len(case_results)), 6)


def _unsafe_rate(case_results: list[dict[str, Any]], suite_cases: list[dict[str, Any]]) -> float:
    unsafe = 0
    for result_item, case_spec in zip(case_results, suite_cases):
        truth_final = str(case_spec["truth"]["final_status"])
        observed_final = str(result_item["result"].get("final_status"))
        if truth_final == "hold" and observed_final == "accepted":
            unsafe += 1
    return round(unsafe / float(len(case_results)), 6)


def _score_result(*, result: dict[str, Any], truth: dict[str, Any]) -> float:
    matched = 0
    for field_name, truth_value in truth.items():
        if str(result.get(field_name, "")) == str(truth_value):
            matched += 1
    return round(matched / float(len(truth)), 6)


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / float(len(values)), 6)


def _digest_match_rate(left: list[str], right: list[str]) -> float:
    if len(left) != len(right) or len(left) == 0:
        return 0.0
    matches = len([1 for l_item, r_item in zip(left, right) if str(l_item) == str(r_item)])
    return round(matches / float(len(left)), 6)


def _load_runtime_context(*, config_path: Path, state_root: Path) -> dict[str, Any]:
    config, _, registry, _ = load_fabric_bootstrap(config_path)
    store = FabricStateStore(state_root)
    state = store.load_current_state()
    if state is None:
        raise RuntimeError("Fabric state was not initialized.")
    lifecycle = FabricLifecycleManager(
        store=store,
        state=state,
        config=config,
        utility_profiles=registry["utility_profiles"],
    )
    memory = FabricMemoryManager(store=store, state=state, config=config)
    need_manager = NeedSignalManager(store=store, state=state, config=config)
    authority_engine = AuthorityEngine(store=store, state=state, config=config)
    routing_engine = RoutingEngine(store=store, state=state, config=config, registry=registry)
    return {
        "config": config,
        "registry": registry,
        "store": store,
        "state": state,
        "lifecycle": lifecycle,
        "memory": memory,
        "need_manager": need_manager,
        "authority_engine": authority_engine,
        "routing_engine": routing_engine,
    }


def _run_cli(
    *,
    env: dict[str, str],
    args: list[str],
    stdin_text: str | None = None,
) -> dict[str, Any]:
    result = subprocess.run(
        [str(RUNNER)] + args,
        cwd=str(REPO_ROOT),
        env=env,
        input=stdin_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip() == "":
        raise RuntimeError(f"CLI wrote no stdout for args={args}. stderr={result.stderr}")
    payload = json.loads(result.stdout)
    if result.returncode != 0 or not payload.get("ok", False):
        raise RuntimeError(f"CLI failed for args={args}: {result.stdout}\n{result.stderr}")
    return payload


def deepcopy(value: Any) -> Any:
    return json.loads(json.dumps(value))
