#import "style.typ": *
#show: setup
#quantum-circuit(
  wire: .8pt + ink, row-spacing: 18pt, column-spacing: 10pt,
  lstick($|0〉$), g($R_Y (w_1 x_"day")$, c: class), g($R_Z (w_2 x_"week")$, c: class), g($R_Y (w_5)$, c: quant), g($R_Z (w_6)$, c: quant), ctrl(1), meter(fill: card), [\ ],
  lstick($|0〉$), g($R_Y (w_3 x_"month")$, c: class), g($R_Z (w_4 x_"return")$, c: class), g($R_Y (w_7)$, c: quant), g($R_Z (w_8)$, c: quant), targ(), meter(fill: card),
  gategroup(2, 5, x: 1, y: 0, stroke: (paint: muted, dash: "dashed"), label: (content: text(fill: muted, size: 12pt)[one layer, repeated $L$ times (inputs re-enter each layer)], pos: bottom)),
)
