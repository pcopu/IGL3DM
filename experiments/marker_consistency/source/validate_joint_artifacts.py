"""No-truth structural validation of graph/track artifacts."""
from pathlib import Path
import json,sys,hashlib,argparse
import numpy as np

def validate(root, tracker_source=None):
    graph=json.loads((root/'frame_graphs.json').read_text());manifest=json.loads((root/'manifest.json').read_text());out={}
    assert manifest['source_sha256']==hashlib.sha256((Path(tracker_source) if tracker_source else Path(__file__).parent/'graph_tracker.py').read_bytes()).hexdigest()
    for variant in ('graph_joint','graph_joint_cycle_veto'):
        tracks=json.loads((root/variant/'tracks.json').read_text());maps=json.loads((root/variant/'associations.json').read_text());observed=set();nobs=0
        for pair in maps:
            mm=pair['matches'];assert len(mm)==len(set(mm.values()))
        for tid,t in tracks.items():
            obs=t['observations'];ids=[o['sample_index'] for o in obs];assert ids==list(range(ids[0],ids[-1]+1))
            for k,o in enumerate(obs):
                i,node=o['sample_index'],o['node_id'];assert (i,node) not in observed;observed.add((i,node));nobs+=1
                assert np.array_equal(o['xy'],graph[i]['nodes'][node]['xy'])
                if k:assert maps[i-1]['matches'][str(obs[k-1]['node_id'])]==node
        expected=sum(len(g['nodes']) for g in graph);assert nobs==expected
        out[variant]=dict(status='passed',tracks=len(tracks),observations=nobs,checks=['one-to-one pair mappings','one track per detection','contiguous no-gap tracks','exactly redetected node coordinates','all continuation edges present','all detections accounted for','unchanged tracker source hash'])
    (root/'structural_validation.json').write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--tracker-source',type=Path);a=p.parse_args();print(json.dumps(validate(a.root,a.tracker_source),indent=2))
