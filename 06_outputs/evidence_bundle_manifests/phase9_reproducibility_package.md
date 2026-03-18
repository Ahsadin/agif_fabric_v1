# Phase 9 Reproducibility Package And Evidence Index

## Purpose
This file is the reviewer entrypoint for the final AGIF v1 package in this workspace.

## Machine Roles
- MacBook Air = development, documentation, benchmark, and primary target machine.
- MSI = imported long-run soak evidence machine.
- For AGIF v1, MSI is the final long-run evidence basis and no additional MacBook Air soak is planned or required for closure.
- The package never treats MSI soak artifacts as MacBook Air-only long-run proof.
- The aligned GitHub origin remote for this workspace is `https://github.com/Ahsadin/agif_fabric_v1`.

## Reviewer Quick Start
1. Read `PROJECT_README.md`, `02_requirements/PROOF_BOUNDARY.md`, and `02_requirements/FALSIFICATION_THRESHOLDS.md`.
2. Run `python3 scripts/check_phase9_closure.py` from the repo root.
3. Read `06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md`.
4. Review `06_outputs/result_tables/phase7_benchmark_results.md`.
5. Review `05_testing/MSI_SOAK_MACHINE_NOTE.md`, `05_testing/PHASE8_LONGRUN_EVIDENCE.md`, `06_outputs/run_summaries/phase8_real_24h_soak.md`, and `06_outputs/run_summaries/phase8_real_72h_soak.md`.
6. Read `06_outputs/paper_drafts/README.md` and open the working `R5` paper draft under `06_outputs/paper_drafts/`.

## One-Command Verification Path
- Command:
  - `python3 scripts/check_phase9_closure.py`
- What the command re-runs locally:
  - `python3 scripts/check_phase8_soak.py`
  - `python3 scripts/check_phase7_benchmarks.py` twice for deterministic hash confirmation
- What the command validates without launching a new soak:
  - package files exist and contain the required machine-role and limitation language
  - the working `R5` paper draft, the paper-draft status note, and the MSI soak-machine note exist
  - imported MSI `24h` and `72h` manifests are present
  - imported MSI evidence-file counts and stress-lane pass flags match the recorded summaries
  - repo footprint stays below the locked `35 GB` cap
- What success looks like:
  - the final line is `AGIF_FABRIC_P9_PASS`

## Expected Outputs After Running The Command
- The tracked Phase 7 result files are regenerated locally:
  - `06_outputs/result_tables/phase7_benchmark_results.md`
  - `06_outputs/result_tables/phase7_benchmark_results.json`
- The tracked Phase 8 bounded validation summaries are regenerated locally:
  - `06_outputs/run_summaries/phase8_bounded_validation.md`
  - `06_outputs/run_summaries/phase8_bounded_validation.json`
- No real `24h` or `72h` soak is launched by the Phase 9 command.

## Evidence Index

| Path | What it is | Verification status |
| --- | --- | --- |
| `PROJECT_README.md` | Root project summary and phase state | locally verified |
| `02_requirements/PROOF_BOUNDARY.md` | Locked positive claim, non-claims, and finish-line requirements | locally verified |
| `02_requirements/FALSIFICATION_THRESHOLDS.md` | Frozen hard-fail and support thresholds | locally verified |
| `05_testing/PHASE9_CLOSURE_EVIDENCE.md` | Honest Phase 9 closure note | locally verified |
| `05_testing/MSI_SOAK_MACHINE_NOTE.md` | Canonical MSI soak-machine provenance, before-soak checks, and honest limits | locally verified with MSI artifact inspection |
| `06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md` | Paper-claim to artifact mapping | locally verified |
| `06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md` | This package guide and final evidence index | locally verified |
| `06_outputs/paper_drafts/README.md` | Status note for the public working paper draft | locally verified |
| `06_outputs/paper_drafts/AGIF_v1_paper_R5_2026-03-18.docx` | Working `R5` DOCX paper draft aligned to the current package and GitHub remote | locally verified |
| `06_outputs/paper_drafts/AGIF_v1_paper_R5_2026-03-18.pdf` | Working `R5` PDF paper draft aligned to the current package and GitHub remote | locally verified |
| `06_outputs/result_tables/phase7_benchmark_results.md` | Human-readable benchmark tables | locally verified |
| `06_outputs/result_tables/phase7_benchmark_results.json` | Machine-readable benchmark tables | locally verified |
| `05_testing/PHASE7_TISSUES_BENCHMARK_EVIDENCE.md` | Phase 7 close evidence | locally verified |
| `05_testing/PHASE76_HARDENING_EVIDENCE.md` | Descriptor, custody, and tradeoff hardening evidence | locally verified |
| `05_testing/PHASE8_LONGRUN_EVIDENCE.md` | Combined bounded plus real `24h` and `72h` long-run note | locally verified with MSI artifact inspection |
| `06_outputs/run_summaries/phase8_bounded_validation.md` | Bounded Phase 8 summary | locally verified |
| `06_outputs/run_summaries/phase8_real_24h_soak.md` | Narrative real `24h` MSI soak summary | locally verified with MSI artifact inspection |
| `06_outputs/run_summaries/phase8_real_72h_soak.md` | Narrative real `72h` MSI soak summary | locally verified with MSI artifact inspection |
| `08_logs/phase8_soak/run_24h/` | Imported MSI `24h` manifest, evidence, and stress artifacts | locally inspected |
| `08_logs/phase8_soak/run_72h/` | Imported MSI `72h` manifest, evidence, stress artifacts, and runtime state | locally inspected |
| `scripts/check_phase9_closure.py` | One-command Phase 9 verifier | locally verified |

## What Is Locally Verified
- The full Phase 3 to Phase 8 bounded runtime and benchmark chain.
- The Phase 7 result tables stay stable across repeated fresh reruns.
- The Phase 8 bounded validation summaries regenerate locally.
- The working `R5` paper draft, paper-draft status note, MSI soak-machine note, claims matrix, and reproducibility package now exist inside this workspace.
- The repo footprint stays well below the locked `35 GB` cap.

## What Is MSI Evidence
- The real `24h` soak artifacts under `08_logs/phase8_soak/run_24h/`.
- The real `72h` soak artifacts under `08_logs/phase8_soak/run_72h/`.
- The reviewer should read these as imported MSI endurance evidence that is inspected locally, not as MacBook Air-only long-run proof.

## What Remains Outside Proof
- MacBook Air-only multi-day long-run endurance. This remains a non-claim, not a pending closure item.
- Full OS-restart or lid-close continuity beyond the documented checkpoint-boundary resume evidence.
- Split or merge efficiency under sustained organic near-capacity normal load.
- AGI, broad open-world generality, or unrestricted self-improvement.
- A final published paper. The repo includes a working `R5` draft, not the final publication.
