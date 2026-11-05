"""ZipDepth via PyPI LibreYOLO CPU baseline on the existing turnaround."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parent
os.environ["DO_NOT_TRACK"] = "1"
sys.path.insert(0, str(ROOT / "package"))
import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw
from libreyolo.models.zipdepth.nn import LibreZipDepthNet
from libreyolo.models.zipdepth.utils import preprocess_numpy

p = argparse.ArgumentParser()
p.add_argument("--input-dir",type=Path,required=True,help="Directory containing view_00.png through view_15.png")
p.add_argument("--output",default=None,help="Unique output name; defaults to model_resolution")
p.add_argument("--resolution", type=int, default=384)
p.add_argument("--threads", type=int, default=4)
a = p.parse_args()
torch.set_num_threads(a.threads)
torch.set_num_interop_threads(1)
torch.manual_seed(0)
out = ROOT / "outputs" / (a.output or f"npu_{a.resolution}")
if out.exists() and any(out.iterdir()):p.error("Output is not empty")
out.mkdir(parents=True, exist_ok=True)
ckpt = ROOT / "models/zipdepth_base_npu.pth"
t = time.perf_counter()
model = LibreZipDepthNet(size="bnpu")
state = torch.load(ckpt, map_location="cpu", weights_only=True, mmap=True)
if "model" in state: state = state["model"]
if "state_dict" in state: state = state["state_dict"]
state = {k.removeprefix("module.").removeprefix("_orig_mod."): v for k, v in state.items()}
model.load_state_dict(state, strict=True, assign=True)
model.eval().cpu()
model.fuse_for_inference()
load_seconds = time.perf_counter() - t
source = a.input_dir
maps, times, inputs = [], [], []
for i in range(16):
    path = source / f"view_{i:02d}.png"
    bgr = cv2.imread(str(path))
    t = time.perf_counter()
    with torch.inference_mode():
        chw, _ = preprocess_numpy(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), input_size=a.resolution)
        raw = model(torch.from_numpy(chw).unsqueeze(0))
        result = torch.nn.functional.interpolate(raw.float(), bgr.shape[:2], mode="bilinear", align_corners=True)[0, 0].numpy()
    times.append(time.perf_counter() - t)
    assert result.shape == bgr.shape[:2]
    assert np.isfinite(result).all()
    maps.append(result)
    inputs.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    print(f"View {i:02d}: {times[-1]:.3f} seconds, range {result.min():.4f} to {result.max():.4f}", flush=True)
maps = np.stack(maps)
np.savez_compressed(out / "prediction.npz", inverse_relative_depth=maps, view_ids=np.arange(16))
cell, title = 192, 22
sheet = Image.new("RGB", (cell * 8, (cell + title) * 4), "white")
d = ImageDraw.Draw(sheet)
quantiles = []
for i, (rgb, raw) in enumerate(zip(inputs, maps)):
    mask = np.any(rgb < 235, axis=-1)
    lo, hi = np.quantile(raw[mask], [0.02, 0.98])
    quantiles.append([float(lo), float(hi)])
    # Display convention: near dark, far light. Background is white.
    norm = np.clip((raw - lo) / max(hi - lo, 1e-6), 0, 1)
    gray = ((1 - norm) * 223 + 16).astype(np.uint8)
    gray[~mask] = 255
    x, y = (i % 4) * cell * 2, (i // 4) * (cell + title)
    d.text((x + 4, y + 4), f"View {i:02d}: source / ZipDepth", fill="black")
    sheet.paste(Image.fromarray(rgb).resize((cell, cell)), (x, y + title))
    sheet.paste(Image.fromarray(gray).convert("RGB").resize((cell, cell)), (x + cell, y + title))
sheet.save(out / "depth_contact.png")
metadata = json.loads((ROOT / "models/metadata.json").read_text())
report = {
    "model": "ZipDepth Base NPU, via LibreYOLO 1.5.0 PyPI port",
    "source_url": "https://github.com/fabiotosi92/ZipDepth",
    "source_commit": metadata["official_commit"], "implementation_metadata": metadata,
    
    "checkpoint_sha256": hashlib.sha256(ckpt.read_bytes()).hexdigest(),
    "license": "MIT code and published checkpoint; DA2 Large teacher lineage documented",
    "parameters": sum(p.numel() for p in model.parameters()),
    "device": "cpu", "dtype": "float32", "threads": a.threads,
    "network_input_resolution": a.resolution,
    "output_shape": list(maps.shape),
    "output_convention": "Inverse relative depth; larger means nearer. Not meters, not calibrated across views.",
    "image_mapping": "Entire 312x312 crop is resized to the network square, then bilinearly returned to 312x312; no crop or recentering.",
    "load_seconds": load_seconds,
    "inference_seconds": sum(times), "per_view_seconds": times,
    "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    "per_view_foreground_display_quantiles": quantiles,
    "notes": [
        "All 16 existing original-sheet crops, no new image generation or hand modeling.",
        "Unchanged numerical files from PyPI LibreYOLO 1.5.0 and official tensor-only checkpoint. Empty package initializers isolate numerical modules; no full framework import.",
        "Depth contact visualization is independently normalized per view and cannot show absolute cross-view scale consistency.",
        "No camera pose or confidence prediction; do not substitute these maps directly into metric fusion.",
        "No paid inference API; download, setup, and load excluded from inference runtime."
    ]
}
(out / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2), flush=True)
