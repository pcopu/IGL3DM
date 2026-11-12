"""Image-only subpixel measurement trial; never changes identities or connectivity."""
from pathlib import Path
import argparse,copy,hashlib,json
import cv2
import numpy as np

def refine(root,images,out,max_shift=1.5):
 root,images,out=Path(root),Path(images),Path(out)
 if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output')
 old=json.loads((root/'frame_graphs.json').read_text());graphs=copy.deepcopy(old);manifest=json.loads((root/'manifest.json').read_text());video=json.loads((images/'video_manifest.json').read_text());stats=[]
 for g,frame in zip(graphs,video['frames']):
  assert g['sample_index']==frame['sample_index']
  image=cv2.imread(str(images/frame['path']),0)
  if image is None:raise ValueError('Missing frame')
  xy=np.array([n['xy'] for n in g['nodes']],np.float32)
  if len(xy):
   refined=cv2.cornerSubPix(image,xy.reshape(-1,1,2).copy(),(3,3),(-1,-1),(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,30,.001)).reshape(-1,2)
   shift=np.linalg.norm(refined-xy,axis=1);keep=np.isfinite(refined).all(1)&(shift<=max_shift)
   for n,p,k in zip(g['nodes'],refined,keep):
    if k:n['xy']=[float(v) for v in p]
   stats.append({'frame':g['sample_index'],'nodes':len(xy),'refined':int(keep.sum()),'rejected_large_or_invalid':int((~keep).sum()),'accepted_shift_px':shift[keep].tolist()})
 out.mkdir(parents=True,exist_ok=True)
 (out/'frame_graphs.json').write_text(json.dumps(graphs));manifest['original_source_sha256']=manifest['source_sha256'];manifest['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();manifest['refinement']={'algorithm':'OpenCV cornerSubPix on each original grayscale image','half_window':[3,3],'iterations':30,'epsilon':.001,'max_shift_px':max_shift,'invalid_policy':'preserve original detection','associations_changed':False,'truth_or_camera_used':False};(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 for variant in ['graph_joint','graph_joint_cycle_veto']:
  tracks=json.loads((root/variant/'tracks.json').read_text())
  for t in tracks.values():
   for o in t['observations']:o['xy']=graphs[o['sample_index']]['nodes'][o['node_id']]['xy']
  d=out/variant;d.mkdir();(d/'tracks.json').write_text(json.dumps(tracks));(d/'associations.json').write_bytes((root/variant/'associations.json').read_bytes())
 (out/'refinement_audit.json').write_text(json.dumps(stats,indent=2));print(json.dumps({'detections':sum(s['nodes'] for s in stats),'refined':sum(s['refined'] for s in stats),'rejected':sum(s['rejected_large_or_invalid'] for s in stats),'identities_and_topology_unchanged':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for x in ['input','images','output']:p.add_argument('--'+x,type=Path,required=True)
 a=p.parse_args();refine(a.input,a.images,a.output)
