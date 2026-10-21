#let green = rgb("#1BAA4A")
#let dgreen = rgb("#23904A")
#let blue = rgb("#00AEEF")
#let indigo = rgb("#2E3192")
#let keybox(body) = block(width: 100%, fill: rgb("#EAF7EE"), stroke: (left: 4pt + green), inset: 12pt, radius: 3pt, above: 1.2em, below: 1.2em, body)
#let horizontalrule = line(length: 100%, stroke: 0.5pt + luma(180))

#set page(paper: "a4", margin: (x: 2.5cm, top: 2.5cm, bottom: 2.5cm))
#set text(font: "Libertinus Serif", size: 11.5pt, lang: "en")
#set par(justify: true, leading: 0.8em, spacing: 1.2em)
#set heading(numbering: "1.1")
#show heading: set text(font: "Noto Sans", fill: indigo)
#show heading.where(level: 1): it => { pagebreak(weak: true); v(0.4em); text(size: 19pt, it); v(-0.3em); line(length: 100%, stroke: 1.5pt + green); v(0.5em) }
#show heading.where(level: 2): it => { v(0.6em); text(size: 14pt, fill: dgreen, it); v(0.2em) }
#show strong: set text(fill: indigo)
#show raw.where(block: true): block.with(fill: luma(245), inset: 10pt, radius: 3pt, width: 100%)
#show figure: set block(above: 1.4em, below: 1.4em)
#show figure.caption: set text(size: 10pt, style: "italic")
#set table(stroke: 0.5pt + luma(190), inset: 7pt, fill: (_, y) => if y == 0 { indigo } else if calc.even(y) { rgb("#F3F6FB") })
#show table.cell.where(y: 0): set text(fill: white, weight: "bold", font: "Noto Sans", size: 10pt)
#show table: set text(size: 10pt)
#show table: set par(justify: false)
#show figure.where(kind: table): set figure.caption(position: top)
#set math.equation(numbering: none)

// Title page
#page(margin: (x: 2.2cm, y: 2cm), numbering: none)[
  #align(center)[
    #image("fig/logo.png", width: 62%)
    #v(1.2cm)
    #text(font: "Noto Sans", size: 12pt, fill: dgreen, weight: "bold")[IEG313 #sym.dot Quantum Computing for Engineers]
    #v(0.5cm)
    #line(length: 70%, stroke: 2pt + green)
    #v(0.4cm)
    #text(font: "Noto Sans", size: 24pt, weight: "bold", fill: indigo)[Quantum Volatility Range Forecaster]
    #v(0.2cm)
    #text(size: 14pt)[Extending single-qubit quantum circuit learning for\ cryptocurrency volatility forecasting]
    #v(0.4cm)
    #line(length: 70%, stroke: 2pt + green)
    #v(0.8cm)
    #text(size: 12pt)[Project Report submitted by group]\
    #text(font: "Noto Sans", size: 16pt, weight: "bold", fill: blue)[Schrödinger's Cat]
    #v(0.6cm)
    #table(columns: (auto, auto), align: (left, left), stroke: none, fill: none, inset: 5pt,
      table.header[*Name*][*Register No.*],
      [Srimoneyshankar Ajith], [2024BCS0055],
      [Bharadwaj B Chand], [2024BCS0059],
      [Nidhi Rakesh], [2024BCD0006],
      [Vishnunath A Suresh], [2024BCS0315],
      [Gopi Krish], [2024BCS0054],
    )
    #v(0.6cm)
    #text(size: 12pt)[*Instructors*]\
    Dr. Rubell Marion Lincy #h(1em) #sym.dot #h(1em) Dr. Asha Sebastian
    #v(1fr)
    #text(size: 12pt)[Department of Computer Science and Engineering\
    Indian Institute of Information Technology Kottayam\
    Academic Year 2026–27 (Third Year)]
  ]
]

