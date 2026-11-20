# -*- coding: utf-8 -*-
"""Стык «живых» слоёв героя: картинка ↔ спокойная петля ↔ «волшебство» — сдвиг в пикселях экрана.

Замечание владельца 20.11: «небольшой пиксельный сдвиг между Мартином, который выпускает светлячка, и Мартином,
который просто двигается». Инструмент берёт у игры слои по отдельности (без фона, на прозрачном холсте — теми же
функциями, которыми их рисует игра) и меряет по альфе нижней половины силуэта (коляска
неподвижна) сдвиг каждой пары (фазовая корреляция, уточнение ECC). Места:
  job     — портрет задания flat (Мартин): картинка («Без анимации»), петля martin_idle кадр 0, волшебство кадр 0;
  result  — итог того же задания (бокс 210×250): то же;
  ride    — портрет у коляски после проезда (230×250): картинка ↔ петля;
  brenna  — Бренна в Гильдии (master.png ↔ brenna_wave кадр 0; не по умолчанию — см. --places);
  forest, party — Мартин во вступлении и на празднике (martin.png ↔ martin_forest / martin_party кадр 0).

  python art_tests/loop_shift.py [--rs 1,1.25,1.5,2,3] [--places job,result,...] [--out папка] [--root корень]
                                 [--web] [--part low|all|top] [--lim-lm 0.35] [--lim-pic 1.0]
--web — кадры, ужатые для браузера (build_web.shrink_anim); --root — другая рабочая копия (сравнить «было»).
--out — сохранить слои (PNG) и увеличенные ×4 стыки «петля | волшебство» (кадр 0 рядом). Код возврата 1, если
сдвиг «петля ↔ волшебство» больше --lim-lm или «петля/волшебство ↔ картинка» больше --lim-pic по любой оси."""
import argparse
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--rs", default="1,1.25,1.5,2,3")
ap.add_argument("--places", default="job,result,ride,forest,party",
                help="через запятую: job, result, ride, forest, party, brenna (Бренна — не по умолчанию: её кадр 0 "
                     "парит на 1–2,5 логических px выше картинки — так нарезана петля, постановка тут ни при чём)")
ap.add_argument("--out", default="")
ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--lim-lm", type=float, default=0.35)
ap.add_argument("--lim-pic", type=float, default=0.5)
ap.add_argument("--web", action="store_true",
                help="кадры петель и волшебства — ужатые, как в браузерном пакете (build_web.shrink_anim, 400 px, маска 200)")
ap.add_argument("--part", default="low", choices=("low", "all", "top"),
                help="по какой части силуэта мерить: нижняя половина (коляска — по умолчанию), весь, верхняя")
args = ap.parse_args()

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, args.root)
os.chdir(args.root)
import numpy as np   # noqa: E402
import cv2           # noqa: E402
import pygame        # noqa: E402

pygame.init()
pygame.display.set_mode((1280, 720))
import game          # noqa: E402

JOB = "flat"


def use_web_frames():
    """Подменить кадры петель/волшебства на ужатые build_web.shrink_anim (во временной папке)."""
    import tempfile
    sys.path.insert(0, args.root)
    import build_web
    tmp = tempfile.mkdtemp(prefix="loop_shift_web_")
    names = set(game.IDLE_LOOPS.values()) | {n for _, n in game.SCENE_LOOPS.values()} | {"magic_martin"}
    for name in names:
        src = os.path.join(game.ASSETS_DIR, "anim", name)
        if not os.path.isdir(src):
            continue
        os.makedirs(os.path.join(tmp, "anim", name))
        for f in os.listdir(src):
            if f.endswith((".jpg", ".a.png")):
                build_web.shrink_anim(os.path.join(src, f), os.path.join(tmp, "anim", name, f))
    orig = game.asset_path

    def asset_path(name):
        parts = name.replace("\\", "/").split("/")
        if len(parts) == 3 and parts[0] == "anim" and parts[1] in names:
            p = os.path.join(tmp, "anim", parts[1], parts[2])
            if os.path.exists(p[:-4] + ".jpg"):
                return p[:-4] + ".jpg"
        return orig(name)
    game.asset_path = asset_path
    print("кадры браузера:", tmp)


