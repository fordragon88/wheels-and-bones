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
       "chair_pulse6.png": dict(key="pulse6"), "chair_gorynych.png": dict(key="jazzy"), "chair_yaga.png": dict(key="d100", spokes=[dict(side=1, c=(-214.4, 305.3), hc=(-219.7, 303.5), zp=305, fl=10, cut_r=(42, 244), cut_z=(292, 332), rh=30, rr=247, n=36, col=(0.72, 0.72, 0.75)), dict(side=-1, c=(-213.2, 308.6), hc=(-218.7, 304.4), zp=305, fl=10, cut_r=(42, 244), cut_z=(292, 332), rh=30, rr=247, n=36, col=(0.72, 0.72, 0.75))]),
       "chair_rusalka.png": dict(key="x3", spokes=[dict(side=1, c=(-121.3, 323.3), hc=(-116.9, 317.4), zp=255, fl=14, cut_r=(62, 264), cut_z=(240, 270), rh=32, rr=268, n=24, col=(0.12, 0.12, 0.13)), dict(side=-1, c=(-121.1, 323.3), hc=(-117.1, 320.1), zp=255, fl=14, cut_r=(62, 264), cut_z=(240, 270), rh=32, rr=268, n=24, col=(0.12, 0.12, 0.13))]), "chair_ra.png": dict(key="nitrum", spokes=[dict(side=1, c=(-106.7, 328.4), hc=(-106.7, 328.4), zp=252, fl=10, cut_r=(118, 264), cut_z=(240, 263), rh=100, rr=268, n=24, cross=0.05, col=(0.62, 0.62, 0.66)), dict(side=-1, c=(-108.1, 328.6), hc=(-108.1, 328.6), zp=252, fl=10, cut_r=(118, 264), cut_z=(240, 263), rh=100, rr=268, n=24, cross=0.05, col=(0.62, 0.62, 0.66))], hubs=[dict(c=(-106.7, 328.4, 257.5), r=115, w=60), dict(c=(-108.1, 328.6, -257.5), r=115, w=60)]),
       "chair_whillc2.png": dict(key="whill"), "chair_basic.png": dict(key="inv9000"), "chair_troll.png": dict(key="inv9000xdt"),
       "chair_focuscr.png": dict(key="fcr"),
       "chair_leshy.png": dict(key="x8", recolor=[28, 4, 26])}
# подгонка коляски под персонажа (только для портрета): сдвиг части модели, мм игры (blender_render.move_parts)
MOVE = {"chair_f5.png": [   # Матильда: без передних антиопрокидывателей, подножка выше под короткие ноги
    dict(x=[385, 520], y=[-20, 140], az=[235, 300], not_wheel=[215, 182, 188, 215], delete=True),
    dict(x=[330, 620], y=[-50, 200], not_wheel=[215, 182, 195, 215], d=[0, 190, 0])]}
if art in GLB:
    xf = json.load(open(os.path.join(HERE, "gen3d", GLB[art]["key"] + "_xform.json"), encoding="utf-8"))
    spec.update(glb=xf["src"], glb_matrix=xf["matrix"], recolor=GLB[art].get("recolor"), move=MOVE.get(art),
                hubs=GLB[art].get("hubs"), spokes=GLB[art].get("spokes"))
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
