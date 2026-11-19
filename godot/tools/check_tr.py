# -*- coding: utf-8 -*-
"""Сверка перевода Godot (Loc.t) с tr() pygame-версии на всех строках, которые проверила самопроверка.
  D:\\Godot\\Godot_v4.7.2-stable_win64_console.exe --headless --path godot -s res://tests/selftest.gd -- --test --dump-tr <файл>
  python godot/tools/check_tr.py <файл>
Строки только из переноса (godot/i18n/lang_en_port.json) pygame не знает — они пропускаются.
"""
import json, os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import pygame
pygame.init()
pygame.display.set_mode((1280, 720))
import game

godot = json.load(open(sys.argv[1], encoding="utf-8"))
port = json.load(open(os.path.join(ROOT, "godot", "i18n", "lang_en_port.json"), encoding="utf-8"))
import re
port_rx = [re.compile(".*".join(re.escape(x) for x in re.split(r"\{\d+\}", p))) for p in port if re.search(r"\{\d+\}", p)]
game.set_lang("en")
bad = 0
for ru, en in godot.items():
    if any(p in ru for p in port) or any(r.search(ru) for r in port_rx):    # шаблоны переноса: «… {0} …»
        continue
    want = game.tr(ru)
    if want != en:
        bad += 1
        sys.stdout.buffer.write(f"≠ {ru!r}\n   pygame {want!r}\n   godot  {en!r}\n".encode("utf-8"))
print(f"{len(godot)} строк, расхождений: {bad}")
sys.exit(1 if bad else 0)
