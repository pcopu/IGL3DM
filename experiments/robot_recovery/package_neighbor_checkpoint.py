"""Package exact endpoint-research evidence and replay metadata, excluding unrelated data."""
from pathlib import Path
import argparse,json,hashlib,zipfile
HERE=Path(__file__).resolve().parent

def build(root,mode,out):
 files={};repo=HERE.parents[1]
 def add(path,name):
  data=path.read_bytes()
  if path.suffix in ['.json','.py','.md','.txt','.log']:data=data.decode().replace(str(root.resolve().parents[1])+'/', '<workspace>/').encode()
  if name in files:raise ValueError('Repeated path')
  files[name]=data
 def directory(path,prefix,omit_frames=False):
  if not path.exists():raise ValueError('Missing declared evidence directory: '+str(path))
  for p in sorted(path.rglob('*')):
   rel=p.relative_to(path)
   if p.is_file() and p.suffix in ['.json','.png','.ply','.py','.avi','.log'] and not ('frames' in rel.parts and omit_frames):add(p,prefix+'/'+str(rel))
 for n in ['trim_orbit_neighborhoods.py','test_orbit_neighborhoods.py','evaluate_neighbor_checkpoint.py','diagnose_periodic_identities.py','render_neighbor_checkpoint.py','render_independent_control.py','associate_orbit_hypotheses.py','assemble_observed_cells.py','score_physical_faces.py','package_neighbor_checkpoint.py','README.md','LOG.md']:add(HERE/n,'source/'+n)
 add(repo/'AGENTS.md','source/AGENTS.md');add(repo/'docs/experiments/25-kling-robot/neighbor-support-checkpoint.png','evidence/neighbor-support-checkpoint.png')
 for n in ['neighbor-control-summary.json','neighbor-target-summary.json','neighbor-final-replay.json','periodic-identity-diagnosis.json']:add(HERE/'results'/n,'results/'+n)
 if mode=='development':
  directory(root/'identity_diagnostics','evaluation-only/identity-diagnostics')
  for name in ['pear','bent','barrel']:
   for tag in ['', 'final_']:
    for v in ['frozen','refit']:directory(root/f'recovery_{name}_neighbors48_{tag}{v}',f'{name}/{tag}{v}')
 elif mode=='waist':
  directory(root/'recovery_waist_control48','input-and-lk-control',True);add(root/'independent_warped_waist96/ground_truth.json','evaluation-only/ground_truth.json');directory(root/'recovery_waist_hypotheses48_resolvable','original-orbit')
  for tag in ['', 'final_']:
   for v in ['frozen','refit']:directory(root/f'recovery_waist_neighbors48_{tag}{v}',tag+v)
 elif mode=='robot':
  for tag in ['', 'final_']:
   for v in ['frozen','refit']:directory(root/f'recovery_robot_neighbors_{tag}{v}',tag+v)
  add(root/'grid_variable_projections.json','input/frozen-pchip-camera.json');add(root/'recovery_robot_hypotheses_resolvable/normalized_measurement_manifest.json','input/normalized-measurement-manifest.json')
 else:raise ValueError('Unknown mode')
 for p in sorted(root.glob('neighbor*tests_final.log')):add(p,'logs/'+p.name)
 for p in sorted(root.glob('recovery_*neighbors*.log')):
  include=('robot' in p.name) if mode=='robot' else ('waist' in p.name) if mode=='waist' else any(s in p.name for s in ['pear','bent','barrel'])
  if include:add(p,'logs/'+p.name)
 if mode=='waist':
  for n in ['recovery_waist_render.log','recovery_waist_control48.log','recovery_waist_hypotheses48_resolvable.log']:add(root/n,'logs/'+n)
 files['README.txt']=f'''IGL3DM endpoint-support checkpoint: {mode}.\nExperimental sparse measured geometry only. All rejected decisions and original withheld predictions are retained.\nControl truth is evaluation-only, never target reference geometry.\nOriginal pear/bent/barrel inputs and broad-view hypotheses are in the preceding public orbit evidence archives. Robot input is the preceding robot-reproducibility archive; base association is robot-orbit-association.zip.\nThe fourth warped-waist input is exact48-frame FFV1 AVI, with96-view evaluation-only truth.\nInitial and final variants have identical XYZ, observations and intervals; final variants correct metadata provenance and input guards.\nThe primary variant preserves XYZ; refit uses retained calibration observations only.\nLocal workspace prefixes in textual logs are normalized to <workspace> during packaging.\nByte-identical repeated files use explicit aliases. Run restore_aliases.py after extraction; verify MANIFEST.json.\n'''.encode()
 manifest={n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in sorted(files.items())};unique={};seen={};aliases={}
 for n,d in sorted(files.items()):
  digest=hashlib.sha256(d).hexdigest()
  if digest in seen:aliases[n]=seen[digest]
  else:seen[digest]=n;unique[n]=d
 unique['MANIFEST.json']=json.dumps(manifest,indent=2).encode();unique['ALIASES.json']=json.dumps(aliases,indent=2).encode();unique['restore_aliases.py']=b"from pathlib import Path\nimport json,hashlib\nr=Path(__file__).resolve().parent\nfor target,source in json.loads((r/'ALIASES.json').read_text()).items():\n a=(r/target).resolve();b=(r/source).resolve()\n if not a.is_relative_to(r) or not b.is_relative_to(r):raise ValueError('Unsafe alias')\n data=b.read_bytes()\n if a.exists() and a.read_bytes()!=data:raise ValueError('Conflicting file')\n a.parent.mkdir(parents=True,exist_ok=True);a.write_bytes(data)\nfor name,meta in json.loads((r/'MANIFEST.json').read_text()).items():\n p=(r/name).resolve()\n if not p.is_relative_to(r) or hashlib.sha256(p.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Hash mismatch')\nprint('All logical evidence files restored and verified')\n"
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,d in sorted(unique.items()):
   info=zipfile.ZipInfo(n,(2026,11,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,d)
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None
  for n,m in manifest.items():assert hashlib.sha256(z.read(aliases.get(n,n))).hexdigest()==m['sha256']
 return {'file':out.name,'mode':mode,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'logical_files':len(manifest),'stored_members':len(unique),'aliases':len(aliases),'all_logical_hashes_verified':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['development','waist','robot'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.root,a.mode,a.output),indent=2))
