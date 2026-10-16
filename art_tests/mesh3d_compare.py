"""Сравнение: кодовая модель коляски vs сгенерированная (Hunyuan3D), нашим рендером."""
import os, sys, json, math, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
import game

CULL = os.environ.get("CULL") == "1"

def load_gen(path):
    d = json.load(open(path))
    m = game.Mesh3D()
    m.verts = [tuple(v) for v in d["verts"]]
    for a, b, c, pi, r, g, bl in d["faces"]:
        m.face((a, b, c), d["parts"][pi], (r, g, bl), game.M_DOUBLE | (game.M_METAL if d["parts"][pi] in ("rim", "frame") else 0))
    xs = [v[0] for v in m.verts]; ys = [v[1] for v in m.verts]
    m.pivot = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0)
    return m

def render(mesh, yaw, pitch, size=(520, 520), ss=2):
    surf = pygame.Surface(size); surf.fill((30, 38, 50))
    rect = pygame.Rect(0, 0, *size)
    big = pygame.Surface((size[0] * ss, size[1] * ss), pygame.SRCALPHA)
    t = time.perf_counter()
    polys = game.project_mesh(mesh, yaw, pitch, rect, float(os.environ.get("ZOOM", "1.0")), getattr(mesh, "pivot", None), ss=ss)
    for depth, pts, col, part, fl in polys:
        pygame.draw.polygon(big, col, pts)
        if fl & game.M_EDGE:
            pygame.draw.polygon(big, game._shade(col, 0.45), pts, 2)
    surf.blit(pygame.transform.smoothscale(big, size), (0, 0))
    return surf, (time.perf_counter() - t) * 1000

coded = game.get_chair3d(os.environ.get("KIND", "manual"), (84, 168, 228) if os.environ.get("KIND", "manual") == "manual" else None)
gens = [(os.path.basename(p)[:-5], load_gen(p)) for p in sys.argv[1:]]
views = [(0.75, 0.28, "3/4"), (0.0, 0.08, "сбоку"), (math.pi * 0.5, 0.15, "спереди"), (2.6, 0.35, "сзади-сверху")]
rows = [("код (по чертежу)", coded)] + gens
T, pad, lab = 300, 8, 26
sheet = pygame.Surface((len(views) * (T + pad) + 190, len(rows) * (T + pad) + lab + pad)); sheet.fill((236, 232, 224))
f = pygame.font.SysFont("segoeui,arial", 18, bold=True)
for j, (_, _, vn) in enumerate(views):
    sheet.blit(f.render(vn, True, (40, 40, 48)), (190 + j * (T + pad), 4))
for i, (name, mesh) in enumerate(rows):
    y = lab + i * (T + pad)
    sheet.blit(f.render(name, True, (40, 40, 48)), (6, y + T // 2 - 20))
    sheet.blit(f.render(f"{len(mesh.faces)} граней", True, (90, 90, 100)), (6, y + T // 2 + 4))
    for j, (yaw, pitch, _) in enumerate(views):
        img, ms = render(mesh, yaw, pitch)
        sheet.blit(pygame.transform.smoothscale(img, (T, T)), (190 + j * (T + pad), y))
    print(name, f"{ms:.0f} мс/кадр")
pygame.image.save(sheet, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_mesh_compare.png"))
