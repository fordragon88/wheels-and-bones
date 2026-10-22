"""Готовый вариант портрета (scratchpad/poses/local/reseat_<ключ>_s<seed>_9_0.png) -> assets/<портрет>.png:
вырезка фона BiRefNet (ComfyUI), alpha_repair, обрезка по объекту, высота — как у прежнего портрета (старый —
art_tests/retired/). python art_tests/portrait_install.py <ключ>=<seed> […]"""
import os, shutil, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SP = r"C:\Users\wario\AppData\Local\Temp\claude\D--wheels-and-bones\d845888a-7a45-42b9-a337-635687a142cf\scratchpad"
sys.path.insert(0, HERE)
import importlib.util
spec = importlib.util.spec_from_file_location("pr", os.path.join(HERE, "portrait_reseat.py"))
src = open(os.path.join(HERE, "portrait_reseat.py"), encoding="utf-8").read()
JOBS = {}
exec(src[src.index("JOBS = {"):src.index("\n}\n") + 3])                 # только словарь, без запуска генерации
for arg in sys.argv[1:]:
    key, seed = arg.split("=")
    portrait = JOBS[key][1]
    gen = os.path.join(SP, "poses", "local", f"reseat_{key}_s{seed}_9_0.png")
    name = f"reseat_{key}"
    subprocess.run([sys.executable, os.path.join(SP, "cut_new.py"), f"{name}={gen}"], check=True, cwd=SP,
                   stdout=subprocess.DEVNULL)
    cut = os.path.join(ROOT, "art_tests", "new_v1", "cut", name + ".png")
    rep = os.path.join(SP, "poses", "local", name + "_rep.png")
    subprocess.run([sys.executable, os.path.join(HERE, "alpha_repair.py"), gen, cut, rep], check=True,
                   stdout=subprocess.DEVNULL)
    dst = os.path.join(ROOT, "assets", portrait)
    old = os.path.join(HERE, "retired", portrait)
    os.makedirs(os.path.dirname(old), exist_ok=True)
    if not os.path.exists(old):
        shutil.copy(dst, old)
    H = Image.open(old).height
    im = Image.open(rep).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
    k = H / im.height
    im = im.resize((round(im.width * k), H), Image.LANCZOS)
    im.save(dst, optimize=True)
    print(portrait, im.size)
