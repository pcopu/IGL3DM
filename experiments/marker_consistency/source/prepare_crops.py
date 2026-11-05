"""Prepare common-grid crops from the committed synthetic input for this diagnostic."""
from pathlib import Path
import shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
source=ROOT.parents[1]/'docs/experiments/14-marker-audit/input.png'
(ROOT/'generated').mkdir(exist_ok=True)
shutil.copy2(source,ROOT/'generated/input.png')
im=Image.open(source);w,h=im.size
for i in range(8):
    box=(round((i%4)*w/4),round((i//4)*h/2),round((i%4+1)*w/4),round((i//4+1)*h/2))
    im.crop(box).save(ROOT/f'generated/view_{i}.png')
print('Prepared eight source-grid crops; no independent object recentering or scaling.')
