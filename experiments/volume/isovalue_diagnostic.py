"""Bounded global isovalue diagnostic. No field optimization or anatomy edits."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np
from fit_volume import export
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--field',action='append',required=True,help='label=path/to/field.npz; NPZ sdf shape1x1xNxNxN')
 parser.add_argument('--renderer',type=Path,required=True)
 parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();OUT=args.output
 if OUT.exists() and any(OUT.iterdir()):raise FileExistsError(f'Refusing nonempty output: {OUT}')
 OUT.mkdir(exist_ok=True,parents=True)
 for item in args.field:
  name,path=item.split('=',1);field_path=Path(path)
  if not name or Path(name).name!=name:raise ValueError('Field label must be a single directory name')
  sdf=np.load(field_path)['sdf'][0,0]
  if sdf.ndim!=3 or len(set(sdf.shape))!=1 or not np.isfinite(sdf).all():raise ValueError('Expected finite cubic SDF')
  for level in [0.,-.002,-.004,-.008,-.012]:
   tag='level_'+str(abs(level)).replace('.','p');out=OUT/name/tag
   out.mkdir(parents=True);info=export(sdf-level,out)
   (out/'config.json').write_text(json.dumps({'source_field':str(field_path),'source_sha256':hashlib.sha256(field_path.read_bytes()).hexdigest(),'isovalue':level,'cleanup':False,'integrity':info},indent=2))
   cmd=['blender','-b','-t','4','--python-exit-code','1','--python',str(args.renderer),'--','--mesh',str(out/'mesh.json'),'--output',str(out/'renders'),'--size','192','--views','16','--samples','4']
   with (out/'render.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
   print(name,level,info,flush=True)
 print('DONE',flush=True)
if __name__=='__main__':main()
