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
print("\n".join(bad) if bad else f"АССЕТЫ OK — {len(g.ALL_JOBS)} заданий: портреты, арт, модели, кадры, хотспоты")
sys.exit(1 if bad else 0)
