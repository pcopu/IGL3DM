# ZipDepth lightweight software-depth comparison

[ZipDepth](https://github.com/fabiotosi92/ZipDepth) is an ECCV 2026 CPU/mobile-oriented depth model. On the original sixteen crops, this run took **1.013 s total inference**, **413.8 MiB peak RSS**, four CPU threads, at 384² network resolution. This is one observed run, not a rigorous throughput benchmark. It produces coarser/smoother depth than V2; it does not create a mesh.

This experiment uses unchanged ZipDepth numerical modules from the LibreYOLO 1.5.0 PyPI wheel, plus official weights. Only `models/zipdepth/nn.py`, `models/zipdepth/utils.py`, shared `kernels/attention/sdpa.py` and provenance `NOTICE` were extracted into a minimal package with empty initializers. Upstream numerical parity was not independently re-tested.

- Wheel SHA-256: `2a921340908e7560301b9358feddf7bc32dd7ed8ff0b3c90ed7a5090342fe513`.
- Port provenance points to official source revision `6b96f4d205f8a2e5377e81c1b74cc99a47f6693a`.
- [Official NPU-friendly checkpoint](https://raw.githubusercontent.com/fabiotosi92/ZipDepth/91f3fd21e131641f51e8d35736d1958350180e3a/checkpoints/zipdepth_base_npu.pth), SHA-256 `627c04fda584133ead4310074884a4a037061b4c01ba86e73e492ea30fab570d`, 27,295,474 bytes.
- 6,142,058 fused parameters; CPU execution, not NPU execution. Strict tensor-only checkpoint load.
- Published code/checkpoint license is MIT, with the Depth Anything V2 Large distillation lineage preserved in NOTICE. The teacher has separate noncommercial checkpoint terms; this is not a blanket legal conclusion about downstream commercial use.

Output is **inverse relative depth, larger = nearer**, with no pose/confidence or cross-view metric calibration. Entire input crops are resized to384² then interpolated to their original size. All inputs are processed locally.

Place the unchanged package subset under `package/libreyolo/` beside the runner and the official checkpoint at `models/zipdepth_base_npu.pth`. Use the CPU PyTorch/OpenCV environment from the other model tests.

```bash
python experiments/zipdepth/run_zipdepth.py \
  --input-dir runs/original/views --resolution 384 --threads 4 --output original_384
```

No new generation was used. [Shared-vertex assessment](../depth_fit/README.md) checks whether these maps can cautiously constrain a common mesh; it does not assume that smoother depth is more correct.
