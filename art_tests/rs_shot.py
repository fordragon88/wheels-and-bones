"""Экраны игры при масштабе рендера RS (как на большом мониторе): python art_tests/rs_shot.py RS out_prefix"""
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init()
import game
game.RS = float(sys.argv[1])
pre = sys.argv[2]
pygame.display.set_mode((round(1280 * game.RS), round(720 * game.RS)))
frame = game.Surf((1280, 720))
g = game.Game(headless=True); g.done = {"flat", "lift"}
def run(n):
    t0 = time.perf_counter()
    for _ in range(n): g.update(1 / 30); g.draw(frame)
    return (time.perf_counter() - t0) / n * 1000
g.scene = "hub"; run(60); ms = run(30); pygame.image.save(frame, pre + "_hub.png"); print(f"hub {ms:.1f} мс")
g.start_job("caster", variant=0); run(60); ms = run(30); pygame.image.save(frame, pre + "_job.png"); print(f"job {ms:.1f} мс")
g.open_seating(); g.seatc["tab"] = "fit"; g._seat_load_case(0); run(90); ms = run(30); pygame.image.save(frame, pre + "_seat.png"); print(f"seat {ms:.1f} мс")
