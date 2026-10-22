#import "../template.typ": *

= Part 3. Quantum Computing You Need, From Zero

You already know a qubit exists. This part builds everything the project uses: amplitudes, measurement, the Bloch sphere, rotation gates, two qubits, CNOT, and how a circuit becomes a trainable model. Nothing else from quantum computing is needed.

== A qubit as two numbers (amplitudes)

A classical bit is 0 or 1. A qubit's state is a pair of numbers $(alpha, beta)$ called *amplitudes*:

$ |psi chevron.r = alpha |0 chevron.r + beta |1 chevron.r, quad |alpha|^2 + |beta|^2 = 1 $

$|0 chevron.r$ and $|1 chevron.r$ are the two basic states (like bit 0 and bit 1). Amplitudes can be negative or even complex numbers (they carry a *phase*). Complex numbers are just numbers with a rotation angle attached; you will not need arithmetic with them beyond the ideas below.

=== Measurement and the Born rule

When you *measure* a qubit you always get a plain 0 or 1, never "both". The chances are fixed by the amplitudes (the *Born rule*):

$ P(0) = |alpha|^2, quad P(1) = |beta|^2 $

*Example.* $alpha = sqrt(0.8), beta = sqrt(0.2)$: 80% chance of 0, 20% chance of 1. Superposition means "before measuring, the state holds *both amplitudes at once*", but what you read out is random with those probabilities. In our project the "forecast" is exactly such a probability, which we compute *exactly* by squaring amplitudes (no repeated sampling needed in a simulator).

#note[Squared size, not the amplitude itself, is the probability. Two different amplitude signs (+ or −) give the same probability on their own but can *interfere* (add up or cancel) later in a circuit. Interference is what quantum circuits exploit.]

== The Bloch sphere: a picture of one qubit

Every single-qubit state can be drawn as an *arrow from the centre of a ball to its surface* (the *Bloch sphere*). Two angles fix the arrow: the polar angle $theta$ measured down from the north pole, and the azimuth $phi$ (longitude) going around the vertical axis:

$ |psi chevron.r = cos(theta/2) |0 chevron.r + e^(i phi) sin(theta/2) |1 chevron.r $

#fig("/fig/bloch_basic.png", [The Bloch sphere. North pole = |0⟩, south pole = |1⟩. The red arrow is the state; θ (amber) is the angle from the north pole, φ (blue) the angle around the vertical axis.], width: 48%)

*How to read it:*
- *North pole* = state $|0 chevron.r$: measuring gives 0 with certainty. *South pole* = $|1 chevron.r$: always 1.
- *Equator*: a 50/50 mix. States on the equator differ only in phase.
- *Latitude decides the probability.* If $z$ is the arrow's height (from −1 at the south pole to +1 at the north):

$ P(0) = (1 + z)/2 = cos^2(theta/2) $

#fig("/fig/p0_vs_angle.png", [Probability of reading 0 as the arrow tilts from the north pole to the south pole.], width: 62%)

- *Longitude (φ) is invisible to a standard measurement.* Measuring 0/1 only cares about height. Spinning the arrow around the vertical axis changes nothing about $P(0)$. This one sentence is the key to the "φ does nothing" discovery in Part 4.

*The globe analogy used on slide 18:* spinning the globe around its axis moves cities east-west, but nobody's latitude changes; $P(0)$ only depends on latitude.

== Gates are rotations of the arrow

A *gate* changes a qubit's state. Every single-qubit gate is a rotation of the Bloch arrow.

#fig("/fig/rotations.png", [Left: R_Y tilts the arrow along a meridian, changing its height (so the probabilities). Right: R_Z spins it around the vertical axis, keeping its height.], width: 95%)

#table(columns: (auto, 1.3fr, 2.2fr),
  [Gate], [Rotates around], [Effect on measurement odds],
  [$R_Y (a)$], [the y-axis (tilts the arrow in the x-z plane)], [Changes P(0). Starting from $|0 chevron.r$: $R_Y (a)|0 chevron.r = cos(a/2)|0 chevron.r + sin(a/2)|1 chevron.r$],
  [$R_Z (a)$], [the vertical z-axis (spins around)], [*Alone* changes nothing visible (changes only phase). It matters when it is *followed by another rotation* that turns phase into height.],
  [$U_3 (theta,phi,lambda)$], [a general rotation], [Any single-qubit state can be reached. Built from three rotations; the three angles are the "three dials" in the paper.],
)

*Matrices (so you can answer "what is the maths"):* a gate is a 2×2 matrix acting on $(alpha, beta)$:

