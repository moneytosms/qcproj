#set document(title: "The Classical Frontier of Quantum Volatility Forecasting", author: "Schrödinger's Cat Project Team")
#set page(paper: "a4", margin: (x: 23mm, top: 22mm, bottom: 22mm), numbering: "1", number-align: center, header: align(right, text(size: 8pt, fill: rgb("64748b"))[Quantum volatility forecasting · Research draft · 22 October 2026]))
#set text(font: "Liberation Serif", size: 10pt, lang: "en")
#set par(justify: true, leading: 0.55em, spacing: 0.8em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => block(above: 1.4em, below: 0.65em, text(size: 13pt, fill: rgb("16324f"), weight: "bold", it))
#show heading.where(level: 2): it => block(above: 1em, below: 0.5em, text(size: 10pt, weight: "bold", it))
#set math.equation(numbering: "(1)")
#show figure.caption: set text(size: 8.5pt)
#show table: set text(size: 8.5pt)
#set table(stroke: none, inset: (x: 5pt, y: 4pt))
#show link: set text(fill: rgb("164b70"))
#let small(body) = text(size: 8.5pt, body)
#let notice(body) = block(width: 100%, fill: rgb("eef3f7"), inset: 10pt, radius: 2pt, body)

#v(0.5em)
#text(size: 8pt, weight: "bold", tracking: 1.2pt, fill: rgb("386484"))[REPRODUCIBLE RESEARCH / QUANTUM MACHINE LEARNING]
#v(0.7em)
#text(size: 23pt, weight: "bold", fill: rgb("16324f"))[The Classical Frontier of\ Quantum Volatility Forecasting]
#v(0.5em)
#text(size: 12pt)[Exact emulation, historical evidence, and a falsifiable route to replication]
#v(0.8em)
#text(weight: "bold")[Schrödinger's Cat Project Team]
\ Department of Computer Science and Engineering, IIIT Kottayam
\ #link("https://github.com/moneytosms/qcproj")[Code and research record: moneytosms/qcproj]
#v(1em)

#notice[
  *Manuscript status.* Research draft. Historical aggregates are identified by source; new development experiments and future confirmation are separate. No hardware result, independent replication, or quantum computational advantage is claimed.
]

*Abstract.* Small quantum circuits can serve as nonlinear volatility forecasters, but improved prediction does not identify a computational quantum advantage. We formalize this distinction for two-qubit, four-class forecasting and audit a sequence of historical cryptocurrency experiments. A direct classical recurrence reproduces every circuit probability using four complex amplitudes, giving an exact reference against which implementation and approximation errors can be separated. In the retained Bitcoin study, multi-horizon memory improves log loss, yet the matched softmax control outperforms the quantum forecaster by 0.0511, with a reported paired 95% block-bootstrap interval of [0.0366, 0.0652]. Later exploratory ensembles narrow the gap without reversing it. The strongest retained single-asset result, calibrated AVAX, reduces log loss from 0.475457 to 0.448466, a 5.68% gain; its three-asset decision rule nevertheless fails, and its variance score worsens. We identify an interval-level discrepancy between that protocol and its results summary. Fifteen new retrospective development runs compare frozen circuit features, residual corrections, and calibrated mixtures across five price series. The largest mixture gain is 0.48% on ETH, and all mixture uncertainty intervals include zero. We also specify a prospective replication design with matched classical features, computational accounting, temporal isolation, and explicit failure criteria. The contribution is an auditable research framework and bounded empirical evidence, not a claim that the current small circuits outperform the classical model class.

= Scientific question and contribution

Forecasting realized volatility requires both persistence and uncertainty. Multi-horizon autoregression supplies a useful classical starting point @corsi2009; parameterized circuits introduce a different family of nonlinear features @mitarai2018. Data re-uploading increases expressivity @perezsalinas2020, but expressivity alone does not imply predictive superiority. Classical surrogate constructions @schreiber2023 and systematic benchmarking @bowles2024 motivate a stronger question: *does a circuit-derived representation add forecast value after information, optimization, calibration, and compute are controlled?*

