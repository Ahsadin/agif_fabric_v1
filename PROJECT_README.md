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
- Phase 3: not started in this thread
- This thread made documentation and tracking changes only. No runtime implementation was started here.

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
- Local verification status is recorded in `01_plan/PROGRESS_TRACKER.md` and `CHANGELOG.md`.
- Runtime behavior is still assumed only because no Phase 3 implementation work was done in this thread.
