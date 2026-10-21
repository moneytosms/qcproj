#!/usr/bin/env bash
# Render Manim clips (1080p30) and poster frames into doc/deck/media/.
set -euo pipefail
cd "$(dirname "$0")"
OUT=media/clips
mkdir -p "$OUT"
for s in VolatilityLevels PaperQubit OurForecast SealedTest; do
  uvx --python 3.12 --from manim manim -r 1920,1080 --frame_rate 30 --media_dir media/manim scenes.py "$s"
  cp "media/manim/videos/scenes/1080p30/$s.mp4" "$OUT/$s.mp4"
  ffmpeg -y -loglevel error -sseof -0.1 -i "$OUT/$s.mp4" -frames:v 1 "$OUT/$s.png"
done
