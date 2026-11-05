"""One pre-specified classical model: 5 log-speed knots, constant tilt/roll/frame.
No truth, shape, learned models, or period-filtered correspondences are read.
Yaw is the integral of PCHIP-interpolated log speed, so speed is positive and
bounded everywhere. Weak log-speed difference penalties are fixed at 1 px.
The caller supplies a fresh output file. Point positions are nuisance
least-squares estimates, not a reconstructed or published shape.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import least_squares
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import fit_shared_orbit as constant

N_KNOTS=5
PENALTY_SCALE=1.0
INTEGRATION_STEPS_PER_FRAME=32


def yaw(samples, params, domain):
    lo,hi=domain
    knots=np.linspace(lo,hi,N_KNOTS)
    grid=np.linspace(lo,hi,int(np.ceil((hi-lo)*INTEGRATION_STEPS_PER_FRAME))+1)
    log_speed=PchipInterpolator(knots,params[:N_KNOTS])(grid)
    integral=cumulative_trapezoid(np.exp(log_speed),grid,initial=0)
    return np.interp(samples,grid,integral)


def design(samples,params,domain):
    theta=yaw(samples,params,domain)
    elev,roll,cx=params[N_KNOTS:]
    c=np.cos(theta); s=np.sin(theta)
    right=np.c_[c,s,np.zeros_like(c)]
    up=np.c_[-s*np.sin(elev),c*np.sin(elev),np.full_like(c,np.cos(elev))]
    rr=right*np.cos(roll)+up*np.sin(roll)
    uu=-right*np.sin(roll)+up*np.cos(roll)
    return 256*np.stack([rr,-uu],axis=1),np.array([cx,256.])


def fit_point(time,xy,params,domain,mask=None):
    A,b=design(time,params,domain)
    mask=np.ones(len(time),bool) if mask is None else mask
    xyz,_,rank,s=np.linalg.lstsq(A[mask].reshape(-1,3),(xy[mask]-b).ravel(),rcond=None)
    condition=float(s[0]/s[-1]) if s[-1]>1e-12 else float('inf')
    pred=np.einsum('nij,j->ni',A,xyz)+b
    return pred,int(rank),condition


def validation(data,params,domain,baseline):
    rows=[]; obs=[]
    for name,(time,xy) in data.items():
        if len(time)<9 or time[-1]<=time[0]:continue
        fraction=(time-time[0])/(time[-1]-time[0])
        train=(fraction>=.25)&(fraction<=.75); test=~train
        if train.sum()<4:continue
        pred,rank,condition=fit_point(time,xy,params,domain,train)
        _,basepred,baserank,basecondition=constant.fit_point(time,xy,baseline,train)
        err=np.linalg.norm(pred-xy,axis=1); baseerr=np.linalg.norm(basepred-xy,axis=1)
        row={'track_id':name,'samples':len(time),'training_samples':int(train.sum()),'heldout_samples':int(test.sum()),'yaw_span_deg':float(np.rad2deg(np.diff(yaw([time[0],time[-1]],params,domain)))[0]),'rank':rank,'condition':condition,'constant_condition':basecondition,'constant_rank':int(baserank),'variable_training_p95_px':float(np.percentile(err[train],95)),'constant_training_p95_px':float(np.percentile(baseerr[train],95)),'variable_endpoint_median_px':float(np.median(err[test])),'constant_endpoint_median_px':float(np.median(baseerr[test])),'variable_endpoint_p95_px':float(np.percentile(err[test],95)),'constant_endpoint_p95_px':float(np.percentile(baseerr[test],95))}
        row['variable_conditional_pass_1px']=bool(rank==3 and condition<=20 and row['variable_training_p95_px']<=1 and row['variable_endpoint_p95_px']<=1)
        row['constant_conditional_pass_1px']=bool(baserank==3 and basecondition<=20 and row['constant_training_p95_px']<=1 and row['constant_endpoint_p95_px']<=1)
        rows.append(row)
        for t,b,v in zip(time[test],baseerr[test],err[test]):
            obs.append({'track_id':name,'sample_index':int(t),'constant_error_px':float(b),'variable_error_px':float(v)})
    return {'track_count':len(rows),'endpoint_observation_count':len(obs),'constant_endpoint_errors_px':constant.summary([o['constant_error_px'] for o in obs]),'variable_endpoint_errors_px':constant.summary([o['variable_error_px'] for o in obs]),'paired_error_change_px':constant.summary([o['variable_error_px']-o['constant_error_px'] for o in obs]),'fraction_observations_improved':float(np.mean([o['variable_error_px']<o['constant_error_px'] for o in obs])) if obs else None,'fraction_tracks_median_improved':float(np.mean([r['variable_endpoint_median_px']<r['constant_endpoint_median_px'] for r in rows])) if rows else None,'constant_conditional_pass_1px':sum(r['constant_conditional_pass_1px'] for r in rows),'variable_conditional_pass_1px':sum(r['variable_conditional_pass_1px'] for r in rows),'constant_condition':constant.summary([r['constant_condition'] for r in rows]),'variable_condition':constant.summary([r['condition'] for r in rows]),'tracks':rows,'paired_observations':obs}


def pack(params,domain):
    frames=np.arange(int(domain[0]),int(domain[1])+1)
    angles=yaw(frames,params,domain)
    return {'log_speed_knots':params[:N_KNOTS].tolist(),'knot_samples':np.linspace(*domain,N_KNOTS).tolist(),'knot_speed_deg_per_frame':np.rad2deg(np.exp(params[:N_KNOTS])).tolist(),'mean_equivalent_period_frames':float((domain[1]-domain[0])*2*np.pi/(angles[-1]-angles[0])),'elevation_deg':float(np.rad2deg(params[N_KNOTS])),'roll_deg':float(np.rad2deg(params[N_KNOTS+1])),'horizontal_center_px':float(params[N_KNOTS+2]),'vertical_center_px':256,'scale_px_per_unit':256,'yaw_samples':frames.tolist(),'yaw_deg':np.rad2deg(angles).tolist()}


def fit(tracks,manifest,baseline_report):
    data=constant.normalized(tracks,manifest['working_size'])
    eligible={n:v for n,v in data.items() if len(v[0])>=16}
    training={n:v for n,v in eligible.items() if int(hashlib.sha256(n.encode()).hexdigest()[:8],16)%5!=0}
    heldout={n:v for n,v in eligible.items() if n not in training}
    assert sorted(training)==baseline_report['calibration_track_ids']
    assert sorted(heldout)==baseline_report['validation_track_ids']
    domain=(float(min(f['sample_index'] for f in manifest['frames'])),float(max(f['sample_index'] for f in manifest['frames'])))
    base=np.array(baseline_report['parameter_vector'])
    x0=np.r_[np.full(N_KNOTS,np.log(2*np.pi)-base[0]),base[1:]]
    low=np.r_[np.full(N_KNOTS,np.log(2*np.pi/192)),np.deg2rad(-30),np.deg2rad(-12),224]
    high=np.r_[np.full(N_KNOTS,np.log(2*np.pi/64)),np.deg2rad(30),np.deg2rad(12),288]
    # Precomputed designs per frame avoid repeated interpolation by identity.
    frames=np.arange(int(domain[0]),int(domain[1])+1)
    packed=[(time.astype(int)-int(domain[0]),xy) for time,xy in training.values()]
    def data_residual(params):
        A,b=design(frames,params,domain); residual=[]
        for idx,xy in packed:
            Ai=A[idx]
            xyz=np.linalg.lstsq(Ai.reshape(-1,3),(xy-b).ravel(),rcond=None)[0]
            residual.append((np.einsum('nij,j->ni',Ai,xyz)+b-xy).ravel())
        return np.concatenate(residual)
    def objective(params):
        return np.r_[data_residual(params),PENALTY_SCALE*np.diff(params[:N_KNOTS])]
    before=data_residual(x0)
    r=least_squares(objective,x0,bounds=(low,high),loss='soft_l1',f_scale=1,max_nfev=200,ftol=1e-8,xtol=1e-8,gtol=1e-8)
    params=r.x
    jac_steps=np.r_[np.full(N_KNOTS,.1),np.deg2rad(10),np.deg2rad(5),10]
    singular=np.linalg.svd(r.jac*jac_steps,compute_uv=False)
    # Compare the nested constant form exactly, before fitting flexible camera.
    exact=max(float(np.max(np.abs(fit_point(t,xy,x0,domain)[0]-constant.fit_point(t,xy,base)[1]))) for t,xy in data.values())
    assert exact<1e-7,exact
    report={'model':'Five PCHIP log-speed knots integrated to monotone yaw; 8 camera parameters total','knots_fixed_in_advance':N_KNOTS,'domain_samples':domain,'optimizer_success':bool(r.success),'optimizer_message':r.message,'nfev':r.nfev,'optimizer_cost':float(r.cost),'optimizer_optimality':float(r.optimality),'initial_parameter_vector':x0.tolist(),'parameter_vector':params.tolist(),'camera':pack(params,domain),'constant_camera':baseline_report['estimated_camera'],'fit_input_truth_or_shape':False,'minimum_calibration_samples':16,'calibration_track_count':len(training),'validation_track_count':len(heldout),'calibration_track_ids':sorted(training),'validation_track_ids':sorted(heldout),'calibration_before_px':constant.summary(np.linalg.norm(before.reshape(-1,2),axis=1)),'calibration_after_px':constant.summary(np.linalg.norm(data_residual(params).reshape(-1,2),axis=1)),'validation':validation(heldout,params,domain,base),'all_tracks_conditional':validation(data,params,domain,base),'bounds':{'knot_speed_deg_per_frame':[360/192,360/64],'elevation_deg':[-30,30],'roll_deg':[-12,12],'horizontal_center_px':[224,288],'active_mask':r.active_mask.tolist(),'minimum_fractional_distance_to_bound':float(np.min(np.minimum(params-low,high-params)/(high-low)))},'regularization':{'form':'1 px * adjacent difference of log knot speeds','penalty_scale_px':PENALTY_SCALE,'penalty_values':(PENALTY_SCALE*np.diff(params[:N_KNOTS])).tolist(),'not_tuned_on_heldout':True},'scaled_robust_jacobian_singular_values':singular.tolist(),'scaled_robust_jacobian_condition':float(singular[0]/singular[-1]),'jacobian_parameter_scaling':jac_steps.tolist(),'nested_constant_prediction_max_abs_difference_px':exact,'integration_steps_per_frame':INTEGRATION_STEPS_PER_FRAME,'calibration_temporal_bins':np.histogram(np.concatenate([v[0] for v in training.values()]),bins=np.linspace(*domain,5))[0].tolist(),'holdout':'Same deterministic sha256(track ID) % 5 == 0 identity holdout as constant baseline. All min16 eligible IDs kept. Fit each held-out point only on middle half of its temporal span; evaluate its endpoint quarters. Graph selection still uses all frames.','limitations':['Fixed orthographic camera scale and vertical-center gauges; yaw phase is fixed to zero at start.','Track identities remain unverified. Segment-level split can share source tracks across train/holdout.','Five speed knots may absorb systematic tracking error or perspective; heldout graph selection is not independent of calibration image processing.','PCHIP log speed is C1 and integrated yaw is C2; numerical trapezoid evaluation is used.','No camera or geometry is accepted from this experiment alone.']}
    return report


def main():
    p=argparse.ArgumentParser(); p.add_argument('--tracks',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Refusing existing output')
    report=fit(json.loads(a.tracks.read_text()),json.loads(a.manifest.read_text()),json.loads(a.baseline.read_text()))
    report['input_paths']={'tracks':str(a.tracks.resolve()),'manifest':str(a.manifest.resolve()),'baseline':str(a.baseline.resolve())}
    a.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['optimizer_success','nfev','camera','calibration_track_count','validation_track_count','calibration_before_px','calibration_after_px','bounds','scaled_robust_jacobian_condition']},indent=2))
    print('PAIRED VALIDATION',json.dumps({k:v for k,v in report['validation'].items() if k not in ['tracks','paired_observations']},indent=2))
if __name__=='__main__':main()
