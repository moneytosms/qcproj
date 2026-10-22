# Frontier v4–v6 measured development results

22 October 2026. **No robust superiority demonstrated.** Completed 15 real-data runs,
240/240 eligible readout fits and 15 transformed-HAR fits under the
[fixed sprint protocol](frontier-protocol.md). All five series have 366 audit dates
in 2024. Heads trained through 2022; 2023 selected models, ridge and mixtures.
The 2024 period was already exposed in earlier work. No 2025 onward targets
entered feature construction, fitting, selection or scoring in this experiment.

## NLL scorecard

Lower is better; mean of per-run losses over seeds 42, 43, 44. This is not the
loss of an additional cross-seed probability ensemble. The comparator is selected
using 2023 NLL separately within each run, not hindsight-selected on 2024.

| Series | Classical selected | v4 | v5 | v6 | v6 gain |
|---|---:|---:|---:|---:|---:|
| bitstamp_daily | 0.738965 | 0.737905 | 0.743591 | 0.738784 | +0.024% |
| btcusdt_daily | 0.742156 | 0.741634 | 0.745168 | 0.742900 | -0.100% |
| dogeusdt_daily | 0.754946 | 0.782063 | 0.759456 | 0.753313 | +0.216% |
| ethusdt_daily | 0.666774 | 0.686087 | 0.665522 | 0.663591 | +0.477% |
| solusdt_daily | 0.605712 | 0.618633 | 0.618002 | 0.606636 | -0.153% |

Positive gain means lower loss than the selected classical control. v4 gains only
0.14%/0.07% on the two BTC series and loses 2.13–3.59% elsewhere. v5 improves
NLL only on ETH (0.19%). v6 has small gains on ETH, DOGE and Bitstamp BTC, and
loses on Binance BTC and SOL. Do not select the best audit seed or track afterward.

## Secondary metrics

| Series | Model | Brier | QLIKE |
|---|---|---:|---:|
| bitstamp_daily | classical-selected | 0.443975 | 0.261887 |
| bitstamp_daily | v4 | 0.437300 | 0.312409 |
| bitstamp_daily | v5 | 0.443866 | 0.262627 |
| bitstamp_daily | v6 | 0.440761 | 0.262542 |
| btcusdt_daily | classical-selected | 0.444821 | 0.263668 |
| btcusdt_daily | v4 | 0.436469 | 0.313182 |
| btcusdt_daily | v5 | 0.439810 | 0.274366 |
| btcusdt_daily | v6 | 0.441371 | 0.265835 |
| dogeusdt_daily | classical-selected | 0.440597 | 0.342181 |
| dogeusdt_daily | v4 | 0.457248 | 0.405287 |
| dogeusdt_daily | v5 | 0.444550 | 0.331157 |
| dogeusdt_daily | v6 | 0.440314 | 0.336047 |
| ethusdt_daily | classical-selected | 0.382507 | 0.260984 |
| ethusdt_daily | v4 | 0.394648 | 0.319930 |
| ethusdt_daily | v5 | 0.383682 | 0.265245 |
| ethusdt_daily | v6 | 0.382020 | 0.264005 |
| solusdt_daily | classical-selected | 0.342720 | 0.237942 |
| solusdt_daily | v4 | 0.348086 | 0.270456 |
| solusdt_daily | v5 | 0.348201 | 0.237689 |
| solusdt_daily | v6 | 0.342821 | 0.239300 |

v4 worsens QLIKE on every series. v6 improves QLIKE only on DOGE; on ETH its
small NLL improvement accompanies worse QLIKE. Four class probabilities with
fixed training-bin mean RV cannot model within-bin severity adaptively.

## Paired uncertainty

95% circular date-block bootstrap, 4,000 replicates, seed 20261022. Resample
paired dates after averaging daily losses over run seeds. These are **unadjusted
descriptive intervals on reused development data**. They do not repair historical
selection or control the complete family of model/asset comparisons.

| Series | v6 minus classical | 7-day interval | 30-day interval |
|---|---:|---|---|
| bitstamp_daily | -0.000181 | [-0.005527, +0.004580] | [-0.004591, +0.003948] |
| btcusdt_daily | +0.000744 | [-0.004599, +0.005765] | [-0.003385, +0.004923] |
| dogeusdt_daily | -0.001633 | [-0.009588, +0.006658] | [-0.009996, +0.007048] |
| ethusdt_daily | -0.003183 | [-0.010474, +0.002605] | [-0.009935, +0.002457] |
| solusdt_daily | +0.000924 | [-0.006134, +0.008328] | [-0.006854, +0.008755] |

Every v6 interval includes zero. No strong positive inference follows even before
multiplicity correction. The two BTC venues and contemporaneous crypto series
are correlated, not five independent confirmations.

## Implementation, effort and limitations

- v4 uses three frozen depth-two, two-qubit WeekendBorn feature maps (12 outputs),
  plus five shared inputs, with a 54-coefficient reference-logit readout.
- v5 adds the same readout to transformed-HAR log probabilities. Zero correction
  reproduces HAR; calibration may select the explicit uncorrected fallback.
- Linear, sine and tanh heads, plus their HAR-offset variants, receive the same
  five inputs. Nonlinear feature width matches; circuit/classical frozen parameter
  counts are 60/72. Linear heads fit 18 coefficients. Effective capacity differs.
