# Classical temporal grid reconstruction

A user-supplied generated pear turnaround gave more coherent **partial candidate geometry** than the eight-view still sheet. It is not a verified complete object. No new ImageGen call, learned depth, neural shape prior, hand modeling, silhouette completion, smoothing or hidden faces were used in this round.

## Input, presentation and measurement

The source has 121 frames at 24 fps. The grid fades in and out. The clean excerpt keeps original frames 14–110 inclusive: 97 decoded frames, with timestamps 0–4 seconds and the final frame duration. One common aspect-preserving resize gives 575×768 tracking images, then a common scale 2/3 and horizontal padding 64.3333 produce 512-pixel measurement canvases. No frame is independently fitted to the object.

A separate presentation loop uses an eight-frame dissolve to join mismatched endpoints. It visibly ghosts during the blend and is not geometric loop closure. **No blended frame is measured.** Original video/audio and associated metadata remain private; only selected silent synthetic input/output visuals are versioned. These eight published views alone cannot reproduce the dense temporal experiment.

A muted intermediate exposed only 96 decoded frames despite 97 encoded frames, because of its MP4 edit list. Its average-rate metadata said 24.25 fps, while actual PTS spacing was 1/24 second. Reran tracking from the verified 97-frame delivery. The final endpoint is deliberately excluded by the period-96 reconstruction prior. Candidate point JSON, face JSON and PLY are byte-identical between the two runs. Only 89 tracks' terminal metadata extends from sample 95 to 96. See [compact provenance checks](results/provenance-checks.json).

## Reconstruction and uncertainty

- Classical junction detection and forward/backward optical flow produce 2,323 candidate tracks; 1,552 last at least three samples. Loss ends a track. Counts include new seeds and are not unique physical vertices.
- Cameras assume a level orthographic full turn over 96 sample intervals, scale 256 pixels/world unit and center (256,256). Z is up; yaw zero names the first retained frame, not independently measured front. Rotation direction, angular speed, camera model and world scale remain assumptions.
- Fit each point by five robust linear least-squares iterations. Require at least nine observations, 30 degrees nominal span and bounded conditioning. Exclude five-frame holdout blocks centered at samples 12,36,60,84, and exclude terminal sample 96. Tracking still sees all frames, so feature selection is not independently held out.
- This gives 1,072 candidate points. Both training and held-out p95 are at most 3 pixels for 335; only 63 also span at least 90 nominal degrees. Periodic grid slips can pass these checks, as the known controls already demonstrated.
- Detect 218–286 closed quads per selected view. Assemble only cycles whose same four candidate IDs/connectivity appear in at least two selected views: 252 quads. Just **11** have all corners passing the conditional reprojection test. Those are not proven physical identities or squares.
- The 252-quads display uses 383 vertices, with 689 unused isolated candidates, five shared-vertex components, 265 boundary edges and one nonmanifold edge. The 11-quad subset uses 36 vertices in seven components. Neither is a closed surface. Rendering preserves all coordinates and uses an explicit diagonal per quad, with no repair or completion; winding is not validated.
- Shape sanity check: all quads have median longest/shortest edge ratio 1.43 and best-plane RMS/mean-edge 1.9%. The 11 qualified quads are more planar (1.1%) but have median edge ratio 1.86. A passing reprojection gate does not make them physical squares.

A separate camera fit hit 150 evaluations without convergence. On 68 paired held-out observations, median residual improved 9.03→7.92 pixels and p95 99.67→61.09. This remains poor calibration; those fitted cameras are rejected and were not substituted into the mesh.

[Selected measured frames](../../docs/experiments/19-video-grid/input-frames.png) · [Software IDs](../../docs/experiments/19-video-grid/software-tagged-cells.png) · [Actual candidate mesh](../../docs/experiments/19-video-grid/candidate-turntable.gif) · [252 candidates vs 11 conditionally supported quads](../../docs/experiments/19-video-grid/all-vs-supported.gif)

## Reproduction with an available local clean clip

Use the documented NumPy/SciPy/Pillow/OpenCV/scikit-image environment from the classical experiments. The video input must be an unblended, permissioned local file. Source helpers are import-safe and refuse nonempty output directories.

```sh
python experiments/marker_consistency/source/video_tracks.py \
  --video clean.mp4 --output runs/video/tracks --sample-fps 24 --size 768
python experiments/marker_consistency/source/prepare_measurements.py \
  --input-directory runs/video/tracks --output-directory runs/video/measurements \
  --period-frames 96 --original-frame-offset 14 --source-fps 24
python experiments/marker_consistency/source/reconstruct_video.py \
  --input-directory runs/video/tracks --measurement-directory runs/video/measurements \
  --output-directory runs/video/geometry --period-frames 96 \
  --holdout-centers 12 36 60 84 --holdout-radius 2 --original-frame-offset 14
python experiments/marker_consistency/source/prepare_quad_render.py \
  --source runs/video/geometry/candidate_grid_mesh.ply --output runs/video/display
blender -b -t 4 --python-exit-code 1 --python scripts/render_mesh.py -- \
  --mesh runs/video/display/mesh.json --output runs/video/display/clay \
  --views 16 --midpoints --size 256 --scale 2 --material clay --skip-data
python experiments/video_grid/audit_quad_shape.py \
  --points runs/video/geometry/candidate_points.json \
  --faces runs/video/geometry/candidate_faces.json --output runs/video/quad-shape.json
```

The period/offset/holdout arguments describe this specific clip; do not silently apply them to unrelated footage. Raw tracks, coordinates and model files remain local and ignored. The public summary reports numerical evidence, not 3D ground-truth accuracy.

## Verification

The final source was rerun from the verified 97-frame tracker output in a fresh directory in the main checkout. Full point JSON, face JSON and PLY match the independent run byte-for-byte. The main suite passes 27 tests; classical marker/grid/video helpers pass 27; quad-shape audit passes 2; the retained square-tilt suite passes 5. The synthetic 97-sample fixture deliberately corrupts endpoint 96 and verifies that it is excluded, preserving the true point and original-frame offset. Empty candidate outputs remain valid negative results.

GLB read-back independently confirms all 504 candidate / 22 qualified display triangles. After the standard glTF Y-up axis conversion, two-way nearest-position maximum errors are 3.04e-8 / 2.20e-8 world units, consistent with float32 export. Flat-normal vertex splits and omission of unused loose points do not change the displayed surface. This checks export fidelity only, not correspondence or true shape.
