"""Экраны диагностики всех заданий со встроенным 3D: python art_tests/diag3d_sheet.py [out.png]"""
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init()
S = pygame.display.set_mode((1280, 720))
import game
out = sys.argv[1] if len(sys.argv) > 1 else "art_tests/_diag3d.png"
g = game.Game(headless=True)
shots = []
for base in game.JOBS:
    g.start_job(base["id"])
    for _ in range(45):
        g.update(1 / 30)
    t = time.perf_counter(); g.draw(S); ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter(); g.draw(S); ms2 = (time.perf_counter() - t) * 1000
    print(f"{base['id']}: кадр {ms:.0f} мс (первый), {ms2:.0f} мс (из кэша)")
    shots.append(S.subsurface((340, 56, 640, 300)).copy())
sheet = pygame.Surface((640 * 3, 300 * 3))
for i, im in enumerate(shots):
    sheet.blit(im, ((i % 3) * 640, (i // 3) * 300))
pygame.image.save(sheet, out); print(out)
