# Cross-view feature probe

This script compares mutual SIFT matches on same-framing generated views. It applies the assumed level-orthographic horizontal epipolar condition, bounded-volume two-view triangulation, exact three-view feature cycles and pairwise triangulation agreement. It uses OpenCV, NumPy and Pillow.

```bash
python experiments/features/compare_features.py \
  --run runs/original --run runs/coarse_pattern --output runs/feature-comparison
```

Observed original → coarse-pattern counts: 284→279 mutual ratio matches, 230→213 geometry-gate matches, 10→21 exact three-view cycles, 2→7 triangulation-agreement cycles. Seven tracks are sparse support, **not recovery of the mesh vertices**. Repeated patterns can pass these gates incorrectly. Generated cameras and object details can differ, so this is not causal proof that a particular drawing style improves correspondence.
