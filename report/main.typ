#import "@preview/charged-ieee:0.1.4": ieee
#import "metadata.typ": *
#import "diagrams.typ": *

// Retain charged-ieee typography, captions, mathematics and citation conventions.
// Replace its conference masthead with the university's separate title page.
#show place: it => if it.clearance != 30pt { it }
#show: ieee.with(title: project-title, authors: (), abstract: none, paper-size:"a4")
#set document(title:project-title,author:students.map(s=>s.at(0)),keywords:("IEG 313","quantum circuits","volatility","QVRF-TWS-1.0"))
#set page(columns:1,margin:(x:19mm,top:19mm,bottom:19mm),numbering:"1",number-align:center,
  header:context if counter(page).get().first()>1 {
    text(8pt,fill:rgb("657586"))[Schrödinger’s Cat #h(1fr) IEG 313 · Project Report]
  })
#set text(size:10pt)
#set par(justify:true,first-line-indent:0pt,leading:.5em,spacing:.55em)
#set heading(numbering:"1.1")
#set figure(supplement:[Figure],numbering:"1")
#show figure.where(kind:table): set text(size:9pt)
#show figure.caption: set text(size:9pt)
#show bibliography: set text(size:9pt)
#show raw: set text(font:"DejaVu Sans Mono",size:8.5pt)
#show heading: it => {
  set text(fill:ink)
  if it.body == [Title page] {
    block(height:0pt,hide(it.body))
  } else if it.level==1 {
    block(above:13pt,below:9pt,sticky:true)[#text(11pt,weight:"bold")[#counter(heading).display("1")#h(6pt)#it.body]]
  } else {
    block(above:9pt,below:5pt,sticky:true)[#text(10pt,weight:"bold")[#if it.numbering != none { counter(heading).display("1.1"); h(5pt) }#it.body]]
  }
}
#let wide(body,caption,label) = [#figure(body,caption:caption,kind:image,placement:top,scope:"parent")#label]
#let tab(body,caption,label) = [#figure(body,caption:caption,kind:table,supplement:[Table])#label]
#let results = json("../doc/fresh-study-results/results.json")
#let model-name(n) = n.replace("quantum-","Q-").replace("softmax-","SM-").replace("network-","NN-")

= Title page
#align(center)[
  #v(6mm)
  #image("assets/iiitk-logo.jpg",height:34mm,alt:"Official Indian Institute of Information Technology Kottayam logo")
  #v(7mm)
  #text(15pt,weight:"bold")[#institution]
  #v(4mm)
  #department
  #v(13mm)
  #text(23pt,weight:"bold",fill:blue)[#project-title]
  #v(4mm)
  #text(13pt)[IEG 313 · University Project Report]
  #v(8mm)
  #text(14pt,weight:"bold")[#group-name]
  #v(6mm)
  #table(columns:(1fr,auto),align:(left,right),stroke:none,inset:(x:8pt,y:5pt),
    table.header([*Student name*],[*Register number*]),
    ..students.flatten().map(s=>[#s]),
  )
  #v(10mm)
  *Instructors*\ #instructors
  #v(7mm)
  *Academic year:* #academic-year
  #v(3mm)
  20 October 2026
]
#pagebreak()

= Abstract
This project implemented and evaluated the Quantum Volatility Range Forecaster using exact classical simulation of one- and two-qubit circuits. It extended a published single-qubit volatility model with multi-horizon memory, four ordered regime probabilities, and realism-aware training. The implementation also included classical baselines, chronological evaluation, recursive generation, and sealed experiment artifacts.

The principal study used Bitstamp Bitcoin realized variance from five-minute returns. Training ended in 2022, validation covered 2023–2024, and testing covered 657 days from January 2025 to October 2026. Circuit depth and realism weights were selected on validation data. Final evaluation used 20 training seeds and paired date-block bootstrap intervals.

Adding weekly and monthly inputs reduced quantum test negative log likelihood from 0.6204 to 0.5695 nats per day. The 30-day block interval for the difference was [−0.0711, −0.0306]. Realism training reduced the mean generated-path moment distance from 33.50 to 29.00, while increasing forecast loss to 0.6042. Same-input softmax regression achieved 0.5184, ahead of the quantum models.

Later calendar-aware Bitcoin variants reduced quantum loss to 0.5145, but these comparisons used an already-examined test period. Weekend-aware ETH, BTC, SOL, and DOGE studies did not satisfy their registered marked-improvement rules. A later calibrated v3 panel reported 5.68% lower NLL on AVAX than its best classical comparator. Its three-asset transfer gate failed, and quantum QLIKE was worse on all three assets. The results support a memory benefit, a forecast–realism trade-off, and a limited exploratory AVAX primary-metric signal. They establish neither quantum advantage nor calibrated numerical prediction intervals. The Bitstamp test period contained no training-defined extreme-regime days, which limits tail-risk conclusions.

#v(4mm)
*Keywords:* quantum circuit learning; realized variance; probabilistic regime classification; heterogeneous autoregressive inputs; reproducibility.

#pagebreak()
= Contents
#outline(title:none,depth:1,indent:0pt)
#v(4mm)
#heading(level:2,numbering:none)[List of figures]
#context {
  let titles = ([Implemented fresh-study architecture], [Paper-model circuit], [Two-qubit Born layer], [Recursive generation], [Experiment stage order], [Observed Bitstamp data and splits], [Fresh-study forecast scores], [Paired date-block intervals], [Forecast–realism trade-off], [Generated-path autocorrelation])
  for (i,f) in query(figure.where(kind:image)).enumerate() {
    block(above:4pt,below:4pt,link(f.location(),grid(columns:(14mm,1fr,auto),[Fig. #numbering("1", ..f.counter.at(f.location()))],titles.at(i),str(counter(page).at(f.location()).first()))))
  }
}
#v(4mm)
#heading(level:2,numbering:none)[List of tables]
#context {
  let titles = ([Comparison families], [Implemented modifications], [Regime definitions], [Chronological target splits], [Selected forecast scorecard], [Paper-model comparison], [Post-hoc Bitcoin variants], [Asset replications], [Cross-market v3 panels], [Team contributions], [Evidence index], [Complete forecast scorecard], [Scientific and writing review])
  for (i,f) in query(figure.where(kind:table)).enumerate() {
    block(above:4pt,below:4pt,link(f.location(),grid(columns:(19mm,1fr,auto),[Table #numbering("I", ..f.counter.at(f.location()))],titles.at(i),str(counter(page).at(f.location()).first()))))
  }
}
#pagebreak()
#heading(level:2,numbering:none)[Abbreviations and notation]
#table(columns:(auto,1fr),stroke:none,inset:4pt,
  [ACF],[Autocorrelation function.],
  [BTC / ETH],[Bitcoin / Ethereum; SOL and DOGE denote Solana and Dogecoin.],
  [Other assets],[LTC: Litecoin; BNB: Binance Coin; ADA: Cardano; LINK: Chainlink; DOT: Polkadot; AVAX: Avalanche.],
  [COBYLA],[Constrained optimization by linear approximation.],
  [CNOT],[Controlled-NOT quantum gate.],
  [HAR],[Heterogeneous autoregressive; this project uses 1-, 7-, and 30-day horizons.],
  [L-BFGS-B],[Limited-memory Broyden–Fletcher–Goldfarb–Shanno optimization with bounds.],
  [MFDFA],[Multifractal detrended fluctuation analysis.],
  [NLL],[Negative log likelihood, reported as natural-log loss in nats per day.],
  [QLIKE],[Quasi-likelihood loss for a positive variance forecast.],
  [RPS],[Ranked probability score; normalized across three cut points here.],
  [RV],[Realized variance in the implementation; its square root is realized volatility.],
  [SD],[Sample standard deviation across training seeds, unless stated otherwise.],
  [UTC],[Coordinated Universal Time; daily aggregation uses UTC boundaries.],
  [$v_t, y_t, r_t$],[Daily realized variance, $y_t=ln(v_t)$, and daily log return.],
  [$x_d,x_w,x_m,x_r$],[Training-standardized daily, weekly, monthly log-RV and previous-return inputs.],
  [$p_(t,k), z_t$],[Probability of regime $k$ and observed regime label for day $t$.],
  [D / A / B],[Forecast-only distribution training / realism-aware training / memory extension.],
  [$λ, θ, L$],[Realism weight, trainable circuit parameters, and circuit depth.],
)

#pagebreak()
#set page(columns:2)
= Introduction
== Background and problem statement
Daily financial variance changes over time. A forecaster must use available history to estimate the next observation without learning from future values. This project studies that task through small parameterized quantum circuits and matched classical controls.

Takaishi’s work provided the starting one-qubit model @takaishi. The project retained its encoding-based approach and audited its reproduction. It then implemented conditional probabilities for four ordered volatility regimes. The output is a categorical probability vector. It is not, by itself, a numerical lower and upper prediction bound.

The central problem is whether longer memory and a generation-based training penalty improve this small-circuit forecasting framework. A second question is whether the quantum component provides a benefit against classical models with comparable information.

== Motivation and objectives
The project connected three measurable objectives to implemented experiments:

+ *Memory:* compare previous-day inputs with daily, weekly, and monthly log-variance inputs, using the same two-qubit circuit.
+ *Distribution:* predict four training-defined regimes and evaluate NLL and normalized RPS on later dates.
+ *Realism:* add a penalty on generated-path moments and measure its effect on forecast loss and path statistics.

A fourth objective was to test these choices against frequency, softmax, neural, HAR, and calibrated GARCH baselines. The repository also implemented calendar-aware variants and asset replications @repo.

== Scope and evidence boundaries
The principal empirical panel is the sealed fresh Bitstamp study. The original 913-day paper reproduction is descriptive and uses the full sample. Earlier short-input studies are development evidence. The later Bitcoin v2/v3 designs are post-hoc because their motivation used an exposed test period.

The report covers the integrated implementation at commit `0aeab94`. The literature proposals in `doc/next-approaches-literature.md` are not completed experiments. The implementation uses exact classical statevector simulation. It contains no deployed trading service, and the reported experiments do not include physical quantum-device runs.

= Literature review
== Existing approaches
Takaishi used one-qubit circuit learning for Bitcoin variance modeling and examined generated-series scaling properties @takaishi. The project’s reproduction audit found an exact classical expression for the measured probability and a redundant trainable phase @audit. These checks motivate explicit classical controls.

HAR models summarize activity at multiple horizons @corsi. The implementation adapts that principle to 1-, 7-, and 30-day log-variance inputs for continuously traded crypto markets. Its 7/30-day windows differ from conventional trading-week and trading-month choices.

GARCH specifies a conditional variance recurrence @garch. The repository includes a calibrated GARCH(1,1) comparator and maps its forecast into the shared regime task. HAR residual and quantile models provide additional finance baselines. They help distinguish an information benefit from a circuit-specific effect.

Proper scoring rules support evaluation of probability forecasts @scoring. The project uses NLL and an ordered RPS. MFDFA provides scaling diagnostics @mfdfa, but multifractal quantities are not part of the fresh study’s four-moment training penalty.

== Limitations and addressed gap
The paper baseline uses previous-day observations and produces one scaled variance value. Its original descriptive fit does not answer the project’s held-out regime-forecasting question. The project therefore adds chronological validation, probability scoring, recursive generation, and matched classical comparisons.

The scientific gap addressed here is an implementation-level evaluation of these extensions. This report does not claim that memory models, quantum probability models, or moment-based training are globally new. It also does not infer a unique quantum mechanism from an improvement over the paper baseline.

#tab(table(columns:(1fr,1fr),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
  table.header([*Approach*],[*Role in this project*]),
  [One-qubit paper model],[Reproduction and point-forecast reference.],
  [HAR residual / quantile],[Longer-memory finance comparators.],
  [Softmax / small network],[Same-input categorical controls.],
  [GARCH(1,1)],[Calibrated conditional-variance baseline.],
  [Two-qubit Born model],[Four-regime probability forecaster.],
),[Implemented comparison families and their experimental roles.],<tab-related>)
@tab-related establishes why the comparison includes both finance and small machine-learning models. A single weak baseline would not isolate the contribution of the circuit.

= Novelty
== What the project changed
The source model is Takaishi’s single-qubit implementation @takaishi. The project’s concrete modifications are summarized in @tab-novelty. These are contributions relative to that baseline, rather than claims of priority across all published work.

#tab(table(columns:(.7fr,1.3fr),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Extension*],[*Implemented modification*]),
 [B: memory],[Past-only daily, 7-day, and 30-day log-RV features; short-input ablations.],
 [D: distribution],[Two-qubit Born probabilities mapped to four ordered, train-fitted regimes.],
 [A: realism],[NLL plus a penalty on lag-1/7/30 ACF and log-RV increment spread.],
 [Audit],[Classical twin, inactive-phase checks, training diagnostics, and source/artifact seals.],
 [Follow-ups],[All-input calendar circuits, restart ensembles, weekend-aware HAR hybrids, and asset replications.],
),[Changes implemented relative to the single-qubit baseline.],<tab-novelty>)

== Attribution of observed effects
The matched fresh-study memory ablation holds the circuit form and nominal parameter count fixed. It replaces weekly and monthly inputs with repeated previous-day log-RV in the short control. That contrast supports a memory interpretation within this design.

The paper-to-project comparison changes several factors together: scaling, qubit count, output semantics, depth, and training loss. It cannot assign its entire improvement to entanglement or additional qubits. Realism training changes the objective and search procedure. Its effects must be assessed on both forecast and generation metrics.

= Methodology / system design
== Architecture and data flow
@fig-architecture maps the implemented fresh-study modules. Data preparation, probability models, optimization, generation, and metrics have separate responsibilities. The shared observation law lets quantum and classical models use the same bins and generation procedure.

#wide(architecture(),[Implemented fresh-study architecture. Arrows show data or artifact flow. The generation module serves realism training and later path evaluation; no test scores enter selection.],<fig-architecture>)

The repository keeps `qvol/` separate from `src/qcvol/`. The former preserves the paper reproduction. The latter implements the main research pipeline. `qcvol_v2`, `qcvol_v3`, and `qcvol_next` contain later designs. These packages are experiment alternatives rather than layers in a deployed application.

== Variance, features, and regime definitions
For intraday prices $P_(t,i)$, let $u_(t,i)=ln(P_(t,i)/P_(t,i-1))$. Daily realized variance is the sum of squared five-minute log returns. The principal forecasting target is its natural logarithm:

$ v_t = sum_i u_(t,i)^2, quad y_t = ln(v_t). $ <eq-rv>

Equation @eq-rv distinguishes variance from volatility. Returns use decimal log-return units. Variance has squared-return units. Log variance, correlations, normalized scores, and the standardized features are dimensionless.

For target day $t$, the raw input vector is

$ h_t = (y_(t-1), 1/7 sum_(j=1)^7 y_(t-j),
  1/30 sum_(j=1)^30 y_(t-j), r_(t-1))^T. $ <eq-har>

The mean and SD of each component are fitted on training rows. The resulting standardized vector is $x_t=(x_d,x_w,x_m,x_r)^T$. Equation @eq-har uses completed days only. The target day is never part of its input window.

Let $c_1,c_2,c_3$ be the 30th, 70th, and 95th percentiles of training log-RV. The indicator $bold(1){C}$ equals 1 when condition $C$ holds and 0 otherwise. Labels follow

$ z_t = sum_(j=1)^3 bold(1){y_t >= c_j}. $ <eq-label>

Equation @eq-label uses right-sided threshold insertion. Equality belongs to the higher regime. @tab-regimes gives the implemented mapping, including the extreme regime’s open upper bound.

#tab(table(columns:(auto,auto,1fr),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Basis*],[*Regime*],[*Log-RV condition*]),
 [`00`],[Calm],[$y_t<c_1$],
 [`01`],[Normal],[$c_1<=y_t<c_2$],
 [`10`],[Wild],[$c_2<=y_t<c_3$],
 [`11`],[Extreme],[$y_t>=c_3$],
),[Four ordered regimes, with thresholds fitted only on training data.],<tab-regimes>)

