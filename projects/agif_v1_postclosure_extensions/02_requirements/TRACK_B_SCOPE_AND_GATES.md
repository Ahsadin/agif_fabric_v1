# Track B Scope And Gates

## Purpose
- This file localizes Track B from the final execution plan so future work can proceed without mixing extension work into the closed AGIF v1 phase history.

## Fixed Denominator
- `15` setup and freeze
- `35` organic split or merge proof
- `35` skill graph and transfer-governance proof
- `45` second bounded proof domain and cross-domain transfer proof

## Tokens
- `AGIF_FABRIC_V1X_SETUP_PASS`
- `AGIF_FABRIC_V1X_G1_PASS`
- `AGIF_FABRIC_V1X_G2_PASS`
- `AGIF_FABRIC_V1X_G3_PASS`
- `AGIF_FABRIC_V1X_PASS`

## Ordered Dependency Rules
1. Setup pass before any other extension pass.
2. Organic load proof before skill-graph proof is counted complete.
3. Skill-graph proof before POS-domain proof is accepted.
4. Bundle close must run the proofs in order and must also confirm root AGIF v1 closure still passes.

## Gap 1 Organic Split Or Merge Proof
- Deterministic finance scenario under normal near-capacity load.
- Fixed stream of `40` cases.
- Control run disables split at the governance level.
- Acceptance requires at least one organically approved split plus a usefulness signal, not just activity.

## Gap 2 Skill Graph
- Add governed descriptor-transfer graph behavior.
- Cross-domain influence must use explicit `transfer_approval`.
- Provenance, abstain, denial, and retirement visibility are required.

## Gap 3 POS Domain
- Add bounded POS operations as a second proof domain.
- Use exactly `5` deterministic POS cases.
- Cross-domain transfer must be causal, governed, and traceable.

## Root Isolation Rules
- Root AGIF v1 stays closed at `600/600`.
- Root `01_plan/PROGRESS_TRACKER.md` does not track extension units.
- Root `05_testing/PASS_TOKENS.md` does not record extension tokens.

