# Soak Test Policy

## Status
This file exists because the execution plan requires it.

Soak testing is planned for later phases and is not active yet.

## Locked Inputs from the Plan
Later soak and long-run evidence work must include:
- repeated workflow learning cycles
- split and merge stress tests
- memory saturation tests
- routing pressure tests
- trust and quarantine fault injection
- replay and rollback recovery tests
- 24h soak test
- 72h soak test

The plan also requires:
- `caffeinate` for wakelock where needed
- restart-resume semantics
- lid-close or restart must not invalidate the evidence log
