"""CPU differentiable shared-SDF reconstruction; no anatomical or per-part edits."""
import os,json,time,argparse,hashlib
os.environ['OMP_NUM_THREADS']='4'
import numpy as np, torch
import torch.nn.functional as F
from scipy import ndimage
from skimage.measure import marching_cubes
from PIL import Image
import trimesh
from pathlib import Path
ROOT=Path(__file__).resolve().parent
torch.set_num_threads(4); torch.manual_seed(13); np.random.seed(13)
def rays(size,steps,yaws):
 u=(torch.arange(size)+.5)*2/size-1; z=-u
 zz,uu=torch.meshgrid(z,u,indexing='ij'); t=torch.linspace(2.5,5.5,steps)
 grids=[]
 for a in yaws:
  a=np.deg2rad(a);right=torch.tensor([np.cos(a),np.sin(a),0.],dtype=torch.float32);toward=torch.tensor([np.sin(a),-np.cos(a),0.],dtype=torch.float32)
  p=uu[None,:,:,None]*right+zz[None,:,:,None]*torch.tensor([0.,0.,1.])+(4-t[:,None,None,None])*toward
  grids.append(p[..., [2,1,0]]) # field axes x,y,z; grid_sample uses W,H,D
 return torch.stack(grids),t

def render(sdf,grid,t,beta=.004):
 # grid_sample outside volume must be empty, not neutral SDF zero
 sampled=F.grid_sample(sdf.expand(len(grid),-1,-1,-1,-1),grid,align_corners=False,padding_mode='border')[:,0]
 inside=(grid.abs()<=1).all(-1)
 density=torch.sigmoid(sampled/beta)*120*inside
 optical=density*(t[1]-t[0]); trans=torch.exp(-torch.cumsum(optical,1)+optical)
 w=trans*(-torch.expm1(-optical)); opacity=w.sum(1)
 depth=(w*t[None,:,None,None]).sum(1)/opacity.clamp_min(1e-6)
 return opacity,depth

