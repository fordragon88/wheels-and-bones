"""Починка «призрачных» полупрозрачных мест после вырезки BiRefNet для картинок на чистом белом фоне.
python art_tests/alpha_repair.py <оригинал_на_белом.png> <вырезка.png> <выход.png>
Альфа = max(альфа BiRefNet, «отличие от белого»), но только рядом с объектом (маска BiRefNet, расширенная);
в достроенных местах цвет берётся из оригинала."""
import sys
import numpy as np
from PIL import Image, ImageFilter
src, cut, out = sys.argv[1:4]
o = Image.open(src).convert("RGB")
c = Image.open(cut).convert("RGBA")
if c.size != o.size:
    c = c.resize(o.size, Image.LANCZOS)
O = np.asarray(o).astype(np.float32)
C = np.asarray(c).astype(np.float32)
a0 = C[..., 3] / 255.0
diff = (255.0 - O.min(-1))                      # насколько пиксель темнее белого
m = np.clip((diff - 10.0) / 35.0, 0, 1)
near = np.asarray(Image.fromarray((a0 > 0.05).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(41))) > 0
m = np.where(near, m, 0.0)
a = np.maximum(a0, m)
rgb = np.where((m > a0)[..., None], O, C[..., :3])
res = np.dstack([rgb, a * 255]).clip(0, 255).astype(np.uint8)
Image.fromarray(res, "RGBA").save(out)
print("достроено пикселей:", int((m > a0 + 0.1).sum()))
