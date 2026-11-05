"""Classical shared constant-speed orthographic orbit fit with held-out track IDs.

No shape model or known control geometry is read. Global camera period,
elevation, roll and horizontal framing are estimated from 2D observations.
Scale and vertical center remain gauge choices; this is a restricted model.
"""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import summary

def design(samples,params):
 logperiod,elev,roll,cx=params;theta=np.asarray(samples)*2*np.pi/np.exp(logperiod);c=np.cos(theta);s=np.sin(theta)
 right=np.c_[c,s,np.zeros_like(c)];up=np.c_[-s*np.sin(elev),c*np.sin(elev),np.full_like(c,np.cos(elev))]
 rr=right*np.cos(roll)+up*np.sin(roll);uu=-right*np.sin(roll)+up*np.cos(roll)
 A=256*np.stack([rr,-uu],axis=1);b=np.array([cx,256.]);return A,b

def fit_point(time,xy,params,mask=None):
 A,b=design(time,params);mask=np.ones(len(time),bool) if mask is None else mask;aa=A[mask].reshape(-1,3);bb=(xy[mask]-b).ravel();xyz,_,rank,s=np.linalg.lstsq(aa,bb,rcond=None);condition=float(s[0]/s[-1]) if s[-1]>1e-12 else float('inf');pred=np.einsum('nij,j->ni',A,xyz)+b;return xyz,pred,rank,condition

def normalized(tracks,working_size):
 w,h=working_size;scale=512/h;pad=(512-w*scale)/2
 return {name:(np.array([o['sample_index'] for o in t['observations']],float),np.array([o['xy'] for o in t['observations']])*scale+[pad,0]) for name,t in tracks.items()}

def evaluate_tracks(data,params):
 rows=[];errors=[]
 for name,(time,xy) in data.items():
  if len(time)<9:continue
  span=time[-1]-time[0]
  if span<=0:continue
  fraction=(time-time[0])/span;train=(fraction>=.25)&(fraction<=.75);test=~train
  if train.sum()<4:continue
  xyz,pred,rank,condition=fit_point(time,xy,params,train);err=np.linalg.norm(pred-xy,axis=1);held=err[test];training=err[train];errors.extend(held.tolist())
  rows.append({'track_id':name,'condition':condition,'rank':int(rank),'samples':len(time),'nominal_span_degrees':float(span*360/np.exp(params[0])),'training_p95_px':float(np.percentile(training,95)),'endpoint_prediction_p95_px':float(np.percentile(held,95)),'endpoint_median_px':float(np.median(held)),'conditional_pass_1px':bool(rank==3 and condition<=20 and np.percentile(training,95)<=1 and np.percentile(held,95)<=1)})
 return {'endpoint_observation_errors_px':summary(errors),'per_track_endpoint_median_px':summary([r['endpoint_median_px'] for r in rows]),'tracks':rows}

def fit(tracks,working_size=(512,512),initial_period=96,minimum_samples=24,max_nfev=200):
 all_data=normalized(tracks,working_size);eligible={n:v for n,v in all_data.items() if len(v[0])>=minimum_samples};training={n:v for n,v in eligible.items() if int(hashlib.sha256(n.encode()).hexdigest()[:8],16)%5!=0};validation={n:v for n,v in eligible.items() if n not in training}
 if len(training)<12 or len(validation)<3:raise ValueError('Insufficient long calibration/validation tracks')
 def residual(params):
  rr=[]
  for time,xy in training.values():
   _,pred,_,_=fit_point(time,xy,params);rr.extend((pred-xy).ravel())
  return np.asarray(rr)
 lo=[np.log(64),np.deg2rad(-30),np.deg2rad(-12),224];hi=[np.log(192),np.deg2rad(30),np.deg2rad(12),288]
 x0=np.array([np.log(initial_period),0.,0.,256.]);r=least_squares(residual,x0,bounds=(lo,hi),loss='soft_l1',f_scale=1.,max_nfev=max_nfev,ftol=1e-8,xtol=1e-8,gtol=1e-8);params=r.x
 def pack(p):return {'period_frames':float(np.exp(p[0])),'elevation_deg':float(np.rad2deg(p[1])),'roll_deg':float(np.rad2deg(p[2])),'horizontal_center_px':float(p[3]),'vertical_center_px':256,'scale_px_per_unit':256}
 report={'optimizer_success':bool(r.success),'optimizer_message':r.message,'nfev':r.nfev,'initial_camera':pack(x0),'estimated_camera':pack(params),'parameter_vector':params.tolist(),'minimum_calibration_samples':minimum_samples,'calibration_track_count':len(training),'validation_track_count':len(validation),'calibration_track_ids':sorted(training),'validation_track_ids':sorted(validation),'calibration_residual_px':summary(np.linalg.norm(residual(params).reshape(-1,2),axis=1)),'validation_before':evaluate_tracks(validation,x0),'validation_after':evaluate_tracks(validation,params),'all_tracks_conditional':evaluate_tracks(all_data,params),'assumptions':'One constant-speed rigid orthographic turn, constant elevation/roll/framing. Track identities unverified. Variable speed, perspective or deformation can invalidate this model.','holdout':'20% deterministic track identities never fit camera parameters. Their middle-half point observations fit point position; endpoint quarters test it. Image graph selection used all frames.','truth_or_shape_consumed':False}
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tracks',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--initial-period',type=float,default=96);p.add_argument('--minimum-samples',type=int,default=24);p.add_argument('--max-nfev',type=int,default=200);a=p.parse_args()
 if a.output.exists():raise ValueError('Refusing existing output')
 tracks=json.loads(a.tracks.read_text());manifest=json.loads(a.manifest.read_text());r=fit(tracks,manifest['working_size'],a.initial_period,a.minimum_samples,a.max_nfev);a.output.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['validation_before','validation_after','all_tracks_conditional','calibration_track_ids','validation_track_ids']},indent=2));print('heldout_before',r['validation_before']['endpoint_observation_errors_px']);print('heldout_after',r['validation_after']['endpoint_observation_errors_px'])
