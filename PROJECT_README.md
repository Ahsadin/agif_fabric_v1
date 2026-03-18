# AGIF v1 Project README

## Goal
Build AGIF v1 as a software-first, architecturally complete, resource-aware intelligence fabric in this standalone workspace.

## Authoritative Plan
- The controlling execution plan for this workspace is `/Users/ahsadin/Downloads/PLAN.md`.

## Locked Context
- This project is standalone. This folder is the single source of truth for AGIF v1 work.
- The old repo at `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell` is reference-only.
- AGIF v1 preserves the full AGIF vision conceptually, including cells, tissues, memory, governance, lifecycle control, and long-horizon growth.
- The proof domain for v1 is document/workflow intelligence.
- The first proof tissue is the finance document workflow.
- The finish line for this initiative is:
  - runnable local AGIF v1
  - research paper
  - benchmark evidence
  - reproducibility package
- Public release packaging is out of scope for this initiative.

## Resource Targets
- Target machine: Apple M4 MacBook Air
- RAM: 16 GB
- Free disk at start: about 65 GiB
- Runtime working set target: `<= 12 GB`
- Total project and evidence footprint target: `<= 35 GB`

## Machine Roles
- MacBook Air = main development, working, documentation, and primary target machine.
- MSI = soak machine for long-run endurance evidence.
- For AGIF v1, the imported MSI soak artifacts are the final long-run evidence basis.
- Those MSI artifacts do not become MacBook Air-only proof.

## Current Verified State
- Phase 0: complete and locally verified
- Phase 1: complete and locally verified
- Phase 2: complete in writing and locally verified
- Phase 3: complete and locally verified
- Phase 4: complete and locally verified
- Phase 5: complete and locally verified
- Phase 6: complete and locally verified
- Phase 4.5 + 5.5 hardening: complete and locally verified without changing project units
- Phase 6.5 hardening: complete and locally verified without changing project units
- Phase 7: complete and locally verified
- Phase 7.5 hardening: complete and locally verified without changing project units
- Phase 7.6 hardening: complete and locally verified without changing project units
- Phase 8: complete and locally verified through bounded harness checks plus real `24h` and real `72h` MSI soak evidence; `AGIF_FABRIC_P8_PASS` is earned
- Phase 8.5 hardening: complete and locally verified as part of the now-closed Phase 8 evidence layer
- Phase 9: complete and locally verified through repo-local paper copies, a claims-to-evidence matrix, a reproducibility package and evidence index, and a one-command closure check; `AGIF_FABRIC_P9_PASS` is earned

## Project Closure Status
- AGIF v1 is closed in this repo.
- The locked AGIF v1 finish line is complete.
- Future expansion work belongs to AGIF v2, not to additional AGIF v1 scope in this workspace history.
- This does not reopen or weaken the AGIF v1 non-claims.

## Phase 3 Foundation
- Local runner entrypoint: `runner/cell`
- Frozen commands now implemented:
  - `runner/cell fabric init`
  - `runner/cell fabric run`
  - `runner/cell fabric status`
  - `runner/cell fabric replay`
  - `runner/cell fabric evidence`
- Local blueprint registry committed for the finance workflow proof domain.
- Deterministic local check script: `scripts/check_phase3_foundation.py`

## Phase 4 Lifecycle Runtime
- Logical population and active runtime population are now tracked separately in the local fabric runtime state.
- Dormant blueprint storage, activation, split, merge, hibernate, reactivate, retire, lineage ledger, veto log, and rollback snapshots now exist locally.
- Split now rejects weak pressure, records usefulness reasons, and exposes structural usefulness and lineage usefulness summaries.
- Hibernate now packs compact dormancy profiles, reactivation restores preserved context, and repeated activate/hibernate oscillation is bounded.
- The local proof target is now verified for:
  - logical population cap `128`
  - steady active population `24`
  - burst active population `48`
  - automatic return from burst to steady after consolidation
- Deterministic Phase 4 fixtures now live under `fixtures/document_workflow/phase4/`.
- Deterministic local Phase 4 check script: `scripts/check_phase4_lifecycle.py`

