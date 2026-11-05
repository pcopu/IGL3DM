"""Evaluate frozen image-only selectors on a known control, never on target truth."""
import argparse
import json
from pathlib import Path
from graph_consistency import select_segments
from trajectory_consistency import select
from evaluate_selection import evaluate


def run(control_directory, graph_evidence, output_directory, period_frames):
    root=Path(control_directory);out=Path(output_directory)
    if out.exists():raise ValueError('Refusing an existing output directory')
    tracks=json.loads((root/'video_tracks/tracks.json').read_text())
    evidence=json.loads(Path(graph_evidence).read_text())
    # No truth is loaded until every image-only selection is fixed.
    segments,_=select_segments(tracks,evidence,mode='segments')
    trajectory,_=select(tracks,period_frames,threshold=1.)
    combined,audit=select(segments,period_frames,threshold=1.)
    truth=json.loads((root/'ground_truth.json').read_text())
    out.mkdir(parents=True);reports={}
    for name,candidates in [('baseline',tracks),('graph_segments',segments),('trajectory1',trajectory),('combined_fixed',combined)]:
        result=evaluate(candidates,truth,period_frames)
        destination=out/name;destination.mkdir()
        (destination/'tracks.json').write_text(json.dumps(candidates,indent=2))
        (destination/'validation.json').write_text(json.dumps(result,indent=2))
        reports[name]={k:v for k,v in result.items() if k!='tracks'}
    (out/'combined_fixed/trajectory_audit.json').write_text(json.dumps(audit,indent=2))
    (out/'summary.json').write_text(json.dumps(reports,indent=2))
    return reports


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--control-directory',type=Path,required=True)
    p.add_argument('--graph-evidence',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True)
    p.add_argument('--period-frames',type=int,required=True)
    a=p.parse_args();print(json.dumps(run(a.control_directory,a.graph_evidence,a.output_directory,a.period_frames),indent=2))