We separate three claims. A *predictive gain* compares finite fitted candidates on a stated population. A *representation gain* survives matched nonlinear classical controls and ablations. A *computational advantage* requires a task and resource regime where classical computation cannot reproduce the benefit at comparable cost. A two-qubit statevector experiment can investigate the first two; it supplies no evidence for the third. The exact construction below makes the distinction operational.

#pagebreak()
= Forecast definition and exact classical reference

== Information set and loss

Let $r_(t,i)$ denote intraday log return $i$ on date $t$, and let $v_t = sum_i r_(t,i)^2$ be realized variance. Forecasts for date $t$ use observations available through $t-1$. The base information set contains lagged $log v$, its trailing seven- and thirty-day means, and lagged daily return. Later historical v3 experiments add calendar variables. Features are transformed using training statistics only. Training quantiles at 0.30, 0.70, and 0.95 define four fixed classes $y_t in {0,1,2,3}$.

For predicted probabilities $p_(t,k)$, the primary score is
$ cal(L)(p) = -1/N sum_(t=1)^N log p_(t,y_t). $ <loss>
Log loss is strictly proper for the categorical target @gneiting2007. Brier score measures another aspect of distributional accuracy. QLIKE evaluates a *positive variance forecast* rather than a categorical forecast, using $v_t / hat(v)_t - log(v_t / hat(v)_t) - 1$ @patton2011. The mapping from classes to variance representatives must therefore also be frozen. An improvement in log loss does not imply an improvement in QLIKE.

== Circuit family

Write $tilde(x) = (x^T,1)^T$ and use the ordered basis $(00,01,10,11)$. At layer $ell$ and qubit $q$, define two affine angles
$ a_(ell,q) = w_(ell,q,y)^T tilde(x), quad b_(ell,q) = w_(ell,q,z)^T tilde(x). $
The repository's v3 Born implementation applies
$ U_(ell,q) = R_Z(b_(ell,q)) R_Y(a_(ell,q)), quad
  psi_ell = C (U_(ell,0) times.o U_(ell,1)) psi_(ell-1), $ <recurrence>
where $psi_0=(1,0,0,0)^T$ and $C$ swaps the last two amplitudes. The output is $p_k=|psi_(L,k)|^2$. For $d$ inputs and $L$ layers, the circuit has $4L(d+1)$ parameters: 84 for $d=6$, $L=3$. Ten-restart historical ensembles average ten probability vectors, so 84 describes one member, not the total stored ensemble. The v3 source inspected here does not contain a classical HAR skip connection.

== Proposition: exact finite classical emulation

*Proposition 1.* For fixed two-qubit width, @recurrence and its Born probabilities are computable by a classical algorithm in $O(L(d+1))$ arithmetic operations per observation, with four complex state amplitudes apart from stored parameters. This holds for any finite weights and inputs in exact arithmetic; floating-point implementations introduce ordinary rounding error.

*Proof.* A single-qubit rotation is a $2 times 2$ matrix whose entries are sines, cosines, or complex exponentials of an affine scalar. Each of the two affine evaluations per qubit costs $O(d+1)$. The tensor-product update acts on four amplitudes and costs a constant amount of arithmetic; CNOT is a fixed permutation. Repeating $L$ layers and taking four squared magnitudes gives the stated bound. Averaging $R$ restart predictions multiplies cost by $R$. No measurement sampling is required. #h(0.3em)$square$

This is an implementation identity at fixed width, not an assertion that arbitrary large quantum circuits are easy to simulate. It also does not promise that a different classical parameterization is equally easy to optimize. It means the *same learned predictor* already has an efficient classical implementation. A learned sine-feature surrogate may be useful, but is not an exact reference unless equality is established. The one-qubit predecessor similarly admits a Bloch-vector expression $p_0=(1+bold(n) dot bold(b))/2$; its terminal phase angle drops out of the observed probability in the repository implementation.

#pagebreak()
= Historical evidence and its limits

The following numbers are transcribed from retained result summaries, not recomputed training runs for this manuscript. Twenty training seeds quantify optimizer variability; they are not twenty independent market histories. Daily paired losses, where available, are the correct resampling unit. Historical studies use overlapping calendar periods, so they cannot be counted as independent confirmations.