## Phase 5 Reviewed Memory Runtime
- Reviewed memory now uses explicit hot, warm, cold, and ephemeral stores under the local fabric state root.
- Hot memory now tracks active workspace refs, current task refs, live runtime state refs, and short review buffers.
- Warm memory now holds recent trusted descriptors and promoted summaries.
- Cold memory now holds quantized long-term state and archived reproducibility traces.
- Raw logs remain in the separate ephemeral store and are never promoted directly into long-term memory.
- Reviewed promotion now records frozen `MemoryPromotionDecision` objects for reject, defer, promote, compress, and retire paths.
- Deduplication, supersession, bounded replay, garbage collection, and memory-pressure consolidation now exist locally.
- Reviewer scoring now weighs novelty, usefulness, trust, reuse potential, compression gain, and conflict risk before promotion.
- Trust-weighted conflict handling now defers weaker conflicting memory, duplicate review now reuses the existing promoted artifact, and pressure handling now prefers lower-priority memory for consolidation or retirement.
- Memory summary now reports reuse, supersession, duplicate compression gain, stale retirement rate, and retention priorities.
- Deterministic Phase 5 fixtures now live under `fixtures/document_workflow/phase5/`.
- Deterministic local Phase 5 check script: `scripts/check_phase5_memory.py`

## Phase 6 Routing And Authority Runtime
- Need signals now support runtime generation, severity normalization, expiry handling, status transitions, and traceable resolution beyond the earlier lifecycle and memory proof paths.
- Routing now evaluates multiple candidates with role fit, reviewed descriptor usefulness, trust, current load, need pressure, workspace context, and utility scoring.
- Authority now records approvals and vetoes for higher-risk descriptor use, memory-driven runtime influence, risky reactivation, split, merge, and quarantine escalation.
- Runtime summaries now expose active need signals, routing decisions, utility traces, descriptor use, approvals, vetoes, and authority outcomes.
- Phase 6.5 hardening adds route confidence, explicit abstain or escalate paths, recurring-need detection, route success or failure memory, descriptor provenance influence, lineage-aware routing and authority review, and authority veto-pattern memory.
- Deterministic Phase 6 fixtures now live under `fixtures/document_workflow/phase6/`.
- Deterministic local Phase 6 check script: `scripts/check_phase6_routing_authority.py`

## Phase 7 Domain Tissues And Benchmarks
- Real finance tissues now exist through dedicated Phase 7 registries for:
  - intake and routing
  - extraction
  - validation and correction
  - anomaly and reviewer
  - workspace and governance
  - reporting and output
- The bounded finance workflow now runs end to end through the actual tissue stages and shared workspace with traceable handoffs.
- The frozen benchmark classes are now locally runnable and comparable:
  - flat baseline
  - multi-cell fabric without bounded adaptation
  - multi-cell fabric with bounded adaptation and descriptor sharing
- Deterministic Phase 7 fixtures now live under `fixtures/document_workflow/phase7/`.
- Deterministic local Phase 7 check script: `scripts/check_phase7_benchmarks.py`
- Current Phase 7 result tables now live under `06_outputs/result_tables/phase7_benchmark_results.md` and `06_outputs/result_tables/phase7_benchmark_results.json`.
- Phase 7.5 hardening strengthens the same benchmark system with:
  - two additional deterministic invoice cases
  - explicit counterfactual comparison notes
  - tissue usefulness, burden, and reuse analytics
  - retained-memory and runtime-overhead deltas
  - explicit structural-pressure signals when split or merge remains unexecuted
- Phase 7.5 hardening evidence now lives at `05_testing/PHASE75_HARDENING_EVIDENCE.md`.
- Phase 7.6 hardening further strengthens the same Phase 7 benchmark system with:
  - one more deterministic governance-sensitive alias case
  - reconciled correction-memory vendor matching across quantized supersession
  - route-of-custody summaries per case
  - explicit descriptor-memory and need-resolution evidence
  - confidence-aware outcome summaries
  - adaptation tradeoff reporting
  - more explicit structural-pressure and no-action explanations
