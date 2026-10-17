"""Полоска на стыке анимации «дыхания» (blit_idle, mode=breathe): верх спрайта растягивается, низ стоит.
Меряем, насколько строки у стыка «рваные» по сравнению с исходной картинкой, на масштабах RS 1 / 1.5 / 2.
python art_tests/seam_check.py   — ОК, если лишняя «полосатость» ≤ 8 (была 62.7 на RS 1.5 до исправления)."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
import game as g
ok = True
for rs in (1.0, 1.5, 2.0):
    g.RS = rs; g._img_cache.clear()
    worst = 0.0
    for name in ("client_elf.png", "client_iris.png", "martin.png", "client_troll.png"):
        img = g.load_image(name, (150, 190), g.GHOST)
        RW, RH = pygame.Surface.get_size(img); cut = int(RH * 0.55)
        o = round(10 * rs)
        base = g.Surf((170, 210)); pygame.Surface.fill(base, (70, 60, 50)); pygame.Surface.blit(base, img, (o, o))
        row = lambda s, y: [s.get_at((o + x, o + y))[:3] for x in range(0, RW, 2)]
        for step in range(20):
            fr = g.Surf((170, 210)); pygame.Surface.fill(fr, (70, 60, 50))
            g.blit_idle(fr, img, (10, 10), step * 0.13)
            for y in range(cut - 3, cut + max(4, RH // 30) + 4):
                a, b, c = row(fr, y - 1), row(fr, y), row(fr, y + 1)
                A, B, C = row(base, y - 1), row(base, y), row(base, y + 1)
                jag = sum(abs(b[i][k] - (a[i][k] + c[i][k]) / 2) for i in range(len(b)) for k in range(3)) / len(b)
                JAG = sum(abs(B[i][k] - (A[i][k] + C[i][k]) / 2) for i in range(len(B)) for k in range(3)) / len(B)
                worst = max(worst, jag - JAG)
    print(f"RS {rs}: лишняя «полосатость» у стыка {worst:.1f}")
    ok &= worst <= 8
print("OK" if ok else "ПОЛОСКА ВИДНА")
sys.exit(0 if ok else 1)
