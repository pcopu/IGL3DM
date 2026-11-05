# Controlled square-texture geometry test

## Finding

**The tested formulation does not justify extending this atlas into a reconstructed object.** The local square-projection mathematics works exactly on its intended fixtures. But square-ness is an assumption rather than a property that can be established from a single projected parallelogram; choosing the smoothest local depth signs does not resolve shape. A negative control with exact equal square facets returns an incorrect surface even with essentially zero integration residual.

The generated atlas also provides inconsistent measured cell sizes and incompatible adjacent depth increments. Actual open patch meshes are included to make the failure inspectable, not as a successful reconstruction. No source ground-truth geometry or normals exist for this generated input.

## One controlled formulation

For four ordered projected corners, use the least-squares affine parallelogram:

- a = ((p1 - p0) + (p2 - p3)) / 2
- b = ((p3 - p0) + (p2 - p1)) / 2
- A = [a b], C = AᵀA, eigenvalues λmin ≤ λmax.

An orthographically projected planar physical square obeys C + d dᵀ = s²I, where d contains the two depth increments. Therefore:

- s = sqrt(λmax), in projected pixel units, not calibrated physical units.
- cos(tilt) = sqrt(λmin / λmax).
- d = ±sqrt(λmax - λmin) vmin.
- The screen-space depth gradient is g = (Aᵀ)⁻¹d.
- The unit normal with positive viewing-depth component is n = (-gx, -gy, 1) / sqrt(1 + |g|²).

The affine-parallelogram corner RMS residual is |p0 + p2 - p1 - p3| / 4. Any nonsingular exact parallelogram satisfies the algebra for some s and d. A front-facing 12×8 rectangle falsely acquires a 48.19° tilt when the square assumption is imposed. Thus local agreement with this algebra does **not** verify physical squares.

For one connected patch, signs σi ∈ {-1,+1} minimize the sum of squared differences between neighboring unit normals. An exact binary MILP uses XOR variables for pair terms; the first sign is fixed only to remove the unavoidable global reflection. No apparent convexity, concavity, pear anatomy, silhouette-depth assumption or hand-selected signs enter the objective. The real selected patch solved to zero reported MILP gap. An independent test compares this optimizer with exhaustive enumeration on eight random six-node graphs.

After signs, shared vertex depths minimize the unweighted squared error of all four per-cell predicted edge increments. This is a linear least-squares solve with the arbitrary mean depth removed. There is no depth smoothing, boundary condition or hidden-surface fill. This two-stage objective is explicit; it is **not** claimed to be a joint optimum of normal smoothness and depth integration.

## Fixtures and falsification

- 105 exact square-plane cases: 7 tilts from 0° to 89°, 3 scales and 5 random orientations each. Maximum scale error 3.56e-15; maximum depth-increment error 2.93e-7 (near-zero eigenvalue-difference roundoff); maximum tilt error 1.21e-6 degrees.
- A 30-cell connected tilted square plane integrates to depth RMSE 1.15e-15, allowing global reflection and depth translation.
- Negative control: 72 exact, equal, planar square facets arranged on a cylindrical strip. The square side is exactly 1; maximum parallelogram error is 2.23e-16. The optimizer prefers the wrong monotone surface: normal smoothness energy 0.600 versus 0.660 for the true convex cylinder. Its edge integration RMS is 2.61e-14, yet depth RMSE to the truth, even after choosing the better global reflection, is 1.094 against a truth depth span of 1.748. **Local signs have alternatives beyond a single global reflection.** A low integration residual is insufficient proof of shape.
- Noise tests add 0.25, 0.5 or 1 pixel Gaussian corner noise to 14-pixel squares at 5°, 45°, 80° and 89° tilt, with 200 trials per case. At 5° and 0.5-pixel noise, the best-sign normal error is 16.8° median / 25.5° p95. Near front-facing, the small eigenvalue gap makes tilt direction unstable. Near edge-on, the inverse projection becomes ill-conditioned; the report includes gradient-relative error, which can be severe even when angular normal error is small.

## Real atlas measurements

Read-only input: `docs/experiments/17-classical-pear/input.png` and a locally generated `quad_graph.json` from `experiments/marker_consistency/source/quad_cells.py`. Input hashes are in `integration_report.json`.

The same 3,757 detected cells are measured both as raw white-interior quads and as welded corner quads. These are **detections**, not certified physical grid corners.

