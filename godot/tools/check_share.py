# -*- coding: utf-8 -*-
"""Коды и ссылки Godot → pygame: всё, что выдала самопроверка Godot (godot/tests/out/share_godot.json), читает game.py.
  D:\\Godot\\Godot_v4.7.2-stable_win64_console.exe --headless --path godot -s res://tests/selftest.gd -- --test
  python godot/tools/check_share.py [файл]
Коды: game.share_decode даёт тот же вид и те же данные, их принимают progress_unpack / assign_parse / result_unpack.
Ссылки: game.parse_link и game.assign_parse дают то же, что ждёт Godot. Обратное направление (коды game.py → Godot)
проверяет сама самопроверка по content/share_ref.json.
"""
import json, os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import pygame
pygame.init()
pygame.display.set_mode((1280, 720))
import game

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "godot", "tests", "out", "share_godot.json")
items = json.load(open(path, encoding="utf-8"))
bad = 0
n = {"P": 0, "J": 0, "R": 0, "link": 0}


def fail(msg):
    global bad
    bad += 1
    sys.stdout.buffer.write(("≠ " + msg + "\n").encode("utf-8"))


for it in items:
    if it["what"] == "code":
        got = game.share_decode(it["code"])
        if not got or got[0] != it["kind"] or got[1] != it["data"]:
            fail(f"код {it['kind']} {it['code'][:40]}…: game.py прочитала {got}, ждали {it['data']}")
            continue
        kind, d = got
        ok = (game.progress_unpack(d) is not None if kind == "P" else
              game.assign_parse({"jobs": d.get("j"), "seat": d.get("s"), "from": d.get("f"), "title": d.get("ti")}) is not None
              if kind == "J" else game.result_unpack(d) is not None)
        if not ok:
            fail(f"код {kind}: данные не приняты распаковкой game.py: {d}")
            continue
        n[kind] += 1
    else:
        p = game.parse_link(it["link"])
        a = game.assign_parse(p)
        if p != it["params"] or a != it["assign"]:
            fail(f"ссылка {it['link']}: game.py {p} / {a}, ждали {it['params']} / {it['assign']}")
            continue
        n["link"] += 1
sys.stdout.buffer.write(f"Godot → game.py: кодов P {n['P']}, J {n['J']}, R {n['R']}, ссылок {n['link']} из {len(items)}; расхождений: {bad}\n".encode("utf-8"))
sys.exit(1 if bad else 0)
