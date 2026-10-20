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
timestamps or missing calendar dates. Detect and report missing 5-minute bars from
timestamp differences without assuming timestamps remain epoch-aligned after a gap; do not
fill them. Record incomplete-day counts and source/output SHA-256 in metadata.

Daily RV is the sum of squared observed consecutive log-close returns, grouped by the UTC
date of the later bar. When a bar gap occurs, use the one observed close-to-close return
across that gap and never invent missing prices; record the gap and mark the day
incomplete. Daily return is log close-to-close; `intervals` counts only observed 5-minute
returns and `zero_volume_fraction` matches the Bitstamp daily schema. Drop the first 30
days as HAR lookback, so the first forecast target is 2017-09-16.

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
6. Quantum and softmax log-probability corrections to the same HAR baseline, with the
   weekend input supplied to both experts.

Every learned model uses the same train rows, target labels, log loss, optimizer budget,
validation dates, and target-day weekend feature where applicable. The four-input quantum
control is retained to measure the feature's effect. The classical models receive the
weekend feature so the comparison is fair.

## Selection and final evaluation

- Development seeds: 900 and 901; 5 fixed restarts per candidate fit.
- Test circuit depths 1-3, with 10 trainable weights per layer. This keeps the depth-3
  circuit's 30 parameters close to the 27-parameter classical network. Select quantum
  depth by mean validation log loss, ties to lower depth. No settings are
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

## Amendment 1: archive gap handling (20 Oct 2026, before model evaluation)

The checksum-verified archive contains 33 timestamp gaps affecting 34 UTC dates. After a
large historical gap, timestamps resume with a 94.8-second offset from their prior
5-minute grid, although subsequent bars remain 5 minutes apart. The builder therefore
checks timestamp differences rather than requiring epoch-aligned timestamps. It includes
each observed close-to-close return once in that date's RV, including one observed return
across a gap; it does not synthesize missing bars. The exact gap list, affected days, and
number of fully sampled 5-minute returns per day are committed in the metadata. No
complete calendar dates are missing; all incomplete dates are in 2023 or earlier, and the
2025-01-01 to 2026-10-19 test period has 288 observed bars per day. The forecast procedure
remains unchanged.

## Amendment 2: validation-only circuit variants (20 Oct 2026)

The first validation sweep did not meet the goal: the best direct quantum weekend model
had mean log loss 0.6076, while the weekend network had 0.5303; the quantum-HAR hybrid
had 0.5306 versus 0.5160 for the softmax-HAR hybrid. The ETH test remains unopened.

Add two quantum variants to the same development selection, using the same inputs, 10
weights per layer, depths 1-3, seeds, restarts, training rows, and validation rule:

1. Replace each weekend-conditioned RZ with RY.
2. Keep the weekend-conditioned RZ but alternate CNOT direction between layers.

Retain all original candidates. Select the best direct weekend quantum architecture and
depth by mean validation log loss, then compare that fixed selection with all classical
models after final training. This amendment does not change the test set, metrics, or
success threshold. No new test score has been computed.

## Amendment 3: RY circuit correction on HAR (20 Oct 2026)

The validation-selected direct RY circuit (0.5711 mean loss) and RZ circuit (0.6076)
remain behind the weekend network (0.5303). The existing quantum correction to the HAR
residual model (RZ expert, depth 1) scored 0.5306, close to the network but behind the
classical softmax-HAR correction (0.5160). Add one candidate: the same HAR plus a
weekend-aware RY quantum expert, depths 1-3. Compare it with the same-input softmax-HAR
correction using the existing log-probability formula and train/validation splits. No
test score has been computed.

Select the strongest quantum model (direct or HAR correction) by two-seed validation loss.
For a marked improvement, it must beat the best classical validation family by at least
5% on test, with paired 7- and 30-day intervals below zero. The classical comparison set
is fixed as weekend softmax, weekend network, and weekend softmax-HAR correction.

