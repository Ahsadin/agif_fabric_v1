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
- Phase 6: complete and locally verified
- Phase 4.5 + 5.5 hardening: complete and locally verified without changing project units
- Phase 6.5 hardening: complete and locally verified without changing project units

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
- Local verification status is recorded in `01_plan/PROGRESS_TRACKER.md` and `CHANGELOG.md`.
- Later runtime behavior beyond the Phase 6 governed routing runtime remains assumed only until later phases verify it.
