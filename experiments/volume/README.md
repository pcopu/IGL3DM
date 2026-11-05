# In-house differentiable shared-volume reconstruction

This optional CPU experiment uses the existing turnaround's segmented silhouettes and gated software-depth estimates to optimize **one shared 3D signed-distance field**. It does not use TripoSR, an image-to-mesh model, anatomical templates, per-part manual edits, or painted-line vertex IDs.

## Algorithm and controls

- Convert the baseline 80³ occupancy into a Euclidean signed-distance field, positive inside, and resample to 64³.
- Optimize a 24³ control field, trilinearly upsampled to 64³, with `0.1*tanh(delta)` displacement bound. The bound limits field offsets, not pointwise mesh vertex motion.
- Use four deterministically sampled orthographic views per step, 64² ray images, 112 depth samples from camera distance 2.5 to 5.5, sigmoid density beta 0.004 and scale120.
- Minimize silhouette MSE +4× accepted training-depth squared error (clamped at0.25), plus offset-gradient and magnitude regularization. No RGB or texture objective.
- Use only `valid_mask & fit_train_mask` and accepted view weights for depth fitting. Four accepted views are required; that count is not sufficient proof of good angular coverage.
- Extract with marching cubes. Keep all raw components; automatic largest-component cleanup is a separate recorded operation.
- Render actual meshes in Blender at192² from16 source cameras and16 unseen yaw midpoints. Report actual ray-mask IoU, depth residual and coverage, not just the optimizer's soft-render scores.

Scope: the current implementation explicitly supports the sixteen-view level orthographic rig, yaw0 through337.5° in22.5° steps, scale2, distance4. Other camera rigs reject rather than being silently misinterpreted. The baseline renderer supports more general rigs separately.

## Original input results

No new generation. Same source as [the original atlas](../../docs/experiments/01-atlas-baseline/input.png), and DA3 Small308 depth accepted on views0–3 and12–15.

| Actual mesh | Source IoU | Training-depth MAE | Spatial-assessment MAE | Components |
|---|---:|---:|---:|---:|
| Baseline | .848219 | .041473 | .041694 | baseline |
| Resampled initial | .847422 | .041225 | .041572 | 2 |
| Unconstrained64³ control | .843178 | .020765 | .031706 | 177 |
| Smooth24³ control + depth | .852281 | .021324 | .027221 | 5 |
| Smooth24³ silhouettes-only | .855169 | .046463 | .047066 | 7 |
| Smooth + depth, largest component | .852145 | .021324 | .027221 | 1 |

The preferred cleaned variant improves IoU by.003925 absolute and agreement with its software-depth prior by34.7%. The silhouette-only control fits outlines better but depth worse. Dense unconstrained optimization creates177 components and worsens actual outline fit, despite a flattering soft-render score. It is retained as a failed control.

The cleaned variant has10,744 vertices /21,496 triangles, consistent winding and watertight edge incidence. Cleanup removes100 faces across four small components, volume.00013136. Depth assessment coverage is99.9833%; missing rays are excluded and explicitly counted.

## Dense-contour input results

Same algorithm and240 steps, but the [dense-contour input](../../docs/experiments/10-dense-contours/input.png) and gated V2 Small518 depth. DA3 accepted only two views and was rejected. V2 accepts views0,1,2,5,6,13,14,15 with uniform support weights; this differs from DA3 confidence weighting.

| Actual mesh | Source IoU | Assessment-depth MAE | Assessment coverage |
|---|---:|---:|---:|
| Dense baseline | .857248 | .111215 | 100% |
| Resampled initial | .855006 | .111352 | 100% |
| Smooth + V2 depth, cleaned | .855622 | .093925 | 99.3347% |
| Matched silhouettes-only | .864213 | .115404 | 99.8609% |

Depth improves agreement with its own target by15.55% but worsens silhouettes. This is a tradeoff, not a clear overall geometry gain. Cleaned depth geometry has12,515 vertices /25,046 triangles in one watertight, consistently wound component. Cleanup removes one effectively zero-volume eight-face component; six near-zero-area faces were confined to it.

## Geometry review and limits

[Original clay turntable](../../docs/experiments/11-shared-volume/clay-turntable.gif) · [Original source views](../../docs/experiments/11-shared-volume/clay-comparison.png) · [Original unseen midpoints](../../docs/experiments/11-shared-volume/clay-midpoints.png)

