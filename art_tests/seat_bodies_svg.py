"""Тело клиента Кабинета посадки из ВЕКТОРНОЙ куклы (SVG от ChatGPT/Codex по ТЗ art_tests/seat_bodies/chatgpt_brief):
5 групп shin/thigh/pelvis/chest/head, суставы — из <g id="joints"> (circle id="j_<имя>") или joints_neutral.json.
Каждая группа рендерится отдельно (Playwright/Chromium, прозрачный фон) -> assets/seat_body_<id>_<часть>.png,
опорные суставы части — в assets/seat_bodies.json (как у art_tests/seat_bodies.py; "slim": 1.0 — пропорции уже под скелет).
python art_tests/seat_bodies_svg.py <файл.svg> [id=seat_troll] [px=900] [out=папка]"""
import json, os, re, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("out=")), os.path.join(HERE, "..", "assets"))
SVG = sys.argv[1]
CID = next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("id=")), "seat_troll")
PX = int(next((a.split("=", 1)[1] for a in sys.argv[2:] if a.startswith("px=")), 900))
# часть: (опорный сустав, второй сустав, порядок рисования — сзади вперёд)
PARTS = {"shin": ("knee", "ankle", 0), "thigh": ("hip", "knee", 1), "pelvis": ("hip", "mid", 2),
         "chest": ("mid", "sh", 3), "upper_arm": ("sh", "elbow", 4), "forearm": ("elbow", "hand", 5),
         "head": ("neck", "head", 6)}
OPTIONAL = {"upper_arm", "forearm"}                       # рука отдельно — если в SVG есть такие группы

src = open(SVG, encoding="utf-8").read()
J = json.load(open(os.path.join(HERE, "seat_bodies", "chatgpt_brief", "joints_neutral.json")))
for name, cx, cy in re.findall(r'<circle[^>]*id="j_(\w+)"[^>]*cx="([\d.]+)"[^>]*cy="([\d.]+)"', src):
    J[name] = [float(cx), float(cy)]
vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', src).group(1).replace(",", " ").split()]
k = PX / vb[2]

from playwright.sync_api import sync_playwright

meta = json.load(open(os.path.join(OUT, "seat_bodies.json"), encoding="utf-8")) if os.path.exists(
    os.path.join(OUT, "seat_bodies.json")) else {}
entry = dict(parts={}, slim=1.0, source=os.path.basename(SVG))
with sync_playwright() as pw:
    br = pw.chromium.launch()
    page = br.new_page(viewport={"width": PX, "height": round(vb[3] * k)})
    for part, (a, b, order) in PARTS.items():
        if part in OPTIONAL and f'id="{part}"' not in src:
            continue
        hide = "".join(f'#{p}{{display:none}}' for p in PARTS if p != part) + "#joints{display:none}"
        html = (f"<html><body style='margin:0;background:transparent'><style>{hide} svg{{width:{PX}px;height:auto;"
                f"display:block}}</style>{src}</body></html>")
        page.set_content(html)
        tmp = os.path.join(OUT, f"_tmp_{part}.png")
        page.screenshot(path=tmp, omit_background=True, full_page=True)
        im = Image.open(tmp).convert("RGBA")
        os.remove(tmp)
        bb = im.getchannel("A").point(lambda v: 255 if v > 4 else 0).getbbox()
        if not bb:
            raise SystemExit(f"пустая часть: {part}")
        im = im.crop(bb)
        fn = f"seat_body_{CID}_{part}.png"
        im.save(os.path.join(OUT, fn), optimize=True)
        to_px = lambda j: [round((J[j][0] - vb[0]) * k - bb[0], 1), round((J[j][1] - vb[1]) * k - bb[1], 1)]
        entry["parts"][part] = dict(file=fn, order=order, a=a, b=b, pa=to_px(a), pb=to_px(b))
        print(part, im.size, entry["parts"][part]["pa"], entry["parts"][part]["pb"])
    br.close()
for old in [f for f in os.listdir(OUT) if f.startswith(f"seat_body_{CID}_") and f[len(f"seat_body_{CID}_"):-4] not in PARTS]:
    os.remove(os.path.join(OUT, old))                       # части прежней «вырезной» куклы (torso) больше не нужны
meta[CID] = entry
json.dump(meta, open(os.path.join(OUT, "seat_bodies.json"), "w", encoding="utf-8"), indent=1)
print("->", os.path.join(OUT, "seat_bodies.json"))