The model returns probabilities for these categories. Continuous quantiles and point forecasts require a separate observation model. Thresholds alone do not establish coverage of a numerical forecasting interval.

== Paper circuit and classical twin
The preserved paper encoder applies four rotations in time order, followed by $U_3$. @fig-paper shows that sequence. The variance input is scaled into $[0,1]$ for this baseline, and the return input lies in $[-1,1]$.

#wide(paper-circuit(),[One-qubit paper circuit as implemented. Here $a_r=arcsin(r)$, $b_r=arccos(r^2)$, $a_v=arcsin(2s-1)$, and $b_v=arccos(s^2)$ for scaled variance $s$. The reported output is the exact probability of state 0.],<fig-paper>)

For encoded Bloch vector $b=(b_x,b_y,b_z)$, the classical twin is

$ P_0 = 1/2 + 1/2 n^T b, \
 n = (-sin θ cos λ, sin θ sin λ, cos θ)^T. $ <eq-twin>

The measured probability in @eq-twin is independent of $φ$. Thus, the three nominal $U_3$ parameters contain only two effective output directions. Agreement between circuit and twin is an implementation check. It also prevents a claim that this baseline requires quantum execution.

== Two-qubit Born forecaster
@fig-born depicts one implemented layer. Each layer applies data-dependent rotations, trainable rotations, and CNOT with $q_0$ controlling $q_1$. The same observation is uploaded at every layer. The state starts at $|00〉$ once; intermediate layers are not measured or reset.

