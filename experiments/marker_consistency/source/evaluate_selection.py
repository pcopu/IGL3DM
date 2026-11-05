"""Evaluation-only truth association and heldout diagnostics for any candidate selection."""
import json,sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import summary
from video_tracks import camera_diagnostic,dlt

def evaluate(tracks,gt,period):
    truth=np.asarray(gt['vertices']);trees={};ids={};projections={}
    for view in gt['views']:
        canon={}
        for p in view['observations']:
            if p['visible']:canon.setdefault(tuple(np.round(truth[p['vertex_id']],7)),p)
        vv=list(canon.values());v=view['view'];trees[v]=cKDTree([p['xy'] for p in vv]);ids[v]=[p['vertex_id'] for p in vv];projections[v]=np.asarray(view['projection_3x4'])
    cameras={'projections':{str(k):v.tolist() for k,v in projections.items()},'heldout_sample_indices':[round(period*x/8) for x in (1,3,5,7)],'source':'exact control-only cameras; evaluation only'}
    diagnostics=camera_diagnostic(tracks,cameras);held={r['track']:r for r in diagnostics['tracks']};rows=[]
    for name,t in tracks.items():
        obs=t['observations']
        if len(obs)<3:continue
        mapped=[]
        for o in obs:
            v=o['sample_index'];d,k=trees[v].query(o['xy']);mapped.append((ids[v][k],float(d)))
        reliable=all(d<=3 for v,d in mapped);same=reliable and len({v for v,d in mapped})==1
        status='correct' if same else 'wrong_identity' if reliable else 'unresolved_detection_or_drift';known_error=None
        if same:
            xyz=dlt([(o['sample_index'],o['xy']) for o in obs],projections)
            if xyz is not None:known_error=float(np.linalg.norm(xyz-truth[mapped[0][0]]))
        errors=held.get(name,{}).get('heldout_px',[])
        rows.append({'track_id':name,'samples':len(obs),'span_degrees':(obs[-1]['sample_index']-obs[0]['sample_index'])*360/period,'identity':status,'heldout_errors':errors,'heldout_pass':bool(errors) and max(errors)<=3,'known_3d_error':known_error})
    def summ(rr):
        passed=[r for r in rr if r['heldout_pass']];evaluated=[r for r in rr if r['heldout_errors']];c=Counter(r['identity'] for r in rr)
        return {'tracks':len(rr),'identity':dict(c),'correct_fraction_all':c['correct']/len(rr) if rr else None,'heldout_evaluated':len(evaluated),'heldout_unevaluated':len(rr)-len(evaluated),'heldout_passes':len(passed),'passing_identity':dict(Counter(r['identity'] for r in passed)),'heldout_observation_error_px':summary([e for r in rr for e in r['heldout_errors']]),'correct_3d_error':summary([r['known_3d_error'] for r in rr if r['known_3d_error'] is not None])}
    return {'all_at_least_3':summ(rows),'span_at_least_30':summ([r for r in rows if r['span_degrees']>=30]),'tracks':rows}
