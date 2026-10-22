#let accent = rgb("155e75")
#let ink = rgb("1b2b3a")
#let pale = rgb("eff6f8")
#let border = rgb("c6d8df")
#let node(title, detail) = block(
  width: 100%,
  fill: pale,
  stroke: 0.7pt + border,
  radius: 3pt,
  inset: 8pt,
)[
  #align(center)[
    #text(weight: "bold", fill: accent)[#title]
    #linebreak()
    #text(size: 8.5pt)[#detail]
  ]
]

#set page(paper: "a4", margin: (x: 16mm, y: 14mm), numbering: "1", number-align: center)
#set text(font: "TeX Gyre Termes", size: 10pt, fill: ink)
#set par(justify: true, leading: 0.55em, spacing: 0.5em)
#set heading(numbering: none)
#show heading.where(level: 1): set text(size: 15pt, weight: "bold", fill: accent)
#show heading.where(level: 2): set text(size: 11pt, weight: "bold", fill: ink)
#show link: set text(fill: accent)
#show figure.caption: set text(size: 8.5pt, fill: ink)

#align(center)[
  #v(2mm)
  #text(size: 21pt, weight: "bold", fill: accent)[Quantum Software Contributions]
  #v(2mm)
  #text(size: 11pt)[IEG 313 · Quantum Computing Assignment]
  #v(3mm)
  *Vishnunath A Suresh*  ·  2024BCS0315  ·  GitHub: #link("https://github.com/vishnunathasuresh")[`@vishnunathasuresh`]
]

#v(5mm)

This report covers two merged open-source contributions: convex-hull optimization in #link("https://github.com/pyRiemann/pyRiemann-qiskit")[pyRiemann-Qiskit] and search-candidate compression in #link("https://github.com/quantum-compiler/quartz")[Quartz]. It also gives the context of the course repository where this assignment is submitted.

== The repositories

