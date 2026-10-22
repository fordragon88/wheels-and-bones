"""Сгенерированная модель (art_tests/gen3d/<имя>_full.npz из tripo_convert) -> 4 вида в Blender рядом с референсом.
python art_tests/gen3d_preview.py <имя> <референс.png> [другие имена…]   -> art_tests/gen3d/<имя>_preview.png"""
import os, sys, json, math, subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
BLENDER = os.path.join(ROOT, "tools", "blender-4.2.23-windows-x64", "blender.exe")
names, ref = [sys.argv[1]] + sys.argv[3:], sys.argv[2]
W, H = 760, 640
rows = []
for name in names:
    d = np.load(os.path.join(HERE, "gen3d", name + "_full.npz"))
    V, F, C = d["V"], d["F"], d["C"][:, :3]
    lo, hi = V.min(0), V.max(0)
    pivot = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0]
    s = H * 0.80 / max(hi[1] - lo[1], 0.75 * (hi[0] - lo[0]))     # пикс/мм: вся коляска в кадре
    yaws = [-0.75 + k * math.pi / 2 for k in range(4)]
    fc = C[F].mean(1)
    spec = dict(art=name, W=W, H=H, s=s, pivot=pivot, pitch=0.26, yaws=yaws, z0=1.0,
                verts=V.round(1).tolist(), faces=[[f.tolist(), "frame", [int(v) for v in c], 0] for f, c in zip(F, fc)])
    src = os.path.join(ROOT, "tools", "render_in", "gen_" + name + ".json")
    json.dump(spec, open(src, "w"), separators=(",", ":"))
    out = os.path.join(ROOT, "tools", "render_out", "gen_" + name)
    subprocess.run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(HERE, "blender_render.py"), "--", src, out],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows.append([Image.open(os.path.join(out, f"gen_{name}_{k:02d}.png")).convert("RGBA") for k in range(4)])
cell = 340
r = Image.open(ref).convert("RGBA")
k = min(cell / r.width, cell / r.height)
r = r.resize((int(r.width * k), int(r.height * k)), Image.LANCZOS)
sheet = Image.new("RGBA", (cell * 5, cell * len(rows)), (222, 200, 170, 255))
for j, row in enumerate(rows):
    sheet.alpha_composite(r, ((cell - r.width) // 2, j * cell + (cell - r.height) // 2))
    for i, im in enumerate(row):
        bb = im.getchannel("A").getbbox()
        im = im.crop(bb) if bb else im
        kk = min((cell - 10) / im.width, (cell - 10) / im.height)
        im = im.resize((int(im.width * kk), int(im.height * kk)), Image.LANCZOS)
        sheet.alpha_composite(im, ((i + 1) * cell + (cell - im.width) // 2, j * cell + (cell - im.height) // 2))
dst = os.path.join(HERE, "gen3d", names[0] + "_preview.png")
sheet.convert("RGB").save(dst)
print(dst)
