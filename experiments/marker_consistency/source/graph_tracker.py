"""Image-only re-detected graph-node association; no truth, cameras or original tracks."""
from pathlib import Path
import argparse, json, sys, hashlib, time
from collections import Counter
import cv2
import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
from grid_tracks import junctions, skeleton_graph
from quad_cells import detect_cells

SETTINGS=dict(detector='unchanged skeleton junctions', descriptor='RootSIFT fixed sizes 16+32',graph='traced ink + uniquely mapped closed quad edges',lk_window=21,lk_levels=3,lk_fb_max=1.5,candidate_gate_spacing=.35,candidate_gate_clip=[3.,7.],max_displacement=80.,max_rootsift_distance=.8,min_patch_ncc=.55,assignment_rounds=3,min_supporting_neighbors=2,min_cost_margin=.12,truth_used=False,cameras_used=False,original_tracks_used=False)

def canon(a,b):return tuple(sorted((int(a),int(b))))
def patch(gray,p):
    p=np.asarray(p,float)
    if p.min()<8 or p[0]>=gray.shape[1]-8 or p[1]>=gray.shape[0]-8:return None
    a=cv2.getRectSubPix(gray,(15,15),tuple(p.astype(float))).astype(float).ravel();a-=a.mean();n=np.linalg.norm(a)
    return a/n if n>1e-8 else None

def detect(gray,sift):
    xy,skel,_=junctions(gray);gg=skeleton_graph(skel,xy);quad=detect_cells(gray)
    edges=set()
    for a,nn in gg['neighbors'].items():
        for b in nn:edges.add(canon(a,b))
    cells=[]
    tree=cKDTree(xy) if len(xy)>=2 else None
    node_map={}
    if tree:
        for n in quad['nodes']:
            ds,ids=tree.query(n['xy'],k=2)
            if ds[0]<=3.5 and ds[1]-ds[0]>=.5:node_map[n['node_id']]=int(ids[0])
        for c in quad['cells']:
            if all(n in node_map for n in c['node_ids']):
                ns=[node_map[n] for n in c['node_ids']]
                if len(set(ns))!=4:continue
                cells.append(ns)
                for a,b in zip(ns,ns[1:]+ns[:1]):edges.add(canon(a,b))
    neighbors=[set() for _ in xy]
    for a,b in edges:neighbors[a].add(b);neighbors[b].add(a)
    dd=[]
    for size in (16,32):
        kp=[cv2.KeyPoint(float(p[0]),float(p[1]),size,0) for p in xy]
        _,d=sift.compute(gray,kp)
        d=np.zeros((len(xy),128),np.float32) if d is None else d
        d=np.sqrt(d/np.maximum(d.sum(1,keepdims=True),1e-8));dd.append(d)
    descriptors=np.concatenate(dd,axis=1)/np.sqrt(2)
    spacing=tree.query(xy,k=2)[0][:,1] if tree else np.full(len(xy),8.)
    return dict(xy=xy,edges=edges,neighbors=neighbors,cells=cells,descriptors=descriptors,spacing=spacing,patches=[patch(gray,p) for p in xy],raw_cells=len(quad['cells']))

