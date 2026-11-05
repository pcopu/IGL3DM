"""Build only shared quad connectivity observed in >=2 views. No surface completion."""
from pathlib import Path
import json,argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def build(directory):
    graphs=json.loads((directory/'quad_graph.json').read_text());points=json.loads((directory/'candidate_vertices.json').read_text());lookup={}
    for i,p in enumerate(points):
        for v,n in p['view_node_ids']:lookup[v,n]=i
    candidates={}
    def canonical(q):
        q=list(q);seq=[]
        for base in [q,q[::-1]]:
            for i in range(4):seq.append(tuple(base[i:]+base[:i]))
        return min(seq)
    for g in graphs:
        v=g['view']
        for c in g['cells']:
            if not all((v,n) in lookup for n in c['node_ids']):continue
            face=[lookup[v,n] for n in c['node_ids']]
            if len(set(face))<4:continue
            key=canonical(face);candidates.setdefault(key,[]).append({'view':v,'cell_id':c['cell_id']})
    faces=[];evidence=[]
    for face,obs in candidates.items():
        if len({x['view'] for x in obs})<2:continue
        faces.append(face);evidence.append({'point_indices':face,'observed_cells':obs,'all_corners_three_view_consistent':all(points[i]['status']=='conditional_consistency_only' for i in face)})
    xyz=np.array([p['xyz'] for p in points]);ply=directory/'candidate_patch_mesh.ply'
    with ply.open('w') as f:
        f.write(f'ply\nformat ascii 1.0\ncomment exploratory grid-derived partial patches; no inferred hidden connectivity\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n')
        for p in xyz:f.write(' '.join(map(str,p))+'\n')
        for face in faces:f.write('4 '+' '.join(map(str,face))+'\n')
    report={'point_count':len(points),'quad_faces_seen_in_at_least_two_views':len(faces),'three_view_consistent_quad_faces':sum(e['all_corners_three_view_consistent'] for e in evidence),
      'faces':evidence,'status':'Exploratory disconnected grid-derived partial mesh, not a complete reconstructed pear. Two-view support does not validate physical identity or camera calibration. No hidden faces filled.'}
    (directory/'candidate_patch_mesh_report.json').write_text(json.dumps(report,indent=2))
    # Render actual point coordinates/quad indices, no artist interpretation.
    canvas=Image.new('RGB',(1500,570),'#f3f6f8');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
    if len(points):
        mid=(xyz.min(0)+xyz.max(0))/2;extent=max(np.ptp(xyz,axis=0).max(),1e-6)
        for col,yaw in enumerate([0,90,40]):
            a=np.deg2rad(yaw);rot=np.array([[np.cos(a),np.sin(a),0],[-np.sin(a),np.cos(a),0],[0,0,1.]])
            q=(xyz-mid)@rot.T;screen=np.c_[col*500+250+q[:,0]/extent*380,280-q[:,2]/extent*430]
            for face,e in sorted(zip(faces,evidence),key=lambda item:q[list(item[0]),1].mean()):
                poly=[tuple(p) for p in screen[list(face)]];d.polygon(poly,fill='#e6b88f' if not e['all_corners_three_view_consistent'] else '#a3d5af',outline='#5d4b3d',width=1)
            for x,y in screen:d.ellipse((x-1,y-1,x+1,y+1),fill='#7b4f2a')
            d.text((col*500+15,18),f'Actual candidate quad patches | yaw {yaw}°',font=font,fill='black')
    d.text((15,520),f"{len(faces)} shared quads; {sum(e['all_corners_three_view_consistent'] for e in evidence)} pass all-corner 3-view consistency. No hidden surfaces completed.",font=font,fill='black')
    canvas.save(directory/'candidate_patch_mesh_preview.png');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();r=build(a.directory);print(json.dumps({k:v for k,v in r.items() if k!='faces'},indent=2))
