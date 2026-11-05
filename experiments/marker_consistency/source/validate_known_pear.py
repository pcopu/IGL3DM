from pathlib import Path
import json
import numpy as np
from scipy.spatial import cKDTree
from geometry import summary
ROOT=Path(__file__).resolve().parents[1]/'controls/known_pear'
gt=json.loads((ROOT/'ground_truth.json').read_text());nodes=json.loads((ROOT/'quad_cells/quad_graph.json').read_text());tracks=json.loads((ROOT/'quad_cells/candidate_vertices.json').read_text())
vertices=np.array(gt['vertices']);trees=[];vids=[];lookup={};coverage=[]
for v,view in enumerate(gt['views']):
 visible=[p for p in view['observations'] if p['visible'] and 8<p['xy'][0]<504 and 8<p['xy'][1]<504]
 # Pole duplicates are geometrically identical; canonicalize by 3D coordinate.
 canonical={}
 for p in visible:canonical.setdefault(tuple(np.round(vertices[p['vertex_id']],7)),p)
 visible=list(canonical.values());ids=[p['vertex_id'] for p in visible];p=np.array([p['xy'] for p in visible]);tree=cKDTree(p);trees.append(tree);vids.append(ids)
 detected=np.array([n['xy'] for n in nodes[v]['nodes']]);d,ii=tree.query(detected)
 for n,dist,i in zip(nodes[v]['nodes'],d,ii):lookup[v,n['node_id']]={'nearest_true_vertex':ids[i],'distance_px':float(dist),'within_3px':bool(dist<=3)}
 nearest_detected=cKDTree(detected).query(p)[0]
 coverage.append({'view':v,'visible_canonical_ground_truth_vertices':len(ids),'detected_nodes':len(detected),'ground_truth_vertices_with_detection_within_3px':int((nearest_detected<=3).sum()),'detected_nodes_near_ground_truth':int((d<=3).sum())})
results=[];correct=0;wrong=0;unresolved=0;errors=[]
for t in tracks:
 mapped=[lookup[v,n] for v,n in t['view_node_ids']];valid=all(x['within_3px'] for x in mapped);same=valid and len({x['nearest_true_vertex'] for x in mapped})==1
 status='correct' if same else 'wrong_identity' if valid else 'unresolved_detection'
 correct+=same;wrong+=status=='wrong_identity';unresolved+=status=='unresolved_detection'
 e=None
 if same:
  # Script fixed scale256; actual scale160. Convert candidate gauge to known world units.
  true=vertices[mapped[0]['nearest_true_vertex']];e=float(np.linalg.norm(np.asarray(t['xyz'])*256/160-true));errors.append(e)
 results.append({'track_id':t['track_id'],'views':list(t['observations']),'status':status,'nearest_truth':mapped,'known_3d_error':e})
report={'control':'Rendered analytic asymmetric pear, independent from generated input; exact cameras and surface known.',
 'coverage':coverage,'tracks_total':len(tracks),'correct_identity_tracks':int(correct),'wrong_identity_tracks':int(wrong),'unresolved_detection_tracks':int(unresolved),
 'correct_track_3d_error':summary(errors),'track_truth_checks':results,
 'interpretation':'This measures the entire cell/context matcher, not just triangulation. False matches on a true consistent render cannot be blamed on image generation. Three-pixel nearest-vertex association is an evaluation tolerance, not a decoder guarantee.'}
(ROOT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='track_truth_checks'},indent=2))
