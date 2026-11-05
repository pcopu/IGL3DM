"""Control-only evaluator. Truth is used after image tracking, not for tracking."""
from pathlib import Path
from collections import Counter
import argparse,json
import numpy as np
from scipy.spatial import cKDTree
from geometry import summary
from video_tracks import dlt

def evaluate(control_directory, output):
 ROOT=Path(control_directory);output=Path(output)
 if output.exists():raise ValueError('Refusing to overwrite output')
 gt=json.loads((ROOT/'ground_truth.json').read_text())
 tracks=json.loads((ROOT/'video_tracks/tracks.json').read_text())
 manifest=json.loads((ROOT/'video_tracks/video_manifest.json').read_text())
 assert manifest['sample_count']==manifest['decoded_frame_count_before_stop']==256
 assert [f['source_frame_index'] for f in manifest['frames']]==list(range(256))
 assert not manifest['truncated']
 P={v['view']:np.array(v['projection_3x4']) for v in gt['views']}; truth=np.array(gt['vertices']); trees=[];ids=[]
 for view in gt['views']:
  canon={}
  for p in view['observations']:
   if p['visible']:canon.setdefault(tuple(np.round(truth[p['vertex_id']],7)),p)
  vv=list(canon.values()); trees.append(cKDTree([p['xy'] for p in vv])); ids.append([p['vertex_id'] for p in vv])
 held={t['track']:t for t in manifest['geometry']['tracks']}
 results=[]
 for name,track in tracks.items():
  obs=track['observations']
  if len(obs)<3:continue
  mapped=[]
  for o in obs:
   v=o['sample_index'];distance,idx=trees[v].query(o['xy']);mapped.append((ids[v][idx],float(distance)))
  reliable=all(d<=3 for vid,d in mapped);same=reliable and len(set(vid for vid,d in mapped))==1
  status='correct' if same else 'wrong_identity' if reliable else 'unresolved_detection_or_drift'
  err=None
  if same:
   xx=dlt([(o['sample_index'],o['xy']) for o in obs],P)
   if xx is not None:err=float(np.linalg.norm(xx-truth[mapped[0][0]]))
  diagnostic=held.get(name); errors=diagnostic['heldout_px'] if diagnostic else []
  results.append({'track_id':name,'samples':len(obs),'angular_span_degrees':(obs[-1]['sample_index']-obs[0]['sample_index'])*360/256,'identity_status':status,'known_3d_error':err,'heldout_evaluated':bool(errors),'heldout_px':errors,'heldout_geometry_pass':bool(errors) and max(errors)<=3})
 def summarize(rr):
  classes=Counter(r['identity_status'] for r in rr); tested=[r for r in rr if r['heldout_evaluated']]; passes=[r for r in tested if r['heldout_geometry_pass']]; pc=Counter(r['identity_status'] for r in passes)
  return {'track_count':len(rr),'identity_classification':dict(classes),'correct_fraction_all':classes['correct']/len(rr) if rr else None,'correct_fraction_resolved':classes['correct']/(classes['correct']+classes['wrong_identity']) if classes['correct']+classes['wrong_identity'] else None,'angular_span_degrees':summary([r['angular_span_degrees'] for r in rr]),'known_correct_track_3d_error':summary([r['known_3d_error'] for r in rr if r['known_3d_error'] is not None]),'heldout_evaluated_tracks':len(tested),'heldout_not_evaluated_tracks':len(rr)-len(tested),'heldout_evaluated_identity':dict(Counter(r['identity_status'] for r in tested)),'heldout_reprojection_px':summary([e for r in tested for e in r['heldout_px']]),'heldout_3px_pass_tracks':len(passes),'heldout_3px_pass_track_identity':dict(pc),'false_pass_wrong_identity':pc['wrong_identity'],'pass_unresolved_identity':pc['unresolved_detection_or_drift'],'false_fraction_among_all_passes':pc['wrong_identity']/len(passes) if passes else None}
 report={'source':'256 genuinely rendered frames of unchanged analytic asymmetric pear, 1.40625 degree steps, encoded 30fps, 8.533333 seconds; not generated-object reconstruction.', 'decoded_all_frames_without_downsampling':True,'heldout_sample_indices':[32,96,160,224],'heldout_yaw_degrees':[45,135,225,315],'heldout_policy':'Same four absolute heldout angles as 64-frame control. Fit all other observations, evaluate available heldout observations; pass requires every available heldout error <=3px. Tracks without >=2 training and >=1 heldout observations are unevaluated, not failed.', 'identity_policy':'Same nearest-visible-known-vertex classifier as 64-frame control: every observation must map within 3px; all mapped IDs identical means correct, different IDs means wrong_identity, otherwise unresolved_detection_or_drift. Duplicate pole coordinates canonicalized.', 'all_at_least_3_frames':summarize(results),'span_at_least_30_degrees':summarize([r for r in results if r['angular_span_degrees']>=30]),'cautions':['Analytic control truth and exact cameras are evaluation only; no generated geometry receives them.','Nearest-vertex-within-3px is an operational classifier, not infallible identity ground truth near compressed silhouette vertices.','Denser cadence changes number of samples and span between reseeding events (unchanged seed_every=5).','Reprojection with many nearby training frames is a weak identity test, even for a track with a longer total span.','A track may have only one of the four heldout angles; missing heldout angles do not count as observations.'], 'tracks':results}
 output.write_text(json.dumps(report,indent=2));return {k:v for k,v in report.items() if k!='tracks'}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--control-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(evaluate(a.control_directory,a.output),indent=2))
