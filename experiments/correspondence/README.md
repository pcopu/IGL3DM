# Closed-cell graph and trajectory rejection

The frozen selector improves identity precision on a new 96-frame cadence control of the **same known analytic shape**, but leaves only **23 conditional segments, 17 triangulated points and zero observed faces** on the actual generated clip. It is more conservative, not a completed pear. The earlier 252-quad exploratory mesh remains unchanged.

## Image-only selection

1. Detect closed white cells at a common 512-pixel height. Associate temporal candidates with corners within 3 pixels and at least a 1-pixel alternative margin; reject collisions.
2. Require a four-ID cell cycle and two neighboring IDs to persist across adjacent frames, with at least two incident cells per corner. Missing support splits a segment; no gap is reconnected.
3. Require nine observations and 30° span under the declared orbit prior. Fit the middle half and predict endpoint quarters. Both p95 errors must be at most 1 normalized pixel, with conditioning at most 20.

The camera prior is level, fixed-framing, orthographic and constant-speed. No 2D coordinate is snapped or changed. No learned prior, truth, target template, manual modeling or hidden surface completion is used. Whole-row slips can preserve graph neighborhoods, so graph continuity alone is insufficient.

One- and two-pixel trajectory thresholds were tested on the 64/256 development controls. The one-pixel rule was frozen before testing the 96-frame control. Same-shape development and reseeding confounds still limit generalization.

## Matched 96-frame control

All 96 genuine frames at 3.75° spacing were encoded MJPEG at 24 fps and analyzed without downsampling. All 32 angles shared with the preserved 64-frame control match pixel-for-pixel.

For tracks spanning at least 30°:
- Original candidates: 556 correct / 29 known-wrong / 27 unresolved.
- Graph-supported segments: 266 correct / 4 known-wrong / 2 unresolved.
- Frozen graph-plus-trajectory rule: 266 correct / 0 known-wrong / 2 unresolved.

The 266 correct tracks cover 258 distinct known vertices, down from 462 in the original correct long tracks; 737 control vertices are visible somewhere. Of the 268 selected tracks, 183 have one of the four absolute held-out angles: 181 correct and two unresolved, all passing. The other 85 are unevaluated, not assumed to pass. Correct-track 3D median/p95 is 0.00697/0.01547 in a fixture of height 2.4. This is conditional control accuracy, not target accuracy or a zero-error guarantee.

The 64-frame development control retained just one correct long track, insufficient coverage. At 256 frames, 142 selected long tracks were operationally correct; 85 had available absolute held-out observations. Full alternatives and negative outcomes are in `results/`.

## Actual clip

The verified unblended 97-frame sequence yields 516 graph-supported segments, 292 with 30° nominal span. The fixed final rule retains 23, from which the existing fitter produces 17 points; eight have a held-out block and pass, nine lack that validation. No four-corner cycle survives in at least two selected measurement views. Zero faces is the actual result; none is filled in.

[Matched control](../../docs/experiments/22-graph-trajectory/control96_selection_comparison.png) · [Actual selected image observations](../../docs/experiments/22-graph-trajectory/real_selection_overlay.png) · [Actual sparse point output](../../docs/experiments/22-graph-trajectory/real_geometry_comparison.png)

## Camera diagnostic

Trimming fades does not establish a full turn in the remaining 97 frames. A separate constant-speed fit uses graph-only candidates, never the period-96 sine-gated subset. It estimates period, elevation, roll and horizontal center. Scale and vertical center are gauges. A deterministic 20% split of candidate IDs never fits the cameras; middle-half point fits predict endpoint quarters. These are not known physical identities: reseeded IDs can leak the same unknown physical vertex, and detection uses all frames.

With at least 16 observations, the real conditional fit estimates period 105.42 frames, elevation 4.12°, roll 0.51° and horizontal center 235.39 px. On the same 396 held-out observations, median/p95 improves 2.760/10.403→1.846/7.063 px, still poor calibration. On the known control, period estimates 94.77 versus true 96 and held-out error slightly worsens. A min-24 sensitivity fit gives a different real period and lacks enough control tracks. These values are not recovered camera truth and do not replace the old mesh cameras. A separate variable-speed test is documented in [camera experiments](../camera_motion/README.md).

## Reproduction and verification

Reusable source is in `../marker_consistency/source/`:

```sh
python experiments/marker_consistency/source/graph_consistency.py \
  --tracking-directory runs/video/tracks --output-directory runs/video/graph
python experiments/marker_consistency/source/apply_selection.py \
  --tracking-directory runs/video/tracks --graph-evidence runs/video/graph/graph_evidence.json \
  --output-directory runs/video/selected --period-frames 96
# Then use the video measurement/reconstruction helpers on runs/video/selected.
# Truth is loaded only by this separate known-control evaluator:
python experiments/marker_consistency/source/evaluate_control_selection.py \
  --control-directory LOCAL_KNOWN_CONTROL --graph-evidence LOCAL_GRAPH_EVIDENCE \
  --output-directory runs/new-control-evaluation --period-frames 96
```

The constant-camera CLI exposes `--minimum-samples` and `--max-nfev` as well as explicit track/manifest/output paths. It consumes graph-only segments from `select_segments`, not the final trajectory-selected tracks. All outputs must be fresh. Seven selector/preview tests cover graph gaps, connectivity, unchanged observations, endpoint slips, short baselines, synthetic camera recovery and empty geometry. The main-checkout replay reproduces selected target tracks/audits byte-for-byte and every matched-control summary metric exactly. Raw tracks, target coordinates, control truth and model files remain local.
