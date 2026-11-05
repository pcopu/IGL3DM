"""Known analytic 3D control; no learned model and no lion geometry."""
from pathlib import Path
import json,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
from geometry import project,analyze_tracks,gate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'controls';OUT.mkdir(exist_ok=True)
S=512;scale=170.;center=(256.,256.);radii=np.array([.95,.68,1.10])
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def surf(phi,lat):return radii*np.array([np.sin(phi)*np.cos(lat),-np.cos(phi)*np.cos(lat),np.sin(lat)])

def visible(p,yaw):
    c=np.array([np.sin(np.deg2rad(yaw)),-np.cos(np.deg2rad(yaw)),0.])
    return np.dot(p/radii**2,c)>0.015

patches={};truth={};tracks={};imgs=[]
for k,phi in enumerate(np.deg2rad(np.arange(16)*22.5)):
 for j,lat in enumerate(np.deg2rad([-42,-14,14,42])):
  mid=k*4+j+1; dphi=np.deg2rad(7);dlat=np.deg2rad(7)
  corners=np.array([surf(phi-dphi,lat+dlat),surf(phi+dphi,lat+dlat),surf(phi+dphi,lat-dlat),surf(phi-dphi,lat-dlat)])
  patches[mid]=corners
  for c,p in enumerate(corners):truth[f'{mid:02}:{c}']=p;tracks[f'{mid:02}:{c}']={}
for v in range(8):
 yaw=v*45;im=Image.new('RGB',(S,S),'#f7f7f7');d=ImageDraw.Draw(im)
 # Draw the analytic ellipsoid's orthographic silhouette.
 a=np.deg2rad(yaw);horizontal=np.sqrt((radii[0]*np.cos(a))**2+(radii[1]*np.sin(a))**2)*scale
 d.ellipse((256-horizontal,256-radii[2]*scale,256+horizontal,256+radii[2]*scale),fill='#d5d8dc',outline='#59636e',width=2)
 for mid,pts in patches.items():
  if not all(visible(p,yaw) for p in pts):continue
  uv=project(pts,yaw,scale,center)
  color=('#f8a5a5','#9ce2ee','#b5dd81','#c6b1f5','#f6d27b','#f2a4dd')[mid%6]
  d.polygon([tuple(p) for p in uv],fill=color,outline='#30404c',width=2)
  cc=uv.mean(0);font=ImageFont.truetype(FONT,12);d.text(tuple(cc),str(mid),fill='black',font=font,anchor='mm')
  # Corner 0 triangle is physically anchored to the same corner.
  t=uv[0]*.72+cc*.28;d.ellipse((t[0]-2,t[1]-2,t[0]+2,t[1]+2),fill='black')
  for c,p in enumerate(uv):tracks[f'{mid:02}:{c}'][v]=p.tolist()
 d.text((16,14),f'Known ellipsoid | view {v} | yaw {yaw}°',font=ImageFont.truetype(FONT,17),fill='black')
 im.save(OUT/f'view_{v}.png');imgs.append(im)
contact=Image.new('RGB',(S*4,S*2),'white')
for v,im in enumerate(imgs):contact.paste(im,((v%4)*S,(v//4)*S))
contact.save(OUT/'known_ellipsoid.png')
rng=np.random.default_rng(741)
noisy={k:{v:(np.asarray(p)+rng.normal(0,.4,2)).tolist() for v,p in obs.items()} for k,obs in tracks.items()}
# Inject a repeated-ID swap in held-out views and a vertical surface warp.
swapped=json.loads(json.dumps(noisy));warped=json.loads(json.dumps(noisy))
changed=0
for v in [1,5]:
 eligible=sorted(k for k,o in swapped.items() if str(v) in o)
 for i in range(0,len(eligible)-1,8):
  k,l=eligible[i],eligible[min(i+4,len(eligible)-1)]
  swapped[k][str(v)],swapped[l][str(v)]=swapped[l][str(v)],swapped[k][str(v)];changed+=2
 for k,obs in warped.items():
  if str(v) in obs:obs[str(v)][1]+=12.*np.sin(int(k.split(':')[0])*.7)
horizontal=json.loads(json.dumps(noisy))
for v in [1,5]:
 # Swap complete patches at the same latitude: y/epipolar remains good.
 mids=sorted(int(k.split(':')[0]) for k,o in horizontal.items() if k.endswith(':0') and str(v) in o)
 for latidx in range(4):
  row=[m for m in mids if (m-1)%4==latidx]
  if len(row)<2:continue
  a,b=row[0],row[-1]
  for c in range(4):
   ka,kb=f'{a:02}:{c}',f'{b:02}:{c}'
   horizontal[ka][str(v)],horizontal[kb][str(v)]=horizontal[kb][str(v)],horizontal[ka][str(v)]
# Swap IDs globally between two latitude rows. All image geometry remains
# self-consistent, but physical identity is wrong and truth error is large.
permuted={}
for tid,obs in noisy.items():
 mid,c=map(int,tid.split(':'));offset=(mid-1)%4
 other=mid+1 if offset==0 else mid-1 if offset==1 else mid
 permuted[tid]=noisy[f'{other:02}:{c}']
allresults={}
for name,data in [('exact',tracks),('noise_0p4px',noisy),('swapped_heldout',swapped),('warped_heldout',warped),('horizontal_swap_heldout',horizontal),('consistent_wrong_identity',permuted)]:
 res=analyze_tracks(data,scale,center,ground_truth=truth)
 res['gate']=gate(res,name!='consistent_wrong_identity',True,True)
 allresults[name]=res
# Camera mismatch from genuine rigid points at off-grid actual camera angles.
mismatch={k:{v:project(truth[k],v*45+(10 if v in [1,5] else 0),scale,center).tolist() for v in obs} for k,obs in tracks.items()}
r=analyze_tracks(mismatch,scale,center,ground_truth=truth);r['gate']=gate(r,True,True,True);allresults['wrong_requested_camera']=r
(OUT/'metrics.json').write_text(json.dumps(allresults,indent=2));(OUT/'observations.json').write_text(json.dumps(tracks,indent=2))
(OUT/'ground_truth.json').write_text(json.dumps({k:v.tolist() for k,v in truth.items()},indent=2))
report={n:{k:v for k,v in x.items() if k not in ['tracks','pairwise']} for n,x in allresults.items()}
(OUT/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
