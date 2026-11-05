"""Decode user-supplied video and track local grid junctions through adjacent frames.

Outputs are candidate observations with timestamps. Geometry requires explicitly
supplied projection matrices; no default 360-degree or camera calibration claim.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import cv2
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw,ImageFont
from grid_tracks import junctions
from geometry import summary


def patch(gray,p,r=7):
    x,y=np.rint(p).astype(int)
    if x<r or y<r or x+r>=gray.shape[1] or y+r>=gray.shape[0]:return None
    return gray[y-r:y+r+1,x-r:x+r+1].astype(float)


def ncc(a,b):
    if a is None or b is None:return -1.
    a=a-a.mean();b=b-b.mean();den=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.sum(a*b)/den) if den>1e-8 else -1.


def dlt(observations,projections):
    """N-view homogeneous DLT. Coordinate units must match supplied cameras."""
    A=[]
    for i,xy in observations:
        P=np.asarray(projections[i],float);x,y=xy
        if P.shape!=(3,4) or not np.isfinite(P).all():raise ValueError('Each camera projection must be finite 3x4')
        A.extend([x*P[2]-P[0],y*P[2]-P[1]])
    if len(A)<4:return None
    A=np.asarray(A);norm=np.linalg.norm(A,axis=1);A=A/np.maximum(norm[:,None],1e-12)
    _,s,V=np.linalg.svd(A)
    if np.linalg.matrix_rank(A)<3:return None
    if abs(V[-1,3])<1e-10:return None
    return V[-1,:3]/V[-1,3]


def camera_diagnostic(tracks,cameras):
    pp={int(k):np.asarray(v,float) for k,v in cameras['projections'].items()}
    held=set(map(int,cameras.get('heldout_sample_indices',[])));errors=[];results=[]
    for tid,track in tracks.items():
        obs=[(o['sample_index'],o['xy']) for o in track['observations'] if o['sample_index'] in pp]
        train=[o for o in obs if o[0] not in held];test=[o for o in obs if o[0] in held]
        if len(train)<2 or not test:continue
        xyz=dlt(train,pp)
        if xyz is None:continue
        e=[]
        for i,p in test:
            pred=pp[i]@np.r_[xyz,1]
            if abs(pred[2])<1e-10:continue
            e.append(float(np.linalg.norm(pred[:2]/pred[2]-p)))
        errors.extend(e);results.append({'track':tid,'training_observations':len(train),'heldout_observations':len(e),'heldout_px':e})
    return {'heldout_reprojection_px':summary(errors),'tracks':results,'camera_source':cameras.get('source','unspecified'),
      'caveat':'Projection matrices supplied by caller; no calibration, physical identity, visibility or ground truth is inferred. DLT is not a dense reconstruction.'}


def ingest(video,output,sample_fps=12.,max_frames=600,size=512,seed_every=5,max_active=400,cameras=None):
    if output.exists() and any(output.iterdir()):raise ValueError('Refusing nonempty output directory')
    output.mkdir(parents=True);(output/'frames').mkdir()
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():raise ValueError('Video decoder could not open input')
    fps=float(cap.get(cv2.CAP_PROP_FPS));native_w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));native_h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not np.isfinite(fps) or fps<=0:raise ValueError('No valid frame rate. Supply a decodable timestamped video; timing cannot be guessed.')
    scale=min(size/native_w,size/native_h);w=round(native_w*scale);h=round(native_h*scale)
    frames=[];grayframes=[];index=0;next_time=0.;last_pts=-1.;pts_fallback=False;truncated=False
    while True:
        ret,bgr=cap.read()
        if not ret:break
        pts=float(cap.get(cv2.CAP_PROP_POS_MSEC))/1000
        if not np.isfinite(pts) or (index>0 and pts<=last_pts):pts=index/fps;pts_fallback=True
        last_pts=pts
        if pts+1e-7>=next_time:
            if len(frames)>=max_frames:truncated=True;break
            rgb=cv2.cvtColor(cv2.resize(bgr,(w,h),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2RGB)
            fname=f'frame_{len(frames):04d}.png';Image.fromarray(rgb).save(output/'frames'/fname)
            frames.append({'sample_index':len(frames),'source_frame_index':index,'timestamp_seconds':pts,'path':f'frames/{fname}'})
            grayframes.append(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY));next_time=pts+1/sample_fps
        index+=1
    cap.release()
    if len(frames)<2:raise ValueError('Need at least two decoded samples')
    tracks={};active={};next_id=0;dropcounts={};pairmetrics=[];first_live={}
    for i,gray in enumerate(grayframes):
        previous=grayframes[i-1] if i else None
        if active and i:
            keys=list(active);old=np.array([active[k] for k in keys],np.float32).reshape(-1,1,2)
            new,status,_=cv2.calcOpticalFlowPyrLK(previous,gray,old,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
            back,statusback,_=cv2.calcOpticalFlowPyrLK(gray,previous,new,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
            fb=np.linalg.norm(back.reshape(-1,2)-old.reshape(-1,2),axis=1);retained={};quality=[]
            for z,k in enumerate(keys):
                p=old[z,0];q=new[z,0];score=ncc(patch(previous,p),patch(gray,q));reason=None
                if not status[z,0] or not statusback[z,0]:reason='optical_flow_failed'
                elif not np.isfinite(q).all() or q[0]<8 or q[1]<8 or q[0]>=w-8 or q[1]>=h-8:reason='left_image_or_invalid'
                elif fb[z]>1.:reason='forward_backward_inconsistent'
                elif np.linalg.norm(q-p)>80:reason='motion_over_limit'
                elif score<.65:reason='patch_appearance_changed'
                if reason:
                    tracks[k]['ended_at_sample']=i;tracks[k]['end_reason']=reason;dropcounts[reason]=dropcounts.get(reason,0)+1
                else:
                    retained[k]=q;tracks[k]['observations'].append({'sample_index':i,'timestamp_seconds':frames[i]['timestamp_seconds'],'xy':q.tolist(),'forward_backward_px':float(fb[z]),'patch_ncc':score});quality.append(float(fb[z]))
            pairmetrics.append({'from':i-1,'to':i,'attempted':len(keys),'retained':len(retained),'forward_backward_px':summary(quality)})
            active=retained
        if i%seed_every==0 and len(active)<max_active:
            pts,_,_=junctions(gray);existing=np.array(list(active.values()))
            tree=cKDTree(existing) if len(existing) else None
            for p in pts:
                if len(active)>=max_active:break
                if tree is not None and tree.query(p)[0]<8:continue
                if p[0]<8 or p[1]<8 or p[0]>=w-8 or p[1]>=h-8:continue
                # Also prevent adjacent newly seeded junction duplicates.
                if len(active) and min(np.linalg.norm(np.asarray(q)-p) for q in active.values())<5:continue
                k=f't{next_id:06d}';next_id+=1;active[k]=p
                tracks[k]={'observations':[{'sample_index':i,'timestamp_seconds':frames[i]['timestamp_seconds'],'xy':p.tolist(),'forward_backward_px':None,'patch_ncc':None}],'start_reason':'new_visible_junction_candidate'}
                if i==0:first_live[k]=p.tolist()
    for k in active:tracks[k]['end_reason']='last_sample';tracks[k]['ended_at_sample']=len(frames)-1
    mae=float(np.mean(np.abs(grayframes[0].astype(float)-grayframes[-1].astype(float))))
    # Endpoint visual similarity is merely a duplicate-frame warning; never closure proof.
    endpoint={'pixel_mae':mae,'near_duplicate_warning':mae<.5,'geometric_loop_closure_verified':False,
              'first_frame_tracks_surviving_to_last':sum(k in active for k in first_live),
              'note':'A copied or visually similar endpoint does not prove intermediate consistency. No endpoint gets extra geometric weight.'}
    metadata={'input_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'native_size':[native_w,native_h],'working_size':[w,h],'coordinate_scale_from_native':scale,
      'reported_fps':fps,'timestamp_source':'decoder_pts_with_frame_index_fps_fallback' if pts_fallback else 'decoder_pts',
      'sample_fps_target':sample_fps,'sample_count':len(frames),'decoded_frame_count_before_stop':index,'truncated':truncated,'frames':frames,
      'track_count':len(tracks),'track_count_at_least_3_samples':sum(len(t['observations'])>=3 for t in tracks.values()),
      'drop_reasons':dropcounts,'adjacent_pairs':pairmetrics,'endpoint':endpoint,
      'identity_caveat':'Temporal candidates only. Forward/backward and appearance checks can still accept periodic-grid swaps or drift.',
      'occlusion_policy':'Terminate on loss/ambiguity; newly visible junctions get new IDs. No hidden points or automatic cross-occlusion ID reuse.',
      'geometry':camera_diagnostic(tracks,cameras) if cameras else {'status':'not_attempted','reason':'No explicit camera projection matrices supplied; timestamps alone do not calibrate cameras.'}}
    (output/'video_manifest.json').write_text(json.dumps(metadata,indent=2));(output/'tracks.json').write_text(json.dumps(tracks,indent=2))
    # Evidence sheet: eight actual decoded frames and candidate positions, not synthetic interpolations.
    selected=np.unique(np.round(np.linspace(0,len(frames)-1,8)).astype(int));thumb_w=256;thumb_h=round(h/w*thumb_w)
    sheet=Image.new('RGB',(thumb_w*4,(thumb_h+35)*2),'white');d=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    for slot,i in enumerate(selected):
        cell=Image.open(output/frames[i]['path']).resize((thumb_w,thumb_h));dc=ImageDraw.Draw(cell)
        for t in tracks.values():
            for ob in t['observations']:
                if ob['sample_index']==i:
                    x,y=np.asarray(ob['xy'])*thumb_w/w;dc.ellipse((x-1,y-1,x+1,y+1),fill='#d52b35')
        x=(slot%4)*thumb_w;y=(slot//4)*(thumb_h+35);sheet.paste(cell,(x,y+35));d.text((x+5,y+8),f"sample {i} / {frames[i]['timestamp_seconds']:.3f}s",font=font,fill='black')
    sheet.save(output/'tracking_overview.png');return metadata
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--video',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sample-fps',type=float,default=12.);p.add_argument('--max-frames',type=int,default=600);p.add_argument('--size',type=int,default=512);p.add_argument('--cameras-json',type=Path);a=p.parse_args()
    if a.sample_fps<=0 or a.max_frames<2 or a.size<64:p.error('Invalid sampling limits')
    r=ingest(a.video,a.output,a.sample_fps,a.max_frames,a.size,cameras=json.loads(a.cameras_json.read_text()) if a.cameras_json else None)
    print(json.dumps({k:r[k] for k in ['sample_count','track_count','track_count_at_least_3_samples','truncated','endpoint','geometry']},indent=2))
