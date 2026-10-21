// Layout follows the single-column NeurIPS-2017 style used by "Attention Is All You Need".
#set document(title: "Quantum Volatility Range Forecasting: Memory Helps, Quantum Advantage Does Not Appear")
#set page(paper: "us-letter", margin: (x: 1.5in, top: 1in, bottom: 1in), numbering: "1", number-align: center)
#set text(font: ("TeX Gyre Termes", "Liberation Serif"), size: 10pt, lang: "en")
#set par(justify: true, leading: 0.55em, spacing: 1em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => block(above: 1.6em, below: 0.9em, text(size: 12pt, weight: "bold", it))
#show heading.where(level: 2): it => block(above: 1.3em, below: 0.7em, text(size: 10pt, weight: "bold", it))
#show figure.caption: it => text(size: 9pt, it)
#show figure: set block(above: 1.4em, below: 1.4em)
#show link: set text(fill: rgb("#1a3fa0"))
#set math.equation(numbering: "(1)")
#show table: set text(size: 9pt)
#set table(stroke: none, inset: (x: 6pt, y: 3pt))
#let rule3 = line(length: 100%, stroke: 0.6pt)

// Title block
#block(width: 100%)[
  #line(length: 100%, stroke: 2pt)
  #v(0.4em)
  #align(center, text(size: 17pt, weight: "bold")[Quantum Volatility Range Forecasting:\ Memory Helps, Quantum Advantage Does Not Appear])
  #v(0.4em)
  #line(length: 100%, stroke: 2pt)
  #v(1.2em)
  #align(center)[
    #text(weight: "bold")[Nidhi Rakesh #h(1.2em) Srimoneyshankar Ajith #h(1.2em) Bharadwaj B Chand] \
    #text(weight: "bold")[Vishnunath A Suresh #h(1.2em) Gopi Krish] \
    #v(0.3em)
    Team Schrödinger's Cat, Department of Computer Science and Engineering \
    Indian Institute of Information Technology Kottayam \
    #raw("github.com/moneytosms/qcproj")
  ]
  #v(1.6em)
]

#align(center, text(weight: "bold", size: 12pt)[Abstract])
#pad(x: 0.5in, top: 0.3em)[
  Quantum circuit learning has been proposed for volatility modelling, but published results use one qubit, one day of history, a single point forecast, and no same-input classical baseline. We rebuild the one-qubit Bitcoin model of Takaishi @takaishi2026 and extend it in three ways: multi-horizon memory, a four-level probability forecast read from two qubits, and a realism-aware training term. Every quantum model is paired with classical models given identical inputs, trained with time-ordered splits, and judged on sealed test data under pass/fail rules written beforehand. On fresh Bitcoin data our two-qubit model reduces test log loss from 1.196 to 0.5695 relative to the original circuit, and weekly and monthly memory contributes a paired improvement of 0.051 (95% interval −0.071 to −0.030). A classical softmax model with the same inputs nevertheless scores 0.5184, and across ten cryptocurrencies no pre-registered group passes a 5% advantage rule. Realism training worsens forecasts. We therefore report a clear improvement over the prior quantum model and no quantum advantage over a matched classical one. All circuits are exact classical simulations.
]

= Introduction

Volatility, the size of price swings, clusters in time: calm days follow calm days and wild days follow wild ones. This memory is the basis of the Heterogeneous Autoregressive (HAR) model of realized volatility @corsi2009, which predicts tomorrow from the average of the last day, week and month and remains a strong benchmark. Quantum circuit learning @mitarai2018 trains a parameterised circuit like a small neural network, and Takaishi @takaishi2025 @takaishi2026 applied a single-qubit circuit to realized volatility of Bitcoin, checking that generated series reproduce multifractal structure @kantelhardt2002.

That model has four limits that motivate this work. It sees only the previous day, so it cannot use the weekly and monthly structure that HAR exploits. It emits one number, so it says nothing about how likely a calm or extreme day is. It is trained for one-step accuracy but judged on long generated histories. And it is fitted and judged on the same data. Meanwhile the quantum machine-learning literature warns that small variational models are frequently matched by classical surrogates @schreiber2023 and that benchmarks must control for inputs and capacity @bowles2024.

