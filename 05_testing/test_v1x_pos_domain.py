"""Deterministic tests for Track B Gap 3 bounded POS-domain transfer proof."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.benchmarking.v1x_pos_domain import (
    run_v1x_pos_domain_benchmark,
    write_v1x_pos_domain_result_tables,
)


class V1XPosDomainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = run_v1x_pos_domain_benchmark()
        cls.enabled_cases = {item["case_id"]: item for item in cls.results["runs"]["transfer_enabled"]["case_results"]}
        cls.control_cases = {item["case_id"]: item for item in cls.results["runs"]["control"]["case_results"]}

    def test_gap3_suite_stays_frozen_at_five_cases_and_same_order(self) -> None:
        suite_summary = self.results["suite_summary"]
        self.assertEqual(suite_summary["case_count"], 5)
        self.assertEqual(
            self.results["runs"]["transfer_enabled"]["case_ids"],
            self.results["runs"]["control"]["case_ids"],
        )

    def test_control_blocks_cross_domain_transfer_at_governance(self) -> None:
        control = self.results["runs"]["control"]
        self.assertFalse(control["cross_domain_transfer_enabled"])
        self.assertGreaterEqual(control["metrics"]["governance_disabled_veto_count"], 1)
        self.assertEqual(control["metrics"]["counted_cross_domain_influence_count"], 0)

    def test_finance_origin_transfer_improves_the_target_pos_case(self) -> None:
        enabled_case = self.enabled_cases["northwind_settlement_alias_hold"]
        control_case = self.control_cases["northwind_settlement_alias_hold"]

        self.assertEqual(enabled_case["transfer_status"], "approved")
        self.assertTrue(enabled_case["counted_cross_domain_influence"])
        self.assertEqual(enabled_case["final_action"], "hold_for_finance_review")
        self.assertEqual(control_case["final_action"], "manual_review")
        self.assertGreater(enabled_case["case_score"], control_case["case_score"])
        self.assertEqual(enabled_case["source_domain"], "finance_ap")
        self.assertTrue(enabled_case["transfer_approval_ref"].startswith("authority_"))

    def test_missing_explicit_transfer_does_not_count_as_cross_domain_influence(self) -> None:
        enabled_case = self.enabled_cases["tailspin_refund_missing_explicit"]
        self.assertEqual(enabled_case["transfer_status"], "denied")
        self.assertFalse(enabled_case["counted_cross_domain_influence"])
        self.assertIsNone(enabled_case["authority_review_id"])

    def test_low_quality_case_abstains(self) -> None:
        enabled_case = self.enabled_cases["unknown_vendor_low_quality_abstain"]
        self.assertEqual(enabled_case["transfer_status"], "abstained")
        self.assertFalse(enabled_case["counted_cross_domain_influence"])
        self.assertEqual(enabled_case["final_action"], "approve_close")

    def test_acceptance_gate_passes(self) -> None:
        acceptance = self.results["acceptance"]
        self.assertTrue(acceptance["bounded_pos_suite_frozen"])
        self.assertTrue(acceptance["same_case_sequence"])
        self.assertTrue(acceptance["control_disables_transfer_at_governance"])
        self.assertTrue(acceptance["finance_origin_descriptor_improves_pos_result"])
        self.assertTrue(acceptance["cross_domain_influence_requires_explicit_transfer_approval"])
        self.assertTrue(acceptance["useful_and_auditable"])
        self.assertTrue(acceptance["passed"])

    def test_result_tables_write_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            paths = write_v1x_pos_domain_result_tables(self.results, output_dir=Path(output_dir))
            json_payload = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown_text = paths["markdown"].read_text(encoding="utf-8")

        self.assertIn("runs", json_payload)
        self.assertIn("Case Comparison", markdown_text)
        self.assertIn("Enabled Audit Trail", markdown_text)


if __name__ == "__main__":
    unittest.main()
