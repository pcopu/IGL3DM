"""Calibration-image neighbor support for conservative orbit-track endpoint trimming.

No truth, silhouettes or synthesized coordinates. Frozen XYZ is the primary variant.
"""
from pathlib import Path
import argparse,json,copy,hashlib,collections,sys
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image
from associate_orbit_hypotheses import fit
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'marker_consistency/source'))
from quad_cells import detect_cells

SETTINGS={'minimum_edge_observations':3,'minimum_edge_span_deg':30,'minimum_simultaneous_stable_neighbors':2,'minimum_calibration_observations':9,'minimum_retained_span_deg':90,'minimum_calibration_density':.9,'maximum_corner_mapping_px':4,'mapping_nearest_margin_px':1,'heldout_modulus':5,'heldout_remainder':4}

def supported_intervals(points,frame_edges,yaw):
 edge_frames={}
 for i,edges in frame_edges.items():
  if i%5==4:raise ValueError('Heldout edges must never enter selection')
  for a,b in set(map(tuple,edges)):edge_frames.setdefault(tuple(sorted((a,b))),[]).append(i)
 stable={edge:sorted(set(frames)) for edge,frames in edge_frames.items() if len(set(frames))>=3 and max(yaw[i] for i in frames)-min(yaw[i] for i in frames)>=30}
 support=[{} for p in points]
 for i,edges in frame_edges.items():
  for a,b in set(map(tuple,edges)):
   if tuple(sorted((a,b))) in stable:
    support[a].setdefault(i,set()).add(b);support[b].setdefault(i,set()).add(a)
 decisions=[]
 for pi,p in enumerate(points):
  eligible=sorted(i for i,nn in support[pi].items() if len(nn)>=2)
  pairs=[(int(i),int(j)) for i,j in p['calibration_node_ids']]
  if not eligible:decisions.append({'point_index':pi,'track_id':p['track_id'],'retained':False,'reason':'no_supported_endpoint_pair','support':{str(i):sorted(s) for i,s in support[pi].items()}});continue
  lo,hi=eligible[0],eligible[-1];pairs=[(i,j) for i,j in pairs if lo<=i<=hi];cal=[i for i in range(lo,hi+1) if i%5!=4];density=len(pairs)/len(cal);span=float(yaw[hi]-yaw[lo]);ok=len(pairs)>=9 and span>=90 and density>=.9
  decisions.append({'point_index':pi,'track_id':p['track_id'],'retained':ok,'reason':'retained' if ok else 'insufficient_remaining_support','interval':[lo,hi],'calibration_node_ids':pairs,'calibration_density':density,'angular_span_deg':span,'support':{str(i):sorted(s) for i,s in support[pi].items()}})
 return stable,decisions

def apply_intervals(points,decisions,P,yaw,refit=False):
 output=[]
 for d in decisions:
  if not d['retained']:continue
  p=copy.deepcopy(points[d['point_index']]);lo,hi=d['interval'];oldobs=p['observations'];p['observations']={i:xy for i,xy in oldobs.items() if lo<=int(i)<=hi};p['calibration_node_ids']=d['calibration_node_ids'];obs=[(i,np.asarray(p['observations'][str(i)])) for i,j in d['calibration_node_ids']]
  xyz,rank,cond,err=fit(obs,P)
  if refit and (rank<3 or cond>20 or np.percentile(err,95)>1.5):d['retained']=False;d['reason']='refit_failed_original_gate';continue
  p['parent_fit_metrics']={'training_reprojection_px':copy.deepcopy(p['training_reprojection_px']),'condition':p['condition'],'calibration_node_ids':copy.deepcopy(points[d['point_index']]['calibration_node_ids'])};p['parent_point_index']=d['point_index'];p['parent_xyz']=p['xyz'];p['neighborhood_interval']=d['interval'];p['sample_span']=d['interval'];p['fitted_angular_span_deg']=float(yaw[hi]-yaw[lo]);p['endpoint_trimmed_observations']=len(oldobs)-len(p['observations']);p['geometry_refitted']=refit
  if refit:p['xyz']=xyz.tolist();p['condition']=cond;p['training_reprojection_px']={'n':len(obs),'p95':float(np.percentile(err,95)),'median':float(np.median(err))}
  actual_err=np.array([np.linalg.norm(P[i,:,:3]@np.asarray(p['xyz'])+P[i,:,3]-xy) for i,xy in obs]);p['condition']=cond;p['training_reprojection_px']={'n':len(obs),'p95':float(np.percentile(actual_err,95)),'median':float(np.median(actual_err))};p['training_reprojection_scope']='Retained calibration observations; primary residual is reported, not a new acceptance gate'
  p['identity_state']='Unverified; calibration-image neighbor endpoint support only';output.append(p)
 return output