#figure(table(
  columns: (2.1fr, 1fr, 1fr, 2.1fr), align: (left, right, right, left),
  table.hline(stroke: 0.8pt),
  [*Comparison*], [*Quantum*], [*Control*], [*Interpretation*],
  table.hline(stroke: 0.4pt),
  [Bitcoin, base memory], [0.5695], [0.5184], [Matched softmax wins],
  [Bitcoin, v3 ensemble], [0.5145], [0.4962], [Post-hoc; softmax wins],
  [LTC, v3], [0.613210], [0.596593], [Exploratory; softmax wins],
  [BNB, v3], [0.391824], [0.366583], [Exploratory; softmax wins],
  [ADA, v3], [0.760215], [0.769787], [1.24% gain; interval includes zero],
  [LINK, calibrated v3], [0.577113], [0.591609], [2.45% gain; panel fails],
  [DOT, calibrated v3], [0.638703], [0.642954], [0.66% gain; panel fails],
  [AVAX, calibrated v3], [0.448466], [0.475457], [5.68% gain; panel fails],
  table.hline(stroke: 0.8pt),
), caption: [Historical test log loss; lower is better. Controls are same-input softmax variants. Rows differ in model, calibration, asset, and selection history and do not constitute one homogeneous benchmark. Sources: H1–H4 in the evidence ledger.]) <history>

== What the Bitcoin study establishes

The retained fresh Bitcoin record gives 2,192 training dates, 731 validation dates, and 657 test dates, ending 19 October 2026. For the base quantum model, the paired quantum-minus-softmax mean loss is 0.051085, with the retained 30-day bootstrap interval [0.036603, 0.065222]. The memory contrast is approximately −0.050870, with interval [−0.071099, −0.030581]. These support the narrower conclusions that memory helps this candidate and that its matched softmax control is better on this period. The 657 test targets contain class counts (490,142,25,0); no extreme-class observation appears. The study cannot establish detection performance for that class.

The v3 mean is 0.5145 versus 0.4962 for softmax and 0.5042 for the small network. Its improvement over earlier quantum versions is a development result on an already inspected test period. Moreover, the v3 note records a post-seal source edit, described as removing an unused import: artifact hashes remain valid, but the old source seal no longer equals the current file hash. Exact historical reruns require the sealed source revision.

== What the AVAX result establishes

The calibrated three-asset study fits one temperature per model and seed on 2023 validation data and evaluates 2025–2026 forecasts. AVAX's 5.68% relative gain is the strongest retained individual-asset result. The displayed 7- and 30-day intervals against softmax are [−0.04814,−0.01039] and [−0.04826,−0.01078]. However, the results label these *95% intervals*, whereas the frozen protocol calls for *97.5% intervals*. We retain their stated level and make no protocol-compliant significance claim from this summary. LINK and DOT miss the 5% threshold in any case, so the conjunctive panel decision fails. Quantum QLIKE is worse than both controls on all three assets. Individual-seed files and optimizer termination metadata are absent from the committed evidence summarized here. This is a promising exploratory categorical forecast result, with material reproducibility limits.

#pagebreak()
= Development progression: v4, v5, and v6

The measured development experiments test whether nonlinear circuit features are useful after simpler structure is accounted for. These are development candidates, not successive independent confirmations. Model selection, calibration, and audit dates must be recorded separately. A 2024 audit on data used in earlier research remains a retrospective development check even when the current script does not fit on it.

== v4: frozen features and a fitted probability head

For frozen circuit features $phi_Q(x)$, let $h_Q(x)=(x^T, phi_Q(x)^T,1)^T$ and fit a regularized multinomial head with one reference class:
$ p^(4)(x) = "softmax"((A h_Q(x),0)). $
The design separates circuit feature quality from end-to-end variational optimization. Matched controls replace $phi_Q$ with sine and hyperbolic-tangent random features, with identical input information and head-fitting procedure. The dimensions, scales, random seeds, ridge grid, and all candidate counts must be disclosed. A gain over linear softmax alone is insufficient evidence for a circuit-specific representation benefit.

== v5: correction to a classical forecast