#set page(numbering: "i", header: align(right, text(size: 9pt, fill: luma(120))[Quantum Volatility Range Forecaster #sym.dot Schrödinger's Cat]))
#counter(page).update(1)
#heading(numbering: none, outlined: false)[Contents]
#outline(title: none, indent: auto, depth: 2)
#heading(numbering: none, outlined: false)[List of Figures]
#outline(title: none, target: figure.where(kind: image))
#heading(numbering: none, outlined: false)[List of Tables]
#outline(title: none, target: figure.where(kind: table))

#set page(numbering: "1")
#counter(page).update(1)
= Abstract
<abstract>
Prices of cryptocurrencies like Bitcoin swing a lot, and those swings
come in waves: a calm day is usually followed by another calm day, and a
wild day by more wild days. The size of these swings is called
#strong[volatility]. Predicting tomorrow's volatility is useful for
managing risk.

A 2026 research paper by T. Takaishi showed that a #strong[one-qubit
quantum circuit] (simulated on a normal computer) can be trained to
predict Bitcoin's next-day volatility. Our project started by
#strong[rebuilding that model exactly] and then tried to make it better
in three ways:

- #strong[More memory:] let the model look at the last day, the last
  week and the last month, not just yesterday.
- #strong[A range instead of one number:] use #strong[two qubits] so the
  model gives the chance that tomorrow is #emph[calm], #emph[normal],
  #emph[wild] or #emph[extreme].
- #strong[More realistic behaviour:] train it so that the price
  histories it imagines look like real ones.

We tested everything fairly: each model is trained on old data, tuned on
newer data, and judged only once on the most recent data it has never
seen. Every quantum model was compared with an ordinary (classical)
model given #strong[exactly the same inputs].

#keybox[
#strong[Main findings.] (1) Our two-qubit model is much better than the
original paper's model on fresh Bitcoin data (score 0.5695 vs 1.196,
lower is better). (2) Giving the model a week and a month of memory
clearly helps. (3) However, simple classical models with the same inputs
were still as good or better in almost every test, including across ten
different cryptocurrencies. #strong[We therefore do not claim any
quantum advantage.] All quantum circuits were run on a simulator; no
real quantum computer was used.

]
= Introduction
<introduction>
== Background
<background>
#strong[What is volatility?] If Bitcoin moves 0.5% in a day, that day
was calm; if it moves 8%, it was wild. We measure each day's volatility
using #strong[realized volatility (RV)]: take the price change over
every few minutes during the day, square each change, and add them up:

$ upright("RV")_t = sum_(i = 1)^n r_(t \, i)^2 $

where $r_(t \, i)$ is the $i$-th small price change (log return) on day
$t$. A bigger RV means a wilder day.

#strong[Why is it predictable at all?] Volatility has #emph[memory]:
wild weeks cluster together. A well-known classical model called
#strong[HAR] (Corsi, 2009) uses exactly this. It predicts tomorrow from
the average of yesterday, the last 7 days and the last 30 days.

#strong[What is quantum circuit learning?] A qubit is the quantum
version of a bit. Instead of being just 0 or 1, it holds a
#emph[probability] of being measured as 0 or 1. A quantum circuit
rotates qubits by angles. In #strong[quantum circuit learning] (Mitarai
et al., 2018), we put our data into some of these angles, leave other
angles as adjustable "knobs", and let a normal computer tune the knobs
until the circuit's output matches the data, very much like training a
small neural network.

== Problem statement
<problem-statement>
The original paper's model has four weaknesses:

+ It only sees #strong[yesterday], so it cannot use the weekly or
  monthly patterns we know exist.
+ It outputs #strong[one number], not how likely a calm or extreme day
  is.
+ It is trained to predict one day ahead, but judged on whether the long
  histories it generates look realistic.
+ It is trained and judged on the #strong[same data], so we cannot tell
  how well it would work on new days.

