# Automatic surface completion: cloud experiment

## Outcome and boundary

This is a **software-driven completion method and controlled failure study**, not a reconstruction of the user's video. It is distinct from camera calibration and silhouette carving: it fits the log radius of reconstructed 3D points with spherical harmonics and exports an untextured, closed triangular surface. It needs candidate points from an independently evaluated camera pipeline. No manual animal modeling, model weights, image generation or external dependencies were used.

The latest input was resolved as Library `libfile_4cc138c77e8881919866ed981ed9d52c`, `shared-existing-output.mp4`, version 0, 10,406,054 bytes. The current Library helper was retrieved through its skill and invoked once via the supported signed-transfer route. It returned `library file transfer failed: download failed` (exit 1); `/workspace/inputs/shared-existing-output.mp4` does not exist. The supplied host `sdmntprcentralus.oaiusercontent.com` is absent from this executor's enforced restricted network allowlist. This is a likely network-policy cause, **not a confirmed HTTP error**, because the helper suppresses details and network diagnostics returned null. No alternate URL, proxy bypass or transfer retry was attempted. No signed URL, token or credentials are recorded here.

Remote main was checked repeatedly during this run and remained `b7bc5788bf5f49eb5b6134e9e6963ce6b8321f57`. Its checkout contains no current MP4 or baseline 555-face candidate point arrays. Thus the 241-frame / 840×1124 / 24fps description is parent-provided, not independently decoded here. The 555-face and 614-point/260-quad results are parent-reported and were not reused as geometry. The requested real pear deliverable remains blocked pending accessible video and/or reconstructed point records. No real geometry quality or completion claim is made.

## Method and assumptions

`complete.py` accepts a JSON array of `xyz` records (the existing candidate_points format) or an Nx3 array and an explicit interior center in the same coordinate gauge. It solves penalized least squares for log radius using a real spherical harmonic basis. The penalty is `[l(l+1)]²`, normalized by point count; exponentiation gives positive radii. A Fibonacci sphere triangulated by a convex hull supplies fixed closed connectivity; vertices are displaced radially by predictions. There are no textures or colored squares.

Assumptions: one radial intersection from the selected center, closed genus-zero surface, consistent scale and coordinates, sufficiently representative points, and no stems/overhangs requiring multiple ray intersections. The center is a required modeling assumption, not automatically validated as an interior point. Equal point weighting can overweight densely tracked regions. Outliers and camera gauge distortion can bias the entire surface. Spherical sampling limits detail and does not recover metric scale. This method can represent star-shaped concavities **when observed**; it cannot identify unseen dents. Watertightness is a construction property, not evidence of fidelity. Real-world leaves, stems and non-star-shaped shapes are unsupported.

The CLI stores per-vertex nearest-observation angular distance in `support.npz`; this is a coverage indicator, **not calibrated uncertainty**. Counts over 20° are reported without pretending 20° is a validated acceptance gate. Topology checks cover edge incidence, winding, connected components, Euler characteristic, triangle degeneracy and signed volume. There is no general self-intersection detector; positive radial construction over a convex spherical triangulation supplies the non-crossing prior when all radii are finite and positive. The CLI rejects nonfinite data, invalid radii and overwrite of existing output directories.

## Experiments and measured failures

`controls.py`: four analytic shapes (sphere, ellipsoid, asymmetric tapered pear, pear with a narrow concave dent), 600 nominal sample directions, 0.5% radial Gaussian noise, missing caps of 0°, 35° and 65°, convex radial baseline and harmonic degrees 4/8/12 at lambda 1e-4. This is 48 cases, plus an injected 30% depth-scale distortion. Evaluation uses 4,096 independently sampled directions. These are **completion-only controls**, not end-to-end video, tracking or camera controls. Analytic control functions never fill a real reconstruction.

All 48 generated meshes have 4,096 vertices, 8,188 triangles, one component, Euler 2, zero boundary/nonmanifold edges, zero winding disagreements and zero degenerate triangles. Local control PLYs are ignored and are not user-object deliverables.

| Control / missing cap | Convex radial p95 | Degree 8 radial p95 |
| --- | ---: | ---: |
| Sphere / 65° | 0.5350 | 0.00218 |
| Ellipsoid / 0° | 0.00979 | 0.02907 |
| Pear / 65° | 0.32386 | 0.04691 |
| Dented pear / 35° | 0.02544 | 0.03816 |

Units are absolute radial distance, with characteristic radius about 1; these are not pixels or real-object physical units. The smooth prior beats a flat convex cap on broad missing smooth regions, but underfits fully observed ellipsoids at this regularization. On the hidden 35° dent, degree 8 has hidden-region p95 **0.13990** and maximum **0.19105** despite zero holes. Convex completion happens to cut closer to that dent (hidden p95 0.06367), but this is not evidence it recovered the concavity. Its missing 65° region is badly flattened. A 30% injected depth stretch gives degree-8 p95 error **0.19749**: closure does not repair a wrong camera-derived shape.

`sweep.py`: 60 configurations (degrees 4/8/12/16 × five lambdas × three missing caps), 900 nominal points, fixed visible back cap held out for hyperparameter selection, then refit all observed points. This selection uses no hidden ground truth. Truth is used only for evaluation. Results:

| Missing cap | Selected degree / lambda | Visible holdout RMSE | All-direction p95 | Hidden p95 | Maximum |
| --- | --- | ---: | ---: | ---: | ---: |
| 0° | 16 / 1e-5 | 0.00403 | 0.00856 | n/a | 0.05654 |
| 35° | 8 / 1e-5 | 0.00364 | 0.00997 | 0.13402 | 0.18550 |
| 65° | 8 / 1e-5 | 0.00358 | 0.03710 | 0.10340 | 0.22435 |

