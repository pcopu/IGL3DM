"""Blender full-orbit colored-quad control with geometric visibility labels.
Run blender -b --python THIS_FILE -- --output DIR --views 24 --size 512
"""
import argparse,json,math,sys,random
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dimple_control import generate,validate

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--views',type=int,default=24);p.add_argument('--size',type=int,default=512);p.add_argument('--resolution',type=int,default=24);p.add_argument('--emission',action='store_true');p.add_argument('--samples',type=int,default=16);p.add_argument('--no-dent',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output
if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output directory')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
verts,faces,unit=generate(a.resolution,not a.no_dent)
mesh=bpy.data.meshes.new('EVALUATION_ONLY_dimple');mesh.from_pydata(verts,[],faces);mesh.update()
obj=bpy.data.objects.new('EVALUATION_ONLY_dimple',mesh);bpy.context.collection.objects.link(obj)
palette=[(.8,.16,.12),(.08,.45,.8),(.95,.62,.08),(.1,.65,.28),(.65,.16,.72),(.05,.7,.68)]
def material(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.85
 if a.emission:
  nodes=m.node_tree.nodes;nodes.clear();e=nodes.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1);output=nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(e.outputs[0],output.inputs['Surface'])
 return m
for i,c in enumerate(palette):obj.data.materials.append(material('cell_'+str(i),c))
rng=random.Random(815);colors=[rng.randrange(len(palette)) for _ in faces]
for face,c in zip(mesh.polygons,colors):face.material_index=c
wire=bpy.data.objects.new('black_grid',mesh.copy());bpy.context.collection.objects.link(wire);wire.data.materials.clear();wire.data.materials.append(material('black',(.005,.005,.005)))
for face in wire.data.polygons:face.material_index=0
mod=wire.modifiers.new('literal_quad_edges','WIREFRAME');mod.thickness=.003;mod.use_replace=True;mod.offset=1
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=a.samples;scene.cycles.use_denoising=False;scene.render.resolution_x=a.size;scene.render.resolution_y=a.size;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(1,1,1,1);bg.inputs['Strength'].default_value=.12
scene.view_settings.view_transform='Standard'
lightdata=bpy.data.lights.new('fixed_off_axis_area','AREA');lightdata.energy=450;lightdata.size=3
light=bpy.data.objects.new('fixed_off_axis_area',lightdata);bpy.context.collection.objects.link(light);light.location=(-3,-4,6);light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('known_ortho');cam=bpy.data.objects.new('known_ortho',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=3.1
bvh=BVHTree.FromPolygons([Vector(v) for v in verts],faces,all_triangles=False);observations=[];visible_counts=[0]*len(verts)
for index in range(a.views):
 yaw=2*math.pi*index/a.views;cam.location=(6*math.cos(yaw),6*math.sin(yaw),.35);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update();toward_camera=cam.location.normalized()
 obs=[]
 for k,v in enumerate(verts):
  point=Vector(v);source=point+toward_camera*10;hit,normal,face,distance=bvh.ray_cast(source,-toward_camera,10.01);visible=hit is not None and abs(distance-10)<.002
  ndc=world_to_camera_view(scene,cam,point);obs.append(dict(vertex_id=k,xy=[ndc.x*a.size,(1-ndc.y)*a.size],visible=visible));visible_counts[k]+=int(visible)
 observations.append(dict(frame=index,yaw_degrees=math.degrees(yaw),camera_matrix_world=[list(row) for row in cam.matrix_world],observations=obs))
 scene.render.filepath=str(out/f'frame_{index:03d}.png');bpy.ops.render.render(write_still=True)
report=validate(a.resolution,not a.no_dent);report.update(dict(views=a.views,size=a.size,ortho_scale=3.1,emission=a.emission,samples=a.samples,palette=palette,color_seed=815,duplicate_endpoint=False,visibility_note='Orthographic rays against base surface; ignores wire overlay and rasterization. Geometric visibility, not detector success.',dent_center_vertex_ids=[i for i,u in enumerate(unit) if u[0]>.999999],dent_center_visible_frame_counts=[visible_counts[i] for i,u in enumerate(unit) if u[0]>.999999]))
(out/'ground_truth.json').write_text(json.dumps(dict(evaluation_only=True,vertices=verts,quads=faces,cell_palette_indices=colors,frames=observations)))
(out/'render_report.json').write_text(json.dumps(report,indent=2));print('CONTROL_RENDER_COMPLETE',out)