- Phase 7.6 hardening evidence now lives at `05_testing/PHASE76_HARDENING_EVIDENCE.md`.

## Phase 8 Long-Run Harness
- Deterministic Phase 8 fixtures now live under `fixtures/document_workflow/phase8/`.
- Phase 8 now has a resumable soak harness:
  - `scripts/run_phase8_soak.py`
  - `scripts/check_phase8_soak.py`
- The bounded local Phase 8 validation now captures:
  - repeated finance workflow cycles with descriptor reuse and reviewed memory carry-forward
  - a Phase 7.6-aligned governance-sensitive reuse hold case inside the repeated mix
  - split and merge stress
  - memory saturation pressure and bounded consolidation
  - routing pressure abstain-and-recover behavior
  - trust and quarantine fault injection
  - replay and rollback recovery
- The Phase 8.5 hardening layer now adds:
  - stronger cycle-health metrics over time
  - explicit drift indicators
  - checkpoint-boundary resume realism checks
  - memory-quality and governance-quality summaries
  - a bounded failure taxonomy and clearer blocker reporting
- The current bounded validation summary lives at:
  - `06_outputs/run_summaries/phase8_bounded_validation.md`
  - `06_outputs/run_summaries/phase8_bounded_validation.json`
- The current real `24h` soak summary lives at:
  - `06_outputs/run_summaries/phase8_real_24h_soak.md`
  - `06_outputs/run_summaries/phase8_real_24h_soak.json`
- The current real `72h` soak summary lives at:
  - `06_outputs/run_summaries/phase8_real_72h_soak.md`
  - `06_outputs/run_summaries/phase8_real_72h_soak.json`
- The current Phase 8 evidence note lives at `05_testing/PHASE8_LONGRUN_EVIDENCE.md`.
- The current Phase 8.5 hardening note lives at `05_testing/PHASE85_HARDENING_EVIDENCE.md`.
- The current Phase 8 state is closed honestly:
  - the harness and bounded validation are locally verified on the MacBook Air development/documentation machine
  - real `24h` and real `72h` soak evidence are completed and extracted from the MSI soak machine
  - for AGIF v1, MSI is the final long-run evidence basis
  - `AGIF_FABRIC_P8_PASS` is earned
  - recorded project progress is now `570/600`
  - this still does not claim MacBook Air-only long-run endurance
  - the recurring `WinError 5` manifest-write interruption in the long-run MSI artifacts is documented as an evidence caveat, not hidden

## Phase 9 Paper, Claims Matrix, And Reproducibility Package
- Repo-local paper copies now live under:
  - `06_outputs/paper_drafts/AGIF_v1_paper_R2_2026-03-18.docx`
  - `06_outputs/paper_drafts/AGIF_v1_paper_R2_2026-03-18.pdf`
- Repo-local claims-to-evidence mapping now lives at:
  - `06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md`
- Repo-local reproducibility package and final evidence index now live at:
  - `06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md`
- The Phase 9 closure evidence note now lives at:
  - `05_testing/PHASE9_CLOSURE_EVIDENCE.md`
- The one-command Phase 9 closure check now lives at:
  - `scripts/check_phase9_closure.py`
- The current Phase 9 state is closed honestly:
  - the earlier Phase 3 to Phase 8 runtime, benchmark, and MSI soak claims are now mapped to repo-local artifacts
  - the research paper, claims matrix, benchmark evidence, and reproducibility package are now all present inside this workspace
  - `python3 scripts/check_phase9_closure.py` passes locally
  - `AGIF_FABRIC_P9_PASS` is earned
  - recorded project progress is now `600/600`
  - no future MacBook Air soak is planned or required for AGIF v1 closure
  - this still does not claim MacBook Air-only long-run endurance
  - this still does not claim AGI or broad open-world generality

## Phase 2 Freeze Set
- `03_design/AGIF_V1_ARCHITECTURE.md`
- `03_design/INTERFACE_FREEZE.md`
- `03_design/MEMORY_MODEL.md`
- `03_design/LIFECYCLE_MODEL.md`
- `03_design/AUTHORITY_MODEL.md`
- `03_design/BENCHMARK_CONTRACT.md`

