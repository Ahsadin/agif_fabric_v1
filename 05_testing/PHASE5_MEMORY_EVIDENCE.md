# Phase 5 Memory Evidence

## Purpose
This note records the local verification used to close Phase 5.

## Deterministic Check
- Command run locally: `python3 scripts/check_phase5_memory.py`
- Result: pass
- Pass token: `AGIF_FABRIC_P5_PASS`

## What Was Locally Verified
- Hot, warm, cold, and ephemeral memory stores exist locally under the fabric state root.
- Raw logs stay in the ephemeral store and are not promoted directly into long-term memory.
- Reviewed memory decisions use the frozen `MemoryPromotionDecision` shape.
- Bad candidates can be rejected and kept out of retained memory.
- Good candidates can be promoted into reviewed warm memory.
- Deferred candidates stay in the short hot review buffer.
- Accepted memory is quantized or compressed before retention.
- Duplicate and superseded memory is deduplicated or archived correctly.
- The memory replay store stays bounded and recorded decisions remain traceable and replayable.
- Referenced cold payloads survive GC and unreferenced cold payloads are removed after governed retirement.
- Memory pressure emits a first-class `memory_pressure` signal and triggers consolidation instead of uncontrolled growth.
- Repeated runs remain inside the committed Phase 5 memory caps locally.
- `python3 scripts/check_phase4_lifecycle.py` still passes locally after the Phase 5 changes.
- `python3 scripts/check_phase3_foundation.py` still passes locally after the Phase 5 changes.

## Assumed Only
- Phase 6 routing, utility, and authority depth
- long-duration soak behavior beyond the deterministic Phase 5 proof
- benchmark outcomes beyond the local Phase 5 memory proof
