"""Рисунок коляски (assets/chair_*.png) = кадр поворота в исходном ракурсе, точно в том месте и масштабе, где игра
рисует модель. В браузере, пока кадры докачиваются, показывается рисунок — с ним подмена незаметна.
python art_tests/art_from_turntable.py <job_id>   (старый рисунок -> art_tests/retired/)"""
import os, sys, shutil
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["WNB_TT"] = "1"                               # компьютер тоже рисует кадры, как браузер
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pygame
pygame.init()
pygame.display.set_mode((1280, 720))
import game
from PIL import Image

g = game.Game(headless=True)
g.start_job(sys.argv[1])
art = g.cur["chair_art"]
tt = g._m3d_mesh()
assert isinstance(tt, game.Turntable), "у коляски нет кадров поворота"
r = g._chair_rect()
fr, zoom = g._m3d_frame()
scale = fr.h / 1250.0 * zoom                             # логических px на единицу модели (как _draw_turntable)
ax, ay = fr.x + fr.w / 2, fr.y + fr.h * 0.54
yaw = g._chair_default_view()[0]                   # исходный ракурс (после вводного доворота)
i = tt.index(yaw)
ox, oy = tt.offsets[i]
M = tt.ref / scale                                       # пикселей рисунка на логический пиксель (кадр — 1:1)
name = os.path.splitext(art)[0]
fp = os.path.join(game.ASSETS_DIR, game.TT_DIR, f"{name}_{i:02d}")
if tt.fmt == "jpg":
    frame = Image.open(fp + ".jpg").convert("RGBA")
    frame.putalpha(Image.open(fp + ".a.png").getchannel("A"))
else:
    frame = Image.open(fp + ".png").convert("RGBA")
W, H = round(r.w * M), round(r.h * M)
canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
x, y = round((ax - r.x) * M + ox * tt.ref), round((ay - r.y) * M + oy * tt.ref)
canvas.alpha_composite(frame, (x, y)) if x >= 0 and y >= 0 else canvas.paste(frame, (x, y), frame)
over = (max(0, -x), max(0, -y), max(0, x + frame.width - W), max(0, y + frame.height - H))
dst = os.path.join(game.ASSETS_DIR, art)
os.makedirs(os.path.join(HERE, "retired"), exist_ok=True)
old = os.path.join(HERE, "retired", art)
if not os.path.exists(old):
    shutil.copy(dst, old)
canvas.save(dst, optimize=True)
import json                                               # игра: пока кадры идут — рисунок, кружки уже от модели
for n in ("index.json", "index_folk.json"):
    ip = os.path.join(game.ASSETS_DIR, game.TT_DIR, n)
    if os.path.exists(ip):
        d = json.load(open(ip, encoding="utf-8"))
        if art in d:
            d[art]["art_matched"] = True
            json.dump(d, open(ip, "w", encoding="utf-8"), separators=(",", ":"))
print(f"{art}: {W}×{H}, кадр {i} в ({x}, {y}); за краем рисунка (л, в, п, н): {over}")
