# Dense high-contrast contours: software-depth controls

Date: 2026-11-05. This experiment runs only DA3 Small, Depth Anything V2 Small, and ZipDepth on the new dense-contour atlas. **No additional TripoSR run was made.** The goal is to provide depth priors and diagnostics for the in-house reconstruction software. All earlier inputs, outputs, and main-repository source are preserved.

## Main finding

**DA3 fails on this representation by collapsing the inferred cameras and producing a thin stacked slab.** Every adjacent inferred camera rotation is between 1.11° and 4.92°, with a median of 2.70°. The maximum rotation between any two of the 16 inferred cameras is only 12.87°, although the supplied pictures visibly span a full turn. The absence of a large camera jump is not an improvement. The dense-line DA3 depth maps are also visibly blotchy.

V2 and ZipDepth still produce smoother, semantically plausible relative-depth maps. That is not proof of cross-view geometry, correct contour interpretation, or improved reconstruction. Their raw arrays were handed to the in-house reconstruction work for the same visibility, alignment, and silhouette checks used previously.

This atlas changes shading, color, shape, framing, and contour density together. The experiment does not isolate line contrast as the cause of a model's behavior. Its findings apply to these learned depth estimators, not to the general usefulness of contour constraints in the in-house solver.

## Inputs and measured runtime

Source atlas: `generated_images/exec-1455af38-ad28-4594-834e-b43f2656c1c6.png`.

All 16 square crops were verified ready before inference: `igl3dm/runs/lion-dense-contour-001/views/view_00.png` through `view_15.png`, each 310×310 pixels. Complete image framing is preserved. The same checkpoints, numerical implementations, model preprocessing, CPU float32, four threads, one inter-op thread, and seed zero were reused. DA3 uses its first reference view and receives no camera constraints.

| Method | Network resolution | All 16 inference time | Peak process RAM |
|---|---:|---:|---:|
| DA3 Small | 308×308 | 6.580 s | 1150.0 MiB |
| V2 Small | 518×518 | 17.290 s | 688.9 MiB |
| ZipDepth Base NPU | 384×384 | 1.339 s | 416.8 MiB |

These are single local runs, excluding package setup, checkpoint download, and model loading. They are not controlled throughput benchmarks; other local work may affect timing. No GPU or paid inference service was used. No new image generation or manual geometry was performed by this experiment.

## Arrays and previews

Paths below are relative to the shared workspace root.

- DA3: `igl3dm-depth-experiment/outputs/dense_full_orbit308/prediction.npz`, with `depth` shape `(1,16,308,308)`, confidence, intrinsics, extrinsics, and RGB. `metrics.json` records input hashes, model hash, code revision, and timing. `cloud_views.png` is the **failed raw slab reconstruction**; `depth_contact.png` shows source, relative depth, and confidence.
- V2: `igl3dm-depthv2-experiment/outputs/dense_small_518/prediction.npz`, `inverse_relative_depth` shape `(16,310,310)`, plus ordered `view_ids`. Preview: `depth_contact.png` alongside it.
- ZipDepth: `igl3dm-zipdepth-experiment/outputs/dense_npu_384/prediction.npz`, same inverse-depth schema. Preview: `depth_contact.png` alongside it.
- Four representative views compared across all models: `igl3dm-dense-depth-comparison/software-depth-comparison.png`.
- Complete measurements and four-atlas representation comparison: `comparison_metrics.json` in this directory.

DA3 outputs relative camera-z depth. V2 and ZipDepth output inverse relative depth, where larger means nearer. None is measured distance in meters or automatically calibrated across views. A negative raw inverse-depth slope is expected when fitting against camera-z. Display maps are independently normalized per view and cannot establish metric agreement.

## Diagnostic masks and interpretation

The dense drawing has white body interiors. The older colored-image heuristic, which thresholds RGB and then opens the mask, can erase thin lines before filling the body. Therefore this run's DA3 **diagnostics only** use the existing pipeline foreground masks, nearest-neighbor resized from 192×192 to the output size. The raw model input, prediction, confidence, and camera output are untouched. Mask paths and hashes are recorded in `geometry_metrics.json`.

All inter-model rank comparisons in this new record also use the existing pipeline masks for each of the four atlases. This gives a consistent foreground definition within the new record. Earlier comparison records used threshold/fill-hole masks, so small numeric changes in their re-evaluated agreement scores are expected. Earlier DA3 geometric diagnostics retain their old masks; do not treat their self-depth errors as a strictly mask-matched comparison to this run.

The collapsed dense DA3 solution reports only 1.26% median adjacent-pair self-depth disagreement and at least 72.12% projected foreground overlap. Those apparently favorable values demonstrate why self-consistency alone is insufficient: cameras looking in almost the same direction can align a shallow stack without reconstructing an orbit.

Under the consistent pipeline-mask analysis, dense-input median per-view Spearman agreement is 0.372 for DA3/V2, 0.402 for DA3/ZipDepth, and 0.750 for V2/ZipDepth. The corresponding fine-grid values are 0.780, 0.827, and 0.812. DA3 agreement is substantially worse here. Inter-model agreement is not ground-truth accuracy or cross-view consistency, and ZipDepth shares a DA2 teacher lineage. Per-view values, including negative agreement cases, are preserved in `comparison_metrics.json`.

## Reproduction and provenance

Use `igl3dm-depth-experiment/venv/bin/python` from the workspace root. Historical portable runner names end in `_pattern.py`, but their explicit input-directory argument supports this atlas. New output folders refuse overwriting. Model/checkpoint revisions, licenses, and CPU environment match the earlier DA3/V2/ZipDepth records and are repeated in per-run metrics.

```sh
python igl3dm-depth-experiment/run_depth_pattern.py --input-dir igl3dm/runs/lion-dense-contour-001/views --model small --resolution 308 --threads 4 --views 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 --reference first --output dense_full_orbit308
python igl3dm-depthv2-experiment/run_depthv2_pattern.py --input-dir igl3dm/runs/lion-dense-contour-001/views --resolution 518 --threads 4 --output dense_small_518
python igl3dm-zipdepth-experiment/run_zipdepth_pattern.py --input-dir igl3dm/runs/lion-dense-contour-001/views --resolution 384 --threads 4 --output dense_npu_384
python igl3dm-depth-experiment/analyze_depth_masked.py dense_full_orbit308 --mask-dir igl3dm/runs/lion-dense-contour-001/masks
python igl3dm-dense-depth-comparison/analyze_comparison.py
```

Choose unused output names when reproducing. Only local isolated experiment files were written. No main-checkout edits, commits, or pushes were made.

## Repository integration

The commands above preserve original local provenance. Portable versions are committed as `experiments/learned_depth/run_depth.py`, `experiments/depth_v2/run_depthv2.py`, `experiments/zipdepth/run_zipdepth.py` and `experiments/triposr/run_triposr.py`; configure the documented model source/checkpoint paths before running them. Only selected public input/output images and reports are committed, not models, raw arrays or environments.