== Objectives
<objectives>
+ Rebuild the paper's one-qubit model and check that we get the same
  results.
+ Add memory, range forecasts and realism-aware training.
+ Compare every quantum model with a classical model that gets the same
  inputs.
+ Check whether any improvement holds up on fresh data and on other
  cryptocurrencies.

== Scope
<scope>
We study daily volatility of Bitcoin (the paper's own data, plus fresh
Bitstamp data up to 19 October 2026) and nine more coins from Binance
(ETH, SOL, DOGE, LTC, BNB, ADA, LINK, DOT, AVAX). Quantum circuits are
run on an exact simulator on ordinary CPUs. A script to run on an IBM
quantum computer exists but #strong[was not run], so we make no claims
about real quantum hardware or speed.

= Literature Review
<literature-review>
#figure(
  align(center)[#table(
    columns: (33.33%, 33.33%, 33.33%),
    align: (auto,auto,auto,),
    table.header([Work], [What it did], [Limitation for our purpose],),
    table.hline(),
    [Mitarai et al.~(2018)], [Introduced quantum circuit
    learning], [General method, not about finance],
    [Pérez-Salinas et al.~(2020)], [Showed that feeding the data into a
    small circuit several times ("re-uploading") makes it much more
    powerful], [Classification, not forecasting],
    [Corsi (2009), HAR model], [Simple classical model using
    day/week/month averages; still a strong benchmark], [Gives one
    number only],
    [Takaishi (2025)], [One-qubit circuit on simulated volatility
    data], [Synthetic data only],
    [Takaishi (2026), #strong[our base paper]], [One-qubit circuit on
    real Bitcoin volatility; checked the "multifractal" shape of
    generated series], [One day of memory; one number; no held-out test;
    no matched classical comparison],
    [Schreiber et al.~(2022); Bowles, Ahmed and Schuld (2024)], [Showed
    many small quantum models can be copied or beaten by classical
    models, and called for fair benchmarks], [Motivates our same-input
    classical controls],
    [Li et al.~(2025)], [Quantum reservoir computing for
    volatility], [Different model type],
  )]
  , caption: [Related work and its limitations]
  , kind: table
  )

#keybox[
#strong[Gap we address.] No earlier quantum volatility study combined
(a) multi-day memory, (b) a probability range output, (c) a strict
train/validate/test split, and (d) classical models with identical
inputs as the comparison.

]
= Novelty
<novelty>
Our work is based on #strong[T. Takaishi, "Quantum Circuit Learning for
Volatility Modeling: Multifractal Analysis of Realized Volatility Time
Series", #emph[Fractal and Fractional] 10(7):442, 2026 \[1\]]. What we
did differently:

#figure(
  align(center)[#table(
    columns: (50%, 50%),
    align: (auto,auto,),
    table.header([Original paper], [Our project],),
    table.hline(),
    [1 qubit], [2 qubits connected by a CNOT gate],
    [Input: yesterday only], [Input: yesterday, 7-day average, 30-day
    average and return],
    [Output: one number], [Output: probability of 4 levels (calm,
    normal, wild, extreme)],
    [Trained on squared error], [Trained on log loss, optionally plus a
    realism penalty],
    [Same data for training and judging], [Train / validation / test
    split in time order],
    [No same-size classical comparison], [Classical "twins" with
    identical inputs and output],
    [One dataset], [Fresh Bitstamp data and 10 Binance coins, 20 random
    seeds each],
    [No pass/fail rule], [Pass/fail rules written down #strong[before]
    looking at test results],
  )]
  , caption: [Original paper vs our project]
  , kind: table
  )

= Methodology and System Design
<methodology-and-system-design>
== Overall pipeline
<overall-pipeline>
#figure(image("fig/pipeline.png", width: 100.0%),
  caption: [
    How raw prices become a forecast and a score.
  ]
)

