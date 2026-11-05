#!/usr/bin/env python3
"""Render an inferred mesh in Blender without changing its geometry.

Run with Blender's Python, for example::

    blender -b --python scripts/render_mesh.py -- \
        --mesh /path/to/mesh.json --output /path/to/renders

The JSON object has ``vertices`` (N x 3), triangle ``faces`` (M x 3), and
optional ``colors`` (N x 3 sRGB floats). The default model coordinates are
z-up, in [-1, 1], viewed with orthographic scale 2.0. At yaw zero the camera
is on negative y; positive yaw moves it toward positive x.

Every color frame is an actual Blender render of the unchanged mesh. Numeric
depth/position maps are exact pixel-center BVH ray intersections with that
same mesh, not values decoded from generated artwork. They have a binary
validity mask and no anti-aliasing. PNG previews are separate from the raw
float32 NPZ data. No image-generation service, network, or model is needed.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys
import time
import zlib

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--views", type=int, default=16)
    parser.add_argument("--elevation", type=float, default=0.0)
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--distance", type=float, default=4.0)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--midpoints", action="store_true", help="Also render unseen yaw midpoints")
    parser.add_argument("--skip-data", action="store_true", help="Skip numeric depth/position outputs")
    parser.add_argument("--save-blend", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if args.size < 1 or args.views < 1 or args.samples < 1:
        parser.error("size, views and samples must be positive")
    if not (args.scale > 0 and args.distance > 0 and -89 < args.elevation < 89):
        parser.error("scale/distance must be positive; elevation must be between -89 and 89")
    return args


def load_mesh(path):
    payload = json.loads(path.read_text())
    vertices = np.asarray(payload["vertices"], dtype=np.float64)
    raw_faces = np.asarray(payload["faces"])
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 3:
        raise ValueError("vertices must be a nonempty N x 3 array")
    if not np.isfinite(vertices).all():
        raise ValueError("vertices contain nonfinite values")
    if raw_faces.ndim != 2 or raw_faces.shape[1] != 3 or len(raw_faces) == 0:
        raise ValueError("faces must be a nonempty M x 3 triangle array")
    if not np.issubdtype(raw_faces.dtype, np.integer):
        raise ValueError("face indices must be integers")
    faces = raw_faces.astype(np.int32)
    if faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError("face indices are outside the vertex array")
    colors = np.asarray(payload.get("colors", np.tile([0.83, 0.43, 0.18], (len(vertices), 1))), dtype=np.float64)
    if colors.shape != vertices.shape or not np.isfinite(colors).all():
        raise ValueError("colors must be a finite N x 3 array")
    if (colors < 0).any() or (colors > 1).any():
        raise ValueError("color values must be in [0, 1]")
    return vertices, faces, colors


def srgb_to_linear(rgb):
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def create_scene(vertices, faces, colors, args):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    mesh = bpy.data.meshes.new("ReconstructedMesh")
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()
    obj = bpy.data.objects.new("ReconstructedMesh", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    color_attr = mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    rgba = np.column_stack([srgb_to_linear(colors), np.ones(len(colors))]).astype(np.float32)
    color_attr.data.foreach_set("color", rgba.ravel())
    mesh.color_attributes.active_color = color_attr
    material = bpy.data.materials.new("ReferenceVertexColors")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    color = nodes.new("ShaderNodeVertexColor")
    color.layer_name = "Col"
    output = nodes.new("ShaderNodeOutputMaterial")
    # Direct color-to-surface is Blender's implicit unlit emission. Unlike an
    # explicit Emission shader, the glTF exporter recognizes this graph as
    # KHR_materials_unlit and preserves vertex colors in external viewers.
    material.node_tree.links.new(color.outputs["Color"], output.inputs["Surface"])
    mesh.materials.append(material)

    camera_data = bpy.data.cameras.new("OrthographicCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = args.scale
    camera_data.clip_start = 0.001
    camera_data.clip_end = args.distance + max(10.0, 2 * float(np.linalg.norm(vertices, axis=1).max()))
    camera = bpy.data.objects.new("OrthographicCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    # This environment's Blender build has no OpenImageDenoise.
    scene.cycles.use_denoising = False
    scene.cycles.samples = args.samples
    scene.render.resolution_x = args.size
    scene.render.resolution_y = args.size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.dither_intensity = 0
    scene.render.use_file_extension = True
    return scene, camera, obj


def camera_basis(yaw, elevation, distance):
    theta, phi = math.radians(yaw), math.radians(elevation)
    right = np.array([math.cos(theta), math.sin(theta), 0.0])
    forward = np.array([-math.sin(theta) * math.cos(phi), math.cos(theta) * math.cos(phi), -math.sin(phi)])
    up = np.cross(right, forward)
    position = -distance * forward
    return position, right, up, forward


def png_bytes(array, color_type, bit_depth):
    """Lossless diagnostic PNG with no gamma/color-management metadata."""
    height, width = array.shape[:2]
    if bit_depth == 16:
        data = array.astype(">u2", copy=False)
    else:
        data = array.astype(np.uint8, copy=False)
    rows = data.reshape(height, -1).view(np.uint8).reshape(height, -1)
    raw = b"".join(b"\x00" + row.tobytes() for row in rows)

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def trace_maps(tree, position, right, up, forward, args, bbox_min, bbox_max, stem):
    n = args.size
    positions = np.full((n, n, 3), np.nan, np.float32)
    depth = np.full((n, n), np.nan, np.float32)
    face_index = np.full((n, n), -1, np.int32)
    direction = Vector(forward.tolist())
    radius = max(float(np.linalg.norm(bbox_min)), float(np.linalg.norm(bbox_max)), args.scale)
    ray_length = args.distance + 2 * radius + 1.0
    for y in range(n):
        row_origin = position + ((0.5 - (y + 0.5) / n) * args.scale) * up
        for x in range(n):
            origin = row_origin + (((x + 0.5) / n - 0.5) * args.scale) * right
            location, _normal, index, ray_distance = tree.ray_cast(Vector(origin.tolist()), direction, ray_length)
            if location is not None:
                positions[y, x] = tuple(location)
                depth[y, x] = ray_distance
                face_index[y, x] = index
    mask = face_index >= 0
    world_from_camera = np.eye(4, dtype=np.float64)
    world_from_camera[:3, :3] = np.column_stack((right, up, -forward))
    world_from_camera[:3, 3] = position
    np.savez_compressed(stem.with_suffix(".npz"), depth=depth, position=positions,
                        mask=mask, face_index=face_index,
                        world_from_camera=world_from_camera,
                        camera_from_world=np.linalg.inv(world_from_camera),
                        orthographic_scale=np.float64(args.scale),
                        bbox_min=bbox_min, bbox_max=bbox_max)
    # Shared display range across all views, not per-frame normalization.
    near, far = args.distance - radius, args.distance + radius
    depth_preview = np.zeros((n, n), np.uint16)
    depth_preview[mask] = 1 + np.rint(np.clip((far - depth[mask]) / (far - near), 0, 1) * 65534).astype(np.uint16)
    stem.with_name(stem.name + "_depth.png").write_bytes(png_bytes(depth_preview, 0, 16))
    xyz_preview = np.zeros((n, n, 4), np.uint8)
    extent = np.maximum(bbox_max - bbox_min, 1e-12)
    xyz_preview[mask, :3] = np.rint(np.clip((positions[mask] - bbox_min) / extent, 0, 1) * 255).astype(np.uint8)
    xyz_preview[mask, 3] = 255
    stem.with_name(stem.name + "_position.png").write_bytes(png_bytes(xyz_preview, 6, 8))
    return {"hit_pixels": int(mask.sum()), "depth_min": float(depth[mask].min()) if mask.any() else None,
            "depth_max": float(depth[mask].max()) if mask.any() else None,
            "preview_depth_near": near, "preview_depth_far": far}


def main():
    args = arguments()
    started = time.monotonic()
    vertices, faces, colors = load_mesh(args.mesh)
    args.output.mkdir(parents=True, exist_ok=True)
    for directory in ("color", "data"):
        (args.output / directory).mkdir(exist_ok=True)
    scene, camera, obj = create_scene(vertices, faces, colors, args)
    # Selection-only excludes the inspection camera from the portable model.
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    glb_path = args.output / "model.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True,
                             export_yup=True, export_normals=True, export_materials="EXPORT")
    tree = BVHTree.FromPolygons(vertices.tolist(), faces.tolist(), all_triangles=True)
    bbox_min, bbox_max = vertices.min(axis=0), vertices.max(axis=0)
    angles = [(i * 360.0 / args.views, False) for i in range(args.views)]
    if args.midpoints:
        angles += [((i + 0.5) * 360.0 / args.views, True) for i in range(args.views)]
    records = []
    for i, (yaw, midpoint) in enumerate(angles):
        stem = ("midpoint" if midpoint else "view") + f"_{i % args.views:03d}"
        position, right, up, forward = camera_basis(yaw, args.elevation, args.distance)
        camera.location = tuple(position)
        camera.rotation_euler = Vector(forward.tolist()).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(args.output / "color" / (stem + ".png"))
        bpy.ops.render.render(write_still=True)
        record = {"stem": stem, "yaw_degrees": yaw, "elevation_degrees": args.elevation,
                  "unseen_midpoint": midpoint, "camera_position": position.tolist(),
                  "camera_right": right.tolist(), "camera_up": up.tolist(),
                  "camera_forward": forward.tolist()}
        if not args.skip_data:
            record.update(trace_maps(tree, position, right, up, forward, args, bbox_min, bbox_max,
                                     args.output / "data" / stem))
        records.append(record)
        print("IGL3DM_RENDER", json.dumps(record), flush=True)
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output / "model.blend"))
    manifest = {
        "schema_version": 1, "renderer": f"Blender {bpy.app.version_string} Cycles CPU",
        "mesh_source": str(args.mesh.resolve()), "geometry_changed": False,
        "vertices": len(vertices), "triangles": len(faces), "size": args.size,
        "orthographic_scale": args.scale, "camera_distance": args.distance,
        "input_coordinates": "right-handed z-up; camera yaw 0 at negative y, positive yaw toward positive x",
        "glb_coordinates": "glTF standard y-up, converted by Blender exporter",
        "input_colors": "sRGB [0,1], converted to linear before vertex storage",
        "material": "unlit emission from vertex color, transparent background",
        "numeric_maps": "Exact BVH pixel-center intersections of the unchanged mesh; no antialiasing; NaN background",
        "depth_definition": "Positive distance along the unit camera-forward ray, from orthographic image-plane ray origin",
        "position_definition": "World-space XYZ per visible surface pixel, not a vertex-ID map",
        "pixel_coordinates": "arrays[y,x], top-left origin, pixel centers at (x+0.5,y+0.5)",
        "depth_png_decode": "0 is invalid; depth=far-(code-1)/65534*(far-near); near/far per record (shared across views)",
        "position_png_decode": "XYZ=bbox_min+(RGB/255)*(bbox_max-bbox_min); alpha 0 is invalid; approximate visualization only",
        "bbox_min": bbox_min.tolist(), "bbox_max": bbox_max.tolist(),
        "elapsed_seconds": round(time.monotonic() - started, 3), "frames": records,
    }
    (args.output / "render_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("IGL3DM_RENDER_COMPLETE", json.dumps({"output": str(args.output), "frames": len(records),
                                              "elapsed_seconds": manifest["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