def raw(s):
    """Surf (логический размер) -> обычная поверхность в пикселях экрана (surfarray смотрит на get_size)."""
    if not isinstance(s, game.Surf):
        return s
    out = pygame.Surface(pygame.Surface.get_size(s), pygame.SRCALPHA)
    out.fill((0, 0, 0, 0))
    pygame.Surface.blit(out, s, (0, 0), None, pygame.BLEND_RGBA_MAX)
    return out


def alpha_of(s):
    s = raw(s)
    return pygame.surfarray.array_alpha(s).swapaxes(0, 1).astype(np.float32) / 255


def rgba_of(s):
    s = raw(s)
    c = pygame.surfarray.array3d(s).swapaxes(0, 1)
    return np.dstack([c, pygame.surfarray.array_alpha(s).swapaxes(0, 1)])


def canvas():
    s = game.Surf((game.WIDTH, game.HEIGHT), pygame.SRCALPHA)
    pygame.Surface.fill(s, (0, 0, 0, 0))
    return s


def set_rs(rs):
    game.RS = rs
    for c in (game._img_cache, game._anim_cache, game._AA_CACHE, game._glow_cache):
        c.clear()
    game._MAGIC_IDX.pop("size", None)
    for k in [k for k in vars(game) if k.startswith("_FIT")]:
        v = getattr(game, k)
        if isinstance(v, dict):
            v.clear()


def portrait_layers(g, box, magic):
    """Слои портрета героя задания в боксе box: картинка, петля кадр 0, волшебство кадр 0 (как рисует игра)."""
    L = {}
    game.A11Y["calm"] = True
    s = canvas()
    g._blit_portrait(s, box)
    L["картинка"] = s
    game.A11Y["calm"] = False
    s = canvas()
    g._blit_portrait(s, box, 1e-4)
    if g._portrait_drawn:
        L["петля"] = s
    if magic:
        name = g._magic_hero()
        if hasattr(g, "_magic_place"):
            key, x, y = g._magic_place(name, box)
        else:                                                    # код до 20.11 (сравнение «было»)
            key, x, y = g._magic_layout(name, box)
        img = game.anim_frame(name, key, 1e-4, magic_fps(name))
        s = canvas()
        pygame.Surface.blit(s, img, (x, y))
        L["волшебство"] = s
    return L


def magic_fps(name):
    return float(game.magic_index()[name]["fps"])


def hero_layers(art, box, loop):
    L = {}
    for calm, key in ((True, "картинка"), (False, "петля")):
        game.A11Y["calm"] = calm
        s = canvas()
        game.blit_hero(s, art, box, 0.0, loop=loop)
        L[key] = s
    return L


def shift(a, b, cut):
    """Сдвиг b относительно a (px экрана) по нижней части силуэта (строки ниже cut; --part)."""
    A, B = alpha_of(a), alpha_of(b)
    if args.part == "low":
        A[:cut] = 0
        B[:cut] = 0
    elif args.part == "top":
        A[cut:] = 0
        B[cut:] = 0
    ys, xs = np.where((A > 0.05) | (B > 0.05))
    if not len(xs):
        return float("nan"), float("nan")
    x0, x1, y0, y1 = max(0, xs.min() - 16), xs.max() + 16, max(0, ys.min() - 16), ys.max() + 16
    A, B = A[y0:y1, x0:x1], B[y0:y1, x0:x1]
    win = cv2.createHanningWindow(A.shape[::-1], cv2.CV_32F)
    (dx, dy), _ = cv2.phaseCorrelate(A, B, win)        # грубо, потом точно — ECC (сдвиг) по размытой альфе
    W = np.float32([[1, 0, dx], [0, 1, dy]])
    try:
        _, W = cv2.findTransformECC(cv2.GaussianBlur(A, (0, 0), 1.0), cv2.GaussianBlur(B, (0, 0), 1.0), W,
                                    cv2.MOTION_TRANSLATION,
                                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 1)
    except cv2.error:
        pass
    return float(W[0, 2]), float(W[1, 2])


