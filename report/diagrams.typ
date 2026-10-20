#import "@preview/cetz:0.5.2" as cetz
#import "@preview/quill:0.8.0" as quill
#import "@preview/lilaq:0.6.0" as lq
#let ink = rgb("182a3c")
#let blue = rgb("235b86")
#let teal = rgb("16847d")
#let diagram-text(body) = {
  set text(size:9pt,fill:ink)
  set par(justify:false,leading:.25em,spacing:0pt)
  body
}
#let architecture() = cetz.canvas({
  import cetz.draw: *
  let node(x,y,w,h,body,fill:rgb("f2f6f9")) = {
    rect((x - w / 2,y - h / 2),(x + w / 2,y + h / 2),fill:fill,stroke:0.65pt+blue,radius:.12)
    content((x,y), diagram-text(block(width:(w - .2)*1cm,align(center,body))))
  }
  let arrow(a,b) = line(a,b,stroke:0.8pt+blue,mark:(end:">"))
  node(2.1,0,4.1,1.9,[*Data preprocessing*\ `data.py`, `fresh_study.py`\ Past-only; train-fitted])
  node(7.7,0,5.8,1.9,[*Model families*\ `quantum.py`, `fresh_models.py`\ `classical.py`, `finance_baselines.py`])
  node(13.8,0,4.6,1.9,[*Training and selection*\ `fresh_study.py`, `fresh_runner.py`\ Validation selects depth and λ])
  arrow((4.15,0),(4.8,0));arrow((10.6,0),(11.5,0))
  node(2.1,-2.9,4.1,1.9,[*Observed daily series*\ `data/*.csv` and provenance\ Bitstamp / Binance archives])
  arrow((2.1,-1.95),(2.1,-.95))
  node(7.7,-2.9,5.8,1.9,[*Recursive generation and metrics*\ `generation.py`, `metrics.py`\ Empirical-bin sampling; path diagnostics])
  node(13.8,-2.9,4.6,1.9,[*Sealed artifacts and evaluation*\ `results/fresh-study/`\ Hash checks → held-out scores])
  arrow((13.8,-.95),(13.8,-1.95));arrow((11.5,-2.9),(10.6,-2.9))
  arrow((7.7,-.95),(7.7,-1.95))
})
#let workflow() = cetz.canvas({
  import cetz.draw: *
  let node(y,body,fill:rgb("f2f6f9")) = {
    rect((-3.65,y - .45),(3.65,y + .45),fill:fill,stroke:.65pt+blue,radius:.1)
    content((0,y),diagram-text(block(width:7cm,align(center,body))))
  }
  for (i,t) in ([Build 30-day histories; split by target date], [Fit scaler, thresholds and pools on training only], [Develop on seeds 900–901; select on validation], [Fit seeds 0–19 with frozen choices], [Seal parameters, selections, data and source hashes], [Verify seal; score test once; save daily losses]).enumerate() {
    node(-i*1.3,t)
    if i < 5 {line((0,-i*1.3 - .45),(0,-i*1.3 - .85),mark:(end:">"),stroke:.7pt+blue)}
  }
})
#let generation-diagram() = cetz.canvas({
  import cetz.draw: *
  let node(x,y,t) = {
    rect((x - 1.75,y - .65),(x + 1.75,y + .65),fill:rgb("f2f6f9"),stroke:.65pt+teal,radius:.1)
    content((x,y),diagram-text(block(width:3.3cm,align(center,t))))
  }
  node(0,0,[30-day log-RV\ and return history])
  node(4.5,0,[Standardize inputs;\ compute probabilities])
  node(9,0,[Sample regime $k$;\ sample $y$ from pool $k$])
  node(13.5,0,[Generate $r=exp(y/2) ε$;\ append to history])
  for x in (1.75,6.25,10.75) {line((x,0),(x + 1,0),mark:(end:">"),stroke:.7pt+teal)}
  line((13.5,-.65),(13.5,-1.35),(0,-1.35),(0,-.65),mark:(end:">"),stroke:.7pt+teal)
})
#let born-circuit() = {
  import quill: *
  quantum-circuit(
    lstick($q_0: |0〉$), $R_y (w_0 x_d)$, $R_z (w_1 x_w)$, $R_y (w_4)$, $R_z (w_5)$, ctrl(1), meter(), [\ ],
    lstick($q_1: |0〉$), $R_y (w_2 x_m)$, $R_z (w_3 x_r)$, $R_y (w_6)$, $R_z (w_7)$, targ(), meter(),
  )
}
#let paper-circuit() = {
  import quill: *
  quantum-circuit(
    lstick($|0〉$), $R_y (a_r)$, $R_z (b_r)$, $R_y (a_v)$, $R_z (b_v)$, $U_3 (θ,φ,λ)$, meter(),
  )
}
#let contrasts() = {
  let rows = json("assets/contrasts.json")
  lq.diagram(width:100%,height:48mm,xlabel:[Paired log-loss difference (nats/day)],ylabel:[Contrast],
    xlim:(-.10,.10),ylim:(.5,3.5),
    ..rows.enumerate().map(((i,r)) => lq.plot((r.lower,r.upper),(i+1,i+1),color:blue,mark:none)),
    lq.plot(rows.map(r=>r.mean_difference),(1,2,3),stroke:none,mark:"o",color:teal),
    lq.plot((0,0),(.5,3.5),stroke:(paint:ink,dash:"dashed"),mark:none),
  )
}
