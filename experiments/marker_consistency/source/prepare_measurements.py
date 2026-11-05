"""Prepare eight timestamped views from dense video tracks; no independent object fitting."""
from pathlib import Path
import argparse,json,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
SOURCE=Path(__file__).resolve().parent.parent/'source'
sys.path.insert(0,str(SOURCE))
from geometry import fit_point,analyze_tracks

def prepare(input_directory,output_directory,period_frames=96,original_frame_offset=14,source_fps=24.):
    if not isinstance(period_frames,(int,np.integer)) or period_frames<=0:raise ValueError('period_frames must be a positive integer')
    if not np.isfinite(source_fps) or source_fps<=0:raise ValueError('source_fps must be finite and positive')
    if not isinstance(original_frame_offset,(int,np.integer)) or original_frame_offset<0:raise ValueError('original_frame_offset must be a nonnegative integer')
    INPUT=Path(input_directory);OUTPUT=Path(output_directory)
    if OUTPUT.exists() and any(OUTPUT.iterdir()):raise ValueError('Refusing nonempty output directory')
    manifest=json.loads((INPUT/'video_manifest.json').read_text());tracks=json.loads((INPUT/'tracks.json').read_text());w,h=manifest['working_size'];s=512/h;pad=(512-w*s)/2
    chosen=np.rint(np.arange(8)*period_frames/8).astype(int).tolist()
    if len(set(chosen))!=8 or max(chosen)>=len(manifest['frames']):raise ValueError('The period and source need eight distinct available measurement frames')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    atlas=Image.new('RGB',(2048,1024),'white');strip=Image.new('RGB',(2048,1100),'white');d=ImageDraw.Draw(strip);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    for v,i in enumerate(chosen):
     im=Image.open(INPUT/manifest['frames'][i]['path']);im=im.resize((round(w*s),512));cell=Image.new('RGB',(512,512),'white');cell.paste(im,(round(pad),0));atlas.paste(cell,((v%4)*512,(v//4)*512));strip.paste(cell,((v%4)*512,(v//4)*550+38));d.text(((v%4)*512+10,(v//4)*550+10),f"view {v}: raw frame {i+original_frame_offset}, source {(i+original_frame_offset)/source_fps:.3f}s",font=font,fill='black')
    atlas.save(OUTPUT/'measurement_atlas.png');strip.save(OUTPUT/'measurement_frames_labeled.png')
    selected=[]
    for name,track in tracks.items():
     ob={o['sample_index']:o for o in track['observations']};data={v:(np.asarray(ob[i]['xy'])*s+[pad,0]).tolist() for v,i in enumerate(chosen) if i in ob}
     if len(data)<2:continue
     xyz,rank,condition=fit_point(list(data.items()),256,(256,256))
     if rank<3 or condition>20:continue
     selected.append({'track_id':name,'xyz':xyz.tolist(),'observations':data,'condition':condition,'first_sample':track['observations'][0]['sample_index'],'last_sample':track['observations'][-1]['sample_index'],'source':'actual unblended video optical-flow track','identity_state':'unverified candidate'})
    (OUTPUT/'camera_candidate_tracks.json').write_text(json.dumps(selected,indent=2));report={'selected_sample_indices':chosen,'selected_original_indices':[i+original_frame_offset for i in chosen],'normalization':{'common_scale':s,'common_x_padding':pad,'independent_object_fitting':False},'selected_corner_tracks':len(selected),'tracks_at_least_three_selected_views':sum(len(t['observations'])>=3 for t in selected),'all_track_lengths':{str(k):sum(len(t['observations'])==k for t in selected) for k in range(2,9)},'period_frames_prior':period_frames,'original_frame_offset':original_frame_offset,'source_fps':source_fps,'measured_sample_count':manifest['sample_count'],'camera_prior':'Equal45deg steps are initial priors only, not recovered angles; frame timestamps retained.'};(OUTPUT/'measurement_manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-directory',type=Path,required=True,help='Tracker output with video_manifest.json, tracks.json and frames/')
    p.add_argument('--output-directory',type=Path,required=True)
    p.add_argument('--period-frames',type=int,default=96,help='Initial full-turn period prior, not measured camera calibration')
    p.add_argument('--original-frame-offset',type=int,default=14)
    p.add_argument('--source-fps',type=float,default=24.)
    a=p.parse_args();prepare(a.input_directory,a.output_directory,a.period_frames,a.original_frame_offset,a.source_fps)
