# Reference Import Matrix

Phase 0 rule: register references now, but do not import runtime code yet.

| Source area | Source path | Planned destination in this repo | Reason for reuse | Reuse mode | Phase 0 status |
| --- | --- | --- | --- | --- | --- |
| Concept paper | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/projects/agif_concept_paper_cleanup/04_execution/agif_concept_paper_clean_v4.md` | `docs/` and paper drafting materials under `06_outputs/` | Preserve AGIF concept language and research framing | Reference-only for now | Registered only; not imported |
| Runner foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/runner/cell` | `runner/cell` | Carry forward CLI patterns, fail-closed execution style, bundle validation, and deterministic execution discipline | Adapt later | Registered only; not imported |
| Reasoning foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/reasoning_engine.py` | `intelligence/fabric/execution/` | Carry forward bounded step execution, timeout policy, budget logic, and trace pattern | Adapt later | Registered only; not imported |
| Need-signal foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/background_agent.py` | `intelligence/fabric/needs/` | Carry forward need scanning and candidate scoring patterns | Adapt later | Registered only; not imported |
| Episodic memory foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/episodic_store.py` | `intelligence/fabric/memory/` | Carry forward bounded local episodic memory pattern | Adapt later | Registered only; not imported |
| Suggestions memory foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/suggestions_store.py` | `intelligence/fabric/memory/` | Carry forward reviewed-promotion memory pattern | Adapt later | Registered only; not imported |

## Import Rules
- The old repo is reference-only.
- Every later import must record:
  - exact source path
  - destination path
  - reason for reuse
  - whether it was copied as-is, adapted, or used only as reference
- No runtime dependency on the old repo is allowed.
