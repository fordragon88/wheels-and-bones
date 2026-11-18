# -*- coding: utf-8 -*-
"""Эталонные снимки экранов pygame-версии (1280×720) для сверки с переносом: godot/tests/ref/<экран>.png
  python godot/tools/ref_shots.py            (--big — текст 150 %, файлы big_<экран>.png)
Часы подменены, кадры рисуются каждый шаг (иначе сцена «стоит» в первом кадре: появления, печать реплик).
Пары снимков Godot — godot/tests/shots.gd (те же имена в godot/tests/shots/).
"""
import os, sys, random, time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "godot", "tests", "ref")
sys.path.insert(0, ROOT); os.chdir(ROOT)
import pygame
_clock = [0.0]
pygame.time.get_ticks = lambda: int(_clock[0] * 1000)
time.time = lambda: 1.7e9 + _clock[0]
random.seed(1)
pygame.init()
S = pygame.display.set_mode((1280, 720))
import game


def run(g, secs, name=None):
    for _ in range(int(secs * 30)):
        _clock[0] += 1 / 30
        g.update(1 / 30)
        g.draw(S)
    if name:
        pygame.image.save(S, os.path.join(OUT, ("big_" if BIG else "") + name + ".png"))
        print(name, g.scene, getattr(g, "phase", None))


BIG = "--big" in sys.argv
if BIG:
    game.A11Y["text"] = 3
g = game.Game(headless=True)
game.set_lang("ru")
run(g, 3, "title")
game.set_lang("en")
g.scene_t0 = g.t
run(g, 3, "title_en")
game.set_lang("ru")
g.tutorial_skipped = True
g.scene = "hub"
run(g, 3, "hub")
for jid in ("flat", "joystick"):
    g.start_job(jid, 0)
    run(g, 3, f"job_{jid}_diagnose")
    parts = g.cur["parts"]
    g.inspect_part(parts[0])
    run(g, 0.5)
    g.inspect_part(parts[1])
    s = g._m3d_state()
    s["yaw"] += 0.7
    s["t0"] = -1e9
    run(g, 1.5, f"job_{jid}_inspected")


# ---- срез 2: ремонт, мини-игры, тест-драйв, итог, мастерская с отметкой ----
def to_repair(jid, v=0):
    g.start_job(jid, v)
    run(g, 0.5)
    for pid in g.cur["parts"][:2]:
        g.inspect_part(pid)
    g.choose_diagnosis(next(i for i, o in enumerate(g.cur["diagnosis"]) if o["correct"]))
    g.toast_timer = 0
    run(g, 1.0)


def skip_until(pred):
    while g.phase == "repair" and not pred(g.cur["steps"][g.step_idx]):
        g.step_skip()
    g.toast_timer = 0


to_repair("flat")
st = g.cur["steps"][0]
g.select_tool(st["tool"])
g.do_action(st["tool"], "brake")                # не та деталь: сообщение об ошибке, инструмент в руке
run(g, 1.0, "job_flat_repair")
for jid, kind in (("flat", "pump"), ("brake", "gap"), ("spokes", "ping"), ("lift", "meter")):
    to_repair(jid)
    skip_until(lambda s: (s.get("mini") or {}).get("kind") == kind)
    s = g.cur["steps"][g.step_idx]
    g.select_tool(s["tool"])
    g.do_action(s["tool"], s["part"])
    m = g.mini_pending
    if kind == "pump":
        m["value"] = (m["cfg"]["lo"] + m["cfg"]["hi"]) // 2
    elif kind == "ping":
        m["dull"], m["tested"] = {1, 5}, {0, 1}
    g.toast_timer = 0
    run(g, 0.6, "mini_" + kind)
    g.mini_pending = None
for jid, hero in (("flat", "martin"), ("lift", "zix")):
    to_repair(jid)
    skip_until(lambda s: False)
    g.mistakes = 0
    run(g, 1.0)
    g.start_ride()
    run(g, 2.0, "ride_" + hero)
g.ride_t0 = None
g.ride_done = True
g.finish_test()
g.result_gag = game.MARTIN_TALK["good"][0]
run(g, 3.7, "result_lift")
g.scene = "hub"
g.hub_page = 0
run(g, 3, "hub_done")


# ---- срез 3: вступление, гараж, вечеринка, титры, замечания, справка F1, настройки ----
g.toast_timer = 0
g.scene = "intro"
for i in range(len(g.intro_slides)):
    g.intro_idx = i
    run(g, 2.6, f"intro_{i + 1}")
