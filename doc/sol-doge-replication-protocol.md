# SOLUSDT and DOGEUSDT fixed replication protocol

## Purpose

Test whether the frozen depth-1 RY quantum HAR hybrid's near-tie on ETH and BTC transfers
to two additional markets. The candidate and comparator set are fixed. This panel is the
last planned cross-market replication for this model version; do not add markets based on
these outcomes.

## Data

Use checksum-verified Binance Spot 5-minute klines, aggregated with the same UTC RV and
gap policy as ETH and BTC. Start with the monthly archive for SOLUSDT 2020-08 and DOGEUSDT
2019-07; end at 2026-10-19. The available starting monthly `.CHECKSUM` files were confirmed
at Binance's public archive before this protocol was committed. If either archive does not
provide at least 64 targets in each fixed split or lacks the full 2025-01-01 to 2026-10-19
test period, stop before fitting and report the coverage issue.

Use all available daily rows for training targets through 2022-12-31, validation targets
2023-01-01 through 2024-12-31, and the fixed test period 2025-01-01 through 2026-10-19.
The 30-day warm-up is discarded by the existing preparation code. Archive gaps remain
recorded and unfilled.

## Fixed model panel

- Quantum: depth-1 weekend-aware RY expert correcting the HAR baseline, frozen from ETH
  validation.
- Classical: weekend softmax, weekend two-unit network, and weekend softmax-HAR hybrid.
- Train 20 final seeds (0-19), five restarts, same train rows, labels, optimizer and
  optimizer budgets. Fit temperature on each seed's validation predictions, equally for
  every model, then carry it to test predictions.
- No candidate or depth selection on these markets. Keep all fits, including ineligible
  ones, in the summary.

## Success rule

Primary metric is calibrated four-class log loss. A cross-market marked improvement is
established only if the quantum model has at least 5% lower mean log loss than each of the
three classical models on **both** assets, and every paired 7- and 30-day 97.5% interval
for quantum-minus-classical log loss is below zero on both assets. Report all secondary
metrics regardless of outcome. This conjunction avoids selecting whichever market or
classical comparator happens to favor the quantum model.

Seal both datasets, metadata, config, code, fixed selection, and all model files before
opening either test. Evaluate each test once. Do not modify or selectively omit the
registered assets, models, intervals, or success rule after test scoring.
