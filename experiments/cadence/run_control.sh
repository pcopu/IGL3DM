#!/usr/bin/env bash
# One matched analytic 256-frame fixture; no generated-target geometry is used.
set -euo pipefail
if [[ $# -ne 1 ]]; then echo 'Usage: PYTHON=/path/to/python run_control.sh FRESH_DIRECTORY' >&2; exit 2; fi
PYTHON=${PYTHON:-python3}
BLENDER=${BLENDER:-blender}
REPO=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$("$PYTHON" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$1")
if [[ -e "$OUT" ]]; then echo 'Refusing an existing output path' >&2; exit 2; fi
mkdir -p "$OUT/source"
for f in render_known_pear.py video_tracks.py grid_tracks.py geometry.py evaluate_cadence.py; do
  cp "$REPO/experiments/marker_consistency/source/$f" "$OUT/source/"
done
cd "$OUT"
CONTROL_VIEWS=256 "$BLENDER" -b -t 4 --python-exit-code 1 --python source/render_known_pear.py > render.log 2>&1
R=controls/known_pear_256
"$PYTHON" - <<'PY'
import json,cv2
from pathlib import Path
r=Path('controls/known_pear_256');g=json.loads((r/'ground_truth.json').read_text())
writer=cv2.VideoWriter(str(r/'control_video.avi'),cv2.VideoWriter_fourcc(*'MJPG'),30.,(512,512))
assert writer.isOpened()
for i in range(256):
 frame=cv2.imread(str(r/f'view_{i}.png'));assert frame is not None;writer.write(frame)
writer.release()
(r/'cameras.json').write_text(json.dumps({'source':'exact known control cameras; evaluation only','heldout_sample_indices':[32,96,160,224],'projections':{str(v['view']):v['projection_3x4'] for v in g['views']}},indent=2))
PY
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 "$PYTHON" source/video_tracks.py --video "$R/control_video.avi" --output "$R/video_tracks" --sample-fps 30 --max-frames 256 --size 512 --cameras-json "$R/cameras.json" > tracking.log
OPENBLAS_NUM_THREADS=1 "$PYTHON" source/evaluate_cadence.py --control-directory "$R" --output "$R/validation.json" > validation_summary.json
ffprobe -v quiet -count_frames -show_entries stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames,nb_read_frames,duration -of json "$R/control_video.avi" > ffprobe.json
