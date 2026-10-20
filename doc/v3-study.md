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

## Final comparison of all results (test period, post-hoc)

Test log loss, mean over 20 seeds (lower is better). Every value here is post-hoc, because the
v2 design was chosen after the test period was seen.

| Rank | Model | Type | Test log loss |
| --- | --- | --- | ---: |
| 1 | softmax-v2 | classical, 28 params | 0.4962 |
| 2 | network-v2 | classical, 26 params | 0.5042 |
| 3 | **quantum-v3** | quantum, 84 params | **0.5145** |
| 4 | softmax-har-D | classical | 0.5184 |
| 5 | har-residual | classical baseline | 0.5221 |
| 6 | quantum-v2 | quantum | 0.5288 |
| 7 | har-quantile | classical baseline | 0.5366 |
| 8 | quantum-har-D (Bharadwaj's `BornCircuit`) | quantum | 0.5695 |

Paired block-bootstrap contrasts, v3 minus other model (negative means v3 is better; 7- and
30-day blocks give the same intervals to three decimals):

- vs quantum-har-D: −0.055 [−0.072, −0.039]
- vs quantum-v2: −0.014 [−0.022, −0.007]
- vs softmax-v2: +0.018 [+0.007, +0.028]
- vs network-v2: +0.010 [+0.004, +0.017]
- vs softmax-har-D: −0.004 [−0.023, +0.012] (no clear difference)

**Conclusion.** v3 is the best quantum model tested. It is not better than classical: softmax-v2
and network-v2 beat it. The classical winner is also post-hoc, because its weekend and Monday
inputs were found on the test period. No quantum advantage is shown. A clean confirmation needs
data the design has never seen (the planned Ethereum market, or future Bitcoin data).

Comparison computed by `/tmp/claude-1001/scratch/compare_all.py` from sealed artifacts and
`results/fresh-study/evaluation/daily-losses.npz`.
