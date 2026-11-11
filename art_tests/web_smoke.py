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
    try:                                              # на :8000 уже кто-то отвечает (старый сервер) — проверка ушла бы к нему
        urllib.request.urlopen(URL, timeout=2)
        print(f"  ..   ВНИМАНИЕ: {URL} уже отвечает до сборки — возможно, старый сервер; закрой его или задай WNB_URL "
              "на свой порт и --no-build", flush=True)
    except Exception:
        pass
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

    async def boot(self, touch=False, query=""):
        await self.pg.route("**/script.google.com/**", lambda r: r.abort())
        await self.pg.goto(URL + query)
        await self.pg.wait_for_timeout(6000)
        vw = await self.pg.evaluate("[innerWidth, innerHeight]")
        if touch:
            await self.pg.touchscreen.tap(vw[0] / 2, vw[1] / 2)   # pygbag ждёт первое действие
        else:
            await self.pg.mouse.click(vw[0] / 2, vw[1] / 2)
        st = await self.wait(lambda s: s.get("scene") in ("title", "intro"), "игра запустилась", 90)
        await self.pg.wait_for_timeout(2500)                     # «авто» подстраивает холст
        for _ in range(3):                                       # первое касание прошло в игру — на титул (Esc,
            if (await self.state()).get("scene") not in ("intro", "hub"):   # нажатый во время смены размера холста,
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
        miss = [m for m in st.get("missing", []) if m in ASSETS or m[:-4] + ".jpg" in ASSETS or "/" in m]   # "/" — кадры anim/
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
    # «залипшая» раскладка настоящего телефона (поворот/полный экран: ширина уже альбомная, высота ещё книжная) —
    # холст выше экрана и уехал вниз; сторож #wnb-fit обязан вернуть его в окно (10.11, телефон владельца)
    await p.pg.evaluate("(function(){var c=document.getElementById('canvas');c.style.width=innerWidth+'px';"
                        "c.style.height=Math.round(innerWidth*9/16)+'px';})()")
    await p.pg.wait_for_timeout(1800)
    fitr = await p.pg.evaluate("(function(){var r=document.getElementById('canvas').getBoundingClientRect();"
                               "return [r.top>=-2,r.bottom<=innerHeight+2,r.right<=innerWidth+2,window.wnbFitFixed||0];})()")
    check(all(fitr[:3]) and fitr[3] >= 1, f"phone: холст, вылезший за окно, сам вернулся на место ({fitr})")
    sel = await p.pg.evaluate("getComputedStyle(document.body).userSelect || getComputedStyle(document.body).webkitUserSelect")
    check(sel == "none", f"phone: текст страницы не выделяется тапом — нет панели поиска Chrome ({sel})")
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
    st = await p.state()
    check(st.get("tap_hint") and not st.get("click_hint"),
          f"phone: подсказки «tap», без «click» (tap {st.get('tap_hint')}, click {st.get('click_hint')})")
    for y in (114, 156):                                         # осмотр: две строки списка деталей
        await p.tap(1120, y, 700)
    for i in range(3):                                           # диагноз: варианты по очереди, пока не ремонт
        if (await p.state()).get("phase") == "repair":
            break
        await p.tap(1120, 378 + i * 76 + 34, 1200)
    st = await p.wait(lambda s: s.get("phase") == "repair", "phone: ремонт")
    await p.tap(18, 585, 1000)                                   # на 6 px левее первой плитки инструмента
    st = await p.state()
    check(st.get("sel_tool"), f"phone: тап рядом с плиткой инструмента выбрал её ({st.get('sel_tool')})")
    await p.shot("2b_tool_near_tap")
    fsb = await p.pg.evaluate("(()=>{const b=document.getElementById('wnb-full'),x=document.getElementById('wnb-exitfs');"
                              "return [b?b.getBoundingClientRect().width:0, x?getComputedStyle(x).display:null]})()")
    check(fsb[0] and fsb[0] <= 48 and fsb[1] in (None, "none"),
          f"phone: кнопка ⛶ компактная ({fsb[0]} px), широкой «Exit fullscreen (Esc)» нет ({fsb[1]})")
    FSQ = ("(()=>{const b=document.getElementById('wnb-full'),x=document.getElementById('wnb-exitfs');"
           "return [!!document.fullscreenElement, b.textContent, b.getAttribute('aria-label'),"
           "Math.round(b.getBoundingClientRect().width), x?getComputedStyle(x).display:null]})()")

    def fs_ok(fs):                      # значок и подпись кнопки совпадают с режимом; широкой кнопки выхода нет
        want = ("✖", "Exit fullscreen") if fs[0] else ("⛶", "Fullscreen")
        return (fs[1], fs[2]) == want and fs[3] <= 48 and fs[4] in (None, "none")
    try:                                # первое касание на телефоне уже включает полный экран (full() по touchend)
        for _ in range(2):              # туда и обратно: ⛶ ⇄ ✖ — одна и та же кнопка
            fs0 = await p.pg.evaluate(FSQ)
            check(fs_ok(fs0), f"phone: кнопка ⛶/✖ соответствует режиму, компактная ({fs0})")
            if fs0[0]:
                await p.shot("2c_fullscreen")
            await p.pg.tap("#wnb-full", timeout=3000)
            await p.pg.wait_for_timeout(1200)
            fs1 = await p.pg.evaluate(FSQ)
            if fs1[0] == fs0[0]:
                print("  ..   phone: полный экран в headless не переключился — проверка ✖ пропущена", flush=True)
                break
            check(fs_ok(fs1), f"phone: тап — режим сменился, значок тоже ({fs0[1]} -> {fs1[1]}, {fs1[2]})")
    except Exception as e:
        print(f"  ..   phone: кнопка ⛶ не нажата ({type(e).__name__})", flush=True)
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
    btn = await p.pg.evaluate("!!document.getElementById('wnb-portrait')")
    check(not btn, "portrait: у телефона кнопки «Play in portrait anyway» нет")
    await ctx.close()