def main():
    if args.web:
        use_web_frames()
    rss = [float(v) for v in args.rs.split(",")]
    places = args.places.split(",")
    rows, bad = [], []
    if args.out:
        os.makedirs(args.out, exist_ok=True)
    for rs in rss:
        set_rs(rs)
        g = game.Game(headless=True)
        g.no_save = True
        g.start_job(JOB)
        for place in places:
            if place == "job":
                L = portrait_layers(g, g.PORTRAIT_BOX, True)
            elif place == "result":
                L = portrait_layers(g, g.RESULT_BOX, True)
            elif place == "ride":
                cr = g._chair_rect()
                L = portrait_layers(g, (cr.centerx - 115, cr.centery - 125, 230, 250), False)
            elif place == "brenna":
                L = hero_layers("master.png", (game.WIDTH - 300, 130, 200, 280), None)
            elif place in ("forest", "party"):
                sc = "intro" if place == "forest" else "ending"
                L = hero_layers("martin.png", game.SCENE_LOOP_BOX[sc], game.SCENE_LOOPS[sc][1])
            else:
                print("неизвестное место", place)
                continue
            pa = alpha_of(L["картинка"])
            ys = np.where(pa.max(1) > 0.5)[0]
            cut = (ys.min() + ys.max()) // 2 if len(ys) else 0
            pairs = [("петля", "волшебство"), ("картинка", "петля"), ("картинка", "волшебство")]
            res = {}
            for a, b in pairs:
                if a in L and b in L:
                    res[(a, b)] = shift(L[a], L[b], cut)
                    dx, dy = res[(a, b)]
                    lim = args.lim_lm if (a, b) == ("петля", "волшебство") else args.lim_pic
                    if max(abs(dx), abs(dy)) > lim:
                        bad.append(f"×{rs:g} {place}: {a} → {b} dx {dx:+.2f} dy {dy:+.2f} (> {lim})")
            rows.append((rs, place, res))
            if args.out:
                tag = f"rs{rs:g}_{place}"
                for k, s in L.items():
                    cv2.imwrite(os.path.join(args.out, f"{tag}_{k}.png"),
                                cv2.cvtColor(np.uint8(rgba_of(s)), cv2.COLOR_RGBA2BGRA))
                b = "волшебство" if "волшебство" in L else "картинка"
                if "петля" in L:                             # стык ×4: петля | второй слой, по нижней части
                    A = rgba_of(L["петля"])
                    ys2, xs2 = np.where(A[..., 3] > 10)
                    y0, y1 = (ys2.min() + ys2.max()) // 2, ys2.max() + 4
                    x0, x1 = xs2.min() - 4, xs2.max() + 4
                    tiles = []
                    for k in ("петля", b):
                        t = rgba_of(L[k])[y0:y1, x0:x1].astype(np.float32)
                        rgb = t[..., :3] * (t[..., 3:] / 255) + 40 * (1 - t[..., 3:] / 255)
                        tiles.append(cv2.resize(np.uint8(rgb), None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
                    both = np.hstack([tiles[0], np.full((tiles[0].shape[0], 8, 3), 255, np.uint8), tiles[1]])
                    cv2.imwrite(os.path.join(args.out, f"seam_x4_{tag}_loop_vs_{'magic' if b == 'волшебство' else 'pic'}.png"),
                                cv2.cvtColor(both, cv2.COLOR_RGB2BGR))
    print()
    print(f"{'RS':>5} {'место':<7} {'петля→волшебство':>18} {'картинка→петля':>18} {'картинка→волшебство':>20}")
    for rs, place, res in rows:
        def f(k):
            if k not in res:
                return "—"
            dx, dy = res[k]
            return f"{dx:+.2f} {dy:+.2f}"
        print(f"{rs:>5g} {place:<7} {f(('петля', 'волшебство')):>18} {f(('картинка', 'петля')):>18} "
              f"{f(('картинка', 'волшебство')):>20}")
    print()
    if bad:
        print("LOOP SHIFT: FAIL")
        for b in bad:
            print("  " + b)
        return 1
    print(f"LOOP SHIFT OK: {len(rows)} мест, петля↔волшебство ≤ {args.lim_lm}, ↔картинка ≤ {args.lim_pic} px экрана")
    return 0


if __name__ == "__main__":
    sys.exit(main())
