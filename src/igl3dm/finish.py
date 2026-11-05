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
    predictions=[];targets=[];cards=[];compare=[];frames=[];source_records=[]
    for index,record in enumerate(manifest["frames"]):
        stem=record["stem"]
        image=on_white(Image.open(renders/"color"/f"{stem}.png"))
        frames.append((record["elevation_degrees"],record["yaw_degrees"],image))
        if record["unseen_midpoint"]:continue
        with np.load(renders/"data"/f"{stem}.npz") as data:
            predicted=data["mask"].astype(bool)
        i=len(predictions)
        target=np.asarray(Image.open(root/"masks"/f"mask_{i:02d}.png").resize((size,size),Image.Resampling.NEAREST))>127
        predictions.append(predicted);targets.append(target);source_records.append(record)
        cards.append(image)
        diff=np.full((size,size,3),255,np.uint8)
        diff[target & predicted]=[45,140,95]
        diff[target & ~predicted]=[220,75,65]
        diff[~target & predicted]=[60,115,220]
        compare.append(Image.fromarray(diff))
    metrics=mask_metrics(predictions,targets)
    report["actual_mesh_reprojection"]=metrics
    elevations=list(dict.fromkeys(r["elevation_degrees"] for r in source_records))
    report["actual_mesh_reprojection_by_elevation"]={str(e):mask_metrics(
        [p for p,r in zip(predictions,source_records) if r["elevation_degrees"]==e],
        [t for t,r in zip(targets,source_records) if r["elevation_degrees"]==e]) for e in elevations}
    report["render_status"]="completed"
    report["render_validation"]={"frames":len(manifest["frames"]),
                                 "unseen_yaw_frames":sum(r["unseen_midpoint"] for r in manifest["frames"]),
                                 "geometry_changed_by_renderer":manifest["geometry_changed"],
                                 "comparison":"pixel-center mesh ray masks against segmented inputs; no 3D ground truth",
                                 "elapsed_seconds":manifest["elapsed_seconds"]}
    save_json(root/"report.json",report)
    contact_sheet(cards).save(root/"rendered_views.png")
    contact_sheet(compare).save(root/"mesh_silhouette_comparison.png")
    def save_gif(ordered_frames,path):
        # One shared palette for the entire animation, avoiding palette flicker.
        palette_image=contact_sheet(ordered_frames,columns=8).quantize(colors=255)
        indexed=[im.quantize(palette=palette_image,dither=Image.Dither.NONE) for im in ordered_frames]
        indexed[0].save(path,save_all=True,append_images=indexed[1:],
                        duration=100,loop=0,optimize=False,disposal=2)
    grouped={e:[im for _,_,im in sorted([f for f in frames if f[0]==e],key=lambda f:f[1])] for e in elevations}
    save_gif(grouped[elevations[0]],root/"turntable.gif")
    if len(elevations)>1:
        for e,images in grouped.items():save_gif(images,root/f"turntable_elevation_{e:g}.gif")
        if len(set(len(images) for images in grouped.values()))==1:
            paired=[contact_sheet([grouped[e][i] for e in elevations],columns=len(elevations))
                    for i in range(len(grouped[elevations[0]]))]
            save_gif(paired,root/"turntable_bands.gif")
    strip=Image.new("RGB",(size*4,len(elevations)*2*(size+20)),"white")
    draw=ImageDraw.Draw(strip)
    for band,e in enumerate(elevations):
        indices=[i for i,r in enumerate(source_records) if r["elevation_degrees"]==e]
        selected=[indices[min(len(indices)-1,j*len(indices)//4)] for j in range(4)]
        for kind in range(2):
            y=(band*2+kind)*(size+20)
            label="GENERATED REFERENCE" if kind==0 else "ACTUAL SOFTWARE MESH"
            draw.text((6,y+3),f"{label} | assumed elevation {e:g} degrees",fill="black")
            for col,i in enumerate(selected):
                im=Image.open(root/"views"/f"view_{i:02d}.png").resize((size,size)) if kind==0 else cards[i]
                strip.paste(on_white(im),(col*size,y+20))
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