#table(
  columns: (1fr, 1.5fr),
  stroke: 0.5pt + border,
  inset: 7pt,
  table.header([*Repository*], [*Purpose and relevance*]),
  [#link("https://github.com/moneytosms/qcproj")[`moneytosms/qcproj`]], [The IEG 313 Quantum Volatility Range Forecaster course project. It studies probabilistic crypto-volatility forecasts with small quantum circuits, exact classical simulation, chronological evaluation, and matched classical baselines. This report is filed here as a separate assignment about my external software contributions.],
  [#link("https://github.com/pyRiemann/pyRiemann-qiskit")[`pyRiemann/pyriemann-qiskit`]], [A Python library joining Qiskit with pyRiemann's Riemannian machine-learning methods for EEG/BCI, including quantum classifiers and a quantum nearest-convex-hull method.],
  [#link("https://github.com/quantum-compiler/quartz")[`quantum-compiler/quartz`]], [A quantum circuit optimizer that searches among functionally equivalent circuits using generated and verified transformations and a cost-based search.],
)

== Problems solved

=== pyRiemann-Qiskit — convex-hull optimizer convergence

#link("https://github.com/pyRiemann/pyRiemann-qiskit/issues/383")[Issue #383] documented failed convex-hull distance cases: the reproduced classical optimizer reached distance near zero, while the single-start `NaiveQAOAOptimizer` was around 0.66 and `QAOACVOptimizer` around 0.74–0.82. The issue identified precision loss from integer discretization and runs settling in poor local minima. The QAOA-CV path also needed an explicit feasibility check for its decoded hull weights.

The follow-up work addressed both existing optimizer behavior and an additional continuous parameterization. The focus was numerical correctness, feasible hull weights, diagnosability, and an opt-in solver choice that left existing defaults intact.

=== Quartz — memory used by queued circuit candidates

#link("https://github.com/quantum-compiler/quartz/issues/150")[Issue #150] described high memory use while searching: each queued `Graph`/`CircuitSeq` retained convenience data that was not needed to rebuild the circuit. The search only needed compact gate/operation identities and their qubit and parameter indices until a candidate was expanded.

The change needed to reduce the queued representation while preserving enough information to reconstruct candidates exactly and continue the same search.

#pagebreak()

= Solutions and validation

== pyRiemann-Qiskit

*PR #468 — #link("https://github.com/pyRiemann/pyRiemann-qiskit/pull/468")[Fix convex hull optimizer convergence].* Integer hull weights are normalized at the configured resolution before objective evaluation. Optional `resolution_bounds` supports comparing resolutions using the original Log-Euclidean distance. Seeded multi-start was added as an opt-in for `NaiveQAOAOptimizer`, preserving one start as the default. The QAOA-CV output is projected onto the simplex so the returned weights are feasible; `decoded_solution_` retains pre-projection marginals for inspection. Exact-grid and regression tests were added.

*PR #469 — #link("https://github.com/pyRiemann/pyRiemann-qiskit/pull/469")[Add simplex-native hull optimizer].* An opt-in `SingleExcitationHullOptimizer` represents hull weights as one-excitation probabilities using exchange-angle gates. It can be selected explicitly in the Log-Euclidean convex-hull routine. In shot mode it ignores invalid outcomes and reports an error when too few valid shots remain. Statevector, decoder, feasibility, and optimization tests cover the new path.

The PR records report 13 passed and 2 skipped for the focused tests on #468; the combined change set passed 765 tests with 2 skipped. PR #469 also records a successful Sphinx build, with 17 warnings. These results support the reported implementation and regression checks, not a claim of quantum advantage.

== Quartz

*PR #231 — #link("https://github.com/quantum-compiler/quartz/pull/231")[Compress queued search candidates].* The implementation adds an opt-in packed representation for both `Graph::optimize` overloads. A queued candidate stores immutable operation and connection arrays; the full graph is rebuilt when that candidate is popped for expansion. Packing preserves operation IDs, gates, qubit and parameter indices, empty adjacency entries, and the special-operation counter. Optional transformation history shares snapshots through parent links. Compression remains disabled by default.

Regression tests exercise packing, reconstruction, search, and history. The PR records a Release build, AddressSanitizer/UndefinedBehaviorSanitizer with leak detection, repository pre-commit checks, and benchmark comparisons for equal work, costs, hashes, and exported QASM. The PR does not publish permanent speed figures, so this report makes no numerical speedup claim.

== Implementation diagrams

#figure(
  grid(
    columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr),
    gutter: 4pt,
    align: center,
    node([Input], [Riemannian covariance features]),
    text(size: 17pt, weight: "bold", fill: accent)[→],
    node([Hull problem], [Log-Euclidean distance with simplex weights]),
    text(size: 17pt, weight: "bold", fill: accent)[→],
    node([Optimizer choices], [Discrete QAOA-CV and continuous one-excitation path]),
    text(size: 17pt, weight: "bold", fill: accent)[→],
    node([Checked output], [Feasible weights, diagnostics, and regression tests]),
  ),
  caption: [pyRiemann-Qiskit convex-hull optimization work in PRs #468 and #469.],
  kind: image,
)

#figure(
  grid(
    columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr),
    gutter: 4pt,
    align: center,
    node([Candidate graph], [Full in-memory graph before queue insertion]),
    text(size: 17pt, weight: "bold", fill: accent)[→],
    node([Pack], [Immutable operation and connection arrays]),
    text(size: 17pt, weight: "bold", fill: accent)[→],
    node([Search queue], [Compact snapshot plus required metadata]),
    text(size: 17pt, weight: "bold", fill: accent)[→],
    node([Expand], [Reconstruct graph when the candidate is popped]),
  ),
  caption: [Quartz's opt-in lossless queue representation in PR #231.],
  kind: image,
)

#pagebreak()
= Merge confirmation — pyRiemann-Qiskit PR #468

#figure(
  image("assets/contributions/pyriemann-pr-468.png", width: 100%, alt: "GitHub pull request page showing pyRiemann-Qiskit PR 468 merged into main"),
  caption: [GitHub shows PR #468 merged into `pyRiemann:main`. #link("https://github.com/pyRiemann/pyRiemann-qiskit/pull/468")[Open the pull request].],
  kind: image,
)

#pagebreak()
= Merge confirmation — pyRiemann-Qiskit PR #469

#figure(
  image("assets/contributions/pyriemann-pr-469.png", width: 100%, alt: "GitHub pull request page showing pyRiemann-Qiskit PR 469 merged into main"),
  caption: [GitHub shows PR #469 merged into `pyRiemann:main`. #link("https://github.com/pyRiemann/pyRiemann-qiskit/pull/469")[Open the pull request].],
  kind: image,
)

#pagebreak()
= Merge confirmation — Quartz PR #231

#figure(
  image("assets/contributions/quartz-pr-231.png", width: 100%, alt: "GitHub pull request page showing Quartz PR 231 merged into main"),
  caption: [GitHub shows PR #231 merged into `quantum-compiler:master`. #link("https://github.com/quantum-compiler/quartz/pull/231")[Open the pull request].],
  kind: image,
)
