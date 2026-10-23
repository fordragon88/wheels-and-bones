"""Вырезка белого фона заливкой от краёв (для картинок Codex с тёмным контуром): белый мех/крылья внутри контура
не трогаются (BiRefNet делал их полупрозрачными). Замкнутые чисто-белые участки (между спицами, прядями, в просветах
рамы) тоже убираются, кроме рамок --keep=x0,y0,x1,y1[;…] (лицо: белки глаз).
python art_tests/cut_white.py in.png out.png [порог=236] [--keep=…]"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

src, dst = sys.argv[1], sys.argv[2]
args = [x for x in sys.argv[3:] if not x.startswith("--")]
thr = int(args[0]) if args else 236
keep = [tuple(int(v) for v in b.split(",")) for x in sys.argv[3:] if x.startswith("--keep=") for b in x[7:].split(";")]
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(int)
white = (a.min(-1) >= thr) & ((a.max(-1) - a.min(-1)) <= 18)
lab, _ = ndimage.label(white)
border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
bg = np.isin(lab, list(border))
sizes = ndimage.sum(np.ones_like(lab), lab, index=range(1, lab.max() + 1))
means = ndimage.mean(a.mean(-1), lab, index=range(1, lab.max() + 1))
objs = ndimage.find_objects(lab)
for i in range(1, lab.max() + 1):
    if i in border or sizes[i - 1] < 40 or means[i - 1] < 249:
        continue
    sl = objs[i - 1]
    if any(sl[1].start >= k[0] and sl[0].start >= k[1] and sl[1].stop <= k[2] and sl[0].stop <= k[3] for k in keep):
        continue
    bg |= lab == i
# мягкий край: полупрозрачность по светлоте в полосе 2 px у границы фона
edge = ndimage.binary_dilation(bg, iterations=2) & ~bg
lum = a.mean(-1)
alpha = np.where(bg, 0, 255).astype(float)
alpha[edge] = np.clip((255 - lum[edge]) / (255 - 170) * 255, 0, 255)
out = im.convert("RGBA")
out.putalpha(Image.fromarray(alpha.astype(np.uint8)))
bb = Image.fromarray((alpha > 8).astype(np.uint8) * 255).getbbox()
out.crop(bb).save(dst)
print("ok", out.crop(bb).size)
