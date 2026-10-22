"""Проверка БРАУЗЕРНОЙ версии в настоящем браузере (Playwright, Chromium) — то, что selftest и боты не видят
(они гоняют настольную версию): загрузка арта, размер холста, касания, геймпад, титры, поле отзыва.

Идея — из скилла develop-web-game (OpenAI, Apache 2.0): после изменения запускать игру в браузере короткими
сценариями, сверять состояние игры (у нас — window.wnbState, Game.debug_state) и скриншоты, ловить ошибки консоли.

python art_tests/web_smoke.py            — собрать (build_web.py --serve), проверить, остановить сервер
python art_tests/web_smoke.py --no-build — сервер на :8000 уже запущен (build_web.py --serve)
Скриншоты — art_tests/web_shots/ (их надо открыть и посмотреть). Код выхода 1 — что-то не так.
Замечания в таблицу не уходят: запросы к script.google.com блокируются, «Отправить» не нажимается."""
import asyncio, json, os, subprocess, sys, time, urllib.request
from playwright.async_api import async_playwright

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SHOTS = os.path.join(ROOT, "art_tests", "web_shots")
URL = os.environ.get("WNB_URL", "http://localhost:8000/")      # WNB_URL — проверить выложенный сайт (с --no-build)
APK = os.path.join(ROOT, "web_build", "wheels_and_bones", "build", "web", "wheels_and_bones.apk")
ASSETS = set(os.listdir(os.path.join(ROOT, "assets")))
fails, notes = [], []


def check(ok, what):
    (notes if ok else fails).append(("ok   " if ok else "FAIL ") + what)
    print(("  ok   " if ok else "  FAIL ") + what, flush=True)
    return ok


def serve():
    """Собрать и запустить локальный сервер pygbag; дождаться свежего пакета."""
    t0 = time.time()
    proc = subprocess.Popen([sys.executable, "build_web.py", "--serve"], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(600):
        try:
            if os.path.getmtime(APK) > t0 and urllib.request.urlopen(URL, timeout=2).status == 200:
                time.sleep(8)                         # пакет мог ещё дописываться — первый сценарий получал пустую страницу
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.kill()
    raise SystemExit("сервер не поднялся")


class Page:
    def __init__(self, pg, name):
        self.pg, self.name, self.errors = pg, name, []
        pg.on("console", self._console)
        pg.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))

    def _console(self, m):
        t = m.text
        if "Traceback" in t or ("Error" in t and ("File \"" in t or "line " in t)):
            self.errors.append(t[:300])

    async def state(self):
        s = await asyncio.wait_for(self.pg.evaluate("window.wnbState || ''"), 15)   # страница зависла — FAIL, не вечное ожидание
        return json.loads(s) if s else {}

    async def wait(self, pred, what, timeout=20):
        st = {}
        for _ in range(int(timeout * 4)):
            st = await self.state()
            if st and pred(st):
                return st
            await self.pg.wait_for_timeout(250)
        check(False, f"{self.name}: {what} (состояние: {st})")
        return st

    async def canvas(self):
        return await self.pg.evaluate("(()=>{const c=document.getElementById('canvas');const r=c.getBoundingClientRect();"
                                      "return [r.left,r.top,r.width,r.height,c.width,c.height,devicePixelRatio]})()")

    async def at(self, x, y):
        """Логические 1280×720 -> точка на странице."""
        r = await self.canvas()
        return r[0] + x * r[2] / 1280, r[1] + y * r[3] / 720

    async def click(self, x, y, wait=900):
        await self.pg.mouse.click(*(await self.at(x, y)))
        await self.pg.wait_for_timeout(wait)

    async def tap(self, x, y, wait=900):
        await self.pg.touchscreen.tap(*(await self.at(x, y)))
        await self.pg.wait_for_timeout(wait)

    async def key(self, k, wait=600):
        await self.pg.keyboard.press(k)
        await self.pg.wait_for_timeout(wait)

    async def shot(self, tag):
        try:                                          # снимок в headless иногда виснет — не роняем весь прогон
            await self.pg.screenshot(path=os.path.join(SHOTS, f"{self.name}_{tag}.png"), timeout=20000)
        except Exception as e:
            print(f"  ..   {self.name}: снимок {tag} не снят ({type(e).__name__})", flush=True)

    async def boot(self, touch=False):
        await self.pg.route("**/script.google.com/**", lambda r: r.abort())
        await self.pg.goto(URL)
        await self.pg.wait_for_timeout(6000)
        vw = await self.pg.evaluate("[innerWidth, innerHeight]")
        if touch:
            await self.pg.touchscreen.tap(vw[0] / 2, vw[1] / 2)   # pygbag ждёт первое действие
        else:
            await self.pg.mouse.click(vw[0] / 2, vw[1] / 2)
        st = await self.wait(lambda s: s.get("scene") in ("title", "intro"), "игра запустилась", 90)
        await self.pg.wait_for_timeout(2500)                     # «авто» подстраивает холст
        for _ in range(3):                                       # первое касание прошло в игру — на титул (Esc,
            if (await self.state()).get("scene") != "intro":     # нажатый ровно во время смены размера холста,
                break                                            # может потеряться — повтор)
            await self.key("Escape", 1500)
        return await self.wait(lambda s: s.get("scene") == "title", "титул")

    async def check_canvas(self):
        await self.pg.wait_for_timeout(2500)
        c = await self.canvas()
        want = c[2] * c[6]
        check(abs(c[4] - want) <= 20, f"{self.name}: холст {c[4]}×{c[5]} = окно {round(want)}×{round(c[3] * c[6])} px")

    async def check_art(self):
        st = await self.state()
        miss = [m for m in st.get("missing", []) if m in ASSETS or m[:-4] + ".jpg" in ASSETS]
        check(not miss, f"{self.name}: весь арт загрузился" + (f" (заглушки: {miss})" if miss else ""))

    def check_console(self):
        check(not self.errors, f"{self.name}: ошибок Python/JS в консоли нет"
              + (f" — {self.errors[:2]}" if self.errors else ""))


