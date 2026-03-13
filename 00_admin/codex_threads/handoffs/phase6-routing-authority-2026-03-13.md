# Phase 6 Routing And Authority Handoff

- Thread ID: `phase6-routing-authority-2026-03-13`
- Status: complete
- Scope: Phase 6 only
- Pass token: `AGIF_FABRIC_P6_PASS`
- Progress units: `465/600`
- Local verification:
  - `python3 scripts/check_phase6_routing_authority.py`
  - `python3 scripts/check_phase5_memory.py`
  - `python3 scripts/check_phase4_lifecycle.py`
  - `python3 scripts/check_phase3_foundation.py`
- Key outcome:
  - need signals now generate operational pressure with expiry, status transitions, and traceable resolution
  - routing now uses reviewed descriptors, trust, load, workspace context, and utility scoring to pick runtime candidates deterministically
  - authority now records approvals and vetoes for higher-risk routing, memory influence, reactivation, split, merge, and quarantine actions
  - Phase 6 traces now connect need signal, utility evaluation, authority review, and final recorded action
- Assumed only:
  - Phase 7 domain tissue expansion
  - benchmark behavior beyond the deterministic local proof
