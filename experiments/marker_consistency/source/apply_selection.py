"""Apply predeclared graph-plus-orbit selector without ground truth or learned models."""
from pathlib import Path
import argparse,json,copy
from graph_consistency import select_segments
from trajectory_consistency import select

def run(tracking_directory,graph_evidence_path,output_directory,period_frames=96):
 root=Path(tracking_directory).resolve();out=Path(output_directory)
 if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output directory')
 tracks=json.loads((root/'tracks.json').read_text());ev=json.loads(Path(graph_evidence_path).read_text());manifest=json.loads((root/'video_manifest.json').read_text())
 segments,graph_audit=select_segments(tracks,ev,mode='segments');selected,trajectory_audit=select(segments,period_frames,manifest['working_size'],threshold=1.)
 report={'original_track_count':len(tracks),'original_tracks_at_least_3':sum(len(t['observations'])>=3 for t in tracks.values()),'graph_supported_segments_at_least_3':len(segments),'graph_segments_at_least_30deg':sum((t['observations'][-1]['sample_index']-t['observations'][0]['sample_index'])*360/period_frames>=30 for t in segments.values()),'final_conditional_segments':len(selected),'retained_original_track_ids':len({t['source_track_id'] for t in selected.values()}),'period_frames_prior':period_frames,'camera_assumptions':'Level orthographic full-turn orbit with fixed image framing. Period is a prior, not recovered calibration.','selection':'Unique visible graph corner, persistent four-ID cell and two edge neighbors; break gaps. Then>=9observations and>=30degrees prior span, middle-half trajectory fit plus endpoint-quarter prediction p95<=1normalized pixel.','truth_used':False,'source_coordinates_changed':False,'reprojection_is_not_identity_proof':True}
 out.mkdir(parents=True,exist_ok=True);(out/'tracks.json').write_text(json.dumps(selected,indent=2));(out/'graph_selection_audit.json').write_text(json.dumps(graph_audit,indent=2));(out/'trajectory_selection_audit.json').write_text(json.dumps(trajectory_audit,indent=2));(out/'selection_summary.json').write_text(json.dumps(report,indent=2))
 # Preserve original frame bytes and timestamps. Paths are resolved reads, not copies or warps.
 for frame in manifest['frames']:frame['path']=str(root/frame['path'])
 manifest['track_count']=len(selected);manifest['track_count_at_least_3_samples']=len(selected);manifest['selection_summary']=report;manifest['geometry']={'status':'not_attempted_by_selector','reason':'No camera truth or shape supplied to selection.'};manifest['identity_caveat']='Conditionally selected candidates, not verified physical vertex identities.'
 (out/'video_manifest.json').write_text(json.dumps(manifest,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tracking-directory',type=Path,required=True);p.add_argument('--graph-evidence',type=Path,required=True);p.add_argument('--output-directory',type=Path,required=True);p.add_argument('--period-frames',type=int,default=96);a=p.parse_args();print(json.dumps(run(a.tracking_directory,a.graph_evidence,a.output_directory,a.period_frames),indent=2))
