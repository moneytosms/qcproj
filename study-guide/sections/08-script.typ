#import "../template.typ": *

= Part 8. The Demo: Slide-by-Slide Script

About 15 minutes at roughly 20 seconds per content slide. Each entry: *what the slide shows*, *what to say*, and a *backup fact* in case you are asked.

== Section 1: Markets have weather (slides 3 to 9)

#term("Slide 1-2: Title and agenda")[Say: "Can a qubit forecast a storm? We rebuilt a quantum model of market volatility, improved it, and tested it fairly against classical methods." Agenda has seven parts.]
#term("Slide 4: Prices shake")[Two days can end at the same price yet feel different. That restlessness is volatility. _Backup:_ plot in Part 1 (calm vs wild).]
#term("Slide 5: Measuring a shake")[288 five-minute slices; take each move, square, add: realized volatility. Like counting bumps on a road. _Backup:_ formula $"RV" = sum r^2$; worked example 0.00085.]
#term("Slide 6: Ten years of Bitcoin")[Real Bitstamp data, Dec 2016 to Oct 2026, calm and stormy eras. _Backup:_ 3,610 days.]
#term("Slide 7: Four kinds of weather")[Calm, normal, wild, extreme from the 30/70/95 percentiles of old data only (about 3, 4, 2.5, 0.5 in ten). _Backup:_ test period was 75% calm.]
#term("Slide 8: Storms cluster")[Volatility has memory; HAR (Corsi 2009) blends yesterday, week, month. It is the bar to beat. _Backup:_ autocorrelation 0.75 / 0.64 / 0.37.]
#term("Slide 9: Why care")[Risk management, option pricing, crypto is wilder. "Could a quantum computer be a good forecaster?"]

== Section 2: A one-qubit idea (slides 10 to 15)

#term("Slide 11: The idea in one picture")[A qubit is an arrow in a sphere (Bloch sphere). Yesterday's move and volatility *turn the arrow*; one learned turn follows; the chance of reading 0 is the forecast. _Backup:_ Part 3 and Part 4 formulas.]
#term("Slide 12: Animation")[Each turn is one gate; the bar on the right is the forecast.]
#term("Slide 13: As a circuit")[Amber gates read data (angles from return and volatility), the teal gate has three adjustable angles; output can be fed back to generate a whole history.]
#term("Slide 14: What the paper found")[Generated prices wander like real ones, generated volatility is rough like real markets, measured by multifractal analysis (MFDFA). Paper concludes the circuit produces realistic data.]
#term("Slide 15: Open questions")[Memory? Uncertainty? Does looking real mean forecasting well? Does it beat a classical model on unseen days?]

== Section 3: Rebuild (slides 16 to 19)

#term("Slide 17: Rebuild matches")[Rewrote from scratch on the author's data: fits history, realistic prices, rough volatility. _Backup:_ MSE 0.00205, correlation 0.449; not every digit replicated.]
#term("Slide 18: The dead dial")[Gate has three dials θ, φ, λ; φ never changes the forecast. Globe analogy: spinning around the axis changes longitude, not latitude. *This is our original finding in the rebuild.* _Backup:_ $U_3 = R_Z R_Y R_Z$, the last $R_Z$ is invisible to a 0/1 measurement.]
#term("Slide 19: Animation")[Turning φ swings the arrow around the red circle; height and forecast stay put.]

== Section 4: Our upgrade (slides 20 to 25)

#term("Slide 21: Three changes")[Memory (yesterday, week, month); say how sure (probabilities of four levels); judge on forecasting (unseen days vs classical models with same inputs).]
#term("Slide 22: Four weather types on two qubits")[Two qubits give four outcomes 00, 01, 10, 11 = calm, normal, wild, extreme: "60% calm, 30% normal, 8% wild, 2% extreme".]
#term("Slide 23: Pipeline")[Last month to tomorrow's forecast (illustrative percentages).]
#term("Slide 24: Inside the circuit")[Amber = data gates, teal = learned, a link (CNOT) lets qubits cooperate, block repeats (re-uploading); three repeats worked best. _Backup:_ 24 parameters.]
#term("Slide 25: Quantum as a second opinion")[Classical model plus a circuit correction; with the dial at zero it is exactly the classical model, so improvements belong to the circuit.]

== Section 5: A fair race (slides 26 to 29)

#term("Slide 27: Final exam locked")[Rules written first, train and tune, seal, then open test once. _Backup:_ SHA-256 sealing; time-ordered split.]
#term("Slide 28: Opponents")[Statistical (softmax), small neural network, HAR, GARCH, "usual mix". Same data, same effort, 20 seeds.]
#term("Slide 29: Log loss")[Forecaster analogy: 90% sun but it pours costs more than 50%. Lower is better; rewards confident and right. _Backup:_ penalty $-ln p$: 0.105 / 0.693 / 2.30 / 4.61.]

== Section 6: What happened (slides 30 to 37)

#term("Slide 31: The race")[Bars of average penalty; shorter is better.]
#term("Slide 32: Good news")[About half the error of the paper's model (0.5695 vs 1.196); more realistic paths too. Because of design (memory, honest uncertainty), mostly not the qubits.]
#term("Slide 33: Classical still wins")[Re-running on thousands of reshuffled test periods (block bootstrap), gap stayed on the classical side in 95%: genuine.]
#term("Slide 34: Paper's own data")[All classical models ahead of the quantum one (0.529 to 0.582 vs 0.692).]
#term("Slide 35: Real-looking vs forecasting well")[Trade-off: fresh data forecasts worse, paths better; paper's data both worse.]
#term("Slide 36: Kept improving")[v1 0.5695, v2 0.529, v3 0.5145; classical 0.4962 stays just ahead. Scored on days we had seen: a hint, not proof.]
#term("Slide 37: Ten coins")[BTC, ETH neck and neck; SOL, DOGE, ADA slightly ahead within noise; LTC, BNB behind; LINK, DOT not passing; AVAX clearly ahead but alone. Rule set in advance: 5% on every coin in a group. No group passed.]

== Section 7: What we learned (slides 38 to 43)

#term("Slide 39: Three takeaways")[(1) The paper holds up, with a twist (dead φ). (2) Good design matters most: memory and honest uncertainty roughly halved the error. (3) No quantum advantage yet.]
#term("Slide 40: Why not")[Two qubits is tiny; same information gives same answers; advantage needs hard problems.]
#term("Slide 41: Limits and next")[Simulator only; reused test days; 20 runs is not 20 markets; no extreme days in test. Next: IBM hardware, stronger tests, quantum reservoirs, a brand-new test period.]
#term("Slide 42-43: Team and thanks")[Credit each member's contribution; invite questions; repo `github.com/moneytosms/qcproj`.]

== A 90-second emergency version

"Volatility is how wildly a price swings and it clusters, so it can be forecast. A recent paper used a one-qubit circuit to do it. We rebuilt it, found one of its three dials is dead, then upgraded it with memory and four-level probability outputs on two qubits, which roughly halved the error. We then tested fairly, against classical models with identical inputs, on data kept sealed, and on ten coins. The classical models did as well or better, so we claim no quantum advantage, only a carefully tested negative result."
