"""Исправленные копии моделей Meshy (спицы — fix_spokes, ступицы e-motion — add_hub,
антиопрокидыватели — add_antitip, кривые куски Meshy — move/delete) -> meshy_models/<имя>_fixed.glb.
Исходники meshy_models/<имя>.glb не меняются. Копия — в осях игры: метры, пол на 0, вперёд +X, правая сторона +Z.
python art_tests/glb_fixed.py [chair_yaga.png …]   (по умолчанию — все коляски с правками в blender_frames.GLB)"""
import os, sys, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
BLENDER = os.path.join(ROOT, "tools", "blender-4.2.23-windows-x64", "blender.exe")
src = open(os.path.join(HERE, "blender_frames.py"), encoding="utf-8").read()
ns = {}
exec(src[src.index("GLB = {"):src.index("\ntotal = 0")], ns)                    # тот же словарь, что для кадров
GLB = ns["GLB"]
arts = sys.argv[1:] or [a for a, g in GLB.items() if g.get("spokes") or g.get("hubs") or g.get("antitips") or g.get("clones") or g.get("tubes")]
tmp = os.path.join(ROOT, "tools", "render_in")
for art in arts:
    g = GLB[art]
    xf = json.load(open(os.path.join(HERE, "gen3d", g["key"] + "_xform.json"), encoding="utf-8"))
    spec = json.load(open(os.path.join(tmp, os.path.splitext(art)[0] + ".json"), encoding="utf-8"))
    spec.update(glb=xf["src"], glb_matrix=xf["matrix"], recolor=None, spokes=g.get("spokes"), hubs=g.get("hubs"),
                move=g.get("move"), antitips=g.get("antitips"), clones=g.get("clones"), tubes=g.get("tubes"), paint=g.get("paint"))
    sp = os.path.join(tmp, "_fixed_" + os.path.splitext(art)[0] + ".json")
    json.dump(spec, open(sp, "w"), separators=(",", ":"))
    out = os.path.splitext(os.path.join(ROOT, xf["src"]) if not os.path.isabs(xf["src"]) else xf["src"])[0] + "_fixed.glb"
    r = subprocess.run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(HERE, "blender_render.py"), "--", sp, tmp],
                       cwd=ROOT, env=dict(os.environ, WB_EXPORT=out), capture_output=True, text=True, errors="replace")
    os.remove(sp)
    ok = os.path.exists(out)
    print(art, "->", out, f"{os.path.getsize(out) / 1e6:.1f} МБ" if ok else "НЕ ВЫШЛО\n" + r.stdout[-1500:] + r.stderr[-800:])
