"""Deterministic tests for Track B Gap 2 governed skill-graph proof."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.benchmarking.v1x_skill_graph import (
    run_v1x_skill_graph_benchmark,
    write_v1x_skill_graph_result_tables,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class V1XSkillGraphTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.results = run_v1x_skill_graph_benchmark()
        cls.requests_by_id = {item["request_id"]: item for item in cls.results["transfer_requests"]}

    def test_gap2_builds_real_graph_with_retired_and_transfer_edges(self) -> None:
        summary = self.results["graph_summary"]
        self.assertGreaterEqual(summary["source_descriptor_count"], 3)
        self.assertGreaterEqual(summary["retired_source_descriptor_count"], 1)
        self.assertGreaterEqual(summary["relation_counts"].get("shared_document_type", 0), 1)
        self.assertGreaterEqual(summary["relation_counts"].get("transfer_approval", 0), 1)

    def test_cross_domain_transfer_uses_explicit_transfer_approval_and_materializes_provenance(self) -> None:
        approved = self.requests_by_id["approved_cross_domain_invoice_transfer"]
        materialized = approved["materialized_transfer"]
        provenance = materialized["provenance_bundle"]

        self.assertEqual(approved["required_action"], "transfer_approval")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["authority_decision"], "approved")
        self.assertTrue(approved["audit_ready"])
        self.assertGreater(approved["target_support_score"], approved["baseline_support_score"])
        self.assertTrue(provenance["source_descriptor_id"].startswith("desc_"))
        self.assertTrue(provenance["source_memory_id"].startswith("mem_"))
        self.assertIn("payloads", provenance["source_payload_ref"])
        self.assertTrue(provenance["transfer_descriptor_id"].startswith("tdesc_"))
        self.assertTrue(provenance["transfer_approval_ref"].startswith("authority_"))

    def test_low_quality_and_missing_explicit_paths_do_not_materialize_transfer(self) -> None:
        low_quality = self.requests_by_id["abstained_low_quality_transfer"]
        missing_explicit = self.requests_by_id["denied_missing_explicit_transfer_approval"]
        boundary_denied = self.requests_by_id["denied_out_of_boundary_transfer"]

        self.assertEqual(low_quality["status"], "abstained")
        self.assertIsNone(low_quality["materialized_transfer_id"])
        self.assertEqual(missing_explicit["status"], "denied")
        self.assertEqual(missing_explicit["decision_reason"], "missing_explicit_transfer_approval")
        self.assertIsNone(missing_explicit["authority_review_id"])
        self.assertEqual(boundary_denied["status"], "denied")
        self.assertEqual(boundary_denied["authority_decision"], "vetoed")
        self.assertIsNone(boundary_denied["materialized_transfer_id"])

    def test_acceptance_gate_passes(self) -> None:
        acceptance = self.results["acceptance"]
        self.assertTrue(acceptance["descriptor_graph_exists"])
        self.assertTrue(acceptance["transfer_approval_path_exists"])
        self.assertTrue(acceptance["provenance_explicit"])
        self.assertTrue(acceptance["low_quality_transfer_abstains_or_denied"])
        self.assertTrue(acceptance["cross_domain_requires_explicit_transfer_approval"])
        self.assertTrue(acceptance["authority_veto_visible"])
        self.assertTrue(acceptance["retirement_visibility"])
        self.assertTrue(acceptance["useful_and_auditable"])
        self.assertTrue(acceptance["passed"])

    def test_result_tables_write_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            paths = write_v1x_skill_graph_result_tables(self.results, output_dir=Path(output_dir))
            json_payload = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown_text = paths["markdown"].read_text(encoding="utf-8")

        self.assertIn("graph_summary", json_payload)
        self.assertNotIn("created_utc", json_payload)
        self.assertIn("Transfer Requests", markdown_text)
        self.assertIn("Materialized Provenance", markdown_text)
        self.assertIn("Retired Source Visibility", markdown_text)


if __name__ == "__main__":
    unittest.main()
