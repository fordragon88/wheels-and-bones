"""Целостность ассетов по заданиям: портрет клиента, арт коляски, 3D-модель, кадры поворота (36), хотспоты.
python art_tests/asset_check.py   -> «АССЕТЫ OK» или список проблем (код выхода 1).
Народные коляски (Яга, Ольга, Леший, Сенеб, Горыныч) живут без модели в assets/models — только кадры
(index_folk.json; модели — art_tests/tripo/models); у заданий Гильдии хотспотов нет (операции списком)."""
import os, sys, json, importlib.util
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("game", "game.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

TT = "assets/turntable"
ANIM = "assets/anim"                       # петли героев: <имя>/NN.jpg + NN.a.png одного размера, подряд с 00
idx = json.load(open(f"{TT}/index.json", encoding="utf-8"))
folk = json.load(open(f"{TT}/index_folk.json", encoding="utf-8"))
files = os.listdir(TT)
bad = []
for j in g.ALL_JOBS:
    jid, ca, cl, cm = j["id"], j.get("chair_art"), j.get("client_art"), j.get("chair_model")
    tech = j.get("track") == "tech"
    if cl and not os.path.exists(f"assets/{cl}"):
        bad.append(f"{jid}: нет портрета {cl}")
    if not ca:
        continue
    k = ca[:-4]
    if not os.path.exists(f"assets/{ca}"):
        bad.append(f"{jid}: нет арта {ca}")
    e = idx.get(ca) or folk.get(ca)
    if e is None:
        bad.append(f"{jid}: нет кадров поворота {ca}")
    else:
        ext = e.get("fmt", "png")
        n = sum(1 for f in files if f.startswith(k + "_") and f.endswith("." + ext) and not f.endswith(".a.png")
                and f[len(k) + 1:len(k) + 3].isdigit() and len(f) == len(k) + 4 + len(ext))
        if n != e.get("n", 36):
            bad.append(f"{jid}: кадров {n} из {e.get('n', 36)} ({ca}, {ext})")
        if ext == "jpg":
            na = sum(1 for f in files if f.startswith(k + "_") and f.endswith(".a.png") and len(f) == len(k) + 9)
            if na != e.get("n", 36):
                bad.append(f"{jid}: масок .a.png {na} из {e.get('n', 36)}")
    if ca not in folk and not os.path.exists(f"assets/models/{k}_ai.json"):
        bad.append(f"{jid}: нет модели assets/models/{k}_ai.json")
    if not tech and cm and cm not in g.CHAIR_HOTSPOTS:
        bad.append(f"{jid}: нет хотспотов CHAIR_HOTSPOTS['{cm}']")
# петли героев (Мартин и Барти машут): кадры подряд с 00, у каждого маска .a.png того же размера, что JPEG
import pygame
pygame.display.init()
anims = sorted(n for n in os.listdir(ANIM) if os.path.isdir(f"{ANIM}/{n}")) if os.path.isdir(ANIM) else []
for name in anims:
    d = f"{ANIM}/{name}"
    jp = sorted(f for f in os.listdir(d) if f.endswith(".jpg"))
    n = len(jp)
    if n < 2:
        bad.append(f"anim/{name}: кадров {n}")
        continue
    if jp != [f"{i:02d}.jpg" for i in range(n)]:
        bad.append(f"anim/{name}: кадры не подряд с 00 ({jp[0]}…{jp[-1]})")
    extra = [f for f in os.listdir(d) if not (f.endswith(".jpg") or f.endswith(".a.png"))]
    if extra:
        bad.append(f"anim/{name}: лишние файлы {extra[:3]}")
    for f in jp:
        a = f"{d}/{f[:-4]}.a.png"
        if not os.path.exists(a):
            bad.append(f"anim/{name}: нет маски {os.path.basename(a)}")
        elif pygame.image.load(a).get_size() != pygame.image.load(f"{d}/{f}").get_size():
            bad.append(f"anim/{name}: маска {os.path.basename(a)} не того размера")
# «волшебство» на портрете: assets/anim/magic_index.json (art_tests/magic_frames.py) — петля есть, кадров и размер как
# в индексе, портрет героя существует, прямоугольник портрета внутри кадра
mi = f"{ANIM}/magic_index.json"
if os.path.exists(mi):
    import json
    with open(mi, encoding="utf-8") as f:
        magic = json.load(f)
    for name, e in sorted(magic.items()):
        d = f"{ANIM}/{name}"
        n = len([f for f in os.listdir(d) if f.endswith(".jpg")]) if os.path.isdir(d) else 0
        if n != e.get("n"):
            bad.append(f"magic_index {name}: кадров {n}, в индексе {e.get('n')}")
            continue
        if not os.path.exists(f"assets/{e.get('art')}"):
            bad.append(f"magic_index {name}: нет портрета assets/{e.get('art')}")
        sz = pygame.image.load(f"{d}/00.jpg").get_size()
        if list(sz) != list(e.get("size", ())):
            bad.append(f"magic_index {name}: кадр {sz}, в индексе {e.get('size')}")
        x, y, w, h = e.get("portrait", (0, 0, 0, 0))
        if not (0 <= x and 0 <= y and w > 0 and h > 0 and x + w <= sz[0] + 1 and y + h <= sz[1] + 1):
            bad.append(f"magic_index {name}: портрет {e.get('portrait')} вне кадра {sz}")
print("\n".join(bad) if bad else f"АССЕТЫ OK — {len(g.ALL_JOBS)} заданий: портреты, арт, модели, кадры, хотспоты; "
      f"петли anim: {', '.join(anims) or 'нет'}")
sys.exit(1 if bad else 0)
