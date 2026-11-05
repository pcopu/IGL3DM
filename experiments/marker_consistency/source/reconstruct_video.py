"""Classical temporal grid reconstruction; conditional camera priors, no learned shape."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw,ImageFont
SOURCE_DIR=Path(__file__).resolve().parent.parent/'source'
sys.path.insert(0,str(SOURCE_DIR))
from geometry import summary
from estimate_cameras import matrix
from quad_cells import detect_cells

def reconstruct(input_directory,measurement_directory,output_directory,period_frames=96,holdout_centers=(12,36,60,84),holdout_radius=2,original_frame_offset=14):
    if not isinstance(period_frames,(int,np.integer)) or period_frames<=0:raise ValueError('period_frames must be a positive integer')
    if not isinstance(holdout_radius,(int,np.integer)) or holdout_radius<0:raise ValueError('holdout_radius must be a nonnegative integer')
    if not isinstance(original_frame_offset,(int,np.integer)) or original_frame_offset<0:raise ValueError('original_frame_offset must be a nonnegative integer')
    if any(not isinstance(c,(int,np.integer)) or c<0 or c>=period_frames for c in holdout_centers):raise ValueError('holdout_centers must be integer indices within the period')
    INPUT=Path(input_directory);MEASUREMENTS=Path(measurement_directory);OUTPUT=Path(output_directory)
    if OUTPUT.exists() and any(OUTPUT.iterdir()):raise ValueError('Refusing nonempty output directory')
    SOURCE=json.loads((INPUT/'tracks.json').read_text());manifest=json.loads((INPUT/'video_manifest.json').read_text());meta=json.loads((MEASUREMENTS/'measurement_manifest.json').read_text());scale=meta['normalization']['common_scale'];pad=meta['normalization']['common_x_padding'];N=manifest['sample_count'];period=period_frames
    if any(i<0 or i>=len(manifest['frames']) for i in meta['selected_sample_indices']):raise ValueError('Measurement indices outside available frames')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    OUT=OUTPUT
    # All camera parameters below are nominal priors, never represented as measured poses.
    cameras=[np.array([2*np.pi*i/period,0,0,np.log(256),256,256]) for i in range(N)]
    holdout=set(i for c in holdout_centers for i in range(c-holdout_radius,c+holdout_radius+1));points=[];usable={};notfit={};quality=[];all_train_errors=[];all_test_errors=[]
    for name,t in SOURCE.items():
     observations=[(o['sample_index'],np.asarray(o['xy'])*scale+[pad,0]) for o in t['observations'] if o['sample_index']<period]
     if len(observations)<9 or observations[-1][0]-observations[0][0]<period*30/360:continue
     training=[o for o in observations if o[0] not in holdout];testing=[o for o in observations if o[0] in holdout]
     if len(training)<6:continue
     A=[];b=[]
     for v,p in training:
      aa,bb=matrix(cameras[v]);A.extend(aa);b.extend(p-bb)
     A=np.array(A);b=np.array(b);w=np.ones(len(A))
     for _ in range(5):
      xyz,_,rank,s=np.linalg.lstsq(A*np.sqrt(w[:,None]),b*np.sqrt(w),rcond=None)
      e=np.linalg.norm((A@xyz-b).reshape(-1,2),axis=1);weights=np.minimum(1.,3/np.maximum(e,1e-6));w=np.repeat(weights,2)
     cond=float(s[0]/s[-1]) if s[-1]>1e-10 else float('inf')
     if rank<3 or cond>20:continue
     trainerrors=np.linalg.norm((A@xyz-b).reshape(-1,2),axis=1);testerrors=[]
     for v,p in testing:
      aa,bb=matrix(cameras[v]);testerrors.append(float(np.linalg.norm(aa@xyz+bb-p)))
     all_train_errors.extend(trainerrors.tolist());all_test_errors.extend(testerrors)
     span=(observations[-1][0]-observations[0][0])*360/period;passed=len(testerrors)>0 and np.percentile(testerrors,95)<=3 and np.percentile(trainerrors,95)<=3
     record={'track_id':name,'xyz':xyz.tolist(),'condition':cond,'sample_span':[observations[0][0],observations[-1][0]],'nominal_angular_span_deg':span,'observations':{v:p.tolist() for v,p in observations},'training_reprojection_px':summary(trainerrors),'heldout_reprojection_px':summary(testerrors),'conditional_pass':bool(passed),'identity_state':'unverified temporal candidate'}
     usable[name]=len(points);points.append(record)
    # Recover only quad faces whose persistent track cycle is seen in >=2 actual sample images.
    faceobservations={};viewaudit=[];tagged=Image.new('RGB',(2048,1120),'white');font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',9);titlefont=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    def canonical(face):
     f=list(face);return min(tuple(q[k:]+q[:k]) for q in [f,f[::-1]] for k in range(4))
    for view,sample in enumerate(meta['selected_sample_indices']):
     image=Image.open(INPUT/manifest['frames'][sample]['path']);image=image.resize((round(image.width*scale),512));cell=Image.new('RGB',(512,512),'white');cell.paste(image,(round(pad),0));gray=np.array(cell.convert('L'));graph=detect_cells(gray)
     active=[];names=[]
     for name,p in zip(usable,points):
      obs=p['observations']
      if sample in obs:names.append(name);active.append(obs[sample])
     corner_map={};tree=cKDTree(active) if active else None
     if tree is not None and len(active)>=2:
      for node in graph['nodes']:
       distance,idx=tree.query(node['xy'],k=2)
       if distance[0]<=4 and distance[1]-distance[0]>=1:corner_map[node['node_id']]=usable[names[idx[0]]]
     assembled=0;d=ImageDraw.Draw(cell)
     for c in graph['cells']:
      if all(n in corner_map for n in c['node_ids']):
       face=[corner_map[n] for n in c['node_ids']]
       if len(set(face))==4:
        key=canonical(face);faceobservations.setdefault(key,[]).append({'view':view,'sample':sample,'local_cell_id':c['cell_id']});assembled+=1
      if c['white_area']>=45:d.text(tuple(c['center']),f"c{c['cell_id']}",font=font,fill='#a2178e',anchor='mm',stroke_width=1,stroke_fill='white')
     for node in graph['nodes']:
      if node['node_id'] in corner_map:
       x,y=node['xy'];idx=corner_map[node['node_id']];d.ellipse((x-2,y-2,x+2,y+2),fill='#e1272c');d.text((x+2,y),str(idx),font=font,fill='#ae1b24',stroke_width=1,stroke_fill='white')
     x=view%4*512;y=view//4*560;tagged.paste(cell,(x,y+38));ImageDraw.Draw(tagged).text((x+8,y+10),f'Frame {sample+original_frame_offset}: {len(graph["cells"])} quads, {assembled} tracked cells',font=titlefont,fill='black');viewaudit.append({'view':view,'sample':sample,'detected_quads':len(graph['cells']),'tracked_candidate_cells':assembled})
    faces=[];facerecords=[]
    for face,obs in faceobservations.items():
     if len(obs)<2:continue
     faces.append(face);facerecords.append({'point_indices':face,'source_cells':obs,'all_corners_conditional_pass':all(points[i]['conditional_pass'] for i in face)})
    tagged.save(OUT/'software_tagged_video_cells.png')
    with (OUT/'candidate_grid_mesh.ply').open('w') as f:
     f.write(f'ply\nformat ascii 1.0\ncomment raw video temporal grid candidates; nominal cameras; no hidden completion\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n')
     for p in points:f.write(' '.join(map(str,p['xyz']))+'\n')
     for face in faces:f.write('4 '+' '.join(map(str,face))+'\n')
    result={'candidate_points_with_at_least_30deg_nominal_span':len(points),'points_passing_train_and_heldout_3px':sum(p['conditional_pass'] for p in points),'points_at_least_90deg_span':sum(p['nominal_angular_span_deg']>=90 for p in points),'passing_points_at_least_90deg_span':sum(p['nominal_angular_span_deg']>=90 and p['conditional_pass'] for p in points),'quad_faces_seen_in_at_least_two_sampled_views':len(faces),'faces_with_all_corners_conditional_pass':sum(f['all_corners_conditional_pass'] for f in facerecords),'training_reprojection_px':summary(all_train_errors),'heldout_observation_px':summary(all_test_errors),'per_track_heldout_median_px':summary([p['heldout_reprojection_px']['median'] for p in points if p['heldout_reprojection_px']['n']]),'view_audit':viewaudit,'period_frames_prior':period,'original_frame_offset':original_frame_offset,'holdout_centers':list(holdout_centers),'holdout_radius':holdout_radius,'decoded_measurement_samples':N,'camera_status':f'Nominal full-turn level orthographic prior: 360deg in {period} sample intervals. Not calibrated. Intrinsic scale is a gauge.','holdout':f'Blocks with radius {holdout_radius} centered at {list(holdout_centers)} excluded from point fits. Samples >= {period} excluded as endpoints. Tracking used all frames; feature selection not held out.','limitations':['Grid identity remains unverified; smooth periodic swaps can pass geometric tests.','Shape/grid warping or varying camera intrinsics can invalidate triangulation.','Only observed shared quad connectivity is assembled; no hidden faces or learned completion.','The presentation crossfade was never used for measurement.']}
    (OUT/'candidate_points.json').write_text(json.dumps(points,indent=2));(OUT/'candidate_faces.json').write_text(json.dumps(facerecords,indent=2));(OUT/'metrics.json').write_text(json.dumps(result,indent=2))
    # Render actual inferred geometry.
    canvas=Image.new('RGB',(1500,570),'#f4f6f8');d=ImageDraw.Draw(canvas)
    if not points:
     d.text((15,25),'No candidate points passed observation, baseline and conditioning requirements.',font=titlefont,fill='black');canvas.save(OUT/'candidate_grid_mesh_preview.png');print(json.dumps(result,indent=2));return
    xyz=np.array([p['xyz'] for p in points]);mid=(xyz.min(0)+xyz.max(0))/2;extent=max(np.ptp(xyz,axis=0).max(),1e-6)
    for col,yaw in enumerate([0,90,40]):
     a=np.deg2rad(yaw);r=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1.]])
     q=(xyz-mid)@r.T;screen=np.c_[col*500+250+q[:,0]/extent*380,280-q[:,2]/extent*430]
     for face,rec in sorted(zip(faces,facerecords),key=lambda item:q[list(item[0]),1].mean()):d.polygon([tuple(p) for p in screen[list(face)]],fill='#a8d4b1' if rec['all_corners_conditional_pass'] else '#e5bd98',outline='#68615b',width=1)
     for i,(x,y) in enumerate(screen):d.ellipse((x-1,y-1,x+1,y+1),fill='#207b3b' if points[i]['conditional_pass'] else '#aa6a34')
     d.text((col*500+10,16),f'Actual video-derived candidates | yaw {yaw}deg',font=titlefont,fill='black')
    d.text((15,521),f'{len(points)} points / {len(faces)} observed quads. Green=conditional checks only. Nominal cameras; no hidden completion.',font=titlefont,fill='black');canvas.save(OUT/'candidate_grid_mesh_preview.png');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-directory',type=Path,required=True,help='Tracker output with video_manifest.json, tracks.json and frames/')
    p.add_argument('--measurement-directory',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True)
    p.add_argument('--period-frames',type=int,default=96)
    p.add_argument('--holdout-centers',type=int,nargs='+',default=[12,36,60,84])
    p.add_argument('--holdout-radius',type=int,default=2)
    p.add_argument('--original-frame-offset',type=int,default=14)
    a=p.parse_args();reconstruct(a.input_directory,a.measurement_directory,a.output_directory,a.period_frames,a.holdout_centers,a.holdout_radius,a.original_frame_offset)
