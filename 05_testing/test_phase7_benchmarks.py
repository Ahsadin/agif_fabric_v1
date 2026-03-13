"""Deterministic tests for Phase 7 domain tissues and benchmark comparison."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.benchmarking.phase7 import run_phase7_benchmarks, write_phase7_result_tables


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "runner" / "cell"
WITH_ADAPT_CONFIG = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "minimal_fabric_config_with_adaptation.json"
SEED_CASE_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase7" / "case_invoice_seed_reference.json"

REQUIRED_TISSUES = {
    "finance_intake_routing_tissue",
    "finance_extraction_tissue",
    "finance_validation_correction_tissue",
    "finance_anomaly_reviewer_tissue",
    "finance_workspace_governance_tissue",
    "finance_reporting_output_tissue",
}


class Phase7BenchmarksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.benchmark_results = run_phase7_benchmarks()

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.state_root = Path(self.tempdir.name) / "runtime_state"
        self.env = os.environ.copy()
        self.env["AGIF_FABRIC_STATE_ROOT"] = str(self.state_root)

    def run_cli(self, args: list[str], *, stdin_text: str | None = None) -> dict:
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
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertTrue(payload["ok"], msg=result.stdout)
        return payload

    def test_phase7_workflow_uses_all_required_tissues_and_traceable_handoffs(self) -> None:
        self.run_cli(["fabric", "init", str(WITH_ADAPT_CONFIG)])
        workflow_payload = SEED_CASE_PATH.read_text(encoding="utf-8")
        run_payload = self.run_cli(["fabric", "run"], stdin_text=workflow_payload)
        result = run_payload["data"]["result"]

        self.assertEqual(set(result["tissues_used"]), REQUIRED_TISSUES)
        self.assertGreaterEqual(int(result["handoff_count"]), 5)
        self.assertIn("finance_document_classifier", result["selected_cells"])
        self.assertIn("finance_output_formatter", result["selected_cells"])

        workspace_ref = Path(str(run_payload["data"]["workspace_ref"]))
        workspace_path = workspace_ref if workspace_ref.is_absolute() else (REPO_ROOT / workspace_ref)
        workspace = json.loads(workspace_path.read_text(encoding="utf-8"))
        self.assertEqual(set(workspace["tissues_used"]), REQUIRED_TISSUES)
        self.assertGreaterEqual(len(workspace["handoffs"]), 5)
        self.assertIn("governance_action", workspace["governance"])

    def test_benchmark_harness_runs_all_frozen_classes(self) -> None:
        classes = self.benchmark_results["classes"]
        self.assertEqual(
            set(classes.keys()),
            {
                "flat_baseline",
                "multi_cell_without_bounded_adaptation",
                "multi_cell_with_bounded_adaptation",
            },
        )
        self.assertTrue(self.benchmark_results["comparisons"]["usefulness_gate_passed"])
        self.assertIn("invoice_followup_alias", self.benchmark_results["comparisons"]["descriptor_change_cases"])
        self.assertIn("invoice_followup_alias_repeat", self.benchmark_results["comparisons"]["descriptor_change_cases"])
        self.assertIn("invoice_high_value_alias_hold", self.benchmark_results["comparisons"]["descriptor_change_cases"])
        self.assertIn("invoice_anomaly_hold", self.benchmark_results["comparisons"]["fabric_beats_baseline_cases"])
        self.assertIn("invoice_total_mismatch_hold", self.benchmark_results["comparisons"]["fabric_beats_baseline_cases"])
        self.assertIn("invoice_high_value_alias_hold", self.benchmark_results["comparisons"]["fabric_beats_baseline_cases"])

    def test_metrics_show_determinism_governance_and_descriptor_reuse(self) -> None:
        baseline = self.benchmark_results["classes"]["flat_baseline"]["metrics"]
        no_adapt = self.benchmark_results["classes"]["multi_cell_without_bounded_adaptation"]["metrics"]
        with_adapt = self.benchmark_results["classes"]["multi_cell_with_bounded_adaptation"]["metrics"]

        self.assertEqual(baseline["replay_determinism"], 1.0)
        self.assertEqual(no_adapt["replay_determinism"], 1.0)
        self.assertEqual(with_adapt["replay_determinism"], 1.0)
        self.assertGreater(no_adapt["governance_success_rate"], baseline["governance_success_rate"])
        self.assertGreater(with_adapt["descriptor_reuse_rate"], 0.0)
        self.assertGreater(with_adapt["improvement_from_prior_descriptors"], 0.0)
        self.assertLessEqual(with_adapt["bounded_forgetting"], 0.1)
        self.assertLess(with_adapt["unsafe_action_rate"], baseline["unsafe_action_rate"])
        self.assertGreater(with_adapt["resource_usage"]["retained_memory_delta_bytes"], 0)
        self.assertGreater(with_adapt["resource_usage"]["governance_overhead_share"], 0.0)
        self.assertIn("structural_signal_cases", with_adapt["split_merge_efficiency"])
        self.assertIn("future_trigger", with_adapt["split_merge_efficiency"])

    def test_hardening_adds_explanations_and_tissue_analytics(self) -> None:
        with_adapt = self.benchmark_results["classes"]["multi_cell_with_bounded_adaptation"]
        tissues = with_adapt["analytics"]["tissues"]
        validation = tissues["finance_validation_correction_tissue"]
        governance = tissues["finance_workspace_governance_tissue"]

        self.assertGreater(validation["reuse_contribution"], 0)
        self.assertGreater(validation["intervention_case_count"], 0)
        self.assertGreater(governance["governance_burden"], 0)

        comparison_rows = {
            item["case_id"]: item for item in self.benchmark_results["comparisons"]["case_rows"]
        }
        followup = comparison_rows["invoice_followup_alias_repeat"]
        self.assertIn("descriptor", followup["reason_summary"])
        self.assertNotEqual(followup["with_adapt_improved"], "no material improvement")
        self.assertIn("handoffs=", followup["with_adapt_route_of_custody"])
        self.assertIn("desc_", followup["with_adapt_descriptor_detail"])
        self.assertIn("confidence", followup["with_adapt_confidence"])

        high_value_hold = comparison_rows["invoice_high_value_alias_hold"]
        self.assertIn("governance", high_value_hold["reason_summary"])
        self.assertIn("hold_for_review", high_value_hold["with_adapt_governance_detail"])
        self.assertIn("uncertainty", high_value_hold["with_adapt_need_resolution"])
        self.assertIn("trust_risk", high_value_hold["with_adapt_need_resolution"])
        self.assertIn("hold/review_required", high_value_hold["outcome_trail"])

    def test_result_tables_normalize_ephemeral_fields_for_deterministic_reruns(self) -> None:
        results = json.loads(json.dumps(self.benchmark_results))
        no_adapt = results["classes"]["multi_cell_without_bounded_adaptation"]["status_refs"]
        with_adapt = results["classes"]["multi_cell_with_bounded_adaptation"]["status_refs"]

        with tempfile.TemporaryDirectory() as output_dir:
            results["created_utc"] = "2099-01-01T00:00:00Z"
            no_adapt["evidence_path"] = "/tmp/run-one/phase7_evidence.json"
            with_adapt["evidence_path"] = "/tmp/run-one-alt/phase7_evidence.json"
            write_phase7_result_tables(results, output_dir=Path(output_dir))
            first_json = (Path(output_dir) / "phase7_benchmark_results.json").read_text(encoding="utf-8")
            first_markdown = (Path(output_dir) / "phase7_benchmark_results.md").read_text(encoding="utf-8")

            results["created_utc"] = "2099-01-02T00:00:00Z"
            no_adapt["evidence_path"] = "/tmp/run-two/phase7_evidence.json"
            with_adapt["evidence_path"] = "/tmp/run-two-alt/phase7_evidence.json"
            write_phase7_result_tables(results, output_dir=Path(output_dir))
            second_json = (Path(output_dir) / "phase7_benchmark_results.json").read_text(encoding="utf-8")
            second_markdown = (Path(output_dir) / "phase7_benchmark_results.md").read_text(encoding="utf-8")

        self.assertEqual(first_json, second_json)
        self.assertEqual(first_markdown, second_markdown)

        payload = json.loads(first_json)
        self.assertNotIn("created_utc", payload)
        self.assertEqual(
            payload["classes"]["multi_cell_without_bounded_adaptation"]["status_refs"]["evidence_path"],
            "<temporary>/phase7_evidence.json",
        )
        self.assertEqual(
            payload["classes"]["multi_cell_with_bounded_adaptation"]["status_refs"]["evidence_path"],
            "<temporary>/phase7_evidence.json",
        )
        self.assertIn("runtime timestamp omitted", first_markdown)
        self.assertIn("Route Of Custody", first_markdown)
        self.assertIn("Descriptor Reuse Evidence", first_markdown)


if __name__ == "__main__":
    unittest.main()
