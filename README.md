# IGL3DM: Image Gen Led 3D Modeling

**Goal:** one image-generation call produces a multiview reference; software turns it into a useful, inspectable 3D asset. **No manual agent modeling.**

This repository now contains a working CPU baseline, regression tests, and an experiment journal in [process.md](process.md). It does **not** claim exact reconstruction or a solved image-to-3D system.

**Current research focus:** classical reconstruction from detected grid cells and temporal corner tracks, with no learned depth or neural shape prior in the pear experiments. The silhouette pipeline below is an outer-envelope control, not square-derived reconstruction. [Video-grid candidates](experiments/video_grid/README.md) now yield a recognizable partial surface, but only 11 of 252 quads pass the stronger conditional checks. [Static-grid experiments](experiments/pear_grid/README.md) and [square-distortion mathematics](experiments/square_shape/README.md) retain their failed controls. Earlier learned-model comparisons remain archived for comparison, not the current target method.

## What actually runs today

1. Generate one 4×4 atlas of a character at 16 yaw angles, 22.5° apart.
2. Split the atlas at shared grid boundaries, remove narrow divider gutters, and segment foreground.
3. Assume common level orthographic cameras. Do not resize or recenter individual silhouettes independently.
4. Compare strict 16-view intersection with explicitly relaxed 15/16 and 14/16 silhouette constraints.
5. Extract one shared mesh with marching tetrahedra, keep the largest occupied component, and project approximate visible colors.
6. Export colored PLY and GLB. Blender renders the **unchanged** mesh from 16 reference and 16 unseen intermediate yaws.
7. Measure the actual mesh's silhouette reprojection. Produce a real mesh turntable GIF, raw depth/XYZ maps, and a result report.

The first generated lion experiment produced a recognizable, imperfect mesh. Final mesh mean silhouette IoU was **0.8482**, worst view **0.7647**. The mesh had 54,160 vertices / 108,324 triangles with zero boundary or nonmanifold edges by incidence counting. These figures describe image-space fit and mesh integrity, **not 84.8% 3D accuracy**. See the journal for failures, fixes and what has not been checked.

## Quick start

Python 3.10+, NumPy, SciPy and Pillow are required. Blender 4.3.2 was tested for export/rendering. No GPU, model weights, credentials or network are required after dependencies are installed.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v

# atlas.png is the output of one external ImageGen call.
# The tool/service call itself is not bundled in this CLI.
igl3dm atlas.png --output runs/example --imagegen-calls 1 --render
```

The output directory must be new or empty. To run without installing the editable package:

```bash
PYTHONPATH=src python -m igl3dm.cli atlas.png \
  --output runs/example --resolution 80 --image-size 192 \
  --max-misses 2 --imagegen-calls 1 --render
```

A later render-only pass is supported:

```bash
blender -b --threads 4 --python scripts/render_mesh.py -- \
  --mesh runs/example/mesh.json --output runs/example/renders \
  --size 192 --views 16 --elevation 0 --midpoints --save-blend