Our contributions are:
- a verified reproduction of the one-qubit model, including the finding that its angle $phi$ has no effect on the output;
- a two-qubit re-uploading circuit with multi-horizon inputs that outputs a distribution over four volatility levels;
- a benchmark design with classical twins, 20 seeds, block-bootstrap intervals, sealed results and pass/fail rules fixed before testing;
- a negative-result study on fresh Bitcoin data and nine further coins, reporting no quantum advantage.

= Background

*Realized volatility.* For day $t$ with intraday log returns $r_(t,i)$, $"RV"_t = sum_(i=1)^n r_(t,i)^2$. We model $log "RV"_t$.

*Quantum circuit learning.* A circuit $U(bold(x); bold(theta))$ acts on $|0 chevron.r^(times.o n)$. Data enter as rotation angles; $bold(theta)$ are trained by a classical optimiser. Repeating the data-encoding gates between trainable blocks, _re-uploading_ @perezsalinas2020, enlarges the family of functions the circuit can express @schuld2021. The outcome probabilities follow the Born rule,
$ p_k = |chevron.l k | psi(bold(x); bold(theta)) chevron.r|^2, quad k in {00, 01, 10, 11}. $ <born>

*Scoring.* Probabilistic forecasts are scored by log loss, a strictly proper rule @gneiting2007,
$ "LL" = -1/N sum_(t=1)^N log p_(t, y_t), $ <ll>
where $y_t$ is the realized level. Volatility point forecasts are compared with QLIKE, which is robust to noise in the volatility proxy @patton2011.

= Model

#figure(
  image("../report/fig/pipeline.png", width: 100%),
  caption: [From prices to a scored forecast. Features and bin edges use training data only.],
) <fig-pipeline>

*Inputs.* Per day we use yesterday's $log "RV"$, its 7-day and 30-day means, and yesterday's return, standardised with training statistics. The first 30 days are dropped.

*Targets.* Training percentiles at 30%, 70% and 95% of $log "RV"$ split days into four levels (calm, normal, wild, extreme), one per two-qubit basis state.

#figure(
  image("../report/fig/circuit.png", width: 100%),
  caption: [One layer: trainable data scaling (blue), $R_Y$/$R_Z$ rotations (green), CNOT. Layers repeat $L$ times; $L = 3$ gives 24 parameters.],
) <fig-circuit>

*Circuit.* Qubit 0 receives yesterday and the weekly mean, qubit 1 the monthly mean and the return, each multiplied by a trainable weight (@fig-circuit). Probabilities come from @born. Later versions (v2, v3) add a classical HAR term to the output and use more restarts; the multi-coin variant uses only $R_Y$ gates plus a HAR term and one temperature parameter.

*Realism-aware training (A).* The plain forecast objective (D) is log loss. A adds a penalty on the distance between statistics of recursively generated paths and real paths, including autocorrelation at 1, 7 and 30 days.

*Classical twins.* Each quantum model has classical counterparts with the same inputs and four-level output: softmax regression, a 24-parameter network, HAR quantile regression, a HAR empirical-residual model and calibrated GARCH(1,1) @bollerslev1986.

= Experimental Protocol

*Data.* (i) The paper's Bitcoin series, 913 days, split 529/177/177. (ii) Fresh Bitstamp Bitcoin, December 2016 to 19 October 2026: 2,192 training, 731 validation and 657 test days. (iii) Ten Binance coins at 5-minute resolution, with the same 657-day test period from 2025-01-01.

*Fairness controls.* Splits are chronological; the test block is opened once. Each model is trained from 20 seeds. Paired differences use circular block bootstrap with 7- and 30-day blocks and 2,000 replicates, so intervals reflect serial dependence. Trained models are hashed before test scoring. For the multi-coin studies the rule was fixed in advance: quantum must beat the best classical model by at least 5% in log loss, with an interval excluding zero, for every coin in a group.

*Implementation.* NumPy statevector simulator, L-BFGS-B and COBYLA from SciPy, 109 automated tests. Everything runs on CPU. No quantum hardware was used and no noise was modelled.

= Results

