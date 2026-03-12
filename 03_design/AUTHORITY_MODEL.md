# Authority Model

## Phase 2 Freeze Status
- Frozen on `2026-03-12` for Phase 2.
- This document freezes who may propose, evaluate, approve, reject, veto, and contain actions in AGIF v1.

## Frozen Authority Chain
- cells propose local action
- tissues evaluate local structural need
- governance approves or rejects higher-risk transitions
- human policy defines the outer safety boundary

This ordering is locked for v1.

## Frozen Authority Layers
| Layer | Frozen authority | What it may not do alone |
| --- | --- | --- |
| Cell | Perform bounded local work, publish allowed descriptors, write allowed workspace updates, and raise need signals or local proposals | It may not approve its own split, merge, quarantine release, or outer-policy change |
| Tissue coordinator | Evaluate local structural need, route work across cells, and recommend activation, dormancy, split, merge, or reviewer action inside policy | It may not override governance on higher-risk transitions |
| Governance | Approve or reject higher-risk transitions, enforce trust rules, trigger quarantine, approve replay or rollback responses, and maintain decision records | It may not expand the human-defined proof boundary or machine envelope |
| Human policy | Define outer safety boundary, resource envelope, proof domain, allowed tissues, and non-claims | It does not perform routine local runtime decisions inside the fabric |

## Frozen Action Classes

### Cell-Proposable Local Actions
Cells may propose or perform bounded local actions when already inside policy, such as:
- current task execution
- allowed workspace writes
- descriptor creation within allowed kinds
- need-signal emission
- requests for replay, rollback, review, split, merge, hibernation, reactivation, or quarantine

A cell proposal does not equal approval.

### Tissue-Evaluated Structural Need
Tissues evaluate whether local conditions justify structural pressure, including:
- overload
- uncertainty
- novelty
- redundancy
- memory pressure
- trust risk
- coordination gap

Tissues are the first structural evaluator because they see cross-cell coordination context that a single cell does not.

### Governance-Approved Higher-Risk Actions
Governance approval is mandatory for:
- split
- merge
- quarantine release
- retirement
- replay or rollback actions that alter retained state
- fabric-visible memory promotion policies
- any action that changes trust or policy status

### Human-Defined Outer Boundary
Human policy freezes:
- proof domain
- machine envelope
- allowed tissues
- benchmark profile
- outer safety constraints
- non-claims

The fabric may not widen these boundaries on its own.

## Frozen Approval Matrix
| Action | Proposal source | Evaluator | Final approval requirement |
| --- | --- | --- | --- |
| Local task step | cell | local policy checks | cell may proceed if already inside policy |
| Workspace write inside assigned scope | cell | local policy checks | cell may proceed if already inside policy |
| Need-signal creation | cell or tissue | tissue or governance review if escalated | no extra approval to record the signal |
| Reactivation within cap and normal trust | cell or tissue | tissue coordinator | governance only if risk or cap exception exists |
| Hibernate request | cell or tissue | tissue coordinator | governance only if tied to trust or rollback concern |
| Split | cell or tissue | tissue coordinator | governance approval required |
| Merge | cell or tissue | tissue coordinator | tissue coordinator plus governance co-approval required |
| Quarantine request | cell, tissue, or governance | governance | governance may impose directly |
| Quarantine release | governance or human review path | governance | governance approval required |
| Retirement | tissue or governance | governance | governance approval required |
| Memory promotion to shared retained use | cell or reviewer proposal | reviewer and governance policy | reviewed decision required before shared reuse |

## Frozen Merge Approval Quorum
Merge is not valid unless both of these are true:
- the tissue coordinator approves the local structural need
- governance approves the risk, trust, and rollback posture

One without the other is not enough.

## Frozen Split Approval Rule
Split is not valid unless governance approves it after a recorded need signal and policy check.

## Frozen Veto Paths
Governance may veto or contain an action when any of these are true:
- trust risk is unresolved
- policy boundary would be crossed
- replay or rollback coverage is missing
- resource caps would be violated
- lineage or consolidation records are incomplete
- a benchmark safety threshold would be put at risk

When vetoed, the system must record a `veto_ref` rather than silently dropping the request.

## Frozen Quarantine Triggers
Quarantine may be triggered by:
- trust risk
- policy breach
- repeated rollback on the same path
- unsafe or misaligned action evidence
- invalid or conflicting descriptor ancestry
- unresolved merge conflict

While quarantined, a cell may not:
- publish new reusable descriptors
- act on shared workflow tasks
- trigger new structural change except through review paths

## Frozen Need-to-Authority Rule
Need creates pressure. Authority decides.

This means:
- a `NeedSignal` may justify evaluation
- it does not authorize action by itself
- every structural action must map to both:
  - a need signal or equivalent bounded reason
  - an approval chain

## Frozen Human Boundary Rule
The human layer is the only layer allowed to change:
- the proof domain
- the machine envelope
- the benchmark contract
- outer safety policy
- frozen non-claims

Phase 2 itself does not authorize any runtime code to cross those boundaries.

## Verification Status
- Locally verified:
  - the authority chain, approval matrix, veto logic, quarantine triggers, split approval rule, and merge quorum are now frozen in writing
- Assumed only:
  - actual governance engine behavior
  - actual veto and quarantine execution
