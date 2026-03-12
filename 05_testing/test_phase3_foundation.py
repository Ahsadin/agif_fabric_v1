"""Base tests for the AGIF Phase 3 runner and fabric foundation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "runner" / "cell"
CONFIG_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase3" / "minimal_fabric_config.json"
WORKFLOW_PAYLOAD_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase3" / "sample_workflow_payload.json"
REPLAY_MANIFEST_PATH = REPO_ROOT / "fixtures" / "document_workflow" / "phase3" / "sample_replay_manifest.json"


class Phase3FoundationTest(unittest.TestCase):
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

    def test_invalid_config_fails_closed(self) -> None:
        invalid_config = Path(self.tempdir.name) / "invalid_config.json"
        invalid_config.write_text(json.dumps({"fabric_id": "broken"}), encoding="utf-8")
        payload = self.run_cli(["fabric", "init", str(invalid_config)], expect_ok=False)
        self.assertEqual(payload["error"]["code"], "CONFIG_INVALID")

    def test_phase3_foundation_flow(self) -> None:
        init_payload = self.run_cli(["fabric", "init", str(CONFIG_PATH)])
        self.assertEqual(init_payload["data"]["registered_blueprints"], 2)

        status_payload = self.run_cli(["fabric", "status"])
        self.assertTrue(status_payload["data"]["initialized"])
        self.assertEqual(status_payload["data"]["metrics"]["registered_blueprint_count"], 2)

        run_payload = self.run_cli(["fabric", "run"], stdin_text=WORKFLOW_PAYLOAD_PATH.read_text(encoding="utf-8"))
        workflow_id = run_payload["data"]["workflow_id"]
        self.assertTrue(workflow_id.startswith("wf_"))
        self.assertEqual(run_payload["data"]["result"]["workflow_name"], "finance_document_intake")

        replay_payload = self.run_cli(["fabric", "replay", str(REPLAY_MANIFEST_PATH)])
        self.assertTrue(replay_payload["data"]["replay_match"])
        self.assertEqual(replay_payload["data"]["workflow_id"], workflow_id)

        evidence_path = Path(self.tempdir.name) / "phase3_evidence_bundle.json"
        evidence_payload = self.run_cli(["fabric", "evidence", str(evidence_path)])
        self.assertTrue(evidence_payload["data"]["pass"])
        self.assertTrue(evidence_path.exists())

        evidence_bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(evidence_bundle["pass_token"], "AGIF_FABRIC_P3_PASS")


if __name__ == "__main__":
    unittest.main()

