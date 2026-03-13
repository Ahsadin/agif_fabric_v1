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

## Current Verified State
- Phase 0: complete and locally verified
- Phase 1: complete and locally verified
- Phase 2: complete in writing and locally verified
- Phase 3: complete and locally verified
- Phase 4: complete and locally verified
- Phase 5: complete and locally verified

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
- Deterministic Phase 5 fixtures now live under `fixtures/document_workflow/phase5/`.
- Deterministic local Phase 5 check script: `scripts/check_phase5_memory.py`

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
- Local verification status is recorded in `01_plan/PROGRESS_TRACKER.md` and `CHANGELOG.md`.
- Later runtime behavior beyond the Phase 5 reviewed memory runtime remains assumed only until later phases verify it.
