"""Ассеты новых персонажей (Баба Яга, Ольга, Леший, Ра, Горыныч): art_tests/new_v2/cut/*.png -> art_tests/new_v2/assets/
(коляски — в рамку 380x300 ×2, как build_new_assets.py; клиенты — по контуру, высота до 640 px).
--install кладёт в assets/ картинки, 3D-модели и хотспоты (задания включатся сами); --uninstall убирает.
В публичную версию — только когда 3D-модели взяты из официальных файлов Tripo."""
import os, sys, shutil
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
HERE = os.path.dirname(os.path.abspath(__file__))
CUT = os.path.join(HERE, "new_v2", "cut")
OUT = os.path.join(HERE, "new_v2", "assets")
os.makedirs(OUT, exist_ok=True)
FW, FH, UP = 380, 300, 2
KEYS = ["yaga", "rusalka", "leshy", "ra", "gorynych"]


def bbox_alpha(img):
    rs = pygame.mask.from_surface(img, 100).get_bounding_rects()
    return rs[0].unionall(rs)


for k in KEYS:
    img = pygame.image.load(os.path.join(CUT, f"chair_{k}.png")).convert_alpha()
    r = bbox_alpha(img)
    s = min((FW - 12) / r.w, (FH - 12) / r.h)
    w, h = r.w * s, r.h * s
    out = pygame.Surface((FW * UP, FH * UP), pygame.SRCALPHA)
    out.blit(pygame.transform.smoothscale(img.subsurface(r), (round(w * UP), round(h * UP))),
             (round((FW - w) / 2 * UP), round((FH - h) / 2 * UP)))
    pygame.image.save(out, os.path.join(OUT, f"chair_{k}.png"))
    img = pygame.image.load(os.path.join(CUT, f"client_{k}.png")).convert_alpha()
    img = img.subsurface(bbox_alpha(img))
    if img.get_height() > 640:
        q = 640 / img.get_height()
        img = pygame.transform.smoothscale(img, (round(img.get_width() * q), 640))
    pygame.image.save(img, os.path.join(OUT, f"client_{k}.png"))
    print(k, "ok")
A = os.path.join(HERE, "..", "assets")
FILES = [f"{p}_{k}.png" for k in KEYS for p in ("chair", "client")]
MODELS = [f"chair_{k}_ai{s}.json" for k in KEYS for s in ("", "_lod")]
if "--install" in sys.argv:              # картинки, 3D-модели (art_tests/tripo/models) и 2D-хотспоты — в игру
    for f in FILES:
        shutil.copy(os.path.join(OUT, f), os.path.join(A, f))
    for f in MODELS:
        shutil.copy(os.path.join(HERE, "tripo", "models", f), os.path.join(A, "models", f))
    shutil.copy(os.path.join(OUT, "models", "folk_hotspots.json"), os.path.join(A, "models", "folk_hotspots.json"))
    print("установлено в assets/")
if "--uninstall" in sys.argv:            # убрать из игры (перед коммитом/выкладкой, пока нет официальных GLB Tripo)
    for f in FILES:
        if os.path.exists(os.path.join(A, f)):
            os.remove(os.path.join(A, f))
    for f in MODELS + ["folk_hotspots.json"]:
        if os.path.exists(os.path.join(A, "models", f)):
            os.remove(os.path.join(A, "models", f))
    print("убрано из assets/")
