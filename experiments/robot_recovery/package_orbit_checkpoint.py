"""Package scoped broad-view research evidence with lossless duplicate aliases."""
from pathlib import Path
import argparse,json,zipfile,hashlib

HERE=Path(__file__).resolve().parent

def build(root,mode,out):
 files={};repo=HERE.parents[1]
 def add(path,name):
  path=Path(path);data=path.read_bytes()
  if path.suffix in ['.json','.log','.md','.py','.txt']:data=data.decode().replace(str(root.resolve().parents[1])+'/', '<workspace>/').encode()
  if name in files:raise ValueError('Duplicate logical archive path')
  files[name]=data
 def directory(path,prefix,omit_frames=False):
  for p in sorted(path.rglob('*')):
   relative=p.relative_to(path)
   if omit_frames and 'frames' in relative.parts:continue
   if p.is_file() and p.suffix in ['.json','.png','.ply','.py','.avi','.log']:add(p,prefix+'/'+str(relative))
 for name in ['associate_orbit_hypotheses.py','validate_orbit_artifacts.py','render_independent_control.py','render_orbit_checkpoint.py','assemble_observed_cells.py','score_physical_faces.py','test_orbit_association.py','package_orbit_checkpoint.py','README.md','LOG.md']:add(HERE/name,'source/'+name)
 for name in ['orbit-hypothesis-control-summary.json','orbit-hypothesis-target-summary.json','orbit-final-replay.json','orbit-runtime-versions.json']:add(HERE/'results'/name,'results/'+name)
 add(repo/'docs/experiments/25-kling-robot/orbit-association-checkpoint.png','evidence/orbit-association-checkpoint.png')
 if mode=='pear':
  folders=['recovery_orbit_hypotheses48','recovery_orbit_hypotheses48_unique','recovery_orbit_hypotheses48_veto','recovery_orbit_hypotheses48_resolvable','recovery_orbit_hypotheses96_veto','recovery_orbit_hypotheses96_resolvable']
  for folder in folders:directory(root/folder,'hypotheses/'+folder)
  for count in [48,96]:
   d=root/f'recovery_face_control{count}_avi'
   for name in ['input_verification.json','declared_acquisition_cameras.json']:add(d/name,f'input{count}/'+name)
  for p in sorted(root.glob('recovery-orbit-hypotheses*.log')):add(p,'logs/'+p.name)
 elif mode in ['bent','barrel']:
  shape='bent_ovoid' if mode=='bent' else 'squat_barrel';control=root/f'recovery_{mode}_control48';directory(control,'control-input-and-lk-baseline',omit_frames=True);add(root/f'independent_{shape}96/ground_truth.json','evaluation-only/ground_truth.json')
  variants=['', '_veto','_resolvable'] if mode=='bent' else ['', '_resolvable']
  for suffix in variants:directory(root/f'recovery_{mode}_hypotheses48{suffix}','hypotheses/'+('base' if not suffix else suffix[1:]))
  for p in sorted(root.glob(f'recovery-{mode}*.log')):add(p,'logs/'+p.name)
  renderlog=root/('recovery-render-independent-control.log' if mode=='bent' else 'recovery-render-barrel-control.log');add(renderlog,'logs/'+renderlog.name)
 elif mode=='robot':
  directory(root/'recovery_robot_hypotheses_resolvable','robot');add(root/'grid_variable_projections.json','input/frozen-pchip-camera.json');add(root/'grid_input/video_manifest.json','input/normalized-frame-manifest.json');add(HERE/'artifacts/robot-orbit-observed-cells.ply','model/robot-orbit-observed-cells.ply')
  for p in sorted(root.glob('recovery-robot-hypotheses*.log')):add(p,'logs/'+p.name)
  for p in sorted(root.glob('recovery-orbit*tests*.log')):add(p,'logs/'+p.name)
 else:raise ValueError('Unknown package mode')
 files['README.txt']=f'''IGL3DM broad-view association evidence: {mode}.\nAll actual predictions, wrong and unresolved identities, source snapshots and failed variants are retained.\nControl geometry is EVALUATION ONLY. It is never the target robot reference.\nThe pear control input video/truth are in the preceding public robot-physical-identity-audit.zip.\nThe robot input is the preceding public robot-reproducibility.zip; its normalized frames follow the repository's shared transform.\nNew independent controls include exact48-frame FFV1 AVI input and full synthetic evaluation truth.\nKnown cameras are declared control acquisition metadata. Robot camera estimates are experimental.\nMissing measurements and surfaces are not synthesized. These are research candidates, not validated assets.\nDuplicate bytes are stored once; ALIASES.json preserves every logical path. Run restore_aliases.py after extraction if full paths are needed.\n'''.encode()
 manifest={n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in sorted(files.items())};unique={};seen={};aliases={}
 for n,d in sorted(files.items()):
  digest=hashlib.sha256(d).hexdigest()
  if digest in seen:aliases[n]=seen[digest]
  else:seen[digest]=n;unique[n]=d
 unique['MANIFEST.json']=json.dumps(manifest,indent=2).encode();unique['ALIASES.json']=json.dumps(aliases,indent=2).encode();unique['restore_aliases.py']=b"from pathlib import Path\nimport json\nr=Path(__file__).resolve().parent\nfor target,source in json.loads((r/'ALIASES.json').read_text()).items():\n a=(r/target).resolve();b=(r/source).resolve()\n if not a.is_relative_to(r) or not b.is_relative_to(r):raise ValueError('Unsafe alias path')\n data=b.read_bytes()\n if a.exists() and a.read_bytes()!=data:raise ValueError('Refusing conflicting existing file')\n a.parent.mkdir(parents=True,exist_ok=True);a.write_bytes(data)\nprint('Restored identical evidence aliases')\n"
 out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name,data in sorted(unique.items()):
   info=zipfile.ZipInfo(name,(2026,11,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise ValueError('Archive CRC failure')
  for n,v in manifest.items():
   if hashlib.sha256(z.read(aliases.get(n,n))).hexdigest()!=v['sha256']:raise ValueError('Logical payload mismatch')
 return {'file':out.name,'mode':mode,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'logical_evidence_files':len(manifest),'stored_members':len(unique),'identical_aliases':len(aliases),'all_logical_member_hashes_verified':True}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['pear','bent','barrel','robot'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.root,a.mode,a.output),indent=2))