== Reproducing the one-qubit model

On the paper's data we recover $theta = -4.557$, $phi = 0.360$, $lambda = 1.700$, training MSE 0.00205 and forecast correlation 0.449. The closed form $P(0) = 1/2 + 1/2 bold(n) dot bold(b)$ matches the simulator to $5.6 times 10^(-16)$. The angle $phi$ leaves the output unchanged and the model uses a single day of history.

== Twenty seeds on the paper's data

#figure(
  image("fig/paperdata.svg", width: 85%),
  caption: [Frozen 20-seed study on the paper's data. Classical models win; realism training hurts the quantum model.],
) <fig-paperdata>

HAR quantile regression has the lowest test log loss (0.5289). The quantum range model scores 0.6920 and adding realism training worsens it to 0.8623, with moment distance rising from 19.7 to 31.9 (@fig-paperdata). The paired interval for the A − D difference excludes zero (@fig-contrasts).

== Fresh Bitcoin data

#figure(
  image("fig/fresh.svg", width: 90%),
  caption: [Test log loss on 657 fresh Bitcoin days, mean of 20 seeds. Each quantum version improves on the last; a matched softmax still wins.],
) <fig-fresh>

#figure(
  table(
    columns: (auto, 1fr, 1fr), align: (left, right, right), stroke: (x: none, y: none),
    table.hline(stroke: 0.8pt),
    [*Measure (lower is better)*], [*Original paper*], [*Our quantum model*],
    table.hline(stroke: 0.4pt),
    [Log loss], [1.196], [*0.5695*],
    [QLIKE], [0.840], [*0.504*],
    [Realism distance], [215.3], [*33.5*],
    table.hline(stroke: 0.8pt),
  ),
  caption: [Original one-qubit circuit against our two-qubit model, fresh Bitcoin test.],
) <tab-paper>

Our model beats the original circuit on all three measures with intervals excluding zero (@tab-paper). This comparison was added after the main test results were seen. Weekly and monthly memory lowers log loss by 0.051 (@fig-contrasts), but the softmax twin with identical inputs scores 0.5184, 0.051 better than the quantum model. Circuit versions v2 and v3 reach 0.529 and 0.5145 against 0.4962 for the matching softmax (@fig-fresh); these were evaluated on a period already inspected, so they are indicative only.

#figure(
  image("fig/contrasts.svg", width: 95%),
  caption: [Paired differences in test log loss with 95% block-bootstrap intervals. Memory helps; realism hurts; the classical twin wins.],
) <fig-contrasts>

== Ten cryptocurrencies

#figure(
  image("fig/coins.svg", width: 85%),
  caption: [Quantum gain over the best classical model per coin, test log loss. Only AVAX exceeds the 5% target, and its group fails jointly.],
) <fig-coins>

Gains range from −6.89% (BNB) to +5.68% (AVAX) (@fig-coins). No group of coins passed the rule fixed in advance. AVAX alone exceeds 5%, but LINK, DOT and AVAX fail together and the quantum model is worse on QLIKE for all three.

= Discussion

The large gain over the published circuit comes from inputs and outputs: memory and a probability forecast. Classical models given the same information match or exceed the circuit, consistent with the surrogate argument of @schreiber2023. Realism training, which targets path statistics rather than one-step accuracy, degraded log loss in our tests; the objectives pull apart.

*Limitations.* All circuits are noiseless simulations. v2, v3 and later panels reuse the 2025--2026 test days, so they are exploratory. Twenty seeds measure optimiser variability, not twenty markets. Training used fixed budgets and does not prove the best optimum was found. The paper's data are pre-scaled and the fresh test period contains no extreme days. Formal Diebold–Mariano tests @diebold1995 are not yet run.

= Conclusion

A two-qubit, memory-aware, four-level quantum forecaster is a clear improvement on the one-qubit published model, yet we find no evidence of quantum advantage over classical models with identical inputs. We release code, protocols and result notes @repo. Natural next steps are a clean out-of-sample test of the best $R_Y$ configuration, hardware runs with noise, and quantum reservoir or Born-machine alternatives.

#bibliography("refs.bib", title: "References", style: "ieee")
