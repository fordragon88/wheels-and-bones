"""«Обезьяний тест»: тысячи случайных действий по всем экранам, ловим падения.
python art_tests/monkey_test.py [шагов] [сидов]"""
import os, sys, random, traceback, collections
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))
import game

STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 6
MOUSE = [640, 360]
pygame.mouse.get_pos = lambda: tuple(MOUSE)


def targets(g):
    """Все кликабельные прямоугольники/точки, которые сейчас может вернуть игра."""
    out = []
    for name in dir(g):
        if not name.startswith("_") or not (name.endswith("_rect") or name.endswith("_rects")):
            continue
        try:
            r = getattr(g, name)()
        except TypeError:
            continue
        except Exception:
            continue
        items = r if isinstance(r, list) else [r]
        for it in items:
            rect = it[-1] if isinstance(it, tuple) else it
            if isinstance(rect, pygame.Rect):
                out.append(rect.center)
    try:
        for pid, x, y, rr in g._chair_hotspots():
            out.append((x, y))
    except Exception:
        pass
    return out


def ev(g, t, **kw):
    g.handle_event(pygame.event.Event(t, **kw))


crashes = collections.OrderedDict()
scene_hits = collections.Counter()
for seed in range(SEEDS):
    rnd = random.Random(seed)
    random.seed(seed)
    g = game.Game(headless=True)
    for step in range(STEPS):
        try:
            scene_hits[g.scene] += 1
            r = rnd.random()
            if r < 0.55:
                tg = targets(g)
                pos = rnd.choice(tg) if tg and rnd.random() < 0.85 else (rnd.randrange(1280), rnd.randrange(720))
                MOUSE[:] = pos
                ev(g, pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))
                ev(g, pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
                if rnd.random() < 0.3:                       # перетаскивание
                    p2 = (pos[0] + rnd.randint(-200, 200), pos[1] + rnd.randint(-120, 120))
                    MOUSE[:] = p2
                    ev(g, pygame.MOUSEMOTION, pos=p2, rel=(1, 1), buttons=(1, 0, 0))
                    pos = p2
                ev(g, pygame.MOUSEBUTTONUP, button=1, pos=pos)
            elif r < 0.62:
                ev(g, pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0)
            elif r < 0.64:
                ev(g, pygame.KEYDOWN, key=pygame.K_m, mod=0, unicode="m", scancode=0)
            elif r < 0.70:
                ev(g, pygame.MOUSEWHEEL, x=0, y=rnd.choice((-1, 1)), flipped=False, precise_x=0.0, precise_y=0.0)
            elif r < 0.75:
                ev(g, pygame.KEYDOWN, key=rnd.choice((pygame.K_RETURN, pygame.K_SPACE, pygame.K_1, pygame.K_LEFT)),
                   mod=0, unicode="", scancode=0)
            else:
                MOUSE[:] = (rnd.randrange(1280), rnd.randrange(720))
            for _ in range(rnd.choice((1, 1, 2, 8))):
                g.update(1 / 30)
                g.draw(screen)
        except Exception as e:
            tb = traceback.format_exc()
            key = tb.strip().splitlines()[-1] + " @ " + [l for l in tb.splitlines() if "game.py" in l][-1].strip()
            if key not in crashes:
                crashes[key] = (seed, step, g.scene, getattr(g, "phase", None), tb)
            g = game.Game(headless=True)                     # после падения — с нуля
print("сцены (кадров):", dict(scene_hits))
print("уникальных падений:", len(crashes))
for key, (seed, step, scene, phase, tb) in crashes.items():
    print("=" * 80)
    print(f"seed={seed} step={step} scene={scene} phase={phase}")
    print(tb)
