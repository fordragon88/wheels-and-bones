# -*- coding: utf-8 -*-
"""Сверка размера текста Godot ↔ pygame (крупный текст 112/125/150 %, «лёгкий» шрифт): снимки обеих версий одних и
тех же экранов и средняя разница по каждому (сетка 8×6 — где именно).

  python godot/tools/text_scale/run.py [--text 3] [--lang en] [--font] [--x] [--out DIR] [имена…]

  --text 0..3  размер текста (100/112/125/150 %), по умолчанию 3 (150 %)
  --lang       en (по умолчанию) | ru
  --font       шрифт для лёгкого чтения (Atkinson, только en)
  --x          не экраны tests/shots.gd, а длинные тексты из xlist.txt (диагнозы, улики, шаги, мини-игры, итоги,
               Гильдия, уроки посадки — «x:вид:задание:вариант:…», см. tests/text_scale/text_shots.gd и ref_x.py)
  имена        только эти экраны (имена tests/shots.gd)
Результат: <out>/ref (pygame), <out>/godot, <out>/diff.txt (худшие сверху); сравнить две папки — diff.py A B,
вырезать кусок бок о бок — crop.py out.png x0 y0 x1 y1 a.png b.png …
Godot — окно без звука (--audio-driver Dummy), сохранение и настройки игрока не трогает (--test, свой APPDATA).
Найдено так 20.11: размер шрифта при 125/150 % был на 1 px крупнее (roundi вместо питоновского round), высота
строки Atkinson — не как у SDL_ttf (UI.fs / UI.px_height)."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GODOT_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
GODOT_EXE = os.environ.get("GODOT_EXE", r"D:\Godot\Godot_v4.7.2-stable_win64_console.exe")


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    text = arg("--text", "3")
    lang = arg("--lang", "en")
    font = "--font" in sys.argv
    xmode = "--x" in sys.argv
    tag = f"{lang}{[100, 112, 125, 150][int(text)]}{'font' if font else ''}{'_x' if xmode else ''}"
    out = os.path.abspath(arg("--out", os.path.join(GODOT_DIR, "tests", "out", "text_scale", tag)))
    skip = {"--text", "--lang", "--out"}
    names, i = [], 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a in skip:
            i += 2
            continue
        if not a.startswith("--"):
            names.append(a)
        i += 1
    if xmode and not names:
        names = [n for n in open(os.path.join(HERE, "xlist.txt"), encoding="utf-8").read().split() if n.startswith("x:")]
    ref, gd = os.path.join(out, "ref"), os.path.join(out, "godot")
    os.makedirs(ref, exist_ok=True)
    os.makedirs(gd, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYGAME_HIDE_SUPPORT_PROMPT="1")
    py = [sys.executable, os.path.join(HERE, "ref_x.py" if xmode else "ref_shots.py"), "--aout", ref, "--text", text]
    if lang == "en":
        py.append("--en")
    if font:
        py.append("--easy")
    if xmode:
        py += ["--ashots"] + names
    print("pygame:", " ".join(py[1:]), flush=True)
    subprocess.run(py, env=env, check=False, stdout=subprocess.DEVNULL)
    genv = dict(env, APPDATA=os.path.join(tempfile.gettempdir(), "wnb_text_scale"))
    g = [GODOT_EXE, "--path", GODOT_DIR, "--audio-driver", "Dummy", "--resolution", "1280x720", "-s",
         "res://tests/text_scale/run.gd", "--", "--test", "--aout", gd.replace("\\", "/"), "--alang", lang, "--atext", text]
    if font:
        g.append("--afont")
    if names:
        g += ["--ashots"] + names
    print("godot:", " ".join(g[5:]), flush=True)
    subprocess.run(g, env=genv, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
    res = subprocess.run([sys.executable, os.path.join(HERE, "diff.py"), ref, gd], capture_output=True, text=True,
                         encoding="utf-8")
    open(os.path.join(out, "diff.txt"), "w", encoding="utf-8").write(res.stdout)
    rows = [ln for ln in res.stdout.splitlines() if ln.strip()]
    vals = [float(r.split()[0]) for r in rows]
    print(res.stdout[:3000])
    print(f"TEXT SCALE {tag}: {len(rows)} пар снимков, средняя разница {sum(vals) / max(1, len(vals)):.2f} из 255 → {out}")


if __name__ == "__main__":
    main()
