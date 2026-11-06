"""Known radial controls: completion accuracy is evaluated separately from topology."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from complete import directions,fit,mesh,topology,save_mesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).parent/'results';OUT.mkdir(exist_ok=True)
LOCAL=Path(__file__).parent/'outputs';LOCAL.mkdir(exist_ok=True)

def truth(u,kind):
    if kind=='sphere': return np.ones(len(u))
    r=1/np.sqrt((u[:,0]/.72)**2+(u[:,1]/.62)**2+(u[:,2]/1.2)**2)
    if kind=='ellipsoid': return r
    r *= 1-.22*u[:,2]+.06*u[:,0]*u[:,2]
    if kind=='dented_pear':
        # Deliberately concave region inside the withheld front sector.
        angle=np.arccos(np.clip(u@np.array([1.,0,0]),-1,1))
        r-=.19*np.exp(-(angle/.24)**2)
    return r

def convex_radius(points,u):
    planes=ConvexHull(points).equations
    denom=u@planes[:,:3].T
    t=np.where(denom>1e-10,-planes[:,3]/np.maximum(denom,1e-10),np.inf)
    return t.min(1)

def summary(x):return {'median':float(np.median(x)),'p95':float(np.quantile(x,.95)),'max':float(np.max(x))}

rng=np.random.default_rng(812)
train=directions(600); test=directions(4096)
rows=[]; examples={}
for kind in ['sphere','ellipsoid','pear','dented_pear']:
 for missing in [0,35,65]:
    keep=train[:,0]<np.cos(np.deg2rad(missing)) if missing else np.ones(len(train),bool)
    points=train[keep]*truth(train[keep],kind)[:,None]
    # 0.5% of characteristic unit independent radial noise.
    points*=1+rng.normal(0,.005,(len(points),1))
    hidden=test[:,0]>np.cos(np.deg2rad(missing)) if missing else np.zeros(len(test),bool)
    for method in ['convex','harmonic_l4','harmonic_l8','harmonic_l12']:
        if method=='convex': pred=convex_radius(points,test)
        else: pred=fit(points,np.zeros(3),int(method.split('l')[-1]),.0001)(test)
        err=np.abs(pred-truth(test,kind));v,f=mesh(test,pred,np.zeros(3))
        rows.append(dict(control=kind,missing_cap_degrees=missing,method=method,observed_points=len(points),radial_error=summary(err),hidden_radial_error=summary(err[hidden]) if hidden.any() else None,topology=topology(v,f)))
        if kind=='dented_pear' and missing==35:
            examples[method]=(v,f,err)
            save_mesh(LOCAL/(method+'.ply'),v,f)
# Camera deformation stress: low image reprojection does not make a completion metrically right.
u=directions(600);p=u*truth(u,'pear')[:,None]; distorted=p*np.array([1,1.3,1])
pred=fit(distorted,np.zeros(3),8,.0001)(test)
rows.append(dict(control='pear_depth_scale_1.3',method='harmonic_l8',radial_error=summary(abs(pred-truth(test,'pear'))),warning='Injected wrong depth scale, not an actual fitted camera test'))
(OUT/'controls.json').write_text(json.dumps({'seed':812,'noise_relative_sigma':.005,'units':'characteristic radius ~1; absolute radial error, not pixels','rows':rows},indent=2))
fig=plt.figure(figsize=(14,4));
for i,(name,(v,f,e)) in enumerate(examples.items()):
 ax=fig.add_subplot(1,4,i+1,projection='3d');ax.plot_trisurf(v[:,0],v[:,1],v[:,2],triangles=f,color='#a8b8c8',linewidth=0,alpha=1);ax.set_title(name+'\np95 radial error '+format(np.quantile(e,.95),'.3f'));ax.view_init(15,5);ax.set_box_aspect((1,1,1.7));ax.set_axis_off()
fig.suptitle('KNOWN CONTROL ONLY: dent centered in missing 35° cap; watertightness does not prove fidelity')
fig.tight_layout(rect=(0,0,1,.90));fig.savefig(OUT/'completion_controls.png',dpi=130);plt.close(fig)
print('Wrote',len(rows),'control results')

# Equatorial section makes the hidden dent and fabricated closure inspectable.
a=np.linspace(-np.pi,np.pi,720);section=np.column_stack((np.cos(a),np.sin(a),np.zeros(len(a))))
keep=train[:,0]<np.cos(np.deg2rad(35));pts=train[keep]*truth(train[keep],'dented_pear')[:,None]
fig,ax=plt.subplots(figsize=(7,6));rad=truth(section,'dented_pear');ax.plot(section[:,0]*rad,section[:,1]*rad,'k',label='Known truth, including hidden dent',linewidth=3)
for degree in [4,8,12]:
 rad=fit(pts,np.zeros(3),degree,.0001)(section);ax.plot(section[:,0]*rad,section[:,1]*rad,label=f'Harmonic degree {degree}')
rad=convex_radius(pts,section);ax.plot(section[:,0]*rad,section[:,1]*rad,label='Convex baseline')
ax.set_aspect('equal');ax.legend();ax.set_title('Control equator: 35 degree front cap unobserved (right)');ax.set_xlabel('x (control units)');ax.set_ylabel('y (control units)');fig.tight_layout();fig.savefig(OUT/'hidden_dent_section.png',dpi=140);plt.close(fig)
