"""Evaluation-only checkpoint runner; run after all declared variants exist."""
from pathlib import Path
import argparse,json,copy,sys
from assemble_observed_cells import assemble
from score_physical_faces import score

def run(root,out,tag=""):
 if out.exists():raise ValueError('Refusing existing evaluation summary')
 names=['pear','bent','barrel','waist'];summary={}
 for name in names:
  base=root/('recovery_face_control48_avi' if name=='pear' else f'recovery_{name}_control48')
  original=root/('recovery_orbit_hypotheses48_resolvable' if name=='pear' else f'recovery_{name}_hypotheses48_resolvable')
  variants={'original':original,**{v:root/f'recovery_{name}_neighbors48_{tag}{v}' for v in ['frozen','refit']}}
  for path in variants.values():
   if not (path/'candidate_points.json').exists():raise ValueError('Every declared output must exist before labels are read')
  truthpath=root.parent/'source/experiments/marker_consistency/controls/known_pear_96/ground_truth.json' if name=='pear' else root/{'bent':'independent_bent_ovoid96','barrel':'independent_squat_barrel96','waist':'independent_warped_waist96'}[name]/'ground_truth.json'
  truth=json.loads(truthpath.read_text());truth['views']=truth['views'][::2]
  for i,v in enumerate(truth['views']):v['view']=i
  summary[name]={}
  for variant,path in variants.items():
   if not (path/'cells/metrics.json').exists():assemble(base/'tracking',path/'candidate_points.json',base/'measurements/measurement_manifest.json',base/'declared_acquisition_cameras.json',path/'cells','Frozen broad-view model + calibration-image neighborhood endpoint support' if variant!='original' else 'Frozen broad-view ambiguity/resolvability')
   ev=score(json.loads((path/'cells/candidate_points.json').read_text()),json.loads((path/'cells/candidate_faces.json').read_text()),truth)
   ev['evaluation_only']=True;ev['control_role']='New frozen-rule fourth-shape comparison' if name=='waist' else 'Development control';(path/'neighbor_physical_evaluation.json').write_text(json.dumps(ev,indent=2))
   summary[name][variant]={k:v for k,v in ev.items() if k not in ['point_rows','face_rows']}
   if variant!='original':
    orig=json.loads((original/'candidate_points.json').read_text());op=score(orig,[],truth)['point_rows'];summary[name][variant]['original_points']=len(orig);summary[name][variant]['transition_counts']={}
    for p,e in zip(json.loads((path/'candidate_points.json').read_text()),ev['point_rows']):
     transition=op[p['parent_point_index']]['identity']+' -> '+e['identity'];d=summary[name][variant]['transition_counts'];d[transition]=d.get(transition,0)+1
 out.write_text(json.dumps(summary,indent=2));print(json.dumps({n:{v:{k:r[k] for k in ['points','point_identity_counts','faces','face_identity_counts','unique_correct_physical_faces','known_correct_point_3d_error']} for v,r in rows.items()} for n,rows in summary.items()},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--tag',default='');a=p.parse_args();run(a.root,a.output,a.tag)
