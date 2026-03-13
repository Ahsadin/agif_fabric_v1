"""Deterministic tests for Phase 6 need signals, routing, utility, and authority."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.common import FabricError
from intelligence.fabric.governance.authority import AuthorityEngine
from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.memory import FabricMemoryManager
from intelligence.fabric.needs.engine import NeedSignalManager
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.routing import RoutingEngine
from intelligence.fabric.state_store import FabricStateStore


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "runner" / "cell"
CONFIG_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "minimal_fabric_config.json"
SCENARIO_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "routing_authority_scenario.json"
STANDARD_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "sample_workflow_payload_standard.json"
PRIORITY_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "sample_workflow_payload_priority.json"
UNCERTAIN_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "sample_workflow_payload_uncertain.json"
LOW_TRUST_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase6" / "sample_workflow_payload_low_trust.json"


class Phase6RoutingAuthorityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.state_root = Path(self.tempdir.name) / "runtime_state"
        self.env = os.environ.copy()
        self.env["AGIF_FABRIC_STATE_ROOT"] = str(self.state_root)
        self.scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def run_cli(self, args: list[str], *, stdin_text: str | None = None, expect_ok: bool = True) -> dict:
        result = subprocess.run(
            [str(RUNNER)] + args,
            cwd=str(REPO_ROOT),
            env=self.env,
            input=stdin_text,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.stdout.strip(), "", "CLI must always write bounded JSON to stdout.")
        payload = json.loads(result.stdout)
        if expect_ok:
            self.assertEqual(result.returncode, 0, msg=result.stdout)
            self.assertTrue(payload["ok"], msg=result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, msg=result.stdout)
            self.assertFalse(payload["ok"], msg=result.stdout)
        return payload

    def init_runtime(
        self,
    ) -> tuple[
        dict,
        dict,
        dict,
        FabricStateStore,
        FabricLifecycleManager,
        FabricMemoryManager,
        NeedSignalManager,
        AuthorityEngine,
        RoutingEngine,
    ]:
        config, _, registry, _ = load_fabric_bootstrap(CONFIG_PATH)
        store = FabricStateStore(self.state_root)
        state = store.load_current_state()
        self.assertIsNotNone(state)
        lifecycle = FabricLifecycleManager(
            store=store,
            state=state,
            config=config,
            utility_profiles=registry["utility_profiles"],
        )
        memory = FabricMemoryManager(store=store, state=state, config=config)
        need_manager = NeedSignalManager(store=store, state=state, config=config)
        authority_engine = AuthorityEngine(store=store, state=state, config=config)
        routing = RoutingEngine(store=store, state=state, config=config, registry=registry)
        return state, config, registry, store, lifecycle, memory, need_manager, authority_engine, routing

    def make_signal(self, kind: str, signal_id: str) -> dict:
        template = dict(self.scenario["signals"][kind])
        template["need_signal_id"] = signal_id
        return template

    def promote_routing_memory(
        self,
        *,
        memory: FabricMemoryManager,
        payload_path: Path,
        producer_cell_id: str,
        trust_ref: str = "trust:bounded_local_v1",
        authority_engine: AuthorityEngine | None = None,
    ) -> dict:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        candidate = memory.nominate_candidate(
            payload={
                "workflow_name": payload["workflow_name"],
                "document_id": payload["document_id"],
                "inputs": payload["inputs"],
                "selected_cells": [producer_cell_id],
                "selected_roles": [producer_cell_id],
                "source_run_ref": "fixture:phase6",
                "source_workspace_ref": "fixture:phase6",
                "source_log_refs": [],
            },
            source_ref="fixture:phase6",
            source_log_refs=[],
            producer_cell_id=producer_cell_id,
            descriptor_kind="workflow_intake",
            task_scope=f"{payload['workflow_name']}:{payload['document_id']}",
            trust_ref=trust_ref,
        )
        return memory.review_candidate(
            candidate_id=candidate["candidate_id"],
            reviewer_id="governance:phase5_memory_reviewer",
            decision="promote",
            compression_mode="quantized_summary_v1",
            retention_tier="warm",
            reason="phase6 promoted routing memory",
            authority_engine=authority_engine,
        )

    def route_payload(
        self,
        *,
        routing: RoutingEngine,
        need_manager: NeedSignalManager,
        authority_engine: AuthorityEngine,
        memory: FabricMemoryManager,
        workflow_id: str,
        payload_path: Path,
    ) -> dict:
        return routing.route_workflow(
            workflow_id=workflow_id,
            workflow_payload=json.loads(payload_path.read_text(encoding="utf-8")),
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory_manager=memory,
        )

    def write_manifest(self, *, payload_path: Path, name: str) -> Path:
        manifest_path = Path(self.tempdir.name) / f"{name}.manifest.json"
        manifest_path.write_text(json.dumps({"workflow_payload_path": str(payload_path)}, indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def test_need_signal_generation_expiry_and_resolution(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        _, _, _, _, _, memory, need_manager, authority_engine, routing = self.init_runtime()

        need_manager.record_signal(signal=self.make_signal("expired_coordination", "need-expired-001"))
        need_manager.expire_signals(now_utc="2026-03-13T02:00:00Z")

        decision = self.route_payload(
            routing=routing,
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory=memory,
            workflow_id="wf_phase6_need",
            payload_path=UNCERTAIN_PAYLOAD_PATH,
        )
        summary = need_manager.summary(now_utc="2026-03-13T02:00:00Z")
        signals = {item["need_signal_id"]: item for item in need_manager.load_signals()}

        self.assertTrue(any(item["signal_kind"] == "uncertainty" for item in signals.values()))
        self.assertGreaterEqual(summary["expired_signal_count"], 1)
        self.assertGreaterEqual(summary["traceable_resolution_count"], 1)
        self.assertNotIn("need-expired-001", [item["need_signal_id"] for item in summary["active_signals"]])
        self.assertTrue(any(item["status"] == "resolved" for item in signals.values()))
        self.assertGreater(summary["history_entry_count"], summary["signal_count"])

    def test_utility_scoring_and_descriptor_usefulness_change_routing_choice(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        _, _, _, _, lifecycle, memory, need_manager, authority_engine, routing = self.init_runtime()

        before = self.route_payload(
            routing=routing,
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory=memory,
            workflow_id="wf_phase6_before",
            payload_path=STANDARD_PAYLOAD_PATH,
        )
        before_scores = {item["cell_id"]: item for item in before["candidate_scores"]}
        baseline_router = next(cell_id for cell_id in before["selected_cells"] if "router" in cell_id)

        self.promote_routing_memory(
            memory=memory,
            payload_path=STANDARD_PAYLOAD_PATH,
            producer_cell_id="finance_priority_router",
            authority_engine=authority_engine,
        )

        after = self.route_payload(
            routing=routing,
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory=memory,
            workflow_id="wf_phase6_after",
            payload_path=STANDARD_PAYLOAD_PATH,
        )
        after_scores = {item["cell_id"]: item for item in after["candidate_scores"]}
        chosen_router = next(cell_id for cell_id in after["selected_cells"] if "router" in cell_id)

        self.assertEqual(baseline_router, "finance_intake_router")
        self.assertEqual(chosen_router, "finance_priority_router")
        self.assertGreater(
            after_scores["finance_priority_router"]["descriptor_usefulness"],
            before_scores["finance_priority_router"]["descriptor_usefulness"],
        )
        self.assertGreater(
            after_scores["finance_priority_router"]["total_score"],
            after_scores["finance_low_trust_router"]["total_score"],
        )

        runtime_path = self.state_root / "agif-fabric-v1-local" / "lifecycle" / "runtime_states.json"
        runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime_payload["states"]["finance_low_trust_router"]["runtime_state"] = "active"
        runtime_payload["states"]["finance_low_trust_router"]["active_task_ref"] = None
        runtime_payload["states"]["finance_priority_router"]["current_need_signals"] = ["need-reactivate-001", "need-reactivate-002"]
        runtime_path.write_text(json.dumps(runtime_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        choices = lifecycle.evaluate_runtime_choices()
        choice_map = {item["cell_id"]: item for item in choices["evaluations"]}
        self.assertEqual(choice_map["finance_low_trust_router"]["recommended_action"], "hibernate")
        self.assertEqual(choice_map["finance_priority_router"]["recommended_action"], "reactivate")

    def test_authority_veto_and_quarantine_paths(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        _, _, _, _, lifecycle, memory, need_manager, authority_engine, routing = self.init_runtime()

        self.promote_routing_memory(
            memory=memory,
            payload_path=LOW_TRUST_PAYLOAD_PATH,
            producer_cell_id="finance_low_trust_router",
            trust_ref="trust:experimental_low_v1",
            authority_engine=None,
        )
        decision = self.route_payload(
            routing=routing,
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory=memory,
            workflow_id="wf_phase6_low_trust",
            payload_path=LOW_TRUST_PAYLOAD_PATH,
        )
        score_map = {item["cell_id"]: item for item in decision["candidate_scores"]}
        self.assertGreater(score_map["finance_low_trust_router"]["authority_penalty"], 0.0)
        self.assertEqual(score_map["finance_low_trust_router"]["descriptor_usefulness"], 0.0)
        self.assertGreaterEqual(authority_engine.summary()["veto_count"], 1)

        with self.assertRaises(FabricError) as err:
            lifecycle.activate_cell(
                cell_id="finance_low_trust_router",
                proposer=self.scenario["actors"]["proposer"],
                governance_approver=self.scenario["actors"]["governance_approver"],
                reason="reactivate risky experimental router",
                need_signal=self.make_signal("trust_risk", "need-reactivate-veto-001"),
                authority_engine=authority_engine,
            )
        self.assertEqual(err.exception.code, "AUTHORITY_REACTIVATION_VETO")

        lifecycle.activate_cell(
            cell_id="finance_low_trust_router",
            proposer=self.scenario["actors"]["proposer"],
            reason="activate experimental router for quarantine review",
        )
        quarantine = lifecycle.quarantine_cell(
            cell_id="finance_low_trust_router",
            proposer=self.scenario["actors"]["proposer"],
            governance_approver=self.scenario["actors"]["governance_approver"],
            need_signal=self.make_signal("trust_risk", "need-quarantine-001"),
            reason="quarantine experimental router after trust-risk review",
            authority_engine=authority_engine,
        )
        self.assertEqual(lifecycle.get_runtime_state("finance_low_trust_router")["runtime_state"], "quarantined")
        history = json.loads(
            (self.state_root / "agif-fabric-v1-local" / "lifecycle" / "history.json").read_text(encoding="utf-8")
        )
        quarantine_entry = next(entry for entry in history["entries"] if entry["event"]["event_id"] == quarantine["event_id"])
        self.assertTrue(quarantine_entry["event"]["rollback_ref"])
        self.assertEqual(quarantine_entry["details"]["kind"], "quarantine_escalation")
        self.assertTrue(quarantine_entry["details"]["authority_review_id"])

    def test_phase6_trace_and_evidence_pass(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        self.run_cli(["fabric", "run"], stdin_text=STANDARD_PAYLOAD_PATH.read_text(encoding="utf-8"))
        self.run_cli(["fabric", "replay", str(self.write_manifest(payload_path=STANDARD_PAYLOAD_PATH, name="phase6-replay"))])

        _, _, _, _, lifecycle, memory, need_manager, authority_engine, routing = self.init_runtime()
        need_manager.record_signal(signal=self.make_signal("expired_coordination", "need-expired-evidence-001"))
        need_manager.expire_signals(now_utc="2026-03-13T02:00:00Z")

        self.promote_routing_memory(
            memory=memory,
            payload_path=STANDARD_PAYLOAD_PATH,
            producer_cell_id="finance_priority_router",
            authority_engine=authority_engine,
        )
        self.promote_routing_memory(
            memory=memory,
            payload_path=LOW_TRUST_PAYLOAD_PATH,
            producer_cell_id="finance_low_trust_router",
            trust_ref="trust:experimental_low_v1",
            authority_engine=None,
        )
        self.route_payload(
            routing=routing,
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory=memory,
            workflow_id="wf_phase6_priority",
            payload_path=PRIORITY_PAYLOAD_PATH,
        )
        self.route_payload(
            routing=routing,
            need_manager=need_manager,
            authority_engine=authority_engine,
            memory=memory,
            workflow_id="wf_phase6_low_trust_evidence",
            payload_path=LOW_TRUST_PAYLOAD_PATH,
        )

        if lifecycle.get_runtime_state("finance_intake_router")["runtime_state"] == "dormant":
            lifecycle.activate_cell(
                cell_id="finance_intake_router",
                proposer=self.scenario["actors"]["proposer"],
                reason="activate intake router before governed split",
            )
        split_result = lifecycle.split_cell(
            parent_cell_id="finance_intake_router",
            child_role_names=["intake_router_alpha", "intake_router_beta"],
            proposer=self.scenario["actors"]["proposer"],
            governance_approver=self.scenario["actors"]["governance_approver"],
            need_signal=self.make_signal("split", "need-phase6-split-001"),
            reason="governed split for phase6 trace evidence",
            authority_engine=authority_engine,
        )
        history_payload = json.loads(
            (self.state_root / "agif-fabric-v1-local" / "lifecycle" / "history.json").read_text(encoding="utf-8")
        )
        split_event = next(entry for entry in history_payload["entries"] if entry["event"]["event_id"] == split_result["event_id"])
        split_signal = next(item for item in need_manager.load_signals() if item["need_signal_id"] == "need-phase6-split-001")
        authority_review = next(
            item for item in authority_engine.load_reviews() if item["review_id"] == split_event["details"]["authority_review_id"]
        )

        self.assertEqual(split_event["details"]["need_signal_id"], "need-phase6-split-001")
        self.assertTrue(split_event["details"]["utility_evaluation"]["attractive"])
        self.assertEqual(split_signal["status"], "resolved")
        self.assertEqual(split_signal["resolution_ref"], split_result["event_id"])
        self.assertEqual(authority_review["action_ref"], split_result["event_id"])

        evidence_path = Path(self.tempdir.name) / "phase6_evidence.json"
        evidence_payload = self.run_cli(["fabric", "evidence", str(evidence_path)])
        self.assertIn("AGIF_FABRIC_P6_PASS", evidence_payload["data"]["earned_pass_tokens"])
        evidence_bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertIn("AGIF_FABRIC_P6_PASS", evidence_bundle["earned_pass_tokens"])
        self.assertGreaterEqual(evidence_bundle["phase6"]["routing_summary"]["decision_count"], 1)
        self.assertGreaterEqual(evidence_bundle["phase6"]["authority_summary"]["veto_count"], 1)
        self.assertGreaterEqual(evidence_bundle["phase6"]["need_summary"]["expired_signal_count"], 1)


if __name__ == "__main__":
    unittest.main()
