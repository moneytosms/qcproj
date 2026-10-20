# Temperature-calibrated quantum v3 cross-market follow-up

## Status

This exploratory follow-up was specified after the LTC/BNB/ADA study and its chronological
validation diagnostic. The new assets and their test labels were not used in those studies,
but the candidate choice was informed by earlier results. A passing result is cross-asset
evidence only, not an independent confirmatory claim.

## Fixed assets and data

Use Binance Spot 5-minute klines through 2026-10-19 for LINKUSDT, DOTUSDT, and AVAXUSDT.
Their first archive checksum files are available for LINK 2019-01, DOT 2020-08, and AVAX
2020-09. Use the existing checksum-verifying Binance builder. Keep gaps unfilled and record
the resulting daily data and metadata hashes. Stop before fitting if any split has fewer
than 64 targets.

Use the existing 30-day HAR warmup and date splits: train through 2022-12-31, validation
2023-01-01 through 2024-12-31, and test 2025-01-01 through 2026-10-19. Fit bins and feature
transforms on training rows only.

## Frozen models and calibration

No architecture or hyperparameter selection is allowed on these assets.

- Quantum: Born v3, six inputs, depth 3, ridge .01, ten restart ensemble, seeds 0-19.
- Classical controls: softmax-v2 (28 parameters) and network-v2 (26 parameters), six
  identical inputs, seeds 0-19.
- Fit each model on training rows only. For each model and seed, fit one temperature in
  [.2, 5] by minimizing 2023 validation log loss. Apply that fixed temperature to 2024
  validation and test predictions. Fit the temperature separately for each model family;
  no test labels enter calibration.
- Retain all fit attempts and failed-fit status. Seal data, source, configuration, and all
  trained parameters before any test evaluation. Evaluate each test once.

## Decision rule

Primary measure is mean calibrated four-class test log loss over seeds. Also report Brier,
QLIKE, and paired circular 7- and 30-day date-bootstrap intervals for quantum minus each
classical control. A marked improvement requires at least 5% lower mean loss than both
classical controls on all three assets, with all paired 97.5% intervals below zero.
Otherwise report failure to establish the improvement. Do not retune any previously
scored test period.

The test dates overlap earlier asset studies. Even a pass cannot establish performance on
future dates, a universal advantage, or a hardware benefit.
