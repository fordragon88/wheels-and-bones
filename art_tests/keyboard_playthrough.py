"""Проверка доступности: «незрячий игрок» проходит всю игру ТОЛЬКО клавишами (стрелки, Tab, Enter, Esc)
и ориентируется по тому, что игра говорит (SPEECH.log) и по подписям пунктов фокуса.
python art_tests/keyboard_playthrough.py [en]"""
import os, sys, re
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init()
S = pygame.display.set_mode((1280, 720))
import game

LANG = sys.argv[1] if len(sys.argv) > 1 else "ru"
game.set_lang(LANG)
game.A11Y["on"] = False                     # голос не нужен — читаем журнал SPEECH.log
g = game.Game(headless=True)
CYR = re.compile("[А-Яа-яЁё]")
leaks = set()
presses = 0


def frame(sec=0.05):
    for _ in range(max(1, int(sec * 30))):
        g.update(1 / 30)
    g.draw(S)


def key(k, mod=0):
    global presses
    presses += 1
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod, unicode=""))
    frame()
    if LANG == "en":
        for t in game.SPEECH.log[-3:]:
            if CYR.search(t):
                leaks.add(t[:100])


def cur():
    return next((it for it in g.kb["items"] if it["key"] == g.kb["key"]), None)


def focus(pred, what=""):
    """Стрелкой вниз — пока фокус не встанет на нужный пункт (как человек, слушающий подписи)."""
    for _ in range(len(g.kb["items"]) + 2):
        c = cur()
        if c and pred(c):
            return c
        key(pygame.K_DOWN)
    raise AssertionError(f"не нашёл пункт: {what}; есть: {[it['label'][:40] for it in g.kb['items']]}")


def enter_on(pred, what=""):
    focus(pred, what)
    key(pygame.K_RETURN)


def by_key(k):
    return lambda it: it["key"] == k


def solve_mini():
    m = g.mini_pending
    cfg = m["cfg"]
    kind = m["kind"]
    if kind == "pump":
        for _ in range(60):
            if cfg["lo"] <= g.mini_pending["value"] <= cfg["hi"]:
                break
            enter_on(lambda it: it["key"][0] == "btn" and ("КАЧАТЬ" in it["label"] or "PUMP" in it["label"].upper()), "качать")
        enter_on(lambda it: it["key"][0] == "btn" and ("ГОТОВО" in it["label"] or "DONE" in it["label"].upper()
                                                       or "CHECK" in it["label"].upper()), "готово")
    elif kind == "gap":
        focus(by_key("gap"), "шкала")
        target = (cfg["lo"] + cfg["hi"]) // 2
        for _ in range(200):
            v = g.mini_pending["value"]
            if v == target:
                break
            key(pygame.K_RIGHT if v < target else pygame.K_LEFT)
        enter_on(lambda it: it["key"][0] == "btn" and it["rect"].w >= 200, "проверить")
    elif kind == "ping":
        for i in range(cfg["total"]):
            if g.mini_pending is None:
                break
            enter_on(by_key(("spoke", i)), f"спица {i}")
    elif kind == "meter":
        ci = next(i for i, o in enumerate(cfg["options"]) if o[1])
        enter_on(by_key(("meter", ci)), "вывод")
    assert g.mini_pending is None, f"мини-игра {kind} не решена"


def play_base(jid):
    g.start_job(jid)
    frame(0.3)
    job = g.cur
    for pid in job["parts"][:game.INSPECT_REQ]:
        enter_on(by_key(("part", pid)), pid)
    ok = next(i for i, o in enumerate(job["diagnosis"]) if o["correct"])
    enter_on(by_key(("diag", ok)), "диагноз")
    assert g.phase == "repair", jid
    while g.phase == "repair":
        st = job["steps"][g.step_idx]
        enter_on(by_key(("tool", st["tool"])), st["tool"])
        n0 = g.step_idx
        enter_on(by_key(("part", st["part"])), st["part"])
        if g.mini_pending:
            solve_mini()
        assert g.step_idx > n0 or g.phase != "repair", f"{jid}: шаг {n0} не выполнен"
    assert g.phase == "test"
    enter_on(lambda it: it["key"][0] == "btn", "прокатить")
    frame(game.Game.RIDE_SECS + 0.7)
    assert g.scene == "result", (jid, g.scene)
    enter_on(lambda it: it["key"][0] == "btn", "дальше")


