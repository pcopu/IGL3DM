"""Controlled orthographic square-texture inference. No learned predictor or hidden fill.

Coordinates internally are (screen-right, screen-up, camera-depth), in pixels.
The original generated atlas and quad graph are read-only inputs.
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsqr
from PIL import Image
FIXTURE_SEED=20261105


def _pyplot():
 """Import plotting only during an explicitly requested artifact write."""
 import matplotlib
 matplotlib.use('Agg')
 from matplotlib import pyplot
 return pyplot

def stats(a):
 a=np.asarray(a,dtype=float)
 return {'count':len(a),'min':float(np.min(a)),'p05':float(np.percentile(a,5)),'median':float(np.median(a)),'p95':float(np.percentile(a,95)),'max':float(np.max(a)),'mean':float(np.mean(a)),'std':float(np.std(a)),'coefficient_of_variation':float(np.std(a)/max(abs(np.mean(a)),1e-15))} if len(a) else {}

def infer(p):
 p=np.asarray(p,dtype=float)
 a=(p[1]-p[0]+p[2]-p[3])/2
 b=(p[3]-p[0]+p[2]-p[1])/2
 A=np.column_stack([a,b]); C=A.T@A
 lam,V=np.linalg.eigh(C); lam=np.maximum(lam,0)
 s=np.sqrt(lam[1]); cos=np.sqrt(lam[0]/max(lam[1],1e-30))
 dz=np.sqrt(max(lam[1]-lam[0],0))*V[:,0]
 # Canonicalization is only reproducibility, not a claim about convexity.
 if dz[np.argmax(np.abs(dz))]<0:dz=-dz
 grad=np.linalg.solve(A.T,dz) if lam[0]>1e-20 else np.full(2,np.nan)
 n=np.r_[-grad,1.];n/=np.linalg.norm(n)
 residual=np.linalg.norm(p[0]+p[2]-p[1]-p[3])/4
 return {'A':A,'s':s,'cos':cos,'theta':np.degrees(np.arccos(np.clip(cos,0,1))), 'dz':dz,'grad':grad,'normal':n,'parallelogram_rms':residual,'parallelogram_relative':residual/max(s,1e-15),'condition':1/max(cos,1e-15)}

def make_graph(nodes,faces):
 nodes=np.asarray(nodes,float); cells=[];edges={}
 for i,face in enumerate(faces):
  face=list(map(int,face));cells.append({'cell_id':i,'node_ids':face})
  for k in range(4):edges.setdefault(tuple(sorted((face[k],face[(k+1)%4]))),[]).append(i)
 adj=[[] for c in cells]
 for ids in edges.values():
  if len(ids)==2:a,b=ids;adj[a].append(b);adj[b].append(a)
 for c,a in zip(cells,adj):c['neighbor_cell_ids']=a
 return nodes,cells

def select(nodes,cells,ids=None):
 ids=sorted(c['cell_id'] for c in cells) if ids is None else sorted(ids)
 by={c['cell_id']:c for c in cells};chosen=[by[i] for i in ids];cidx={c['cell_id']:i for i,c in enumerate(chosen)}
 measurements=[infer(nodes[c['node_ids']]) for c in chosen]
 pairs=[(i,cidx[n]) for i,c in enumerate(chosen) for n in c['neighbor_cell_ids'] if n in cidx and i<cidx[n]]
 return chosen,measurements,pairs

def sign_solve(m,pairs):
 """Exact binary optimization (within MILP solver tolerance), reflection gauge fixed.

