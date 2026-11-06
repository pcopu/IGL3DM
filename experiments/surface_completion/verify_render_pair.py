"""Verify local paired Blender render outputs and make a small evidence montage."""
import argparse,json,math
from pathlib import Path
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('dented',type=Path);p.add_argument('undented',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
d=json.loads((a.dented/'ground_truth.json').read_text());u=json.loads((a.undented/'ground_truth.json').read_text());rd=json.loads((a.dented/'render_report.json').read_text());ru=json.loads((a.undented/'render_report.json').read_text())
assert d['quads']==u['quads'] and d['cell_palette_indices']==u['cell_palette_indices']
assert len(d['frames'])==len(u['frames'])==rd['views']==ru['views']
for x,y in zip(d['frames'],u['frames']):assert x['camera_matrix_world']==y['camera_matrix_world']
for folder in [a.dented,a.undented]:
 images=sorted(folder.glob('frame_*.png'));assert len(images)==rd['views']
 for image in images:
  with Image.open(image) as im:assert im.size==(rd['size'],rd['size']);im.verify()
center=rd['dent_center_vertex_ids'][0]
frames=lambda raw:[f['frame'] for f in raw['frames'] if f['observations'][center]['visible']]
# Base surface labels, not measured image visibility.
report=dict(status='EVALUATION ONLY; paired known geometry, not real reconstruction',blender_version='4.3.2',views=rd['views'],size=rd['size'],samples=rd['samples'],same_quads=True,same_colors=True,same_camera_matrices=True,all_images_decoded=True,dent_center_vertex_id=center,dented_visible_frames=frames(d),undented_visible_frames=frames(u),dented_topology=rd,undented_topology=ru,warning='Vertex visibility uses unoccluded base-surface rays, not black wire overlay or pixel darkness. No detector accuracy has been evaluated.')
a.output.mkdir(parents=True,exist_ok=True);(a.output/'dimple_render_validation.json').write_text(json.dumps(report,indent=2))
canvas=Image.new('RGB',(960,720),'white');draw=ImageDraw.Draw(canvas)
for row,folder in enumerate([a.dented,a.undented]):
 for col,index in enumerate([0,2,4]):
  im=Image.open(folder/f'frame_{index:03d}.png').convert('RGB').resize((320,320));canvas.paste(im,(320*col,30+row*345));draw.text((320*col+8,12+row*345),('Dimple' if row==0 else 'Undented')+f' | yaw {360*index/rd["views"]:.0f} deg',fill='black')
draw.text((8,706),'Evaluation-only fixed colored quad mesh; matched geometry ablation, no real input.',fill='black');canvas.save(a.output/'dimple_render_pair.png')
print(json.dumps({k:report[k] for k in ['views','size','dented_visible_frames','undented_visible_frames','same_quads','same_colors','same_camera_matrices','all_images_decoded']},indent=2))
