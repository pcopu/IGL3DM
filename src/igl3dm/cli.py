"""Reproducible one-atlas experiment. No model weights, APIs or manual sculpting."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

from .core import (Camera, orbit_cameras, split_atlas, segment, grid_points, silhouette_fields,
                   carve, project_occupancy, mask_metrics, extract_mesh,
                   mesh_integrity, vertex_colors, save_ply, save_json, sha256)


def contact_sheet(images, columns=4, background="white"):
    rows=(len(images)+columns-1)//columns
    w,h=images[0].size
    result=Image.new("RGB",(columns*w,rows*h),background)
    for i,im in enumerate(images):result.paste(im.convert("RGB"),((i%columns)*w,(i//columns)*h))
    return result


def run(args):
    started=time.monotonic()
    out=Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"Output directory is not empty: {out}. Use a new run directory.")
    out.mkdir(parents=True,exist_ok=True)
    atlas=Image.open(args.atlas)
    all_tiles=split_atlas(atlas,args.rows,args.columns,args.gutter)
    elevations=[args.elevation] if args.elevation_bands is None else [float(v) for v in args.elevation_bands.split(",")]
    all_cameras=orbit_cameras(len(all_tiles),elevations)
    source_indices=list(range(len(all_tiles)))
    if args.view_range is not None:
        bounds=args.view_range.split(":")
        if len(bounds)!=2:raise ValueError("view-range must be START:END, with end exclusive")
        start,end=map(int,bounds)
        if not 0 <= start < end <= len(all_tiles):raise ValueError("view-range is outside the atlas")
        source_indices=source_indices[start:end]
    tiles=[all_tiles[i] for i in source_indices]
    cameras=[all_cameras[i] for i in source_indices]
    camera_manifest={"views":[{"yaw_degrees":c.yaw_degrees,"elevation_degrees":c.elevation_degrees,
                               "source_view_index":source_indices[i]} for i,c in enumerate(cameras)]}
    save_json(out/"cameras.json",camera_manifest)
    view_dir=out/"views";view_dir.mkdir()
    mask_dir=out/"masks";mask_dir.mkdir()
    masks=[];segmentation=[];working_tiles=[]
    for i,tile in enumerate(tiles):
        tile.save(view_dir/f"view_{i:02d}.png")
        tile=tile.resize((args.image_size,args.image_size),Image.Resampling.LANCZOS)
        working_tiles.append(tile)
        mask,info=segment(tile,args.background_threshold)
        info["view"]=i
        info["source_view_index"]=source_indices[i]
        masks.append(mask);segmentation.append(info)
        Image.fromarray((mask*255).astype("uint8")).save(mask_dir/f"mask_{i:02d}.png")
    count=len(masks)
    if args.max_misses>=count or (args.fixed_misses is not None and not 0 <= args.fixed_misses < count):
        raise ValueError("Miss tolerance must be nonnegative and smaller than the view count")
    points=grid_points(args.resolution)
    fields=silhouette_fields(masks,cameras,points)
    candidates=[];best=None
    miss_values = range(args.max_misses+1) if args.fixed_misses is None else [args.fixed_misses]
    for misses in miss_values:
        try:
            field,occupied,info=carve(fields,args.resolution,misses,args.smooth_sigma)
            projections=project_occupancy(occupied,points,cameras,args.image_size)
            info["voxel_reprojection"]=mask_metrics(projections,masks)
            candidates.append(info)
            # This selects fit to synthetic targets, not a ground-truth accuracy claim.
            score=info["voxel_reprojection"]["mean_iou"]
            if best is None or score>best[0]:best=(score,field,occupied,info,projections)
        except ValueError as exc:
            candidates.append({"allowed_misses":misses,"error":str(exc)})
    if best is None:
        save_json(out/"failure.json",{"candidates":candidates,"segmentation":segmentation})
        raise ValueError("No common solid. See failure.json; do not call this a reconstruction.")
    _,field,occupied,chosen,projections=best
    vertices,faces=extract_mesh(field)
    colors,color_info=vertex_colors(vertices,faces,working_tiles,masks,cameras)
    save_ply(out/"model.ply",vertices,faces,colors)
    save_json(out/"mesh.json",{"vertices":vertices.tolist(),"faces":faces.tolist(),"colors":colors.tolist()})
    np.savez_compressed(out/"field.npz",signed_field=field,occupied=occupied,voxel_resolution=args.resolution)
    diagnostic=[]
    for mask,pred in zip(masks,projections):
        rgb=np.full((*mask.shape,3),255,dtype=np.uint8)
        rgb[mask & pred]=[45,140,95]     # agreement
        rgb[mask & ~pred]=[220,75,65]   # missing
        rgb[~mask & pred]=[60,115,220]  # excess
        diagnostic.append(Image.fromarray(rgb))
    contact_sheet(diagnostic).save(out/"silhouette_comparison.png")
    contact_sheet(working_tiles).save(out/"input_views.png")
    warnings=[
        "The input is a generated multiview drawing, not calibrated photographic evidence.",
        "Yaw/elevation and orthographic projection are assumptions requested of ImageGen, not recovered measurements.",
        "Silhouettes cannot recover invisible concavities, correct anatomical topology, or exact wireframe vertices.",
        "Voxel reprojection scores are approximate selection diagnostics. They can rank candidates differently from final mesh masks; compare fixed-misses runs before claiming the best fit.",
        "Painted mesh lines and colors are appearance only; they are not vertex IDs or measured depth.",
    ]
    if chosen["allowed_misses"]:
        warnings.append(f"Selected relaxed hull tolerates {chosen['allowed_misses']} contradictory views per voxel.")
    if chosen["boundary_voxel_hits"]:warnings.append("Hull touches volume boundary; geometry may be truncated.")
    if any(s["touches_frame"] for s in segmentation):warnings.append("At least one segmented view touches the frame; generated source may be clipped.")
    report={"schema_version":1,"created_at_utc":datetime.now(timezone.utc).isoformat(),
        "input":{"filename":Path(args.atlas).name,"sha256":sha256(args.atlas),"size":list(atlas.size),
                 "view_count":count,"atlas_view_count":len(all_tiles),"selected_source_indices":source_indices,"imagegen_calls_for_this_input":args.imagegen_calls,
                 "provenance_note":"Call count is caller-provided experiment provenance, not verified by image pixels."},
        "method":"common-camera silhouette visual hull; marching tetrahedra; approximate visibility-aware vertex color projection",
        "manual_modeling":False,"wireframe_vertices_decoded":False,"learned_depth_model_used":False,
        "config":{"rows":args.rows,"columns":args.columns,"gutter_pixels":args.gutter,
                  "working_image_size":args.image_size,"resolution":args.resolution,"max_misses":args.max_misses,"fixed_misses":args.fixed_misses,
                  "smooth_sigma_voxels":args.smooth_sigma,"background_threshold":args.background_threshold,
                  "cell_alignment":"shared grid; no per-view silhouette translation or scaling"},
        "camera_convention":{"coordinate_system":"right-handed z-up","yaw0_location":[0,-4,0],
                             "yaw_positive":"camera moves from -Y toward +X","orthographic_scale":2.0,
                             "elevation_bands_degrees":elevations,"per_view":camera_manifest["views"]},
        "segmentation":segmentation,"candidates":candidates,"selected":chosen,
        "mesh":mesh_integrity(vertices,faces),"color_projection":color_info,"warnings":warnings,
        "elapsed_seconds_before_render":time.monotonic()-started,"render_status":"not_requested"}
    save_json(out/"report.json",report)
    print(json.dumps({"output":str(out),"mesh":report["mesh"],"selected":chosen},indent=2),flush=True)
    if args.render:
        blender=shutil.which(args.blender)
        if not blender:raise ValueError(f"Blender executable not found: {args.blender}")
        script=Path(__file__).resolve().parents[2]/"scripts"/"render_mesh.py"
        if not script.exists():raise ValueError(f"Renderer script missing: {script}")
        command=[blender,"-b","--python-exit-code","1","--threads",str(args.render_threads),"--python",str(script),"--",
                 "--mesh",str((out/"mesh.json").resolve()),"--output",str((out/"renders").resolve()),
                 "--size",str(args.render_size),"--views",str(count),"--elevation",str(args.elevation),
                 "--midpoints","--save-blend","--cameras",str((out/"cameras.json").resolve())]
        with (out/"blender.log").open("w") as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=False)
        report["render_status"]="completed" if result.returncode==0 else "failed"
        report["render_exit_code"]=result.returncode
        report["elapsed_seconds_total"]=time.monotonic()-started
        save_json(out/"report.json",report)
        if result.returncode:raise ValueError(f"Blender failed with {result.returncode}; see {out/'blender.log'}")
        from .finish import finish
        report=finish(out)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("atlas",help="Single generated atlas image (static PNG/JPG)")
    parser.add_argument("--output",required=True,help="New, empty directory for artifacts")
    parser.add_argument("--rows",type=int,default=4);parser.add_argument("--columns",type=int,default=4)
    parser.add_argument("--gutter",type=int,default=2,help="Uniform pixels trimmed from each cell edge")
    parser.add_argument("--image-size",type=int,default=192)
    parser.add_argument("--resolution",type=int,default=80)
    parser.add_argument("--max-misses",type=int,default=2)
    parser.add_argument("--fixed-misses",type=int,default=None,help="Evaluate exactly this tolerance, bypassing approximate voxel-score selection")
    parser.add_argument("--smooth-sigma",type=float,default=0.6)
    parser.add_argument("--background-threshold",type=float,default=32)
    parser.add_argument("--elevation",type=float,default=0)
    parser.add_argument("--elevation-bands",default=None,help="Comma-separated elevations for band-major full orbits, e.g. 15,-15")
    parser.add_argument("--view-range",default=None,help="Use source atlas indices START:END (end exclusive), preserving their cameras")
    parser.add_argument("--imagegen-calls",type=int,default=None,help="Caller-attested generation call count; omitted means unknown")
    parser.add_argument("--render",action="store_true")
    parser.add_argument("--render-size",type=int,default=256)
    parser.add_argument("--render-threads",type=int,default=4)
    parser.add_argument("--blender",default="blender")
    args=parser.parse_args()
    if args.image_size<32 or args.render_size<32 or args.smooth_sigma<0:
        parser.error("Image/render size must be >=32 and smoothing must be nonnegative")
    try:run(args)
    except (ValueError,OSError) as exc:parser.exit(1,f"igl3dm: {exc}\n")


if __name__=="__main__":main()