+ #strong[Raw data:] prices every 1 or 5 minutes.
+ #strong[Daily RV:] squared small returns added up for each day
  (equation above). We work with $log \( upright("RV") \)$ because it is
  better behaved.
+ #strong[Memory features:] for each day we compute yesterday's value,
  the 7-day average, the 30-day average, and yesterday's return. The
  first 30 days are dropped because they lack a full month of history.
+ #strong[Scaling:] features are rescaled using statistics from the
  training period only, so no future information leaks in.
+ #strong[Model:] the quantum circuit (or a classical model) turns the
  features into four probabilities.
+ #strong[Score:] we compare the probabilities with what actually
  happened.

== The four volatility levels
<the-four-volatility-levels>
#figure(image("fig/levels.png", width: 100.0%),
  caption: [
    The four levels. Each one is matched to one outcome of the two
    qubits.
  ]
)

Using the training data, we find the 30th, 70th and 95th percentile of
$log \( upright("RV") \)$. These cut points define four levels. Two
qubits have exactly four possible measurement outcomes
($\| 00 chevron.r \, \| 01 chevron.r \, \| 10 chevron.r \, \| 11 chevron.r$),
so each outcome naturally represents one level.

== Original model (paper)
<original-model-paper>
The paper's single qubit receives yesterday's return $r$ and variance
$sigma^2$ as rotation angles, then one trainable rotation
$U_3 \( theta \, phi.alt \, lambda \)$. The probability of measuring 0
is used directly as the forecast. We verified our rebuild against the
paper's closed-form formula
$P \( 0 \) = 1 / 2 + 1 / 2 thin upright(bold(n)) dot.op upright(bold(b))$.

== Our two-qubit circuit
<our-two-qubit-circuit>
#figure(image("fig/circuit.png", width: 100.0%),
  caption: [
    One layer of our circuit. Blue gates load the data, green gates are
    trainable, then a CNOT links the qubits. The layer is repeated L
    times.
  ]
)

- #strong[Load data (blue):] qubit 0 gets yesterday and the weekly
  average; qubit 1 gets the monthly average and the return. Each is
  multiplied by a trainable weight $w$.
- #strong[Trainable rotations (green):] each qubit gets an adjustable
  $R_Y$ and $R_Z$ rotation.
- #strong[CNOT:] links the two qubits so they can share information.
- #strong[Repeat:] the whole layer is repeated $L$ times (we tried 1 to
  4; 3 layers = 24 parameters). Loading the data again in every layer is
  the "re-uploading" trick.
- #strong[Measure:] the probabilities of the four outcomes are the
  forecast.

The probability of each outcome comes from the quantum state
$\| psi chevron.r$ (the Born rule):

$ p_k = \| chevron.l k thin \| thin psi \( upright(bold(x)) \; bold(theta) \) chevron.r \|^2 \, #h(2em) k in { 00 \, 01 \, 10 \, 11 } $

Later versions (v2 and v3) added a classical HAR term to the circuit's
output and used more training restarts. Our multi-coin version uses only
$R_Y$ gates plus a HAR term, with a single "temperature" setting that
makes the probabilities slightly more or less confident.

== How the model is scored
<how-the-model-is-scored>
#strong[Log loss] (main score, lower is better). If the model gave
probability $p_(upright("true") \, t)$ to the level that actually
happened on day $t$:

$ upright("Log loss") = - 1 / N sum_(t = 1)^N log p_(upright("true") \, t) $

A model that puts high probability on what really happens gets a low
score. A model that is confidently wrong is punished heavily.

Other checks: #strong[QLIKE] (a standard error score for volatility),
how realistic generated histories look (their correlation with the past
at 1, 7 and 30 days), and calibration (does "30% chance" happen about
30% of the time).

== Making the comparison fair
<making-the-comparison-fair>
#figure(image("fig/fair.png", width: 95.0%),
  caption: [
    Every quantum model is paired with classical models given exactly
    the same information.
  ]
)

