# Paper Withdrawal Public Handoff

## Scope
- Remove the unpublished paper draft files from the public repo.
- Replace them with a clear status note in `06_outputs/paper_drafts/`.
- Update the current public-facing Phase 9 docs and verifier so they no longer claim the draft is included.
- Continue the active path-sanitization pass for public polish.

## Files Updated
- `AGENTS.md`
- `PROJECT_README.md`
- `DECISIONS.md`
- `CHANGELOG.md`
- `01_plan/PROGRESS_TRACKER.md`
- `02_requirements/AGIF_V1_REQUIREMENTS.md`
- `02_requirements/FALSIFICATION_THRESHOLDS.md`
- `05_testing/PASS_TOKENS.md`
- `05_testing/PHASE9_CLOSURE_EVIDENCE.md`
- `06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md`
- `06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md`
- `06_outputs/paper_drafts/README.md`
- `intelligence/fabric/benchmarking/phase7.py`
- `scripts/check_phase9_closure.py`
- `00_admin/REFERENCE_IMPORT_MATRIX.md`
- `00_admin/CODEX_THREAD_MAP.md`

## File Removals
- `06_outputs/paper_drafts/AGIF_v1_paper_R2_2026-03-18.docx`
- `06_outputs/paper_drafts/AGIF_v1_paper_R2_2026-03-18.pdf`
- `06_outputs/paper_drafts/AGIF_v1_paper_R4_2026-03-18.docx`
- `06_outputs/paper_drafts/AGIF_v1_paper_R4_2026-03-18.pdf`

## Intended Verification
- Re-run `python3 scripts/check_phase7_benchmarks.py` so the tracked Phase 7 JSON uses repo-relative config paths.
- Re-run `python3 scripts/check_phase9_closure.py` after the paper-removal note is in place.
- Re-scan the repo for active absolute local-path references before the public visibility change.
