"""Настоящие сохранения pygame-версии для проверки переноса в Godot (шаг 6, «Перенос сохранений»).

  python godot/tools/save_fixtures.py          — записать godot/tests/saves/<случай>.save.json / .settings.json
                                                 и эталон чтения game.py: godot/tests/saves/expected.json
  python godot/tools/save_fixtures.py --godot  — Godot headless читает их (tests/save_compat.gd), сверка поле в поле
  python godot/tools/save_fixtures.py --check <dump.json>  — сверить готовый разбор Godot с эталоном

Сохранения пишет сама game.py (Game(headless=True) + её методы: finish_test, skip_tutorial, start_assignment,
assign_record, exit_assignment, save_progress, save_settings) в отдельную временную папку — save.json/settings.json
игрока не трогаются (SAVE_PATH/SETTINGS_PATH подменяются). Старый формат полей и битые файлы game.py сейчас не
пишет — их случаи составлены здесь, а эталоном служит то, как их ЧИТАЕТ game.py (load_progress/load_settings).
"""
import json
import os
import random
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "godot", "tests", "saves")


def _game():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    sys.path.insert(0, ROOT)
    import pygame
    pygame.init()
    pygame.display.set_mode((1280, 720))
    import game
    return game


def main():
    g_ = _game()
    random.seed(7)
    tmp = tempfile.mkdtemp(prefix="wnb_saves_")
    g_.SAVE_PATH = os.path.join(tmp, "save.json")
    g_.SETTINGS_PATH = os.path.join(tmp, "settings.json")
    g_.BAK_PATH = os.path.join(tmp, "save.bak.json")
    g_.FEEDBACK_PATH = os.path.join(tmp, "feedback.json")
    g_.DATA_DIR = tmp
    a11y0, vol0, disp0 = dict(g_.A11Y), dict(g_.VOL), dict(g_.DISPLAY)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT, f))

    def defaults():
        g_.A11Y.clear(); g_.A11Y.update(a11y0)
        g_.VOL.clear(); g_.VOL.update(vol0)
        g_.DISPLAY.clear(); g_.DISPLAY.update(disp0)
        g_.set_lang("en")

    def new_game():
        for p in (g_.SAVE_PATH, g_.SETTINGS_PATH):
            if os.path.exists(p):
                os.remove(p)
        defaults()
        g = g_.Game(headless=True)
        return g

    def write(g, settings=True):
        g.headless = False                       # save_* в headless молчат — пишем как настоящая игра
        g.save_progress()
        if settings:
            g.save_settings()
        g.headless = True

    def finish(g, jid, mistakes=0, exam=False):
        g.cur = next(j for j in g_.ALL_JOBS if j["id"] == jid)
        g.mistakes = mistakes
        g.exam_mode = exam
        g.headless = False
        g.finish_test()
        g.headless = True
        g.exam_mode = False

    cases = {}

    def keep(name, g=None, save_text=None, settings_text=None):
        sv = save_text if save_text is not None else open(g_.SAVE_PATH, encoding="utf-8").read()
        st = settings_text if settings_text is not None else (
            open(g_.SETTINGS_PATH, encoding="utf-8").read() if os.path.exists(g_.SETTINGS_PATH) else None)
        with open(os.path.join(OUT, name + ".save.json"), "w", encoding="utf-8", newline="") as f:
            f.write(sv)
        if st is not None:
            with open(os.path.join(OUT, name + ".settings.json"), "w", encoding="utf-8", newline="") as f:
                f.write(st)
        cases[name] = {"settings": st is not None}

    # 1. свежее: вступление пройдено, обучение не начато (прогресса нет, настройки по умолчанию)
    g = new_game()
    write(g)
    keep("fresh_intro")
    # 2. середина: несколько заданий с разными оценками, переигрывание (лучшая оценка), две примерки, обучение
    g = new_game()
    finish(g, "flat", 0)
    finish(g, "caster", 2)
    finish(g, "brake", 5)
    finish(g, "caster", 0)                       # переигрывание: в гараже — лучшая оценка
    finish(g, "lift", 3)
    seat_ids = [c["id"] for c in g_.SEAT_CASES]
    for c in seat_ids[:2]:
        g.seat_done.add(c)
    write(g)
    keep("mid")
    # 3. всё пройдено: 21 задание, 6 про-заданий, экзамен, вечеринка, Кабинет посадки (все примерки и зачёт)
    g = new_game()
    g.skip_tutorial()
    for i, j in enumerate(g_.JOBS):
        finish(g, j["id"], i % 6)
    for j in g_.TECH_JOBS:
        finish(g, j["id"], 1)
    finish(g, g_.TECH_JOBS[0]["id"], 0, exam=True)
    g.seat_done.update(seat_ids)
    g.seat_quiz_ok = True
    g.ending_seen = True
    write(g)
    keep("all_done")
    full_text = open(g_.SAVE_PATH, encoding="utf-8").read()
    # 4. ссылка-задание открыта и идёт (active), один пункт выполнен с ошибками и временем
    g = new_game()
    finish(g, "flat", 0)
    a = g_.assign_parse({"jobs": "caster,brake", "seat": seat_ids[0], "from": "Анна Петровна", "title": "Домашка №3"})
    g.start_assignment(a)
    g.assign_record("caster", 2, 95.7)
    finish(g, "brake", 1)                        # пройдено в задании: обычный прогресс не меняется
    write(g)
    keep("assign_active")
    # 5. задание выполнено, итог отправлен (sent), игрок вышел в обычную игру (active: false)
    g = new_game()
    g.skip_tutorial()
    a = g_.assign_parse({"jobs": "flat", "seat": ",".join(seat_ids[:2]), "from": "Teacher", "title": "Week 1"})
    g.start_assignment(a)
    g.assign_record("flat", 0, 61)
    g.assign_record(seat_ids[0], 3, 200)
    g.assign_record(seat_ids[1], 1, 45)
    g.assign["sent"] = True
    g.exit_assignment()
    write(g)
    keep("assign_sent")
    # 6. настройки игрока не по умолчанию: язык, размер текста, шрифт, «Без анимации», контраст, громкости,
    #    скорость голоса, озвучка, «Призрак Барти: выкл», свечение, полный экран
    g = new_game()
    finish(g, "flat", 1)
    g_.set_lang("ru")
    g_.VOL.update(master=0.35, music=0.0, sfx=0.6, amb=0.15, on=False)
    g_.A11Y.update(text=3, text_set=True, font=True, calm=True, calm_set=True, contrast=True, rate=4, on=True,
                   speech_set=True, voices=False, barty=False, instant=True, quiet=True, quiet_set=True)
    g_.DISPLAY.update(glow=False, fullscreen=True)
    write(g)
    keep("settings_custom")
    # 7. «Без анимации» снова включено игроком после выключения: calm=False, но calm_set — системное не действует
    g = new_game()
    g_.A11Y.update(calm=False, calm_set=True, text=1, text_set=True)
    g_.set_lang("en")
    write(g)
    keep("settings_calm_off")
    # 8. старый формат полей (его game.py больше не пишет, но load_progress понимает): garage парами/одиночными,
    #    done со вложенными списками, числа строками, лишние ключи, assign с done списком и числами-дробями
    old = {"done": ["flat", ["x"], "caster", 5, "nope", "spokes", "spokes"],
           "garage": [["flat", 3], ["caster"], 5, ["spokes", 2.7], ["flat", 1], "ab", ["brake", 2, 9], ["joystick", 0],
                      ["lift", True], ["brake", "2"], ["caster", "2.5"]],
           "exam_passed": "yes", "seat_done": [seat_ids[0], "no_such_case", 3], "seat_quiz_ok": 1,
           "tutorial_skipped": True, "ending_seen": None, "pygame_only_key": {"keep": [1, 2]},
           "assign": {"jobs": ["caster", "nope", "caster"], "seat": seat_ids[1] + "," + seat_ids[0], "from": "  Иван\n",
                      "title": "x" * 120, "done": ["caster", "zz"], "errors": {"caster": 2.9, "zz": 1, seat_ids[1]: -4},
                      "secs": {"caster": 1e9, seat_ids[0]: True}, "active": None, "sent": "yes"}}
    old_settings = {"volume": {"master": 0.5, "music": 2, "sfx": -1, "amb": None, "on": True}, "lang": "ru",
                    "glow": True, "a11y": {"rate": "fast", "on": "false", "instant": None, "text": 2.9, "text_set": True,
                                           "barty": False, "contrast": 1, "calm": True},
                    "fullscreen": False, "res": [1600, 900], "gpu3d": True}
    keep("old_format", save_text=json.dumps(old, ensure_ascii=False),
         settings_text=json.dumps(old_settings, ensure_ascii=False))
    # 8б. настройки ещё старее: числа и флажки строками/числами, язык заглавными
    keep("old_format2", save_text=json.dumps({"done": ["flat"], "garage": [["flat", "3"]], "exam_passed": True}),
         settings_text=json.dumps({"volume": {"master": "0.25", "music": True, "sfx": "x", "on": 0}, "lang": "RU",
                                   "glow": 0, "a11y": {"text": "2", "text_set": 1, "calm": 1, "calm_set": True, "rate": -12.5,
                                                       "barty": 0, "font": "yes"}}))
    # 9. битые файлы: обрезанное сохранение, не словарь, пустое; обрезанные настройки
    keep("broken_truncated", save_text=full_text[:len(full_text) // 2],
         settings_text=open(os.path.join(OUT, "settings_custom.settings.json"), encoding="utf-8").read()[:60])
    keep("broken_list", save_text="[\"flat\", \"caster\"]", settings_text="null")
    keep("broken_empty", save_text="", settings_text="")

    # эталон: как game.py ЧИТАЕТ каждый случай (новый Game, тот же код load_progress/load_settings)
    expected = {}
    for name, info in cases.items():
        shutil.copyfile(os.path.join(OUT, name + ".save.json"), g_.SAVE_PATH)
        sp = os.path.join(OUT, name + ".settings.json")
        if info["settings"]:
            shutil.copyfile(sp, g_.SETTINGS_PATH)
        elif os.path.exists(g_.SETTINGS_PATH):
            os.remove(g_.SETTINGS_PATH)
        defaults()
        g = g_.Game(headless=False)
        a = g.assign
        acc = dict(g_.A11Y)
        expected[name] = {
            "done": sorted(g.done), "garage": [[j, s] for j, s in g.garage], "exam_passed": g.exam_passed,
            "seat_done": sorted(g.seat_done), "seat_quiz_ok": g.seat_quiz_ok, "tutorial_skipped": g.tutorial_skipped,
            "ending_seen": g.ending_seen,
            "assign": None if not a else {k: (sorted(a[k]) if k == "done" else a[k]) for k in
                                          ("id", "jobs", "seat", "from", "title", "done", "errors", "secs", "active", "sent")},
            "volume": {k: round(float(v), 4) if k != "on" else bool(v) for k, v in g_.VOL.items()},
            "lang": g_.LANG["code"], "glow": bool(g_.DISPLAY["glow"]),
            "a11y": {k: acc[k] for k in ("on", "voices", "rate", "contrast", "instant", "speech_set", "text", "text_set",
                                         "calm_set", "font", "barty", "quiet", "quiet_set")},
            "calm": acc["calm"] if acc.get("calm_set") else "system",   # без calm_set — как в системе (пункт 4)
        }
        for p in (g_.SAVE_PATH + ".bad",):
            if os.path.exists(p):
                os.remove(p)
    defaults()
    with open(os.path.join(OUT, "expected.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(expected, f, ensure_ascii=False, indent=1, sort_keys=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"сохранений: {len(cases)} → {OUT}")


def norm(v):
    """Числа JSON у Godot — дроби: 3.0 и 3 — одно и то же."""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    return v


def check(dump_path, web_only=False):
    exp = json.load(open(os.path.join(OUT, "expected.json"), encoding="utf-8"))
    got = json.load(open(dump_path, encoding="utf-8-sig"))
    got.pop("_calm_priority", None)
    bad = compare(exp, got)
    for b in bad:
        print("  РАЗНИЦА " + b)
    print(f"SAVE COMPAT: {len(exp)} сохранений, полей сверено {sum(len(v) for v in exp.values())}, расхождений {len(bad)}")
    return not bad


def compare(exp, got, skip=()):
    bad = []
    for name, e in exp.items():
        gv = got.get(name)
        if gv is None:
            bad.append(f"{name}: нет разбора Godot")
            continue
        for k, v in e.items():
            if k in skip:
                continue
            x = norm(gv.get(k))
            if k == "volume":
                x = {a: (round(float(b), 4) if a != "on" else b) for a, b in (x or {}).items()}
            if norm(v) != x:
                bad.append(f"{name}.{k}: game.py {json.dumps(v, ensure_ascii=False)} ≠ Godot {json.dumps(x, ensure_ascii=False)}")
    return bad


GODOT = r"D:\Godot\Godot_v4.7.2-stable_win64_console.exe"


def run_godot():
    """Godot headless читает каждое сохранение (tests/save_compat.gd) → сверка с эталоном game.py."""
    import subprocess
    dump = os.path.join(tempfile.gettempdir(), "wnb_save_compat.json")
    if os.path.exists(dump):
        os.remove(dump)
    r = subprocess.run([GODOT, "--headless", "--path", os.path.join(ROOT, "godot"), "-s", "res://tests/save_compat.gd",
                        "--", "--test", "--out", dump], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not os.path.exists(dump):
        print(r.stdout[-2000:], r.stderr[-2000:])
        return False
    got = json.load(open(dump, encoding="utf-8"))
    pri = got.pop("_calm_priority", None)
    want = {"set_off": [False, False], "set_on": [True, True], "unset": [True, False], "none": [True, False]}
    print(f"  «Без анимации» [система выкл, вкл] по выбору игрока: {pri} — "
          + ("как game.py" if pri == want else f"РАЗНИЦА, ждали {want}"))
    kept = [n for n, v in got.items() if not v.get("kept")]
    for n in kept:
        print(f"  РАЗНИЦА {n}: файл сохранения изменён при чтении")
    return check(dump) and not kept and pri == want


if __name__ == "__main__":
    if "--godot" in sys.argv:
        sys.exit(0 if run_godot() else 1)
    if "--check" in sys.argv:
        sys.exit(0 if check(sys.argv[sys.argv.index("--check") + 1]) else 1)
    main()