Let $p_H(x)$ be the categorical probabilities from a training-fitted transformed-HAR empirical-residual model. Fit a correction with its log probabilities as an offset:
$ p^(5)(x) = "softmax"(log p_H(x) + (A h_Q(x),0)). $
The correction isolates incremental value beyond persistence. The same correction must be fitted with matched classical features. It must be possible to recover the baseline by setting the correction to zero; strong regularization provides a check against unnecessary nonlinear complexity. Parameter count alone does not equalize the cost of feature construction or hyperparameter search.

== v6: a validation-fitted probability mixture

Let $p_C$ be the selected classical forecast. The implemented mixture is
$ p^(6) = (1-alpha) p_C + alpha (beta p^(4) + (1-beta) p^(5)). $
Choose from $alpha in {0,0.25,0.5,0.75,1}$ and $beta in {0,0.5,1}$ on 2023 calibration data. All 15 grid combinations, including duplicated endpoints, are considered. The v5 family includes the uncorrected HAR fallback; hence a nominal nonzero mixture weight need not imply circuit contribution. No equivalently searched classical-only mixture is included in this development run, so any mixture gain cannot be attributed specifically to quantum features.

== Measured development results

The implementation uses five shared inputs: four squashed HAR/return features and a centered weekend indicator, excluding the Monday flag. Three frozen depth-two `WeekendBorn` maps supply twelve probability features. Sine and tanh controls have the same feature width; frozen parameter counts differ (60 circuit versus 72 classical). Nonlinear heads have 54 fitted reference-logit coefficients; linear heads have 18. Ridge is selected from {0.001,0.01}. The transformed-HAR baseline uses squashed inputs and is not canonical log-HAR. Each run fits 16 heads plus that baseline. These fixed feature maps differ from the trained v3 affine circuit in Section 2.

Three run seeds (42,43,44) each use maps at seed, seed+1, and seed+2; the resulting map sets overlap. These seeds are dependent sensitivity checks, not independent replications. All heads train through 2022; candidate/ridge/mixture selection uses 2023; the 366 days of 2024 form an already-exposed development audit. No 2025–2026 rows enter this script.

#pagebreak()
== Development audit results

#figure(table(
  columns: (1.4fr, 1fr, 1fr, 1fr, 1fr, 1fr),
  align: (left, right, right, right, right, right),
  table.hline(stroke: 0.8pt),
  [*Series*], [*Classical*], [*v4*], [*v5*], [*v6*], [*v6 gain*],
  table.hline(stroke: 0.4pt),
  [BTC, Bitstamp], [0.738965], [0.737905], [0.743591], [0.738784], [+0.024%],
  [BTC, Binance], [0.742156], [0.741634], [0.745168], [0.742900], [−0.100%],
  [ETH, Binance], [0.666774], [0.686087], [0.665522], [0.663591], [+0.477%],
  [SOL, Binance], [0.605712], [0.618633], [0.618002], [0.606636], [−0.153%],
  [DOGE, Binance], [0.754946], [0.782063], [0.759456], [0.753313], [+0.216%],
  table.hline(stroke: 0.8pt),
), caption: [Measured 2024 development log loss, averaged over seeds 42–44. Positive gain means lower loss than the 2023-selected classical comparator. These are five price series but four distinct assets; the two BTC series are not independent markets.]) <development>

All 240 fitted heads met the saved success and gradient criteria, alongside 15 baseline fits. Scores are computed from saved daily predictions; the scorecard records hashes of each run's summary and prediction file. Classical control selection is based on calibration performance, not the best retrospectively observed 2024 score. No candidate reaches a 5% improvement in this development audit.

#figure(table(
  columns: (1.25fr, 0.8fr, 1.7fr, 1.7fr),
  align: (left, right, right, right),
  table.hline(stroke: 0.8pt),
  [*Series*], [*v6 − C*], [*7-day 95% interval*], [*30-day 95% interval*],
  table.hline(stroke: 0.4pt),
  [BTC, Bitstamp], [−0.000181], [[−0.005527, 0.004580]], [[−0.004591, 0.003948]],
  [BTC, Binance], [+0.000744], [[−0.004599, 0.005765]], [[−0.003385, 0.004923]],
  [ETH, Binance], [−0.003183], [[−0.010474, 0.002605]], [[−0.009935, 0.002457]],
  [SOL, Binance], [+0.000924], [[−0.006134, 0.008328]], [[−0.006854, 0.008755]],
  [DOGE, Binance], [−0.001633], [[−0.009588, 0.006658]], [[−0.009996, 0.007048]],
  table.hline(stroke: 0.8pt),
), caption: [Paired circular date-bootstrap intervals from seed-averaged daily losses; 4,000 replicates, bootstrap seed 20261022. All intervals include zero. They are unadjusted descriptive intervals on exposed development data, not confirmatory tests.])