def flow(a,b,pts):
    if not len(pts):return np.zeros((0,2)),np.zeros(0,bool),np.zeros(0)
    p=np.asarray(pts,np.float32).reshape(-1,1,2)
    q,s,_=cv2.calcOpticalFlowPyrLK(a,b,p,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
    back,sb,_=cv2.calcOpticalFlowPyrLK(b,a,q,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
    fb=np.linalg.norm(back[:,0]-p[:,0],axis=1)
    valid=s[:,0].astype(bool)&sb[:,0].astype(bool)&np.isfinite(q[:,0]).all(1)&(fb<=1.5)&(np.linalg.norm(q[:,0]-pts,axis=1)<=80)
    return q[:,0],valid,fb

def associate(im1,im2,a,b):
    x,y=a['xy'],b['xy'];n,m=len(x),len(y)
    if not n or not m:return {},dict(raw=0,assigned=0,accepted=0,reason='empty graph'),[]
    forward,fv,fb=flow(im1,im2,x);back,bv,bb=flow(im2,im1,y)
    gx=np.clip(a['spacing']*.35,3,7);gy=np.clip(b['spacing']*.35,3,7)
    base=np.full((n,m),1e5);details={};tree=cKDTree(y)
    for i in range(n):
        if not fv[i]:continue
        for j in tree.query_ball_point(forward[i],gx[i]):
            if not bv[j]:continue
            fr=float(np.linalg.norm(forward[i]-y[j]));br=float(np.linalg.norm(back[j]-x[i]))
            if br>gy[j]:continue
            dd=float(np.linalg.norm(a['descriptors'][i]-b['descriptors'][j]))
            if dd>.8:continue
            pp,qq=a['patches'][i],b['patches'][j]
            nc=float(pp@qq) if pp is not None and qq is not None else -1
            if nc<.55:continue
            base[i,j]=(fr/gx[i])**2+(br/gy[j])**2+2*dd**2+.4*(1-nc)
            details[i,j]=dict(forward_residual_px=fr,backward_residual_px=br,forward_backward_px=float(fb[i]),reverse_forward_backward_px=float(bb[j]),descriptor_distance=dd,patch_ncc=nc)
    cost=base.copy();previous={};raw=int((base<1e4).sum())
    for iteration in range(3):
        aug=np.concatenate([cost,np.full((n,n),2.5)],axis=1)
        ii,jj=linear_sum_assignment(aug);mapping={int(i):int(j) for i,j in zip(ii,jj) if j<m and cost[i,j]<2.5}
        if iteration==2:break
        cost=base.copy()
        for (i,j) in details:
            mapped=[mapping[k] for k in a['neighbors'][i] if k in mapping]
            if mapped:
                support=sum(q in b['neighbors'][j] for q in mapped)
                cost[i,j]+=.75*(len(mapped)-support)/len(mapped)
        previous=mapping
    accepted={};audit=[];reasons=Counter()
    for i,j in mapping.items():
        nn=[mapping[k] for k in a['neighbors'][i] if k in mapping]
        support=sum(q in b['neighbors'][j] for q in nn)
        src=np.sort(cost[i][np.arange(m)!=j]);dst=np.sort(cost[:,j][np.arange(n)!=i])
        margin=min(float(src[0]-cost[i,j]) if len(src) else 1e5,float(dst[0]-cost[i,j]) if len(dst) else 1e5)
        reason='accepted'
        if support<2:reason='insufficient_graph_neighbors'
        elif len(nn)-support>support:reason='graph_disagreement'
        elif margin<.12:reason='ambiguous_cost_margin'
        if reason=='accepted':accepted[i]=j
        reasons[reason]+=1
        audit.append(dict(from_node_id=i,to_node_id=j,cost=float(cost[i,j]),margin=margin,supporting_graph_neighbors=int(support),mapped_source_neighbors=len(nn),decision=reason,**details[i,j]))
    return accepted,dict(raw=raw,assigned=len(mapping),accepted=len(accepted),decisions=dict(reasons)),audit

def emit_tracks(graphs,maps,frames,variant):
    tracks={};active={};next_id=0
    for i,g in enumerate(graphs):
        current={}
        if i:
            for src,dst in maps[i-1].items():
                if src in active:current[dst]=active[src]
        for node,p in enumerate(g['xy']):
            tid=current.get(node)
            if tid is None:
                tid=f'g{next_id:07d}';next_id+=1;current[node]=tid
                tracks[tid]=dict(observations=[],start_reason='new_visible_redetected_junction',selection=variant)
            tracks[tid]['observations'].append(dict(sample_index=i,timestamp_seconds=frames[i]['timestamp_seconds'],node_id=node,xy=[float(v) for v in p]))
        for node,tid in active.items():
            if tid not in current.values():tracks[tid]['end_reason']='association_lost_or_rejected_no_gap_bridge';tracks[tid]['ended_at_sample']=i-1
        active=current
    for tid in active.values():tracks[tid]['end_reason']='last_sample';tracks[tid]['ended_at_sample']=len(graphs)-1
    return tracks

def run(root,out):
    if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output')
    out.mkdir(parents=True,exist_ok=True);t=time.time();manifest=json.loads((root/'video_manifest.json').read_text());frames=manifest['frames'];images=[cv2.imread(str(root/f['path']),0) for f in frames]
    if any(x is None for x in images):raise ValueError('Missing input image')
    sift=cv2.SIFT_create();graphs=[]
    for i,im in enumerate(images):
        graphs.append(detect(im,sift))
        if i%16==0:print('detect',i,len(graphs[-1]['xy']),flush=True)
    evidence=[dict(sample_index=i,nodes=[dict(node_id=k,xy=[float(v) for v in p],neighbor_ids=sorted(g['neighbors'][k])) for k,p in enumerate(g['xy'])],closed_cells=g['cells'],raw_closed_cells=g['raw_cells']) for i,g in enumerate(graphs)]
    (out/'frame_graphs.json').write_text(json.dumps(evidence))
    adjacent=[];skip=[];audit=[]
    for delta,target in [(1,adjacent),(2,skip)]:
        for i in range(len(images)-delta):
            mapping,stats,aa=associate(images[i],images[i+delta],graphs[i],graphs[i+delta]);target.append(mapping)
            audit.append(dict(from_sample=i,to_sample=i+delta,stats=stats,associations=aa))
            if i%16==0:print('associate',delta,i,stats,flush=True)
    veto=[dict(mm) for mm in adjacent];conflicts=[]
    for i,direct in enumerate(skip):
        for a,b in adjacent[i].items():
            c=adjacent[i+1].get(b)
            if c is not None and a in direct and direct[a]!=c:
                veto[i].pop(a,None);veto[i+1].pop(b,None);conflicts.append(dict(from_sample=i,source_node=a,middle_node=b,composed_target=c,direct_target=direct[a]))
    for name,mm in [('graph_joint',adjacent),('graph_joint_cycle_veto',veto)]:
        dest=out/name;dest.mkdir();tracks=emit_tracks(graphs,mm,frames,name)
        (dest/'tracks.json').write_text(json.dumps(tracks))
        (dest/'associations.json').write_text(json.dumps([dict(from_sample=i,matches={str(a):b for a,b in x.items()}) for i,x in enumerate(mm)]))
        print(name,'tracks',len(tracks),'3+',sum(len(t['observations'])>=3 for t in tracks.values()),flush=True)
    (out/'pair_audit.json').write_text(json.dumps(audit));(out/'cycle_conflicts.json').write_text(json.dumps(conflicts,indent=2))
    result=dict(settings=SETTINGS,input_directory=str(root.resolve()),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),frame_count=len(frames),seconds=time.time()-t,per_frame_nodes=[len(g['xy']) for g in graphs],adjacent_matches=[len(x) for x in adjacent],skip_matches=[len(x) for x in skip],cycle_conflicts=len(conflicts),limitations=['Periodic grids can support coherent wrong phase despite descriptor, graph and cycles.','Per-frame missing or merged junctions fragment tracks; no gap bridge.','Node positions are new detections, not previous LK coordinates.'])
    (out/'manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.input,a.output)
