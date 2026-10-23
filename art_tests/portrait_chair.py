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
       "chair_q6edge.png": dict(key="q6c",   # классическая Q6 Edge (жёлтая); пульт у Meshy висел в 4 см перед подлокотником —
           move=[dict(x=[72, 101], y=[660, 752], z=[262, 358], delete=True),   # круглый фланец между подлокотником и пультом
                 dict(x=[101, 300], y=[655, 800], z=[255, 380], rot=(0, 0), pivot=(80, 700, 315), d=(-66, 4, 0)),  # вплотную
                 dict(x=[88, 160], y=[598, 655], z=[280, 340], rot=(0, 0), pivot=(80, 700, 315), d=(-66, 4, 0))],  # (низ пульта)
           tubes=[dict(p0=(-110, 674, 312), p1=(110, 666, 312), r=12, col=(0.32, 0.33, 0.35)),   # кронштейн под подушкой
                  dict(p0=(-110, 674, 286), p1=(-110, 674, 338), r=9, col=(0.32, 0.33, 0.35)),   # хомут сзади
                  dict(p0=(20, 671, 286), p1=(20, 671, 338), r=9, col=(0.32, 0.33, 0.35))]),     # хомут спереди
       "chair_dwarf.png": dict(key="q2"),   # Quickie 2 (оборотень Вольф)
       "chair_focuscr.png": dict(key="fcr"),
       "chair_leshy.png": dict(key="x8", recolor=[28, 4, 26])}
# подгонка коляски под персонажа (только для портрета): сдвиг части модели, мм игры (blender_render.move_parts)
MOVE = {"chair_f5.png": [   # Матильда: без передних антиопрокидывателей, подножка выше под короткие ноги
    dict(x=[385, 520], y=[-20, 140], az=[235, 300], not_wheel=[215, 182, 188, 215], delete=True),
    dict(x=[330, 620], y=[-50, 200], not_wheel=[215, 182, 195, 215], d=[0, 190, 0])],
    # Мартин и Бомм: у Invacare 9000 от сиденья до подножки ~360 мм, у прежней коляски портрета ~285 — подножки
    # выше на 80–90 мм (иначе Qwen дорисовывает под ногами вторую «ступеньку», а настоящие подножки висят пустые)
    "chair_basic.png": [dict(x=[360, 570], y=[30, 180], d=[0, 80, 0])],
    "chair_troll.png": [dict(x=[385, 610], y=[32, 192], d=[0, 90, 0])]}
if art in GLB:
    xf = json.load(open(os.path.join(HERE, "gen3d", GLB[art]["key"] + "_xform.json"), encoding="utf-8"))
    spec.update(glb=xf["src"], glb_matrix=xf["matrix"], recolor=GLB[art].get("recolor"),
                move=(GLB[art].get("move") or []) + (MOVE.get(art) or []) or None,
                hubs=GLB[art].get("hubs"), spokes=GLB[art].get("spokes"), antitips=GLB[art].get("antitips"), clones=GLB[art].get("clones"),
                    tubes=GLB[art].get("tubes"), paint=GLB[art].get("paint"))
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
