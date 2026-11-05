from pathlib import Path
import json,sys
import numpy as np
from scipy.spatial import cKDTree
from geometry import summary
from video_tracks import dlt
ROOT=Path(__file__).resolve().parents[1]/'controls/known_pear_64'
gt=json.loads((ROOT/'ground_truth.json').read_text());tracks=json.loads((ROOT/'video_tracks/tracks.json').read_text());manifest=json.loads((ROOT/'video_tracks/video_manifest.json').read_text());P={v['view']:np.array(v['projection_3x4']) for v in gt['views']};truth=np.array(gt['vertices']);trees=[];ids=[]
for view in gt['views']:
 canon={}
 for p in view['observations']:
  if p['visible']:canon.setdefault(tuple(np.round(truth[p['vertex_id']],7)),p)
 vv=list(canon.values());trees.append(cKDTree([p['xy'] for p in vv]));ids.append([p['vertex_id'] for p in vv])
results=[];knownerrors=[];classes={};pass_status={}
held={t['track']:t for t in manifest['geometry']['tracks']}
for name,track in tracks.items():
 obs=track['observations']
 if len(obs)<3:continue
 mapped=[]
 for o in obs:
  v=o['sample_index'];distance,idx=trees[v].query(o['xy']);mapped.append((ids[v][idx],float(distance)))
 reliable=all(d<=3 for vid,d in mapped);same=reliable and len(set(vid for vid,d in mapped))==1
 status='correct' if same else 'wrong_identity' if reliable else 'unresolved_detection_or_drift'
 classes[status]=classes.get(status,0)+1
 err=None
 if same:
  xx=dlt([(o['sample_index'],o['xy']) for o in obs],P)
  if xx is not None:err=float(np.linalg.norm(xx-truth[mapped[0][0]]));knownerrors.append(err)
 diagnostic=held.get(name);passed=diagnostic is not None and max(diagnostic['heldout_px'],default=1e9)<=3
 if passed:pass_status[status]=pass_status.get(status,0)+1
 results.append({'track_id':name,'samples':len(obs),'angular_span_degrees':(obs[-1]['sample_index']-obs[0]['sample_index'])*360/64,'identity_status':status,'known_3d_error':err,'heldout_geometry_pass':passed})
report={'source':'64 genuinely rendered frames of known analytic pear, 5.625deg steps, encoded12fps; not an ImageGen animation and not copied endpoints.',
 'tracks_at_least_3_samples':len(results),'identity_classification':classes,'known_correct_track_3d_error':summary(knownerrors),
 'heldout_3px_pass_track_identity':pass_status,'all_track_heldout_reprojection_px':manifest['geometry']['heldout_reprojection_px'],
 'ground_truth_qualification':'Each observation associated with nearest actually visible known vertex within3px; otherwise unresolved. Known geometry used only to evaluate, never to track.',
 'interpretation':'Small temporal steps may help correspondence, but periodic swaps and drift remain. Passing a reprojection threshold alone is not identity proof.',
 'tracks':results}
(ROOT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='tracks'},indent=2))
