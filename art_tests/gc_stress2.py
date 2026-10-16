"""Стресс сборщика мусора в полной игре (со звуком): python art_tests/gc_stress2.py RS lang кадров"""
import os, sys, gc, faulthandler
faulthandler.enable()
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
import game
game.RS = float(sys.argv[1]); game.set_lang(sys.argv[2]); n = int(sys.argv[3])
game.build_sounds()
pygame.display.set_mode((round(1280 * game.RS), round(720 * game.RS)))
F = game.Surf((1280, 720))
g = game.Game()
for i in range(n):
    if i == n // 5: g.scene = "hub"
    if i == 2 * n // 5: g.start_job("flat")
    if i == 3 * n // 5: g.start_job("lift")
    if i == 4 * n // 5: g.open_seating()
    g.update(1 / 30); g.draw(F); gc.collect()
print("OK", sys.argv[1:])
