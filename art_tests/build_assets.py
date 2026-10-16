"""Сборка ассетов игры из art_tests/final_v1 + расчёт хотспотов колясок по чертежу.

Коляски нормализуются: контур каждой PNG вписывается в габарит чертежа в рамке
380x300 (как рисует игра), поэтому одна таблица хотспотов на тип коляски.
Печатает константы для game.py и кладёт отладочные картинки с хотспотами."""
import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
HERE = os.path.dirname(os.path.abspath(__file__))
FIN = os.path.join(HERE, "final_v1")
REF = sys.argv[1]                       # папка с skel_flat.png / power_skel_flat.png
OUT = os.path.join(HERE, "..", "assets")
DBG = os.path.join(HERE, "hotspots_check")
os.makedirs(DBG, exist_ok=True)
FW, FH, UP = 380, 300, 2                # рамка схемы и супер-разрешение PNG

# чертежи: px = OX + x*K, py = OY - y*K (мм -> пиксели 1024)
SKEL = {"manual": ("skel_flat.png", 330, 930, 0.78), "power": ("power_skel_flat.png", 470, 930, 0.78)}
# хотспоты в мм чертежа: деталь -> (x, y, радиус в px рамки)
HOT_MM = {
    "manual": {
        "tire": (-216, 89, 18), "rim": (-260, 410, 13), "spokes": (-51, 164, 15),
        "axle": (0, 305, 12), "bearing": (70, 285, 12), "rear_wheel": (150, 140, 20),
        "tube": (-113, 38, 12), "valve": (0, 22, 12), "caster": (430, 95, 20),
        "caster_stem": (462, 200, 12), "brake": (268, 548, 15), "seat": (360, 492, 11),
        "cushion": (120, 532, 11), "footrest": (620, 150, 15), "frame": (424, 410, 13),
        "bolts": (20, 600, 11),
    },
    "power": {
        "controller": (240, 670, 13), "joystick": (270, 800, 13), "boot": (270, 712, 9),
        "battery": (205, 205, 14), "fuse": (-200, 230, 9), "wiring": (255, 520, 13),
        "motor": (-110, 175, 14), "freewheel": (-185, 300, 11), "frame": (-340, 215, 14),
        "axle": (0, 175, 12),
    },
}

def bbox_nonwhite(img):
    m = pygame.mask.from_threshold(img, (255, 255, 255, 255), (24, 24, 24, 255))
    m.invert(); return m.get_bounding_rects()[0].unionall(m.get_bounding_rects())

def bbox_alpha(img):
    m = pygame.mask.from_surface(img, 100)
    rs = m.get_bounding_rects(); r = rs[0].unionall(rs); return r

consts = {}
for kind, (fn, OX, OY, K) in SKEL.items():
    sk = pygame.image.load(os.path.join(REF, fn)).convert()
    bb = bbox_nonwhite(sk)
    s = min((FW - 12) / bb.w, (FH - 12) / bb.h)
    fx0 = (FW - bb.w * s) / 2; fy0 = (FH - bb.h * s) / 2
    AX = fx0 + (OX - bb.x) * s; AY = fy0 + (OY - bb.y) * s; S = K * s
    hot = {p: (round(AX + x * S), round(AY - y * S), r) for p, (x, y, r) in HOT_MM[kind].items()}
    consts[kind] = dict(AX=round(AX, 2), AY=round(AY, 2), S=round(S, 5), box=(round(fx0, 1), round(fy0, 1), round(bb.w * s, 1), round(bb.h * s, 1)), hot=hot)

REAL = {"chair_basic": "inv9000", "chair_troll": "xdt", "chair_elf": "ego", "chair_dwarf": "tekna", "chair_fairy": "exelle_jr",
        "chair_orc": "noir", "chair_edge4": "edge4", "chair_trident": "trident", "chair_m3": "m3"}   # арт -> модель
HOT_FILES = {m: os.path.join(HERE, f"hotspots_{m}.json") for m in REAL.values()}   # точки клика по арту


