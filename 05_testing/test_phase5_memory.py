"""Deterministic tests for AGIF Phase 5 reviewed memory and bounded growth."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.lifecycle import FabricLifecycleManager
from intelligence.fabric.memory import FabricMemoryManager
from intelligence.fabric.registry.loader import load_fabric_bootstrap
from intelligence.fabric.state_store import FabricStateStore


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "runner" / "cell"
CONFIG_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase5" / "minimal_fabric_config.json"
GOOD_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase5" / "sample_workflow_payload_good.json"
BAD_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase5" / "sample_workflow_payload_bad.json"
SUPERSEDE_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase5" / "sample_workflow_payload_supersede.json"
REPLAY_MANIFEST_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase5" / "sample_replay_manifest.json"


class Phase5MemoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.state_root = Path(self.tempdir.name) / "runtime_state"
        self.env = os.environ.copy()
        self.env["AGIF_FABRIC_STATE_ROOT"] = str(self.state_root)

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

    def init_runtime(self) -> tuple[dict, dict, dict, FabricStateStore, FabricLifecycleManager, FabricMemoryManager]:
        config, _, registry, _ = load_fabric_bootstrap(CONFIG_PATH)
        store = FabricStateStore(self.state_root)
        state = store.load_current_state()
        self.assertIsNotNone(state)
        lifecycle = FabricLifecycleManager(store=store, state=state, config=config)
        memory = FabricMemoryManager(store=store, state=state, config=config)
        return state, config, registry, store, lifecycle, memory

    def make_variant_payload(self, *, document_id: str, vendor_name: str, total: str) -> dict:
        payload = json.loads(GOOD_PAYLOAD_PATH.read_text(encoding="utf-8"))
        payload["document_id"] = document_id
        payload["inputs"]["vendor_name"] = vendor_name
        payload["inputs"]["total"] = total
        return payload

    def write_manifest(self, *, payload: dict, name: str) -> Path:
        payload_path = Path(self.tempdir.name) / f"{name}.payload.json"
        manifest_path = Path(self.tempdir.name) / f"{name}.manifest.json"
        payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_path.write_text(json.dumps({"workflow_payload_path": payload_path.name}, indent=2) + "\n", encoding="utf-8")
        return manifest_path

    def test_phase5_reviewed_memory_flow_and_evidence(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        self.run_cli(["fabric", "run"], stdin_text=GOOD_PAYLOAD_PATH.read_text(encoding="utf-8"))

        _, _, _, store, lifecycle, memory = self.init_runtime()
        summary = memory.summary()
        decisions = memory.load_decisions()
        promoted = memory.load_promoted_memories()
        descriptors = memory.load_descriptors()
        self.assertEqual(decisions[-1]["decision"], "promote")
        self.assertEqual(summary["raw_log_count"], 1)
        self.assertEqual(summary["raw_log_promoted_count"], 0)
        self.assertEqual(summary["active_promoted_count"], 1)
        self.assertEqual(summary["active_descriptor_count"], 1)
        promoted_record = next(iter(promoted["active"].values()))
        descriptor_record = next(iter(descriptors["active"].values()))
        self.assertEqual(promoted_record["retention_tier"], "warm")
        self.assertEqual(descriptor_record["storage_tier"], "warm")
        self.assertNotEqual(memory.load_raw_logs()[0]["payload_ref"], promoted_record["payload_ref"])

        self.run_cli(["fabric", "run"], stdin_text=GOOD_PAYLOAD_PATH.read_text(encoding="utf-8"))
        _, _, _, _, _, memory = self.init_runtime()
        duplicate_summary = memory.summary()
        duplicate_decisions = memory.load_decisions()
        self.assertEqual(duplicate_decisions[-1]["decision"], "compress")
        self.assertEqual(duplicate_summary["active_promoted_count"], 1)

        self.run_cli(["fabric", "run"], stdin_text=SUPERSEDE_PAYLOAD_PATH.read_text(encoding="utf-8"))
        _, _, _, _, _, memory = self.init_runtime()
        superseded_promoted = memory.load_promoted_memories()
        superseded_descriptors = memory.load_descriptors()
        active_descriptor = next(iter(superseded_descriptors["active"].values()))
        self.assertEqual(len(superseded_promoted["active"]), 1)
        self.assertGreaterEqual(len(superseded_promoted["archived"]), 1)
        self.assertIsNotNone(active_descriptor["supersedes_descriptor_id"])

        for index in range(2, 8):
            payload = self.make_variant_payload(
                document_id=f"doc-phase5-{index:03d}",
                vendor_name=f"Vendor {index:03d}",
                total=f"{100 + index}.00",
            )
            self.run_cli(["fabric", "run"], stdin_text=json.dumps(payload))

        _, _, _, store, lifecycle, memory = self.init_runtime()
        bounded_summary = memory.summary()
        active_memories = memory.load_promoted_memories()["active"]
        self.assertTrue(all(bool(value) for value in bounded_summary["within_caps"].values()))
        self.assertGreaterEqual(bounded_summary["memory_pressure_signal_count"], 1)
        self.assertTrue(any(record["retention_tier"] == "cold" for record in active_memories.values()))
        self.assertLessEqual(bounded_summary["raw_log_count"], 3)
        self.assertTrue(memory.replay_decisions()["traceable"])
        self.assertTrue(memory.replay_decisions()["replay_match"])
        self.assertTrue(any(signal["signal_kind"] == "memory_pressure" for signal in lifecycle.load_need_signals()))

        protected_cold = next(record for record in active_memories.values() if record["retention_tier"] == "cold")
        protected_path = REPO_ROOT / protected_cold["payload_ref"]
        self.assertTrue(protected_path.exists())
        memory.garbage_collect(reason="phase5_protected_cold_gc")
        self.assertTrue(protected_path.exists(), "GC must not remove cold payloads still referenced by active descriptors.")

        retired = memory.retire_memory(
            memory_id=protected_cold["memory_id"],
            reviewer_id="governance:phase5_memory_reviewer",
            reason="retire a cold payload so GC can remove the unreferenced artifact",
        )
        self.assertEqual(retired["memory_id"], protected_cold["memory_id"])
        memory.garbage_collect(reason="phase5_retire_gc")
        self.assertFalse(protected_path.exists(), "GC should remove cold payloads once they are no longer referenced.")

        for index in range(8, 13):
            payload = self.make_variant_payload(
                document_id=f"doc-replay-{index:03d}",
                vendor_name=f"Replay Vendor {index:03d}",
                total=f"{200 + index}.00",
            )
            self.run_cli(["fabric", "run"], stdin_text=json.dumps(payload))
            manifest_path = self.write_manifest(payload=payload, name=f"replay-{index:03d}")
            self.run_cli(["fabric", "replay", str(manifest_path)])

        replay_dir = store.fabric_dir("agif-fabric-v1-local") / "replays"
        self.assertLessEqual(len(list(replay_dir.glob("*.json"))), 3)

        evidence_path = Path(self.tempdir.name) / "phase5_evidence.json"
        evidence_payload = self.run_cli(["fabric", "evidence", str(evidence_path)])
        self.assertIn("AGIF_FABRIC_P5_PASS", evidence_payload["data"]["earned_pass_tokens"])
        evidence_bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertIn("AGIF_FABRIC_P5_PASS", evidence_bundle["earned_pass_tokens"])
        self.assertTrue(evidence_bundle["memory"]["cold_reference_integrity"])

    def test_phase5_reject_and_defer_paths(self) -> None:
        self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        self.run_cli(["fabric", "run"], stdin_text=BAD_PAYLOAD_PATH.read_text(encoding="utf-8"))

        _, _, _, _, _, memory = self.init_runtime()
        summary = memory.summary()
        decisions = memory.load_decisions()
        self.assertEqual(decisions[-1]["decision"], "reject")
        self.assertEqual(summary["active_promoted_count"], 0)
        self.assertEqual(summary["raw_log_promoted_count"], 0)

        deferred_candidate = memory.nominate_candidate(
            payload={
                "workflow_name": "finance_document_intake",
                "document_id": "doc-phase5-defer",
                "inputs": {
                    "currency": "EUR",
                    "document_type": "invoice",
                    "total": "44.00",
                    "vendor_name": "Deferred Vendor GmbH",
                },
                "selected_cells": ["finance_intake_router"],
                "selected_roles": ["intake_router"],
                "source_run_ref": "fixture:manual",
                "source_workspace_ref": "fixture:manual",
                "source_log_refs": [],
            },
            source_ref="fixture:manual",
            source_log_refs=[],
            producer_cell_id="finance_intake_router",
            descriptor_kind="workflow_intake",
            task_scope="finance_document_intake:doc-phase5-defer",
        )
        memory.review_candidate(
            candidate_id=deferred_candidate["candidate_id"],
            reviewer_id="governance:phase5_memory_reviewer",
            decision="defer",
            compression_mode="review_buffer_v1",
            retention_tier="hot",
            reason="keep the candidate in the short review buffer",
        )
        deferred_state = memory.load_candidates()[deferred_candidate["candidate_id"]]
        self.assertEqual(deferred_state["status"], "deferred")
        self.assertIsInstance(deferred_state["payload_ref"], str)
        self.assertTrue((REPO_ROOT / deferred_state["payload_ref"]).exists())
        self.assertEqual(memory.summary()["pending_review_count"], 1)


if __name__ == "__main__":
    unittest.main()
