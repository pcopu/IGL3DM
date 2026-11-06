"""Completion sensitivity to measured dent coverage and interior-center assumptions.

Independent analytic control only. Error compares radial predictions along rays
through exact held-out surface points, never nearest sampled-neighbor distance.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from complete import directions, fit


def radius(u):
    r=1/np.sqrt((u[:,0]/.72)**2+(u[:,1]/.62)**2+(u[:,2]/1.2)**2)
    r*=1-.22*u[:,2]+.06*u[:,0]*u[:,2]
    return r-.19*np.exp(-(np.arccos(np.clip(u[:,0],-1,1))/.24)**2)


def run():
    rng=np.random.default_rng(814)
    train=directions(900);query=directions(4096)
    true_points=query*radius(query)[:,None]
    dent=query[:,0]>np.cos(np.deg2rad(20))
    centers=[np.zeros(3)]+[np.eye(3)[axis]*offset for axis in range(3) for offset in [-.2,.2]]
    rows=[]
    for missing in [0,10,20,35,65]:
        keep=train[:,0]<np.cos(np.deg2rad(missing)) if missing else np.ones(len(train),bool)
        points=train[keep]*radius(train[keep])[:,None]
        points*=1+rng.normal(0,.005,(len(points),1))
        for center in centers:
            model=fit(points,center,12,1e-6)
            delta=true_points-center;expected=np.linalg.norm(delta,axis=1);rays=delta/expected[:,None]
            error=abs(model(rays)-expected)
            observed=points-center;observed/=np.linalg.norm(observed,axis=1)[:,None]
            dist,_=cKDTree(observed).query(rays)
            angle=np.rad2deg(2*np.arcsin(np.clip(dist/2,0,1)))
            rows.append(dict(missing_cap_degrees=missing,center=center.tolist(),observed_points=len(points),degree=12,regularization=1e-6,all_radial_p95=float(np.quantile(error,.95)),dent_radial_p95=float(np.quantile(error[dent],.95)),dent_radial_max=float(error[dent].max()),dent_nearest_observation_angle_p95=float(np.quantile(angle[dent],.95)),dent_fraction_over_20deg=float(np.mean(angle[dent]>20))))
    # Fully covered but wrong geometry: coverage must not be interpreted as accuracy.
    points=train*radius(train)[:,None]*np.array([1,1.3,1])
    model=fit(points,np.zeros(3),12,1e-6);err=abs(model(query)-radius(query))
    observed=points/np.linalg.norm(points,axis=1)[:,None];dist,_=cKDTree(observed).query(query)
    angle=np.rad2deg(2*np.arcsin(np.clip(dist/2,0,1)))
    distortion=dict(condition='all directions observed, y stretched 30 percent',all_radial_p95=float(np.quantile(err,.95)),nearest_observation_angle_p95=float(np.quantile(angle,.95)),fraction_over_20deg=float(np.mean(angle>20)))
    out=Path(__file__).parent/'results'/'support_sensitivity.json'
    out.write_text(json.dumps(dict(seed=814,description=__doc__,rows=rows,distortion=distortion),indent=2))
    for missing in [0,10,20,35,65]:
        selected=[r for r in rows if r['missing_cap_degrees']==missing]
        print(missing,'origin dent p95',selected[0]['dent_radial_p95'],'center range',min(r['dent_radial_p95'] for r in selected),max(r['dent_radial_p95'] for r in selected))
    print(distortion)

if __name__=='__main__':run()
