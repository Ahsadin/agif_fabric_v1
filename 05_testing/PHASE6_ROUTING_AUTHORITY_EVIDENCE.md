# Phase 6 Routing And Authority Evidence

## Purpose
This note records the local verification used to close Phase 6.

## Deterministic Check
- Command run locally: `python3 scripts/check_phase6_routing_authority.py`
- Result: pass
- Pass token: `AGIF_FABRIC_P6_PASS`

## What Was Locally Verified
- Need signals are generated during routing and stored with severity, status, expiry, and resolution references.
- Expired need signals stop influencing routing and authority decisions locally.
- Resolved need signals remain traceable through the need history and final resolution refs.
- Utility scoring changes candidate preference in deterministic routing fixtures.
- Lower-trust and lower-utility options score below safer, more useful alternatives locally.
- Runtime utility evaluation exposes hibernate and reactivate recommendations from the frozen utility thresholds.
- Routing chooses between multiple candidates using role fit, descriptor usefulness, trust, load, need pressure, workspace context, and utility.
- Routing reasons, selected descriptors, and candidate utility traces are recorded deterministically.
- Authority records approvals and vetoes for descriptor use, risky reactivation, split follow-through, and quarantine escalation.
- Higher-risk actions fail closed when trust or policy conditions are not met locally.
- Governed structural actions keep rollback references in lifecycle history and authority reviews.
- A governed split can be traced locally from need signal to utility evaluation to authority review to final lifecycle action.
- `python3 scripts/check_phase5_memory.py` still passes locally after the Phase 6 changes.
- `python3 scripts/check_phase4_lifecycle.py` still passes locally after the Phase 6 changes.
- `python3 scripts/check_phase3_foundation.py` still passes locally after the Phase 6 changes.

## Assumed Only
- Phase 7 tissue expansion beyond the current finance workflow scope
- benchmark system behavior beyond the deterministic local checks
- long-duration soak behavior beyond the current local proof
