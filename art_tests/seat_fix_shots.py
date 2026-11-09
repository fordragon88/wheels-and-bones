"""Кабинет посадки: снимки урока «Мерки» и зачёта после ответа + проверка наложения подписей мерок.
python art_tests/seat_fix_shots.py  ->  art_tests/seat_fix_shots/*.png, итог «МЕРКИ: наложений 0»"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import pygame  # noqa: E402
import game  # noqa: E402

pygame.init()
SCR = pygame.display.set_mode((game.WIDTH, game.HEIGHT))

OUT = os.path.join(ROOT, "art_tests", "seat_fix_shots")
os.makedirs(OUT, exist_ok=True)
MEASURE = ["до подколенной ямки", "−5 см", "спинка", "локоть 90°", "голень"]


def setup(lang, text, easy=False):
    game.set_lang(lang)
    game.A11Y["text"], game.A11Y["font"] = text, easy
    game._font_cache.clear()


def measure_check(g, scr, tag, shot=None):
    """Рисует урок «Мерки» и собирает прямоугольники всех строк (с плашкой, как _plate) на рисунке."""
    g.seatc.update(tab="lessons", lesson=next(i for i, l in enumerate(game.SEAT_LESSONS) if l["pose"].get("measure")),
                   demo_good=False)
    rects = []
    orig = game.draw_text

    def spy(surf, text, pos, size=18, color=game.WHITE, bold=False, center=False, right=False, alpha=255, plate=False):
        r = orig(surf, text, pos, size, color, bold, center, right, alpha, plate)
        rects.append((str(text), pygame.Rect(r).inflate(16, 8) if plate else pygame.Rect(r)))
        return r
    game.draw_text = spy
    try:
        g.draw(scr)
    finally:
        game.draw_text = orig
    if shot:
        pygame.image.save(scr, os.path.join(OUT, shot))
    cv = g._seat_canvas()
    meas = [(t, r) for t, r in rects if t in MEASURE]
    others = [(t, r) for t, r in rects if t not in MEASURE and cv.colliderect(r)]
    others.append(("кнопка «норма»", g._seat_demo_toggle_rect()))
    bad = []
    for i, (t, r) in enumerate(meas):
        if not cv.contains(r):
            bad.append(f"{tag}: «{t}» выходит за рамку")
        for t2, r2 in meas[i + 1:] + others:
            if r.colliderect(r2):
                bad.append(f"{tag}: «{t}» {tuple(r)} налезает на «{t2}» {tuple(r2)}")
    if len(meas) != len(MEASURE):
        bad.append(f"{tag}: подписей мерок {len(meas)} из {len(MEASURE)}")
    return bad


def main():
    g = game.Game(headless=True)
    g.done = {"flat"}
    g.open_seating()
    scr = SCR
    bad = []
    for lang in ("ru", "en"):
        for text in (0, 2):
            for easy in ((False, True) if lang == "en" else (False,)):
                setup(lang, text, easy)
                tag = f"{lang} {int(game.TEXT_K[text] * 100)}%" + (" лёгкий" if easy else "")
                shot = f"measure_{lang}_{int(game.TEXT_K[text] * 100)}{'_easy' if easy else ''}.png"
                bad += measure_check(g, scr, tag, shot if (lang == "en" or text == 0) else None)
    for b in bad:
        print(b)
    print(f"МЕРКИ: наложений {len(bad)}")
    # зачёт: после верного ответа (конец перехода), после неверного, середина перехода
    for lang in ("ru", "en"):
        setup(lang, 0)
        g.seatc.update(tab="quiz", quiz_done=False)
        for qi, q in enumerate(game.SEAT_QUIZ):
            right = next(i for i, o in enumerate(q["options"]) if o[1])
            wrong = next(i for i, o in enumerate(q["options"]) if not o[1])
            g.seatc.update(quiz=qi, picked=None)
            g.draw(scr)
            if lang == "ru":
                pygame.image.save(scr, os.path.join(OUT, f"quiz{qi + 1}_ru_0_question.png"))
            for kind, idx in (("right", right), ("wrong", wrong)):
                if lang == "en" and kind == "wrong":
                    continue
                g.seatc.update(quiz=qi, picked=None)
                g._seat_quiz_pick(idx)
                g.seatc["fix_t0"] = g.t - 10.0             # конец перехода
                g.draw(scr)
                pygame.image.save(scr, os.path.join(OUT, f"quiz{qi + 1}_{lang}_{kind}.png"))
                if kind == "right" and qi == 1 and lang == "ru":
                    g.seatc["fix_t0"] = g.t - game.Game.SEAT_FIX_DUR * 0.5
                    g.draw(scr)
                    pygame.image.save(scr, os.path.join(OUT, f"quiz{qi + 1}_ru_mid.png"))
    setup("ru", 0)
    print("снимки:", OUT)


if __name__ == "__main__":
    main()
