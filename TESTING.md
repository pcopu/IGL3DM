# Verification and reproduction

Run from the repository root. Each experimental output directory must be fresh; preserve previous evidence. No test command below makes an ImageGen call or downloads model weights.

## Core baseline

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
```

The base dependency set is NumPy, SciPy and Pillow. Optional differentiable-volume tests skip when Torch is absent; a skip is not a pass. Those historical volume experiments are separate from the strictly classical pear path. Blender is required for actual renders/GLB export, not ordinary core unit tests.

## Classical grid, video and camera code

```sh
pip install -e '.[classical]'
python -m unittest discover -s experiments/marker_consistency/source -v
python -m unittest discover -s experiments/video_grid -v
```

The classical extra adds OpenCV and scikit-image only, with no learned depth, neural shape prior or weights. These suites cover numerical geometry, graph connectivity and gaps, video decode/occlusion behavior, independent synthetic camera recovery, endpoint exclusion, partial-mesh conversion, output protection and quad-shape diagnostics. Passing fixtures does not establish correct identities or camera calibration on generated inputs.

The recorded environment for recent classical runs used Python 3.12, OpenCV 5.0.0, NumPy 2.3.5, SciPy 1.17.0, Pillow 13.0.0 and scikit-image 0.26.0. Dependency ranges permit other compatible releases; exact experiment replay should match the recorded environment and source revision.

## Square-distortion mathematical falsification

The separate square experiment includes numerical fixtures and checks on its actual saved outputs. It needs no neural dependencies. Recreate the local run before invoking its artifact checks:

```sh
python experiments/marker_consistency/source/quad_cells.py \
  --input docs/experiments/17-classical-pear/input.png --output runs/square-check-quads
python experiments/square_shape/run_experiment.py \
  --atlas docs/experiments/17-classical-pear/input.png \
  --quad-graph runs/square-check-quads/quad_graph.json --output runs/square-check
python experiments/square_shape/test_experiment.py --output runs/square-check
```

A test can pass by correctly demonstrating ambiguity or rejecting a false geometry hypothesis. The exact-cylinder counterexample is a required negative result, not a successful target reconstruction.

## End-to-end experiments and withheld data

- Follow each experiment README for its precise input, camera assumptions, gates and commands. Do not substitute unrelated periods, coordinate scales or thresholds without recording a new test.
- The known analytic cadence controls can be regenerated with `experiments/cadence/run_control.sh` into an isolated fresh directory. Known geometry is evaluation-only and never fills the generated target.
- Real-clip reconstruction needs the available unblended clip or its saved tracker outputs. The repository publishes selected silent frames and summaries, not raw video/audio, per-point coordinates or models. The eight-frame preview alone cannot reproduce dense temporal tracking.
- The image-generation service call is external to this repository. An atlas flag records the caller's stated call count; it is not an independently verified service receipt.
- Rendered GIFs are actual mesh previews. They are not generated-video consistency evidence or calibrated source reprojections unless that exact projection was separately checked.

No GitHub Actions workflow is installed by this research update. Local suite results, exact replay checks, source revisions and inspected visuals are recorded in process.md. A passing unit suite, low image error, closed edge incidence or converged optimizer alone is not proof of a useful or correct 3D asset.
