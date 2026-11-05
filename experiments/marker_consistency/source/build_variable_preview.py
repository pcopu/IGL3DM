"""Exploratory geometry from selected observations and explicit experimental cameras.

No completion: only four-corner cells observed in at least three actual frames
are assembled. Calibration is NOT accepted; this output is model-conditional.
"""
from pathlib import Path
import argparse,json,sys
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parent))
from quad_cells import detect_cells
from geometry import summary
from graph_consistency import canonical_cycle

def build(tracks_path,manifest_path,graph_path,cameras_path,selection_path,output_directory):
 out=Path(output_directory)
 if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output directory')
 tracks=json.loads(Path(tracks_path).read_text());manifest_path=Path(manifest_path);manifest=json.loads(manifest_path.read_text());ev=json.loads(Path(graph_path).read_text());camera=json.loads(Path(cameras_path).read_text());selection=json.loads(Path(selection_path).read_text())['real']['variable']['selected_candidate_track_ids'];cameras={v['sample_index']:np.asarray(v['orthographic_projection_2x4_normalized512']) for v in camera['views']};w,h=manifest['working_size'];scale=512/h;pad=(512-w*scale)/2
 records=[];lookup={};allerrors=[]
 for name in selection:
  t=tracks[name];oo=t['observations'];time=np.array([o['sample_index'] for o in oo]);xy=np.array([o['xy'] for o in oo])*scale+[pad,0];fraction=(time-time[0])/(time[-1]-time[0]);train=(fraction>=.25)&(fraction<=.75);A=np.stack([cameras[int(i)][:,:3] for i in time]);b=np.stack([cameras[int(i)][:,3] for i in time]);xyz,_,rank,s=np.linalg.lstsq(A[train].reshape(-1,3),(xy[train]-b[train]).ravel(),rcond=None);pred=np.einsum('nij,j->ni',A,xyz)+b;errors=np.linalg.norm(pred-xy,axis=1);allerrors.extend(errors[~train].tolist());lookup[name]=len(records);records.append({'track_id':name,'source_track_id':t['source_track_id'],'xyz':xyz.tolist(),'observations':{int(i):p.tolist() for i,p in zip(time,xy)},'fit_samples':time[train].tolist(),'test_samples':time[~train].tolist(),'condition':float(s[0]/s[-1]),'rank':int(rank),'training_px':summary(errors[train]),'endpoint_test_px':summary(errors[~train]),'status':'conditional experimental camera; physical identity unverified'})
 faceobs={};node_maps={}
 for name in selection:
  t=tracks[name];source=t['source_track_id'];by_sample={r['sample_index']:r for r in ev['tracks'][source]}
  for ob in t['observations']:
   i=ob['sample_index'];nid=by_sample[i]['node_id']
   if nid is not None:node_maps.setdefault(i,{})[nid]=lookup[name]
 for i,node_to_point in node_maps.items():
  frame=manifest['frames'][i];raw=cv2.imread(str(manifest_path.parent/frame['path']),cv2.IMREAD_GRAYSCALE);resized=cv2.resize(raw,(round(w*scale),512),interpolation=cv2.INTER_AREA);image=np.full((512,512),255,np.uint8);left=round(pad);image[:,left:left+resized.shape[1]]=resized;graph=detect_cells(image)
  for c in graph['cells']:
   if all(n in node_to_point for n in c['node_ids']):
    ids=[node_to_point[n] for n in c['node_ids']]
    if len(set(ids))==4:faceobs.setdefault(canonical_cycle(ids),[]).append({'sample_index':i,'local_cell_id':c['cell_id']})
 faces=[{'point_indices':list(face),'source_cells':obs,'status':'observed cyclic connectivity only; winding unvalidated'} for face,obs in faceobs.items() if len(obs)>=3]
 out.mkdir(parents=True,exist_ok=True);(out/'candidate_points.json').write_text(json.dumps(records,indent=2));(out/'candidate_faces.json').write_text(json.dumps(faces,indent=2))
 with (out/'experimental_grid_mesh.ply').open('w') as f:
  f.write(f'ply\nformat ascii 1.0\ncomment UNVALIDATED variable camera; no hidden completion\nelement vertex {len(records)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n')
  for p in records:f.write(' '.join(map(str,p['xyz']))+'\n')
  for face in faces:f.write('4 '+' '.join(map(str,face['point_indices']))+'\n')
 report={'experimental_camera_accepted':False,'points':len(records),'observed_quad_faces_seen_at_least_three_frames':len(faces),'vertices_used_by_faces':len({i for f in faces for i in f['point_indices']}),'endpoint_test_observation_px':summary(allerrors),'fit':'Middle half of each segment; endpoint quarters are conditional checks. Camera itself was fitted to calibration track candidates, and selection used all frames.','camera_status':camera['status'],'coordinates':camera['coordinates'],'world_convention':'Z-up orbit-axis gauge; yaw0 near negativeY viewing direction with fitted elevation/roll. Scale256px/world-unit is a relative gauge, not metric calibration. Exact per-frame projection matrices retained separately.','no_hidden_faces':True,'winding_validated':False,'prior_results_preserved':True}
 (out/'metrics.json').write_text(json.dumps(report,indent=2))
 canvas=Image.new('RGB',(1500,590),'#f7f8fa');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
 if not records:
  d.text((15,30),'No selected points; no surface invented.',font=font,fill='#a83326');canvas.save(out/'experimental_geometry_preview.png');return report
 xyz=np.asarray([p['xyz'] for p in records]);mid=(xyz.max(0)+xyz.min(0))/2;extent=max(np.ptp(xyz,axis=0).max(),1e-6)
 for j,angle in enumerate([0,90,40]):
  a=np.deg2rad(angle);R=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1]]);q=(xyz-mid)@R.T;screen=np.c_[j*500+250+q[:,0]/extent*390,285-q[:,2]/extent*440]
  for face in faces:d.polygon([tuple(v) for v in screen[face['point_indices']]],fill='#b1c5dd',outline='#56708e',width=2)
  for p in screen:d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill='#1d5d8e')
  d.text((j*500+15,17),f'Actual inferred points | display yaw {angle}deg',font=font,fill='black')
 d.text((15,525),f'UNVALIDATED CAMERA: {len(records)} points / {len(faces)} observed quads. No completed surface.',font=font,fill='#a83326');d.text((15,553),'More flexible motion improves held-out image error but worsens known-control camera accuracy. Not ground truth.',font=font,fill='black');canvas.save(out/'experimental_geometry_preview.png');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['tracks','manifest','graph','cameras','selection','output-directory']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(build(a.tracks,a.manifest,a.graph,a.cameras,a.selection,a.output_directory),indent=2))
