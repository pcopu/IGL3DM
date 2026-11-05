"""Isolated, reproducible CPU experiment with official DA3 code and weights.

No manual geometry. Uses official preprocessing and network directly, fp32,
without optional export/UI/Gaussian dependencies or CUDA autocast.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Depth-Anything-3" / "src"))
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import numpy as np
import torch
from safetensors.torch import load_file
from depth_anything_3.cfg import create_object, load_config
from depth_anything_3.utils.io.input_processor import InputProcessor

parser = argparse.ArgumentParser()
parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing view_00.png etc")
parser.add_argument("--views", default="0,1")
parser.add_argument("--resolution", type=int, default=308)
parser.add_argument("--threads", type=int, default=4)
parser.add_argument("--output", default="pair01")
parser.add_argument("--model", choices=["small", "base"], default="small")
parser.add_argument("--reference", choices=["first", "saddle_balanced"], default="first")
args = parser.parse_args()
torch.set_num_threads(args.threads)
torch.set_num_interop_threads(1)
torch.manual_seed(0)

view_ids = [int(v) for v in args.views.split(",")]
paths = [args.input_dir / f"view_{v:02d}.png" for v in view_ids]
outdir = ROOT / "outputs" / args.output
if outdir.exists() and any(outdir.iterdir()):
    raise ValueError(f"Refusing to overwrite nonempty output directory: {outdir}")
outdir.mkdir(parents=True, exist_ok=True)
ckpt = ROOT / f"models/DA3-{args.model.upper()}/model.safetensors"
config = ROOT / f"Depth-Anything-3/src/depth_anything_3/configs/da3-{args.model}.yaml"
t = time.perf_counter()
model = create_object(load_config(str(config))).eval().cpu()
weights = load_file(str(ckpt), device="cpu")
weights = {k.removeprefix("model."): v for k, v in weights.items()}
load = model.load_state_dict(weights, strict=False)
# Official checkpoint omits six auxiliary-ray LayerNorm affine tensors.
# They initialize to identity and do not affect depth or the camera decoder.
# Do not silently accept any other mismatch. Ray-based pose is disabled.
allowed_missing = {f"head.scratch.output_conv2_aux.{i}.2.{kind}"
                   for i in (1, 2, 3) for kind in ("weight", "bias")}
assert not load.unexpected_keys, load
assert set(load.missing_keys).issubset(allowed_missing), load
del weights
print("Model loaded", load, "params", sum(p.numel() for p in model.parameters()), flush=True)
load_seconds = time.perf_counter() - t
images, _, _ = InputProcessor()([str(p) for p in paths], process_res=args.resolution,
                               process_res_method="upper_bound_resize", sequential=True)
if images.ndim == 4:
    images = images[None]
print("Input", tuple(images.shape), "threads", args.threads, flush=True)
t = time.perf_counter()
with torch.inference_mode():
    prediction = model(images.float(), infer_gs=False, use_ray_pose=False, ref_view_strategy=args.reference)
elapsed = time.perf_counter() - t
arrays = {k: v.detach().cpu().float().numpy() for k, v in prediction.items() if torch.is_tensor(v)}
rgb = images[0].permute(0, 2, 3, 1).numpy()
rgb = np.clip((rgb * np.array([.229, .224, .225]) + np.array([.485, .456, .406])) * 255, 0, 255).astype(np.uint8)
arrays["images"] = rgb
np.savez_compressed(outdir / "prediction.npz", **arrays)
stats = {
    "model": f"depth-anything/DA3-{args.model.upper()}", "checkpoint_sha256": hashlib.sha256(ckpt.read_bytes()).hexdigest(),
    "code_commit": "3d835ec1a5802d64a8b8b15f817a1ab54809bfe4", "device": "cpu", "dtype": "float32",
    "torch": torch.__version__, "threads": args.threads, "view_ids": view_ids, "reference_strategy": args.reference,
    "input_shape": list(images.shape), "load_seconds": load_seconds,
    "inference_seconds": elapsed, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "parameters": sum(p.numel() for p in model.parameters()),
    "missing_checkpoint_keys": load.missing_keys,
    "outputs": {k: {"shape": list(v.shape), "finite_fraction": float(np.isfinite(v).mean()),
                     "min": float(v.min()), "median": float(np.median(v)), "max": float(v.max())}
                for k, v in arrays.items()},
    "notes": ["Depth is relative, not meters.", "No hand modeling or known-camera constraint supplied.",
              "The generated views were requested as 22.5-degree steps, but are not calibrated.",
              "Raw network forward and official InputProcessor used, without high-level export or autocast.",
              "Six auxiliary-ray LayerNorm affine tensors absent from the official checkpoint retain identity defaults; depth and camera decoder are fully loaded; ray pose is not used."],
}
ext = arrays.get("extrinsics")
if ext is not None:
    ext = ext[0]
    angles = []
    for a, b in zip(ext[:-1], ext[1:]):
        r = b[:3, :3] @ a[:3, :3].T
        angles.append(float(np.degrees(np.arccos(np.clip((np.trace(r)-1)/2, -1, 1)))))
    stats["adjacent_rotation_degrees"] = angles
    stats["extrinsics"] = ext.tolist()
stats_path = outdir / "metrics.json"
stats_path.write_text(json.dumps(stats, indent=2) + "\n")
print(json.dumps(stats, indent=2), flush=True)
