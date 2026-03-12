# Benchmark Contract

## Phase 2 Freeze Status
- Frozen on `2026-03-12` for Phase 2.
- Benchmark classes and metrics are frozen now so later phases cannot redefine success after implementation starts.

## Purpose
The benchmark contract defines how AGIF v1 will be compared inside the bounded finance document workflow proof domain.

This contract is part of the scientific claim. It must not be deferred until after code exists.

## Frozen Benchmark Scope
- Proof domain: document/workflow intelligence
- First benchmark tissue: finance document workflow
- Comparison target: determine whether AGIF structure adds value over simpler alternatives without breaking safety, replayability, or machine limits

## Frozen Benchmark Classes

### 1. Flat baseline
A non-fabric baseline with no real cell or tissue structure.

Frozen characteristics:
- one flat workflow path
- no real cell lineage
- no governed descriptor sharing
- no bounded adaptation loop
- may still use the same task inputs and evaluation harness

### 2. Multi-cell fabric without bounded adaptation
A real multi-cell and tissue-organized system that keeps structure but disables bounded adaptation benefits.

Frozen characteristics:
- real cells and tissues
- shared workspace
- governance path
- no descriptor-sharing improvement path
- no reviewed promotion path that changes later behavior

### 3. Multi-cell fabric with bounded adaptation and descriptor sharing
The full AGIF v1 target class.

Frozen characteristics:
- real cells and tissues
- shared workspace
- local and fabric memory
- reviewed promotion
- bounded descriptor reuse
- utility and need-signal pressure
- governed split, merge, hibernate, reactivate, quarantine, replay, and rollback paths as implemented later

## Frozen Fair-Comparison Rules
All benchmark classes must use:
- the same proof-domain task family
- the same evaluation fixtures
- the same output scoring rules
- the same machine envelope
- the same bounded runner contract
- the same replay or evidence rules where applicable

If stochastic components exist later, runs must also use the same seeds or seed-recording policy.

## Frozen Required Metrics
All later benchmark work must report these metrics:

| Metric | Frozen meaning |
| --- | --- |
| task accuracy / correctness | How often the workflow output matches the expected bounded result for the task |
| replay determinism | How consistently replay reproduces materially the same result under the same inputs and configuration |
| descriptor reuse rate | Fraction of eligible reused descriptors that are actually reused in the bounded-adaptation system |
| improvement from prior descriptors | Measured gain when prior reviewed descriptors are available versus withheld |
| memory density gain | Useful retained value per unit of retained storage compared with flatter or less-disciplined alternatives |
| active/logical population ratio | Live active cells divided by total logical cells known to the fabric |
| split/merge efficiency | Quality or resource benefit achieved relative to the structural cost of split or merge events |
| governance success rate | How often governance correctly allows beneficial actions and blocks unsafe or misaligned ones |
| resource usage | Runtime memory, compute, and storage behavior against the locked machine envelope |
| bounded forgetting | Performance loss on prior tasks after bounded adaptation or consolidation |
| unsafe/misaligned action rate | Rate of unsafe, policy-breaking, or materially misaligned actions |

## Frozen Metric Interpretation Rules
- task accuracy / correctness must be measured against explicit fixture truth, policy truth, or bounded review truth
- replay determinism must use the same inputs, configuration, and seeds when seeds exist
- descriptor reuse rate must count only descriptors that were eligible and trusted enough to be used
- improvement from prior descriptors must compare before and after reviewed descriptor availability
- memory density gain must use retained useful artifacts, not raw logs
- active/logical population ratio must show that logical population can exceed active runtime population
- split/merge efficiency must include both the benefit and the structural cost
- governance success rate must include both correct approvals and correct rejections
- resource usage must report whether the run stayed under:
  - runtime working set `<= 12 GB`
  - total project and evidence footprint `<= 35 GB`
- bounded forgetting must respect the frozen falsification threshold of `<= 10%`
- unsafe/misaligned action rate must respect the frozen falsification threshold of `<= 0.1%`

## Frozen Threshold Binding
The benchmark contract is bound to the already frozen falsification thresholds:
- catastrophic forgetting: `<= 10%`
- unsafe or misaligned action rate: `<= 0.1%`
- resource depletion, overload, or repeated rollback: `<= 5%` operational time
- sample or compute cost to reach bounded target performance: `<= 2x` flat baseline
- runtime working set: `<= 12 GB`
- total project and evidence footprint: `<= 35 GB`

If the later benchmark results break these thresholds, AGIF v1 must not be presented as a successful bounded proof.

## Frozen Evidence Expectations
Later benchmark evidence must be able to show:
- which class was run
- which configuration and fixtures were used
- which machine profile was used
- what results were produced
- what replay and governance traces exist
- whether the run passed or failed the frozen thresholds

## Relation to CLI Contract
The later `runner/cell fabric evidence` command must write an evidence bundle that is compatible with this contract. The exact file layout may be implemented later, but the command may not change the benchmark classes or metrics frozen here.

## Verification Status
- Locally verified:
  - the three benchmark classes are frozen in writing
  - the required benchmark metrics are frozen in writing
  - the benchmark contract is tied back to the locked falsification thresholds and machine envelope
- Assumed only:
  - actual benchmark harness behavior
  - actual benchmark results
