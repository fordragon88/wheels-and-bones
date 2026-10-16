"""Сетка сравнения: python sheet.py out.png cols tile_w tile_h file1[:подпись] file2 ..."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
out, C, TW, TH = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
items = [a.split("::") for a in sys.argv[5:]]
pad, lab = 10, 28
rows = (len(items) + C - 1) // C
sheet = pygame.Surface((C * TW + (C + 1) * pad, rows * (TH + lab + pad) + pad)); sheet.fill((236, 232, 224))
f = pygame.font.SysFont("segoeui,arial", 20, bold=True)
for n, it in enumerate(items):
    path = it[0]; label = it[1] if len(it) > 1 else os.path.basename(path)
    im = pygame.image.load(path).convert_alpha()
    bg = pygame.Surface(im.get_size()); bg.fill((200, 196, 188) if im.get_bitsize() == 32 else (255, 255, 255)); bg.blit(im, (0, 0))
    x = pad + (n % C) * (TW + pad); y = pad + (n // C) * (TH + lab + pad)
    sheet.blit(f.render(label, True, (40, 40, 48)), (x + 4, y + 3))
    sheet.blit(pygame.transform.smoothscale(bg, (TW, TH)), (x, y + lab))
pygame.image.save(sheet, out); print(out, sheet.get_size())
