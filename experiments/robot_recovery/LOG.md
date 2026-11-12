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

## 2026-11-12 · 19 · Multi-view association experiment declared

The next experiment replaces one-step LK identity commitment with candidate trajectories fit across a broad orbit interval. It uses detected image junctions plus frozen/declared camera matrices, never target-reference geometry or evaluation labels. Start with the failed 48-view control, retain the 96-view case as a cadence comparison, then evaluate a separately rendered shape before any claim of generalization.

**Frozen prototype:** Every fifth frame (indices congruent to 4 modulo 5) is withheld from hypothesis generation, fitting and selection. Seed candidate 3D points from all epipolar-compatible junction pairs separated by at least 30 degrees, using anchor frames every four samples. Consider at most 180 degrees around each anchor. Match predicted coordinates to independently detected nodes within 2 pixels with at least 0.5-pixel nearest-neighbor separation. Permit at most one missing calibration sample between observed matches; never fabricate a missing coordinate. Require at least 9 actual calibration observations and 90 degrees angular support. Refit twice from actual matched coordinates, retaining training p95 at most 1.5 pixels and condition at most 20. Rank by observed support then residual and select without reusing calibration nodes. Report all generated hypotheses, selection conflicts, and withheld predictions before any heldout filtering. Calibration-pixel support is not physical truth.

**Limits:** Known-camera controls isolate association, not unknown-camera estimation. The target has only experimental camera estimates. Repeating patterns may admit physically different but equally predictive trajectories, so residuals and a visually denser mesh cannot establish identity. This is a prospective protocol, not an assertion that the hypothesis search will succeed.

## 2026-11-12 · 20 · Prototype recovery and independent-shape protocol

The first 48-view multi-view prototype tests 21,255 two-view seeds and retains 310 trajectories after calibration-only selection. Independent full-track evaluation finds 188 correct, 61 identity-changing and 61 unresolved tracks, versus zero correct / 32 wrong / 2 unresolved accepted LK points. Correct-track 3D-error p95 is 0.008291 control units. Across all 999 withheld predictions, nearest detected-node p95 is 3.5005 pixels and 903 meet the declared 2-pixel/margin rule. These errors are reported before any heldout selection. This is meaningful recovery but still unacceptable identity ambiguity.

**Independent shape:** Render a new bent ovoid with a separate frozen analytic formula, 32 longitudinal cells and 24 latitude bands, the same declared level orthographic acquisition and 96 actual rendered views. Use every second image for a 48-view evaluation. The new shape is not the robot, not the earlier pear, and never enters fitting. Its truth labels remain unread until all candidate variants have been produced. This is a new shape under similar rendering conditions, not a realistic generator-domain benchmark.

**Competing-hypothesis veto declared:** Before greedy assignment, reject a trajectory if another valid candidate shares at least one detected calibration node, has at least as many actual calibration observations, has training p95 no more than 0.25 pixels worse, and differs by at least 4 pixels in projection within their common observed frame span. This compares supported alternatives rather than picking a phase solely by local flow. The 4-pixel difference is twice the existing matching radius. Preserve both vetoed and original variants. This remains a heuristic, not proof of uniqueness.

**Heldout collision audit:** Independently predicted withheld-node matches can collide even though calibration nodes are exclusive. Reject all such heldout associations, report their original errors, and do not change selected point models or use withheld outcomes for selection. Missing coordinates stay missing. This is a structural constraint, not a threshold tuned on identities.

## 2026-11-12 · 21 · Broad-view recovery generalizes, but the first veto is insufficient

The first independent bent-ovoid 48-view control is evaluated only after both candidate variants finish. Its historical LK subset contains 13 wrong-identity points and no correct points or faces. The new broad-view method recovers 141 correct / 45 wrong / 37 unresolved points; the competing-hypothesis veto changes this to 151 correct / 33 wrong / 32 unresolved. It yields 34 correct / 10 wrong-track / 28 unresolved faces, with all withheld prediction errors retained (see exact metrics). This is progress under the separate shape, but not a trustworthy complete reconstruction.

On the original pear48, the veto keeps 186 correct / 45 wrong / 45 unresolved points; correct observed faces fall 33 to 27 while wrong-track faces fall 57 to 47. On pear96 it retains 222 correct / 32 wrong / 112 unresolved points and only 32 strictly correct faces among 244 candidates, far worse than the historical dense control face result. Therefore this hypothesis method is not a universal replacement for the existing tracker.

**Next fixed measurement gate:** Test a separately labeled resolvability variant: require the next-nearest detected node to lie outside the existing 2-pixel match radius, local detected-node separation at least 6 pixels (three times that radius), and at least 90 percent actual matched calibration frames within a trajectory's accepted span. Keep all prior support, fitting and ambiguity thresholds fixed. This should abstain on unresolved converging lines and periodic sparse-hit paths, rather than claim identities there. It may discard genuine surface detail.

The first two control shapes are now development evidence. Freeze this variant before rendering/evaluating a third, independently defined squat asymmetric barrel-shaped control under the same 48-view cadence. Report all three, not only favorable cases. No evaluation labels may repair or choose individual target tracks.

