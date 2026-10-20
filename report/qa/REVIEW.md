# Report verification: 20 October 2026

## Scientific review

Implementation baseline: `0aeab94`. The report does not change model code,
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
- The user requested a balanced allocation of development, research, validation,
  and report work across all five members. The contribution table records that
  allocation without rewriting Git authorship or inventing verified completion.
- Integrated current upstream main at `0aeab94` after discovering newly merged
  studies. Checked the six later v3 aggregate score rows and their gain arithmetic.
  These panels lack committed raw data/per-seed artifacts, so no independent
  seed replay is claimed for them.
- Found and disclosed that both later v3 protocols require 97.5% intervals, while
  the evaluation implementations compute 95% intervals. AVAX's 5.68% mean NLL gain
  is retained as an exploratory primary-metric signal; three-asset gates failed.
- Current fresh-study source seal does not fully match: fresh_runner.py adds the
  bootstrap_confidence field and two calendar modules were added after sealing.
  Training artifact hashes and independent numerical replays still match.

Current repository verification: **154 passed, 2 skipped**. Skips:
`tests/test_finance_comparison.py:181` lacks ignored historical study artifacts;
`qvol/tests/test_reproduction.py:82` lacks optional MFDFA. Existing saved audit
results are attributed to the recorded study, not represented as rerun here.

## Technical writing and template review

`writing-checks.json` records all 13 sections, 10 figures, 13 tables, and 11
numbered equations. All important figure/table/equation labels are referenced.
Bibliographic keys resolve. Narrative paragraphs have no flagged sentences over
35 words. The abstract has no placeholder language and states actual results.
QVRF-TWS-1.0 principles are applied without claiming formal ASD/ISO/NeurIPS
certification. Automated checks are scoped to source prose and PDF word bounds;
manual review covers captions, interpretation, equations, and figure readability.

## Rendered-page review

Compiled successfully with Typst 0.15.1 and bundled TeX Gyre fonts, without compiler
warnings. Rendered all 17 A4 pages with Poppler at 1600 pixels on the long edge.
Inspected every page in contact sheets and enlarged the mathematical/diagram pages.

- Pages 1–4: title identity, official logo, instructors, abstract, generated contents,
  short figure/table lists, and abbreviation typography checked.
- Pages 5–8: two-column hierarchy, architecture node bounds, arrow endpoints,
  actual gate order and CNOT direction, formula grouping, equation numbering,
  workflow labels, and training/test boundaries checked.
- Pages 9–12: data-derived chart labels, error-bar meaning, interval identities,
  forecast/realism units, score tables, and post-hoc/replication distinctions checked.
- Pages 13–17: latest panel limitations, balanced contribution allocation, numerical citations, and line-wrapped build
  commands, evidence index, complete scorecard, and review table checked.

Corrected label overflow in the architecture diagram, enlarged generation nodes,
separated the Bloch-twin vector onto its own equation line, and corrected Typst
subscript grouping before the final inspection. No unresolved page-edge overflow,
missing reference, clipped caption, broken equation, or font substitution was found.

The university's contribution section is present for every member, with substantial
responsibilities assigned to all five under the user's allocation directive. The CSE department
and 2026–2027 academic year remain editable assumptions, documented in report/README.md.

## Contribution wording revision

Replaced document-production tasks and assignment commentary with concise research
and technical responsibilities for each member. The section covers quantum model
development, classical evaluation, market-data replication, model forecasting methodology and
generalization, and Born-model/realism experiments. Shared work concerns interpretation
and methodological limitations. Original implementation credits remain unchanged.
