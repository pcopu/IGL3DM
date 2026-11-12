"""Plot actual reconstructed geometry; truth colors are evaluation annotations only."""
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from audit_cell_conflicts import audit

def render(root,out):
 font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
 im=Image.new('RGB',(1720,1270),'#f6f8fa');d=ImageDraw.Draw(im);d.text((28,18),'Physical identity checks before topology cleanup',font=font(32),fill='#18394a');d.text((28,63),'Actual reconstructed faces below. Control truth is used only to evaluate, never to reconstruct.',font=font(23),fill='#40515d')
 control=root/'recovery_face_control96_avi';datasets=[(control/'cells',control/'physical_identity_evaluation.json','96-view control: original 270 faces','242 correct / 7 wrong-track / 21 unresolved'),(control/'joined_cells',control/'joined_cells/physical_identity_evaluation.json','After seven supported fragment joins: 252','230 correct / 4 wrong-track / 18 unresolved'),(root/'recovery_dense_cells',None,'Robot: original 81 observed faces','4 overused edges; conflicting faces highlighted'),(root/'recovery_joined_cells',None,'After two supported fragment joins: 78','1 overused edge remains; no hidden surface filling')]
 data=[]
 for folder,ev,title,sub in datasets:
  p=json.loads((folder/'candidate_points.json').read_text());f=json.loads((folder/'candidate_faces.json').read_text());data.append((p,f,json.loads(ev.read_text()) if ev else None,title,sub))
 for row in range(2):
  used=[i for f in data[row*2][1] for i in f['point_indices']];base=np.array([p['xyz'] for p in data[row*2][0]])[used];center=(base.min(0)+base.max(0))/2;extent=np.ptp(base,axis=0).max()
  for col in range(2):
   p,faces,ev,title,sub=data[row*2+col];x=col*860;y=105+row*510;d.text((x+28,y),title,font=font(24),fill='#18394a');d.text((x+28,y+37),sub,font=font(21),fill='#40515d');xyz=np.array([p['xyz'] for p in p]);a=np.deg2rad(35);R=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1]]);q=(xyz-center)@R.T;screen=np.c_[x+430+q[:,0]/extent*470,y+270-q[:,2]/extent*340];bad=set(audit(p,faces)[0]['removed_face_indices']);statuses=[f['identity'] for f in ev['face_rows']] if ev else None
   for fi in sorted(range(len(faces)),key=lambda fi:q[faces[fi]['point_indices'],1].mean()):
    face=faces[fi];color=('#88c0a6' if statuses[fi]=='correct' else '#e08a83' if statuses[fi] in ['wrong_track_identity','wrong_topology'] else '#e4c07c') if statuses else '#d790b0' if fi in bad else '#9bbcca';d.polygon([tuple(v) for v in screen[face['point_indices']]],fill=color,outline='#45616a',width=1)
   if row==0:caption='218 distinct correct physical cells; 30 overused edges' if col==0 else 'Same 218 distinct correct physical cells; 8 overused edges'
   else:caption='25 disconnected surface components; identities unverified'
   d.text((x+28,y+456),caption,font=font(20),fill='#40515d')
 d.text((28,1140),'Green / red / amber are control-only correctness labels. Pink marks robot topological contradictions.',font=font(22),fill='#40515d');d.text((28,1181),'48-view stress: 32 of 34 accepted points switch identity, and no faces survive. Periodic aliasing persists.',font=font(22),fill='#a23b31');d.text((28,1221),'These are partial measured patches, not completed or validated robot assets.',font=font(22),fill='#40515d');out.parent.mkdir(parents=True,exist_ok=True);im.save(out)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();render(a.root,a.output)
