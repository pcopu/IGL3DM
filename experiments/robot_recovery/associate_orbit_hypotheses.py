"""Image-only multi-view trajectory association with a declared frozen camera model.

Every fifth image is withheld from hypothesis construction and selection.
No geometry truth, original track labels or rendered target references are read.
"""
from pathlib import Path
import argparse,json,sys,hashlib,time
import numpy as np
from scipy.spatial import cKDTree
import cv2
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'marker_consistency/source'))
from grid_tracks import junctions

SETTINGS={'holdout_frame_modulus':5,'holdout_frame_remainder':4,'anchor_stride':4,'seed_min_angle_deg':30,'maximum_window_span_deg':180,'match_radius_px':2.,'nearest_margin_px':.5,'max_missing_calibration_samples':1,'min_calibration_observations':9,'min_observed_span_deg':90,'refit_rounds':2,'training_p95_max_px':1.5,'condition_max':20,'truth_used':False}

def segment(hits,anchor,partner):
 # Missing withheld frames are not calibration failures. No predicted point is emitted.
 hit=np.flatnonzero(hits);groups=[];group=[]
 for i in hit:
  if group and i-group[-1]>2:groups.append(group);group=[]
  group.append(int(i))
 if group:groups.append(group)
 return next((g for g in groups if anchor in g and partner in g),[])

def support_gate(g,win,yaw,resolvable):
 return len(g)>=9 and yaw[win[g[-1]]]-yaw[win[g[0]]]>=90 and (not resolvable or len(g)/(g[-1]-g[0]+1)>=.9)

def fit(observations,P):
 A=np.concatenate([P[i,:,:3] for i,xy in observations]);b=np.concatenate([xy-P[i,:,3] for i,xy in observations]);xyz,_,rank,s=np.linalg.lstsq(A,b,rcond=None);cond=float(s[0]/s[-1]) if s[-1]>1e-10 else float('inf');err=np.linalg.norm((A@xyz-b).reshape(-1,2),axis=1);return xyz,rank,cond,err


def choose(hypotheses,P,use_veto=False):
 unique={}
 for h in hypotheses:
  key=tuple(map(tuple,h['calibration_nodes']))
  if key not in unique or h['train_p95_px']<unique[key]['train_p95_px']:unique[key]=h
 ranked=sorted(unique.values(),key=lambda h:(-len(h['calibration_nodes']),h['train_p95_px'],tuple(map(tuple,h['calibration_nodes']))))
 nodes=[set(map(tuple,h['calibration_nodes'])) for h in ranked];lookup={}
 for i,ns in enumerate(nodes):
  for node in ns:lookup.setdefault(node,[]).append(i)
 veto={}
 if use_veto:
  for i,h in enumerate(ranked):
   alternatives=sorted({j for node in nodes[i] for j in lookup[node] if j!=i})
   for j in alternatives:
    other=ranked[j]
    if len(nodes[j])<len(nodes[i]) or other['train_p95_px']>h['train_p95_px']+.25:continue
    common=sorted({a for a,b in nodes[i]}&{a for a,b in nodes[j]})
    separation=float(np.linalg.norm(np.einsum('vij,j->vi',P[common,:,:3],np.asarray(h['xyz'])-other['xyz']),axis=1).max())
    if separation>=4:
     veto[i]={'alternative_index':j,'shared_detected_nodes':len(nodes[i]&nodes[j]),'maximum_common_projection_difference_px':separation,'candidate_observations':len(nodes[i]),'alternative_observations':len(nodes[j]),'candidate_p95':h['train_p95_px'],'alternative_p95':other['train_p95_px']};break
 used=set();selected=[];conflicts=0
 for i,h in enumerate(ranked):
  if i in veto:continue
  if used.intersection(nodes[i]):conflicts+=1;continue
  used.update(nodes[i]);selected.append(h)
 return ranked,selected,conflicts,veto

def remove_heldout_collisions(points,rows):
 # Withheld observations never change model selection. Reject every many-to-one match.
 collisions={}
 for pi,row in enumerate(rows):
  for oi,o in enumerate(row['predictions']):
   if o['matched']:collisions.setdefault((o['sample_index'],o['node_id']),[]).append((pi,oi))
 collision_count=0
 for key,items in collisions.items():
  if len(items)<2:continue
  for pi,oi in items:
   o=rows[pi]['predictions'][oi];o['matched']=False;o['rejection']='heldout_node_collision';points[pi]['observations'].pop(str(o['sample_index']),None);collision_count+=1
 return collision_count

