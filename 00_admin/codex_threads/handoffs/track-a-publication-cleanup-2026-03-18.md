# Track A Publication Cleanup Handoff

## Goal
- Align the closed AGIF v1 public repo to the final execution plan's Track A rules without reopening AGIF v1 proof work.

## Files Updated
- `PROJECT_README.md`
- `DECISIONS.md`
- `CHANGELOG.md`
- `05_testing/PASS_TOKENS.md`
- `06_outputs/evidence_bundle_manifests/phase9_reproducibility_package.md`
- `06_outputs/evidence_bundle_manifests/agif_v1_release_note.md`
- `00_admin/CODEX_THREAD_MAP.md`

## What Changed
- Added a public release note for the closed AGIF v1 package.
- Refined the root repo wording so it now says:
  - AGIF v1 remains closed at `600/600`
  - post-closure publication cleanup is docs and package maintenance only
  - new proof work must live in a separate post-closure initiative
  - AGIF v2 planning starts only after that separate extension bundle
- Kept the public and private boundary explicit:
  - unpublished paper draft still omitted from the public repo
  - paper-draft status note still present
  - no stray helper files remain in the repo root
- Kept the machine split and v1 caveats explicit:
  - MacBook Air = development, documentation, benchmark, and primary target machine
  - MSI = final AGIF v1 long-run soak machine
  - `72h` run still carries the documented `WinError 5` bookkeeping caveat
  - finance remains the only closed v1 proof domain

## Verification
- `python3 scripts/check_phase9_closure.py`
  - result: `AGIF_FABRIC_P9_PASS`
- Repo-root helper-file audit:
  - no stray paper helper files remain in the repo root

## Notes
- Root AGIF v1 progress remains unchanged at `600/600`.
- This Track A pass does not start Track B implementation work.
