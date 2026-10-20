# Cross-market quantum v3 check

## Status and limitation

Protocol frozen before full archives are downloaded or any model is fitted for these assets.
The 2025-01-01 to 2026-10-19 dates were used in earlier studies on other assets, so this is
an exploratory cross-asset replication, not a new chronological holdout or independent
confirmation. Report it that way even if it passes.

## Fixed assets and data

Use Binance Spot USDT pairs LTCUSDT, BNBUSDT, and ADAUSDT. Selection is based only on the
availability of their first archive checksum files: LTC 2017-12, BNB 2017-11, ADA 2018-04.
No price or forecast labels were downloaded for selection. Use 5-minute klines through
2026-10-19, verify every ZIP with its `.CHECKSUM`, use the existing daily-RV builder and
record gaps without filling them. Freeze each input CSV and metadata hash before fitting.
Stop before fitting if any asset lacks at least 64 targets in train, validation, or test.

Use the existing `prepare_dates` splits: training targets through 2022-12-31, validation
2023-01-01 through 2024-12-31, test 2025-01-01 through 2026-10-19. Discard the same
30-day HAR warmup. Fit bins and feature transforms on training rows only.

## Frozen models

No architecture or hyperparameter selection is allowed on these assets.

- Quantum: the Born-readout v3 circuit, six squashed inputs, depth 3, ridge .01, ten
  training-objective-ranked restarts, ensemble of restart probabilities; final seeds 0-19.
- Classical controls: softmax-v2 (28 parameters) and network-v2 (26 parameters) on the
  same six inputs, from the frozen v2 definitions; final seeds 0-19.
- Use the same training rows, labels, bins, seeds, and optimizer budgets per asset. Do not
  drop failed or ineligible fits. Seal data, source, settings, and all fitted parameters
  before reading test labels. Evaluate each asset test once.

## Measures and decision

Primary metric: mean four-class test log loss across seeds. Also report Brier, QLIKE, and
paired circular 7- and 30-day bootstrap intervals for quantum minus each classical model.
The panel passes only if quantum has at least 5% lower mean log loss than both controls on
all three assets and every paired 97.5% interval is below zero. Any lesser result is a
failure to establish the marked improvement. Report each market separately and retain all
negative results.

A pass would be evidence on these three new assets only; it would not establish universal
quantum advantage, a clean future-period holdout, physical-hardware benefit, or improved
performance over the original paper on these assets. The existing BTC paper comparison
remains the paper-comparison evidence.
