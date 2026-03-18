# Pass Tokens

## Current Earned Tokens
- `AGIF_FABRIC_P3_PASS`
  - Earned on `2026-03-12`
  - Local verification command: `python3 scripts/check_phase3_foundation.py`
- `AGIF_FABRIC_P4_PASS`
  - Earned on `2026-03-13`
  - Local verification command: `python3 scripts/check_phase4_lifecycle.py`
  - Re-verified on `2026-03-13` during the Phase 4.5 hardening pass with the same command
- `AGIF_FABRIC_P5_PASS`
  - Earned on `2026-03-13`
  - Local verification command: `python3 scripts/check_phase5_memory.py`
  - Re-verified on `2026-03-13` during the Phase 5.5 hardening pass with the same command
- `AGIF_FABRIC_P6_PASS`
  - Earned on `2026-03-13`
  - Local verification command: `python3 scripts/check_phase6_routing_authority.py`
  - Re-verified on `2026-03-13` during the Phase 6.5 hardening pass with the same command
- `AGIF_FABRIC_P7_PASS`
  - Earned on `2026-03-13`
  - Local verification command: `python3 scripts/check_phase7_benchmarks.py`
  - Re-verified on `2026-03-13` during the Phase 7.5 hardening pass with the same command
  - Re-verified on `2026-03-13` during the Phase 7.6 hardening pass with the same command
- `AGIF_FABRIC_P8_PASS`
  - Earned on `2026-03-18`
  - Local verification command: `python3 scripts/check_phase8_soak.py`
  - Real long-run evidence inspected locally from:
    - `08_logs/phase8_soak/run_24h/`
    - `08_logs/phase8_soak/run_72h/`
  - Honest caveats:
    - the long-run soak machine is MSI, not MacBook Air-only proof
    - the `72h` run recovered after a repeated `WinError 5` manifest-write interruption, but final resume bookkeeping stayed incomplete
- `AGIF_FABRIC_P9_PASS`
  - Earned on `2026-03-18`
  - Local verification command: `python3 scripts/check_phase9_closure.py`
  - This command re-verifies locally:
    - `python3 scripts/check_phase8_soak.py`
    - `python3 scripts/check_phase7_benchmarks.py` twice for deterministic hash confirmation
  - Package artifacts validated locally:
    - `05_testing/PHASE9_CLOSURE_EVIDENCE.md`
    - `06_outputs/evidence_bundle_manifests/phase9_claims_to_evidence_matrix.md`
    - `06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md`
    - `06_outputs/paper_drafts/AGIF_v1_paper_R4_2026-03-18.docx`
    - `06_outputs/paper_drafts/AGIF_v1_paper_R4_2026-03-18.pdf`
  - Honest caveats:
    - the long-run soak machine is still MSI, not MacBook Air-only proof
    - the `72h` run still carries the documented `WinError 5` resume-bookkeeping caveat
    - split or merge efficiency under sustained organic near-capacity load remains outside the present proof

## Phase 8 Honest Status
- A real `24h` Phase 8 soak is recorded under `08_logs/phase8_soak/run_24h/`.
- A real `72h` Phase 8 soak is recorded under `08_logs/phase8_soak/run_72h/`.
- `AGIF_FABRIC_P8_PASS` is now earned because the locked Phase 8 gate is satisfied by:
  - the bounded local harness verification
  - the real `24h` soak evidence
  - the real `72h` soak evidence
  - passing soak, replay, rollback, quarantine, and resource-cap checks
- The imported long-run artifacts came from the MSI soak machine and must not be described as MacBook Air-only proof.

## Harness Readiness Tokens
- `AGIF_FABRIC_P8_HARNESS_READY`
  - Recorded on `2026-03-13`
  - Local verification command: `python3 scripts/check_phase8_soak.py`
  - Meaning: the bounded Phase 8 harness, stress lanes, resumable manifests, and summary outputs are locally verified
  - Re-verified on `2026-03-13` during the Phase 8.5 hardening pass with the same command
  - Important: this is not the Phase 8 completion token and does not replace `AGIF_FABRIC_P8_PASS`

## Phase 9 Honest Status
- The finish-line deliverables are now present in this workspace:
  - runnable local AGIF v1
  - research paper copies
  - benchmark evidence
  - reproducibility package
- The imported `24h` and `72h` long-run artifacts still come from the MSI soak machine and must not be described as MacBook Air-only proof.
- Phase 9 closure does not remove the explicit non-claims around AGI, broad open-world generality, or the split/merge placeholder limits.
