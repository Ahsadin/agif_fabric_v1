# MSI Soak Note Paper R5 Handoff

## Goal
- Align the public repo and the private `R5` paper draft around the explicit MSI soak-machine provenance note supplied after closure, while keeping the draft out of the public repo.

## Files Updated
- `PROJECT_README.md`
- `CHANGELOG.md`
- `01_plan/PROGRESS_TRACKER.md`
- `05_testing/MSI_SOAK_MACHINE_NOTE.md`
- `05_testing/PASS_TOKENS.md`
- `05_testing/PHASE8_LONGRUN_EVIDENCE.md`
- `05_testing/PHASE9_CLOSURE_EVIDENCE.md`
- `06_outputs/run_summaries/phase8_real_24h_soak.md`
- `06_outputs/run_summaries/phase8_real_72h_soak.md`
- `06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md`
- `06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md`
- `06_outputs/paper_drafts/README.md`
- `scripts/check_phase9_closure.py`
- `00_admin/CODEX_THREAD_MAP.md`

## What Changed
- Added a canonical MSI soak-machine note with the provided hardware, OS, Python, power-setting, before-soak, run-outcome, artifact-footprint, and honest-limit details.
- Updated the Phase 8 and Phase 9 package docs so they now point at the MSI note instead of relying on path inference.
- Updated the private local `R5` paper draft outside the public repo with:
  - `R5` status labels
  - the public GitHub clone path
  - the explicit MSI Windows soak-machine paragraph
  - the MSI provenance and paper-status rows in the evidence appendix
- Kept the public repo on the non-paper state with `06_outputs/paper_drafts/README.md`.
- Updated the one-command Phase 9 verifier so it now requires the MSI note and the paper-status note, not the private draft files.
- Stripped paper draft binaries from the public git history.

## Verification
- `python3 scripts/check_phase9_closure.py`
  - result: `AGIF_FABRIC_P9_PASS`
- Public-path audit over the active docs:
  - no remaining `/Users/ahsadin/...` paths in the active public package files

## Honest Caveats
- MSI remains the final AGIF v1 long-run evidence machine.
- The MSI note and the private `R5` paper draft do not convert the long-run evidence into MacBook Air-only proof.
- The `R5` paper draft stays private and is not published in the public repo.
