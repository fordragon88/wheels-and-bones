"""Тела клиентов Кабинета посадки — «вырезные куклы» из рисунка сбоку (ChatGPT/Codex по рисунку клиента).

Рисунок: персонаж строго сбоку, лицом вправо, сидит прямо (бёдра горизонтально, голени вертикально), белый фон.
Суставы отмечаются вручную в пикселях рисунка (RIGS ниже). Скрипт убирает белый фон, режет рисунок на части
по ближайшей «кости» (торс с головой, бедро, голень со стопой, рука) и пишет:
  assets/seat_body_<id>_<part>.png  и  assets/seat_bodies.json  (суставы каждой части в её пикселях).
Игра (Game._draw_seat_puppet) поворачивает и масштабирует каждую часть по своей кости скелета — поза живая.
python art_tests/seat_bodies.py   (рисунки — art_tests/seat_bodies/side_<id>.png)"""
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "seat_bodies")
OUT = os.path.join(HERE, "..", "assets")
MAX = 640                                   # сторона рисунка в игре (меньше памяти и места)
# суставы в пикселях исходного рисунка
RIGS = {
    "seat_troll": dict(src="side_troll.png", hip=(330, 730), knee=(730, 765), ankle=(720, 990), toe=(910, 1040),
                       sh=(365, 370), elbow=(455, 535), hand=(800, 500), neck=(430, 275), head=(440, 150)),
}
# части: (имя, кости для разрезки — ломаные, опорный сустав, второй сустав, порядок рисования).
# Рука — вместе с торсом (у толстых персонажей прилегает к животу; у скелета движется вместе с плечом).
# Голова — отдельно (neck→head): у мультяшных героев она огромная, игра подгоняет её к черепу скелета.
PARTS = [("shin", (("knee", "ankle", "toe"),), "knee", "ankle", 0),
         ("thigh", (("hip", "knee"),), "hip", "knee", 1),
         ("torso", (("hip", "sh"), ("sh", "elbow", "hand")), "hip", "sh", 2),
         ("head", (("neck", "head"),), "neck", "head", 3)]


def seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / max(1e-9, dx * dx + dy * dy), 0, 1)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def cut_white(im):
    """Белый фон, связанный с краем картинки -> прозрачность (контуры персонажа тёмные — заливка их не переходит)."""
    rgb = im.convert("RGB")
    a = np.asarray(rgb, np.int16)
    white = (a.min(2) > 232)
    from scipy.ndimage import label
    lab, _ = label(white)
    edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    bg = np.isin(lab, list(edge))
    alpha = Image.fromarray(np.uint8(~bg) * 255).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def main():
    meta = {}
    for cid, rig in RIGS.items():
        im = cut_white(Image.open(os.path.join(SRC, rig["src"])))
        k = MAX / max(im.size)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        J = {n: (v[0] * k, v[1] * k) for n, v in rig.items() if n != "src"}
        A = np.asarray(im)[:, :, 3]
        ys, xs = np.mgrid[0:im.height, 0:im.width]
        d = []
        for name, chains, *_ in PARTS:
            dd = np.full(A.shape, 1e9)
            for chain in chains:
                for p, q in zip(chain, chain[1:]):
                    dd = np.minimum(dd, seg_dist(xs, ys, J[p], J[q]))
            d.append(dd)
        owner = np.argmin(np.stack(d), 0)
        meta[cid] = dict(parts={})
        for i, (name, chains, j0, j1, order) in enumerate(PARTS):
            m = Image.fromarray(np.uint8((owner == i) & (A > 0)) * 255).filter(ImageFilter.MaxFilter(7))   # нахлёст
            part = im.copy()
            pa = np.minimum(np.asarray(part)[:, :, 3], np.asarray(m))
            part.putalpha(Image.fromarray(pa))
            bb = part.getbbox()
            if not bb:
                continue
            part = part.crop(bb)
            fn = f"seat_body_{cid}_{name}.png"
            part.save(os.path.join(OUT, fn), optimize=True)
            meta[cid]["parts"][name] = dict(file=fn, order=order, a=j0, b=j1,
                                            pa=[round(J[j0][0] - bb[0], 1), round(J[j0][1] - bb[1], 1)],
                                            pb=[round(J[j1][0] - bb[0], 1), round(J[j1][1] - bb[1], 1)])
        print(cid, {n: v["file"] for n, v in meta[cid]["parts"].items()})
    json.dump(meta, open(os.path.join(OUT, "seat_bodies.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
