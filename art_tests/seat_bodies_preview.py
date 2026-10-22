"""Тело клиента в сцене Кабинета посадки в 4 позах (как в игре): python art_tests/seat_bodies_preview.py <папка с
seat_bodies.json и частями> <out.png> [id=seat_troll]. Части берутся из папки, а не из assets (можно смотреть до вставки)."""
import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pygame
pygame.init()
pygame.display.set_mode((1280, 720))
import game
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
cid = next((a.split("=", 1)[1] for a in sys.argv[3:] if a.startswith("id=")), "seat_troll")
game.FEEDBACK_URL = ""
game.Game._SEAT_RIGS = json.load(open(os.path.join(src, "seat_bodies.json"), encoding="utf-8"))
_ap = game.asset_path
game.asset_path = lambda f: os.path.join(src, f) if os.path.exists(os.path.join(src, f)) else _ap(f)
game.Game.SEAT_BODY_ON = True
g = game.Game(headless=True)
case = next(c for c in game.SEAT_CASES if c["id"] == cid)
base = dict(depth=45, leg=44, back_h=45, back_a=100, tilt=0)
poses = [("neutral", base), ("slump", dict(base, depth=52, back_a=90, back_h=38)), ("knees up", dict(base, leg=38)),
         ("feet dangle", dict(base, leg=54)), ("tilt 45°", dict(base, tilt=45))]
tiles = []
for name, cfg in poses:
    checks, pose = g.seat_eval(case, cfg)
    s = game.Surf((560, 560))
    pygame.Surface.fill(s, (236, 232, 224))
    g._draw_seat_scene(s, pygame.Rect(20, 20, 520, 520), case, cfg, pose, highlight=False, show_necro=False, show_body=True)
    fn = out + f".{len(tiles)}.png"
    pygame.image.save(s, fn)
    im = Image.open(fn).convert("RGB")
    os.remove(fn)
    tiles.append((name, im))
W = sum(im.width for _, im in tiles) + 10 * len(tiles)
sheet = Image.new("RGB", (W, tiles[0][1].height + 30), (255, 255, 255))
from PIL import ImageDraw
d = ImageDraw.Draw(sheet)
x = 0
for name, im in tiles:
    sheet.paste(im, (x, 30))
    d.text((x + 10, 8), name, fill=(0, 0, 0))
    x += im.width + 10
sheet.save(out)
print(out)
