"""Собирает assets/lang_en.json из en1..en4.json и проверяет покрытие:
прогоняет все экраны игры на английском и ловит строки, оставшиеся с кириллицей."""
import os, sys, json, re, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
merged = {}
for f in sorted(glob.glob(os.path.join(HERE, "en*.json"))):
    merged.update(json.load(open(f, encoding="utf-8")))
chunks = []
for f in sorted(glob.glob(os.path.join(HERE, "chunk*.json"))):
    chunks += json.load(open(f, encoding="utf-8"))
missing = [c["ru"] for c in chunks if c["ru"] not in merged]
json.dump(merged, open(os.path.join(ROOT, "assets", "lang_en.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"словарь: {len(merged)} строк, не переведено из выгрузки: {len(missing)}")
for m in missing[:10]:
    print("   нет:", m[:90])

# --- покрытие: что реально попадает на экран ---
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, ROOT)
import pygame
pygame.init()
S = pygame.display.set_mode((1280, 720))
import game
game.set_lang("en")
leaks = {}
orig_render = pygame.font.Font.render
CYR = re.compile(r"[А-Яа-яЁё]")


class SpyFont:
    def __init__(self, f):
        self.f = f

    def render(self, text, *a, **k):
        if isinstance(text, str) and CYR.search(text):
            leaks[text] = leaks.get(text, 0) + 1
        return self.f.render(text, *a, **k)

    def __getattr__(self, name):
        return getattr(self.f, name)


_orig_font = game.font
_spy_cache = {}


def spy_font(size, bold=False):
    key = (size, bold)
    if key not in _spy_cache:
        _spy_cache[key] = SpyFont(_orig_font(size, bold))
    return _spy_cache[key]


game.font = spy_font
sys.argv = [sys.argv[0]]
exec(open(os.path.join(ROOT, "art_tests", "ui_playthrough.py"), encoding="utf-8").read().split("try:\n    shot(\"title\")")[0]
     .replace("game.Game(headless=True)", "game.Game(headless=True)"), globals())
src = open(os.path.join(ROOT, "art_tests", "ui_playthrough.py"), encoding="utf-8").read()
body = src[src.index("try:\n    shot(\"title\")"):]
exec(body, globals())
# все варианты заданий, все тосты осмотра/ошибок
for base in game.ALL_JOBS:
    for v in range(len(base.get("variants", [None]))):
        g2 = game.Game(headless=True)
        g2.start_job(base["id"], v if base.get("variants") else None)
        for pid in g2.cur.get("parts", []):
            g2.inspect_part(pid); g2.draw(S)
        for st in g2.cur["steps"]:
            for txt in (st.get("instr", ""), st.get("ghost", ""), st.get("note", ""), st.get("wrongmsg", "")):
                if txt:
                    game.draw_wrapped(S, txt, (0, 0), 600)
        for d in g2.cur.get("diagnosis", []):
            game.draw_wrapped(S, d.get("text", "") + " " + d.get("why", ""), (0, 0), 600)
        for k in ("fact", "thanks", "test", "symptom", "intro", "title", "client"):
            if g2.cur.get(k):
                game.draw_wrapped(S, g2.cur[k], (0, 0), 600)
for pg in getattr(game, "MANUAL", {}).values():
    for v in (pg.values() if isinstance(pg, dict) else [pg]):
        for t in (v if isinstance(v, list) else [v]):
            if isinstance(t, str):
                game.draw_wrapped(S, t, (0, 0), 600)
print(f"строк с кириллицей на экране: {len(leaks)}")
for t, n in sorted(leaks.items(), key=lambda x: -x[1])[:60]:
    print("   ", repr(t[:100]))
