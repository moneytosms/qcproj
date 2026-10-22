# Frontier literature and research decisions

Accessed 2026-10-22. Primary sources only. This is a bounded research review,
not an exhaustive systematic review or independent replication. Published
findings below motivate tests; they do not establish an advantage on this repo.
The companion [execution plan](frontier-research-plan.md) specifies those tests.

## What changes the next experiment

1. **Quantum memory is a defensible new hypothesis.** Li, Mukhopadhyay, Bayat
   and Habibnia, *Quantum reservoir computing for realized volatility forecasting*,
   Physical Review Research 8, 023028, published 2026-04-08
   ([journal](https://doi.org/10.1103/rbj7-4wnq),
   [full text, arXiv v2](https://arxiv.org/html/2505.13933v2)). The paper uses a
   fixed transverse-field Ising reservoir with input replacement and retained
   hidden quantum states, then trains a readout. Its empirical setting is 815
   monthly S&P 500 observations, 1950–2017, with economic predictors and rolling
   re-estimation. The authors report improvements against their controls.
   This differs materially from next-day crypto variance from five-minute bars.
   Reproduce the state-update mechanism in a small simulator, with ESN, nonlinear
   autoregression and equal-history controls. Do not transfer its score claims
   or mistake log monthly volatility for daily realized variance. Check feature
   selection and macroeconomic release vintages before reproducing the full paper.

2. **Recent finance evidence is mixed, not a mandate to increase qubits.**
   Ahmad et al., *Quantum vs. Classical Machine Learning: A Benchmark Study for
   Financial Prediction*, preprint submitted 2026-01-07
   ([version 1](https://arxiv.org/html/2601.03802v1)). It compares quantum and
   classical models across returns, trading simulations and volatility; quantum
   SVR results depend on asset and encoding. Its prose contains differing
   descriptions of which kernel leads QLIKE, so reproduce table definitions,
   target units, splits and tuning before using its rankings. It is useful as a
   source of candidate kernels, not confirmation for this project. A preprint and
   a favorable market-specific result do not justify broad quantum-superiority
   language.

3. **Strong classical forecasting controls are mandatory.** Jones et al.,
   *Benchmarking Quantum Models for Time-series Forecasting*, IEEE QCE 2024,
   posted 2024-12-18 ([paper](https://arxiv.org/abs/2412.13878),
   [proceedings](https://doi.org/10.1109/QCE60285.2024.10246)). Their real-data
   comparison with hyperparameter optimization finds the best classical methods
   ahead overall; beating ARIMA on an individual task is a weaker result.
   For this project, comparing only tiny softmax/network controls leaves the
   main forecasting question unanswered.

4. **Entanglement needs its own control.** Bowles, Ahmed and Schuld,
   *Better than classical? The subtle art of benchmarking quantum machine
   learning models*, 2024
   ([paper v2](https://arxiv.org/abs/2403.07059v2)). Across their small
   classification benchmark, ordinary classical methods generally lead and
   removing entanglement often preserves or improves performance. This is not
   a theorem against quantum forecasting. It motivates an otherwise identical
   no-entangler ablation, including the same learned readout; comparing a
   factorized Born distribution with a flexible entangled readout confounds
   two changes.

5. **Encoding, rather than the quantum label, defines an important function
   class.** Schuld, Sweke and Meyer, *The effect of data encoding on the
   expressive power of variational quantum machine learning models*, Physical
   Review A 103, 032430 (2021)
   ([paper](https://arxiv.org/abs/2008.08605),
   [journal](https://doi.org/10.1103/PhysRevA.103.032430)). Quantum expectation
   functions admit Fourier representations whose frequencies depend on
   encoding. This motivates matched trigonometric controls. With trainable
   affine angle weights, frequencies themselves move; fixed random sine
   features are useful controls but are not an exact matched model.
   The repo's two-qubit circuit also has an exact classical matrix simulator.
   Numerical identity to that simulator is a correctness test, never evidence
   of a quantum computational advantage.

6. **Re-uploading is established prior art.** Pérez-Salinas et al., *Data
   re-uploading for a universal quantum classifier*, Quantum 4, 226 (2020)
   ([published paper](https://quantum-journal.org/papers/q-2020-02-06-226/)).
   Repeated encoding supports expressive low-qubit models. Universality is an
   approximation statement, not a finite-sample forecasting guarantee. A new
   paper here must contribute an evaluation, mechanism or domain result beyond
   re-uploading itself.

7. **Kernel diagnostics can reject bad expensive bets.** Huang et al.,
   *Power of data in quantum machine learning*, Nature Communications 12, 2631
   (2021) ([authors' paper](https://arxiv.org/abs/2011.01938)). Data can make
   classical learning competitive even for functions hard to compute without
   examples. Projected representations and geometric diagnostics help frame
   comparisons, but a favorable geometric difference is not sufficient evidence
   for predictive advantage on observed labels. Start with small projected
   features and classical RBF/polynomial/Fourier controls; tune geometry only on
   development observations.

8. **More expressive kernels can become uninformative.** Thanasilp et al.,
   *Exponential concentration in quantum kernel methods*, Nature Communications
   15, 5200 (2024)
   ([published paper](https://www.nature.com/articles/s41467-024-49287-w),
   [preprint](https://arxiv.org/abs/2208.11060)). Under identified conditions,
   expressivity, global measurement, entanglement and noise can concentrate
   kernels, requiring excessive measurements to distinguish inputs. Measure
   off-diagonal variance, effective rank and shot uncertainty before a large
   kernel search. A simulated exact kernel omits that measurement cost.

9. **Classical memory can be both cheap and expressive.** Gauthier, Bollt,
   Griffith and Barbosa, *Next generation reservoir computing*, Nature
   Communications 12, 5564 (2021)
   ([paper](https://www.nature.com/articles/s41467-021-25801-2),
   [preprint](https://arxiv.org/abs/2106.07688)). Their nonlinear vector
   autoregression performs strongly on dynamical-system benchmarks with modest
   training cost. Those tasks differ from noisy financial forecasting. A
   ridge-regularized delay polynomial model is nevertheless a necessary simple
   control for any quantum-memory claim here.

## Information, target and inference foundations

| Source | Supported result | Decision for this project |
| --- | --- | --- |
| Patton and Sheppard (2015), [Good Volatility, Bad Volatility](https://public.econ.duke.edu/~ap172/Patton_Sheppard_REStat_2015.pdf) | Positive and negative realized variation carry different predictive information in their equity study. | Add lagged downside share to every family before making circuits deeper. Crypto benefit remains a hypothesis. |
| Bollerslev, Patton and Quaedvlieg (2016), [Exploiting the Errors](https://public.econ.duke.edu/~ap172/BPQ_Exploiting_Errors_JoE_2016.pdf) | HARQ uses estimated measurement error to modify persistence; results depend on reliable quarticity information. | Include native HARQ plus a separately named quarticity-enriched feature experiment. Do not equate any log-RQ regressor with canonical HARQ. |
| Patton (2011), [Volatility forecast comparison using imperfect volatility proxies](https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf) | Some losses preserve forecast rankings under specified assumptions on noisy variance proxies. | Use positive variance forecasts and QLIKE; audit those assumptions instead of claiming automatic robustness to exchange gaps. |
| Gneiting and Raftery (2007), [Strictly Proper Scoring Rules, Prediction, and Estimation](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf) | Proper scores evaluate distributions; different scores emphasize different aspects. | Keep categorical NLL as a fixed endpoint; use separate CRPS/interval experiments for continuous distributions. A score change is a new hypothesis. |
| Gibbs and Candès (2024), [Conformal Inference for Online Prediction with Arbitrary Distribution Shifts](https://www.jmlr.org/papers/volume25/22-1218/22-1218.pdf) | Adaptive online prediction sets have coverage/regret properties under the paper's conditions. | Give quantum and classical forecasts the same causal wrapper. Coverage does not establish conditional coverage, narrow intervals or better underlying NLL. |
| White (2000), [A Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152) | Repeated model searches affect forecast-comparison inference. | Log every candidate; a fresh endpoint is still needed after unrecorded historical exploration. |
| Hansen, Lunde and Nason (2011), [The Model Confidence Set](https://doi.org/10.3982/ECTA5771) | Data may identify a set of competitive models without identifying a unique winner. | Report model uncertainty; retain ties and negative results. A model remaining in the set does not prove superiority. |

## Claim boundaries

The promising question is whether a particular circuit or recurrent quantum-state
parameterization supplies a useful, economical forecasting bias after strong
controls. The existing two-qubit simulation cannot establish computational
speedup. Quantum hardware usefulness additionally requires end-to-end measured
resource accounting and a scaling argument against the best classical methods.

Do not describe richer intraday inputs, HAR corrections, calibration, probability
averaging, or repeated encoding as new quantum mechanisms. Test them on all
families. Do not infer a long-lived memory advantage from a feed-forward circuit
that receives hand-built HAR averages. Existing research already establishes
the relevance of these controls; the proposed experiment must establish its own
market-specific effect.

Not checked: author-code reproduction, all supplementary materials, exhaustive
2026 literature, or hardware experiments. No source establishes this repo's
desired 5% transferable improvement.
