#!/bin/bash
# Render one frame range of a project as a video segment, for splitting a render across cloud sessions.
#   tools/render_segment.sh projects/<name> FIRST LAST [WORKERS]
# Builds projects/<name>/scene.blend via projects/<name>/build.sh if missing, renders FIRST..LAST
# (resumable), and writes projects/<name>/segments/seg_FIRST_LAST.mp4 (near-lossless, a few MB).
# Commit + push that one file; the final edit concatenates segments with ffmpeg's concat demuxer.
set -euo pipefail
P=${1%/}; FS=$2; FE=$3; W=${4:-3}; FPS=${FPS:-24}
PY=/home/user/blender-shorts/.venv/bin/python
[ -f "$P/scene.blend" ] || bash "$P/build.sh"
OUT="$P/frames"; mkdir -p "$OUT" "$P/segments"
# split the range across W local workers (~3.5 GB RAM each)
n=$((FE - FS + 1)); step=$(( (n + W - 1) / W ))
for ((a = FS; a <= FE; a += step)); do
  b=$((a + step - 1)); ((b > FE)) && b=$FE
  FS=$a FE=$b OUT="$OUT/f_" $PY tools/bl.py run tools/render_range.py --blend "$P/scene.blend" > "$OUT/log_$a.txt" 2>&1 &
done
wait
find "$OUT" -name 'f_*.png' -size 0 -delete
for ((f = FS; f <= FE; f++)); do [ -s "$(printf "$OUT/f_%04d.png" $f)" ] || { echo "missing frame $f" >&2; exit 1; }; done
seg=$(printf "$P/segments/seg_%04d_%04d.mp4" "$FS" "$FE")
ffmpeg -y -loglevel error -framerate "$FPS" -start_number "$FS" -i "$OUT/f_%04d.png" -frames:v "$n" \
  -c:v libx264 -crf 12 -preset medium -pix_fmt yuv420p "$seg"
echo "wrote $seg"
