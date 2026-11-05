from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results';FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
f=lambda n:ImageFont.truetype(FONT,n)
# Three source comparisons at native scale with explicit inspected failures.
canvas=Image.new('RGB',(1500,1140),'#f4f6f8');d=ImageDraw.Draw(canvas)
d.text((26,20),'Surface-marked lion: correspondence audit',font=f(32),fill='#182938')
d.text((26,62),'One generated eight-view atlas. Printed patches wrap, but IDs are not reliably surface-fixed.',font=f(21),fill='#394957')
for col,v in enumerate([2,6,7]):
 im=Image.open(ROOT/f'generated/view_{v}.png').resize((480,480));dr=ImageDraw.Draw(im)
 if v in [6,7]:
  boxes=([(88,225,173,314),(162,269,213,325)] if v==6 else [(109,229,169,314),(160,270,210,324)])
  for b in boxes:dr.rectangle(tuple(x*480/443.5 for x in b),outline='#e2272b',width=5)
 canvas.paste(im,(10+col*500,108));d.text((24+col*500,596),f'View {v}: '+('left flank 05 / 06 / 07' if v==2 else 'same IDs on opposite flank'),font=f(19),fill='#142935')
 if v in [6,7]:d.text((24+col*500,625),'Red boxes: two patches both labeled 18',font=f(17),fill='#be1e28')
# Mane identity flip excerpt, no reworking of pixels.
for col,v in enumerate([0,1,2]):
 im=Image.open(ROOT/f'generated/view_{v}.png');crop=im.crop((110 if v==0 else 80,60,320 if v==0 else 280,180)).resize((400,240))
 canvas.paste(crop,(35+col*500,691));d.text((35+col*500,941),f'View {v}: mane patch '+('04' if v in [0,2] else '12 replaces 04'),font=f(20),fill='#142935')
d.text((26,997),'Inventory: 21 of 24 requested IDs appear; IDs 13, 14, 15 never appear.',font=f(22),fill='#142935')
d.text((26,1032),'Missing/occluded patches are not scored as geometric errors. Duplicate IDs are direct contradictions.',font=f(20),fill='#394957')
d.text((26,1070),'Gate: reject global marker identity. Any requested mesh is exploratory and is not validated by these marks.',font=f(20),fill='#be1e28')
canvas.save(OUT/'identity_failures.png')
# Compact control comparison chart rendered as scientific evidence.
r=json.loads((ROOT/'controls/summary.json').read_text())
can=Image.new('RGB',(1400,760),'white');d=ImageDraw.Draw(can)
d.text((25,22),'Known 3D control: test the validator, not the lion',font=f(30),fill='#142935')
d.text((25,65),'256 analytic ellipsoid corner tracks; held-out views 1 and 5; no model weights or lion mesh.',font=f(20),fill='#435365')
y=125
names=[('exact','Exact projections'),('noise_0p4px','0.4 px measurement noise'),('horizontal_swap_heldout','Same-height ID swaps'),('warped_heldout','12 px surface warps'),('wrong_requested_camera','Actual camera differs by 10°'),('consistent_wrong_identity','Globally permuted identities')]
d.text((25,y),'Control',font=f(20),fill='black');d.text((525,y),'Held-out p95',font=f(20),fill='black');d.text((785,y),'Epipolar p95',font=f(20),fill='black');d.text((1065,y),'Gate',font=f(20),fill='black');y+=52
for k,label in names:
 a=r[k];d.rectangle((15,y-8,1380,y+48),fill='#f2f5f7' if y%2 else '#fafafa')
 d.text((25,y),label,font=f(21),fill='black');d.text((525,y),f"{a['heldout_reprojection_px']['p95']:.2f} px",font=f(21),fill='black');d.text((785,y),f"{a['known_camera_epipolar_px']['p95']:.2f} px",font=f(21),fill='black');d.text((1065,y),'PASS' if a['gate']['pass'] else 'REJECT',font=f(21),fill='#167345' if a['gate']['pass'] else '#be1e28');y+=70
d.text((25,640),'Same-height swaps can pass epipolar tests. Consistently wrong IDs can pass all reprojection tests.',font=f(21),fill='#be1e28')
d.text((25,682),'Therefore: low residuals support conditional consistency, not true identity or original 3D accuracy.',font=f(21),fill='#142935')
can.save(OUT/'control_comparison.png')
