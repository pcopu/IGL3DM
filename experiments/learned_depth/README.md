# Learned multiview depth: CPU experiment

**Result: inference is practical; naive full-orbit fusion is rejected for this input.** This optional experiment is independent of the production-free visual-hull baseline. It does not replace that mesh and does not silently install model dependencies.

## Reproducibility

The input is the original sixteen-view wireframe-lion sheet, SHA-256 `d6b6381b4baca46d19120e08795cfb8723e9150ac1dd4c27617a0e73593d64c4`, split by the baseline into shared-framing crops. These runs used **no additional ImageGen call** and no manual alignments or anatomy.

- Official source: [Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3), revision `3d835ec1a5802d64a8b8b15f817a1ab54809bfe4`.
- [DA3-Small checkpoint](https://huggingface.co/depth-anything/DA3-SMALL), revision `e08cab65ca0ec38e7826075418411ab90cab4da3`, SHA-256 `364492e38a3a06d221ac75da7f6621ada3f2361cd24fde11ba79091e9f40efcf`.
- [DA3-Base checkpoint](https://huggingface.co/depth-anything/DA3-BASE), revision `f4a6c9b3c95e41c82048423d3493a81ec3fa810e`, SHA-256 `e01067dc1659613083d9145a9a2547ccdbe6ccbbf83c4fe7b3e8a4e2bdae78b5`.
- Source and these two checkpoints are Apache-2.0. Other checkpoint families have different licenses.
- Four CPU threads, float32, seed 0, official InputProcessor and network forward. No CUDA, xformers, mixed precision, Gaussian exporter, or manual pose correction.
- Torch 2.6.0+cpu, torchvision 0.21.0+cpu, NumPy 2.3.5, SciPy 1.17.0, Pillow 13.0.0, matplotlib 3.10.8. Additional package versions are in `requirements.txt`.

The checkpoint omits six auxiliary-ray LayerNorm affine tensors. The runner asserts the exact allowed family and rejects other unexpected/missing keys. These remain identity-initialized; the fully loaded depth head and camera decoder used here do not use that ray-output branch. This is an explicitly logged implementation qualification.

## Setup and run

Use an isolated environment. Install the pinned CPU PyTorch packages from the [official CPU wheel index](https://download.pytorch.org/whl/cpu) and `requirements.txt`. Clone the official DA3 source at the revision above into `Depth-Anything-3/` beside these scripts. Download each official checkpoint's `model.safetensors` into `models/DA3-SMALL/` or `models/DA3-BASE/`, preserving the recorded hashes. No weights or vendor source are committed here.

```bash
python experiments/learned_depth/run_depth.py \
  --input-dir runs/example/views --model small \
  --views 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 \
  --resolution 308 --threads 4 --output full_orbit
python experiments/learned_depth/analyze_depth.py full_orbit
```

Use `--model base`, `--resolution 504`, or `--reference saddle_balanced` for the controls below. A nonempty run directory is rejected. Telemetry is disabled; input images are processed locally, not uploaded to an inference service.

## Measured runs

Inference timings exclude model loading, downloads, preprocessing and export. Peak memory is process RSS, not total system memory. Full machine-readable results are in `results-2026-11-05.json`.

| Model / views / input size | Reference | Inference | Peak RSS | Adjacent rotation estimate range |
|---|---|---:|---:|---:|
| Small / 2 / 308² | first | 0.983 s | 739.9 MiB | 13.71° |
| Small / 4 / 308² | first | 1.344 s | 841.7 MiB | 10.65–15.58° |
| Small / 16 / 308² | first | 6.399 s | 1156.4 MiB | 2.64–127.22° |
| Small / 16 / 504² | first | 25.855 s | 1985.6 MiB | 1.29–63.62° |
| Base / 16 / 308² | first | 18.131 s | 2012.0 MiB | 3.65–124.42° |
| Base / 16 / 308² | saddle_balanced | 16.758 s | 1984.4 MiB | 2.32–156.54° |

Every full-orbit cloud showed detached, misregistered or duplicate surfaces. Small 308 and Base 308 first-reference runs jumped about 127° and 124° respectively between requested-adjacent views 7→8. Higher resolution did not close the object. Automatic reference selection moved the catastrophic jump to 14→15 rather than fixing it.

These are predicted pose disagreements, **not measured ground-truth pose errors**. The generated sheet itself is uncalibrated. Low local depth residuals and finite tensors do not prove a coherent object.

## Outputs and acceptance

The runner writes raw depth/confidence/cameras/RGB to NPZ and numerical metadata to JSON. The analyzer back-projects a heuristic foreground mask into PLY/NPZ point clouds, computes adjacent reprojection diagnostics and saves depth/confidence/cloud plots. It does not create a watertight mesh, clip to a hull, sculpt an animal, or repair registrations.

Accept a future depth backend only after it demonstrates a coherent orbit, stable cross-view surfaces, usable unseen views and meaningful uncertainty handling. Per-view depth scale/offset and camera calibration require attention before using these predictions as shape constraints. Relative depth is not metric distance, and jointly predicted depth/pose self-consistency is not independent validation.
