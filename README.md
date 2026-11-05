# Image Gen Led 3D Modeling (IGL3DM)

An experimental workflow for reconstructing editable 3D meshes from AI-generated multiview character art.

## Goal

Reconstruct a cel-shaded lion in a fixed crouching / snarling pose, consistently from all angles, using image-generated orthographic or near-orthographic turnarounds as reference. Generate aligned color, wireframe, and edge-flow guides; extract silhouettes; fit and optimize actual mesh geometry; refine the result in Blender.

**This is an experimental reconstruction, not yet a 1:1 match.** Previous silhouette-constrained visual-hull iterations reached approximately 83–85% mean overlap across 16 generated reference views, depending on smoothing and reconstruction configuration. Image-generated turnarounds can be inconsistent; wireframe lines drawn by an image model are not guaranteed to represent valid 3D vertices.

## Workflow

1. **Character reference:** Keep the same design, pose, scale, camera elevation, and orientation across views. Generate a color turnaround.
2. **Mesh-style guide:** Generate the same view grid in high-contrast monochrome wireframe. Use the artwork to guide landmarks and massing, not as authoritative topology.
3. **Topology guide:** Generate edge-flow references for face/muzzle, eyes, mane clumps, shoulders, legs, paws, and tail.
4. **Silhouette constraints:** Extract binary masks and exterior contours, calibrate views, and solve a volumetric visual hull.
5. **Mesh reconstruction:** Extract the isosurface as GLB/OBJ, optimize geometry and vertex placement against projected masks and landmarks; avoid simply merging independent view images.
6. **Surface sculpt and texture:** Project and clean color markings, sculpt actual geometry, and maintain a clean topology suitable for rigging.
7. **Validation:** Re-render identical camera positions and report per-view overlap and feature alignment. Iteratively improve before claiming 1:1.

## Current state

- Multiple 16-view silhouette extraction, visual-hull, smoothing, color-projection, and mesh-detail passes have been completed in the ChatGPT conversation.
- Real GLB/OBJ/PLY meshes and comparison renders were generated, but the lion is not yet a faithful reproduction of the source artwork.
- An eight-view color reference sheet was generated for the next iteration. An eight-view topology sheet remains an exploratory image-reference task.
- See [Project history](docs/PROJECT_HISTORY.md), [Reconstruction specification](docs/RECONSTRUCTION_SPEC.md), [Artifact manifest](docs/ARTIFACT_MANIFEST.md), and [Conversation transcript](docs/CONVERSATION_TRANSCRIPT.md).

## What the model must preserve

- Strong triangular, swept-back layered mane
- Golden-tan muscular body and darker chest/mane
- Wide open snarling mouth, cream muzzle, visible teeth
- Forward-low stance with all legs on the ground
- Curled elevated tail with a dense tuft
- Stable dimensions, limb pose, and facial proportions from every viewpoint

## Asset storage

The chat-created assets include large PNG/GIF/GLB/OBJ/PLY binaries and scripts. The full locally packaged archive is available with the ChatGPT conversation; this repository tracks the project specification, reproducibility material, and commit status. See the artifact manifest for the inventory and which assets are actually committed. **A file listed as created in the chat is not necessarily uploaded to this repository.** 

## Project name

**Image Gen Led 3D Modeling** — IGL3DM.
