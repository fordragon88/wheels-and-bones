# Сравнение двух папок снимков: средняя разница и худшие области (сетка 8×6). diff.py A B [имена]
import sys, os
from PIL import Image, ImageChops, ImageStat
a, b = sys.argv[1], sys.argv[2]
names = sys.argv[3:] or sorted(n for n in os.listdir(a) if n.endswith('.png'))
# Известные отличия от game.py — области, которые не сравниваются (в обоих снимках закрашены одинаково):
# Кабинет посадки на компьютере — значки в списках уроков и клиентов (решение владельца 21.11; seating.gd desk_icon):
# весь список (уроки 4 ряда по 44 с y 112, клиенты 5 рядов по 40 — до y 307) на вкладках уроков и примерки.
SEAT_LIST = (776, 108, 1260, 310)
KNOWN = [(lambda n: n.removeprefix('big_').removeprefix('calm_').startswith(('seat_lesson', 'seat_fit', 'scan_seat',
                                                                             'x_lesson_')), SEAT_LIST)]


def masked(n, A, B):
    for test, box in KNOWN:
        if test(n):
            for im in (A, B):
                im.paste((0, 0, 0), box)
    return A, B


rows = []
for n in names:
    pa, pb = os.path.join(a, n), os.path.join(b, n)
    if not os.path.exists(pb): continue
    A = Image.open(pa).convert('RGB'); B = Image.open(pb).convert('RGB')
    if A.size != B.size: B = B.resize(A.size)
    A, B = masked(n, A, B)
    d = ImageChops.difference(A, B).convert('L')
    m = ImageStat.Stat(d).mean[0]
    W, H = A.size; cells = []
    for gy in range(6):
        for gx in range(8):
            box = (gx*W//8, gy*H//6, (gx+1)*W//8, (gy+1)*H//6)
            cells.append((ImageStat.Stat(d.crop(box)).mean[0], box))
    cells.sort(reverse=True)
    rows.append((m, n, cells[:3]))
rows.sort(reverse=True)
for m, n, c in rows:
    print(f"{m:6.2f} {n:40s} " + " ".join(f"{v:.0f}@{bx[0]},{bx[1]}" for v, bx in c))
