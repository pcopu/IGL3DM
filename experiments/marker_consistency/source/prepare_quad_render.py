"""Prepare observed quad fragments for the existing triangle renderer, without completion."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def triangle_topology(vertices, faces):
    """Count the displayed surface, distinguishing unused candidate points."""
    edges = Counter(tuple(sorted((a, b))) for face in faces
                    for a, b in zip(face, face[1:] + face[:1]))
    used = sorted({i for face in faces for i in face})
    parent = {i: i for i in used}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in edges:
        parent[find(a)] = find(b)
    components = Counter(find(i) for i in used)
    zero_area = 0
    for a, b, c in faces:
        u = [vertices[b][k] - vertices[a][k] for k in range(3)]
        v = [vertices[c][k] - vertices[a][k] for k in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        zero_area += all(value == 0 for value in cross)
    return {
        'input_vertices': len(vertices), 'vertices_used_by_faces': len(used),
        'unused_candidate_points': len(vertices) - len(used),
        'display_triangles': len(faces),
        'face_connected_components_by_shared_vertex': len(components),
        'component_used_vertex_counts_descending': sorted(components.values(), reverse=True),
        'boundary_edges': sum(n == 1 for n in edges.values()),
        'nonmanifold_edges': sum(n > 2 for n in edges.values()),
        'zero_area_display_triangles': zero_area,
        'watertight_edge_incidence': bool(edges) and all(n == 2 for n in edges.values()),
        'surface_winding_orientability_checked': False,
        'self_intersections_checked': False,
        'notes': 'Counts only; no coordinate, winding, connectivity or surface repair.'}


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
                'display_topology':triangle_topology(vertices, faces),
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
