# Adjacent-frame video ingestion and candidate tracking

`source/video_tracks.py` accepts a user-supplied video and saves actual decoded frames, timestamps, source-frame indices, scaling metadata and tracked 2D junction observations. No external user clip has been tested yet. Synthetic clips and independently rendered controls are clearly separated from generated inputs.

It seeds automatic skeleton-junction candidates, uses pyramidal Lucas–Kanade flow with forward/backward error <=1 pixel, patch NCC >=0.65 and a bounded displacement, and terminates a track when those checks fail. Newly appearing intersections get new IDs. No point is automatically reattached after disappearance. The manifest distinguishes loss causes, but cannot prove whether a loss was physical occlusion or ambiguity.

The endpoint comparison is only a near-duplicate warning. A copied closing frame is never accepted as proof of a coherent orbit. A static ImageGen PNG sheet is not treated as an animation.

## Usage

```sh
python source/video_tracks.py --video supplied_clip.mp4 --output new_output --sample-fps 30
```

Use a sufficiently high sampling rate for the grid density and rotation speed. The current default is 12 fps for bounded prototype processing; explicit 30 fps is preferable for a normal short turntable when available. Outputs are capped at 600 sampled frames; truncation is reported. Sampling preserves original timestamps, falling back to frame index / reported FPS when decoder timestamps are unusable. Coordinates retain one common aspect-preserving image scale, never independent object fitting.

Without camera information the script **does not triangulate**. Explicit camera matrices can be supplied:

```json
{
  "source": "describe calibration or clearly label estimated cameras",
  "heldout_sample_indices": [8, 24, 40, 56],
  "projections": {
    "0": [[160, 0, 0, 256], [0, 0, -160, 256], [0, 0, 0, 1]]
  }
}
```

Each projection is a finite 3×4 matrix in the working-frame pixel coordinate system, keyed by sampled-frame index. Supply at least two nondegenerate training views and a held-out view for a diagnostic. Use `--cameras-json cameras.json`. Timestamps alone do not calibrate a camera. Perspective DLT and orthographic matrices are supported mathematically; this is not a calibrated reconstruction guarantee.

## Tests and actual controls

Three video-specific tests pass: known projection triangulation, rejection of a degenerate repeated camera, and actual AVI decoding / translated grid tracking / termination at a completely occluded frame. No old ID is reattached after that disappearance. Together with the existing geometry and junction tests, 13 tests passed before later quad/camera tests are added.

A separate 64-frame Blender-rendered analytic asymmetric pear control uses true 5.625° camera increments, encoded at 12 fps. It is not an ImageGen animation and never supplies geometry to the generated pear.

- 1,672 seeded candidate tracks; 806 span at least three samples.
- Against known visible ground-truth vertices (3 px association tolerance): 200 keep the correct physical identity, 599 switch identity, 7 are unresolved.
- The 200 correct tracks triangulate with median known-world error 0.00823 and p95 0.02004. The control has a total height of 2.4 world units.
- Among tracks passing a <=3 px held-out reprojection threshold, 50 are correct, 100 are wrong and 1 is unresolved.

This is a limited positive result for smaller temporal steps, plus a strong warning: smooth tracking and low reprojection can still accept periodic-grid swaps. This prototype is not yet a dependable cell-identity decoder. Ground truth is used only to evaluate this control, not to perform the tracking.

Selected control overview: `controls/known_pear_64/video_tracks/tracking_overview.png`. Compact metrics are in `controls/known_pear_64/validation.json`; raw video, full 3D ground truth, projection arrays and model-like outputs stay local rather than in published evidence.

Public summaries of the known rendered controls and selected overview images are under `experiments/pear_grid` and `docs/experiments/17-classical-pear`. No actual generated/user-supplied turntable video has been validated.