def export(sdf,out):
 out.mkdir(exist_ok=True); n=sdf.shape[0]
 v,f,_,_=marching_cubes(np.pad(sdf,1,constant_values=-1),0,spacing=(2/n,)*3)
 v=v-1-1/n; m=trimesh.Trimesh(v,f,process=True);m.fix_normals()
 m.export(out/'model.ply');v=m.vertices;f=m.faces
 (out/'mesh.json').write_text(json.dumps({'vertices':v.tolist(),'faces':f.tolist(),'colors':np.tile([.68,.68,.68],(len(v),1)).tolist()}))
 info={'vertices':len(v),'faces':len(f),'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),'components':len(m.split(only_watertight=False)),'volume':float(m.volume),'degenerate_faces':int((m.area_faces<1e-12).sum()),'self_intersections_checked':False}
 (out/'integrity.json').write_text(json.dumps(info,indent=2));return info

def primitive_test(output_dir):
 n=48;axis=(torch.arange(n)+.5)*2/n-1;x,y,z=torch.meshgrid(axis,axis,axis,indexing='ij');radius=torch.tensor(.55,requires_grad=True)
 grid,t=rays(48,128,[0,67,180]);sdf=(radius-torch.sqrt(x*x+y*y+z*z))[None,None];op,d=render(sdf,grid,t)
 u=(torch.arange(48)+.5)*2/48-1;zz,xx=torch.meshgrid(u,u,indexing='ij');mask=xx*xx+zz*zz<.55**2; exact=4-torch.sqrt((.55**2-xx*xx-zz*zz).clamp_min(0));interior=xx*xx+zz*zz<.45**2
 err=float((d[:,interior]-exact[interior]).abs().mean());iou=float(((op>.5)&mask).sum()/((op>.5)|mask).sum());op.sum().backward()
 report={'silhouette_iou':iou,'interior_depth_mae':err,'radius_gradient_positive':bool(radius.grad>0),'radius_gradient':float(radius.grad),'max_rotation_difference':float((op[0]-op[1]).abs().max())}
 assert err<.05 and iou>.9 and radius.grad>0,report
 (Path(output_dir)/'primitive_validation.json').write_text(json.dumps(report,indent=2));print('PRIMITIVE',report,flush=True)

def validate_inputs(args,base,out):
 if not np.isfinite(args.initial_sigma) or args.initial_sigma<0:raise ValueError("Initial sigma must be finite and nonnegative")
 if any(v<=0 for v in [args.iterations,args.size,args.grid,args.control]):
  raise ValueError('iterations, image size, grid and control dimensions must be positive')
 if args.grid<4 or args.control<2 or args.size<4:
  raise ValueError('grid and image size must be >=4; control dimension >=2')
 if not np.isfinite(args.depth_weight) or args.depth_weight<0:
  raise ValueError('depth weight must be finite and nonnegative')
 if not args.name or Path(args.name).name!=args.name:
  raise ValueError('name must be a single nonempty directory name')
 if out.exists() and any(out.iterdir()):
  raise FileExistsError(f'Refusing to overwrite nonempty output directory: {out}')
 report=json.loads((base/'report.json').read_text());camera=report.get('camera_convention',{})
 views=camera.get('per_view',[])
 yaws=[v.get('yaw_degrees',np.nan) for v in views] if views else camera.get('yaw_degrees',[])
 elev=[v.get('elevation_degrees',np.nan) for v in views] if views else camera.get('elevation_degrees',float('nan'))
 if len(yaws)!=16 or not np.allclose(yaws,np.arange(16)*22.5) or not np.allclose(elev,0) or camera.get('orthographic_scale')!=2.0 or not np.allclose(camera.get('yaw0_location',[np.nan]*3),[0,-4,0]):
  raise ValueError('Only the 16-view level orthographic rig, scale 2, distance 4, ordered yaw 0..337.5 is supported')
 if (base/'cameras.json').exists():
  views=json.loads((base/'cameras.json').read_text()).get('views',[])
  if len(views)!=16 or any(not np.isclose(v.get('yaw_degrees',np.nan),i*22.5) or not np.isclose(v.get('elevation_degrees',np.nan),0) for i,v in enumerate(views)):
   raise ValueError('Explicit cameras.json disagrees with supported rig')
 field=np.load(base/'field.npz')['occupied']
 if field.ndim!=3 or len(set(field.shape))!=1 or field.shape[0]<4:
  raise ValueError('Source occupancy must be a cubic volume with resolution >=4')
 prior=np.load(args.depth_prior);shape=prior['calibrated'].shape
 if len(shape)!=3 or shape[0]!=16 or shape[1]!=shape[2]:
  raise ValueError('Expected sixteen square calibrated depth maps')
 for key in ['valid_mask','confidence_weight','fit_train_mask','fit_heldout_mask']:
  if prior[key].shape!=shape:raise ValueError(f'Prior shape mismatch: {key}')
 if np.any(prior['fit_train_mask'] & prior['fit_heldout_mask']):
  raise ValueError('Train and heldout masks must not overlap')
 if 'view_ids' in prior and not np.array_equal(prior['view_ids'],np.arange(16)):raise ValueError('Prior view_ids must follow the source camera order')
 if prior['view_gate'].shape!=(16,):raise ValueError('Expected sixteen view gates')
 if args.depth_weight>0 and np.count_nonzero(prior['view_gate'])<4:
  raise ValueError('Depth fitting rejected: fewer than four accepted views')
 support=prior['valid_mask'] & np.isfinite(prior['calibrated']) & np.isfinite(prior['confidence_weight']) & (prior['confidence_weight']>0) & prior['view_gate'][:,None,None]
 if args.depth_weight>0 and (not np.any(support & prior['fit_train_mask']) or not np.any(support & prior['fit_heldout_mask'])):
  raise ValueError('Accepted depth needs finite training and heldout support')
 for i in range(16):
  if not (base/f'masks/mask_{i:02}.png').is_file():raise ValueError(f'Missing mask {i}')

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-run',required=True);p.add_argument('--depth-prior',required=True);p.add_argument('--output-root',default='volume-runs');p.add_argument('--initial-sigma',type=float,default=0.0,help='Experimental initial-SDF Gaussian sigma in voxels; default off');p.add_argument('--iterations',type=int,default=160);p.add_argument('--size',type=int,default=64);p.add_argument('--grid',type=int,default=64);p.add_argument('--control',type=int,default=24);p.add_argument('--depth-weight',type=float,default=4);p.add_argument('--name',default='depth');a=p.parse_args();base=Path(a.source_run);out=Path(a.output_root)/a.name
 validate_inputs(a,base,out)
 out.mkdir(exist_ok=True,parents=True)
 primitive_test(out);n=a.grid;raw=np.load(base/'field.npz')['occupied'];initial=ndimage.distance_transform_edt(raw)-ndimage.distance_transform_edt(~raw);initial=initial.astype('f')*2/raw.shape[0]
 initial=F.interpolate(torch.tensor(initial)[None,None],size=(n,n,n),mode='trilinear',align_corners=False)
 if a.initial_sigma>0:
  initial=torch.tensor(ndimage.gaussian_filter(initial.numpy(),sigma=(0,0,a.initial_sigma,a.initial_sigma,a.initial_sigma),mode='nearest'))
 delta=torch.nn.Parameter(torch.zeros((1,1,a.control,a.control,a.control)));optim=torch.optim.Adam([delta],lr=.012)
 grid,t=rays(a.size,112,np.arange(16)*22.5)
 masks=torch.tensor(np.stack([np.asarray(Image.open(base/f'masks/mask_{i:02}.png').convert('L').resize((a.size,a.size),Image.Resampling.NEAREST))>127 for i in range(16)]),dtype=torch.float32)
 prior=np.load(a.depth_prior);height=prior['calibrated'].shape[-1];ix=np.floor((np.arange(a.size)+.5)*height/a.size).astype(int)
 def take(k):return torch.tensor(prior[k][:,ix[:,None],ix[None,:]].astype('f'))
 target=take('calibrated');valid=take('valid_mask')*torch.isfinite(target);target=torch.nan_to_num(target);weight=torch.nan_to_num(take('confidence_weight'),nan=0,posinf=0,neginf=0).clamp_min(0)*valid*torch.tensor(prior['view_gate'],dtype=torch.float32)[:,None,None];train=weight*take('fit_train_mask');held=weight*take('fit_heldout_mask')
 if a.depth_weight>0 and (train.sum()<=0 or held.sum()<=0):
  raise ValueError('Depth support is empty after working-resolution sampling')
 history=[];start=time.time();export(initial[0,0].numpy(),out/'initial')
 def evaluate(sdf):
  with torch.no_grad():
   ops=[];ds=[]
   for i in range(0,16,4):
    op,d=render(sdf,grid[i:i+4],t);ops.append(op);ds.append(d)
   op=torch.cat(ops);d=torch.cat(ds);pred=op>.5;truth=masks>.5
   return {'soft_render_iou':float((pred&truth).sum()/(pred|truth).sum()),'depth_train_mae':float(((d-target).abs()*train).sum()/train.sum()) if train.sum()>0 else None,'depth_heldout_mae':float(((d-target).abs()*held).sum()/held.sum()) if held.sum()>0 else None}
 before=evaluate(initial);print('INITIAL',before,flush=True)
 for it in range(a.iterations):
  ids=torch.randperm(16)[:4];optim.zero_grad();offset=F.interpolate(.10*torch.tanh(delta),size=(n,n,n),mode='trilinear',align_corners=False);sdf=initial+offset;op,d=render(sdf,grid[ids],t)
  silhouette=((op-masks[ids])**2).mean();ww=train[ids];depth=(((d-target[ids]).square().clamp_max(.25))*ww).sum()/ww.sum().clamp_min(1)
  smooth=sum((offset.diff(dim=k)**2).mean() for k in [2,3,4]);anchor=offset.square().mean();loss=silhouette+a.depth_weight*depth+2*smooth+.2*anchor
  loss.backward();optim.step()
  if it%10==0 or it==a.iterations-1:
   rec={'iteration':it,'loss':float(loss.detach()),'silhouette':float(silhouette.detach()),'depth_mse':float(depth.detach()),'seconds':time.time()-start};history.append(rec);print(rec,flush=True)
  if it in [39,79,a.iterations-1]:
   ss=(initial+F.interpolate(.10*torch.tanh(delta),size=(n,n,n),mode='trilinear',align_corners=False)).detach();print('CHECK',it,evaluate(ss),flush=True)
 final=(initial+F.interpolate(.10*torch.tanh(delta),size=(n,n,n),mode='trilinear',align_corners=False)).detach();after=evaluate(final);integ=export(final[0,0].numpy(),out/'final');np.savez_compressed(out/'field.npz',initial=initial.numpy(),sdf=final.numpy());(out/'loss_curve.json').write_text(json.dumps(history,indent=2));report={'config':vars(a),'initial_smoothing':{'sigma_voxels':a.initial_sigma,'sigma_world_units':a.initial_sigma*2/n,'method':'Gaussian initial SDF, nearest boundary extension; disabled at zero'},'input_hashes':{'source_field_sha256':hashlib.sha256((base/'field.npz').read_bytes()).hexdigest(),'depth_prior_sha256':hashlib.sha256(Path(a.depth_prior).read_bytes()).hexdigest()},'before':before,'after':after,'seconds':time.time()-start,'integrity':integ,'caveats':['Not ground-truth 3D accuracy','Depth affine calibration and view gating used baseline and heldout statistics; heldout is not blind validation','Soft ray-render metrics must be checked on extracted mesh',f'Shared {n}-cubed SDF, no anatomical edits; displacement bounded to 0.1 world units']};(out/'report.json').write_text(json.dumps(report,indent=2));print('FINAL',report,flush=True)
if __name__=='__main__':main()
