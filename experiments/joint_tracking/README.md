# Jointly re-detect and match grid junctions

Classical image processing and graph assignment improve known-control correspondence coverage. The generated clip still gives only **38 conditional points and zero faces**, or **37 points and zero faces** with the unchanged, unaccepted variable-camera hypothesis. No complete target mesh is claimed or invented.

## Method and evidence

Each frame independently detects skeleton junctions and closed quad cells. RootSIFT descriptors at 16/32 px and reciprocal optical-flow proposals supply bounded candidates. Hungarian one-to-one assignment adds neighbor disagreement penalties; two supporting graph neighbors and a cost margin are required. Missing matches terminate a track, with no gap bridging. The tracker does not read camera matrices, old tracks, learned features or truth.

The previously frozen midpoint-fit/end-quarter 1 px trajectory gate is then applied unchanged, with an explicit nominal orbit/framing prior. On tracks spanning at least 30°:

| Known frames | Correct | Known wrong | Unresolved | Distinct correct vertices |
| --- | ---: | ---: | ---: | ---: |
| 64 | 26 | 0 | 0 | 26 |
| 96 | 586 | 0 | 5 | 510 |
| 256 | 570 | 0 | 8 | 504 |

The preceding filter covered 258 distinct correct vertices on the same 96-frame shape. These controls share one analytic object; five/eight unresolved identities remain. The image-only graph tracker alone retains 15 wrong long tracks at 96 frames and 401 at 64. Its optional direct skip-frame veto fails badly at coarse cadence. Keep those results in [graph_REPORT.md](graph_REPORT.md), rather than presenting the combined gate as a solved identity detector.

All accepted pair links in this experiment had only one candidate inside the flow window. Large cost margins therefore do not compare every integer grid phase. At 64 frames, 5.625° steps equal half the control's local 11.25° longitudinal pitch. Global pear asymmetry can break full symmetry; this local alias is not proof that every grid reconstruction is impossible.

## Actual clip

A single recorded affine normalization maps every original 575×768 working image to a padded 512×512 frame. No per-frame object fitting, interpolation or presentation blend is used. All 97 unblended samples are processed, retaining the original 14–110 frame mapping. Sample 96 is excluded by the existing nominal-period gate. A 96-frame full orbit remains a hypothesis, not something established by trimming.

There are 9,195 software IDs, 1,070 with at least three observations, 498 with at least 30° nominal span, and 40 selected segments. The prior fitter retains 38 points; 21 have sufficient held-out block data and pass its 3 px test. No complete four-corner cell survives. Selection uses all-frame evidence, so small residuals are not independent physical identity validation. With the prior variable cameras, 37 points and zero faces survive without camera refitting. Earlier exploratory meshes remain unchanged.

## Reproduction

Use the `classical` dependency extra and a fresh output directory. The source modules live in `../marker_consistency/source` so their classical dependencies are shared, not copied. Saved frame inputs need `video_manifest.json` with frame paths and timestamps. The full real clip and control truth are deliberately not published.

```sh
S=experiments/marker_consistency/source
python "$S/prepare_graph_input.py" --input <decoded-tracker-directory> --output runs/joint-input
python "$S/graph_tracker.py" --input runs/joint-input --output runs/joint-tracks
python "$S/validate_joint_artifacts.py" --root runs/joint-tracks
python "$S/run_joint_fixed_gate.py" --tracks runs/joint-tracks/graph_joint/tracks.json \
  --period 96 --output runs/joint-selected
```

For a known control, supply the optional `--truth <ground_truth.json>` only to the fixed-gate evaluator after selection. To evaluate both raw tracker variants, use `evaluate_joint_tracker.py --root <tracker-output> --truth <control-truth> --period 96`. Never give evaluation truth to the tracker. Use the earlier documented measurement/reconstruction helpers for nominal-camera geometry. `build_graph_geometry.py --tracks <tracks.json> --graphs <frame_graphs.json> --cameras <camera-matrices.json> --output <fresh-directory>` uses explicit supplied projections, labels calibration unaccepted and assembles only repeatedly observed four-node cycles.

Integration only changes imports, safe empty-output handling and CLI orchestration. All three control summaries replay exactly; selected track/audit files are byte-identical. Three real control frame graphs and their three pair audits replay exactly, with source-hash and no-gap/one-to-one structural validation. Seven new helper/tracker tests cover blank images, identity restart at gaps, exact node coordinates, source hash mismatch, output protection, shared affine framing and empty geometry. Full classical suite: 47 tests passed. Main: 27 passed. Quad-shape: 2 passed. These are software checks, not target accuracy guarantees.

[Known-control improvement](../../docs/experiments/24-joint-tracking/control96_improvement.png) · [Actual selected observations](../../docs/experiments/24-joint-tracking/real_selected_overlay.png) · [38-point output](../../docs/experiments/24-joint-tracking/real-38-points.png) · [37-point output](../../docs/experiments/24-joint-tracking/real-37-points.png)
