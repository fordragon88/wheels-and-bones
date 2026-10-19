"""Бот проходит всю игру через интерфейс (клики по настоящим кнопкам), как игрок.
Все 9 заданий, Гильдия (3 про-задания), экзамен, финал, гараж. Снимает каждый
новый экран в art_tests/audit_shots/. python art_tests/ui_playthrough.py"""
import os, sys, traceback
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pygame
pygame.init()
S = pygame.display.set_mode((1280, 720))
import game

SHOTS = os.path.join(HERE, "audit_shots")
os.makedirs(SHOTS, exist_ok=True)
MOUSE = [640, 360]
pygame.mouse.get_pos = lambda: tuple(MOUSE)
g = game.Game(headless=True)
log, seen = [], set()


def tick(n=3):
    for _ in range(n):
        g.update(1 / 30)
        g.draw(S)


def shot(tag):
    key = tag
    if key in seen:
        return
    seen.add(key)
    tick(40)
    pygame.image.save(S, os.path.join(SHOTS, f"{len(seen):02d}_{tag}.png"))


def click(pos, label=""):
    MOUSE[:] = [int(pos[0]), int(pos[1])]
    g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=tuple(MOUSE), rel=(0, 0), buttons=(0, 0, 0)))
    tick(2)
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=tuple(MOUSE)))
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=tuple(MOUSE)))
    tick(3)


def esc():
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0))
    tick(2)


def rect_of(pairs, key):
    for k, r in pairs:
        if k == key:
            return r
    return None


def solve_mini():
    m = g.mini_pending
    shot("mini_" + m["kind"])
    k, cfg = m["kind"], m["cfg"]
    if k == "pump":
        b_pump, b_done = g._mini_pump_rects()
        for _ in range(60):
            if g.mini_pending is None:
                return
            v = g.mini_pending["value"]
            click(b_done.center if cfg["lo"] <= v <= cfg["hi"] or v > cfg["hi"] else b_pump.center)
    elif k == "gap":
        g.mini_pending["value"] = (cfg["lo"] + cfg["hi"]) / 2
        click(g._mini_gap_check_rect().center)
    elif k == "ping":
        for i, r in g._mini_ping_spots():
            if g.mini_pending is None:
                return
            if i in g.mini_pending["dull"]:
                click(r.center)
    elif k == "meter":
        ci = next(i for i, o in enumerate(cfg["options"]) if o[1])
        click(rect_of(g._mini_meter_rects(), ci).center)
    assert g.mini_pending is None, "мини-игра не решилась кликами"


def play_base_job(jid):
    if not (g.scene == "job" and g.cur["id"] == jid):      # туториал открывается сразу после интро
        assert g.scene == "hub", g.scene
        for _ in range(g._hub_pages()):                     # листаем очередь стрелкой, как игрок
            if jid in dict(g._hub_job_rects()):
                break
            click(g._hub_arrow_rects()[1][1].center)
        click(rect_of(g._hub_job_rects(), jid).center)
    assert g.scene == "job", f"{jid}: клик по карточке не открыл задание"
    shot("job_diag")
    # осмотр: две детали — одна по схеме, одна по списку
    tick(40)                                              # 3D-коляска доворачивается к зрителю (~1 с) — кружки едут
    spots = g._chair_hotspots()
    if spots:
        click(spots[0][1:3])
    click(g._part_rects()[-1][1].center)
    # 3D прямо на экране задания: потянуть коляску мышью (за пустое место окна) — поворот
    if g._m3d_mesh() is not None:
        cr = g._chair_rect()
        p0 = (cr.x + 6, cr.y + 6)
        yaw0 = g._m3d_view()[0]
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=p0))
        g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(p0[0] + 120, p0[1]), rel=(120, 0), buttons=(1, 0, 0)))
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(p0[0] + 120, p0[1])))
        assert abs(g._m3d_view()[0] - yaw0) > 0.5, "коляска не повернулась от перетаскивания"
        tick(10)
        shot("m3d_" + g.cur["kind"])
    # диагноз
    ci = next(i for i, d in enumerate(g.cur["diagnosis"]) if d["correct"])
    click(rect_of(g._diag_rects(), ci).center)
    assert g.phase == "repair", f"{jid}: верный диагноз не принят (осмотрено {g.inspected})"
    shot("job_repair")
    for n in range(100):
        if g.phase != "repair":
            break
        if g.mini_pending:
            solve_mini()
            continue
        st = g.cur["steps"][g.step_idx]
        click(rect_of(g._tool_rects(), st["tool"]).center)
        assert g.sel_tool == st["tool"], "клик по иконке не выбрал инструмент"
        pos = None
        for pid, x, y, r in g._chair_hotspots():
            if pid == st["part"]:
                pos = (x, y)
        if pos is None:
            pos = rect_of(g._part_rects(), st["part"]).center
        before = (g.step_idx, g.mistakes)
        click(pos)
        if (g.step_idx, g.mistakes) == before and not g.mini_pending:
            # клик по хотспоту мог попасть в соседний — пробуем строку списка
            click(rect_of(g._part_rects(), st["part"]).center)
        tick(30)
    assert g.phase == "test", f"{jid}: не дошли до теста (шаг {g.step_idx})"
    shot("job_test")
    click(g._test_btn_rect().center)
    tick(12)
    shot("ride")
    tick(80)
    assert g.scene == "result", f"{jid}: после тест-драйва не открылся результат ({g.scene})"
    shot("result")
    log.append((jid, g.mistakes))
    click(g._result_btn_rect().center)


