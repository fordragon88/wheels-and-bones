"""Проверка геймпада: тот же «игрок», что в keyboard_playthrough.py, но жмёт кнопки геймпада (события SDL
GameController: крестовина, A, B, LB/RB, Back, Y). python art_tests/pad_playthrough.py [en]"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "keyboard_playthrough.py"), encoding="utf-8").read()
head, tail = src.split("# --- титул и вступление ---", 1)
ns = {"__name__": "__pad__", "__file__": os.path.join(HERE, "keyboard_playthrough.py")}
exec(compile(head, "keyboard_playthrough.py", "exec"), ns)
game, g, pygame = ns["game"], ns["g"], ns["pygame"]
P = pygame
BTN = {P.K_UP: P.CONTROLLER_BUTTON_DPAD_UP, P.K_DOWN: P.CONTROLLER_BUTTON_DPAD_DOWN,
       P.K_LEFT: P.CONTROLLER_BUTTON_DPAD_LEFT, P.K_RIGHT: P.CONTROLLER_BUTTON_DPAD_RIGHT,
       P.K_RETURN: P.CONTROLLER_BUTTON_A, P.K_KP_ENTER: P.CONTROLLER_BUTTON_A, P.K_SPACE: P.CONTROLLER_BUTTON_A,
       P.K_ESCAPE: P.CONTROLLER_BUTTON_B, P.K_F1: P.CONTROLLER_BUTTON_BACK, P.K_r: P.CONTROLLER_BUTTON_Y,
       P.K_h: P.CONTROLLER_BUTTON_X}
stat = dict(buttons=0)


def key(k, mod=0):
    b = BTN.get(k)
    if k == P.K_TAB:
        b = P.CONTROLLER_BUTTON_LEFTSHOULDER if mod & P.KMOD_SHIFT else P.CONTROLLER_BUTTON_RIGHTSHOULDER
    if b is None:                                 # клавиш без кнопки на геймпаде в сценарии нет
        raise AssertionError(f"нет кнопки геймпада для клавиши {k}")
    stat["buttons"] += 1
    g.handle_event(P.event.Event(P.CONTROLLERBUTTONDOWN, instance_id=0, button=b))
    g.handle_event(P.event.Event(P.CONTROLLERBUTTONUP, instance_id=0, button=b))
    ns["frame"]()


ns["key"] = key
tail = tail.replace("ПРОЙДЕНО С КЛАВИАТУРЫ", "ПРОЙДЕНО С ГЕЙМПАДА").replace("Нажатий: {presses}, ", "")
exec(compile("# --- титул и вступление ---" + tail, "keyboard_playthrough.py", "exec"), ns)
print(f"   нажатий кнопок геймпада: {stat['buttons']}")
