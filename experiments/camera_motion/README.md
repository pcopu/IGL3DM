# Camera flexibility improves image fit, not proven camera accuracy

**Do not promote these parameters to accepted calibration.** A single bounded variable-speed camera model improves real-clip endpoint prediction, but hits a speed bound and introduces spurious acceleration on the constant-speed known control. An exploratory application produces 73 conditional points and six observed quads, not a complete or validated pear. The original 252-quad output and the stricter 17-point/zero-face output remain unchanged.

## Fixed model and validation

Five equally spaced log-angular-speed knots are PCHIP-interpolated, exponentiated and integrated. Speed is positive and bounded to 1.875–5.625° per frame. Elevation, roll and horizontal center are constant; scale 256 px/unit, vertical center 256 px and initial yaw zero are gauges. A fixed weak adjacent-log-speed penalty and soft-L1 loss were not tuned on validation. Integration uses 32 steps/frame.

The fit consumes graph-only candidate observations, never truth or the period-96 trajectory-gated set. It uses the same min-16 sample tracks and deterministic held-out candidate-ID split as the constant baseline: real 148/35 and control 82/15 calibration/validation IDs. Held-out point locations fit only their middle halves and predict their endpoint quarters. Source track IDs do not overlap, but unknown reseeded physical vertices still can; all-frame image/graph processing is shared. This is not independent physical-identity validation.

On the same real 396 endpoint observations, constant→variable median error is 1.846→0.801 px and p95 7.063→3.213. On the known control's 152 observations, median worsens 0.090→0.096 and p95 0.294→0.397. After fitting, true-control yaw RMS worsens 1.349→2.250°, with only one phase offset/sign allowed in evaluation, no time warp or angular rescale.

The real speed knots are approximately 1.875,3.864,3.800,3.353,1.956°/frame. The first hits its lower bound. Elevation is 4.369°, roll 0.212°, center 244.343 px, mean equivalent period 109.11 frames. The fitted sweep is 316.75°, not established true motion. Control estimates introduce acceleration despite constant-speed truth. Numerical optimizer success and moderate Jacobian condition do not prove identifiability or a statistically valid uncertainty interval.

No model was refitted after truth evaluation. Positive speed, monotone yaw, exact paired samples/splits, constant-model equivalence and integration convergence are checked. Using 512 rather than 32 integration steps/frame changes yaw by at most 0.0000124° on the real fit. These validate numerical implementation, not the physical camera assumption.

## Exploratory observed-cell output

Apply the same rank/conditioning and 1-pixel middle-fit/endpoint gate, with at least nine samples and 30° fitted span. Real candidate selection rises from 18 for the fitted constant camera to 73 for variable speed. On the known control it drops from 266 correct / 2 unresolved to 255 correct / 2 unresolved, with no known-wrong selected in this limited control.

The 73 real points support six four-corner cycles observed in 8–17 actual frames, using 20 surface vertices. Only those observed faces are exported, with no hidden fill, smoothing, silhouette completion, learned prior or manual target geometry. Physical IDs and camera parameters remain unverified. Point coordinates have a Z-up relative gauge; no metric camera distance/translation is identified. Exact experimental projection matrices stay local.

Blender displays the unchanged six quads using a stated diagonal per quad and standard turntable cameras. **Those turntables are not calibrated input-view reprojections.** The actual sparse fragments, not an imagined completed surface, are shown below.

[Camera diagnostic](../../docs/experiments/23-camera-motion/camera-diagnostic.png) · [Point/face preview](../../docs/experiments/23-camera-motion/experimental-geometry.png) · [Actual mesh turntable](../../docs/experiments/23-camera-motion/actual-patch-turntable.gif)

## Reproduction

Source is in `../marker_consistency/source/`:
- `fit_shared_orbit.py` supplies the constant fit. Use graph-only segments, `--minimum-samples 16`, explicit manifest/track/output paths and the declared initial period.
- `fit_variable_orbit.py --tracks GRAPH_SEGMENTS --manifest TRACKER_MANIFEST --baseline CONSTANT_REPORT --output NEW_REPORT` runs the fixed alternative. It saves resolved input paths in the private runtime report.
- `evaluate_variable_orbit.py --report-directory REPORTS --control-truth CONTROL_TRUTH --output NEW_JSON` runs post-fit invariants and control-yaw evaluation. REPORTS contains `real_variable.json` and `control96_variable.json`.
- `package_variable_orbit.py --report-directory REPORTS --control-validation CONTROL_VALIDATION --output-directory FRESH_DIRECTORY` exports experimental matrices/conditional selections. Legacy reports with relative input paths can use `--input-base-directory`.
- `build_variable_preview.py --tracks GRAPH_SEGMENTS --manifest TRACKER_MANIFEST --graph GRAPH_EVIDENCE --cameras EXPERIMENTAL_CAMERAS --selection CONDITIONAL_SELECTION --output-directory FRESH_DIRECTORY` triangulates selected points and assembles only repeated observed cell cycles.

Main-checkout replays reproduce every numerical evaluation field, camera/selection artifact, and point/face/PLY artifact exactly after canonicalizing equivalent provenance paths. Empty output is a valid tested negative result. Raw runtime reports with paths/coordinates, videos/audio, full control truth and 3D models are not published; only compact metrics, source and silent visuals are retained.
