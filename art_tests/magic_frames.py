# -*- coding: utf-8 -*-
"""«Волшебство» героя на портрете экрана задания (assets/anim/magic_<герой>/NN.jpg + NN.a.png) из клипа MiniMax H3.

  python art_tests/magic_frames.py <герой> <mp4> [--layout путь/layout.json] [--height 360] [--step 2]
                                   [--thin 14] [--trap-near 12] [--lo 0.2] [--hi 0.85]

Исходники — art_tests/portrait_magic/<герой>/ в основной папке (не в git): клип 960×640, 24 к/с, ~90 кадров (кадр 0 —
исходная картинка с фоном другого оттенка, не берём) и layout.json (раскладка на холсте 1536×1024, клип — тот же
холст ×0,625): key (green|magenta), portrait [x, y, w, h] — где в кадре стоит портрет героя (assets/<art>, высота
704), crop [x0, y0, x1, y1] — какую часть кадра брать (портрет + поля под волшебство), art — файл портрета.

Шаги: кадры 1..N через --step (12 к/с) → ключ `ride_loop.key_frame` (фон — медиана рамки кадра, `--thin` сохраняет
тонкие светлые детали — звёзды, искры; `--trap-near` чистит «зажатый фон» только у края силуэта) → цвет кадров под
статичный портрет (усиление каналов по первому кадру; H3 рисует героя чуть темнее) → обрезка по crop → масштаб до
--height (не больше исходника), края кадра (кроме верхнего — он под шапкой) гаснут на --feather px, чтобы корни
и топор, вылезшие за поле, не резались по линии → assets/anim/magic_<герой>/. Совмещение: альфа портрета (assets/<art> по
раскладке) подгоняется к первому кадру клипа (сдвиг и масштаб, H3 иногда сдвигает героя на пару пикселей) —
в индекс идёт уточнённый прямоугольник портрета в пикселях кадра; заодно меряется, насколько последний кадр совпадает
с портретом (герой «вернулся в позу»).

Индекс для игры — assets/anim/magic_index.json: имя петли → {art, n, fps, size [w, h], portrait [x, y, w, h]}.
Инструмент дописывает/обновляет запись героя; игра строит «портрет → петля» только из этого файла (game.py править
не нужно). Листы проверки — art_tests/magic_shots/<герой>_key.png (кадры на тёмном/светлом/тёплом + крупно поле
с волшебством) и <герой>_frames.png (все кадры).
"""
import argparse, json, os, shutil, sys
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from ride_loop import (read_frames, bg_color, key_frame, bleed, comp, zoom, fit_h, hstack, vstack,  # noqa: E402
                       DARK, LIGHT, WARM)

CLIP_K = 0.625                                    # клип 960×640 = холст раскладки 1536×1024 × 0,625


def portrait_rgba(art, layout, shape):
    """Статичный портрет (assets/<art>) на холсте клипа по раскладке — с чем сравнивать кадры: (rgb, альфа)."""
    x, y, w, h = layout["portrait"]
    im = Image.open(os.path.join(ROOT, "assets", art)).convert("RGBA")
    pw, ph = w * CLIP_K, h * CLIP_K
    big = np.asarray(im, np.float32)
    M = np.float32([[pw / im.width, 0, x * CLIP_K], [0, ph / im.height, y * CLIP_K]])
    out = cv2.warpAffine(big, M, (shape[1], shape[0]), flags=cv2.INTER_AREA)
    return out[..., :3], out[..., 3] / 255


def register(a_ref, a, box):
    """Сдвиг (dx, dy) и масштаб s портрета в кадре клипа относительно раскладки: подбор по разнице альф в окрестности
    портрета (масштаб — от левого верхнего угла портрета). Возвращает (dx, dy, s, ошибка до, ошибка после)."""
    x0, y0, x1, y1 = box
    ref = a_ref[y0:y1, x0:x1]
    tgt = a[y0:y1, x0:x1]
    base = float(np.abs(ref - tgt).mean())
    best = (base, 0.0, 0.0, 1.0)
    for s in np.arange(0.97, 1.0301, 0.005):
        for dy in np.arange(-6, 6.01, 0.5):
            for dx in np.arange(-6, 6.01, 0.5):
                M = np.float32([[s, 0, dx], [0, s, dy]])
                w = cv2.warpAffine(ref, M, (ref.shape[1], ref.shape[0]), flags=cv2.INTER_LINEAR)
                e = float(np.abs(w - tgt).mean())
                if e < best[0]:
                    best = (e, float(dx), float(dy), float(s))
    return best[1], best[2], best[3], base, best[0]