Minimize sum_(ij) ||n_i(sigma_i)-n_j(sigma_j)||^2 over sigma in {-1,+1}.
Only first two components of n flip. XOR variables linearize all pair terms.
"""
 n=len(m);E=len(pairs);obj=np.zeros(n+E);row=[];col=[];data=[];lo=[];hi=[]
 def constraint(vals,l,u):
  r=len(lo)
  for c,v in vals.items():row.append(r);col.append(c);data.append(v)
  lo.append(l);hi.append(u)
 for k,(i,j) in enumerate(pairs):
  y=n+k;obj[y]=4*np.dot(m[i]['normal'][:2],m[j]['normal'][:2])
  constraint({y:1,i:-1,j:1},0,np.inf)
  constraint({y:1,i:1,j:-1},0,np.inf)
  constraint({y:1,i:-1,j:-1},-np.inf,0)
  constraint({y:1,i:1,j:1},-np.inf,2)
 lb=np.zeros(n+E);ub=np.ones(n+E);ub[0]=0
 A=coo_matrix((data,(row,col)),shape=(len(lo),n+E)).tocsr()
 if not E:return np.ones(n),{'success':True,'status':0,'message':'One isolated cell','mip_gap':0}
 result=milp(obj,integrality=np.ones(n+E),bounds=Bounds(lb,ub),constraints=LinearConstraint(A,np.array(lo),np.array(hi)),options={'time_limit':60,'mip_rel_gap':1e-9})
 if result.x is None:raise RuntimeError(str(result.message))
 signs=1-2*np.rint(result.x[:n]);meta={'success':bool(result.success),'status':int(result.status),'message':str(result.message),'mip_gap':float(result.mip_gap),'mip_node_count':int(result.mip_node_count),'linear_objective':float(result.fun),'linear_lower_bound':float(result.mip_dual_bound),'variables':n+E,'cell_signs':n,'adjacent_pairs':E,'objective':'sum squared neighboring unit-normal differences, reflection gauge sigma[0]=+1'}
 return signs,meta

def energy(m,pairs,signs):
 N=np.array([x['normal'] for x in m]);N[:,:2]*=np.asarray(signs)[:,None]
 return float(sum(np.sum((N[i]-N[j])**2) for i,j in pairs))

def integrate(nodes,cells,m,signs):
 """Shared vertices; fit all four depth increments of each inferred affine cell.
 No regularizer, boundary silhouette depth, or shape-specific constraint is added.
 """
 used=sorted({n for c in cells for n in c['node_ids']});idx={n:i for i,n in enumerate(used)}
 row=[];col=[];data=[];target=[];edge_meta=[]
 for ci,(c,q,sign) in enumerate(zip(cells,m,signs)):
  ns=c['node_ids'];p=nodes[ns]
  for k in range(4):
   a,b=ns[k],ns[(k+1)%4];r=len(target)
   row.extend((r,r));col.extend((idx[a],idx[b]));data.extend((-1,1))
   target.append(sign*np.dot(q['grad'],p[(k+1)%4]-p[k]));edge_meta.append((ci,k,a,b))
 D=coo_matrix((data,(row,col)),shape=(len(target),len(used))).tocsr();target=np.array(target)
 sol=lsqr(D,target,atol=1e-12,btol=1e-12,iter_lim=20000);z=sol[0];z-=z.mean();res=D@z-target
 # Each face's best affine depth gradient, independent check after integration.
 fitgrad=[];ang=[];metric=[];planarity=[]
 for c,q,sign in zip(cells,m,signs):
  p=nodes[c['node_ids']];zz=z[[idx[n] for n in c['node_ids']]]
  coef=np.linalg.lstsq(np.c_[p,np.ones(4)],zz,rcond=None)[0];g=coef[:2];fitgrad.append(g);planarity.append(float(np.sqrt(np.mean((np.c_[p,np.ones(4)]@coef-zz)**2))))
  nn=np.r_[-g,1.];nn/=np.linalg.norm(nn);want=q['normal'].copy();want[:2]*=sign
  ang.append(np.degrees(np.arccos(np.clip(np.dot(nn,want),-1,1))))
  dz=q['A'].T@g;C=q['A'].T@q['A']+np.outer(dz,dz)
  metric.append(np.linalg.norm(C/(q['s']**2)-np.eye(2),'fro'))
 shared={}
 for t,(_,_,a,b) in zip(target,edge_meta):shared.setdefault(tuple(sorted((a,b))),[]).append(t if a<b else -t)
 disagreements=[abs(v[0]-v[1]) for v in shared.values() if len(v)==2]
 return {'used':used,'idx':idx,'z':z,'target':target,'residual':res,'fitgrad':np.array(fitgrad),'normal_deviation_deg':ang,'normalized_metric_error':metric,'quad_best_plane_depth_rms_px':planarity,'shared_depth_disagreement_px':disagreements,'lsqr_istop':int(sol[1]),'lsqr_iterations':int(sol[2]),'depth_rmse_px':float(np.sqrt(np.mean(res**2))),'target_increment_rms_px':float(np.sqrt(np.mean(target**2))),'relative_depth_rmse':float(np.linalg.norm(res)/max(np.linalg.norm(target),1e-15))}

def mesh(path,nodes,cells,z,used,view=0,comment=''):
 idx={n:i for i,n in enumerate(used)};theta=np.deg2rad(view*45)
 # World: z-up, yaw0 camera -Y, positive camera-depth +Y; x right.
 pts=np.c_[(nodes[used,0]-256)/256,z/256,(nodes[used,1]+256)/256]
 xx=pts[:,0].copy();yy=pts[:,1].copy();pts[:,0]=xx*np.cos(theta)-yy*np.sin(theta);pts[:,1]=xx*np.sin(theta)+yy*np.cos(theta)
 with path.open('w') as f:
  f.write('ply\nformat ascii 1.0\ncomment '+comment+'\n'+f'element vertex {len(used)}\nproperty float x\nproperty float y\nproperty float z\nelement face {2*len(cells)}\nproperty list uchar int vertex_indices\nend_header\n')
  for p in pts:f.write(' '.join(f'{v:.10g}' for v in p)+'\n')
  for c in cells:
   ns=c['node_ids']
   for tri in ((0,1,2),(0,2,3)):f.write('3 '+' '.join(str(idx[ns[k]]) for k in tri)+'\n')
 return pts

def fixture_test(output=None):
 """Run the unchanged fixtures, with a fresh fixed RNG on every invocation."""
 RNG=np.random.default_rng(FIXTURE_SEED)
 cases=[];worst={'scale_abs_error':0.,'depth_increment_abs_error':0.,'tilt_error_deg':0.,'metric_residual':0.}
 for tilt in (0,5,20,45,70,85,89):
  for s in (1,8,15):
   for k in range(5):
    th=np.deg2rad(tilt);phi,alpha=RNG.uniform(-np.pi,np.pi,2)
    u=np.array([np.cos(th)*np.cos(phi),np.cos(th)*np.sin(phi),-np.sin(th)]);v=np.array([-np.sin(phi),np.cos(phi),0.])
    rot=np.array([[np.cos(alpha),-np.sin(alpha)],[np.sin(alpha),np.cos(alpha)]])
    E=s*np.column_stack((u,v))@rot;p3=np.array([[0,0,0],E[:,0],E[:,0]+E[:,1],E[:,1]])
    q=infer(p3[:,:2]);b=E[2];delta=min(np.linalg.norm(q['dz']-b),np.linalg.norm(q['dz']+b));mm=np.linalg.norm(q['A'].T@q['A']+np.outer(q['dz'],q['dz'])-s*s*np.eye(2))
    vals=[abs(q['s']-s),delta,abs(q['theta']-tilt),mm]
    for name,val in zip(worst,vals):worst[name]=max(worst[name],float(val))
    cases.append({'tilt':tilt,'s':s,'scale_error':float(vals[0]),'depth_increment_error':float(delta),'tilt_error':float(vals[2])})
 assert worst['scale_abs_error']<1e-10 and worst['depth_increment_abs_error']<1e-6 and worst['tilt_error_deg']<2e-6 and worst['metric_residual']<1e-10,worst
 noisy=[]
 for tilt in (5,45,80,89):
  th=np.deg2rad(tilt);s=14;E=np.array([[s*np.cos(th),0],[0,s],[-s*np.sin(th),0]])
  p3=np.array([[0,0,0],E[:,0],E[:,0]+E[:,1],E[:,1]]);truth=np.cross(E[:,0],E[:,1]);truth/=np.linalg.norm(truth)
  for sigma in (.25,.5,1.):
   errors=[];gradient_errors=[]
   for k in range(200):
    q=infer(p3[:,:2]+RNG.normal(0,sigma,(4,2)))
    n=q['normal'].copy();other=n.copy();other[:2]*=-1
    truth_grad=np.linalg.solve(E[:2].T,E[2]);gradient_errors.append(min(np.linalg.norm(q['grad']-truth_grad),np.linalg.norm(q['grad']+truth_grad))/np.linalg.norm(truth_grad))
    errors.append(min(np.degrees(np.arccos(np.clip(np.dot(n,truth),-1,1))),np.degrees(np.arccos(np.clip(np.dot(other,truth),-1,1)))))
   noisy.append({'tilt_deg':tilt,'cell_side_px':s,'corner_noise_sigma_px':sigma,'best_sign_normal_error_deg':stats(errors),'best_sign_gradient_relative_error':stats(gradient_errors)})
 # Flat rectangle is indistinguishable from a tilted square from one projection.
 rectangle=infer(np.array([[0,0],[12,0],[12,8],[0,8]],float))
 # Shared exact planar square lattice.
 E=np.array([[.8,0],[0,1],[-.6,0]]);nodes3=np.array([E@np.array([i,j]) for j in range(6) for i in range(7)])
 faces=[[j*7+i,j*7+i+1,(j+1)*7+i+1,(j+1)*7+i] for j in range(5) for i in range(6)]
 nodes,cells=make_graph(nodes3[:,:2],faces);chosen,m,pairs=select(nodes,cells);signs,solver=sign_solve(m,pairs);out=integrate(nodes,chosen,m,signs);truth=nodes3[out['used'],2];truth-=truth.mean();plane_err=min(np.sqrt(np.mean((out['z']-truth)**2)),np.sqrt(np.mean((out['z']+truth)**2)))
 assert plane_err<1e-9 and out['depth_rmse_px']<1e-9
 # Exact equal square facets on a cylinder. Each horizontal chord and vertical edge is 1.
 cols=12;rows=6;R=10.;dtheta=2*np.arcsin(.5/R);angles=(np.arange(cols+1)-cols/2)*dtheta
 nodes3=np.array([[R*np.sin(a),j,R*np.cos(a)] for j in range(rows+1) for a in angles])
 faces=[[j*(cols+1)+i,j*(cols+1)+i+1,(j+1)*(cols+1)+i+1,(j+1)*(cols+1)+i] for j in range(rows) for i in range(cols)]
 nodes,cells=make_graph(nodes3[:,:2],faces);chosen,m,pairs=select(nodes,cells);signs,solver=sign_solve(m,pairs);out=integrate(nodes,chosen,m,signs);truth=nodes3[out['used'],2];truth-=truth.mean()
 true_sign=[]
 for c,q in zip(chosen,m):
  z=nodes3[c['node_ids'],2];dz=np.array([(z[1]-z[0]+z[2]-z[3])/2,(z[3]-z[0]+z[2]-z[1])/2]);true_sign.append(1 if np.dot(dz,q['dz'])>=0 else -1)
 cylinder_err=min(np.sqrt(np.mean((out['z']-truth)**2)),np.sqrt(np.mean((out['z']+truth)**2)))
 cylinder={'cell_count':len(chosen),'equal_square_size_error':float(max(abs(q['s']-1) for q in m)),'maximum_parallelogram_error':float(max(q['parallelogram_rms'] for q in m)),'optimizer':solver,'true_normal_smoothness_energy':energy(m,pairs,true_sign),'optimized_normal_smoothness_energy':energy(m,pairs,signs),'integrated_edge_rmse':out['depth_rmse_px'],'depth_rmse_to_truth_best_global_reflection':float(cylinder_err),'truth_depth_span':float(np.ptp(truth)),'reconstruction_depth_span':float(np.ptp(out['z'])),'conclusion':'The objective prefers an incorrect monotone depth surface over the true convex cylinder, despite exact equal square input. Ambiguity exceeds a single global reflection.'}
 assert cylinder_err>.1 and out['depth_rmse_px']<1e-8 and cylinder['optimized_normal_smoothness_energy']<cylinder['true_normal_smoothness_energy']
 if output is not None:
  plt=_pyplot()
  fig,ax=plt.subplots(figsize=(9,4));ax.plot(nodes3[:cols+1,0],truth[:cols+1],'-o',label='Exact cylinder truth');ax.plot(nodes3[:cols+1,0],out['z'][:cols+1],'-o',label='Optimized smooth-normal depth');ax.plot(nodes3[:cols+1,0],-out['z'][:cols+1],'--',label='Reflected branch');ax.set(xlabel='Screen horizontal coordinate',ylabel='Mean-centered depth',title='Negative control: exact equal square facets do not identify curvature');ax.legend();ax.set_aspect('equal',adjustable='datalim');fig.tight_layout();fig.savefig(output/'synthetic_cylinder_ambiguity.png',dpi=160);plt.close(fig)
 return {'passed':True,'exact_square_cases':len(cases),'worst_exact_errors':worst,'planar_patch':{'cells':30,'best_reflection_depth_rmse':float(plane_err)},'noise_sensitivity':noisy,'front_facing_12_by_8_rectangle':{'actual_tilt_deg':0,'square_assumption_inferred_tilt_deg':float(rectangle['theta']),'inferred_side':float(rectangle['s']),'conclusion':'Square-ness is an input prior, not a locally testable conclusion.'},'faceted_cylinder_negative_control':cylinder}

def components(cells,allowed):
 allowed=set(allowed);adj={c['cell_id']:set(c['neighbor_cell_ids'])&allowed for c in cells if c['cell_id'] in allowed};out=[]
 while allowed:
  todo=[min(allowed)];allowed.remove(todo[0]);comp=[]
  while todo:
   a=todo.pop();comp.append(a)
   for b in sorted(adj[a]&allowed):allowed.remove(b);todo.append(b)
  out.append(sorted(comp))
 return sorted(out,key=lambda x:(-len(x),x))

def public_integration(out):
 return {k:out[k] for k in ('lsqr_istop','lsqr_iterations','depth_rmse_px','target_increment_rms_px','relative_depth_rmse')}|{'depth_span_px':float(np.ptp(out['z'])),'normal_deviation_deg':stats(out['normal_deviation_deg']),'normalized_metric_error':stats(out['normalized_metric_error']),'shared_depth_disagreement_px':stats(out['shared_depth_disagreement_px']),'quad_best_plane_depth_rms_px':stats(out['quad_best_plane_depth_rms_px'])}

def visuals(output,atlas,view,nodes,cells,m,signs,out):
 plt=_pyplot()
 from matplotlib.collections import PolyCollection
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 w,h=atlas.size;im=atlas.crop((round(view%4*w/4),round(view//4*h/2),round((view%4+1)*w/4),round((view//4+1)*h/2))).resize((512,512),Image.Resampling.LANCZOS)
 polys=[nodes[c['node_ids']] * [1,-1] for c in cells]
 N=np.array([q['normal'] for q in m]);N[:,:2]*=signs[:,None];rgb=(N+1)/2
 cent=np.array([nodes[c['node_ids']].mean(0) for c in cells]);depth=np.array([np.mean(out['z'][[out['idx'][n] for n in c['node_ids']]]) for c in cells]);fitnormal=np.c_[-out['fitgrad'],np.ones(len(cells))];fitnormal/=np.linalg.norm(fitnormal,axis=1)[:,None]
 fig,axes=plt.subplots(2,3,figsize=(15,10))
 for ax in axes.ravel():ax.set_xlim(0,512);ax.set_ylim(512,0);ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
 axes[0,0].imshow(im);axes[0,0].add_collection(PolyCollection(polys,facecolors='none',edgecolors='#e42931',linewidths=.4));axes[0,0].set_title(f'Source view {view}: {len(cells)} selected visible cells')
 axes[0,1].add_collection(PolyCollection(polys,facecolors=rgb,edgecolors='none'));axes[0,1].set_title('Local square-derived normals, optimized signs\nRGB = screen x / screen up / viewing depth')
 pc=PolyCollection(polys,array=depth,cmap='coolwarm',edgecolors='none');axes[0,2].add_collection(pc);axes[0,2].set_title('Integrated depth, branch A (pixel units)');fig.colorbar(pc,ax=axes[0,2],fraction=.04)
 axes[1,0].add_collection(PolyCollection(polys,facecolors=(fitnormal+1)/2,edgecolors='none'));axes[1,0].set_title('Best-fit face normals from shared-vertex depths')
 pc=PolyCollection(polys,array=np.asarray(out['normal_deviation_deg']),cmap='magma',edgecolors='none');axes[1,1].add_collection(pc);axes[1,1].set_title('Local versus integrated normal discrepancy (degrees)');fig.colorbar(pc,ax=axes[1,1],fraction=.04)
 pc=PolyCollection(polys,array=-depth,cmap='coolwarm',edgecolors='none');axes[1,2].add_collection(pc);axes[1,2].set_title('Equally unresolved reflected depth, branch B');fig.colorbar(pc,ax=axes[1,2],fraction=.04)
 fig.suptitle('Conditional mathematical patch, not validated object geometry. Missing cells are not filled.',fontsize=15);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(output/'source_normals_depth_comparison.png',dpi=150);plt.close(fig)
 fig=plt.figure(figsize=(13,6))
 for k,sgn in enumerate((1,-1)):
  ax=fig.add_subplot(1,2,k+1,projection='3d');p=np.c_[nodes[out['used'],0],nodes[out['used'],1],sgn*out['z']]
  verts=[p[[out['idx'][n] for n in c['node_ids']]] for c in cells];ax.add_collection3d(Poly3DCollection(verts,facecolors=(.22,.6,.8,.8),edgecolors=(.05,.1,.15,.4),linewidths=.3));ax.auto_scale_xyz(p[:,0],p[:,1],p[:,2]);ax.set_box_aspect(np.maximum(np.ptp(p,axis=0),1));ax.view_init(25,-65);ax.set(xlabel='Screen right',ylabel='Screen up',zlabel='Viewing depth',title=f'Actual open patch mesh: branch {"A" if sgn==1 else "B"}')
 fig.suptitle('Surface connects only detected shared quad corners; no hidden faces or silhouette completion');fig.tight_layout();fig.savefig(output/'conditional_patch_mesh_preview.png',dpi=160);plt.close(fig)


def run_experiment(atlas_path,quad_graph_path,output):
 """Run the fixed formulation into a new or empty output directory.

 Inputs are read-only. Refuse nonempty output before calculations or artifact writes.
 No file paths, random state or plotting work are initialized at import time.
 """
 atlas_path=Path(atlas_path).resolve()
 quad_graph_path=Path(quad_graph_path).resolve()
 output=Path(output).resolve()
 if output.exists() and (not output.is_dir() or any(output.iterdir())):
  raise FileExistsError(f'Refusing nonempty or non-directory output: {output}')
 for path in (atlas_path,quad_graph_path):
  if not path.is_file():raise FileNotFoundError(f'Input file not found: {path}')
 graphs=json.loads(quad_graph_path.read_text())
 with Image.open(atlas_path) as image:
  atlas=image.convert('RGB')
 output.mkdir(parents=True,exist_ok=True)
 fixture=fixture_test(output);(output/'fixture_tests.json').write_text(json.dumps(fixture,indent=2))
 summary=[];allmeasure=[];candidates=[]
 for graph in graphs:
  nodes=np.array([n['xy'] for n in graph['nodes']],float)*[1,-1]
  for mode in ('raw_white_interiors','welded_corners'):
   vals=[]
   for c in graph['cells']:
    p=np.array(c['corners'],float)*[1,-1] if mode=='raw_white_interiors' else nodes[c['node_ids']]
    q=infer(p);vals.append(q);allmeasure.append({'view':graph['view'],'mode':mode,'cell_id':c['cell_id'],**{k:float(q[k]) for k in ('s','cos','theta','condition','parallelogram_rms','parallelogram_relative')}})
   by={c['cell_id']:q for c,q in zip(graph['cells'],vals)}
   adjdelta=[abs(np.log(by[c['cell_id']]['s']/by[n]['s'])) for c in graph['cells'] for n in c['neighbor_cell_ids'] if c['cell_id']<n]
   good=[c['cell_id'] for c,q in zip(graph['cells'],vals) if q['parallelogram_relative']<=.1 and q['cos']>=.25 and q['s']>=5]
   comp=components(graph['cells'],good)
   summary.append({'view':graph['view'],'mode':mode,'total_cells':len(vals),'square_side_px':stats([q['s'] for q in vals]),'inferred_tilt_deg':stats([q['theta'] for q in vals]),'parallelogram_rms_px':stats([q['parallelogram_rms'] for q in vals]),'parallelogram_relative':stats([q['parallelogram_relative'] for q in vals]),'adjacent_log_scale_mismatch':stats(adjdelta),'ill_conditioned_over_4':int(sum(q['cos']<.25 for q in vals)),'relative_nonparallelogram_over_10pct':int(sum(q['parallelogram_relative']>.1 for q in vals)),'quality_accepted':len(good),'largest_component':len(comp[0])})
   if mode=='welded_corners':candidates.append((len(comp[0]),graph['view'],comp[0]))
 # Selection uses only graph support and fixed local numeric gates, not apparent anatomy.
 _,view,ids=sorted(candidates,key=lambda x:(-x[0],x[1]))[0];graph=graphs[view];nodes=np.array([n['xy'] for n in graph['nodes']],float)*[1,-1];cells,m,pairs=select(nodes,graph['cells'],ids)
 signs,solver=sign_solve(m,pairs);out=integrate(nodes,cells,m,signs)
 side=np.array([q['s'] for q in m]);sharedscale=[abs(np.log(m[i]['s']/m[j]['s'])) for i,j in pairs]
 report={'input_sha256':hashlib.sha256(atlas_path.read_bytes()).hexdigest(),'quad_graph_sha256':hashlib.sha256(quad_graph_path.read_bytes()).hexdigest(),'coordinate_convention':'Internal right/up/depth coordinates in pixels. Export /256, center256, z-up, view*45 degree yaw, camera0 on -Y. Depth gauge = mean0; no absolute placement evidence.','square_model':'A.T A + b b.T = s^2 I. s=sqrt(lambda_max(A.T A)); b=+-sqrt(lambda_max-lambda_min)*v_min. grad=solve(A.T,b).','acceptance_gates':{'relative_affine_parallelogram_corner_rms_max':.1,'minimum_projected_minor_major_ratio':.25,'minimum_inferred_square_side_px':5},'selection':'Largest connected welded-cell component across all eight views, lowest view index tie-break. No shape or depth sign labels.','selected_view':view,'selected_cell_ids':ids,'selected_cells':len(cells),'selected_nodes':len(out['used']),'exported_triangles':2*len(cells),'triangulation':'Each detected quad is split along its fixed 0-to-2 diagonal. No new vertices or hole filling.','selected_adjacencies':len(pairs),'selected_side_px':stats(side),'selected_adjacent_log_scale_mismatch':stats(sharedscale),'best_common_size_rms_relative':float(np.sqrt(np.mean((side-side.mean())**2))/side.mean()),'sign_optimizer':solver,'normal_smoothness_energy':energy(m,pairs,signs),'integration':public_integration(out),'ground_truth':'No source geometry, true normals, depth, cell size, or calibrated cameras exist for this generated image.','conclusion':'Exact-square planar fixtures pass. A known exact-square faceted cylinder defeats the smooth-normal sign rule, proving unresolved alternatives beyond a global reflection. Real detections fail common square size and have incompatible shared-edge depths. The exported patches are reproducible conditional diagnostic surfaces, not useful validated reconstruction. Do not extend this formulation on the atlas without independently supported cell geometry or depth/sign evidence.','mesh_branch_relationship':'B is A reflected in screen plane. This pair does not exhaust all possible local sign fields.','hidden_completion':False,'publication':False}
 (output/'measurement_summary.json').write_text(json.dumps(summary,indent=2));(output/'cell_measurements.json').write_text(json.dumps(allmeasure,indent=2));(output/'integration_report.json').write_text(json.dumps(report,indent=2));(output/'selected_patch_data.json').write_text(json.dumps({'view':view,'node_ids':out['used'],'xy_screen_right_up':nodes[out['used']].tolist(),'depth_A_px':out['z'].tolist(),'cell_ids':ids,'faces':[[out['idx'][n] for n in c['node_ids']] for c in cells],'canonical_local_gradients':[q['grad'].tolist() for q in m],'optimized_signs':signs.tolist()},indent=2))
 mesh(output/'conditional_patch_A.ply',nodes,cells,out['z'],out['used'],view,'UNVALIDATED square-prior conditional patch A; no hidden completion')
 mesh(output/'conditional_patch_B.ply',nodes,cells,-out['z'],out['used'],view,'UNVALIDATED reflected square-prior patch B; no hidden completion')
 visuals(output,atlas,view,nodes,cells,m,signs,out)
 return {'fixture':fixture['worst_exact_errors'],'cylinder':fixture['faceted_cylinder_negative_control'],'real':report}


def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--atlas',type=Path,required=True,help='Read-only 4-by-2 generated atlas image')
 parser.add_argument('--quad-graph',type=Path,required=True,help='Read-only quad_graph.json from marker_consistency/source/quad_cells.py')
 parser.add_argument('--output',type=Path,required=True,help='New or empty output directory; nonempty output is refused')
 args=parser.parse_args(argv)
 try:
  result=run_experiment(args.atlas,args.quad_graph,args.output)
 except (OSError,ValueError) as error:
  parser.error(str(error))
 print(json.dumps(result,indent=2))


if __name__=='__main__':
 main()