def play_tech_job(jid):
    assert g.scene == "guild"
    click(rect_of(g._guild_job_rects(), jid).center)
    assert g.scene == "job" and g.cur["id"] == jid
    shot("tech_job")
    for n in range(200):
        if g.phase != "repair":
            break
        if g.mini_pending:
            solve_mini()
            continue
        if g.spec_pending:
            shot("spec")
            click(g._spec_manual_rect().center)
            if g.show_manual:
                shot("manual")
                esc()
            ci = next(i for i, o in enumerate(g.spec_pending["spec"]["options"]) if o[1])
            click(g._spec_option_rects()[ci][1].center if isinstance(g._spec_option_rects()[ci], tuple)
                  else g._spec_option_rects()[ci].center)
            continue
        ready = [s for s in g.cur["steps"] if s["id"] not in g.done_steps
                 and all(a in g.done_steps for a in s.get("after", []))]
        st = ready[0]
        click(rect_of(g._tool_rects(), st["tool"]).center)
        click(rect_of(g._op_rects(), st["id"]).center)
        tick(30)
    assert g.phase == "test", f"{jid}: tech не дошло до теста"
    click(g._test_btn_rect().center)
    tick(100)
    assert g.scene in ("result", "exam_result"), g.scene
    shot("tech_result" if g.scene == "result" else "exam_result")
    click(g._result_btn_rect().center)


try:
    shot("title")
    click((640, 400))
    while g.scene == "intro":
        shot("intro")
        click((640, 400))
    shot("hub_start")
    order = ["flat"] + [j["id"] for j in game.JOBS if j["id"] != "flat"]
    for jid in order:
        play_base_job(jid)
        if g.scene == "ending":
            break
    if g.scene != "hub":
        click((640, 600))                                   # финал -> гараж
    if g.scene == "garage":                                 # из гаража — кнопкой «Назад» в мастерскую
        click(g._back_rect().center)
    assert g.scene == "hub", g.scene
    shot("hub_all_done")
    click(g._hub_garage_rect().center)
    assert g.scene == "garage"
    shot("garage_full")
    click(g._garage_card_rects()[0][1].center)              # карточка -> окно с полным уроком
    assert g.garage_open is not None, "карточка гаража не открыла урок"
    shot("garage_lesson")
    click((640, 360))                                       # любой клик закрывает окно
    assert g.garage_open is None
    if g._garage_arrow_rects():
        click(g._garage_arrow_rects()[1][1].center)
        shot("garage_page2")
    click(g._back_rect().center)
    click(g._hub_guild_rect().center)
    assert g.scene == "guild", f"Гильдия не открылась ({g.scene})"
    shot("guild")
    for tj in game.TECH_JOBS:
        play_tech_job(tj["id"])
    shot("guild_all_done")
    click(g._guild_exam_rect().center)
    assert g.scene == "job" and g.exam_mode, "экзамен не начался"
    play_tech_job.__wrapped__ = None
    # экзамен: тот же проход по свободному порядку
    jid = g.cur["id"]
    g.scene = "guild"; g.scene = "job"     # уже внутри задания
    for n in range(200):
        if g.phase != "repair":
            break
        if g.mini_pending:
            solve_mini(); continue
        if g.spec_pending:
            click(g._spec_manual_rect().center)
            if g.show_manual:
                esc()
            ci = next(i for i, o in enumerate(g.spec_pending["spec"]["options"]) if o[1])
            r = g._spec_option_rects()[ci]
            click((r[1] if isinstance(r, tuple) else r).center)
            continue
        ready = [s for s in g.cur["steps"] if s["id"] not in g.done_steps
                 and all(a in g.done_steps for a in s.get("after", []))]
        st = ready[0]
        click(rect_of(g._tool_rects(), st["tool"]).center)
        click(rect_of(g._op_rects(), st["id"]).center)
        tick(30)
    click(g._test_btn_rect().center)
    tick(100)
    shot("exam_result")
    click(g._result_btn_rect().center)
    click(g._guild_back_rect().center)
    if g.scene == "hub":
        click(g._hub_ending_rect().center)
    shot("ending")
    print("ПРОЙДЕНО: все задания, Гильдия, экзамен, финал. Ошибок по ходу:", log)
except Exception:
    print("СБОЙ на сцене", g.scene, "фаза", getattr(g, "phase", None))
    traceback.print_exc()
print("экранов снято:", len(seen))
