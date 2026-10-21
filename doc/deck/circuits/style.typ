#import "@preview/quill:0.7.2": *
#let ink = rgb("#ECECEC")
#let muted = rgb("#8C8C93")
#let quant = rgb("#2DD4BF")
#let class = rgb("#F5B544")
#let card = rgb("#151517")
#let g(body, c: ink) = gate(body, fill: card, stroke: .8pt + c)
#let setup(body) = {
  set page(width: auto, height: auto, margin: 10pt, fill: none)
  set text(fill: ink, size: 15pt, font: "Liberation Sans")
  body
}
