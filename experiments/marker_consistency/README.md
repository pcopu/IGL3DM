# Independent surface-marker consistency test

## Result

**Reject the sparse labeled sheet as a source of globally identified vertices.** The generated marks visibly wrap around the lion, but their identities do not remain fixed. The later request rejected this input design and requested a dense continuous black quad grid on a white lion, with no numbers, colors or labels. This experiment remains failure evidence, not the requested final input.

- One caller-attested ImageGen call supplied `generated/input.png`: 1774 × 887 pixels, eight cells in a 4 × 2 layout. Source SHA-256: `b1732858f38c9121fa1211ee32dd910b27e8cea54a7a0741ae2b577b37e44b2e`.
- All eight views inspected. Conservative manual inventory: 101 readable label instances, 21 of 24 requested unique IDs. IDs 13–15 are absent. This is a readable-label inventory, not an automatic detection benchmark or proof every visible mark was counted.
- IDs 05/06/07 occur on both flanks, although distinct opposite-side patches were requested. Views 6 and 7 each have two different hind-leg patches marked 18. The side-mane patch reads 04, then 12, then 04 across views 0, 1, 2. These are direct correspondence contradictions independent of camera calibration.
- Zero globally authenticated corner tracks were accepted. This is a conservative acceptance result, not a claim that no useful local corners could ever be recovered.
- An exploratory diagnostic annotated 12 candidate boundary corners on three patches (06, 09, 11), in only views 1, 2, 3. No candidate identity was propagated to the opposite side. The local observations are not treated as verified physical IDs.

## Held-out diagnostic

Fit each candidate point using only views 2 and 3 under requested 45°-spaced common level orthographic cameras; predict view 1. Use one common 512/443.5 scale from source-cell coordinates, without independently resizing or recentering silhouettes.

- Training reprojection: median **0.58 px**, p95 **3.20 px** (24 observations).
- Held-out reprojection: median **11.76 px**, p95 **28.62 px** (12 observations).
- Three-view prediction loop: median **10.92 px**, p95 **27.97 px** (36 pair-to-third predictions).
- Conditional epipolar distance: adjacent-pair p95 **6.93 px**, 90°-pair p95 **12.24 px**. Level orthographic epipolar distance only tests vertical alignment.
- View 5 was reserved as another held-out view, but no qualified track reached it. Thus only 1 of 2 held-out views and 3 of 8 total views have this local diagnostic. Full-orbit closure is **not evaluable**, not a zero error.

These points were manually annotated in 2D, estimated to ±3 source pixels. They are not a hand-modeled lion. A 300-trial independent bounded perturbation sensitivity test gives held-out median errors 7.08–18.26 px. This random sensitivity exercise is **not** a worst-case error bound or a proof that no better annotation could fit. The predeclared 3 px engineering threshold is below the estimated manual-corner uncertainty, so the geometric test is exploratory. Actual cameras are uncalibrated: camera spacing, framing, geometry and corner ambiguity can all contribute. The identity contradictions are the decisive failure, not these conditional residuals alone.

## Separate known-3D control

An analytic ellipsoid supplies 64 surface patches / 256 physical corner tracks with known 3D coordinates, visibility, cameras and projections. It is not a lion model and never supplies geometry to the generated test. The validator consumes exact projected coordinates, so this is a **mathematical validator control**, not an end-to-end marker-detector accuracy test. The preview uses a coarse polygon approximation of each curved patch; observations are analytic corner projections.

- Exact projections: numerical-zero reconstruction and reprojection error.
- Independent 0.4 px noise: held-out p95 **1.38 px**, 3D error p95 **0.00637** in ellipsoid units; pass.
- Same-height held-out identity swaps: epipolar p95 stays **1.09 px**, but held-out p95 becomes **254.20 px**; reject.
- 12 px held-out surface warp: held-out p95 **12.24 px**; reject.
- Genuine rigid geometry with actual held-out cameras offset by 10°: epipolar error **0**, held-out p95 **23.48 px**; reject the requested-camera hypothesis, not the true geometry.
- Consistently permuted identities: held-out p95 still **1.38 px**, yet true physical identities are wrong; the identity gate rejects. This explicitly demonstrates that low reprojection cannot prove true correspondence.

## Gate and outcome

Predeclared in `PROTOCOL.md`: unique stable identity/corner orientation, connected eight-view graph with at least three independent patches per adjacent edge and coverage of mane/torso/legs on both sides, held-out and loop p95 ≤3 px and epipolar p95 ≤2 px at 512-pixel cells. This gates sparse constraints only, never dense surface truth.

The generated sparse input fails identity and coverage before these numerical thresholds matter. No dense marker-derived lion reconstruction was produced. The later request explicitly requested exploratory reconstruction regardless of the strict gate; the separate baseline implements that and must label camera/surface assumptions. A silhouette mesh cannot be called an ID-validated mesh.

## Reproduce

Runtime used: existing local Python environment with NumPy, Pillow and SciPy (geometry itself uses NumPy only); no model weights, learned mesh prior or Tripo dependency. No network is required.

```sh
python source/prepare_crops.py
python source/synthetic_control.py
python source/analyze_generated.py
python source/make_evidence.py
python -m unittest discover -s source -p 'test_*.py' -v
```

Six regression tests passed: exact triangulation, opposite-camera degeneracy, held-out isolation, identity rejection overriding good fit, missing-metric rejection, and positive/negative controls.

Selected evidence:
- `results/identity_failures.png`
- `results/heldout_corner_diagnostic.png`
- `results/control_comparison.png`
- `controls/known_ellipsoid.png`
- `results/generated_metrics.json` and `controls/summary.json`

## Animation attempt and revised input

The experiment record reports a subsequent native ImageGen animation request returned a static PNG sheet, not an animated GIF: `exec-53df3047-2a96-4353-a288-28a6faa8e040.png`. No native animated turnaround is claimed. A copied closing frame would not establish temporal or geometric consistency. Future externally supplied 5–10 second clips should retain timestamps, avoid duplicate endpoint weighting, track through adjacent frames, terminate tracks at occlusion and validate camera geometry. No real external clip has been supplied to this worker yet.

Latest requested visual: eight views, white untextured lion, literal dense connected black square/quad grid over every surface, no colors/numbers/IDs/text. This supersedes the sparse coded-marker design; repeated black intersections will require contextual/temporal matching rather than treating printed codes as identity.

## Public artifact policy

The public record omits raw inferred3D point coordinates, while retaining2D candidate observations, identities, residuals and conditioning. The source recreates full local diagnostic data, but no point cloud or animal model is committed. Selected annotated visuals are under `docs/experiments/14-marker-audit`. Re-running the diagnostic reproduces original numeric metrics before this public-only coordinate omission.
