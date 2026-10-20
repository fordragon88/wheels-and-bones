"""Ассеты новых персонажей (Баба Яга, Ольга, Леший, Ра, Горыныч): art_tests/new_v2/cut/*.png -> art_tests/new_v2/assets/
(коляски — в рамку 380x300 ×2, как build_new_assets.py; клиенты — по контуру, высота до 640 px).
С ключом --install копирует в assets/ (только когда 3D-модели взяты из официальных файлов Tripo)."""
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
if "--install" in sys.argv:
    for f in os.listdir(OUT):
        shutil.copy(os.path.join(OUT, f), os.path.join(HERE, "..", "assets", f))
    print("скопировано в assets/")
