# -*- coding: utf-8 -*-
"""Кадры тест-драйва (проезд после ремонта) в игре, 1280×720, RU.

  python art_tests/ride_shots.py flat brake ...        -> art_tests/ride_shots/<задание>_ride.png (полоса 8 кадров)
  python art_tests/ride_shots.py --md5 spokes lift ...  -> только md5 кадров (сравнение кода «до/после»)

Часы подменены (pygame.time.get_ticks, time.time/perf_counter/monotonic) и random.seed(1): одинаковый код даёт
одинаковые байты кадров — так проверяли, что проезд героев без петли не изменился (ветка feature/ride-anim).
"""
import hashlib, os, random, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import pygame

_clock = [0.0]
pygame.time.get_ticks = lambda: int(_clock[0] * 1000)
time.time = lambda: 1.7e9 + _clock[0]
time.perf_counter = lambda: _clock[0]
time.monotonic = lambda: _clock[0]
random.seed(1)
pygame.init()
S = pygame.display.set_mode((1280, 720))
import game

md5 = "--md5" in sys.argv
jobs = [a for a in sys.argv[1:] if not a.startswith("--")] or ["flat", "brake", "joystick", "caster"]
N = 8
out = os.path.join(ROOT, "art_tests", "ride_shots")
os.makedirs(out, exist_ok=True)
for jid in jobs:
    random.seed(1)
    _clock[0] = 0.0
    g = game.Game(headless=True)
    g.no_save = True
    game.set_lang("ru")
    j = g.job_by_id(jid)
    g.start_job(jid, variant=0 if "variants" in j else None)
    g.phase = "test"
    for _ in range(10):
        _clock[0] += 1 / 30
        g.update(1 / 30)
    g.start_ride()
    secs = g.ride_secs() if hasattr(g, "ride_secs") else g.RIDE_SECS
    frames, hashes = [], []
    step = secs / (N + 1)
    t_end = g.t + secs
    for i in range(1, N + 1):
        while g.t < g.ride_t0 + step * i - 1e-6 and g.ride_t0 is not None:
            _clock[0] += 1 / 60
            g.update(1 / 60)
        g.draw(S)
        hashes.append(hashlib.md5(pygame.image.tobytes(S, "RGB")).hexdigest()[:10])
        frames.append(S.copy())
    print(jid, f"{secs:.2f} с", " ".join(hashes))
    if not md5:
        k = 0.5
        w, h = int(1280 * k), int(720 * k)
        sheet = pygame.Surface((w * 2, h * (N // 2)))
        for i, im in enumerate(frames):
            sheet.blit(pygame.transform.smoothscale(im, (w, h)), ((i % 2) * w, (i // 2) * h))
        pygame.image.save(sheet, os.path.join(out, f"{jid}_ride.png"))
        pygame.image.save(frames[N // 2 - 1], os.path.join(out, f"{jid}_ride_full.png"))
