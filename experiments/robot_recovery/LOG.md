# Incremental experiment log

## 2026-11-12 · 01 · Freeze the measured robot baseline

**Intent:** Preserve the completed strict-grid result before further recovery attempts.

**Input:** Existing silent Kling robot clip; SHA256 is recorded in `results/robot-grid-baseline.json`. No new paid generation. Base source `b7bc5788bf5f49eb5b6134e9e6963ce6b8321f57`.

**Commands/settings:** Existing `video_tracks.py --sample-fps 24 --size 768`; `prepare_graph_input.py`; `graph_tracker.py`; `validate_joint_artifacts.py`; `fit_shared_orbit.py --initial-period 192 --minimum-samples 16`; five-knot `fit_variable_orbit.py` with only actual/reported speed floor changed to 0.01 degrees/frame; `build_graph_geometry.py`; quad-shape diagnostics. Fresh outputs preserve the originals.

**Observed:** 199 conditional 3D points, 16 observed quads, 7 disconnected surface patches. Heldout projection p95 2.231930 pixels versus restricted constant baseline 10.198764. All 49 classical/video-grid tests and both graph validators pass.

**Failures/limits:** No full orbit track, no verified camera calibration, no authenticated periodic identities, no complete surface. Optimizer reports step-size termination but high optimality 219.678. The inferred 345.918-degree sweep is not a measured complete turn.

**Historical finding:** The earlier full-looking 252-quad pear was a permissive candidate display, with only 11 stronger-check quads. Later stricter methods deliberately discarded uncertain geometry. Recover its mechanism, not its unsupported certainty.

**Next:** Execute the three comparisons declared in README before choosing any new default.

## 2026-11-12 · 02 · Historical replay did not recover supported coverage

**Intent:** Determine whether the visually fuller Round 19 method works better on this exact robot input.

**Commands:** `prepare_measurements.py --period-frames 192 --original-frame-offset 0 --source-fps 24`; `reconstruct_video.py --period-frames 192 --holdout-centers 24 72 120 168 --holdout-radius 4 --original-frame-offset 0`, using the existing 768-high LK tracks. No new generation or tracking thresholds.

**Observed:** 1,277 candidate points and 66 repeated candidate quads. Only 404 points and 3 quads pass the historical 3-pixel training/holdout condition. Unselected heldout p95 is 65.049 pixels. The full candidate preview contains obvious extended sheets and inconsistent depth.

**Conclusion:** Do not promote dense candidate count to reconstruction quality. The known-inaccurate constant-speed prior and permissive LK paths contribute failures. Retain all artifacts for comparison. This result does not isolate tracking from camera error.

## 2026-11-12 · 03 · Central differences alone do not fix camera convergence

**Intent:** Check whether the original high optimality was a simple numerical finite-difference issue, without changing model or choosing by heldout success.

**Fixed change:** Three-point central Jacobian, relative step 1e-4, Jacobian variable scaling and max_nfev 500. Same five PCHIP log-speed knots, initialization, bounds, data, hash-ID split, loss and regularizer.

**Observed:** Calibration robust cost 1917.178586 to 1916.941735; endpoint p95 2.231930 to 2.221847 pixels. However optimality worsens 219.678 to 930.176, and termination is still `xtol` after 24 evaluations.

**Conclusion:** Reject this as a convergence fix. The tiny heldout change is not a reason to select a new default. Preserve original baseline and failed numerical trial.

## 2026-11-12 · 04 · Cycle veto is not the main coverage bottleneck here

**Intent:** Test the already-produced adjacent-only graph tracks on exactly the original variable camera matrices and strict geometry gates.

**Observed:** Removing the veto changes 199 to 201 selected points, with 16 quads and 46 surface vertices unchanged. No camera refit and no threshold changes.

**Conclusion:** Do not remove the veto to chase density. It explains only two selected points in this input, not the missing surface.

## 2026-11-12 · 05 · Public reproducibility artifacts authorized

The owner explicitly approved publishing this experiment's video, reconstruction models, tracking/metrics/evidence and detailed logs to the public repository. This is specific to the relevant IGL3DM work, not a general data-sharing permission. Credentials and unrelated private data remain excluded. The robot reproducibility bundle adds the delivered silent input, actual grid models, measured observations, projection matrices and local experiment code. Generated references and known target generator geometry are excluded to prevent reconstruction leakage. This supersedes the earlier compact-only publication choice for this experiment alone.

## 2026-11-12 · 06 · Next isolated tests declared before execution

**Image measurement refinement:** Refine each existing detected junction using OpenCV cornerSubPix on the original gray frame, a fixed 3 by 3 half-window, 30 iterations / 0.001 tolerance. Accept only finite adjustments at most 1.5 analysis pixels; otherwise preserve the original detection. Keep every original track ID, association, gap and cell unchanged. Compare the strict 1-pixel geometry gate on the same frozen cameras. Evaluate physical correspondence/coordinate error on the separate known 96-view control before recommending it. No target camera or shape enters refinement.

**Smooth camera basis:** Test five clamped cubic B-spline log-speed coefficients instead of PCHIP interpolation, with the same eight total parameters, speed bounds, regularization, initialization and fragment split. A convex B-spline basis preserves the speed bounds while avoiding PCHIP slope-branch changes around equal adjacent values. Use one central-difference solver run and independent constant/variable synthetic trajectory controls. Select numerical behavior from training objective, derivative checks and controls, not desired target geometry or heldout score. Preserve failure if no improvement.
