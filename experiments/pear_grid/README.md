# Generated solid pear: software quad IDs and classical reconstruction

## Scope and result

One ImageGen call supplied eight views of a white, solid, slightly bent pear with a shallow side dent and a dense black quad grid. No colors, IDs or labels were requested from ImageGen. Software assigns its own IDs afterward. Source SHA-256: 28e2a918f97b80499b99529f2922a2e783896bc2436de55caf40d17a24342e75.

Everything after generation is classical image processing and geometry: connected components, quad approximation, constrained corner welding, shared-edge graphs, SIFT descriptors, adjacency votes, linear triangulation and robust least-squares camera fitting. No learned depth, neural 3D prior, hand-shaped surface or silhouette-derived hidden completion is used in the grid-derived result.

**Outcome: actual software-tagged cells, triangulated candidate points and a fragmented partial quad mesh, not a successful pear reconstruction.**

## Detection and candidate identity

Detected closed quads per view: 489, 470, 473, 464, 469, 461, 473, 458. These are closed white regions approximated as convex quads, not a guarantee that every true visible cell was detected. Thin or occluded cells, broken lines, merged regions and rasterization can be missed or misclassified. The generated image has no ground-truth count, so its true missing-cell rate is unknown.

Local cell/corner IDs are assigned in each view. Corner welding cannot merge two corners belonging to the same cell. Shared edges create explicit cell neighborhoods. Across adjacent views, mutual descriptor matches need a consistent neighboring matched cell; a corner needs votes from at least two matched cells and no competing destination. Missing support ends a track. Hidden points are not invented and identities are not automatically reattached after occlusion.

There are 320 candidate corner tracks: 207 span two views, 77 three, 15 four, 9 five, 5 six, 6 seven and 1 eight. These are candidate physical identities only. Long tracks can slip across repeated cells. A point does not need full-orbit visibility: two nondegenerate views permit triangulation and a third offers a check.

## Actual point and partial-face output

Nominal cameras: level orthographic, 45-degree yaw increments, 512-pixel cells, scale 256 pixels/world unit, center (256,256), Z-up, yaw-zero camera on negative Y. Scale is relative.

- 320 candidate 3D points were fitted; observations, conditioning and errors are retained.
- Only 7 have three-view prediction p95 <=3 pixels, conditional on assumed cameras and candidate identity.
- 93 quad faces have the same four candidate IDs and cyclic connectivity observed in at least two views. These were assembled algorithmically, not manually modeled.
- Zero of these faces have all four corners passing the three-view check. Many corners have only two-view evidence, so not qualified does not always mean a measured inconsistency.
- No unseen faces, holes or disconnected regions were filled. No smoothing or learned completion was used.

Local outputs in quad_cells/: candidate_points.ply, candidate_patch_mesh.ply, candidate_vertices.json and candidate_patch_mesh_report.json. Model-like coordinates remain local. Publish source, previews and compact diagnostics instead.

Selected images: software_tagged_detail.png (legible adjacent-view tags), software_tagged_cells.png (all detections), triangulated_candidate_points.png (actual inferred points), and candidate_patch_mesh_preview.png (actual partial topology).

## Camera estimation attempt

estimate_cameras.py jointly fits 90 calibration tracks and seven cameras, estimating yaw, elevation, roll, effective orthographic image scale and center offsets. The 45-degree sequence is a prior. Camera 0 fixes the scale/orientation/translation gauge. Physical perspective focal length and camera distance cannot be separately identified under this orthographic model and are not claimed.

A deterministic 20% identity-level split reserves 23 tracks from camera fitting. Views 1 and 5 are withheld from the reserved tracks' point triangulation.

The first 100-evaluation run and a vectorized 400-evaluation retry both reached iteration limits. Several yaw corrections hit their +/-30-degree bounds; minimum view spacing collapsed to 4.92 degrees. These are not accepted camera calibrations.

