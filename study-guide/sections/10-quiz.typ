#import "../template.typ": *

= Part 12. Self-Test (answers below)

Cover the answers and say each one aloud in one or two sentences.

+ What is realized volatility and how is it computed?
+ Why do we take the logarithm of RV?
+ What does 'volatility clusters' mean and what number shows it?
+ Name the three HAR look-back windows.
+ What is the probability of measuring 0 when the Bloch arrow points at the equator?
+ What does $R_Z$ do to the arrow? Why does it not change P(0) by itself?
+ Why does $phi$ not matter in the paper's model?
+ Why does our model use two qubits?
+ What does the CNOT do?
+ How many parameters does the v1 circuit have and why?
+ Define log loss and give the penalty for giving 10% to what happened.
+ What are the train, validation and test sets for?
+ Why can the test set be used only once?
+ What is a seed and why 20?
+ What does a bootstrap interval that excludes zero tell you?
+ What was the headline comparison against the original paper?
+ Did quantum beat the classical twin? What was the evidence?
+ Why did you set a 5% rule before testing?
+ Why does AVAX not count as a win?
+ Name three limitations.

#pagebreak()
== Answers

+ Sum of squared 5-minute log returns in a day; bigger means a wilder day.
+ Raw RV is skewed with huge outliers; log makes it bell-like and manageable.
+ Wild days follow wild days; autocorrelation of log RV 0.75 at lag 1, 0.64 at lag 7, 0.37 at lag 30.
+ Yesterday, last 7 days, last 30 days.
+ 50%.
+ Spins it around the vertical axis (height unchanged); measurement odds depend only on height, so alone it is invisible.
+ $U_3 = R_Z (phi) R_Y (theta) R_Z (lambda)$ and the last $R_Z$ does not alter the odds; closed form $P(0) = 1/2 + 1/2 n dot b$ has no $phi$.
+ Two qubits have four outcomes, one per volatility level.
+ Flips qubit 2 when qubit 1 is 1; entangles the qubits.
+ 24: per layer 2 qubits × (2 data weights + 2 free angles) = 8, times 3 layers.
+ $-1/N sum ln p_"true"$; $-ln 0.1 = 2.30$.
+ Fit parameters; choose settings; final unbiased exam.
+ Otherwise you tune to it and the score no longer measures new data.
+ A random starting point; averaging 20 evens out training luck (not market luck).
+ The gap is unlikely to be luck.
+ Log loss 1.196 vs 0.5695; QLIKE 0.840 vs 0.504; realism 215.3 vs 33.5.
+ No: classical softmax 0.5184 vs 0.5695 (v1); 0.4962 vs 0.5145 (v3); no group of coins passed the 5% rule.
+ So we could not pick a flattering threshold after seeing results.
+ The rule needed every coin in the group; LINK and DOT failed; on QLIKE quantum was worse on all three.
+ Simulator only; reused test days for v2/v3; 20 seeds on one market is not 20 markets (also: no extreme days in test).
