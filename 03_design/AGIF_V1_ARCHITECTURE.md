# AGIF v1 Architecture

## Phase 2 Freeze Status
- Frozen on `2026-03-12` for Phase 2.
- This document freezes architecture only. It does not claim that runtime behavior already exists.
- No frozen architecture decision in this file may change later without a matching update in `DECISIONS.md`.

## Goal
AGIF v1 is a software-first, local-first architectural proof of the AGIF concept inside a bounded document/workflow domain.

The first real tissue system is the finance document workflow. Phase 2 freezes the architecture so Phase 3 can start implementation without design ambiguity.

## Locked Architectural Completeness
AGIF v1 must preserve all of these AGIF pillars conceptually in v1 architecture:
- cells
- tissues
- skill descriptors
- shared workspace
- local and fabric memory
- bounded adaptation
- utility and motivation
- governance
- replay, rollback, trust, and quarantine
- growth over time
- elastic split, merge, hibernate, and reactivate lifecycle

AGIF v1 also keeps the long-horizon AGIF path visible. V1 does not remove or deny the broader path toward:
- large-scale emergence
- self-organizing intelligence
- massive autonomous fabric behavior
- real-world embodied intelligence
- AGI-like generality

V1 does not claim those long-horizon properties are already proven. The locked proof claim stays limited to document/workflow intelligence.

## Locked Proof Boundary
- Proof domain: document/workflow intelligence
- First real tissue system: finance document workflow
- First proof character: structured, stateful, auditable document work
- Finish line remains:
  - runnable local AGIF v1
  - research paper
  - benchmark evidence
  - reproducibility package

## Frozen Machine Envelope
AGIF v1 architecture is locked to this primary machine target:
- Apple M4 MacBook Air
- `16 GB` RAM
- about `65 GiB` free disk
- runtime working set `<= 12 GB`
- total project and evidence footprint `<= 35 GB`

These limits are architecture constraints, not later optimization goals. All later design and implementation choices must fit them.

## Core Architectural Layers
| Layer | Frozen responsibility | Notes |
| --- | --- | --- |
| Human policy boundary | Defines outer safety limits, allowed proof domain, allowed tissues, machine envelope, and non-claims. | Human policy is outside the fabric and has final veto authority. |
| Governance plane | Reviews risky actions, approves or rejects structural change, controls trust, replay, rollback, and quarantine. | Governance is required for high-risk transitions. |
| Tissue coordination plane | Organizes cells into workflow-capable groups, evaluates structural need, and manages local coordination pressure. | Tissues are not optional wrappers; they are real coordination units. |
| Cell execution plane | Runs bounded role-specific work, emits descriptors, writes to workspace, and proposes need-driven actions. | Cells are specialized, bounded, and policy-limited. |
| Shared workspace plane | Holds cross-cell task state, handoffs, and replayable work context. | Workspace is not long-term memory. |
| Memory plane | Separates local memory, fabric memory, and evidence/log storage under bounded retention rules. | Raw logs are evidence only unless reviewed and promoted. |
| Replay and evidence plane | Stores lifecycle, memory, and governance traces needed for replay, rollback, benchmark evidence, and reproducibility. | Replayability is part of the architecture, not a later add-on. |

## Frozen Structural Units

### Fabric
The fabric is the whole bounded AGIF v1 system. It owns:
- global configuration
- blueprint registry
- active and logical population caps
- workspace policy
- governance policy
- need-signal policy
- benchmark profile
- memory and storage caps

### Tissues
Tissues are organized groups of cells with a workflow purpose. In v1, the first real tissue system is the finance document workflow.

Phase 2 freezes the requirement that tissues exist as real organizing units, not naming wrappers over a flat script.

### Cells
Cells are bounded, role-specific units. Each cell must have:
- stable identity
- lineage tracking
- role family and role name
- trust and policy envelope
- resource budget
- allowed tissues
- utility profile
- descriptor publication and consumption limits

### Descriptors
Descriptors are compact, governed records that cells publish for reuse. They support:
- routing
- reuse
- trust evaluation
- later bounded adaptation
- replay and audit

### Need Signals
Need signals create pressure to adapt or reorganize. They do not grant permission by themselves. They must be evaluated by the authority chain.

### Ledgered Control Events
Lifecycle changes, memory promotion decisions, governance actions, and replay or rollback outcomes must be recorded in replayable form. No major structural change is allowed to exist only in transient runtime state.

## Frozen Population Model
AGIF v1 must distinguish between:
- fabric population: every cell blueprint or lineage member known to the fabric
- active runtime population: the cells currently instantiated and consuming live resources

This distinction is frozen and must appear in architecture, implementation, benchmarks, and reporting.

The architecture assumes:
- active population is the scarce resource controlled by `active_population_cap`
- logical population may exceed active population and is controlled separately by `logical_population_cap`
- dormant cells keep identity without consuming the active runtime budget

## Frozen Control Loops

### 1. Task Execution Loop
1. A workflow enters through the fabric runner.
2. The fabric activates or reuses the needed cells.
3. Cells read from the shared workspace, perform bounded work, and write bounded results.
4. Cells may emit descriptors, need signals, and evidence refs.

### 2. Need and Utility Loop
1. Cells or tissues detect pressure such as overload, uncertainty, novelty, redundancy, memory pressure, trust risk, or coordination gaps.
2. The pressure is recorded as a `NeedSignal`.
3. Utility and policy context determine whether the proposed response is valuable enough to evaluate.
4. Authority decides whether the response is allowed.

### 3. Memory Loop
1. Work produces transient artifacts in workspace and logs.
2. Candidate memory or descriptor artifacts are reviewed.
3. Reviewed artifacts may be promoted, compressed, deferred, rejected, or retired.
4. Fabric memory remains bounded through retention, consolidation, and intentional forgetting.

### 4. Lifecycle Loop
1. Cells begin as seed or dormant fabric members.
2. Demand or policy may activate them.
3. Need pressure may lead to split, merge, hibernate, reactivation, quarantine, or retirement paths.
4. Every structural change must be justified, approved when required, and recorded with rollback linkage.

### 5. Recovery Loop
1. Governance or replay tooling can reconstruct prior bounded states.
2. Bad descriptors, bad structural moves, or unsafe actions can trigger quarantine or rollback.
3. Trust and lineage history stay inspectable after recovery events.

## Finance Workflow Tissue Scope
The first proof tissue must support a real finance document workflow with multi-step, auditable work such as:
- intake
- classification
- extraction
- field normalization
- policy or rule checking
- exception detection
- routing or handoff
- audit summary generation

Phase 2 does not freeze exact implementation classes or filenames for these roles. It does freeze that the first proof must be a real multi-cell tissue in this domain.

## Frozen Non-Claims
This architecture freeze does not claim:
- a runnable AGIF v1 already exists
- benchmark results already exist
- broad AGI has been demonstrated
- large-scale emergence has been demonstrated
- embodied intelligence has been demonstrated

## Phase 3 Entry Rule
Phase 3 must not begin until:
- all six Phase 2 design docs exist
- all frozen interfaces are written clearly
- all state transitions are written clearly
- all CLI contracts are frozen
- all benchmark classes and metrics are frozen
- the Phase 2 gate is marked complete in `01_plan/PHASE_GATE_CHECKLIST.md`

## Verification Status
- Locally verified:
  - this architecture freeze is written in this workspace
  - the proof boundary, machine envelope, and preserved AGIF pillars are explicit in writing
- Assumed only:
  - runtime behavior
  - benchmark outcomes
  - future implementation quality