- Two ridges (0.001/0.01) yield 16 head fits per run. All 240 pass success and
  infinity-norm gradient <=1e-4. Every fit, including any failure, is saved.
- v6 selects among 15 discrete mixture pairs on 2023. No equally searched
  classical-only mixture was run; mixture gains cannot establish quantum value.
- The HAR reference uses squashed inputs, not canonical raw-log HAR. GARCH, HARQ,
  boosted trees, learned Fourier frequencies and continuous-density controls remain
  necessary. The tested panel is not all classical forecasting.
- Feature seed banks overlap: 42–44, 43–45, 44–46. These are correlated sensitivity
  checks. No seed-based confidence interval is reported.
- These fixed circuit features are not end-to-end trained v3 successors. No direct
  v3 improvement, hardware gain or computational advantage is measured.
- Simulator and optimizer times are measured local CPU times, not hardware estimates.

| Series | Total fit/run seconds (3 runs) | Effective quantum weights |
|---|---:|---|
| bitstamp_daily | 2.061 | [1.0, 0.75, 0.0] |
| btcusdt_daily | 1.822 | [1.0, 0.5, 0.0] |
| dogeusdt_daily | 1.374 | [0.5, 0.5, 0.5] |
| ethusdt_daily | 1.891 | [0.125, 0.0, 0.5] |
| solusdt_daily | 1.047 | [1.0, 0.5, 0.5] |

Times include feature preparation and fitting, exclude CSV output and aggregate
replay. Thread limits were OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1.

## Reproduction

Use a new output directory. Installed dependencies were restored with
`uv sync --locked --all-extras`. Run all registered seeds and series:

```bash
for asset in bitstamp btcusdt ethusdt solusdt dogeusdt; do
  for seed in 42 43 44; do
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run python scripts/run_frontier_study.py \
      --data data/${asset}_daily.csv --seed "$seed" \
      --output results/frontier-repeat/${asset}-seed${seed}
  done
done
OPENBLAS_NUM_THREADS=1 uv run python scripts/summarize_frontier_study.py \
  results/frontier-repeat/*-seed* --output results/frontier-repeat/scorecard.json
```

The original run directories live under `results/frontier-20261022/`. Their
`summary.json` files contain complete fit parameters, residual pools, transformations,
selections, candidate metrics, source/data/protocol hashes and software versions.
`predictions.csv` contains every candidate forecast, date, label and score.
`verified-scorecard.json` checks source/data identity, cross-seed configurations,
probability validity, target alignment, and independently recomputes NLL/Brier/QLIKE.
This is loss replay, not a complete independent reconstruction of every feature.

All generated artifacts remain ignored as required by repository policy. The
following hashes identify the completed summaries; these are provenance, not a
substitute for obtaining the local artifacts or rerunning the commands.

| Run | Summary SHA-256 |
|---|---|
| bitstamp-seed42 | `6f6daad7ce3406fbe2b4e77675bb00f282165d6c63726a20cd17385dfc8efd5f` |
| bitstamp-seed43 | `82fa34904c40c64de71d4adac93203bafb3753bb7546f87e190342ba81d7677d` |
| bitstamp-seed44 | `f872467b8f31d753ab8c99af48fbe9ca92858f70a90a431da02f643c002af41d` |
| btc-seed42 | `0682e40d285620bf85d85b6c2288209939e2a80ae5310e5bc2002918f86f09b8` |
| btc-seed43 | `47504538182e3e0bb8c1e3f6fe32235fcb8108a20ab7b02b86d2ab840cc52570` |
| btc-seed44 | `149cdca147eaf0910ef325f0c00768f5807a55ac1e7b7d0218cc85723fd953a2` |
| doge-seed42 | `16aa98a4367eea70a77574933d4049dae60108f6fee4874dd4bccfc891ee2832` |
| doge-seed43 | `758c73f8682860cc47109417a33b628745578b5126b8131dc99c205acfaebd98` |
| doge-seed44 | `007cb9d41fded0358dd9e405e376beea53d237ea15c7754576f1ef98a5b60105` |
| eth-seed42 | `1c90e0ae4a69fdf2f440f4cf39f8ec49e8923179af7c4a1cfd32b9743c1850fc` |
| eth-seed43 | `d871d901f6b973a45c46e1e0e360c560dfe1968f201d010be0132ce268e5b9c9` |
| eth-seed44 | `37477290a7c50af42ae6764ef8fe269e71168cd3dacf07497799b2653e72828f` |
| sol-seed42 | `577081df1cfd0bf4de692ec9579cebe47d98ded4e520a643a5fb26ed8d9737aa` |
| sol-seed43 | `4600bcf5d8fc0ad40330d8eaa947fa35537baa0a6904b05f9e78906da07faa43` |
| sol-seed44 | `ac9efebcc1dc46ef8bb8c1ef448f8432d1acd08e4b3279a595b7a4f196d92d48` |

## Decision

Do not promote these candidates to a superiority claim or retune the scored 2024
period. Continue with the fairness and continuous-target work packages in the
[agent-ready research plan](frontier-research-plan.md). The accompanying
[manuscript](../paper/frontier.typ) includes these measured negative/mixed outcomes.
Independent confirmation and publication readiness remain open.