#wide(born-circuit(),[One layer of `BornCircuit` / `FastBorn`, with parameter indices local to that layer. Repeat the unitary layer $L$ times and measure only after the final CNOT. Basis order is $|q_0 q_1〉$ = 00, 01, 10, 11.],<fig-born>)

For final state $|ψ_θ (x_t)〉$, the output is

$ p_(t,k) = abs(〈k|ψ_θ (x_t)〉)^2,
 quad sum_(k=0)^3 p_(t,k)=1. $ <eq-born>

Equation @eq-born defines the Born probability readout used in the main study. Simulation evaluates these probabilities exactly. Categorical generation uses a classical pseudorandom stream.

The nominal parameter count is $8L$, or 24 at the selected depth $L=3$. Two final phase directions are inactive for computational-basis probabilities. Nominal parameter matching is therefore an incomplete capacity argument. The two-qubit state has four complex amplitudes and is inexpensive to simulate classically.

== Forecast and realism objectives
The forecast-only objective is mean NLL:

$ cal(L)_D (θ) = -1/N sum_(t=1)^N ln max(p_(t,z_t),10^(-12)). $ <eq-nll>

The implementation validates nonnegative normalized probabilities before scoring. The floor in @eq-nll prevents logarithms of zero; it is not a claim about calibration.

For a log-RV path $y$, define the moment vector

$ m(y) = (ρ_1 (y),ρ_7 (y),ρ_30 (y),
  "sd"(y_t-y_(t-1)))^T. $ <eq-moments>

In @eq-moments, $ρ_l$ is the sample correlation of observations separated by $l$ days. The final component measures increment dispersion. It is not an estimate of a Hurst exponent.

The project forms a reference mean $μ_j$ and scale $s_j$ from training windows of the same length as the simulated paths. Each scale is floored at 0.02. The mismatch and realism objective are

