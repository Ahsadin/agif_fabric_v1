# AGIF v1 Post-Closure Extensions Project README

## Goal
- Strengthen AGIF v1 after closure through three separate proof extensions without reopening the closed AGIF v1 phase history.

## Relation To Root AGIF v1
- Root AGIF v1 remains closed at `600/600`.
- Root AGIF v1 source-of-truth files remain the closed v1 record.
- This project tracks only the separate post-closure extension work.
- Track B progress must never be counted inside the root AGIF v1 tracker.

## Fixed Denominator
- Total extension denominator: `130`
- Weight split:
  - setup and freeze: `15`
  - organic split or merge proof: `35`
  - skill graph and transfer-governance proof: `35`
  - second bounded proof domain and cross-domain transfer proof: `45`

## Extension Tokens
- `AGIF_FABRIC_V1X_SETUP_PASS`
- `AGIF_FABRIC_V1X_G1_PASS`
- `AGIF_FABRIC_V1X_G2_PASS`
- `AGIF_FABRIC_V1X_G3_PASS`
- `AGIF_FABRIC_V1X_PASS`

## Ordered Dependency Rules
1. Setup pass must be earned first.
2. Organic load proof must pass before skill-graph proof is treated as complete.
3. Skill-graph proof must pass before POS-domain proof is accepted.
4. Final bundle verifier must run in order: Gap 1, then Gap 2, then Gap 3.
5. Final bundle closure must re-check the root AGIF v1 closure path and confirm root progress still reads `600/600`.

## Current Status
- Setup-and-freeze gate is closed.
- `AGIF_FABRIC_V1X_SETUP_PASS` is earned.
- Gap 1 organic split or merge proof is closed honestly.
- `AGIF_FABRIC_V1X_G1_PASS` is earned.
- Gap 2 skill graph and transfer-governance proof is closed honestly.
- `AGIF_FABRIC_V1X_G2_PASS` is earned.
- Current extension progress: `85/130`

## In Scope
- project-local planning and freeze records
- organic split or merge usefulness proof under normal near-capacity load
- governed skill-graph and transfer-approval proof
- bounded POS operations proof with causal cross-domain transfer evidence

## Out Of Scope
- changing root AGIF v1 phase completion
- changing root AGIF v1 progress from `600/600`
- claiming AGI or broad open-world generality
- silently replacing the closed AGIF v1 finance-only proof with extension claims

## Root Tracker Isolation
- Root `01_plan/PROGRESS_TRACKER.md` remains frozen at `600/600`.
- Track B progress is recorded only in `projects/agif_v1_postclosure_extensions/01_plan/PROGRESS_TRACKER.md`.
- Root AGIF v1 pass tokens remain unchanged during Track B work.

## Frozen Gap 1 Start Rules
- Gap 1 uses one deterministic fixed stream of `40` cases.
- The elastic run and the no-split control run must use the same `40`-case sequence in the same order.
- No fake stress-mode switch is allowed inside the stream to force the result.
- The control run disables split at the governance level.
- If no organic split occurs inside the `40`-case stream, the Gap 1 acceptance gate fails.

## Frozen Gap 3 Start Rules
- Gap 3 uses the same `5` deterministic POS cases for both comparison runs.
- The control run disables cross-domain transfer at the governance level.
- The transfer-enabled run uses the same suite and the same order.
- Cross-domain influence counts only when there is explicit `transfer_approval`.

## Expected Root-Level Runtime Touch Points Later
- `fixtures/document_workflow/v1x/finance_organic_load/`
- `fixtures/pos_operations/v1x/`
- `intelligence/fabric/descriptors/`
- `intelligence/fabric/domain/pos_operations.py`
- `scripts/check_v1x_organic_load.py`
- `scripts/check_v1x_skill_graph.py`
- `scripts/check_v1x_pos_domain.py`
- `scripts/check_v1x_bundle.py`

## Current Verification
- `python3 scripts/check_v1x_setup.py` passes locally.
- `python3 scripts/check_v1x_organic_load.py` passes locally.
- `python3 scripts/check_v1x_skill_graph.py` passes locally.
- Root AGIF v1 remains closed at `600/600`.
- Root tracker isolation is explicit in the Track B docs.
- Gap 1 is now locally verified by:
  - `fixtures/document_workflow/v1x/finance_organic_load/benchmark_sequence.json`
  - `05_testing/V1X_ORGANIC_LOAD_EVIDENCE.md`
  - `06_outputs/result_tables/v1x_finance_organic_load.md`
  - `06_outputs/result_tables/v1x_finance_organic_load.json`
  - `scripts/check_v1x_organic_load.py`
- Gap 2 is now locally verified by:
  - `fixtures/document_workflow/v1x/skill_graph/minimal_fabric_config.json`
  - `fixtures/document_workflow/v1x/skill_graph/transfer_suite.json`
  - `intelligence/fabric/descriptors/graph.py`
  - `05_testing/V1X_SKILL_GRAPH_EVIDENCE.md`
  - `06_outputs/result_tables/v1x_skill_graph_transfer.md`
  - `06_outputs/result_tables/v1x_skill_graph_transfer.json`
  - `scripts/check_v1x_skill_graph.py`
- Gap 2 current proof result is:
  - `3` source descriptors in the graph
  - `1` retired source descriptor still visible
  - `1` approved governed cross-domain transfer with explicit provenance
  - `1` low-quality abstain
  - `2` denials, including one missing explicit `transfer_approval` and one authority veto at the boundary
- Gap 3 start rules remain frozen for later execution work.
