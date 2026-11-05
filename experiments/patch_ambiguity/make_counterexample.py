"""Read-only known-control patch counterexamples; truth is for annotation only."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial import cKDTree

def make(control,scores_file,output):
    if output.exists():raise ValueError('Refusing to overwrite output')
    gt=json.loads((control/'ground_truth.json').read_text());tracks=json.loads((control/'video_tracks/tracks.json').read_text());manifest=json.loads((control/'video_tracks/video_manifest.json').read_text());scores=json.loads(scores_file.read_text());vertices=np.asarray(gt['vertices'])
    title=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    canvas=Image.new('RGB',(1440,730),'white');draw=ImageDraw.Draw(canvas)
    draw.text((15,12),'High local patch uniqueness can still follow the wrong grid row',font=title,fill='black')
    draw.text((15,44),'Known analytic control only. Red cross = tracked point; blue circle = first mapped vertex when visible.',font=font,fill='black')
    records=[]
    for row,tid in enumerate(['t001057','t001064']):
        observations=tracks[tid]['observations'];mapped=[]
        for ob in observations:
            view=gt['views'][ob['sample_index']];canonical={}
            for item in view['observations']:
                if item['visible']:canonical.setdefault(tuple(np.round(vertices[item['vertex_id']],7)),item)
            points=list(canonical.values());dist,idx=cKDTree([p['xy'] for p in points]).query(ob['xy']);mapped.append((points[idx]['vertex_id'],float(dist)))
        first=mapped[0][0];margin=scores['scores'][tid]['score'];top=90+row*300
        draw.text((15,top),f'{tid}: minimum bilateral NCC margin +{margin:.4f}; original 3 px held-out test passes; known IDs change',font=font,fill='black')
        for col,(ob,(identity,dist)) in enumerate(zip(observations,mapped)):
            frame=ob['sample_index'];im=Image.open(control/'video_tracks'/manifest['frames'][frame]['path']).convert('RGB');x,y=ob['xy'];left,upper=round(x)-40,round(y)-40;crop=im.crop((left,upper,left+80,upper+80)).resize((160,160),Image.Resampling.NEAREST);d=ImageDraw.Draw(crop);cx,cy=(x-left)*2,(y-upper)*2;d.line((cx-7,cy,cx+7,cy),fill='#c9262a',width=2);d.line((cx,cy-7,cx,cy+7),fill='#c9262a',width=2)
            ref=next((p for p in gt['views'][frame]['observations'] if p['vertex_id']==first and p['visible']),None)
            if ref:
                rx,ry=(np.asarray(ref['xy'])-[left,upper])*2;d.ellipse((rx-6,ry-6,rx+6,ry+6),outline='#145cba',width=2)
            px=15+col*178;canvas.paste(crop,(px,top+54));draw.text((px,top+28),f'Frame {frame}',font=font,fill='black');draw.text((px,top+222),f'Nearest ID {identity}',font=font,fill='black');draw.text((px,top+242),f'distance {dist:.2f} px',font=font,fill='black')
        records.append({'candidate_track':tid,'minimum_ncc_margin':margin,'nearest_known_vertex_ids':[v for v,d in mapped],'nearest_distance_max_px':max(d for v,d in mapped),'first_mapped_vertex':first})
    draw.text((15,698),'Nearest visible vertex within 3 px is the operational identity test. These are false passes, not target geometry.',font=font,fill='black');output.parent.mkdir(parents=True,exist_ok=True);canvas.save(output);return records

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--control-directory',type=Path,required=True);p.add_argument('--scores',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(make(a.control_directory,a.scores,a.output),indent=2))
