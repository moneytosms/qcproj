# Temperature-calibrated quantum v3 results

20 October 2026. This is the one-time evaluation from the frozen
[protocol](calibrated-v3-protocol.md), using a quantum v3 forecast and same-input softmax
and network controls on Binance LINKUSDT, DOTUSDT, and AVAXUSDT. Temperature was fitted
on 2023 validation rows for each model and seed, then applied to test forecasts. The asset
selection and candidate were informed by earlier study results, and the 2025–2026 dates
overlap studies on other assets; treat this as exploratory cross-asset evidence.

## Test results

Mean calibrated four-class log loss over 20 seeds; lower is better.

| Asset | Quantum v3 | Softmax-v2 | Network-v2 | Best classical | Gain vs best |
| --- | ---: | ---: | ---: | ---: | ---: |
| LINK | **.577113** | .591609 | .596943 | .591609 | +2.45% |
| DOT | **.638703** | .642954 | .653899 | .642954 | +0.66% |
| AVAX | **.448466** | .475457 | .518658 | .475457 | **+5.68%** |

On AVAX, quantum v3 beats softmax by 5.68% and the network by 13.53%. Both 7- and 30-day
date-bootstrap intervals for quantum-minus-classical log loss are below zero:

| AVAX control | 7-day 95% interval | 30-day 95% interval |
| --- | ---: | ---: |
| Softmax-v2 | [−.04814, −.01039] | [−.04826, −.01078] |
| Network-v2 | [−.11564, −.03427] | [−.11445, −.03455] |

This is a marked single-asset gain on the registered primary metric. It does **not** pass
the frozen three-asset rule: LINK and DOT are below the 5% threshold and their intervals
against softmax include zero. The panel therefore does not establish a transferable gain.

There is a metric tradeoff. Quantum has lower Brier score on all three assets, but higher
QLIKE than both classical models on all three. Per-seed fit and evaluation files are not
included in the repository; the aggregate metrics and all six interval comparisons are
reported here.

## Integrity and limits

- Training used train rows only; each per-model temperature used only 2023 validation rows.
- The data, protocol, configuration, source, and model hashes were checked before scoring.
  Fit/evaluation artifacts were created before test evaluation, then excluded from this PR
  to comply with the repository rule against committing downloaded datasets and generated
  experiment output. The scored summary is retained; individual seed records are not.
- Each 657-day test set was evaluated once. All 20 seeds and all ten quantum restart
  outputs per seed are retained in the reported means.
- The existing quantum restart runner saves parameters and objectives but not optimizer
  convergence flags or iteration counts. This protocol detail was not met; the primary
  scores remain reproducible from the saved parameters, but optimizer termination cannot
  be audited for this run.
- These results do not show improvement over the paper model on these assets. The prior
  paper comparison is separate. The panel is exploratory because the design and asset
  choice followed earlier outcomes.

The requested single-asset marked improvement is demonstrated on AVAX's primary log-loss
metric. The three-asset transfer rule fails, and QLIKE moves in the wrong direction, so
this does not establish a general or all-metric quantum advantage. Independent AVAX
replication remains the next scientific step.
