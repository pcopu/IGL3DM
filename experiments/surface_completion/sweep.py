"""Spatially held-out regularization experiment, independent of ground-truth tuning."""
import json
from pathlib import Path
import numpy as np
from complete import directions,fit
# Standalone analytic function: do not import controls, whose top-level runs experiments.
def shape(u):
 r=1/np.sqrt((u[:,0]/.72)**2+(u[:,1]/.62)**2+(u[:,2]/1.2)**2)
 r*=1-.22*u[:,2]+.06*u[:,0]*u[:,2]
 return r-.19*np.exp(-(np.arccos(np.clip(u[:,0],-1,1))/.24)**2)

rng=np.random.default_rng(813);u=directions(900);query=directions(4096);target=shape(query)
records=[]
for missing in [0,35,65]:
 keep=u[:,0]<np.cos(np.deg2rad(missing)) if missing else np.ones(len(u),bool)
 obs=u[keep];r=shape(obs)*(1+rng.normal(0,.005,len(obs)))
 # Fixed visible back sector is withheld, never the unknown front region.
 validation=obs[:,0]<-.8;train=~validation
 choices=[]
 for degree in [4,8,12,16]:
  for lam in [1e-8,1e-7,1e-6,1e-5,1e-4]:
   model=fit(obs[train]*r[train,None],np.zeros(3),degree,lam)
   score=float(np.sqrt(np.mean((model(obs[validation])-r[validation])**2)))
   full=fit(obs*r[:,None],np.zeros(3),degree,lam);pred=full(query);err=abs(pred-target)
   hidden=query[:,0]>np.cos(np.deg2rad(missing)) if missing else np.zeros(len(query),bool)
   choices.append(dict(degree=degree,regularization=lam,validation_rmse=score,full_radial_p95=float(np.quantile(err,.95)),full_radial_max=float(err.max()),hidden_p95=float(np.quantile(err[hidden],.95)) if hidden.any() else None))
 best=min(choices,key=lambda x:x['validation_rmse'])
 records.append(dict(missing_cap_degrees=missing,selected_by_visible_holdout=best,choices=choices))
Path(__file__).with_name('results').joinpath('regularization.json').write_text(json.dumps(records,indent=2))
print(json.dumps([{'missing':r['missing_cap_degrees'],**r['selected_by_visible_holdout']} for r in records],indent=2))
