# Software depth attached to one shared mesh

The source turnaround is not replaced by an ImageGen-painted depth sheet. This experiment uses software-estimated depth from DA3, Depth Anything V2 and ZipDepth, projects the **same actual mesh vertex IDs** into each view, and tests bounded geometry changes. Drawn dots in different images are never treated as proven common vertices.

## Calibration and rejection

`analyze_depth.py` uses the baseline's real mesh ray-depth maps and source framing. It verifies image registration, erodes silhouette boundaries, excludes unstable visibility, and fits one positive affine relationship per view using Huber IRLS. DA3 provides relative camera-z depth. V2/ZipDepth provide inverse relative depth, so their raw outputs are negated before fitting; this is an approximate ordinal surrogate, not a metric conversion. Their unknown inverse-depth zero offset does not justify a naive reciprocal.

A 12-pixel checkerboard partitions fitting and assessment pixels. Candidate views require Pearson/Spearman ≥0.7, assessment skill over a constant ≥0.35, normalized RMSE ≤0.3 and positive slope. These are exploratory necessary checks, not proof of correct geometry. The assessment pixels are excluded from affine/deformation fitting but used in view gates, so this is **not blind independent validation**.

DA3 confidence is not a calibrated probability; only its top-half stable foreground contributes. V2/ZipDepth have no confidence output and use uniform weights on accepted stable foreground. Their support sets therefore differ.

```bash
python experiments/depth_fit/analyze_depth.py \
  --baseline runs/original \
  --prediction experiments/learned_depth/outputs/full_orbit/prediction.npz \
  --output runs/depth-calibration
python experiments/depth_fit/fit_field.py \
  --baseline runs/original \
  --aligned runs/depth-calibration/full_orbit/aligned_depths.npz \
  --output runs/depth-fit
blender -b --python-exit-code 1 --threads 4 --python scripts/render_mesh.py -- \
  --mesh runs/depth-fit/mesh.json --output runs/depth-fit/renders \
  --size 192 --views 16 --midpoints
PYTHONPATH=src python -m igl3dm.finish runs/depth-fit
python experiments/depth_fit/evaluate_fit.py \
  --fit-run runs/depth-fit \
  --aligned runs/depth-calibration/full_orbit/aligned_depths.npz
```

Optional OpenCV verifies DA3's exact resize. NumPy/SciPy/Pillow are the baseline dependencies. Model inference is separate; no model download or network call occurs here.

## Failed first deformation and safer alternative

`fit_vertices.py` solves regularized normal displacement on the original triangulation. On the lion, the proposed step flipped 1,011 small triangles. Orientation-preserving line search reduced the step to 1/4096, effectively no change. This was rejected as a meaningful refinement.

`fit_field.py` instead accumulates accepted training-pixel residuals into a 24³ displacement field, smooths it, caps node displacement at 0.03 normalized units and applies a conservative global derivative bound of 0.25. Trilinear interpolation moves existing vertices; no vertex or face is added, removed or manually modeled. A final face-orientation check still runs. It does not claim a complete self-intersection proof.

## Measured original-atlas results

Baseline silhouette IoU: 0.848219. All runs preserve 54,160 vertices / 108,324 faces and have zero boundary/nonmanifold edges.

| Depth prior | Accepted view IDs | Assessment RMSE before → after | Final silhouette IoU |
|---|---|---:|---:|
| DA3 Small 308 | 0,1,2,3,12,13,14,15 | 0.056476 → 0.051446 | 0.847961 |
| V2 Small 518 | 0,1,2,6,10,13,14,15 | 0.146960 → 0.142778 | 0.847312 |
| ZipDepth 384 | 1,2,3,6,7,9,10,15 | 0.164873 → 0.160983 | 0.846467 |

The residuals have different model-dependent calibrations/support; do not rank models by their raw magnitudes alone. All fits improve agreement with their own priors but slightly worsen silhouettes. DA3's maximum applied movement was 0.01345 normalized units, with mean 0.00579. Visual changes are modest, not a fidelity breakthrough. The baseline is itself approximate; calibration agreement cannot prove hidden anatomy or correct camera geometry.

A synthetic sphere regression verifies unchanged vertex/face identity, bounded nonzero movement, orientation preservation and edge closure. No new image-generation call was used for these refinements.
