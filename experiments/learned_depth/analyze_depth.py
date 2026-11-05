"""Visual QA and reprojection diagnostics of learned, unposed depth outputs."""
import argparse
import json
from pathlib import Path
import numpy as np
import scipy.ndimage as ndi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument("run");a=p.parse_args()
root=Path(__file__).resolve().parent/"outputs"/a.run
run_metadata=json.loads((root/"metrics.json").read_text())
data=np.load(root/"prediction.npz")
depth=data["depth"][0]; conf=data["depth_conf"][0]
ext=data["extrinsics"][0]; intr=data["intrinsics"][0];rgb=data["images"]
n,h,w=depth.shape
mask=rgb.min(-1)<220
for i in range(n):
 mask[i]=ndi.binary_fill_holes(ndi.binary_opening(mask[i],iterations=1))
v,u=np.mgrid[:h,:w];rays=np.stack([u,v,np.ones_like(u)],-1)
world=[];clouds=[];colors=[]
for i in range(n):
 xyz=(rays@np.linalg.inv(intr[i]).T)*depth[i,...,None]
 pts=(xyz-ext[i,:3,3])@ext[i,:3,:3]
 world.append(pts)
 valid=mask[i] & np.isfinite(depth[i])
 clouds.append(pts[valid]); colors.append(rgb[i][valid])
world=np.array(world);cloud=np.concatenate(clouds);color=np.concatenate(colors)
np.savez_compressed(root/"point_cloud.npz",xyz=cloud,rgb=color)
with (root/"point_cloud.ply").open("w") as f:
 f.write(f"ply\nformat ascii 1.0\nelement vertex {len(cloud)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
 for xyz,c in zip(cloud,color):f.write("%.6f %.6f %.6f %d %d %d\n"%(*xyz,*c))

# Measure cross-view depth agreement in projected foreground, not silhouette fit.
pairs=[]
for i in range(n):
 j=(i+1)%n
 pts=world[i][mask[i]]
 target=pts@ext[j,:3,:3].T+ext[j,:3,3]
 proj=target@intr[j].T
 xy=proj[:,:2]/np.maximum(proj[:,2:],1e-9)
 x=np.rint(xy[:,0]).astype(int);y=np.rint(xy[:,1]).astype(int)
 valid=(x>=0)&(x<w)&(y>=0)&(y<h)&(target[:,2]>0)
 ids=np.nonzero(valid)[0];ids=ids[mask[j,y[ids],x[ids]]]
 z=target[ids,2];z2=depth[j,y[ids],x[ids]]
 relative=np.abs(z-z2)/np.maximum(z2,1e-6)
 pairs.append({"from_index":i,"to_index":j,"projected_foreground_fraction":float(len(ids)/max(len(pts),1)),
               "relative_depth_median":float(np.median(relative)) if len(ids) else None,
               "depth_within_2pct_fraction":float((relative<.02).mean()) if len(ids) else None,
               "note":"Includes occlusions; descriptive self-consistency, not ground-truth accuracy."})
centers=np.array([-e[:3,:3].T@e[:3,3] for e in ext])
summary={"view_count":n,"point_count":len(cloud),"foreground_points_per_view":[len(c) for c in clouds],
         "adjacent_reprojection":pairs,"camera_centers":centers.tolist(),
         "cloud_bbox":np.ptp(cloud,axis=0).tolist(),
         "limitations":["Relative scale only.","White-background mask is heuristic.",
                        "No cleaning, deformation, component modeling or hull clipping was applied.",
                        "Low reprojection error alone does not prove shape correctness; poses and depths are jointly predicted."]}
(root/"geometry_metrics.json").write_text(json.dumps(summary,indent=2)+"\n")

show=list(range(n)) if n<=4 else [0,2,4,6,8,10,12,14]
fig,axs=plt.subplots(3,len(show),figsize=(2.2*len(show),6.5),squeeze=False)
lo,hi=np.percentile(depth[mask],[2,98])
for c,i in enumerate(show):
 axs[0,c].imshow(rgb[i]);axs[0,c].set_title(f"View {i}")
 axs[1,c].imshow(np.where(mask[i],depth[i],np.nan),cmap="viridis",vmin=lo,vmax=hi)
 axs[1,c].set_title("Relative depth")
 axs[2,c].imshow(np.where(mask[i],conf[i],np.nan),cmap="magma",vmin=1,vmax=5)
 axs[2,c].set_title("Confidence")
 for r in range(3):axs[r,c].axis("off")
fig.suptitle(f"Official {run_metadata['model'].split('/')[-1]} CPU output | one generated sheet | no hand modeling")
fig.tight_layout();fig.savefig(root/"depth_contact.png",dpi=130);plt.close(fig)

fig=plt.figure(figsize=(14,5))
stride=max(1,len(cloud)//20000);pts=cloud[::stride];col=color[::stride]/255
for k,(x,y,sy,label) in enumerate([(0,1,-1,"Front X / -Y"),(2,1,-1,"Side Z / -Y"),(0,2,1,"Top X / Z")]):
 ax=fig.add_subplot(1,3,k+1)
 ax.scatter(pts[:,x],pts[:,y]*sy,c=col,s=1)
 ax.set_title(label);ax.set_aspect("equal");ax.grid(alpha=.15)
fig.suptitle("Raw multi-view depth back-projection | colored foreground points")
fig.tight_layout();fig.savefig(root/"cloud_views.png",dpi=130);plt.close(fig)
print(json.dumps(summary,indent=2))
