"""Recover only measured cyclic connectivity from all video frames; no geometry fit."""
from pathlib import Path
import argparse,json,sys,collections
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'marker_consistency/source'))
from quad_cells import detect_cells
from prepare_quad_render import triangle_topology

def canonical(face):
 f=list(face);return min(tuple(q[k:]+q[:k]) for q in [f,f[::-1]] for k in range(4))

def assemble(tracking,points_path,measurement,cameras,out):
 tracking,out=Path(tracking),Path(out)
 if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output')
 manifest=json.loads((tracking/'video_manifest.json').read_text());norm=json.loads(Path(measurement).read_text())['normalization'];cam=json.loads(Path(cameras).read_text());yaw={v['sample_index']:v['yaw_deg'] for v in cam['views']};source=json.loads(Path(points_path).read_text());points=[p for p in source if p['conditional_pass']];active=[{} for _ in manifest['frames']]
 for i,p in enumerate(points):
  for frame,xy in p['observations'].items():active[int(frame)][i]=xy
 faceobs={};audit=[]
 for i,frame in enumerate(manifest['frames']):
  image=Image.open(tracking/frame['path']).convert('RGB');image=image.resize((round(image.width*norm['common_scale']),512));cell=Image.new('RGB',(512,512),'white');cell.paste(image,(round(norm['common_x_padding']),0));g=detect_cells(np.array(cell.convert('L')));keys=list(active[i]);positions=list(active[i].values());candidate={}
  if len(keys)>=2:
   tree=cKDTree(positions)
   for n in g['nodes']:
    dd,ii=tree.query(n['xy'],k=2)
    if dd[0]<=4 and dd[1]-dd[0]>=1:candidate[n['node_id']]=keys[int(ii[0])]
  counts=collections.Counter(candidate.values());mapping={n:p for n,p in candidate.items() if counts[p]==1};collisions=sum(counts[p]>1 for p in candidate.values());mapped=0
  for c in g['cells']:
   if all(n in mapping for n in c['node_ids']):
    face=[mapping[n] for n in c['node_ids']]
    if len(set(face))==4:faceobs.setdefault(canonical(face),[]).append({'sample_index':i,'local_cell_id':c['cell_id']});mapped+=1
  audit.append({'sample_index':i,'cells_detected':len(g['cells']),'unique_node_track_mappings':len(mapping),'colliding_mappings_rejected':collisions,'four_corner_cells':mapped})
 faces=[]
 for ids,obs in faceobs.items():
  span=max(yaw[o['sample_index']] for o in obs)-min(yaw[o['sample_index']] for o in obs)
  if len(obs)>=3 and span>=15:faces.append({'point_indices':list(ids),'source_cells':obs,'fitted_yaw_span_deg':span,'all_corners_conditional_pass':True,'status':'Observed cyclic topology; periodic identity and camera not validated.'})
 xyz=[p['xyz'] for p in points];tri=[t for f in faces for t in [f['point_indices'][:3],[f['point_indices'][0],f['point_indices'][2],f['point_indices'][3]]]];topology=triangle_topology(xyz,tri);report={'points':len(points),'observed_quads':len(faces),'settings':{'minimum_observations':3,'minimum_yaw_span_deg':15,'max_node_track_distance_px':4,'nearest_margin_px':1,'collision_policy':'reject all','point_gate':'unchanged historical3pixel block holdout','point_geometry_refitted':False,'camera_refitted':False,'hidden_completion':False},'topology':topology,'face_observations_min':min((len(f['source_cells']) for f in faces),default=0),'face_observations_max':max((len(f['source_cells']) for f in faces),default=0),'limitations':['All topology is image-conditioned, not proof of physical identities.','Same periodic phase errors may survive both tracking and repeated cells.','Camera is experimental and uncalibrated.','Face winding and self intersections not validated.']}
 out.mkdir(parents=True);(out/'candidate_points.json').write_text(json.dumps(points,indent=2));(out/'candidate_faces.json').write_text(json.dumps(faces,indent=2));(out/'frame_audit.json').write_text(json.dumps(audit,indent=2));(out/'metrics.json').write_text(json.dumps(report,indent=2))
 with (out/'observed_cells.ply').open('w') as f:
  f.write(f'ply\nformat ascii 1.0\ncomment Conditional measured points and observed cells only\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n')
  for p in xyz:f.write(' '.join(map(str,p))+'\n')
  for face in faces:f.write('4 '+' '.join(map(str,face['point_indices']))+'\n')
 print(json.dumps(report,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['tracking','points','measurement','cameras','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();assemble(a.tracking,a.points,a.measurement,a.cameras,a.output)
