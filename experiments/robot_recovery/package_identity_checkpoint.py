"""Package the explicitly authorized experiment evidence, never unrelated workspace data."""
from pathlib import Path
import argparse,json,zipfile,hashlib

def package(root,out):
 source=Path(__file__).resolve().parent;repo=source.parents[1];files={}
 def add(path,name=None):
  path=Path(path)
  if not path.is_file():raise FileNotFoundError(path)
  data=path.read_bytes()
  if path.suffix in ['.json','.log','.txt','.md','.py']:
   text=data.decode();workspace=str(root.resolve().parents[1]);text=text.replace(workspace+'/', '<workspace>/');data=text.encode()
  name=name or path.name
  if name in files:raise ValueError('Duplicate archive name '+name)
  files[name]=data
 for p in sorted(source.glob('*.py')):add(p,'source/'+p.name)
 for n in ['README.md','LOG.md']:add(source/n,'source/'+n)
 add(source/'results/physical-face-control-summary.json','results/physical-face-control-summary.json')
 add(repo/'docs/experiments/25-kling-robot/physical-identity-audit.png','evidence/physical-identity-audit.png')
 add(source.parent/'marker_consistency/controls/known_pear_96/ground_truth.json','control96/evaluation-only-ground-truth.json')
 for label,folder in [('control96','recovery_face_control96_avi'),('control48','recovery_face_control48_avi')]:
  d=root/folder
  if label=='control96':add(d/'control-lossless.avi',label+'/control-lossless.avi')
  for n in ['input_verification.json','declared_acquisition_cameras.json']:add(d/n,label+'/'+n)
  for n in ['tracks.json','video_manifest.json','tracking_overview.png']:add(d/'tracking'/n,label+'/tracking/'+n)
  add(d/'measurements/measurement_manifest.json',label+'/measurement_manifest.json')
  for sub in ['geometry','cells','joined','joined_cells','quarantined','historical_eight_frame']:
   if not (d/sub).exists():continue
   for p in sorted((d/sub).rglob('*')):
    if p.is_file() and p.suffix in ['.json','.ply','.png']:add(p,label+'/'+str(p.relative_to(d)))
  if (d/'physical_identity_evaluation.json').exists():add(d/'physical_identity_evaluation.json',label+'/physical_identity_evaluation.json')
 for folder in ['recovery_dense_cells','recovery_conflict_quarantine','recovery_joined_points','recovery_joined_cells']:
  for p in sorted((root/folder).rglob('*')):
   if p.is_file() and p.suffix in ['.json','.ply']:add(p,'robot/'+folder+'/'+str(p.relative_to(root/folder)))
 add(root/'grid_variable_projections.json','robot/frozen-pchip-projections.json')
 for p in sorted(root.glob('recovery-face*.log')):add(p,'logs/'+p.name)
 for n in ['recovery-conflict-quarantine.log','recovery-control96-join.log','recovery-control48-join.log','recovery-robot-join.log']:add(root/n,'logs/'+n)
 files['README.txt']=b'''IGL3DM physical-identity checkpoint, 2026-11-12.\nTruth is evaluation-only and belongs to a distinct synthetic control, never the robot target.\nThe source controls were rendered before this experiment. The control96 FFV1 AVI decodes pixel-identically to all 96 original images.\nThe control48 sequence uses every second original frame; its input verification and full measurements are retained.\nUse the previous public robot-reproducibility.zip for the exact robot input and original detector/tracker sources from the repository.\nAll new point/face identities, join proposals, rejection reasons, camera assumptions, full evaluation rows, logs and candidate models are retained here.\nThese models are incomplete conditional observations. No hidden geometry, target reference mesh, credentials or unrelated private files are included.\n'''
 manifest={name:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(files.items())}
 unique={};hash_to_name={};aliases={}
 for name,data in sorted(files.items()):
  digest=hashlib.sha256(data).hexdigest()
  if digest in hash_to_name:aliases[name]=hash_to_name[digest]
  else:unique[name]=data;hash_to_name[digest]=name
 unique['MANIFEST.json']=json.dumps(manifest,indent=2).encode();unique['ALIASES.json']=json.dumps(aliases,indent=2).encode()
 unique['restore_aliases.py']=b"from pathlib import Path\nimport json\nr=Path(__file__).resolve().parent\nfor target,source in json.loads((r/'ALIASES.json').read_text()).items():\n a=(r/target).resolve();b=(r/source).resolve()\n if not a.is_relative_to(r) or not b.is_relative_to(r):raise ValueError('Unsafe alias path')\n data=b.read_bytes()\n if a.exists() and a.read_bytes()!=data:raise ValueError('Refusing conflicting existing file')\n a.parent.mkdir(parents=True,exist_ok=True);a.write_bytes(data)\nprint('Restored identical evidence aliases')\n"
 unique['ARCHIVE_LAYOUT.txt']=b'Byte-identical repeated evidence payloads are stored once. MANIFEST.json preserves every expanded logical path and checksum. ALIASES.json maps duplicate paths to stored payloads. After extraction, run python restore_aliases.py to recreate all original evidence paths. No observations are removed.\n'
 out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name,data in sorted(unique.items()):
   info=zipfile.ZipInfo(name,(2026,11,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
 with zipfile.ZipFile(out) as z:
  if z.testzip() is not None:raise ValueError('Archive CRC failure')
  for name,expected in manifest.items():
   data=z.read(aliases.get(name,name))
   if hashlib.sha256(data).hexdigest()!=expected['sha256']:raise ValueError('Member hash mismatch')
 return {'file':out.name,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'stored_members':len(unique),'logical_evidence_members':len(manifest),'byte_identical_aliases':len(aliases),'verified_logical_member_hashes':len(manifest)}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(package(a.root,a.output),indent=2))
