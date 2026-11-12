"""Evaluation-only decomposition of frozen periodic-identity failures.

No observation/model selection or modification. Truth IDs are scorer-canonical IDs.
Run with existing python_deps on PYTHONPATH. Input files remain unchanged.
"""
import argparse, collections, hashlib, json
from pathlib import Path
import numpy as np

def stats(values):
    return {'n':len(values),'median':float(np.median(values)), 'p95':float(np.percentile(values,95)), 'min':float(min(values)), 'max':float(max(values))} if values else {'n':0}

def diagnose(base):
    truths={'orbit':base.parent/'source/experiments/marker_consistency/controls/known_pear_96/ground_truth.json', 'bent':base/'independent_bent_ovoid96/ground_truth.json', 'barrel':base/'independent_squat_barrel96/ground_truth.json'}
    result={'evaluation_only':True, 'methodology':{'dominant_identity':'Most common resolved physical ID; ties follow observation order.', 'majority_endpoint_contamination':'Wrong identity, dominant fraction > 0.5, all minority resolved observations strictly outside dominant observation interval, dominant ID nearest inferred XYZ.', 'coherent_ring_walk':'Wrong identity without a majority, with all resolved observations distinct. Name is a diagnostic description, not proof of ring topology.', 'truth_boundary':'Truth is used only to classify frozen outputs, never select or repair them.', 'coordinate_units':'Native control geometry units.', 'limitations':['Unresolved observations are not assigned identities.', 'Dominant error is not meaningful as a unique target error when there is no majority.', 'These controls are development evidence after diagnosis.', 'Adjacency improvement is proposed, not evaluated here.']},'controls':{}}
    for name,tp in truths.items():
        root=base/f'recovery_{name}_hypotheses48_resolvable'; pp=root/'candidate_points.json'; ep=root/'physical_identity_evaluation.json'
        points=json.loads(pp.read_text()); evaluation=json.loads(ep.read_text()); truth=json.loads(tp.read_text()); vertices=[]; seen=set()
        for vertex in truth['vertices']:
            key=tuple(np.round(vertex,7))
            if key not in seen: seen.add(key); vertices.append(vertex)
        vertices=np.asarray(vertices); rows=[]
        assert len(points)==len(evaluation['point_rows'])
        for point,row in zip(points,evaluation['point_rows']):
            assert point['track_id']==row['track_id']
            observations=row['observation_identity']; resolved=[o for o in observations if o['physical_id'] is not None]
            counts=collections.Counter(o['physical_id'] for o in resolved)
            dominant,n=counts.most_common(1)[0] if counts else (None,0)
            fraction=n/len(resolved) if resolved else None
            dominant_frames=[o['sample_index'] for o in resolved if o['physical_id']==dominant]
            minority=[o for o in resolved if o['physical_id']!=dominant]
            outside=bool(minority) and all(o['sample_index']<min(dominant_frames) or o['sample_index']>max(dominant_frames) for o in minority)
            distances=np.linalg.norm(vertices-np.asarray(point['xyz']),axis=1); nearest=int(np.argmin(distances))
            calids={o['physical_id'] for o in resolved if o['sample_index']%5!=4}
            wrong=row['identity']=='wrong_identity'; category=row['identity']
            if wrong:
                category='majority_endpoint_contamination' if fraction>.5 and outside and nearest==dominant else 'coherent_ring_walk' if fraction<=.5 and len(counts)==len(resolved) else 'other_wrong_identity'
            rows.append({'track_id':point['track_id'],'point_index':row['point_index'],'identity':row['identity'],'diagnostic_class':category,'dominant_id':dominant,'dominant_fraction_resolved':fraction,'resolved_distinct_ids':sorted(counts),'resolved_observations':len(resolved),'unresolved_observations':row['unresolved_observations'],'dominant_frame_interval':[min(dominant_frames),max(dominant_frames)] if dominant_frames else None,'minority_frames':[o['sample_index'] for o in minority],'all_minorities_outside_dominant_interval':outside,'all_resolved_ids_distinct':len(counts)==len(resolved),'calibration_distinct_ids':len(calids),'wrong_only_after_heldout_added':wrong and len(calids)<=1,'nearest_truth_vertex':nearest,'dominant_is_nearest_xyz':dominant==nearest,'dominant_xyz_error':float(distances[dominant]) if dominant is not None else None,'nearest_truth_xyz_error':float(distances[nearest]),'train_p95_px':point['training_reprojection_px']['p95'],'sample_span':point['sample_span'],'xyz':point['xyz'],'observation_identity':observations})
        groups={category:[r for r in rows if r['diagnostic_class']==category] for category in sorted({r['diagnostic_class'] for r in rows})}
        summary={'point_identity_counts':evaluation['point_identity_counts'],'diagnostic_class_counts':{k:len(v) for k,v in groups.items()},'wrong_only_after_heldout_added':sum(r['wrong_only_after_heldout_added'] for r in rows),'class_metrics':{k:{'dominant_xyz_error':stats([r['dominant_xyz_error'] for r in v if r['dominant_xyz_error'] is not None]),'nearest_truth_xyz_error':stats([r['nearest_truth_xyz_error'] for r in v]),'train_p95_px':stats([r['train_p95_px'] for r in v])} for k,v in groups.items()},'face_identity_counts':evaluation['face_identity_counts'],'source_cell_identity_counts':evaluation['source_cell_identity_counts']}
        result['controls'][name]={'input_sha256':{str(p.relative_to(base.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [tp,pp,ep]},'summary':summary,'point_rows':rows}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--base',type=Path,required=True); p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    if args.output.exists(): raise ValueError('Refusing existing diagnostic output')
    report=diagnose(args.base.resolve()); args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v['summary'] for k,v in report['controls'].items()},indent=2))
