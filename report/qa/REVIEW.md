# Report verification: 20 October 2026

## Scientific review

Implementation baseline: `fc8d6c8`. The report does not change model code,
experiment configurations, source datasets, or the supplied reference PDFs.

- Confirmed fresh-study results against both tracked JSON and local saved evaluation.
- Verified 30 sealed training-artifact hashes and data/configuration hashes.
- Replayed all 20 quantum HAR D and 20 softmax HAR D daily-loss arrays independently;
  maximum discrepancy was 0 in this environment.
- Recomputed all 26 paired 7/30-day bootstrap rows and all model mean NLL values.
- Checked paper follow-up QLIKE values against the machine-readable summary.
- Checked v2/v3 design and parameter counts against code, including 60 parameters
  without calendar, 84 with calendar, and ten members in the v3 restart ensemble.
- Disclosed exposed-period Bitcoin follow-ups, v3's recorded source-hash mismatch,
  optimizer eligibility failures, unequal capacity/effort, zero extreme Bitstamp
  test days, empirical generator support, and the four-moment realism boundary.
- Retained earlier negative realism results and rejected calendar/readout/ensemble
  candidates. No proposal-only experiment is reported as implemented.
- Distinguished categorical regime probabilities from numerical intervals, variance
  from volatility, seed variability from date uncertainty, and simulation from hardware.
- Contribution attribution uses repository evidence; Gopi's tasks remain unverified.

Current repository verification: **152 passed, 2 skipped**. Skips:
`tests/test_finance_comparison.py:181` lacks ignored historical study artifacts;
`qvol/tests/test_reproduction.py:82` lacks optional MFDFA. Existing saved audit
results are attributed to the recorded study, not represented as rerun here.

## Technical writing and template review

`writing-checks.json` records all 13 sections, 10 figures, 12 tables, and 11
numbered equations. All important figure/table/equation labels are referenced.
Bibliographic keys resolve. Narrative paragraphs have no flagged sentences over
35 words. The abstract has no placeholder language and states actual results.
QVRF-TWS-1.0 principles are applied without claiming formal ASD/ISO/NeurIPS
certification. Automated checks are scoped to source prose and PDF word bounds;
manual review covers captions, interpretation, equations, and figure readability.

## Rendered-page review

Compiled successfully with Typst 0.15.1 and bundled TeX Gyre fonts, without compiler
warnings. Rendered all 16 A4 pages with Poppler at 1600 pixels on the long edge.
Inspected every page in contact sheets and enlarged the mathematical/diagram pages.

- Pages 1–4: title identity, official logo, instructors, abstract, generated contents,
  short figure/table lists, and abbreviation typography checked.
- Pages 5–8: two-column hierarchy, architecture node bounds, arrow endpoints,
  actual gate order and CNOT direction, formula grouping, equation numbering,
  workflow labels, and training/test boundaries checked.
- Pages 9–12: data-derived chart labels, error-bar meaning, interval identities,
  forecast/realism units, score tables, and post-hoc/replication distinctions checked.
- Pages 13–16: contribution records, numerical citations, line-wrapped build
  commands, evidence index, complete scorecard, and review table checked.

Corrected label overflow in the architecture diagram, enlarged generation nodes,
separated the Bloch-twin vector onto its own equation line, and corrected Typst
subscript grouping before the final inspection. No unresolved page-edge overflow,
missing reference, clipped caption, broken equation, or font substitution was found.

The university's contribution section is present for every member. Specific tasks
for Gopi cannot be validated without additional team information. The CSE department
and 2026–2027 academic year remain editable assumptions, documented in report/README.md.
