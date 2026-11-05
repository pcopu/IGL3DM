# IGL3DM — Image Gen Led 3D Modeling

**Concept:** Use image generation to perform most of the visual design and reference creation for a 3D character, then use software to turn those references into a coherent, editable 3D mesh. Finish and validate it in Blender with an agent.

This is a proposed workflow, **not** a claim that a complete 1:1 reconstruction pipeline already exists.

## Core idea

Instead of generating one image and asking an agent to sculpt a model from it, generate **synchronized multi-view references** in three complementary representations:

| Reference | Views | Purpose |
| --- | --- | --- |
| Color / shaded | 8 | Silhouette, volumes, proportions, color, expressions and character identity |
| High-contrast mesh-like | 8 | Structural landmarks, boundaries between major masses, visibility relationships |
| Topology / edge flow | 8 | Suggested edge loops around face, joints, extremities and surface transitions |

**Important:** These are image-generated *reference drawings*. A drawn wireframe is not guaranteed to be an actual, consistent polygon mesh, and the apparent vertex locations in different images may not correspond to the same physical points. Software must solve the 3D geometry.

## End-to-end workflow

### 1. Lock the character and camera

- Choose a single character pose, including limb placement, expression and tail position.
- Choose a consistent frame, ground plane, orthographic or calibrated perspective camera and rotation axis.
- Generate the same subject at **0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°**.
- Lock overall object scale, camera pitch, lighting and frame composition.
- Validate that adjacent views depict a physically plausible single object before committing to reconstruction.

To reduce view drift, consider generating a coarse 3D anchor first and using its rendered views as control/reference images for subsequent detail generation. This trades off some image-first freedom for much better cross-view consistency.

### 2. Generate three aligned sheets

**A — Color sheet:** Establish the final intended appearance with clearly separated forms and a stable silhouette.  
**B — Mesh-contrast sheet:** Render the identical pose from the same cameras with white/gray clay and readable dark structural lines.  
**C — Edge-flow sheet:** Overlay topology guides, such as rings around the eyes and mouth, transitions between facial planes, shoulders, elbows, knees, paws and tail.

Create matching crops for each angle. Reject or repair inconsistent camera views and mismatched anatomy *before* fitting the mesh.

### 3. Extract constraints from the images

For each view:

1. Segment the subject into a binary **silhouette mask**.
2. Trace the exterior contour at pixel accuracy.
3. Identify major **3D-relevant landmarks** such as eyes, ear tips, muzzle, paw contacts, joint centers and tail root.
4. Trace internal structural curves (mouth edge, mane masses, body transitions).
5. Estimate which landmarks/curves are occluded; annotate confidence and view visibility.
6. Link the same semantic landmarks and curves across views.

**Do not attempt to instantiate every drawn wireframe crossing as an independent 3D vertex.** Use correspondences only when they are reliable; otherwise rely on a predefined mesh topology and image-space constraints.

### 4. Solve an initial solid

- Use calibrated cameras and masks to build a **visual hull** or signed-distance/voxel occupancy field.
- Extract a watertight surface with marching cubes or a comparable method.
- Optionally initialize a riggable quadruped template and deform it toward the visual hull.
- Keep separate semantic regions for body, mane, face, mouth, paws and tail when that helps topology and animation.

The initial hull captures what the views permit, but cannot reconstruct concavities hidden from all silhouettes; internal feature lines and geometry priors are needed for the rest.

### 5. Optimize a shared 3D mesh

Fit **one mesh** against all eight cameras at once. For each candidate vertex arrangement, render the mesh back into all reference views and evaluate:

- **Silhouette loss:** discrepancy between rendered and source masks.
- **Landmark reprojection loss:** difference in projected feature positions.
- **Contour/curve loss:** discrepancy around the muzzle, mane, mouth and body transitions.
- **Regularization:** mesh smoothness, minimum thickness, plausible anatomy, no self-intersections.
- **Cross-view consistency:** the same geometry must explain every input view.

A conceptual objective is:

