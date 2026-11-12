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

## 2026-11-12 · 07 · Image refinement has mixed control behavior and loses target coverage

**Observed on robot:** 169 points / 12 quads, versus 199 / 16 with original measurements and identical cameras/gates. Identities, assignments, cells and gaps are unchanged. Both structural validators pass on refined measurements.

**Known 96-view control:** Long tracks keep the same identities: 619 correct, 13 wrong, 6 unresolved. On correct long tracks, 3D-error p95 improves from 0.008234 to 0.006750 in control units. Yet heldout image p95 worsens from 0.5816 to 0.8698 pixels. The broader at-least-three-sample 3D-error tail also worsens, from 0.01451 to 0.02221. No claim of uniformly better localization is justified.

**Decision:** Retain as an informative failure, not a new default. Do not change the 1.5-pixel cap or window after inspecting these results.

## 2026-11-12 · 08 · Smooth camera basis improves numerical behavior, not heldout p95

**Observed on robot:** The same eight-parameter count with five clamped cubic B-spline log-speed coefficients reduces calibration robust cost from 1917.18 to 1835.79. Optimality improves from 219.68 to 0.05385; it terminates by `ftol` after 10 evaluations. One coefficient hits its upper bound. This is not unrestricted or independently accepted calibration.

**Heldout:** Mean endpoint error 0.78136 to 0.76908 pixels and median 0.54667 to 0.54039 improve slightly, while p95 worsens 2.23193 to 2.25128. The unchanged geometry gate retains 230 points / 30 observed quads, using 79 vertices. This increases conditional surface coverage, not verified physical correctness. Inferred sweep is 353.402 degrees.

**Independent projected-coordinate controls:** 100 known random point segments, 0.15-pixel Gaussian noise, 74 camera-training and 26 heldout IDs. On constant rotation the B-spline invents a small 0.04224-degree RMS yaw variation; heldout p95 0.39462 versus constant 0.39311. On the varying-speed fixture it recovers yaw with 0.02281-degree RMS and heldout p95 0.37941, versus a deliberately mismatched restricted constant prior at 40.397 pixels. These verify numerical behavior under model-compatible conditions, not image detection or target identities.

**Tests:** Five added tests pass for positive partition-of-unity basis, nested constant-camera equivalence, global speed bounds/monotonicity, numerical integration and image-refinement invariants. Historical source remains unchanged. Preserve both camera hypotheses rather than choose by target face count.

## 2026-11-12 · 09 · Next historical-camera isolation declared

Replay the historical robust LK/cell reconstruction with the already-frozen original PCHIP camera matrices instead of the known-inaccurate uniform 192-frame camera. Keep the old 3-pixel robust weighting, five iterations, nine-observation minimum, conditioning limit, global five-frame-angle-equivalent holdout blocks and observed two-view face rule. Use actual fitted angular span rather than nominal elapsed-frame span. Do not fit cameras again or consume the B-spline result. Report all candidates and the old 3-pixel-qualified subset separately; this is not the strict midpoint/endpoint graph pipeline. This isolates how much the historical replay failed because of its camera prior.

## 2026-11-12 · 10 · Fixed experimental camera recovers more historical supported cells

With frozen PCHIP projections and actual angular-span selection, the historical LK method yields 1,174 total points / 63 candidate quads. Of these, 752 points and 33 quads meet its old 3-pixel block-holdout criterion, versus 404 / 3 under uniform speed. Passing points spanning at least 90 degrees increase from 22 to 190. This supports the motion hypothesis for a useful subset.

The unselected heldout p95 worsens from 65.05 to 76.08 pixels, despite median improving from 3.38 to 1.11. Different point eligibility means this pooled comparison is not paired. Severe outliers remain, and this is not the 1-pixel graph gate. The qualified-only comparison image makes the differences explicit rather than rendering bad candidates as a complete surface.

Metadata corrections distinguish B-spline coefficients from interpolation knots and fitted spans from nominal spans. No numerical target result was changed by the terminology fix. Added an exact-projection fixture checking explicit-camera triangulation, terminal-frame exclusion and sample-order validation. Final local suites: 6 recovery + 47 classical + 2 video-grid + 23 core tests passed, with 4 optional core tests skipped.

## 2026-11-12 · 11 · Dense observed-cell assembly declared before execution

**Hypothesis:** The historical method detects repeated cells only in eight sampled frames. It may miss genuine observed connectivity on a complex robot despite having 752 conditionally supported points.

**Frozen experiment:** Reuse exactly the existing historical explicit-camera 3D points and camera hypothesis, without refitting or moving points. Detect cells in all 193 actual frames with the historical image normalization. Keep its 4-pixel nearest-track gate and 1-pixel nearest-margin rule, but reject every globally colliding node-to-track association. Assemble only the same cyclic four track IDs observed at least 3 times with at least 15 degrees of fitted angular separation, and with all four corners already passing the historical 3-pixel block holdout. No hidden completion, smoothing or changed point threshold. Compare the old eight-frame faces and the denser assembly separately; a face count increase does not authenticate periodic identities. Retain source-cell provenance and topology metrics for every face.