#figure(image("fig/split.png", width: 100.0%),
  caption: [
    Time-ordered split for the fresh Bitcoin study. The test period is
    only opened once.
  ]
)

- #strong[20 seeds:] each model is trained 20 times from different
  random starting points; we report the average.
- #strong[Confidence intervals:] we resample blocks of 7 or 30
  consecutive test days (bootstrap) to see whether a difference could
  just be luck. If the interval includes zero, the difference is
  #strong[not] convincing.
- #strong[Rules written in advance:] for the multi-coin studies we
  decided beforehand that the quantum model must beat the best classical
  model by #strong[at least 5%] in log loss, with an interval that
  excludes zero, on all coins in the group.
- #strong[Sealed results:] trained models were saved and fingerprinted
  (hashed) before test scoring, so they could not be changed afterwards.

= Implementation
<implementation>
== Tools
<tools>
#figure(
  align(center)[#table(
    columns: (50%, 50%),
    align: (auto,auto,),
    table.header([Item], [Details],),
    table.hline(),
    [Language], [Python 3.12, managed with `uv`],
    [Main libraries], [NumPy, SciPy (optimisation)],
    [Extra libraries], [JAX (faster quantum versions), `arch` (GARCH
    model), matplotlib (plots)],
    [Quantum simulator], [Our own exact simulator written in NumPy (no
    noise)],
    [Optimisers], [L-BFGS-B and COBYLA from SciPy],
    [Testing], [109 automated tests (pytest) plus Ruff style checks],
    [Hardware], [Ordinary laptops (CPU only)],
  )]
  , caption: [Software and tools]
  , kind: table
  )

== Datasets
<datasets>
#figure(
  align(center)[#table(
    columns: (33.33%, 33.33%, 33.33%),
    align: (auto,auto,auto,),
    table.header([Dataset], [Source], [Period and size],),
    table.hline(),
    [Paper's Bitcoin data], [Author's public repository], [913 days (Aug
    2020 to Feb 2023); split 529 / 177 / 177],
    [Fresh Bitcoin (Bitstamp)], [1-minute prices], [Dec 2016 to 19 Oct
    2026; train 2,192 days, validation 731, test 657],
    [10 Binance coins], [5-minute prices, checksum-verified], [Up to 19
    Oct 2026; same 657-day test period (from 2025-01-01)],
  )]
  , caption: [Datasets used]
  , kind: table
  )

== Code organisation
<code-organisation>
- `qvol/`: the rebuild of the original paper, with five experiment
  scripts.
- `src/qcvol/`: our main pipeline: data, quantum simulator, classical
  models, training, scoring.
- `src/qcvol_v2/`, `src/qcvol_v3/`: improved quantum versions.
- `src/qcvol_next/`: Binance data and the multi-coin models.
- `scripts/`: data builders, study runners, checkers and plotting.
- `doc/`: a written plan (protocol) and a results note for every study.

== Development steps
<development-steps>
+ Rebuild and check the paper's model.
+ Build the two-qubit model and the classical comparators on the paper's
  data.
+ Run a frozen 20-seed comparison.
+ Repeat on fresh Bitstamp data.
+ Improve the circuit (v2, v3).
+ Write rules in advance, then test on ten Binance coins.

= Results and Discussion
<results-and-discussion>
== Step 1: Rebuilding the paper
<step-1-rebuilding-the-paper>
We reproduced the paper's model on its own data: fitted angles
$theta = - 4.557$, $phi.alt = 0.360$, $lambda = 1.700$\; training error
(MSE) 0.00205; correlation between forecast and real value 0.449. We
also found that the angle $phi.alt$ has #strong[no effect] on the
output, and confirmed the model only uses one day of history.

#figure(image("fig/fig_memory_gap.png", width: 80.0%),
  caption: [
    Diagnostic figure from our rebuild of the paper model.
  ]
)

