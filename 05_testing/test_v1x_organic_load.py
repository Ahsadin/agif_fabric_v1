"""Deterministic tests for Track B Gap 1 organic split usefulness proof."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.benchmarking.v1x_organic_load import (
    run_v1x_organic_load_benchmark,
    write_v1x_organic_load_result_tables,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class V1XOrganicLoadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = run_v1x_organic_load_benchmark()

    def test_suite_stays_frozen_at_40_cases_with_required_mix(self) -> None:
        suite_summary = self.results["suite_summary"]
        self.assertEqual(suite_summary["case_count"], 40)
        self.assertEqual(
            suite_summary["composition"],
            {
                "alias_heavy": 20,
                "novelty_heavy": 10,
                "recovery_tail": 10,
            },
        )

    def test_elastic_and_control_share_the_exact_same_stream(self) -> None:
        elastic = self.results["runs"]["elastic"]
        control = self.results["runs"]["control"]
        self.assertEqual(elastic["case_ids"], control["case_ids"])
        self.assertEqual(len(elastic["case_ids"]), 40)

    def test_gap1_records_one_real_split_and_blocks_control_split_transitions(self) -> None:
        elastic = self.results["runs"]["elastic"]
        control = self.results["runs"]["control"]

        self.assertEqual(elastic["split_event_count"], 1)
        self.assertEqual(elastic["split_events"][0]["history_transition"], "split_pending_to_active_children")
        self.assertEqual(elastic["split_events"][0]["case_id"], "alias_006_northwind_high_value_a")
        self.assertEqual(control["split_event_count"], 0)
        self.assertEqual(control["overhead"]["split_transition_count"], 0)
        self.assertTrue(control["split_proposals"])
        self.assertEqual(control["split_proposals"][0]["governance_outcome"], "split_disabled_by_governance")

    def test_split_children_are_used_after_the_split(self) -> None:
        elastic_rows = self.results["runs"]["elastic"]["case_results"]
        post_split_rows = elastic_rows[6:10]
        self.assertTrue(all(row["queue_metrics"]["correction_worker_count"] == 2 for row in post_split_rows))
        self.assertTrue(
            all(
                row["correction_selected_cell"].startswith("finance_correction_specialist__child_")
                for row in post_split_rows
            )
        )

    def test_usefulness_gate_requires_latency_gain_without_accuracy_regression(self) -> None:
        elastic = self.results["runs"]["elastic"]
        control = self.results["runs"]["control"]
        comparison = self.results["comparison"]
        acceptance = self.results["acceptance"]

        self.assertGreaterEqual(elastic["metrics"]["task_accuracy"], control["metrics"]["task_accuracy"])
        self.assertLess(elastic["metrics"]["mean_queue_age_units"], control["metrics"]["mean_queue_age_units"])
        self.assertLess(
            elastic["metrics"]["mean_end_to_end_latency_units"],
            control["metrics"]["mean_end_to_end_latency_units"],
        )
        self.assertTrue(comparison["usefulness_gate_passed"])
        self.assertTrue(acceptance["passed"])

    def test_population_returns_near_start_and_merge_is_recorded(self) -> None:
        elastic = self.results["runs"]["elastic"]
        self.assertEqual(elastic["population"]["initial"]["active_population"], 0)
        self.assertEqual(elastic["population"]["after_settle"]["active_population"], 0)
        self.assertTrue(elastic["population"]["returned_near_start"])
        self.assertEqual(elastic["merge_event_count"], 1)

    def test_result_tables_write_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            paths = write_v1x_organic_load_result_tables(self.results, output_dir=Path(output_dir))
            json_payload = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown_text = paths["markdown"].read_text(encoding="utf-8")

        self.assertIn("runs", json_payload)
        self.assertNotIn("created_utc", json_payload)
        self.assertIn("Elastic Split Events", markdown_text)
        self.assertIn("Control Split Decisions", markdown_text)
        self.assertIn("Overhead Vs Usefulness", markdown_text)


if __name__ == "__main__":
    unittest.main()
