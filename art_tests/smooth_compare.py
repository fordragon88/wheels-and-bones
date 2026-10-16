"""Сравнение моделей нашим рендером: python art_tests/smooth_compare.py out.png a.json b.json ... (крупно + мелко)"""
import os, sys, json, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
import game

def load(p):
    d = json.load(open(p)); m = game.Mesh3D(); m.verts = [tuple(v) for v in d["verts"]]
    for a, b, c, pi, r, g, bl in d["faces"]:
        part = d["parts"][pi]
        m.face((a, b, c), part if part in game.PARTS else None, (r, g, bl),
               (0 if d.get("cull") else game.M_DOUBLE) | (game.M_METAL if part in ("rim", "spokes", "axle") else 0))
    game._finish_mesh(m); return m, len(d["faces"])

out, files = sys.argv[1], sys.argv[2:]
BW, BH, SW, SH = 560, 460, 260, 210
sheet = pygame.Surface((len(files) * BW, BH + SH + 30)); sheet.fill((20, 26, 36))
f = pygame.font.SysFont("segoeui", 16, bold=True)
for n, p in enumerate(files):
    m, nf = load(p)
    for k, (w, h, ss, y0) in enumerate(((BW, BH, 2, 0), (SW, SH, 2, BH + 30))):
        big = pygame.Surface((w * ss, h * ss)); big.fill((30, 38, 50))
        t = time.perf_counter()
        polys = game.project_mesh(m, -0.75, 0.3, pygame.Rect(0, 0, w, h), 0.9, m.pivot, ss=ss)
        for depth, pts, col, part, fl in polys:
            pygame.draw.polygon(big, col, pts)
        ms = (time.perf_counter() - t) * 1000
        sheet.blit(pygame.transform.smoothscale(big, (w, h)), (n * BW, y0))
        sheet.blit(f.render(f"{os.path.basename(p)}  {nf} гр.  {ms:.0f} мс", True, (235, 225, 190)), (n * BW + 6, y0 + 4 if k == 0 else BH + 6))
pygame.image.save(sheet, out); print(out)