def run(images,cameras,out,use_veto=False,resolvable=False):
 if out.exists():raise ValueError('Refusing existing output')
 out.mkdir(parents=True);source_snapshot=Path(__file__).read_bytes();started=time.time();manifest=json.loads((images/'video_manifest.json').read_text());frames=manifest['frames'];views=json.loads(cameras.read_text())['views'];P=np.asarray([v['orthographic_projection_2x4_normalized512'] for v in views]);yaw=np.array([v['yaw_deg'] for v in views]);n=len(frames)
 if len(P)!=n or [v['sample_index'] for v in views]!=list(range(n)):raise ValueError('Camera/frame order mismatch')
 graphs=[];trees=[];spacing=[]
 for i,frame in enumerate(frames):
  im=cv2.imread(str(images/frame['path']),0)
  if im is None or im.shape!=(512,512):raise ValueError('Requires exact512-square source images')
  xy,_,_=junctions(im);graphs.append(xy);trees.append(cKDTree(xy));spacing.append(trees[-1].query(xy,k=2)[0][:,1])
  if i%16==0:print('detect',i,len(xy),flush=True)
 cal=np.array([i for i in range(n) if i%5!=4]);held=[i for i in range(n) if i%5==4];seeds=0;hypotheses=[];rejections={}
 def reject(k):rejections[k]=rejections.get(k,0)+1
 def matches(xyz,win):
  ids=[];dist=[];valid=[]
  for frame in win:
   pred=P[frame,:,:3]@xyz+P[frame,:,3];d,k=trees[frame].query(pred,k=2);ids.append(int(k[0]));dist.append(float(d[0]));valid.append(d[0]<=2 and d[1]-d[0]>=.5 and (not resolvable or (d[1]>2 and spacing[frame][int(k[0])]>=6)))
  return np.array(ids),np.array(dist),np.array(valid)
 for anchor in range(0,n,4):
  if anchor%5==4:continue
  later=cal[yaw[cal]>=yaw[anchor]+30]
  if not len(later):continue
  partner=int(later[0]);win=cal[(yaw[cal]>=yaw[anchor]-90)&(yaw[cal]<=yaw[anchor]+90)]
  ai=np.flatnonzero(win==anchor);bi=np.flatnonzero(win==partner)
  if not len(ai) or not len(bi):continue
  ai,bi=int(ai[0]),int(bi[0]);A=np.concatenate([P[anchor,:,:3],P[partner,:,:3]]);pinv=np.linalg.pinv(A)
  # Check every detected pair, not just an LK-selected periodic phase.
  for a,x in enumerate(graphs[anchor]):
   target=np.concatenate([np.broadcast_to(x-P[anchor,:,3],(len(graphs[partner]),2)),graphs[partner]-P[partner,:,3]],axis=1);xyzs=target@pinv.T;res=np.linalg.norm((xyzs@A.T-target).reshape(-1,2,2),axis=2).max(1)
   for b in np.flatnonzero(res<=1.):
    seeds+=1;xyz=xyzs[b];ids,dist,ok=matches(xyz,win);g=segment(ok,ai,bi)
    if not g or ids[ai]!=a or ids[bi]!=b:reject('seed_not_retained');continue
    if not support_gate(g,win,yaw,resolvable):reject('insufficient_broad_support');continue
    for _ in range(2):
     observations=[(int(win[k]),graphs[win[k]][ids[k]]) for k in g];xyz,rank,cond,err=fit(observations,P);ids,dist,ok=matches(xyz,win);g=segment(ok,ai,bi)
     if not g:break
    if not support_gate(g,win,yaw,resolvable):reject('refit_lost_support');continue
    observations=[(int(win[k]),graphs[win[k]][ids[k]]) for k in g];xyz,rank,cond,err=fit(observations,P)
    if rank<3 or cond>20 or np.percentile(err,95)>1.5:reject('training_gate');continue
    pairs=tuple((int(win[k]),int(ids[k])) for k in g)
    hypotheses.append({'xyz':xyz.tolist(),'calibration_nodes':pairs,'condition':cond,'train_p95_px':float(np.percentile(err,95)),'train_median_px':float(np.median(err)),'anchor':anchor,'partner':partner,'seed_nodes':[int(a),int(b)]})
  print('anchor',anchor,'seeds',seeds,'hypotheses',len(hypotheses),flush=True)
 ranked,selected,conflicts,veto=choose(hypotheses,P,use_veto)
 points=[];tracks={};holdout_rows=[]
 for k,h in enumerate(selected):
  tid=f'orbit{k:06d}';xyz=np.asarray(h['xyz']);obs={str(i):graphs[i][j].tolist() for i,j in h['calibration_nodes']};lo=min(map(int,obs));hi=max(map(int,obs));tests=[]
  for i in held:
   if not lo<=i<=hi:continue
   pred=P[i,:,:3]@xyz+P[i,:,3];d,j=trees[i].query(pred,k=2);matched=bool(d[0]<=2 and d[1]-d[0]>=.5 and (not resolvable or (d[1]>2 and spacing[i][int(j[0])]>=6)));tests.append({'sample_index':i,'predicted_xy':pred.tolist(),'nearest_distance_px':float(d[0]),'nearest_separation_px':float(d[1]-d[0]),'matched':matched,'node_id':int(j[0]) if matched else None})
   if matched:obs[str(i)]=graphs[i][int(j[0])].tolist()
  obs=dict(sorted(obs.items(),key=lambda kv:int(kv[0])));point={'track_id':tid,'xyz':h['xyz'],'condition':h['condition'],'observations':obs,'sample_span':[lo,hi],'fitted_angular_span_deg':float(yaw[hi]-yaw[lo]),'conditional_pass':True,'identity_state':'unverified multi-view image association','calibration_node_ids':[[i,j] for i,j in h['calibration_nodes']],'training_reprojection_px':{'n':len(h['calibration_nodes']),'p95':h['train_p95_px'],'median':h['train_median_px']},'holdout_not_used_for_selection':True}
  points.append(point);tracks[tid]={'observations':[{'sample_index':int(i),'xy':xy,'timestamp_seconds':frames[int(i)]['timestamp_seconds']} for i,xy in obs.items()]};holdout_rows.append({'track_id':tid,'predictions':tests})
 collision_count=remove_heldout_collisions(points,holdout_rows)
 for point in points:
  tracks[point['track_id']]['observations']=[{'sample_index':int(i),'xy':xy,'timestamp_seconds':frames[int(i)]['timestamp_seconds']} for i,xy in point['observations'].items()]
 distances=[o['nearest_distance_px'] for row in holdout_rows for o in row['predictions']];report={'settings':{**SETTINGS,'competing_hypothesis_veto':use_veto,'resolvability_gate':resolvable,'minimum_detected_node_spacing_px':6 if resolvable else None,'minimum_calibration_density':.9 if resolvable else None,'heldout_collision_policy':'reject all'},'source_sha256':hashlib.sha256(source_snapshot).hexdigest(),'camera_sha256':hashlib.sha256(cameras.read_bytes()).hexdigest(),'frame_count':n,'calibration_frames':cal.tolist(),'heldout_frames':held,'seeds_tested':seeds,'hypotheses_before_deduplication':len(hypotheses),'unique_hypotheses':len(ranked),'ambiguous_hypotheses_rejected':len(veto),'heldout_colliding_associations_rejected':collision_count,'selected_tracks':len(points),'calibration_conflicting_hypotheses_rejected':conflicts,'rejection_counts':rejections,'heldout_predictions':len(distances),'heldout_matched_predictions':sum(o['matched'] for row in holdout_rows for o in row['predictions']),'heldout_nearest_error_px':{'median':float(np.median(distances)) if distances else None,'p95':float(np.percentile(distances,95)) if distances else None,'max':max(distances) if distances else None},'seconds':time.time()-started,'limitations':['Camera model is supplied, not recovered or validated here.','Nearest heldout node error is not physical identity error.','Selection is greedy set packing, not a proven global optimum.','Periodic and reflective ambiguities may produce coherent wrong trajectories.','Missing/occluded coordinates are never synthesized.']}
 (out/'source_snapshot.py').write_bytes(source_snapshot);(out/'hypothesis_veto.json').write_text(json.dumps(veto,indent=2));(out/'input_frame_hashes.json').write_text(json.dumps([{'sample_index':i,'sha256':hashlib.sha256((images/f['path']).read_bytes()).hexdigest()} for i,f in enumerate(frames)],indent=2))
 (out/'candidate_points.json').write_text(json.dumps(points,indent=2));(out/'tracks.json').write_text(json.dumps(tracks,indent=2));(out/'hypotheses.json').write_text(json.dumps(ranked,indent=2));(out/'heldout_predictions.json').write_text(json.dumps(holdout_rows,indent=2));(out/'metrics.json').write_text(json.dumps(report,indent=2));(out/'frame_nodes.json').write_text(json.dumps([{'sample_index':i,'xy':xy.tolist()} for i,xy in enumerate(graphs)]));print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['images','cameras','output']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--ambiguity-veto',action='store_true');p.add_argument('--resolvable-only',action='store_true');a=p.parse_args();run(a.images,a.cameras,a.output,a.ambiguity_veto,a.resolvable_only)
