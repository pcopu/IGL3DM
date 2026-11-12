"""Diagnose observed topology contradictions and quarantine, never infer missing faces."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,json,hashlib
import numpy as np

def audit(points,faces):
 edges=defaultdict(list)
 for fi,f in enumerate(faces):
  ids=f['point_indices']
  if len(ids)!=4 or len(set(ids))!=4:raise ValueError('Expected four distinct corners')
  for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))].append(fi)
 conflicts=[];remove=set()
 for edge,ff in edges.items():
  if len(ff)<=2:continue
  remove.update(ff);frames={fi:{int(o.get('sample_index',o.get('sample'))) for o in faces[fi]['source_cells']} for fi in ff};count=Counter(i for s in frames.values() for i in s);details=[]
  for fi in ff:
   f=faces[fi];xyz=np.array([points[i]['xyz'] for i in f['point_indices']]);normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]);length=np.linalg.norm(normal)
   details.append({'face_index':fi,'point_indices':f['point_indices'],'track_ids':[points[i].get('track_id') for i in f['point_indices']],'observed_frames':sorted(frames[fi]),'normal_unoriented':(normal/length).tolist() if length>1e-12 else None})
  conflicts.append({'edge':list(edge),'incident_faces':details,'frames_with_at_least_three_incident_cells':sorted(i for i,c in count.items() if c>=3),'frames_with_two_incident_cells':sorted(i for i,c in count.items() if c==2),'all_incident_faces_coobserved':sorted(set.intersection(*frames.values()))})
 retained=[f for i,f in enumerate(faces) if i not in remove]
 def metrics(fs):
  e=Counter();adj=defaultdict(set);used=set()
  for f in fs:
   ids=f['point_indices'];used.update(ids)
   for a,b in zip(ids,ids[1:]+ids[:1]):e[tuple(sorted((a,b)))]+=1;adj[a].add(b);adj[b].add(a)
  seen=set();sizes=[]
  for start in sorted(used):
   if start in seen:continue
   todo=[start];seen.add(start);size=0
   while todo:
    a=todo.pop();size+=1
    for b in adj[a]-seen:seen.add(b);todo.append(b)
   sizes.append(size)
  return {'faces':len(fs),'used_vertices':len(used),'isolated_vertices':len(points)-len(used),'boundary_edges':sum(v==1 for v in e.values()),'nonmanifold_edges':sum(v>2 for v in e.values()),'surface_components':len(sizes),'component_vertices':sorted(sizes,reverse=True)}
 report={'before':metrics(faces),'after_quarantine':metrics(retained),'policy':'Quarantine every face incident to an edge of multiplicity greater than two; never choose a winner or alter points.','removed_face_indices':sorted(remove),'conflicts':conflicts,'limitations':['Edge multiplicity rejection does not validate physical identities.','Bow-tie vertices, winding, self intersections and overlapping duplicate fragments may remain.','Original observations and original output are preserved.']}
 return report,retained

def run(points_path,faces_path,out):
 if out.exists():raise ValueError('Refusing existing output')
 points=json.loads(points_path.read_text());faces=json.loads(faces_path.read_text());r,retained=audit(points,faces);out.mkdir(parents=True);r['input_sha256']={'points':hashlib.sha256(points_path.read_bytes()).hexdigest(),'faces':hashlib.sha256(faces_path.read_bytes()).hexdigest()};(out/'audit.json').write_text(json.dumps(r,indent=2));(out/'candidate_points.json').write_bytes(points_path.read_bytes());(out/'candidate_faces.json').write_text(json.dumps(retained,indent=2))
 with (out/'quarantined_cells.ply').open('w') as f:
  f.write(f'ply\nformat ascii 1.0\ncomment Observed cells after contradiction quarantine, not validated physical topology\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(retained)}\nproperty list uchar int vertex_indices\nend_header\n')
  for p in points:f.write(' '.join(map(str,p['xyz']))+'\n')
  for p in retained:f.write('4 '+' '.join(map(str,p['point_indices']))+'\n')
 print(json.dumps({k:v for k,v in r.items() if k!='conflicts'},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['points','faces','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();run(a.points,a.faces,a.output)
