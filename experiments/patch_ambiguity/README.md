# Patch uniqueness is not vertex identity

Tested an image-only rejection filter on existing temporal tracks. A 31×31-pixel patch is compared with the accepted location and alternative centers 6–32 pixels away, in both directions. Each track's score is its worst accepted-minus-alternative normalized-correlation margin. Three thresholds were fixed in advance: −0.05, 0, +0.05. No coordinates, identities or tracks are repaired, and no camera/truth is read by selection.

**Reject this as an identity guarantee.** On the 64-frame known control, the strongest +0.05 gate retains four tracks spanning at least 30°. All four change known physical identity, and two still pass the existing held-out geometric test. The [annotated counterexamples](../../docs/experiments/21-patch-ambiguity/known-wrong-high-margin.png) show the tracked point jumping one grid vertex per frame despite positive margins of 0.0643 and 0.1056. Blue marks the first mapped vertex where visible; red is the candidate. Nearest-known-vertex association is an operational 3-pixel test, not exact intended identity.

At 256 frames, the same strongest gate retains 60 correct / 0 known-wrong / 7 unresolved long tracks, but rejects 432 of 492 original correct long tracks. Zero known errors among this small retained set is not universal reliability. On the uploaded clip, candidates lasting at least three samples fall from 1,552 to 399 / 230 / 122 for the three thresholds. These are coverage counts only; there is no truth-based real-clip accuracy claim.

Whole-track minima penalize long tracks and dense sampling. Fixed patch/search sizes do not adapt to grid scale. Translation-only, rounded-pixel comparison can reject true points under shear, perspective or occlusion. Both controls show the same analytic shape. All these limitations are retained in the [full compact evaluation](evaluation.json), along with known-wrong and unresolved passes.

## Reproduce

Source is in `../marker_consistency/source/`. `score_patch_ambiguity.py --root TRACKER_OUTPUT --output FRESH_DIRECTORY` computes image-only scores. `evaluate_patch_rejection.py --control64 CONTROL64 --control256 CONTROL256 --score-directory SCORES --output NEW_JSON` joins existing truth labels only afterward; score directories are named `known64` and `known256` below SCORES. Neither stage changes original tracks. Four synthetic tests cover unique, duplicated, stronger-alternative and boundary patches.

The public evaluator now accepts explicit paths and refuses existing output. Every metric reproduces the independent run exactly. `make_counterexample.py` reproduces the read-only annotated figure from known-control images/vertices and saved scores; no inferred target model is created. Raw observations and model files stay local.
