"""Prepare observed quad fragments for the existing triangle renderer, without completion."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def prepare(source, output):
    source,output=Path(source),Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Refusing to overwrite a nonempty output directory')
    lines=source.read_text().splitlines()
    if lines[:2]!=['ply','format ascii 1.0']:
        raise ValueError('Expected ASCII PLY')
    end=lines.index('end_header');header=lines[:end]
    nv=int(next(s.split()[-1] for s in header if s.startswith('element vertex ')))
    nf=int(next(s.split()[-1] for s in header if s.startswith('element face ')))
    if nv<4 or nf<1 or len(lines)!=end+1+nv+nf:
        raise ValueError('Unexpected vertex/face count')
    vertices=[list(map(float,s.split())) for s in lines[end+1:end+1+nv]]
    if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vertices):
        raise ValueError('Expected finite xyz-only vertices')
    quads=[list(map(int,s.split())) for s in lines[end+1+nv:]]
    if any(len(q)!=5 or q[0]!=4 or len(set(q[1:]))!=4 or min(q[1:])<0 or max(q[1:])>=nv for q in quads):
        raise ValueError('Expected four distinct valid indices per quad')
    faces=[];parents=[]
    for i,(_,a,b,c,d) in enumerate(quads):
        faces.extend([[a,b,c],[a,c,d]]);parents.extend([i,i])
    payload={'vertices':vertices,'faces':faces,'colors':[[.68,.68,.68]]*nv}
    provenance={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'source_vertices':nv,'source_quads':nf,'display_triangles':len(faces),
                'vertex_coordinates_changed':False,'transform':'identity',
                'triangulation':'Each observed quad [a,b,c,d] becomes [a,b,c] and [a,c,d]. No extra vertices or hidden faces. Nonplanar quads require this explicit display diagonal.',
                'parent_quad_for_each_triangle':parents,
                'status':'Display conversion only; no correspondence, camera or surface validity is established.'}
    output.mkdir(parents=True,exist_ok=True)
    (output/'mesh.json').write_text(json.dumps(payload))
    (output/'display_provenance.json').write_text(json.dumps(provenance,indent=2))
    return provenance


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output),indent=2))

if __name__=='__main__':main()
