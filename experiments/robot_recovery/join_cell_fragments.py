"""Join only short disjoint fragments supported by matching observed three-corner cells.

No truth geometry or identities are imported. Original points/cells remain intact.
"""
from pathlib import Path
from collections import defaultdict
import argparse,json,copy,hashlib
import numpy as np
from assemble_observed_cells import canonical

def propose(points,faces,projections,max_gap=5,max_projection=3.):
 candidates=defaultdict(list)
 for i,f in enumerate(faces):
  aa=f['point_indices'];sa=set(aa)
  for j in range(i):
   bb=faces[j]['point_indices'];sb=set(bb)
   if len(sa&sb)!=3:continue
   a=next(iter(sa-sb));b=next(iter(sb-sa))
   if canonical([b if k==a else k for k in aa])!=canonical(bb):continue
   candidates[tuple(sorted((a,b)))].append([j,i])
 rows=[];eligible=[]
 for (a,b),support in sorted(candidates.items()):
  aa=points[a];bb=points[b];ta=sorted(map(int,aa['observations']));tb=sorted(map(int,bb['observations']));gap=max(min(tb)-max(ta),min(ta)-max(tb));overlap=bool(set(ta)&set(tb));delta=np.asarray(aa['xyz'])-bb['xyz'];distance=np.linalg.norm(np.einsum('vij,j->vi',projections[:,:,:3],delta),axis=1);peak=float(distance.max());reason='overlapping_observations' if overlap else 'gap_outside_seed_cadence' if gap<1 or gap>max_gap else 'projection_disagreement' if peak>max_projection else 'eligible'
  rows.append({'point_pair':[a,b],'support_face_pairs':support,'gap_samples':gap,'maximum_projection_difference_px':peak,'reason':reason})
  if reason=='eligible':eligible.append((a,b))
 degree=defaultdict(int)
 for a,b in eligible:degree[a]+=1;degree[b]+=1
 accepted=[]
 for row in rows:
  a,b=row['point_pair']
  if row['reason']=='eligible':
   if degree[a]>1 or degree[b]>1:row['reason']='ambiguous_candidate_component'
   else:accepted.append((a,b))
 return rows,accepted

def refit(a,b,projections,heldout,yaws):
 obs={**a['observations'],**b['observations']};obs={str(k):obs[str(k)] for k in sorted(map(int,obs))};train=[(int(k),p) for k,p in obs.items() if int(k) not in heldout];test=[(int(k),p) for k,p in obs.items() if int(k) in heldout]
 if len(train)<6 or not test:return None
 A=np.concatenate([projections[i,:,:3] for i,p in train]);target=np.concatenate([np.asarray(p)-projections[i,:,3] for i,p in train]);w=np.ones(len(A))
 for _ in range(5):
  xyz,_,rank,s=np.linalg.lstsq(A*np.sqrt(w[:,None]),target*np.sqrt(w),rcond=None);errors=np.linalg.norm((A@xyz-target).reshape(-1,2),axis=1);w=np.repeat(np.minimum(1.,3/np.maximum(errors,1e-6)),2)
 condition=float(s[0]/s[-1]) if s[-1]>1e-10 else float('inf');trainerrors=np.linalg.norm((A@xyz-target).reshape(-1,2),axis=1);testerrors=[np.linalg.norm(projections[i,:,:3]@xyz+projections[i,:,3]-p) for i,p in test]
 if rank<3 or condition>20 or np.percentile(trainerrors,95)>3 or np.percentile(testerrors,95)>3:return None
 def summary(es):return {'n':len(es),'median':float(np.median(es)),'p95':float(np.percentile(es,95)),'max':float(max(es))}
 frames=list(map(int,obs));return {'track_id':f"join({a['track_id']},{b['track_id']})",'source_track_ids':[a['track_id'],b['track_id']],'xyz':xyz.tolist(),'condition':condition,'sample_span':[min(frames),max(frames)],'fitted_angular_span_deg':float(yaws[max(frames)]-yaws[min(frames)]),'observations':obs,'training_reprojection_px':summary(trainerrors),'heldout_reprojection_px':summary(testerrors),'conditional_pass':True,'identity_state':'unverified three-shared-corner temporal fragment join'}

def join(points_path,faces_path,cameras,out,holdout_centers,holdout_radius):
 if out.exists():raise ValueError('Refusing existing output')
 points=json.loads(points_path.read_text());faces=json.loads(faces_path.read_text());cam=json.loads(cameras.read_text());views=cam['views']
 if [v['sample_index'] for v in views]!=list(range(len(views))):raise ValueError('Cameras not in sample order')
 P=np.array([v['orthographic_projection_2x4_normalized512'] for v in views]);yaw=np.array([v['yaw_deg'] for v in views]);held={i for c in holdout_centers for i in range(c-holdout_radius,c+holdout_radius+1)};rows,pairs=propose(points,faces,P);replacements={};merged=[]
 for a,b in pairs:
  record=refit(points[a],points[b],P,held,yaw)
  row=next(r for r in rows if r['point_pair']==[a,b])
  if record is None:row['reason']='merged_geometry_gate_failed';continue
  record['source_point_indices']=[a,b];replacements[a]=record;replacements[b]=None;merged.append([a,b]);row['reason']='joined_conditional'
 result=[];mapping={}
 for i,p in enumerate(points):
  if i in replacements:
   if replacements[i] is None:continue
   new=replacements[i];index=len(result);result.append(new)
   for k in new['source_point_indices']:mapping[k]=index
  else:mapping[i]=len(result);result.append(copy.deepcopy(p))
 out.mkdir(parents=True);(out/'candidate_points.json').write_text(json.dumps(result,indent=2));report={'input_points':len(points),'output_points':len(result),'joined_pairs':merged,'candidate_rows':rows,'source_to_output_indices':mapping,'settings':{'three_shared_corners':True,'cyclic_order_required':True,'maximum_gap_samples':5,'maximum_projection_difference_px':3,'overlapping_observations_allowed':False,'ambiguous_components':'reject all','geometry_gate':'unchanged robust five iterations, train and block holdout p95 <=3px, condition<=20','holdout_centers':holdout_centers,'holdout_radius':holdout_radius},'truth_used':False,'input_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in [('points',points_path),('faces',faces_path),('cameras',cameras)]},'limitations':['Joined identities are hypotheses supported by images and cameras, not physical proof.','Does not correct coherent periodic phase swaps.','Refits only union of observed coordinates; no synthetic observations or completion.']};(out/'join_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['candidate_rows','source_to_output_indices']},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['points','faces','cameras','output']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--holdout-centers',type=int,nargs='+',required=True);p.add_argument('--holdout-radius',type=int,required=True);a=p.parse_args();join(a.points,a.faces,a.cameras,a.output,a.holdout_centers,a.holdout_radius)
