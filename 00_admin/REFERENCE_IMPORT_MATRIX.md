# Reference Import Matrix

Phase 0 rule: register references early, but do not import runtime code before the required phase gate.

| Source area | Source path | Planned destination in this repo | Reason for reuse | Reuse mode | Current status |
| --- | --- | --- | --- | --- | --- |
| Concept paper | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/projects/agif_concept_paper_cleanup/04_execution/agif_concept_paper_clean_v4.md` | `docs/` and paper drafting materials under `06_outputs/` | Preserve AGIF concept language and research framing | Reference-only for now | Registered only; not imported |
| Runner foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/runner/cell` | `runner/cell`, `runner/README.md`, `intelligence/fabric/cli.py`, `intelligence/fabric/registry/loader.py`, and `intelligence/fabric/state_store.py` | Carry forward CLI patterns, fail-closed execution style, bundle validation, and deterministic execution discipline | Adapted locally in Phase 3 | Adapted in this repo; no runtime dependency on old repo |
| Reasoning foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/reasoning_engine.py` | `intelligence/fabric/execution/bounded_executor.py` | Carry forward bounded step execution, timeout policy, budget logic, and trace pattern | Adapted locally in Phase 3 | Adapted in this repo; no runtime dependency on old repo |
| Need-signal foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/background_agent.py` | `intelligence/fabric/needs/engine.py` | Carry forward need scanning and candidate scoring patterns | Adapted locally in Phase 3 | Adapted as a bounded scoring skeleton in this repo; no runtime dependency on old repo |
| Episodic memory foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/episodic_store.py` | `intelligence/fabric/memory/episodic_store.py` | Carry forward bounded local episodic memory pattern | Adapted locally in Phase 3 | Adapted in this repo; no runtime dependency on old repo |
| Suggestions memory foundation | `/Users/ahsadin/Documents/Projects/ENF/AGIF/agif-tasklet-cell/intelligence/suggestions_store.py` | `intelligence/fabric/memory/suggestions_store.py` | Carry forward reviewed-promotion memory pattern | Adapted locally in Phase 3 | Adapted in this repo; no runtime dependency on old repo |

## Import Rules
- The old repo is reference-only.
- Every later import must record:
  - exact source path
  - destination path
  - reason for reuse
  - whether it was copied as-is, adapted, or used only as reference
- No runtime dependency on the old repo is allowed.