## Project Structure
- Root source-of-truth:
  - `PROJECT_README.md`
  - `DECISIONS.md`
  - `CHANGELOG.md`
- Control and tracking:
  - `00_admin/`
  - `01_plan/`
- Future execution areas:
  - `02_requirements/`
  - `03_design/`
  - `04_execution/`
  - `05_testing/`
  - `06_outputs/`
  - `07_assets/`
  - `08_logs/`
  - `docs/`
  - `runner/`
  - `cells/`
  - `intelligence/`
  - `personalization/`
  - `fixtures/`
  - `scripts/`
- Plan-required supporting paths:
  - `00_admin/codex_threads/handoffs/`
  - `00_admin/codex_threads/archive/`
  - `06_outputs/paper_drafts/`
  - `06_outputs/figures/`
  - `06_outputs/result_tables/`
  - `06_outputs/evidence_bundle_manifests/`

## Verification
- Phase 0 verification method: confirm the required folders and bootstrap files exist in this workspace.
- Phase 1 verification method: confirm the required requirement and proof-boundary files exist and state the bounded claim clearly.
- Phase 2 verification method: confirm the six design freeze docs exist and that the gate checklist and progress tracker record the freeze consistently.
- Phase 3 verification method: run the deterministic runner foundation check and confirm the Phase 3 pass token and evidence note.
- Phase 4 verification method: run the deterministic lifecycle and lineage check and confirm the Phase 4 pass token and evidence note.
- Phase 5 verification method: run the deterministic reviewed-memory check and confirm the Phase 5 pass token and evidence note.
- Phase 6 verification method: run the deterministic routing and authority check and confirm the Phase 6 pass token and evidence note.
- Hardening verification method: run the Phase 4 and Phase 5 deterministic checks again and confirm `05_testing/PHASE45_HARDENING_EVIDENCE.md`.
- Phase 6.5 hardening verification method: run `python3 scripts/check_phase6_routing_authority.py` and confirm `05_testing/PHASE65_HARDENING_EVIDENCE.md`.
- Phase 7 verification method: run `python3 scripts/check_phase7_benchmarks.py` and confirm `05_testing/PHASE7_TISSUES_BENCHMARK_EVIDENCE.md`.
- Phase 7.5 hardening verification method: run `python3 scripts/check_phase7_benchmarks.py` and confirm `05_testing/PHASE75_HARDENING_EVIDENCE.md`.
- Phase 7.6 hardening verification method: run `python3 scripts/check_phase7_benchmarks.py` and confirm `05_testing/PHASE76_HARDENING_EVIDENCE.md`.
- Phase 8 harness verification method: run `python3 scripts/check_phase8_soak.py` and confirm the bounded summary under `06_outputs/run_summaries/` plus `05_testing/PHASE8_LONGRUN_EVIDENCE.md` and `05_testing/PHASE85_HARDENING_EVIDENCE.md`.
- Phase 9 closure verification method: run `python3 scripts/check_phase9_closure.py` and confirm the workspace paper copies, the claims matrix, the reproducibility package and evidence index, the Phase 7 deterministic rerun hash check, and the imported MSI `24h` and `72h` artifact counts.
- Local verification status is recorded in `01_plan/PROGRESS_TRACKER.md` and `CHANGELOG.md`.
- Real `24h` soak evidence is now recorded from imported MSI artifacts under `08_logs/phase8_soak/run_24h/`.
- Real `72h` soak evidence is now recorded from imported MSI artifacts under `08_logs/phase8_soak/run_72h/`.
- Phase 8 is now closed honestly through the bounded harness plus the real `24h` and real `72h` MSI soak evidence.
- For AGIF v1, MSI remains the final long-run evidence basis and no future MacBook Air soak is planned or required for project closure.
- Phase 9 is now closed honestly through the repo-local paper copies, the claims matrix, the reproducibility package, the final evidence index, and the one-command closure check.
- AGI-like generality and broader open-world claims remain outside the locked proof boundary.
