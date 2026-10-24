"""Все сцены и оверлеи при масштабе рендера RS (ловим падения слоя): python art_tests/rs_smoke.py 2"""
import os, sys
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")   # проверки — без звука
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init()
import game
game.RS = float(sys.argv[1] if len(sys.argv) > 1 else 2)
pygame.display.set_mode((round(1280 * game.RS), round(720 * game.RS)))
F = game.Surf((1280, 720))
g = game.Game(headless=True)
def run(n=20):
    for _ in range(n): g.update(1 / 30); g.draw(F)
E = lambda t, **k: g.handle_event(pygame.event.Event(t, **k))
for sc in ("title", "intro", "hub", "garage", "guild", "ending"):
    g.scene = sc; run()
g.done = {j["id"] for j in game.JOBS}; g.scene = "hub"; run(); g.hub_page = 1; run()
for jid in [j["id"] for j in game.ALL_JOBS]:
    g.start_job(jid); run(15)
    if g.cur.get("track") == "tech":
        g.open_manual(); run(5); g.show_manual = False; continue
    g.open_v3d(); run(10)
    E(pygame.MOUSEBUTTONDOWN, button=1, pos=g._v3d_view_rect().center)
    E(pygame.MOUSEMOTION, pos=(g._v3d_view_rect().centerx + 50, 300), rel=(50, 0), buttons=(1, 0, 0)); run(3)
    E(pygame.MOUSEBUTTONUP, button=1, pos=(g._v3d_view_rect().centerx + 50, 300)); g.v3d = None
    for p in g.cur["parts"][:2]: g.inspect_part(p)
    g.choose_diagnosis(next(i for i, d in enumerate(g.cur["diagnosis"]) if d["correct"])); run(10)
g.show_sound = True; run(5); g.show_sound = False
g.open_seating()
for tab in ("lessons", "fit", "quiz"):
    g.seatc["tab"] = tab; run(10)
print("RS", game.RS, "— все сцены отрисованы без ошибок")
