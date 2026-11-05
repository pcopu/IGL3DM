# Global isovalue diagnostic: a real density/extraction mismatch

Two retained ORIGINAL-atlas learned fields were held fixed: the prior smooth24³-control field (unsmoothed initialization), and the sigma1-presmoothed field. No optimization was rerun. For each field, marching cubes extracted the globally offset field `sdf - level` at zero for levels0, -0.002, -0.004, -0.008, -0.012 world units. Negative levels expand the occupied region. All ten raw meshes were evaluated using actual192×192 Blender ray intersections against source silhouettes and the same gated DA3 depth priors. No component cleanup was applied to any candidate.

## All measured levels

| Field | Level | Mean mesh IoU | Heldout depth MAE | Heldout coverage | Components |
|---|---:|---:|---:|---:|---:|
| Smooth | 0 | .852281 | .027221 | 99.9833% | 5 |
| Smooth | -.002 | .854434 | .027141 | 99.9958% | 10 |
| Smooth | -.004 | .855976 | .027259 | 99.9958% | 7 |
| Smooth | -.008 | .857566 | .027992 | 100% | 4 |
| Smooth | -.012 | .856082 | .029254 | 100% | 2 |
| Sigma1 | 0 | .824367 | .026394 | 99.6458% | 6 |
| Sigma1 | -.002 | .835599 | .026391 | 99.7917% | 5 |
| Sigma1 | -.004 | .844406 | .026388 | 99.8500% | 6 |
| Sigma1 | -.008 | .855118 | .027098 | 99.9792% | 9 |
| Sigma1 | -.012 | .857133 | .028569 | 99.9917% | 5 |

Original pre-optimization mesh reference: IoU .848219, heldout MAE .041694,100% coverage. All per-view IoUs, training residuals and coverage are retained in `actual_mesh_metrics.json` and `summary.json`.

## Interpretation

Global threshold shifts recover much of sigma1's lost outline fit without any anatomical modeling. Sigma1 at-.008 improves IoU by .030751 versus its level0 extraction and visibly restores the tail connection. It reaches IoU .855118 with MAE .027098, a small joint evidence-score improvement over the unsmoothed field's level0 extraction (.852281/.027221). It is still a nine-component raw mesh with poor leg detail; this is not a clean production-model result.

For the unsmoothed field, -.002 is the strict joint-score improvement over its own0 baseline: IoU .854434 and MAE .027141. Those gains are small, while component count increases5→10. -.008 maximizes its tested IoU but worsens depth MAE. For sigma1, -.004 is the best strict joint improvement relative to its own0 baseline, but its IoU .844406 remains below the previous unsmoothed preferred model; -.008 is the more useful cross-field tradeoff. There is no universally best threshold across outline, depth and topology.

This supports the density/isovalue mismatch explanation. At SDF-.008 with beta.004, sigmoid density is still about14.3 inverse world units (120×sigmoid(-2)), so a ray can accumulate substantial opacity through geometry that level0 marching cubes excludes. A negative isovalue partially reconciles the extracted surface with this soft renderer. Finite ray/grid sampling also matters; this test does not isolate every source of mismatch. The learned field is not guaranteed to remain an exact distance function, so isovalue offsets are field units, not uniform physical surface displacements.

## Visual checks and topology

`clay_comparison.png` and `clay_midpoints.png` compare unsmoothed0/-.002 and sigma1 0/-.008. `clay_turntable.gif` shows synchronized32-frame actual-geometry rotation. Same gray clay material, flat triangle normals, fixed world-space lighting,192px frames. The existing sigma1 level0 clay renders were reused because geometry is unchanged; other selected clay renders are new.

Inspection confirms sigma1-.008 reconnects the visible tail but also thickens portions of the legs/body and retains rough anatomy. No painted contour lines were treated as vertices. The raw nine components have triangle counts[21340,72,56,16,16,16,16,8,8]. Unsmoothed-.002 components are[21858,68,16,8,8,8,8,8,8,8]. All tested meshes report watertightness and consistent winding; unsmoothed-.002 has two numerical near-zero-area faces, sigma1-.002 has one. Self-intersections were not checked. No tiny components were silently removed.

## Limits and decision

These isovalues were compared on the same source outlines and software-depth targets that guided learning/calibration. Selecting a level from these results is additional fitting/model selection, not independent validation. DA3 priors were affine-calibrated against a baseline and view gates used heldout statistics. No ground-truth3D or unseen-view reference exists. Midpoint renders demonstrate one shared geometry, not correct hidden anatomy.

The diagnostic explains a significant part of the sigma1 failure and identifies plausible globally calibrated extraction levels. Do not automatically replace production/default extraction from this single-atlas test. A principled density-to-surface calibration with independent validation is preferable to claiming threshold tuning solved reconstruction. This bounded diagnostic is complete; no more levels, source images or fitting passes were attempted.

## Source and artifacts

- `../isovalue_diagnostic.py`: standalone bounded extractor/renderer; explicit `--field label=field.npz`, `--renderer`, `--output`; refuses nonempty output.
- `evaluate_run.py`: portable evaluation against supplied source masks and depth prior.
- Selected unchanged-geometry contact sheets/GIF are committed under `docs/experiments/13-isovalue-control`.
- `{smooth,sigma1}/level_*/`: every raw actual mesh, integrity/config/input hashes, Blender numeric maps, camera manifest and model.glb.
- `smooth/level_0p002/clay/model.glb` and `sigma1/level_0p008/clay/model.glb`: selected clay preview meshes. No cleanup applied.
- `component_details.json`: all component sizes, volumes and bounds.

Example rerun to a new directory:

```sh
python isovalue_diagnostic.py --field smooth=/path/to/smooth/field.npz --field sigma1=/path/to/presmooth_sigma1/field.npz --renderer /path/to/render_mesh.py --output /new/diagnostic-directory
```
