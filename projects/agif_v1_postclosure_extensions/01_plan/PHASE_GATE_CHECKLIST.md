# Phase Gate Checklist

## Setup And Freeze
- [x] project-local source-of-truth files exist
- [x] fixed denominator `130` is recorded locally
- [x] extension tokens are recorded locally
- [x] ordered dependency rules are recorded locally
- [x] final bundle verifier order is frozen as Gap 1 -> Gap 2 -> Gap 3
- [x] root AGIF v1 closed-state isolation is recorded locally
- [x] Gap 1 start rules are frozen:
  - fixed deterministic `40`-case stream
  - same stream and order for elastic and no-split control
  - no fake stress-mode switch
  - governance-level split disable in the control run
  - gate failure if no organic split occurs inside the stream
- [x] Gap 3 start rules are frozen:
  - same `5` POS cases and same order for both runs
  - governance-level cross-domain transfer disable in the control run
  - explicit `transfer_approval` required for counted cross-domain influence
- [x] `python3 scripts/check_v1x_setup.py` passes locally
- [x] `AGIF_FABRIC_V1X_SETUP_PASS` is earned honestly

## Gap 1 Organic Load
- [ ] deterministic 40-case stream is frozen
- [ ] elastic vs no-split control comparison is frozen
- [ ] organically approved split occurs inside the deterministic stream
- [ ] latency or queue improvement is shown without accuracy regression
- [ ] `AGIF_FABRIC_V1X_G1_PASS` is earned honestly

## Gap 2 Skill Graph
- [ ] descriptor graph and transfer-approval path exist
- [ ] provenance is explicit for transferred descriptors
- [ ] low-quality transfers abstain or are denied
- [ ] `AGIF_FABRIC_V1X_G2_PASS` is earned honestly

## Gap 3 POS Domain
- [ ] bounded POS domain cases are frozen
- [ ] transfer-enabled and control runs use the same case suite
- [ ] finance-origin descriptor causally improves a POS result
- [ ] `AGIF_FABRIC_V1X_G3_PASS` is earned honestly

## Bundle Close
- [ ] ordered extension chain passes
- [ ] root AGIF v1 closure still passes
- [ ] root AGIF v1 progress still reads `600/600`
- [ ] `AGIF_FABRIC_V1X_PASS` is earned honestly
