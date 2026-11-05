# Independent surface-marker consistency experiment

Predeclared on 2026-11-05, before the eight-view generated image was available.

## Scope

One additional ImageGen call: same lion, eight rigid-pose orthographic views at nominal 45-degree increments. Large uniquely numbered, colored surface-conforming quadrilateral grid patches and a fixed-corner orientation triangle. The image model is asked for consistency; that request is not calibration or evidence. No manually modeled lion, Tripo, learned mesh prior or mesh reconstruction occurs unless the correspondence gate passes. Source reference is the original lion atlas, not a fitted mesh.

## Measurements and order

1. Audit visible marker IDs, duplicates, anatomical placement, color and orientation. An uncertain ID is rejected, not guessed from a desired fit. Occlusion is reported, not used to invent a point. Distinguish four visible boundary corners from four stable physical corner identities.
2. Record image coordinates for defensible corners. Use native source crops and convert all cells to one common 512-pixel coordinate system, with a single global scale, no independent silhouette fitting.
3. Preserve held-out views 1 and 5 (45 and 225 degrees) for evaluation only. Do not adjust cameras, tracks or model using those views. A second explicitly exploratory all-view audit may examine failures, but not retune the fixed test.
4. Under the requested common level orthographic cameras, triangulate each corner by linear least squares from >=2 nondegenerate training views. Report conditioning, training reprojection, held-out reprojection, vertical epipolar error, and three-view loop prediction error. Adjacent and 90-degree/wider pairs are identified separately. These are consistency tests conditional on requested cameras, not calibrated physical accuracy.
5. Reject known duplicate or swapped labels and ID/corner ambiguities before reconstruction. At least three independent visible marker patches per adjacent-view edge and a connected eight-view graph, plus coverage of mane, torso and legs on both sides, are required to use sparse marker geometry. P95 held-out error <=3px, loop error <=3px and epipolar distance <=2px at 512px cells. These are deliberately stringent engineering thresholds, not universal statistical guarantees.
6. If gate fails, stop before dense reconstruction. Do not present nearest anatomical guesses or arbitrary repeated square intersections as stable vertex IDs. If it passes, only sparse measured constraints are justified; surface completion remains underdetermined.

## Controls and caveats

Render a separate analytic ellipsoid with known 3D marker corner coordinates, cameras, visibility and synthetic image projections. This is not a modeled lion and never supplies geometry to the generated test. Test exact/noisy observations and deliberately swapped/warped observations; include a camera-mismatch control. Report known 3D errors only for this control.

Low fitting error can be produced by degenerate correspondences, overly flexible cameras and overfitting. Epipolar agreement alone is particularly weak for level orthographic views: only vertical coordinates are constrained. Synthetic projected-coordinate controls verify validator mathematics, not automatic detection on a real animal. Surface-conforming tiles may curve, so planar-square shape constraints are not assumed. Self-occluded patches and missing views cannot be scored as geometric errors without visibility ground truth.
