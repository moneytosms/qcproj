# Fresh-data study protocol: memory + realism, and HAR + quantum hybrids

Written and committed **before any model was trained or scored** on this data. The code
that scores the test period (`qcvol.fresh_runner.evaluate`) is part of the same commit and
is protected by the training seal, so it cannot change after training.

## Why this study

The frozen 20-seed study ([final-study.md](final-study.md)) found no quantum advantage and
found that realism training (A) hurt on test. Reading its code shows three things it did not
test, which this study does:

1. **A was never combined with memory (B).** Its quantum family is `ShortBorn`, which sees
   only yesterday. A then asked a model with one day of memory to reproduce 7- and 30-day
   autocorrelation, which it cannot represent. B was rejected earlier on a different model
   (the 1-qubit point forecaster, by MSE), not on the 2-qubit range model.
2. **The realism target was biased.** Generated paths of 128 days were compared with the
   autocorrelation of the *full* training series. Autocorrelation at lag 30 measured on short
   windows is much lower. On this study's training data: full sample 0.302, mean over
   256-day windows 0.136. Here, targets are always measured on real windows of the same
   length as the simulated paths.
3. **Quantum was only compared against classical, never added on top of it.** The hybrid
   models below ask whether a circuit adds anything to the best classical forecaster.

The test period was also reused: the earlier studies inspected their test block during
development. This study uses new data with a test period nobody has modelled.

## Data

* Source: Bitstamp BTC/USD 1-minute candles,
  [ff137/bitstamp-btcusd-minute-data](https://github.com/ff137/bitstamp-btcusd-minute-data),
  pinned commit `c711b69cdcffd1356247126b1e0f53455efb70ba` (data CC BY-SA 4.0 / CC BY 4.0).
* Daily RV = sum of squared 5-minute log returns within each UTC day; daily return =
  log close-to-close. Built by `scripts/build_bitstamp_daily.py` into
  `data/bitstamp_daily.csv` (3,610 complete days, 2016-12-01 to 2026-10-19, no gaps).
* **The paper's data is this same source.** Matching Takaishi's published series against
  ours gives correlation 0.9998 (RV) and 1.0000 (returns) for Bitstamp
  **2020-08-30 to 2023-02-28**. The paper does not state its dates.

| Split | Target dates | Days |
| --- | --- | ---: |
| Train | 2016-12-31 to 2022-12-31 | 2,192 |
| Validation | 2023-01-01 to 2024-12-31 | 731 |
| Test | 2025-01-01 to 2026-10-19 | 657 |

The test period lies entirely after the paper's data and after everything the earlier
studies used. Feature scaling, the four volatility levels (30/70/95% training quantiles) and
the empirical value pools use training rows only.

Disclosure: while checking data quality, yearly median RV for every year (including 2025
and 2026) and the last three rows of the file were printed. No model was fitted, selected or
scored on 2025-2026 data.

## Models

All learned models output probabilities for calm / normal / wild / extreme and are trained
with log loss. "-har" models see yesterday's log RV, the 7- and 30-day mean log RV and
yesterday's return. "-short" models see only yesterday's log RV and return.

| Name | What it is | Parameters |
| --- | --- | ---: |
| quantum-har | 2-qubit re-uploading circuit (Bharadwaj's `BornCircuit`), depth chosen on validation | 8 x depth |
| quantum-short | same circuit, week/month slots filled with yesterday | 8 x depth |
| softmax-har / -short | multinomial logistic regression | 20 / 9 |
| network-har / -short | small tanh networks, ridge 0.001 | 24 / 24 |
| hybrid-quantum | HAR-quantile probabilities x circuit^gamma, renormalized; gamma = 0 is HAR | 1 + 8 x depth |
| hybrid-softmax | same with softmax-har as the expert (classical twin) | 21 |
| baselines | frequency, short-AR, HAR residual, HAR quantile, short quantile, calibrated GARCH | fixed |

D = forecast training only. A = start from D, then minimize
`log loss + lambda x realism distance`, where the realism distance compares four moments
(autocorrelation of log RV at lags 1, 7, 30 and the spread of daily changes) of 4 simulated
256-day paths with the mean over real 256-day training windows, scaled by their spread.

## Fixed procedure

1. **Development** (seeds 900, 901; validation only): D fits for every model, depths 1-3
   for circuits, 5 restarts each (best by training objective). Depth = lowest mean validation
   log loss. Then A for lambda in {0.01, 0.05, 0.2, 1.0} at the chosen depth.
2. **Lambda choice**: selection score = validation log loss + 0.01 x validation realism
   distance (731-day simulated paths vs the validation series, same length), as in the
   earlier study. lambda = 0 (keep D) is a candidate. The best non-zero lambda is always
   trained as "A" so A-versus-D can be reported on test either way.
3. **Final training**: seeds 0-19 with frozen choices. Then seal (hashes of all artifacts
   and of the package source).
4. **Test scoring, once**: log loss, ranked probability score, extreme-level Brier score;
   realism of 32 simulated paths as long as the test period against the test series;
   paired circular block bootstrap (7- and 30-day blocks, 2,000 replicates) on
   seed-averaged daily losses for the contrasts below.

Pre-registered contrasts (negative favours the left model): quantum-har A vs D; quantum
har vs short (D and A); softmax-har and network-har A vs D; quantum-har D vs softmax-har D,
network-har D and HAR quantile; quantum-har A vs softmax-har A and network-har A;
hybrid-quantum vs HAR quantile; hybrid-softmax vs HAR quantile; hybrid-quantum vs
hybrid-softmax.

All results are reported, including unfavourable ones. No setting is changed after test
scores are seen.