g.garage = [(j["id"], (3, 2, 1)[i % 3]) for i, j in enumerate(game.JOBS[:10])]
g.done = {jid for jid, _ in g.garage}
g.garage_open = None
g.garage_page = 0
g.scene = "garage"
run(g, 2.0, "garage")
g.garage_open = 0
run(g, 0.5, "garage_open")
g.garage_open = None
g.scene = "ending"
run(g, 3.0, "ending")
g.scene = "title"
run(g, 0.2)
g.open_credits()
run(g, 3.0, "credits")
g.scene = "hub"
run(g, 0.5)
g.open_feedback()
g.dispute_ui["reason"] = 1
g.dispute_ui["text"] = "Карточка съехала"
run(g, 0.5, "feedback_general")
g.close_dispute()
g.start_job("flat", 0)
run(g, 0.5)
for pid in g.cur["parts"][:2]:
    g.inspect_part(pid)
g.choose_diagnosis(next(i for i, o in enumerate(g.cur["diagnosis"]) if o["text"].startswith("Погнут обод")))
g.toast_timer = 0
g.open_dispute()
run(g, 0.5, "feedback_dispute")
g.close_dispute()
g.scene = "hub"
g.dispute = None
run(g, 0.5)
g.kb["help"] = True
run(g, 0.5, "help")
g.kb["help"] = False
for tab in ("sound", "graphics", "access", "game"):
    g.show_sound = True
    g.settings_tab = tab
    run(g, 0.5, "settings_" + tab)
g.show_sound = False


# ---- срез 4: Гильдия и экзамен (порядок карточек операций — как в данных, чтобы снимки сравнивались) ----
def tech(jid, exam=False):
    g.start_job(jid)
    g.step_order = [s["id"] for s in g.cur["steps"]]
    if exam:
        g.exam_mode = True
        g.ghost_line = (f"Бренна: «Экзамен. Билет — „{g.cur['title']}“. Мануал разрешён, "
                        f"подсказок не будет. Больше {game.EXAM_MAX_MISTAKES} ошибок — пересдача.»")
    g.toast_timer = 0


def tech_do(sid):
    st = g.step_by_id(sid)
    r = g.do_tech_action(st["tool"], sid)
    if r == "spec":
        for key in g._manual_pages():
            g.manual_viewed.add(key)
        g.choose_spec(next(i for i, o in enumerate(st["spec"]["options"]) if o[1]))
    elif r == "mini":
        m = g.mini_pending
        m["value"] = m["cfg"].get("lo", 0)
        g.mini_gap_check() if m["kind"] == "gap" else g.mini_pump_done()


g.done = {j["id"] for j in game.JOBS[:5]}
g.garage = []
g.exam_passed = False
g.scene = "guild"
run(g, 2.0, "guild_open")
tech("truing")
g.select_tool(g.cur["steps"][0]["tool"])
run(g, 2.0, "tech_ops")
g.open_manual()
run(g, 0.5, "tech_manual")
g.show_manual = False
spec_i = next(i for i, s in enumerate(g.cur["steps"]) if s.get("spec"))
for s in g.cur["steps"][:spec_i]:
    tech_do(s["id"])
for key in g._manual_pages():
    g.manual_viewed.add(key)
st = g.cur["steps"][spec_i]
g.do_tech_action(st["tool"], st["id"])
g.toast_timer = 0
run(g, 0.5, "tech_spec")
g.spec_pending = None
tech("toe")
mini_i = next(i for i, s in enumerate(g.cur["steps"]) if s.get("mini"))
for s in g.cur["steps"][:mini_i]:
    tech_do(s["id"])
st = g.cur["steps"][mini_i]
g.do_tech_action(st["tool"], st["id"])
g.toast_timer = 0
run(g, 0.6, "tech_mini")
g.mini_pending = None
tech("t_battery")
st = g.step_by_id("p_disc_neg")
g.do_tech_action(st["tool"], "p_disc_neg")
run(g, 1.2, "tech_failed")
tech("truing")
for s in g.cur["steps"]:
    tech_do(s["id"])
g.mistakes = 0
g.toast_timer = 0
run(g, 1.0, "tech_test")
g.start_ride()
run(g, 2.0, "tech_ride")
g.ride_t0 = None
g.ride_done = True
g.finish_test()
g.result_gag = game.MARTIN_TALK["good"][0]
run(g, 3.0, "tech_result")
g.done |= {j["id"] for j in game.TECH_JOBS}
g.scene = "guild"
run(g, 2.0, "guild_done")
tech("truing", exam=True)
run(g, 1.5, "exam_ticket")
first = g.cur["steps"][0]
for k in range(4):
    g.do_tech_action("lube", first["id"])
run(g, 1.2, "exam_failed")
tech("truing", exam=True)
for s in g.cur["steps"]:
    tech_do(s["id"])
g.ride_t0 = None
g.ride_done = True
g.finish_test()
run(g, 3.0, "exam_passed")
g.scene = "guild"
run(g, 2.0, "guild_diploma")


