# Known dimple tracking control (evaluation only)

Use **`experiments/surface_completion/dimple_control.py`** as the deterministic mesh generator and **`experiments/surface_completion/render_dimple_control.py`** as the Blender colored-grid full-rotation renderer. These synthetic coordinates must never be used to fill or validate the real object's unseen geometry.

The control uses the same analytic radial dimple as the completion study, now sampled on an all-quad cube-sphere instead of triangular Fibonacci directions. Resolution 24 gives **3,458 shared vertices and 3,456 quads**, with no duplicated seam/pole vertices. Every polygon has four distinct vertices. Cube corners are three-valent; most grid junctions are four-valent. This is an explicit topological difference from a latitude/longitude grid. Adjacent cells may share a color, but thin black geometry marks every quad edge.

Parameters: ellipsoid axes `(0.72, 0.62, 1.2)`, z taper `0.22`, xz asymmetry `0.06`, Gaussian radial dent centered at **+X**, depth **0.19**, angular width **0.24 radians**. The dent center radius is **0.53**. At equatorial angular offsets ±0.12 radians, the chord lies **0.0361353** units outside the center: this verifies a true inward recess rather than just global pear taper. There are **61 vertices within 20°** of the dimple axis. `--no-dent` removes only the Gaussian term, preserving quad identities and cell colors.

## Reproduce

The mesh generator uses only Python's standard library. It also exports an evaluation-only `mesh.json` on request (ignored by Git):

```sh
python experiments/surface_completion/dimple_control.py --resolution 24 --output /tmp/new-dimple-mesh
```

The renderer was tested with **Blender 4.3.2**, CPU Cycles. Both commands below were executed successfully, producing **48 decoded 512×512 PNGs**, 24 evenly spaced views per object, 32 samples per image:

```sh
blender -b --python experiments/surface_completion/render_dimple_control.py -- --output /workspace/dimple-shaded-24 --views 24 --size 512 --samples 32
blender -b --python experiments/surface_completion/render_dimple_control.py -- --output /workspace/undented-shaded-24 --views 24 --size 512 --samples 32 --no-dent
python experiments/surface_completion/verify_render_pair.py /workspace/dimple-shaded-24 /workspace/undented-shaded-24 experiments/surface_completion/results
OPENBLAS_NUM_THREADS=1 python -m unittest discover -s experiments/surface_completion -p 'test_*.py' -v
```

Output directories must be new or empty. For a dense temporal test use `--views 240 --size 512 --samples 32` with fresh directories; **240-view rendering was not run in this validation**. Views are `360*i/N` with no duplicated endpoint; view zero looks toward the +X recess. Geometry and lighting remain fixed while the camera orbits at `(6*cos(yaw), 6*sin(yaw), 0.35)`, aimed at the origin. Camera is orthographic, scale 3.1. There is no motion blur or temporal deformation.

The palette has six colors assigned using seed **815**, retained as per-quad palette indices. Diffuse rough materials, a fixed off-axis area light at `(-3,-4,6)`, and low world illumination expose recessed shading. `--emission` gives a matched color-only ablation that removes shading (available but not validated in the paired render run). The verified preview visibly contains darker recessed cells; no photometric difficulty threshold or tracking success is claimed. These are generated rendered controls, not a reproduction of the real input's palette or exact grid density.

## Ground truth and validation

Each output includes `ground_truth.json`: vertices, quads, cell palette indices, all camera world matrices, per-frame 2D vertex projections and geometric visibility. `render_report.json` contains parameters and visibility summary. Quad topology, cell colors and camera matrices were compared exactly across the dented/undented pair. Every rendered PNG was decoded and its size verified.

The dimple-center vertex ID is **937**. On the 24-view cycle it is visible in **7 frames** `[0,1,2,3,21,22,23]`; the corresponding undented vertex is visible in **13 frames** `[0,1,2,3,4,5,6,18,19,20,21,22,23]`. Thus this control demonstrably exercises a shorter geometric visibility arc. The observed 7/24 and 13/24 counts are discrete samples, not precise continuous visibility limits. Tracks crossing index 23→0 should be treated cyclically when measuring arc length.

Visibility uses orthographic parallel rays against the known base mesh, with distance tolerance **0.002**. It does **not** include the black wire overlay, pixel sampling, darkness, or detector behavior. Wire thickness is 0.003 in world units; its surface offset means rendered line junctions need not coincide perfectly with base-surface projections. Treat this as a subpixel-to-pixel rasterization tolerance issue, not identity drift; measure it in the detector benchmark. Nonplanar quads use Blender's internal triangulation. Camera matrices and orthographic scale are recorded, but the JSON does not directly supply a 3×4 projection matrix.

Topology validation: zero boundary edges, zero nonmanifold edges, zero winding disagreements, Euler characteristic 2; shared cube-grid construction gives one connected shell. Positive radial parameterization supplies the no-crossing construction; there is no general triangle self-intersection check. Seven unit tests pass, including matched topology and negative/positive recession controls.

Committed evidence:

- `results/dimple_mesh_validation.json`
- `results/dimple_render_validation.json`
- `results/dimple_render_pair.png` (visually inspected)

Raw mesh coordinates, full frame sequences and ground-truth arrays remain local, reproducible from the committed scripts. No original audio, real-input model or video is included. This control is suitable for the tracking team to measure identity, gap bridges, visibility arcs and shading sensitivity; **that detector benchmark has not been performed here**.