def play_tech(jid):
    g.start_job(jid)
    frame(0.3)
    job = g.cur
    done = set()
    while g.phase == "repair":
        nxt = next(s_ for s_ in job["steps"] if s_["id"] not in done and all(a in done for a in s_["after"]))
        enter_on(by_key(("tool", nxt["tool"])), nxt["tool"])
        enter_on(by_key(("op", nxt["id"])), nxt["id"])
        if g.spec_pending:
            enter_on(lambda it: it["key"][0] == "btn" and it["rect"].x < 500, "открыть мануал")
            assert g.show_manual
            key(pygame.K_ESCAPE)
            ci = next(i for i, o in enumerate(nxt["spec"]["options"]) if o[1])
            enter_on(by_key(("spec", ci)), "спецификация")
        if g.mini_pending:
            solve_mini()
        assert nxt["id"] in g.done_steps, f"{jid}: {nxt['id']}"
        done.add(nxt["id"])
    enter_on(lambda it: it["key"][0] == "btn", "проверить")
    frame(game.Game.RIDE_SECS + 0.7)
    assert g.scene in ("result", "exam_result"), (jid, g.scene)
    key(pygame.K_ESCAPE)


# --- титул и вступление ---
frame(2.0)
assert g.scene == "title"
key(pygame.K_RETURN)
while g.scene == "intro":
    key(pygame.K_RETURN)
assert g.scene == "job" and g.cur["id"] == "flat", g.scene
g.scene = "hub"
frame()
for j in game.JOBS:
    play_base(j["id"])
    print("  ✔", j["id"], f"(нажатий всего: {presses})")
for j in game.TECH_JOBS:
    play_tech(j["id"])
    print("  ✔", j["id"])

# --- мастерская: выбрать клиента с клавиатуры ---
g.scene = "hub"; frame()
key(pygame.K_TAB)
c = cur()
assert c and c["group"] == "Клиенты", c
key(pygame.K_RETURN)
assert g.scene == "job"
key(pygame.K_ESCAPE); key(pygame.K_ESCAPE)
assert g.scene == "hub"

# --- Кабинет посадки: ползунки стрелками, проверка, зачёт ---
g.open_seating(); frame()
enter_on(lambda it: it["key"][0] == "btn" and ("ПРИМЕРКА" in it["label"].upper() or "FIT" in it["label"].upper()), "вкладка примерка")
assert g.seatc["tab"] == "fit"
case = game.SEAT_CASES[g.seatc["case"]]
for _ in range(400):
    checks, _ = g.seat_eval(case, g.seatc["cfg"])
    bad = [(k, t) for k, ok, t in checks if not ok]
    if not bad:
        break
    k = bad[0][0] if bad[0][0] in game.SEAT_SLIDERS else "leg"
    focus(by_key(("seat", k)), k)
    lo_hi = {"depth": case["body"]["thigh"] - 5, "leg": case["body"]["shank"], "back_h": sum(case["back"]) // 2,
             "back_a": sum(case["angle"]) // 2, "tilt": case.get("tilt", 0)}
    v = g.seatc["cfg"][k]
    key(pygame.K_RIGHT if v < lo_hi[k] else pygame.K_LEFT)
checks, _ = g.seat_eval(case, g.seatc["cfg"])
assert all(ok for _, ok, _ in checks), checks
enter_on(lambda it: it["key"][0] == "btn" and it["rect"].y > 600, "проверить посадку")
assert g.seatc["solved"]
print("  ✔ примерка")

# --- настройки: вкладка «Доступность» с клавиатуры ---
g.scene = "hub"; frame()
enter_on(by_key("settings"), "настройки")
assert g.show_sound
enter_on(by_key(("tab", "access")), "вкладка доступность")
before = game.A11Y["contrast"]
enter_on(by_key(("acc", "contrast")), "контраст")
assert game.A11Y["contrast"] != before
key(pygame.K_RETURN)
game.A11Y["contrast"] = before
key(pygame.K_ESCAPE)
assert not g.show_sound
# --- справка F1 и повтор R ---
key(pygame.K_F1); assert g.kb["help"]; key(pygame.K_ESCAPE); assert not g.kb["help"]
game.SPEECH.log.clear(); key(pygame.K_r); assert game.SPEECH.log, "R молчит"

print(f"ПРОЙДЕНО С КЛАВИАТУРЫ: {len(game.JOBS)} заданий, {len(game.TECH_JOBS)} Гильдии, примерка, настройки. "
      f"Нажатий: {presses}, фраз озвучки: {len(game.SPEECH.log)}")
if LANG == "en":
    print("кириллица в озвучке:", len(leaks))
    for t in sorted(leaks)[:15]:
        print("   ", t)