== Step 2: 20-seed study on the paper's data
<step-2-20-seed-study-on-the-papers-data>
#figure(
  align(center)[#table(
    columns: 2,
    align: (auto,auto,),
    table.header([Model], [Test log loss (lower is better)],),
    table.hline(),
    [HAR quantile (classical)], [#strong[0.5289]],
    [HAR residual (classical)], [0.5295],
    [Small network (classical)], [0.5784],
    [Softmax (classical)], [0.5822],
    [Quantum, range forecast], [0.6920],
    [Quantum, with realism training], [0.8623],
  )]
  , caption: [Step 2: 20-seed test results on the paper's data]
  , kind: table
  )

#keybox[
On the paper's data, #strong[classical models won]. Adding realism
training made the quantum model's forecasts worse, and on the test data
its generated histories were also less realistic (moment distance 19.72
rose to 31.86).

]
== Step 3: Fresh Bitcoin data and the original paper
<step-3-fresh-bitcoin-data-and-the-original-paper>
#figure(image("fig/fresh.png", width: 85.0%),
  caption: [
    Test log loss on fresh Bitstamp Bitcoin data, 657 test days, average
    of 20 seeds.
  ]
)

#figure(
  align(center)[#table(
    columns: 3,
    align: (auto,auto,auto,),
    table.header([Measure (lower is better)], [Original paper], [Our
      quantum model],),
    table.hline(),
    [Log loss], [1.196], [#strong[0.5695]],
    [QLIKE], [0.840], [#strong[0.504]],
    [Realism distance], [215.3], [#strong[33.5]],
  )]
  , caption: [Step 3: original paper model vs our quantum model (fresh
  Bitcoin test)]
  , kind: table
  )

#keybox[
#strong[Our upgrade clearly beats the original paper model] on every
measure, and all confidence intervals exclude zero. #strong[Memory
helps:] adding weekly and monthly averages improved log loss by 0.051
(interval −0.071 to −0.030). #strong[But] the classical softmax model
with the same inputs scored 0.5184, better than our quantum model. (This
paper comparison was planned after we had already seen the main test
results.)

]
#figure(image("fig/fig_paper_vs_ours.png", width: 80.0%),
  caption: [
    Paper model vs our model.
  ]
)

== Step 4: Improved circuits (v2 and v3)
<step-4-improved-circuits-v2-and-v3>
#figure(
  align(center)[#table(
    columns: 2,
    align: (auto,auto,),
    table.header([Model], [Test log loss],),
    table.hline(),
    [Quantum v1], [0.5695],
    [Quantum v2], [0.529],
    [Quantum v3], [0.5145],
    [Classical softmax with v2 inputs], [#strong[0.4962]],
  )]
  , caption: [Step 4: quantum circuit versions vs matching classical
  model]
  , kind: table
  )

Each new quantum version was better than the last, but the matching
classical model still won by 0.018. These were tested on a period we had
already looked at, so they are only indicative.

== Step 5: Ten cryptocurrencies
<step-5-ten-cryptocurrencies>
#figure(image("fig/multimarket.png", width: 85.0%),
  caption: [
    How much better (positive) or worse (negative) the quantum model was
    than the best classical model, per coin. The red line is the 5%
    target.
  ]
)

#figure(
  align(center)[#table(
    columns: (20%, 20%, 20%, 20%, 20%),
    align: (auto,auto,auto,auto,auto,),
    table.header([Coin], [Quantum log loss], [Best classical], [Quantum
      gain], [Passed 5% rule?],),
    table.hline(),
    [ETH], [0.6480], [0.6482], [+0.03%], [No],
    [BTC], [0.5320], [0.5309], [−0.21%], [No],
    [SOL], [0.4050], [0.4174], [+2.98%], [No],
    [DOGE], [0.7627], [0.7633], [+0.08%], [No],
    [LTC], [0.6132], [0.5966], [−2.79%], [No],
    [BNB], [0.3918], [0.3666], [−6.89%], [No],
    [ADA], [0.7602], [0.7698], [+1.24%], [No],
    [LINK], [0.5771], [0.5916], [+2.45%], [No],
    [DOT], [0.6387], [0.6430], [+0.66%], [No],
    [AVAX], [0.4485], [0.4755], [#strong[\+5.68%]], [Alone yes, group
    no],
  )]
  , caption: [Step 5: quantum vs best classical model on ten coins (test
  log loss)]
  , kind: table
  )

