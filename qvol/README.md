# Quantum Volatility Range Forecaster

SQC course project, IIIT Kottayam. We improve Takaishi's one-qubit Bitcoin volatility model
([Fractal and Fractional 10(7):442, 2026](https://www.mdpi.com/2504-3110/10/7/442), arXiv 2609.04569) with:

- **B, longer memory:** inputs from yesterday, last 7 days and last 30 days (HAR style)
- **D, a range, not one number:** a 2-qubit circuit whose 4 measurement outcomes are calm / normal / wild / extreme
- **A, trained for realism:** loss = forecast log loss + λ × mismatch of long-run patterns in generated histories

A beginner-friendly explanation of the whole project is in `../Quantum_Volatility_Project_Guide.pdf`; the plan is in `../Quantum Stochastic Volatility SQC Project Plan.pdf` (both at the top of the repo).

## Setup

All commands run from inside this `qvol/` folder.

```bash
pip install -r requirements.txt
python -m pytest -q tests        # 5 tests, about 1 second
```

## Layout

| Path | What it is |
| --- | --- |
| `data/takaishi/` | Bitcoin daily realized volatility and returns (913 days) from the paper's author, GPL-3; see `data/README.md` |
| `src/qvol/gates.py` | RY, RZ, U3, CNOT and Bloch vector as NumPy matrices |
| `src/qvol/data.py` | Loads the data; HAR inputs; time split; volatility levels |
| `src/qvol/paper_model.py` | The paper's 1-qubit model: encoding, training (COBYLA), generation, exact closed form |
| `src/qvol/metrics.py` | Shared scores: log loss, ranked probability score, autocorrelation, tail index, MFDFA h(q) |
| `experiments/01_reproduce_paper.py` | Train the paper's model and compare with real data and the author's own output |
| `experiments/02_closed_form_check.py` | Show φ does nothing and P0 = ½ + ½ n·b on the trained model |
| `experiments/03_plot_phase1.py` | Memory-gap figure |
| `results/` | JSON results and figures |

Run the experiments in order: `python experiments/01_reproduce_paper.py`, then 02, then 03 (about 30 seconds in total).

## Phase 1 results (19 Oct 2026)

**Reproduction.** Our NumPy rebuild, trained on all 913 days, comes close to the author's published generated series on the paper's own measures:

| Measure | Real Bitcoin | Author's generated | Our rebuild |
| --- | --- | --- | --- |
| Hurst exponent h(2) of returns | 0.52 | 0.53 | 0.51 |
| h(2) of volatility increments (roughness) | 0.20 | 0.10 | 0.08 |
| Multifractal width of returns | 0.43 | 0.24 | 0.23 |
| Spread of daily change in log volatility | 0.74 | 1.69 | 1.65 |
| Tail index of returns | 3.7 | 3.0 | 3.7 |
| Mean volatility | 0.028 | 0.010 | 0.007 |
| Memory: correlation of log volatility, 1 / 7 / 30 days | 0.75 / 0.58 / 0.32 | 0.14 / 0.06 / −0.01 | −0.02 / 0.01 / 0.00 |

The paper reports volatility-increment roughness h(2) of about 0.05 to 0.1; we get 0.08. One-step forecast correlation with actual RV is 0.45.

**Memory gap (motivates part B).** Real Bitcoin volatility stays correlated with itself for months, with a weekly rhythm. Both the author's series and our rebuild lose all memory within a few days (`results/fig_memory_gap.png`).

**Closed form (paper audit).** On the trained model, changing φ changes no prediction (difference 0), and

P0 = ½ + ½ n(θ, λ) · b(r, σ²),  n = (−sin θ cos λ, sin θ sin λ, cos θ)

matches the circuit to 3e-16 on all 913 days. The model has 2 working parameters, not 3.

## Open questions

1. **Return formula during generation.** The paper only states the generic rule r = σ ε. The author's generated returns are about 4 times smaller than √v × ε would give. We use r = √v × ε (closer match on most measures); `ret_scale` in `paper_model.generate` lets us test others. Worth emailing the author.
2. **Exact training setup** (data period, restarts, fitted values) is not in the text we could access. Our fitted values: θ = −4.557, φ = 0.360 (no effect), λ = 1.700.
3. **Closest related work:** HQCS (Zhang et al., arXiv 2610.15083) generates VIX windows by sequential circuit sampling. Not a forecaster; cite it.

## Next: Phase 2 (weeks 3 to 4)

1. Add HAR inputs to the 1-qubit model (part B alone) and measure the memory gain.
2. Build the 2-qubit, 4-level circuit (part D), log-loss training, 1 to 4 layers.
3. Write `src/qvol/range_model.py` and `experiments/04_ablation_b_d.py` using the same metrics.
