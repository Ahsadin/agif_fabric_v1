# Phase Gate Checklist

## Status Key
- Checked items were locally verified in this workspace.
- Unchecked items are planned only and remain assumed until later work verifies them.

## Phase 0
- [x] Local `AGENTS.md` exists at the project root.
- [x] Root source-of-truth files exist.
- [x] Required admin files exist.
- [x] Required planning files exist.
- [x] Required directory structure exists.
- [x] Progress denominator is fixed at `600`.
- [x] Phase weights are recorded exactly.
- [x] No runtime code was implemented in this thread.

## Phase 1
- [x] Requirements documents define AGIF v1 scope clearly.
- [x] Proof boundary is written down clearly.
- [x] Falsification thresholds are written down clearly.
- [x] Finance workflow proof scope is fixed.

## Phase 2
- [x] All six Phase 2 design docs exist in `03_design/`.
- [x] Architecture documents define the AGIF v1 structure and preserve the full AGIF concept while keeping v1 proof claims bounded.
- [x] Core interfaces are frozen in writing with the exact required field names.
- [x] Need-signal taxonomy is frozen in writing.
- [x] Lifecycle states and state transitions are frozen in writing.
- [x] Split and merge inheritance rules are frozen in writing.
- [x] Decision authority layers and merge approval quorum are frozen in writing.
- [x] Resource guardrails and machine envelope are frozen in writing.
- [x] CLI contracts are frozen in writing.
- [x] Benchmark classes and metrics are frozen in writing.
- [x] Decision records cover all interface freezes.

## Phase 3
- [x] Runner foundation exists locally.
- [x] Fabric execution control exists locally.
- [x] Deterministic execution path exists.
- [x] Base execution tests pass locally.

## Phase 4
- [x] Logical fabric population and active runtime population are stored separately.
- [x] Dormant blueprint storage exists locally.
- [x] Governed activation, split, merge, hibernate, reactivate, and retire flows exist locally.
- [x] Split inheritance rules are enforced locally.
- [x] Split rejects weak pressure and records usefulness reasons locally.
- [x] Merge veto and conflict-aware consolidation exist locally.
- [x] Merge rejects specialization-destroying branches locally.
- [x] Lineage ledger and rollback-safe lifecycle history exist locally.
- [x] Compact dormancy, reactivation usefulness, and lifecycle anti-thrashing guardrails exist locally.
- [x] Structural usefulness and lineage usefulness summaries exist locally.
- [x] Burst active population reaches `48` and returns automatically to steady `24` after consolidation.
- [x] Lifecycle replay passes locally.

## Phase 5
- [x] Hot, warm, and cold retained memory tiers exist locally.
- [x] Raw logs are stored ephemerally and are not auto-promoted into long-term memory.
- [x] Reviewed memory supports reject, defer, promote, compress, and retire locally.
- [x] Reviewed promotion decisions use the frozen `MemoryPromotionDecision` shape.
- [x] Reviewer scoring uses novelty, usefulness, trust, reuse potential, compression gain, and conflict risk locally.
- [x] Quantized consolidation, deduplication, supersession, bounded replay, and memory GC work locally.
- [x] Trust-weighted conflict handling and strategic memory-pressure retention exist locally.
- [x] Memory reuse, supersession, duplicate compression gain, and stale retirement metrics are recorded locally.
- [x] Referenced cold payloads are protected and unreferenced cold payloads can be retired safely.
- [x] `memory_pressure` is recorded as a first-class need signal and triggers consolidation locally.
- [x] Phase 5 fixtures, tests, and evidence pass locally.

## Phase 6
- [x] Need signals drive routing and authority review beyond the current lifecycle and memory cases.
- [x] Utility scoring is active in runtime decisions beyond the current bounded proof paths.
- [x] Routing logic uses reviewed descriptors under explicit authority checks.
- [x] Authority evaluation covers the planned Phase 6 depth locally.
- [x] Routing records explicit confidence, low-confidence abstain or escalate paths, and deterministic rejection reasons locally.
- [x] Need handling records resolution quality, effectiveness, expiry, and recurring unresolved pressure locally.
- [x] Routing history, descriptor provenance, and lineage usefulness influence later routing locally.
- [x] Authority history, trust-band review pressure, and weak-lineage review pressure influence later governance locally.
- [x] Phase 3, Phase 4, and Phase 5 deterministic checks still pass locally after the Phase 6.5 hardening changes.

## Phase 7
- [x] Domain tissues are implemented beyond the current finance workflow seed roles.
- [x] The benchmark system is active across the frozen benchmark classes.
- [x] Domain tissue tests pass locally.
- [x] Benchmark evidence can be generated locally.
- [x] Phase 7.5 hardening improved benchmark explanations, tissue analytics, bounded resource reporting, and structural-pressure honesty without changing the frozen benchmark classes or project units.
- [x] Phase 7.6 hardening improved descriptor-reuse credibility, route-of-custody reporting, confidence-aware outcome reporting, and explicit structural no-action explanations without changing the frozen benchmark classes or project units.

## Phase 8
- [x] Phase 8 fixtures, run profiles, and a resumable soak harness exist locally.
- [x] A bounded local validation run exercises repeated workflow cycles and the planned stress lanes locally.
- [x] Run manifests and restart-resume semantics exist locally.
- [x] Bounded validation summaries can be regenerated locally.
- [x] The bounded local validation stayed inside the written `12 GB` runtime working-set cap.
- [ ] Real 24h soak completed locally.
- [ ] Real 72h soak completed locally.
- [ ] Full Phase 8 closure evidence exists locally and earns `AGIF_FABRIC_P8_PASS`.

## Phase 9
- [ ] Paper draft exists with a claims matrix tied to the frozen thresholds.
- [ ] Reproducibility package exists and reruns locally.
- [ ] Finish line deliverables are present in this workspace.
- [ ] Public release packaging remains out of scope.