def norm_chair(name, kind):
    img = pygame.image.load(os.path.join(FIN, name + ".png")).convert_alpha()
    r = bbox_alpha(img)
    if kind not in consts:                       # коляска по арту (не по чертежу): вписать по контуру
        k = min((FW - 12) / r.w, (FH - 12) / r.h)
        hot = {}
        if os.path.exists(HOT_FILES.get(kind, "")):
            hot = {p: tuple(v) for p, v in json.load(open(HOT_FILES[kind], encoding="utf-8")).items()}
        consts[kind] = dict(box=((FW - r.w * k) / 2, (FH - r.h * k) / 2, r.w * k, r.h * k), hot=hot)
    x0, y0, w, h = consts[kind]["box"]
    crop = img.subsurface(r)
    out = pygame.Surface((FW * UP, FH * UP), pygame.SRCALPHA)
    out.blit(pygame.transform.smoothscale(crop, (round(w * UP), round(h * UP))), (round(x0 * UP), round(y0 * UP)))
    pygame.image.save(out, os.path.join(OUT, name + ".png"))
    dbg = pygame.Surface((FW * UP, FH * UP)); dbg.fill((40, 36, 44)); dbg.blit(out, (0, 0))
    f = pygame.font.SysFont("arial", 18, bold=True)
    for p, (hx, hy, hr) in consts[kind]["hot"].items():
        pygame.draw.circle(dbg, (255, 190, 60), (hx * UP, hy * UP), hr * UP, 3)
        dbg.blit(f.render(p, True, (255, 255, 255)), (hx * UP + hr * UP + 2, hy * UP - 10))
    pygame.image.save(dbg, os.path.join(DBG, name + ".png"))

def copy_fit(name, src=None, max_h=None):
    img = pygame.image.load(os.path.join(FIN, (src or name) + ".png")).convert_alpha()
    if img.get_bitsize() == 32 and max_h:
        img = img.subsurface(bbox_alpha(img))
        if img.get_height() > max_h:
            k = max_h / img.get_height()
            img = pygame.transform.smoothscale(img, (round(img.get_width() * k), max_h))
    pygame.image.save(img, os.path.join(OUT, name + ".png"))

if __name__ == "__main__":
    for c, model in REAL.items():                # реальные коляски: вписываются по контуру арта
        norm_chair(c, model)
    norm_chair("chair_power", "power")
    for b in ("bg_workshop", "bg_road", "bg_garage", "bg_party", "bg_guild"):
        img = pygame.image.load(os.path.join(FIN, b + ".png")).convert()
        pygame.image.save(pygame.transform.smoothscale(img, (1280, 720)), os.path.join(OUT, b + ".png"))
    pygame.image.save(pygame.image.load(os.path.join(OUT, "bg_workshop.png")), os.path.join(OUT, "bg_title.png"))
    for c in ("martin", "ghost", "master", "client_elf", "client_dwarf", "client_fairy", "client_orc",
              "client_troll", "client_goblin", "client_sorceress", "client_golem", "client_centaur", "gag_leg"):
        copy_fit(c, max_h=640)
    # иконки инструментов: обрезка по контуру, квадрат с полями, 128x128
    TD = os.path.join(FIN, "tools")
    for fn in sorted(os.listdir(TD)) if os.path.isdir(TD) else []:
        img = pygame.image.load(os.path.join(TD, fn)).convert_alpha()
        img = img.subsurface(bbox_alpha(img))
        side = int(max(img.get_size()) * 1.12)
        sq = pygame.Surface((side, side), pygame.SRCALPHA)
        sq.blit(img, img.get_rect(center=(side // 2, side // 2)))
        pygame.image.save(pygame.transform.smoothscale(sq, (128, 128)), os.path.join(OUT, fn))
    print(json.dumps({k: {kk: vv for kk, vv in v.items()} for k, v in consts.items()}, ensure_ascii=False))
