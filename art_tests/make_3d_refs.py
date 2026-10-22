"""Референсы всех колясок игры для 3D-генератора (Tripo) -> art_tests/focus_ref/.
Для каждой коляски из заданий — рисунок коляски из игры на белом фоне, имя файла = модель коляски
(<NN>_<модель>__<рисунок>.png); у фольклорных колясок — ещё готовые «for_3d» из art_tests/export/.
python art_tests/make_3d_refs.py"""
import os, re, sys, glob, shutil
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
import pygame
pygame.init()
pygame.display.set_mode((64, 64))
import game
from PIL import Image

OUT = os.path.join(HERE, "focus_ref")
os.makedirs(OUT, exist_ok=True)
game.set_lang("en")


def slug(s):
    s = re.sub(r"\(.*?\)", "", s)
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:60]


seen = {}
for job in game.ALL_JOBS:
    art = job.get("chair_art")
    if not art or art in seen:
        continue
    src = os.path.join(game.ASSETS_DIR, art)
    if not os.path.exists(src):
        continue
    name = game.tr(job.get("chair_name") or art)
    seen[art] = name
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    pad = int(max(im.size) * 0.08)                         # поля: генератору нужен объект целиком, не впритык
    out = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), "white")
    out.paste(bg.convert("RGB"), (pad, pad))
    fn = f"{len(seen):02d}_{slug(name)}__{os.path.splitext(art)[0]}.png"
    out.save(os.path.join(OUT, fn))
    print(fn, "—", name)
for f in glob.glob(os.path.join(HERE, "export", "wheels_and_bones_folk_chairs", "*", "reference", "for_3d__*.png")):
    if "wolturnus" in f:                                   # прототип Жар-птицы — не Nitrum, путает
        continue
    shutil.copy(f, os.path.join(OUT, "folk_" + os.path.basename(f)))
    print("folk_" + os.path.basename(f))
print(len(seen), "колясок ->", OUT)
