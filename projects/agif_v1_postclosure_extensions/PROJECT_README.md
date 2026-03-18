# AGIF v1 Post-Closure Extensions Project README

## Goal
- Strengthen AGIF v1 after closure through three separate proof extensions without reopening the closed AGIF v1 phase history.

## Relation To Root AGIF v1
- Root AGIF v1 remains closed at `600/600`.
- Root AGIF v1 source-of-truth files remain the closed v1 record.
- This project tracks only the separate post-closure extension work.

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
4. Final bundle closure must re-check the root AGIF v1 closure path and confirm root progress still reads `600/600`.

## Current Status
- Project scaffold created.
- No extension tokens earned yet.
- Current extension progress: `0/130`

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
- Confirm this project folder exists with its local source-of-truth files.
- Confirm root AGIF v1 remains closed at `600/600`.
- Confirm no extension tokens are recorded as earned yet.

