#!/usr/bin/env python3
"""Render a mesh against cameras held out from the same generated atlas.

This is image-space validation under assumed cameras, not 3D ground truth.
The reference run supplies every target mask and its camera manifest.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
from PIL import Image
from igl3dm.core import mask_metrics, save_json, sha256
from igl3dm.cli import contact_sheet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-run",type=Path,required=True)
    parser.add_argument("--reference-run",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--size",type=int,default=192)
    parser.add_argument("--blender",default="blender")
    args=parser.parse_args()
    source=json.loads((args.mesh_run/"report.json").read_text())
    reference=json.loads((args.reference_run/"report.json").read_text())
    if source["input"]["sha256"]!=reference["input"]["sha256"]:
        parser.error("A held-out comparison must use the same source atlas")
    if args.output.exists() and any(args.output.iterdir()):parser.error("Output directory is not empty")
    args.output.mkdir(parents=True,exist_ok=True)
    cameras=json.loads((args.reference_run/"cameras.json").read_text())["views"]
    renderer=Path(__file__).resolve().parent/"render_mesh.py"
    command=[args.blender,"-b","--python-exit-code","1","--threads","4","--python",str(renderer),"--",
             "--mesh",str((args.mesh_run/"mesh.json").resolve()),"--output",str((args.output/"renders").resolve()),
             "--cameras",str((args.reference_run/"cameras.json").resolve()),"--size",str(args.size),"--views",str(len(cameras))]
    with (args.output/"blender.log").open("w") as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    predictions=[];targets=[];panels=[]
    for i,camera in enumerate(cameras):
        with np.load(args.output/"renders"/"data"/f"view_{i:03d}.npz") as data:prediction=data["mask"].astype(bool)
        target=np.asarray(Image.open(args.reference_run/"masks"/f"mask_{i:02d}.png").resize((args.size,args.size),Image.Resampling.NEAREST))>127
        predictions.append(prediction);targets.append(target)
        panel=np.full((args.size,args.size,3),255,np.uint8)
        panel[prediction&target]=[45,140,95];panel[target&~prediction]=[220,75,65];panel[prediction&~target]=[60,115,220]
        panels.append(Image.fromarray(panel))
    trained=set(source["input"]["selected_source_indices"])
    heldout=[i for i,c in enumerate(cameras) if c["source_view_index"] not in trained]
    fitted=[i for i,c in enumerate(cameras) if c["source_view_index"] in trained]
    def subset(indices):
        return mask_metrics([predictions[i] for i in indices],[targets[i] for i in indices]) if indices else None
    result={"source_atlas_sha256":source["input"]["sha256"],"mesh_json_sha256":sha256(args.mesh_run/"mesh.json"),
            "trained_source_indices":sorted(trained),"evaluated_source_indices":[c["source_view_index"] for c in cameras],
            "heldout_source_indices":[cameras[i]["source_view_index"] for i in heldout],
            "all_views":mask_metrics(predictions,targets),"fitted_views":subset(fitted),"heldout_views":subset(heldout),
            "limitations":["Generated cameras remain assumed, not measured.","Image-space consistency is not ground-truth 3D accuracy."]}
    save_json(args.output/"metrics.json",result)
    contact_sheet(panels).save(args.output/"silhouette_comparison.png")
    print(json.dumps({key:result[key]["mean_iou"] if result[key] else None for key in ("all_views","fitted_views","heldout_views")},indent=2))


if __name__=="__main__":main()