$ D(m,μ) = sum_(j=1)^4 ((m_j-μ_j)/s_j)^2, $ <eq-distance>
$ cal(L)_A (θ) = cal(L)_D (θ) + λ D(m,μ). $ <eq-realism>

The forecast term can include a model-specific ridge penalty during fitting. Equation @eq-realism describes the substantive realism addition. Common random numbers reduce variation between objective evaluations. Matching the window lengths addresses the earlier bias from comparing short simulated paths with full-series ACF targets.

== Recursive generation
@fig-generation shows the implemented categorical and empirical-pool observation law. After sampling regime $k$, the generator samples log-RV from that regime’s training pool. It then draws a standard Gaussian innovation $ε$ and sets $r=exp(y/2)ε$.

#wide(generation-diagram(),[Implemented recursion in `generation.py`. Each generated pair updates the next 30-day history. Sampling pools, standardization, and thresholds remain fixed from training.],<fig-generation>)

This observation law supplies within-regime values that the four probabilities do not specify. Pool support is limited to observed training values. Gaussian innovations are an assumption, and generated return tails need separate evaluation.

== Selection and uncertainty
@fig-workflow states the stage order. Depth selection used validation NLL averaged over development seeds 900 and 901. Realism-weight selection used a validation score combining NLL with a weighted path discrepancy. The quantum HAR choice was depth 3 and $λ=0.05$ @fresh.

#figure(workflow(),caption:[Fresh-study stage order. The seal precedes held-out scoring. Evaluation artifacts preserve per-seed records and daily losses for paired comparisons.],kind:image)<fig-workflow>

Final seeds 0–19 measure variability from training and simulation streams. They are not independent market samples. For date uncertainty, the fresh study averaged daily losses over seeds, then resampled paired date blocks. It used 2,000 circular-bootstrap replicates at block lengths 7 and 30 days.

The confidence intervals are conditional on the selected models, observed period, and resampling design. They do not include all architecture-search uncertainty. Multiple exploratory contrasts and common market shocks also restrict broad inferential claims.

== Metric conventions
Normalized RPS evaluates cumulative probabilities at three ordered cut points:

$ "RPS" = 1/(3N) sum_(t=1)^N sum_(j=0)^2
  (sum_(k=0)^j p_(t,k)-bold(1){z_t<=j})^2. $ <eq-rps>

Equation @eq-rps uses the mean across cut points, rather than their unnormalized sum. Lower NLL and RPS are better. Extreme-bin Brier loss evaluates only class 3. Its interpretation requires observed extreme days.

For positive point forecast $hat(v)_t$, the reported QLIKE convention is

$ "QLIKE" = 1/N sum_(t=1)^N
 (v_t/hat(v)_t-ln(v_t/hat(v)_t)-1). $ <eq-qlike>

Equation @eq-qlike evaluates a variance point forecast, not a regime-probability vector directly. The paper comparison specifies the mapping between each model’s output and these point or categorical scores.

= Implementation
== Tools and execution environment
The implementation is Python, with NumPy statevectors and SciPy optimization. Root dependencies require Python 3.11 or later, NumPy 2.2–2.x, and SciPy 1.16–1.x. `uv.lock` records the resolved environment. Matplotlib supplies optional figures, `arch` supplies the finance extra, and JAX supports v2/v3 gradients.

The present verification ran on Linux x86-64 with Python 3.11.16 and an AMD Ryzen 7 7840HS CPU. This describes the report audit machine. It does not identify every earlier training host or establish a hardware performance comparison.

The fresh study uses numerical-gradient L-BFGS-B for forecast fits and COBYLA for realism fitting. The paper reproduction uses COBYLA. v2/v3 use JAX derivatives with L-BFGS-B. The completed implementation therefore differs from the proposal’s uniform gradient-free training description.

== Datasets and preparation
The paper reproduction uses 913 author-standardized daily observations and 912 consecutive next-day pairs. Its scaling and descriptive fit are separate from the later raw-return-unit dataset.

The principal Bitstamp file contains 3,610 daily rows from 1 December 2016 to 19 October 2026. The first 30 days initialize history features. @tab-splits reports the remaining target dates. @fig-data shows the observed series, split boundaries, and train-defined regime thresholds.

#tab(table(columns:(auto,1fr,auto),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Split*],[*Target dates*],[*Days*]),
 [Training],[2016-12-31–2022-12-31],[2,192],
 [Validation],[2023-01-01–2024-12-31],[731],
 [Test],[2025-01-01–2026-10-19],[657],
),[Chronological fresh-study target splits after the 30-day warm-up.],<tab-splits>)

#wide(image("assets/observed-data.svg",width:100%,alt:"Observed Bitstamp daily log realized variance with training validation and test regions and three training quantile thresholds"),[Observed Bitstamp log-RV from the saved daily CSV. Dashed lines are the training quantiles. The lower test-period distribution explains the scarcity of high-regime labels; this is observed data, not a generated illustration.],<fig-data>)

The file hash matches the fresh-study manifest. The daily series is derived from a community mirror of Bitstamp prices. This provenance supports reproducibility, but does not eliminate exchange or mirror data-quality risk.

Binance follow-ups aggregate checksum-verified five-minute archives into UTC days. BTC and ETH have 3,351 daily rows; SOL and DOGE have shorter listing histories. The builders preserve gaps and record incomplete dates. They do not fabricate missing bars. No incomplete dates occur in the reported replication test periods @markets.

== Development and training details
The fresh configuration compares depths 1–3 with five forecast restarts. The general Born implementation supports depths 1–4. The larger capability must not be described as a four-depth completed fresh-study sweep.

Forecast fitting permits 50,000 objective calls and 2,000 iterations. An independent central-difference check uses an infinity-norm gradient threshold of $10^(-4)$. Realism fitting uses three starts, at most 600 calls, and tolerance 0.002.

Realism-training simulations use four paths of 256 days after 60 burn-in days. Validation uses eight paths. Evaluation uses 32 paths after 100 burn-in days, with a 657-day horizon matching the test window. The generation streams are seeded. Model-specific ridge penalties and selection settings are preserved in the configuration and fit files.

The code stores initialization seeds, selected parameters, objective values, convergence messages, and eligibility flags. Failed eligibility does not silently remove an unfavorable model from the reported aggregate.

== Later implemented variants
The v2 circuit uses affine functions of all inputs in both qubits’ rotation angles. It squashes the four standardized HAR inputs through $2 tanh(x/2)$ and adds target-day weekend and Monday flags. Three layers give 84 nominal parameters. Its no-calendar ablation isolates the calendar addition within that design.

