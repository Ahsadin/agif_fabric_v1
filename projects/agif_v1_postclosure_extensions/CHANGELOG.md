# Changelog

## 2026-03-18 Track B Setup-And-Freeze Closure
- Closed the Track B setup-and-freeze gate honestly.
- Added the missing frozen requirements for later work:
  - explicit root tracker isolation
  - explicit Gap 1 deterministic `40`-case comparison rules
  - explicit Gap 3 deterministic `5`-case comparison rules
  - explicit final bundle verifier order
- Added the local setup verification artifacts:
  - `05_testing/TRACK_B_SETUP_FREEZE_EVIDENCE.md`
  - `scripts/check_v1x_setup.py`
- Recorded the closed setup gate:
  - Track B progress is now `15/130`
  - `AGIF_FABRIC_V1X_SETUP_PASS` is now earned
  - root AGIF v1 remains `600/600`

## 2026-03-18 Track B Setup
- Created the separate Track B project scaffold under `projects/agif_v1_postclosure_extensions/`.
- Added the local source-of-truth files:
  - `PROJECT_README.md`
  - `DECISIONS.md`
  - `CHANGELOG.md`
  - `01_plan/PROGRESS_TRACKER.md`
- Added local extension management files:
  - `01_plan/PHASE_GATE_CHECKLIST.md`
  - `02_requirements/TRACK_B_SCOPE_AND_GATES.md`
  - `05_testing/PASS_TOKENS.md`
  - `00_admin/CODEX_THREAD_MAP.md`
- Recorded that root AGIF v1 remains closed at `600/600` and that no extension tokens are earned yet.
