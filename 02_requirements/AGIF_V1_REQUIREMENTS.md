# AGIF v1 Requirements

## Purpose
AGIF v1 is a standalone software project that must prove the AGIF architecture in a bounded, local, resource-aware form.

This project must not depend at runtime on the old repo at `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell`. That repo is reference-only.

## Locked Outcome
AGIF v1 must finish with:
- a runnable local AGIF v1 prototype
- a research paper
- benchmark evidence
- a reproducibility package

Public release packaging is out of scope.

## Locked Proof Domain
- AGIF v1 is limited to document/workflow intelligence.
- The first real tissue system is the finance document workflow.
- The first proof must focus on structured, stateful, auditable document work where specialization, memory, reuse, governance, and rollback matter.

## Locked Character of v1
- AGIF v1 is a software-first architectural proof.
- AGIF v1 is not an AGI claim.
- AGIF v1 is local-first.
- AGIF v1 is resource-aware.
- AGIF v1 is anti-bloat by design.

## What AGIF v1 Must Preserve Conceptually
AGIF v1 must preserve the full AGIF architecture in concept, even if the first implementation stays bounded:
- cells
- tissues
- skill descriptors
- shared workspace
- local memory
- fabric memory
- bounded adaptation
- utility and motivation
- governance
- replay
- rollback
- trust
- quarantine
- growth over time
- elastic lifecycle: split, merge, hibernate, reactivate

## What AGIF v1 Does Not Claim Yet
AGIF v1 does not claim to prove:
- large-scale emergence
- self-organizing intelligence at massive scale
- massive autonomous fabric behavior
- real-world embodied intelligence
- AGI-like generality in the broad sense

Those remain part of the long-horizon AGIF path and must stay visible in the design direction.

## Core Product Requirements

### R1. Standalone Local System
- The project root is this workspace.
- All runnable AGIF v1 code, configs, tests, docs, and evidence must live in this workspace.
- Any reused foundation from the old repo must be copied or adapted into this repo with written provenance.

### R2. Software-First Fabric
- AGIF v1 must be built as software-first intelligence fabric, not as a hardware claim.
- The implementation must make the AGIF architecture real in local software form.
- The system must support bounded local execution on the target machine profile.

### R3. Cell Model
- The system must represent cells as bounded, role-specific units.
- Each cell must have a defined identity, role, operating limits, and governed interfaces.
- Cells must be able to participate in the finance workflow proof domain.

### R4. Tissue Model
- The system must support tissues as organized groups of cells.
- The first required tissue is the finance document workflow tissue.
- Tissue behavior must show coordination across multiple bounded cells rather than one flat component pretending to be many cells.

### R5. Skill Descriptor Model
- The system must support compact skill descriptors or descriptor-like records that cells can publish, consume, and govern.
- Descriptors must support routing, reuse, and trust decisions.
- Descriptor handling must be bounded and auditable.

### R6. Shared Workspace
- The system must provide a shared workspace for cross-cell state and task coordination.
- The workspace must separate transient work state from long-term memory.
- Workspace updates must be attributable and suitable for replay.

### R7. Memory Discipline
- The system must support both local and fabric memory.
- Raw logs are not long-term memory.
- Memory must use selective retention, review, and bounded storage rules.
- Memory behavior must support later reuse and evidence generation.

### R8. Bounded Adaptation
- The system must support bounded adaptation in the proof domain.
- Adaptation must happen under explicit limits, review rules, and rollback paths.
- AGIF v1 must not rely on uncontrolled self-modification.

### R9. Utility and Motivation
- The system must represent need pressure, utility, and response selection in explicit system terms.
- Need generates pressure; governance validates the response.
- The implementation must distinguish between a demand signal and permission to act.

### R10. Governance
- Governance must control promotion, trust, execution, memory retention, and recovery actions.
- Governance decisions must be inspectable.
- Governance must be able to reject, quarantine, replay, and roll back bounded changes.

### R11. Lifecycle Control
- The design path must preserve elastic lifecycle operations:
  - split
  - merge
  - hibernate
  - reactivate
- AGIF v1 does not need to prove large-scale self-organization, but it must keep these lifecycle concepts first-class in architecture and later implementation planning.

### R12. Population Discipline
- AGIF v1 must distinguish:
  - fabric population: all cells known to the fabric
  - active runtime population: cells currently instantiated and using live resources
- This distinction must appear in requirements, design, implementation, and benchmark language.

### R13. Resource Discipline
- Primary target machine:
  - Apple M4 MacBook Air
  - 16 GB RAM
  - about 65 GiB free disk at project start
- Target runtime working set: `<= 12 GB`
- Total project and evidence footprint: `<= 35 GB`
- Later benchmarks must report resource use against these limits.

### R14. Evidence Discipline
- AGIF v1 must generate auditable evidence, not just narrative claims.
- The evidence package must be reproducible on the target local machine.
- The paper, benchmarks, and reproducibility package must all refer to the same bounded system claim.

## First Proof Tasks
The first finance document workflow proof must cover a real multi-step workflow, such as:
- intake
- classification
- extraction
- field normalization
- policy or rule checking
- exception detection
- routing or handoff
- audit summary generation

The exact task mix can be refined later, but the workflow must remain document-centered, multi-step, stateful, and auditable.

## Non-Requirements for v1
AGIF v1 does not require:
- public release packaging
- cloud-scale deployment
- production-grade enterprise integration
- hardware embodiment
- proof of open-ended AGI
- proof of massive emergent autonomy

## Frozen Phase 1 Thresholds
The following thresholds are frozen in Phase 1 and must carry forward unchanged unless a later decision record explicitly changes them:
- catastrophic forgetting threshold: `<= 10%`
- unsafe or misaligned action rate: `<= 0.1%`
- resource depletion, overload, or repeated rollback: `<= 5%` operational time
- sample or compute cost to reach bounded target performance: `<= 2x` flat baseline
- runtime working set: `<= 12 GB`
- total project and evidence footprint: `<= 35 GB`

## Phase 1 Exit Condition
Phase 1 is complete when:
- this requirements file freezes the core scope
- `PROOF_BOUNDARY.md` freezes what v1 does and does not prove
- `FALSIFICATION_THRESHOLDS.md` freezes what would count as failure
- the finance workflow proof domain is bounded clearly enough for Phase 2 architecture work