async def desktop(b, name, w, h, dpr):
    ctx = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr)
    p = Page(await ctx.new_page(), name)
    await p.boot()
    await p.check_canvas()
    await p.shot("1_title")
    await p.click(525, 540)                                      # «ТИТРЫ» (рядом — «Поддержать GOAT»)
    await p.wait(lambda s: s["scene"] == "credits", "титры открылись")
    await p.pg.wait_for_timeout(1200)
    await p.shot("2_credits")
    await p.key("Escape")
    await p.wait(lambda s: s["scene"] == "title", "из титров — на титул")
    await p.click(640, 470)                                      # начать
    await p.wait(lambda s: s["scene"] == "intro", "вступление")
    await p.click(1125, 667, 2000)                               # пропустить обучение
    await p.wait(lambda s: s["scene"] == "hub", "мастерская")
    await p.shot("3_hub")
    await p.check_art()
    await p.click(160, 250, 1500)                                # Мартин
    await p.wait(lambda s: s["scene"] == "job" and s["job"] == "flat", "задание Мартина")
    await p.pg.wait_for_timeout(4000)                            # кадры поворота подгружаются с сайта
    await p.shot("4_job")
    await p.key("F1")
    await p.wait(lambda s: s["help"], "справка F1")
    await p.key("Escape")
    n1 = (await p.state()).get("tt_frames", 0)
    await p.key("Escape", 300); await p.key("Escape", 1200)     # двойной Esc — из задания в мастерскую
    await p.wait(lambda s: s["scene"] == "hub", "двойной Esc — в мастерскую")
    await p.click(374, 250, 1500)                                # Элин — другая коляска
    await p.wait(lambda s: s["scene"] == "job" and s["job"] == "caster", "задание Элин")
    await p.pg.wait_for_timeout(4000)
    n2 = (await p.state()).get("tt_frames", 0)
    check(0 < n2 <= 36 + 8, f"{p.name}: в памяти кадры только одной коляски ({n1} → {n2})")
    p.check_console()
    await ctx.close()


