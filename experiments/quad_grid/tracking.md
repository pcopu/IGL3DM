# Dense black quad-grid: adjacent-view candidate tracking

Input: corrected single-call eight-view white lion with dense black quad/square surface grid, no labels or colors. Source SHA-256: `7fe9abcb46ff7cc0a9916f0467301c4e7c8d3b84eed661fbe089a3a2bc87a405`. Native atlas 1774 × 887, 4 × 2. It visibly includes the face, mane, limbs, toes and tail. The existing reconstruction pipeline produces the separately requested exploratory mesh; these tracking tests do not block it.

## Automatic procedure

1. Common 512 px cell normalization, no per-subject recentering. Threshold black ink, suppress cell borders, Zhang–Suen skeletonization.
2. Detect skeleton branch/intersection candidates and merge nearby branch pixels. These include T-junctions and drawing artifacts, not only true four-way quad vertices.
3. Compute 24 px SIFT context descriptors at those candidate locations. Adjacent-view mutual ratio matching, followed by support from at least two nearby matches with plausible local displacement/scale. This uses local grid-neighborhood appearance rather than global numbered labels. It does not yet explicitly solve full quad-edge graph isomorphism.
4. Propagate adjacent matches. A missing/ambiguous match terminates its track. No bridge across disappearance, no invented hidden point and no automatic reuse of an identity after reappearance. Track loss cannot distinguish actual occlusion from deformation, viewpoint change or descriptor ambiguity.
5. Check independent direct matching across the third view for three-view feature cycles, and attempt full-orbit closure. Components with two different points from the same view are rejected.
6. Conditional camera diagnostics assume 45° spacing, common level orthographic cameras. These cameras are requested, not measured. Views 1 and 5 are withheld from point fits, but not from feature selection, so this is exploratory testing rather than untouched validation.

## Results

444, 643, 748, 683, 510, 667, 728, 696 junction candidates per view (5,119 total). These are detection counts, not known 3D vertices.

Strict ratio 0.72:
- 52 mutual adjacent context matches, 39 survive local-neighborhood support.
- 39 candidate tracks, all only two views long.
- No independently closed three-view cycle, no full-orbit track, and no held-out prediction available.

More permissive exploratory ratio 0.85:
- 171 mutual adjacent context matches, 151 survive local-neighborhood support.
- 145 candidate tracks: 139 span two views and 6 span three. None spans 4+ views.
- Strongest adjacent pair 2→3 has 95 supported candidates. Pairs 3→4, 4→5, 7→0 have none, so the orbit graph is disconnected.
- Two independently closed feature cycles (views 5, 6, 7), but their requested-camera middle-view prediction errors are about 60.5 px. A cycle in image descriptors is not geometric truth.
- Six fit-held-out observations: median 85.53 px, p95 90.83 px under requested cameras. These could be false tracks, uncalibrated camera/scale/framing, source shape inconsistency, or a combination. Do not call them true 3D error.
- No full-orbit closure is observed. Missing evidence is not scored as zero error.

## Interpretation

The corrected sheet satisfies the requested dense-grid appearance and yields some local candidate support. This particular prototype matcher does **not** yet recover a reliable connected surface grid around the lion. It is not proof that all better methods must fail. Repeated black grid cells can match the wrong neighbors, and the source's actual angle increments are not calibrated. A dense temporal video could reduce adjacent-view change and make propagation more practical; it still needs the same ambiguity, occlusion and geometry checks.

No marker-derived mesh is exported by this probe. The separately generated silhouette mesh remains exploratory, and its displayed grid texture does not establish actual shared surface vertices.

## Reproduce

Requires OpenCV with SIFT, NumPy and Pillow; the already-installed OpenCV 5.0.0 environment was used. No learned model or weights.

```sh
python experiments/marker_consistency/source/grid_tracks.py --input docs/experiments/15-dense-quad-grid/input.png --output runs/grid-tracks-strict --ratio .72
python experiments/marker_consistency/source/grid_tracks.py --input docs/experiments/15-dense-quad-grid/input.png --output runs/grid-tracks-exploratory --ratio .85
python -m unittest discover -s experiments/marker_consistency/source -p 'test_*.py' -v
```

Output must be empty. Ten regression tests pass across the geometry and grid-junction suites. Tests cover thinning/crossing detection and local-neighborhood behavior, but are not an end-to-end detector accuracy benchmark on known 3D surface data.

Selected visuals: `strict/junction_candidates.png` shows detected intersections; `exploratory/adjacent_candidates.png` shows supported local matches. `strict/metrics.json` and `exploratory/metrics.json` preserve full counts, settings and conditional errors. Original input remains unchanged.

## Extended evidence export

The current source also writes candidate evidence, raw match scores, traced/spatial neighborhood graphs, track termination reasons and conditional triangulation diagnostics. Full local evidence preserves inferred3D coordinates; public summaries omit those coordinates in accordance with the no-models publication rule. The candidate graph remains disconnected and should not be described as recovered surface topology.
