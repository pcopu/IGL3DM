"""Evaluation-only physical vertex/face identities. Never repair reconstruction with truth."""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib
import numpy as np
from scipy.spatial import cKDTree

def cyclic(ids):
 f=list(ids);return min(tuple(q[k:]+q[:k]) for q in [f,f[::-1]] for k in range(len(f)))

def score(points,faces,truth,radius=3.,margin=1.):
 vertices=np.asarray(truth['vertices']);physical={};canon=[]
 for v in vertices:
  key=tuple(np.round(v,7));physical.setdefault(key,len(physical));canon.append(physical[key])
 positions={canon[i]:v for i,v in enumerate(vertices)}
 truefaces={cyclic([canon[i] for i in f]) for f in truth['faces'] if len(f)==4 and len({canon[i] for i in f})==4}
 lookups={};visible={};visible_cells={};view_yaw={}
 for view in truth['views']:
  unique={}
  for ob in view['observations']:
   if ob['visible']:unique.setdefault(canon[ob['vertex_id']],ob['xy'])
  ids=list(unique);xy=list(unique.values());idx=int(view['view']);lookups[idx]=(cKDTree(xy),ids);visible[idx]=set(ids);view_yaw[idx]=view['yaw_deg']
  for face in truefaces:
   if set(face)<=visible[idx]:visible_cells.setdefault(face,[]).append(idx)
 point_rows=[];obs_maps=[]
 for pi,p in enumerate(points):
  resolved={};obsrows=[];ds=[]
  for frame,xy in p['observations'].items():
   frame=int(frame);tree,ids=lookups[frame];d,k=tree.query(xy,k=2);ds.append(float(d[0]));known=int(ids[int(k[0])]) if d[0]<=radius and d[1]-d[0]>=margin else None
   resolved[frame]=known;obsrows.append({'sample_index':frame,'physical_id':known,'nearest_distance_px':float(d[0]),'nearest_separation_px':float(d[1]-d[0])})
  distinct={v for v in resolved.values() if v is not None};unresolved=sum(v is None for v in resolved.values())
  status='wrong_identity' if len(distinct)>1 else 'unresolved' if unresolved or not distinct else 'correct'
  pid=next(iter(distinct)) if status=='correct' else None
  point_rows.append({'point_index':pi,'track_id':p.get('track_id'),'identity':status,'physical_id':pid,'resolved_distinct_ids':sorted(distinct),'unresolved_observations':unresolved,'observations':len(resolved),'known_3d_error':float(np.linalg.norm(np.asarray(p['xyz'])-positions[pid])) if pid is not None else None,'observation_identity':obsrows})
  obs_maps.append(resolved)
 face_rows=[];correctfaces=[];local_correctfaces=[]
 for fi,f in enumerate(faces):
  ids=f['point_indices'];pr=[point_rows[i] for i in ids];local=[];mapped=[]
  for ob in f['source_cells']:
   frame=int(ob.get('sample_index',ob.get('sample')));physicalids=[obs_maps[i].get(frame) for i in ids]
   key=cyclic(physicalids) if None not in physicalids else None
   status='unresolved' if key is None else 'correct_cell' if key in truefaces else 'wrong_cell'
   local.append({'sample_index':frame,'status':status,'physical_cycle':list(key) if key is not None else None})
   if status=='correct_cell':mapped.append(key)
  statuses=[p['identity'] for p in pr];key=cyclic([p['physical_id'] for p in pr]) if all(s=='correct' for s in statuses) else None
  status='wrong_track_identity' if 'wrong_identity' in statuses else 'unresolved' if 'unresolved' in statuses else 'correct' if key in truefaces else 'wrong_topology'
  if status=='correct':correctfaces.append(key)
  local_status='unresolved' if any(o['status']=='unresolved' for o in local) else 'wrong_cell' if any(o['status']=='wrong_cell' for o in local) else 'changed_physical_cell' if len(set(mapped))>1 else 'correct_same_cell'
  if local_status=='correct_same_cell':local_correctfaces.append(mapped[0])
  face_rows.append({'face_index':fi,'point_indices':ids,'identity':status,'physical_cycle':list(key) if key is not None else None,'source_cell_identity':local_status,'source_observations':local})
 available={face for face,frames in visible_cells.items() if len(frames)>=3 and max(view_yaw[i] for i in frames)-min(view_yaw[i] for i in frames)>=15}
 errs=[p['known_3d_error'] for p in point_rows if p['known_3d_error'] is not None]
 return {'evaluation_only':True,'settings':{'maximum_association_distance_px':radius,'minimum_nearest_separation_px':margin,'physical_vertex_canonicalization_decimals':7,'full_track_required':True},'points':len(points),'point_identity_counts':dict(Counter(p['identity'] for p in point_rows)),'faces':len(faces),'face_identity_counts':dict(Counter(f['identity'] for f in face_rows)),'source_cell_identity_counts':dict(Counter(f['source_cell_identity'] for f in face_rows)),'strict_correct_face_fraction_all':len(correctfaces)/len(faces) if faces else None,'unique_correct_physical_faces':len(set(correctfaces)),'duplicate_correct_physical_faces':len(correctfaces)-len(set(correctfaces)),'unique_locally_correct_physical_faces':len(set(local_correctfaces)),'available_non_degenerate_truth_faces':len(truefaces),'geometrically_visible_faces_with_support':len(available),'strict_covered_visible_faces':len(set(correctfaces)&available),'strict_geometric_visibility_coverage':len(set(correctfaces)&available)/len(available) if available else None,'known_correct_point_3d_error':{'n':len(errs),'median':float(np.median(errs)) if errs else None,'p95':float(np.percentile(errs,95)) if errs else None,'max':max(errs) if errs else None},'limitations':['Geometric visibility is an upper-bound denominator, not evidence of detector readability.','Ambiguous or unresolved observations remain in all denominators.','Shared control cameras are declared acquisition metadata; this does not evaluate unknown camera calibration.','No truth labels, positions or face connectivity are used to select or repair algorithm outputs.'],'point_rows':point_rows,'face_rows':face_rows}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['points','faces','truth','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise ValueError('Refusing existing evaluation')
 r=score(json.loads(a.points.read_text()),json.loads(a.faces.read_text()),json.loads(a.truth.read_text()));r['input_sha256']={k:hashlib.sha256(getattr(a,k).read_bytes()).hexdigest() for k in ['points','faces','truth']};a.output.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['point_rows','face_rows']},indent=2))
