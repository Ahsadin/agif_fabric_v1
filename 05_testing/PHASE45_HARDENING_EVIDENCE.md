# Phase 4.5 And 5.5 Hardening Evidence

## Purpose
This note records the local verification for the lifecycle and memory hardening pass completed after Phase 5.

## Deterministic Checks
- Command run locally: `python3 scripts/check_phase4_lifecycle.py`
- Result: pass
- Command run locally: `python3 scripts/check_phase5_memory.py`
- Result: pass
- Regression command run locally: `python3 scripts/check_phase3_foundation.py`
- Result: pass

## What Was Locally Verified
- Split now rejects weak pressure and only admits overload, novelty, or coordination pressure with a usefulness reason.
- Split history now records why the split was useful, not just that the transition happened.
- Merge now rejects specialization-destroying branches with an explicit specialization-risk veto.
- Lifecycle thrashing is reduced by blocking the third immediate reactivation in an activate/hibernate oscillation pattern.
- Hibernate now packs a compact dormancy profile and reactivation restores the preserved runtime context predictably.
- Lifecycle summary now exposes deterministic structural usefulness metrics and lineage usefulness metrics.
- Lifecycle metrics now record when a lineage produces promoted or reused memory.
- Memory review now scores candidates using novelty, usefulness, trust, reuse potential, compression gain, and conflict risk.
- Low-value memory can now be deferred even when it is structurally valid.
- Lower-trust conflicting memory is prevented from overriding higher-trust reviewed memory.
- Useful reviewed memory is still promoted, exact duplicates reuse the existing promoted artifact, and true updates can supersede older memory.
- Memory summary now reports reuse, supersession, duplicate compression gain, stale retirement rate, and retention priorities.
- Memory pressure now chooses lower-priority memory for compression or retirement before higher-trust memory.
- Raw logs remain ephemeral and are not promoted directly into long-term memory.
- Cold-reference integrity, bounded replay, and deterministic replay checks still pass after the hardening changes.

## Assumed Only
- Phase 6 routing, utility, and authority behavior
- long-duration soak behavior beyond the deterministic local checks
- benchmark outcomes beyond the current local runtime proof