```text
L = w_s * silhouette_loss
  + w_l * landmark_reprojection_loss
  + w_c * feature_curve_loss
  + w_r * geometry_regularization
  + w_v * cross_view_consistency_loss
```

Treat `w_*` as tunable priorities, not fixed parameters. Prefer a differentiable renderer or iterative optimization with projected masks. Keep the template's connectivity stable during early fitting; remesh only after convergence or in dedicated refinement phases.

### 6. Build physical surface detail

Use the color and wireframe-like references to add genuinely 3D features:

- Separately layered mane geometry rather than a large smooth blob.
- Eyebrows, eyelids, ears, nose bridge, nostrils and muzzle volumes.
- A real mouth opening and interior, tongue and teeth if visible.
- Individual toes and paws, recognizable joints and grounded foot contact.
- A continuous tail with controlled taper and tuft shape.

Apply UVs / vertex colors / textures only after the underlying shape meets multi-view projection tests. Color projections should be visibility-aware to avoid painting the wrong side of the model.

### 7. Blender agent refinement

An automated Blender pass can handle:

- topology cleanup and selective retopology
- surface intersections, loose geometry and shading artifacts
- mirrored/paired anatomy where applicable
- UV unwrapping and texture baking
- optional skeleton, skin weights and animation checks
- turntable renders from exact source camera angles

The agent should make bounded changes and rerun visual validation after each pass. Do not let cleanup improve one view while silently degrading the others.

### 8. Validate before calling it done

Render the model from all eight original angles (and several **intermediate, unseen angles**) at locked camera settings.

Track:
- per-view and mean silhouette IoU
- landmark reprojection error in normalized image coordinates
- consistency of the outline, joint locations and face across views
- mesh watertightness, self-intersections and non-manifold edges
- subjective character likeness and material match

Use generated references as *targets*, not ground truth about hidden geometry. A perfect 2D silhouette score alone does not prove a 1:1 model: the mesh may be malformed, topologically unsuitable or inconsistent at unseen viewpoints.

## Proposed software architecture

```text
ImageGen
  → synchronized view generation
  → quality control / registration
  → silhouettes + landmarks + feature curves
  → camera calibration
  → visual-hull / template initialization
  → multi-view vertex optimization
  → geometry + UV/material refinement
  → Blender agent cleanup
  → eight-view + novel-view validation
  ↺ iterate until quality targets are met
```

Potential implementation modules:

- `view_generator` — prompts, pose/view controls, image batches, provenance.
- `view_registration` — camera/scale checks and crop alignment.
- `constraint_extractor` — segmentation, silhouettes, curves and landmarks.
- `mesh_initializer` — voxel occupancy, visual hull and initial mesh.
- `mesh_fitter` — common-topology vertex optimization and reprojection.
- `material_builder` — visibility-aware color projection and texture baking.
- `blender_agent` — mesh cleanup, rigging preparation and renders.
- `validator` — quantitative view comparisons and mesh integrity tests.

## Development order

1. Prove robust silhouette fitting from eight **known consistent** views using a simple shape.
2. Add view-specific feature landmarks and recover a stable, plausible 3D form.
3. Test on stylized quadrupeds with limbs and tails.
4. Introduce mesh-reference and edge-flow image sheets as additional, confidence-weighted constraints.
5. Automate sculpting/cleanup in Blender and validate on unseen viewpoints.
6. Only then attempt highly detailed, near-1:1 stylized characters.

## Guiding principles

- **ImageGen leads the design; geometry software enforces physical consistency.**
- Multi-view agreement matters more than how convincing one frame looks.
- Separate generated **wireframe appearance** from mathematically real vertices and edges.
- Silhouettes are the starting point, not the entire solution.
- Every automated improvement should be measured by rendering the *actual* mesh.
- Be explicit about failure modes; do not advertise pixel-perfect 1:1 fidelity until it is demonstrated.

## Repository scope

This repository documents the **overall approach**. It intentionally does **not** include example models, GLB/OBJ meshes, image-generation outputs, chat transcripts, or historical test artifacts.
