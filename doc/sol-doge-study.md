# SOL and DOGE quantum replication results

This report completes the preregistered two-market replication in
[sol-doge-replication-protocol.md](sol-doge-replication-protocol.md). The protocol fixed
the depth-1 quantum candidate, comparators, 20 seeds, 5 restarts, calibration, 97.5%
paired block intervals, and success rule before test evaluation.

## Result

The marked-improvement rule failed on both assets. The quantum hybrid did not achieve
at least 5% lower calibrated log loss than every classical comparator, and its paired
intervals were not all below zero. This replication does not establish quantum advantage.
Tests were evaluated once after sealing.

## Data and execution

| Asset | Daily coverage | 5-minute bars | Missing bars | Incomplete days | Train / validation / test |
|---|---|---:|---:|---:|---|
| SOL | 2020-08-11–2026-10-19 | 650,813 | 283 across 10 gaps | 11 (none in test) | 843 / 731 / 657 |
| DOGE | 2019-07-05–2026-10-19 | 766,478 | 610 across 18 gaps | 19 (none in test) | 1246 / 731 / 657 |

Observed archive gaps were preserved, not filled. Each market used the common test
period 2025-01-01 through 2026-10-19 (657 targets), with 20 final seeds and five
restarts. Temperatures were fitted on validation predictions for each seed and model.
SOL had 19/20 eligible softmax-HAR hybrid fits (seed 18 ineligible); DOGE had 17/20
(seeds 1, 17, and 19 ineligible). All quantum fits and other classical fits were
eligible. Ineligible records remain included.

Both panels were sealed before test evaluation. Seals contain the data and metadata
hashes, config, selection, all trained model files, preregistration, Python sources,
and locked environment. Evaluation creates a one-use marker to prevent reruns.

## SOL results

Scores are mean ± across-seed standard deviation; lower is better. For each metric, raw precedes calibrated.

| Model | Log loss raw / calibrated | Normalized RPS raw / calibrated | Extreme Brier raw / calibrated | QLIKE raw / calibrated |
|---|---:|---:|---:|---:|
| Quantum RY hybrid | 0.400439 ± 0.003196 / 0.404973 ± 0.002617 | 0.042514 ± 0.000202 / 0.042881 ± 0.000164 | 0.003224 ± 0.000131 / 0.003280 ± 0.000097 | 0.332512 ± 0.006703 / 0.349904 ± 0.001971 |
| Weekend softmax | 0.425781 ± 0.000000 / 0.424834 ± 0.000000 | 0.044178 ± 0.000000 / 0.044760 ± 0.000000 | 0.004654 ± 0.000000 / 0.004549 ± 0.000000 | 0.319065 ± 0.000000 / 0.331813 ± 0.000000 |
| Weekend network | 0.416529 ± 0.000001 / 0.417410 ± 0.000001 | 0.044609 ± 0.000000 / 0.044747 ± 0.000000 | 0.005212 ± 0.000000 / 0.005175 ± 0.000000 | 0.331374 ± 0.000001 / 0.336041 ± 0.000001 |
| Softmax-HAR hybrid | 0.420787 ± 0.005164 / 0.424215 ± 0.005362 | 0.044604 ± 0.000769 / 0.045002 ± 0.000756 | 0.003564 ± 0.000858 / 0.003592 ± 0.000865 | 0.347528 ± 0.016245 / 0.359629 ± 0.019821 |

Quantum minus classical paired calibrated log-loss intervals (7- and 30-day blocks; 97.5%):

| Classical comparator | Mean difference | 7-day interval | 30-day interval | Quantum improvement vs comparator |
|---|---:|---:|---:|---:|
| Weekend softmax | -0.019861 | [-0.047460, 0.002243] | [-0.044417, 0.002246] | 4.68% |
| Weekend network | -0.012437 | [-0.039983, 0.010575] | [-0.039091, 0.009329] | 2.98% |
| Softmax-HAR hybrid | -0.019242 | [-0.032941, -0.005954] | [-0.033547, -0.006856] | 4.54% |

Marked improvement: **no**.

## DOGE results

Scores are mean ± across-seed standard deviation; lower is better. For each metric, raw precedes calibrated.

| Model | Log loss raw / calibrated | Normalized RPS raw / calibrated | Extreme Brier raw / calibrated | QLIKE raw / calibrated |
|---|---:|---:|---:|---:|
| Quantum RY hybrid | 0.760504 ± 0.002528 / 0.762719 ± 0.002650 | 0.084816 ± 0.000326 / 0.084965 ± 0.000303 | 0.004217 ± 0.000070 / 0.004205 ± 0.000071 | 0.543112 ± 0.003950 / 0.556192 ± 0.005905 |
| Weekend softmax | 0.763115 ± 0.000000 / 0.763335 ± 0.000000 | 0.085115 ± 0.000000 / 0.085206 ± 0.000000 | 0.004149 ± 0.000000 / 0.004147 ± 0.000000 | 0.565918 ± 0.000001 / 0.561258 ± 0.000000 |
| Weekend network | 0.772817 ± 0.000001 / 0.772791 ± 0.000001 | 0.085796 ± 0.000000 / 0.085792 ± 0.000000 | 0.003550 ± 0.000000 / 0.003547 ± 0.000000 | 0.550468 ± 0.000001 / 0.550225 ± 0.000001 |
| Softmax-HAR hybrid | 0.766942 ± 0.009507 / 0.766459 ± 0.009579 | 0.085402 ± 0.001106 / 0.085340 ± 0.001121 | 0.004170 ± 0.000189 / 0.004173 ± 0.000192 | 0.576970 ± 0.023258 / 0.576213 ± 0.023354 |

Quantum minus classical paired calibrated log-loss intervals (7- and 30-day blocks; 97.5%):

| Classical comparator | Mean difference | 7-day interval | 30-day interval | Quantum improvement vs comparator |
|---|---:|---:|---:|---:|
| Weekend softmax | -0.000616 | [-0.021268, 0.020098] | [-0.019665, 0.016932] | 0.08% |
| Weekend network | -0.010072 | [-0.034608, 0.014993] | [-0.032367, 0.010388] | 1.30% |
| Softmax-HAR hybrid | -0.003740 | [-0.018697, 0.010904] | [-0.017421, 0.010569] | 0.49% |

Marked improvement: **no**.
