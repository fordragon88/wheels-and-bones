# -*- coding: utf-8 -*-
"""Стык «живых» слоёв героя в Godot: картинка ↔ спокойная петля ↔ «волшебство», сдвиг в пикселях экрана.

Как art_tests/loop_shift.py pygame-версии (замечание владельца 20.11: Мартин «прыгает» на стыке петли и волшебства).
Запускает Godot с окном (звук Dummy) — tests/loop_shift.gd рисует каждый слой отдельно на прозрачном холсте при окне
1280×720, 1920×1080 и телефонном 2340×1080 (×1,5 с полосами по бокам), прежним расчётом (old) и нынешним (new), —
и меряет сдвиг по альфе нижней половины силуэта (коляска неподвижна): фазовая корреляция, уточнение ECC.
  python godot/tools/loop_shift.py [--out папка] [--keep] [--lim-lm 0.25] [--lim-pic 0.5]
Код возврата 1, если по нынешнему расчёту «петля ↔ волшебство» > --lim-lm или «петля/волшебство ↔ картинка» >
--lim-pic по любой оси (Бренна не в счёт: её кадр 0 парит выше картинки — так нарезана петля)."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
GODOT = os.environ.get("GODOT", r"D:\Godot\Godot_v4.7.2-stable_win64_console.exe")
SIZES = ("1280x720", "1920x1080", "2340x1080")
PLACES = ("job", "result", "ride", "forest", "party", "brenna")


def load_alpha(fp):
    if not os.path.exists(fp):
        return None
    im = cv2.imread(fp, cv2.IMREAD_UNCHANGED)
    return None if im is None else im[..., 3].astype(np.float32) / 255


def shift(A, B, cut):
    A, B = A.copy(), B.copy()
    A[:cut] = 0
    B[:cut] = 0
    ys, xs = np.where((A > 0.05) | (B > 0.05))
    x0, x1, y0, y1 = max(0, xs.min() - 16), xs.max() + 16, max(0, ys.min() - 16), ys.max() + 16
    A, B = A[y0:y1, x0:x1], B[y0:y1, x0:x1]
    (dx, dy), _ = cv2.phaseCorrelate(A, B, cv2.createHanningWindow(A.shape[::-1], cv2.CV_32F))
    W = np.float32([[1, 0, dx], [0, 1, dy]])
    try:
        _, W = cv2.findTransformECC(cv2.GaussianBlur(A, (0, 0), 1.0), cv2.GaussianBlur(B, (0, 0), 1.0), W,
                                    cv2.MOTION_TRANSLATION, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6),
                                    None, 1)
    except cv2.error:
        pass
    return float(W[0, 2]), float(W[1, 2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--keep", action="store_true", help="не удалять PNG слоёв")
    ap.add_argument("--lim-lm", type=float, default=0.25)
    ap.add_argument("--lim-pic", type=float, default=0.5)
    args = ap.parse_args()
    out = args.out or tempfile.mkdtemp(prefix="godot_loop_shift_")
    os.makedirs(out, exist_ok=True)
    r = subprocess.run([GODOT, "--audio-driver", "Dummy", "--path", PROJ, "-s", "res://tests/loop_shift.gd", "--",
                        os.path.abspath(out)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=600)
    if "LOOP SHIFT LAYERS" not in r.stdout:
        print(r.stdout[-3000:], r.stderr[-3000:])
        print("LOOP SHIFT: Godot не нарисовал слои")
        return 2
    rows, bad = [], []
    for sz in SIZES:
        for pl in PLACES:
            L = {k: load_alpha(os.path.join(out, f"{sz}_{pl}_{k}.png"))
                 for k in ("pic", "loop_old", "loop_new", "magic_old", "magic_new")}
            if L["pic"] is None:
                continue
            ys = np.where(L["pic"].max(1) > 0.5)[0]
            cut = (ys.min() + ys.max()) // 2
            res = {}
            for ver in ("old", "new"):
                for a, b, lim in (("loop_" + ver, "magic_" + ver, args.lim_lm), ("pic", "loop_" + ver, args.lim_pic),
                                  ("pic", "magic_" + ver, args.lim_pic)):
                    if L[a] is None or L[b] is None:
                        continue
                    d = shift(L[a], L[b], cut)
                    res[(a, b)] = d
                    if ver == "new" and pl != "brenna" and max(abs(d[0]), abs(d[1])) > lim:
                        bad.append(f"{sz} {pl}: {a} → {b} dx {d[0]:+.2f} dy {d[1]:+.2f} (> {lim})")
            rows.append((sz, pl, res))
    f = lambda res, k: (f"{res[k][0]:+.2f} {res[k][1]:+.2f}" if k in res else "—")   # noqa: E731
    print(f"{'окно':<10} {'место':<7} | {'петля→волш. было':>16} {'стало':>12} | {'карт.→петля было':>16} "
          f"{'стало':>12} | {'карт.→волш. было':>16} {'стало':>12}")
    for sz, pl, res in rows:
        print(f"{sz:<10} {pl:<7} | {f(res, ('loop_old', 'magic_old')):>16} {f(res, ('loop_new', 'magic_new')):>12} | "
              f"{f(res, ('pic', 'loop_old')):>16} {f(res, ('pic', 'loop_new')):>12} | "
              f"{f(res, ('pic', 'magic_old')):>16} {f(res, ('pic', 'magic_new')):>12}")
    if not args.keep and not args.out:
        shutil.rmtree(out, ignore_errors=True)
    if bad:
        print("LOOP SHIFT: FAIL")
        for b in bad:
            print("  " + b)
        return 1
    print(f"LOOP SHIFT OK: петля↔волшебство ≤ {args.lim_lm}, ↔картинка ≤ {args.lim_pic} px экрана")
    return 0


if __name__ == "__main__":
    sys.exit(main())
