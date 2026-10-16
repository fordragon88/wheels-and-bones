"""Экраны задания (диагноз/ремонт) для проверки раскладки: python art_tests/layout_shots.py jid [jid...]"""
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init(); S = pygame.display.set_mode((1280, 720))
import game
g = game.Game(headless=True)
shots = []
for jid in sys.argv[1:] or ["flat", "joystick"]:
    g.start_job(jid, variant=0 if "variants" in g.job_by_id(jid) else None)
    for _ in range(45): g.update(1 / 30)
    t = time.perf_counter(); g.draw(S); ms = (time.perf_counter() - t) * 1000
    shots.append(S.copy())
    for pid in g.cur["parts"][:2]: g.inspect_part(pid)
    ok = next(i for i, d in enumerate(g.cur["diagnosis"]) if d["correct"]); g.choose_diagnosis(ok)
    g.ghost_line = g.ghost_line or "Барти: «Проверка длинной подсказки призрака в узкой колонке справа.»"
    for _ in range(60): g.update(1 / 30)
    g.draw(S); shots.append(S.copy())
    print(f"{jid}: первый кадр диагноза {ms:.0f} мс")
sheet = pygame.Surface((1280 * 2, 720 * (len(shots) // 2)))
for i, im in enumerate(shots): sheet.blit(im, ((i % 2) * 1280, (i // 2) * 720))
pygame.image.save(pygame.transform.smoothscale(sheet, (sheet.get_width() // 2, sheet.get_height() // 2)), "art_tests/_layout.png")
