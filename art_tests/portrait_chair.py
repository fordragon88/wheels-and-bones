"""Рендер новой коляски (кадры Blender, как в игре) в ракурсе портрета клиента — референс для перерисовки портрета.
python art_tests/portrait_chair.py <chair_x.png> <yaw[,yaw…]> [pitch=0.12]
-> tools/render_out/portrait_<chair>/…png (белый фон) — потом art_tests/portrait_reseat.py"""
import os, sys, json, subprocess
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
BLENDER = os.path.join(ROOT, "tools", "blender-4.2.23-windows-x64", "blender.exe")
art, yaws = sys.argv[1], [float(v) for v in sys.argv[2].split(",")]
pitch = float(sys.argv[3]) if len(sys.argv) > 3 else 0.12
name = os.path.splitext(art)[0]
src = os.path.join(ROOT, "tools", "render_in", name + ".json")
subprocess.run([sys.executable, os.path.join(HERE, "blender_export.py"), art], check=True, cwd=ROOT,
               stdout=subprocess.DEVNULL)
spec = json.load(open(src, encoding="utf-8"))
sys.path.insert(0, HERE)
GLB = {"chair_m3.png": dict(key="m3", recolor=[0, 275, 28]), "chair_edge4.png": dict(key="edge4", recolor=[228, 2, 32]),
       "chair_f5.png": dict(key="f5m", recolor=[175, -1, 30]), "chair_trident.png": dict(key="trident"),
       "chair_pulse6.png": dict(key="pulse6")}
if art in GLB:
    xf = json.load(open(os.path.join(HERE, "gen3d", GLB[art]["key"] + "_xform.json"), encoding="utf-8"))
    spec.update(glb=xf["src"], glb_matrix=xf["matrix"], recolor=GLB[art].get("recolor"))
V = spec["verts"]
hgt = max(v[1] for v in V) - min(v[1] for v in V)
spec.update(W=1024, H=1024, s=1024 * 0.78 / max(hgt, 1100), pitch=pitch, yaws=yaws)
spec["pivot"][1] = (max(v[1] for v in V) + min(v[1] for v in V)) / 2 + 0.04 * hgt
pj = os.path.join(ROOT, "tools", "render_in", f"portrait_{name}.json")
json.dump(spec, open(pj, "w"), separators=(",", ":"))
out = os.path.join(ROOT, "tools", "render_out", f"portrait_{name}")
subprocess.run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(HERE, "blender_render.py"), "--", pj, out],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for i, y in enumerate(yaws):
    fp = os.path.join(out, f"portrait_{name}_{i:02d}.png")
    im = Image.open(fp).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(fp.replace(".png", "_white.png"))
    print(fp.replace(".png", "_white.png"), "yaw", y)
