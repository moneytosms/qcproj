#!/usr/bin/env bash
# Rebuild the v2 deck: Typst circuits/formulas, Manim clips (slow, skip with SKIP_CLIPS=1), then the .pptx.
set -euo pipefail
cd "$(dirname "$0")"
for f in paper ours rv logloss hybrid; do typst compile --format png --ppi 300 "circuits/$f.typ" "circuits/$f.png"; done
[[ "${SKIP_CLIPS:-}" == 1 ]] || ./build_clips.sh
[[ -d node_modules ]] || npm install
node build.js
