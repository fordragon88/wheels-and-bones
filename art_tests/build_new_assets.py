"""Ассеты второй волны: art_tests/new_v1/cut/*.png -> assets/ (коляски вписаны в рамку 380x300 как в build_assets,
клиенты/наставник — по контуру, max 640 px). Хотспоты по арту: art_tests/hotspots_<model>.json (координаты рамки 380x300).
python art_tests/build_new_assets.py [--grid]  (--grid: отладочные картинки с сеткой и хотспотами в hotspots_check/)"""
import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
HERE = os.path.dirname(os.path.abspath(__file__))
CUT = os.path.join(HERE, "new_v1", "cut")
OUT = os.path.join(HERE, "..", "assets")
DBG = os.path.join(HERE, "hotspots_check")
os.makedirs(DBG, exist_ok=True)
FW, FH, UP = 380, 300, 2
CHAIRS = ["aeroz", "cross6", "iris", "focuscr", "whillc2", "f5", "pulse6", "q6edge"]
PEOPLE = ["client_aeroz", "client_cross6", "client_iris", "client_focuscr", "client_whillc2", "client_f5", "necro"]


def bbox_alpha(img):
    rs = pygame.mask.from_surface(img, 100).get_bounding_rects()
    return rs[0].unionall(rs)


def chair(k, grid):
    img = pygame.image.load(os.path.join(CUT, f"chair_{k}.png")).convert_alpha()
    r = bbox_alpha(img)
    s = min((FW - 12) / r.w, (FH - 12) / r.h)
    w, h = r.w * s, r.h * s
    x0, y0 = (FW - w) / 2, (FH - h) / 2
    out = pygame.Surface((FW * UP, FH * UP), pygame.SRCALPHA)
    out.blit(pygame.transform.smoothscale(img.subsurface(r), (round(w * UP), round(h * UP))), (round(x0 * UP), round(y0 * UP)))
    pygame.image.save(out, os.path.join(OUT, f"chair_{k}.png"))
    if grid:
        dbg = pygame.Surface((FW * UP, FH * UP)); dbg.fill((40, 36, 44)); dbg.blit(out, (0, 0))
        f = pygame.font.SysFont("arial", 14, bold=True)
        for gx in range(0, FW, 20):
            pygame.draw.line(dbg, (90, 90, 120) if gx % 100 else (160, 160, 220), (gx * UP, 0), (gx * UP, FH * UP), 1)
            if gx % 40 == 0: dbg.blit(f.render(str(gx), True, (200, 200, 255)), (gx * UP + 2, 2))
        for gy in range(0, FH, 20):
            pygame.draw.line(dbg, (90, 90, 120) if gy % 100 else (160, 160, 220), (0, gy * UP), (FW * UP, gy * UP), 1)
            if gy % 40 == 0: dbg.blit(f.render(str(gy), True, (200, 200, 255)), (2, gy * UP + 2))
        hp = os.path.join(HERE, f"hotspots_{k}.json")
        if os.path.exists(hp):
            for p, (hx, hy, hr) in json.load(open(hp, encoding="utf-8")).items():
                pygame.draw.circle(dbg, (255, 190, 60), (hx * UP, hy * UP), hr * UP, 3)
                dbg.blit(f.render(p, True, (255, 255, 255)), (hx * UP + hr * UP + 2, hy * UP - 8))
        pygame.image.save(dbg, os.path.join(DBG, f"chair_{k}.png"))


def person(name):
    img = pygame.image.load(os.path.join(CUT, name + ".png")).convert_alpha()
    img = img.subsurface(bbox_alpha(img))
    if img.get_height() > 640:
        k = 640 / img.get_height()
        img = pygame.transform.smoothscale(img, (round(img.get_width() * k), 640))
    pygame.image.save(img, os.path.join(OUT, ("mentor_necro" if name == "necro" else name) + ".png"))
    if name == "necro":                                  # портрет по плечи для реплик в кабинете
        w, h = img.get_size()
        r = pygame.Rect(int(w * 0.30), 0, int(w * 0.62), int(h * 0.36))
        pygame.image.save(img.subsurface(r.clip(img.get_rect())), os.path.join(OUT, "mentor_necro_head.png"))


if __name__ == "__main__":
    grid = "--grid" in sys.argv
    for k in CHAIRS:
        chair(k, grid)
    for n in PEOPLE:
        person(n)
    print("ok")