PYTHONPATH=src python -m igl3dm.finish runs/example
```

`--imagegen-calls` is caller-attested provenance, not something software can infer from pixels. If omitted, the report records it as unknown. The generation service may produce a static sheet, an animation or another format; this prototype accepts a static atlas, and does not assume an animated generation API exists.

## Input contract

Request a single fixed character pose, plain white background, no ground/shadows/text, constant lighting, common scale, level orthographic camera, and enough margin. Use a 4×4 row-major grid: 0°, 22.5°, …, 337.5°. Front is first; positive yaw shows the animal's left-facing profile at 90°. Thin mesh-like lines and cel-shaded colors are useful appearance references, not correspondence guarantees.

Generated files need not divide perfectly into 16 square cells. The splitter rounds shared boundaries, trims the same configurable gutter from each cell and pads cells to a common canvas. This handles one-pixel differences without individually fitting the animals. Segmentation assumes a plain border background or meaningful alpha. A sheet with large labels, thick frames, missing margins or changing pose may fail or reconstruct poorly.

World coordinates are right-handed, Z-up, nominally in [-1, 1]. The yaw-zero camera is on negative Y; positive yaw moves toward positive X. Orthographic scale is 2.0. These are **requested assumptions**, not camera calibration recovered from the images.

## Outputs

- `model.ply`: inferred mesh with approximate RGB vertex colors.
- `renders/model.glb`: portable Y-up glTF, unlit vertex colors.
- `renders/model.blend`: reproducible Blender inspection scene when requested.
- `rendered_views.png`, `reference_vs_mesh.png`: actual-mesh review images.
- `turntable.gif`: actual mesh rotation, including unseen yaws, one shared palette.
- `report.json`: source hash, caller-attested provenance, settings, segmentation, all candidate scores, selected tolerance, mesh integrity and final reprojection scores.
- `renders/data/*.npz`: float32 mesh-ray depth and world-space XYZ, validity mask, face index and camera transforms.
- `renders/data/*_depth.png`: 16-bit preview with explicit shared near/far encoding.
- `renders/data/*_position.png`: world XYZ visualization using one global bounding box.
- `renders/render_manifest.json`: depth/position decoding conventions and timings.

Raw depth/XYZ are generated **from the inferred mesh**. They make that mesh measurable and reusable; they do not add missing evidence or prove it is correct. XYZ maps are per-visible-surface positions, not original vertex IDs. Invalid pixels remain masked/NaN. Display PNGs are not a replacement for raw floats.

## Honest limits

- A painted wireframe cannot establish identical vertices across views. Color-coding arbitrary vertices in ImageGen is not a reliable geometric correspondence protocol.
- Synthetic images can disagree on pose, camera, proportions, tail and facial detail. A relaxed hull deliberately tolerates some conflicting views; the exact tolerance is reported.
- Silhouettes cannot recover hidden concavities, separate every touching limb, or create correct facial topology. Texture projection smears or conflicts when the drawings disagree.
- Keeping the largest component can discard detached details. Discarded voxel counts are recorded.
- Edge incidence checks do not prove lack of self-intersection, anatomical correctness, riggability or game-ready topology.
- No learned depth/correspondence model, semantic template fitting, rigging, UV atlas or high-quality material reconstruction is in this baseline.
- GIF playback alone cannot recover 3D. Frame count is not evidence of geometric consistency. GIF generation, if available, should be evaluated as an alternative source of frames, not confused with the renderer's output GIF.

## Research direction

Prioritize identifiable grid geometry, temporal correspondence, camera calibration and independently checked mathematical reconstruction. Preserve the same generated input when comparing software methods. Only regenerate when testing a specific input hypothesis, and record the prompt, call count, outcome and limitation. Known rendered controls measure false correspondence, not just low reprojection error. Research candidates are not results until they have actually run and been inspected.

Every meaningful round belongs in [process.md](process.md). Source changes, tests and concise result summaries are committed. Each recorded test includes selected generated input and output PNG/GIF visuals under `docs/experiments/`. Mesh files, weights, large raw arrays and machine-local runtime artifacts stay under ignored `runs/`; model binaries are not published. Never commit credentials, private user data or unrelated diagnostics.


## Multiple elevations and held-out views

For an 8-column×4-row sheet containing sixteen +15° views followed by sixteen −15° views:

```bash
igl3dm dual.png --rows 4 --columns 8 --elevation-bands=15,-15 \
  --fixed-misses 4 --output runs/dual --imagegen-calls 1 --render
# Fit only the upper orbit without changing its source framing or cameras.
igl3dm dual.png --rows 4 --columns 8 --elevation-bands=15,-15 \
  --view-range 0:16 --fixed-misses 2 --output runs/upper --render
PYTHONPATH=src python scripts/validate_cross_views.py \
  --mesh-run runs/upper --reference-run runs/dual --output runs/upper-heldout
```

`cameras.json` records every assumed yaw/elevation and original source index. The renderer accepts `--cameras` directly; midpoint generation requires complete uniformly spaced orbits. The combined turntable shows synchronized bands, not a discontinuous jump between elevations. Tolerance selection from voxel footprints remains approximate; use `--fixed-misses` and actual-mesh validation for controlled comparisons.


## Optional learned-model experiments

- [DA3 multiview depth/pose](experiments/learned_depth/README.md): fast CPU inference, rejected full-orbit raw fusion.
- [V2 Small](experiments/depth_v2/README.md) and [ZipDepth](experiments/zipdepth/README.md): independent software depth, with explicit inverse-relative-depth semantics.
- [Shared-vertex depth fitting](experiments/depth_fit/README.md): preserves actual vertex IDs/faces; small bounded changes, no demonstrated silhouette gain.
- [TripoSR](experiments/triposr/README.md): one-view complete-object prior; frontal failure and imperfect three-quarter successes retained.
- [Feature correspondence probe](experiments/features/README.md): tests drawn patterns without treating them as exact vertices.

These runners require their own explicitly documented official source/checkpoints and dependencies. They do not silently download or execute models as part of the baseline CLI. Selected output visuals and failures are versioned in `docs/experiments`; model binaries are not.


## Geometry-only review

Pass `--material clay` to `scripts/render_mesh.py` for neutral gray shading under a fixed light rig. This is a display-only material change; exact depth/XYZ/mask outputs and mesh geometry remain unchanged. The GLB carries a rough gray material but requires viewer lighting. Default vertex-color rendering remains available.

Contour and high-contrast input controls, rejected camera collapse, and fixed-vertex comparisons are recorded in [Rounds 9–10](process.md#round-9--surface-contour-curves-and-fixed-vertex-controls). TripoSR is a comparison only, not the target pipeline.

## In-house shared-volume optimization

The [optional shared-SDF experiment](experiments/volume/README.md) optimizes one volume from the turnaround's silhouettes and gated software depth, without a learned image-to-mesh prior or manual animal modeling. It includes matched no-depth and failed unconstrained controls, actual-mesh evaluation and geometry-only previews. The original source improves both measured constraints modestly; the dense-contour source shows a depth/outline tradeoff. Neither is a production-quality reconstruction.
