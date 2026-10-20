"""Крупные виды модели (сбоку/спереди/сверху) с подписанной сеткой 50 мм — чтобы задать области деталей.
python tripo_views.py <prefix>   (читает <prefix>_full.npz, пишет <prefix>_grid.png)
Если есть <prefix>_labels.npy (номер детали на грань) — красит детали условными цветами (проверка разметки)."""
import sys, os
import numpy as np
from PIL import Image, ImageDraw

prefix = sys.argv[1]
import os as _os
_lm = prefix + "_labeled_mesh.npz"
d = np.load(_lm if (_os.path.exists(_lm) and "--raw" not in sys.argv) else prefix + "_full.npz")
V, F, C = d["V"], d["F"], d["C"]
lab_path = prefix + "_labels.npz"
Cf = C[F].mean(1)
legend = []
if os.path.exists(lab_path) and "--raw" not in sys.argv:
    L = np.load(lab_path, allow_pickle=True)
    lab, names = L["lab"], list(L["names"])
    rng = np.random.RandomState(3)
    pal = rng.randint(40, 235, size=(len(names), 3))
    Cf = np.where(lab[:, None] >= 0, pal[np.maximum(lab, 0)], Cf * 0.35 + 160)
    legend = [(n, tuple(int(t) for t in pal[i])) for i, n in enumerate(names)]
Pc = V[F].mean(1)
S = 720
views = [("SIDE: x right(forward), y up", 0, 1, 2, 1), ("FRONT (from +x): z right, y up", 2, 1, 0, -1),
         ("TOP: x right, z down", 0, 2, 1, 1)]
lo, hi = V.min(0), V.max(0)
sheet = Image.new("RGB", (S * 3, S + 30 + 18 * ((len(legend) + 5) // 6)), "white")
for k, (title, ax, ay, depth_ax, dsign) in enumerate(views):
    im = Image.new("RGB", (S, S), (252, 252, 252))
    dr = ImageDraw.Draw(im)
    span = max(hi[ax] - lo[ax], hi[ay] - lo[ay]) * 1.08
    s = (S - 60) / span
    cx, cy = (hi[ax] + lo[ax]) / 2, (hi[ay] + lo[ay]) / 2

    def to(x, y):
        yy = y if ay != 2 else -y
        cyy = cy if ay != 2 else -cy
        return S / 2 + (x - cx) * s, S / 2 - (yy - cyy) * s
    for g in range(-2000, 2001, 50):
        col = (200, 200, 220) if g % 100 == 0 else (235, 235, 242)
        x0, y0 = to(g, -2000); x1, y1 = to(g, 2000)
        dr.line([(x0, y0), (x1, y1)], fill=col)
        x0, y0 = to(-2000, g); x1, y1 = to(2000, g)
        dr.line([(x0, y0), (x1, y1)], fill=col)
    order = np.argsort(dsign * Pc[:, depth_ax])
    X, Y = V[:, ax], V[:, ay]
    for fi in order:
        a, b, c = F[fi]
        dr.polygon([to(X[a], Y[a]), to(X[b], Y[b]), to(X[c], Y[c])], fill=tuple(int(t) for t in Cf[fi]))
    for g in range(-2000, 2001, 100):                    # подписи сетки
        x, _ = to(g, 0)
        if 20 < x < S - 20:
            dr.text((x - 10, S - 14), str(g), fill=(150, 0, 0))
        _, y = to(0, g)
        if 10 < y < S - 20:
            dr.text((2, y - 6), str(g), fill=(0, 0, 160))
    dr.text((6, 4), title, fill=(200, 0, 0))
    sheet.paste(im, (k * S, 0))
dr = ImageDraw.Draw(sheet)
for i, (n, col) in enumerate(legend):
    x, y = 10 + (i % 6) * 360, S + 8 + (i // 6) * 18
    dr.rectangle([x, y, x + 14, y + 12], fill=col)
    dr.text((x + 20, y), n, fill=(0, 0, 0))
sheet.save(prefix + ("_grid.png" if not legend else "_labeled.png"))
print("bbox", lo.round(), hi.round())
