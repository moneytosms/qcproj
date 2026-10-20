# Quantum v3 (post-hoc, Born readout, ridge 0.01, 10-restart ensemble)

**Post-hoc.** The test period (2025-01-01 to 2026-10-19) was already scored by the v2 study,
so this result is not a clean confirmation. A clean test needs a new market or future data.

## Design (chosen on validation only, seeds 900-901, 2023-2024)

| Candidate | Validation log loss (mean of 2 seeds) |
| --- | ---: |
| v2 design, 5 restarts, ridge 0.001, best restart | 0.648 |
| v2, 5-restart ensemble | 0.636 |
| Pauli-expectation readout (hybrid), 5-restart ensemble | 0.636 |
| v2, 10-restart ensemble, ridge 0.001 | 0.633 |
| v2, 10-restart ensemble, ridge 0.003 | 0.632 |
| **v2, 10-restart ensemble, ridge 0.01 (v3)** | **0.631** |
| Softmax-v2 (classical, same inputs; from v2 protocol) | 0.623 |

Weekday one-hot flags and depth 4 were also tested on validation and were worse.

## Final models and test result (seeds 0-19, training rows only)

| Model | Test log loss | Brier | QLIKE |
| --- | ---: | ---: | ---: |
| quantum-v2 (recomputed, matches sealed 0.5288) | 0.5288 | 0.2915 | 0.4486 |
| **quantum-v3** | **0.5145** | **0.2872** | **0.4239** |
| softmax-v2 (sealed, classical) | 0.4962 | 0.2876 | 0.2888 |

v3 − v2 log loss: −0.0144, 95% block-bootstrap interval −0.022 to −0.007 (7-day blocks) and
−0.023 to −0.007 (30-day blocks). Both exclude zero.

**Quantum still does not beat classical.** Softmax-v2 remains better on test by 0.018 log
loss and on validation by 0.008.

## Notes

- Artifacts sealed before evaluation (`results/v3-study/seal.json`), evaluated once.
- After sealing and evaluation, one unused import was removed from
  `src/qcvol_v3/models.py` and one unused variable from `scripts/run_v3_study.py`. Neither
  changes any computation.
- The seal records a hash of `models.py` as it was when sealed, so it no longer matches the
  file. The artifact hashes still match. The import removal does not change any output.
- Full test suite: 94 passed, 1 skipped (requires the `finance` extra for one seal test).
