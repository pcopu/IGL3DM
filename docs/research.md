# Reconstruction research, 2026-11-05

Primary-source candidates for the one-generated-image-to-3D goal. **Only DA3 Small/Base have completed the learned-model experiments recorded here.** Availability, licenses and hardware requirements should be rechecked before a new run.

## Tested depth route

[Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3) Small/Base ran in float32 on CPU. Their code and selected checkpoints are Apache-2.0; larger checkpoint families differ. All full-orbit raw fusions failed the coherence gate on the wireframe lion. See [the experiment](../experiments/learned_depth/README.md), not just runtime or finite-tensor checks.

## Complete-object priors

- [TripoSR](https://github.com/VAST-AI-Research/TripoSR): MIT code/model, explicit CPU fallback. A useful independent full-mesh baseline, unlike depth-only point fusion. CPU performance and output quality remain to be established in this journal.
- [TRELLIS.2](https://github.com/microsoft/TRELLIS.2): MIT code/model and shape/PBR output; official implementation requires Linux/NVIDIA with at least 24 GB VRAM. Not a direct fit for the current CPU experiment.
- [Pixal3D](https://github.com/TencentARC/Pixal3D): pixel-aligned multi-view conditioning, but requires camera poses/FOV and consistent image framing. Its supplied four-view rig is not a camera estimator.
- [UniForge3D](https://github.com/xibushu/UniForge3D): sparse unposed views to complete assets, based on VGGT/TRELLIS.2. Original source is MIT, but released VGGT-derived weights are noncommercial and background-removal dependencies have separate terms.

## Geometry and correspondence alternatives

- [MapAnything](https://github.com/facebookresearch/map-anything): CPU fallback and optional geometric conditioning. Apache code; use its specifically named Apache checkpoint rather than assuming the default checkpoint is commercial-use compatible.
- [LightGlue](https://github.com/cvg/LightGlue): Apache code/weights and reported CPU benchmark. Feature extractor licenses must also be checked. Painted wireframe crossings remain ambiguous even if matching software is strong.
- [MASt3R](https://github.com/naver/mast3r): potentially useful dense matching, but noncommercial/share-alike terms and checkpoint training-data obligations require review.

## Ports to evaluate separately

[depth-anything.cpp](https://github.com/localai-org/depth-anything.cpp) is a CPU-first GGML runtime, but model licenses and relative-versus-metric distinctions are unchanged. [trellis.cpp](https://github.com/pwilkin/trellis.cpp) reports an Apple Metal path and a slow/RAM-heavy CPU fallback. Upstream timing claims are not measurements on this machine, and neither port was executed in the recorded baseline.

## Experimental priorities

1. Reuse the same generated input for software comparisons.
2. Separate camera/elevation coverage from mesh-pattern, vertex-color and painted-depth changes where possible.
3. Treat generated depth/XYZ/vertex colors as hypotheses, not calibrated data.
4. Compare silhouette-only and depth-assisted solutions on the same inputs and cameras.
5. Include held-out elevations, actual mesh renders, topology checks and visual rejection of duplicate surfaces. No single IoU score establishes 3D correctness.
