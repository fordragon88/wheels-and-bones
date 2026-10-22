"""Скачать картинки коляски (список URL) в art_tests/meshy_ref/_raw/<ключ>/ и сделать лист превью.
python art_tests/meshy_fetch.py <ключ> <url> [url…]"""
import os, sys, subprocess
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
key, urls = sys.argv[1], sys.argv[2:]
out = os.path.join(HERE, "meshy_ref", "_raw", key)
os.makedirs(out, exist_ok=True)
for i, u in enumerate(urls):
    name = f"{i:02d}_" + os.path.basename(u.split("?")[0])
    fp = os.path.join(out, name)
    if not os.path.exists(fp):
        subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", "Mozilla/5.0", "-o", fp, u])
cells = []
for f in sorted(os.listdir(out)):
    if f.startswith("_"):
        continue
    try:
        im = Image.open(os.path.join(out, f)).convert("RGBA")
    except Exception:
        print("не картинка:", f)
        continue
    bg = Image.new("RGBA", im.size, "white")
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    size = im.size
    im.thumbnail((300, 300))
    c = Image.new("RGB", (300, 320), "white")
    c.paste(im, ((300 - im.width) // 2, 0))
    ImageDraw.Draw(c).text((4, 304), f"{f[:34]} {size[0]}x{size[1]}", fill="black")
    cells.append(c)
sheet = Image.new("RGB", (300 * 6, 320 * max(1, (len(cells) + 5) // 6)), "white")
for i, c in enumerate(cells):
    sheet.paste(c, ((i % 6) * 300, (i // 6) * 320))
sheet.save(os.path.join(out, "_sheet.png"))
print(len(cells), "картинок ->", out)
