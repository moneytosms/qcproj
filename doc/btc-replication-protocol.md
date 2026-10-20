# BTCUSDT quantum forecast replication protocol

## Objective and status

This is a fixed-architecture replication of the ETH study, not a new model search. The
ETH test result was nearly tied with the best classical model and did not meet its marked
improvement threshold. Freeze this BTC plan before downloading or inspecting BTC scores.

## Data and split

Use checksum-verified Binance Spot BTCUSDT 5-minute klines and the same UTC daily RV
calculation, gap policy, features, and date splits as the ETH study. Expected coverage is
2017-08-17 through 2026-10-19. If the archive does not cover the registered dates or has
missing full UTC dates, stop and amend this protocol before model fitting. Test targets
are 2025-01-01 through 2026-10-19. Do not inspect test metrics until all training files
are sealed.

## Fixed models

- Quantum: depth-1 weekend-aware RY expert correcting the same HAR probability baseline.
- Classical comparison: weekend-aware softmax, weekend-aware two-unit network, and
  weekend-aware softmax expert on the HAR baseline.
- Use the same four HAR inputs and target-weekend flag, train-only feature scaling,
  training dates, labels, optimizer, five restarts, and 20 final seeds (0-19) as ETH.
- Fit a scalar temperature on each seed's BTC validation predictions, uniformly for every
  model, and apply it to that seed's test predictions.
- Do not select architecture, depth, restarts, or thresholds from BTC validation or test.
  The quantum depth and family were frozen from ETH validation before its test was opened.

## Evaluation and decision rule

Primary metric is calibrated four-class log loss. Report raw and calibrated log loss, RPS,
extreme-bin Brier score, QLIKE, all 20 seed results, and paired circular date-block
bootstrap intervals at 7 and 30 days for the quantum model against each classical model.
Use 97.5% two-sided intervals (2.5% family-wise error across the ETH and BTC market
studies); both intervals must be below zero against the best classical model. The quantum
model must also reduce mean log loss by at least 5% versus the best classical model.
Include ineligible fits and report their count.

No model may be retuned on BTC test data. ETH and BTC test windows overlap in calendar
time, so the two results are not independent evidence about market regimes. A positive BTC
replication is market-specific evidence, not proof of general quantum advantage or a
hardware speedup. Any further market requires its own precommitted protocol and must be
identified as another sequential experiment.
