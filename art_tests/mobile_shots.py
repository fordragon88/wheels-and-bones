"""Снимки всех основных экранов при крупном тексте и/или сенсорном режиме (проверка «Колёс и Костей» для телефонов).
python art_tests/mobile_shots.py ru 3          — RU, TEXT_K[3] (150 %): проход ui_playthrough + окна и вкладки
python art_tests/mobile_shots.py en 3 touch    — то же с game.TOUCH["on"] = True (подсказки «тап», запас на промах)
Снимки: art_tests/mobile_shots/<lang>_<pct>[_touch]/, листы по 6 экранов — art_tests/mobile_shots/sheet_<…>_NN.png."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pygame

LANG = sys.argv[1] if len(sys.argv) > 1 else "ru"
TEXT = int(sys.argv[2]) if len(sys.argv) > 2 else 3
TOUCH = "touch" in sys.argv[3:]
ONLY_EXTRA = "extra" in sys.argv[3:]          # без прохода ui_playthrough — только окна и вкладки (быстро)

src = open(os.path.join(HERE, "ui_playthrough.py"), encoding="utf-8").read()
import game                                   # noqa: E402  (тот же модуль, что импортирует проход)
pct = int(round(game.TEXT_K[TEXT] * 100))
tag = f"{LANG}_{pct}" + ("_touch" if TOUCH else "")
OUT = os.path.join(HERE, "mobile_shots", tag)
os.makedirs(OUT, exist_ok=True)
src = src.replace('os.path.join(HERE, "audit_shots")', repr(OUT))
setup = (f"\ngame.A11Y['text'] = {TEXT}; game.A11Y['text_set'] = True; game.set_lang({LANG!r}); "
         f"game.TOUCH['on'] = {TOUCH}; game._font_cache.clear()\n")
src = src.replace("g = game.Game(headless=True)\n", "g = game.Game(headless=True)\n" + setup, 1)
if ONLY_EXTRA:
    src = src[:src.index("try:\n    shot(\"title\")")]
ns = {"__name__": "__mobile__", "__file__": os.path.join(HERE, "ui_playthrough.py")}
exec(compile(src, "ui_playthrough.py", "exec"), ns)
g, shot, click, tick, esc = ns["g"], ns["shot"], ns["click"], ns["tick"], ns["esc"]

# --- окна и вкладки, которых нет в проходе ---
try:
    g.done = {j["id"] for j in game.JOBS}
    g.scene = "hub"; g.hub_page = 0; tick(5)
    if ONLY_EXTRA:
        g.scene = "title"; shot("title")
        g.scene = "intro"; g.intro_idx = 0; shot("intro")
        g.scene = "hub"; shot("hub")
    for t in ("sound", "graphics", "access", "game"):
        g.show_sound, g.settings_tab = True, t
        shot("settings_" + t)
    g.show_sound = False
    g.toggle_help(); shot("help_f1"); g.toggle_help()
    g.open_feedback(); shot("feedback"); g.close_dispute()
    g.start_job("flat"); tick(10)
    g.open_v3d(); tick(10); shot("v3d"); g.v3d = None
    g.phase = "diagnose"
    for pid in g.cur["parts"][:3]:
        g.inspect_part(pid)
    shot("job_diag_unlocked")
    g.choose_diagnosis(next(i for i, d in enumerate(g.cur["diagnosis"]) if not d["correct"])); tick(5)
    if g.dispute is not None:
        shot("job_wrong_diag")
        g.open_dispute(); shot("dispute"); g.close_dispute()
    g.choose_diagnosis(next(i for i, d in enumerate(g.cur["diagnosis"]) if d["correct"])); tick(10)
    g.select_tool(g.cur["steps"][g.step_idx]["tool"]); shot("job_repair_tool")
    for mode in ("paste", "builder"):
        g.scene = "hub"
        try:
            g.open_share(mode); shot("share_" + mode)
        except Exception as e:
            print("share", mode, e)
        g.share_ui = None
    try:
        g.open_share("show", text="P.eJyrVspJLEnyTSxRslIqyMlMTlXSUUpJLElUslIqyc_PSVWyMjSoBQBJ5Qk3.abc123",
                     title="Код прогресса", note="Сохрани код.", kind="P", ok=True)
        shot("share_show")
    except Exception as e:
        print("share show", e)
    g.share_ui = None
    g.open_seating()
    for t in ("lessons", "fit", "quiz"):
        g.seatc["tab"] = t
        shot("seat_" + t)
    g.seatc["tab"] = "quiz"
    g._seat_quiz_pick(0); tick(60); shot("seat_quiz_answered")
    g.scene = "guild"; shot("guild_extra")
    tj = game.TECH_JOBS[0]["id"]
    g.start_job(tj); tick(10); g.open_manual(); shot("tech_manual"); g.show_manual = False
    g.fail_msg = "Ты попытался: «Снять колесо» — не выполнив шаг техники безопасности: «Выключить питание»."
    g.scene = "failed"; shot("failed")
    g.scene = "ending"; shot("ending_extra")
    g.open_credits(); shot("credits_extra")
except Exception:
    import traceback
    traceback.print_exc()

# --- листы по 6 снимков (половинный масштаб) ---
files = sorted(f for f in os.listdir(OUT) if f.endswith(".png"))
for n in range(0, len(files), 6):
    part = files[n:n + 6]
    sheet = pygame.Surface((1280, 360 * ((len(part) + 1) // 2)))
    sheet.fill((40, 40, 40))
    for i, f in enumerate(part):
        im = pygame.transform.smoothscale(pygame.image.load(os.path.join(OUT, f)), (640, 360))
        sheet.blit(im, ((i % 2) * 640, (i // 2) * 360))
    pygame.image.save(sheet, os.path.join(HERE, "mobile_shots", f"sheet_{tag}_{n // 6:02d}.png"))
print(f"{tag}: снимков {len(files)} -> {OUT}")