v3 retains the Born readout and uses a ten-restart probability ensemble with ridge 0.01. A trainable Pauli-expectation readout was considered during validation, but it was not the final selected v3 model @variants.

The separate weekend-aware replication pipeline adds weekend rotations to the original circuit family. ETH validation selected a depth-1 $R_y$ expert combined with a fixed HAR forecast. Later BTC, SOL, and DOGE studies reused the selected architecture. Per-seed temperatures are fitted on validation predictions before test evaluation @markets.

The later v3 runners also support asset-specific input files. Two three-asset panels used the 84-parameter Born circuit, ten restart forecasts per seed, and the same six inputs for classical controls. The LINK/DOT/AVAX panel fitted one temperature per model and seed on 2023 validation rows, within bounds [0.2, 5.0]. The 2024 validation slice and test predictions used the fixed temperatures @crossmarkets.

== Testing and artifact integrity
The current combined suite reported *154 passed and 2 skipped*. One skip lacks local historical study artifacts. The other lacks the optional MFDFA package. A skip is not a passed check. The tests cover probability normalization, matrix-reference agreement, paper-twin equivalence, feature leakage, gradient checks, and experiment-stage safeguards.

For this report, independent replay recomputed 20 quantum HAR and 20 softmax HAR daily-loss arrays from saved parameters. The softmax replay used an explicit design matrix and independent normalization. Both matched the saved losses with zero maximum numerical discrepancy in this environment.

The report audit also verified all 30 sealed training-artifact hashes, the data and configuration hashes, every model’s saved mean NLL, and all 26 paired bootstrap interval rows. The tracked results matched the local evaluation JSON exactly. These checks validate the reported evidence; they are not a new training experiment. The current package differs from the historical fresh-study source seal: `fresh_runner.py` adds a configuration field, and two calendar modules were added. The training-artifact hashes still match; this report does not claim that the entire historical source seal matches the current package.

= Results and discussion
== Paper reproduction and earlier study outcomes
The original-paper audit reports converged full-sample fits and a verified classical twin @audit. It does not establish exact replication of every published statistic. The rebuilt return series had lighter tails than the author’s saved generated output. Input normalization, zero-return handling, and unpublished scale choices limit exact reproduction.

Earlier small-sample memory investigations did not find a stable improvement for their one-qubit point-loss task. The earlier short-input realism study also produced weaker test path realism. Those findings are preserved in the repository. They concern different targets, data periods, and training settings from the fresh study.

The fresh study does not erase these negative findings. Its larger dataset, categorical task, and matched-window realism targets changed the experimental question. Conclusions below therefore identify the relevant panel explicitly.

The completed historical 20-seed study used 529/177/177 training, validation, and test targets from the 913-row author dataset @historical. Quantum D had test NLL 0.6920, compared with 0.5289 for HAR quantile. Quantum A increased NLL to 0.8623 and moment distance from 19.72 to 31.86. Earlier smoke work had exposed that test block. It is distinct from the later 657-day fresh-data evaluation.


== Principal forecasting results
@tab-score reports selected fresh-study scores. Q, SM, and NN denote quantum, softmax, and network in that table. @fig-scores provides the corresponding model comparison, including optimizer-seed dispersion. The same-input softmax model had the lowest mean NLL in this panel. The HAR residual comparator had slightly lower normalized RPS.

#tab(table(columns:(1.35fr,.7fr,.65fr,.75fr),inset:3.3pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Model*],[*NLL*],[*RPS*],[*Path D*]),
 ..("softmax-har-D","har-residual","network-har-D","har-quantile","hybrid-quantum","quantum-har-D","quantum-har-A","quantum-short-D","garch-calibrated").map(n => {
   let s=results.summary.at(n)
   ( [#model-name(n)], [#calc.round(s.log_loss.mean,digits:4)], [#calc.round(s.rps_normalized.mean,digits:4)], [#calc.round(s.test_moment_distance.mean,digits:2)] )
 }).flatten(),
),[Fresh-study test means over 20 seeds. NLL is in nats/day; RPS is normalized. Path D is the dimensionless four-moment discrepancy. Lower is better for each metric.],<tab-score>)

#wide(image("assets/forecast-scores.svg",width:100%,alt:"Horizontal bars of held-out negative log likelihood for nine models with across-seed standard-deviation error bars"),[Fresh Bitstamp forecast scores from saved evaluation JSON. Error bars show across-seed SD, not date-sampling confidence intervals. Deterministic or nearly identical fits can have negligible seed SD.],<fig-scores>)

Quantum HAR D achieved NLL 0.5695, compared with 0.5184 for softmax HAR D. Their mean difference was +0.0511. The paired 30-day 95% interval was [+0.0366, +0.0652]. This comparison favors softmax on the observed period. It does not establish a universal ordering across markets.

== Memory benefit and uncertainty
Quantum short D had NLL 0.6204. Adding weekly and monthly inputs reduced it by 0.0509. The 7-day and 30-day paired intervals were [−0.0697, −0.0302] and [−0.0711, −0.0306], respectively.

@fig-contrasts contrasts that gain with realism training and the classical comparison. The intervals assess variation over paired blocks of test dates. The three contrasts answer different questions; none establishes a quantum speedup.

#wide(contrasts(),[Native Lilaq plot of 30-day, 95% paired bootstrap intervals. Contrast 1: quantum HAR A minus HAR D; 2: quantum HAR D minus short D; 3: quantum HAR D minus softmax HAR D. Negative differences favor the first model. Data come directly from the saved interval rows.],<fig-contrasts>)

Memory also improved classical forecasts. Softmax NLL changed from 0.5945 to 0.5184, and network NLL changed from 0.5959 to 0.5228. This shared improvement supports the usefulness of longer history. It does not isolate a uniquely quantum benefit.

== Realism training and generated memory
@fig-tradeoff shows that A training reduced test moment distance for all three HAR model families. It increased their mean forecast NLL. Quantum path distance changed from 33.50 to 29.00, while NLL changed from 0.5695 to 0.6042.

#wide(image("assets/realism-tradeoff.svg",width:100%,alt:"Paired forecast-only and realism-trained model points showing higher negative log likelihood and lower path moment distance"),[Forecast–realism trade-off in the saved fresh-study results. The two panels use different units. Lower distance concerns the selected four moments; it does not certify every property of generated histories.],<fig-tradeoff>)

The quantum A-minus-D NLL difference was +0.0347, with 30-day interval [+0.0230, +0.0454]. Softmax A increased NLL by 0.0080. The network increase was 0.0034, with an interval containing zero. Seed-level improvement counts for path distance were 15/20, 16/20, and 18/20 for quantum, softmax, and network, respectively @fresh.

