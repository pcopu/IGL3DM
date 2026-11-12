"""Run the unchanged image-only LK and observed-cell pipeline on a rendered control.

Only input image pixels and declared acquisition metadata enter reconstruction.
The control ground-truth file is deliberately never read by this program.
"""
from pathlib import Path
import argparse,sys,json,subprocess,hashlib
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'marker_consistency/source'))
from video_tracks import ingest
from prepare_measurements import prepare
from reconstruct_explicit_camera import reconstruct
from assemble_observed_cells import assemble

def run(images,out,stride=1):
 images,out=Path(images),Path(out)
 if stride not in [1,2]:raise ValueError('Only predeclared original or alternate-frame cadence is supported')
 count=96//stride
 if out.exists():raise ValueError('Refusing existing output')
 out.mkdir(parents=True)
 # Declared original render setup: 96 views, 3.75deg steps, 512px, ortho width3.2.
 subprocess.run(['ffmpeg','-v','error','-framerate','24','-i',str(images/'view_%d.png'),'-vf',f'select=not(mod(n\,{stride})),setpts=N/(24*TB)','-frames:v',str(count),'-c:v','ffv1','-pix_fmt','bgr0',str(out/'control-lossless.avi')],check=True)
 ingest(out/'control-lossless.avi',out/'tracking',sample_fps=24,max_frames=count,size=512)
 manifest=json.loads((out/'tracking/video_manifest.json').read_text())
 if len(manifest['frames'])!=count:raise ValueError('Unexpected sample count')
 pixel_equal=[]
 for i,f in enumerate(manifest['frames']):
  pixel_equal.append(bool(np.array_equal(np.array(Image.open(images/f'view_{i*stride}.png').convert('RGB')),np.array(Image.open(out/'tracking'/f['path']).convert('RGB')))))
 if not all(pixel_equal):raise ValueError('Lossless input verification failed')
 prepare(out/'tracking',out/'measurements',count,0,24)
 views=[]
 for i in range(count):
  yaw=i*360/count;a=np.deg2rad(yaw)
  views.append({'sample_index':i,'yaw_deg':yaw,'orthographic_projection_2x4_normalized512':[[160*np.cos(a),160*np.sin(a),0,256],[0,0,-160,256]]})
 camera=out/'declared_acquisition_cameras.json';camera.write_text(json.dumps({'source':'Declared control render setup, independent of ground-truth file; known-camera benchmark only.','views':views},indent=2))
 reconstruct(out/'tracking',out/'measurements',out/'geometry',count,tuple(count*i//8 for i in [1,3,5,7]),max(1,round(count/48)),0,camera)
 assemble(out/'tracking',out/'geometry/candidate_points.json',out/'measurements/measurement_manifest.json',camera,out/'cells')
 (out/'input_verification.json').write_text(json.dumps({'frames':count,'source_image_stride':stride,'all_decoded_pixels_equal_original':all(pixel_equal),'truth_loaded_by_reconstruction':False,'projection_status':'Declared acquisition metadata, not recovered camera calibration.','video_sha256':hashlib.sha256((out/'control-lossless.avi').read_bytes()).hexdigest()},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--images',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--stride',type=int,default=1);a=p.parse_args();run(a.images,a.output,a.stride)