#keybox[
#strong[No coin group passed the rule written in advance.] AVAX was the
only coin above 5%, but its group (LINK, DOT, AVAX) failed together, and
on the QLIKE score the quantum model was worse on all three.

]
== What this means
<what-this-means>
- The big jump over the original paper came from #strong[better inputs
  (memory)] and #strong[a better output (four probabilities)], not from
  anything uniquely quantum: classical models given the same things do
  as well or better.
- Realism training made forecasts worse in our tests.
- Small quantum circuits like ours behave much like small classical
  models, which matches warnings in recent research (Schreiber et al.,
  2022; Bowles et al., 2024).

= Conclusion and Future Work
<conclusion-and-future-work>
== What we achieved
<what-we-achieved>
- A checked rebuild of the Takaishi one-qubit model.
- A two-qubit range forecaster with memory that #strong[clearly beats
  the original model] on fresh data.
- A fair testing setup: time-ordered splits, classical twins, 20 seeds,
  rules written in advance, sealed results.
- Tests on ten cryptocurrencies, plus 109 automated code tests.

== Limitations
<limitations>
- #strong[Simulator only:] no real quantum computer was used, and no
  noise was modelled.
- #strong[Reused test period:] v2, v3 and some later studies use the
  same 2025-2026 test days, so their results are only indicative.
- #strong[Seeds are not markets:] 20 seeds show training variation, not
  20 independent experiments.
- #strong[Optimiser limits:] training stopped at a fixed budget, which
  does not prove the best settings were found.
- #strong[Data limits:] the paper's data is pre-scaled (no real units),
  and the fresh Bitcoin test period had no "extreme" days.

== Future work
<future-work>
- Test our most promising Bitcoin setting (a 3-layer $R_Y$ circuit that
  was 2.39% better than the network on validation data) on truly new
  data.
- Run on IBM quantum hardware and study the effect of noise.
- Add formal forecast comparison tests (Diebold--Mariano).
- Try other quantum approaches such as quantum reservoirs or generative
  "Born machines".

= Contributions
<contributions>
#figure(
  align(center)[#table(
    columns: (50%, 50%),
    align: (auto,auto,),
    table.header([Member], [Responsibilities and tasks],),
    table.hline(),
    [#strong[Srimoneyshankar Ajith] (2024BCS0055)], [Project
    coordination; Binance data pipeline with checksum verification; ETH,
    BTC, SOL and DOGE replication studies and their pre-written rules;
    $R_Y$ HAR hybrid quantum model; research log],
    [#strong[Bharadwaj B Chand] (2024BCS0059)], [Checking the paper
    rebuild and multifractal analysis; memory experiments;
    realism-training study; classical baselines (HAR, GARCH);
    verification scripts and comparison figures],
    [#strong[Nidhi Rakesh] (2024BCD0006)], [Packaging the paper rebuild
    (`qvol`); quantum v2 models; fresh Bitstamp memory and realism
    study; paper-vs-ours comparison; sealed results; IBM hardware
    script],
    [#strong[Vishnunath A Suresh] (2024BCS0315)], [Literature survey and
    future-direction research; design of scoring metrics and statistical
    tests; report and presentation preparation],
    [#strong[Gopi Krish] (2024BCS0054)], [Code integration and review of
    pull requests \#1 to \#12; automated test and style checks;
    LTC/BNB/ADA and LINK/DOT/AVAX multi-coin studies; result plots],
  )]
  , caption: [Team member contributions]
  , kind: table
  )

