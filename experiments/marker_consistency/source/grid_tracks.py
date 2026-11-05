"""Adjacent-view grid-junction/context probe. Candidate tracks, not original mesh IDs."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import cv2
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw,ImageFont
from geometry import analyze_tracks,summary
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def thin(binary):
    """Zhang-Suen thinning with zero padding; binary is bool/0-1."""
    a=np.pad(binary.astype(np.uint8),1)
    for _ in range(160):
        before=a.sum()
        for step in [0,1]:
            p=a[1:-1,1:-1]
            ns=[a[:-2,1:-1],a[:-2,2:],a[1:-1,2:],a[2:,2:],a[2:,1:-1],a[2:,:-2],a[1:-1,:-2],a[:-2,:-2]]
            N=sum(ns);T=sum((ns[i]==0)&(ns[(i+1)%8]==1) for i in range(8))
            if step==0:q=(ns[0]*ns[2]*ns[4]==0)&(ns[2]*ns[4]*ns[6]==0)
            else:q=(ns[0]*ns[2]*ns[6]==0)&(ns[0]*ns[4]*ns[6]==0)
            remove=(p==1)&(N>=2)&(N<=6)&(T==1)&q;p[remove]=0
        if a.sum()==before:break
    return a[1:-1,1:-1]

def junctions(gray):
    ink=(gray<155).astype(np.uint8);ink[:10]=0;ink[-10:]=0;ink[:,:10]=0;ink[:,-10:]=0
    skeleton=thin(ink);a=np.pad(skeleton,1)
    ns=[a[:-2,1:-1],a[:-2,2:],a[1:-1,2:],a[2:,2:],a[2:,1:-1],a[2:,:-2],a[1:-1,:-2],a[:-2,:-2]]
    transitions=sum((ns[i]==0)&(ns[(i+1)%8]==1) for i in range(8))
    branches=((skeleton==1)&(transitions>=3)).astype(np.uint8)
    spread=cv2.dilate(branches,np.ones((5,5),np.uint8))
    n,labels,stats,centroids=cv2.connectedComponentsWithStats(spread,8)
    pts=[]
    for k in range(1,n):
        yy,xx=np.where((labels==k)&(branches>0))
        if not len(xx):continue
        pts.append([float(xx.mean()),float(yy.mean())])
    return np.asarray(pts,dtype=np.float32).reshape(-1,2),skeleton,branches


def skeleton_graph(skeleton,points):
    """Trace ink segments between detected node neighborhoods; ambiguous branches retained separately."""
    yy,xx=np.where(skeleton>0);assignment=np.zeros(skeleton.shape,np.int32)
    if not len(points):return {'neighbors':{},'ambiguous_segments':[]}
    distances,idx=cKDTree(points).query(np.column_stack([xx,yy]));close=distances<=3.5
    assignment[yy[close],xx[close]]=idx[close]+1
    segments=((skeleton>0)&(assignment==0)).astype(np.uint8)
    _,labels=cv2.connectedComponents(segments,8)
    touched={}
    for dy,dx in [(a,b) for a in [-1,0,1] for b in [-1,0,1] if a or b]:
        rolled=np.roll(np.roll(assignment,dy,0),dx,1);mask=(labels>0)&(rolled>0)
        for seg,node in np.unique(np.column_stack([labels[mask],rolled[mask]]),axis=0):touched.setdefault(int(seg),set()).add(int(node)-1)
    neighbors={i:set() for i in range(len(points))};ambiguous=[]
    for seg,nodes in touched.items():
        if len(nodes)==2:
            a,b=sorted(nodes);neighbors[a].add(b);neighbors[b].add(a)
        elif len(nodes)>2:ambiguous.append({'segment':seg,'node_ids':sorted(nodes)})
    return {'neighbors':{i:sorted(n) for i,n in neighbors.items()},'ambiguous_segments':ambiguous}

def mutual_context(desc1,desc2,ratio):
    if desc1 is None or desc2 is None or len(desc1)<2 or len(desc2)<2:return []
    matcher=cv2.BFMatcher(cv2.NORM_L2)
    f=matcher.knnMatch(desc1,desc2,k=2);b=matcher.knnMatch(desc2,desc1,k=2)
    f=[m[0] for m in f if len(m)==2 and m[0].distance<ratio*m[1].distance]
    b={(m[0].queryIdx,m[0].trainIdx) for m in b if len(m)==2 and m[0].distance<ratio*m[1].distance}
    return [(m.queryIdx,m.trainIdx,float(m.distance)) for m in f if (m.trainIdx,m.queryIdx) in b]

def neighborhood_support(matches,p,q,radius=70,min_neighbors=2):
    if not matches:return []
    pp=np.array([p[a] for a,b,d in matches]);qq=np.array([q[b] for a,b,d in matches]);kept=[]
    for i,m in enumerate(matches):
        dp=np.linalg.norm(pp-pp[i],axis=1);dq=np.linalg.norm(qq-qq[i],axis=1)
        near=(dp>3)&(dp<radius)&(dq>3)&(dq<radius*1.5)
        # Small-neighborhood context must have plausible deformation, not arbitrary swaps.
        plausible=near&(dq>=dp*.35)&(dq<=dp*2.8)&(np.linalg.norm((qq-pp)-(qq[i]-pp[i]),axis=1)<35)
        if plausible.sum()>=min_neighbors:kept.append(m)
    return kept

def run(input_path,output,ratio=.72):
    output.mkdir(parents=True,exist_ok=True)
    im=Image.open(input_path).convert('RGB');w,h=im.size;images=[];points=[];descs=[];gridgraphs=[];sift=cv2.SIFT_create()
    for v in range(8):
        box=(round(v%4*w/4),round(v//4*h/2),round((v%4+1)*w/4),round((v//4+1)*h/2))
        cell=im.crop(box).resize((512,512),Image.Resampling.LANCZOS);rgb=np.array(cell);gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
        pts,skel,br=junctions(gray)
        kp=[cv2.KeyPoint(float(p[0]),float(p[1]),24,0) for p in pts]
        kk,dd=sift.compute(gray,kp);pts=np.array([k.pt for k in kk])
        points.append(pts);descs.append(dd);images.append(rgb);gridgraphs.append(skeleton_graph(skel,pts))
        cv2.imwrite(str(output/f'skeleton_{v}.png'),(255-skel*255))
    pairs=[];maps={};rawmaps={};match_records=[]
    for i in range(8):
        for delta in [1,2]:
            j=(i+delta)%8;m=mutual_context(descs[i],descs[j],ratio);good=neighborhood_support(m,points[i],points[j])
            maps[i,j]={a:b for a,b,d in good};rawmaps[i,j]={a:b for a,b,d in m}
            goodset={(a,b) for a,b,d in good}
            match_records.append({'from_view':i,'to_view':j,'matches':[{'from_node_id':a,'to_node_id':b,'descriptor_l2':d,'neighborhood_supported':(a,b) in goodset,'conditional_vertical_error_px':float(abs(points[i][a,1]-points[j][b,1]))} for a,b,d in m]})
            pairs.append({'from':i,'to':j,'nominal_yaw_gap_degrees':delta*45,'raw_mutual_context_matches':len(m),'neighborhood_supported_matches':len(good),
                          'conditional_vertical_error_px':summary([abs(points[i][a,1]-points[j][b,1]) for a,b,d in good])})
    cycles=[];cycletracks=[]
    for i in range(8):
        j=(i+1)%8;k=(i+2)%8;count=0;geometry=[]
        for a,b in maps[i,j].items():
            c=maps[j,k].get(b)
            if c is not None and maps[i,k].get(a)==c:
                count+=1;obs={i:points[i][a].tolist(),j:points[j][b].tolist(),k:points[k][c].tolist()}
                r=analyze_tracks({'p':obs},256,(256,256),heldout=(j,))
                if r['heldout_reprojection_px']['n']:geometry.append(r['heldout_reprojection_px']['mean'])
                cycletracks.append(obs)
        cycles.append({'views':[i,j,k],'independently_closed_feature_cycles':count,'middle_view_prediction_px':summary(geometry)})
    # Propagate adjacent local matches. Missing support terminates a track; no identity re-use or jump over occlusion.
    parents={}
    def root(a):
        parents.setdefault(a,a)
        if parents[a]!=a:parents[a]=root(parents[a])
        return parents[a]
    def union(a,b):parents[root(a)]=root(b)
    for i in range(8):
        j=(i+1)%8
        for a,b in maps[i,j].items():union((i,a),(j,b))
    groups={}
    for k in list(parents):groups.setdefault(root(k),[]).append(k)
    valid=[];conflicts=[]
    for nodes in groups.values():
        if len({v for v,k in nodes})<len(nodes):conflicts.append(nodes)
        else:valid.append(nodes)
    tracks={f'candidate_{t:04d}':{v:points[v][k].tolist() for v,k in nodes} for t,nodes in enumerate(valid)}
    fullcycles=[]
    for a in maps[0,1]:
        now=a;path=[(0,a)]
        for i in range(8):
            nxt=maps[i,(i+1)%8].get(now)
            if nxt is None:break
            now=nxt;path.append(((i+1)%8,now))
        if len(path)==9:fullcycles.append({'start':a,'end':now,'exact_closure':now==a,'endpoint_distance_px':float(np.linalg.norm(points[0][a]-points[0][now]))})
    result={'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'opencv_version':cv2.__version__,
      'settings':{'ratio':ratio,'junction_neighbor_radius_px':70,'min_support_neighbors':2,'descriptor_context_size_px':24,'normalized_cell_size':512,'gray_ink_threshold':155},
      'detected_junction_candidates_per_view':[len(x) for x in points],'pairs':pairs,'three_view_cycles':cycles,
      'propagated_candidate_tracks':len(valid),'propagated_track_length_histogram':{str(n):sum(len(g)==n for g in valid) for n in range(2,9)},
      'rejected_components_with_repeated_view':len(conflicts),'full_orbit_candidates':fullcycles,
      'heldout_requested_camera_diagnostic':analyze_tracks(tracks,256,(256,256),(1,5)),
      'identity_status':'None are authenticated physical vertex IDs. Repeated black grids can generate wrong but self-consistent matches.',
      'occlusion_policy':'A missing adjacent match ends the track. No hidden point is hallucinated and no later point is reattached automatically. Loss cannot distinguish occlusion from appearance change or ambiguity.',
      'heldout_caveat':'Views 1 and 5 are held out from XYZ fits only, not feature-track selection. This is an exploratory consistency diagnostic, not untouched test data.'}
    node_evidence=[]
    for v,pts in enumerate(points):
        tree=cKDTree(pts);_,near=tree.query(pts,k=min(7,len(pts)))
        node_evidence.append({'view':v,'nodes':[{'node_id':i,'xy':p.tolist(),'spatial_neighbor_ids':[int(n) for n in np.atleast_1d(near[i]) if int(n)!=i],'traced_grid_neighbor_ids':gridgraphs[v]['neighbors'][i]} for i,p in enumerate(pts)],'ambiguous_ink_segments':gridgraphs[v]['ambiguous_segments']})
    (output/'junction_graph.json').write_text(json.dumps(node_evidence,indent=2))
    (output/'match_graph.json').write_text(json.dumps(match_records,indent=2))
    fitted={r['track']:r for r in result['heldout_requested_camera_diagnostic']['tracks']}
    evidence=[]
    for t,nodes in enumerate(valid):
        name=f'candidate_{t:04d}'
        evidence.append({'track_id':name,'observations':[{'view':v,'node_id':k,'xy':points[v][k].tolist(),'traced_grid_neighbor_ids':gridgraphs[v]['neighbors'][k]} for v,k in sorted(nodes)],'identity_state':'candidate_only','occlusion_state':'no_automatic_gap_bridge; missing edge may be occlusion, appearance change or ambiguity','conditional_geometry':fitted.get(name),'termination_reason':'adjacent_support_ends' if len(nodes)<8 else 'full_orbit_candidate'})
    (output/'candidate_evidence.json').write_text(json.dumps(evidence,indent=2))
    (output/'metrics.json').write_text(json.dumps(result,indent=2));(output/'tracks.json').write_text(json.dumps(tracks,indent=2))
    # Most-supported adjacent pairs; show at most 25 matches to keep evidence legible.
    selected=sorted([p for p in pairs if p['nominal_yaw_gap_degrees']==45],key=lambda x:x['neighborhood_supported_matches'],reverse=True)[:4]
    sheet=Image.new('RGB',(1024,4*557),'white');font=ImageFont.truetype(FONT,17)
    for row,pair in enumerate(selected):
        i,j=pair['from'],pair['to'];a=Image.fromarray(images[i]);b=Image.fromarray(images[j]);card=Image.new('RGB',(1024,557),'white');card.paste(a,(0,45));card.paste(b,(512,45));d=ImageDraw.Draw(card)
        d.text((10,12),f"Views {i}→{j}: {pair['neighborhood_supported_matches']} neighborhood-supported candidates; NOT verified vertices",font=font,fill='black')
        for k,(aa,bb) in enumerate(list(maps[i,j].items())[:25]):
            x,y=points[i][aa];u,v=points[j][bb];color=('#ee3b3b','#237dc5','#1c9959','#a23dba')[k%4]
            d.line((x,y+45,u+512,v+45),fill=color,width=1);d.ellipse((x-3,y+42,x+3,y+48),outline=color,width=2);d.ellipse((u+509,v+42,u+515,v+48),outline=color,width=2)
        sheet.paste(card,(0,row*557))
    sheet.save(output/'adjacent_candidates.png')
    # All-view junction evidence without any invented correspondence labels.
    overview=Image.new('RGB',(1024,600),'white');d=ImageDraw.Draw(overview)
    for i,rgb in enumerate(images):
        cell=Image.fromarray(rgb).resize((256,256));dc=ImageDraw.Draw(cell)
        for x,y in points[i]:dc.ellipse((x/2-1,y/2-1,x/2+1,y/2+1),fill='#d62b35')
        overview.paste(cell,((i%4)*256,40+(i//4)*280));d.text(((i%4)*256+5,15+(i//4)*280),f"View {i}: {len(points[i])} candidates",font=ImageFont.truetype(FONT,15),fill='black')
    overview.save(output/'junction_candidates.png')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--ratio',type=float,default=.72);a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):p.error('Refusing to overwrite nonempty output')
    r=run(a.input,a.output,a.ratio);print(json.dumps({k:v for k,v in r.items() if k not in ['heldout_requested_camera_diagnostic','pairs','three_view_cycles']},indent=2))
