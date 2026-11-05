"""Blender-run analytic asymmetric control, never used to fill generated pear geometry."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view
import os
NV=int(os.environ.get('CONTROL_VIEWS','8'))
OUT=Path(__file__).resolve().parents[1]/('controls/known_pear' if NV==8 else f'controls/known_pear_{NV}');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
NL=32;NT=24
vertices=[]
for j in range(NT+1):
 lat=-math.pi/2+math.pi*j/NT;z=1.20*math.sin(lat);rad=.64*math.cos(lat)*(1-.34*math.sin(lat))
 for i in range(NL):
  phi=2*math.pi*i/NL;wrapped=math.atan2(math.sin(phi-.35),math.cos(phi-.35));dent=.12*math.exp(-((wrapped/.38)**2+((z-.18)/.30)**2))
  rr=rad-dent*math.cos(lat);x=rr*math.sin(phi)+.09*(math.sin(lat)+1)**2;y=-rr*math.cos(phi)*.88
  vertices.append((x,y,z))
faces=[]
for j in range(NT):
 for i in range(NL):faces.append((j*NL+i,j*NL+(i+1)%NL,(j+1)*NL+(i+1)%NL,(j+1)*NL+i))
mesh=bpy.data.meshes.new('analytic_control');mesh.from_pydata(vertices,[],faces);mesh.update();obj=bpy.data.objects.new('analytic_control',mesh);bpy.context.collection.objects.link(obj)
def emission(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');e=n.new('ShaderNodeEmission');e.inputs['Color'].default_value=(*color,1);e.inputs['Strength'].default_value=1;m.node_tree.links.new(e.outputs[0],out.inputs['Surface']);return m
white=emission('white',(1,1,1));black=emission('black',(0,0,0));obj.data.materials.append(white)
# Actual shared mesh edges, drawn as thin curves slightly above the analytic surface.
curve=bpy.data.curves.new('known_quad_edges','CURVE');curve.dimensions='3D';curve.resolution_u=1;curve.bevel_depth=.0060;curve.bevel_resolution=0
edges=set()
for face in faces:
 for a,b in zip(face,face[1:]+face[:1]):edges.add(tuple(sorted((a,b))))
for a,b in sorted(edges):
 va=Vector(vertices[a]);vb=Vector(vertices[b])
 if (va-vb).length<1e-7:continue
 sp=curve.splines.new('POLY');sp.points.add(1);sp.points[0].co=(*va,1);sp.points[1].co=(*vb,1)
lines=bpy.data.objects.new('known_grid',curve);bpy.context.collection.objects.link(lines);curve.materials.append(black)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=False
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.world.color=(1,1,1)
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=1
scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast' if 'Medium High Contrast' in [] else 'None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
camdata=bpy.data.cameras.new('control_camera');cam=bpy.data.objects.new('control_camera',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=3.2
bvh=BVHTree.FromPolygons([Vector(p) for p in vertices],faces,all_triangles=False);observations=[]
for v in range(NV):
 yaw=math.radians(v*360/NV);cam.location=(6*math.sin(yaw),-6*math.cos(yaw),0);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 scene.render.filepath=str(OUT/f'view_{v}.png');bpy.ops.render.render(write_still=True)
 obs=[]
 for k,p in enumerate(vertices):
  point=Vector(p);direction=point-cam.location;hit,normal,faceidx,distance=bvh.ray_cast(cam.location,direction.normalized(),direction.length+.02)
  visible=hit is not None and distance>=direction.length-.015
  ndc=world_to_camera_view(scene,cam,point)
  obs.append({'vertex_id':k,'xy':[float(ndc.x*512),float((1-ndc.y)*512)],'visible':visible})
 observations.append({'view':v,'yaw_deg':v*360/NV,'observations':obs,'projection_3x4':[[160*math.cos(yaw),160*math.sin(yaw),0,256],[0,0,-160,256],[0,0,0,1]]})
(OUT/'ground_truth.json').write_text(json.dumps({'source':'Analytic known 3D control rendered in Blender; NOT generated input truth','vertices':vertices,'faces':faces,'views':observations},indent=2))
print('KNOWN_CONTROL_DONE',OUT)
