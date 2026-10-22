#let blue = rgb("#2b5fa5")
#let teal = rgb("#1a8f84")
#let amber = rgb("#b5790a")
#let red = rgb("#c4452d")
#let ink = rgb("#1d2430")

#let box(label, title, color, fill, body) = block(
  width: 100%, inset: (x: 11pt, y: 9pt), radius: 4pt, breakable: false,
  fill: fill, stroke: (left: 3pt + color),
)[
  #text(weight: "bold", fill: color, size: 9.5pt)[#label#if title != none [ · #title]] \
  #v(2pt)
  #body
]
#let idea(title: none, body) = box("IDEA", title, blue, blue.lighten(92%), body)
#let math-box(title: none, body) = box("MATH", title, teal, teal.lighten(92%), body)
#let say(title: none, body) = box("SAY IT LIKE THIS", title, amber, amber.lighten(90%), body)
#let warn(title: none, body) = box("DO NOT CLAIM / WATCH OUT", title, red, red.lighten(92%), body)
#let note(title: none, body) = box("REMEMBER", title, ink, luma(95%), body)

#let term(name, body) = block(spacing: 0.6em)[*#name.* #body]

#let conf(doc) = {
  set document(title: "Quantum Volatility Project: Complete Study Guide", author: "Study guide")
  set page(paper: "a4", margin: (x: 2.2cm, top: 2.2cm, bottom: 2.2cm),
    numbering: "1",
    header: context {
      if counter(page).get().first() > 1 {
        set text(size: 8.5pt, fill: luma(40%))
        [Quantum Volatility Project: Study Guide #h(1fr) #counter(page).display()]
        line(length: 100%, stroke: 0.4pt + luma(80%))
      }
    })
  set text(font: "New Computer Modern", size: 10.5pt, lang: "en")
  set par(justify: true, leading: 0.62em, spacing: 0.95em)
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    v(0.5em)
    block(width: 100%, inset: (bottom: 6pt), stroke: (bottom: 1.5pt + blue))[
      #text(size: 22pt, weight: "bold", fill: blue)[#it.body]
    ]
    v(0.8em)
  }
  show heading.where(level: 2): it => { v(0.9em); text(size: 14pt, weight: "bold", fill: ink, it.body); v(0.2em) }
  show heading.where(level: 3): it => { v(0.5em); text(size: 11.5pt, weight: "bold", fill: teal, it.body); v(0.1em) }
  show raw: set text(font: "DejaVu Sans Mono", size: 8.5pt)
  show figure: set block(breakable: false, spacing: 1em)
  show figure.caption: set text(size: 9pt, fill: luma(35%))
  set table(stroke: 0.4pt + luma(70%), inset: 6pt)
  show table.cell.where(y: 0): set text(weight: "bold")
  set list(indent: 0.6em)
  doc
}

#let fig(path, caption, width: 90%) = figure(image(path, width: width), caption: caption)