@fig-acf shows that HAR inputs increased generated weekly dependence relative to the short quantum control. Nevertheless, all displayed forecasters under-produced the observed test lag-7 correlation. A lower aggregate distance can coexist with this visible mismatch.

#wide(image("assets/memory-acf.svg",width:100%,alt:"Observed and generated log-variance autocorrelations at lags one seven and thirty days for short quantum HAR quantum and HAR softmax models"),[Generated-path mean ACFs versus the observed Bitstamp test series. Quantum HAR improves weekly memory relative to quantum short, but remains below the observed lag-7 value of 0.578.],<fig-acf>)

The moment targets are limited. They omit multifractal width, return-tail indices, and interval coverage. Improvements in @eq-distance should not be described as full statistical realism or robustness.

== Distribution shift and failure cases
Training-defined labels in the 657-day Bitstamp test block were 490 calm, 142 normal, 25 wild, and zero extreme. Thus, 74.6% of test days were calm. The extreme-bin Brier score cannot establish detection ability when no extreme event occurs.

The observed lag-30 log-RV correlation was 0.011 in test, compared with 0.251 in same-length training windows. Matching training moments therefore need not reproduce the later market regime. The training-pool generator also cannot generate variance values outside its empirical pool support.

Five of 160 forecast fits missed the fresh-study eligibility check. They were classical hybrid fits and remained in the score summaries. All 120 realism fits terminated normally @fresh. Retaining these records avoids selective reporting, but optimizer termination alone does not certify global optimality.

== Comparison with the original model
A separately registered follow-up compared the paper model with the frozen fresh-study forecasts @papercompare. @tab-paper shows the resulting same-period metrics. The project quantum model had lower NLL, QLIKE, and squared error than this reference.

#tab(table(columns:(1.35fr,.7fr,.7fr,.7fr),inset:3.5pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Model*],[*NLL*],[*QLIKE*],[*Path D*]),
 [Paper, 1 qubit],[1.1961],[0.8399],[215.30],
 [Quantum short D],[0.6204],[0.4886],[72.34],
 [Quantum HAR D],[0.5695],[0.5044],[33.50],
 [Quantum HAR A],[0.6042],[0.5600],[29.00],
),[Paper-model follow-up on the same 657 Bitstamp test days. The protocol was written after the main test results were available; the project forecasts were not refitted.],<tab-paper>)

The paper model’s point output required a specified residual-based categorical mapping for NLL. Its input scale was fitted on training data. The follow-up therefore evaluates the stated adapted baseline, rather than reusing a full-sample fit for forecasting.

The short-to-HAR step improved regime NLL and generated-path distance. It did not improve QLIKE: that score changed from approximately 0.489 to 0.504. A claim that memory improved every forecasting measure would be incorrect.

== Post-hoc calendar variants
@tab-versions summarizes implemented Bitcoin variants. v2 changed input routing, squashing, calendar inputs, and regularization. v3 added the selected restart ensemble and stronger ridge. These variants improved their quantum NLLs on the exposed test period @variants.

#tab(table(columns:(1.5fr,.65fr,.7fr),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Variant*],[*Nominal parameters*],[*Test NLL*]),
 [Quantum v1 HAR D],[24],[0.5695],
 [Quantum v2, no calendar],[60],[0.556],
 [Quantum v2],[84],[0.5288],
 [Quantum v3],[84 per member],[0.5145],
 [Softmax, v2 inputs],[28],[0.4962],
 [Network, v2 inputs],[26],[0.5042],
),[Post-hoc Bitcoin variant comparison. v3 averages ten fitted restart forecasts, so its total fitting effort exceeds one 84-parameter circuit.],<tab-versions>)

Same-input softmax still had lower NLL than v3. The weekend idea followed examination of the main test block, so these scores are exploratory. They are not an independent confirmation of generalization. v2/v3 generation realism was not evaluated in these reported panels.

The v3 seal also has a documented source-hash mismatch caused by removal of an unused import after evaluation. Training-artifact hashes remain intact. This report does not present the v3 source seal as fully matching the current file.

A separate calendar/readout development sweep also retained negative results @development. Its sine control had validation NLL 0.6082, ahead of the quantum readout at 0.6177. A controlled ensemble assigned zero weight to the offered quantum models and achieved 0.6048 using calendar-linear and sine forecasts. Its progression gate failed, so that candidate received no new test evaluation.


== Weekend-aware asset replications
The separate replication family uses a depth-1 weekend-aware $R_y$ expert on HAR, rather than the v3 ensemble. @tab-markets summarizes its validation-temperature-calibrated test NLL @markets. The same date window spans all assets, so these panels are not independent time periods.

#tab(table(columns:(auto,.75fr,.85fr,.7fr),inset:3.5pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Asset*],[*Quantum hybrid*],[*Best classical*],[*Relative gain*]),
 [ETH],[0.648027],[0.648215],[+0.03%],
 [BTC],[0.531976],[0.530880],[−0.21%],
 [SOL],[0.404973],[0.417410],[+2.98%],
 [DOGE],[0.762719],[0.763335],[+0.08%],
),[Calibrated asset-replication NLL. Positive relative gain means lower quantum loss than the best classical comparator. No asset met its registered marked-improvement rule.],<tab-markets>)

The registered rules required at least 5% improvement and paired interval evidence against the relevant classical comparisons. ETH used 95% intervals; BTC, SOL, and DOGE reports used 97.5% intervals under their respective protocols. The 5% magnitude threshold failed for every asset.

SOL’s mean quantum NLL was lower than each comparator’s mean. However, its intervals against weekend softmax and the network included zero. DOGE’s gains were smaller, and the relevant intervals also crossed zero. These results do not support a reliable quantum advantage across the tested assets.

Some classical hybrid fits failed eligibility: 2/20 for ETH, 1/20 for BTC, 1/20 for SOL, and 3/20 for DOGE. They remained in the aggregate results. These failures and the shared market window limit stronger cross-asset conclusions.

The additional 25-parameter quantum-outcome readout failed its ETH validation gate @readout. Its regularized mean calibrated NLL was 0.5221, compared with 0.5171 for the same-seed network. BTC validation and new test scoring were not run for this rejected candidate. Exploratory fixed 50/50 quantum/network blends also failed to reach a 5% validation gain on any of the four assets.


