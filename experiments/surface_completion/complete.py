"""Automatic radial log-spherical-harmonic completion; no learned/manual geometry.

A closed genus-zero star-shaped prior, NOT an assertion of measured hidden surface.
Consumes candidate_points.json records with xyz or a plain Nx3 JSON array.
"""
import argparse
from pathlib import Path
import json
import numpy as np
from scipy.spatial import ConvexHull, cKDTree
from scipy.special import sph_harm_y
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def directions(n):
    z = 1 - 2 * (np.arange(n) + .5) / n
    a = np.arange(n) * np.pi * (3 - np.sqrt(5))
    return np.column_stack((np.sqrt(1-z*z)*np.cos(a), np.sqrt(1-z*z)*np.sin(a), z))


def basis(u, degree):
    theta = np.arccos(np.clip(u[:, 2], -1, 1))
    phi = np.arctan2(u[:, 1], u[:, 0])
    cols, penalty = [], []
    for l in range(degree+1):
        for m in range(-l, l+1):
            h = sph_harm_y(l, abs(m), theta, phi)
            cols.append(h.real if m == 0 else np.sqrt(2)*(h.imag if m < 0 else h.real))
            penalty.append((l*(l+1))**2)
    return np.column_stack(cols), np.array(penalty)


def fit(points, center, degree=8, regularization=.0001):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 4 or not np.isfinite(points).all():
        raise ValueError("Require at least four finite 3D points")
    if degree < 0 or regularization <= 0:
        raise ValueError("Require degree >= 0 and positive regularization")
    p = points-center
    radius = np.linalg.norm(p, axis=1)
    if np.any(radius < 1e-9):
        raise ValueError('Point at chosen center; radial parameterization undefined')
    u = p/radius[:, None]
    A, penalty = basis(u, degree)
    # Normalize objective by N so lambda is independent of number of points.
    coefficient = np.linalg.solve(A.T@A/len(A)+regularization*np.diag(penalty)+1e-12*np.eye(A.shape[1]), A.T@np.log(radius)/len(A))
    def predict(query):
        B, _ = basis(query, degree)
        radius = np.exp(B@coefficient)
        if not np.isfinite(radius).all() or np.any(radius <= 0):
            raise ValueError("Nonfinite or nonpositive extrapolated radius")
        return radius
    return predict


def topology(vertices, faces):
    edges = np.sort(np.concatenate([faces[:, [0,1]], faces[:, [1,2]], faces[:, [2,0]]]), axis=1)
    unique, inverse, counts = np.unique(edges, axis=0, return_counts=True, return_inverse=True)
    directed = np.concatenate([faces[:, [0,1]], faces[:, [1,2]], faces[:, [2,0]]])
    signs = np.where(directed[:,0] < directed[:,1], 1, -1)
    orientation = np.bincount(inverse, weights=signs)
    graph = coo_matrix((np.ones(len(unique)), (unique[:,0], unique[:,1])),shape=(len(vertices),len(vertices)))
    components = connected_components(graph,directed=False,return_labels=False)
    normals = np.cross(vertices[faces[:,1]]-vertices[faces[:,0]], vertices[faces[:,2]]-vertices[faces[:,0]])
    return dict(connected_components=int(components), inconsistent_edge_winding=int(np.sum(orientation != 0)), vertices=len(vertices), triangles=len(faces), boundary_edges=int(np.sum(counts==1)), nonmanifold_edges=int(np.sum(counts>2)), euler=int(len(vertices)-len(counts)+len(faces)), degenerate_triangles=int(np.sum(np.linalg.norm(normals,axis=1)<1e-12)), signed_volume=float(np.sum(vertices[faces[:,0]]*normals)/6))


def mesh(u, radius, center):
    faces=ConvexHull(u).simplices.copy()
    a,b,c=u[faces[:,0]],u[faces[:,1]],u[faces[:,2]]
    flip=np.einsum('ij,ij->i',np.cross(b-a,c-a),a)<0
    faces[flip]=faces[flip][:,[0,2,1]]
    return u*radius[:,None]+center,faces


def save_mesh(path, vertices, faces):
    with Path(path).open('w') as f:
        f.write('ply\nformat ascii 1.0\ncomment Automatic PRIOR completion; unobserved regions inferred; no texture\n')
        f.write(f'element vertex {len(vertices)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n')
        for p in vertices: f.write(' '.join(map(str,p))+'\n')
        for t in faces: f.write('3 '+' '.join(map(str,t))+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--center',nargs=3,type=float,required=True,help='Explicit gauge-space interior center; must be justified')
    p.add_argument('--degree',type=int,default=8);p.add_argument('--regularization',type=float,default=.0001)
    p.add_argument('--vertices',type=int,default=4096)
    a=p.parse_args(); raw=json.loads(a.input.read_text()); xyz=np.array([r['xyz'] for r in raw] if isinstance(raw[0],dict) else raw)
    if a.output.exists(): raise ValueError('Refusing to overwrite output directory')
    predict=fit(xyz,np.array(a.center),a.degree,a.regularization);u=directions(a.vertices);radius=predict(u)
    v,f=mesh(u,radius,np.array(a.center));a.output.mkdir(parents=True)
    save_mesh(a.output/'completed_prior.ply',v,f)
    obs=xyz-a.center;obs/=np.linalg.norm(obs,axis=1)[:,None]
    dist,_=cKDTree(obs).query(u);angle=np.rad2deg(2*np.arcsin(np.clip(dist/2,0,1)))
    np.savez_compressed(a.output/'support.npz',angle_to_nearest_observation_deg=angle)
    report={'topology':topology(v,f),'input_points':len(xyz),'center':a.center,'degree':a.degree,'regularization':a.regularization,'fraction_vertices_over_20deg_from_observation':float(np.mean(angle>20)), 'warning':'Closed prior completion, not measured hidden geometry; no texture or original squares; no calibration validation or resemblance claim.'}
    (a.output/'metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__': main()
