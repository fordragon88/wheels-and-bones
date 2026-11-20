# Бок о бок: crop.py out.png x0 y0 x1 y1 img1 img2 ... (масштаб ×2)
import sys
from PIL import Image
out = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); ims = [Image.open(p).convert('RGB') for p in sys.argv[6:]]
cs = []
for im in ims:
    if im.size != (1280, 720): im = im.resize((1280, 720))
    c = im.crop((x0, y0, x1, y1)); cs.append(c.resize((c.width*2, c.height*2)))
W = sum(c.width for c in cs) + 8*(len(cs)-1); H = max(c.height for c in cs)
if W > 2400:  # столбиком
    W = max(c.width for c in cs); H = sum(c.height for c in cs) + 8*(len(cs)-1)
    o = Image.new('RGB', (W, H), (255, 0, 255)); y = 0
    for c in cs: o.paste(c, (0, y)); y += c.height + 8
else:
    o = Image.new('RGB', (W, H), (255, 0, 255)); x = 0
    for c in cs: o.paste(c, (x, 0)); x += c.width + 8
o.save(out)
