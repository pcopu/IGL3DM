# Frozen graph-node retracking experiment

## Result

Re-detecting junctions and associating them with image context and local graph support improves usable coverage on the 96- and 256-frame controls, but does not solve periodic phase ambiguity. The skip-frame veto is unsafe at coarse cadence: it removes every long 96-frame track and preferentially keeps wrong 64-frame aliases. Do not promote this as an identity-safe replacement for the fixed filter.

One method and two predeclared variants were tested without truth-driven retuning. The optional 256-frame control used exactly the same tracker hash and parameters. Ground truth was read only by separate evaluation/diagnostic scripts after emitted tracks existed.

## Tracks spanning at least 30 degrees

| Control | Method | Correct | Wrong | Unresolved | Unique correct vertices | Correct observation coverage | Wrong heldout passes |
|---|---|---:|---:|---:|---:|---:|---:|
| 96 | Original LK | 556 | 29 | 27 | 462 | 37.41% | 23 |
| 96 | Previously fixed v2 filter | 266 | 0 | 2 | 258 | 12.06% | 0 |
| 96 | graph_joint | 605 | 15 | 6 | 517 | 40.82% | 10 |
| 96 | graph_joint_cycle_veto | 0 | 0 | 0 | 0 | 0.00% | 0 |
| 64 | Original LK | 43 | 357 | 5 | 43 | 1.83% | 83 |
| 64 | graph_joint | 67 | 401 | 2 | 67 | 2.73% | 78 |
| 64 | graph_joint_cycle_veto | 0 | 242 | 1 | 0 | 0.00% | 28 |
| 256 | Original LK | 492 | 1 | 155 | 405 | 31.41% | 1 |
| 256 | graph_joint | 589 | 0 | 8 | 519 | 40.96% | 0 |
| 256 | graph_joint_cycle_veto | 589 | 0 | 8 | 519 | 40.96% | 0 |

All controls have 737 unique physical vertex locations visible somewhere. Unique coverage counts physical coordinates, not fragment IDs. Correct observation coverage is the union of `(frame, physical vertex)` observations belonging to correct qualifying tracks, divided by all visible truth observations. Multiple fragments of one vertex count once. These denominators include vertices that image detection may miss.

## All tracks of at least three samples

| Control | Method | Correct | Wrong | Unresolved | Total | Unique correct vertices |
|---|---|---:|---:|---:|---:|---:|
| known96 | graph_joint | 886 | 22 | 6 | 914 | 554 |
| known96 | graph_joint_cycle_veto | 193 | 3 | 1 | 197 | 183 |
| known64 | graph_joint | 327 | 746 | 2 | 1075 | 273 |
| known64 | graph_joint_cycle_veto | 11 | 602 | 1 | 614 | 11 |
| known256 | graph_joint | 1420 | 11 | 20 | 1451 | 569 |
| known256 | graph_joint_cycle_veto | 1420 | 11 | 20 | 1451 | 569 |

## Heldout geometry

| Control | Method | Long tracks evaluated | Passed | Correct / wrong / unresolved among passes | Heldout p95 px |
|---|---|---:|---:|---|---:|
| known96 | graph_joint | 532 | 531 | 515 / 10 / 6 | 0.6058712182496532 |
| known96 | graph_joint_cycle_veto | 0 | 0 | 0 / 0 / 0 | n/a |
| known64 | graph_joint | 366 | 115 | 36 / 78 / 1 | 20.135760081646847 |
| known64 | graph_joint_cycle_veto | 214 | 28 | 0 / 28 / 0 | 8.220935460930779 |
| known256 | graph_joint | 501 | 501 | 495 / 0 / 6 | 0.47230510898962424 |
| known256 | graph_joint_cycle_veto | 501 | 501 | 495 / 0 / 6 | 0.47230510898962424 |

