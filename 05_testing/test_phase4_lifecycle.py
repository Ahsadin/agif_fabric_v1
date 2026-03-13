"""Deterministic tests for AGIF Phase 4 lifecycle and lineage."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.common import FabricError
from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.state_store import FabricStateStore


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "runner" / "cell"
CONFIG_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase4" / "minimal_fabric_config.json"
WORKFLOW_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase4" / "sample_workflow_payload.json"
REPLAY_MANIFEST_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase4" / "sample_replay_manifest.json"
SCENARIO_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase4" / "lifecycle_scenario.json"


class Phase4LifecycleTest(unittest.TestCase):
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

    def init_runtime(self) -> tuple[dict, dict, dict, FabricStateStore, FabricLifecycleManager]:
        config, _, registry, _ = load_fabric_bootstrap(CONFIG_PATH)
        store = FabricStateStore(self.state_root)
        state = store.load_current_state()
        self.assertIsNotNone(state)
        manager = FabricLifecycleManager(store=store, state=state, config=config)
        return state, config, registry, store, manager

    def make_signal(self, kind: str, signal_id: str) -> dict:
        template = dict(self.scenario["signals"][kind])
        template["need_signal_id"] = signal_id
        return template

    def test_phase4_lifecycle_flow_and_replay(self) -> None:
        init_payload = self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        self.assertEqual(init_payload["data"]["population"]["logical_population"], 2)
        self.assertEqual(init_payload["data"]["population"]["active_population"], 0)

        status_payload = self.run_cli(["fabric", "status"])
        self.assertEqual(status_payload["data"]["population"]["steady_active_population_target"], 24)
        self.assertEqual(status_payload["data"]["population"]["burst_active_population_cap"], 48)

        run_payload = self.run_cli(["fabric", "run"], stdin_text=WORKFLOW_PAYLOAD_PATH.read_text(encoding="utf-8"))
        self.assertEqual(run_payload["data"]["result"]["workflow_name"], "finance_document_intake")
        self.assertEqual(run_payload["data"]["population"]["active_population"], 2)

        replay_payload = self.run_cli(["fabric", "replay", str(REPLAY_MANIFEST_PATH)])
        self.assertTrue(replay_payload["data"]["replay_match"])
        self.assertTrue(replay_payload["data"]["lifecycle_replay_match"])

        _, _, _, store, manager = self.init_runtime()
        actors = self.scenario["actors"]

        split_result = manager.split_cell(
            parent_cell_id="finance_intake_router",
            child_role_names=["intake_router_alpha", "intake_router_beta"],
            proposer=actors["proposer"],
            governance_approver=actors["governance_approver"],
            need_signal=self.make_signal("split", "need-split-001"),
            reason="approved overload split for deterministic fixture",
        )
        child_a, child_b = split_result["child_ids"]

        parent_record = manager.get_cell_record("finance_intake_router")
        child_record = manager.get_cell_record(child_a)
        child_runtime = manager.get_runtime_state(child_a)
        self.assertEqual(parent_record["lifecycle_state"], "dormant")
        self.assertEqual(child_record["lineage_id"], parent_record["lineage_id"])
        self.assertEqual(child_record["blueprint"]["role_family"], parent_record["blueprint"]["role_family"])
        self.assertEqual(child_record["trust_ancestry"], parent_record["trust_ancestry"])
        self.assertEqual(child_record["descriptor_eligibility"], parent_record["descriptor_eligibility"])
        self.assertEqual(child_record["policy_envelope"], parent_record["policy_envelope"])
        self.assertEqual(child_runtime["runtime_state"], "active")

        merge_result = manager.merge_cells(
            survivor_cell_id=child_a,
            merged_cell_id=child_b,
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            governance_approver=actors["governance_approver"],
            need_signal=self.make_signal("merge", "need-merge-001"),
            reason="approved conflict-aware merge for deterministic fixture",
        )
        self.assertEqual(merge_result["retired_cell_id"], child_b)
        self.assertEqual(manager.get_runtime_state(child_a)["runtime_state"], "dormant")
        self.assertEqual(manager.get_runtime_state(child_b)["runtime_state"], "retired")

        manager.activate_cell(
            cell_id=child_a,
            proposer=actors["proposer"],
            reason="reactivate merged survivor",
        )
        manager.hibernate_cell(
            cell_id=child_a,
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            reason="hibernate merged survivor",
        )
        manager.activate_cell(
            cell_id=child_a,
            proposer=actors["proposer"],
            reason="reactivate after hibernate",
        )
        manager.hibernate_cell(
            cell_id=child_a,
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            reason="hibernate before retirement",
        )
        retire_result = manager.retire_cell(
            cell_id=child_a,
            proposer=actors["proposer"],
            governance_approver=actors["governance_approver"],
            reason="retire dormant survivor while preserving lineage history",
        )
        self.assertEqual(retire_result["runtime_state"], "retired")

        replay_result = manager.replay_history()
        self.assertTrue(replay_result["replay_match"])
        summary = manager.summary()
        self.assertGreater(summary["logical_population"], summary["active_population"])
        self.assertTrue(summary["within_runtime_working_set_cap"])
        self.assertGreaterEqual(summary["structural_usefulness"]["split_useful_count"], 1)
        self.assertGreaterEqual(summary["structural_usefulness"]["merge_useful_count"], 1)
        self.assertIn(parent_record["lineage_id"], summary["lineage_usefulness"])
        self.assertGreaterEqual(summary["lineage_usefulness"][parent_record["lineage_id"]]["useful_split_count"], 1)

        history_path = store.lifecycle_history_path("agif-fabric-v1-local")
        self.assertTrue(history_path.exists())
        history_payload = json.loads(history_path.read_text(encoding="utf-8"))
        allowed_transitions = {
            "seed_to_dormant",
            "dormant_to_active",
            "active_to_split_pending",
            "split_pending_to_active_children",
            "active_to_consolidating",
            "consolidating_to_dormant",
            "active_to_quarantined",
            "quarantined_to_dormant",
            "dormant_to_retired",
        }
        for entry in history_payload["entries"]:
            event = entry["event"]
            self.assertTrue(event["proposer"])
            self.assertTrue(event["approver"])
            self.assertTrue(event["reason"])
            self.assertTrue(event["rollback_ref"])
            self.assertIn(event["transition"], allowed_transitions)
        split_commit = next(entry for entry in history_payload["entries"] if entry["details"].get("kind") == "split_commit")
        self.assertEqual(
            split_commit["details"]["usefulness_reason"],
            "split relieves sustained overload on the active branch",
        )
        merge_survivor = next(entry for entry in history_payload["entries"] if entry["details"].get("kind") == "merge_survivor")
        self.assertEqual(
            merge_survivor["details"]["usefulness_reason"],
            "merge removes real redundancy while keeping the surviving branch replay-safe",
        )

        evidence_path = Path(self.tempdir.name) / "phase4_evidence.json"
        evidence_payload = self.run_cli(["fabric", "evidence", str(evidence_path)])
        self.assertIn("AGIF_FABRIC_P4_PASS", evidence_payload["data"]["earned_pass_tokens"])
        evidence_bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertIn("AGIF_FABRIC_P4_PASS", evidence_bundle["earned_pass_tokens"])

        repeat_summary = self.run_deterministic_flow_again()
        self.assertEqual(summary["state_digest"], repeat_summary["state_digest"])

    def test_invalid_merge_fails_closed_with_veto(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        _, _, _, _, manager = self.init_runtime()
        actors = self.scenario["actors"]

        manager.activate_cell(cell_id="finance_intake_router", proposer=actors["proposer"], reason="activate intake router")
        manager.activate_cell(cell_id="finance_audit_reporter", proposer=actors["proposer"], reason="activate audit reporter")

        with self.assertRaises(FabricError) as err:
            manager.merge_cells(
                survivor_cell_id="finance_intake_router",
                merged_cell_id="finance_audit_reporter",
                proposer=actors["proposer"],
                tissue_approver=actors["tissue_approver"],
                governance_approver=actors["governance_approver"],
                need_signal=self.make_signal("merge", "need-merge-invalid"),
                reason="invalid cross-role merge should fail closed",
            )
        self.assertEqual(err.exception.code, "MERGE_SPECIALIZATION_RISK")
        veto_log = manager.load_veto_log()
        self.assertEqual(len(veto_log), 1)
        self.assertEqual(veto_log[0]["action"], "merge")
        self.assertEqual(veto_log[0]["code"], "MERGE_SPECIALIZATION_RISK")

    def test_split_guardrails_and_activation_thrashing(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        _, _, _, _, manager = self.init_runtime()
        actors = self.scenario["actors"]

        manager.activate_cell(cell_id="finance_intake_router", proposer=actors["proposer"], reason="activate intake router")
        with self.assertRaises(FabricError) as err:
            manager.split_cell(
                parent_cell_id="finance_intake_router",
                child_role_names=["router_alpha"],
                proposer=actors["proposer"],
                governance_approver=actors["governance_approver"],
                need_signal=self.make_signal("split_weak", "need-split-weak"),
                reason="weak split pressure should not be enough",
            )
        self.assertEqual(err.exception.code, "SPLIT_WEAK_PRESSURE")

        manager.hibernate_cell(
            cell_id="finance_intake_router",
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            reason="pack for compact dormancy",
        )
        manager.activate_cell(
            cell_id="finance_intake_router",
            proposer=actors["proposer"],
            reason="first reactivation stays allowed",
        )
        manager.hibernate_cell(
            cell_id="finance_intake_router",
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            reason="second compact dormancy step",
        )
        with self.assertRaises(FabricError) as thrash_err:
            manager.activate_cell(
                cell_id="finance_intake_router",
                proposer=actors["proposer"],
                reason="third immediate reactivation should be blocked as thrash",
            )
        self.assertEqual(thrash_err.exception.code, "LIFECYCLE_THRASH")
        self.assertGreaterEqual(manager.summary()["structural_usefulness"]["thrash_prevented_count"], 1)

    def test_dormancy_profile_preserves_needed_state_compactly(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        _, _, _, store, manager = self.init_runtime()
        actors = self.scenario["actors"]

        manager.activate_cell(
            cell_id="finance_intake_router",
            proposer=actors["proposer"],
            reason="activate intake router for dormancy compaction",
            workflow_ref="fixture:phase45-dormancy",
        )
        runtime_path = store.runtime_states_path("agif-fabric-v1-local")
        runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime_payload["states"]["finance_intake_router"]["workspace_subscriptions"] = ["workspace:finance"]
        runtime_payload["states"]["finance_intake_router"]["loaded_descriptor_refs"] = ["memory/warm/payloads/mem_fixture.json"]
        runtime_payload["states"]["finance_intake_router"]["current_need_signals"] = ["need-dormancy-001"]
        runtime_path.write_text(json.dumps(runtime_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        manager.hibernate_cell(
            cell_id="finance_intake_router",
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            reason="compact dormant state should preserve only what is needed",
        )
        dormant_runtime = manager.get_runtime_state("finance_intake_router")
        dormant_logical = manager.get_cell_record("finance_intake_router")
        self.assertEqual(dormant_runtime["workspace_subscriptions"], [])
        self.assertEqual(dormant_runtime["loaded_descriptor_refs"], [])
        self.assertEqual(dormant_runtime["current_need_signals"], [])
        self.assertEqual(dormant_logical["dormancy_profile"]["packed_workspace_subscriptions"], ["workspace:finance"])
        self.assertEqual(dormant_logical["dormancy_profile"]["packed_descriptor_refs"], ["memory/warm/payloads/mem_fixture.json"])
        self.assertGreater(dormant_logical["dormancy_profile"]["compaction_saved_bytes"], 0)

        manager.activate_cell(
            cell_id="finance_intake_router",
            proposer=actors["proposer"],
            reason="reactivate from compact dormancy profile",
        )
        restored_runtime = manager.get_runtime_state("finance_intake_router")
        self.assertEqual(restored_runtime["active_task_ref"], "fixture:phase45-dormancy")
        self.assertEqual(restored_runtime["workspace_subscriptions"], ["workspace:finance"])
        self.assertEqual(restored_runtime["loaded_descriptor_refs"], ["memory/warm/payloads/mem_fixture.json"])
        summary = manager.summary()
        self.assertGreaterEqual(summary["structural_usefulness"]["dormancy_saved_bytes"], 1)
        self.assertGreaterEqual(summary["structural_usefulness"]["reactivation_useful_count"], 1)

    def test_burst_population_returns_to_steady_after_consolidation(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        _, _, _, _, manager = self.init_runtime()
        actors = self.scenario["actors"]

        manager.activate_cell(cell_id="finance_intake_router", proposer=actors["proposer"], reason="activate root lineage cell")

        split_count = 0
        while manager.summary()["active_population"] < 48:
            split_count += 1
            active_cell = manager.list_active_cells()[0]
            manager.split_cell(
                parent_cell_id=active_cell,
                child_role_names=[f"{active_cell}_alpha", f"{active_cell}_beta"],
                proposer=actors["proposer"],
                governance_approver=actors["governance_approver"],
                need_signal=self.make_signal("split", f"need-burst-{split_count:03d}"),
                reason="grow active population inside approved burst cap",
            )

        before = manager.summary()
        self.assertEqual(before["active_population"], 48)
        self.assertGreater(before["logical_population"], before["active_population"])
        self.assertTrue(before["within_runtime_working_set_cap"])

        manager.hibernate_cell(
            cell_id=manager.list_active_cells()[0],
            proposer=actors["proposer"],
            tissue_approver=actors["tissue_approver"],
            reason="trigger automatic return from burst to steady state after consolidation",
        )
        after = manager.summary()
        self.assertEqual(after["active_population"], 24)
        self.assertEqual(after["steady_active_population_target"], 24)
        self.assertEqual(after["burst_active_population_cap"], 48)
        self.assertTrue(manager.replay_history()["replay_match"])

    def run_deterministic_flow_again(self) -> dict:
        with tempfile.TemporaryDirectory() as other_tmp:
            state_root = Path(other_tmp) / "runtime_state"
            env = dict(self.env)
            env["AGIF_FABRIC_STATE_ROOT"] = str(state_root)

            init_result = subprocess.run(
                [str(RUNNER), "fabric", "init", str(CONFIG_PATH)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(init_result.returncode, 0, msg=init_result.stdout)

            config, _, _, _ = load_fabric_bootstrap(CONFIG_PATH)
            store = FabricStateStore(state_root)
            state = store.load_current_state()
            self.assertIsNotNone(state)
            manager = FabricLifecycleManager(store=store, state=state, config=config)
            actors = self.scenario["actors"]

            manager.activate_cell(cell_id="finance_audit_reporter", proposer=actors["proposer"], reason="activate audit reporter")
            manager.activate_cell(cell_id="finance_intake_router", proposer=actors["proposer"], reason="activate intake router")
            split_result = manager.split_cell(
                parent_cell_id="finance_intake_router",
                child_role_names=["intake_router_alpha", "intake_router_beta"],
                proposer=actors["proposer"],
                governance_approver=actors["governance_approver"],
                need_signal=self.make_signal("split", "need-split-001"),
                reason="approved overload split for deterministic fixture",
            )
            child_a, child_b = split_result["child_ids"]
            manager.merge_cells(
                survivor_cell_id=child_a,
                merged_cell_id=child_b,
                proposer=actors["proposer"],
                tissue_approver=actors["tissue_approver"],
                governance_approver=actors["governance_approver"],
                need_signal=self.make_signal("merge", "need-merge-001"),
                reason="approved conflict-aware merge for deterministic fixture",
            )
            manager.activate_cell(cell_id=child_a, proposer=actors["proposer"], reason="reactivate merged survivor")
            manager.hibernate_cell(
                cell_id=child_a,
                proposer=actors["proposer"],
                tissue_approver=actors["tissue_approver"],
                reason="hibernate merged survivor",
            )
            manager.activate_cell(cell_id=child_a, proposer=actors["proposer"], reason="reactivate after hibernate")
            manager.hibernate_cell(
                cell_id=child_a,
                proposer=actors["proposer"],
                tissue_approver=actors["tissue_approver"],
                reason="hibernate before retirement",
            )
            manager.retire_cell(
                cell_id=child_a,
                proposer=actors["proposer"],
                governance_approver=actors["governance_approver"],
                reason="retire dormant survivor while preserving lineage history",
            )
            return manager.summary()


if __name__ == "__main__":
    unittest.main()
