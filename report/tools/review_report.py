"""Check report structure, cross-references, sentence length, and rendered text bounds.

This supports, but does not replace, visual page review and scientific review.
"""

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "report/main.typ"
PDF = ROOT / "output/pdf/ieg313-project-report.pdf"
QA = ROOT / "report/qa"
source = SOURCE.read_text()
required = [
    "Title page",
    "Abstract",
    "Contents",
    "Introduction",
    "Literature review",
    "Novelty",
    "Methodology / system design",
    "Implementation",
    "Results and discussion",
    "Conclusion and future work",
    "Contributions",
    "References",
    "Appendices",
]
headings = re.findall(r"^= (.+)$", source, re.MULTILINE)
assert headings == required, headings
labels = set(re.findall(r"<((?:eq|tab|fig)-[^>]+)>", source))
refs = set(re.findall(r"@((?:eq|tab|fig)-[\w-]+)", source))
assert labels == refs, {"unreferenced": sorted(labels - refs), "undefined": sorted(refs - labels)}
bib = set(re.findall(r"@\w+\{([\w-]+),", (ROOT / "report/references.bib").read_text()))
cites = set(re.findall(r'(?<![\w"])@([a-z][\w-]+)', source)) - refs
assert cites <= bib, cites - bib
abstract = source.split("= Abstract\n", 1)[1].split("#pagebreak()", 1)[0]
assert not re.search(r"\b(TBD|TODO|placeholder)\b", abstract, re.IGNORECASE)
# Every narrative paragraph occupies one source line. Code, tables, math, and
# declarations are excluded. Long sentences are flagged, never silently passed.
long_sentences = []
in_code = False
for line_no, line in enumerate(source.splitlines(), 1):
    if line.startswith("```"):
        in_code = not in_code
        continue
    if in_code or not line.strip() or line[0] in "#=+[$ )" or line.startswith("  "):
        continue
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line):
        words = re.findall(r"\S+", sentence)
        if len(words) > 35:
            long_sentences.append({"line": line_no, "words": len(words), "sentence": sentence})
# Use Poppler's physical word positions to detect page-edge clipping.
xml = subprocess.check_output(["pdftotext", "-bbox-layout", str(PDF), "-"], text=True)
doc = ET.fromstring(xml)
ns = {"p": "http://www.w3.org/1999/xhtml"}
pages = doc.findall(".//p:page", ns)
outside = []
for page_no, page in enumerate(pages, 1):
    width, height = float(page.attrib["width"]), float(page.attrib["height"])
    for word in page.findall(".//p:word", ns):
        x0, x1 = float(word.attrib["xMin"]), float(word.attrib["xMax"])
        y0, y1 = float(word.attrib["yMin"]), float(word.attrib["yMax"])
        if x0 < 45 or x1 > width - 45 or y0 < 15 or y1 > height - 15:
            outside.append({"page": page_no, "text": word.text, "box": [x0, y0, x1, y1]})
text = subprocess.check_output(["pdftotext", "-raw", str(PDF), "-"], text=True)
assert "�" not in text, "Replacement character in PDF text"
report = {
    "standard": "QVRF-TWS-1.0",
    "required_sections": headings,
    "figures": len([k for k in labels if k.startswith("fig-")]),
    "tables": len([k for k in labels if k.startswith("tab-")]),
    "important_equations": len([k for k in labels if k.startswith("eq-")]),
    "cross_references_resolved": True,
    "bibliographic_keys_resolved": True,
    "abstract_has_no_placeholder_text": True,
    "pages": len(pages),
    "sentences_over_35_words": long_sentences,
    "page_edge_overflows": outside,
    "automated_checks_pass": not long_sentences and not outside,
    "manual_review_required": [
        "scientific interpretation",
        "mathematical layout",
        "diagram truthfulness and label placement",
        "all rendered pages",
    ],
}
(QA / "writing-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
if not report["automated_checks_pass"]:
    raise SystemExit(1)
