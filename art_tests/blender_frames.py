"""Кадры поворота колясок через Blender (мягкий свет, плавный цвет, сглаживание) -> assets/turntable/:
<коляска>_NN.jpg (цвет) + <коляска>_NN.a.png (белая маска прозрачности), запись в index.json / index_folk.json
(fmt="jpg", смещения кадров; центр, масштаб и центры деталей — как у build_turntables.py, кружки на месте).
python art_tests/blender_frames.py [chair_f5.png,…]   (без списка — все коляски, у которых есть кадры)
Нужен Blender: tools/blender-4.2.23-windows-x64 (portable, вне git)."""
import os, sys, json, glob, subprocess
from PIL import Image
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
from build_web import _bleed

BLENDER = os.path.join(ROOT, "tools", "blender-4.2.23-windows-x64", "blender.exe")
TT = os.path.join(ROOT, "assets", "turntable")
RIN, ROUT = os.path.join(ROOT, "tools", "render_in"), os.path.join(ROOT, "tools", "render_out")
idx_files = {n: json.load(open(os.path.join(TT, n), encoding="utf-8")) for n in ("index.json", "index_folk.json")
             if os.path.exists(os.path.join(TT, n))}
arts = sys.argv[1].split(",") if len(sys.argv) > 1 else [a for d in idx_files.values() for a in d]
subprocess.run([sys.executable, os.path.join(HERE, "blender_export.py"), ",".join(arts)], check=True, cwd=ROOT)
# коляски с оригинальной моделью (Meshy и т.п.): кадры — с исходного GLB (art_tests/gen3d/<ключ>_xform.json)
GLB = {"chair_m3.png": dict(key="m3", recolor=[0, 275, 28]),            # красный -> фиолетовый
       "chair_edge4.png": dict(key="edge4", recolor=[228, 2, 32]),       # синий -> красный
       "chair_f5.png": dict(key="f5m", recolor=[175, -1, 30]),           # бирюзовый -> графит
       "chair_trident.png": dict(key="trident")}
total = 0
for art in arts:
    name = os.path.splitext(art)[0]
    src = os.path.join(RIN, name + ".json")
    if not os.path.exists(src):
        print("нет модели:", art)
        continue
    if art in GLB:
        spec = json.load(open(src, encoding="utf-8"))
        xf = json.load(open(os.path.join(HERE, "gen3d", GLB[art]["key"] + "_xform.json"), encoding="utf-8"))
        spec.update(glb=xf["src"], glb_matrix=xf["matrix"], recolor=GLB[art].get("recolor"))
        json.dump(spec, open(src, "w"), separators=(",", ":"))
    out = os.path.join(ROUT, name)
    for f in glob.glob(os.path.join(out, "*.png")):
        os.remove(f)
    subprocess.run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(HERE, "blender_render.py"), "--", src, out],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.load(open(src, encoding="utf-8"))
    W, H, s = d["W"], d["H"], d["s"]
    for f in glob.glob(os.path.join(TT, name + "_[0-9][0-9].*")):
        os.remove(f)
    offsets = []
    for i in range(len(d["yaws"])):
        im = Image.open(os.path.join(out, f"{name}_{i:02d}.png")).convert("RGBA")
        a = np.asarray(im.getchannel("A"))
        ys, xs = np.nonzero(a > 6)
        bb = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        im = im.crop(bb)
        base = os.path.join(TT, f"{name}_{i:02d}")
        _bleed(im).save(base + ".jpg", "JPEG", quality=86, optimize=True, progressive=True)
        mask = Image.new("RGBA", im.size, (255, 255, 255, 0))
        mask.putalpha(im.getchannel("A"))
        mask.save(base + ".a.png", "PNG", optimize=True)
        total += os.path.getsize(base + ".jpg") + os.path.getsize(base + ".a.png")
        offsets.append([round((bb[0] - W / 2) / s, 2), round((bb[1] - H * 0.54) / s, 2)])
    which = next((n for n, dd in idx_files.items() if art in dd), "index.json")
    e = idx_files.setdefault(which, {}).get(art, {})
    e.update(n=len(d["yaws"]), yaw0=d["yaws"][0], pitch=d["pitch"], z0=round(d["z0"], 5), ref=round(s, 5),
             offsets=offsets, pivot=[round(float(c), 2) for c in d["pivot"]], fmt="jpg",
             centers={p: [[round(float(v), 1) for v in c] for c in cs] for p, cs in d["centers"].items()})
    idx_files[which][art] = e
    print(f"{name}: {len(offsets)} кадров", flush=True)
for n, dd in idx_files.items():
    with open(os.path.join(TT, n), "w", encoding="utf-8") as f:
        json.dump(dd, f, separators=(",", ":"))
print(f"готово, {total / 1e6:.1f} МБ")
