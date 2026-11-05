"""Confidence-gated software-depth displacement of one shared mesh.

No anatomical primitives, new vertices, new faces, hand modeling, or decoded
ImageGen wireframe vertices. Fixed mesh vertex IDs are retained. Depth is fitted
only at spatial training pixels; held-out blocks remain evaluation-only.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.linalg import cg

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from igl3dm.core import Camera, mesh_integrity, save_json, save_ply

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--baseline",type=Path,required=True)
p.add_argument("--aligned",type=Path,required=True)
p.add_argument("--output",type=Path,required=True)
p.add_argument("--prior",type=float,default=3.0)
p.add_argument("--smooth",type=float,default=1.0)
p.add_argument("--max-displacement",type=float,default=.03)
a=p.parse_args()
if a.output.exists() and any(a.output.iterdir()):p.error("Output already exists")
a.output.mkdir(parents=True,exist_ok=True)
m=json.loads((a.baseline/"mesh.json").read_text());v=np.asarray(m["vertices"],float);f=np.asarray(m["faces"],int);colors=np.asarray(m["colors"],float)
report=json.loads((a.baseline/"report.json").read_text())
n=np.zeros_like(v)
fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
for k in range(3):np.add.at(n,f[:,k],fn)
n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-14)
with np.load(a.aligned) as raw:data={k:raw[k] for k in raw.files}
weights=np.zeros(len(v));rhs=np.zeros(len(v));records=[]
for i in range(len(data["calibrated"])):
 c=Camera(i*360/len(data["calibrated"]))
 size=data["calibrated"].shape[1]
 uv=c.project(v,size)
 xy=np.rint(uv).astype(int)
 in_frame=(xy[:,0]>=0)&(xy[:,0]<size)&(xy[:,1]>=0)&(xy[:,1]<size)
 x=np.clip(xy[:,0],0,size-1);y=np.clip(xy[:,1],0,size-1)
 target=data["calibrated"][i,y,x]
 surface=data["mesh_depth"][i,y,x]
 mask=data["valid_mask"][i,y,x]&data["fit_train_mask"][i,y,x]&in_frame
 toward=c.basis()[2];depth=4-v@toward;facing=n@toward
 mask &= np.isfinite(target)&np.isfinite(surface)&(np.abs(depth-surface)<.03)&(facing>.25)
 w=data["confidence_weight"][i,y,x]*mask
 residual=np.where(mask,target-depth,0)
 coeff=-facing
 weights+=w*coeff*coeff;rhs+=w*coeff*residual
 records.append({"view":i,"used_vertices":int(mask.sum()),"mean_absolute_initial_residual":float(np.abs(residual[mask]).mean()) if mask.any() else None})
edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);edges=np.unique(edges,axis=0)
row=np.concatenate([edges[:,0],edges[:,1]]);col=np.concatenate([edges[:,1],edges[:,0]])
adj=sparse.coo_matrix((np.ones(len(row)),(row,col)),shape=(len(v),len(v))).tocsr()
laplacian=sparse.diags(np.asarray(adj.sum(axis=1)).ravel())-adj
system=sparse.diags(weights+a.prior)+a.smooth*laplacian
shift,status=cg(system,rhs,rtol=1e-7,atol=1e-10,maxiter=500)
if status:raise RuntimeError(f"Conjugate gradient did not converge: {status}")
shift=np.clip(shift,-a.max_displacement,a.max_displacement)
displacement=n*shift[:,None]
old_cross=fn;old_norm=np.linalg.norm(old_cross,axis=1)
nonzero=old_norm>0
scale=1.0;attempts=[]
for _ in range(24):
 candidate=v+scale*displacement
 new_cross=np.cross(candidate[f[:,1]]-candidate[f[:,0]],candidate[f[:,2]]-candidate[f[:,0]])
 flips=int(np.count_nonzero(np.einsum('ij,ij->i',new_cross[nonzero],old_cross[nonzero])<=0))
 attempts.append({"scale":scale,"flipped_or_collapsed_faces":flips})
 if flips==0:break
 scale*=.5
else:raise RuntimeError("No orientation-preserving step found")
new=v+scale*displacement
save_json(a.output/"mesh.json",{"vertices":new.tolist(),"faces":f.tolist(),"colors":colors.tolist()})
save_ply(a.output/"model.ply",new,f,colors)
np.savez_compressed(a.output/"vertex_displacement.npz",displacement=scale*displacement,weights=weights,vertex_ids=np.arange(len(v)))
result={"method":"one shared mesh, confidence-gated train-pixel depth residuals, regularized normal displacement",
        "manual_modeling":False,"vertex_count_unchanged":True,"faces_unchanged":True,"colors_unchanged":True,
        "accepted_views":np.flatnonzero(data["view_gate"]).tolist(),"config":{"prior":a.prior,"smooth":a.smooth,"max_displacement":a.max_displacement},
        "applied_step_scale":scale,"line_search":attempts,"per_view":records,"constrained_vertices":int((weights>0).sum()),
        "displacement_max":float(np.linalg.norm(scale*displacement,axis=1).max()),
        "displacement_mean":float(np.linalg.norm(scale*displacement,axis=1).mean()),"mesh":mesh_integrity(new,f),
        "limitations":["Depth is relative and empirically aligned to an approximate mesh.","Orthographic rig is assumed; the learned depth model assumes perspective imagery.","Pixel holdout is not independent geometric truth; spatial regularization also couples nearby vertices.","Self-intersections are not checked."]}
save_json(a.output/"fit_report.json",result)
print(json.dumps(result,indent=2))
