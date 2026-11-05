"""Auditable orthographic track validation, not image-to-3D truth recovery."""
import numpy as np


def camera(yaw_degrees, scale=150.0, center=(256.0,256.0)):
    a=np.deg2rad(yaw_degrees)
    return scale*np.array([[np.cos(a),np.sin(a),0.],[0.,0.,-1.]]), np.asarray(center,float)


def project(points,yaw_degrees,scale=150.,center=(256.,256.)):
    A,t=camera(yaw_degrees,scale,center)
    return np.asarray(points)@A.T+t


def fit_point(observations,scale=150.,center=(256.,256.),yaw_step=45.):
    A=[]; b=[]
    for view,p in observations:
        aa,tt=camera(view*yaw_step,scale,center)
        A.append(aa); b.append(np.asarray(p)-tt)
    A=np.concatenate(A);b=np.concatenate(b)
    x,residual,rank,s=np.linalg.lstsq(A,b,rcond=None)
    return x, int(rank), float(s[0]/s[-1]) if s[-1]>1e-10 else float('inf')


def summary(a):
    a=np.asarray(a,float)
    if not len(a):return {'n':0,'mean':None,'median':None,'p95':None,'max':None}
    return {'n':len(a),'mean':float(a.mean()),'median':float(np.median(a)),
            'p95':float(np.percentile(a,95)),'max':float(a.max())}


def analyze_tracks(tracks,scale=150.,center=(256.,256.),heldout=(1,5),yaw_step=45.,ground_truth=None):
    """tracks maps persistent physical CORNER ID to {view:[x,y]}.
    Identity qualification is external. Requested cameras remain assumptions.
    Held-out views never contribute to point fits.
    """
    train_err=[];test_err=[];epi=[];loop=[];truth=[];details=[];pairwise=[]
    retained=0;predicted_obs=0
    for tid, obs0 in sorted(tracks.items()):
        obs={int(k):np.asarray(v,float) for k,v in obs0.items()}
        training=[(v,p) for v,p in obs.items() if v not in heldout]
        testing=[(v,p) for v,p in obs.items() if v in heldout]
        if len(training)<2:continue
        xyz,rank,cond=fit_point(training,scale,center,yaw_step)
        if rank<3 or cond>10:continue
        retained+=1
        te=[float(np.linalg.norm(project(xyz,v*yaw_step,scale,center)-p)) for v,p in training]
        he=[float(np.linalg.norm(project(xyz,v*yaw_step,scale,center)-p)) for v,p in testing]
        train_err.extend(te);test_err.extend(he);predicted_obs+=len(testing)
        if ground_truth is not None:truth.append(float(np.linalg.norm(xyz-ground_truth[tid])))
        # Pairwise epipolar line distance under common level orthographic cameras.
        vv=sorted(obs)
        for i,v in enumerate(vv):
            for w in vv[i+1:]:
                d=abs(float(obs[v][1]-obs[w][1]));epi.append(d)
                pairwise.append({'track':tid,'view_a':v,'view_b':w,'yaw_gap':min(abs(v-w),8-abs(v-w))*yaw_step,'epipolar_px':d})
        # Independent two-view fits predict third views, including loop triangles.
        l=[]
        for i,v in enumerate(vv):
            for j in range(i+1,len(vv)):
                w=vv[j]; xx,rr,cc=fit_point([(v,obs[v]),(w,obs[w])],scale,center,yaw_step)
                if rr<3 or cc>10:continue
                for q in vv:
                    if q not in (v,w):l.append(float(np.linalg.norm(project(xx,q*yaw_step,scale,center)-obs[q])))
        loop.extend(l)
        details.append({'track':tid,'training_views':[v for v,_ in training],'heldout_views':[v for v,_ in testing],
                        'fit_xyz':xyz.tolist(),'condition':cond,'train_px':te,'heldout_px':he,'loop_px':l})
    return {'input_corner_tracks':len(tracks),'fit_eligible_corner_tracks':retained,'heldout_predicted_observations':predicted_obs,
            'training_reprojection_px':summary(train_err),'heldout_reprojection_px':summary(test_err),
            'known_camera_epipolar_px':summary(epi),'three_view_loop_px':summary(loop),
            'ground_truth_3d_error':summary(truth) if ground_truth is not None else None,'tracks':details,'pairwise':pairwise}


def gate(result,identity_ok,views_connected,coverage_ok):
    reasons=[]
    if not identity_ok:reasons.append('identity_or_corner_orientation_not_defensible')
    if not views_connected:reasons.append('no_connected_eight_view_marker_graph')
    if not coverage_ok:reasons.append('insufficient_independent_surface_coverage')
    for key,limit in [('heldout_reprojection_px',3.),('three_view_loop_px',3.),('known_camera_epipolar_px',2.)]:
        metric=result[key]
        if metric['n']==0:reasons.append(key+'_unobservable')
        elif metric['p95']>limit:reasons.append(key+'_over_limit')
    return {'pass':not reasons,'reasons':reasons,'threshold_units':'512px cell; heldout and loop p95 <=3px, epipolar p95 <=2px',
            'scope':'Gate for sparse marker constraints only. No claim of dense surface or original 3D truth.'}
