# AGIF Fabric v1

**AGIF v1 is a bounded software proof of a governed intelligence fabric.**

This repo claims something narrower and testable: a local, auditable system made of specialized cells can coordinate through tissues, shared workspace state, reviewed memory, bounded adaptation, and explicit governance — and can outperform flatter baselines on structured multi-step work.

---

## Current Status

| Item | Status |
|---|---|
| Root v1 closure | **600/600 complete** |
| Root closure token | `AGIF_FABRIC_P9_PASS` |
| Post-closure extension bundle | **130/130 complete** |
| Extension bundle token | `AGIF_FABRIC_V1X_PASS` |
| Public repo | [github.com/Ahsadin/agif_fabric_v1](https://github.com/Ahsadin/agif_fabric_v1) |
| License | MIT |

---

## Requirements

Python 3.11 or later. No external dependencies beyond the standard library.

---

## What This Repo Proves

AGIF v1 is a working local software system, not a concept. The repo contains:

- a real multi-cell software runtime with bounded lifecycle control
- explicit tissues and shared workspace coordination across 5 traced handoffs per case
- reviewed memory with hot, warm, cold, and ephemeral tier handling
- routing, authority approval, veto, replay, rollback, and quarantine paths
- a deterministic finance workflow benchmark suite (6 cases, 3 system classes)
- real 24h and real 72h soak evidence from the MSI soak machine
- a post-closure extension bundle that closes the three largest bounded v1 proof gaps

---

## Key Results

| Result | Value |
|---|---|
| Adaptive fabric accuracy (6-case finance suite) | **1.000** vs 0.583 for flat baseline |
| Unsafe / misaligned action rate (multi-cell classes) | **0.000** vs 0.500 for flat baseline |
| Descriptor reuse causality | Finance alias-heavy cases: 0.500 → 1.000 (causal, authority-approved) |
| Adaptation efficiency | **9× better** accuracy gain per retained KiB than governance alone |
| 72h soak runtime memory (repeated-cycle lane) | Fixed at **1,507,328 bytes** across 1690 cycles |
| 72h soak cycle score | **0.994434** average; improved from 0.988750 (first 100) to 0.995000 (last 100) |
| Organic load lane | 40-case near-capacity stream; one governed split with **no accuracy regression and measurable latency improvement** |
| Skill graph | Explicit `transfer_approval`, provenance, abstain paths, and denial paths |
| POS domain | 2nd bounded proof domain; 5 cases; **2 outcomes causally improved by finance-origin descriptor transfer** |
| Total deterministic proof coverage | **11 cases across 2 domains** |

---

## What the Post-Closure Bundle Added

The extension track closed three bounded proof gaps that remained after v1 root closure:

### Gap 1 — Split/Merge Under Normal Organic Load
- A deterministic 40-case near-capacity finance stream drove organic lifecycle pressure
- One governance-approved split occurred without an explicit stress-mode injection
- Elastic run showed no accuracy regression and measurable latency improvement over the no-split control run
- Active population returned near starting level after pressure fell

### Gap 2 — Governed Descriptor Transfer
- Extended `DescriptorRecord` with `domain_tags`, `transfer_eligible`, `transfer_score`, `conflict_score`, `retirement_score`, and `provenance_chain`
- Built a descriptor graph with `derived_from`, `supersedes`, `conflicts_with`, and `transfers_to` edges
- Cross-domain influence now requires an explicit `transfer_approval` — separate from standard descriptor approval
- Low-quality and low-trust transfer candidates can abstain or be denied; this is verified deterministically

### Gap 3 — Second Bounded Proof Domain (POS Operations)
- Six POS tissues added: intake/routing, validation, anomaly/fraud, governance, correction memory, output
- Five deterministic POS benchmark cases including one cross-domain transfer case
- Finance-origin descriptor causally improved 2 POS outcomes via the governed transfer path
- Transfer approval and provenance are recorded in the skill graph for every case

---

## What This Repo Does Not Claim

This repo does not claim:

- AGI or open-world general intelligence
- noisy production-scale proof
- proof of the full CellPOS product
- MacBook Air-only long-run endurance proof
- broad multi-domain generalization beyond the two bounded proof domains

**Machine roles are explicit:**
- **MacBook Air** — development, documentation, benchmark, and primary target machine
- **MSI** — long-run soak machine (24h and 72h evidence)

The long-run soak evidence is real and analyzed, but it is MSI evidence. MacBook Air-only multi-day endurance is not claimed.

---

## Best Starting Points

### For the public v1 truth

| File | What it contains |
|---|---|
| `PROJECT_README.md` | Full project overview and architecture |
| `DECISIONS.md` | Every major design decision with rationale |
| `CHANGELOG.md` | Phase-by-phase record of all changes |
| `06_outputs/evidence_bundle_manifests/agif_v1_release_note.md` | Formal v1 release note: what v1 proves, does not prove, and excluded by design |
| `06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md` | Every paper claim mapped to a concrete artifact and verification command |
| `06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md` | Reviewer-ready package with expected outputs and machine-role distinctions |

### For the post-closure extension evidence

| File | What it contains |
|---|---|
| `05_testing/V1X_ORGANIC_LOAD_EVIDENCE.md` | Gap 1 — organic split/merge proof |
| `05_testing/V1X_SKILL_GRAPH_EVIDENCE.md` | Gap 2 — skill graph and governed transfer proof |
| `05_testing/V1X_POS_DOMAIN_EVIDENCE.md` | Gap 3 — POS domain and cross-domain transfer proof |
| `05_testing/V1X_BUNDLE_CLOSURE_EVIDENCE.md` | Full extension bundle closure record |

---

## Verification

### Root AGIF v1 closure

```bash
git clone https://github.com/Ahsadin/agif_fabric_v1.git
cd agif_fabric_v1
python3 scripts/check_phase9_closure.py
```

Expected output: `AGIF_FABRIC_P9_PASS`

### Post-closure extension bundle

```bash
python3 scripts/check_v1x_bundle.py
```

Expected output: `AGIF_FABRIC_V1X_PASS`

> **Note:** `check_v1x_bundle.py` runs the full ordered chain including Phase 9 closure re-verification. Allow 3–5 minutes for a complete local run.

If both commands pass, the repo matches the closed public state described in this README.

### Individual gap checks (faster)

```bash
python3 scripts/check_v1x_organic_load.py   # Gap 1 — organic load (~30s)
python3 scripts/check_v1x_skill_graph.py    # Gap 2 — skill graph (<1s)
python3 scripts/check_v1x_pos_domain.py     # Gap 3 — POS domain (<1s)
```

---

## Pass Tokens

| Token | Meaning |
|---|---|
| `AGIF_FABRIC_P3_PASS` | Runner and fabric foundation verified |
| `AGIF_FABRIC_P4_PASS` | Elastic lifecycle and lineage verified |
| `AGIF_FABRIC_P5_PASS` | Reviewed memory and bounded growth verified |
| `AGIF_FABRIC_P6_PASS` | Need signals, routing, and authority verified |
| `AGIF_FABRIC_P7_PASS` | Finance tissues and benchmark system verified |
| `AGIF_FABRIC_P8_PASS` | Long-run soak evidence verified (24h + 72h MSI) |
| `AGIF_FABRIC_P9_PASS` | Paper, claims matrix, and reproducibility package verified |
| `AGIF_FABRIC_V1X_SETUP_PASS` | Extension track scaffold and freeze verified |
| `AGIF_FABRIC_V1X_G1_PASS` | Organic split/merge proof verified |
| `AGIF_FABRIC_V1X_G2_PASS` | Skill graph and governed transfer verified |
| `AGIF_FABRIC_V1X_G3_PASS` | POS domain and cross-domain transfer verified |
| `AGIF_FABRIC_V1X_PASS` | Full extension bundle verified |

---

*Root v1 closure: 2026-03-18. Post-closure extension bundle: 2026-03-18. Author: Danish Z. Khan.*