v4 improves log loss by only 0.14% and 0.07% on the two BTC series, loses 2.13–3.59% on the other three, and worsens QLIKE on every series. v5 improves mean log loss only on ETH (0.19%). v6's largest improvement is ETH (0.48%); QLIKE nevertheless worsens on ETH from 0.260984 to 0.264005. DOGE is the only series where v6 improves QLIKE, from 0.342181 to 0.336047. These small, uncertain differences do not establish a robust predictive gain.

*Run provenance.* Local artifact `results/frontier-20261022/scorecard.json` aggregates fifteen `summary.json` and `predictions.csv` pairs. Per-run summaries retain data/source hashes, transforms, frozen parameters, fitted coefficients, optimization status, candidate decisions, and software versions. Generated artifacts are ignored by Git; retained documentation must accompany them for independent review. No new future-period outcome is measured.


== Diagnostic outcomes that change the interpretation

If the exact classical circuit evaluator disagrees, stop and fix the implementation. If a random classical feature map matches the circuit, report a generic nonlinear-feature benefit. If only a mixture improves, report an ensemble benefit and its circuit weight. If improvements vanish outside calibration, report selection overfit. If log loss improves while QLIKE worsens, preserve both results; a single favorable metric cannot justify an all-metric claim. If a single seed wins while the multi-seed mean does not, do not select that seed after inspecting the audit.

#pagebreak()
= Proposed confirmatory protocol

*Status: proposed, not executed or externally registered.* Before collecting a new untouched evaluation block, archive a dated protocol, code revision, full candidate list, and a manifest of all previously inspected dates and assets. Historical retrospective audits cannot be repaired by renaming them test sets. An embargo after the last observed target and a future-only evaluation window provide a defensible separation from development.

== Freeze the decision before outcomes

Choose one primary target, one score, one circuit-derived candidate, and a finite fixed set of classical controls. Fix data source, return convention, daily aggregation, missing-day treatment, forecast issuance time, bin edges, transforms, training span, retraining schedule, calibration span, seeds, compute budget, and evaluation horizon. Any rolling retraining may use only information preceding the forecast timestamp. A prespecified minimum number of observed tail events is necessary for a separate tail-performance claim; inadequate tail support yields an inconclusive result.

Controls should include a HAR-input linear probability model, a small nonlinear network, matched sine/tanh feature heads, and the exact classical circuit implementation. The last control is an identity check and a resource comparator, not an independent forecasting competitor. If an actual hardware claim is made, include shot counts, noise calibration, compilation, queue/execution time, failures, and the corresponding classical simulation cost. No hardware experiment has been performed here.

== Estimand, resampling, and success criteria

For each competitor $c$, define the seed-averaged daily paired loss difference
$ d_(t,c) = 1/S sum_(s=1)^S (ell_(Q,s,t) - ell_(c,s,t)), quad
  Delta_c = 1/N sum_(t=1)^N d_(t,c). $
Resample contiguous date blocks jointly across models and, where dates align, across markets; never treat every seed-date pair as independent. Prespecify block lengths and the primary interval construction. Preserve 7- and 30-day sensitivity analyses for continuity with historical work. If multiple model or asset claims are made, specify the family and simultaneous error control before evaluation. Ordinary marginal intervals do not silently become familywise intervals. Formal forecast-comparison methods provide another sensitivity analysis @diebold1995, subject to their assumptions.

