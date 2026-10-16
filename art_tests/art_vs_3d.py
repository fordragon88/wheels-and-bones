"""Арт коляски (2D) рядом с её 3D-моделью: python art_tests/art_vs_3d.py out.png [model ...]"""
import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
import game
keys = sys.argv[2:] or [os.path.basename(k)[6:-4] for k in game.AI_MODELS]
CW, CH = 340, 270
sheet = pygame.Surface((CW * 3, CH * ((len(keys) + 1) // 2) + 0)); sheet.fill((30, 34, 44))
sheet = pygame.Surface((CW * 4, CH * ((len(keys) + 1) // 2))); sheet.fill((30, 34, 44))
f = pygame.font.SysFont("segoeui", 15, bold=True)
for i, k in enumerate(keys):
    x0, y0 = (i % 2) * CW * 2, (i // 2) * CH
    art = pygame.image.load(f"assets/chair_{k}.png").convert_alpha()
    w, h = art.get_size(); s = min((CW - 10) / w, (CH - 30) / h)
    sheet.blit(pygame.transform.smoothscale(art, (int(w * s), int(h * s))), (x0 + 5, y0 + 25))
    m = game.get_ai_chair3d(f"chair_{k}.png")
    if m:
        big = pygame.Surface((CW * 2, CH * 2)); big.fill((44, 50, 62))
        for yaw in (-0.75,):
            for d, pts, col, part, fl in game.project_mesh(m, yaw, 0.28, pygame.Rect(0, 0, CW, CH), 0.95, m.pivot, ss=2):
                pygame.draw.polygon(big, col, pts)
        sheet.blit(pygame.transform.smoothscale(big, (CW, CH)), (x0 + CW, y0))
    sheet.blit(f.render(k, True, (240, 220, 120)), (x0 + 6, y0 + 4))
pygame.image.save(sheet, sys.argv[1]); print("ok", len(keys))
