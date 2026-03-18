# MSI Soak Note Paper R5 Handoff

## Goal
- Align the public repo, the working paper draft, and the Phase 8 or Phase 9 package around the explicit MSI soak-machine provenance note supplied after closure.

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
- `06_outputs/paper_drafts/AGIF_v1_paper_R5_2026-03-18.docx`
- `06_outputs/paper_drafts/AGIF_v1_paper_R5_2026-03-18.pdf`
- `scripts/check_phase9_closure.py`
- `00_admin/CODEX_THREAD_MAP.md`

## What Changed
- Added a canonical MSI soak-machine note with the provided hardware, OS, Python, power-setting, before-soak, run-outcome, artifact-footprint, and honest-limit details.
- Updated the Phase 8 and Phase 9 package docs so they now point at the MSI note instead of relying on path inference.
- Reintroduced the public working paper draft as `R5` and marked it clearly as a working draft, not final publication.
- Updated the `R5` paper draft itself with:
  - `R5` status labels
  - the public GitHub clone path
  - the explicit MSI Windows soak-machine paragraph
  - the MSI provenance and paper-status rows in the evidence appendix
- Updated the one-command Phase 9 verifier so it now requires the MSI note and the `R5` DOCX/PDF pair.

## Verification
- `python3 scripts/check_phase9_closure.py`
  - result: `AGIF_FABRIC_P9_PASS`
- Public-path audit over the active docs and `R5` PDF:
  - no remaining `/Users/ahsadin/...` paths
- Visual render audit:
  - checked the updated `R5` PDF opening page
  - checked the updated long-run evidence pages
  - checked the updated appendix and footer pages

## Honest Caveats
- MSI remains the final AGIF v1 long-run evidence machine.
- The MSI note and the `R5` paper draft do not convert the long-run evidence into MacBook Air-only proof.
- The included `R5` paper draft is still a working draft, not the final publication.
