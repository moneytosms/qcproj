#import "../template.typ": *

= Part 0. Start Here

== The project in 60 seconds

*The question.* Bitcoin's price sometimes barely moves and sometimes lurches wildly. How wild a day is, is called *volatility*. Volatility has memory (wild periods cluster), so it can be forecast. Can a tiny quantum circuit do that forecasting?

*The starting point.* A 2026 paper by T. Takaishi trained a *one-qubit* circuit (simulated on a normal computer) to forecast Bitcoin volatility from yesterday only, and said the circuit's imagined price histories look realistic.

*What we did.*
+ *Rebuilt* the paper's model from scratch and checked it matches. Found a quirk: one of its three tunable dials (the angle $phi$) never affects the output.
+ *Upgraded* it: more memory (yesterday, last week, last month), *two* qubits so it outputs probabilities for four volatility levels (calm, normal, wild, extreme), and a strict time-ordered train / validation / test procedure.
+ *Raced* it fairly against classical models that get exactly the same inputs, with pass/fail rules written before looking at the test results, then repeated on nine more coins.

*What we found.* Our upgrade roughly *halves* the error of the paper's model (log loss 0.5695 vs 1.196). But the gain comes from better design (memory and probability outputs), not from anything quantum: plain classical models with the same inputs match or beat our quantum models almost everywhere. *We claim no quantum advantage.* Everything ran on a simulator.

#say(title: "The one-sentence verdict")[
  "We rebuilt a one-qubit quantum volatility model, improved it by giving it memory and probabilistic outputs, and tested it fairly: the improvement is real, but classical models with the same information do just as well, so we find no quantum advantage."
]

== Numbers you should know cold

#table(columns: (1.5fr, 2.5fr),
  [Fact], [Value],
  [Base paper], [T. Takaishi, _Fractal and Fractional_ 10(7):442, 2026. One qubit. Forecasts Bitcoin volatility; tests realism with multifractal analysis.],
  [Paper's data], [913 days (Aug 2020 to Feb 2023), already rescaled; split 529 / 177 / 177 days in our study],
  [Our fresh Bitcoin data], [Bitstamp exchange, Dec 2016 to 19 Oct 2026. Train 2,192 days, validation 731, test 657 (test = 1 Jan 2025 onward)],
  [Ten coins], [BTC plus ETH, SOL, DOGE, LTC, BNB, ADA, LINK, DOT, AVAX (Binance, 5-minute prices)],
  [Four levels], [calm / normal / wild / extreme = cut at the 30th, 70th, 95th percentile of training log RV],
  [Our circuit], [2 qubits, a CNOT between them, 3 repeated layers, 24 trainable numbers (v1)],
  [Headline score (log loss, lower = better)], [Paper model *1.196*, our v1 quantum *0.5695*, v2 0.529, v3 0.5145, best classical (v2 inputs) *0.4962*],
  [Effect of memory], [Adding week + month inputs improved log loss by 0.051 (95% interval −0.071 to −0.030)],
  [Fairness], [20 random seeds per model; time-ordered splits; classical "twins"; block bootstrap intervals; 5% pre-registered rule],
  [Verdict], [No quantum advantage claimed; no group of coins passed the 5% rule; simulator only; 109 automated tests],
)

== Map of the 15-minute talk

The deck has 43 slides in seven sections. Each maps to a chapter of this guide:

#table(columns: (auto, 1fr, auto),
  [Deck section], [Message], [Study here],
  [1 Markets have weather (slides 3-9)], [What volatility is, how it is measured, why it is forecastable], [Part 1],
  [2 A one-qubit idea (10-15)], [The base paper and its open questions], [Parts 3, 4],
  [3 First, rebuild it (16-19)], [We reproduced it; the $phi$ dial does nothing], [Part 4],
  [4 Our upgrade (20-25)], [Memory, four levels on two qubits, quantum as second opinion], [Part 5],
  [5 A fair race (26-29)], [Locked test set, classical rivals, log loss], [Parts 2, 5],
  [6 What happened (30-37)], [Halved error; classical still wins; ten coins], [Part 6],
  [7 What we learned (38-43)], [Honest verdict, limits, team], [Part 7],
)

== Suggested study plan for tonight

#table(columns: (auto, 1fr),
  [Time], [Do],
  [20 min], [Part 0, then Part 1 (finance, RV, clustering, HAR). Be able to say "RV = sum of squared 5-minute returns" aloud.],
  [30 min], [Part 3 (qubit, Bloch sphere, rotations, CNOT) and Part 4 (the paper, the dead $phi$ dial). This is the hardest material; the figures do most of the work.],
  [30 min], [Part 2 (log loss, splits, seeds, bootstrap) and Part 5 plus 5B (our model, one day end to end).],
  [20 min], [Part 6 (results tables) then memorise the numbers box above.],
  [20 min], [Part 8 (script), say it out loud once; then Part 12 self-test.],
)
