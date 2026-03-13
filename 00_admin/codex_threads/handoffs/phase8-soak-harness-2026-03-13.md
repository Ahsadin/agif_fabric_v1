# Phase 8 Soak Harness Handoff

## Thread
- Thread ID: `phase8-soak-harness-2026-03-13`
- Date: `2026-03-13`

## What Closed In This Thread
- Part A:
  - stabilized Phase 7 benchmark artifacts so rerunning `python3 scripts/check_phase7_benchmarks.py` no longer dirties tracked files
  - cleanup commit: `a0608a2` `fix(benchmark): stabilize phase 7 outputs`
- Part B:
  - added the Phase 8 bounded soak harness in `intelligence/fabric/benchmarking/phase8.py`
  - added Phase 8 fixtures under `fixtures/document_workflow/phase8/`
  - added:
    - `scripts/run_phase8_soak.py`
    - `scripts/check_phase8_soak.py`
    - `05_testing/test_phase8_soak.py`
    - `05_testing/PHASE8_LONGRUN_EVIDENCE.md`
    - `06_outputs/run_summaries/phase8_bounded_validation.md`
    - `06_outputs/run_summaries/phase8_bounded_validation.json`

## Local Verification Completed
- `python3 scripts/check_phase8_soak.py`
  - passed locally
  - printed `AGIF_FABRIC_P8_HARNESS_READY`
- This chained:
  - `python3 scripts/check_phase7_benchmarks.py`
  - `python3 scripts/check_phase6_routing_authority.py`
  - `python3 scripts/check_phase5_memory.py`
  - `python3 scripts/check_phase4_lifecycle.py`
  - `python3 scripts/check_phase3_foundation.py`
- The bounded Phase 8 validation locally showed:
  - descriptor reuse benefit delta `0.625`
  - active/logical ratio `0.909`
  - runtime bytes `1507328`
  - split/merge, memory pressure, routing pressure, trust/quarantine, and replay/rollback lanes all passing locally

## What Is Still Open
- Real `24h` soak is not completed locally.
- Real `72h` soak is not completed locally.
- `AGIF_FABRIC_P8_PASS` is not earned.
- Project progress remains `525/600`.

## Next Recommended Actions
1. Run `python3 scripts/run_phase8_soak.py --profile fixtures/document_workflow/phase8/soak_24h_profile.json --run-root 08_logs/phase8_soak/run_24h`
2. Confirm the run stays resumable after an intentional stop and resume.
3. Capture the completed 24h summary and update `05_testing/PHASE8_LONGRUN_EVIDENCE.md`.
4. Repeat with `soak_72h_profile.json`.
5. Only after both real runs are locally complete:
   - update `05_testing/PASS_TOKENS.md` with `AGIF_FABRIC_P8_PASS`
   - move progress to `570/600`
   - mark the Phase 8 gate complete
