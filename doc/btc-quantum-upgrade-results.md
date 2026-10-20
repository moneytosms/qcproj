# BTC quantum improvement sweep: exploratory validation result

20 October 2026. This reuses the fixed BTC training and 2023-2024 validation dates. The
previously scored 2025-01-01 to 2026-10-19 test was not evaluated. See the
[precommitted protocol](btc-quantum-upgrade-protocol.md).

## Result

The best validation candidate was a depth-3 RY quantum readout added as a log-probability
correction to the training-only HAR forecast (`hybrid-quantum-readout-ry`). At the initial
5,000-call budget, its mean calibrated validation log loss was **0.647738**, versus
**0.661423** for the weekend network, **0.661841** for the HAR forecast, and **0.665553**
for weekend softmax. Lower is better. The candidate was selected after comparing multiple
quantum structures on these same validation dates, so this is an exploratory result.

The initial quantum candidate and network both hit the 5,000-call optimizer cap. A
pre-registered sensitivity check refit both with 20,000 calls, 2,000 iterations, two fresh
seeds, and two restarts. Both methods converged successfully:

| Development seed | Quantum readout RY | Weekend network |
| ---: | ---: | ---: |
| 902 | 0.651540 | 0.661434 |
| 903 | 0.639767 | 0.661433 |
| Mean | **0.645654** | 0.661433 |

The quantum validation loss is **2.39% lower**. Paired circular date-block intervals for
quantum minus network were [−0.03091, −0.00200] at 7 days and [−0.03011, −0.00368] at 30
days. Since architecture selection and temperature fitting used this same validation
period, these intervals are descriptive and do not account for model-selection bias.

## Limits

This suggests that the RY quantum readout can improve the current classical-comparable
BTC validation score when used as a HAR correction. It does not establish better BTC test
performance: the historical test period was already used for earlier models and was kept
closed here. The original fixed RY HAR hybrid scored 0.531976 on that old test versus
0.530880 for the weekend network; the new candidate has no test score. A fresh BTC
chronological holdout is needed for confirmation. This noiseless simulator result does not
show quantum hardware speedup or general quantum advantage.

Generated fit records are local under `results/btc-quantum-upgrade/` and are not committed.
