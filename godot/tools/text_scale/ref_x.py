# -*- coding: utf-8 -*-
"""Эталонные снимки экранов pygame-версии (1280×720) для сверки с переносом: godot/tests/ref/<экран>.png
  python godot/tools/ref_shots.py            (--big — текст 150 %, файлы big_<экран>.png)
Часы подменены, кадры рисуются каждый шаг (иначе сцена «стоит» в первом кадре: появления, печать реплик).
Пары снимков Godot — godot/tests/shots.gd (те же имена в godot/tests/shots/).
"""
import os, sys, random, time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = sys.argv[sys.argv.index("--aout")+1]; os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, ROOT); os.chdir(ROOT)
import pygame
_clock = [0.0]
pygame.time.get_ticks = lambda: int(_clock[0] * 1000)
time.time = lambda: 1.7e9 + _clock[0]
random.seed(1)
pygame.init()
S = pygame.display.set_mode((1280, 720))
import game
if "--en" in sys.argv:
    _sl = game.set_lang
    game.set_lang = lambda c: _sl("en")
    _sl("en")
if "--easy" in sys.argv:
    game.A11Y["font"] = True
IDLE_T = 1.6     # петли «живых» персонажей (Бренна, Мартин во вступлении и на празднике) — кадр на это время, как
_anim_frame = game.anim_frame   # Figure.idle_t в tests/shots.gd: иначе кадр зависит от того, сколько игра уже идёт,
_IDLE_NAMES = set(game.IDLE_LOOPS.values()) | {lp for _, lp in getattr(game, "SCENE_LOOPS", {}).values()}   # и разница
game.anim_frame = lambda name, size, t, fps=game.ANIM_FPS: _anim_frame(                                     # снимков ложная
    name, size, IDLE_T if name in _IDLE_NAMES else t, fps)


def run(g, secs, name=None):
    for _ in range(int(secs * 30)):
        _clock[0] += 1 / 30
        g.update(1 / 30)
        g.draw(S)
    if name:
        pygame.image.save(S, os.path.join(OUT, name + ".png"))
        print(name, g.scene, getattr(g, "phase", None))


BIG = "--big" in sys.argv
if BIG:
    game.A11Y["text"] = 3
if "--text" in sys.argv:                          # размер текста 0..3 (100/112/125/150 %)
    game.A11Y["text"] = int(sys.argv[sys.argv.index("--text") + 1])
g = game.Game(headless=True)

g.tutorial_skipped = True
g.scene = "hub"
run(g, 1)
def tr(s): return game.tr(s) if hasattr(game, "tr") else s
def go(jid, v):
    g.start_job(jid, v); run(g, 2.5)
def repair(jid, v):
    go(jid, v)
    for pid in g.cur["parts"][:2]: g.inspect_part(pid)
    g.choose_diagnosis(next(i for i, o in enumerate(g.cur["diagnosis"]) if o["correct"]))
    run(g, 0.3)
names = sys.argv[sys.argv.index("--ashots")+1:]
for name in names:
    p = name.split(":"); kind, jid, v = p[1], p[2], int(p[3])
    g.toast_timer = 0
    if kind == "diag":
        go(jid, v)
    elif kind == "insp":
        go(jid, v); g.inspect_part(g.cur["parts"][0]); g.inspect_part(p[4]); run(g, 0.6)
    elif kind == "wrong":
        go(jid, v)
        for pid in g.cur["parts"][:2]: g.inspect_part(pid)
        ds = g.cur["diagnosis"]
        best = max((i for i, d in enumerate(ds) if not d.get("correct")), key=lambda i: len(tr(ds[i].get("feedback", ""))))
        g.choose_diagnosis(best); run(g, 0.6)
    elif kind in ("step", "done", "back", "result"):
        repair(jid, v)
        k = int(p[4]) if len(p) > 4 else 999
        if kind == "back": k += 1
        while g.phase == "repair" and g.step_idx < k: g.step_skip()
        g.toast_timer = 0
        if kind in ("step", "done") and g.phase == "repair":
            st = g.cur["steps"][g.step_idx]; g.select_tool(st["tool"])
            if kind == "done": g.complete_base_step(st)
        elif kind == "back":
            g.step_back()
        elif kind == "result":
            g.ride_t0 = None; g.ride_done = True; g.mistakes = 0; g.finish_test()
            pool = game.MARTIN_TALK["good"]; g.result_gag = max(pool, key=lambda s: len(tr(s)))
            run(g, 4.5)
    run(g, 1.0, name.replace(":", "_"))