- Across individual views, inferred side-size coefficient of variation is approximately 20–26%. Median size is about 12 pixels from white interiors and 14 pixels after welding. Ink thickness and the detector's interior-versus-line convention materially affect the measurements.
- Of 3,757 welded cells, 406 have projected aspect ratio below 0.25 (inverse-projection condition above 4); 278 have affine-parallelogram residual above 10% of inferred side. These counts overlap.
- Fixed numeric acceptance gates are affine residual / side ≤0.10, minor/major singular ratio ≥0.25, and inferred side ≥5 pixels. The largest shared-edge connected component across all eight views is selected automatically, with lowest view index as tie-break. No visually favorable region is chosen.
- Selection: view 4, 238 quads, 370 vertices and 322 adjacent cell pairs.
- Selected inferred square side: median 15.73px, 5th–95th percentiles 12.53–18.78px, full range 9.61–28.51px, CV 13.1%. A physically exact connected square mesh would need a common side length across shared edges. The observations do not support that premise; they cannot distinguish varying grid scale from drawing, curvature, corner approximation and welding errors.
- Adjacent inferred size ratio mismatch: median |log(si/sj)| 0.0359, p95 0.1410 (ratios approximately 1.037 and 1.151).
- Signed predictions for the same shared edge disagree by 1.61px median / 6.03px p95.
- Integration edge RMS residual: 2.52px, 37.6% of target depth-increment RMS (6.70px).
- Best-fit integrated quad normals differ from target local normals by 6.86° median / 16.49° p95, maximum 47.69°.
- The diagnostic patch depth range is 123.99px. This is an assumption-dependent result, not an accuracy measure or recovered metric size.

## Locally generated artifacts

Raw PLY meshes and `selected_patch_data.json` coordinates are local outputs, not committed assets. The runner refuses to overwrite a nonempty output directory. The five regression tests read an explicitly supplied run directory; they do not write to it.

- `source_normals_depth_comparison.png`: original selected source view and exact support, optimized local normals, integrated depth, best-fit integrated normals, normal discrepancy, reflected depth. The normal maps are computed estimates, not ground truth. Missing cells stay blank.
- `conditional_patch_mesh_preview.png`: actual computed open patch, both reflection branches.
- `conditional_patch_A.ply`, `conditional_patch_B.ply`: 370 vertices / 476 triangles each. Every detected quad is split along its fixed 0–2 diagonal. No added vertices, hole filling, back surface or unseen parts. Branch B reflects A in the viewing plane. This pair does **not** exhaust the unidentifiable sign fields.
- `synthetic_cylinder_ambiguity.png`: the exact-square negative-control failure.
- `selected_patch_data.json`: exact support, local gradients, optimized signs and mean-centered depths.
- `fixture_tests.json`, `measurement_summary.json`, `cell_measurements.json`, `integration_report.json`: quantitative results.
- `run_experiment.py`: full deterministic experiment.
- `test_experiment.py`, `unittest.log`: five independent tests, all passed, including optimizer enumeration and PLY projection/reflection verification.

PLY coordinates use the supplied nominal convention: 512-pixel views, scale 256, center 256, z-up, view-0 camera on -Y, nominal 45° yaw increments. World pose and depth zero are conventions, not calibration results. This experiment uses single-view cell geometry and does not invent cross-view correspondences.

## Reproduce

From the repository root, install this experiment's pinned dependencies and the marker-consistency detector's existing dependencies. Choose new or empty output directories outside the source tree:

    python -m pip install -r experiments/square_shape/requirements.txt
    python experiments/marker_consistency/source/quad_cells.py \
      --input docs/experiments/17-classical-pear/input.png \
      --output /tmp/pear-square-quads
    python experiments/square_shape/run_experiment.py \
      --atlas docs/experiments/17-classical-pear/input.png \
      --quad-graph /tmp/pear-square-quads/quad_graph.json \
      --output /tmp/pear-square-shape
    python experiments/square_shape/test_experiment.py \
      --output /tmp/pear-square-shape

If the Python plotting cache is not writable, set `MPLCONFIGDIR` and/or `XDG_CACHE_HOME` to writable cache directories before running. For unittest discovery, set `SQUARE_SHAPE_OUTPUT` to the generated run directory and use `python -m unittest discover -s experiments/square_shape -p 'test_experiment.py' -v`.

All three runner paths are explicit. The run only writes to `--output`; atlas and detector outputs stay read-only. Importing the runner performs no experiment, plotting setup or filesystem writes. Each fixture invocation starts with the same seed (20261105), so repeated calls do not consume shared random state. The five tests retain their original fixture assertions and measured thresholds. Small floating-point or solver-version differences can occur on a different platform; raw source input hashes are recorded for comparison.

No learned depth, neural 3D model, anatomical modeling, new ImageGen, credentials, external transmission or hidden completion are part of this experiment. Generated outputs must not be added to version control.

**Stop condition reached:** This one controlled square-prior/sign-smoothness formulation is tested and falsified as a reliable shape estimator here. Extending it would require independently supported square geometry and additional sign/depth evidence, not more arbitrary smoothing or manually choosing a desired surface.

## Published evidence

Selected summaries are in `records/`. [Source, inferred normals and depth](../../docs/experiments/18-square-tilt/source-normals-depth-comparison.png), [both conditional open patches](../../docs/experiments/18-square-tilt/conditional-patch-mesh-preview.png), and [the exact-cylinder ambiguity](../../docs/experiments/18-square-tilt/synthetic-cylinder-ambiguity.png) are committed as images. Raw inferred coordinates, patch models and arrays remain local, not in Git. These are failed/conditional mathematical demonstrations, not a validated pear reconstruction.
