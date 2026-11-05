"""Uniformly place every decoded frame on one512px canvas; no independent framing."""
from pathlib import Path
import json,argparse,copy
import cv2
import numpy as np

def prepare(root,out):
 root=Path(root).resolve();out=Path(out)
 if out.exists() and any(out.iterdir()):raise ValueError('Refusing nonempty output')
 manifest=json.loads((root/'video_manifest.json').read_text());w,h=manifest['working_size'];scale=min(512/w,512/h);tx=(512-w*scale)/2;ty=(512-h*scale)/2;M=np.array([[scale,0,tx],[0,scale,ty]],float)
 out.mkdir(parents=True,exist_ok=True);(out/'frames').mkdir()
 for frame in manifest['frames']:
  image=cv2.imread(str(root/frame['path']),cv2.IMREAD_COLOR)
  if image is None:raise ValueError('Missing source frame')
  result=cv2.warpAffine(image,M,(512,512),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=(255,255,255));dest=f'frames/frame_{frame["sample_index"]:04d}.png';cv2.imwrite(str(out/dest),result);frame['path']=dest
 manifest['working_size']=[512,512];manifest['prior_working_size']=[w,h];manifest['uniform_affine_from_previous_working']=M.tolist();manifest['spatial_processing']='Same aspect-preserving scale and white padding for every frame; no independent object framing or temporal interpolation.';manifest['tracking_status']='No prior tracks copied; input for new image-only detector.';(out/'video_manifest.json').write_text(json.dumps(manifest,indent=2));return {'frame_count':len(manifest['frames']),'uniform_affine':M.tolist()}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.input,a.output)))
