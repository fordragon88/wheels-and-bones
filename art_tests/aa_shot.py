"""Крупный план главного экрана (как на мониторе с масштабом 1.5x): python art_tests/aa_shot.py out.png"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init(); S = pygame.display.set_mode((1280, 720))
import game
g = game.Game(headless=True); g.done = {"flat", "lift"}
g.scene = "hub"
for _ in range(90): g.update(1 / 30); g.draw(S)
crop = S.subsurface((40, 110, 640, 320)).copy()
pygame.image.save(pygame.transform.smoothscale(crop, (1280, 640)), sys.argv[1])
