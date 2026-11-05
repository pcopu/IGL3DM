# Depth Anything V2 Small

Independent per-view software depth on all sixteen original atlas crops. No new image generation, manual modeling or paid inference API.

- [Official source](https://github.com/DepthAnything/Depth-Anything-V2), revision `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`.
- [Official Small checkpoint](https://huggingface.co/depth-anything/Depth-Anything-V2-Small), revision `03876f8651c73a60fe4c2c48294e09fcb6838fcf`.
- Code and Small checkpoint: Apache-2.0. Larger checkpoint licenses differ.
- Weights SHA-256 `715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`; 99,218,434 bytes; 24,785,089 parameters.
- Official preprocessing resizes the whole square input and returns predictions at original resolution, without crop or recentering. CPU float32, four threads, seed 0.
- All16 at 308²: 4.154 s inference, 579.3 MiB peak process RSS. All16 at official-default 518²: 16.585 s, 689.6 MiB. Excludes download/setup/load.

Output is **inverse relative depth, larger = nearer**, without poses, confidence, metric units or cross-view calibration. Display PNGs normalize foreground quantiles separately per view. Smooth-looking maps are not a mesh or proof of correct geometry.

Place the pinned checkout in `Depth-Anything-V2/` and checkpoint in `models/depth_anything_v2_vits.pth`. Use the isolated CPU PyTorch/OpenCV environment described by the DA3 experiment.

```bash
python experiments/depth_v2/run_depthv2.py \
  --input-dir runs/original/views --resolution 518 --threads 4 --output original_518
```

[Shared-vertex assessment and bounded fitting](../depth_fit/README.md) is a separate controlled test. Source and weights are not included in this repository.