**Visible holdout success does not validate a hidden dent.** Increasing degree alone cannot create missing evidence. The sweep shows a possible practical regularization selector, not a universally selected real-input configuration. Ground truth, noise seeds, exact choices and failures are retained in JSON.

## Reproduction and artifacts

Environment: Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, existing Matplotlib and Pillow. No installation performed. `scipy.special.sph_harm_y` is required (older SciPy may lack it). No applicable AGENTS.md or repo `.agents/skills` was found; `/workspace/.agents` was empty. Matplotlib initially warned about unwritable default cache directories; the rerun uses `/tmp/igl-mpl`. A fontconfig warning did not prevent output.

From the repository root:

```sh
OPENBLAS_NUM_THREADS=1 python -m unittest discover -s experiments/surface_completion -p 'test_*.py' -v
MPLCONFIGDIR=/tmp/igl-mpl OPENBLAS_NUM_THREADS=1 python experiments/surface_completion/controls.py
OPENBLAS_NUM_THREADS=1 python experiments/surface_completion/sweep.py
# After compatible independently reconstructed points are available, choose and justify center:
OPENBLAS_NUM_THREADS=1 python experiments/surface_completion/complete.py /absolute/candidate_points.json /absolute/new-output-directory --center 0 0 0 --degree 8 --regularization 0.00001
```

The last command is an **integration example, not a completed real run**. Zero is valid only if the supplied point gauge supports that interior center. Do not choose it blindly.

Four unit tests pass: exact constant-radius recovery with translation, closed connected oriented topology, invalid input rejection, and the unseen-dent ambiguity counterexample. The diagnostic mesh previews were inspected. `results/completion_controls.png` shows the completed control surfaces; `results/hidden_dent_section.png` compares the true and inferred equatorial sections. Machine-readable results: `results/controls.json`, `results/regularization.json`. `results/environment.json` pins runtime versions.

## Next integration checks

1. Obtain authorized video bytes in this consumer executor, verify hash and decode metadata; alternatively fetch the parent's explicitly committed video when available. Do not substitute another turnaround.
2. Consume candidate points from the independently validated camera/endpoint-join pipeline; preserve coordinate gauge and point-to-observation identity. Evaluate a center sweep and outlier/coverage sensitivity before selecting any completion.
3. Fit only training points, predict spatially withheld observed points, render against independent real frames and measure silhouettes and marker reprojection. Explicitly separate observations, interpolations and unsupported completion.
4. Compare regions across camera hypotheses. A closed texture-free model may be an honest approximate deliverable, but cannot be called geometrically validated based on current controls.

Original audio, raw model files, arrays and video bytes are excluded from this branch's commit. The repository's existing ignore policy remains unchanged. Source, metrics and diagnostic figures are committed on `cloud/automatic-surface-completion`; main is untouched.

## Follow-up: measured dent coverage and center sensitivity

The parent's later silhouette-hull and camera-plus-point results motivated a distinct follow-up, `support_sensitivity.py`. No real input was available for this test. We used 900 nominal noisy observations of the analytic dented pear, 4,096 exact held-out surface points, degree 12 and lambda 1e-6 fixed in advance of this run. Five missing front-cap sizes and seven centers (origin; ±0.2 along each axis) give 35 completion cases. The error is predicted radius minus exact radius along each ray from the assumed center through a known test point. It does not use approximate nearest-neighbor surface distance. Center variants are sensitivity cases, not a ground-truth-tuned choice for the real object.

The evaluation region is the same fixed 20° dimple cap for all cases, unlike the earlier table whose hidden region changes with missing-cap size. Units remain control radius units. These numbers therefore should not be compared directly to the earlier hidden-region p95 values.

| Missing measured cap | Origin-center dimple p95 | Range across seven centers |
| --- | ---: | ---: |
| 0° | 0.02015 | 0.00767–0.03834 |
| 10° | 0.06040 | 0.04929–0.08017 |
| 20° | 0.13358 | 0.13358–0.14873 |
| 35° | 0.17238 | 0.17108–0.19275 |
| 65° | 0.19354 | 0.17410–0.23476 |

Measured points in the concavity materially improve this completion on the control; smoothness and center changes do not restore an entirely unobserved dent. Center sensitivity can be substantial even with full coverage. This motivates checking multiple justified interior centers when applying the method to measured geometry. No claim is made that every arbitrary center preserves radial uniqueness on a real shape.

A separate fully covered control with 30% y-axis stretching has nearest-observation angular p95 **4.24°**, zero queries more than 20° from observations, but radial p95 error **0.19979**. Thus the CLI angular-support indicator cannot certify accuracy, even when all regions look well supported. Independent camera/geometry controls remain necessary. This is a deliberately injected distortion, not an evaluated real camera fit.

```sh
OPENBLAS_NUM_THREADS=1 python experiments/surface_completion/support_sensitivity.py
```

The complete 35 cases plus distortion case are recorded in `results/support_sensitivity.json`, seed 814. These 36 follow-up cases add to the earlier 109 configurations. Nothing in this follow-up uses the parent's repeatedly reused real-frame checks as a pristine final test set. Real-video work remains blocked pending the approved input snapshot.

## Renderer-ready known dimple control

A reproducible all-quad evaluation mesh and matched shaded/undented full-rotation renderer are now available. See [DIMPLE_CONTROL.md](DIMPLE_CONTROL.md) for exact paths, parameters, commands and validation. The paired 24-view run verifies dimple-center visibility of 7/24 frames versus 13/24 without the recess. This is a known-geometry control, never real reconstruction geometry.
