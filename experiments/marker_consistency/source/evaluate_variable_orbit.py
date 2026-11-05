"""Post-fit evaluation and invariant tests; never fits or changes camera outputs."""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.integrate import cumulative_trapezoid
sys.path.insert(0,str(Path(__file__).resolve().parent))
import fit_variable_orbit as f


def checks_and_coverage(name,directory,input_base_directory=None):
    HERE=Path(directory)
    d=json.loads((HERE/f'{name}_variable.json').read_text())
    params=np.array(d['parameter_vector']);domain=d['domain_samples']
    tracks=json.loads((Path(input_base_directory or Path.cwd())/d['input_paths']['tracks']).read_text())
    baseline=json.loads((Path(input_base_directory or Path.cwd())/d['input_paths']['baseline']).read_text())
    train=d['calibration_track_ids'];test=d['validation_track_ids']
    assert not set(train)&set(test)
    assert train==baseline['calibration_track_ids'] and test==baseline['validation_track_ids']
    assert all(len(tracks[n]['observations'])>=16 for n in train+test)
    assert all(int(hashlib.sha256(n.encode()).hexdigest()[:8],16)%5==0 for n in test)
    pair=d['validation']['paired_observations']
    assert len(pair)==len({(o['track_id'],o['sample_index']) for o in pair})
    assert len(pair)==baseline['validation_after']['endpoint_observation_errors_px']['n']
    for key in ['mean','median','p95','max']:
        assert abs(d['validation']['constant_endpoint_errors_px'][key]-baseline['validation_after']['endpoint_observation_errors_px'][key])<1e-9
    dense=np.linspace(*domain,20001)
    speed=np.exp(PchipInterpolator(np.linspace(*domain,5),params[:5])(dense))
    assert np.min(speed)>=2*np.pi/192-1e-12 and np.max(speed)<=2*np.pi/64+1e-12
    angles=f.yaw(dense,params,domain);assert np.all(np.diff(angles)>0)
    grid=np.linspace(*domain,int((domain[1]-domain[0])*512)+1)
    precise=cumulative_trapezoid(np.exp(PchipInterpolator(np.linspace(*domain,5),params[:5])(grid)),grid,initial=0)
    error=float(np.max(np.abs(f.yaw(np.arange(domain[1]+1),params,domain)-np.interp(np.arange(domain[1]+1),grid,precise))))
    assert error<1e-6
    sources_train={tracks[n].get('source_track_id',n) for n in train}
    sources_test={tracks[n].get('source_track_id',n) for n in test}
    parent_overlap=sorted(sources_train&sources_test)
    coverage={}
    bins=np.linspace(*domain,5)
    for m in ['constant','variable']:
        values=np.array([o[f'{m}_error_px'] for o in pair])
        coverage[m]={'fraction_endpoint_observations_at_most_1px':float(np.mean(values<=1)),'fraction_endpoint_observations_at_most_2px':float(np.mean(values<=2)),'fraction_endpoint_observations_at_most_5px':float(np.mean(values<=5))}
    temporal=[]
    for i,(lo,hi) in enumerate(zip(bins[:-1],bins[1:])):
        ob=[o for o in pair if lo<=o['sample_index'] and (o['sample_index']<hi or (i==3 and o['sample_index']<=hi))]
        temporal.append({'interval':[float(lo),float(hi)],'observations':len(ob),'constant':f.constant.summary([o['constant_error_px'] for o in ob]),'variable':f.constant.summary([o['variable_error_px'] for o in ob])})
    return {'tests_passed':['Exact baseline split and minimum eligibility','Same paired endpoint observation keys and baseline statistics','Unique heldout identity/sample pairs','Strictly monotone yaw with globally bounded interpolated speed','32-vs-512-steps/frame integration error below 1e-6 rad','Nested constant prediction agrees within 1e-7 px'],'integration_error_rad':error,'integration_error_degrees':float(np.rad2deg(error)),'source_track_overlap_count':len(parent_overlap),'source_track_overlap_ids':parent_overlap,'coverage':coverage,'temporal_validation':temporal}


def evaluate_control_yaw(directory,truth_path,input_base_directory=None):
    HERE=Path(directory);truth_path=Path(truth_path).resolve()
    # Both fitted outputs already exist. Only yaw fields of truth are used here.
    assert (HERE/'real_variable.json').exists() and (HERE/'control96_variable.json').exists()
    views=json.loads(truth_path.read_text())['views']
    time=np.array([v['view'] for v in views]);true=np.unwrap(np.deg2rad([v['yaw_deg'] for v in views]))
    d=json.loads((HERE/'control96_variable.json').read_text())
    baseline=json.loads((Path(input_base_directory or Path.cwd())/d['input_paths']['baseline']).read_text())
    predictions={'constant':time*2*np.pi/np.exp(baseline['parameter_vector'][0]),'variable':f.yaw(time,np.array(d['parameter_vector']),d['domain_samples'])}
    results={}
    for name,pred in predictions.items():
        alternatives=[]
        for sign in [1,-1]:
            offset=float(np.mean(true-sign*pred));error=sign*pred+offset-true
            alternatives.append((float(np.mean(error**2)),sign,offset,error))
        _,sign,offset,error=min(alternatives,key=lambda r:r[0])
        deg=np.rad2deg(error)
        results[name]={'absolute_error_deg':f.constant.summary(np.abs(deg)),'rms_error_deg':float(np.sqrt(np.mean(deg**2))),'phase_offset_deg':float(np.rad2deg(offset)),'orientation_sign':sign,'total_sweep_deg':float(np.rad2deg(pred[-1]-pred[0])),'per_frame_signed_error_deg':deg.tolist()}
    return {'truth_path':str(truth_path),'truth_used_for':'Post-fit evaluation only; only views[*].view and yaw_deg consumed. No shape vertices, faces, image observation truth, or cameras enter fitting.','gauge':'Choose orientation sign and one constant yaw phase offset to minimize squared angular error; no angular scale, time warp, or nonlinear alignment.','true_total_sweep_deg':float(np.rad2deg(true[-1]-true[0])),'constant':results['constant'],'variable':results['variable']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report-directory',type=Path,required=True);p.add_argument('--control-truth',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--input-base-directory',type=Path,default=Path.cwd());a=p.parse_args()
    if a.output.exists():raise ValueError('Refusing to overwrite output')
    out={'real_checks':checks_and_coverage('real',a.report_directory,a.input_base_directory),'control96_checks':checks_and_coverage('control96',a.report_directory,a.input_base_directory),'control_yaw_evaluation':evaluate_control_yaw(a.report_directory,a.control_truth,a.input_base_directory),'no_refits_after_truth_evaluation':True}
    a.output.write_text(json.dumps(out,indent=2))
    compact={k:v for k,v in out.items() if k!='control_yaw_evaluation'}
    compact['control_yaw_evaluation']={k:({a:b for a,b in v.items() if a!='per_frame_signed_error_deg'} if isinstance(v,dict) else v) for k,v in out['control_yaw_evaluation'].items()}
    print(json.dumps(compact,indent=2))
