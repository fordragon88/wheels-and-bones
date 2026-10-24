"""Проверка «одной кнопки» (switch access): тот же «игрок», что в keyboard_playthrough.py, но у него ОДНА кнопка.
Пункты выделяются сами (A11Y["scan"]); бот ждёт, пока выделится нужный, и коротко нажимает Пробел;
«назад» — долгое нажатие; ползунки — нажать, затем «меньше / больше / готово» по очереди.
python art_tests/switch_playthrough.py [en]"""
import os, sys
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")   # проверки — без звука (владелец слышал тесты в наушниках, 24.10)
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "keyboard_playthrough.py"), encoding="utf-8").read()
head, tail = src.split("# --- титул и вступление ---", 1)
ns = {"__name__": "__switch__", "__file__": os.path.join(HERE, "keyboard_playthrough.py")}
exec(compile(head, "keyboard_playthrough.py", "exec"), ns)
game, g, pygame, S = ns["game"], ns["g"], ns["pygame"], ns["S"]
game.A11Y["scan"] = 1
stat = dict(press=0, hold=0, wait=0)


def _iv():
    return g._scan_iv()


def _step():
    g.update(_iv() / 2 + 0.01)
    g.draw(S)
    stat["wait"] += 1


def _ev(t, k=pygame.K_SPACE):
    g.handle_event(pygame.event.Event(t, key=k, mod=0, unicode=" "))


def press(hold=False):
    _ev(pygame.KEYDOWN)
    if hold:
        g.update(game.SCAN_HOLD + 0.1)
        stat["hold"] += 1
    else:
        stat["press"] += 1
    _ev(pygame.KEYUP)
    ns["frame"]()


def _sub():
    sb = g.kb.get("scan_sub")
    c = ns["cur"]()
    return sb if (sb and c and c["key"] == sb["key"]) else None


def leave_sub():
    for _ in range(12):
        sb = _sub()
        if sb is None:
            return
        if sb["i"] == 2:
            press()
            return
        _step()
    raise AssertionError("не вышел из ползунка")


def wait_move():
    leave_sub()
    k0 = g.kb["key"]
    for _ in range(8):
        _step()
        if g.kb["key"] != k0 or len(g.kb["items"]) <= 1:
            return
    raise AssertionError(f"выделение не движется: {k0}")


def adjust(d):
    if _sub() is None:
        press()                                   # нажать на ползунок — режим «меньше / больше / готово»
    want = 0 if d < 0 else 1
    for _ in range(12):
        sb = _sub()
        assert sb is not None, "ползунок не перешёл в режим «меньше / больше»"
        if sb["i"] == want:
            press()
            return
        _step()
    raise AssertionError("не дождался «меньше/больше»")


def key(k, mod=0):
    K = pygame
    if k == K.K_DOWN:
        wait_move()
    elif k == K.K_UP:
        for _ in range(max(1, len(g.kb["items"]) - 1)):
            wait_move()
    elif k in (K.K_RETURN, K.K_KP_ENTER, K.K_SPACE):
        if ns["cur"]() is None:                   # ничего не выделено — ждём выделения, как человек
            wait_move()
            if g.scene not in ("title", "intro", "ending"):
                return                            # (клавиатура: Enter без фокуса лишь ставит фокус)
        press()
    elif k == K.K_ESCAPE:
        press(hold=True)
    elif k in (K.K_LEFT, K.K_RIGHT):
        adjust(-1 if k == K.K_LEFT else 1)
    elif k == K.K_TAB:
        c0 = ns["cur"]()
        grp = c0["group"] if c0 else None
        for _ in range(len(g.kb["items"]) + 2):
            wait_move()
            c = ns["cur"]()
            if c and c["group"] != grp:
                return
    else:                                         # F1, R и т. п. — обычные клавиши
        g.handle_event(pygame.event.Event(K.KEYDOWN, key=k, mod=mod, unicode=""))
        ns["frame"]()


ns["key"] = key
tail = tail.replace("ПРОЙДЕНО С КЛАВИАТУРЫ", "ПРОЙДЕНО ОДНОЙ КНОПКОЙ").replace("Нажатий: {presses}, ", "")
exec(compile("# --- титул и вступление ---" + tail, "keyboard_playthrough.py", "exec"), ns)
print(f"   нажатий: {stat['press']}, долгих (назад): {stat['hold']}, ожиданий выделения: {stat['wait']}")
