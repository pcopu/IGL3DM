"""Image-only closed-cell graph evidence for already observed temporal candidates.

No ground truth, camera matrices or inferred 3D is consumed. Loss of graph
support breaks a segment; identities are never rejoined across missing support.
"""
from pathlib import Path
import argparse,json,sys
import cv2
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from quad_cells import detect_cells

def canonical_cycle(nodes):
    f=list(nodes)
    return min(tuple(q[k:]+q[:k]) for q in (f,f[::-1]) for k in range(4))

def evidence(tracking_directory,output_directory,max_distance=3.,margin=1.):
    if not np.isfinite(max_distance) or max_distance<=0:raise ValueError('max_distance must be finite and positive')
    if not np.isfinite(margin) or margin<0:raise ValueError('margin must be finite and nonnegative')
    root=Path(tracking_directory);out=Path(output_directory)
    if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output directory')
    manifest=json.loads((root/'video_manifest.json').read_text());tracks=json.loads((root/'tracks.json').read_text());frames=manifest['frames'];w,h=manifest['working_size'];scale=512/h;pad=(512-w*scale)/2
    if w<=0 or h<=0 or w>h:raise ValueError('Expected positive portrait or square working dimensions')
    active=[{} for _ in frames]
    for name,t in tracks.items():
        for o in t['observations']:active[o['sample_index']][name]=np.asarray(o['xy'])*scale+[pad,0]
    records={name:[] for name in tracks};stats=[];prior_cycles=set();prior_neighbors={}
    for i,frame in enumerate(frames):
        raw=cv2.imread(str(root/frame['path']),cv2.IMREAD_GRAYSCALE)
        resized=cv2.resize(raw,(round(w*scale),512),interpolation=cv2.INTER_AREA)
        image=np.full((512,512),255,np.uint8);left=round(pad);image[:,left:left+resized.shape[1]]=resized
        graph=detect_cells(image);nodes=graph['nodes'];by_node={};by_track={};distances={};ambiguities={}
        if len(nodes)>=2:
            tree=cKDTree([n['xy'] for n in nodes]);candidate={}
            for name,p in active[i].items():
                ds,ids=tree.query(p,k=2);distances[name]=float(ds[0]);ambiguities[name]=float(ds[1]-ds[0])
                if ds[0]<=max_distance and ds[1]-ds[0]>=margin:candidate.setdefault(int(ids[0]),[]).append((float(ds[0]),name))
            for nid,nn in candidate.items():
                nn.sort()
                # Reject a collision, rather than choose one track after it drifts into another.
                if len(nn)!=1:continue
                name=nn[0][1];by_node[nid]=name;by_track[name]=nid
        neighbors={name:set() for name in active[i]};cycles=set();node_cycles={name:set() for name in active[i]}
        for c in graph['cells']:
            ids=c['node_ids']
            for a,b in zip(ids,ids[1:]+ids[:1]):
                if a in by_node and b in by_node:
                    na,nb=by_node[a],by_node[b];neighbors[na].add(nb);neighbors[nb].add(na)
            if all(n in by_node for n in ids):
                cycle=canonical_cycle([by_node[n] for n in ids])
                if len(set(cycle))!=4:continue
                cycles.add(cycle)
                for name in cycle:node_cycles[name].add(cycle)
        for name in active[i]:
            nid=by_track.get(name);stable=node_cycles[name]&prior_cycles
            records[name].append({'sample_index':i,'node_id':nid,'nearest_node_distance_px':distances.get(name),'nearest_margin_px':ambiguities.get(name),'incident_detected_cells':len(nodes[nid]['cell_ids']) if nid is not None else 0,'mapped_neighbor_track_ids':sorted(neighbors[name]),'stable_neighbor_count_from_previous':len(neighbors[name]&prior_neighbors.get(name,set())),'full_cell_count':len(node_cycles[name]),'stable_full_cell_count_from_previous':len(stable)})
        stats.append({'sample_index':i,'detected_closed_cells':len(graph['cells']),'graph_nodes':len(nodes),'active_candidates':len(active[i]),'uniquely_associated_candidates':len(by_track),'fully_associated_cells':len(cycles),'persistent_cells_from_previous':len(cycles&prior_cycles)})
        prior_cycles=cycles;prior_neighbors=neighbors
    out.mkdir(parents=True,exist_ok=True)
    result={'settings':{'normalized_height':512,'max_node_distance_px':max_distance,'min_nearest_margin_px':margin,'collision_policy':'reject all colliding candidate IDs','truth_used':False,'reconstruction_used':False},'frames':stats,'tracks':records}
    (out/'graph_evidence.json').write_text(json.dumps(result,indent=2));return result

def select_segments(tracks,evidence_record,minimum_cells=1,minimum_neighbors=2,mode='segments'):
    """Preserve original coordinates/quality, only split/reject uncertain observations."""
    result={};audit=[]
    for name,track in tracks.items():
        rr=evidence_record['tracks'][name];observations=track['observations'];flags=[]
        for k,r in enumerate(rr):
            forward=rr[k+1] if k+1<len(rr) and rr[k+1]['sample_index']==r['sample_index']+1 else None
            backward_good=(r['stable_full_cell_count_from_previous']>=minimum_cells and r['stable_neighbor_count_from_previous']>=minimum_neighbors)
            forward_good=forward is not None and forward['stable_full_cell_count_from_previous']>=minimum_cells and forward['stable_neighbor_count_from_previous']>=minimum_neighbors
            flags.append(r['node_id'] is not None and r['incident_detected_cells']>=2 and (backward_good or forward_good))
        if mode=='whole':
            if len(flags)>=3 and np.mean(flags)>=.9:
                result[name]=track.copy();result[name]['selection']='image-only graph support on >=90% observations'
            audit.append({'source_track':name,'observations':len(flags),'supported_observations':sum(flags),'retained_whole':name in result})
            continue
        start=None
        for k,good in enumerate(flags+[False]):
            if good and start is None:start=k
            if not good and start is not None:
                if k-start>=3:
                    oo=observations[start:k];key=f'{name}_g{oo[0]["sample_index"]:04d}_{oo[-1]["sample_index"]:04d}'
                    result[key]={'observations':oo,'source_track_id':name,'start_reason':'image-only closed-cell graph supported segment','end_reason':'graph support ended; no cross-gap identity reuse','selection':'at least one persistent four-ID cell and two persistent edge neighbors; unique visible junction association'}
                start=None
        audit.append({'source_track':name,'observations':len(flags),'supported_observations':sum(flags)})
    return result,audit

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tracking-directory',type=Path,required=True);p.add_argument('--output-directory',type=Path,required=True);a=p.parse_args();r=evidence(a.tracking_directory,a.output_directory);print(json.dumps({'frames':len(r['frames']),'tracks':len(r['tracks'])}))
if __name__=='__main__':main()