= References
<references>
+ T. Takaishi, "Quantum Circuit Learning for Volatility Modeling:
  Multifractal Analysis of Realized Volatility Time Series,"
  #emph[Fractal and Fractional], vol.~10, no. 7, p.~442, 2026.
  arXiv:2609.04569.
+ T. Takaishi, "Volatility time series modeling by single-qubit quantum
  circuit learning," arXiv:2512.10584, 2025.
+ K. Mitarai, M. Negoro, M. Kitagawa, K. Fujii, "Quantum circuit
  learning," #emph[Phys. Rev.~A], vol.~98, 032309, 2018.
+ A. Pérez-Salinas et al., "Data re-uploading for a universal quantum
  classifier," #emph[Quantum], vol.~4, p.~226, 2020.
+ M. Schuld, R. Sweke, J. J. Meyer, "Effect of data encoding on the
  expressive power of variational quantum machine-learning models,"
  arXiv:2008.08605, 2021.
+ F. J. Schreiber et al., "Classical surrogates for quantum learning
  models," 2022.
+ J. Bowles, S. Ahmed, M. Schuld, "Better than classical? The subtle art
  of benchmarking quantum machine learning models," arXiv:2403.07059,
  \2024.
+ F. Corsi, "A simple approximate long-memory model of realized
  volatility," #emph[J. Financial Econometrics], vol.~7, no. 2, 2009.
+ J. Gatheral, T. Jaisson, M. Rosenbaum, "Volatility is rough,"
  #emph[Quantitative Finance], vol.~18, no. 6, 2018.
+ J. W. Kantelhardt et al., "Multifractal detrended fluctuation analysis
  of nonstationary time series," #emph[Physica A], vol.~316, 2002.
+ A. J. Patton, "Volatility forecast comparison using imperfect
  volatility proxies," #emph[J. Econometrics], 2011.
+ T. Gneiting, A. E. Raftery, "Strictly proper scoring rules,
  prediction, and estimation," #emph[J. American Statistical
  Association], 2007.
+ F. X. Diebold, R. S. Mariano, "Comparing predictive accuracy,"
  #emph[J. Business & Economic Statistics], 1995.
+ Q. Li et al., "Quantum reservoir computing for realized volatility
  forecasting," 2025.

= Appendices
<appendices>
== A. How to run the code
<a.-how-to-run-the-code>
```
uv sync --all-extras
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run python qvol/experiments/01_reproduce_paper.py
```

== B. Glossary
<b.-glossary>
#figure(
  align(center)[#table(
    columns: (50%, 50%),
    align: (auto,auto,),
    table.header([Term], [Plain meaning],),
    table.hline(),
    [Volatility], [How much the price swings in a day],
    [Realized volatility (RV)], [Sum of squared small price changes
    within a day],
    [HAR], [Classical model using day, week and month averages],
    [Qubit], [Quantum bit; measured as 0 or 1 with some probability],
    [CNOT], [Two-qubit gate that flips the second qubit if the first is
    1],
    [Log loss], [Score for probability forecasts; lower is better],
    [QLIKE], [Standard error score for volatility forecasts; lower is
    better],
    [Seed], [Random starting point for training],
    [Bootstrap interval], [Range showing how much a result could vary by
    chance],
  )]
  , caption: [Glossary of terms]
  , kind: table
  )

== C. Additional figures
<c.-additional-figures>
#figure(image("fig/fig_memory.png", width: 75.0%),
  caption: [
    Effect of memory on test log loss (fresh study).
  ]
)

#figure(image("fig/fig_v2.png", width: 75.0%),
  caption: [
    Quantum v2 comparison.
  ]
)

== D. Repository
<d.-repository>
Full code, written plans and per-study results:
`github.com/moneytosms/qcproj` (folder `doc/`).