For the proposed protocol in the companion research plan, require at least a 5% reduction in pooled primary loss against the development-selected classical champion, with a prespecified paired 95% interval entirely below zero. Pool by averaging each date's loss over the fixed asset panel, then averaging dates. Freeze 2% maximum relative deterioration in RPS and QLIKE as guardrails, report every locked control and each market separately, and apply the registered multiplicity procedure if additional comparisons are confirmatory. This is a pooled predictive-gain claim; it does not require or establish superiority on every market. Independent future AVAX replication can be a distinct, narrower claim; it must not be substituted for a failed pooled claim after results arrive.

== Resource fairness and abort conditions

Record wall time, hardware, thread count, model evaluations, parameters, restarts, early stops, all failed fits, and preprocessing/compilation overhead. Share information and tuning opportunities across model families; equal parameter counts are not sufficient. Prespecify behavior for missing data and optimization failures. Do not silently drop failures or add restarts after seeing outcomes. Stop scoring if a seal fails, targets leak into preprocessing, any forecast uses later information, or probabilities are invalid. Failed checks are evidence about the experiment, not permission to repair a scored test through further model selection.

#notice[
  *Publication gate.* A complete paper needs a frozen release, auditable per-date predictions and fit statuses, an independent temporal evaluation, power/precision planning, reconciled interval levels, and review of every numerical claim. A compiled manuscript is a reviewable artifact; it is not evidence that these scientific requirements have been met.
]

#pagebreak()
= Reproducibility, limitations, and evidence ledger

The principal limitation is historical selection. Much of the best-performing model design was developed after related test results were visible; overlapping markets also share shocks. A sealed run protects a particular evaluation from later modification but does not erase prior design selection. The present manuscript audits local records and source logic; it does not independently reconstruct every historical dataset, refit every seed, or validate every original seal. Generated experiment files remain outside version control under the repository policy.

Small circuit width is another substantive limit. Proposition 1 rules out inferring computational advantage from these experiments. Circuit-specific inductive bias remains an empirical possibility; proving it requires controls at least as carefully tuned as the quantum candidates. Increasing qubit count alone does not establish computational hardness for the actual forecasting task. Hardware noise, shot error, and calibration drift are unmeasured here.

#figure(table(
  columns: (0.35fr, 2.2fr, 2.5fr),
  table.hline(stroke: 0.8pt),
  [*ID*], [*Retained source*], [*Scope and qualification*],
  table.hline(stroke: 0.4pt),
  [H1], [#small[`doc/fresh-study-results/results.json`;
    `paper/results.json`]], [Fresh Bitcoin splits, class support, base-model contrasts; rounded presentation values checked against detailed summary where available.],
  [H2], [#small[`doc/v3-study.md`]], [Post-hoc Bitcoin v3 means; source seal mismatch disclosed in original record.],
  [H3], [#small[`doc/multimarket-v3-results.md`]], [LTC/BNB/ADA means, intervals, failed panel. Cross-asset exploratory evidence.],
  [H4], [#small[`doc/calibrated-v3-results.md`;
    `doc/calibrated-v3-protocol.md`]], [LINK/DOT/AVAX means, failed panel, QLIKE tradeoff, 95% versus 97.5% discrepancy.],
  [M1], [#small[`src/qcvol_v3/models.py`;
    `src/qcvol/quantum.py`]], [Gate order, affine angles, parameter counts, exact finite-state recurrence and one-qubit twin.],
  table.hline(stroke: 0.8pt),
), caption: [Evidence ledger. Paths are relative to the linked project repository. These are internal research records, not independently peer-reviewed datasets.])

*Availability.* The companion audit, `doc/frontier-evidence-audit.md`, records the numerical and provenance distinctions behind this draft. The source manuscript is `paper/frontier.typ`; it does not replace the earlier manuscript or source PDFs. Rebuilding uses Typst with the adjacent bibliography. The research repository and dated source revision should accompany any circulation of a numerical result.

*Conclusion.* The historical evidence supports useful modeling progress and one exploratory AVAX log-loss gain. It does not establish a transferable quantum advantage. The most defensible next contribution is a rigorous study of whether circuit-derived nonlinear features improve probabilistic volatility forecasts beyond strong classical features, with exact classical emulation as a mandatory reference. The answer may be negative; the proposed protocol is designed to make that outcome as reportable as a positive one.

#bibliography("frontier-refs.bib", title: "References", style: "ieee")
