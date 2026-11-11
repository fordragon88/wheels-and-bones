# -*- coding: utf-8 -*-
"""Петля проезда героя для тест-драйва (assets/anim/ride_<имя>/NN.jpg + NN.a.png) из клипа MiniMax H3.

  python art_tests/ride_loop.py <имя> <mp4> [--key green|magenta] [--height 440] [--len N --start S] [--fade 2]

Клип: 960×640, 24 к/с, герой едет «на месте» вправо на ровном фоне (зелёный или пурпурный — у Мартина зелёная кожа,
у Аэлин зелёное платье и рама, поэтому они на пурпурном). Шаги:
1) кадры через ffmpeg; первый (исходная картинка, фон другого оттенка) не берём;
2) петля: перебор длины 18–72 и начала; цена шва = разница кадра начала и кадра «после конца» (тогда переход
   последний → первый — обычный шаг) + разница скоростей на шве; сравнение — только по «движущимся» пикселям
   (колёса, руки): у электроколяски тело почти неподвижно, иначе шум тела заглушил бы колесо;
3) ключ: фон — медиана рамки каждого кадра (в рендере он чуть «плывёт»); альфа по «экранности» (зелёный: G − max(R,B);
   пурпурный: min(R,B) − G; в долях от фона: ≤ lo — непрозрачно, ≥ hi — прозрачно; тёмное ≠ фон),
   «распутывание» полупрозрачной кромки F = (C − (1−a)·фон)/a, поджатие кромки, подавление рефлекса фона
   (цветность вдоль цветности фона — прочь, если оттенок близок к фону) у кромки и в тёмных деталях; островки — прочь;
4) общий bbox по всем кадрам петли (герой не «плавает»), поле, масштаб до --height; цвет под прозрачностью — от
   соседей (как build_web._bleed), иначе JPEG даёт тёмную кайму;
5) листы проверки: art_tests/ride_shots/<имя>_key.png (кадры на тёмном/светлом/тёплом + ×3 колесо, волосы, руки)
   и <имя>_loop.png (все кадры + шов «последний → первый»);
6) замер колеса (центр и радиус по кругу Хафа, поворот за кадр — подбором угла) — для скорости проезда в игре.
"""
import argparse, json, os, shutil, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = os.environ.get("FFMPEG", r"I:\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe")
if not os.path.exists(FF):
    FF = "ffmpeg"
sys.path.insert(0, ROOT)


