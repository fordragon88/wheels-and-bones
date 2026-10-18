"""Обороты колясок для браузерной версии (там нет numpy/OpenGL — 3D-модель не отрисовать на лету):
каждая детальная модель рендерится на GPU с N углов в кадр окна «ОСМОТР 3D» и сохраняется PNG (256 цветов).
python art_tests/build_turntables.py [N]   → assets/turntable/<chair>_<i>.png + assets/turntable/index.json
Кадр i снят при yaw = -0.75 + i * 2π / N (стартовый ракурс игры), pitch = 0.28, zoom как в осмотре."""
import os, sys, json, math, io
os.environ.setdefault("SDL_VIDEODRIVER", "windows")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import pygame
pygame.init()
pygame.display.set_mode((64, 64), pygame.HIDDEN)
import game
from PIL import Image

N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
OUT = os.path.join(ROOT, "assets", "turntable")
os.makedirs(OUT, exist_ok=True)
W, H = 860, 524                     # _v3d_view_rect при RS = 1
YAW0, PITCH = -0.75, 0.28
assert game.gl_ok(), "нужен OpenGL (moderngl) — запускать на компьютере с видеокартой"

kinds = {}
for j in game.ALL_JOBS:
    for v in (j.get("variants") or [None]):
        jj = game.resolve_job(j, j["variants"].index(v)) if v else j
        kinds[jj.get("chair_art")] = jj.get("kind", "manual")
index, total = {}, 0
for art, fn in game.AI_MODELS.items():
    mesh = game.get_ai_chair3d(art)
    if mesh is None:
        continue
    zoom = 0.8 if kinds.get(art) == "power" else 0.9
    name = os.path.splitext(art)[0]
    frames = []
    for i in range(N):
        yaw = YAW0 + i * 2 * math.pi / N
        img, pick = game.gl_render(mesh, yaw, PITCH, (W, H), zoom)
        bb = pick.bbox
        raw = pygame.image.tobytes(img, "RGBA")
        im = Image.frombytes("RGBA", img.get_size(), raw).crop((bb.x, bb.y, bb.right, bb.bottom))
        q = im.quantize(colors=200, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.FLOYDSTEINBERG)
        path = os.path.join(OUT, f"{name}_{i:02d}.png")
        q.save(path, "PNG", optimize=True)
        total += os.path.getsize(path)
        frames.append([bb.x, bb.y])
    index[art] = dict(n=N, size=[W, H], zoom=zoom, yaw0=YAW0, pitch=PITCH, offsets=frames)
    print(f"{name}: {N} кадров")
with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f)
print(f"всего {len(index)} колясок, {total / 1e6:.1f} МБ")
