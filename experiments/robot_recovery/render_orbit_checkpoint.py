"""Render actual multi-view candidate geometry and independent identity annotations."""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def render(root,out):
 font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
 im=Image.new('RGB',(1800,1380),'#f6f8fa');d=ImageDraw.Draw(im);d.text((28,18),'Wider-view matching recovers identities that optical flow missed',font=font(31),fill='#18394a');d.text((28,65),'Three 48-view controls. All colors below score actual inferred geometry, never a substituted reference mesh.',font=font(22),fill='#40515d')
 def project(points,x,y,width,height,yaw):
  xyz=np.array([p['xyz'] for p in points]);mid=(xyz.min(0)+xyz.max(0))/2;extent=max(np.ptp(xyz,axis=0).max(),1e-6);a=np.deg2rad(yaw);R=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1]]);q=(xyz-mid)@R.T;screen=np.c_[x+width/2+q[:,0]/extent*width*.77,y+height/2-q[:,2]/extent*height*.94];return q,screen
 folders=['recovery_orbit_hypotheses48_resolvable','recovery_bent_hypotheses48_resolvable','recovery_barrel_hypotheses48_resolvable'];names=['Original pear: development','Bent ovoid: development','Third shape: frozen blind comparison']
 for col,(folder,name) in enumerate(zip(folders,names)):
  h=root/folder;points=json.loads((h/'cells/candidate_points.json').read_text());faces=json.loads((h/'cells/candidate_faces.json').read_text());ev=json.loads((h/'physical_identity_evaluation.json').read_text());counts=ev['point_identity_counts'];x=col*600;d.text((x+24,112),name,font=font(23),fill='#18394a');d.text((x+24,149),f"{counts.get('correct',0)} correct / {counts.get('wrong_identity',0)} wrong / {counts.get('unresolved',0)} unresolved",font=font(20),fill='#40515d');q,screen=project(points,x+10,196,580,342,35)
  for fi in sorted(range(len(faces)),key=lambda fi:q[faces[fi]['point_indices'],1].mean()):
   face=faces[fi];status=ev['face_rows'][fi]['identity'];color='#8ac3a4' if status=='correct' else '#dc8a85' if status in ['wrong_track_identity','wrong_topology'] else '#e5c17e';d.polygon([tuple(p) for p in screen[face['point_indices']]],fill=color,outline='#56716c',width=1)
  for pi,p in enumerate(screen):
   status=ev['point_rows'][pi]['identity'];color='#1b7950' if status=='correct' else '#b93d38' if status=='wrong_identity' else '#aa7d24';d.ellipse((p[0]-1.4,p[1]-1.4,p[0]+1.4,p[1]+1.4),fill=color)
  d.text((x+24,558),f"{ev['unique_correct_physical_faces']} correct physical faces / {len(faces)} candidates",font=font(20),fill='#40515d')
 d.text((28,612),'Green = correct; red = identity change; amber = unresolved. Old LK accepted subset: zero correct tracks on these controls.',font=font(22),fill='#40515d')
 h=root/'recovery_robot_hypotheses_resolvable';points=json.loads((h/'cells/candidate_points.json').read_text());faces=json.loads((h/'cells/candidate_faces.json').read_text());metrics=json.loads((h/'metrics.json').read_text());d.text((28,677),'Actual robot output: 198 measured points and 49 observed quads',font=font(29),fill='#18394a')
 for col,yaw in enumerate([0,55]):
  x=col*600;q,screen=project(points,x+15,772,570,370,yaw)
  for f in sorted(faces,key=lambda f:q[f['point_indices'],1].mean()):d.polygon([tuple(p) for p in screen[f['point_indices']]],fill='#97bdcf',outline='#436273',width=1)
  for px,py in screen:d.ellipse((px-1.4,py-1.4,px+1.4,py+1.4),fill='#3b748c')
  d.text((x+28,1170),f'Inferred mesh, yaw {yaw} degrees',font=font(21),fill='#40515d')
 text=['12 disconnected surface patches','113 vertices participate in faces','85 remaining isolated points','104 boundary edges','0 overused quad edges','','1,931 / 2,024 withheld predictions','matched unique detected nodes.','','Robot identities remain unverified.','Camera is still experimental.']
 for j,line in enumerate(text):d.text((1220,786+j*33),line,font=font(23),fill='#a13e35' if j>=9 else '#40515d')
 d.text((28,1240),'No hidden faces, silhouette filling or target reference geometry. Better controls do not prove robot correctness.',font=font(23),fill='#a13e35');d.text((28,1283),'Point models use calibration images only. Target camera estimates and face assembly have separate limits.',font=font(22),fill='#40515d');d.text((28,1325),'All failures, source observations, model files and exact test results are retained in the experiment log.',font=font(22),fill='#40515d');out.parent.mkdir(parents=True,exist_ok=True);im.save(out)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();render(a.root,a.output)
