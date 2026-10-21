#!/usr/bin/env bash
# Render Manim clips and convert them to looping GIFs (GIFs autoplay in PowerPoint and LibreOffice).
set -euo pipefail
cd "$(dirname "$0")"
OUT=media/clips
mkdir -p "$OUT"
SCENES=("$@")
[[ ${#SCENES[@]} -gt 0 ]] || SCENES=(VolatilityLevels PaperQubit PhiSpin OurForecast HybridNudge SealedTest ResultsRace)
for s in "${SCENES[@]}"; do
  uvx --python 3.12 --from manim manim -r 1280,720 --frame_rate 20 --media_dir media/manim scenes.py "$s"
  ffmpeg -y -loglevel error -i "media/manim/videos/scenes/720p20/$s.mp4" \
    -vf "split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
    "$OUT/$s.gif"
done
# Stills: an illustrative calm/wild day, and the final frame of the Bloch clip.
uvx --python 3.12 --from manim manim -s -r 1920,1080 --media_dir media/manim scenes.py CalmVsWild
cp media/manim/images/scenes/CalmVsWild_ManimCE_*.png "$OUT/CalmVsWild.png"
ffmpeg -y -loglevel error -sseof -0.1 -i media/manim/videos/scenes/720p20/PaperQubit.mp4 -frames:v 1 "$OUT/PaperQubit.png"
