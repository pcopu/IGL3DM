"""Package already-fitted camera matrices and exploratory selections; no fit."""
from pathlib import Path
import argparse,json,sys,hashlib
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import fit_variable_orbit as f

def package(report_directory,control_validation,output_directory,input_base_directory=None):
    INPUT=Path(report_directory);HERE=Path(output_directory)
    if HERE.exists():raise ValueError('Refusing an existing output directory')
    HERE.mkdir(parents=True)
    out={}
    for name in ['real','control96']:
        report=json.loads((INPUT/f'{name}_variable.json').read_text())
        p=np.array(report['parameter_vector']);domain=report['domain_samples']
        samples=np.array(report['camera']['yaw_samples'])
        A,b=f.design(samples,p,domain)
        matrices=[]
        for t,a,y in zip(samples,A,report['camera']['yaw_deg']):
            right=a[0]/256;up=-a[1]/256;depth=np.cross(right,up)
            orientation=np.stack([right,up,depth])
            assert np.allclose(orientation@orientation.T,np.eye(3),atol=1e-12)
            matrices.append({'sample_index':int(t),'yaw_deg':y,'orthographic_projection_2x4_normalized512':np.c_[a,b].tolist(),'orientation_world_to_camera_3x3':orientation.tolist()})
        (HERE/f'{name}_camera_matrices.json').write_text(json.dumps({'status':'Experimental camera only, not accepted calibration','parameter_vector':p.tolist(),'camera':report['camera'],'coordinates':'Projection maps nuisance world coordinates to 512-high centered/padded image pixels. Orientation rows are image-right, image-up, and their cross product. No metric camera location or depth translation is identified.','views':matrices},indent=2))
        rows=report['all_tracks_conditional']['tracks']
        sets={}
        baseperiod=report['constant_camera']['period_frames']
        tracks=json.loads((Path(input_base_directory or Path.cwd())/report['input_paths']['tracks']).read_text())
        for model in ['constant','variable']:
            def span(r):
                if model=='variable':return r['yaw_span_deg']
                times=[o['sample_index'] for o in tracks[r['track_id']]['observations']]
                return (max(times)-min(times))*360/baseperiod
            selected=[r for r in rows if r[f'{model}_conditional_pass_1px'] and span(r)>=30]
            sets[model]=set(r['track_id'] for r in selected)
            out.setdefault(name,{})[model]={'selected_count':len(selected),'selected_with_at_least_16_samples':sum(r['samples']>=16 for r in selected),'selected_candidate_track_ids':sorted(sets[model])}
        out[name]['variable_added_ids']=sorted(sets['variable']-sets['constant'])
        out[name]['variable_removed_ids']=sorted(sets['constant']-sets['variable'])
        out[name]['gate']='All graph-only candidates with at least 9 samples and at least 4 middle-half samples: rank=3, point condition<=20, middle-half training p95<=1px, endpoint quarters p95<=1px, fitted yaw span>=30deg. Calibration min16 eligibility does not restrict this exploratory all-candidate gate. No verification of physical identity.'
        out[name]['min16_only_available_separately']=True
        if name=='control96':
            artifact=Path(control_validation).resolve()
            val=json.loads(artifact.read_text())
            identity={r['track_id']:r['identity'] for r in val['tracks']}
            assert set(identity)==set(tracks)
            out[name]['physical_identity_evaluation_source']=str(artifact)
            out[name]['physical_identity_evaluation_method']='Reuse precomputed existing evaluate_selection.py results on these identical graph-only IDs: all observations nearest visible truth vertex within 3px and same physical vertex => correct; all reliable but varying vertex => wrong_identity; otherwise unresolved_detection_or_drift. No refit or new geometry computed.'
            for model in ['constant','variable']:
                out[name][model]['identity_counts']=dict(Counter(identity[n] for n in sets[model]))
                out[name][model]['min16_identity_counts']=dict(Counter(identity[n] for n in sets[model] if len(tracks[n]['observations'])>=16))
            out[name]['added_identity_counts']=dict(Counter(identity[n] for n in out[name]['variable_added_ids']))
            out[name]['removed_identity_counts']=dict(Counter(identity[n] for n in out[name]['variable_removed_ids']))
            out[name]['known_wrong_selected_ids']={m:sorted(n for n in sets[m] if identity[n]=='wrong_identity') for m in ['constant','variable']}

    (HERE/'conditional_selection.json').write_text(json.dumps(out,indent=2))
    compact={name:{k:({a:b for a,b in v.items() if a!='selected_candidate_track_ids'} if isinstance(v,dict) else v) for k,v in dataset.items() if k not in ['variable_added_ids','variable_removed_ids']} for name,dataset in out.items()}
    return compact

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report-directory',type=Path,required=True);p.add_argument('--control-validation',type=Path,required=True);p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--input-base-directory',type=Path,default=Path.cwd());a=p.parse_args();print(json.dumps(package(a.report_directory,a.control_validation,a.output_directory,a.input_base_directory),indent=2))
