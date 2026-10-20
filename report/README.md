# IEG 313 project report

The 16-page Typst report covers the implementation at `fc8d6c8`. It follows all
13 sections of the supplied university template. Its abstract reports completed
experiments and their measured outcomes. It uses `charged-ieee:0.1.4` as its
primary foundation, with a separate academic cover and front matter, a two-column
research body, and one-column supporting appendices.

## Build

From the repository root, after installing the locked Python environment:

```sh
uv sync --locked --extra dev --extra plots --python 3.12
uv run python report/tools/build_evidence.py
typst compile --font-path report/fonts --root . report/main.typ output/pdf/ieg313-project-report.pdf
uv run python report/tools/review_report.py
```

Typst 0.15.1 was used for verification. The source pins charged-ieee 0.1.4,
CeTZ 0.5.2, Quill 0.8.0, and Lilaq 0.6.0. Packages download on the first build.
Bundled TeX Gyre fonts avoid template font substitution. Run the compile command
with `--font-path report/fonts`. The final PDF is a local build artifact under
`output/pdf/`; it is not committed. Prebuilt figure assets are committed so the
report can compile without running Python. Evidence replay uses the existing
tracked fresh-study fits and saved evaluation, not retraining.

## Source and evidence boundaries

- `main.typ`, `metadata.typ`, `diagrams.typ`, and `references.bib` are editable.
- `assets/*.svg` are reproducible vector plots of real saved results or data.
- Architecture and workflow diagrams use CeTZ. Quantum circuits use Quill.
  The paired interval plot uses Lilaq directly with `assets/contrasts.json`.
- `tools/build_evidence.py` checks all 30 sealed training artifacts, independently
  rebuilds quantum/softmax daily losses, and recomputes 26 bootstrap rows.
- `tools/review_report.py` checks the 13-section order, reference coverage,
  bibliography keys, prose sentences above 35 words, and PDF word bounds.
- `qa/` contains review evidence. Automated checks supplement manual scientific
  and rendered-page review; they do not certify formal standards compliance.
- `reference/` preserves the supplied university template and team proposal
  unchanged. Proposal statements do not override tested implementation facts.

The contribution table follows explicit credits and Git authorship. Gopi Krish's
specific tasks are not recorded in the inspected repository and were not supplied.
The report states that evidence limit rather than inventing a responsibility.
Department and academic year use the CSE / 2026–2027 interpretation for the current
course report; these can be edited centrally in `metadata.typ` if needed. Instructor
names and all five student/register-number pairs follow user-supplied material.

## Asset provenance

The institutional logo is the official image from
<https://www.iiitkottayam.ac.in/data/images/main/logo.jpg>, retrieved 20 October 2026.
It is used for academic institutional identification.

Unmodified TeX Gyre Termes (regular, bold, italic, bold italic) and Cursor regular
were retrieved from CTAN `fonts/tex-gyre/opentype/`. They are distributed under the
GUST Font License; see `fonts/GUST-FONT-LICENSE.txt` and
<https://ctan.org/pkg/tex-gyre>. Plot data retain the source repository's provenance
and upstream licensing conditions. No additional market datasets were acquired for
this report.