ROT = "(()=>{const o=document.getElementById('wnb-rotate');return o?[getComputedStyle(o).display,o.textContent]:null})()"


async def tablet(b):
    """Планшет в книжной ориентации: просьба повернуть с кнопкой «Play in portrait anyway»; поворот — оверлей уходит."""
    ctx = await b.new_context(viewport={"width": 768, "height": 1024}, is_mobile=True, has_touch=True,
                              device_scale_factor=2, screen={"width": 768, "height": 1024})
    p = Page(await ctx.new_page(), "tablet")
    await p.pg.route("**/script.google.com/**", lambda r: r.abort())
    await p.pg.goto(URL)
    await p.pg.wait_for_timeout(6000)
    await p.pg.touchscreen.tap(384, 300)
    await p.wait(lambda s: s.get("scene"), "игра запустилась", 90)
    ov = await p.pg.evaluate(ROT)
    check(ov and ov[0] == "flex" and "Turn your device sideways" in ov[1] and "Play in portrait anyway" in ov[1],
          f"tablet: книжная — просьба повернуть с кнопкой ({ov})")
    await p.shot("1_portrait")
    await p.pg.set_viewport_size({"width": 1024, "height": 768})
    await p.pg.wait_for_timeout(1000)
    ov = await p.pg.evaluate(ROT)
    check(ov and ov[0] == "none", f"tablet: повернули в альбомную — оверлей пропал ({ov and ov[0]})")
    await p.shot("2_landscape")
    await p.pg.set_viewport_size({"width": 768, "height": 1024})
    await p.pg.wait_for_timeout(1000)
    ov = await p.pg.evaluate(ROT)
    check(ov and ov[0] == "flex", f"tablet: снова книжная — оверлей вернулся ({ov and ov[0]})")
    await p.pg.tap("#wnb-portrait")
    await p.pg.wait_for_timeout(800)
    ov = await p.pg.evaluate(ROT)
    check(ov and ov[0] == "none", f"tablet: «Play in portrait anyway» убрала оверлей ({ov and ov[0]})")
    await p.shot("3_anyway")
    st = await p.state()
    check(st.get("touch"), "tablet: сенсорный режим включён")
    p.check_console()
    await ctx.close()