def read_frames(path):
    p = subprocess.run([FF, "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    pr = subprocess.run([os.path.join(os.path.dirname(FF), "ffprobe.exe") if os.path.dirname(FF) else "ffprobe", "-v", "error",
                         "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                        capture_output=True, text=True, check=True)
    w, h = map(int, pr.stdout.strip().split(","))
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w, 3)


def bg_color(f):
    b = np.concatenate([f[:12].reshape(-1, 3), f[-12:].reshape(-1, 3), f[:, :12].reshape(-1, 3), f[:, -12:].reshape(-1, 3)])
    return np.median(b, 0).astype(np.float32)


def stabilize(fr, bgs, mode):
    """Герой «уплывает» в кадре (Тилли: 80 px вправо за клип — петля не замыкается). Сдвиг — по жёсткой части
    коляски: левый и правый край силуэта в нижней трети (колёса, подножка; руки и крылья выше). Края сглажены
    кубической кривой по времени (дрейф плавный, край даёт шум ±1 px), сдвиг дробный, поле — цветом фона."""
    xs = []
    for f, b in zip(fr, bgs):
        c = f.astype(np.int16)
        r, g, bl = c[..., 0], c[..., 1], c[..., 2]
        kv = (g - np.maximum(r, bl)) if mode == "green" else (np.minimum(r, bl) - g)
        on = kv < 40
        rows = np.where(on.any(1))[0]
        cols = np.where(on[int(rows.min() + 0.66 * (rows.max() - rows.min())):].any(0))[0]
        xs.append((cols.min() + cols.max()) / 2)
    xs = np.array(xs, np.float64)
    t = np.arange(len(xs))
    fit = np.polyval(np.polyfit(t[1:], xs[1:], 3), t)                 # кадр 0 — исходная картинка
    fit[0] = xs[0]
    dx = fit - np.median(fit)
    out = np.empty_like(fr)
    for i, f in enumerate(fr):
        M = np.float32([[1, 0, -dx[i]], [0, 1, 0]])
        out[i] = cv2.warpAffine(f, M, (f.shape[1], f.shape[0]), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=[float(v) for v in bgs[i]])
    return out, float(dx.max() - dx.min()), float(np.abs(xs[1:] - fit[1:]).max())


# ---------- петля ----------
def dedup(fr, bgs):
    """Повторы кадров: H3 иногда даёт 18 к/с, растянутые до 24 повтором каждого 3-го (у Мартина шаг 0 через
    каждые 4 кадра — колесо «спотыкается» 6 раз в секунду). Почти нулевые шаги (< 0,35 медианы) выбрасываем, если их
    ≥ 15 %; частота исходника — 24 · оставшиеся / все. Иначе — всё как есть (Вольф, Мора, Аэлин)."""
    sm = np.stack([cv2.resize(f.astype(np.float32) - b, (240, 160), interpolation=cv2.INTER_AREA)
                   for f, b in zip(fr, bgs)])
    var = sm[1:].std(0).mean(-1)
    w = var >= np.percentile(var, 88)
    adj = np.array([np.abs(sm[i + 1][w] - sm[i][w]).mean() for i in range(len(sm) - 1)])
    dup = adj < 0.35 * np.median(adj)
    if dup.mean() < 0.15:
        return list(range(len(fr))), 24.0
    keep = [0] + [i + 1 for i in range(len(adj)) if not dup[i]]
    return keep, 24.0 * len(keep) / len(fr)


def pick_loop(fr, bgs, lmin=18, lmax=72, step=1):
    n = len(fr)
    sm = np.stack([cv2.resize(f.astype(np.float32) - b, (240, 160), interpolation=cv2.INTER_AREA)
                   for f, b in zip(fr, bgs)])
    var = sm[1:].std(0).mean(-1)                                      # где кадры меняются (колёса, руки)
    w = var >= np.percentile(var, 88)
    v = sm[:, w]                                                        # (n, k, 3)
    D = np.zeros((n, n))
    for i in range(n):
        D[i] = np.abs(v - v[i]).mean((1, 2))
    adj = np.array([D[i, i + 1] for i in range(1, n - 1)])
    ma = float(np.median(adj))
    best = None
    for L in range(lmin, min(lmax, n - 2) + 1):
        if L % step:
            continue                                                    # прореживание: целое число кадров
        for s in range(1, n - L):                                       # кадр 0 не берём
            seam = D[s, s + L] / ma                                     # «после конца» ≈ начало
            last = s + L - step
            speed = abs(D[last, s] - D[last, s + L]) / ma               # шаг через шов как обычный шаг
            c = seam + 0.5 * speed
            if step > 1:                                                # ровность шагов после прореживания
                st = np.array([D[i, i + step] for i in range(s, s + L, step)])
                c += 0.5 * st.std() / st.mean()
            if best is None or c < best[0] - 1e-9:
                best = (c, L, s, seam, speed)
    return best, ma, D


# ---------- ключ ----------
def key_frame(f, bg, mode, lo, hi, choke=0.15, thin=0, trap_near=0):
    c = f.astype(np.float32)
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    if mode == "green":                                                  # «экранность»: насколько канал фона
        kv, kb = g - np.maximum(r, b), bg[1] - max(bg[0], bg[2])          # выше остальных (тёмное ≠ фон)
    else:
        kv, kb = np.minimum(r, b) - g, min(bg[0], bg[2]) - bg[1]
    kv = kv / kb                                                         # 1 — как фон, 0 и меньше — не фон
    a = np.clip((hi - kv) / (hi - lo), 0, 1)
    if thin:
        # тонкие светлые спицы (1 px поверх фона: Гра, Юки, Тилли): H3 жмёт цвет 4:2:0, оттенок спицы — почти фон,
        # «экранность» даёт рваную полупрозрачную линию, и её куски уходят как островки. Яркость же у спицы заметно
        # выше фона (фон ровный): светлее фона на thin…thin+45 — непрозрачность 0…1
        y = c @ np.float32([0.299, 0.587, 0.114])
        yb = float(bg @ np.float32([0.299, 0.587, 0.114]))
        a = np.maximum(a, np.clip((y - yb - thin) / 45.0, 0, 1))
    clear = (a <= 0.02).astype(np.uint8)
    near = cv2.dilate(clear, np.ones((7, 7), np.uint8)) > 0             # кромка: ≤ 3 px от прозрачного
    semi = (a > 0.02) & (a < 0.98)
    aa = np.maximum(a, 0.25)[..., None]
    un = np.clip((c - (1 - a[..., None]) * bg) / aa, 0, 255)
    c = np.where(semi[..., None], un, c)
    # поджать полупрозрачную кромку — слегка: тонкие светлые спицы Аэлин (1–2 px поверх пурпурного) при прежнем
    # (a − 0,3)/0,7 исчезали; цвет кромки и так очищен «распутыванием» и рефлексом ниже
    a = np.where(near, np.clip((a - choke) / (1 - choke), 0, 1), a)
    # рефлекс фона: у кромки (H3 жмёт цвет 4:2:0 — оттенок фона «вытекает» за контур на 1–2 px) и в очень тёмных
    # деталях (обод, шины) убрать составляющую цветности вдоль цветности фона, если оттенок пикселя близок к фону
    # (косинус > 0,5): оранжевая рубашка у пурпурного, клетка у зелёного — не того оттенка и не трогаются
    u = bg - bg.mean()
    ch = c - c.mean(-1, keepdims=True)
    dot = (ch * u).sum(-1)
    cos = dot / (np.linalg.norm(ch, axis=-1) * np.linalg.norm(u) + 1e-6)
    t = np.clip(dot / (u * u).sum(), 0, None)
    band = near & (a > 0)
    dark = (a > 0) & (c.max(-1) < 60)
    fix = (band | dark) & (cos > 0.5)
    # «зажатый» фон в узких щелях (между трубками рамы, в шерсти): заметно «экранный» исходник и оттенок фона.
    # Зелёный: ещё и B > R — смесь с зелёным фоном (0,157,59) синевата, а зелёная клетка рубашки Вольфа — нет
    trap = (a > 0) & (kv > 0.12) & (cos > (0.8 if mode == "green" else 0.75))
    if mode == "green":
        trap &= c[..., 2] > c[..., 0] + 8
    if trap_near:                                                        # бирюзовая мантия мамы Искры на зелёном: вся
        k = 2 * int(trap_near) + 1                                       # ткань «похожа на зажатый фон» и шла пятнами —
        trap &= cv2.dilate(clear, np.ones((k, k), np.uint8)) > 0         # щели ищем только у края силуэта
    fix |= trap
    c = np.where(fix[..., None], c - t[..., None] * u, c)
    # островки (мусор фона) — прочь; тело, колёса и спицы связаны в крупные области
    on = (a > 0.15).astype(np.uint8)
    k, lab, st, _ = cv2.connectedComponentsWithStats(on, 8)
    small = np.zeros(k, bool)
    small[1:] = st[1:, cv2.CC_STAT_AREA] < 40
    a = np.where(small[lab], 0, a)
    return np.clip(c, 0, 255), a


def bleed(rgb, a):
    out = rgb.copy()
    pm = Image.fromarray(np.uint8(np.clip(rgb * a[..., None], 0, 255)))
    wa = Image.fromarray(np.uint8(a * 255))
    for r in (2, 6, 16, 40):
        bp = np.asarray(pm.filter(ImageFilter.GaussianBlur(r)), np.float32)
        bw = np.asarray(wa.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255
        m = (a < 0.03) & (bw > 0.02)                                     # только под прозрачным: у тонких спиц
                                                                         # (a < 0,5) свой цвет, не цвет обода
        out[m] = (bp / np.maximum(bw[..., None], 1e-3))[m]
    return out


# ---------- колесо ----------
def measure_wheel(alphas, rgbs, scale, given=None, amax=25):
    """Большое колесо: круг Хафа (самый «голосистый») по кадру на белом, уточнение центра ±8 px — где поворот
    кадр → кадр совпадает лучше всего; затем угол за каждый кадр (подбор ±25° через 0,5°)."""
    grays = []
    for r, a in zip(rgbs, alphas):
        g = cv2.cvtColor(np.uint8(np.clip(r, 0, 255)), cv2.COLOR_RGB2GRAY).astype(np.float32)
        grays.append(g * a + 255 * (1 - a))
    h = grays[0].shape[0]
    g0 = cv2.GaussianBlur(np.uint8(grays[0]), (5, 5), 0)
    cs = cv2.HoughCircles(g0, cv2.HOUGH_GRADIENT, 1.5, 30, param1=100, param2=45,
                          minRadius=int(h * 0.18), maxRadius=int(h * 0.32))
    if given:
        cx, cy, R = given
    elif cs is None:
        return None
    else:
        cx, cy, R = cs[0][0]
    yy, xx = np.mgrid[:h, :grays[0].shape[1]]

    def best_angle(A, B, cx, cy, angs):
        ring = (np.hypot(xx - cx, yy - cy) < R * 0.85) & (np.hypot(xx - cx, yy - cy) > R * 0.2)
        best = None
        for ang in angs:
            M = cv2.getRotationMatrix2D((float(cx), float(cy)), float(ang), 1.0)
            e = np.abs(cv2.warpAffine(A, M, (A.shape[1], A.shape[0])) - B)[ring].mean()
            if best is None or e < best[0]:
                best = (e, ang)
        return best

    coarse = np.arange(-amax, amax + 0.01, 2.5)
    cand = []
    for dx in range(-8, 9, 2):
        for dy in range(-8, 9, 2):
            e = sum(best_angle(grays[i], grays[i + 1], cx + dx, cy + dy, coarse)[0] for i in (0, len(grays) // 2))
            cand.append((e, dx, dy))
    _, dx, dy = min(cand)
    cx, cy = cx + dx, cy + dy
    steps, errs = [], []
    for i in range(len(grays)):
        e, ang = best_angle(grays[i], grays[(i + 1) % len(grays)], cx, cy, np.arange(-amax, amax + 0.01, 0.5))
        steps.append(-ang)                                               # cv2: + — против часовой; вправо — по часовой
        errs.append(e)
    floor = int(np.where(np.max(np.stack(alphas), 0).max(1) > 0.5)[0].max())
    return dict(cx=float(cx) / scale, cy=float(cy) / scale, r=float(R) / scale, floor=floor,
                deg_per_frame=[round(float(s), 1) for s in steps], match_err=round(float(np.mean(errs)), 1))


# ---------- листы ----------
def comp(rgb, a, color):
    return np.uint8(rgb * a[..., None] + np.array(color, np.float32) * (1 - a[..., None]))


def zoom(img, box, k=3):
    x0, y0, x1, y1 = box
    return cv2.resize(img[y0:y1, x0:x1], ((x1 - x0) * k, (y1 - y0) * k), interpolation=cv2.INTER_NEAREST)


def fit_h(img, h):
    return cv2.resize(img, (round(img.shape[1] * h / img.shape[0]), h), interpolation=cv2.INTER_AREA)


def hstack(ims, gap=6, color=(60, 60, 60)):
    h = max(i.shape[0] for i in ims)
    out = []
    for i in ims:
        if i.shape[0] < h:
            i = np.vstack([i, np.full((h - i.shape[0], i.shape[1], 3), color, np.uint8)])
        out += [i, np.full((h, gap, 3), color, np.uint8)]
    return np.hstack(out[:-1])


def vstack(ims, gap=6, color=(60, 60, 60)):
    w = max(i.shape[1] for i in ims)
    out = []
    for i in ims:
        if i.shape[1] < w:
            i = np.hstack([i, np.full((i.shape[0], w - i.shape[1], 3), color, np.uint8)])
        out += [i, np.full((gap, w, 3), color, np.uint8)]
    return np.vstack(out[:-1])


DARK, LIGHT, WARM = (24, 22, 28), (236, 236, 232), (120, 78, 44)


def key_sheet(rgbs, alphas, wheel, path):
    h, w = alphas[0].shape
    n = len(rgbs)
    z = max(60, h // 5)
    if wheel:                                                            # колесо со спицами — сектор у обода
        wx, wy, wr = int(wheel["cx"]), int(wheel["cy"]), wheel["r"]
        wb = (max(0, wx - int(wr * 0.9)), max(0, wy - z // 2), 0, 0)
    else:
        wb = (int(w * 0.1), int(h * 0.6), 0, 0)
    rows_t = np.where(alphas[0].max(1) > 0.5)[0]
    top = rows_t.min()
    cols = np.where(alphas[0][top + z // 2] > 0.5)[0]
    hx = int(cols.mean()) if len(cols) else w // 2
    boxes = {"колесо": (wb[0], wb[1], wb[0] + z, wb[1] + z),
             "волосы": (max(0, hx - z // 2), top, max(0, hx - z // 2) + z, top + z),
             "руки": (int(w * 0.35), int(h * 0.42), int(w * 0.35) + z, int(h * 0.42) + z)}
    rows = []
    for i in np.linspace(0, n - 1, 4).round().astype(int):
        rgb, a = rgbs[i], alphas[i]
        full = [fit_h(comp(rgb, a, c), 300) for c in (DARK, LIGHT, WARM)]
        zs = []
        for nm, bx in boxes.items():
            bx = (bx[0], bx[1], min(w, bx[2]), min(h, bx[3]))
            for c in (DARK, LIGHT) if nm != "руки" else (WARM,):
                zs.append(fit_h(zoom(comp(rgb, a, c), bx), 300))
        rows.append(hstack(full + zs))
    Image.fromarray(vstack(rows)).save(path)
    return boxes


def loop_sheet(rgbs, alphas, path):
    th = [fit_h(comp(r, a, LIGHT), 110) for r, a in zip(rgbs, alphas)]
    per = 12
    grid = vstack([hstack(th[i:i + per], 3) for i in range(0, len(th), per)], 3)
    seam = hstack([fit_h(comp(rgbs[-1], alphas[-1], LIGHT), 360), fit_h(comp(rgbs[0], alphas[0], LIGHT), 360),
                   fit_h(comp(rgbs[1], alphas[1], LIGHT), 360)], 10, (200, 40, 40))
    Image.fromarray(vstack([grid, seam], 14)).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("mp4")
    ap.add_argument("--key", choices=["green", "magenta"], default="green")
    ap.add_argument("--height", type=int, default=440)
    ap.add_argument("--lo", type=float, default=None, help="экранность (доля фона): ниже — непрозрачно")
    ap.add_argument("--hi", type=float, default=None, help="выше — прозрачно")
    ap.add_argument("--choke", type=float, default=0.15, help="поджатие кромки: a' = (a − choke)/(1 − choke)")
    ap.add_argument("--len", type=int, default=0)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--lmin", type=int, default=18)
    ap.add_argument("--lmax", type=int, default=72)
    ap.add_argument("--fade", type=int, default=0, help="кроссфейд на шве, кадров (0 — без)")
    ap.add_argument("--step", type=int, default=1, help="2 — проредить 24 → 12 к/с")
    ap.add_argument("--wheel", default="", help="cx,cy,r колеса в кадре петли (если круг Хафа ошибся)")
    ap.add_argument("--amax", type=float, default=25, help="поиск поворота колеса за кадр, ± градусов")
    ap.add_argument("--margin", type=int, default=6)
    ap.add_argument("--thin", type=float, default=0, help="сохранять тонкие светлые детали: порог «светлее фона» (14)")
    ap.add_argument("--trap-near", type=int, default=0, help="чистить «зажатый фон» только в N px от края (Искра: 12)")
    ap.add_argument("--stab", action="store_true", help="снять плавный дрейф героя по горизонтали (Тилли)")
    ap.add_argument("--out", default=os.path.join(ROOT, "assets", "anim"))
    args = ap.parse_args()
    lo = args.lo if args.lo is not None else 0.2
    hi = args.hi if args.hi is not None else 0.85

    fr = read_frames(args.mp4)
    bgs = [bg_color(f) for f in fr]
    if args.stab:
        fr, drift, resid = stabilize(fr, bgs, args.key)
        print(f"{args.name}: выравнивание — дрейф {drift:.0f} px снят, остаток края ±{resid:.1f} px")
    keep, src_fps = dedup(fr, bgs)
    if len(keep) < len(fr):
        src_fps = round(src_fps)
        print(f"{args.name}: повторы кадров — оставлено {len(keep)} из {len(fr)}, исходник {src_fps} к/с")
        fr, bgs = fr[keep], [bgs[i] for i in keep]
        args.lmin, args.lmax = round(args.lmin * src_fps / 24), round(args.lmax * src_fps / 24)
    best, ma, D = pick_loop(fr, bgs, args.lmin, args.lmax, args.step)
    c, L, s, seam, speed = best
    if args.len:
        L, s = args.len, args.start or s
        seam = D[s, s + L] / ma if s + L < len(fr) else float("nan")
    idx = list(range(s, s + L, args.step))
    print(f"{args.name}: петля кадры {s}..{s + L - 1} ({L} кадров, {L / src_fps:.2f} с), шов {seam:.2f}·шага, "
          f"скорость {speed:.2f}, фон кадра {s}: {bgs[s].round().astype(int).tolist()}")

    rgbs, alphas = [], []
    for i in idx:
        rgb, a = key_frame(fr[i], bgs[i], args.key, lo, hi, args.choke, args.thin, args.trap_near)
        rgbs.append(rgb)
        alphas.append(a)
    if args.fade and len(idx) > 2 * args.fade and args.step == 1:                           # шов: последние кадры плавно в кадры до начала
        for k in range(args.fade):
            j = s - args.fade + k                                        # кадр, который шёл бы перед первым
            if j < 1:
                break
            rp, ap_ = key_frame(fr[j], bgs[j], args.key, lo, hi, args.choke, args.thin, args.trap_near)
            t = (k + 1) / (args.fade + 1)
            p = len(idx) - args.fade + k
            rgbs[p] = rgbs[p] * (1 - t) + rp * t
            alphas[p] = alphas[p] * (1 - t) + ap_ * t
    on = np.max(np.stack(alphas), 0) > 0.05
    ys, xs = np.where(on)
    H, W = on.shape
    m = args.margin
    x0, x1, y0, y1 = max(0, xs.min() - m), min(W, xs.max() + 1 + m), max(0, ys.min() - m), min(H, ys.max() + 1 + m)
    k = args.height / (y1 - y0)
    size = (round((x1 - x0) * k), args.height)
    out = os.path.join(args.out, f"ride_{args.name}")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    o_rgb, o_a = [], []
    for n, (rgb, a) in enumerate(zip(rgbs, alphas)):
        # масштаб с умножением на альфу: иначе цвет фона под прозрачными пикселями подмешивается к кромке
        ac = a[y0:y1, x0:x1].astype(np.float32)
        pm = cv2.resize(rgb[y0:y1, x0:x1] * ac[..., None], size, interpolation=cv2.INTER_AREA)
        a2 = np.clip(cv2.resize(ac, size, interpolation=cv2.INTER_AREA), 0, 1)
        r2 = np.clip(pm / np.maximum(a2, 1e-4)[..., None], 0, 255) * (a2 > 1e-4)[..., None]
        r2 = bleed(r2, a2)
        Image.fromarray(np.uint8(np.clip(r2, 0, 255))).save(os.path.join(out, f"{n:02d}.jpg"), "JPEG", quality=90,
                                                             optimize=True)
        mask = Image.new("RGBA", size, (255, 255, 255, 0))
        mask.putalpha(Image.fromarray(np.uint8(np.round(a2 * 255))))
        mask.save(os.path.join(out, f"{n:02d}.a.png"), "PNG", optimize=True)
        o_rgb.append(r2)
        o_a.append(a2)
    wheel = measure_wheel(o_a, o_rgb, 1.0, [float(v) for v in args.wheel.split(",")] if args.wheel else None,
                          args.amax)
    edge = [float(np.abs(o_a[i + 1] - o_a[i]).mean()) for i in range(len(o_a) - 1)]
    shots = os.path.join(ROOT, "art_tests", "ride_shots")
    os.makedirs(shots, exist_ok=True)
    key_sheet(o_rgb, o_a, wheel, os.path.join(shots, f"{args.name}_key.png"))
    loop_sheet(o_rgb, o_a, os.path.join(shots, f"{args.name}_loop.png"))
    kb = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)) / 1024
    floor = int(np.where(np.max(np.stack(o_a), 0).max(1) > 0.5)[0].max())
    info = dict(name=args.name, src=os.path.relpath(args.mp4, ROOT).replace("\\", "/"), key=args.key, lo=lo, hi=hi,
                start=s, len=L, step=args.step, fade=args.fade, frames=len(o_a), fps=round(src_fps / args.step, 2),
                size=list(size), floor_y=floor, kb=round(kb), crop=[int(x0), int(y0), int(x1), int(y1)],
                bg=bgs[s].round().astype(int).tolist(), alpha_flicker=round(float(np.mean(edge)), 4), wheel=wheel)
    if wheel:
        dpf = np.mean(wheel["deg_per_frame"])
        info["wheel"]["mean_deg_per_frame"] = round(float(dpf), 2)
        rr = wheel["floor"] - wheel["cy"]                                # радиус по шине: центр → пол
        info["wheel"]["tire_r"] = round(float(rr), 1)
        info["wheel"]["px_per_sec"] = round(float(np.pi * 2 * rr * dpf * info["fps"] / 360), 1)
        info["wheel"]["roll"] = round(float(np.pi * 2 * rr * dpf * info["fps"] / 360) / size[1], 4)  # высот кадра/с
    print(json.dumps(info, ensure_ascii=False))
    with open(os.path.join(shots, f"{args.name}_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
