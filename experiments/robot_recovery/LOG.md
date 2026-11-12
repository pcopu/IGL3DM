# Incremental experiment log

## 2026-11-12 · 01 · Freeze the measured robot baseline

**Intent:** Preserve the completed strict-grid result before further recovery attempts.

**Input:** Existing silent Kling robot clip; SHA256 is recorded in `results/robot-grid-baseline.json`. No new paid generation. Base source `b7bc5788bf5f49eb5b6134e9e6963ce6b8321f57`.

**Commands/settings:** Existing `video_tracks.py --sample-fps 24 --size 768`; `prepare_graph_input.py`; `graph_tracker.py`; `validate_joint_artifacts.py`; `fit_shared_orbit.py --initial-period 192 --minimum-samples 16`; five-knot `fit_variable_orbit.py` with only actual/reported speed floor changed to 0.01 degrees/frame; `build_graph_geometry.py`; quad-shape diagnostics. Fresh outputs preserve the originals.

**Observed:** 199 conditional 3D points, 16 observed quads, 7 disconnected surface patches. Heldout projection p95 2.231930 pixels versus restricted constant baseline 10.198764. All 49 classical/video-grid tests and both graph validators pass.

**Failures/limits:** No full orbit track, no verified camera calibration, no authenticated periodic identities, no complete surface. Optimizer reports step-size termination but high optimality 219.678. The inferred 345.918-degree sweep is not a measured complete turn.

**Historical finding:** The earlier full-looking 252-quad pear was a permissive candidate display, with only 11 stronger-check quads. Later stricter methods deliberately discarded uncertain geometry. Recover its mechanism, not its unsupported certainty.

**Next:** Execute the three comparisons declared in README before choosing any new default.
