"""Evaluate exact Blender mesh-ray outputs; no soft-render metric substitution."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--source-run',type=Path,required=True);p.add_argument('--depth-prior',type=Path,required=True);p.add_argument('--model',action='append',required=True,help='Label=path/to/renders');p.add_argument('--output',type=Path,required=True);a=p.parse_args();prior=np.load(a.depth_prior);n,h,w=prior['calibrated'].shape
masks=np.stack([np.asarray(Image.open(a.source_run/f'masks/mask_{i:02}.png').convert('L').resize((w,h),Image.Resampling.NEAREST))>127 for i in range(n)])
result={'source_run':str(a.source_run),'prior':str(a.depth_prior),'accepted_views':np.where(prior['view_gate'])[0].tolist(),'variants':{}}
for model in a.model:
 name,path=model.split('=',1);path=Path(path);maps=[np.load(path/f'data/view_{i:03}.npz') for i in range(n)];mm=np.stack([d['mask'] for d in maps]);dd=np.stack([d['depth'] for d in maps]);assert mm.shape==masks.shape
 ious=(mm&masks).sum((1,2))/(mm|masks).sum((1,2));rec={'mean_actual_mesh_iou':float(ious.mean()),'iou_per_view':ious.tolist()}
 for split in ['train','heldout']:
  valid=prior['valid_mask']&prior[f'fit_{split}_mask']&(prior['confidence_weight']>0);common=valid&mm;weight=prior['confidence_weight']*common;err=np.nan_to_num(abs(dd-prior['calibrated']));rec[split+'_weighted_depth_mae']=float((err*weight).sum()/weight.sum());rec[split+'_coverage']=float(common.sum()/valid.sum())
 result['variants'][name]=rec
 a.output.write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