def run(images,cameras,source,out,refit=False):
 if out.exists():raise ValueError('Refusing existing output')
 manifest=json.loads((images/'video_manifest.json').read_text());frames=manifest['frames'];points=json.loads((source/'candidate_points.json').read_text());views=json.loads(cameras.read_text())['views'];P=np.asarray([v['orthographic_projection_2x4_normalized512'] for v in views]);yaw=[v['yaw_deg'] for v in views]
 if len(views)!=len(frames) or [v['sample_index'] for v in views]!=list(range(len(frames))):raise ValueError('Camera/frame order mismatch')
 for p in points:
  seen=set()
  for i,j in p['calibration_node_ids']:
   if i%5==4 or not 0<=i<len(frames) or i in seen or str(i) not in p['observations']:raise ValueError('Invalid source calibration sample')
   seen.add(i)
 active=[{} for f in frames]
 for pi,p in enumerate(points):
  for i,j in p['calibration_node_ids']:active[i][pi]=p['observations'][str(i)]
 frame_edges={};audit=[];hashes=[]
 for i,frame in enumerate(frames):
  if i%5==4:continue
  path=images/frame['path'];im=Image.open(path).convert('L')
  if im.size!=(512,512):raise ValueError('Needs normalized512 frames')
  g=detect_cells(np.asarray(im));keys=list(active[i]);xy=list(active[i].values());mapping={}
  if len(keys)>=2:
   tree=cKDTree(xy)
   for node in g['nodes']:
    d,j=tree.query(node['xy'],k=2)
    if d[0]<=4 and d[1]-d[0]>=1:mapping[node['node_id']]=keys[int(j[0])]
  counts=collections.Counter(mapping.values());mapping={n:p for n,p in mapping.items() if counts[p]==1};edges=set()
  for cell in g['cells']:
   ns=cell['node_ids']
   for a,b in zip(ns,ns[1:]+ns[:1]):
    if a in mapping and b in mapping and mapping[a]!=mapping[b]:edges.add(tuple(sorted((mapping[a],mapping[b]))))
  frame_edges[i]=sorted(edges);audit.append({'sample_index':i,'cells':len(g['cells']),'mapped_unique_corners':len(mapping),'observed_edges':len(edges)});hashes.append({'sample_index':i,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 stable,decisions=supported_intervals(points,frame_edges,yaw);output=apply_intervals(points,decisions,P,yaw,refit)
 original_predictions=json.loads((source/'heldout_predictions.json').read_text());kept={p['track_id']:p for p in output};predictions=copy.deepcopy(original_predictions)
 for row in predictions:
  p=kept.get(row['track_id'])
  for ob in row['predictions']:
   i=ob['sample_index'];ob['retained_interval']=bool(p and p['sample_span'][0]<=i<=p['sample_span'][1]);ob['original_nearest_distance_px']=ob['nearest_distance_px']
   if refit and p:
    # No heldout image lookup or new association. Predict against the old matched node only.
    pred=P[i,:,:3]@np.asarray(p['xyz'])+P[i,:,3];ob['refitted_predicted_xy']=pred.tolist()
    old=points[p['parent_point_index']]['observations'].get(str(i));ob['refitted_error_to_original_matched_detection_px']=float(np.linalg.norm(pred-old)) if old is not None else None
 report={'settings':SETTINGS,'geometry_refitted':refit,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_points_sha256':hashlib.sha256((source/'candidate_points.json').read_bytes()).hexdigest(),'camera_sha256':hashlib.sha256(cameras.read_bytes()).hexdigest(),'original_points':len(points),'retained_points':len(output),'rejected_points':len(points)-len(output),'stable_edges':len(stable),'retained_trimmed_points':sum(p['endpoint_trimmed_observations']>0 for p in output),'removed_observations_in_retained_tracks':sum(p['endpoint_trimmed_observations'] for p in output),'original_observations':sum(len(p['observations']) for p in points),'retained_observations':sum(len(p['observations']) for p in output),'all_original_heldout_predictions':sum(len(r['predictions']) for r in predictions),'heldout_predictions_in_retained_intervals':sum(o['retained_interval'] for r in predictions for o in r['predictions']),'decision_counts':dict(collections.Counter(d['reason'] for d in decisions)),'limitations':['Image neighbor support is not authenticated physical identity.','Original full-span models and associations influenced input selection.','No new heldout matches are made after refitting.','Stable neighbors may share coherent aliases.','The target cameras are experimental; source withholding was not end-to-end calibration isolation.']}
 out.mkdir(parents=True)
 for name,data in [('candidate_points',output),('decisions',decisions),('frame_edges',frame_edges),('frame_audit',audit),('stable_edges',[{'point_indices':list(e),'samples':f} for e,f in sorted(stable.items())]),('heldout_predictions',predictions),('input_calibration_hashes',hashes),('metrics',report)]: (out/(name+'.json')).write_text(json.dumps(data,indent=2))
 (out/'source_snapshot.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(report,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['images','cameras','source','output']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--refit',action='store_true');a=p.parse_args();run(a.images,a.cameras,a.source,a.output,a.refit)
