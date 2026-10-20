"""2D-хотспоты (рамка 380x300) для колясок новых персонажей — из 3D-модели, без ручной разметки.
Картинка коляски нарисована по рендеру нашей 3D-модели (yaw -0.75, pitch 0.22, zoom 0.95, 1100 px; затем обрезка
по контуру): точку детали проецируем тем же ракурсом, переводим в доли рамки контура рендера и кладём в рамку
контура готовой картинки (art_tests/new_v2/assets/chair_<k>.png). Пишет art_tests/new_v2/assets/models/folk_hotspots.json.
python art_tests/folk_hotspots.py [--check]   (--check: картинки с кружками в art_tests/new_v2/hotspots_check/)"""
import os, sys, json, math
os.environ.setdefault("SDL_VIDEODRIVER", "windows")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import pygame
pygame.init()
pygame.display.set_mode((64, 64), pygame.HIDDEN)
import game as g

OUT = os.path.join(ROOT, "art_tests", "new_v2", "assets")
MODELS = os.path.join(ROOT, "art_tests", "tripo", "models")
YAW, PITCH, SIZE, ZOOM = -0.75, 0.22, 1100, 0.95
FW, FH, UP = 380, 300, 2
CHAIRS = {"yaga": "d100", "rusalka": "x3", "leshy": "x8", "ra": "nitrum_em", "gorynych": "jazzy614"}
# ручные поправки (рамка 380x300), где проекция попала мимо детали на рисунке
OVERRIDE = {
    "leshy": {"tire": (173, 277), "rim": (193, 253), "motor": (127, 233), "axle": (77, 220), "freewheel": (83, 177), "joystick": (125, 131)},
    "gorynych": {"breaker": (220, 180), "tire": (147, 255), "battery": (180, 196), "joystick": (161, 119),
                 "controller": (182, 139)},
}
NEED = {j["chair_art"][6:-4]: j["parts"] for j in g.FOLK_JOBS}


def alpha_bbox(surf):
    rs = pygame.mask.from_surface(surf, 100).get_bounding_rects()
    return rs[0].unionall(rs)


res = {}
os.makedirs(os.path.join(OUT, "models"), exist_ok=True)
for key, model in CHAIRS.items():
    g.AI_MODELS[f"chair_{key}.png"] = os.path.relpath(os.path.join(MODELS, f"chair_{key}_ai.json"),
                                                       os.path.join(g.ASSETS_DIR, "models"))
    mesh = g.get_ai_chair3d(f"chair_{key}.png")
    img, pick = g.gl_render(mesh, YAW, PITCH, (SIZE, SIZE), ZOOM)
    rb = pick.bbox                                          # контур рендера
    art = pygame.image.load(os.path.join(OUT, f"chair_{key}.png")).convert_alpha()
    ab = alpha_bbox(art)                                    # контур нарисованной коляски (×UP)
    rect = pygame.Rect(0, 0, SIZE, SIZE)
    spots = {}
    for part in NEED[key]:
        cs = mesh.centers.get(part)
        if not cs:
            print(f"  {key}: нет детали {part} на модели!")
            continue
        near = max(cs, key=lambda c: g.project_point(c, YAW, PITCH, rect, ZOOM, mesh.pivot)[1])
        (x, y), _ = g.project_point(near, YAW, PITCH, rect, ZOOM, mesh.pivot)
        u, v = (x - rb.x) / rb.w, (y - rb.y) / rb.h
        fx = (ab.x + u * ab.w) / UP
        fy = (ab.y + v * ab.h) / UP
        spots[part] = [round(fx), round(fy), 11]
    # разнести близкие кружки (не перекрываться — правило selftest)
    keys = list(spots)
    for _ in range(80):
        moved = False
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = spots[keys[i]], spots[keys[j]]
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = math.hypot(dx, dy) or 1
                need = max(a[2], b[2]) + 4
                if d < need:
                    push = (need - d) / 2 + 0.5
                    a[0] -= dx / d * push; a[1] -= dy / d * push
                    b[0] += dx / d * push; b[1] += dy / d * push
                    moved = True
        if not moved:
            break
    res[model] = {p: [int(round(v[0])), int(round(v[1])), v[2]] for p, v in spots.items()}
    res[model].update({p: list(v) + [11] for p, v in OVERRIDE.get(key, {}).items()})
    print(key, model, res[model])
    if "--check" in sys.argv:
        dbg = pygame.Surface(art.get_size()); dbg.fill((40, 36, 44)); dbg.blit(art, (0, 0))
        f = pygame.font.SysFont("arial", 15, bold=True)
        for p, (hx, hy, hr) in res[model].items():
            pygame.draw.circle(dbg, (255, 190, 60), (hx * UP, hy * UP), hr * UP, 3)
            dbg.blit(f.render(p, True, (255, 255, 255)), (hx * UP + hr * UP + 2, hy * UP - 8))
        os.makedirs(os.path.join(ROOT, "art_tests", "new_v2", "hotspots_check"), exist_ok=True)
        pygame.image.save(dbg, os.path.join(ROOT, "art_tests", "new_v2", "hotspots_check", f"{key}.png"))
json.dump(res, open(os.path.join(OUT, "models", "folk_hotspots.json"), "w", encoding="utf-8"), ensure_ascii=False)