== Additional cross-market v3 results
@tab-crossmarkets summarizes the two later v3 panels @crossmarkets. The first used LTC, BNB, and ADA. The temperature-calibrated follow-up used LINK, DOT, and AVAX. Both used the same 657 test dates as earlier asset studies. Candidate and asset selection followed earlier outcomes, so the evidence remains exploratory.

#tab(table(columns:(auto,1fr,1fr,1fr),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Asset*],[*Quantum NLL*],[*Best classical*],[*Relative gain*]),
 [LTC],[0.613210],[0.596593],[−2.79%],
 [BNB],[0.391824],[0.366583],[−6.89%],
 [ADA],[0.760215],[0.769787],[+1.24%],
 [LINK],[0.577113],[0.591609],[+2.45%],
 [DOT],[0.638703],[0.642954],[+0.66%],
 [AVAX],[0.448466],[0.475457],[+5.68%],
),[Later v3 test panels. LTC/BNB/ADA are uncalibrated; LINK/DOT/AVAX use 2023-fitted temperatures. Values are retained aggregate study reports, rather than independently replayed per-seed results in this report audit.],<tab-crossmarkets>)

Both three-asset pass rules failed. The AVAX mean reduction exceeded 5%, and its reported 30-day quantum-minus-softmax interval was [−0.04826, −0.01078]. That is a single-asset signal on NLL. Quantum QLIKE was worse than both classical controls on LINK, DOT, and AVAX. The observation does not establish an all-metric or transferable advantage.

An additional reporting discrepancy limits the interval claim. Both frozen protocols specified 97.5% intervals, while the evaluation code used the 2.5th and 97.5th percentiles, producing 95% intervals. This report preserves the actual interval level and does not claim that the registered uncertainty requirement was met.

The newer market data and per-seed fit/evaluation artifacts are excluded from the merged repository. Their aggregate reports are retained. The v3 restart runner also omitted optimizer termination flags and iteration counts in these records, contrary to the calibrated protocol. Consequently, this report cannot independently audit those panels' source-data transformations, seed-level losses, or optimizer termination.

== Additional validation-only development
The BTC upgrade sweep selected a depth-3 quantum $R_y$ readout on HAR @btcupgrade. After a higher-budget convergence check, mean calibrated validation NLL was 0.645654 versus 0.661433 for the network, a 2.39% reduction. Two fresh development seeds and two restarts were used. The previously scored BTC test period remained closed. Selection and temperature fitting reused the validation period, so its intervals are descriptive.

The BTC market-signal study added preceding-week BTC log-RV to other assets' input blocks @btcupgrade. Its complete SOL validation panel improved by only 0.39% over the network. The 5% gate failed; ETH was stopped partially, and DOGE and BTC self-control were not run. These incomplete panels are not presented as completed replications.

== Interpretation
The clearest supported effect is the fresh-study memory benefit. Realism-aware training produced a measurable trade-off for the four chosen path statistics. Classical baselines remained competitive or better in the main study. Later v3 evaluation reported a 5.68% AVAX NLL gain, but both three-asset panel rules failed. The interval-level discrepancy and missing seed artifacts limit that exploratory signal.

A comparison between a quantum circuit and a classical baseline is not a hardware speedup experiment. Exact statevector execution on a laptop supplies no evidence of computational quantum advantage. The paper model’s exact classical twin further reinforces the need for careful attribution.

= Conclusion and future work
== Achievements
The completed repository contains a paper reproduction audit, one- and two-qubit forecasters, classical controls, past-only preprocessing, recursive generation, and reproducible evaluation stages. The main fresh study includes saved fits, sealed artifacts, daily losses, and paired date-bootstrap intervals.

The matched memory comparison improved quantum regime NLL by 0.0509 on the 657-day Bitstamp test block. Realism training lowered the selected path discrepancy and increased forecast loss. Calendar-aware variants improved the quantum model’s exposed-period score. Later v3 panels produced a limited AVAX NLL signal while failing their transfer rules. A separate BTC validation sweep nominated an untested candidate.

== Limitations
The studies use small noiseless simulated circuits and a limited set of crypto assets. Newer cross-market panels lack committed per-seed artifacts and used 95% intervals where their protocols required 97.5%. The main test block contains no training-defined extreme events. Twenty seeds quantify algorithmic variability, not twenty independent market histories. Repeated Bitcoin benchmark use limits confirmatory interpretation of later designs.

Model capacity, effective parameter count, optimizer effort, and input information are not uniformly identical across every comparison. Training-pool support constrains generated extremes. Four path moments do not characterize the full distribution. Data gaps, source provenance, and nonstationarity remain relevant.

== Possible improvements
A future evaluation should freeze the full procedure before using new dates or assets. Rolling development folds could test sensitivity to market regimes. Matched no-entanglement and periodic classical controls could clarify which circuit features matter.

Numerical interval forecasting requires an explicit continuous predictive law and measured coverage. Tail-focused evaluation needs a held-out block with enough extreme events. Broader path diagnostics should remain separate from targets used in training. Device execution, shot noise, and measured resource comparisons would require a new hardware study.

These items are future work. No results from them are included in the reported achievements.

= Contributions
The team’s research and development responsibilities are summarized in @tab-contributions.

#tab({
 set par(justify:false)
 table(columns:(.75fr,1.6fr),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Team member*],[*Research and development*]),
 [Nidhi Rakesh],[Reproduction of the one-qubit reference model and investigation of quantum data encoding; development and evaluation of the v2 and v3 circuit variants.],
 [Srimoneyshankar Ajith],[Market-data preparation and calendar effects; weekend-aware forecasting, probability calibration, and replication across multiple crypto assets.],
 [Bharadwaj B Chand],[Development of the two-qubit Born model and realism-aware training; analysis of generated volatility dynamics, optimizer behavior, and controlled ablations.],
 [Vishnunath A Suresh],[Design of the multi-horizon regime-forecasting framework and experimental methodology; research on volatility memory, model selection, and out-of-sample generalization.],
 [Gopi Krish],[Development of classical baselines and evaluation methods; comparative research on scoring rules, calibration, and the performance of quantum and classical models.],
)},[Team responsibilities across model development, experimental evaluation, and research.],<tab-contributions>)

Interpretation of experimental results and assessment of methodological limitations are shared across the team.

= References
#bibliography("references.bib",style:"ieee",title:none)

#pagebreak()
#set page(columns:1)
= Appendices
== Reproduction and report build
The following commands use the existing checkout and saved evidence. Report preparation does not retrain any model or overwrite a sealed evaluation directory.

```sh
uv sync --locked --extra dev --extra plots --python 3.12
uv run pytest -q
uv run python report/tools/build_evidence.py
typst compile --font-path report/fonts --root . report/main.typ output/pdf/ieg313-project-report.pdf
uv run python report/tools/review_report.py
```

