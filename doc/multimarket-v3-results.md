# Cross-market quantum v3 results

20 October 2026. This is the one-time test evaluation from the frozen
[protocol](multimarket-v3-protocol.md). It tests the same Born v3 forecaster against
same-input softmax-v2 and network-v2 controls on Binance LTCUSDT, BNBUSDT, and ADAUSDT.
These assets were not used in the prior model studies. The test dates overlap earlier
studies on other assets, so the result is exploratory cross-asset evidence, not a fresh
chronological confirmation.

## Test results

Mean four-class log loss over 20 training seeds; lower is better.

| Asset | Quantum v3 | Softmax-v2 | Network-v2 | Best classical | Quantum gain vs best |
| --- | ---: | ---: | ---: | ---: | ---: |
| LTC | .613210 | **.596593** | .613345 | .596593 | −2.79% |
| BNB | .391824 | **.366583** | .368502 | .366583 | −6.89% |
| ADA | **.760215** | .769787 | .770901 | .769787 | +1.24% |

The quantum model misses the 5% rule on all three assets: it loses on LTC and BNB and
has only a 1.24% gain on ADA. The conjunctive panel gate fails.

Paired circular date-bootstrap intervals for quantum minus each classical model:

| Asset | Control | 7-day 95% interval | 30-day 95% interval |
| --- | --- | ---: | ---: |
| LTC | Softmax-v2 | [.00567, .02636] | [.00487, .02865] |
| LTC | Network-v2 | [−.00827, .00747] | [−.00727, .00745] |
| BNB | Softmax-v2 | [.01172, .03587] | [.00954, .03918] |
| BNB | Network-v2 | [.01476, .03139] | [.01249, .03431] |
| ADA | Softmax-v2 | [−.02526, .00370] | [−.02688, .00617] |
| ADA | Network-v2 | [−.02289, .00024] | [−.02053, .00080] |

Positive differences favor classical. The ADA intervals include zero, so its small gain is
uncertain. Other metrics show mixed results:

| Asset | Quantum Brier | Softmax Brier | Network Brier | Quantum QLIKE | Softmax QLIKE | Network QLIKE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LTC | .347126 | .347974 | .348733 | .459077 | .398703 | .420810 |
| BNB | .206937 | .205083 | .204693 | .719934 | .423111 | .436523 |
| ADA | .442452 | .450634 | .450303 | .665390 | .743976 | .682528 |

Quantum has lower Brier on LTC and ADA but not BNB. QLIKE favors classical on LTC and BNB;
quantum leads both controls on ADA. Generated evaluation files are excluded from the repo.

## Chronological validation calibration check

After the registered test comparison, an exploratory diagnostic fitted one probability
temperature on 2023 validation rows and scored the same frozen models on 2024 validation
rows. This was not part of the pass rule and did not use test labels.

| Asset | Quantum v3 | Softmax-v2 | Network-v2 |
| --- | ---: | ---: | ---: |
| LTC, raw | .707681 | .718167 | .714265 |
| LTC, 2023-calibrated | **.707195** | .716431 | .714761 |
| BNB, raw | .604848 | .604973 | **.600521** |
| BNB, 2023-calibrated | .601264 | .604837 | **.600509** |
| ADA, raw | .781585 | .798737 | .804244 |
| ADA, 2023-calibrated | **.778799** | .798855 | .804780 |

Quantum leads this 2024 validation slice on LTC and ADA, while network leads on BNB.
These validation differences did not yield a marked, consistent advantage on test; do not
use them to reopen the scored periods.

## Integrity and limits

- All 60 model fits per asset (20 seeds for each of three models) were trained on train rows.
- Data, protocol, configuration, code, and model artifacts were hashed. All seals passed
  before evaluation; the run records identify the runs as post-hoc.
- Each test set was opened once after the artifacts were committed. Generated model and
  evaluation files are excluded from this repository; all optimizer failures remain
  included in the reported 20-seed means.
- The result does not show a marked quantum improvement over classical controls. The
  existing Bitstamp paper comparison remains separate; this study does not test the paper
  model on these three assets.

The user goal remains open. Do not retune these test windows. A later candidate needs a
new protocol and data not used for selection or prior model testing.
