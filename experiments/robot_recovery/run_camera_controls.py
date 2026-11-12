"""Synthetic projected-coordinate controls, not end-to-end detector validation."""
from pathlib import Path
import argparse,json,importlib.util,sys
import numpy as np
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bspline_camera',HERE/'fit_bspline_orbit.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
def run(out):
 out=Path(out)
 if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output')
 out.mkdir(parents=True);rng=np.random.default_rng(4242);summary={}
 for label,speeds in [('constant',[360/192]*5),('variable',[.4,3,3,3,.1])]:
  truth=np.r_[np.log(np.deg2rad(speeds)),.06,-.02,254.];tracks={}
  for i in range(100):
   start=int(rng.integers(0,130));length=int(rng.integers(40,64));time=np.arange(start,min(193,start+length));xyz=rng.uniform(-.7,.7,3);A,b=model.design(time,truth,(0,192));xy=np.einsum('nij,j->ni',A,xyz)+b+rng.normal(0,.15,(len(time),2));tracks[f'fixture_{i:04d}']={'observations':[{'sample_index':int(t),'xy':p.tolist()} for t,p in zip(time,xy)]}
  manifest={'working_size':[512,512],'frames':[{'sample_index':i} for i in range(193)]};baseline=model.constant.fit(tracks,(512,512),192,16,200);r=model.fit(tracks,manifest,baseline);time=np.arange(193);trueyaw=model.yaw(time,truth,(0,192));fityaw=model.yaw(time,np.array(r['parameter_vector']),(0,192));baseyaw=time*2*np.pi/np.exp(baseline['parameter_vector'][0]);row={'control':'random known 3D point segments projected by explicit cameras; truth never supplied to fitter','noise_standard_deviation_px':.15,'track_count':100,'camera_training_tracks':r['calibration_track_count'],'camera_heldout_tracks':r['validation_track_count'],'constant_true_yaw_rms_deg':float(np.sqrt(np.mean(np.rad2deg(baseyaw-trueyaw)**2))),'bspline_true_yaw_rms_deg':float(np.sqrt(np.mean(np.rad2deg(fityaw-trueyaw)**2))),'bspline_endpoint_errors_px':r['validation']['variable_endpoint_errors_px'],'constant_endpoint_errors_px':r['validation']['constant_endpoint_errors_px'],'optimizer_message':r['optimizer_message'],'optimizer_optimality':r['optimizer_optimality'],'optimizer_cost':r['optimizer_cost'],'bounds_active':r['bounds']['active_mask'],'limitations':'Mathematical camera fixture only; not image detection or periodic identity validation.'};summary[label]=row;(out/f'{label}_fit.json').write_text(json.dumps(r,indent=2));print(label,json.dumps(row),flush=True)
 (out/'summary.json').write_text(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.output)
