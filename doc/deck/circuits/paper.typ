#import "style.typ": *
#show: setup
#let opts = (wire: .8pt + ink, column-spacing: 12pt)
#stack(dir: ttb, spacing: 16pt,
  quantum-circuit(..opts,
    lstick($|0〉$),
    g($R_Y (arcsin r_t)$, c: class), g($R_Z (arccos r_t^2)$, c: class),
    g($R_Y (arcsin(2 sigma_t^2 - 1))$, c: class), g($R_Z (arccos sigma_t^4)$, c: class), 1,
  ),
  pad(left: 160pt, quantum-circuit(..opts,
    1, g($U_3 (theta, phi, lambda)$, c: quant), meter(fill: card), 1,
    rstick($P(0) = hat(sigma)^2_(t+1)$),
  )),
)
