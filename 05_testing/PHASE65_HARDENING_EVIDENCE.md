# Phase 6.5 Hardening Evidence

## Purpose
This note records the local verification used to close the Phase 6.5 hardening pass.

## Deterministic Check
- Command run locally: `python3 scripts/check_phase6_routing_authority.py`
- Result: pass
- Pass token re-verified: `AGIF_FABRIC_P6_PASS`

## What Was Locally Verified
- Weak routing candidates now produce explicit route confidence, confidence bands, and deterministic rejection reasons.
- At least one deterministic routing scenario now abstains instead of forcing a weak route.
- Need handling now records separate resolution quality, effectiveness score, expiry, and recurring unresolved pressure without changing the frozen `NeedSignal` fields.
- Repeated unresolved need pressure is now detectable through recurring signatures and resolution memory.
- Prior routing failure memory changes a later routing choice deterministically.
- Reviewed descriptor provenance now affects routing preference visibly and is recorded in candidate traces.
- Lineage usefulness now affects routing scores and is passed into higher-risk authority review metadata.
- Authority now records proposer history, trust-band history, repeated veto patterns, and weak-lineage review pressure.
- A repeated risky reactivation attempt now receives stronger authority veto reasons because of prior review history.
- `python3 scripts/check_phase5_memory.py` still passes locally through the chained Phase 6 check.
- `python3 scripts/check_phase4_lifecycle.py` still passes locally through the chained Phase 6 check.
- `python3 scripts/check_phase3_foundation.py` still passes locally through the chained Phase 6 check.

## Usefulness Gate
- Deterministic routing is now more useful than the earlier Phase 6 base because it can say no to weak routes, learn from prior failures, and explain why a better candidate was preferred.
- Deterministic authority is now more useful than the earlier Phase 6 base because repeated risky patterns now strengthen later veto behavior instead of treating each review as isolated.

## Remaining Weaknesses
- Route outcome feedback is still lightweight and bounded. It is strong enough for local deterministic hardening, but it is not yet a benchmark-grade long-horizon learning loop.
- Need-resolution quality still uses bounded local heuristics rather than domain-truth outcome scoring.
- Authority history is local and deterministic, not yet a long-run governance model for later tissue-scale benchmark work.

## Assumed Only
- Phase 7 tissue expansion beyond the current finance workflow proof
- benchmark behavior beyond the deterministic local checks
- long-duration soak behavior beyond the current local hardening pass
