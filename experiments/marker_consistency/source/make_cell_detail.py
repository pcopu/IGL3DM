import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'pear/quad_cells';graphs=json.loads((OUT/'quad_graph.json').read_text());pairs=json.loads((OUT/'cell_matches.json').read_text());vertices=json.loads((OUT/'candidate_vertices.json').read_text())
ids={}
for p in vertices:
 for v,n in p['view_node_ids']:ids[v,n]=p['track_id'].replace('vertex_','p')
match=min(pairs[0]['neighbor_supported_cell_matches'],key=lambda m:np.linalg.norm(np.array(next(c for c in graphs[0]['cells'] if c['cell_id']==m['from_cell_id'])['center'])-[240,330]))
raw=Image.open(ROOT/'pear/input.png');W,H=raw.size;canvas=Image.new('RGB',(1240,720),'white');d=ImageDraw.Draw(canvas)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
for v,cid in [(0,match['from_cell_id']),(1,match['to_cell_id'])]:
 cell=raw.crop((round(v*W/4),0,round((v+1)*W/4),round(H/2))).resize((512,512));cc=next(c for c in graphs[v]['cells'] if c['cell_id']==cid)['center'];x0=int(cc[0]-70);y0=int(cc[1]-70)
 pic=cell.crop((x0,y0,x0+140,y0+140)).resize((600,600));dp=ImageDraw.Draw(pic)
 for c in graphs[v]['cells']:
  cx,cy=c['center']
  if x0<cx<x0+140 and y0<cy<y0+140:
   pts=[tuple((np.asarray(graphs[v]['nodes'][n]['xy'])-[x0,y0])*600/140) for n in c['node_ids']];dp.line(pts+[pts[0]],fill='#1275ad',width=2)
   dp.text(((cx-x0)*600/140,(cy-y0)*600/140),f"c{c['cell_id']}",font=small,fill='#a01492',anchor='mm',stroke_width=1,stroke_fill='white')
 for n in graphs[v]['nodes']:
  x,y=n['xy']
  if x0<x<x0+140 and y0<y<y0+140 and (v,n['node_id']) in ids:
   X,Y=(np.array([x,y])-[x0,y0])*600/140;dp.ellipse((X-4,Y-4,X+4,Y+4),fill='#e12b2b');dp.text((X+5,Y+3),ids[v,n['node_id']],font=small,fill='#b01922',stroke_width=1,stroke_fill='white')
 canvas.paste(pic,(20+v*620,70));d.text((20+v*620,22),f'View {v}: software-detected cell/corner tags (enlarged)',font=font,fill='black')
d.text((20,685),'Blue: detected quad edges. Purple c: local cell IDs. Red p: candidate propagated corner IDs, not proven physical identity.',font=small,fill='black');canvas.save(OUT/'software_tagged_detail.png')