# ---- срез 5: Кабинет посадки (уроки, примерка, зачёт; варианты ответов — в порядке данных) ----
g.done = {"flat"}
g.seat_done = set()
g.seat_quiz_ok = False
orig = [list(q["options"]) for q in game.SEAT_QUIZ]
g.open_seating()
for q, o in zip(game.SEAT_QUIZ, orig):
    q["options"][:] = o
sc = g.seatc
M = game.SEAT_MENTOR
run(g, 2.5, "seat_lessons")
sc.update(lesson=1, demo_good=False, say=M["lesson"][1])
run(g, 2.5, "seat_lesson_slump")
sc["demo_good"] = True
run(g, 0.5, "seat_lesson_norm")
sc.update(lesson=5, demo_good=False, say=M["lesson"][5])
run(g, 2.5, "seat_lesson_measure")
sc.update(tab="fit")
g._seat_load_case(0)
run(g, 2.5, "seat_fit_troll")
c0 = game.SEAT_CASES[0]
sc["cfg"].update(depth=c0["body"]["thigh"] - 5, leg=c0["body"]["shank"], back_h=sum(c0["back"]) // 2,
                 back_a=sum(c0["angle"]) // 2)
run(g, 0.5, "seat_fit_troll_good")
g._seat_load_case(3)
run(g, 2.5, "seat_fit_golem")
g._seat_load_case(6)
sc.update(view="side", say=M["side_ok"])
run(g, 2.5, "seat_fit_dryad_side")
sc.update(tab="quiz", say=M["quiz"])
run(g, 2.5, "seat_quiz_q1")
g._seat_quiz_pick(next(i for i, o in enumerate(game.SEAT_QUIZ[0]["options"]) if not o[1]))
run(g, 0.5)
sc["fix_t0"] = g.t - 0.35 + 1 / 30
run(g, 1 / 30, "seat_quiz_mid")
sc["fix_t0"] = g.t - 5
run(g, 2.5, "seat_quiz_wrong")
sc.update(quiz=1, picked=None)
g._seat_quiz_pick(next(i for i, o in enumerate(game.SEAT_QUIZ[1]["options"]) if o[1]))
run(g, 2.5, "seat_quiz_right")
sc.update(quiz=3, picked=None)
run(g, 1.0, "seat_quiz_myth")
sc.update(quiz_done=True, score=6, say=M["pass"])
g.seat_quiz_ok = True
run(g, 2.5, "seat_quiz_pass")


# ---- срез 5, часть 3: виды спереди и сверху (верная посадка — перебором по одному ползунку, как в shots.gd) ----
def seat_solve(case, keys, cfg):
    cfg = dict(cfg)
    score = lambda x: sum(1 for c in game.Game.seat_eval(case, x)[0] if c[1])     # noqa: E731
    total = len(game.Game.seat_eval(case, cfg)[0])
    for _ in range(6):
        for k in keys:
            lo, hi = game.SEAT_SLIDERS[k][2], game.SEAT_SLIDERS[k][3]
            best, best_v = score(cfg), cfg[k]
            for v in range(lo, hi + 1):
                s_ = score(dict(cfg, **{k: v}))
                if s_ > best:
                    best, best_v = s_, v
            cfg[k] = best_v
        if score(cfg) == total:
            break
    return cfg


sc.update(tab="fit", quiz_done=False, score=0)
for ci, nm in ((6, "dryad"), (7, "owl"), (8, "orc")):
    g._seat_load_case(ci)
    run(g, 2.5, f"seat_fit_{nm}")
    c_ = game.SEAT_CASES[ci]
    keys_ = c_.get("sliders") or ["depth", "leg", "back_h", "back_a"] + (["tilt"] if c_.get("tilt") else [])
    sc["cfg"].update(seat_solve(c_, keys_, sc["cfg"]))
    run(g, 0.5, f"seat_fit_{nm}_good")
sc.update(tab="lessons", lesson=3, demo_good=False, say=M["lesson"][3])
run(g, 2.5, "seat_lesson_front")
sc["demo_good"] = True
run(g, 0.5, "seat_lesson_front_norm")
sc.update(tab="quiz", quiz=5, picked=None, say=M["quiz"])
run(g, 2.5, "seat_quiz_wedge")
g._seat_quiz_pick(next(i for i, o in enumerate(game.SEAT_QUIZ[5]["options"]) if o[1]))
sc["fix_t0"] = g.t - 5
run(g, 2.5, "seat_quiz_wedge_after")
sc.update(quiz=6, picked=None)
run(g, 1.0, "seat_quiz_pads")
g._seat_quiz_pick(next(i for i, o in enumerate(game.SEAT_QUIZ[6]["options"]) if not o[1]))
sc["fix_t0"] = g.t - 5
run(g, 2.5, "seat_quiz_pads_after")
