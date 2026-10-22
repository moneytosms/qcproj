#import "template.typ": *
#show: conf

#align(center)[
  #v(3cm)
  #text(size: 30pt, weight: "bold", fill: blue)[Can a Qubit Forecast a Storm?]
  #v(0.3cm)
  #text(size: 16pt)[Complete Study Guide for the Quantum Volatility Project]
  #v(0.6cm)
  #text(size: 12pt, fill: luma(35%))[IEG 313 · Team Schrödinger's Cat · prepared for the demo]
  #v(2cm)
]

#block(width: 100%, inset: 14pt, radius: 5pt, fill: blue.lighten(92%))[
  *What this is.* A self-contained guide that assumes you know only: basic maths, plain English, and that a qubit exists. It explains the finance, the crypto, the quantum, the machine learning, the base research paper, everything our team built, every result, and gives you a talk script and exam-style Q&A.

  *How to read it.* Read Part 0 first (10 minutes). Then Parts 1 to 4 teach the background in order. Parts 5 to 7 are the project itself. Part 8 is the demo script. Part 9 is the Q&A bank, a glossary, and a "do not say this" list. Coloured boxes: #text(fill: blue)[*IDEA*] plain-language intuition; #text(fill: teal)[*MATH*] the formula; #text(fill: amber)[*SAY IT LIKE THIS*] a sentence you can speak; #text(fill: red)[*DO NOT CLAIM*] a trap.
]

#v(0.6cm)
#outline(title: [Contents], depth: 2, indent: 1em)

#include "sections/00-start.typ"
#include "sections/01-finance.typ"
#include "sections/02-ml.typ"
#include "sections/03-quantum.typ"
#include "sections/04-paper.typ"
#include "sections/05-ours.typ"
#include "sections/05b-example.typ"
#include "sections/06-results.typ"
#include "sections/07-meaning.typ"
#include "sections/08-script.typ"
#include "sections/09-qa.typ"
#include "sections/10-quiz.typ"
