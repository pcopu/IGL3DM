# TripoSR single-view complete-object baseline

Two separate original-atlas crops were tested, with no new ImageGen call or manual modeling. The frontal crop produced an incomplete mane-and-legs form. The three-quarter crop produced a recognizable full lion, but rough surfaces/colors and inferred rear geometry. Watertightness alone would incorrectly approve the frontal failure.

- [Official source](https://github.com/VAST-AI-Research/TripoSR), MIT, revision `107cefdc244c39106fa830359024f6a2f1c78871`.
- [Official weights](https://huggingface.co/stabilityai/TripoSR), MIT, revision `5b521936b01fbe1890f6f9baed0254ab6351c04a`.
- Checkpoint SHA-256 `429e2c6b22a0923967459de24d67f05962b235f79cde6b032aa7ed2ffcd970ee`, 1,677,246,742 bytes, 419,275,628 parameters.
- Source is unchanged. The included `torchmcubes.py` adapter substitutes standard scikit-image marching cubes and preserves the expected reversed coordinate interface. This numerical backend difference is explicit.
- CPU float32, four threads, seed 0, renderer chunk 4096, 128³ extraction. Existing mask, official foreground ratio 0.85, neutral-gray alpha background. No smoothing, island removal or repair.

| Input | Model inference | Extraction | Peak RSS | Vertices / triangles | Outcome |
|---|---:|---:|---:|---:|---|
| Frontal view 00 | 19.69 s | 4.02 s | 2.72 GiB | 12,420 / 24,836 | Structurally failed |
| Three-quarter view 02 | 17.74 s | 3.63 s | 2.95 GiB | 16,090 / 32,176 | Recognizable, imperfect full lion |

Both are edge-watertight/winding-consistent. The view-02 result includes an untouched eight-face island. Timings exclude model load/download/setup. Display renders center the original mesh at its bounding-box center and uniformly scale its largest extent to 1.8; they are not calibrated against atlas cameras. Original mesh geometry is retained locally.

To reproduce, place the pinned official checkout in `TripoSR/`, its official model/config in `models/TripoSR/`, and use an isolated CPU PyTorch environment. Tested versions include torch 2.6.0, torchvision 0.21.0, transformers 4.35.2, tokenizers 0.15.2, huggingface-hub 0.36.2, scikit-image 0.26.0 and trimesh 5.2.0, with the official source's other dependencies.

```bash
python experiments/triposr/run_triposr.py \
  --source-run runs/original --view 2 --resolution 128 \
  --threads 4 --chunk 4096 --output three_quarter
```

Model checkpoints and vendor source are not committed. This learned prior invents unseen surfaces and is not a joint sixteen-view reconstruction.
