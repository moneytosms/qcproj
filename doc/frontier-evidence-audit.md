# Frontier manuscript evidence audit

Audit date: 22 October 2026. Scope: retained paper summaries, fresh-study aggregate,
v3 source, multi-market and calibrated protocols/results. This is a provenance audit,
not a retraining or independent replication. Existing manuscript/source PDFs preserved.

## Supported historical statements

| Claim | Retained evidence | Qualification |
| --- | --- | --- |
| Base quantum Bitcoin LL .5695 vs matched softmax .5184 | `paper/results.json`; `doc/fresh-study-results/results.json` | Quantum loses; 20 seeds are optimizer replicates, not independent histories |
| Quantum minus softmax .05108537, interval [.03660320,.06522185] | Same fresh aggregate, 30-day paired bootstrap | Interval stated 95%; positive favors classical |
| Memory gain -.05086958, interval [-.07109926,-.03058105] | `paper/results.json` | Specific historical model and period |
| Bitcoin v3 .5145 vs softmax .4962 / network .5042 | `doc/v3-study.md` | Post-hoc reused dates; v3 does not win |
| LTC .613210 vs .596593; BNB .391824 vs .366583; ADA .760215 vs .769787 | `doc/multimarket-v3-results.md` | Exploratory; all miss 5% rule; ADA intervals include zero |
| Calibrated AVAX .448466 vs softmax .475457, +5.68% | `doc/calibrated-v3-results.md` | Strongest single-asset retained primary-metric gain; not transferable panel gain |
| LINK +2.45%, DOT +.66%, calibrated panel fails | Same calibrated results | Quantum QLIKE worse than both controls on all three assets |

Fresh BTC support: 2,192 train / 731 validation / 657 test dates. Test classes
490 / 142 / 25 / 0. No extreme-class test events, hence no tail detection conclusion.

## Material discrepancies and missing provenance

1. Calibrated protocol requires **97.5%** intervals; retained results label displayed
   intervals **95%**. Do not claim the significance component of the protocol passed
   from that summary. The three-asset gain threshold fails regardless.
2. `paper/main.typ` conflates circuit variants, including a HAR skip and RY-only
   multi-coin description. `src/qcvol_v3/models.py` inspected here uses affine
   `RZ @ RY` per qubit, CNOT, and Born readout, with no HAR skip in that module.
   Frontier manuscript states the inspected v3 family explicitly.
3. v3 source has 4 L (d+1) parameters per circuit: 84 at depth 3 and six inputs.
   Ten-restart ensembles store ten such parameter vectors. Reporting only 84 without
   identifying the ensemble understates total stored model size/compute.
4. v3 record discloses post-seal removal of unused code, so source hash no longer
   matches. Exact reruns require the original sealed revision; current files alone
   do not validate that historical seal.
5. Calibrated retained record omits individual seed artifacts and reports missing
   optimizer convergence/iteration metadata. Aggregate scores do not repair this.
6. Cross-asset studies reuse calendar dates and were informed by prior outcomes.
   Frozen per-run artifacts do not make design choices independent of past results.

## Exact classical emulation argument

For each layer, evaluate four affine angles, apply two 2x2 local gates to a
four-amplitude state, permute CNOT indices, and square magnitudes. This is exactly
the circuit function in exact arithmetic, O(L(d+1)) per row at two-qubit width.
Ensembling R restarts multiplies this by R. This directly follows the inspected
source; it is not a hardness statement about growing-width circuits, nor a claim
that alternative classical parameterizations have identical optimization geometry.

## Bibliography and output

Frontier bibliography reuses established entries from `paper/refs.bib`.
Primary records additionally checked: Bowles et al. arXiv:2403.07059;
Schreiber et al. arXiv:2206.11740 / PRL 131,100803;
Pérez-Salinas et al. Quantum 4,226 (publisher record).
The manuscript avoids relying on unverified future-dated source-paper metadata.

## Manuscript validation

- `typst compile --root . paper/frontier.typ output/pdf/quantum-volatility-frontier.pdf`
  succeeds with Typst 0.15.1 and no warnings.
- The initial six-page draft was rendered and visually inspected in a contact
  sheet. The completed seven-page tagged A4 PDF adds measured development results;
  its results page was rendered and inspected with no clipping or overlap.
- Extracted text checks confirm core AVAX values, interval discrepancy, parameter
  count, bibliography, and final measured ETH value 0.663591; no replacement glyphs.
- Memory and quantum-minus-softmax intervals independently checked against the
  `intervals` entries with `block=30` in the fresh-study aggregate.

The final manuscript includes 15 completed v4/v5/v6 runs, 240 eligible readout
fits and the complete five-series development table. Saved per-date losses were
independently recomputed by `scripts/summarize_frontier_study.py`, including
source/data/configuration checks. See `doc/frontier-results.md` for hashes and
reproduction commands. All v6 descriptive intervals cross zero. This evidence
cannot be promoted to independent confirmation.
