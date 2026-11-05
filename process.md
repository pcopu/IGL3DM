# Experiment journal

## Goal and rules

Turn one image-generation call into a decent 3D character using software, without manual agent modeling. Test competing approaches, commit coherent increments, record unsuccessful rounds, and distinguish generated drawings from measured geometry. Exact 1:1 reconstruction is not an assumed capability.

A successful experiment must include an actual mesh, inspected renders, quantitative checks, provenance, and explicit limits. An appealing atlas or GIF alone is not success. Reuse each generated input for software comparisons so generation and reconstruction changes are not confounded.

## 2026-11-05 · Repository inspection

- Starting revision: `34ed9eb` (README-only proposed workflow).
- Prior proposal used three eight-view sheets and an agent refinement phase. Neither was implemented.
- Replaced that proposal with an executable sixteen-view, one-sheet pipeline. Manual agent modeling was removed from the implementation and goal.
- Available runtime: Python/NumPy/SciPy/Pillow and Blender 4.3.2 CPU. No CUDA device or installed PyTorch was observed at this stage.

## Round 1 · Single generated wireframe/cel-shaded lion atlas

**Hypothesis:** one sixteen-view sheet contains enough shared silhouette information for a recognizable common 3D volume.

- One ImageGen call produced a 1261×1247 PNG with a 4×4 grid, nominally yaw 0° through 337.5° at 22.5° increments.
- Input SHA-256: `d6b6381b4baca46d19120e08795cfb8723e9150ac1dd4c27617a0e73593d64c4`.
- The image has painted wireframe lines and body-region colors. These are **appearance**, not decoded vertices, vertex IDs or calibrated depth.
- Cell splitting: rounded shared grid boundaries, two-pixel divider gutters, common square padding. No per-animal rescaling or recentering.
- Working masks: 192×192. Foreground from border-color distance, hole filling and tiny-speck rejection.
- Cameras: assumed level orthographic, scale 2, Z-up, fixed yaws. No measured camera recovery.
- Geometry: 80³ sampled field, signed silhouette distances, 0.6-voxel Gaussian smoothing, largest occupied component, marching tetrahedra.
- Compared all candidate tolerances on the same input:

| Allowed contradictory views per voxel | Minimum supporting views | Mean voxel-footprint silhouette IoU |
|---|---:|---:|
| 0 | 16 | 0.773258 |
| 1 | 15 | 0.835373 |
| 2 | 14 | 0.841801 |

The 14-of-16 candidate was selected for best mean image-space agreement. It had 61,317 occupied voxels; three connected occupied components before cleanup, with ten voxels discarded outside the largest component. No occupied voxel touched the grid boundary.

**Failure found:** the initial extractor removed triangles below an arbitrary area threshold, leaving four boundary edges. Two extremely small but valid triangles had been dropped. This was a software defect, not an image-generation failure.

## Round 2 · Fix tiny-triangle handling and validate actual mesh

**Change:** preserve nonzero triangles instead of rejecting them merely for small area. Reused the exact same generated input; **no second ImageGen call**.

- Final mesh: 54,160 vertices, 108,324 triangles, 162,486 unique edges.
- Boundary edges: 0. Nonmanifold edges: 0. Every counted edge has incidence 2.
- Signed volume: 0.953759 in arbitrary normalized units. Euler characteristic: -2. These checks do not establish anatomical quality or rule out self-intersections.
- Approximate color projection uses front-facing normals and a point z-buffer. Unobserved vertices receive neutral gray. No manually modeled anatomy or painted corrections.
- Blender exported the unchanged geometry to GLB and rendered 16 source yaws plus 16 unseen midpoint yaws. Actual mesh-ray depth and XYZ maps use the same geometry and cameras.
- Blender rendering/data/export took 6.659 seconds in this local run. Reconstruction before rendering took approximately eight seconds. These are observed timings, not general benchmarks.
- **Actual final-mesh silhouette IoU: mean 0.848219, worst view 0.764702.** Computed from pixel-center ray-intersection masks, separately from voxel selection scores.
- Generated a 32-frame turntable GIF with one shared palette, actual-mesh contact sheet, source-vs-mesh comparison and red/green/blue silhouette diagnostics.
- Inspected front and profile renders and all-view silhouette comparison. The lion is recognizable, but surface details are rough, facial texture and wireframe colors smear, and tail/legs/some outlines disagree with source views.
- Regression suite: 10 tests passed, including camera orientation, irregular atlas split, alpha/white-interior segmentation, known-consistent sphere carving, empty-hull failures, tolerance accounting and tiny-triangle closure.

**Renderer implementation checks:** Blender's bundled build lacks OpenImageDenoise; CPU denoising is explicitly disabled. A direct vertex-color-to-output material exports proper unlit GLB vertex colors, unlike the explicit Emission graph initially tested. A synthetic cube renderer fixture passed at level and elevated cameras; ray-map/render-alpha IoU was 1.0 for cardinal views and at least 0.9948 for the elevated midpoint checks. These primitive tests verify code, not the generated animal's correctness.

**Outcome:** working automatic one-generated-atlas-to-mesh baseline, with useful but visibly approximate results. This is not a 1:1 reconstruction, a retopologized asset, or an animation-ready character.

## Next investigations

- Learned multi-view depth and camera pose on this same atlas, with actual CPU/RAM feasibility and license checks.
- Compare reconstructed depth/correspondence quality before using it to fit geometry.
- Separate data derived from the fitted mesh from independent geometric evidence; do not reward self-consistency as if it proved truth.
- If testing a GIF input becomes supported, compare a locked-pose orbit against the static atlas and score the resulting mesh, not the apparent animation smoothness.

No learned-model result is claimed yet. Additional rounds should append actual commands/configuration, source/model versions, input hashes, test results, observed failures and whether another ImageGen call was used.