async def fps(b):
    """?fps=1 — плашка fps поверх игры (для замеров на телефоне); без параметра её нет."""
    ctx = await b.new_context(viewport={"width": 1280, "height": 720})
    p = Page(await ctx.new_page(), "fps")
    st = await p.boot(query="?fps=1")
    await p.pg.wait_for_timeout(2500)
    st = await p.state()
    check(st.get("fps_hud") and not st.get("assign"), f"fps: ?fps=1 — плашка включена, в задание не попал ({st.get('fps_hud')})")
    await p.shot("1_fps")
    p.check_console()
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


def progress_code(done):
    """Код прогресса из самой игры (game.share_encode) — для проверки ?load=."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    sys.path.insert(0, ROOT)
    import game

    class P:
        pass
    g = P()
    g.done, g.garage, g.exam_passed, g.seat_done, g.seat_quiz_ok, g.tutorial_skipped = set(done), [], False, set(), False, True
    return game.share_encode("P", game.progress_pack(g))


async def links(b):
    """Ссылки: ?jobs=flat,caster — в очереди ровно два задания; «Скопировать код»; ?load=<код> — вопрос и загрузка."""
    ctx = await b.new_context(viewport={"width": 1280, "height": 720})
    await ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    p = Page(await ctx.new_page(), "links")
    await p.boot(query="?jobs=flat,caster&from=Smoke")
    st = await p.wait(lambda s: s.get("assign") and s.get("queue") == ["flat", "caster"], "?jobs=flat,caster: задание")
    check(st.get("queue") == ["flat", "caster"], f"{p.name}: в очереди два задания из ссылки ({st.get('queue')})")
    await p.click(640, 470, 1500)                                # с титула — сразу в мастерскую (без вступления)
    await p.wait(lambda s: s["scene"] == "hub", "задание: мастерская")
    await p.shot("1_hub_assign")
    await p.click(1249, 27)                                      # шестерёнка
    await p.wait(lambda s: s["settings"], "настройки")
    await p.click(833, 192)                                      # вкладка «ИГРА»
    await p.click(508, 342, 1500)                                # «СКОПИРОВАТЬ КОД»
    await p.wait(lambda s: s.get("share") == "show", "окно кода")
    code = await p.pg.evaluate("(document.getElementById('wnb-field')||{}).value || ''")
    copied = await p.pg.evaluate("window.wnbCopied|0")
    check(code.startswith("P.") and copied == 1, f"{p.name}: код прогресса скопирован ({code[:12]}…, wnbCopied={copied})")
    await p.shot("2_code")
    await p.key("Escape"); await p.key("Escape")
    p.check_console()
    await ctx.close()
    ctx = await b.new_context(viewport={"width": 1280, "height": 720})
    p = Page(await ctx.new_page(), "links_load")
    await p.boot(query="?load=" + progress_code({"flat", "caster", "brake"}))
    await p.wait(lambda s: s.get("share") == "confirm", "?load=: вопрос «загрузить прогресс?»")
    await p.shot("3_confirm")
    await p.click(852, 477, 1500)                                # «ДА»
    st = await p.wait(lambda s: s.get("share") is None and s.get("done") == 3, "?load=: прогресс загружен")
    check(st.get("done") == 3, f"{p.name}: прогресс из ссылки загружен ({st.get('done')} починено)")
    bak = await p.pg.evaluate("!!localStorage.getItem('wnb:save.bak.json')")
    check(bak, f"{p.name}: прежний прогресс сохранён (wnb:save.bak.json)")
    p.check_console()
    await ctx.close()


async def ride(b, mode):
    """Петля проезда героя качается с сайта (anim/ride_*), когда открыто его задание (не лежит в пакете игры).
    ok — кадры Мартина скачались (и только его), на тест-драйве выбрана петля и её кадры рисуются;
    404 — сайт кадры не отдаёт: тест-драйв по-старому (скользящий портрет), без ошибок в консоли."""
    ctx = await b.new_context(viewport={"width": 1280, "height": 720})
    p = Page(await ctx.new_page(), "ride_" + mode)
    asked = []
    p.pg.on("request", lambda r: asked.append(r.url) if "/anim/" in r.url else None)
    if mode == "404":
        await p.pg.route("**/anim/ride_*/**", lambda r: r.fulfill(status=404, body="no"))
    await p.boot()
    await p.click(640, 470)                                      # начать
    await p.wait(lambda s: s["scene"] == "intro", "вступление")
    await p.click(1125, 667, 2000)                               # пропустить обучение
    await p.wait(lambda s: s["scene"] == "hub", "мастерская")
    check(not asked, f"{p.name}: до задания петли проезда не качаются ({len(asked)} запросов)")
    await p.click(160, 250, 1500)                                # Мартин
    await p.wait(lambda s: s["scene"] == "job" and s["job"] == "flat", "задание Мартина")
    want = "ready" if mode == "ok" else "failed"
    st = await p.wait(lambda s: s.get("ride_web", {}).get("ride_martin") == want, f"петля Мартина: {want}", 60)
    check(st.get("ride_web", {}).get("ride_martin") == want, f"{p.name}: петля Мартина с сайта — {want} ({st.get('ride_web')})")
    mine = {"ride_martin", "magic_martin"}                      # у Мартина с 12.11 есть и волшебство на портрете
    other = sorted({u.split("/anim/")[1].split("/")[0] for u in asked} - mine)
    check("ride_martin" in st.get("ride_web", {}) and set(st.get("ride_web", {})) <= mine and not other,
          f"{p.name}: качается только петля открытого героя ({list(st.get('ride_web', {}))}, другие запросы: {other})")
    for y in (114, 156):                                         # осмотр: две строки списка деталей
        await p.click(1120, y, 700)
    for i in range(3):                                           # диагноз: варианты по очереди, пока не ремонт
        if (await p.state()).get("phase") == "repair":
            break
        await p.click(1120, 378 + i * 76 + 34, 1200)
    await p.wait(lambda s: s.get("phase") == "repair", "ремонт")
    for _ in range(12):                                          # «ШАГ ▸» — игра делает шаги сама
        if (await p.state()).get("phase") == "test":
            break
        await p.click(926, 73, 900)
    await p.wait(lambda s: s.get("phase") == "test", "тест-драйв")
    await p.pg.wait_for_timeout(2500)                            # читают «Тест-драйв» — кадры петли в память
    await p.click(640, 592, 300)                                 # «ПРОКАТИТЬ И ПРОВЕРИТЬ»
    st = await p.wait(lambda s: s.get("ride_on"), "проезд начался", 10)
    await p.pg.wait_for_timeout(1200)
    await p.shot("1_ride")
    st = await p.wait(lambda s: s.get("ride_done"), "проезд закончился — «ГОТОВО»", 15)
    if mode == "ok":
        check(st.get("ride") == "ride_martin" and st.get("ride_drawn", 0) > 10,
              f"{p.name}: проезд петлёй ride_martin, кадров нарисовано {st.get('ride_drawn')} (ride={st.get('ride')})")
    else:
        check(st.get("ride") is None and st.get("ride_drawn") == 0,
              f"{p.name}: без кадров — проезд скользящим портретом (ride={st.get('ride')}, кадров {st.get('ride_drawn')})")
    await p.shot("2_done")
    p.check_console()
    await ctx.close()


async def magic(b, mode):
    """«Волшебство» героя на портрете (anim/magic_*) качается с сайта, когда открыто его задание (в пакете — только
    индекс). ok — у Гра (bearing) кадры скачались, «волшебство» само сыграло и нарисовалось, клик по портрету —
    ещё раз; 404 — сайт кадры не отдаёт: задание как раньше, без волшебства (и по клику тоже) и без ошибок в консоли."""
    ctx = await b.new_context(viewport={"width": 1280, "height": 720})
    p = Page(await ctx.new_page(), "magic_" + mode)
    asked = []
    p.pg.on("request", lambda r: asked.append(r.url) if "/anim/" in r.url else None)
    if mode == "404":
        await p.pg.route("**/anim/magic_*/**", lambda r: r.fulfill(status=404, body="no"))
    await p.boot()
    await p.click(640, 470)                                      # начать
    await p.wait(lambda s: s["scene"] == "intro", "вступление")
    await p.click(1125, 667, 2000)                               # пропустить обучение
    await p.wait(lambda s: s["scene"] == "hub", "мастерская")
    check(not asked, f"{p.name}: до задания петли не качаются ({len(asked)} запросов)")
    await p.click(160, 500, 1500)                                # Гра (bearing) — вторая строка, первая карточка
    await p.wait(lambda s: s["scene"] == "job" and s["job"] == "bearing", "задание Гра")
    want = "ready" if mode == "ok" else "failed"
    st = await p.wait(lambda s: s.get("ride_web", {}).get("magic_gra") == want, f"волшебство Гра: {want}", 60)
    check(st.get("ride_web", {}).get("magic_gra") == want,
          f"{p.name}: волшебство Гра с сайта — {want} ({st.get('ride_web')})")
    other = sorted({u.split("/anim/")[1].split("/")[0] for u in asked} - {"magic_gra", "ride_gra"})
    check(not other, f"{p.name}: качаются только петли открытого героя (другие запросы: {other})")
    if mode == "ok":
        st = await p.wait(lambda s: s.get("magic_plays", 0) >= 1 and s.get("magic_drawn", 0) > 3, "волшебство играет", 25)
        await p.pg.wait_for_timeout(700)
        await p.shot("1_magic")
        st = await p.wait(lambda s: s.get("magic") is None and s.get("magic_plays") == 1, "волшебство доиграло", 15)
        drawn = st.get("magic_drawn", 0)
        check(drawn > 20, f"{p.name}: волшебство сыграло само, кадров нарисовано {drawn}")
        await p.click(99, 165, 300)                              # клик по портрету — ещё раз
        st = await p.wait(lambda s: s.get("magic_plays") == 2 and s.get("magic_drawn", 0) > drawn, "повтор по клику", 10)
        check(st.get("magic_plays") == 2, f"{p.name}: клик по портрету — повтор ({st.get('magic_plays')} запуска)")
        await p.wait(lambda s: s.get("magic") is None, "повтор доиграл", 15)
    else:
        await p.pg.wait_for_timeout(3000)
        await p.click(99, 165, 1500)                             # клик по портрету — ничего
        st = await p.state()
        check(st.get("scene") == "job" and not st.get("magic_plays") and not st.get("magic_drawn"),
              f"{p.name}: без кадров — без волшебства (запусков {st.get('magic_plays')}, кадров {st.get('magic_drawn')})")
    await p.shot("2_after")
    p.check_console()
    await ctx.close()


async def main():
    os.makedirs(SHOTS, exist_ok=True)
    for f in os.listdir(SHOTS):
        os.remove(os.path.join(SHOTS, f))
    async with async_playwright() as pw:
        for fn, args in ((desktop, ("site", 1100, 620, 1.0)), (desktop, ("full", 1920, 1080, 1.0)),
                         (desktop, ("laptop125", 1366, 768, 1.25)), (phone, ()), (tablet, ()), (fps, ()),
                         (gamepad, ()), (links, ()), (ride, ("ok",)), (ride, ("404",)),
                         (magic, ("ok",)), (magic, ("404",))):
            print(f"— {fn.__name__} {args[0] if args else ''}", flush=True)
            b = await pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required", "--mute-audio"])   # свой браузер на
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
        if proc:                                      # вместе с дочерним pygbag (иначе он остаётся слушать :8000)
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
            else:
                proc.kill()
    print(f"\nWEB SMOKE: {len(notes)} ok, {len(fails)} FAIL. Скриншоты: art_tests/web_shots/ — открой и посмотри.")
    for f in fails:
        print("  ", f)
    sys.exit(1 if fails else 0)
