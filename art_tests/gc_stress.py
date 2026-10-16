"""Стресс сборщика мусора при RS>1 (ловит порчу памяти в слое Surf): python art_tests/gc_stress.py [RS] [кадров]"""
import os, sys, gc, faulthandler
faulthandler.enable()
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init()
import game
game.RS = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
pygame.display.set_mode((round(1280 * game.RS), round(720 * game.RS)))
F = game.Surf((1280, 720))
game.set_lang(os.environ.get("WNB_LANG", "ru")); g = game.Game(headless=True); g.done = {"flat", "caster"}
n = int(sys.argv[2]) if len(sys.argv) > 2 else 400
for i in range(n):
    if i == n // 4: g.start_job("caster", variant=0)
    if i == n // 2: g.open_seating()
    if i == 3 * n // 4: g.scene = "hub"
    g.update(1 / 30); g.draw(F); gc.collect()
print("gc_stress OK", n, "кадров при RS", game.RS)
