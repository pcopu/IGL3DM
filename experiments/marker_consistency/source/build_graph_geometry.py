"""Conditional geometry from re-detected graph tracks and explicit camera matrices.

Camera parameters are supplied experimental estimates, not accepted calibration.
Only observed four-node cell cycles are assembled; no hidden completion.
"""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from geometry import summary

def cycle(ids):
 f=list(ids);return min(tuple(q[k:]+q[:k]) for q in [f,f[::-1]] for k in range(4))

def build(tracks_path,graphs_path,cameras_path,out):
 out=Path(out)
 if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output')
 tracks=json.loads(Path(tracks_path).read_text());graphs=json.loads(Path(graphs_path).read_text());camera=json.loads(Path(cameras_path).read_text());cams={v['sample_index']:np.asarray(v['orthographic_projection_2x4_normalized512']) for v in camera['views']};yaw={v['sample_index']:v['yaw_deg'] for v in camera['views']};points=[];audit=[]
 for name,t in tracks.items():
  oo=t['observations']
  if len(oo)<9:continue
  time=np.array([o['sample_index'] for o in oo]);span=yaw[int(time[-1])]-yaw[int(time[0])]
  if span<30:continue
  xy=np.array([o['xy'] for o in oo]);fraction=(time-time[0])/(time[-1]-time[0]);train=(fraction>=.25)&(fraction<=.75)
  if train.sum()<4:continue
  A=np.stack([cams[int(i)][:,:3] for i in time]);b=np.stack([cams[int(i)][:,3] for i in time]);xyz,_,rank,s=np.linalg.lstsq(A[train].reshape(-1,3),(xy[train]-b[train]).ravel(),rcond=None);condition=float(s[0]/s[-1]) if s[-1]>1e-12 else float('inf');errors=np.linalg.norm(np.einsum('nij,j->ni',A,xyz)+b-xy,axis=1);training=summary(errors[train]);held=summary(errors[~train]);keep=bool(rank==3 and condition<=20 and training['p95']<=1 and held['p95']<=1)
  audit.append({'track_id':name,'span_deg':float(span),'condition':condition,'training_p95':training['p95'],'end_quarter_p95':held['p95'],'retained':keep})
  if keep:points.append({'track_id':name,'xyz':xyz.tolist(),'condition':condition,'fitted_yaw_span_deg':float(span),'observations':oo,'training_px':training,'endpoint_test_px':held,'status':'conditional candidate, experimental camera unaccepted'})
 nodes={}
 for p,t in enumerate(points):
  for o in t['observations']:nodes.setdefault(o['sample_index'],{})[o['node_id']]=p
 faceobs={}
 for g in graphs:
  frame=g['sample_index'];mapping=nodes.get(frame,{})
  for cid,cc in enumerate(g['closed_cells']):
   if all(n in mapping for n in cc):
    face=[mapping[n] for n in cc]
    if len(set(face))==4:faceobs.setdefault(cycle(face),[]).append({'sample_index':frame,'local_cell_index':cid})
 faces=[{'point_indices':list(ids),'source_cells':ob,'status':'observed connectivity; winding not validated'} for ids,ob in faceobs.items() if len(ob)>=3]
 out.mkdir(parents=True,exist_ok=True);(out/'candidate_points.json').write_text(json.dumps(points,indent=2));(out/'candidate_faces.json').write_text(json.dumps(faces,indent=2));(out/'selection_audit.json').write_text(json.dumps(audit,indent=2))
 with (out/'conditional_graph_mesh.ply').open('w') as f:
  f.write(f'ply\nformat ascii 1.0\ncomment UNVALIDATED graph geometry with unchanged experimental camera\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n')
  for p in points:f.write(' '.join(map(str,p['xyz']))+'\n')
  for face in faces:f.write('4 '+' '.join(map(str,face['point_indices']))+'\n')
 report={'input_track_count':len(tracks),'candidate_points':len(points),'observed_quad_faces_at_least_three_frames':len(faces),'vertices_used_in_faces':len({i for f in faces for i in f['point_indices']}),'camera_sha256':hashlib.sha256(Path(cameras_path).read_bytes()).hexdigest(),'camera_refitted':False,'accepted_calibration':False,'selected_training_p95_distribution':summary([p['training_px']['p95'] for p in points]),'selected_endpoint_p95_distribution':summary([p['endpoint_test_px']['p95'] for p in points]),'minimum_face_observations':min((len(f['source_cells']) for f in faces),default=0),'maximum_face_observations':max((len(f['source_cells']) for f in faces),default=0),'selection':'Same predeclared1px midpoint-fit/end-quarter gate and>=30deg experimental yaw span. This is selection-conditioned fit quality, not independent physical accuracy.','coordinates':camera['coordinates'],'completion_added':False};(out/'metrics.json').write_text(json.dumps(report,indent=2))
 canvas=Image.new('RGB',(1500,590),'#f7f8fa');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
 if points:
  xyz=np.array([p['xyz'] for p in points]);mid=(xyz.max(0)+xyz.min(0))/2;extent=max(np.ptp(xyz,axis=0).max(),1e-6)
  for j,angle in enumerate([0,90,40]):
   a=np.deg2rad(angle);R=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1]]);q=(xyz-mid)@R.T;screen=np.c_[j*500+250+q[:,0]/extent*390,285-q[:,2]/extent*440]
   for face in faces:d.polygon([tuple(p) for p in screen[face['point_indices']]],fill='#b4d3be',outline='#51765e',width=2)
   for x,y in screen:d.ellipse((x-2,y-2,x+2,y+2),fill='#247248')
   d.text((j*500+15,17),f'Actual graph-derived geometry | display {angle}deg',font=font,fill='black')
 else:d.text((15,70),'No accepted candidates; no surface invented.',font=font,fill='black')
 d.text((15,525),f'UNVALIDATED CAMERA: {len(points)} points / {len(faces)} observed quads. No completed surface.',font=font,fill='#a62b24');d.text((15,553),'Re-detected nodes and joint graph matching. Camera estimates unchanged. Low residuals do not prove identity.',font=font,fill='black');canvas.save(out/'conditional_graph_geometry_preview.png');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['tracks','graphs','cameras','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(build(a.tracks,a.graphs,a.cameras,a.output),indent=2))
