# -*- coding: utf-8 -*-
"""Петля «наставник живёт на месте» (assets/anim/<имя>/NN.jpg + NN.a.png) из клипа MiniMax H3 — как машущий Барти.

  python art_tests/idle_loop.py brenna_wave <mp4> --art master.png [--pad 0.08] [--lmin 60 --lmax 80] [--step 2]

Клип делает tools/trailer/make_idle_prompts.py: картинка наставника (assets/<art>) высотой 700 по центру листа
1536×1024 на ровном зелёном, H3 рисует 960×640. Отличие от проезда (ride_loop.py): кадр НЕ обрезается по силуэту —
холст петли = холст картинки, раздвинутый на --pad с каждой стороны (доля ширины/высоты). Тогда первый кадр петли
совпадает со статичной картинкой пиксель в пиксель, и игра рисует петлю в прямоугольнике (1+2·pad) от прямоугольника
картинки с тем же центром: при «Без анимации» наставник стоит ровно там же. Поле нужно: призрак покачивается и
колышет подол, а у master.png рисунок касается краёв своего холста.
Ключ, поиск шва и листы проверки — из ride_loop.py.
"""
import argparse, json, os, shutil, sys
import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ride_loop as R

ROOT = R.ROOT
SHEET, PIC_H = (1536, 1024), 700          # раскладка make_idle_prompts.py


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("mp4")
    ap.add_argument("--art", required=True, help="картинка в assets/, с которой сделан клип")
    ap.add_argument("--pad", type=float, default=0.08)
    ap.add_argument("--height", type=int, default=512, help="высота кадра петли (с полями)")
    ap.add_argument("--lmin", type=int, default=60)
    ap.add_argument("--lmax", type=int, default=80)
    ap.add_argument("--len", type=int, default=0)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--lo", type=float, default=0.2)
    ap.add_argument("--hi", type=float, default=0.85)
    ap.add_argument("--choke", type=float, default=0.15)
    ap.add_argument("--thin", type=float, default=0)
    ap.add_argument("--hole", default="", help="x0,dy0,x1,dy1 в кадре петли (dy — от макушки силуэта): «зажатый» фон в "
                                               "просвете (очки Бренны) — бирюзовое (G − R > 30) там закрашивается по соседям")
    ap.add_argument("--no-tone", action="store_true", help="не подгонять тон под исходную картинку")
    ap.add_argument("--key", default="green", choices=["green", "magenta"],
                    help="цвет фона клипа: magenta — где зелёное в герое (Мартин; make_martin_idle.py)")
    ap.add_argument("--art-file", default="", help="картинка для сверки и тона, если она ещё не в assets/")
    args = ap.parse_args()

    art = Image.open(args.art_file or os.path.join(ROOT, "assets", args.art)).convert("RGBA")
    fr = R.read_frames(args.mp4)
    bgs = [R.bg_color(f) for f in fr]
    Hc, Wc = fr[0].shape[:2]
    k = Wc / SHEET[0]                                                   # лист → клип
    pw = round(art.width * PIC_H / art.height)
    cw, ch = pw * k, PIC_H * k                                          # холст картинки в клипе
    cx0, cy0 = (SHEET[0] - pw) / 2 * k, (SHEET[1] - PIC_H) / 2 * k
    p = args.pad
    oh = args.height
    ow = round(oh * art.width / art.height)
    sx, sy = cw * (1 + 2 * p) / ow, ch * (1 + 2 * p) / oh               # кадр петли → клип
    M = np.float32([[sx, 0, cx0 - p * cw], [0, sy, cy0 - p * ch]])

    best, ma, D = R.pick_loop(fr, bgs, args.lmin, args.lmax, args.step)
    c, L, s, seam, speed = best
    if args.len:
        L, s = args.len, args.start or s
        seam = D[s, s + L] / ma if s + L < len(fr) else float("nan")
    idx = list(range(s, s + L, args.step))
    print(f"{args.name}: петля кадры {s}..{s + L - 1} ({L} кадров, {L / 24:.2f} с), шов {seam:.2f}·шага, "
          f"скорость {speed:.2f}, фон {bgs[s].round().astype(int).tolist()}")

    def warp(i):
        rgb, a = R.key_frame(fr[i], bgs[i], args.key, args.lo, args.hi, args.choke, args.thin)
        a = a.astype(np.float32)
        fl = cv2.WARP_INVERSE_MAP | cv2.INTER_LINEAR
        pm = cv2.warpAffine(rgb.astype(np.float32) * a[..., None], M, (ow, oh), flags=fl)
        a2 = np.clip(cv2.warpAffine(a, M, (ow, oh), flags=fl), 0, 1)
        r2 = np.clip(pm / np.maximum(a2, 1e-4)[..., None], 0, 255) * (a2 > 1e-4)[..., None]
        holed = 0
        if args.hole:                                                   # просвет между оправой и лицом: в картинке он
            x0, d0, x1, d1 = [int(v) for v in args.hole.split(",")]     # прозрачный, H3 рисует там «стекло» цвета фона
            top = int(np.where((a2 > 0.5).max(1))[0].min())
            m = np.zeros(a2.shape, np.uint8)
            win = (slice(top + d0, top + d1), slice(x0, x1))
            m[win] = ((r2[win][..., 1] - r2[win][..., 0] > 30) & (a2[win] > 0.15))
            holed = int(m.sum())
            # вырезать нельзя — в лице видна дырка (проба 19.11); закрашиваем по соседям: стекло как стекло
            m = cv2.dilate(m, np.ones((3, 3), np.uint8))
            r2 = cv2.inpaint(np.uint8(np.clip(r2, 0, 255)), m, 4, cv2.INPAINT_TELEA).astype(np.float32)
        return r2, a2, holed

    # тон: H3 чуть темнит и глушит цвет — усиление по каналам, чтобы поза картинки (кадр клипа №1) совпала с ней
    art_c = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
    iw, ih = round(ow / (1 + 2 * p)), round(oh / (1 + 2 * p))
    art_c.paste(art.resize((iw, ih), Image.LANCZOS), ((ow - iw) // 2, (oh - ih) // 2))
    art_n = np.asarray(art_c).astype(np.float32)
    r1, a1f, _ = warp(1)
    both = (a1f > 0.98) & (art_n[..., 3] > 250)
    both = cv2.erode(both.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0   # без кромок: там позы расходятся на пиксель
    gain = np.ones(3, np.float32) if args.no_tone else art_n[..., :3][both].mean(0) / r1[both].mean(0)
    print(f"{args.name}: тон — усиление по каналам {gain.round(3).tolist()} (по {int(both.sum())} пикселям)")

    out = os.path.join(ROOT, "assets", "anim", args.name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    o_rgb, o_a, edge_hit, holes = [], [], 0.0, []
    for n, i in enumerate(idx):
        r2, a2, holed = warp(i)
        holes.append(holed)
        r2 = np.clip(r2 * gain, 0, 255) * (a2 > 1e-4)[..., None]
        r2 = R.bleed(r2, a2)
        edge_hit = max(edge_hit, float(max(a2[0].max(), a2[-1].max(), a2[:, 0].max(), a2[:, -1].max())))
        Image.fromarray(np.uint8(np.clip(r2, 0, 255))).save(os.path.join(out, f"{n:02d}.jpg"), "JPEG", quality=90,
                                                             optimize=True)
        mask = Image.new("RGBA", (ow, oh), (255, 255, 255, 0))
        mask.putalpha(Image.fromarray(np.uint8(np.round(a2 * 255))))
        mask.save(os.path.join(out, f"{n:02d}.a.png"), "PNG", optimize=True)
        o_rgb.append(r2)
        o_a.append(a2)

    # сверка с картинкой: кадр клипа №1 (поза картинки) в том же холсте против альфы самой картинки
    a1 = a1f > 0.5
    ra = art_n[..., 3] > 127
    if args.hole:
        print(f"{args.name}: просвет — закрашено пикселей за кадр {min(holes)}…{max(holes)}")
    iou = float((a1 & ra).sum() / max(1, (a1 | ra).sum()))

    def box(m):
        ys, xs = np.where(m)
        return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    allb = box(np.max(np.stack(o_a), 0) > 0.05)
    print(f"{args.name}: кадр {ow}×{oh}, поле {p:.2f}; совпадение позы с {args.art}: IoU {iou:.3f} "
          f"(картинка {box(ra)}, кадр 1 {box(a1)}); силуэт за всю петлю {allb}; у края кадра альфа до {edge_hit:.2f}")
    shots = os.path.join(ROOT, "art_tests", "ride_shots")
    os.makedirs(shots, exist_ok=True)
    R.key_sheet(o_rgb, o_a, None, os.path.join(shots, f"{args.name}_key.png"))
    R.loop_sheet(o_rgb, o_a, os.path.join(shots, f"{args.name}_loop.png"))
    kb = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)) / 1024
    flick = [float(np.abs(o_a[i + 1] - o_a[i]).mean()) for i in range(len(o_a) - 1)]
    info = dict(name=args.name, art=args.art, src=os.path.relpath(args.mp4, ROOT).replace("\\", "/"), pad=p, start=s, len=L,
                step=args.step, frames=len(o_a), fps=24 / args.step, size=[ow, oh], kb=round(kb), iou=round(iou, 3),
                seam=round(float(seam), 2), bbox=allb, edge_alpha=round(edge_hit, 2),
                alpha_flicker=round(float(np.mean(flick)), 4))
    json.dump(info, open(os.path.join(shots, f"{args.name}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{args.name}: {len(o_a)} кадров, {kb:.0f} КБ -> {out}")


if __name__ == "__main__":
    main()
