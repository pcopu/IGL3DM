"""Draw the actual retained mesh, with explicit coverage loss and evaluation labels."""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def render(root,out):
 font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
 im=Image.new('RGB',(1800,1390),'#f6f8fa');d=ImageDraw.Draw(im)
 d.text((28,20),'Fewer identity errors, at the cost of coverage',font=font(30),fill='#18394a')
 d.text((28,67),'Fourth independent shape: rule frozen before truth was read. Drawings show inferred geometry, not reference meshes.',font=font(21),fill='#40515d')
 def draw(folder,box,bounds_folder,yaw=35,evaluation=False):
  p=json.loads((folder/'candidate_points.json').read_text());f=json.loads((folder/'cells/candidate_faces.json').read_text());allp=json.loads((bounds_folder/'candidate_points.json').read_text());xyz=np.array([q['xyz'] for q in p]);bounds=np.array([q['xyz'] for q in allp]);mid=(bounds.min(0)+bounds.max(0))/2;extent=np.ptp(bounds,axis=0).max();a=np.deg2rad(yaw);R=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1]]);q=(xyz-mid)@R.T;x,y,w,h=box;xy=np.c_[x+w/2+q[:,0]/extent*w*.8,y+h/2-q[:,2]/extent*h*.9];ev=json.loads((folder/'neighbor_physical_evaluation.json').read_text()) if evaluation else None
  for i in sorted(range(len(f)),key=lambda i:q[f[i]['point_indices'],1].mean()):
   ids=f[i]['point_indices'];state=ev['face_rows'][i]['identity'] if ev else None;color='#87bea2' if state=='correct' else '#d7807b' if state in ['wrong_track_identity','wrong_topology'] else '#dfbd77' if ev else '#99bdce';d.polygon([tuple(v) for v in xy[ids]],fill=color,outline='#56716c',width=1)
  for i,(x,y) in enumerate(xy):
   state=ev['point_rows'][i]['identity'] if ev else None;color='#1b7950' if state=='correct' else '#b93d38' if state=='wrong_identity' else '#aa7d24' if ev else '#3b748c';d.ellipse((x-1.6,y-1.6,x+1.6,y+1.6),fill=color)
 original=root/'recovery_waist_hypotheses48_resolvable';trim=root/'recovery_waist_neighbors48_final_frozen'
 for col,(folder,title,sub) in enumerate([(original,'Original broad-view model','189 correct / 9 wrong / 61 unresolved points'),(trim,'After image-neighbor endpoint support','72 correct / 0 wrong / 1 unresolved point')]):
  x=col*600;d.text((x+24,120),title,font=font(22),fill='#18394a');d.text((x+24,157),sub,font=font(20),fill='#40515d');draw(folder,(x+10,210,580,330),original,evaluation=True)
 d.text((28,565),'25 correct faces / 82 candidates',font=font(21),fill='#40515d');d.text((628,565),'16 correct faces / 17 candidates',font=font(21),fill='#40515d')
 lines=['Cleaner does not mean complete.','73 of 259 points remain.','17 of 82 faces remain.','','Wrong tracks remain on another','shape: four coherent ring walks.','All four are isolated points.','','Green: correct identity','Red: wrong identity','Amber: unresolved']
 for j,line in enumerate(lines):d.text((1220,142+j*35),line,font=font(22),fill='#a13e35' if j<3 else '#40515d')
 d.text((28,640),'Robot: same rule, no physical-identity truth available',font=font(29),fill='#18394a')
 original=root/'recovery_robot_hypotheses_resolvable';trim=root/'recovery_robot_neighbors_final_frozen'
 for col,(folder,title) in enumerate([(original,'Original: 198 points / 49 quads'),(trim,'Retained subset: 57 points / 20 quads')]):
  x=col*600;d.text((x+24,692),title,font=font(23),fill='#40515d');draw(folder,(x+15,760,570,385),original,yaw=30)
 lines=['36 vertices in retained faces','21 isolated points','3 surface components','26 boundary edges','0 overused quad edges','','141 candidates are rejected.','No missing surface is invented.','','Robot accuracy is still unknown.','Camera remains experimental.']
 for j,line in enumerate(lines):d.text((1220,756+j*35),line,font=font(22),fill='#a13e35' if j>=9 else '#40515d')
 d.text((28,1200),'Primary comparison keeps XYZ unchanged: this tests temporal endpoint support, not improved geometry.',font=font(23),fill='#40515d')
 d.text((28,1245),'A separate calibration-only refit has the same retained identities and faces. Original predictions and rejected points are preserved.',font=font(21),fill='#40515d')
 d.text((28,1290),'All surfaces are assembled from actual observed cells. This is an incomplete research reconstruction, not a finished asset.',font=font(22),fill='#a13e35')
 d.text((28,1335),'Next obstacle: keep genuine coverage while detecting visibility loss and coherent periodic aliases.',font=font(22),fill='#40515d');out.parent.mkdir(parents=True,exist_ok=True);im.save(out)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();render(a.root,a.output)