def key_sheet(rgbs, alphas, pr, path):
    """Кадры на тёмном/светлом/тёплом фоне + ×2 поле с волшебством (справа от портрета и над ним) на тёмном и светлом."""
    n = len(rgbs)
    h, w = alphas[0].shape
    px, py, pw, ph = pr
    # кадры, где волшебства (альфы вне портрета) больше всего, + первый и последний
    outside = np.ones((h, w), bool)
    outside[int(py):int(py + ph), int(px):int(px + pw * 0.8)] = False
    amt = [float((a * outside).sum()) for a in alphas]
    peak = sorted(np.argsort(amt)[-2:].tolist())
    idx = sorted(set([0, n // 3, peak[0], peak[1], (2 * n) // 3, n - 1]))
    zb = (int(px + pw * 0.45), 0, w, h)                                  # поле справа: корни, руна, топор
    tb = (int(px), 0, int(px + pw), int(py + ph * 0.4))                  # над головой: листья на рогах, топор вверху
    rows = []
    for i in idx:
        rgb, a = rgbs[i], alphas[i]
        full = [fit_h(comp(rgb, a, c), 300) for c in (DARK, LIGHT, WARM)]
        zs = [fit_h(zoom(comp(rgb, a, c), zb, 2), 300) for c in (DARK, LIGHT)]
        zs += [fit_h(zoom(comp(rgb, a, DARK), tb, 2), 300)]
        rows.append(hstack(full + zs))
    Image.fromarray(vstack(rows)).save(path)
    return idx


def frames_sheet(rgbs, alphas, path):
    th = [fit_h(comp(r, a, DARK), 150) for r, a in zip(rgbs, alphas)]
    per = 9
    Image.fromarray(vstack([hstack(th[i:i + per], 3) for i in range(0, len(th), per)], 3)).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hero")
    ap.add_argument("mp4")
    ap.add_argument("--layout", default="", help="layout.json (по умолчанию — рядом с клипом)")
    ap.add_argument("--height", type=int, default=360, help="высота кадра, px (не больше исходника)")
    ap.add_argument("--step", type=int, default=2, help="2 — 24 → 12 к/с")
    ap.add_argument("--lo", type=float, default=0.2)
    ap.add_argument("--hi", type=float, default=0.85)
    ap.add_argument("--choke", type=float, default=0.15)
    ap.add_argument("--thin", type=float, default=14)
    ap.add_argument("--trap-near", type=int, default=12)
    ap.add_argument("--feather", type=int, default=12, help="края кадра гаснут на столько px (обрезанное волшебство)")
    ap.add_argument("--feather-top", action="store_true", help="гасить и верхний край (если верх кадра не под шапкой)")
    ap.add_argument("--no-match", dest="match", action="store_false", help="не подгонять цвет кадров под портрет")
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "anim"))
    args = ap.parse_args()
    lay_p = args.layout or os.path.join(os.path.dirname(os.path.abspath(args.mp4)), "layout.json")
    with open(lay_p, encoding="utf-8") as f:
        lay = json.load(f)
    key, art = lay["key"], lay["art"]
    name = f"magic_{args.hero}"

    fr = read_frames(args.mp4)
    idx = list(range(1, len(fr), args.step))                           # кадр 0 — исходная картинка, не берём
    cx0, cy0, cx1, cy1 = [v * CLIP_K for v in lay["crop"]]
    X0, Y0 = int(np.floor(cx0)), int(np.floor(cy0))                    # обрезка в пикселях клипа (наружу)
    X1, Y1 = min(fr.shape[2], int(np.ceil(cx1))), min(fr.shape[1], int(np.ceil(cy1)))
    H = min(args.height, Y1 - Y0)                                      # не увеличивать исходник
    k = H / (Y1 - Y0)
    size = (round((X1 - X0) * k), H)

    rgbs, alphas = [], []
    for i in idx:
        bg = bg_color(fr[i])
        rgb, a = key_frame(fr[i], bg, key, args.lo, args.hi, args.choke, args.thin, args.trap_near)
        rgbs.append(rgb)
        alphas.append(a)

    # совмещение: портрет из раскладки ↔ первый и последний кадр (в пикселях клипа)
    rgb_ref, a_ref = portrait_rgba(art, lay, fr.shape[1:3])
    px, py, pw, ph = [v * CLIP_K for v in lay["portrait"]]
    box = (max(0, int(px) - 20), max(0, int(py) - 20), min(fr.shape[2], int(px + pw) + 20),
           min(fr.shape[1], int(py + ph) + 20))
    # масштаб в register — от угла окна box; переводим в прямоугольник портрета
    dx, dy, s, e0, e1 = register(a_ref, alphas[0], box)
    bx, by = box[0], box[1]
    rpx, rpy = bx + (px - bx) * s + dx, by + (py - by) * s + dy
    rpw, rph = pw * s, ph * s
    ldx, ldy, ls, le0, le1 = register(a_ref, alphas[-1], box)
    print(f"{name}: первый кадр vs портрет — сдвиг ({dx:+.1f}, {dy:+.1f}) px клипа, масштаб {s:.3f}, "
          f"ошибка альфы {e0:.4f} -> {e1:.4f}; последний кадр — ({ldx:+.1f}, {ldy:+.1f}), {ls:.3f}, {le0:.4f} -> {le1:.4f}")

    # цвет: H3 перерисовывает героя чуть иначе (Леший темнее и бурее портрета) — усиление каналов по сплошной части
    # портрета в первом кадре, то же для всех кадров (переход портрет ↔ кадр без «вспышки» цвета)
    gain = np.ones(3, np.float32)
    if args.match:
        both = (a_ref > 0.95) & (alphas[0] > 0.95)
        gain = np.clip(rgb_ref[both].mean(0) / np.maximum(rgbs[0][both].mean(0), 1), 0.8, 1.25).astype(np.float32)
        rgbs = [np.clip(r * gain, 0, 255) for r in rgbs]
    print(f"{name}: цвет кадров × {[round(float(v), 3) for v in gain]} (под статичный портрет)")

    out = os.path.join(args.out, name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    # края обрезки: то, что вылезло за поле (корни внизу, топор слева), гаснет на --feather px, а не режется по линии
    # (верх — нет: верх кадра на экране уходит под шапку задания, топор Гра над головой иначе бледнел)
    fy = np.arange(size[1])[::-1].astype(np.float32)
    if args.feather_top:
        fy = np.minimum(fy, np.arange(size[1]))
    fx = np.minimum(np.arange(size[0]), np.arange(size[0])[::-1]).astype(np.float32)
    edge = np.clip(np.minimum(fy[:, None], fx[None, :]) / max(1, args.feather), 0, 1)
    o_rgb, o_a = [], []
    for n, (rgb, a) in enumerate(zip(rgbs, alphas)):
        ac = a[Y0:Y1, X0:X1].astype(np.float32)                        # масштаб с умножением на альфу (без каймы фона)
        pm = cv2.resize(rgb[Y0:Y1, X0:X1] * ac[..., None], size, interpolation=cv2.INTER_AREA)
        a2 = np.clip(cv2.resize(ac, size, interpolation=cv2.INTER_AREA), 0, 1) * edge
        r2 = np.clip(pm / np.maximum(a2, 1e-4)[..., None], 0, 255) * (a2 > 1e-4)[..., None]
        r2 = bleed(r2, a2)
        Image.fromarray(np.uint8(np.clip(r2, 0, 255))).save(os.path.join(out, f"{n:02d}.jpg"), "JPEG", quality=90,
                                                             optimize=True)
        mask = Image.new("RGBA", size, (255, 255, 255, 0))
        mask.putalpha(Image.fromarray(np.uint8(np.round(a2 * 255))))
        mask.save(os.path.join(out, f"{n:02d}.a.png"), "PNG", optimize=True)
        o_rgb.append(r2)
        o_a.append(a2)
    portrait = [round((rpx - X0) * k, 2), round((rpy - Y0) * k, 2), round(rpw * k, 2), round(rph * k, 2)]
    fps = round(24 / args.step, 2)

    shots = os.path.join(ROOT, "art_tests", "magic_shots")
    os.makedirs(shots, exist_ok=True)
    rows = key_sheet(o_rgb, o_a, portrait, os.path.join(shots, f"{args.hero}_key.png"))
    frames_sheet(o_rgb, o_a, os.path.join(shots, f"{args.hero}_frames.png"))

    ip = os.path.join(args.out, "magic_index.json")
    idx_all = {}
    if os.path.exists(ip):
        with open(ip, encoding="utf-8") as f:
            idx_all = json.load(f)
    idx_all[name] = dict(art=art, n=len(o_a), fps=fps, size=list(size), portrait=portrait)
    with open(ip, "w", encoding="utf-8", newline="\n") as f:
        json.dump(idx_all, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    kb = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)) / 1024
    print(f"{name}: {len(o_a)} кадров {fps} к/с, {size[0]}×{size[1]}, портрет в кадре {portrait}, {kb:.0f} КБ; "
          f"лист ключа (кадры {rows}) — art_tests/magic_shots/{args.hero}_key.png")


if __name__ == "__main__":
    main()
