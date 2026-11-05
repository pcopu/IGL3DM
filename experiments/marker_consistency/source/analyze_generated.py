from pathlib import Path
import json,sys,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
from geometry import analyze_tracks,gate,summary
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
# Manual pixel annotation of visible contour junctions, not manually modeled 3D.
# Order: local left-top, right-top, right-bottom, left-bottom. Orientation
# is only a candidate within this one side's views 1,2,3; never across sides.
# Coordinates estimated to ~3 native pixels from enlarged source crops.
candidates={
 '06':{1:[[274,160],[309,170],[304,241],[263,253]],2:[[232,159],[307,161],[288,237],[207,251]],3:[[200,159],[278,155],[238,237],[166,252]]},
 '09':{1:[[192,320],[235,320],[235,381],[192,381]],2:[[126,319],[172,319],[164,387],[122,377]],3:[[109,318],[149,319],[142,388],[105,377]]},
 '11':{1:[[313,312],[346,307],[354,384],[316,381]],2:[[301,313],[339,304],[354,387],[315,379]],3:[[252,313],[284,305],[300,390],[258,380]]},
}
# Readable IDs are conservatively transcribed. Occluded/unreadable codes omitted.
ids={0:[1,2,3,4,8,9,12,16,17],1:[1,2,3,5,6,7,8,9,10,11,12,16,17,18,19,23,24],
2:[1,2,3,4,5,6,7,8,9,10,11,18,19,23,24],3:[1,4,5,6,7,8,9,10,11,23,24],
4:[10,11,18,19,20,21,22,23,24],5:[8,9,10,11,19,20,21,22,23,24],
6:[1,5,6,7,11,12,16,17,18,18,19,23,24],7:[1,2,3,5,6,7,8,9,11,12,16,17,18,18,19,23,24]}
tracks={}
for mid,views in candidates.items():
 for c in range(4):tracks[f'{mid}:{c}']={v:(np.asarray(pts[c])*512/443.5).tolist() for v,pts in views.items()}
res=analyze_tracks(tracks,scale=150.,center=(256.,256.),heldout=(1,5))
res['gate']=gate(res,False,False,False)
res['scope']='Exploratory 12 manually annotated candidate corner tracks from 3 labels in views 1,2,3. Not globally authenticated correspondences. View 1 held out; view 5 has no eligible track.'
res['coordinate_uncertainty']='Estimated +/-3 native pixels (~3.5 normalized pixels), not independently measured; corners on curved borders can be ambiguous.'
res['conditioning_caveat']='Fixed requested 45-degree cameras, equal scale, common grid center. Actual cameras are not calibrated; high error does not identify whether cameras, framing, or surface geometry caused it.'
# Sensitivity: independent bounded annotation perturbation (not fitted to errors).
rng=np.random.default_rng(742);sens=[]
for k in range(300):
 perturbed={tid:{v:(np.asarray(p)+rng.uniform(-3.5,3.5,2)).tolist() for v,p in obs.items()} for tid,obs in tracks.items()}
 rr=analyze_tracks(perturbed,150.,(256.,256.),(1,5))
 sens.append(rr['heldout_reprojection_px']['median'])
res['annotation_perturbation_heldout_median_px']={'trials':300,'native_bound_px':3.0,'min':float(min(sens)),'max':float(max(sens)),'median':float(np.median(sens))}
res['adjacent_pair_epipolar_px']=summary([p['epipolar_px'] for p in res['pairwise'] if p['yaw_gap']==45])
res['wide_90deg_pair_epipolar_px']=summary([p['epipolar_px'] for p in res['pairwise'] if p['yaw_gap']>=90])
res['source_sha256']=hashlib.sha256((ROOT/'generated/input.png').read_bytes()).hexdigest()
res['inventory']={'readable_label_instances':sum(map(len,ids.values())),'unique_requested_labels_seen':len(set(sum(ids.values(),[]))),
 'missing_requested_ids':[i for i in range(1,25) if i not in sum(ids.values(),[])],'per_view_ids':ids,
 'duplicate_id_instances':[{'view':v,'id':i,'count':L.count(i)} for v,L in ids.items() for i in sorted(set(L)) if L.count(i)>1],
 'confirmed_global_corner_tracks':0,'candidate_local_corner_tracks':12,'candidate_local_label_tracks':3,
 'views_with_candidate_tracks':[1,2,3],'heldout_views_with_evaluable_tracks':[1],
 'full_orbit_loop_closure':'Not evaluable: globally stable unique patch identity is contradicted; no admissible full-orbit graph.'}
(OUT/'generated_metrics.json').write_text(json.dumps(res,indent=2))
(OUT/'candidate_corners.json').write_text(json.dumps(candidates,indent=2));(OUT/'candidate_tracks_512px.json').write_text(json.dumps(tracks,indent=2))
# Annotated fit/heldout diagnostic, retaining actual source pixels.
font=ImageFont.truetype(FONT,19);small=ImageFont.truetype(FONT,15)
canvas=Image.new('RGB',(1536,614),'white');dc=ImageDraw.Draw(canvas)
colors=['#007acc','#d32f2f','#008844']
for col,v in enumerate([2,3,1]):
 im=Image.open(ROOT/f'generated/view_{v}.png').resize((512,512))
 d=ImageDraw.Draw(im)
 for j,(mid,views) in enumerate(candidates.items()):
  pts=np.asarray(views[v])*512/443.5;d.line([tuple(p) for p in pts]+[tuple(pts[0])],fill=colors[j],width=3)
  for c,p in enumerate(pts):d.ellipse((p[0]-4,p[1]-4,p[0]+4,p[1]+4),fill=colors[j]);d.text((p[0]+4,p[1]+3),f'{mid}.{c}',font=small,fill=colors[j],stroke_width=1,stroke_fill='white')
  if v==1:
   for c,p in enumerate(pts):
    detail=next(x for x in res['tracks'] if x['track']==f'{mid}:{c}')
    from geometry import project
    pred=project(detail['fit_xyz'],45,150,(256,256))
    d.line((tuple(p),tuple(pred)),fill=colors[j],width=2);x,y=pred;d.line((x-5,y-5,x+5,y+5),fill='black',width=2);d.line((x-5,y+5,x+5,y-5),fill='black',width=2)
 canvas.paste(im,(col*512,60));dc.text((col*512+15,15),f'View {v}: '+('HELD OUT; crosses = predictions' if v==1 else 'training'),font=font,fill='black')
dc.text((15,580),'Candidate corners only. Fixed requested cameras. Disagreement can include camera/framing error; identities fail independently.',font=small,fill='black')
canvas.save(OUT/'heldout_corner_diagnostic.png')
print(json.dumps({k:v for k,v in res.items() if k not in ['tracks','pairwise','inventory']},indent=2));print(res['inventory'])
