# IGL3DM: reconstruction research process

This file is the repeatable project procedure and handoff for future work. Read it before changing reconstruction code. The detailed history is in [process.md](process.md), [the robot recovery README](experiments/robot_recovery/README.md), and [the incremental experiment log](experiments/robot_recovery/LOG.md). Keep this guide current when the method changes. Keep full commands, settings, failures and measurements in the log rather than relying on conversation history.

## What we are trying to recover

Recover measured 3D grid junctions and observed shared cells from a rotating object's video. The result must come from image correspondences and explicit camera assumptions. It must not quietly become a silhouette hull, a supplied target mesh, a learned shape prior or a visually plausible completion.

- Use the existing approved video for a replay. Generating a new video is a separate, explicitly authorized task, not a substitute for investigating a failure.
- If a new turnaround is explicitly commissioned, the reference recipe is matching front/back images only, with the correct patterns on each side. Think through continuity but let the video model connect the intermediate views. Do not supply a hidden reference mesh to the reconstruction.
- Keep source video unchanged. Audio removal is acceptable as a documented lossless video remux. No interpolated frames, endpoint crossfades, duplicated endpoints or independently centered crops may enter measurement.
- Retain one shared spatial transform across every frame. A stationary camera or constant-speed orbit is a hypothesis unless actually supplied by a controlled acquisition.
- Missing observations remain missing. Missing surfaces remain absent.

## Required experiment discipline

1. Inspect the current repository state and relevant existing outputs. Preserve unrelated changes. Do not repeat an expensive experiment before checking whether its result already exists.
2. Read the current log and identify which method and gate produced each quoted result. Candidate density is not confidence.
3. Before execution, append the hypothesis, exact input hashes, settings, changed variable, fixed variables, output directory, comparison and expected failure test. Use a fresh output directory; existing scripts intentionally refuse nonempty outputs.
4. Change one mechanism at a time when possible. If several mechanisms differ, label the comparison as end-to-end rather than a clean ablation.
5. Freeze variants before reading an independent control's identity labels. Once a control has informed a design change, call it development evidence, not an untouched test set.
6. Preserve the unfiltered candidates, all rejected/ambiguous cases, all withheld predictions and the failures. Do not tune a threshold until the image looks full, then report only surviving residuals.
7. Run structural/numerical checks and independent physical-identity scoring where truth legitimately exists. Keep these different kinds of evidence separate.
8. Render actual inferred geometry, inspect the pixels, and label incomplete or conditional outputs. Do not substitute a reference mesh in a preview.
9. Append the outcome, interpretation, failed alternatives, test results and next decision. Commit coherent increments with the log, source and relevant evidence. Verify the expected commit reached the remote without replacing unrelated work.

## Data and truth boundaries

Synthetic controls may have known geometry and cameras. They are separate objects, not the robot's reference generator.

- Tracking, hypothesis fitting, point selection and face assembly must not read physical vertex IDs, control faces or control XYZ truth.
- A controlled camera can be supplied as declared acquisition metadata. That tests association with known cameras; it does not solve unknown camera calibration.
- `score_physical_faces.py` is evaluation-only. It must never repair or filter the algorithm's outputs using truth.
- Do not read or use the target robot geometry generator, silhouette reconstruction or its mesh while fitting the grid reconstruction.
- Keep the actual robot's unknown identities unknown. A synthetic score is not the robot's accuracy.
- Treat this as a public repository. Publish only authorized project inputs and outputs. Never include credentials, unrelated private files, account data or machine-specific secrets. Do not force-push or overwrite unrelated code.

## Environment and dependencies

Use an approved, isolated Python environment with NumPy, SciPy, Pillow, OpenCV and scikit-image already available. Do not silently install dependencies, download learned models or create credentials. Blender is needed only to render independent synthetic controls, not for tracking or triangulation. Record exact versions for each experiment.

The verified broad-view checkpoint used Python 3.12, NumPy/SciPy, OpenCV 5.0, scikit-image 0.26, Pillow 13 and already-installed Blender 4.3.2. Exact versions are in `experiments/robot_recovery/results/orbit-runtime-versions.json`; do not assume those are still installed.

From the repository root, add the source package to the existing approved environment:

```sh
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -c 'import numpy, scipy, cv2, PIL, skimage'
```

