"""Conditional rigid-orbit image trajectory check; no known shape/camera truth input.

The period and framing are declared priors. Fit the middle half of a visible
track and predict both end quarters, keeping temporal separation from fitting.
"""
import numpy as np

def select(tracks,period,working_size=(512,512),threshold=1.,minimum_span=30.):
    if not np.isfinite(period) or period<=0:raise ValueError('period must be finite and positive')
    if not np.isfinite(threshold) or threshold<=0:raise ValueError('threshold must be finite and positive')
    if not np.isfinite(minimum_span) or minimum_span<=0:raise ValueError('minimum_span must be finite and positive')
    w,h=working_size
    if w<=0 or h<=0 or w>h:raise ValueError('Expected positive portrait or square working dimensions')
    scale=512/h;pad=(512-w*scale)/2;selected={};audit=[]
    for name,t in tracks.items():
        oo=[o for o in t['observations'] if o['sample_index']<period]
        if len(oo)<9:continue
        time=np.asarray([o['sample_index'] for o in oo],float);span=(time[-1]-time[0])*360/period
        if span<minimum_span:continue
        xy=np.array([o['xy'] for o in oo])*scale+[pad,0];theta=time*2*np.pi/period
        # Global image-center gauge; the 3-D point itself is not supplied.
        A=np.c_[np.cos(theta),np.sin(theta)];b=xy[:,0]-256
        fraction=(time-time[0])/(time[-1]-time[0]);train=(fraction>=.25)&(fraction<=.75);test=~train
        if train.sum()<4 or test.sum()<2:continue
        coef,_,rank,s=np.linalg.lstsq(A[train],b[train],rcond=None);condition=float(s[0]/s[-1]);ycenter=float(np.median(xy[train,1]));pred=np.c_[A@coef+256,np.full(len(time),ycenter)];errors=np.linalg.norm(pred-xy,axis=1)
        tp=float(np.percentile(errors[train],95));hp=float(np.percentile(errors[test],95));passed=rank==2 and condition<=20 and tp<=threshold and hp<=threshold
        record={'track_id':name,'nominal_span_degrees':span,'middle_training_samples':time[train].astype(int).tolist(),'endpoint_test_samples':time[test].astype(int).tolist(),'condition':condition,'training_p95_px':tp,'endpoint_prediction_p95_px':hp,'passed':bool(passed)};audit.append(record)
        if passed:selected[name]=t
    return selected,audit
