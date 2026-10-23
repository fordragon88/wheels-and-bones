"""Вырезка белого фона заливкой от краёв (для картинок Codex с тёмным контуром): белый мех/крылья внутри контура
не трогаются (BiRefNet делал их полупрозрачными). python art_tests/cut_white.py in.png out.png [порог=236]"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

src, dst = sys.argv[1], sys.argv[2]
thr = int(sys.argv[3]) if len(sys.argv) > 3 else 236
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(int)
white = (a.min(-1) >= thr) & ((a.max(-1) - a.min(-1)) <= 18)
lab, _ = ndimage.label(white)
border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
bg = np.isin(lab, list(border))
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
