# ETH quantum forecasting upgrade protocol

Written before any ETH validation or test score is computed.

## Goal

Test whether a stronger two-qubit forecaster can improve on same-input classical
forecasting for ETH realized variance. The main candidate adds the target day's weekend
indicator to the circuit. This tests the documented weekend effect while giving the same
feature to each classical comparator. We will report negative results; no result will be
described as quantum advantage unless evidence supports that claim.

## Data and splits

Use Binance public spot ETHUSDT 5-minute klines. Monthly ZIPs are used through
2026-09; daily ZIPs supply 2026-10-01 through 2026-10-19 because monthly data for the
current month is not yet released. Verify each ZIP against its `.CHECKSUM` sidecar before
parsing it. Binance documents that spot timestamps from 2025-01-01 use microseconds;
earlier spot timestamps use milliseconds. Convert both to UTC and fail on duplicate
timestamps or missing calendar dates. Detect and report missing 5-minute bars without
filling them; record incomplete-day counts and source/output SHA-256 in metadata.

Daily RV is the sum of squared consecutive 5-minute log-close returns, grouped by the UTC
date of the later bar. Daily return is log close-to-close; `intervals` and
`zero_volume_fraction` match the Bitstamp daily schema. Drop the first 30 days as HAR
lookback, so the first forecast target is 2017-09-16.

| Split | Target dates | Use |
| --- | --- | --- |
| Train | 2017-09-16 to 2022-12-31 | Fit preprocessing, bins, and model parameters |
| Validation | 2023-01-01 to 2024-12-31 | Select architecture and depth only |
| Test | 2025-01-01 to 2026-10-19 | One final comparison after sealing |

All feature scaling and four log-RV category thresholds (30/70/95% quantiles) use train
rows only. The test period remains unopened until the final models and code are sealed.

## Models

1. Existing 2-qubit HAR Born model, as the no-weekday quantum control.
2. Quantum-weekend model: same four standardized HAR inputs plus standardized target-day
   weekend flag; each layer applies a learned conditional Z rotation to both qubits before
   the CNOT. Depths 1-4 are candidate settings.
3. Multinomial softmax with the same four HAR inputs and weekend feature.
4. Two-hidden-unit tanh network with the same inputs and 27 parameters, close to the
   30-parameter depth-3 quantum candidate.
5. HAR residual/quantile baseline with a target-weekend term in its location regression.

Every learned model uses the same train rows, target labels, log loss, optimizer budget,
validation dates, and target-day weekend feature where applicable. The four-input quantum
control is retained to measure the feature's effect. The classical models receive the
weekend feature so the comparison is fair.

## Selection and final evaluation

- Development seeds: 900 and 901; 5 fixed restarts per candidate fit.
- Select quantum depth by mean validation log loss, ties to lower depth. No settings are
  selected from test results.
- Final quantum models use seeds 0-19 with selected depth. Classical comparators use the
  same final seeds where their fitting procedure is stochastic.
- Before test evaluation, hash the daily CSV, source metadata, candidate code, selected
  settings, and trained models. Test evaluation is one run and reports every candidate.
- Primary metric: four-level test log loss. Also report ranked probability score, extreme
  bin Brier score, expected-RV QLIKE, and paired 7- and 30-day circular block bootstrap
  intervals for quantum-weekend minus each classical comparator.
- A marked improvement requires at least 5% lower mean test log loss than both softmax and
  the small network, with both 95% block-bootstrap intervals below zero. Otherwise state
  that this experiment did not meet the target. Do not retune on ETH test; any further
  candidate needs a new protocol and an untouched test period.

## Limits

ETH is one market and one chronological test period. Binance archives can be revised. The
result cannot establish a universal quantum advantage or hardware speedup. A validation
win that fails on test remains a failed headline result.

## Sources

- Binance public archive layout, checksum files, and timestamp-unit notice:
  [binance/binance-public-data README](https://github.com/binance/binance-public-data/).
- Binance Spot kline UTC semantics:
  [Spot REST API kline documentation](https://developers.binance.com/en/docs/products/spot/rest-api#klinecandlestick-data).
- Binance documents that daily files appear the next day and monthly files on the first
  Monday of the month in the public-data README above.