[Dense clay turntable](../../docs/experiments/11-shared-volume/dense-clay-turntable.gif) · [Dense source views](../../docs/experiments/11-shared-volume/dense-clay-comparison.png) · [Dense unseen midpoints](../../docs/experiments/11-shared-volume/dense-clay-midpoints.png)

Geometry is recognizable but coarse and lumpy, with poor facial detail, imperfect limb separation and small surface artifacts. Dense painted contours have not become recovered surface detail. Neither result is production-quality or animation-ready. Self-intersections have not been directly tested. Clay lighting changes appearance only, not vertices or normals.

Depth targets were affine-aligned to imperfect baseline meshes, and view gates used spatial-assessment statistics. Assessment pixels are excluded from fitting, but this is **not blind validation** or evidence of ground-truth3D accuracy. No independent true-depth or unseen-view reference exists. Midpoint renders prove that one common mesh exists, not that hidden anatomy is correct. Errors from different priors/sources/supports cannot be ranked directly.

## Reproduce

Optional dependencies: PyTorch CPU, NumPy, SciPy, Pillow, scikit-image and trimesh. These are separate from baseline dependencies. The measured environment uses four CPU threads and PyTorch2.6.0+cpu. No weights are needed by the volume solver itself. Generate the baseline and run the documented software-depth/alignment steps first.

```sh
python experiments/volume/fit_volume.py \
  --source-run runs/lion-002 --depth-prior path/to/aligned_depths.npz \
  --output-root runs/volume --name depth --control 24 --iterations 240
python experiments/volume/cleanup.py --input runs/volume/depth/final --output runs/volume/depth/cleaned
blender -b -t 4 --python-exit-code 1 --python scripts/render_mesh.py -- \
  --mesh runs/volume/depth/cleaned/mesh.json --output runs/volume/depth/cleaned/renders \
  --size 192 --views 16 --midpoints --material clay
python experiments/volume/evaluate_run.py \
  --source-run runs/lion-002 --depth-prior path/to/aligned_depths.npz \
  --model baseline=runs/lion-002/renders \
  --model fitted=runs/volume/depth/cleaned/renders --output runs/volume/results.json
# Use a fresh name and --depth-weight 0 for the matched silhouette control.
PYTHONPATH=src python -m unittest discover -s tests -v
```

Runs refuse to overwrite a nonempty directory, validate camera/data shapes and disjoint masks, reject inadequate depth support, mask nonfinite target data, and hash input occupancy/prior arrays. Primitive sphere tests validate depth convention, positive radius gradients and convergence independently of the lion. Validation hardening happened after the first measured experiments; retained records and local outputs are unchanged. Portable-source reproduction is checked separately.

`records/` contains configurations, loss histories, metrics, integrity and primitive checks, including failures. Public Git contains source, reports and PNG/GIF evidence only. Models, checkpoints, arrays and environments are excluded.

Portable-source regression: the full original 240-step run was repeated after integration and validation hardening. Its final SDF array is exactly equal to the retained original experiment (maximum absolute difference0.0). Default dependency tests pass16 and skip the3 optional volume tests; the documented optional environment passes all19.

## Rejected smoothing control

A bounded generic ablation applies `--initial-sigma 1` to the64³ initial SDF, Gaussian sigma0.03125 world units with nearest boundary extension. Smoothing-only yields IoU0.837015; the same depth optimization yields0.824367 raw and0.813528 after largest-component cleanup, compared with the prior preferred0.852145. The small software-depth residual improvement (0.027221→0.026394 raw) does not offset lost outline agreement and a detached tail tip. Cleanup deletes that meaningful fragment. The option remains **off by default** and is recorded to reproduce the failure, not recommended.

[Geometry comparison](../../docs/experiments/12-smoothing-control/clay-comparison.png) · [Turntable](../../docs/experiments/12-smoothing-control/clay-turntable.gif). Full metrics, components and loss history are retained under `records/presmooth-*`. Soft-render IoU0.861331 versus actual mesh0.824367 exposes an extraction/rendering mismatch; future work must measure real mesh output rather than trusting the soft score.

[Rejected unconstrained-field actual mesh](../../docs/experiments/11-shared-volume/unconstrained-failure.png) shows the fragmented control under the same neutral clay lighting.