async def phone(b):
    ctx = await b.new_context(viewport={"width": 740, "height": 360}, is_mobile=True, has_touch=True,
                              device_scale_factor=2, screen={"width": 740, "height": 360})
    p = Page(await ctx.new_page(), "phone")
    await p.boot(touch=True)
    await p.check_canvas()
    st = await p.state()
    check(st.get("touch"), "phone: сенсорный режим включён")
    await p.tap(640, 470)
    await p.wait(lambda s: s["scene"] == "intro", "касание «начать» — вступление, без двойного срабатывания")
    st = await p.state()
    await p.tap(1125, 667, 2000)
    await p.wait(lambda s: s["scene"] == "hub", "касание «пропустить обучение»")
    await p.tap(160, 250, 1500)
    await p.wait(lambda s: s["scene"] == "job", "касание по карточке — задание")
    await p.pg.wait_for_timeout(4000)
    await p.shot("1_job")
    before = await p.pg.screenshot()
    x0, y0 = await p.at(560, 380)
    cdp = await ctx.new_cdp_session(p.pg)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0}]})
    for i in range(1, 15):
        await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + i * 8, "y": y0}]})
        await p.pg.wait_for_timeout(40)
    await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await p.pg.wait_for_timeout(1200)
    check(before != await p.pg.screenshot(), "phone: протянуть пальцем — коляска повернулась")
    await p.shot("2_rotated")
    await p.tap(1145, 27, 1500)                                  # ⚑
    await p.wait(lambda s: s["dispute"], "окно замечания")
    ta = await p.pg.evaluate("(()=>{const t=document.getElementById('wnb-text');return t?getComputedStyle(t).display:null})()")
    check(ta == "block", "phone: поле для экранной клавиатуры показано")
    if ta == "block":
        await p.pg.tap("#wnb-text")
        await p.pg.keyboard.type("smoke test, not sent")
        await p.pg.wait_for_timeout(800)
        await p.shot("3_feedback")
    await p.tap(408, 594, 1200)                                  # ОТМЕНА (не «Отправить»!)
    await p.wait(lambda s: not s["dispute"], "«Отмена» закрыла окно")
    ta = await p.pg.evaluate("(()=>{const t=document.getElementById('wnb-text');return t?getComputedStyle(t).display:null})()")
    check(ta in (None, "none"), "phone: поле спрятано после «Отмены»")
    p.check_console()
    await ctx.close()
    ctx = await b.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              device_scale_factor=2, screen={"width": 360, "height": 740})
    p = Page(await ctx.new_page(), "portrait")
    await p.pg.route("**/script.google.com/**", lambda r: r.abort())
    await p.pg.goto(URL)
    await p.pg.wait_for_timeout(6000)
    await p.pg.touchscreen.tap(180, 370)
    await p.wait(lambda s: s.get("scene"), "игра запустилась", 90)
    disp = await p.pg.evaluate("(()=>{const o=document.getElementById('wnb-rotate');return o?getComputedStyle(o).display:null})()")
    check(disp == "flex", "portrait: просьба повернуть телефон")
    await p.shot("1_rotate")
    await ctx.close()


PAD = """(() => {
  const btn = () => ({pressed: false, touched: false, value: 0});
  const pad = {id: 'Smoke Gamepad (STANDARD GAMEPAD)', index: 0, connected: true, mapping: 'standard',
               timestamp: 0, axes: [0, 0, 0, 0], buttons: Array.from({length: 17}, btn)};
  navigator.getGamepads = () => [pad, null, null, null];
  window.__padPress = (i, on) => { pad.buttons[i].pressed = on; pad.buttons[i].value = on ? 1 : 0; pad.timestamp = performance.now(); };
  window.__padConnect = () => { const e = new Event('gamepadconnected'); e.gamepad = pad; window.dispatchEvent(e); };
})();"""


async def gamepad(b):
    ctx = await b.new_context(viewport={"width": 1280, "height": 720})
    await ctx.add_init_script(PAD)
    p = Page(await ctx.new_page(), "gamepad")
    await p.boot()
    await p.pg.evaluate("__padConnect()")
    await p.pg.wait_for_timeout(1200)

    async def press(i):
        await p.pg.evaluate(f"__padPress({i}, true)"); await p.pg.wait_for_timeout(180)
        await p.pg.evaluate(f"__padPress({i}, false)"); await p.pg.wait_for_timeout(600)
    await press(9)                                               # Start
    await p.wait(lambda s: s["settings"], "геймпад: Start — настройки")
    await press(1)                                               # B
    await p.wait(lambda s: not s["settings"], "геймпад: B — закрыть")
    await press(13)                                              # крестовина вниз
    await press(0)                                               # A
    await p.wait(lambda s: s["scene"] != "title", "геймпад: крестовина + A — из титула дальше")
    p.check_console()
    await ctx.close()


async def main():
    os.makedirs(SHOTS, exist_ok=True)
    for f in os.listdir(SHOTS):
        os.remove(os.path.join(SHOTS, f))
    async with async_playwright() as pw:
        for fn, args in ((desktop, ("site", 1100, 620, 1.0)), (desktop, ("full", 1920, 1080, 1.0)),
                         (desktop, ("laptop125", 1366, 768, 1.25)), (phone, ()), (gamepad, ())):
            print(f"— {fn.__name__} {args[0] if args else ''}", flush=True)
            b = await pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])   # свой браузер на
            try:                                                                                # сценарий
                await asyncio.wait_for(fn(b, *args), 480)
            except Exception as e:
                check(False, f"{fn.__name__} {args[:1]}: {e!r}"[:300])
            finally:
                await b.close()


if __name__ == "__main__":
    proc = None if "--no-build" in sys.argv else serve()
    try:
        asyncio.run(main())
    finally:
        if proc:
            proc.kill()
    print(f"\nWEB SMOKE: {len(notes)} ok, {len(fails)} FAIL. Скриншоты: art_tests/web_shots/ — открой и посмотри.")
    for f in fails:
        print("  ", f)
    sys.exit(1 if fails else 0)
