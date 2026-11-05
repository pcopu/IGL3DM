"""Image-only rejection of already tracked image points; never loads truth/cameras.

For each adjacent observation, compare a 31 px square patch at the source with
its accepted target and alternative centers 6--32 px from the accepted target.
Use the same test backwards. The track score is its minimum accepted-minus-best-
alternative NCC across either direction and every adjacent pair. No reattachment,
coordinates, or observations are changed. The three declared thresholds are
-0.05, 0, +0.05; thresholds cannot be changed based on this control evaluation.
"""
import argparse,json,time
from pathlib import Path
import cv2
import numpy as np

PARAMS={'patch_radius_px':15,'alternative_min_radius_px':6,'alternative_max_radius_px':32,
        'bilateral_test':True,'track_aggregation':'minimum_all_steps_both_directions',
        'thresholds':[-0.05,0.0,0.05]}

def direction(a,b,p,q):
    r=PARAMS['patch_radius_px']; search=PARAMS['alternative_max_radius_px']
    x,y=np.rint(p).astype(int);u,v=np.rint(q).astype(int)
    if x-r<0 or y-r<0 or x+r>=a.shape[1] or y+r>=a.shape[0]:return None
    template=a[y-r:y+r+1,x-r:x+r+1]
    x0=max(r,u-search);x1=min(b.shape[1]-r-1,u+search)
    y0=max(r,v-search);y1=min(b.shape[0]-r-1,v+search)
    if u<x0 or u>x1 or v<y0 or v>y1:return None
    scores=cv2.matchTemplate(b[y0-r:y1+r+1,x0-r:x1+r+1],template,cv2.TM_CCOEFF_NORMED)
    yy,xx=np.ogrid[y0:y1+1,x0:x1+1]
    ds=(xx-u)**2+(yy-v)**2
    alternatives=(ds>=PARAMS['alternative_min_radius_px']**2)&(ds<=search**2)
    if not alternatives.any():return None
    accepted=float(scores[v-y0,u-x0]);alternative=float(scores[alternatives].max())
    return accepted-alternative,accepted,alternative

def run(root,out):
    assert not out.exists(),f'Refusing to overwrite {out}'
    out.mkdir(parents=True)
    tracks=json.loads((root/'tracks.json').read_text())
    manifest=json.loads((root/'video_manifest.json').read_text())
    images=[cv2.imread(str(root/f['path']),cv2.IMREAD_GRAYSCALE) for f in manifest['frames']]
    if any(im is None for im in images):raise ValueError('Unreadable frame')
    scored={};start=time.time()
    for ti,(tid,track) in enumerate(tracks.items()):
        obs=track['observations']
        if len(obs)<3:continue
        rows=[];failed=False
        for p,q in zip(obs,obs[1:]):
            i=p['sample_index'];j=q['sample_index']
            if j!=i+1:raise ValueError('Only strictly adjacent tracks supported')
            fw=direction(images[i],images[j],p['xy'],q['xy'])
            bw=direction(images[j],images[i],q['xy'],p['xy'])
            if fw is None or bw is None:failed=True;break
            rows.append({'from':i,'to':j,'forward_margin':fw[0],'backward_margin':bw[0],
                         'forward_accepted_ncc':fw[1],'forward_alternative_ncc':fw[2],
                         'backward_accepted_ncc':bw[1],'backward_alternative_ncc':bw[2]})
        margin=None if failed else min(min(x['forward_margin'],x['backward_margin']) for x in rows)
        scored[tid]={'samples':len(obs),'score':margin,'pair_scores':rows,
                     'decision_state':'unscorable_patch_boundary' if failed else 'scored'}
        if ti%200==0:print(root,ti,'elapsed',round(time.time()-start,1),flush=True)
    report={'source_directory':str(root.resolve()),'parameters':PARAMS,
            'selection_uses':'Decoded grayscale pixels and already saved candidate 2D observations only. No truth, projection, object model, or heldout reprojection inputs.',
            'input_track_count':len(tracks),'scored_track_count':len(scored),'scores':scored}
    (out/'scores.json').write_text(json.dumps(report,indent=2))
    for threshold in PARAMS['thresholds']:
        selected={tid:tracks[tid] for tid,s in scored.items() if s['score'] is not None and s['score']>=threshold}
        tag=f'{threshold:+.2f}'.replace('+','plus').replace('-','minus').replace('.','p')
        (out/f'selected_{tag}.json').write_text(json.dumps(selected,indent=2))
        print(root,'threshold',threshold,'selected',len(selected),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.root,a.output)
