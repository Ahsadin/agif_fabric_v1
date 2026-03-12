# Decision Gates

## Global Gate Rule
- A phase can start only when the prior phase exit gate is met.
- A phase can close only when its required evidence is written down, `CHANGELOG.md` is updated, and `01_plan/PROGRESS_TRACKER.md` is updated.
- If a gate is passed based on direct local checks, mark it as locally verified.
- If a gate is passed based on planned work or outside evidence, mark it as assumed until local verification exists.

## Phase Entry and Exit Rules

### Phase 0: Bootstrap
- Entry:
  - standalone workspace exists
  - global instructions have been read
  - local `AGENTS.md` exists or is created first
- Exit:
  - required folder structure exists
  - root source-of-truth files exist
  - required admin and planning files exist
  - progress denominator is fixed at `600`
  - locked phase weights are recorded exactly
  - no AGIF runtime code was implemented

### Phase 1: Requirements Freeze
- Entry:
  - Phase 0 exit gate is met
- Exit:
  - requirements documents define scope, proof boundary, and failure conditions
  - the finance workflow proof domain is clearly bounded
  - out-of-scope claims are written down

### Phase 2: Architecture Freeze
- Entry:
  - Phase 1 exit gate is met
- Exit:
  - architecture documents define core models, interfaces, and resource controls
  - interface freeze is written down
  - later interface changes require a `DECISIONS.md` update

### Phase 3: Runner and Fabric Foundation
- Entry:
  - Phase 2 exit gate is met
- Exit:
  - bounded runner and fabric control surfaces exist locally
  - deterministic execution paths are defined
  - base tests for execution behavior pass locally

### Phase 4: Memory, Governance, Workspace, and Lifecycle
- Entry:
  - Phase 3 exit gate is met
- Exit:
  - local and fabric memory paths exist
  - governance, replay, rollback, trust, and quarantine controls exist
  - lifecycle controls for split, merge, hibernate, and reactivate are defined and tested locally

### Phase 5: Finance Workflow Tissue
- Entry:
  - Phase 4 exit gate is met
- Exit:
  - the finance document workflow runs as the first real tissue system
  - proof tasks run within the machine and storage targets
  - benchmark-facing workflow tests pass locally

### Phase 6: Benchmarks and Evidence
- Entry:
  - Phase 5 exit gate is met
- Exit:
  - benchmark contract is active
  - evidence capture is repeatable
  - result tables and manifests can be reproduced locally

### Phase 7: Paper and Reproducibility
- Entry:
  - Phase 6 exit gate is met
- Exit:
  - research paper draft exists
  - reproducibility package exists
  - reported evidence can be regenerated locally from the package

### Phase 8: Reliability and Resource Hardening
- Entry:
  - Phase 7 exit gate is met
- Exit:
  - soak, replay, rollback, and quarantine checks pass locally
  - runtime working set remains at or below `12 GB`
  - total project and evidence footprint remains at or below `35 GB`

### Phase 9: Final Integration
- Entry:
  - Phase 8 exit gate is met
- Exit:
  - local AGIF v1 is runnable end to end
  - final evidence index is complete
  - finish line deliverables are present:
    - runnable local AGIF v1
    - research paper
    - benchmark evidence
    - reproducibility package
  - public release packaging remains out of scope
