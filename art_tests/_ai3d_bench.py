import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame
pygame.init(); S = pygame.display.set_mode((1280, 720))
import game
g = game.Game(headless=True); g.start_job("flat", None); g.open_v3d(); g.v3d["idle"] = -99
for ai in (False, True):
    g.v3d["ai"] = ai
    for _ in range(12): g.draw(S); g.update(1/30)
    t = time.perf_counter()
    for _ in range(10): g.v3d["yaw"] += 0.05; g.draw(S)
    print(f"{sys.version.split()[0]} numpy={'yes' if game._np is not None else 'no'} ai={ai}: {(time.perf_counter()-t)/10*1000:.0f} ms/кадр")
    if ai and len(sys.argv) > 1:
        pygame.image.save(S, sys.argv[1])
