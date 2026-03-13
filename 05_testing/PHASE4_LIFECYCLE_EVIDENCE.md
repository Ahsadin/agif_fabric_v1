# Phase 4 Lifecycle Evidence

## Purpose
This note records the local verification used to close Phase 4.

## Deterministic Check
- Command run locally: `python3 scripts/check_phase4_lifecycle.py`
- Result: pass
- Pass token: `AGIF_FABRIC_P4_PASS`

## What Was Locally Verified
- Dormant logical cells and active runtime cells are stored separately under the local fabric state root.
- `runner/cell fabric init` seeds dormant blueprint storage and lineage roots from the committed registry.
- `runner/cell fabric run` activates the needed committed cells without changing the frozen CLI surface.
- Governed split creates active children and preserves lineage, role family, trust ancestry, descriptor eligibility, and policy envelope.
- Governed merge uses conflict-aware consolidation and retires merged-away cells only through the approved path.
- Invalid merge attempts fail closed and record a veto reference locally.
- Hibernate and reactivate work through the frozen lifecycle transitions without adding new enums.
- Retire preserves lineage history and rollback references.
- Active runtime population reaches the committed burst target of `48` and returns automatically to the steady target of `24` after consolidation.
- Lifecycle replay reproduces the committed structural state deterministically.
- `python3 scripts/check_phase3_foundation.py` still passes locally after the Phase 4 changes.

## Assumed Only
- Phase 5 reviewed memory behavior
- long-duration soak behavior
- benchmark outcomes beyond the local Phase 4 lifecycle proof
