"""Evaluation only. Joins image-only scores to existing truth-based validation.

It never creates or edits the score/selection files. This separation lets the
three fixed image-only selection rules be audited independently of labels.
"""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter

def summarize(rows,eligible,held):
    counts=Counter(r['identity_status'] for r in rows)
    passed=[r for r in rows if r['heldout_geometry_pass']]
    passes=Counter(r['identity_status'] for r in passed)
    n=len(rows);resolved=counts['correct']+counts['wrong_identity']
    return {'retained_tracks':n,'baseline_tracks':eligible,'coverage_fraction':n/eligible if eligible else None,
            'correct':counts['correct'],'wrong_identity':counts['wrong_identity'],
            'unresolved_detection_or_drift':counts['unresolved_detection_or_drift'],
            'correct_fraction_all':counts['correct']/n if n else None,
            'correct_fraction_resolved':counts['correct']/resolved if resolved else None,
            'heldout_evaluated_tracks':sum(r['track_id'] in held and len(held[r['track_id']]['heldout_px'])>0 for r in rows),
            'existing_3px_heldout_passes':len(passed),'existing_3px_heldout_correct_passes':passes['correct'],
            'existing_3px_heldout_false_passes_wrong_identity':passes['wrong_identity'],
            'existing_3px_heldout_unresolved_passes':passes['unresolved_detection_or_drift'],
            'wrong_fraction_among_all_heldout_passes':passes['wrong_identity']/len(passed) if passed else None}

def run(control64,control256,score_directory,output):
    ROOT=Path(score_directory);output=Path(output)
    CONTROLS={'known64':Path(control64),'known256':Path(control256)}
    if output.exists():raise ValueError('Refusing to overwrite output')
    report={'method':'Symmetric alternative-patch ambiguity rejection; whole original tracks retained or rejected, never corrected.',
            'truth_policy':'Scores and selections generated in separate script that does not read truth or cameras. This script joins existing validation classifications only.',
            'cautions':['Image-only rejection does not prove retained identities.','At most three fixed thresholds, used unchanged for both controls. No threshold selected for final use after truth comparison.','Whole-track minimum penalizes longer tracks and denser cadence through more opportunities to fail.','The two cadences show the same analytic pear and are not independent object tests.','NCC uses rounded integer centers and translation-only 31px patches; local shear, rotation, lighting, occlusion and grid repetition can reject true identities.','Unresolved labels remain unresolved and are never counted as correct or false passes.','The 3px heldout diagnostic and labels are those of the original intact tracks; no refitting or threshold tuning.'],
            'controls':{}}
    for name,control in CONTROLS.items():
        scorepath=ROOT/name/'scores.json';raw=scorepath.read_bytes();scores=json.loads(raw)
        validation=json.loads((control/'validation.json').read_text())
        rows=validation['tracks'];manifest=json.loads((control/'video_tracks/video_manifest.json').read_text())
        held={x['track']:x for x in manifest['geometry']['tracks']}
        d={'score_sha256':hashlib.sha256(raw).hexdigest(),'parameters':scores['parameters'],'groups':{}}
        for label,subset in [('all_at_least_3_frames',rows),('span_at_least_30_degrees',[r for r in rows if r['angular_span_degrees']>=30])]:
            dd={'baseline':summarize(subset,len(subset),held),'thresholds':{}}
            for threshold in scores['parameters']['thresholds']:
                keep=[r for r in subset if scores['scores'][r['track_id']]['score'] is not None and scores['scores'][r['track_id']]['score']>=threshold]
                dd['thresholds'][str(threshold)]=summarize(keep,len(subset),held)
            d['groups'][label]=dd
        report['controls'][name]=d
    output.write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--control64',type=Path,required=True);p.add_argument('--control256',type=Path,required=True);p.add_argument('--score-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.control64,a.control256,a.score_directory,a.output),indent=2))