Fresh-study training is stage-based. To reproduce it independently, choose a new directory and run `scripts/run_fresh_study.py --help`. The stage order is:

```text
manifest
 develop-d          (development seeds 900 and 901)
 develop-hybrid     (development seeds 900 and 901)
 select-d
 develop-a          (development seeds 900 and 901)
 select-a
 train              (final seeds 0 through 19)
 seal
 evaluate
```

Each stage uses `--config configs/fresh-study.json --output NEW_DIRECTORY`. Development and training stages also require the relevant repeated `--seed` arguments. The Bitstamp input defaults to `data/bitstamp_daily.csv`. Evaluation is permitted only after seal verification. To rebuild the input file, follow the dataset provenance and acquisition instructions in `data/README.md`.

== Supporting code excerpt
The following logic corresponds to `history_features` in `src/qcvol/data.py`. It illustrates the absence of target-day inputs. The caller supplies a history ending strictly before the target day.

```python
def history_features(log_rv, returns):
    y, r = np.asarray(log_rv), np.asarray(returns)
    if len(y) < 30 or len(r) != len(y):
        raise ValueError("Need 30 aligned past observations")
    return np.array([y[-1], y[-7:].mean(), y[-30:].mean(), r[-1]])
```

== Evidence index and provenance
@tab-evidence connects key claims to inspectable source artifacts. `report/qa/evidence-checks.json` records the independent replay and hashes produced during this report’s audit. The source snapshot is `0aeab94`; the report changes do not modify the scientific model files.

#tab(table(columns:(1.1fr,2fr),inset:5pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Claim or component*],[*Primary repository evidence*]),
 [Fresh study scores and intervals],[`doc/fresh-study-results/results.json`; local `results/fresh-study/evaluation/`],
 [Frozen choices and budget],[`configs/fresh-study.json`; `doc/fresh-study-protocol.md`; `select-d.json`, `select-a.json`],
 [Training integrity],[`results/fresh-study/seal.json`; 30 hashed training artifacts; data and config SHA-256 values],
 [Architecture and quantum gates],[`src/qcvol/quantum.py`; `fresh_models.py`; `generation.py`; `fresh_runner.py`],
 [Paper audit and follow-up],[`doc/paper-reproduction.md`; `doc/paper-comparison.md`; saved `paper-comparison.json`],
 [Post-hoc variants],[`doc/v2-study.md`; `doc/v3-study.md`; `src/qcvol_v2/`; `src/qcvol_v3/`],
 [Asset replications],[`doc/eth-study.md`; `doc/btc-study.md`; `doc/sol-doge-study.md`; `src/qcvol_next/`],
 [Later v3 panels],[`doc/multimarket-v3-results.md`; `doc/calibrated-v3-results.md`; frozen protocols and `scripts/evaluate_calibrated_v3.py`],
 [Team identity],[Supplied seven-page _Schrödinger’s Cat: Quantum Volatility Range Forecaster_ document; instructor names supplied separately.],
),[Claim-to-source index for reproducibility and scientific review.],<tab-evidence>)

The Bitstamp daily-data SHA-256 is:

```text
bff1209621cd2ac95880b789668b950caec1b3198bf73d22e3d3b4767037f17a
```

All plotted numerical results derive from the saved JSON, NPZ daily losses, or observed daily CSV. The circuit and flow diagrams depict code structure and mathematical operations; they are explanatory diagrams, not experimental observations. The institutional logo was retrieved from the institute’s official website.

== Additional complete forecast scorecard
@tab-complete preserves all 20 fresh-study model rows. SD refers to training-seed dispersion. It does not replace the paired date-block intervals in the principal analysis.

#tab(table(columns:(1.4fr,1fr,1fr,1fr,auto),inset:4pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Model*],[*NLL mean ± SD*],[*RPS mean*],[*Path D mean ± SD*],[*Eligible*]),
 ..results.summary.pairs().sorted(key:p=>p.at(1).log_loss.mean).map(((n,s)) => (
   [#n],
   [#calc.round(s.log_loss.mean,digits:4) ± #calc.round(s.log_loss.sd,digits:4)],
   [#calc.round(s.rps_normalized.mean,digits:4)],
   [#calc.round(s.test_moment_distance.mean,digits:2) ± #calc.round(s.test_moment_distance.sd,digits:2)],
   [#s.fits_eligible/20],
 )).flatten(),
),[Complete fresh-study test scorecard, generated directly from the saved result summary.],<tab-complete>)

== Scientific reporting and QVRF-TWS-1.0 review
The report follows the university’s 13-part structure. IEEE numerical references and mathematical conventions provide the writing foundation @ieeestyle. The reporting review adapts reproducibility and limitation principles from the NeurIPS checklist @neurips.

The project uses selected controlled-language, verifiability, and plain-language principles specified in QVRF-TWS-1.0. This adaptation does not constitute formal compliance certification under ASD-STE100, ISO/IEC/IEEE 29148, ISO 24495-1, or NeurIPS.

#tab(table(columns:(1.05fr,2fr),inset:5pt,stroke:.35pt+rgb("ccd5dc"),
 table.header([*Review item*],[*Evidence and disposition*]),
 [Claims and observations],[Completed work is separated from future work. No hardware speedup, quantum advantage, or universal superiority is inferred.],
 [Experimental integrity],[Train/validation/test periods, selection, seeds, failed-fit handling, and post-hoc exposure are explicit.],
 [Uncertainty],[Seed SD and paired date-bootstrap intervals have distinct meanings. Confidence levels differ across protocols.],
 [Reproducibility],[Commands, configuration paths, artifact index, hashes, and independent replay are provided.],
 [Notation and terminology],[RV means variance in the code. Regime probabilities are distinguished from continuous intervals. Equations define symbols and scoring conventions.],
 [Limitations and failures],[Zero extreme test days, empirical support limits, data gaps, model-capacity differences, and exposed-period variants are disclosed.],
 [Writing review],[Sentences above 35 words are flagged by the companion review tool. Important equations, figures, and tables are cross-referenced.],
 [Research ethics and access],[Public market data; no human-subject experiment. Source datasets and licenses retain their upstream conditions. No trade execution or personal financial data is involved.],
),[Scientific-consistency and technical-writing review criteria applied to this report.],<tab-review>)

@tab-review describes the reporting review and its scope. Compilation, page rendering, and visual inspection are recorded in the companion QA notes. The review makes no claim that a short checklist proves every scientific conclusion.
