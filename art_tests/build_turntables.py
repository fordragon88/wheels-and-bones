"""Обороты колясок для браузерной версии (там нет numpy/OpenGL — 3D-модель не отрисовать на лету).
Каждая модель окна диагностики (облегчённая, как на десктопе) рендерится на GPU с N углов
и сохраняется PNG (200 цветов с прозрачностью). Кружки деталей игра считает сама (project_point —
чистый Python) по центрам деталей из index.json, поэтому они стоят на модели при любом повороте.
python art_tests/build_turntables.py [N]   → assets/turntable/<chair>_<i>.png + assets/turntable/index.json
Кадр i снят при yaw = YAW0 + i * 2π / N, pitch = M3D_PITCH; масштаб — как в окне диагностики (_m3d_zoom)
при высоте окна коляски REF_H пикселей экрана. В index.json единица смещений — «единица модели после
перспективы»: игра умножает её на свой масштаб (высота окна × z0 / 1250)."""
import os, sys, json, math, glob
os.environ.setdefault("SDL_VIDEODRIVER", "windows")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import pygame
pygame.init()
pygame.display.set_mode((64, 64), pygame.HIDDEN)
import game
import numpy as np
from PIL import Image

FOLK = "--folk" in sys.argv          # фольклорные клиенты: модели из art_tests/tripo/models -> art_tests/new_v2/assets
args = [a for a in sys.argv[1:] if not a.startswith("--")]
N = int(args[0]) if args else 36
if FOLK:
    OUT = os.path.join(ROOT, "art_tests", "new_v2", "assets", "turntable")
    for k in ("yaga", "rusalka", "leshy", "ra", "gorynych"):
        game.AI_MODELS = {} if k == "yaga" else game.AI_MODELS
        game.AI_MODELS[f"chair_{k}.png"] = os.path.relpath(
            os.path.join(ROOT, "art_tests", "tripo", "models", f"chair_{k}_ai.json"),
            os.path.join(game.ASSETS_DIR, "models"))
else:
    OUT = os.path.join(ROOT, "assets", "turntable")
os.makedirs(OUT, exist_ok=True)
for old in glob.glob(os.path.join(OUT, "*.png")):
    os.remove(old)
REF_H = 600                         # высота окна коляски в пикселях экрана (≈ 400 логических × RS 1.5)
PAD = 60                            # поля (M3D_PAD × 1.5): модель может выходить за окно (по высоте — на M3D_TALL)
YAW0, PITCH = game.Game.M3D_YAW, game.Game.M3D_PITCH
assert game.gl_ok(), "нужен OpenGL (moderngl) — запускать на компьютере с видеокартой"


def fit_zoom(mesh):
    """То же, что Game._m3d_zoom (game.m3d_fit_zoom): окно 380×300, исходный ракурс — целиком."""
    V = np.asarray(mesh.verts, dtype=np.float64)[::3] - np.asarray(mesh.pivot)
    z, dy = game.m3d_fit(V, 380.0, 300.0, YAW0, PITCH, game.Game.M3D_WIDE, game.Game.M3D_TALL)
    mesh.pivot = (mesh.pivot[0], mesh.pivot[1] + dy, mesh.pivot[2])   # высота центра — как в игре
    mesh._pivot_fit = True
    return z


index, total = {}, 0
for art in game.AI_MODELS:
    mesh = game.get_ai_chair3d(art, lod=True)
    if mesh is None:
        continue
    z0 = fit_zoom(mesh)
    PAD_X = PAD + math.ceil(REF_H * 380 / 300 / 2 * (game.Game.M3D_WIDE - 1))   # запас по ширине — как в игре
    W, H = round(REF_H * 380 / 300) + 2 * PAD_X, REF_H + 2 * PAD
    zoom = z0 * REF_H / H                                   # как _m3d_frame: масштаб = REF_H × z0 / 1250
    s_ref = REF_H * z0 / 1250.0                             # пикселей на единицу
    ax, ay = W / 2, H * 0.54                                # куда проецируется центр (pivot)
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
        frames.append([round((bb.x - ax) / s_ref, 2), round((bb.y - ay) / s_ref, 2)])
    index[art] = dict(n=N, yaw0=YAW0, pitch=PITCH, z0=round(z0, 5), ref=round(s_ref, 5), offsets=frames,
                      pivot=[round(float(c), 2) for c in mesh.pivot],
                      centers={p: [[round(float(v), 1) for v in c] for c in cs] for p, cs in mesh.centers.items()})
    print(f"{name}: {N} кадров")
with open(os.path.join(OUT, "index_folk.json" if FOLK else "index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, separators=(",", ":"))
print(f"всего {len(index)} колясок, {total / 1e6:.1f} МБ")
