# V1X Skill Graph Evidence

## Purpose
- This note records the honest Track B Gap 2 proof target for the governed skill-graph and transfer-approval path.

## Gap 2 Frozen Acceptance Path
- A real descriptor graph must exist and stay auditable.
- Cross-domain transfer influence must require explicit `transfer_approval`.
- Approved transfers must carry explicit provenance from the source descriptor and approval record.
- Low-quality transfers must abstain or be denied.
- Retired descriptors must stay visible in the graph and must not become invisible debt.
- The proof must be useful and auditable, not a stub.

## Local Verification Path
- Local verifier command:
  - `python3 scripts/check_v1x_skill_graph.py`
- The verifier is expected to:
  - run `05_testing/test_v1x_skill_graph.py`
  - rebuild the deterministic Gap 2 result tables
  - confirm one approved governed transfer with explicit provenance
  - confirm at least one abstained or denied low-quality path
  - confirm cross-domain transfer requests require explicit `transfer_approval`
  - confirm retired descriptor visibility remains present

## Evidence Artifacts
- Result tables:
  - `06_outputs/result_tables/v1x_skill_graph_transfer.md`
  - `06_outputs/result_tables/v1x_skill_graph_transfer.json`
- Runtime and benchmark code:
  - `intelligence/fabric/descriptors/graph.py`
  - `intelligence/fabric/benchmarking/v1x_skill_graph.py`
  - `scripts/check_v1x_skill_graph.py`

## Scope Boundaries
- This evidence closes Gap 2 only.
- Root AGIF v1 remains closed at `600/600`.
- This evidence does not start Gap 3 and does not claim POS-domain proof.

## Local Verification Completed
- Result: pass
- Command run locally:
  - `python3 scripts/check_v1x_skill_graph.py`
- Verified current proof summary:
  - `3` source descriptors were loaded into the skill graph
  - `1` retired source descriptor stayed visible after retirement
  - `1` governed cross-domain transfer was approved with explicit provenance
  - `1` low-quality transfer abstained
  - `2` transfer requests were denied, including one missing-explicit-approval block and one authority veto at the boundary
- Honest scope note:
  - this proof establishes the governed skill-graph and transfer-approval path only
  - it does not claim POS-domain causality or Gap 3 closure