On the same 12 held-out observations before/after, median error changed from 42.88 to 18.86 pixels, p95 from 78.24 to 46.78. Total evaluable coverage fell from 22 observations to 12 because conditioning worsened. Low calibration-training median error (1.19 pixels) did not establish accurate held-out geometry. The camera-adjusted cloud is separate and is not used for the nominal-camera 93-face mesh.

## Independent known-rendered controls

A separate analytic asymmetric pear was rendered in Blender with a true shared quad mesh, exact cameras, 3D coordinates and ray-tested visibility. Its geometry never supplies the generated pear's missing surface.

An initial subpixel-line render detected no closed cells and is retained as a failed rasterization control. The corrected line width gave 126-147 detected cells per view. Of 204 propagated candidates, 203 changed known physical vertex identity and 1 was unresolved under a 3-pixel nearest-visible-vertex evaluation tolerance. The present 45-degree-jump repeated-cell matcher is therefore not qualified even on a consistent render. Its failures cannot all be attributed to ImageGen.

A separate 64-frame control used genuine 5.625-degree rendered steps and adjacent-frame optical flow. Among 806 tracks spanning at least three samples, 200 retained correct known identity, 599 switched and 7 were unresolved. The correct subset triangulated to median 0.00823 world-unit error (control height 2.4). However, 100 wrong tracks still passed a 3-pixel held-out test. See ../VIDEO.md.

This separates working cell tagging and correct-correspondence triangulation from the still-unreliable physical correspondence decoder. Camera adjustment cannot repair arbitrary identity swaps.

## Reproduce

Run from the experiment root:

    python experiments/marker_consistency/source/quad_cells.py --input docs/experiments/17-classical-pear/input.png --output runs/pear-new-quads
    python experiments/marker_consistency/source/build_candidate_patches.py --directory runs/pear-new-quads
    python experiments/marker_consistency/source/estimate_cameras.py --vertices runs/pear-new-quads/candidate_vertices.json --output runs/pear-new-camera-fit --max-nfev 400
    python -m unittest discover -s experiments/marker_consistency/source -p 'test_*.py' -v

Known rendered control:

    blender -b --factory-startup --threads 4 --python-exit-code 1 --python experiments/marker_consistency/source/render_known_pear.py

Eighteen regression tests pass across geometry, degeneracy, held-out isolation, identity gating, junctions, quad detection/welding, camera projection and actual video decode/occlusion termination. They do not substitute for the failed end-to-end correspondence control.

## Published display and numeric controls

[Actual unvalidated square patches](../../docs/experiments/17-classical-pear/unvalidated-square-patches.gif) are rendered with unchanged320 candidate vertex coordinates. Each of93 observed quads uses the explicit display diagonal `[a,b,c]`, `[a,c,d]` (186 triangles). No hidden geometry is completed; the choice of diagonal matters for nonplanar candidate quads. The display camera matches the nominal scale2, z-up rig. `prepare_quad_render.py` reproduces this conversion and rejects overwriting or invalid input.

The [separate silhouette-only envelope](../../docs/experiments/17-classical-pear/silhouette-control-only.gif) is **not** square reconstruction. It fits outlines but misses the inward dimple. Its first2px-gutter run rejected thick border contamination; one common6px gutter fixes segmentation without per-view fitting. A numerical marching-tetrahedra issue produced16 tiny boundary edges; generic exact-collinearity edge subdivision repairs them without moving any vertex, changing surface area, volume or actual silhouette scores. The closed control has36,800 vertices /73,596 triangles and zero boundary/nonmanifold edges.

The public record deliberately omits raw inferred3D coordinates, faces and ground-truth arrays. Source, configuration, summary metrics and selected images suffice to reproduce the local experiment without publishing model artifacts. The known analytic control is only a software fixture and never supplies the generated pear's missing geometry.

A prior software-depth trial completed before the new strictly mathematical restriction arrived. It was stopped, archived locally and excluded from every result in this mathematical experiment. No learned prediction constrains these points, faces, cameras or controls.
