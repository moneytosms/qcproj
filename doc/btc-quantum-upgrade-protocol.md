# BTC quantum forecast improvement sweep

## Goal

Explore whether circuit changes, HAR corrections, or validation calibration improve the
existing BTC quantum forecast against matched classical models. This is development only;
the previously scored 2025-01-01 to 2026-10-19 test period is excluded from selection and
will not be rescored.

## Data and split

Use the committed Binance BTCUSDT daily data and the existing train/validation split:
training through 2022-12-31; validation 2023-01-01 through 2024-12-31. Fit all features,
HAR baselines, bins, and model parameters on training data. Validation-only temperature
calibration is part of selection and therefore exploratory.

## Candidate methods

Run the existing ETH upgrade sweep on BTC without changing its model implementations:
depths 1-3; weekend RZ, weekend RY, alternating entangler; direct and HAR-residual quantum
forecasts; quantum readout correction; and same-input softmax, small network, and HAR
classical baselines. Compare calibrated validation log loss, plus raw loss and optimizer
eligibility. Use two development seeds, two restarts, and a 5,000-call / 500-iteration fit
budget to bound runtime. Do not fit final seeds or evaluate the historical BTC test.

## Interpretation

Report candidate scores and paired 7/30-day validation intervals against the best
classical model. A validation win is exploratory because architectures and calibration
are selected on that same period. It can nominate a frozen candidate for future data only;
it cannot establish an out-of-sample improvement. No downloaded data or generated model
outputs are committed.

## Amendment 1: optimizer-cap sensitivity check

Before drawing a conclusion, refit the validation-selected quantum candidate and the
weekend network with equal 20,000-call / 2,000-iteration budgets, two fresh development
seeds (902, 903), and two restarts. This is a convergence sensitivity check on the same
validation dates, not an independent confirmation; retain all failures and make no
architectural changes after observing it.