Keep large temporary frame sets and unapproved raw data outside the repository. Do not install optional Torch/volume dependencies just to turn skipped tests green.

## Input normalization and existing robot replay

The recorded robot input has 193 decoded frames, 24 fps, 720 by 1280 pixels. The shared transform to 512-square analysis is native scale 0.4 with horizontal padding 112. It is not independent object recentering.

`prepare_graph_input.py` preserves some earlier manifest fields. Its inherited LK track count and scale are not the graph detector's observation count or the final native-to-analysis scale. Use the dedicated tracker and experiment reports for those numbers.

The original input is in `experiments/robot_recovery/artifacts/robot-reproducibility.zip`:

- `input/robot-character-kling-v4-turnaround-silent.mp4`
- `evidence/grid_variable_projections.json`

The second file is a frozen experimental PCHIP camera hypothesis, not accepted calibration. Reusing it is deliberate when isolating association changes. Do not silently refit it or replace it with control truth.

A fresh broad-view replay can be prepared as follows. Set `WORK` to a new task directory outside the repository, and use the approved Python environment.

```sh
mkdir -p "$WORK/base"
unzip -q experiments/robot_recovery/artifacts/robot-reproducibility.zip -d "$WORK/base"

python experiments/marker_consistency/source/video_tracks.py \
  --video "$WORK/base/input/robot-character-kling-v4-turnaround-silent.mp4" \
  --output "$WORK/robot-lk" --sample-fps 24 --size 768

python experiments/marker_consistency/source/prepare_graph_input.py \
  --input "$WORK/robot-lk" --output "$WORK/robot512"
```

Verify frame count, order, timestamps, shared normalization and input hashes before continuing. Do not derive angles from timestamps without declaring the motion model. The video has nonuniform motion and near-pauses.

## Existing method families: do not mix their gates

### Original redetected graph pipeline

`experiments/marker_consistency/source/graph_tracker.py` detects every frame independently and associates junctions using local flow, appearance, graph support and optional skip-cycle veto. `validate_joint_artifacts.py` checks source hashes, one-to-one assignments, no gaps and accounting for every detection. Those are structural checks, not physical identity proof.

The robot baseline used explicit variable-camera geometry with at least 9 observations, at least 30 degrees fitted span, rank 3, condition at most 20, a middle-half fit and endpoint-quarter p95 at most 1 analysis pixel. It retained 199 points and 16 quads. Preserve that baseline.

### Historical LK and observed-cell reconstruction

`prepare_measurements.py`, `reconstruct_explicit_camera.py` and `assemble_observed_cells.py` preserve the older LK-based experiment. The historical point gate uses five robust iterations and 3-pixel train/block-holdout p95. It is not equivalent to the graph pipeline's 1-pixel midpoint/endpoint gate.

All-frame cell assembly uses only previously accepted point records, nearest node-to-track distance at most 4 pixels, a 1-pixel nearest-margin rule and rejection of every globally colliding mapping. Each accepted cyclic quad needs at least 3 observed frames and 15 degrees of fitted angular separation. It never fills an unseen face.

`join_cell_fragments.py` is a separate conditional experiment. It joins disjoint fragments only when observed cells share three fixed corners with compatible cyclic order, the time gap is at most 5 samples, all supplied-camera projections agree within 3 pixels, no many-to-one candidate ambiguity exists, and the refitted observation union passes the historical gate. It does not solve coherent periodic swaps.

### Broad-view hypothesis association

`associate_orbit_hypotheses.py` is an experimental alternative for hard temporal aliasing, not the default replacement for all inputs.

- Every fifth frame, index 4 modulo 5, is withheld from hypothesis generation, fitting and point-model selection.
- Candidate points come from detected junction pairs at least 30 degrees apart, not a single LK phase choice.
- Each candidate needs at least 9 actual calibration observations over at least 90 degrees, within a maximum 180-degree search window.
- Initial matching radius is 2 pixels with a 0.5-pixel nearest-neighbor margin. Refit twice; final training p95 is at most 1.5 pixels and condition at most 20.
- Calibration node assignments are one-to-one. Independently predicted withheld-node collisions are all rejected without changing selected point models. No predicted coordinate is inserted as a measurement.
- `--ambiguity-veto` rejects supported competing trajectories using the fixed source policy. It remains a heuristic, not a proof of uniqueness or a globally optimal assignment.
- `--resolvable-only` additionally requires next-nearest nodes outside the 2-pixel matching radius, local node spacing at least 6 pixels and at least 90 percent actual calibration hits within the accepted span.
- Preserve variants without these flags as comparisons. Do not tune the flags or thresholds on a blind control after reading its labels.

