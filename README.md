# AGIF Fabric v1

AGIF v1 is a bounded software proof of a governed intelligence fabric.

This repo claims something narrower and testable: a local, auditable system made of specialized cells can coordinate through tissues, shared workspace state, reviewed memory, bounded adaptation, and explicit governance, and can outperform flatter baselines on structured multi-step work.

## Current Status

- AGIF v1 root closure is complete at `600/600`
- Root closure token earned: `AGIF_FABRIC_P9_PASS`
- Post-closure extension bundle is complete at `130/130`
- Extension bundle token earned: `AGIF_FABRIC_V1X_PASS`
- Public GitHub repo: [github.com/Ahsadin/agif_fabric_v1](https://github.com/Ahsadin/agif_fabric_v1)
- License: MIT

## What This Repo Proves

AGIF v1 now includes:

- a real multi-cell software runtime with bounded lifecycle control
- explicit tissues and shared workspace coordination
- reviewed memory with hot, warm, cold, and ephemeral handling
- routing, authority approval, veto, replay, rollback, and quarantine paths
- a deterministic finance workflow benchmark suite
- real `24h` and real `72h` soak evidence from the MSI soak machine
- a post-closure extension bundle that closes the biggest bounded v1 proof gaps

## Key Results

The public evidence in this repo supports these bounded results:

- the adaptive fabric benchmark reached `1.000` task accuracy versus `0.583` for the flat baseline on the original six-case finance suite
- unsafe or misaligned action rate fell to `0.000` for the multi-cell classes versus `0.500` for the flat baseline
- descriptor reuse causally improved alias-heavy finance cases
- the real `72h` soak completed `1690` cycles while keeping repeated-cycle runtime memory fixed at `1,507,328` bytes
- the post-closure organic-load lane used a deterministic `40`-case finance stream and showed one organically triggered, governance-approved split with no accuracy loss
- the post-closure skill graph added explicit transfer approvals, abstains, denials, and provenance
- the post-closure POS proof added a second bounded domain with `5` deterministic cases and `2` causally improved outcomes from finance-origin transfer

## What The Post-Closure Bundle Added

The post-closure extension work closed three bounded proof gaps:

1. Split or merge under normal organic load
   - closed with a deterministic `40`-case near-capacity finance lane
2. Governed descriptor transfer
   - closed with a skill graph and explicit `transfer_approval`
3. Second proof domain
   - closed with a bounded POS operations suite

That means the current bounded proof set now covers:

- `6` deterministic finance benchmark cases
- `1` deterministic `40`-case finance organic-load lane
- `5` deterministic POS cases

## What This Repo Does Not Claim

This repo does not claim:

- AGI
- open-world general intelligence
- noisy production-scale proof
- proof of the full CellPOS product
- MacBook-only long-run endurance proof

Important machine distinction:

- MacBook Air = development, documentation, benchmark, and primary target machine
- MSI = long-run soak machine

The long-run soak evidence is real, but it is MSI evidence, not MacBook-only endurance proof.

## Best Starting Points

If you want the public truth first, read:

- [PROJECT_README.md](PROJECT_README.md)
- [DECISIONS.md](DECISIONS.md)
- [CHANGELOG.md](CHANGELOG.md)
- [agif_v1_release_note.md](06_outputs/evidence_bundle_manifests/agif_v1_release_note.md)
- [phase9_claims_to_evidence_matrix.md](06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md)
- [phase9_reproducibility_package.md](06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md)

For the post-closure extension evidence:

- [V1X_ORGANIC_LOAD_EVIDENCE.md](05_testing/V1X_ORGANIC_LOAD_EVIDENCE.md)
- [V1X_SKILL_GRAPH_EVIDENCE.md](05_testing/V1X_SKILL_GRAPH_EVIDENCE.md)
- [V1X_POS_DOMAIN_EVIDENCE.md](05_testing/V1X_POS_DOMAIN_EVIDENCE.md)
- [V1X_BUNDLE_CLOSURE_EVIDENCE.md](05_testing/V1X_BUNDLE_CLOSURE_EVIDENCE.md)

## Verification

Root AGIF v1 closure:

```bash
python3 scripts/check_phase9_closure.py
```

Post-closure extension bundle:

```bash
python3 scripts/check_v1x_bundle.py
```

If both pass locally, the repo matches the closed public state described above.
