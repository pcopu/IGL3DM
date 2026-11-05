"""Validate the exported mesh's real ray masks and package human review assets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .core import mask_metrics, save_json
from .cli import contact_sheet


def on_white(image):
    rgba=image.convert("RGBA")
    bg=Image.new("RGBA",rgba.size,"white")
    return Image.alpha_composite(bg,rgba).convert("RGB")


def finish(directory):
    root=Path(directory);renders=root/"renders"
    report=json.loads((root/"report.json").read_text())
    manifest=json.loads((renders/"render_manifest.json").read_text())
    size=manifest["size"]
    predictions=[];targets=[];cards=[];compare=[];frames=[]
    for index,record in enumerate(manifest["frames"]):
        stem=record["stem"]
        image=on_white(Image.open(renders/"color"/f"{stem}.png"))
        frames.append((record["yaw_degrees"],image))
        if record["unseen_midpoint"]:continue
        with np.load(renders/"data"/f"{stem}.npz") as data:
            predicted=data["mask"].astype(bool)
        i=len(predictions)
        target=np.asarray(Image.open(root/"masks"/f"mask_{i:02d}.png").resize((size,size),Image.Resampling.NEAREST))>127
        predictions.append(predicted);targets.append(target)
        cards.append(image)
        diff=np.full((size,size,3),255,np.uint8)
        diff[target & predicted]=[45,140,95]
        diff[target & ~predicted]=[220,75,65]
        diff[~target & predicted]=[60,115,220]
        compare.append(Image.fromarray(diff))
    metrics=mask_metrics(predictions,targets)
    report["actual_mesh_reprojection"]=metrics
    report["render_status"]="completed"
    report["render_validation"]={"frames":len(manifest["frames"]),
                                 "unseen_yaw_frames":sum(r["unseen_midpoint"] for r in manifest["frames"]),
                                 "geometry_changed_by_renderer":manifest["geometry_changed"],
                                 "comparison":"pixel-center mesh ray masks against segmented inputs; no 3D ground truth",
                                 "elapsed_seconds":manifest["elapsed_seconds"]}
    save_json(root/"report.json",report)
    contact_sheet(cards).save(root/"rendered_views.png")
    contact_sheet(compare).save(root/"mesh_silhouette_comparison.png")
    frames=[im for _,im in sorted(frames,key=lambda pair:pair[0])]
    # Quantize every frame using one shared palette, avoiding palette flicker.
    palette_image=contact_sheet(frames,columns=8).quantize(colors=255)
    indexed=[im.quantize(palette=palette_image,dither=Image.Dither.NONE) for im in frames]
    indexed[0].save(root/"turntable.gif",save_all=True,append_images=indexed[1:],
                    duration=100,loop=0,optimize=False,disposal=2)
    strip=Image.new("RGB",(size*4,size*2+38),"white")
    for row,indices in enumerate(([0,4,8,12],[0,4,8,12])):
        for col,i in enumerate(indices):
            im=Image.open(root/"views"/f"view_{i:02d}.png").resize((size,size)) if row==0 else cards[i]
            strip.paste(on_white(im),(col*size,row*size+19))
    draw=ImageDraw.Draw(strip)
    draw.text((6,3),"GENERATED REFERENCE: assumed camera angles",fill="black")
    draw.text((6,size+3),"ACTUAL SOFTWARE MESH: no manual modeling",fill="black")
    strip.save(root/"reference_vs_mesh.png")
    print(json.dumps({"actual_mesh_mean_iou":metrics["mean_iou"],"actual_mesh_worst_iou":metrics["worst_iou"],
                      "frames":len(frames),"gif":str(root/"turntable.gif")},indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    args=parser.parse_args()
    finish(args.run_directory)


if __name__=="__main__":main()