```sh
python experiments/robot_recovery/associate_orbit_hypotheses.py \
  --images "$WORK/robot512" \
  --cameras "$WORK/base/evidence/grid_variable_projections.json" \
  --output "$WORK/orbit" --ambiguity-veto --resolvable-only

python experiments/robot_recovery/validate_orbit_artifacts.py \
  --root "$WORK/orbit" \
  --cameras "$WORK/base/evidence/grid_variable_projections.json" \
  --output "$WORK/orbit/structural_validation.json"

printf '%s\n' '{"normalization":{"common_scale":1,"common_x_padding":0}}' \
  > "$WORK/normalized_measurement.json"

python experiments/robot_recovery/assemble_observed_cells.py \
  --tracking "$WORK/robot512" --points "$WORK/orbit/candidate_points.json" \
  --measurement "$WORK/normalized_measurement.json" \
  --cameras "$WORK/base/evidence/grid_variable_projections.json" \
  --output "$WORK/orbit/cells" \
  --point-gate-label 'Broad-view calibration-only candidate; physical identity unverified'
```

The explicit point-gate label matters: do not describe this new candidate subset as passing the old historical block holdout. `validate_orbit_artifacts.py` recomputes XYZ from calibration observations and verifies exact detected-coordinate provenance; it does not read truth.

## Holdout interpretation

- Report every withheld prediction, including unmatched nodes and large errors, before any acceptance filtering.
- Nearest detected-node error is not physical identity error. A repeating grid can predict the wrong node accurately.
- The robot camera matrices were estimated earlier from video evidence, including some frames withheld by the new association experiment. The new fifth-frame split is not independent end-to-end camera validation.
- Face assembly uses all actual matched observations, including withheld detections. It is not a heldout topology test.
- Fragment-ID splits need not be independent physical-point splits. Periodic aliases and duplicate fragments can appear in both groups.
- Do not compare residuals from different selected track populations as a paired improvement. List differing gates, cameras, splits and eligibility rules.

## Independent controls and identity evaluation

The existing analytic pear has 96 rendered views. The added controls are a bent ovoid and a separately defined squat asymmetric barrel. They share a renderer, grid pitch and camera family, so success on them is not broad real-world validation.

Render new control images only as a declared experiment, into a fresh directory:

```sh
CONTROL_VIEWS=96 CONTROL_SHAPE=bent_ovoid CONTROL_OUTPUT="$WORK/bent96" \
  blender -b -t 4 --python experiments/robot_recovery/render_independent_control.py

python experiments/robot_recovery/run_face_control.py \
  --images "$WORK/bent96" --output "$WORK/bent48" --stride 2
```

Use `CONTROL_SHAPE=squat_barrel` for the other frozen formula. The control runner never reads truth. It encodes FFV1 AVI and verifies that every decoded measurement frame is pixel-identical to its source image. The earlier Matroska wrapper quantized timestamps and failed the frame-count guard; that failure is retained. Do not interpolate missing frames to make counts match.

Run all declared tracking variants first. Only afterward use `score_physical_faces.py` with the control's evaluation truth. When scoring a stride-2 sequence, select every second truth view and renumber its view indices in the evaluation copy; never change the source truth or pass it to tracking.

The scorer associates only actually visible physical vertices within 3 pixels, with at least a 1-pixel nearest separation. Geometrically duplicated pole vertices are canonicalized. Full corner tracks must resolve to one identity, and the cyclic four-corner order must be a real nondegenerate control face. Keep wrong and unresolved cases in the denominator. Report unique physical coverage and duplicate faces separately.

A face may look correct in its few supporting images while a corner track switches identity elsewhere. Score both local source-cell support and complete track identity; do not conflate them.

## What the evidence currently says

This is a dated checkpoint, 2026-11-12. Update these facts through reproducible experiments, not by relabeling uncertainty.

