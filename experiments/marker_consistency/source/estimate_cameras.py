"""Classical robust orthographic bundle adjustment with explicit camera priors/gauge.

No learned depth or 3D model. Intrinsics mean effective orthographic image scale;
focal length and camera distance cannot be separately recovered in this model.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from geometry import summary


def matrix(params):
    yaw,elev,roll,logscale,tx,ty=params
    right=np.array([np.cos(yaw),np.sin(yaw),0.]);up=np.array([-np.sin(yaw)*np.sin(elev),np.cos(yaw)*np.sin(elev),np.cos(elev)])
    rr=right*np.cos(roll)+up*np.sin(roll);uu=-right*np.sin(roll)+up*np.cos(roll)
    return np.exp(logscale)*np.array([rr,-uu]),np.array([tx,ty])


def predict(xyz,params):
    A,b=matrix(params);return np.asarray(xyz)@A.T+b


def triangulate(obs,cams):
    A=[];b=[]
    for v,p in obs:
        aa,bb=matrix(cams[v]);A.extend(aa);b.extend(np.asarray(p)-bb)
    if len(A)<4:return None,None
    x,_,rank,s=np.linalg.lstsq(A,b,rcond=None)
    if rank<3:return None,None
    return x,float(s[0]/s[-1])


def fit(tracks,prior_weight=1.,max_nfev=100):
    base=np.array([[np.deg2rad(v*45),0,0,np.log(256),256,256] for v in range(8)])
    eligible={k:v for k,v in tracks.items() if len(v)>=3}
    # Deterministic identity-level split: validation tracks never optimize cameras.
    training={k:v for k,v in eligible.items() if int(hashlib.sha256(k.encode()).hexdigest()[:8],16)%5!=0}
    validation={k:v for k,v in eligible.items() if k not in training}
    if len(training)<12:return {'status':'insufficient_tracks','eligible':len(eligible),'training':len(training)},base
    names=sorted(training);init=[];obs=[]
    for p,k in enumerate(names):
        data=[(int(v),xy) for v,xy in training[k].items()];x,c=triangulate(data,base);init.append(x)
        obs.extend((p,v,np.asarray(xy)) for v,xy in data)
    obs_points=np.array([p for p,v,xy in obs]);obs_views=np.array([v for p,v,xy in obs]);obs_xy=np.array([xy for p,v,xy in obs]);init=np.array(init);x0=np.r_[base[1:].ravel(),init.ravel()];nobs=len(obs);nprior=42;ny=len(names)
    # Camera0 fixes image coordinate orientation, translation and scale. Mean depth fixes remaining global translation gauge.
    def unpack(x):return np.r_[base[:1],x[:42].reshape(7,6)],x[42:].reshape(-1,3)
    sigmas=np.array([np.deg2rad(12),np.deg2rad(8),np.deg2rad(5),.07,12.,12.])
    def residual(x):
        cams,xyz=unpack(x);matrices=[matrix(c) for c in cams];AA=np.array([a for a,b in matrices]);bb=np.array([b for a,b in matrices]);r=(np.einsum('nij,nj->ni',AA[obs_views],xyz[obs_points])+bb[obs_views]-obs_xy).ravel().tolist()
        r.extend(((cams[1:]-base[1:])/sigmas*prior_weight).ravel())
        r.append(float(xyz[:,1].mean())*.01)
        angles=np.r_[cams[:,0],2*np.pi];r.extend(np.maximum(np.deg2rad(5)-np.diff(angles),0)*100)
        return np.asarray(r)
    sparsity=lil_matrix((2*nobs+nprior+1+8,len(x0)),dtype=int)
    for i,(p,v,xy) in enumerate(obs):
        sparsity[2*i:2*i+2,42+3*p:42+3*p+3]=1
        if v:sparsity[2*i:2*i+2,6*(v-1):6*v]=1
    for i in range(42):sparsity[2*nobs+i,i]=1
    sparsity[2*nobs+42,43::3]=1;sparsity[2*nobs+43:,:42]=1
    lo=base[1:]-[np.deg2rad(30),np.deg2rad(20),np.deg2rad(12),.2,35,35]
    hi=base[1:]+[np.deg2rad(30),np.deg2rad(20),np.deg2rad(12),.2,35,35]
    result=least_squares(residual,x0,jac_sparsity=sparsity.tocsr(),bounds=(np.r_[lo.ravel(),np.full(init.size,-np.inf)],np.r_[hi.ravel(),np.full(init.size,np.inf)]),loss='soft_l1',f_scale=2.,max_nfev=max_nfev,ftol=1e-7,xtol=1e-7)
    cams,xyz=unpack(result.x)
    trainerrors=[float(np.linalg.norm(predict(xyz[p],cams[v])-xy)) for p,v,xy in obs]
    def evaluate(cameras,source):
        errors=[];used=[]
        for k,data in source.items():
            fitting=[(int(v),p) for v,p in data.items() if int(v) not in [1,5]];held=[(int(v),p) for v,p in data.items() if int(v) in [1,5]]
            if len(fitting)<2 or not held:continue
            xx,condition=triangulate(fitting,cameras)
            if xx is None or condition>20:continue
            ee=[float(np.linalg.norm(predict(xx,cameras[v])-p)) for v,p in held];errors.extend(ee)
            used.append({'track_id':k,'training_views':[v for v,p in fitting],'heldout_views':[v for v,p in held],'condition':condition,'heldout_px':ee})
        return {'heldout_reprojection_px':summary(errors),'tracks':used}
    records=[]
    for v,c in enumerate(cams):
        A,b=matrix(c);records.append({'view':v,'yaw_deg':float(np.rad2deg(c[0])),'elevation_deg':float(np.rad2deg(c[1])),'roll_deg':float(np.rad2deg(c[2])),'effective_scale_px':float(np.exp(c[3])),'center_px':c[4:].tolist(),'projection_3x4':np.r_[np.c_[A,b],np.array([[0,0,0,1.]])].tolist()})
    before=evaluate(base,validation);after=evaluate(cams,validation);bm={t['track_id']:t for t in before['tracks']};am={t['track_id']:t for t in after['tracks']};common=sorted(set(bm)&set(am))
    report={'paired_validation_before_px':summary([e for k in common for e in bm[k]['heldout_px']]),'paired_validation_after_px':summary([e for k in common for e in am[k]['heldout_px']]),'common_validation_tracks':len(common),'status':'regularized_fit_complete' if result.success else 'iteration_limit_or_unconverged','optimizer_success':bool(result.success),'optimizer_message':result.message,'function_evaluations':result.nfev,
      'training_tracks':len(training),'validation_tracks':len(validation),'prior_weight':prior_weight,'calibration_training_reprojection_px':summary(trainerrors),
      'validation_before':before,'validation_after':after,'cameras':records,
      'min_yaw_step_deg':float(np.rad2deg(np.diff(np.r_[cams[:,0],2*np.pi])).min()),
      'gauge':'Camera0 yaw/elevation/roll=0, scale256px and center(256,256) fixed; world units arbitrary. Mean-depth weak gauge term.',
      'intrinsics_status':'Effective orthographic image scales estimated; perspective focal length and camera distance not identifiable in this assumed orthographic model.',
      'assumptions':'Same rigid points, level orbit prior, ±30deg yaw correction and bounded roll/elevation/scale/framing. False periodic-grid matches can bias or defeat the fit.',
      'holdout_protocol':'20% identity-level track split chosen by SHA256. Validation tracks never optimize camera parameters; views1/5 withheld from their point triangulation.',
      'acceptance':'This numerical optimum is not calibrated truth. Judge held-out errors, track identity, camera plausibility and known controls separately.'}
    return report,cams


def main(source,output,prior_weight=1.,max_nfev=400):
    output.mkdir(parents=True,exist_ok=True);vertices=json.loads(source.read_text());tracks={r['track_id']:r['observations'] for r in vertices}
    report,cams=fit(tracks,prior_weight,max_nfev);(output/'camera_estimation.json').write_text(json.dumps(report,indent=2))
    points=[]
    for name,data in tracks.items():
        obs=[(int(v),xy) for v,xy in data.items()];xyz,cond=triangulate(obs,cams)
        if xyz is None:continue
        e=[float(np.linalg.norm(predict(xyz,cams[v])-xy)) for v,xy in obs]
        points.append({'track_id':name,'xyz':xyz.tolist(),'condition':cond,'all_observation_reprojection_px':summary(e),'observations':data,'status':'candidate_after_regularized_camera_fit'})
    (output/'camera_adjusted_candidates.json').write_text(json.dumps(points,indent=2))
    with (output/'camera_adjusted_candidates.ply').open('w') as f:
        f.write(f'ply\nformat ascii 1.0\ncomment regularized orthographic camera fit; unverified identity\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nend_header\n')
        for p in points:f.write(' '.join(map(str,p['xyz']))+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['cameras','validation_before','validation_after']},indent=2));print('HELDOUT',report.get('validation_before',{}).get('heldout_reprojection_px'),report.get('validation_after',{}).get('heldout_reprojection_px'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vertices',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prior-weight',type=float,default=1.);p.add_argument('--max-nfev',type=int,default=400);a=p.parse_args();main(a.vertices,a.output,a.prior_weight,a.max_nfev)
