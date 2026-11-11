# -*- coding: utf-8 -*-
"""Экран задания в первые секунды (портрет героя в левом верхнем углу и его «волшебство»), 1280×720, RU.

  python art_tests/magic_shots.py leshy_x8 joystick bearing      -> art_tests/magic_shots/<задание>_magic.png (полоса
                                                                     кадров) + _before/_during/_after.png (крупно угол)
  python art_tests/magic_shots.py --md5 flat spokes lift          -> только md5 кадров (сравнение кода «до/после»)
  --calm — с «Без анимации»; --rs 1.5 — рендер ×1,5 (как на экране 1920×1080); --click — ещё и клик по портрету
  после первого показа (повтор).

Часы подменены (как в ride_shots.py): pygame.time.get_ticks, time.time/perf_counter/monotonic и random.seed(1) —
одинаковый код даёт одинаковые байты кадров. Так проверяли, что герои без волшебства и «Без анимации» не изменились.
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
args = sys.argv[1:]
rs = float(args[args.index("--rs") + 1]) if "--rs" in args else 1.0
if "--rs" in args:
    del args[args.index("--rs"):args.index("--rs") + 2]
S = pygame.display.set_mode((round(1280 * rs), round(720 * rs)))
import game

game.RS = rs
F = game.Surf((1280, 720)) if rs != 1 else S
md5 = "--md5" in args
calm = "--calm" in args
click = "--click" in args
jobs = [a for a in args if not a.startswith("--")] or ["leshy_x8", "joystick", "bearing"]
TIMES = [0.3, 0.9, 1.3, 1.7, 2.1, 2.5, 2.9, 3.3, 3.7, 4.1, 4.5, 4.9, 5.4, 6.5]
out = os.path.join(ROOT, "art_tests", "magic_shots")
os.makedirs(out, exist_ok=True)


def frame():
    g.draw(F)
    return pygame.Surface.copy(F)


for jid in jobs:
    random.seed(1)
    _clock[0] = 0.0
    g = game.Game(headless=True)
    g.no_save = True
    game.set_lang("ru")
    game.A11Y["calm"] = calm
    j = g.job_by_id(jid)
    g.start_job(jid, variant=0 if "variants" in j else None)
    times = list(TIMES)
    if click:
        times += [7.0, 7.4, 8.0, 9.0, 11.5]
    frames, hashes, t0 = [], [], g.t
    clicked = False
    for T in times:
        while g.t < t0 + T - 1e-6:
            _clock[0] += 1 / 60
            g.update(1 / 60)
            if click and not clicked and g.t >= t0 + 6.9:
                clicked = True
                r = g.portrait_rect() if hasattr(g, "portrait_rect") else pygame.Rect(24, 70, 150, 190)
                g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r.center))
                g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=r.center))
        im = frame()
        hashes.append(hashlib.md5(pygame.image.tobytes(im, "RGB")).hexdigest()[:10])
        frames.append(im)
    tag = ("_calm" if calm else "") + (f"_rs{rs:g}" if rs != 1 else "")
    print(jid + tag, " ".join(hashes), "magic:", getattr(g, "_magic_drawn", None))
    if not md5:
        W, H = pygame.Surface.get_size(frames[0])
        k = 0.25 * 1280 / W
        w, h = int(W * k), int(H * k)
        cols = 4
        rows = (len(frames) + cols - 1) // cols
        sheet = pygame.Surface((w * cols, h * rows))
        for i, im in enumerate(frames):
            sheet.blit(pygame.transform.smoothscale(im, (w, h)), ((i % cols) * w, (i // cols) * h))
        pygame.image.save(sheet, os.path.join(out, f"{jid}{tag}_magic.png"))
        corner = pygame.Rect(0, 0, round(520 * W / 1280), round(330 * H / 720))
        for nm, i in (("before", 0), ("during1", 3), ("during2", 6), ("during3", 9), ("after", len(TIMES) - 1)):
            pygame.image.save(frames[i].subsurface(corner), os.path.join(out, f"{jid}{tag}_{nm}.png"))
