# Robot grid reconstruction: baseline and recovery experiments

The input is the existing Kling robot turnaround, not a new generation. The target reference-generator geometry and silhouette reconstruction are excluded from every grid reconstruction. Original source is commit `b7bc5788bf5f49eb5b6134e9e6963ce6b8321f57`.

## Recorded baseline

- 193 decoded frames, 24 fps, 720 by 1280. One shared transform produces 512-square analysis: native scale 0.4, x offset 112. No independent object recentering.
- Unchanged re-detected graph tracker and cycle-veto variant: 47,192 observations, 18,382 track fragments, 964 with at least 9 samples, 601 with at least 16. Maximum length 78 frames; no complete-loop track. Both structural validators pass.
- Camera fitting uses 462 fragment IDs; 139 are held out by the unchanged SHA256 split. All 2,204 heldout endpoint errors are reported before acceptance filtering. Fragment independence does not prove physical-point independence.
- Restricted constant-speed camera fit hits its 192-frame upper bound. One five-knot variable-speed experiment changes only the speed floor from 1.875 to 0.01 degrees/frame to permit near-pauses, retaining the original 5.625 upper bound, regularization and split.
- Paired heldout p95 improves 10.198764 to 2.231930 analysis pixels. Variable optimizer terminates on step size with optimality 219.678, not a demonstrated stationary optimum. Inferred sweep 345.918 degrees is not verified loop closure.
- Unchanged geometric gate: at least 9 observations, at least 30 degrees fitted span, rank 3, condition at most 20, middle-half fit and endpoint-quarter p95 each at most 1 pixel. It retains 199 points and 16 observed quads using 46 vertices, in 7 disconnected patches. The other 153 points are isolated. Faces must be observed in at least 3 frames; actual support is 6–30 frames. No completion.
- Of 199 points, 118 came from camera-training fragments, 41 from camera-heldout fragments, and 40 from shorter fragments. Selected residuals are selection-conditioned, not independent 3D accuracy.
- 47 classical and 2 video-grid tests pass. An independent numerical audit recomputes every paired error, every camera matrix, all retained points and all face provenance.

[Measured source observations](../../docs/experiments/25-kling-robot/detected-and-selected-junctions.png) · [Actual sparse geometry](../../docs/experiments/25-kling-robot/grid-199-points-16-quads.png) · [Complete compact metrics](results/robot-grid-baseline.json)

## What worked in the earlier experiments

The visually fuller pear output in Round 19 contained 1,072 candidate points and 252 observed candidate quads. Only 335 points and 11 quads passed its stronger 3-pixel checks; 689 points were isolated. Its appearance depended heavily on uncertain correspondences. This is not equivalent to the later 1-pixel graph gate. See [video-grid method](../video_grid/README.md).

Dense temporal sampling improved known-control correspondence, with unresolved identities still retained in the denominator. Joint redetection and graph matching later doubled distinct correct control coverage from 258 to 510 vertices, while the actual pear yielded only 38 points and no faces. See [cadence](../cadence/README.md) and [joint tracking](../joint_tracking/README.md).

The robot's 199 points / 16 quads therefore do not by themselves establish improvement or regression versus 252 permissive pear quads. Different inputs, association policies, gates, camera models and face-support rules must be separated.

## Predeclared next comparisons

1. **Historical replay:** Run the original LK, robust point fit and repeated-cell reconstruction on the same robot video. Use period 192, holdout centers 24, 72, 120, 168 with radius 4, and original offset 0. The 192-frame prior remains intentionally weak because this video pauses. Preserve its full candidate and 3-pixel-qualified outputs separately. Do not relabel its extra coverage as verified identity.
2. **Numerical solver check:** Keep the same five-knot model, data, split, bounds, initialization and regularization. Compare the original forward-difference solver with one fixed central-difference run (`jac=3-point`, relative difference step 1e-4, Jacobian variable scaling, max_nfev 500). Select solver behavior using calibration objective, derivative checks and synthetic fixtures, never heldout success or desired face count. Retain unsuccessful optimization and known-control regressions.
3. **Topology/association ablation:** Compare original and cycle-veto graph outputs on fixed explicit cameras and the same geometric thresholds. Any dense diagnostic output must retain separate uncertainty labels. No reference geometry, hidden-face filling, arbitrary periodic phase repair or new paid generation.

Each meaningful experiment will append a dated log entry with intent, exact inputs/settings, commands, outcome, failures, tests, artifacts and next conclusion. Public commits contain source, compact evidence and selected synthetic visuals, not raw runtime data or model binaries.

## Public reproduction bundle

The owner subsequently authorized the relevant video, raw tracking/evidence and actual models for this public experiment. [Robot reproducibility bundle](artifacts/robot-reproducibility.zip) includes the silent input video, measured data, model files and preserved comparisons. [GLB](artifacts/robot-grid-candidates.glb) and [PLY](artifacts/robot-grid-candidates.ply) are the exact sparse baseline geometry. [Hashes and sizes](results/public-artifacts.json) verify file integrity, not reconstruction accuracy. Credentials, unrelated private data and target reference-generator geometry are excluded. This authorization does not change the privacy policy for earlier experiments.