Projection matrices and heldout schedule come from the existing control evaluator, not the tracker. A heldout pass means measured reprojection <=3 px; it does not prove identity. Tracks without heldout observations are separately reported and not called validated.

## Method and limits

- Every frame is independently re-detected using the existing skeleton-junction detector. The graph combines traced ink edges with uniquely mapped closed quad-cell edges. Coordinates are these detections, not a selection of original LK track coordinates. All are in the original 512×512 working image coordinates.
- RootSIFT descriptors at 16 and 32 px, reciprocal LK predictions, NCC, and a local spacing gate define candidate node pairs. Hungarian one-to-one assignment is iterated with a graph disagreement penalty. At least two graph-neighbor agreements are required against the assignment hypothesis before final filtering. Final filtering may remove some supporting neighbors; there is no claim that all emitted edges form complete consistent cells.
- Both variants restart IDs after missing support and never bridge gaps. All detections, including singletons, are preserved, so headline evaluation explicitly excludes tracks shorter than three samples.
- The candidate gate is narrow around LK predictions. Post hoc audit found every accepted correspondence had no surviving alternative in that gate. Therefore the cost margin tests local assignment ambiguity only; they do not test competing whole-cell phases. RootSIFT and graph checks did not provide independent global phase anchors.
- At 96 frames, adjacent accepted edges were 13,861 correct, 28 wrong and 15 unresolved. Direct skip-frame edges were 379 correct, 12,867 wrong and 12 unresolved. The cycle veto incorrectly trusted this highly aliased direct evidence, producing 11,221 contradictions and destroying long-track coverage.
- At 64 frames, correct and wrong adjacent-edge median descriptor distances were 0.06218 and 0.06225, both with median four supporting graph neighbors and ~0.01 px LK forward/backward error. Strong local checks accepted wrong phase.
- At 256 frames the skip veto found zero contradictions and produced identical tracks. Long tracks have zero observed wrong identity but eight unresolved tracks; the all-three-sample set still has 11 wrong tracks. This is measured control performance, not a guarantee for real footage.

## Source, protocol, and artifacts

- `PREDECLARED.md`: protocol frozen before truth evaluation, including two variants.
- `graph_tracker.py`: image-only tracker. Frozen SHA-256: `449b118e15cf09ce0105602c7dfd02553310b1dbe26c15bb7a243a9548db37a6`.
- `evaluate.py`: wraps the existing `correspondence_v2/source/evaluate_selection.py` and adds unique physical/observation coverage.
- `analyze_associations.py`: evaluation-only diagnosis of accepted pairwise edges.
- `validate_artifacts.py`: structural validation, without truth.
- `baseline_comparison.json`: re-evaluation of original LK and existing fixed96 filter using the same coverage computation.
- `known96/`, `known64/`, `known256/`: each includes `frame_graphs.json`, `pair_audit.json`, `manifest.json`, `cycle_conflicts.json`, `association_truth_diagnosis.json`, `evaluation_summary.json`, and `structural_validation.json`.
- Each variant subdirectory contains `tracks.json` with explicit local track IDs, sample/time, redetected node IDs and XY coordinates, `associations.json`, and complete `evaluation.json`. Original frame/timestamp manifest is referenced by `input_directory` in the run manifest. No source images are copied or altered.

## Verification and provenance

All three controls passed structural checks: pairwise one-to-one mappings; no detection assigned twice; contiguous no-gap tracks; coordinates exactly equal emitted frame graph node coordinates; continuation edges present; all detections accounted for; identical tracker source hash. Python compilation passed. The only repair was a module-root typo before the first tracking run, documented in the frozen protocol. No original input, repository, model, camera, or control was edited. Nothing was published.

The original source hash describes the frozen isolated experiment. The repository integration only adjusts import paths and allows an existing empty output directory. Its first three frame graphs and three pair audits exactly replay the saved control. The default structural validator checks the integrated source hash; `--tracker-source` can explicitly identify the historical source for old outputs. See README.md for current commands.
