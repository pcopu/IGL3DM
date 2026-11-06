"""Evaluation-only deterministic all-quad radial dimple control (standard library).

Never use these coordinates as reconstruction of an observed or generated object.
Cube-sphere topology avoids collapsed polar vertices and keeps every face a quad.
"""
import math
import json
import argparse
from pathlib import Path
from collections import Counter

PARAMETERS=dict(resolution=24,axes=[.72,.62,1.2],taper=.22,asymmetry=.06,dent_depth=.19,dent_width_radians=.24,dent_direction=[1,0,0])


def radial(u,dent=True):
 x,y,z=u
 r=(1/math.sqrt((x/.72)**2+(y/.62)**2+(z/1.2)**2))*(1-.22*z+.06*x*z)
 return r-(.19*math.exp(-(math.acos(max(-1,min(1,x)))/.24)**2) if dent else 0)


def generate(n=24,dent=True):
 if n<4 or n%2:raise ValueError('Resolution must be even and at least four')
 vertices=[];faces=[];lookup={};directions=[]
 def vertex(key):
  key=tuple(key)
  if key not in lookup:
   norm=math.sqrt(sum(x*x for x in key));u=[x/norm for x in key];r=radial(u,dent)
   lookup[key]=len(vertices);directions.append(u);vertices.append([x*r for x in u])
  return lookup[key]
 for axis in range(3):
  axes=[k for k in range(3) if k!=axis]
  for side in [-1,1]:
   for j in range(n):
    for i in range(n):
     ids=[]
     for a,b in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]:
      key=[0,0,0];key[axis]=side*n;key[axes[0]]=2*a-n;key[axes[1]]=2*b-n;ids.append(vertex(key))
     u,v,w=[directions[k] for k in ids[:3]]
     ab=[v[k]-u[k] for k in range(3)];ac=[w[k]-u[k] for k in range(3)]
     cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
     if sum(cross[k]*u[k] for k in range(3))<0:ids.reverse()
     faces.append(ids)
 return vertices,faces,directions


def validate(n=24,dent=True):
 v,f,u=generate(n,dent);counts=Counter();orientation=Counter()
 for face in f:
  assert len(set(face))==4
  for a,b in zip(face,face[1:]+face[:1]):
   counts[tuple(sorted((a,b)))]+=1;orientation[tuple(sorted((a,b)))]+=1 if a<b else -1
 boundary=sum(c==1 for c in counts.values());nonmanifold=sum(c!=2 for c in counts.values());winding=sum(c!=0 for c in orientation.values())
 angle=.12;direction=[math.cos(angle),math.sin(angle),0]
 chord_x=radial(direction,dent)*direction[0];center_x=radial([1,0,0],dent);recess=chord_x-center_x
 assert boundary==nonmanifold==winding==0 and len(v)-len(counts)+len(f)==2 and (recess>0 if dent else recess<0)
 return dict(parameters={**PARAMETERS,'resolution':n,'dent_enabled':dent},vertices=len(v),quads=len(f),boundary_edges=boundary,nonmanifold_edges=nonmanifold,inconsistent_edge_winding=winding,euler=len(v)-len(counts)+len(f),minimum_radius=min(radial(x,dent) for x in u),center_dent_depth=.19 if dent else 0,equatorial_chord_half_angle_radians=angle,center_recession_below_chord=recess,dent_vertices_within_20deg=sum(x[0]>math.cos(math.radians(20)) for x in u),status='EVALUATION ONLY; radial synthetic mesh, never inferred real geometry')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resolution',type=int,default=24);p.add_argument('--output',type=Path);a=p.parse_args();r=validate(a.resolution)
 if a.output:
  if a.output.exists():raise ValueError('Refusing overwrite')
  a.output.mkdir(parents=True);v,f,u=generate(a.resolution);(a.output/'mesh.json').write_text(json.dumps(dict(vertices=v,faces=f,parameters=r['parameters'],evaluation_only=True)))
 print(json.dumps(r,indent=2))