## 2026-11-12 · 12 · All-frame cells recover connectivity, while exposing contradictions

**Observed:** The identical 752 qualified point records support 81 repeated quads when all actual frames are checked, versus 33 in the eight-frame historical assembly. No point position or camera was changed. Every retained quad is observed in at least 3 frames spanning at least 15 fitted degrees; actual support reaches 56 frames. All colliding node-to-track mappings were rejected.

**Topology:** 204 points participate in faces; 548 remain isolated. The surface has 25 shared-vertex components, 200 boundary edges and 4 nonmanifold quad edges (5 after display triangulation), with no zero-area display triangles. These are real contradictions/limitations, not repaired or suppressed. The result is a measured partial patch assembly, not a watertight or validated robot.

**Verification:** Exact point-record equality, unique frame provenance per face, all four-corner qualification and all observation/span gates were checked. A seventh recovery fixture verifies unchanged geometry, minimum span, global collision rejection and refusal to overwrite results. No false claim of physical identity accuracy is made. This experiment has not yet had a separate known-identity face-assembly control, so it is not promoted as an accepted correspondence algorithm.

**Current interpretation:** Recovering correct nonuniform motion helps the historical method's useful subset. Examining all temporal views recovers additional observed topology. The next bottleneck is conflicting periodic identities and fragmented surfaces, not a lack of silhouette filling. Keep both the strict 1-pixel graph output and the denser 3-pixel diagnostic, with uncertainty visible.

## 2026-11-12 · 13 · Physical face control and contradiction audit declared

**Primary control:** Run the identical image-only LK, historical robust point fit and all-frame observed-cell assembly on the existing independent 96-view analytic pear render. Lossless FFV1 encoding must decode pixel-identically. Use the original declared acquisition metadata (512 pixels, orthographic width 3.2, level orbit at 3.75 degrees/frame), not inferred robot cameras or target reference geometry. This deliberately known-camera benchmark isolates image identity/topology; it does not validate target camera calibration. No ground-truth file enters tracking, point fitting or assembly.

**Evaluation only:** After output is frozen, associate observations with actually visible physical control vertices within 3 pixels, requiring at least a 1-pixel nearest-neighbor separation. Merge geometric duplicate pole vertices before identity comparison. Report wrong identities and unresolved observations, including unresolved items in every denominator. A face is strictly verified only if all observations of each full corner track resolve to one physical vertex and their cyclic order is an actual nondegenerate control quad. Also report local source-cell support separately, duplicates and geometric visibility coverage. Truth never repairs or filters the algorithm's output.

**Target diagnosis:** Inspect every nonmanifold quad edge and its observed face timelines. Preserve original 81 faces. A conservative contradiction variant will quarantine all faces incident to edges with more than two faces, rather than guessing which face is correct. Compare coverage and control false positives before recommending it. This is rejection only, never surface synthesis. More elaborate identity repair requires separate evidence.

**Execution failure retained:** The initial Matroska FFV1 wrapper quantized timestamps to milliseconds; the unchanged tracker sampled fewer than 96 frames and the explicit sample-count assertion stopped before reconstruction. Retain that failed output. Retry with lossless FFV1 in AVI, whose timestamp representation preserves the 24-fps frame cadence. This changes the transport container, not image pixels or tracker thresholds. Verify all 96 decoded images exactly before continuing.

## 2026-11-12 · 14 · Physical identity audit reveals fragmentation and persistent swaps

The lossless AVI control decodes all 96 frames pixel-identically. With declared known control cameras, 519 points pass the historical gate: 498 have consistent physical identities, 3 switch identities, and 18 are unresolved under the predeclared ambiguity rule. Among 270 assembled quads, 242 are strictly correct, 7 inherit identity-changing tracks, and 21 are unresolved. Correct faces cover 218 distinct physical quads out of 704 nondegenerate geometrically visible quads; 24 extra faces duplicate physical cells through fragmented IDs. Local source-cell observations alone classify 250 faces as consistent physical cells, illustrating why testing entire corner tracks matters.

Blanket quarantine removes 63 faces and all 30 control nonmanifold edges. It leaves 192 correct / 2 wrong / 13 unresolved faces, but only 183 distinct correct physical cells. Thus it loses 35 genuine cells and still does not eliminate wrong identities. On the robot it removes 10 of 81 faces, leaving 71 faces, 191 surface vertices and 26 components. All four target overused edges combine different-time faces; none has three incident cells observed simultaneously. Repeated cells with three shared corners and a newly assigned fourth corner suggest fragmentation, not necessarily three physical faces on one edge. Quarantine remains a diagnostic, not an accepted repair.

## 2026-11-12 · 15 · Constrained image-supported fragment joins declared

