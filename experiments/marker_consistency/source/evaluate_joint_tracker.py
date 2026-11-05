"""Evaluator only. Truth is not imported by or supplied to graph_tracker.py."""
from pathlib import Path
import argparse,json,sys,hashlib
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
from evaluate_selection import evaluate

def coverage(tracks,gt,period,ev):
    truth=np.asarray(gt['vertices']);keys=[tuple(np.round(p,7)) for p in truth]
    trees={};lookups={};visible=set();visible_obs=set()
    for view in gt['views']:
        canon={}
        for p in view['observations']:
            if p['visible']:canon.setdefault(keys[p['vertex_id']],p)
        ps=list(canon.values());v=view['view'];trees[v]=cKDTree([p['xy'] for p in ps]);lookups[v]=[keys[p['vertex_id']] for p in ps]
        visible.update(canon);visible_obs.update((v,k) for k in canon)
    rows={r['track_id']:r for r in ev['tracks']};result={}
    for name,min_span in [('all_at_least_3',0),('span_at_least_30',30)]:
        correct_ids=set();correct_obs=set();covered_obs=set();all_obs=0;all_ids=set();count=0
        for tid,row in rows.items():
            if row['span_degrees']<min_span:continue
            count+=1
            for o in tracks[tid]['observations']:
                all_obs+=1;v=o['sample_index'];d,k=trees[v].query(o['xy']);key=lookups[v][k]
                if d<=3:covered_obs.add((v,key));all_ids.add(key)
                if row['identity']=='correct':correct_ids.add(key);correct_obs.add((v,key))
        result[name]=dict(tracks=count,unique_correct_physical_vertices=len(correct_ids),unique_physical_vertices_with_any_nearby_observation=len(all_ids),correct_track_unique_visible_observations=len(correct_obs),any_track_unique_visible_observations=len(covered_obs),total_track_observations=all_obs,available_unique_visible_physical_vertices=len(visible),available_unique_visible_observations=len(visible_obs),correct_vertex_coverage=len(correct_ids)/len(visible),correct_observation_coverage=len(correct_obs)/len(visible_obs))
    return result

def main(root,gt_path,period):
    gt=json.loads(gt_path.read_text());summary={}
    for variant in ('graph_joint','graph_joint_cycle_veto'):
        p=root/variant/'tracks.json';tracks=json.loads(p.read_text());ev=evaluate(tracks,gt,period);ev['coverage']=coverage(tracks,gt,period,ev)
        ev['track_source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();ev['truth_evaluation_only']=True
        (root/variant/'evaluation.json').write_text(json.dumps(ev,indent=2));summary[variant]={k:v for k,v in ev.items() if k!='tracks'}
    (root/'evaluation_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--truth',type=Path,required=True);p.add_argument('--period',type=int,required=True);a=p.parse_args();main(a.root,a.truth,a.period)
