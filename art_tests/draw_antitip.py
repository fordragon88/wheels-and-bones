"""Дорисовать антиопрокидыватели на арте колясок (трубка из-за заднего колеса + колёсико).
python art_tests/draw_antitip.py — берёт оригиналы из art_tests/bak_antitip/, пишет в assets/."""
from PIL import Image, ImageDraw
import os, math
HERE = os.path.dirname(os.path.abspath(__file__))
SS = 4                                   # суперсэмплинг для гладких краёв
# координаты в пикселях арта 760×600: (начало трубки у колеса, центр колёсика, радиус колёсика)
SPECS = {
    "aeroz":   [((150, 520), (70, 552), 13)],
    "cross6":  [((226, 530), (124, 542), 12)],
    "focuscr": [((122, 524), (66, 550), 13)],
}


def draw(name, items):
    base = Image.open(os.path.join(HERE, "bak_antitip", f"chair_{name}.png")).convert("RGBA")
    W, H = base.size
    ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for (x0, y0), (cx, cy), r in items:
        s = lambda v: v * SS
        ang = math.atan2(cy - y0, cx - x0)
        ex, ey = cx - (r * 0.2) * math.cos(ang), cy - (r * 0.2) * math.sin(ang)
        d.line([(s(x0), s(y0)), (s(ex), s(ey))], fill=(40, 40, 46, 255), width=s(9))          # обводка трубки
        d.line([(s(x0), s(y0)), (s(ex), s(ey))], fill=(150, 156, 168, 255), width=s(6))       # металл
        d.line([(s(x0), s(y0) - s(1.2)), (s(ex), s(ey) - s(1.2))], fill=(214, 218, 226, 255), width=s(2))  # блик
        d.ellipse([s(cx - r - 1.5), s(cy - r - 1.5), s(cx + r + 1.5), s(cy + r + 1.5)], fill=(26, 26, 30, 255))
        d.ellipse([s(cx - r), s(cy - r), s(cx + r), s(cy + r)], fill=(44, 44, 50, 255))
        d.ellipse([s(cx - r * 0.5), s(cy - r * 0.5), s(cx + r * 0.5), s(cy + r * 0.5)], fill=(170, 174, 184, 255))
        d.ellipse([s(cx - r * 0.18), s(cy - r * 0.18), s(cx + r * 0.18), s(cy + r * 0.18)], fill=(60, 60, 66, 255))
    ov = ov.resize((W, H), Image.LANCZOS)
    out = Image.alpha_composite(base, ov)
    out.save(os.path.join(HERE, "..", "assets", f"chair_{name}.png"))


if __name__ == "__main__":
    for n, it in SPECS.items():
        draw(n, it)
    print("ok")