**Hypothesis:** Some duplicate faces differ only because one corner lost its track ID briefly. Join only pairs suggested by two observed cyclic quads sharing exactly three unchanged corner IDs and compatible cyclic order. Require disjoint point observation times, a positive gap of at most five samples (the unchanged seed cadence), and at most 3-pixel difference between both existing 3D point projections in every supplied camera. Reject ambiguous many-to-one candidate components entirely. Refit each unique pair from the union of its actual observations using the original five-iteration 3-pixel robust fit, original holdout blocks and conditioning gate; retain all original outputs and provenance. Reject any merged point failing the same train/holdout gate. Re-detect cells on all original pixels with unchanged assembly thresholds. No interpolated observations, new camera fitting, guessed phase offsets, truth-guided selection or hidden faces.

Freeze these settings before running either control or robot joins. Evaluate output only afterward using the same independent physical-identity scorer. A synthetic deliberately conflicting candidate fixture must reject ambiguous merges. This is a conditional identity hypothesis, not a claim of authenticated robot correspondences.

## 2026-11-12 · 16 · Cell-supported joins preserve distinct control coverage

Seven unique control fragment pairs pass every frozen join gate, and all seven independently evaluate as the same correct physical vertex. Re-detection after joining yields 252 faces: 230 strictly correct, 4 attached to identity-switching tracks, 18 unresolved. All 218 distinct correct physical cells survive; duplicate correct faces decrease 24 to 12, while nonmanifold edges decrease 30 to 8. This repairs fragmentation without increasing unique true coverage and does not correct the three underlying wrong-identity point tracks. Correct-point 3D-error p95 changes only 0.015632 to 0.015655 control units, not a geometry-accuracy improvement.

On the robot, two pairs pass; one fails the unchanged 3-pixel projection-agreement gate. The resulting 750 point records support 78 observed faces instead of 81, with 202 surface vertices and the same 25 components. Three of four nonmanifold edges disappear through evidence-supported fragment joins. The remaining edge is intentionally unresolved. Fewer faces here removes duplicate fragments rather than filling missing surface. A final optional quarantine leaves 75 faces, but neither variant is a complete or physically validated robot.

**Predeclared cadence stress:** Run the identical control pipeline on every second original image (48 views, 7.5-degree steps). This is a correlated cadence stress test of the same shape, not an independent new scene. Retain original thresholds, seed cadence and 3-pixel gates. Use the declared 48-view acquisition metadata and corresponding original angular holdout blocks (centers 6/18/30/42, radius 1). Score all outputs afterward with the same evaluator; do not tune joins based on labels.

## 2026-11-12 · 17 · Cadence stress fails; temporal aliasing remains fundamental

Every second control image yields a verified pixel-identical 48-view sequence with the correct declared 7.5-degree camera steps. The unchanged historical gate accepts only 34 points. Independent evaluation classifies 32 as identity-changing and 2 as unresolved, with no strictly correct complete track. No faces survive the observed-cell gate, so joins have no proposals and cannot repair the failure. This is a negative result on correlated resampled data, not a second independent shape. Do not hide it or call the method generally robust.

The original 96-view eight-frame assembly contains 106 qualified faces: 97 correct, 2 wrong-track and 7 unresolved, covering 97 distinct physical cells. All-frame assembly covers 218 distinct correct physical cells on the same qualified points, demonstrating a real control coverage gain rather than only a larger candidate count. Fragment joins preserve those 218 distinct cells but do not add new verified coverage. The two face-support policies also differ (historical two sampled views versus three actual views spanning 15 degrees), so this is a measured end-to-end comparison, not an isolated frame-count ablation.

Inspection of the three wrong 96-view tracks identifies two near-pole identity changes that still have maximum reprojection errors below 3 pixels, and one early single-sample switch with 9.89-pixel error hidden by the p95 criterion. A simple maximum-error filter would catch only the latter and is not implemented as a cure. Topology and reprojection alone cannot guarantee periodic physical identity.

## 2026-11-12 · 18 · Verify and preserve this checkpoint

All 13 recovery tests, 47 classical tests, 2 video-grid tests and 23 core tests pass; four optional Torch/volume core tests remain skipped. Added fixtures cover full-track versus local face identity, unresolved denominators, ambiguity, duplicate physical vertices, cyclic order, all-conflict quarantine, many-to-one join rejection and exact observed-coordinate union. All seven control joins independently connect the same correct physical point. Reconstructed output and comparison figures preserve original variants and label uncertainty.

The public checkpoint includes standalone source, compact control/topology metrics, full observation and evaluation provenance, the known synthetic control video and evaluation truth, target observed models and the detailed failure logs. Synthetic truth is isolated to evaluation and is not target robot reference geometry. No new paid generation, package installation or credential use occurred. Next research should improve association under periodic temporal aliasing on additional independent shapes, rather than relax gates or cosmetically complete the robot.

**Publication transport failure:** The first 13.9 MB evidence ZIP exceeded the GitHub connector's 16 MiB JSON request-body limit after base64 encoding. The request was rejected before creating that archive blob, and no branch was updated. Repackage only byte-identical repeated payloads as explicit aliases, retaining every logical evidence path and checksum plus a restoration script. This is lossless packaging, not discarded measurements. Reverify all expanded member hashes before retrying the smaller artifact.
