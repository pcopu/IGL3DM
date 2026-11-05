"""Automatic largest-component cleanup; never select anatomy by hand."""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Refusing to overwrite a nonempty output directory')
    mesh=trimesh.load(args.input/'model.ply',force='mesh')
    parts=sorted(mesh.split(only_watertight=False),key=lambda m:len(m.faces),reverse=True)
    if not parts:parser.error('Input has no mesh components')
    keep=parts[0]
    args.output.mkdir(parents=True,exist_ok=True)
    keep.export(args.output/'model.ply')
    (args.output/'mesh.json').write_text(json.dumps({'vertices':keep.vertices.tolist(),'faces':keep.faces.tolist(),'colors':np.tile([.68,.68,.68],(len(keep.vertices),1)).tolist()}))
    report={'rule':'Keep component with largest triangle count, no anatomical selection','raw_component_face_counts':[len(p.faces) for p in parts],'discarded_faces':sum(len(p.faces) for p in parts[1:]),'discarded_volume':sum(p.volume for p in parts[1:]),'vertices':len(keep.vertices),'faces':len(keep.faces),'components':1,'watertight':bool(keep.is_watertight),'winding_consistent':bool(keep.is_winding_consistent),'degenerate_faces':int((keep.area_faces<1e-12).sum()),'self_intersections_checked':False}
    (args.output/'integrity.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
