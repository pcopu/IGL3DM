"""Recompute geometry and structural provenance without reading physical truth."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from associate_orbit_hypotheses import fit

def validate(root,cameras):
 points=json.loads((root/'candidate_points.json').read_text());metrics=json.loads((root/'metrics.json').read_text());nodes={f['sample_index']:np.array(f['xy']) for f in json.loads((root/'frame_nodes.json').read_text())};P=np.array([v['orthographic_projection_2x4_normalized512'] for v in json.loads(cameras.read_text())['views']]);rows=json.loads((root/'heldout_predictions.json').read_text());used=set();held_used=set();coordinate_errors=[];xyz_errors=[];training_max=[];density=[]
 if len(points)!=len(rows):raise ValueError('Model/holdout row count mismatch')
 if hashlib.sha256(cameras.read_bytes()).hexdigest()!=metrics['camera_sha256']:raise ValueError('Camera source hash mismatch')
 for point,row in zip(points,rows):
  if point['track_id']!=row['track_id']:raise ValueError('Holdout record order mismatch')
  pairs=[tuple(k) for k in point['calibration_node_ids']]
  if any(i%5==4 for i,j in pairs):raise ValueError('Heldout node used for model fit')
  if any(p in used for p in pairs):raise ValueError('Calibration node reused')
  used.update(pairs);obs=[(i,nodes[i][j]) for i,j in pairs];xyz,rank,condition,errors=fit(obs,P);xyz_errors.append(float(np.linalg.norm(xyz-point['xyz'])));training_max.append(float(max(errors)))
  for i,j in pairs:coordinate_errors.append(float(np.linalg.norm(nodes[i][j]-point['observations'][str(i)])))
  inside=[i for i in metrics['calibration_frames'] if pairs[0][0]<=i<=pairs[-1][0]];density.append(len(pairs)/len(inside))
  for o in row['predictions']:
   if o['matched']:
    key=(o['sample_index'],o['node_id'])
    if key in held_used:raise ValueError('Withheld node reused')
    held_used.add(key);coordinate_errors.append(float(np.linalg.norm(nodes[key[0]][key[1]]-point['observations'][str(key[0])])))
   elif str(o['sample_index']) in point['observations']:raise ValueError('Rejected prediction inserted as observation')
 if max(xyz_errors,default=0)>1e-10 or max(coordinate_errors,default=0)>1e-10:raise ValueError('Numerical provenance mismatch')
 if metrics['settings']['resolvability_gate'] and min(density,default=1)<.9:raise ValueError('Calibration density gate violated')
 return {'passed':True,'models':len(points),'calibration_nodes_unique':len(used),'matched_heldout_nodes_unique':len(held_used),'maximum_xyz_recompute_error':max(xyz_errors,default=0),'maximum_observed_coordinate_difference':max(coordinate_errors,default=0),'minimum_calibration_density':min(density,default=None),'maximum_final_training_residual_px':max(training_max,default=None),'camera_sha256_matches':hashlib.sha256(cameras.read_bytes()).hexdigest()==metrics['camera_sha256'],'truth_read':False,'checks':['Heldout nodes absent from all model fits.','Every emitted coordinate is an actual independently detected node.','All calibration and emitted heldout nodes are one-to-one.','All XYZ values reproduce from calibration observations only.','Rejected predictions are never inserted.']}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--cameras',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=validate(a.root,a.cameras);a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
