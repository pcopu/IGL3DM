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

## Round 3 · Resolution and numerical robustness controls

Reused the original sheet; **no new ImageGen call**. Increased the field from 80³ to 128³ and expanded tolerance comparisons through four contradictory views.

- An early 128³ run exposed exact-zero and float32-coordinate degeneracies in marching tetrahedra. Exact level samples now use one shared vertex; coincident float32 positions are welded and only truly collapsed faces are removed. The repaired mesh has zero boundary/nonmanifold edges.
- Voxel-footprint rasterization previously left sparse diagonal gaps at some image/voxel resolution ratios. It now uses camera-basis-aware conservative footprints.
- That proxy can rank tolerances differently from actual mesh masks. At 128³ it selected one allowed miss, whose actual mean IoU was 0.840205. The explicitly evaluated two-miss mesh reached 0.848718. Added `--fixed-misses` so measured comparisons do not silently rely on the proxy winner.
- Matched comparison: 256×256 working and render images, exactly two misses, same source and cameras. 80³: 53,634 vertices / 107,276 triangles, mean actual IoU 0.846542, worst 0.760403. 128³: 143,776 vertices / 287,584 triangles, mean 0.848718, worst 0.770334.
- The approximately 2.7× triangle count buys only about 0.0022 mean overlap in this comparison. Extra resolution is not a solution to missing/contradictory geometric evidence.
- Added an executable end-to-end test for mesh export, real depth maps, GIF generation, caller-attested provenance and refusal to overwrite results. Added exact-level and float32-weld regressions.

[Higher-resolution output comparison](docs/experiments/02-resolution-control/reference-vs-mesh.png) · [Turntable](docs/experiments/02-resolution-control/turntable.gif)

## Round 4 · Software-predicted depth and pose on the original turnaround

Reused the original sheet; **no new ImageGen call**. Ran official Depth Anything 3 Small/Base on CPU, not image-generated depth. Six controls varied view count, input resolution, model size and reference selection.

- Small 16×308²: 6.399 seconds inference, 1156.4 MiB peak process RSS.
- Small 16×504²: 25.855 seconds, 1985.6 MiB.
- Base 16×308², first reference: 18.131 seconds, 2012.0 MiB.
- Base 16×308², automatic reference: 16.758 seconds, 1984.4 MiB.
- Every full-orbit raw cloud showed detached/duplicated surfaces and severe pose inconsistencies. Increased resolution/model size and automatic reference selection did not repair the orbit.
- These runs establish practical CPU inference, not successful full-mesh reconstruction. Predicted rotations are not ground-truth errors because the source cameras are uncalibrated.
- The raw fusion is rejected. Software depth may still be useful as confidence-gated constraints on one shared mesh with an explicit camera model.

Exact revisions, licenses, hashes, setup, controls and measured results: [learned-depth experiment](experiments/learned_depth/README.md). [Research survey](docs/research.md).

![Rejected full-orbit learned-depth cloud](docs/experiments/03-learned-depth/small-308-rejected.png)

## Round 5 · One atlas with above/below camera bands

A second ImageGen call produced a single 1774×887, 8-column×4-row atlas. The first sixteen cells request a full orbit at +15° elevation; the next sixteen request the matching orbit at −15°. It contains part colors, visible wireframe and vertex-like dots. These marks are not decoded 3D vertices.

- Reconstructed upper-only, lower-only and combined views from the same atlas, with no per-view recentering/scaling and no manual geometry.
- Used 80³ fields, 192×192 masks/renders, and the same 12.5% miss tolerance: 2/16 for each single band, 4/32 combined.
- All three meshes have zero counted boundary or nonmanifold edges. Combined mesh: 47,684 vertices / 95,372 triangles.
- Upper-only fitted-band mean IoU: 0.806490. Its held-out lower-band score: 0.782265. Across all 32 views: 0.794378.
- Lower-only fitted-band mean IoU: 0.806622. Its held-out upper-band score: 0.764792. Across all 32 views: 0.785707.
- Combined mean IoU: 0.789783; worst view 0.650234. This is below the upper-only mesh's all-view score, so the additional constraints did not improve this controlled result.
- Visual inspection shows a recognizable but smeared lion, inconsistent rear/front transitions and uncertain camera spacing/elevation. Requested angles are not measured angles. Parts and character design also differ from the original atlas, so this is not a pure same-character comparison to Round 1.
- Added explicit camera manifests, multiple elevation bands, source-index-preserving subset tests, paired-band turntables and cross-view validation. Blender's Python exit code is explicitly set so render-script errors cannot masquerade as success.

![Above/below reference and actual mesh](docs/experiments/04-dual-elevation/reference-vs-mesh.png)

[Input](docs/experiments/04-dual-elevation/input.png) · [Synchronized actual-mesh turntables](docs/experiments/04-dual-elevation/turntable-bands.gif)

## Clarification · Software depth, not painted depth

A proposed paired RGB/generated-depth sheet was superseded by the clarified objective: run **software depth estimation on the original turnaround**, and associate it with the same actual shared-mesh vertices. Generated grayscale values are not the requested depth source. No generated-depth reconstruction is accepted or claimed. One such input had already been generated; it is preserved as [an abandoned input](docs/experiments/05-abandoned-generated-depth/README.md), not a successful test. Total generation calls through this point: three, of which two supplied reconstruction inputs and one was abandoned.

Next: validate calibration/visibility/confidence for software-predicted depth before allowing it to deform the common mesh. Preserve vertex IDs in that mesh; do not claim identity correspondence for dots invented in separate source drawings.

## Published experiment evidence

Source and output visuals are versioned under [docs/experiments](docs/experiments), with hashes in [assets.json](docs/experiments/assets.json). Images and animated previews are included; mesh files, model weights, raw large arrays, environments and unrelated data are excluded. Machine-readable results and concise failed-experiment records are part of the journal, not just favorable screenshots.
