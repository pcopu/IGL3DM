"""Detect closed quad cells, weld shared corners, assign software IDs and track adjacency.

All cross-view IDs and inferred 3D remain candidates until independently validated.
"""
from pathlib import Path
import argparse,json,itertools,hashlib
import numpy as np
import cv2
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw,ImageFont
from grid_tracks import mutual_context
from geometry import analyze_tracks,fit_point,summary
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def detect_cells(gray):
    white=(gray>165).astype(np.uint8);n,labels,stats,_=cv2.connectedComponentsWithStats(white,8)
    cells=[]
    for k in range(1,n):
        x,y,w,h,area=stats[k]
        if x<8 or y<8 or x+w>=gray.shape[1]-8 or y+h>=gray.shape[0]-8 or area<9 or area>900 or min(w,h)<3 or max(w,h)>70:continue
        region=(labels[y:y+h,x:x+w]==k).astype(np.uint8)
        contours,_=cv2.findContours(region,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if not contours:continue
        con=max(contours,key=cv2.contourArea);length=cv2.arcLength(con,True);quad=None
        for eps in [.035,.045,.055,.065,.075,.085]:
            ap=cv2.approxPolyDP(con,eps*length,True)
            if len(ap)==4 and cv2.isContourConvex(ap):quad=ap[:,0,:].astype(float)+[x,y];break
        if quad is None or min(np.linalg.norm(quad-np.roll(quad,1,axis=0),axis=1))<2:continue
        center=quad.mean(0);angle=np.arctan2(quad[:,1]-center[1],quad[:,0]-center[0]);quad=quad[np.argsort(angle)]
        cells.append({'cell_id':len(cells),'corners':quad.tolist(),'center':center.tolist(),'white_area':int(area)})
    raw=np.array([p for c in cells for p in c['corners']]);parents=list(range(len(raw)));member_cells={i:{i//4} for i in range(len(raw))}
    def root(a):
        while parents[a]!=a:parents[a]=parents[parents[a]];a=parents[a]
        return a
    if len(raw):
        for a,b in sorted(cKDTree(raw).query_pairs(3.2),key=lambda ab:np.linalg.norm(raw[ab[0]]-raw[ab[1]])):
            ra,rb=root(a),root(b)
            if ra==rb or member_cells[ra]&member_cells[rb]:continue
            da=raw[a]-cells[a//4]['center'];db=raw[b]-cells[b//4]['center']
            if np.dot(da,db)>0.5*np.linalg.norm(da)*np.linalg.norm(db):continue
            if len(member_cells[ra]|member_cells[rb])>6:continue
            parents[ra]=rb;member_cells[rb]|=member_cells[ra]
    groups={}
    for i in range(len(raw)):groups.setdefault(root(i),[]).append(i)
    ids={};nodes=[]
    for members in groups.values():
        nid=len(nodes);xy=raw[members].mean(0);nodes.append({'node_id':nid,'xy':xy.tolist(),'cell_ids':sorted(set(i//4 for i in members))})
        for i in members:ids[i]=nid
    good=[];bad=[]
    for c in cells:
        c['node_ids']=[ids[c['cell_id']*4+i] for i in range(4)]
        if len(set(c['node_ids']))<4:bad.append(c['cell_id'])
        else:good.append(c)
    edges={}
    for c in good:
        for i in range(4):
            edge=tuple(sorted([c['node_ids'][i],c['node_ids'][(i+1)%4]]));edges.setdefault(edge,[]).append(c['cell_id'])
    neighbors={c['cell_id']:set() for c in good};ambiguous=[]
    for edge,cc in edges.items():
        if len(cc)==2:neighbors[cc[0]].add(cc[1]);neighbors[cc[1]].add(cc[0])
        elif len(cc)>2:ambiguous.append({'edge':edge,'cells':cc})
    for c in good:c['neighbor_cell_ids']=sorted(neighbors[c['cell_id']])
    return {'cells':good,'nodes':nodes,'rejected_collapsed_cells':bad,'ambiguous_shared_edges':ambiguous,
            'note':'Closed white regions approximated as convex four-sided cells. Shared corners are clustered within3.2px; thin/merged/occluded cells can be missed or wrongly joined.'}


def run(input_path,output,ratio=.85):
    if output.exists() and any(output.iterdir()):raise ValueError('Refusing nonempty output')
    output.mkdir(parents=True);im=Image.open(input_path).convert('RGB');w,h=im.size;graphs=[];images=[];descs=[];lookup=[]
    sift=cv2.SIFT_create()
    for v in range(8):
        box=(round(v%4*w/4),round(v//4*h/2),round((v%4+1)*w/4),round((v//4+1)*h/2));cell=im.crop(box).resize((512,512),Image.Resampling.LANCZOS);rgb=np.array(cell)
        g=detect_cells(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY));g['view']=v;graphs.append(g);images.append(rgb)
        kp=[cv2.KeyPoint(float(c['center'][0]),float(c['center'][1]),float(np.clip(np.sqrt(c['white_area'])*3,18,36)),0) for c in g['cells']]
        _,dd=sift.compute(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY),kp);descs.append(dd);lookup.append({c['cell_id']:j for j,c in enumerate(g['cells'])})
    pairs=[];node_maps={};cell_maps={}
    for i in range(8):
        j=(i+1)%8;raw=mutual_context(descs[i],descs[j],ratio)
        cm={graphs[i]['cells'][a]['cell_id']:graphs[j]['cells'][b]['cell_id'] for a,b,d in raw}
        good=[];votes={}
        targetbyid={c['cell_id']:c for c in graphs[j]['cells']}
        for a,b,dist in raw:
            ca,cb=graphs[i]['cells'][a],graphs[j]['cells'][b]
            supporting=[x for x in ca['neighbor_cell_ids'] if cm.get(x) in cb['neighbor_cell_ids']]
            if not supporting:continue
            # Screen-local cyclic orientation, corroborated by neighboring matched cells.
            # This is an assumption, not proof of a physical corner's identity.
            p=np.asarray(ca['corners'])-ca['center'];q=np.asarray(cb['corners'])-cb['center'];p/=np.linalg.norm(p);q/=np.linalg.norm(q)
            costs=[float(np.sum((p-np.roll(q,k,axis=0))**2)) for k in range(4)];shift=int(np.argmin(costs));targetnodes=np.roll(cb['node_ids'],shift)
            pairs_nodes=[]
            for na,nb in zip(ca['node_ids'],targetnodes):
                key=(int(na),int(nb));votes.setdefault(key,[]).append((ca['cell_id'],cb['cell_id']));pairs_nodes.append(key)
            good.append({'from_cell_id':ca['cell_id'],'to_cell_id':cb['cell_id'],'descriptor_l2':dist,'supporting_neighbor_cell_ids':supporting,'assumed_cyclic_corner_shift':shift,'corner_shape_cost':min(costs),'corner_pairs':pairs_nodes})
        # At least two matched closed cells must agree on a corner identity.
        supported=[(a,b,cs) for (a,b),cs in votes.items() if len(cs)>=2]
        src_counts={a:sum(x==a for x,y,z in supported) for a,b,c in supported};dst_counts={b:sum(y==b for x,y,z in supported) for a,b,c in supported}
        qualified=[(a,b,cs) for a,b,cs in supported if src_counts[a]==1 and dst_counts[b]==1]
        node_maps[i,j]={a:b for a,b,cs in qualified};cell_maps[i,j]={m['from_cell_id']:m['to_cell_id'] for m in good}
        pairs.append({'from_view':i,'to_view':j,'raw_mutual_cell_matches':len(raw),'neighbor_supported_cell_matches':good,'corner_matches':[{'from_node_id':a,'to_node_id':b,'supporting_cell_pairs':cs} for a,b,cs in qualified],'rejected_corner_conflicts':len(supported)-len(qualified)})
    parents={}
    def root(a):
        parents.setdefault(a,a)
        if parents[a]!=a:parents[a]=root(parents[a])
        return parents[a]
    for (i,j),matches in node_maps.items():
        for a,b in matches.items():parents[root((i,a))]=root((j,b))
    groups={}
    for a in list(parents):groups.setdefault(root(a),[]).append(a)
    valid=[n for n in groups.values() if len({v for v,k in n})==len(n)];conflicts=len(groups)-len(valid)
    tracks={f'vertex_{t:04d}':{v:graphs[v]['nodes'][n]['xy'] for v,n in nodes} for t,nodes in enumerate(valid)}
    diag=analyze_tracks(tracks,256,(256,256),(1,5));allfit=[]
    for t,(name,obs) in enumerate(tracks.items()):
        xyz,rank,cond=fit_point(list(obs.items()),256,(256,256))
        if rank<3 or cond>10:continue
        local=analyze_tracks({name:obs},256,(256,256),heldout=())
        loop=local['three_view_loop_px'];status='two_view_unvalidated' if len(obs)==2 else 'conditional_consistency_only' if loop['p95'] is not None and loop['p95']<=3 else 'multi_view_disagrees'
        allfit.append({'track_id':name,'xyz':xyz.tolist(),'observations':obs,'view_node_ids':valid[t],'condition':cond,'status':status,'all_view_fit_px':local['training_reprojection_px'],'three_view_prediction_px':loop})
    # Actual mathematical point output, never a manually sculpted model.
    cloud=output/'candidate_points.ply'
    with cloud.open('w') as f:
        f.write('ply\nformat ascii 1.0\ncomment exploratory generated-image quad-corner candidates; uncalibrated cameras\n'+f'element vertex {len(allfit)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
        for p in allfit:
            rgb=(30,160,70) if p['status']=='conditional_consistency_only' else (210,100,30)
            f.write(' '.join(map(str,p['xyz']+list(rgb)))+'\n')
    result={'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),'settings':{'ink_threshold':165,'corner_weld_px':3.2,'descriptor_ratio':ratio,'corner_vote_minimum':2,'cell_size':512,'cameras':'ASSUMED level orthographic 45-degree yaw increments; not calibrated'},
      'closed_quad_cells_per_view':[len(g['cells']) for g in graphs],'shared_corner_nodes_per_view':[len(g['nodes']) for g in graphs],
      'adjacent_pair_counts':[{'views':[p['from_view'],p['to_view']],'raw_cells':p['raw_mutual_cell_matches'],'supported_cells':len(p['neighbor_supported_cell_matches']),'supported_corners':len(p['corner_matches'])} for p in pairs],
      'candidate_corner_tracks':len(tracks),'track_length_histogram':{str(n):sum(len(t)==n for t in tracks.values()) for n in range(2,9)},'rejected_track_components':conflicts,
      'triangulated_candidate_points':len(allfit),'conditional_3view_consistent_points':sum(p['status']=='conditional_consistency_only' for p in allfit),
      'heldout_requested_camera_diagnostic':diag,'mesh_exported':False,'mesh_reason':'No dense globally justified cross-view shared-cell surface established. Do not connect unrelated candidate points just to produce a mesh.',
      'caveats':['Local software IDs are detections, not original generated vertex IDs. Persistent IDs are only candidate matches.','Corner welding, cyclic orientation and repeated-cell appearance can be wrong.','Two-view fit has no held-out evidence. Three-view consistency is conditional on uncalibrated requested cameras.','Missing support ends a track; hidden vertices are not invented or reattached.','No original 3D ground truth exists for this generated input.']}
    (output/'quad_graph.json').write_text(json.dumps(graphs,indent=2));(output/'cell_matches.json').write_text(json.dumps(pairs,indent=2));(output/'candidate_vertices.json').write_text(json.dumps(allfit,indent=2));(output/'metrics.json').write_text(json.dumps(result,indent=2))
    # Software tags: rendered only after ImageGen, never requested from the generator.
    sheet=Image.new('RGB',(2048,1120),'white');font=ImageFont.truetype(FONT,10);titlefont=ImageFont.truetype(FONT,18)
    persistent={}
    for t,nodes in enumerate(valid):
        for v,n in nodes:persistent[v,n]=t
    for v,rgb in enumerate(images):
        pic=Image.fromarray(rgb);d=ImageDraw.Draw(pic)
        for c in graphs[v]['cells']:
            poly=[tuple(graphs[v]['nodes'][n]['xy']) for n in c['node_ids']];d.line(poly+[poly[0]],fill='#1676bc',width=1)
            if c['white_area']>=35:d.text(tuple(c['center']),f"c{c['cell_id']}",font=font,fill='#9d169c',anchor='mm',stroke_width=1,stroke_fill='white')
        for n in graphs[v]['nodes']:
            if (v,n['node_id']) in persistent:
                x,y=n['xy'];d.ellipse((x-3,y-3,x+3,y+3),fill='#e3272b');d.text((x+3,y),f"p{persistent[v,n['node_id']]}",font=font,fill='#b51a20',stroke_width=1,stroke_fill='white')
        x=v%4*512;y=v//4*560;sheet.paste(pic,(x,y+40));ImageDraw.Draw(sheet).text((x+10,y+9),f"View {v}: {len(graphs[v]['cells'])} quads | c=local cell, p=candidate track",font=titlefont,fill='black')
    sheet.save(output/'software_tagged_cells.png')
    # Inspect actual inferred points in three projections, not a drawn lion substitute.
    canvas=Image.new('RGB',(1200,450),'#f5f7f8');d=ImageDraw.Draw(canvas)
    if allfit:
        pts=np.asarray([p['xyz'] for p in allfit]);extent=max(np.ptp(pts,axis=0).max(),1e-5);mid=(pts.max(0)+pts.min(0))/2
        for col,(a,b,label) in enumerate([(0,2,'X/Z'),(1,2,'Y/Z'),(0,1,'X/Y')]):
            d.text((col*400+15,15),f'Actual candidate points: {label}',font=titlefont,fill='black')
            for p,row in zip(allfit,pts):
                x=col*400+200+(row[a]-mid[a])/extent*330;y=230-(row[b]-mid[b])/extent*330;color='#168343' if p['status']=='conditional_consistency_only' else '#c77726';d.ellipse((x-3,y-3,x+3,y+3),fill=color)
    else:d.text((20,100),'No triangulatable corner tracks found; no points invented.',font=titlefont,fill='black')
    d.text((15,415),'Assumed cameras. Orange = unvalidated/disagreeing. Green = conditional 3-view consistency only. No ground truth.',font=ImageFont.truetype(FONT,16),fill='black');canvas.save(output/'triangulated_candidate_points.png')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--ratio',type=float,default=.85);a=p.parse_args();r=run(a.input,a.output,a.ratio)
    print(json.dumps({k:v for k,v in r.items() if k not in ['heldout_requested_camera_diagnostic','caveats']},indent=2))
