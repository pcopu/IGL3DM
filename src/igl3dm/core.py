"""Image-atlas segmentation, common-camera carving and real mesh extraction.

Image-generated views are targets, not calibrated observations. These functions
make a single geometry consistent where possible; they do not identify genuine
vertices from painted wireframes or treat drawn depth colors as measurements.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


@dataclass(frozen=True)
class Camera:
    """Z-up orthographic camera: front (yaw 0) is at negative Y, right is +X."""
    yaw_degrees: float
    elevation_degrees: float = 0.0
    scale: float = 2.0

    def basis(self):
        a, e = np.deg2rad([self.yaw_degrees, self.elevation_degrees])
        right = np.array([np.cos(a), np.sin(a), 0.0])
        toward_camera = np.array([np.sin(a)*np.cos(e), -np.cos(a)*np.cos(e), np.sin(e)])
        up = np.cross(toward_camera, right)
        return right, up, toward_camera

    def project(self, points, size):
        right, up, _ = self.basis()
        uv = np.stack([points @ right, points @ up], axis=-1) / self.scale + 0.5
        # Pixel-center convention: -scale/2 maps to -0.5, not pixel center 0.
        return np.stack([uv[..., 0]*size-0.5, (1-uv[..., 1])*size-0.5], axis=-1)


def split_atlas(image: Image.Image, rows=4, columns=4, gutter=2):
    """Split equal grid boundaries, trim generated divider lines, then letterbox.

    Image generators need not honor requested pixel dimensions. Rounding grid
    boundaries changes cells by at most one pixel; a common square canvas keeps
    source scale intact instead of separately fitting/centering each animal.
    """
    if rows < 1 or columns < 1 or gutter < 0:
        raise ValueError("Grid dimensions must be positive and gutter nonnegative")
    w, h = image.size
    xs = np.rint(np.linspace(0,w,columns+1)).astype(int)
    ys = np.rint(np.linspace(0,h,rows+1)).astype(int)
    side = max(int(np.diff(xs).max()),int(np.diff(ys).max()))-2*gutter
    if min(w//columns,h//rows)-2*gutter < 16:
        raise ValueError("Atlas cells must be at least 16 pixels after trimming")
    tiles=[]
    for r in range(rows):
        for c in range(columns):
            crop=image.crop((xs[c]+gutter,ys[r]+gutter,xs[c+1]-gutter,ys[r+1]-gutter)).convert("RGBA")
            canvas=Image.new("RGBA",(side,side),(255,255,255,255))
            canvas.paste(crop,((side-crop.width)//2,(side-crop.height)//2))
            tiles.append(canvas)
    return tiles


def segment(tile: Image.Image, threshold=32.0, min_component_fraction=0.0008):
    """Infer background from border; fill enclosed white fur/wireframe regions.

    Uses alpha if meaningful. Otherwise a border-connected background-color mask
    keeps white enclosed surfaces inside a dark outline. Tiny specks are removed;
    no per-view translation, scaling or manual silhouette painting is performed.
    """
    arr = np.asarray(tile.convert("RGBA"))
    if arr[..., 3].min() < 128 and np.mean(arr[..., 3] < 128) > 0.05:
        mask = arr[..., 3] >= 128
        mode, background = "alpha", None
    else:
        rgb = arr[..., :3].astype(np.float32)
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        bg = np.median(border, axis=0)
        mask = np.linalg.norm(rgb-bg, axis=-1) > threshold
        mode, background = "border-color-distance", bg.tolist()
    mask = ndimage.binary_fill_holes(mask)
    labels, n = ndimage.label(mask)
    counts = np.bincount(labels.ravel())
    keep = counts >= max(3, int(mask.size*min_component_fraction))
    keep[0] = False
    mask = keep[labels]
    rows, cols = np.where(mask)
    fraction = float(mask.mean())
    if not 0.005 <= fraction <= 0.85:
        raise ValueError(f"Foreground fraction {fraction:.4f} is implausible; check sheet/background")
    clipped = bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any())
    info = {"mode": mode, "background_rgb": background,
            "foreground_fraction": fraction, "touches_frame": clipped,
            "bbox_xyxy": [int(cols.min()), int(rows.min()), int(cols.max()+1), int(rows.max()+1)],
            "connected_components": int(np.count_nonzero(keep)), "threshold": threshold}
    return mask, info


def grid_points(resolution):
    if not 12 <= resolution <= 256:
        raise ValueError("Voxel resolution must be between 12 and 256")
    axis = (np.arange(resolution, dtype=np.float32)+0.5)*2/resolution-1
    return np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)


def silhouette_fields(masks, cameras, points):
    if len(masks) != len(cameras):
        raise ValueError("Need exactly one camera per mask")
    result = np.empty((len(masks), len(points)), dtype=np.float32)
    for i, (mask, camera) in enumerate(zip(masks, cameras)):
        h, w = mask.shape
        if h != w:
            raise ValueError("Masks must be square")
        sdf = (ndimage.distance_transform_edt(mask)-ndimage.distance_transform_edt(~mask)).astype(np.float32)
        uv = camera.project(points, w)
        result[i] = ndimage.map_coordinates(sdf, [uv[:, 1], uv[:, 0]], order=1,
                                            mode="constant", cval=-w)
    return result


def carve(fields, resolution, allowed_misses=0, smooth_sigma=0.6):
    """A relaxed visual hull. Miss count is a declared robustness setting.

    Strict intersection is allowed_misses=0. Relaxed hulls can include a voxel
    unsupported by up to that many input views. The report always compares them.
    """
    if not 0 <= allowed_misses < fields.shape[0]:
        raise ValueError("allowed_misses must be less than the view count")
    field = np.partition(fields, allowed_misses, axis=0)[allowed_misses].reshape((resolution,)*3).copy()
    if smooth_sigma:
        field = ndimage.gaussian_filter(field, smooth_sigma)
    occupied = field > 0
    labels, count = ndimage.label(occupied)
    counts = np.bincount(labels.ravel())
    if len(counts) <= 1:
        raise ValueError("Views have no common solid at this tolerance")
    counts[0] = 0
    largest = int(counts.argmax())
    keep = labels == largest
    removed = int(np.count_nonzero(occupied & ~keep))
    field[occupied & ~keep] = -np.maximum(field[occupied & ~keep], 0.1)
    # Grid boundary must remain outside; otherwise hull is open/truncated.
    boundary_hits = int(sum(np.count_nonzero(keep.take(i, axis=a)) for a in range(3) for i in (0, -1)))
    info = {"allowed_misses": allowed_misses, "minimum_supporting_views": int(fields.shape[0]-allowed_misses),
            "voxel_count": int(keep.sum()), "component_count_before_cleanup": int(count),
            "removed_component_voxels": removed, "boundary_voxel_hits": boundary_hits,
            "smoothing_sigma_voxels": smooth_sigma}
    return field, keep, info


def project_occupancy(occupied, points, cameras, image_size):
    """Rasterize voxel footprints for selection diagnostics, not final mesh QA."""
    p = points[occupied.ravel()]
    result = []
    n = occupied.shape[0]
    for camera in cameras:
        raster = np.zeros((image_size, image_size), bool)
        if len(p):
            uv = np.rint(camera.project(p, image_size)).astype(int)
            inside = (uv[:, 0]>=0)&(uv[:, 0]<image_size)&(uv[:, 1]>=0)&(uv[:, 1]<image_size)
            raster[uv[inside, 1], uv[inside, 0]] = True
            # Conservative footprint of the voxel rather than center-only holes.
            radius = max(1, int(np.ceil(image_size/n/2)))
            raster = ndimage.binary_dilation(raster, iterations=radius)
        result.append(raster)
    return result


def mask_metrics(predictions, targets):
    rows=[]
    for pred, target in zip(predictions, targets):
        intersection = int(np.count_nonzero(pred & target))
        union = int(np.count_nonzero(pred | target))
        p, t = int(pred.sum()), int(target.sum())
        rows.append({"iou": intersection/union if union else 1.0,
                     "precision": intersection/p if p else 0.0,
                     "recall": intersection/t if t else 0.0})
    return {"per_view": rows, "mean_iou": float(np.mean([r["iou"] for r in rows])),
            "worst_iou": float(min(r["iou"] for r in rows))}


# Six tetrahedra sharing cube diagonal 0->6, with compatible neighbor faces.
_CORNERS = np.array([[0,0,0], [1,0,0], [1,1,0], [0,1,0],
                     [0,0,1], [1,0,1], [1,1,1], [0,1,1]])
_TETS = ((0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6))


def extract_mesh(field):
    """Marching tetrahedra with edge deduplication, using only NumPy.

    A one-cell negative pad closes solids at the finite volume boundary. Reports
    still flag boundary hits: closure does not turn clipped geometry into truth.
    """
    n = field.shape[0]
    f = np.pad(field, 1, constant_values=-max(1.0, abs(float(field.min()))))
    lo = np.minimum.reduce([f[x:x+n+1,y:y+n+1,z:z+n+1] for x,y,z in _CORNERS])
    hi = np.maximum.reduce([f[x:x+n+1,y:y+n+1,z:z+n+1] for x,y,z in _CORNERS])
    active = np.argwhere((lo<=0)&(hi>0))
    vertices=[]; faces=[]; edges={}
    size = f.shape[0]
    def intersection(a, b, va, vb):
        ida, idb = int((a[0]*size+a[1])*size+a[2]), int((b[0]*size+b[1])*size+b[2])
        key = (min(ida,idb),max(ida,idb))
        if key not in edges:
            t = va/(va-vb)
            pos = a+t*(b-a)
            # padded grid coordinate 1 is original first center at -1+1/n
            pos = (pos-0.5)*2/n-1
            edges[key] = len(vertices); vertices.append(pos)
        return edges[key]
    for base in active:
        corners = base+_CORNERS
        values = f[tuple(corners.T)]
        for tet in _TETS:
            inside=[i for i in tet if values[i]>0]
            outside=[i for i in tet if values[i]<=0]
            if not inside or not outside: continue
            pairs=[(i,j) for i in inside for j in outside]
            idx=[intersection(corners[i],corners[j],values[i],values[j]) for i,j in pairs]
            if len(idx)==3:
                triangles=[idx]
            else:
                # pair ordering is (in0,out0),(in0,out1),(in1,out0),(in1,out1)
                triangles=[[idx[0],idx[1],idx[3]],[idx[0],idx[3],idx[2]]]
            out_direction=corners[outside].mean(axis=0)-corners[inside].mean(axis=0)
            for tri in triangles:
                a,b,c=(vertices[i] for i in tri)
                normal=np.cross(b-a,c-a)
                if np.linalg.norm(normal) == 0: continue
                if np.dot(normal,out_direction)<0: tri=[tri[0],tri[2],tri[1]]
                faces.append(tri)
    if not faces: raise ValueError("No surface was extracted")
    return np.asarray(vertices,dtype=np.float32), np.asarray(faces,dtype=np.int32)


def mesh_integrity(vertices, faces):
    edges=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    unique, counts=np.unique(edges,axis=0,return_counts=True)
    signed_volume=float(np.einsum('ij,ij->i',vertices[faces[:,0]],
                                 np.cross(vertices[faces[:,1]],vertices[faces[:,2]])).sum()/6)
    return {"vertices":len(vertices), "triangles":len(faces), "edges":len(unique),
            "boundary_edges":int(np.count_nonzero(counts==1)),
            "nonmanifold_edges":int(np.count_nonzero(counts>2)),
            "watertight_edge_incidence":bool(np.all(counts==2)),
            "euler_characteristic":int(len(vertices)-len(unique)+len(faces)),
            "signed_volume":signed_volume,
            "self_intersections_checked":False,
            "notes":"Edge incidence is not a complete self-intersection or animation-readiness test."}


def vertex_colors(vertices, faces, tiles, masks, cameras):
    """Visibility-aware approximate color projection onto the one actual mesh.

    A point z-buffer rejects hidden samples. The source may be inconsistent;
    these are appearance colors, never vertex IDs or metric depth.
    """
    normals=np.zeros_like(vertices)
    fn=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    for k in range(3): np.add.at(normals,faces[:,k],fn)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    colors=np.zeros_like(vertices); weights=np.zeros(len(vertices),np.float32)
    for tile, mask, camera in zip(tiles,masks,cameras):
        rgb=np.asarray(tile.convert("RGB"),dtype=np.float32)/255
        size=mask.shape[0]
        uv=np.rint(camera.project(vertices,size)).astype(int)
        valid=(uv[:,0]>=0)&(uv[:,0]<size)&(uv[:,1]>=0)&(uv[:,1]<size)
        pixel=np.clip(uv[:,1],0,size-1)*size+np.clip(uv[:,0],0,size-1)
        depth=vertices@camera.basis()[2]
        zbuf=np.full(size*size,-np.inf,np.float32)
        np.maximum.at(zbuf,pixel[valid],depth[valid])
        # Neighbor max handles subpixel triangulation gaps. Tolerance is explicitly approximate.
        zbuf=ndimage.maximum_filter(zbuf.reshape(size,size),size=3).ravel()
        facing=np.maximum(normals@camera.basis()[2],0)**3
        valid &= (depth >= zbuf[pixel]-0.04)&mask[np.clip(uv[:,1],0,size-1),np.clip(uv[:,0],0,size-1)]
        w=facing*valid
        c=rgb[np.clip(uv[:,1],0,size-1),np.clip(uv[:,0],0,size-1)]
        colors+=c*w[:,None]; weights+=w
    fallback=np.array([0.55,0.55,0.55])
    colors=np.where(weights[:,None]>1e-8,colors/np.maximum(weights[:,None],1e-8),fallback)
    return np.clip(colors,0,1), {"unobserved_vertices":int(np.count_nonzero(weights<=1e-8)),
                                "method":"front-facing point-z-buffer projection; unobserved vertices gray"}


def save_ply(path, vertices, faces, colors):
    rgb=np.rint(colors*255).astype(np.uint8)
    with Path(path).open("w") as out:
        out.write(f"ply\nformat ascii 1.0\ncomment IGL3DM approximate inferred geometry\nelement vertex {len(vertices)}\n")
        out.write("property float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\n")
        out.write(f"element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n")
        for v,c in zip(vertices,rgb):out.write(" ".join(f"{x:.6f}" for x in v)+" "+" ".join(map(str,c))+"\n")
        for f in faces:out.write("3 "+" ".join(map(str,f))+"\n")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