$ R_Y (a) = mat(cos(a/2), -sin(a/2); sin(a/2), cos(a/2)), quad R_Z (a) = mat(e^(-i a/2), 0; 0, e^(i a/2)) $

*Check (verified numerically):* $R_Y (pi/2)|0 chevron.r = (|0 chevron.r + |1 chevron.r)/sqrt(2)$, i.e. the arrow tipped onto the equator, 50/50.

#idea(title: "Why rotations help a data model")[
  An angle can carry a data value. Feeding a number $x$ into a gate $R_Y (x)$ means "tilt the arrow by $x$". The probabilities then depend on $x$ through $cos$ and $sin$, a smooth, wavy function. Stacking several rotations with trainable angles produces a flexible wavy function of the inputs. That is the whole idea of a *quantum circuit as a machine-learning model*.
]

== Two qubits

Two qubits have *four* basis states, written $|q_0 q_1 chevron.r$: $|00 chevron.r, |01 chevron.r, |10 chevron.r, |11 chevron.r$. A two-qubit state has four amplitudes:

$ |psi chevron.r = a_(00)|00 chevron.r + a_(01)|01 chevron.r + a_(10)|10 chevron.r + a_(11)|11 chevron.r $

Measuring both gives one of four outcomes with probabilities $|a_(00)|^2, |a_(01)|^2, |a_(10)|^2, |a_(11)|^2$ that add to 1. *That is exactly a probability forecast over four volatility levels*, which is why our upgrade uses two qubits: outcome 00 = calm, 01 = normal, 10 = wild, 11 = extreme. With $n$ qubits you get $2^n$ outcomes, so the number of amplitudes doubles with each qubit (why simulation becomes hard around 40-50 qubits, but two qubits is trivial).

=== CNOT and entanglement

*CNOT* ("controlled NOT") is a two-qubit gate: if the first (control) qubit is 1, flip the second (target); otherwise leave it.

#table(columns: 5, align: center,
  [Input], [00], [01], [10], [11],
  [Output], [00], [01], [11], [10],
)
As a matrix it swaps the last two amplitudes: $|10 chevron.r <-> |11 chevron.r$.

*Entanglement example (verified).* Put qubit 0 on the equator ($R_Y (pi/2)$), giving $(|00 chevron.r + |10 chevron.r)/sqrt(2)$. Apply CNOT: you get $(|00 chevron.r + |11 chevron.r)/sqrt(2)$. Now the qubits are *entangled*: you cannot describe either alone; measuring one tells you the other (both 0 or both 1, 50/50). In our model the CNOT's job is to let the two qubits share information so the four outcomes are not independent.

== Circuits as trainable models: quantum circuit learning

A *quantum circuit* is a sequence of gates drawn left to right, one wire per qubit, ending in measurement.

*Quantum circuit learning* (Mitarai et al., 2018), also called a *variational quantum circuit* or *parameterised quantum circuit*:
+ *Encode* data into rotation angles (data gates).
+ Apply gates with *trainable* angles.
+ Measure; the output probability is the prediction.
+ A *classical* optimiser changes the trainable angles to reduce the loss; the quantum part is just evaluated (simulated).

It is the quantum cousin of a small neural network: angles are weights, rotations are the nonlinear layer.

*Data re-uploading* (Pérez-Salinas et al., 2020): feed the same data into the circuit *several times* in successive layers, with different trainable multipliers. One upload gives only simple sinusoids of the input; re-uploading makes the model far more expressive. Our circuit repeats a layer 1 to 4 times (3 best).

*Expressivity warning.* A circuit with few uploads can only represent sums of sine and cosine waves of the inputs (a "Fourier series", Schuld et al. 2021). This is why, outside the range of the training data, such a model can *bend back* in odd ways (the 'calm-market extrapolation' issue found in v2).

== Simulators, hardware and noise

- A *simulator* computes the amplitudes with ordinary linear algebra on a normal computer. For 1-2 qubits it is instant and *exact* (no sampling error, no noise). Everything in our project ran this way, in NumPy (plus JAX for gradients).
- *Real quantum hardware* (e.g. IBM) is noisy and measures by repeating the circuit thousands of times ("shots"). We wrote a script for IBM hardware but *did not run it*.
- *Quantum advantage* means doing something faster or better than the best classical method. A 2-qubit circuit can be simulated by a laptop in microseconds, so no speed advantage is possible here, and in accuracy we found no advantage either.

#warn[Do not say "we ran it on a quantum computer". Say "an exact classical simulator of a quantum circuit".]
