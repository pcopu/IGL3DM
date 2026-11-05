"""Official TripoSR CPU baseline on an existing generated lion view."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parent
os.environ["HF_HOME"]=str(ROOT/"hf-cache")
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
os.environ["DO_NOT_TRACK"]="1"
os.environ["NUMBA_CACHE_DIR"]=str(ROOT/"numba-cache")
sys.path.insert(0,str(ROOT/"TripoSR"))
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from omegaconf import OmegaConf
from PIL import Image
import onnxruntime
onnxruntime.disable_telemetry_events()
from tsr.system import TSR
from tsr.utils import resize_foreground

p=argparse.ArgumentParser()
p.add_argument("--source-run",type=Path,required=True,help="Pipeline run with views/ and masks/")
p.add_argument("--view",type=int,default=0)
p.add_argument("--resolution",type=int,default=128)
p.add_argument("--threads",type=int,default=4)
p.add_argument("--chunk",type=int,default=4096)
p.add_argument("--output",default="view00_128")
a=p.parse_args()
torch.set_num_threads(a.threads);torch.set_num_interop_threads(1);torch.manual_seed(0)
out=ROOT/"outputs"/a.output
if out.exists() and any(out.iterdir()):p.error("Output is not empty")
out.mkdir(parents=True,exist_ok=True)
source=a.source_run
image_path=source/"views"/f"view_{a.view:02d}.png"
mask_path=source/"masks"/f"mask_{a.view:02d}.png"
rgb=np.array(Image.open(image_path).convert("RGB"))
mask=np.array(Image.open(mask_path).convert("L").resize((rgb.shape[1],rgb.shape[0]),Image.Resampling.NEAREST))
assert rgb.shape[:2]==mask.shape,(rgb.shape,mask.shape)
rgba=Image.fromarray(np.dstack([rgb,mask]))
rgba=resize_foreground(rgba,0.85)
arr=np.array(rgba).astype(np.float32)/255
arr=arr[...,:3]*arr[...,3:4]+(1-arr[...,3:4])*0.5
image=Image.fromarray((arr*255).astype(np.uint8));image.save(out/"input.png")
checkpoint=ROOT/"models/TripoSR/model.ckpt"
h=hashlib.sha256()
with checkpoint.open("rb") as f:
    while b:=f.read(8*1024*1024):h.update(b)
print("Checkpoint SHA256",h.hexdigest(),flush=True)
t=time.perf_counter()
cfg=OmegaConf.load(ROOT/"models/TripoSR/config.yaml");OmegaConf.resolve(cfg)
model=TSR(cfg).eval().cpu()
print("Model constructed",sum(p.numel() for p in model.parameters()),"parameters",flush=True)
# Tensor-only loading, memory mapped to avoid a second resident copy.
state=torch.load(checkpoint,map_location="cpu",weights_only=True,mmap=True)
model.load_state_dict(state,strict=True,assign=True)
del state
model.renderer.set_chunk_size(a.chunk)
load_seconds=time.perf_counter()-t
print("Model loaded",load_seconds,"seconds",flush=True)
t=time.perf_counter()
with torch.inference_mode():codes=model([image],device="cpu")
inference_seconds=time.perf_counter()-t
print("Inference",inference_seconds,"seconds",tuple(codes.shape),flush=True)
np.save(out/"scene_codes.npy",codes.detach().cpu().numpy())
t=time.perf_counter()
mesh=model.extract_mesh(codes,True,resolution=a.resolution)[0]
mesh_seconds=time.perf_counter()-t
print("Mesh extracted",mesh_seconds,"seconds",len(mesh.vertices),len(mesh.faces),flush=True)
mesh.export(out/"mesh.glb");mesh.export(out/"mesh.ply")
components=mesh.split(only_watertight=False)
report={"model":"stabilityai/TripoSR","source_view":str(image_path),"source_mask":str(mask_path),
        "source_commit":"107cefdc244c39106fa830359024f6a2f1c78871",
        "model_revision":"5b521936b01fbe1890f6f9baed0254ab6351c04a",
        "checkpoint_sha256":h.hexdigest(),"device":"cpu","dtype":"float32","threads":a.threads,
        "parameters":sum(p.numel() for p in model.parameters()),"torch":torch.__version__,
        "image_preprocessing":"Existing 192-pixel pipeline mask nearest-resized to the 312-pixel source view, official resize_foreground at 0.85, alpha composited on neutral gray.",
        "mesh_resolution":a.resolution,"chunk_size":a.chunk,"load_seconds":load_seconds,
        "inference_seconds":inference_seconds,"mesh_extraction_seconds":mesh_seconds,
        "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "vertices":len(mesh.vertices),"faces":len(mesh.faces),"watertight":bool(mesh.is_watertight),
        "winding_consistent":bool(mesh.is_winding_consistent),"components":len(components),
        "component_face_counts":sorted([len(m.faces) for m in components],reverse=True),
        "bounds":mesh.bounds.tolist(),"notes":["No new imagegen calls or hand modeling.",
        "Official TripoSR source is unchanged; a local API adapter uses standard scikit-image marching cubes as a documented numerical backend substitution.",
        "One view conditions a learned complete-object prior, not measured reconstruction of every sheet view.",
        "No paid inference service used. Runtime excludes download and installation."]}
(out/"metrics.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2),flush=True)