| Method / control | Key observed result | Limitation |
| --- | --- | --- |
| Earlier visually full pear | 252 candidate quads, only 11 passing its stronger gate | Appearance was not verified density |
| Robot strict graph baseline | 199 points / 16 observed quads | Unverified identities and experimental cameras |
| Robot historical uniform camera | 66 candidate quads / 3 qualified | Severe camera/association outliers |
| Robot historical frozen variable camera | 752 qualified points / 33 qualified sampled quads | Different 3-pixel gate |
| Robot all-frame observed cells | 81 quads, 4 overused quad edges | Fragmentation and contradictions |
| Robot supported fragment joins | 78 quads, 1 overused edge | No new physical-identity proof |
| Robot broad-view final variant | 198 points / 49 quads, 12 patches, 0 overused edges | Incomplete; unknown physical accuracy |
| Hard pear48 broad-view variant | 206 correct / 32 wrong / 57 unresolved points | Historical accepted LK subset had zero correct |
| Hard bent48 broad-view variant | 162 correct / 29 wrong / 27 unresolved points | Development control; wrong identities remain |
| Third-shape barrel48 final variant | 237 correct / 29 wrong / 50 unresolved points | Frozen before labels; still not solved |
| Easier pear96 broad-view variant | 214 correct points, only 32 strictly correct faces | Regression against historical fine-cadence method |

The broad-view robot has 113 vertices in faces and 85 isolated points. All 2,024 fifth-frame predictions are reported: 1,931 match unique detected nodes, nearest-node p95 is 1.6451 pixels and the maximum is 41.9596. These values are not authenticated robot reconstruction error.

The current final-source robot replay reproduced points, tracks, detections, hypotheses, vetoes and withheld predictions byte-for-byte. See `results/orbit-final-replay.json` under the robot recovery experiment.

## Failed approaches and guardrails to retain

- Changing central-difference solver settings alone did not fix PCHIP convergence. A low residual is not a verified stationary optimum.
- The smooth B-spline camera lowered the fitting objective and improved numerical behavior, but heldout p95 worsened slightly and a coefficient hit a bound. Do not select cameras by desired face count.
- Subpixel refinement had mixed control behavior and lost robot coverage. Do not present it as a uniform improvement.
- Removing the graph cycle veto added only two robot points and no faces. It was not the main coverage bottleneck.
- Blindly removing all faces at overused edges discarded correct control cells and still left wrong identities. Treat quarantine as a diagnostic, not an identity solver.
- Broad-view association helps hard cadence but regresses at fine cadence. Preserve both methods rather than replacing the old pipeline globally.
- Dense repeated patterns admit periodic and sometimes reflective ambiguities. Three-pixel reprojection checks can pass the wrong identity. Near-pole convergence can be genuinely unresolved.
- Face counts, smooth surfaces, low selected residuals, and zero overused edges do not establish a valid complete mesh. Check boundary edges, isolated vertices, connected components, winding and self intersections separately. Some are still unvalidated.

## Tests, artifacts and commits

Run these suites from the repository root with the approved environment:

```sh
python -m unittest discover -s experiments/robot_recovery -p 'test_*.py' -v
python -m unittest discover -s experiments/marker_consistency/source -p 'test_*.py' -v
python -m unittest discover -s experiments/video_grid -p 'test_*.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

The checkpoint has 18 recovery + 47 classical + 2 video-grid + 23 core passes: 90 passing tests. Four optional core tests are skipped because their dependencies are absent. Keep skips explicit. Local tests are not a CI result; verify checks on the exact remote commit and report when none are configured.

Important regression fixtures prove that modifying all withheld-image detections leaves selected models unchanged, colliding withheld observations are all rejected, sparse periodic hit paths fail the density gate, ambiguous geometric competitors are not forced, and final geometry is exactly reproducible from real detections.

Keep artifacts under `experiments/robot_recovery/artifacts/` and compact metrics under its `results/`. The evidence ZIPs retain source snapshots, input hashes, all predictions, failures, evaluation rows and actual candidate models. Repeated identical bytes use `ALIASES.json`; after extraction, `python restore_aliases.py` recreates every logical file. Verify all entries in `MANIFEST.json`. Never deduplicate approximately or discard an inconvenient failure.

Use small, coherent commits: first the method and measured result, then the complete reproducibility bundle or documentation followup when appropriate. Preserve the old checkpoints. Include clear source links in the log, verify changed blobs and untouched files, and never claim a commit, attachment, test or calibration succeeded without checking its outcome.
