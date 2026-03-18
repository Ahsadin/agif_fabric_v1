"""Deterministic tests for Track B ordered bundle closure."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.benchmarking.v1x_bundle import (
    REQUIRED_COMMAND_SPECS,
    run_v1x_bundle_benchmark,
    write_v1x_bundle_result_tables,
)


class V1XBundleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.command_log = [
            {
                "command": spec["command"],
                "returncode": 0,
                "stdout": spec["expected_token"] + "\n",
                "stderr": "",
            }
            for spec in REQUIRED_COMMAND_SPECS
        ]
        cls.results = run_v1x_bundle_benchmark(command_log=cls.command_log)
        cls.gap_by_id = {item["gate_id"]: item for item in cls.results["gap_chain"]}

    def test_bundle_records_exact_ordered_command_chain(self) -> None:
        command_chain = self.results["command_chain"]
        self.assertEqual(
            [item["step_id"] for item in command_chain],
            [spec["step_id"] for spec in REQUIRED_COMMAND_SPECS],
        )
        self.assertTrue(all(item["matched_expected_order"] for item in command_chain))
        self.assertTrue(all(item["expected_token_present"] for item in command_chain))

    def test_bundle_reuses_closed_gap_results_without_changing_counts(self) -> None:
        self.assertTrue(self.gap_by_id["gap_1"]["accepted"])
        self.assertEqual(self.gap_by_id["gap_1"]["support"]["split_event_count"], 1)
        self.assertTrue(self.gap_by_id["gap_2"]["accepted"])
        self.assertEqual(self.gap_by_id["gap_2"]["support"]["approved_transfer_count"], 1)
        self.assertTrue(self.gap_by_id["gap_3"]["accepted"])
        self.assertIn(
            "northwind_settlement_alias_hold",
            self.gap_by_id["gap_3"]["support"]["improved_case_ids"],
        )

    def test_bundle_acceptance_requires_root_isolation_and_local_record(self) -> None:
        acceptance = self.results["acceptance"]
        self.assertTrue(acceptance["ordered_command_chain_passed"])
        self.assertTrue(acceptance["setup_prerequisite_recorded"])
        self.assertTrue(acceptance["ordered_gap_chain_passed"])
        self.assertTrue(acceptance["root_closure_rechecked"])
        self.assertTrue(acceptance["root_progress_still_600_of_600"])
        self.assertTrue(acceptance["root_tokens_still_isolated"])
        self.assertTrue(acceptance["track_b_progress_still_130_of_130"])
        self.assertTrue(acceptance["track_b_closure_record_complete"])
        self.assertTrue(acceptance["passed"])

    def test_result_tables_write_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            paths = write_v1x_bundle_result_tables(self.results, output_dir=Path(output_dir))
            json_payload = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown_text = paths["markdown"].read_text(encoding="utf-8")

        self.assertIn("acceptance", json_payload)
        self.assertNotIn("created_utc", json_payload)
        self.assertIn("Ordered Command Chain", markdown_text)
        self.assertIn("Gap Chain", markdown_text)
        self.assertIn("Root Re-Check", markdown_text)


if __name__ == "__main__":
    unittest.main()
