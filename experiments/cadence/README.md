# Matched 64 / 256-frame analytic cadence control

This is a known analytic fixture, **not a new target model or a reconstruction success on generated imagery**. It measures the classical tracker's identity errors before changing the real-clip method. No ImageGen or learned prior was used, and known vertices/cameras enter only evaluation.

## What was matched

The existing analytic pear renderer, image tracker, framing and settings are unchanged. Every fourth 256-frame view has exactly the same image pixels as its corresponding 64-frame view: 64/64 pairs, maximum difference zero. PNG metadata differs, so file hashes differ. Both videos use MJPEG/yuvj420p. All 256 genuine frames were decoded in order at 30 fps without interpolation or downsampling. Their yaw step is 1.40625°, versus 5.625° for 64 frames. Four held-out absolute angles remain 45°,135°,225°,315°.

This is **not a pure single-variable cadence experiment**: reseeding remains every five frames, so it occurs every 7.03125° instead of 28.125°. Playback duration also changes, although this tracker matches adjacent images rather than time-scaled velocity. No defaults were changed from these results.

## Identity results

The same evaluator labels a track correct only when every observation is within 3 pixels of a visible known vertex and all mapped IDs agree. Different reliable IDs mean a known wrong identity. Otherwise the result is unresolved, not correct and not proven false. Pole duplicates are canonicalized; compressed silhouette vertices can still make this operational classifier ambiguous.

- All tracks lasting at least three samples: 64 frames gives 200 correct / 599 wrong / 7 unresolved, out of 806. At 256 frames: 1,380 correct / 38 wrong / 501 unresolved, out of 1,919.
- With at least 30° nominal angular span: 64 gives 43 correct / 357 wrong / 5 unresolved, out of 405. At 256: 492 correct / 1 wrong / 155 unresolved, out of 648.
- Among long-span tracks passing every available held-out residual ≤3 pixels: 64 gives 27 correct / 83 wrong / 1 unresolved, out of 111 passes. At 256: 391 correct / 1 wrong / 124 unresolved, out of 516 passes.
- The denser run therefore still admits a known wrong identity and has **24.03% unresolved** among its long-span passes. The 0.19% known-wrong share is not a total false rate. Quoting 99.8% precision among resolved tracks would hide the unresolved pool.
- Correct long-span tracks have median 3D error 0.01008 and p95 0.02018 in a fixture of height 2.4. These accuracy figures use truth-classified tracks and do not transfer to generated imagery.

This is strong practical improvement in the matched control, with a substantial unresolved population. Low residual remains insufficient for identity. Training frames may be temporally close to held-out frames even when a track spans a wider angle.

[256-frame tracking preview](../../docs/experiments/20-temporal-cadence/256-tracking.png) · [64-frame preview](../../docs/experiments/20-temporal-cadence/64-tracking.png) · [Full compact 256 metrics](results/256-summary.json) · [Preserved 64 metrics](results/64-summary.json) · [Pixel/codec provenance](results/provenance.json)

## Reproduce

Use the existing classical NumPy/SciPy/Pillow/OpenCV/scikit-image environment, Blender and ffprobe. The script copies unchanged renderer/tracker source into a new isolated directory and refuses an existing path. No downloads or installs are performed.

```sh
PYTHON=/path/to/python bash experiments/cadence/run_control.sh runs/fresh-cadence-control
# Re-summarize a preserved 64-frame fixture without modifying it:
python experiments/marker_consistency/source/compare_preserved_64.py \
  --control-directory path/to/known_pear_64 --output runs/new-64-summary.json
```

The two evaluator helpers now have explicit CLI paths, import safety and fresh-output guards. Replaying them against the existing private control arrays reproduces every reported 256/64 summary field exactly. Three tracker tests and the new helper protection test pass. Full render truth, per-track coordinate records, video and models remain ignored local artifacts; only source, selected images and compact summaries are published.