## 2026-11-12 · 22 · Resolvability variant improves independent recovery, not certainty

The fixed spacing/density variant retains 206 correct / 32 wrong / 57 unresolved point tracks on pear48, and 162 correct / 29 wrong / 27 unresolved on the bent ovoid. Their observed faces contain respectively 30 correct / 44 wrong-track / 66 unresolved, and 46 correct / 12 wrong-track / 32 unresolved. Incorrect full-track identities remain a substantial problem. Do not render only the green subset and call the whole mesh solved.

The third shape is frozen before its labels are read. Its accepted historical LK subset has 14 wrong-identity points and no correct points. The broad-view baseline has 217 correct / 52 wrong / 56 unresolved points. The declared ambiguity-plus-resolvability variant yields 237 correct / 29 wrong / 50 unresolved points and 66 correct / 41 wrong-track / 57 unresolved faces. Across all withheld predictions, nearest-node p95 changes 5.1785 to 4.6314 pixels. This verifies a real cross-shape recovery but also an unresolved failure tail. The heldout metric concerns nearest measured nodes, not authenticated identity.

On the easier pear96 cadence, the new variant yields 214 correct / 30 wrong / 113 unresolved points and only 32 correct faces, so it does not replace the stronger historical 96-view result. Preserve the existing fine-cadence tracker and the new hard-cadence research as separate methods. The three controls share a renderer, grid pitch and camera family; they do not establish performance on arbitrary generated video.

## 2026-11-12 · 23 · Transfer the frozen association method to the actual robot

The unchanged ambiguity-plus-resolvability variant uses the existing normalized robot frames and frozen PCHIP camera matrices. It produces 198 measured 3D point candidates and 49 observed quads using 113 vertices, with 85 isolated points. There are 12 shared-vertex surface components, 104 boundary edges and no overused quad edges. There is no hole filling or surface completion.

The 2,024 fifth-frame predictions are reported before any heldout model gate: 1,931 match unique detected nodes; nearest-node median is 0.4681 pixels, p95 1.6451 and maximum 41.9596. The long tail remains visible. This is not a paired accuracy comparison with the old 199-point strict graph result because tracks, thresholds, angular support and splits differ.

The new split withholds images from association/model selection only. The previously fitted target camera parameters already used video evidence from some of those frames, so this is not independent end-to-end calibration validation. Face assembly uses actual matched observations from all frames, including matched withheld detections; it is not a heldout topology test. Independent synthetic physical truth, not target reference geometry, is the only identity ground truth used anywhere.

A structural auditor exactly recomputes all 198 XYZ values from calibration coordinates, verifies all 8,197 calibration nodes and 1,931 emitted heldout nodes are unique, checks every emitted coordinate against its source detection and confirms no rejected prediction is inserted. Minimum calibration-hit density is 0.9032. No robot physical-identity accuracy can be claimed.

## 2026-11-12 · 24 · Exact replay and heldout-isolation verification

Final installed-tool suites pass 18 recovery, 47 classical, 2 video-grid and 23 core tests, with four optional core tests skipped: 90 passing total. New fixtures verify rejection of sparse periodic-hit paths, ambiguity between similarly supported geometric hypotheses, all-collision rejection and absence of synthesized observations. Changing every withheld image's detected coordinates by a large amount leaves selected calibration identities and XYZ models bit-identical while worsening reported prediction errors.

A final robot rerun with the published source reproduces candidate points, tracks, per-frame detections, withheld predictions, all hypotheses and all veto decisions byte-for-byte. The independent auditor passes again. Source hash, output hashes and runtime versions (including already-installed Blender) are recorded. No packages were installed during this stage. The broad-view method remains an experimental alternative with significant identity failures, not a complete solution.

## 2026-11-12 · 25 · Preserve scoped reproducibility bundles

Four separate bundles preserve the pear-development variants, bent-ovoid variants, third-shape blind comparison and actual robot transfer. Their payloads capture source/log entries through 24, exact observations, all hypotheses, vetoes, withheld predictions, evaluation rows, source snapshots and actual model files. The independent-control bundles include the exact measured FFV1 input and evaluation-only truth. Existing preceding bundles retain the original pear input and actual robot video, avoiding redundant copies.

Every logical evidence file has a SHA256 checksum. Identical repeated payloads are represented by explicit aliases, with a restoration helper. All 319 logical files across the four archives were extracted, aliases restored and hashes independently checked. Bundle sizes stay below the publication transport limit. No unrelated files, credentials or robot reference-generator geometry are included. This packaging preserves the failures as well as improved examples.

## 2026-11-12 · 26 · Add the requested durable process guide

Added the repository-level `AGENTS.md` requested by the owner. No previous repository guide existed at the verified current head. It records the complete operating procedure, exact replay/test commands, input and truth boundaries, distinct confidence gates, independent-control workflow, withheld-image caveats, dated validated results, known regressions, artifact verification and incremental commit practice. It links back to this detailed ledger instead of relying on transient conversation context. Private instructions, credentials, local account data and internal identifiers are excluded.
