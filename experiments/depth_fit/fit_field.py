"""Smooth, bounded software-depth warp with unchanged mesh vertex IDs/faces."""
import argparse
import json
from pathlib import Path
import sys
import shutil
import hashlib
import numpy as np
from scipy import ndimage
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from igl3dm.core import Camera, mesh_integrity, save_json, save_ply

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--baseline",type=Path,required=True);p.add_argument("--aligned",type=Path,required=True)
p.add_argument("--output",type=Path,required=True);p.add_argument("--prior",type=float,default=.2)
p.add_argument("--grid",type=int,default=24);p.add_argument("--sigma",type=float,default=1.5)
p.add_argument("--max-displacement",type=float,default=.03);p.add_argument("--gradient-bound",type=float,default=.25)
a=p.parse_args()
if a.grid<4 or a.sigma<=0 or a.prior<0 or a.max_displacement<0 or not 0<a.gradient_bound<1:p.error("Invalid deformation bounds")
if a.output.exists() and any(a.output.iterdir()):p.error("Output already exists")
a.output.mkdir(parents=True,exist_ok=True)
m=json.loads((a.baseline/"mesh.json").read_text());v=np.asarray(m["vertices"],float);f=np.asarray(m["faces"],int);colors=np.asarray(m["colors"],float)
fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
n=np.zeros_like(v)
for k in range(3):np.add.at(n,f[:,k],fn)
n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-14)
with np.load(a.aligned) as raw:data={k:raw[k] for k in raw.files}
if (a.baseline/"cameras.json").exists():
 camera_specs=json.loads((a.baseline/"cameras.json").read_text())["views"]
 cameras=[Camera(c["yaw_degrees"],c["elevation_degrees"]) for c in camera_specs]
else:cameras=[Camera(i*360/len(data["calibrated"])) for i in range(len(data["calibrated"]))]
if len(cameras)!=len(data["calibrated"]):raise ValueError("Camera/depth view count mismatch")
weight=np.zeros(len(v));target=np.zeros_like(v);records=[]
for i in range(len(data["calibrated"])):
 c=cameras[i]
 size=data["calibrated"].shape[1];uv=c.project(v,size);xy=np.rint(uv).astype(int)
 in_frame=(xy[:,0]>=0)&(xy[:,0]<size)&(xy[:,1]>=0)&(xy[:,1]<size)
 x=np.clip(xy[:,0],0,size-1);y=np.clip(xy[:,1],0,size-1)
 observed=data["calibrated"][i,y,x];surface=data["mesh_depth"][i,y,x]
 toward=c.basis()[2];depth=4-v@toward;facing=n@toward
 mask=data["valid_mask"][i,y,x]&data["fit_train_mask"][i,y,x]&in_frame
 mask &= np.isfinite(observed)&np.isfinite(surface)&(np.abs(depth-surface)<.03)&(facing>.25)
 w=data["confidence_weight"][i,y,x]*mask*facing**2
 residual=np.where(mask,observed-depth,0)
 target += (-toward[None,:])*residual[:,None]*w[:,None];weight+=w
 records.append({"view":i,"used_vertices":int(mask.sum())})
