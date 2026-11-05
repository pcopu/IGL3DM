"""Probe generated wireframe correspondences, not recover guaranteed mesh IDs.

Uses mutual SIFT matches, assumed level-orthographic epipolar consistency,
volume bounds and three-view cycles. None is a ground-truth match label.
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--run",type=Path,action="append",required=True)
p.add_argument("--output",type=Path,required=True)
p.add_argument("--size",type=int,default=256)
a=p.parse_args()
if a.output.exists() and any(a.output.iterdir()):p.error("Output not empty")
a.output.mkdir(parents=True,exist_ok=True)
summary=[]
for run in a.run:
    images=[];keypoints=[];descriptors=[]
    sift=cv2.SIFT_create(nfeatures=2000,contrastThreshold=.025,edgeThreshold=15)
    for i in range(16):
        im=cv2.imread(str(run/"views"/f"view_{i:02d}.png"))
        im=cv2.resize(im,(a.size,a.size),interpolation=cv2.INTER_AREA)
        mask=cv2.imread(str(run/"masks"/f"mask_{i:02d}.png"),cv2.IMREAD_GRAYSCALE)
        mask=cv2.resize(mask,(a.size,a.size),interpolation=cv2.INTER_NEAREST)
        kp,desc=sift.detectAndCompute(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY),mask)
        images.append(im);keypoints.append(kp);descriptors.append(desc)
    matcher=cv2.BFMatcher(cv2.NORM_L2)
    def mutual(i,j):
        if descriptors[i] is None or descriptors[j] is None:return []
        forward=matcher.knnMatch(descriptors[i],descriptors[j],k=2)
        backward=matcher.knnMatch(descriptors[j],descriptors[i],k=2)
        f=[m[0] for m in forward if len(m)==2 and m[0].distance < .7*m[1].distance]
        b={(m[0].queryIdx,m[0].trainIdx) for m in backward if len(m)==2 and m[0].distance < .7*m[1].distance}
        return [m for m in f if (m.trainIdx,m.queryIdx) in b]
    def triangulate(i,j,pi,pj):
        angles=np.deg2rad([i*22.5,j*22.5]);matrix=np.column_stack([np.cos(angles),np.sin(angles)])
        xy=np.linalg.solve(matrix,(np.array([pi[0],pj[0]])+.5)/a.size*2-1)
        z=1-(pi[1]+pj[1]+1)/a.size
        return np.r_[xy,z]
    pairs=[];maps=[];all_matches=[]
    for i in range(16):
        j=(i+1)%16;matches=mutual(i,j);good=[];errors=[]
        for m in matches:
            pi=keypoints[i][m.queryIdx].pt;pj=keypoints[j][m.trainIdx].pt
            error=abs(pi[1]-pj[1])/a.size
            xyz=triangulate(i,j,pi,pj)
            errors.append(error)
            if error <= .02 and np.all(np.abs(xyz)<=1.05):good.append(m)
        pairs.append({"from":i,"to":j,"mutual_ratio_matches":len(matches),"geometry_gate_matches":len(good),
                      "gate_fraction":len(good)/len(matches) if matches else 0,
                      "median_vertical_error_fraction":float(np.median(errors)) if errors else None})
        maps.append({m.queryIdx:m.trainIdx for m in good});all_matches.append((matches,good))
    cycles=[]
    for i in range(16):
        j=(i+1)%16;k=(i+2)%16;direct={m.queryIdx:m.trainIdx for m in mutual(i,k)};count=0;consistent=0
        for start,middle in maps[i].items():
            end=maps[j].get(middle)
            if end is None or direct.get(start)!=end:continue
            count+=1
            ab=triangulate(i,j,keypoints[i][start].pt,keypoints[j][middle].pt)
            bc=triangulate(j,k,keypoints[j][middle].pt,keypoints[k][end].pt)
            consistent += int(np.linalg.norm(ab-bc)<=.1)
        cycles.append({"views":[i,j,k],"exact_feature_cycles":count,"triangulation_agreement_cycles":consistent})
    result={"run":run.name,"opencv":cv2.__version__,"settings":{"size":a.size,"ratio":.7,"vertical_gate_fraction":.02,"volume_bound":1.05,"cycle_distance_gate":.1},
            "keypoint_count_per_view":[len(k) for k in keypoints],"pairs":pairs,"cycles":cycles,
            "totals":{"mutual_matches":sum(r["mutual_ratio_matches"] for r in pairs),"geometry_gate_matches":sum(r["geometry_gate_matches"] for r in pairs),
                      "exact_three_view_cycles":sum(r["exact_feature_cycles"] for r in cycles),"triangulation_agreement_cycles":sum(r["triangulation_agreement_cycles"] for r in cycles)},
            "limitations":["Feature indices are not original 3D mesh vertex IDs.","Assumed cameras, epipolar and cycle gates can accept false matches, especially repeated mesh patterns.","Different generated atlases also change silhouettes, pose details and appearance; this is not isolated causal attribution."]}
    (a.output/f"{run.name}.json").write_text(json.dumps(result,indent=2)+"\n")
    panels=[]
    for i in [0,3,7,15]:
        j=(i+1)%16;_,good=all_matches[i]
        im=cv2.drawMatches(images[i],keypoints[i],images[j],keypoints[j],good[:30],None,matchColor=(60,180,40),flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        card=Image.new("RGB",(2*a.size,a.size+24),'white');card.paste(Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB)),(0,24))
        ImageDraw.Draw(card).text((4,4),f"{run.name} {i:02d}->{j:02d}: {len(good)} gate-passing SIFT matches; NOT vertex IDs",fill='black')
        panels.append(card)
    sheet=Image.new('RGB',(2*a.size,4*(a.size+24)),'white')
    for i,card in enumerate(panels):sheet.paste(card,(0,i*(a.size+24)))
    sheet.save(a.output/f"{run.name}.png");summary.append(result)
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps([{r['run']:r['totals']} for r in summary],indent=2))
