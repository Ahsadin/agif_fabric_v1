# Memory Model

## Phase 2 Freeze Status
- Frozen on `2026-03-12` for Phase 2.
- This document freezes memory structure and promotion rules before runtime implementation begins.

## Locked Memory Principles
- Raw logs are not long-term memory.
- AGIF memory grows by selective retention, not raw accumulation.
- AGIF v1 must support both local memory and fabric memory.
- Every promoted memory must be reviewed.
- Memory pressure must trigger consolidation, compression, dormancy, merge review, or retirement pressure before cap breach.
- No referenced descriptor payload may be garbage-collected without validation that its references remain safe.

## Frozen Memory Tiers
Phase 2 freezes three memory tiers plus a separate evidence log store.

| Store | Scope | Frozen purpose | What belongs here |
| --- | --- | --- | --- |
| Ephemeral log store | local and fabric evidence only | Temporary traces for audit, replay, and debugging | raw logs, raw traces, transient execution notes |
| Hot memory | active runtime | Immediate work state needed for live tasks | active workspace state, current tasks, live cell state, short review buffers |
| Warm memory | bounded reusable memory | Recent trusted reusable state | recent trusted descriptors, recent promoted summaries, locally useful intermediate state |
| Cold memory | compressed long-term memory | Long-term retained state kept for reuse, replay, and reproducibility | compressed long-term state, archived traces selected for evidence, reproducibility artifacts |

Raw logs may help justify later promotion, but they do not count as memory unless a reviewed promotion decision creates a bounded retained artifact.

## Local Memory Versus Fabric Memory

### Local Memory
Local memory is cell-bounded or tissue-bounded memory used for immediate or near-term work. It is constrained by:
- `working_memory_bytes`
- `idle_memory_bytes`
- `descriptor_cache_bytes`
- `memory_tier`

Local memory is allowed to hold:
- hot task state
- recent warm descriptors useful to that cell or tissue
- short-lived review buffers

Local memory is not allowed to silently become permanent fabric memory.

### Fabric Memory
Fabric memory is shared retained memory available across cells and tissues after review. It includes:
- reviewed descriptors
- promoted summaries
- compressed cold artifacts
- replay-safe retained references

Fabric memory is governed by:
- `memory_caps`
- `storage_caps`
- `retention_policy`
- `trust_ref`
- `MemoryPromotionDecision`

## Frozen Tier Assignment Rules
- `CellBlueprint.memory_tier` must point to the default operating tier for that cell and is limited to `hot`, `warm`, or `cold`.
- `DescriptorRecord.storage_tier` is limited to `hot`, `warm`, or `cold`.
- `MemoryPromotionDecision.retention_tier` is limited to `hot`, `warm`, or `cold`.
- The ephemeral log store is not a `storage_tier` value. It is a separate evidence path.

## Frozen Promotion Flow
1. Work artifacts first appear in workspace or the ephemeral log store.
2. A cell, tissue, or reviewer nominates an artifact as a memory candidate.
3. A reviewer records a `MemoryPromotionDecision`.
4. The decision must be one of:
   - `reject`
   - `defer`
   - `promote`
   - `compress`
   - `retire`
5. If the result is `promote` or `compress`, the record must state:
   - `compression_mode`
   - `retention_tier`
   - `reason`
   - `rollback_ref`
6. Only reviewed and retained artifacts become eligible for fabric reuse.

## Frozen Retention Rules

### Hot
- Used for active work only
- Must remain small and discardable
- May be dropped after task completion, hibernation, quarantine, or retirement unless explicitly promoted

### Warm
- Used for recent trusted reuse
- Holds near-term descriptors and summaries that still have bounded reuse value
- May be demoted or consolidated under memory pressure

### Cold
- Used for compressed long-term retention
- Must favor compact summaries, deduplicated payloads, and replay-safe references
- Exists for later reuse, replay, rollback support, benchmark evidence, and reproducibility

## Frozen Compression and Consolidation Rules
- Reviewed promotion should compress or quantize where feasible.
- Memory pressure must prefer consolidation over growth.
- Deduplication is required before keeping materially duplicate warm or cold artifacts.
- Compression must not destroy the minimum information needed for trust review, replay, rollback, or reproducibility.
- If compression would remove required audit or rollback information, the decision must be `defer` or `reject`, not silent loss.

## Frozen Forgetting Rule
Intentional forgetting is allowed and expected. AGIF v1 is not trying to keep everything forever.

Forgetting must be:
- explicit
- bounded
- reviewable
- compatible with falsification thresholds

AGIF v1 fails its bounded-learning claim if catastrophic forgetting exceeds the already frozen threshold of `10%`.

## Frozen Replay and Rollback Implications
- Promoted memory must remain traceable through `payload_ref`, `trust_ref`, and promotion records.
- Every nontrivial promotion or compression path must preserve a `rollback_ref` when reversal is possible.
- Replay tools must be able to distinguish:
  - transient workspace state
  - reviewed retained memory
  - evidence-only raw logs

## Frozen Storage Cap Handling
- `memory_caps` and `storage_caps` must set hard upper bounds by tier and store.
- When pressure rises, the system must favor:
  - consolidation
  - compression
  - dormancy
  - merge review
  - retirement
- The system must not rely on uncontrolled accumulation to improve quality.

## Verification Status
- Locally verified:
  - memory tiers, promotion rules, and raw-log exclusions are now frozen in writing
  - local versus fabric memory is distinguished clearly in this workspace
- Assumed only:
  - actual memory retention behavior
  - actual garbage collection
  - actual replay performance