g=a.grid;spacing=2/(g-1)
index=np.clip(np.rint((v+1)/2*(g-1)).astype(int),0,g-1)
den=np.zeros((g,g,g));num=np.zeros((g,g,g,3))
np.add.at(den,tuple(index.T),weight)
for j in range(3):np.add.at(num[...,j],tuple(index.T),target[:,j])
den=ndimage.gaussian_filter(den,a.sigma)
for j in range(3):num[...,j]=ndimage.gaussian_filter(num[...,j],a.sigma)
prior=a.prior*float(np.percentile(den[den>0],90))
field=num/(den[...,None]+max(prior,1e-8))
length=np.linalg.norm(field,axis=-1,keepdims=True)
field*=np.minimum(1,a.max_displacement/np.maximum(length,1e-12))
# Conservative global Frobenius bound from maximum edge slopes for all nine
# derivative components. Trilinear derivatives are convex mixtures of these.
bound=np.sqrt(sum(float(np.max(np.abs(np.diff(field[...,j],axis=k)/spacing)))**2 for j in range(3) for k in range(3)))
gradient_scale=min(1,a.gradient_bound/max(bound,1e-12));field*=gradient_scale
coords=((v+1)/2*(g-1)).T
displacement=np.stack([ndimage.map_coordinates(field[...,j],coords,order=1,mode="nearest") for j in range(3)],axis=-1)
scale=1.;attempts=[];nonzero=np.linalg.norm(fn,axis=1)>0
for _ in range(24):
 candidate=v+scale*displacement
 newfn=np.cross(candidate[f[:,1]]-candidate[f[:,0]],candidate[f[:,2]]-candidate[f[:,0]])
 flips=int(np.count_nonzero(np.einsum('ij,ij->i',newfn[nonzero],fn[nonzero])<=0))
 attempts.append({"scale":scale,"flipped_or_collapsed_faces":flips})
 if flips==0:break
 scale*=.5
else:raise RuntimeError("No orientation-preserving step")
new=v+scale*displacement
save_json(a.output/"mesh.json",{"vertices":new.tolist(),"faces":f.tolist(),"colors":colors.tolist()})
save_ply(a.output/"model.ply",new,f,colors)
np.savez_compressed(a.output/"vertex_displacement.npz",displacement=scale*displacement,field=field*scale,vertex_ids=np.arange(len(v)))
result={"method":"smooth low-resolution displacement field from accepted software-depth train pixels",
        "manual_modeling":False,"vertex_count_unchanged":True,"faces_unchanged":True,"colors_unchanged":True,
        "accepted_views":np.flatnonzero(data["view_gate"]).tolist(),"config":{"prior":a.prior,"grid":g,"sigma":a.sigma,"max_displacement":a.max_displacement,"gradient_bound":a.gradient_bound},
        "unscaled_gradient_bound":bound,"gradient_scale":gradient_scale,"applied_step_scale":scale,"line_search":attempts,
        "per_view":records,"constrained_vertices":int((weight>0).sum()),
        "displacement_max":float(np.linalg.norm(scale*displacement,axis=1).max()),"displacement_mean":float(np.linalg.norm(scale*displacement,axis=1).mean()),
        "mesh":mesh_integrity(new,f),"limitations":["Relative depth was empirically aligned to an imperfect visual hull.","Camera-z under a learned perspective model is compared with an assumed orthographic rig.","Assessment pixels are excluded from fitting but used by view gates; this is not a blind independent validation. Smooth deformation also couples nearby vertices.","No anatomical primitives or manual corrections were used.","Self-intersections are not directly tested; deformation gradient and face orientation are bounded."]}
result["baseline_mesh_sha256"]=hashlib.sha256((a.baseline/"mesh.json").read_bytes()).hexdigest()
result["aligned_depth_sha256"]=hashlib.sha256(a.aligned.read_bytes()).hexdigest()
result["additional_imagegen_calls"]=0
save_json(a.output/"fit_report.json",result)
if (a.baseline/"report.json").exists():
 report=json.loads((a.baseline/"report.json").read_text())
 for key in ("actual_mesh_reprojection","actual_mesh_reprojection_by_elevation","render_validation"):
  report.pop(key,None)
 report.update({"mesh":result["mesh"],"method":result["method"],"depth_fit":result,"render_status":"not_requested"})
 save_json(a.output/"report.json",report)
 for name in ("views","masks"):
  if (a.baseline/name).exists():shutil.copytree(a.baseline/name,a.output/name)
 if (a.baseline/"cameras.json").exists():shutil.copy2(a.baseline/"cameras.json",a.output/"cameras.json")
print(json.dumps(result,indent=2))
