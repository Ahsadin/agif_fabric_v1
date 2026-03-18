# MSI Soak Machine Note

## Purpose
This note records the paper-safe provenance details for the real Phase 8 `24h` and `72h` soak runs that were executed on the MSI Windows soak machine.

## MSI Soak Machine
- Long-run Phase 8 soak execution was performed on an MSI laptop, not on the MacBook target machine.
- Model: `Micro-Star International Co., Ltd. GP63 Leopard 8RF`
- OS: `Microsoft Windows 11 Home`, version `10.0.26220`, `64-bit`
- BIOS: `E16P5IMS.110`, release date `2019-05-20`
- CPU: `Intel Core i7-8750H @ 2.20 GHz`
- CPU topology: `6` physical cores, `12` logical threads
- RAM: `15.85 GB` physical memory
- GPU observed: `NVIDIA GeForce GTX 1070`
- Python: `3.13.5`
- Project path on this machine: `E:\AGIF\agif_fabric_v1`
- Power plan during soak: `Balanced`
- Plugged-in sleep setting before soak: `Never`
- Plugged-in hibernate setting before soak: `Never`

## Before Soak
- Verified on the MSI soak machine before the real runs:
  - the project opened correctly from `E:\AGIF\agif_fabric_v1`
  - Python worked
  - `scripts/check_phase8_soak.py` passed on this Windows machine
  - the chained earlier regressions passed through the Phase 8 readiness check
  - the machine was prepared as the dedicated MSI soak machine
  - charger / AC-online state was locally confirmed before launch in the soak thread
- Current disk state measured after the runs:
  - drive `E:` used `86.91 GB`
  - drive `E:` free `31.92 GB`
- Exact before-soak free disk was not captured as a durable snapshot, so no exact before-soak disk number is claimed.

## 24h Soak Outcome
- Run root: `08_logs\phase8_soak\run_24h`
- Started: `2026-03-13T20:05:45Z`
- Completed: `2026-03-14T20:08:22Z`
- Wall-clock runtime: about `24h 2m 37s`
- Completed cycles: `989`
- Resume count: `1`
- Stress lanes recorded: `5`
- Stress result: all `5` passed
- Recorded failure case count: `1`
- That recorded failure case was expected governed behavior, not a surprise crash:
  - `AUTHORITY_REACTIVATION_VETO`

## 72h Soak Outcome
- Run root: `08_logs\phase8_soak\run_72h`
- Started: `2026-03-14T23:54:31Z`
- Completed: `2026-03-17T23:58:40Z`
- Wall-clock runtime: about `72h 4m 9s`
- Completed cycles: `1690`
- Resume count: `1`
- Stress lanes recorded: `5`
- Stress result: all `5` passed
- Recorded failure case count: `1`
- That recorded failure case was again the expected governed stress behavior:
  - `AUTHORITY_REACTIVATION_VETO`

## Stress Suite
- `split_merge`: passed
- `memory_pressure`: passed
- `routing_pressure`: passed
- `trust_quarantine`: passed
- `replay_rollback`: passed

## Windows-Side Execution Notes
- This MSI run needed small Windows-specific harness hardening during execution:
  - launching the internal `runner/cell` entrypoint through the active Python interpreter on Windows
  - hiding child console windows for internal subprocesses
  - extending manifest-write retry handling for transient Windows file-lock collisions
- The `24h` run had one real interruption and was resumed honestly from the same run root.
- The `72h` run had one real interruption and was resumed honestly from the same run root.
- These were MSI/Windows soak-machine execution details, not MacBook-only proof.

## Artifact Footprint
- `run_24h` folder size: about `171.56 MB`
- `run_72h` folder size: about `289.29 MB`
- Existing export folder size: about `181.38 MB`

## Honest Limits For The Paper
- These long-run results were locally verified on the MSI Windows soak machine.
- They should not be described as MacBook-only runtime or resource proof.
- Battery telemetry was not available from this session, so no exact battery condition percentage is claimed.
- Light concurrent user activity was not formally instrumented in a machine log here, so this note does not claim strictly zero concurrent activity.
