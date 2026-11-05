"""Read-only summary of the preserved64 control; writes only inside cadence_256."""
from pathlib import Path
from collections import Counter
import argparse,json
from geometry import summary

def compare(control_directory,output):
 OLD=Path(control_directory);output=Path(output)
 if output.exists():raise ValueError('Refusing to overwrite output')
 v=json.loads((OLD/'validation.json').read_text());m=json.loads((OLD/'video_tracks/video_manifest.json').read_text());h={r['track']:r for r in m['geometry']['tracks']}
 def report(rows):
  tested=[r for r in rows if r['track_id'] in h and h[r['track_id']]['heldout_px']];passed=[r for r in tested if max(h[r['track_id']]['heldout_px'])<=3]
  c=Counter(r['identity_status'] for r in rows);p=Counter(r['identity_status'] for r in passed)
  return {'track_count':len(rows),'identity_classification':dict(c),'correct_fraction_all':c['correct']/len(rows),'heldout_evaluated_tracks':len(tested),'heldout_not_evaluated_tracks':len(rows)-len(tested),'heldout_evaluated_identity':dict(Counter(r['identity_status'] for r in tested)),'heldout_3px_pass_tracks':len(passed),'heldout_3px_pass_track_identity':dict(p),'heldout_reprojection_px':summary([e for r in tested for e in h[r['track_id']]['heldout_px']]),'known_wrong_fraction_among_passes':p['wrong_identity']/len(passed),'unresolved_fraction_among_passes':p['unresolved_detection_or_drift']/len(passed)}
 d={'source':'Existing preserved64 validation and video manifest only. No new rendering or tracking.','all_at_least_3_frames':report(v['tracks']),'span_at_least_30_degrees':report([r for r in v['tracks'] if r['angular_span_degrees']>=30])}
 output.write_text(json.dumps(d,indent=2));return d

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--control-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(compare(a.control_directory,a.output),indent=2))
