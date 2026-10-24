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
       "chair_trident.png": dict(key="trident"), "chair_pulse6.png": dict(key="pulse6",   # розовый «паучок» на затылке подголовника — нарисован в ТЕКСТУРЕ Meshy
           paint=[dict(x=[-285, -230], y=[1092, 1165], z=[-58, 30], col=(0.04, 0.04, 0.045), rough=1.0)]),   # (сетка там чистая) — закрасить
       "chair_gorynych.png": dict(key="jazzy"), "chair_whillc2.png": dict(key="whill"),
       "chair_yaga.png": dict(key="d100", spokes=[dict(side=1, c=(-214.4, 305.3), hc=(-219.7, 303.5), zp=305, fl=10, cut_r=(42, 244), cut_z=(292, 332), rh=30, rr=247, n=36, col=(0.72, 0.72, 0.75)), dict(side=-1, c=(-213.2, 308.6), hc=(-218.7, 304.4), zp=305, fl=10, cut_r=(42, 244), cut_z=(292, 332), rh=30, rr=247, n=36, col=(0.72, 0.72, 0.75))]), "chair_rusalka.png": dict(key="x3", spokes=[dict(side=1, c=(-121.3, 323.3), hc=(-116.9, 317.4), zp=255, fl=14, cut_r=(62, 264), cut_z=(240, 270), rh=32, rr=268, n=24, col=(0.12, 0.12, 0.13)), dict(side=-1, c=(-121.1, 323.3), hc=(-117.1, 320.1), zp=255, fl=14, cut_r=(62, 264), cut_z=(240, 270), rh=32, rr=268, n=24, col=(0.12, 0.12, 0.13))]),
       "chair_ra.png": dict(key="nitrum", spokes=[dict(side=1, c=(-106.7, 328.4), hc=(-106.7, 328.4), zp=252, fl=10, cut_r=(118, 264), cut_z=(240, 263), rh=100, rr=268, n=24, cross=0.05, col=(0.62, 0.62, 0.66)), dict(side=-1, c=(-108.1, 328.6), hc=(-108.1, 328.6), zp=252, fl=10, cut_r=(118, 264), cut_z=(240, 263), rh=100, rr=268, n=24, cross=0.05, col=(0.62, 0.62, 0.66))], hubs=[dict(c=(-106.7, 328.4, 257.5), r=115, w=60), dict(c=(-108.1, 328.6, -257.5), r=115, w=60)]),   # ступицы Alber e-motion
       "chair_basic.png": dict(key="inv9000"), "chair_troll.png": dict(key="inv9000xdt"),
       "chair_fairy.png": dict(key="exelle", recolor=[72, 330, 30, 0.5],   # салатовый -> пастельный розовый
           move=[dict(x=[-428, -392], y=[18, 52], az=[17, 50], delete=True),         # поперечина колёсика
                 dict(x=[-470, -362], y=[-8, 96], az=[50, 115], d=[0, 0, -47])],   # колесо — вплотную к трубе
           # антиопрокидыватель — родной Meshy, один по центру (решение владельца 23.10; у настоящей Exelle Junior их
           # бывает и пара). Пара по бокам: move=[dict(x=[-180, 30], y=[100, 262], az=[0, 45], delete=True),
           #   dict(x=[-230, -125], y=[235, 310], az=[0, 45], delete=True)], clones=[dict(x=[-460, -185], y=[0, 245],
           #   az=[0, 100], copies=[dict(d=(78, 0, 128)), dict(mirror=True, d=(78, 0, -128))])]
           spokes=[dict(side=1, c=(-92.7, 294.0), hc=(-98.1, 292.0), zp=197, fl=9, cut_r=(40, 232), cut_z=(183, 213), rh=26, rr=235, n=24, col=(0.72, 0.72, 0.75)), dict(side=-1, c=(-93.2, 295.0), hc=(-97.4, 292.9), zp=197, fl=9, cut_r=(40, 232), cut_z=(183, 213), rh=26, rr=235, n=24, col=(0.72, 0.72, 0.75))]),
       "chair_aeroz.png": dict(key="aeroz", antitips=[dict(p0=(-235, 245, s * 172), p1=(-470, 58, s * 172), r=10, wheel=(24, 18)) for s in (1, -1)],   # в модели Meshy их нет
           spokes=[dict(side=1, c=(-205.9, 295.9), hc=(-204.9, 294.6), zp=235, fl=12, cut_r=(40, 228), cut_z=(212, 262), rh=28, rr=232, n=24, col=(0.72, 0.72, 0.75)), dict(side=-1, c=(-204.6, 302.1), hc=(-204.5, 298.9), zp=235, fl=12, cut_r=(40, 228), cut_z=(212, 262), rh=28, rr=232, n=24, col=(0.72, 0.72, 0.75))]),
       "chair_cross6.png": dict(key="cross6", spokes=[dict(side=1, c=(-146.5, 322.2), hc=(-154.0, 324.4), zp=290, fl=12, cut_r=(40, 255), cut_z=(262, 318), rh=30, rr=258, n=24, col=(0.72, 0.72, 0.75)), dict(side=-1, c=(-147.1, 322.9), hc=(-152.5, 323.9), zp=290, fl=12, cut_r=(40, 255), cut_z=(262, 318), rh=30, rr=258, n=24, col=(0.72, 0.72, 0.75))]),
       "chair_orc.png": dict(key="noir", spokes=[dict(side=1, c=(-101.3, 352.8), hc=(-101.7, 357.0), zp=290, fl=12, cut_r=(34, 272), cut_z=(250, 332), rh=28, rr=276, n=24, col=(0.72, 0.72, 0.75)), dict(side=-1, c=(-101.6, 344.4), hc=(-101.7, 346.8), zp=290, fl=12, cut_r=(34, 272), cut_z=(250, 332), rh=28, rr=276, n=24, col=(0.72, 0.72, 0.75))]),
       "chair_elf.png": dict(key="ego", spokes=[dict(side=1, c=(-133.6, 327.9), hc=(-128.1, 327.1), zp=300, fl=12, cut_r=(34, 252), cut_z=(258, 342), rh=28, rr=258, n=24, col=(0.72, 0.72, 0.75)), dict(side=-1, c=(-137.3, 328.0), hc=(-133.7, 327.1), zp=300, fl=12, cut_r=(34, 252), cut_z=(258, 342), rh=28, rr=258, n=24, col=(0.72, 0.72, 0.75))]),
       "chair_q6edge.png": dict(key="q6m",   # Q6 Edge 2.0 (синяя) — выбор владельца 24.10; по фото _raw/q6edge2:
           move=[dict(x=[165, 410], y=[636, 775], z=[100, 300], rot=(11, -15), pivot=(205, 668, 200), d=(-40, 0, 0)),  # пульт: ровно,
                 #   вплотную к подушке подлокотника (у Meshy задран на 15°, развёрнут на 11°, отнесён вперёд)
                 dict(x=[285, 520], y=[40, 80], z=[-180, 125], d=(0, 35, 0))],   # две площадки подножек лежали на полу — на ~9 см
           tubes=[dict(p0=(232, 616, 232), p1=(232, 656, 214), r=10, col=(0.18, 0.18, 0.2)),   # стояк с кронштейна под пульт
                  dict(p0=(270, 200, 30), p1=(322, 105, 30), r=14, col=(0.1, 0.1, 0.11)),      # центральная стойка подножек
                  dict(p0=(326, 100, -165), p1=(326, 100, 115), r=9, col=(0.1, 0.1, 0.11))]),  # поперечина под площадками
       # прежняя жёлтая классика (q6c, 23.10) — правила в git до 24.10: delete-коробки проводов/ремешка/зажима, фланец,
       # пульт d=-66, кронштейн tubes; арт — art_tests/retired/chair_q6edge_classic_yellow_2310.png
       "chair_dwarf.png": dict(key="q2"),   # Quickie 2 (оборотень Вольф)
       "chair_focuscr.png": dict(key="fcr"),
       "chair_leshy.png": dict(key="x8", recolor=[28, 4, 26])}           # оранжевый -> красный                               # цвета Meshy (тёмно-синяя рама, как на фото)
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
        spec.update(glb=xf["src"], glb_matrix=xf["matrix"], recolor=GLB[art].get("recolor"), hubs=GLB[art].get("hubs"),
                    spokes=GLB[art].get("spokes"), move=GLB[art].get("move"), antitips=GLB[art].get("antitips"), clones=GLB[art].get("clones"),
                    tubes=GLB[art].get("tubes"), paint=GLB[art].get("paint"))
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
