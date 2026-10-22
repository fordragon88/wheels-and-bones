"""Модели колясок + камера игры -> tools/render_in/<коляска>.json для рендера кадров поворота в Blender.
Камера и масштаб — те же, что у build_turntables.py (окно 380×300, fit_zoom, REF_H, PAD), поэтому кружки деталей
(центры деталей и смещения кадров) совпадают с кадрами.
python art_tests/blender_export.py [chair_f5.png,chair_basic.png,…]   (без списка — все коляски с кадрами)"""
import os, sys, math, json
os.environ.setdefault("SDL_VIDEODRIVER", "windows")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
import pygame
pygame.init()
pygame.display.set_mode((64, 64), pygame.HIDDEN)
import numpy as np
import game

OUT = os.path.join(ROOT, "tools", "render_in")
os.makedirs(OUT, exist_ok=True)
N = 36
REF_H, PAD = 600, 60                                     # как в build_turntables.py
YAW0, PITCH = game.Game.M3D_YAW, game.Game.M3D_PITCH
only = sys.argv[1].split(",") if len(sys.argv) > 1 else None


def fit_zoom(mesh):
    V = np.asarray(mesh.verts, dtype=np.float64)[::3] - np.asarray(mesh.pivot)
    z, dy = game.m3d_fit(V, 380.0, 300.0, YAW0, PITCH, game.Game.M3D_WIDE, game.Game.M3D_TALL)
    mesh.pivot = (mesh.pivot[0], mesh.pivot[1] + dy, mesh.pivot[2])
    mesh._pivot_fit = True
    return z


for k in ("yaga", "rusalka", "leshy", "ra", "gorynych"):          # фольклорные: модели вне игры (только кадры)
    fp = os.path.join(HERE, "tripo", "models", f"chair_{k}_ai.json")
    if os.path.exists(fp):
        game.AI_MODELS.setdefault(f"chair_{k}.png", os.path.relpath(fp, os.path.join(game.ASSETS_DIR, "models")))
for art in game.AI_MODELS:
    if only and art not in only:
        continue
    lod = game.get_ai_chair3d(art, lod=True)            # центр и масштаб — по облегчённой (как в игре)
    full = game.get_ai_chair3d(art)                     # рисуем полную
    if lod is None or full is None:
        continue
    z0 = fit_zoom(lod)
    PAD_X = PAD + math.ceil(REF_H * 380 / 300 / 2 * (game.Game.M3D_WIDE - 1))
    W, H = round(REF_H * 380 / 300) + 2 * PAD_X, REF_H + 2 * PAD
    s_ref = REF_H * z0 / 1250.0                         # пикселей на мм у центра
    faces = []
    for idx, part, col, fl in full.faces:
        faces.append([list(idx), part or "", list(col), 1 if fl & game.M_METAL else 0])
    name = os.path.splitext(art)[0]
    json.dump(dict(art=art, W=W, H=H, s=s_ref, pivot=list(lod.pivot), pitch=PITCH,
                   yaws=[YAW0 + i * 2 * math.pi / N for i in range(N)], z0=z0,
                   verts=[list(v) for v in full.verts], faces=faces,
                   centers={p: [list(c) for c in cs] for p, cs in lod.centers.items()}),
              open(os.path.join(OUT, name + ".json"), "w"), separators=(",", ":"))
    print(name, W, H, round(s_ref, 4), len(faces), "граней")
