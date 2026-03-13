"""Deterministic tests for the Phase 8 bounded soak harness."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intelligence.fabric.benchmarking.phase8 import (
    PHASE8_SHORT_PROFILE,
    run_phase8_bounded_validation,
    run_phase8_profile,
    write_phase8_summary,
)


class Phase8SoakTest(unittest.TestCase):
    def test_phase8_profile_supports_resume_and_bounded_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            run_root = Path(tempdir) / "phase8_resume"
            partial = run_phase8_profile(PHASE8_SHORT_PROFILE, run_root=run_root, resume=True, max_steps=2)
            self.assertFalse(partial["completion"]["bounded_validation_ready"])

            manifest = json.loads((run_root / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["completed_cycle_count"], 2)
            self.assertEqual(manifest["status"], "incomplete")

            resumed = run_phase8_profile(PHASE8_SHORT_PROFILE, run_root=run_root, resume=True)
            self.assertTrue(resumed["completion"]["bounded_validation_ready"])
            self.assertFalse(resumed["completion"]["phase_complete"])
            summary = resumed["artifact_summary"]
            self.assertGreater(summary["trends"]["descriptor_reuse_benefit"], 0.0)
            self.assertGreater(summary["trends"]["governed_reuse_hold_count"], 0)
            self.assertIn("routing_quality_drift", summary["drift"])
            self.assertIn("memory_pollution", summary["failure_taxonomy"])
            self.assertEqual(summary["manifest_continuity"]["checkpoint_scope"], "cycle_and_stress_boundary_only")
            self.assertTrue(summary["stress_results"]["memory_pressure"]["triggered"])
            self.assertTrue(summary["stress_results"]["replay_rollback"]["rollback_restored"])
            self.assertEqual(summary["completion"]["phase8_open_blockers"][0], "real 24h soak not completed locally")
            self.assertTrue(
                any(
                    row["case_id"] == "invoice_high_value_alias_hold"
                    and row["descriptor_reuse_used"]
                    and row["final_status"] == "hold"
                    for cycle in summary["cycles"]
                    for row in cycle["case_rows"]
                )
            )

    def test_phase8_bounded_validation_checks_resume_scenarios(self) -> None:
        result = run_phase8_bounded_validation()
        summary = result["artifact_summary"]
        self.assertTrue(summary["resume_checks"]["all_passed"])
        self.assertTrue(summary["completion"]["resume_gate_passed"])
        self.assertIn("quarantine_resume", summary["resume_checks"]["scenarios"])
        self.assertIn("still_missing_for_closure", summary["blocker_report"])

    def test_phase8_summary_writer_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            result = run_phase8_bounded_validation()
            output_dir = Path(tempdir) / "outputs"
            write_phase8_summary(result, output_dir=output_dir, basename="phase8_test_summary")
            first_json = (output_dir / "phase8_test_summary.json").read_text(encoding="utf-8")
            first_markdown = (output_dir / "phase8_test_summary.md").read_text(encoding="utf-8")

            changed = json.loads(json.dumps(result))
            changed["artifact_summary"]["failure_cases"].append("synthetic note")
            changed["artifact_summary"]["failure_cases"].remove("synthetic note")
            write_phase8_summary(changed, output_dir=output_dir, basename="phase8_test_summary")
            second_json = (output_dir / "phase8_test_summary.json").read_text(encoding="utf-8")
            second_markdown = (output_dir / "phase8_test_summary.md").read_text(encoding="utf-8")

        self.assertEqual(first_json, second_json)
        self.assertEqual(first_markdown, second_markdown)
        payload = json.loads(first_json)
        self.assertNotIn("workflow_id", json.dumps(payload))
        self.assertIn("runtime timestamps", first_markdown)
        self.assertIn("Resume Realism", first_markdown)


if __name__ == "__main__":
    unittest.main()
