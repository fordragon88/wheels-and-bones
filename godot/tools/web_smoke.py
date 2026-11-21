# -*- coding: utf-8 -*-
"""Проверка браузерной Godot-версии в настоящем браузере (Playwright, Chromium) — по образцу art_tests/web_smoke.py.

  python godot/tools/web_smoke.py              — собрать (build_web.py), проверить, всё закрыть
  python godot/tools/web_smoke.py --no-build   — проверить готовую godot/build/web/
  python godot/tools/web_smoke.py --only boot,play   — только эти сценарии
  python godot/tools/web_smoke.py --browser firefox|webkit   — другой движок (по умолчанию chromium); снимки —
      godot/tests/web_shots/<движок>/; сценарии на CDP (perf, prof, screens) — только Chromium (пропускаются)
  WNB_URL=https://…/godot/ python godot/tools/web_smoke.py --no-build --only boot,play,perf  — выложенный сайт

Локальный сервер — на своём порту (WNB_PORT, по умолчанию 8061; не 8000/8188/8797), закрывается в конце.
Firefox и WebKit — тоже без окна и без звука: у них нет --mute-audio, поэтому Firefox — с настройкой профиля
media.volume_scale 0, а в обоих страница ещё до своих скриптов приглушает <audio> (muted при каждом play) и WebAudio
(всё, что подключается к выходу AudioContext, идёт через усиление 0) — MUTE_JS.
Браузер — Chromium без окна, с --mute-audio (у владельца в наушниках НИЧЕГО не звучит; голос браузера speechSynthesis
подменён заглушкой — на Windows он шёл бы мимо --mute-audio, через SAPI) и с видеокартой (ANGLE D3D11), чтобы кадры/с
были похожи на настоящие. Игра открывается с ?test=1: раз в 0,25 с кладёт состояние в window.wnbState (autoload/web.gd):
экран, фаза, кадры/с, кадры (скачано/в очереди/ошибки), видимые кнопки с прямоугольниками и подсказку «что нажать».
Тест жмёт кнопки НАСТОЯЩИМИ кликами/касаниями по их прямоугольникам. В сеть наружу ничего не уходит (всё, что не
127.0.0.1, обрывается). Скриншоты — godot/tests/web_shots/ (не в git), их надо открыть и посмотреть.
Код выхода 1 — что-то не так."""
import asyncio
import json
import re
import os
import sys
import time
import urllib.parse

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_web  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GODOT = os.path.dirname(HERE)
BROWSER = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chromium"
if BROWSER not in ("chromium", "firefox", "webkit"):
    sys.exit(f"--browser: chromium | firefox | webkit, а не {BROWSER}")
CHROMIUM = BROWSER == "chromium"                           # CDP (замедление процессора, экран телефона) — только здесь
SHOTS = os.path.join(GODOT, "tests", "web_shots", *([] if CHROMIUM else [BROWSER]))
PORT = int(os.environ.get("WNB_PORT", "8061"))
URL = os.environ.get("WNB_URL", f"http://127.0.0.1:{PORT}/")
GPU_ARGS = ["--mute-audio", "--autoplay-policy=user-gesture-required", "--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"]
fails, notes, metrics = [], [], {}

# Прогресс pygame-версии (localStorage «wnb:save.json» — тот же формат, что save.json)
LEGACY_SAVE = {"done": ["flat", "caster", "brake", "spokes", "lift", "joystick"],
               "garage": [["flat", 3], ["caster", 2], ["brake", 3], ["spokes", 1], ["lift", 3], ["joystick", 2]],
               "exam_passed": False, "seat_done": ["seat_bomm"], "seat_quiz_ok": False, "tutorial_skipped": True,
               "ending_seen": False, "pygame_only_key": 7}
LEGACY_SETTINGS = {"volume": {"master": 0.5, "music": 0.3, "sfx": 0.7, "amb": 0.4, "on": True}, "lang": "ru",
                   "glow": True, "a11y": {"text": 1, "text_set": True}, "fullscreen": True}

INIT_JS = """
(() => {
  // голос браузера — заглушка: фразы копятся в window.__spoken, ничего не звучит
  const said = window.__spoken = [];
  const fake = { speak(u) { said.push(u.text); }, cancel() {}, pause() {}, resume() {}, getVoices() { return []; },
                 speaking: false, pending: false, onvoiceschanged: null, addEventListener() {} };
  try { Object.defineProperty(window, 'speechSynthesis', { value: fake, configurable: true }); } catch (e) {}
  // WebKit Playwright под Windows: голоса браузера нет совсем — заглушке нужен и конструктор фразы
  if (!window.SpeechSynthesisUtterance) window.SpeechSynthesisUtterance = function (t) { this.text = t; };
})();
"""


# Firefox/WebKit: звук страницы — в ноль до её скриптов. <audio> — muted при каждом play и любой попытке снять;
# WebAudio (Godot: эффекты, фоновые петли) — всё, что подключается к выходу контекста, идёт через усиление 0.
MUTE_JS = """
(() => {
  try {
    const mp = HTMLMediaElement.prototype, md = Object.getOwnPropertyDescriptor(mp, 'muted'), play = mp.play;
    mp.play = function () { try { md.set.call(this, true); } catch (e) {} return play.apply(this, arguments); };
    Object.defineProperty(mp, 'muted', { configurable: true, get() { return md.get.call(this); },
                                         set(v) { md.set.call(this, true); } });
  } catch (e) {}
  try {
    const conn = AudioNode.prototype.connect, gains = new WeakMap();
    AudioNode.prototype.connect = function (dst, ...rest) {
      if (typeof AudioDestinationNode !== 'undefined' && dst instanceof AudioDestinationNode) {
        let g = gains.get(dst);
        if (!g) { g = dst.context.createGain(); g.gain.value = 0; conn.call(g, dst); gains.set(dst, g); }
        window.__mutedNodes = (window.__mutedNodes || 0) + 1;
        return conn.call(this, g, ...rest);
      }
      return conn.call(this, dst, ...rest);
    };
  } catch (e) {}
  window.__muted = true;
})();
"""
# Буфер обмена: что игра положила (writeText) и чем ответил браузер — Firefox/WebKit не дают тесту readText
CLIP_JS = """
(() => {
  const c = navigator.clipboard;
  if (!c || !c.writeText) return;
  const w = c.writeText.bind(c);
  c.writeText = function (t) {
    window.__clip = t; window.__clipErr = null;
    return w(t).then(r => { window.__clipOk = true; return r; }, e => { window.__clipErr = String(e); throw e; });
  };
})();
"""
# Firefox/WebKit: «экран телефона» (screen.width/height, screen.orientation.type) — без CDP, подменой (orient)
SCREEN_JS = """
(() => {
  const S = (k, p) => { const d = Object.getOwnPropertyDescriptor(p, k); if (!d || !d.get) return;
    Object.defineProperty(p, k, { configurable: true, get() { const v = window.__wnbS; return v && k in v ? v[k] : d.get.call(this); } }); };
  ['width', 'height', 'availWidth', 'availHeight'].forEach(k => S(k, Screen.prototype));
  if (window.ScreenOrientation) ['type', 'angle'].forEach(k => S(k, ScreenOrientation.prototype));
})();
"""


def check(ok, what):
    (notes if ok else fails).append(("ok   " if ok else "FAIL ") + what)
    print(("  ok   " if ok else "  FAIL ") + what, flush=True)
    return ok


def info(what):
    print("  ..   " + what, flush=True)


class Page:
    def __init__(self, ctx, pg, name, touch=False):
        self.ctx, self.pg, self.name, self.touch = ctx, pg, name, touch
        self.errors, self.console = [], []
        self.allow = []                                   # подстроки ожидаемых ошибок (404 в сценарии обрыва)
        # Windows: локальному http.server не хватает буфера сокетов, когда параллельно идут несколько прогонов —
        # кадр не пришёл, игра повторяет его сама (Frames: retry); к игре не относится
        self.allow.append("ERR_NO_BUFFER_SPACE")
        if BROWSER == "webkit":
            # проверка WebGL в WebKit строже: Godot (Compatibility) копирует кадр glBlitFramebuffer-ом, WebKit ругается
            # один раз, картинка при этом верная (снимки) — сообщение движка, не игры
            self.allow.append("glBlitFramebuffer: Read and write color attachments cannot be the same image")
        pg.on("console", self._console)
        pg.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"[:300]))

    def _console(self, m):
        t = m.text
        self.console.append(f"{m.type}: {t}"[:300])
        if m.type == "error" and not any(a in t for a in self.allow):
            self.errors.append(t[:300])

    async def state(self):
        s = await asyncio.wait_for(self.pg.evaluate("window.wnbState || ''"), 15)
        return json.loads(s) if s else {}

    async def wait(self, pred, what, timeout=30, quiet=False):
        st = {}
        t0 = time.time()
        while time.time() - t0 < timeout:
            st = await self.state()
            if st and pred(st):
                return st
            await self.pg.wait_for_timeout(150)
        if not quiet:
            st.pop("buttons", None)
            check(False, f"{self.name}: {what} (состояние: {json.dumps(st, ensure_ascii=False)[:600]})")
        return {}

    async def fresh(self, after):
        """Состояние, снятое позже момента after (мс игры)."""
        return await self.wait(lambda s: s.get("t", 0) > after, "состояние обновилось", 10)

    async def canvas(self):
        return await self.pg.evaluate("(()=>{const c=document.getElementById('canvas');const r=c.getBoundingClientRect();"
                                      "return [r.left,r.top,r.width,r.height,c.width,c.height,devicePixelRatio,"
                                      "innerWidth,innerHeight]})()")

    async def at(self, x, y):
        """Логические 1280×720 → точка страницы (холст растянут на окно, игра — 16:9 с полями, canvas_items/keep)."""
        c = await self.canvas()
        W, H = c[4], c[5]
        s = min(W / 1280, H / 720)
        ox, oy = (W - 1280 * s) / 2, (H - 720 * s) / 2
        k = c[2] / W
        return c[0] + (ox + x * s) * k, c[1] + (oy + y * s) * k

    async def tap_xy(self, x, y):
        px, py = await self.at(x, y)
        if self.touch:
            await self.pg.touchscreen.tap(px, py)
        else:
            await self.pg.mouse.click(px, py)

    async def press(self, name, st=None, wait=250):
        """Нажать кнопку по имени (верхнюю из видимых) настоящим кликом/касанием по центру её прямоугольника."""
        st = st or await self.state()
        hits = [b for b in st.get("buttons", []) if b[0] == name]
        t0 = time.time()
        while not hits and time.time() - t0 < 6:          # кнопка может появиться не сразу («начать» — через 1,6 с)
            await self.pg.wait_for_timeout(150)
            st = await self.state()
            hits = [b for b in st.get("buttons", []) if b[0] == name]
        if not hits:
            check(False, f"{self.name}: нет кнопки {name} на экране {st.get('screen')} "
                         f"(есть: {[b[0] for b in st.get('buttons', [])][:40]})")
            return False
        b = hits[-1]
        await self.tap_xy(b[1] + b[3] / 2, b[2] + b[4] / 2)
        await self.pg.wait_for_timeout(wait)
        return True

    async def key(self, k, wait=300):
        await self.pg.keyboard.press(k)
        await self.pg.wait_for_timeout(wait)

    async def shot(self, tag):
        try:
            await self.pg.screenshot(path=os.path.join(SHOTS, f"{self.name}_{tag}.png"), timeout=20000)
        except Exception as e:
            info(f"{self.name}: снимок {tag} не снят ({type(e).__name__})")

    async def boot(self, query="", what="титул"):
        t0 = time.time()
        await self.pg.goto(URL + "?test=1" + query)
        st = await self.wait(lambda s: s.get("screen") in ("title", "hub", "intro", "job"), what, 90)
        secs = time.time() - t0
        times = await self.pg.evaluate("JSON.stringify(window.wnbTimes || {})")
        return st, secs, json.loads(times)

    def check_console(self):
        check(not self.errors, f"{self.name}: ошибок в консоли браузера нет"
              + (f" — {self.errors[:3]}" if self.errors else ""))


async def new_page(b, name, touch=False, mobile=False, w=1280, h=720, dpr=1.0, legacy=None, motion="no-preference",
                   block_frames=False, legacy_raw=None, hook=None):
    """hook(route, path) — свой ответ на запрос к игре (True — обработан): обрыв, 500, «висящий» ответ, мусор."""
    opts = dict(viewport={"width": w, "height": h}, device_scale_factor=dpr, reduced_motion=motion)
    if mobile:
        opts.update(has_touch=True)
        if BROWSER != "firefox":                           # Firefox: isMobile не поддерживается (касания — есть)
            opts.update(is_mobile=True)
    ctx = await b.new_context(**opts)
    u = urllib.parse.urlsplit(URL)
    perms = {"chromium": ["clipboard-read", "clipboard-write"], "webkit": ["clipboard-read"], "firefox": []}[BROWSER]
    if perms:
        await ctx.grant_permissions(perms, origin=f"{u.scheme}://{u.netloc}")
    if not CHROMIUM:
        await ctx.add_init_script(MUTE_JS)
        await ctx.add_init_script(SCREEN_JS)
        if mobile:
            # Firefox/WebKit без окна: полный экран растягивает страницу на «экран» компьютера (альбомный 1366×768) —
            # телефон в книжной «поворачивался» сам. На настоящем телефоне размер окна в полном экране — свой.
            await ctx.add_init_script("for (const k of ['requestFullscreen', 'webkitRequestFullscreen']) if "
                                      "(Element.prototype[k]) Element.prototype[k] = function () { return Promise.resolve(); };")
    await ctx.add_init_script(INIT_JS)
    await ctx.add_init_script(CLIP_JS)
    if legacy or legacy_raw:                           # legacy — словари, legacy_raw — текст файла как есть
        raw = {k: json.dumps(v) for k, v in (legacy or {}).items()}
        raw.update(legacy_raw or {})
        js = "".join(f"localStorage.setItem({json.dumps('wnb:' + k)}, {json.dumps(v)});" for k, v in raw.items())
        await ctx.add_init_script("if (!sessionStorage.getItem('wnb-test-seeded')) {" + js +
                                  "sessionStorage.setItem('wnb-test-seeded', '1');}")
    host = urllib.parse.urlsplit(URL).netloc

    async def route(r):
        u = urllib.parse.urlsplit(r.request.url)
        if u.netloc != host:
            await r.abort()                            # наружу — ничего (таблица замечаний, счётчики)
        elif hook and await hook(r, u.path):
            pass
        elif block_frames and "/frames/" in u.path:
            await r.fulfill(status=404, body="not found")
        else:
            await r.continue_()
    await ctx.route("**/*", route)
    pg = await ctx.new_page()
    p = Page(ctx, pg, name, touch)
    if block_frames:
        p.allow += ["404", "Frames: кадры", "at: push_warning"]   # ожидаемо: файл не найден, кадры — запасным видом
    return p


# ---------------- прохождение ----------------

async def clip_text(p):
    """Что лежит в буфере обмена после «Скопировать». Chromium — readText; Firefox/WebKit тесту читать буфер не дают —
    то, что игра отдала в navigator.clipboard.writeText (CLIP_JS), и ответ браузера (ошибка — в __clipErr)."""
    if CHROMIUM:
        return await p.pg.evaluate("navigator.clipboard.readText().catch(e => 'ERR ' + e)")
    await p.pg.wait_for_timeout(300)
    r = await p.pg.evaluate("[window.__clip || '', window.__clipErr || null, !!window.__clipOk]")
    info(f"{p.name}: буфер обмена ({BROWSER}): writeText «{r[0][:24]}…», принят браузером={r[2]}, ошибка={r[1]}")
    check(r[2] and not r[1], f"{p.name}: браузер принял запись в буфер обмена (writeText) — {r[1] or 'ok'}")
    return r[0]


async def follow_hints(p, until, timeout=240, on_state=None, max_steps=400):
    """Жать подсказку игры (state.hint), пока until(state) не станет истиной."""
    t0 = time.time()
    last = None
    st = await p.state()
    for _ in range(max_steps):
        if until(st):
            return st
        if time.time() - t0 > timeout:
            break
        if on_state:
            r = await on_state(st)
            if r == "skip":
                st = await p.fresh(st.get("t", 0))
                continue
        hint = st.get("hint", [])
        if hint:
            names = [b[0] for b in st.get("buttons", [])]
            target = next((h for h in hint if h in names), None)
            if target is None:
                await p.pg.wait_for_timeout(300)
            else:
                await p.press(target, st, 120)
                last = target
        else:
            await p.pg.wait_for_timeout(300)
        st = await p.fresh(st.get("t", 0))
        if not st:
            break
    st.pop("buttons", None)
    check(False, f"{p.name}: не дошли до цели (последнее нажатие {last}; {json.dumps(st, ensure_ascii=False)[:500]})")
    return st


PORTRAIT_SEEN = {}   # задание -> какими петлями рисовался портрет героя ("" — картинкой); debug state «portrait»


async def play_job(p, jid, expect_loop, shots=True):
    """Задание jid до итога по подсказкам: осмотр, диагноз, шаги инструментами, мини-игры, проезд, итог."""
    st = await p.wait(lambda s: s.get("screen") == "job" and s.get("job") == jid, f"открыто задание {jid}", 30)
    if not st:
        return {}
    if shots:
        await p.pg.wait_for_timeout(2500)
        await p.shot(f"{jid}_1_diagnose")
    seen_magic = {"ready": False, "playing": False}
    PORTRAIT_SEEN[jid] = set()

    async def watch(s):
        m = s.get("magic") or {}
        PORTRAIT_SEEN[jid].add(s.get("portrait", ""))
        seen_magic["ready"] |= bool(m.get("ready"))
        seen_magic["playing"] |= bool(m.get("playing"))
        if s.get("mini") and shots and not seen_magic.get("mini_shot"):
            seen_magic["mini_shot"] = True
            await p.shot(f"{jid}_2_mini")
        return None

    st = await follow_hints(p, lambda s: s.get("phase") == "test", 240, watch)
    if st.get("phase") != "test":
        return st
    check(st.get("mistakes", 0) == 0, f"{p.name}: {jid} пройдено без ошибок по подсказкам ({st.get('mistakes')})")
    loop_key = f"loop:{expect_loop}" if expect_loop else ""
    if expect_loop:
        st = await p.wait(lambda s: (s["frames"]["sets"].get(loop_key, [0, 1])[0] == s["frames"]["sets"].get(loop_key, [0, 1])[1]),
                          f"петля {expect_loop} скачалась", 60)
        check(bool(st), f"{p.name}: петля проезда {expect_loop} скачалась ({st.get('frames', {}).get('sets', {}).get(loop_key)})")
    await p.press("TestDrive")
    st = await p.wait(lambda s: (s.get("ride") or {}).get("riding"), "проезд начался", 10)
    await p.pg.wait_for_timeout(1500)
    st = await p.state()
    ride = st.get("ride") or {}
    if shots:
        await p.shot(f"{jid}_3_ride")
    if expect_loop:
        check(ride.get("loop") == expect_loop and ride.get("drawn", 0) > 0,
              f"{p.name}: проезд петлёй {expect_loop}, кадров нарисовано {ride.get('drawn')}")
    else:
        check(ride.get("loop") == "", f"{p.name}: проезд без петли (запасной вид: скользящий портрет) — {ride}")
    st = await p.wait(lambda s: s.get("ride_done"), "проезд закончился", 20)
    await p.press("TestDrive")
    st = await p.wait(lambda s: s.get("screen") == "result", "итог задания", 15)
    if st:
        await p.pg.wait_for_timeout(2500)
        if shots:
            await p.shot(f"{jid}_4_result")
        m = (await p.state()).get("magic") or {}
        info(f"{p.name}: волшебство на портрете: в задании готово={seen_magic['ready']} играло={seen_magic['playing']}, "
             f"на итоге {m}")
        await p.press("ToHub")
        st = await p.wait(lambda s: s.get("screen") == "hub", "в мастерскую", 15)
        check(jid in st.get("done", []), f"{p.name}: {jid} отмечено в прогрессе")
    return st


skipped = []


def skip_cdp(name):
    """Сценарий на CDP (замедление процессора, Page.setWebLifecycleState) в Firefox/WebKit не прогнать."""
    skipped.append(name)
    print(f"  --   {name}: пропущено: только Chromium (нужен CDP)", flush=True)


async def measure_fps(p, secs=5.0):
    vals = []
    t0 = time.time()
    while time.time() - t0 < secs:
        st = await p.state()
        if st.get("fps"):
            vals.append(st["fps"])
        await p.pg.wait_for_timeout(1000)
    st = await p.state()
    return (sum(vals[1:]) / max(1, len(vals) - 1)) if len(vals) > 1 else (vals[0] if vals else 0), st.get("worst_ms", 0)


# ---------------- сценарии ----------------

async def sc_boot(b):
    """Первая загрузка до титула, кадры петель титула, музыка ждёт первого нажатия, поля 16:9, ресайз окна."""
    p = await new_page(b, "boot")
    st, secs, times = await p.boot()
    check(st.get("screen") == "title", f"{p.name}: титул ({st.get('screen')})")
    check(st.get("touch") is False, f"{p.name}: мышь — не режим касаний ({st.get('touch')})")
    check(st.get("phone") is False, f"{p.name}: компьютер — не телефонный режим ({st.get('phone')})")
    t_title = (times.get("title", 0) - times.get("start", 0)) / 1000
    metrics["boot_title_s"] = round(t_title, 2)
    info(f"{p.name}: титул через {t_title:.2f} с от начала страницы (движок запущен через "
         f"{(times.get('started', 0) - times.get('start', 0)) / 1000:.2f} с)")
    st = await p.wait(lambda s: s["frames"]["sets"].get("loop:martin_wave", [0, 1])[0] == 36 and
                      s["frames"]["sets"].get("loop:barty_wave", [0, 1])[0] == 36, "петли титула скачались", 30)
    check(bool(st), f"{p.name}: машущие Мартин и Барти скачались ({st.get('frames', {}).get('decoded')} кадров, "
                    f"декодирование {st.get('frames', {}).get('decode_ms')} мс/кадр)")
    await p.pg.wait_for_timeout(1500)
    await p.shot("1_title")
    net = st.get("net", {})
    fr = st.get("frames", {})
    metrics["decode"] = [BROWSER, net.get("mode"), net.get("worker_ms"), fr.get("decode_ms")]
    no_oc = await p.pg.evaluate("!window.OffscreenCanvas")
    if no_oc:                       # WebKit (Safari до 16.4): нет OffscreenCanvas — запасной путь, распаковывает игра
        check(net.get("mode") == "godot" and fr.get("decoded", 0) >= 72,
              f"{p.name}: нет OffscreenCanvas — запасной путь, кадры распаковывает игра ({net.get('mode')}, "
              f"{fr.get('decoded')} кадров, {fr.get('decode_ms')} мс/кадр в игровом кадре)")
    else:
        check(net.get("mode") == "worker" and net.get("worker_decoded", 0) >= 72,
              f"{p.name}: кадры распаковывает фоновый поток страницы ({net.get('mode')}, {net.get('worker_decoded')} кадров, "
              f"{net.get('worker_ms')} мс/кадр в потоке; в игровом кадре — {fr.get('decode_ms')} мс)")
    # пиксели фоновой распаковки = распаковка WebP как есть (PIL): цвет под прозрачными пикселями не потерян
    import base64
    import io
    from PIL import Image
    for rel in ("turntable/chair_aeroz_00.webp", "anim/barty_wave/00.webp") if not no_oc else ():
        r = await p.pg.evaluate("(u) => wnbNet.probe(u)", "frames/" + rel)
        got = base64.b64decode(r["b64"])
        ref = Image.open(os.path.join(GODOT, "content", "frames", *rel.split("/"))).convert("RGBA")
        same_size = (r["w"], r["h"]) == ref.size
        diff = max(abs(a - b) for a, b in zip(got[::7], ref.tobytes()[::7])) if same_size else 999
        check(same_size and diff <= 2, f"{p.name}: фоновая распаковка {rel} = PIL (размер {r['w']}×{r['h']}, "
                                       f"наибольшая разница {diff})")
    mus = await p.pg.evaluate("wnbMusic.state()")
    act = await p.pg.evaluate("navigator.userActivation.hasBeenActive")
    # Playwright помечает страницу «уже нажатой» (userActivation.hasBeenActive = true) — запрет автозапуска звука
    # здесь не проверить; без жеста страница только пробует play() и ждёт pointerdown/keydown (wnbMusic.tryPlay)
    info(f"{p.name}: музыка на титуле: {mus} (страница активирована Playwright: {act})")
    c = await p.canvas()
    check(abs(c[2] - c[7]) < 2 and abs(c[3] - c[8]) < 2, f"{p.name}: холст на всё окно ({c[2]}×{c[3]} при {c[7]}×{c[8]})")
    # ресайз окна: холст за окном, картинка 16:9 с полями
    await p.pg.set_viewport_size({"width": 900, "height": 800})
    await p.pg.wait_for_timeout(1200)
    c = await p.canvas()
    check(abs(c[2] - 900) < 2 and abs(c[3] - 800) < 2, f"{p.name}: после ресайза холст {c[2]:.0f}×{c[3]:.0f} = окно 900×800")
    await p.shot("2_resize_900x800")
    x, y = await p.at(640, 360)
    check(abs(x - 450) < 2 and abs(y - 400) < 2, f"{p.name}: центр игры в центре окна ({x:.0f},{y:.0f})")
    await p.pg.set_viewport_size({"width": 1280, "height": 720})
    await p.pg.wait_for_timeout(800)
    p.check_console()
    await p.ctx.close()


async def sc_play(b):
    """Новая игра: титул → вступление → задание Мартина целиком (проезд петлёй, итог); музыка; перезагрузка —
    прогресс и настройки на месте (IndexedDB); F2 — голос браузера и aria-live."""
    p = await new_page(b, "play")
    st, _, _ = await p.boot()
    await p.wait(lambda s: "Start" in [x[0] for x in s.get("buttons", [])], "кнопка «начать»", 10)
    # «живой» Мартин (IDLE_LOOPS martin_idle): качается с сайта уже на титуле (как game.py _scene_loops_web)
    k = "loop:martin_idle"
    st = await p.wait(lambda s: s["frames"]["sets"].get(k, [0, 1])[0] == s["frames"]["sets"].get(k, [0, 1])[1],
                      "martin_idle скачалась на титуле", 60)
    check(bool(st) and st.get("screen") == "title",
          f"{p.name}: петля martin_idle скачана на титуле ({(st or {}).get('frames', {}).get('sets', {}).get(k)})")
    await p.press("Start", wait=800)
    st = await p.wait(lambda s: s.get("screen") == "intro", "вступление", 10)
    mus = await p.pg.evaluate("wnbMusic.state()")
    check(mus.startswith("playing"), f"{p.name}: после первого нажатия музыка играет ({mus})")
    await p.shot("1_intro")
    st = await follow_hints(p, lambda s: s.get("screen") == "job", 60)
    st = await play_job(p, "flat", "ride_martin")
    check("martin_idle" in PORTRAIT_SEEN.get("flat", set()),
          f"{p.name}: портрет в задании Мартина рисуется петлёй martin_idle ({PORTRAIT_SEEN.get('flat')})")
    await p.shot("5_hub")
    # F2: озвучка — голос браузера (заглушка) и скрытая область aria-live
    await p.key("F2", 800)
    st = await p.state()
    spoken = await p.pg.evaluate("window.__spoken.slice(-3)")
    live = await p.pg.evaluate("(document.getElementById('wnb-live')||{}).textContent || ''")
    check(st.get("speech_on") is True, f"{p.name}: F2 включил озвучку")
    check(bool(live), f"{p.name}: текст в aria-live: «{live[:80]}»")
    check(bool(spoken), f"{p.name}: голос браузера вызван (заглушка): {spoken[:2]}")
    await p.key("F2", 500)
    # настройки: M — звук выкл (сохраняется сразу), перезагрузка через 0,4 с — запись должна дойти до IndexedDB
    await p.key("m", 400)
    st = await p.state()
    check(st.get("sound") is False, f"{p.name}: M выключил звук")
    await p.pg.reload()
    st = await p.wait(lambda s: s.get("screen") in ("title", "hub"), "после перезагрузки", 60)
    check("flat" in st.get("done", []), f"{p.name}: после перезагрузки прогресс на месте ({st.get('done')})")
    check(st.get("sound") is False, f"{p.name}: после перезагрузки настройка «звук выкл» на месте")
    await p.key("m", 400)
    p.check_console()
    await p.ctx.close()


async def sc_links(b):
    """?jobs=flat,caster&from=… — задание по ссылке; копирование кода в буфер; ?load=код — вопрос один раз
    (wnb:load_seen); поле вставки кода — настоящее <input> поверх холста."""
    p = await new_page(b, "links", legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    st, _, _ = await p.boot("&jobs=flat,caster&from=" + urllib.parse.quote("Анна"))
    st = await p.wait(lambda s: s.get("assign"), "задание из ссылки принято", 15)
    check(bool(st.get("assign")), f"{p.name}: ?jobs=flat,caster — задание {st.get('assign')}, экран {st.get('screen')}")
    await p.press("Start", wait=1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "мастерская задания", 10)
    await p.shot("1_assign_hub")
    names = [x[0] for x in st.get("buttons", [])]
    check("Card_flat" in names and "Card_caster" in names and "Card_brake" not in names,
          f"{p.name}: в мастерской только назначенные (flat, caster)")
    # обычная игра: выйти из задания, скопировать код прогресса (настройки → ИГРА)
    await p.press("ExitAssign", wait=800)
    await p.press("Gear", wait=600)
    await p.press("Tab_game", wait=400)
    await p.shot("2_settings_game")
    await p.press("Share_code", wait=800)
    st = await p.state()
    clip = await clip_text(p)
    check(clip.startswith("P."), f"{p.name}: «Скопировать код» положил код в буфер обмена ({clip[:24]}…)")
    await p.key("Escape", 400)
    # вставка кода: поле страницы поверх рамки
    await p.press("Share_paste", wait=800)
    vis = await p.pg.evaluate("""(()=>{const f=document.getElementById('wnb-field'); if(!f) return null;
        const r=f.getBoundingClientRect(); return [getComputedStyle(f).display, r.left, r.top, r.width, r.height,
        document.activeElement===f]})()""")
    check(vis is not None and vis[0] == "block" and vis[3] > 100, f"{p.name}: поле ввода кода — <input> поверх холста {vis}")
    if vis:                                               # поле — внутри игровой картинки, по центру окна
        g, _, _ = await game_rect(p)
        cx, cy = vis[1] + vis[3] / 2, vis[2] + vis[4] / 2
        check(g[0] < vis[1] and vis[1] + vis[3] < g[0] + g[2] and g[1] < cy < g[1] + g[3] and abs(cx - (g[0] + g[2] / 2)) < 40,
              f"{p.name}: поле кода внутри картинки игры ({vis[1]:.0f},{vis[2]:.0f} {vis[3]:.0f}×{vis[4]:.0f}; "
              f"игра {g[0]:.0f},{g[1]:.0f} {g[2]:.0f}×{g[3]:.0f})")
        # ресайз окна при открытом поле — поле едет за картинкой
        await p.pg.set_viewport_size({"width": 1000, "height": 700})
        await p.pg.wait_for_timeout(1200)
        v2 = await p.pg.evaluate("(()=>{const r=document.getElementById('wnb-field').getBoundingClientRect();"
                                 "return [r.left, r.top, r.width, r.height]})()")
        g2, _, _ = await game_rect(p)
        rel = lambda v, g: ((v[0] - g[0]) / g[2], (v[1] - g[1]) / g[3], v[2] / g[2])
        a, z = rel(vis[1:5], g), rel(v2, g2)
        check(all(abs(x - y) < 0.01 for x, y in zip(a, z)),
              f"{p.name}: окно 1000×700 — поле на том же месте картинки ({[round(x, 3) for x in a]} → "
              f"{[round(x, 3) for x in z]})")
        await p.pg.set_viewport_size({"width": 1280, "height": 720})
        await p.pg.wait_for_timeout(1000)
    await p.shot("3_paste_field")
    if vis and clip.startswith("P."):
        await p.pg.fill("#wnb-field", clip)
        await p.pg.press("#wnb-field", "Enter")
        st = await p.wait(lambda s: s.get("share_dlg") == "confirm", "вопрос «загрузить прогресс?»", 10)
        check(st.get("share_dlg") == "confirm", f"{p.name}: код из поля распознан — вопрос о загрузке")
        await p.shot("4_paste_confirm")
        await p.key("Escape", 500)
        gone = await p.pg.evaluate("getComputedStyle(document.getElementById('wnb-field')).display")
        check(gone == "none", f"{p.name}: окно закрыто — поле страницы спрятано ({gone})")
    p.check_console()
    await p.ctx.close()
    # ?load=<код> — вопрос; «Нет» — после перезагрузки не спрашивает (wnb:load_seen)
    if clip.startswith("P."):
        q = await new_page(b, "load")
        st, _, _ = await q.boot("&load=" + urllib.parse.quote(clip))
        st = await q.wait(lambda s: s.get("share_dlg") == "confirm", "вопрос о прогрессе из ссылки", 15)
        check(st.get("share_dlg") == "confirm", f"{q.name}: ?load= — вопрос «загрузить прогресс?»")
        await q.pg.wait_for_timeout(800)
        await q.shot("1_load_confirm")
        await q.press("Btn_no", wait=800)
        seen = await q.pg.evaluate("localStorage.getItem('wnb:load_seen')")
        check(bool(seen) and clip.endswith(seen), f"{q.name}: ответ запомнен (wnb:load_seen = {seen})")
        await q.pg.reload()
        st = await q.wait(lambda s: s.get("screen") == "title", "титул после перезагрузки", 60)
        await q.pg.wait_for_timeout(1500)
        st = await q.state()
        check(st.get("share_dlg") == "", f"{q.name}: после перезагрузки тот же ?load= больше не спрашивает")
        q.check_console()
        await q.ctx.close()


async def sc_migrate(b):
    """localStorage pygame-версии (wnb:save.json, wnb:settings.json) → прогресс и настройки подхвачены один раз."""
    p = await new_page(b, "migrate", legacy={"save.json": LEGACY_SAVE, "settings.json": LEGACY_SETTINGS})
    st, _, _ = await p.boot()
    check(st.get("migrated") is True, f"{p.name}: прогресс pygame-версии перенесён (migrated)")
    check(sorted(st.get("done", [])) == sorted(LEGACY_SAVE["done"]), f"{p.name}: done = {st.get('done')}")
    check(st.get("lang") == "en" and st.get("sound") is True,
          f"{p.name}: настройки перенесены, язык при старте английский, как game.py в браузере (язык {st.get('lang')})")
    old = await p.pg.evaluate("localStorage.getItem('wnb:save.json')")
    check(old and json.loads(old) == LEGACY_SAVE, f"{p.name}: старое сохранение pygame не тронуто")
    await p.press("Start", wait=1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 10)
    await p.shot("1_hub")
    await p.pg.reload()
    st = await p.wait(lambda s: s.get("screen") == "title", "титул после перезагрузки", 60)
    check(st.get("migrated") is False and sorted(st.get("done", [])) == sorted(LEGACY_SAVE["done"]),
          f"{p.name}: второй запуск — своё сохранение, без повторного переноса")
    await lang_restart(p)
    p.check_console()
    await p.ctx.close()
    await migrate_real(b)


async def title_ready(p):
    """Титул показал кнопки (до этого щелчки по нему не доходят) — «начать» видна."""
    await p.wait(lambda s: s.get("screen") == "title" and any(b_[0] == "Start" for b_ in s.get("buttons", [])),
                 "кнопки титула", 20)


async def lang_restart(p):
    """Язык в браузере как game.py: старт всегда английский (даже с «lang: ru» в настройках); русский — переключателем
    RU/EN в игре, он сохраняется в настройки, но после перезагрузки страницы игра снова стартует по-английски
    (game.py: set_lang("en" if IS_WEB …) при каждом запуске)."""
    st = await p.state()
    check(st.get("lang") == "en", f"{p.name}: настройки с lang ru — старт по-английски ({st.get('lang')})")
    await title_ready(p)
    await p.press("Lang", wait=600)
    st = await p.state()
    check(st.get("lang") == "ru", f"{p.name}: переключатель RU/EN в игре — русский ({st.get('lang')})")
    await p.pg.wait_for_timeout(800)                    # настройки записаны (user://settings.json)
    await p.pg.reload()
    st = await p.wait(lambda s: s.get("screen") == "title", "титул после перезагрузки", 60)
    check(st.get("lang") == "en", f"{p.name}: после перезагрузки снова английский, как game.py ({st.get('lang')})")


async def migrate_real(b):
    """Настоящие сохранения pygame-версии (их пишет сама game.py: tools/save_fixtures.py → tests/saves/) переносятся
    поле в поле так, как их читает game.py (tests/saves/expected.json); битые — игра стартует, старое не тронуто.
    Отличия браузера в эталоне: размер текста по умолчанию 125 % (text 2), «Без анимации» без выбора игрока — как в
    системе (здесь prefers-reduced-motion: no-preference → выкл). Язык при старте — всегда английский, как game.py в
    браузере (set_lang("en" if IS_WEB …)), при любом «lang» в настройках."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import save_fixtures as sf
    exp = json.load(open(os.path.join(sf.OUT, "expected.json"), encoding="utf-8"))
    for name, e in exp.items():
        raw = {"save.json": open(os.path.join(sf.OUT, name + ".save.json"), encoding="utf-8").read()}
        sp = os.path.join(sf.OUT, name + ".settings.json")
        if os.path.exists(sp):
            raw["settings.json"] = open(sp, encoding="utf-8").read()
        p = await new_page(b, "migrate_" + name, legacy_raw=raw)
        st, _, _ = await p.boot("&compat=1")
        got = st.get("compat") or {}
        e = dict(e)
        if not e["a11y"]["text_set"]:
            e["a11y"] = dict(e["a11y"], text=2)
        if e["calm"] == "system":
            e["calm"] = False
        e["lang"] = "en"                                  # браузер: старт всегда по-английски, как game.py
        got = dict(got, calm=got.get("calm") if got.get("calm") != "system" else
                   (await p.state()).get("calm"))
        bad = sf.compare({name: e}, {name: got})
        broken = name.startswith("broken")
        check(not bad and bool(st.get("screen")) and st.get("migrated") is (not broken and name != "broken_list"),
              f"{p.name}: прогресс и настройки = game.py ({len(e)} полей; перенос {st.get('migrated')})"
              + ("" if not bad else " — " + "; ".join(bad)[:400]))
        left = await p.pg.evaluate("[localStorage.getItem('wnb:save.json'), localStorage.getItem('wnb:settings.json')]")
        check(left[0] == raw["save.json"] and left[1] == raw.get("settings.json"),
              f"{p.name}: сохранение pygame-версии в localStorage не тронуто")
        p.check_console()
        await p.ctx.close()


async def sc_net404(b):
    """Кадры на сайте недоступны (404): коляска — рисунком, проезд — скользящим портретом, игра живёт."""
    p = await new_page(b, "net404", legacy={"save.json": {"done": [], "tutorial_skipped": True}}, block_frames=True)
    st, _, _ = await p.boot()
    await p.press("Start", wait=1000)
    st = await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 10)
    await p.press("Card_flat", wait=800)
    st = await p.wait(lambda s: s.get("screen") == "job", "задание", 10)
    await p.pg.wait_for_timeout(4000)
    st = await p.state()
    fr = st.get("frames", {})
    check(fr.get("failed", 0) > 0 and fr.get("loaded", 0) == 0, f"{p.name}: кадров нет (неудачных {fr.get('failed')})")
    await p.shot("1_job_no_frames")
    st = await play_job(p, "flat", "", shots=False)
    await p.shot("2_hub")
    check(st.get("screen") == "hub", f"{p.name}: задание пройдено без кадров")
    p.check_console()
    await p.ctx.close()


async def sc_guild(b):
    """Про-задание Гильдии: Бренна «живая» (петля brenna_wave), «Проверка под нагрузкой» — петля проезда."""
    p = await new_page(b, "guild", legacy={"save.json": LEGACY_SAVE})
    st, _, _ = await p.boot()
    await p.press("Start", wait=1000)
    await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 10)
    await p.press("Guild", wait=800)
    st = await p.wait(lambda s: s.get("screen") == "guild", "Гильдия", 10)
    st = await p.wait(lambda s: s["frames"]["sets"].get("loop:brenna_wave", [0, 1])[0] ==
                      s["frames"]["sets"].get("loop:brenna_wave", [0, 1])[1], "петля Бренны скачалась", 30)
    check(bool(st), f"{p.name}: Бренна — петля brenna_wave скачалась")
    await p.pg.wait_for_timeout(800)
    await p.shot("1_guild")
    techs = [x[0] for x in st.get("buttons", []) if x[0].startswith("Tech_")]
    jid = "t_q6brake" if "Tech_t_q6brake" in techs else (techs[0][5:] if techs else "")   # Бренна в коляске Q6 Edge
    if not jid:
        check(False, f"{p.name}: нет карточек про-заданий")
        await p.ctx.close()
        return
    await p.press("Tech_" + jid, wait=1000)
    st = await p.wait(lambda s: s.get("screen") == "tech", "про-задание", 10)
    await p.shot("2_tech")
    st = await follow_hints(p, lambda s: s.get("phase") == "test", 120)
    sets = st.get("frames", {}).get("sets", {})
    loop = next((k[5:] for k in sets if k.startswith("loop:ride_")), "")
    if loop:
        st = await p.wait(lambda s: s["frames"]["sets"].get("loop:" + loop, [0, 1])[0] ==
                          s["frames"]["sets"].get("loop:" + loop, [0, 1])[1], f"петля {loop}", 60)
    await p.press("TestDrive")
    st = await p.wait(lambda s: (s.get("ride") or {}).get("riding"), "проверка под нагрузкой", 10)
    await p.pg.wait_for_timeout(2000)
    st = await p.state()
    await p.shot("3_tech_ride")
    check((st.get("ride") or {}).get("loop", "") == ("ride_brenna_q6edge" if jid == "t_q6brake" else loop)
          and (st.get("ride") or {}).get("drawn", 0) > 0,
          f"{p.name}: проезд Гильдии петлёй {(st.get('ride') or {}).get('loop')}")
    st = await p.wait(lambda s: s.get("ride_done"), "проезд закончился", 20)
    await p.pg.wait_for_timeout(500)
    await p.shot("4_tech_after")
    p.check_console()
    await p.ctx.close()


async def sc_phone(b):
    """Телефон (альбом 740×360, касания, dpr 3): титул, касание «начать», холст на всё окно, поле кода по касанию;
    потом книжная ориентация и планшет (sc_rotate)."""
    p = await new_page(b, "phone", touch=True, mobile=True, w=740, h=360, dpr=3,
                       legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    if not CHROMIUM:                                     # экран телефона (screen.width/height) — подменой, до загрузки
        await orient(p, 740, 360, True)
    st, secs, times = await p.boot()
    await p.pg.wait_for_timeout(1500)
    await p.shot("1_title")
    c = await p.canvas()
    check(abs(c[2] - 740) < 2 and abs(c[3] - 360) < 2 and c[4] >= 2000,
          f"{p.name}: холст {c[2]:.0f}×{c[3]:.0f} CSS = окно, {c[4]}×{c[5]} px (dpr {c[6]})")
    st = await p.state()
    check(st.get("touch") is True, f"{p.name}: сенсорный экран (pointer: coarse) — режим касаний, как TOUCH в game.py "
                                   f"(«тап», без подсказок клавиш): {st.get('touch')}")
    check(st.get("phone") is True, f"{p.name}: телефон (касания и экран < 600 CSS px) — телефонный режим, цели 56: "
                                   f"{st.get('phone')}")
    phone_small(p, st, "титул")
    await p.press("Start", wait=1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "касание «начать» → мастерская", 10)
    await p.shot("2_hub")
    # запас на промах пальцем (_touch_snap game.py, TOUCH_PAD 16): левее карточки на 30 px — мимо, на 10 px — в неё
    cf = next((x for x in (await p.state()).get("buttons", []) if x[0] == "Card_flat"), None)
    check(cf is not None, f"{p.name}: карточка flat на экране")
    if cf:
        await p.tap_xy(cf[1] - 30, cf[2] + cf[4] / 2)
        await p.pg.wait_for_timeout(900)
        st = await p.state()
        check(st.get("screen") == "hub", f"{p.name}: касание на 30 px левее карточки — мимо (экран {st.get('screen')})")
        await p.tap_xy(cf[1] - 10, cf[2] + cf[4] / 2)
    else:
        await p.press("Card_flat", wait=0)
    st = await p.wait(lambda s: s.get("screen") == "job", "касание на 10 px левее карточки → задание (запас пальца)", 10)
    check(st.get("screen") == "job", f"{p.name}: касание на 10 px левее карточки — задание (запас пальца TOUCH_PAD 16)")
    await p.pg.wait_for_timeout(3000)
    await p.shot("3_job")
    st = await p.state()
    phone_small(p, st, "задание")
    # касание у нижнего края строки детали (56 px; прежняя строка 36 px сюда не доставала) — осмотр
    row = next((b for b in st.get("buttons", []) if b[0].startswith("Part_")), None)
    if row:
        check(row[4] >= 56, f"{p.name}: строка детали {row[0]} высотой {row[4]} px холста (телефон: ≥ 56)")
        await p.tap_xy(row[1] + row[3] / 2, row[2] + row[4] - 4)
        st = await p.wait(lambda s: bool(s.get("toast")), "касание у нижнего края строки детали → улика сверху", 5)
        check(bool(st), f"{p.name}: касание у нижнего края строки детали (4 px от края) — осмотр ({(st or {}).get('toast', '')[:40]})")
    else:
        check(False, f"{p.name}: нет строки детали в задании")
    # «назад» 56×56: касание в (57, 53) — внутри нового значка, мимо прежнего (8..46 и запас 9 px)
    await p.tap_xy(57, 53)                              # первый раз — «Ещё раз Esc — покинуть ремонт»
    await p.pg.wait_for_timeout(500)
    await p.tap_xy(57, 53)
    st = await p.wait(lambda s: s.get("screen") == "hub", "касание края значка «назад» 56×56 → мастерская", 10)
    check(bool(st), f"{p.name}: касание у края значка «назад» (57, 53) — мастерская")
    phone_small(p, st or await p.state(), "мастерская")
    # Game._tap: значок ⚙ на сенсоре шире пальца на 9 px — касание на 6 px правее него открывает настройки
    g = next((x for x in st.get("buttons", []) if x[0] == "Gear"), None)
    if g and g[1] + g[3] + 6 >= 1280:                   # телефонный режим: ⚙ 56×56 у самого края — запас снизу
        await p.tap_xy(g[1] + g[3] / 2, g[2] + g[4] + 6)
        st = await p.wait(lambda s: s.get("settings"), "касание на 6 px ниже ⚙ → настройки (запас пальца)", 10)
        check(bool(st.get("settings")), f"{p.name}: касание на 6 px ниже ⚙ 56×56 — настройки (Game._tap, +9 px)")
    elif g:
        await p.tap_xy(g[1] + g[3] + 6, g[2] + g[4] / 2)
        st = await p.wait(lambda s: s.get("settings"), "касание на 6 px правее ⚙ → настройки (запас пальца)", 10)
        check(bool(st.get("settings")), f"{p.name}: касание на 6 px правее ⚙ — настройки (Game._tap, +9 px)")
    else:
        check(False, f"{p.name}: нет значка Gear")
        await p.press("Gear", wait=600)
    await p.press("Tab_game", wait=400)
    await p.press("Share_paste", wait=800)
    f = await p.pg.evaluate("(()=>{const f=document.getElementById('wnb-field');if(!f)return null;const r=f.getBoundingClientRect();"
                            "return [r.left+r.width/2, r.top+r.height/2, document.activeElement===f]})()")
    if f:
        check(f[2] is False, f"{p.name}: на телефоне поле не забирает фокус само (клавиатура — по касанию)")
        await p.pg.touchscreen.tap(f[0], f[1])
        await p.pg.wait_for_timeout(400)
        focused = await p.pg.evaluate("document.activeElement && document.activeElement.id")
        check(focused == "wnb-field", f"{p.name}: касание поля кода — фокус в <input> (экранная клавиатура)")
    else:
        check(False, f"{p.name}: нет поля кода")
    await p.shot("4_paste")
    # задание касаниями от мастерской до итога (телефонная раскладка: диагнозы рядом, Барти справа, плитки 56)
    st = await p.state()
    if st.get("share_dlg"):
        await p.key("Escape", 500)
    st = await p.state()
    if st.get("settings"):
        await p.press("Done", wait=600)
    st = await p.wait(lambda s: s.get("screen") == "hub" and not s.get("settings") and not s.get("share_dlg"),
                      "мастерская без окон", 10)
    await p.press("Card_flat", wait=800)
    st = await play_job(p, "flat", "ride_martin")
    check(bool(st) and st.get("screen") == "hub" and "flat" in st.get("done", []),
          f"{p.name}: задание Мартина пройдено касаниями от мастерской до итога ({(st or {}).get('screen')})")
    p.check_console()
    await p.ctx.close()
    await sc_rotate(b)                                    # книжная ориентация: заслонка, планшет, ?res=


def phone_small(p, st, where):
    """Телефонный режим: кнопки на экране (wnbState.buttons) не мельче 56 px холста; кружки деталей (Spot_*) —
    их зона пальца r + 16 считается в игре (самопроверка phone_check), здесь не мерим."""
    small = [b for b in st.get("buttons", []) if min(b[3], b[4]) < 56 and not b[0].startswith("Spot_")]
    check(not small, f"{p.name}: {where} — целей мельче 56 px холста нет"
          + (f" (есть: {[(b[0], b[3], b[4]) for b in small][:6]})" if small else ""))


async def orient(p, w, h, landscape, dpr=3):
    """Повернуть «телефон»: размер окна и экрана (screen.width/height) и screen.orientation — через CDP."""
    fs = await p.pg.evaluate("!!document.fullscreenElement && (document.exitFullscreen(), true)")
    if fs:                                               # первое касание включило полный экран — окно не ресайзится
        await p.pg.wait_for_timeout(500)
    await p.pg.set_viewport_size({"width": w, "height": h})   # и Playwright помнит размер (снимок его восстановит)
    if not CHROMIUM:                                     # без CDP: экран и ориентация — подменой (SCREEN_JS)
        v = {"width": w, "height": h, "availWidth": w, "availHeight": h,
             "type": "landscape-primary" if landscape else "portrait-primary", "angle": 90 if landscape else 0}
        await p.ctx.add_init_script(f"window.__wnbS = {json.dumps(v)};")   # и для следующей загрузки страницы
        try:
            await p.pg.evaluate("""(v) => { window.__wnbS = v; window.dispatchEvent(new Event('orientationchange'));
                try { screen.orientation.dispatchEvent(new Event('change')); } catch (e) {}
                window.dispatchEvent(new Event('resize')); }""", v)
        except Exception:
            pass                                         # страница ещё не открыта (about:blank) — хватит init-скрипта
        await p.pg.wait_for_timeout(900)
        return
    cdp = await p.ctx.new_cdp_session(p.pg)
    await cdp.send("Emulation.setDeviceMetricsOverride", {
        "width": w, "height": h, "deviceScaleFactor": dpr, "mobile": True, "screenWidth": w, "screenHeight": h,
        "screenOrientation": {"type": "landscapePrimary" if landscape else "portraitPrimary",
                              "angle": 90 if landscape else 0}})
    await p.pg.wait_for_timeout(900)


async def rot_state(p):
    return await p.pg.evaluate("""(()=>{const o=document.getElementById('wnb-rotate'), pa=document.getElementById('wnb-portrait'),
        f=document.getElementById('wnb-full');
        return {shown: !!o && getComputedStyle(o).display !== 'none', text: o ? o.textContent : '',
                anyway: pa ? pa.textContent : null, full: f ? [getComputedStyle(f).display, f.getAttribute('aria-label')] : null,
                cover: window.wnbCover ? wnbCover() : null, lang: window.wnbLangNow ? wnbLangNow() : ''}})()""")


async def sc_rotate(b):
    """Сенсорный экран, книжная ориентация: телефон — заслонка «поверни боком» поверх заставки и игры, игра под ней
    на паузе и касаний не получает; поворот в альбом — заслонки нет, игра идёт; планшет — «играть так» работает;
    плашка ?fps=1 на телефоне — крупная, с окном в CSS-пикселях и dpr; ?res= — потолок разрешения холста."""
    # телефон, книжная: заслонка с самого начала (во время загрузки)
    p = await new_page(b, "rotate", touch=True, mobile=True, w=360, h=740, dpr=3,
                       legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    await orient(p, 360, 740, False)
    await p.pg.goto(URL + "?test=1&fps=1")
    await p.pg.wait_for_timeout(300)
    r = await rot_state(p)
    load_vis = await p.pg.evaluate("!!document.getElementById('wnb-load')")
    check(r["shown"] and load_vis, f"{p.name}: заслонка видна уже во время загрузки (поверх заставки): «{r['text'][:60]}»")
    st = await p.wait(lambda s: s.get("screen") == "title", "титул под заслонкой", 90)
    await p.pg.wait_for_timeout(1200)
    st = await p.state()
    check(st.get("covered") is True and st.get("paused") is True,
          f"{p.name}: под заслонкой игра на паузе и не рисует (covered={st.get('covered')}, paused={st.get('paused')})")
    await p.shot("1_portrait_cover")
    # касание по заслонке туда, где «начать», — игре не достаётся
    await p.pg.evaluate("""window.__canvasHits = 0; ['touchstart','touchend','pointerdown','mousedown'].forEach(n =>
        document.getElementById('canvas').addEventListener(n, () => window.__canvasHits++, true))""")
    for xy in ((640, 600), (640, 360), (640, 650)):          # где на титуле «начать» и середина
        await p.tap_xy(*xy)
        await p.pg.wait_for_timeout(400)
    st = await p.state()
    hits = await p.pg.evaluate("window.__canvasHits")
    check(st.get("screen") == "title" and hits == 0,
          f"{p.name}: касания по заслонке холсту не достались (событий на холсте {hits}, экран {st.get('screen')})")
    # поворот в альбом
    await orient(p, 740, 360, True)
    r = await rot_state(p)
    st = await p.wait(lambda s: s.get("covered") is False and s.get("paused") is False, "игра снова идёт", 10)
    check(not r["shown"] and bool(st), f"{p.name}: в альбомной ориентации заслонки нет, игра идёт")
    can_fs = await p.pg.evaluate("!!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen)")
    if can_fs:
        check(bool(r["full"]) and r["full"][0] != "none", f"{p.name}: кнопка полного экрана у левого края ({r['full']})")
    else:                                                # Safari на iPhone (и WebKit с isMobile): Fullscreen API нет
        check(r["full"] is None, f"{p.name}: нет Fullscreen API (как Safari на iPhone) — кнопки ⛶ нет ({r['full']})")
    await p.pg.wait_for_timeout(2500)
    await p.press("Start", None, 1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "касание «начать» после поворота → мастерская", 10)
    c = await p.canvas()
    res = await p.pg.evaluate("wnbRes.line()")
    check(abs(c[2] - 740) < 2 and abs(c[3] - 360) < 2 and c[4] >= 2000,
          f"{p.name}: холст {c[2]:.0f}×{c[3]:.0f} CSS = окно, {c[4]}×{c[5]} px; {res}")
    await p.pg.wait_for_timeout(1500)
    await p.shot("2_landscape_hub_fps")
    lang = (await rot_state(p))["lang"]
    check(lang == st.get("lang"), f"{p.name}: язык страницы = язык игры ({lang})")
    # обратно в книжную — заслонка снова, игра на паузе
    await orient(p, 360, 740, False)
    st = await p.wait(lambda s: s.get("covered") is True, "снова заслонка", 10)
    check(bool(st) and (await rot_state(p))["shown"], f"{p.name}: снова книжная — снова заслонка")
    p.check_console()
    await p.ctx.close()
    # ?res=720 на телефоне: холст ниже, картинка та же по размеру
    q = await new_page(b, "res", touch=True, mobile=True, w=740, h=360, dpr=3,
                       legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    await orient(q, 740, 360, True)
    await q.boot("&res=720")
    c = await q.canvas()
    check(abs(c[3] - 360) < 2 and abs(c[5] - 720) <= 2, f"{q.name}: ?res=720 — холст {c[4]}×{c[5]} px при окне "
                                                        f"{c[2]:.0f}×{c[3]:.0f} CSS (dpr {c[6]})")
    await q.press("Start", None, 1200)
    st = await q.wait(lambda s: s.get("screen") == "hub", "касание при ?res=720 попадает в кнопку", 10)
    check(bool(st), f"{q.name}: касание при пониженном разрешении попадает куда надо")
    q.check_console()
    await q.ctx.close()
    # планшет, книжная: заслонка с кнопкой «играть так»
    t = await new_page(b, "tablet", touch=True, mobile=True, w=768, h=1024, dpr=2,
                       legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    await orient(t, 768, 1024, False, 2)
    st, _, _ = await t.boot()
    r = await rot_state(t)
    check(r["shown"] and bool(r["anyway"]), f"{t.name}: заслонка с кнопкой «{r['anyway']}»")
    await t.shot("1_portrait_cover")
    box = await t.pg.evaluate("(()=>{const r=document.getElementById('wnb-portrait').getBoundingClientRect();"
                              "return [r.left+r.width/2, r.top+r.height/2]})()")
    await t.pg.touchscreen.tap(box[0], box[1])
    await t.pg.wait_for_timeout(600)
    r = await rot_state(t)
    st = await t.wait(lambda s: s.get("covered") is False, "игра идёт после «играть так»", 10)
    check(not r["shown"] and bool(st), f"{t.name}: «играть так» убрал заслонку, игра идёт")
    check(st.get("touch") is True and st.get("phone") is False,
          f"{t.name}: планшет — касания, но не телефонный режим (touch={st.get('touch')}, phone={st.get('phone')})")
    await t.pg.wait_for_timeout(1500)
    await t.press("Start", None, 1200)
    st = await t.wait(lambda s: s.get("screen") == "hub", "касание «начать» в книжной на планшете", 10)
    check(bool(st), f"{t.name}: в книжной ориентации игра принимает касания")
    await t.shot("2_portrait_hub")
    t.check_console()
    await t.ctx.close()


STALE_JS = """(([k, v]) => { Object.defineProperty(window, k, { configurable: true, get: () => v }); })"""


async def game_rect(p):
    """Прямоугольник игровой картинки 16:9 на странице (CSS px): холст (положение, CSS-размер, буфер) + окно Godot и
    сдвиг/масштаб растяжения из wnbState (win, game); без них — как Godot кладёт 1280×720 с полями в буфер холста."""
    c = await p.canvas()
    st = await p.state()
    W, H = (st.get("win") or [c[4], c[5]])
    g = st.get("game")
    if not g:
        s = min(W / 1280, H / 720)
        g = [(W - 1280 * s) / 2, (H - 720 * s) / 2, 1280 * s, 720 * s]
    kx, ky = c[2] / max(1, c[4]), c[3] / max(1, c[5])
    return [c[0] + g[0] * kx, c[1] + g[1] * ky, g[2] * kx, g[3] * ky], c, st


async def check_fit(p, vw, vh, what):
    """Игра 16:9 целиком в видимом окне vw×vh и занимает его по высоте (окно шире 16:9)."""
    r, c, st = await game_rect(p)
    inside = r[0] >= -1 and r[1] >= -1 and r[0] + r[2] <= vw + 1 and r[1] + r[3] <= vh + 1
    full_h = abs(r[3] - min(vh, vw * 9 / 16)) <= 2
    diag = await p.pg.evaluate("window.wnbView ? wnbView.line() : ''")
    return check(inside and full_h, f"{p.name}: {what}: картинка {r[0]:.0f},{r[1]:.0f} {r[2]:.0f}×{r[3]:.0f} в окне "
                                    f"{vw}×{vh} (холст CSS {c[2]:.0f}×{c[3]:.0f} в {c[0]:.0f},{c[1]:.0f}, буфер "
                                    f"{c[4]}×{c[5]}, Godot {st.get('win')}) {diag}")


async def sc_stale(b):
    """Телефон владельца (Mate 20 Pro, 780×360 CSS, dpr 3): после полного экрана и поворота window.innerHeight
    остался книжным (780) — игра была сдвинута вниз на 170 px. Здесь: открыть в книжной (заслонка), «повернуть» и
    подменить innerHeight = 780; потом обратный случай — innerWidth = 360 с самой загрузки в альбомной."""
    p = await new_page(b, "stale", touch=True, mobile=True, w=360, h=780, dpr=3,
                       legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    await orient(p, 360, 780, False)
    await p.pg.goto(URL + "?test=1&fps=1")
    await p.wait(lambda s: s.get("screen") == "title", "титул под заслонкой", 90)
    await orient(p, 780, 360, True)
    await p.pg.evaluate(STALE_JS, ["innerHeight", 780])
    await p.pg.evaluate("window.dispatchEvent(new Event('resize'))")
    await p.wait(lambda s: s.get("covered") is False, "заслонка снята после поворота", 10)
    await p.pg.wait_for_timeout(2000)
    await p.shot("1_landscape_stale_innerHeight")
    await check_fit(p, 780, 360, "innerHeight остался 780 после поворота")
    await p.press("Start", None, 1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "касание «начать» при старом innerHeight", 10)
    check(bool(st), f"{p.name}: касание «начать» попало (мастерская)")
    await p.pg.wait_for_timeout(1500)
    await p.shot("2_hub")
    await check_fit(p, 780, 360, "мастерская")
    diag = await p.pg.evaluate("(()=>{const d=document.getElementById('wnb-diag');if(!d)return null;"
                               "const r=d.getBoundingClientRect();return [d.textContent, r.top, r.height]})()")
    check(bool(diag) and diag[1] <= 1 and "screen" in diag[0] and "godot" in diag[0],
          f"{p.name}: ?fps=1 — строка размеров страницы у верхнего края: {diag}")
    p.check_console()
    await p.ctx.close()
    # обратный случай: innerWidth = 360 (книжная) с самого начала, окно альбомное
    q = await new_page(b, "stale_w", touch=True, mobile=True, w=780, h=360, dpr=3,
                       legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    await q.ctx.add_init_script("Object.defineProperty(window, 'innerWidth', {configurable: true, get: () => 360});")
    await orient(q, 780, 360, True)
    await q.boot()
    await q.pg.wait_for_timeout(1500)
    await q.shot("1_title_stale_innerWidth")
    await check_fit(q, 780, 360, "innerWidth = 360 при альбомном окне")
    await q.press("Start", None, 1200)
    st = await q.wait(lambda s: s.get("screen") == "hub", "касание «начать» при старом innerWidth", 10)
    check(bool(st), f"{q.name}: касание «начать» попало (мастерская)")
    q.check_console()
    await q.ctx.close()


async def sc_a11y(b):
    """prefers-reduced-motion → «Без анимации»; полный экран из настроек (в headless может не включиться)."""
    p = await new_page(b, "calm", motion="reduce")
    st, _, _ = await p.boot()
    check(st.get("calm") is True, f"{p.name}: prefers-reduced-motion: reduce → «Без анимации»")
    await p.pg.wait_for_timeout(1500)
    st = await p.state()
    check("loop:martin_wave" not in st["frames"]["sets"], f"{p.name}: без анимации петли титула не качаются")
    await p.shot("1_title_calm")
    await p.press("Gear", wait=600)
    await p.press("Tab_graphics", wait=400)
    await p.press("Fullscreen", wait=1200)
    fs = await p.pg.evaluate("!!document.fullscreenElement")
    st = await p.state()
    info(f"{p.name}: полный экран из настроек: document.fullscreenElement={fs}, игра видит {st.get('fullscreen')}")
    check(fs or st.get("fullscreen") is not None, f"{p.name}: кнопка полного экрана не падает")
    if fs:
        await p.pg.wait_for_timeout(800)
        await p.shot("2_fullscreen")
        iw, ih = await p.pg.evaluate("[innerWidth, innerHeight]")   # Firefox без окна: полный экран = его «экран» 1366×768
        await check_fit(p, iw, ih, "полный экран на компьютере")
        await p.press("Fullscreen", wait=800)
    p.check_console()
    await p.ctx.close()
    await kb_order_web(b)
    await calm_priority(b)


async def kb_order_web(b):
    """Обход с клавиатуры в браузере — по списку game.py (A11y.kb_items): в мастерской фокуса клавиатуры ещё нет,
    ↓ — первая карточка, ↑ с неё — заворот на последний пункт («Меню»), Tab — первая группа («Клиенты»), Enter —
    задание; в задании ↓ — первая деталь списка (кружки на коляске в список не входят)."""
    p = await new_page(b, "kb_order", legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    await p.boot()
    await title_ready(p)
    await p.press("Start", wait=1200)
    await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 10)
    await p.pg.wait_for_timeout(600)
    await p.key("ArrowDown", 300)
    st = await p.state()
    check(st.get("kb") == "Card_flat", f"{p.name}: ↓ в мастерской — первая карточка ({st.get('kb')})")
    await p.key("ArrowUp", 300)
    st = await p.state()
    check(st.get("kb") in ("Lang", "Flag", "Gear"), f"{p.name}: ↑ с первого пункта — заворот на последний ({st.get('kb')})")
    await p.key("Tab", 300)
    st = await p.state()
    check(st.get("kb") == "Card_flat", f"{p.name}: Tab с «Меню» — заворот на первую группу, «Клиенты» ({st.get('kb')})")
    act = await p.pg.evaluate("document.activeElement && (document.activeElement.id || document.activeElement.tagName)")
    check(act == "canvas", f"{p.name}: после Tab и стрелок фокус страницы — у холста ({act}), браузер его не увёл")
    # F1 — справка игры (не справка браузера), Esc — закрыть; фокус остаётся у холста, вкладок не прибавилось
    n_pages = len(p.ctx.pages)
    await p.key("F1", 600)
    st = await p.state()
    h1 = st.get("help")
    await p.key("Escape", 500)
    st = await p.state()
    act = await p.pg.evaluate("document.activeElement && (document.activeElement.id || document.activeElement.tagName)")
    check(h1 is True and st.get("help") is False and act == "canvas" and len(p.ctx.pages) == n_pages,
          f"{p.name}: F1 — справка игры ({h1}), Esc закрыл ({st.get('help')}), фокус у холста ({act}), новых вкладок нет")
    await p.key("Enter", 1200)
    st = await p.wait(lambda s: s.get("screen") == "job", "задание по Enter", 10)
    await p.key("ArrowDown", 300)
    st = await p.state()
    check(str(st.get("kb", "")).startswith("Part_"), f"{p.name}: ↓ в задании — первая деталь списка ({st.get('kb')})")
    p.check_console()
    await p.ctx.close()


async def calm_priority(b):
    """«Без анимации»: выбор игрока (calm_set в settings.json) главнее системы — как load_settings в game.py; выбор,
    сделанный в игре, переживает перезагрузку при системном reduce."""
    cases = [("calm_off_set", "reduce", {"a11y": {"calm": False, "calm_set": True}}, False),
             ("calm_on_set", "no-preference", {"a11y": {"calm": True, "calm_set": True}}, True),
             ("calm_unset", "reduce", {"a11y": {"calm": False, "calm_set": False}}, True),
             ("calm_sys_off", "no-preference", {"a11y": {"calm": True}}, False)]
    for name, motion, sets, want in cases:
        p = await new_page(b, name, motion=motion, legacy={"settings.json": sets})
        st, _, _ = await p.boot()
        check(st.get("calm") is want, f"{p.name}: система {motion}, настройки {json.dumps(sets['a11y'])} → "
                                      f"«Без анимации» {st.get('calm')} (ждали {want}, как game.py)")
        if name == "calm_unset":                       # игрок сам выключил «Без анимации» — после перезагрузки так же
            await p.pg.wait_for_timeout(2500)
            await p.press("Gear", wait=900)
            await p.press("Tab_access", wait=400)
            await p.press("Acc_calm", wait=400)
            await p.press("Done", wait=400)
            st = await p.state()
            await p.pg.reload()
            st2 = await p.wait(lambda s: s.get("screen") in ("title", "hub", "intro"), "перезагрузка", 60)
            check(st.get("calm") is False and st2.get("calm") is False,
                  f"{p.name}: игрок выключил «Без анимации» при системном reduce — {st.get('calm')}, после "
                  f"перезагрузки {st2.get('calm')}")
        p.check_console()
        await p.ctx.close()


async def drag_chair(p, secs):
    """Крутить коляску перетаскиванием (мышью — и в мобильном окне) secs секунд: диагноз «с поворотом»."""
    st = await p.state()
    hb = [x for x in st.get("buttons", []) if x[0].startswith("Spot_")]
    cx, cy = (575, 380)
    if hb:
        cx = sum(x[1] + x[3] / 2 for x in hb) / len(hb)
        cy = sum(x[2] + x[4] / 2 for x in hb) / len(hb)
    x0, y0 = await p.at(cx - 60, cy + 40)
    x1, _ = await p.at(cx + 60, cy + 40)
    await p.pg.mouse.move(x0, y0)
    await p.pg.mouse.down()
    t0 = time.time()
    k = 0
    while time.time() - t0 < secs:
        k += 1
        u = (k % 20) / 20
        x = x0 + (x1 - x0) * (u if (k // 20) % 2 == 0 else 1 - u)
        await p.pg.mouse.move(x, y0)
        await p.pg.wait_for_timeout(60)
    await p.pg.mouse.up()


async def measure_phase(p, secs, prof_out=None, key="", during=None):
    """Кадры/с за secs секунд (среднее окон по 1 с без первого), худший кадр; с ?prof=1 — последняя сводка профиля."""
    if during:
        (f, w), _ = await asyncio.gather(measure_fps(p, secs), during(p, secs))
    else:
        f, w = await measure_fps(p, secs)
    if prof_out is not None:
        pr = (await p.state()).get("prof") or {}
        if pr:
            prof_out[key] = pr
    return f, w


async def perf_run(b, label, rate, mobile, query="", prof_out=None):
    """Один проход замера: титул → мастерская → задание flat: диагноз (стоя и крутим коляску), ремонт (инструмент
    в руке у курсора), проезд. Возврат: словарь кадров/с по фазам."""
    p = await new_page(b, "perf", touch=mobile, mobile=mobile, w=740 if mobile else 1280, h=360 if mobile else 720,
                       dpr=3 if mobile else 1, legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    cdp = await p.ctx.new_cdp_session(p.pg)
    await cdp.send("Network.enable")
    await cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    await cdp.send("Emulation.setCPUThrottlingRate", {"rate": rate})
    r = {"label": label}
    st, secs, times = await p.boot(query)
    r["t_title"] = (times.get("title", 0) - times.get("start", 0)) / 1000
    await p.wait(lambda s: s["frames"]["sets"].get("loop:barty_wave", [0, 1])[0] == 36, "петли титула", 120, quiet=True)
    r["title"], r["w_title"] = await measure_phase(p, 5, prof_out, "title")
    await p.press("Start", wait=1500)
    await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 30, quiet=True)
    await p.pg.wait_for_timeout(1500)                       # карточки въехали
    r["hub"], r["w_hub"] = await measure_phase(p, 5, prof_out, "hub")
    await p.press("Card_flat", wait=1500)
    await p.wait(lambda s: s.get("screen") == "job", "задание", 30, quiet=True)
    t0 = time.time()
    await p.wait(lambda s: all(v[0] == v[1] for k, v in s["frames"]["sets"].items() if k.startswith("tt:")),
                 "кадры поворота", 120, quiet=True)
    r["t_tt"] = time.time() - t0
    await p.wait(lambda s: s["frames"]["queue"] == 0 and s["frames"]["inflight"] == 0 and s["frames"]["wait"] == 0,
                 "все кадры задания (поворот, волшебство, проезд)", 120, quiet=True)
    r["t_all"] = time.time() - t0
    r["job"], r["w_job"] = await measure_phase(p, 5, prof_out, "diagnose")
    r["drag"], r["w_drag"] = await measure_phase(p, 5, prof_out, "diagnose_drag", drag_chair)
    r["dec"] = (await p.state()).get("frames", {}).get("decode_ms")
    await p.shot(f"{label.replace(' ', '_')}_1_diagnose")
    st = await follow_hints(p, lambda s: s.get("phase") == "repair", 60)
    st = await p.wait(lambda s: s.get("phase") == "repair" and s.get("hint"), "ремонт", 10, quiet=True)
    hint = (st.get("hint") or [""])[0]
    if hint.startswith("Tool_"):
        await p.press(hint, st, 400)                        # инструмент в руке (рисуется у курсора)
        x, y = await p.at(560, 380)
        await p.pg.mouse.move(x, y)
    await p.pg.wait_for_timeout(1200)
    r["repair"], r["w_repair"] = await measure_phase(p, 5, prof_out, "repair")
    await p.shot(f"{label.replace(' ', '_')}_2_repair")
    st = await follow_hints(p, lambda s: s.get("phase") == "test", 120)
    await p.wait(lambda s: all(v[0] == v[1] for k, v in s["frames"]["sets"].items() if k.startswith("loop:ride_")),
                 "петля проезда", 60, quiet=True)
    await p.press("TestDrive", wait=200)
    await p.wait(lambda s: (s.get("ride") or {}).get("riding"), "проезд", 10, quiet=True)
    await p.pg.wait_for_timeout(600)
    r["ride"], r["w_ride"] = await measure_phase(p, 3.2, prof_out, "ride")
    await p.shot(f"{label.replace(' ', '_')}_3_ride")
    await p.ctx.close()
    info(f"{label}: титул {r['t_title']:.1f} с; fps титул {r['title']:.0f}, мастерская {r['hub']:.0f}, диагноз "
         f"{r['job']:.0f} (крутим {r['drag']:.0f}, худший {r['w_drag']:.0f} мс), ремонт {r['repair']:.0f} "
         f"(худший {r['w_repair']:.0f} мс), проезд {r['ride']:.0f} (худший {r['w_ride']:.0f} мс); кадры поворота "
         f"за {r['t_tt']:.1f} с, все кадры задания за {r['t_all']:.1f} с, декодирование {r['dec']} мс/кадр")
    return r


async def sc_perf(b):
    """Замер: загрузка до титула и кадры/с на титуле, в мастерской и в задании (диагноз — стоя и с поворотом коляски,
    ремонт, проезд) — без замедления, с замедлением процессора ×4 и ×6 (CDP Emulation.setCPUThrottlingRate) и в
    мобильном окне (740×360, dpr 3, ×6 — по снимку владельца 19.11 это и есть его телефон: 27 к/с в мастерской).
    WNB_PERF_RES=720,1080 — добавить проходы телефона с ?res=…"""
    if not CHROMIUM:
        return skip_cdp("perf")
    rows = []
    runs = [("desktop x1", 1, False, ""), ("desktop x4", 4, False, ""), ("desktop x6", 6, False, ""),
            ("phone x6", 6, True, "")]
    for v in filter(None, os.environ.get("WNB_PERF_RES", "").split(",")):
        runs.append((f"phone x6 res{v}", 6, True, f"&res={v}"))
    for label, rate, mobile, q in runs:
        rows.append(await perf_run(b, label, rate, mobile, q))
    metrics["perf"] = rows
    check(all(r.get("hub", 0) > 0 and r.get("repair", 0) > 0 for r in rows), "perf: замер кадров/с снят")


async def sc_prof(b):
    """?prof=1 — профилировка (ui/prof.gd): сводки в window.wnbState.prof по фазам на телефоне ×6 (что дороже всего
    в кадре) → godot/tests/web_shots/prof_phone_x6.json и строки в выводе; «[wnb] prof …» в консоли браузера."""
    if not CHROMIUM:
        return skip_cdp("prof")
    prof = {}
    r = await perf_run(b, "prof phone x6", 6, True, "&prof=1", prof)
    check(bool(prof.get("hub")) and bool(prof.get("repair")), f"prof: сводки профиля сняты по фазам ({sorted(prof)})")
    with open(os.path.join(SHOTS, "prof_phone_x6.json"), "w", encoding="utf-8") as f:
        json.dump({"fps": r, "prof": prof}, f, ensure_ascii=False, indent=1)
    for k, pr in prof.items():
        top = ", ".join(f"{x[0]} {x[1]:.2f}" for x in pr.get("draw_top", [])[:6])
        tx = ", ".join(f"{n} {v[0]:.2f}/{v[1]:.0f}" for n, v in pr.get("text", {}).items())
        info(f"prof {k}: кадр {pr.get('frame_ms')} мс — process {pr.get('process_ms')}, draw {pr.get('draw_ms')}, "
             f"render {pr.get('render_cpu_ms')} (gpu {pr.get('render_gpu_ms')}), вызовов рисования "
             f"{pr.get('draw_calls')}, перерисовок {pr.get('redraws')}; узлы: {top}; текст мс/вызовов: {tx}; "
             f"тик {pr.get('tick')}")
    metrics["prof"] = prof


# Экраны и состояния для замера по всем экранам (sc_screens): [ключ, состояние tests/shots.gd (window.wnbStage),
# что делать во время замера, секунд замера]. Состояния — те же, что у снимков --shots (сверка картинки).
SCREENS = [
    ("title", "title", None, 4), ("intro", "intro_2", None, 4), ("hub", "hub", None, 4),
    ("job_loading", "job_joystick_diagnose", "loading", 4),   # кадры коляски качаются и распаковываются (просадки)
    ("job_diag", "job_flat_inspected", None, 4), ("job_repair", "job_flat_repair", None, 4),
    ("mini_pump", "mini_pump", None, 4), ("mini_gap", "mini_gap", None, 4), ("mini_ping", "mini_ping", None, 4),
    ("mini_meter", "mini_meter", None, 4), ("result", "result_lift", None, 4),
    ("seat_lesson1", "seat_lessons", None, 4), ("seat_slump", "seat_lesson_slump", None, 4),
    ("seat_measure", "seat_lesson_measure", None, 4), ("seat_front", "seat_lesson_front", None, 4),
    ("seat_front_norm", "seat_lesson_front_norm", None, 4),
    ("seat_fit", "seat_fit_troll", None, 4), ("seat_fit_drag", "seat_fit_troll", "slider", 4),
    ("seat_fit_front", "seat_fit_dryad", None, 4), ("seat_fit_front_drag", "seat_fit_dryad", "slider", 4),
    ("seat_fit_top", "seat_fit_owl", None, 4),
    ("seat_quiz", "seat_quiz_q1", None, 4), ("seat_quiz_answer", "seat_quiz_wrong", None, 4),
    ("seat_quiz_myth", "seat_quiz_myth", None, 4), ("seat_quiz_wedge", "seat_quiz_wedge", None, 4),
    ("seat_quiz_pass", "seat_quiz_pass", None, 4),
    ("guild", "guild_open", None, 4), ("tech_ops", "tech_ops", None, 4), ("tech_manual", "tech_manual", None, 4),
    ("tech_spec", "tech_spec", None, 4), ("tech_mini", "tech_mini", None, 4), ("tech_test", "tech_test", None, 4),
    ("tech_ride", "tech_ride", None, 3), ("tech_result", "tech_result", None, 4),
    ("exam", "exam_ticket", None, 4), ("exam_failed", "exam_failed", None, 4), ("exam_passed", "exam_passed", None, 4),
    ("garage", "garage", None, 4), ("garage_open", "garage_open", None, 4),
    ("ending", "ending", None, 4), ("credits", "credits", None, 4),
    ("settings_sound", "settings_sound", None, 4), ("settings_graphics", "settings_graphics", None, 4),
    ("settings_access", "settings_access", None, 4), ("settings_game", "settings_game", None, 4),
    ("help", "help", None, 4), ("feedback", "feedback_general", None, 4),
    ("share_paste", "share_paste", None, 4), ("share_builder", "share_builder", None, 4),
    ("share_summary", "share_summary", None, 4),
]


async def drag_slider(p, secs, name="Slider_leg"):
    """Двигать ползунок примерки мышью туда-сюда secs секунд (рисунок едет за ползунком)."""
    st = await p.state()
    sl = [x for x in st.get("buttons", []) if x[0] == name] or \
         [x for x in st.get("buttons", []) if x[0].startswith("Slider_")]
    if not sl:
        await p.pg.wait_for_timeout(int(secs * 1000))
        return
    b = sl[0]
    y = b[2] + b[4] / 2
    x0, py = await p.at(b[1] + 25, y)
    x1, _ = await p.at(b[1] + b[3] - 25, y)
    await p.pg.mouse.move(x0, py)
    await p.pg.mouse.down()
    t0 = time.time()
    k = 0
    while time.time() - t0 < secs:
        k += 1
        u = (k % 24) / 24
        await p.pg.mouse.move(x0 + (x1 - x0) * (u if (k // 24) % 2 == 0 else 1 - u), py)
        await p.pg.wait_for_timeout(50)
    await p.pg.mouse.up()


async def measure_win(p, secs, during=None, profs=None):
    """Кадры/с (среднее окон по 1 с без первого) и худший кадр за всё время замера (мс); profs — сюда сводки профиля
    по окнам (с ?prof=1)."""
    fps, worst = [], []

    async def sample():
        t0 = time.time()
        while time.time() - t0 < secs:
            st = await p.state()
            if st.get("fps"):
                fps.append(st["fps"])
                worst.append(st.get("worst_ms", 0))
                if profs is not None and st.get("prof"):
                    profs.append(dict(st["prof"], frames_stats=st.get("frames")))
            await p.pg.wait_for_timeout(1000)
    if during:
        await asyncio.gather(sample(), during(p, secs))
    else:
        await sample()
    f = (sum(fps[1:]) / max(1, len(fps) - 1)) if len(fps) > 1 else (fps[0] if fps else 0)
    return f, max(worst[1:] or worst or [0])


async def screens_run(b, label, rate, mobile, query="", only=None):
    """Один проход по всем экранам: состояние (wnbStage) → дождаться кадров → замер. Возврат: ключ → [к/с, худший мс,
    профиль]."""
    p = await new_page(b, "screens", touch=mobile, mobile=mobile, w=740 if mobile else 1280, h=360 if mobile else 720,
                       dpr=3 if mobile else 1, legacy={"save.json": {"done": [], "tutorial_skipped": True}})
    p.allow.append("ERR_NO_BUFFER_SPACE")   # Windows: сокетам локального сервера не хватило буфера на поток кадров —
    cdp = await p.ctx.new_cdp_session(p.pg)  # игра повторяет загрузку сама (Frames: retry)
    await cdp.send("Emulation.setCPUThrottlingRate", {"rate": rate})
    await p.boot(query)
    await p.wait(lambda s: s["frames"]["sets"].get("loop:barty_wave", [0, 1])[0] == 36, "петли титула", 120, quiet=True)
    out = {}
    for key, stage, act, secs in SCREENS:
        if only and key not in only:
            continue
        await p.pg.evaluate("(n) => window.wnbStage(n)", stage)
        if act == "loading":                              # замер сразу: кадры задания ещё качаются
            await p.pg.wait_for_timeout(300)
            f0 = (await p.state()).get("frames", {}).get("decoded", 0)
            profs = []
            f, w = await measure_win(p, secs + 1, profs=profs)
            st = await p.state()
            pr = max(profs, key=lambda x: x.get("worst_ms", 0)) if profs else {}   # окно с худшим кадром
            pr = dict(pr, decoded=st.get("frames", {}).get("decoded", 0) - f0, windows=[
                [x.get("fps"), x.get("worst_ms"), x.get("frame_ms"), x.get("process_ms"), x.get("draw_ms"),
                 x.get("render_cpu_ms"), (x.get("text") or {}).get("frames")] for x in profs])
            out[key] = [round(f, 1), round(w, 1), pr]
            await p.wait(lambda s: s.get("frames", {}).get("queue", 1) == 0, "кадры", 60, quiet=True)
            continue
        ok = False
        t0 = time.time()
        while time.time() - t0 < 40:
            if await p.pg.evaluate("window.wnbStaged || ''") == stage:
                ok = True
                break
            await p.pg.wait_for_timeout(200)
        if not ok:
            check(False, f"{label}: состояние {stage} не встало")
            continue
        await p.wait(lambda s: s["frames"]["queue"] == 0 and s["frames"]["inflight"] == 0 and s["frames"]["wait"] == 0,
                     "кадры докачались", 30, quiet=True)
        await p.pg.wait_for_timeout(600)
        during = drag_slider if act == "slider" else None
        f, w = await measure_win(p, secs + 1, during)
        pr = (await p.state()).get("prof") or {}
        out[key] = [round(f, 1), round(w, 1), pr]
        if mobile and rate >= 6 and not query:
            await p.shot(f"{label.replace(' ', '_')}_{key}")
    p.check_console()
    await p.ctx.close()
    slow = [f"{k} {v[0]:.0f}" for k, v in out.items() if v[0] < 50]
    info(f"{label}: экранов {len(out)}; ниже 50 к/с: {', '.join(slow) or 'нет'}")
    return out


async def sc_screens(b):
    """Замер кадров/с по ВСЕМ экранам и состояниям (SCREENS; состояния ставит игра — window.wnbStage, ?test=1):
    без замедления, ×6 и «телефон ×6» (740×360, dpr 3); плюс проход телефона ×6 с ?prof=1 — что дороже всего в кадре.
    WNB_SCREENS=ключ,ключ — только эти; WNB_SCREENS_MODES=x1,x6,phone,prof — только эти проходы (phone0 — телефон
    с прежней раскладкой, ?phone=0: сверка скорости телефонного режима).
    Итог — godot/tests/web_shots/screens_perf.json и таблица в конце вывода."""
    if not CHROMIUM:
        return skip_cdp("screens")
    only = [x for x in os.environ.get("WNB_SCREENS", "").split(",") if x]
    modes = [x for x in os.environ.get("WNB_SCREENS_MODES", "x1,x6,phone,prof").split(",") if x]
    runs = {"x1": ("desktop x1", 1, False, ""), "x6": ("desktop x6", 6, False, ""), "phone": ("phone x6", 6, True, ""),
            "prof": ("prof phone x6", 6, True, "&prof=1"),
            "phone0": ("phone x6, phone=0", 6, True, "&phone=0")}    # телефон с прежней раскладкой (сверка скорости)
    res = {}
    for m in modes:
        label, rate, mobile, q = runs[m]
        res[m] = await screens_run(b, label, rate, mobile, q, only)
    with open(os.path.join(SHOTS, "screens_perf.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    metrics["screens"] = res
    check(all(len(v) > 0 for v in res.values()), f"screens: замер по экранам снят ({', '.join(f'{k}: {len(v)}' for k, v in res.items())})")
    for k, (fv, wv, pr) in res.get("prof", {}).items():
        if not pr:
            continue
        top = ", ".join(f"{x[0]} {x[1]:.2f}" for x in pr.get("draw_top", [])[:5])
        info(f"prof {k}: кадр {pr.get('frame_ms')} мс — process {pr.get('process_ms')}, draw {pr.get('draw_ms')}, "
             f"render {pr.get('render_cpu_ms')}, вызовов {pr.get('draw_calls')}, перерисовок {pr.get('redraws')}; {top}")


async def sc_fpshud(b):
    """?fps=1 — плашка и строка «[wnb] fps …» в консоли; в ссылки-задания fps не попадает."""
    p = await new_page(b, "fps")
    await p.pg.goto(URL + "?test=1&fps=1")
    await p.wait(lambda s: s.get("screen") == "title", "титул", 60)
    await p.pg.wait_for_timeout(3800)
    lines = [c for c in p.console if "[wnb] fps" in c]
    check(bool(lines), f"{p.name}: строка в консоли браузера: {lines[-1][:120] if lines else '—'}")
    await p.shot("1_title_fps")
    # «Ссылка с прогрессом» при ?fps=1&test=1: в ссылку параметры замера не попадают, адрес — из сборки (--base-url)
    await p.press("Gear", wait=600)
    await p.press("Tab_game", wait=400)
    await p.press("Share_link", wait=800)
    link = await clip_text(p)
    info_ = json.load(open(os.path.join(build_web.OUT, "build_info.json"), encoding="utf-8"))
    keys = set(urllib.parse.parse_qs(urllib.parse.urlsplit(link).query))
    check(link.startswith(info_["base_url"] + "?load=P.") and keys == {"load"},
          f"{p.name}: ссылка с прогрессом ведёт на сборку и без ?fps/?test (ключи {sorted(keys)}): {link[:70]}…")
    p.check_console()
    await p.ctx.close()


async def feedback_page(b, name, lang, outbox=None):
    """Страница с перехватом адреса таблицы замечаний: запросы записываются, наружу ничего не уходит (fulfill 200
    или abort — «нет сети»). outbox — очередь pygame-версии в localStorage «wnb:outbox» до запуска."""
    raw = {"save.json": json.dumps({"done": ["flat"], "garage": [["flat", 3]], "tutorial_skipped": True}),
           "settings.json": json.dumps({"lang": lang})}
    if outbox is not None:
        raw["outbox"] = json.dumps(outbox)
    p = await new_page(b, name, legacy_raw=raw)
    p.fb = []
    p.fb_mode = ["ok"]
    furl = json.load(open(os.path.join(build_web.OUT, "..", "..", "content", "data", "game_consts.json"),
                          encoding="utf-8"))["feedback_url"]
    p.furl = furl

    async def route(r):
        rq = r.request
        p.fb.append({"method": rq.method, "url": rq.url, "headers": await rq.all_headers(), "body": rq.post_data,
                     "mode": p.fb_mode[0]})
        if p.fb_mode[0] == "ok":
            await r.fulfill(status=200, body="ok")
        else:
            await r.abort("internetdisconnected")
    host = urllib.parse.urlsplit(furl).netloc
    await p.ctx.route(lambda u: urllib.parse.urlsplit(u).netloc == host, route)   # раньше общего «наружу — abort»
    return p


async def type_text(p, text):
    """Набор как с физической клавиатуры (русская раскладка — keydown с key «п» и кодом клавиши): keyboard.type
    Playwright вставляет не-латиницу через insertText без нажатий — холст Godot их не видит. Firefox/WebKit: CDP нет,
    а keyboard.press не знает «п» — события keydown/keyup страницы прямо на холст (Godot их принимает так же)."""
    if not CHROMIUM:
        await p.pg.evaluate("""(t) => { const c = document.getElementById('canvas');
            for (const ch of t) { const code = ch === ' ' ? 'Space' : (/\p{L}/u.test(ch) ? 'KeyA' : 'Digit1');
              for (const ty of ['keydown', 'keyup'])
                c.dispatchEvent(new KeyboardEvent(ty, { key: ch, code: code, bubbles: true, cancelable: true })); } }""", text)
        return
    cdp = await p.ctx.new_cdp_session(p.pg)
    for ch in text:
        ev = {"key": ch, "text": ch, "unmodifiedText": ch, "code": "KeyA" if ch.isalpha() else "Digit1"}
        if ch == " ":
            ev.update(code="Space", windowsVirtualKeyCode=32)
        await cdp.send("Input.dispatchKeyEvent", dict(ev, type="keyDown"))
        await cdp.send("Input.dispatchKeyEvent", {"type": "keyUp", "key": ch, "code": ev["code"]})
    await cdp.detach()


async def fb_send(p, stage, reason, text, enter=False):
    """Открыть ⚑ на экране stage, причина reason, напечатать text в поле, «ОТПРАВИТЬ» (или Enter в поле)."""
    await p.pg.evaluate("(n) => { window.wnbStaged = ''; window.wnbStage(n); }", stage)
    t0 = time.time()
    while time.time() - t0 < 30 and await p.pg.evaluate("window.wnbStaged || ''") != stage:
        await p.pg.wait_for_timeout(200)
    await p.pg.wait_for_timeout(800)
    await p.press("Flag", wait=600)
    await p.press("Reason_%d" % reason, wait=200)
    await p.press("Comment", wait=200)
    await type_text(p, text)
    await p.pg.wait_for_timeout(300)
    n0 = len(p.fb)
    if enter:
        await p.key("Enter", 600)
    else:
        await p.press("Send", wait=600)
    t0 = time.time()
    while time.time() - t0 < 8 and len(p.fb) == n0:
        await p.pg.wait_for_timeout(200)
    return p.fb[n0] if len(p.fb) > n0 else None


async def sc_feedback(b):
    """Отправка замечания в браузере ↔ game.py (без настоящей таблицы: адрес перехвачен, ответ — локальный).
    Адрес, метод, заголовок, тело (поля = эталон game.py content/feedback_ref.json, формат = json.dumps: кириллица
    в виде \\uXXXX), RU и EN, обрезка длинного текста (600), Enter в поле — отправка, нет сети — очередь «wnb:outbox» и
    досылка при следующем запуске, недосланное pygame-версией — тоже досылается."""
    ref = json.load(open(os.path.join(build_web.OUT, "..", "..", "content", "feedback_ref.json"), encoding="utf-8"))
    leftover = json.dumps(dict(ref["general_hub"], time="2026-11-01T10:00:00", platform="web", uid="pygame-left"))
    p = await feedback_page(b, "feedback", "ru", outbox=[leftover])
    await p.boot()
    await title_ready(p)
    await p.press("Lang", wait=500)                       # браузер стартует по-английски (как game.py) — русский кнопкой
    t0 = time.time()
    while time.time() - t0 < 10 and not p.fb:
        await p.pg.wait_for_timeout(200)
    await p.pg.wait_for_timeout(800)
    q = await p.pg.evaluate("localStorage.getItem('wnb:outbox')")
    check(len(p.fb) == 1 and p.fb[0]["body"] == leftover and q == "[]",
          f"{p.name}: недосланное pygame-версией ушло при запуске тем же телом, очередь пуста ({len(p.fb)} запр., {q})")

    def same(p, r, key, what):
        if not check(r is not None, f"{p.name}: {what}: запрос ушёл"):
            return {}
        body = r["body"] or ""
        d = json.loads(body)
        exp = {k: v for k, v in ref[key].items() if not k.startswith("_")}
        diff = {k: (v, d.get(k)) for k, v in exp.items() if d.get(k) != v}
        check(r["url"] == p.furl and r["method"] == "POST" and r["headers"].get("content-type") == "text/plain",
              f"{p.name}: {what}: адрес = FEEDBACK_URL game.py, POST, Content-Type {r['headers'].get('content-type')}")
        check(not diff and d.get("platform") == "godot-web" and d.get("uid") and d.get("time"),
              f"{p.name}: {what}: поля = game.py ({len(exp)}), platform {d.get('platform')}"
              + (f" — РАЗНИЦА {json.dumps(diff, ensure_ascii=False)[:300]}" if diff else ""))
        check(body.isascii() and body == json.dumps(d),
              f"{p.name}: {what}: тело как json.dumps game.py (ASCII, «, »/«: »; {len(body)} байт, снимок "
              f"{len(d.get('screenshot_jpg_b64', '')) // 1024} КБ)")
        return d

    r = await fb_send(p, "hub", 1, ref["general_hub"]["comment"])
    same(p, r, "general_hub", "⚑ мастерская RU")
    await p.shot("1_after_send")
    long = ("Длинный текст ёжика — " * 40)[:650]
    r = await fb_send(p, "hub", 1, long, enter=True)
    d = json.loads(r["body"]) if r else {}
    check(d.get("comment") == long[:600].strip(), f"{p.name}: Enter в поле отправляет; длинный текст обрезан как в "
                                                  f"game.py: {len(d.get('comment', ''))} знаков из {len(long)}")
    p.fb_mode[0] = "abort"
    p.allow += ["ERR_INTERNET_DISCONNECTED"]              # ожидаемо: «нет сети» для запроса в таблицу
    r = await fb_send(p, "hub", 0, "нет сети")
    await p.pg.wait_for_timeout(800)
    q = json.loads(await p.pg.evaluate("localStorage.getItem('wnb:outbox') || '[]'"))
    check(r is not None and q == [r["body"]], f"{p.name}: нет сети — замечание осталось в очереди wnb:outbox ({len(q)})")
    st = await p.state()
    check(bool(st.get("screen")), f"{p.name}: игра живёт после обрыва ({st.get('screen')}, тост «{st.get('toast')}»)")
    p.fb_mode[0] = "ok"
    n0 = len(p.fb)
    await p.pg.reload()
    await p.wait(lambda s: s.get("screen") in ("title", "hub"), "перезагрузка", 60)
    t0 = time.time()
    while time.time() - t0 < 10 and len(p.fb) == n0:
        await p.pg.wait_for_timeout(200)
    await p.pg.wait_for_timeout(800)
    q2 = await p.pg.evaluate("localStorage.getItem('wnb:outbox')")
    check(len(p.fb) == n0 + 1 and r is not None and p.fb[-1]["body"] == r["body"] and q2 == "[]",
          f"{p.name}: следующий запуск дослал то же тело, очередь пуста ({len(p.fb) - n0} запр., {q2})")
    p.check_console()
    await p.ctx.close()
    e = await feedback_page(b, "feedback_en", "en")
    await e.boot()
    r = await fb_send(e, "garage", 3, ref["general_garage_en"]["comment"])
    same(e, r, "general_garage_en", "⚑ гараж EN")
    e.check_console()
    await e.ctx.close()


PLATE_STAGES = ["title", "hub", "guild_open", "job_flat_repair"]


async def plates_clear(p, tag):
    """?fps=1: плашка кадров/с (#wnb-hud) и строка размеров (#wnb-diag) видны целиком (текст не обрезан) и не
    закрывают ни одной кнопки игры (wnbState.buttons, 1280×720 → CSS) и кнопки ⛶; касания сквозь них (pointer-events)."""
    r = await p.pg.evaluate("""(()=>{const o={};for(const id of ['wnb-hud','wnb-diag','wnb-full']){const e=document.
        getElementById(id);if(!e||getComputedStyle(e).display==='none'){o[id]=null;continue}const b=e.getBoundingClientRect();
        o[id]={r:[b.left,b.top,b.width,b.height],t:e.textContent,mode:e.getAttribute('data-mode'),
        full:e.scrollHeight<=e.clientHeight+1,pe:getComputedStyle(e).pointerEvents}}return o})()""")
    gr, c, st = await game_rect(p)
    k = gr[2] / 1280
    btns = [(x[0], gr[0] + x[1] * k, gr[1] + x[2] * k, x[3] * k, x[4] * k) for x in st.get("buttons", [])]
    if r.get("wnb-full"):
        btns.append(("⛶",) + tuple(r["wnb-full"]["r"]))

    def hit(a, b):
        return a[0] < b[0] + b[2] - 0.5 and b[0] < a[0] + a[2] - 0.5 and a[1] < b[1] + b[3] - 0.5 and b[1] < a[1] + a[3] - 0.5
    for pid in ("wnb-hud", "wnb-diag"):
        e = r.get(pid)
        if not check(bool(e) and bool(e["t"]), f"{p.name} {tag}: {pid} есть"):
            continue
        over = [b[0] for b in btns if hit(e["r"], b[1:])]
        check(not over and e["full"] and e["pe"] == "none",
              f"{p.name} {tag}: {pid} ({e['mode']}, {e['r'][0]:.0f},{e['r'][1]:.0f} {e['r'][2]:.0f}×{e['r'][3]:.0f}) "
              f"не закрывает кнопок{(' — закрывает ' + ', '.join(over)) if over else ''}, текст целиком={e['full']}, "
              f"касания сквозь={e['pe'] == 'none'}")


async def sc_plates(b):
    """Плашки ?fps=1 на телефоне 2220×1080 (поля по бокам) и в окнах компьютера 16:9 (без полей) и шире 16:9."""
    for name, kw in (("plates_phone", dict(touch=True, mobile=True, w=740, h=360, dpr=3)),
                     ("plates_desk", dict(w=1280, h=720)), ("plates_wide", dict(w=1536, h=730))):
        p = await new_page(b, name, legacy={"save.json": {"done": [], "tutorial_skipped": True}}, **kw)
        if kw.get("mobile"):
            await orient(p, kw["w"], kw["h"], True, kw["dpr"])
        await p.boot("&fps=1")
        await p.pg.wait_for_timeout(2500)
        for stage in PLATE_STAGES:
            await p.pg.evaluate("(n) => window.wnbStage(n)", stage)
            t0 = time.time()
            while time.time() - t0 < 30 and await p.pg.evaluate("window.wnbStaged || ''") != stage:
                await p.pg.wait_for_timeout(200)
            await p.pg.wait_for_timeout(1800)
            await plates_clear(p, stage)
            await p.shot(stage)
        p.check_console()
        await p.ctx.close()


# ---------------- хранение в браузере, загрузчик, сбои сети (находки аудита 20.11) ----------------

SKIP_SEED = {"save.json": {"done": [], "tutorial_skipped": True}}


async def job_to_hub(p, jid):
    """Из мастерской: карточка jid → по подсказкам до итога → в мастерскую (без ожидания петли проезда)."""
    await p.press("Card_" + jid, wait=1200)
    if not await p.wait(lambda s: s.get("screen") == "job", f"задание {jid}", 15):
        return {}
    st = await follow_hints(p, lambda s: s.get("phase") == "test", 240)
    await p.press("TestDrive")
    await p.wait(lambda s: s.get("ride_done"), "проезд закончился", 40)
    await p.press("TestDrive", wait=50)
    await p.wait(lambda s: s.get("screen") == "result", "итог", 15)
    await p.press("ToHub", wait=1200)
    return await p.wait(lambda s: s.get("screen") == "hub", "в мастерскую", 15)


async def to_hub(p):
    await title_ready(p)
    await p.press("Start", wait=1200)
    return await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 15)


async def tab(p, name):
    """Ещё одна вкладка того же браузера (тот же сайт, то же хранилище)."""
    q = Page(p.ctx, await p.ctx.new_page(), name)
    await q.boot()
    return q


async def sc_tabs(b):
    """Две вкладки одного сайта (сохранение — ключами localStorage «wnb-godot:<файл>», SaveGame.merge_saves):
    1) A проходит задание, B (загружена раньше) меняет настройку (M) — прогресс A на месте (раньше IDBFS B стирал его);
    2) B со старым прогрессом проходит своё задание — в хранилище оба (объединение растущих полей);
    3) «Сбросить прогресс» в A при открытой B, B проходит задание — старое не «воскресает» (поколение сохранения)."""
    a = await new_page(b, "tabs_A", legacy=SKIP_SEED)
    await a.boot()
    bq = await tab(a, "tabs_B")
    await a.pg.bring_to_front()
    await to_hub(a)
    st = await job_to_hub(a, "flat")
    check("flat" in st.get("done", []), f"tabs: A прошла flat ({st.get('done')})")
    await bq.pg.bring_to_front()
    await bq.key("m", 1500)
    st = await bq.state()
    check(st.get("sound") is False, f"tabs: B выключила звук (M)")
    c = await tab(a, "tabs_C")
    st = await c.state()
    check("flat" in st.get("done", []) and st.get("sound") is False,
          f"tabs: смена настройки во вкладке B не стёрла прогресс A — новая вкладка: done={st.get('done')}, звук={st.get('sound')}")
    await c.pg.close()
    raw = await a.pg.evaluate("[localStorage.getItem('wnb-godot:save.json'), localStorage.getItem('wnb-godot:settings.json')]")
    check(bool(raw[0]) and bool(raw[1]), "tabs: сохранение и настройки — ключами localStorage wnb-godot:save.json / settings.json")
    # 2) B не знает про flat (загружена до него) — проходит caster
    await bq.pg.bring_to_front()
    await to_hub(bq)
    st = await job_to_hub(bq, "caster")
    check(sorted(st.get("done", [])) == ["caster", "flat"],
          f"tabs: B со старым прогрессом сохранила caster — в ней теперь {st.get('done')} (flat из A подхвачен)")
    c = await tab(a, "tabs_D")
    st = await c.state()
    check(sorted(st.get("done", [])) == ["caster", "flat"], f"tabs: в хранилище оба задания — {st.get('done')}")
    await c.pg.close()
    # 3) сброс в A, B (до сброса знала flat и caster) снова проходит flat (переигранное — тоже «своё новое»)
    await a.pg.bring_to_front()
    await a.pg.wait_for_timeout(500)
    await a.press("Gear", wait=600)
    await a.press("Tab_game", wait=400)
    await a.press("Reset", wait=400)
    await a.press("ResetYes", wait=1200)
    st = await a.wait(lambda s: s.get("screen") == "title", "A: титул после сброса", 15)
    check(st.get("done") == [], f"tabs: A сбросила прогресс ({st.get('done')})")
    await bq.pg.bring_to_front()
    st = await job_to_hub(bq, "flat")
    check(st.get("done") == ["flat"], f"tabs: B после сброса в A снова прошла flat — старое не воскресло: {st.get('done')}")
    c = await tab(a, "tabs_E")
    st = await c.state()
    check(st.get("done") == ["flat"], f"tabs: в хранилище после сброса — только новое из B: {st.get('done')}")
    prev = await a.pg.evaluate("localStorage.getItem('wnb-godot:save.prev.json') || ''")
    check('"done"' in prev, "tabs: копия прежнего сохранения (save.prev.json) пишется")
    for p in (a, bq, c):
        p.check_console()
    await a.ctx.close()


NOLS_JS = """if (/[?&]nols=1/.test(location.search)) Object.defineProperty(window, 'localStorage', { configurable: true,
    get() { throw new DOMException('The operation is insecure.', 'SecurityError'); } });"""


async def sc_store(b):
    """Запасные пути хранения: без localStorage (SecurityError) — игра стартует и пишет в user:// (IndexedDB); те же
    сохранения Godot-версии потом, когда localStorage есть, один раз переносятся в ключи «wnb-godot:*» (так переедут
    сохранения тестеров, записанные до 20.11). Без IndexedDB — тоже стартует и играется."""
    p = await new_page(b, "store_nols")
    await p.ctx.add_init_script(NOLS_JS)
    st, secs, _ = await p.boot("&nols=1")
    check(st.get("screen") == "title", f"store: без localStorage игра стартует ({st.get('screen')}, {secs:.0f} с)")
    await title_ready(p)
    await p.press("Start", wait=1200)
    await p.wait(lambda s: s.get("screen") == "intro", "вступление", 15)
    await p.press("SkipTutorial", wait=1200)
    await p.wait(lambda s: s.get("screen") == "hub", "мастерская после «пропустить»", 15)
    st = await job_to_hub(p, "flat")
    check("flat" in st.get("done", []), f"store: без localStorage задание пройдено ({st.get('done')})")
    await p.pg.wait_for_timeout(1500)                    # запись user:// дошла до IndexedDB
    await p.pg.goto(URL + "?test=1")                     # теперь localStorage есть
    st = await p.wait(lambda s: s.get("screen") in ("title", "hub"), "после смены адреса", 60)
    keys = await p.pg.evaluate("[localStorage.getItem('wnb-godot:moved'), !!localStorage.getItem('wnb-godot:save.json')]")
    check("flat" in st.get("done", []) and keys == ["1", True],
          f"store: сохранение Godot из user:// (IndexedDB) перенесено в localStorage один раз: done={st.get('done')}, "
          f"moved={keys[0]}, ключ save.json={keys[1]}")
    p.allow += ["SecurityError", "insecure"]
    p.check_console()
    await p.ctx.close()
    for tag, js in (("throw", "Object.defineProperty(window, 'indexedDB', { configurable: true, get() { throw new "
                              "DOMException('denied', 'SecurityError'); } });"),
                    ("open", "window.indexedDB.open = function () { throw new DOMException('quota', 'QuotaExceededError'); };")):
        q = await new_page(b, "store_noidb_" + tag)
        await q.ctx.add_init_script(js)
        st, secs, _ = await q.boot()
        ok = st.get("screen") == "title"
        if ok:
            await title_ready(q)
            await q.press("Start", wait=1200)
            st = await q.wait(lambda s: s.get("screen") in ("intro", "hub"), "после «начать»", 15)
        check(st.get("screen") in ("intro", "hub"), f"store: без IndexedDB ({tag}) игра стартует и играется ({st.get('screen')})")
        await q.ctx.close()


async def load_state(p):
    return await p.pg.evaluate("window.wnbLoad ? window.wnbLoad.state() : null")


async def sc_loader(b):
    """Сторож загрузки (web/shell.html): движок «повис» (полоса стоит) — два автоповтора, потом сообщение и кнопка
    «Обновить страницу»; она работает. Пакет отдаёт 500 (старая страница из кеша после выкладки) — то же."""
    hang = {"on": True, "wasm": 0, "pck": 0, "index": 0}

    async def hook(r, path):
        if path.endswith(".wasm"):
            hang["wasm"] += 1
            if hang["on"]:
                await asyncio.sleep(40)
                try:
                    await r.abort()
                except Exception:
                    pass
                return True
        if path.endswith("/") or path.endswith("index.html"):
            hang["index"] += 1
        return False
    p = await new_page(b, "loader_hang", hook=hook)
    p.allow += ["net::", "Failed to load", "ERR_"]
    await p.pg.goto(URL + "?test=1&stall=3")
    t0 = time.time()
    s = None
    while time.time() - t0 < 60:
        try:
            s = await load_state(p)
        except Exception:
            s = None                                     # страница перезагружается
        if s and s.get("reload"):
            break
        await p.pg.wait_for_timeout(500)
    check(bool(s and s.get("reload")) and hang["wasm"] == 3,
          f"loader: движок не качается — после {hang['wasm'] - 1} автоповторов сообщение и кнопка «Обновить» ({s})")
    await p.shot("1_stalled")
    hang["on"] = False
    n_index = hang["index"]
    await p.pg.click("#wnb-reload")
    st = await p.wait(lambda s: s.get("screen") == "title", "титул после «Обновить»", 90)
    check(st.get("screen") == "title" and hang["index"] > n_index,
          f"loader: кнопка «Обновить страницу» перезагрузила страницу (index.html запрошен заново), игра запустилась")
    await p.ctx.close()

    cnt = {"pck": 0}

    async def hook500(r, path):
        if path.endswith(".pck"):
            cnt["pck"] += 1
            await r.fulfill(status=500, body="err")
            return True
        return False
    p = await new_page(b, "loader_pck500", hook=hook500)
    p.allow += ["500", "Failed loading", "Failed to load"]
    await p.pg.goto(URL + "?test=1&stall=3")
    t0 = time.time()
    s = None
    while time.time() - t0 < 90:
        try:
            s = await load_state(p)
        except Exception:
            s = None
        if s and s.get("reload"):
            break
        await p.pg.wait_for_timeout(500)
    check(bool(s and s.get("reload")) and s.get("tries") == 2,
          f"loader: пакет 500 — два автоповтора, потом «Игра не запустилась» и кнопка «Обновить» ({s}, запросов .pck {cnt['pck']})")
    await p.shot("2_pck500")
    await p.ctx.close()


def frames_of(st, key):
    return (st.get("frames", {}).get("sets", {}) or {}).get(key)


async def sc_netfail(b):
    """Сбои сети при подгрузке кадров: зависшие запросы (тайм-аут страницы), «200 + HTML» вместо WebP, сеть пропала
    и вернулась (петли догружаются при следующем входе в задание)."""
    async def hang6(r, path):
        if re.search(r"/frames/anim/barty_wave/0[0-5]\.webp", path):
            await asyncio.sleep(60)
            try:
                await r.abort()
            except Exception:
                pass
            return True
        return False
    p = await new_page(b, "net_hang", legacy=SKIP_SEED, hook=hang6)
    p.allow += ["Frames: кадры", "at: push_warning", "net::"]
    await p.boot()
    await to_hub(p)
    await p.press("Card_flat", wait=1200)
    await p.wait(lambda s: s.get("screen") == "job", "задание", 15)
    st = await p.wait(lambda s: (frames_of(s, "tt:chair_basic.png") or [0, 1])[0] == (frames_of(s, "tt:chair_basic.png") or [0, 1])[1],
                      "кадры коляски при 6 зависших запросах", 45)
    check(bool(st), f"net: 6 зависших запросов не мешают кадрам коляски ({frames_of(st, 'tt:chair_basic.png')}, "
                    f"тайм-аутов страницы {st.get('net', {}).get('timeouts')})")
    await p.ctx.close()

    async def garbage(r, path):
        if path.endswith("/frames/anim/barty_wave/03.webp"):
            await r.fulfill(status=200, content_type="image/webp", body="<html>not found</html>")
            return True
        return False
    p = await new_page(b, "net_garbage", legacy=SKIP_SEED, hook=garbage)
    p.allow += ["Frames: кадры", "at: push_warning"]
    await p.boot()
    await p.pg.wait_for_timeout(6000)
    await to_hub(p)
    await p.press("Card_flat", wait=1200)
    st = await p.wait(lambda s: (frames_of(s, "tt:chair_basic.png") or [0, 1])[0] == 36, "кадры коляски", 30)
    corrupt = [c for c in p.console if "ERR_FILE_CORRUPT" in c or "webp_load" in c]
    want_mode = "godot" if await p.pg.evaluate("!window.OffscreenCanvas") else "worker"   # WebKit: распаковывает игра
    check(st.get("net", {}).get("mode") == want_mode and not corrupt,
          f"net: «200 + HTML» вместо кадра — сбой одного файла, фоновая распаковка осталась "
          f"(mode={st.get('net', {}).get('mode')}, битых {st.get('net', {}).get('bad')}, ERR_FILE_CORRUPT в консоли: {len(corrupt)})")
    await p.ctx.close()

    p = await new_page(b, "net_offline", legacy=SKIP_SEED)
    p.allow += ["Frames: кадры", "at: push_warning", "net::", "Failed to load"]
    await p.boot()
    await to_hub(p)
    await p.pg.wait_for_timeout(2000)
    await p.ctx.set_offline(True)
    await p.press("Card_flat", wait=1200)
    await p.wait(lambda s: s.get("screen") == "job", "задание без сети", 15)
    await p.pg.wait_for_timeout(6000)
    st = await p.state()
    info(f"net offline: без сети {st.get('frames', {}).get('sets')}")
    await p.key("Escape", 300)
    await p.key("Escape", 800)
    await p.wait(lambda s: s.get("screen") == "hub", "в мастерскую", 10)
    await p.ctx.set_offline(False)
    await p.pg.wait_for_timeout(500)
    await p.press("Card_flat", wait=1200)
    keys = ("tt:chair_basic.png", "loop:ride_martin", "loop:magic_martin")

    def full(s):
        return all((frames_of(s, k) or [0, 1])[0] == (frames_of(s, k) or [0, 1])[1] for k in keys)
    st = await p.wait(full, "кадры и петли после возврата сети", 40, quiet=True)
    st = st or await p.state()
    check(full(st), f"net: сеть вернулась — при следующем входе в задание коляска и петли проезда/волшебства догрузились "
                    f"({[frames_of(st, k) for k in keys]})")
    await p.shot("back_online")
    await p.ctx.close()


FS_STAGES = ["title", "hub", "intro_1", "intro_5", "job_flat_diagnose", "job_flat_repair", "mini_pump", "mini_gap",
             "mini_ping", "mini_meter", "ride_martin", "result_lift", "hub_done", "garage", "garage_open", "ending",
             "credits", "feedback_general", "help", "settings_sound", "settings_game", "guild_open", "tech_ops",
             "tech_mini", "tech_result", "exam_ticket", "exam_passed", "seat_fit_troll", "seat_lessons"]


async def exitfs_rect(p):
    return await p.pg.evaluate("(()=>{const x=document.getElementById('wnb-exitfs'); if(!x) return null; const r="
                               "x.getBoundingClientRect(); return [getComputedStyle(x).display, r.left, r.top, r.width, "
                               "r.height, x.textContent]})()")


async def sc_fsexit(b):
    """Компьютер, полный экран (окно = экран, как F11): надпись «✖ Выйти из полного экрана (Esc)» видна 4 с после входа
    и пока указатель у верхнего края; в остальное время не закрывает ни одной кнопки игры ни на одном экране при
    1280×720, 1366×768, 1920×1080; после нажатия на неё клавиши снова у игры (фокус — холсту)."""
    for w, h in ((1280, 720), (1366, 768), (1920, 1080)):
        p = await new_page(b, f"fsexit_{w}", w=w, h=h, legacy=SKIP_SEED)
        if not CHROMIUM:                                  # «окно = экран» (F11): Firefox/WebKit без окна экран не подгоняют
            await p.ctx.add_init_script(f"window.__wnbS = {{width: {w}, height: {h}, availWidth: {w}, availHeight: {h}}};")
        await p.boot()
        r = await exitfs_rect(p)
        es = await p.pg.evaluate("window.wnbExitFs ? wnbExitFs.state() : null")
        # 4 с отсчитываются с загрузки страницы: Firefox без окна грузит игру ~5 с — к титулу надпись уже погасла
        check(bool(r) and (r[0] == "block" or (es or {}).get("until", 0) > 0),
              f"fsexit {w}×{h}: при входе в полный экран надпись видна ({r}; показ до {es})")
        await p.pg.mouse.move(w / 2, h / 2)
        await p.pg.wait_for_timeout(4500)
        hits, shown = [], []
        for s in FS_STAGES:
            await p.pg.evaluate("(n) => { window.wnbStaged = ''; window.wnbStage(n); }", s)
            for _ in range(60):
                if await p.pg.evaluate("window.wnbStaged || ''") == s:
                    break
                await p.pg.wait_for_timeout(250)
            await p.pg.wait_for_timeout(600)
            st = await p.state()
            r = await exitfs_rect(p)
            if r[0] != "none":
                shown.append(s)
                for bt in st.get("buttons", []):
                    x0, y0 = await p.at(bt[1], bt[2])
                    x1, y1 = await p.at(bt[1] + bt[3], bt[2] + bt[4])
                    if x0 < r[1] + r[3] and x1 > r[1] and y0 < r[2] + r[4] and y1 > r[2]:
                        hits.append((s, bt[0]))
            if s == "garage":
                await p.shot("garage")
        check(not hits and not shown, f"fsexit {w}×{h}: надпись не видна и не закрывает кнопок на {len(FS_STAGES)} экранах "
                                      f"(видна на {shown}, закрывает {hits})")
        await p.pg.mouse.move(w / 2, 2)
        await p.pg.wait_for_timeout(700)
        r = await exitfs_rect(p)
        check(r[0] == "block" and r[2] <= 1, f"fsexit {w}×{h}: указатель у верхнего края — надпись появилась сверху ({r})")
        if w == 1280:
            await p.shot("garage_reveal")
        await p.ctx.close()
    # фокус после нажатия
    p = await new_page(b, "fsexit_focus", legacy=SKIP_SEED)
    await p.boot()
    await to_hub(p)
    await p.pg.mouse.move(640, 2)
    await p.pg.wait_for_timeout(500)
    r = await exitfs_rect(p)
    await p.pg.mouse.click(r[1] + r[3] / 2, r[2] + r[4] / 2)
    await p.pg.wait_for_timeout(500)
    act = await p.pg.evaluate("document.activeElement.id || document.activeElement.tagName")
    k0 = (await p.state()).get("kb")
    await p.key("ArrowDown", 300)
    await p.key("ArrowDown", 300)
    k1 = (await p.state()).get("kb")
    check(act == "canvas" and k1 and k1 != k0, f"fsexit: после нажатия надписи фокус у холста ({act}), стрелки работают ({k0} → {k1})")
    await p.ctx.close()


async def sc_resparam(b):
    """?res= разбирается строго: мусор (1e3, 0.5, -5, 99) — по умолчанию (1080), 720 и 0 — как заданы."""
    for q, want in (("1e3", 1080), ("0.5", 1080), ("-5", 1080), ("99", 1080), ("720", 720), ("0", 0)):
        p = await new_page(b, "res_" + q.replace(".", "_"), legacy=SKIP_SEED)
        await p.boot("&res=" + q)
        cap = await p.pg.evaluate("window.wnbRes.cap")
        c = await p.canvas()
        check(cap == want and c[4] >= 640, f"res: ?res={q} → потолок {cap} (ждали {want}), холст {c[4]}×{c[5]}")
        await p.ctx.close()


# ---------------- хвосты аудита 20.11 (блок 3, 21.11) ----------------

async def sc_zoom(b):
    """Масштаб страницы браузера 50–300 % × dpr экрана 1 / 1,5 / 2 × ?res= (по умолчанию, 720, 0). Масштаб z в
    браузере = окно в CSS-пикселях / z и devicePixelRatio × z: окно 1280×720 физ. → CSS (1280/z)×(720/z), dpr d·z.
    Холст — на всё окно, буфер = CSS × эффективный dpr (потолок ?res=), картинка 16:9 целиком, нажатие «начать»
    попадает в кнопку (мастерская)."""
    for z in (0.5, 1.0, 1.5, 2.0, 3.0):
        for d in (1.0, 1.5, 2.0):
            for q in ("", "720", "0"):
                if z == 1.5 and q:                        # 1,5 — только по умолчанию
                    continue
                w, h = round(1280 / z), round(720 / z)
                dpr = d * z
                p = await new_page(b, f"zoom_{int(z * 100)}_{d}_{q or 'def'}", w=w, h=h, dpr=dpr, legacy=SKIP_SEED)
                p.allow.append("ERR_NO_BUFFER_SPACE")         # Windows: буфер сокетов локального сервера (как в screens)
                await p.boot("&res=" + q if q else "")
                c = await p.canvas()
                cap = {"": 1080, "720": 720, "0": 0}[q]
                gh = min(h, w * 9 / 16)
                eff = dpr if not cap or gh * dpr <= cap else max(1.0 if not q else 0.25, min(dpr, cap / gh))
                okbuf = abs(c[4] - round(w * eff)) <= 1 and abs(c[5] - round(h * eff)) <= 1
                full = abs(c[2] - w) < 2 and abs(c[3] - h) < 2
                await title_ready(p)
                await p.press("Start", wait=1200)
                st = await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 10, quiet=True)
                check(okbuf and full and bool(st),
                      f"{p.name}: масштаб {z * 100:.0f} %, dpr экрана {d}, res {q or 'по умолч.'}: CSS {c[2]:.0f}×{c[3]:.0f} "
                      f"(окно {w}×{h}), буфер {c[4]}×{c[5]} (ждали {round(w * eff)}×{round(h * eff)}, dpr {dpr:g} → "
                      f"{eff:.2f}), «начать» попало: {bool(st)}")
                if (z, d) in ((0.5, 1.0), (3.0, 2.0), (2.0, 1.5)) and not q:
                    await p.shot("hub")
                p.check_console()
                await p.ctx.close()


def assign_seed():
    """Сохранение game.py с активным незаконченным заданием (tests/saves/assign_active: caster, brake + seat_troll)."""
    return {"save.json": open(os.path.join(GODOT, "tests", "saves", "assign_active.save.json"), encoding="utf-8").read()}


async def sc_assign(b):
    """Ссылка-задание при уже активном другом задании (game.py start_assignment: другой id — заново, тот же — с места):
    1) без ссылки — при входе в мастерскую окно «продолжить задание или обычная игра» (отступление Godot, 12.11);
    2) при открытом окне в ту же вкладку — ссылка с другим заданием: новое задание, окна нет, в мастерской его пункты;
    3) пункт нового задания пройден; «Назад» браузера (адрес без ссылки) — то же задание, вопрос «продолжить» о нём;
    4) «Вперёд» (та же ссылка) — задание с места, пройденный пункт на месте."""
    p = await new_page(b, "assign", legacy_raw=assign_seed())
    await p.boot()
    await to_hub(p)
    st = await p.wait(lambda s: s.get("share_dlg") == "resume", "окно «продолжить задание»", 10)
    old = st.get("assign")
    check(st.get("share_dlg") == "resume" and bool(old), f"{p.name}: без ссылки — окно «продолжить задание» ({old})")
    await p.shot("1_resume")
    link = "&jobs=flat,spokes&from=" + urllib.parse.quote("Боб")
    await p.boot(link)
    st = await p.wait(lambda s: s.get("assign") and s.get("assign") != old, "новое задание из ссылки", 15)
    new = st.get("assign")
    await title_ready(p)
    await p.press("Start", wait=1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "мастерская задания", 10)
    await p.pg.wait_for_timeout(800)
    st = await p.state()
    names = [x[0] for x in st.get("buttons", [])]
    check(bool(new) and new != old and st.get("share_dlg") == "" and "Card_flat" in names and "Card_spokes" in names
          and "Card_caster" not in names,
          f"{p.name}: ссылка при открытом окне и другом активном задании — новое задание {new} (было {old}), окна нет, "
          f"пункты {[n for n in names if n.startswith('Card_')]}")
    st = await job_to_hub(p, "flat")
    check("flat" in st.get("assign_done", []), f"{p.name}: пункт flat задания пройден ({st.get('assign_done')})")
    await p.pg.wait_for_timeout(800)
    await p.pg.go_back()
    st = await p.wait(lambda s: s.get("screen") in ("title", "hub"), "«Назад» браузера", 60)
    if st.get("screen") == "title":
        await to_hub(p)
    st = await p.wait(lambda s: s.get("share_dlg") == "resume", "после «Назад» — окно «продолжить»", 10, quiet=True) \
        or await p.state()
    check(st.get("assign") == new and "flat" in st.get("assign_done", []),
          f"{p.name}: «Назад» (адрес без ссылки) — задание {st.get('assign')} с пройденным {st.get('assign_done')}, "
          f"окно «{st.get('share_dlg')}»")
    await p.pg.go_forward()
    st = await p.wait(lambda s: s.get("screen") in ("title", "hub"), "«Вперёд» браузера", 60)
    await p.pg.wait_for_timeout(800)
    st = await p.state()
    check(st.get("assign") == new and "flat" in st.get("assign_done", []) and st.get("share_dlg") != "resume",
          f"{p.name}: «Вперёд» (та же ссылка) — то же задание с места: {st.get('assign')}, пройдено {st.get('assign_done')}")
    p.check_console()
    await p.ctx.close()


PAD_JS = """
(() => {
  // геймпад для проверки: navigator.getGamepads и события gamepadconnected/disconnected — как у настоящего
  const pads = window.__pads = [null, null, null, null];
  navigator.getGamepads = () => pads.slice();
  const ev = (n, g) => { const e = new Event(n); Object.defineProperty(e, 'gamepad', { value: g }); window.dispatchEvent(e); };
  window.__padConnect = (i) => {
    const g = { id: 'Test pad (STANDARD GAMEPAD Vendor: 045e Product: 028e)', index: i, connected: true, mapping: 'standard',
      timestamp: performance.now(), axes: [0, 0, 0, 0], vibrationActuator: null,
      buttons: Array.from({ length: 17 }, () => ({ pressed: false, touched: false, value: 0 })) };
    pads[i] = g; ev('gamepadconnected', g);
  };
  window.__padBtn = (i, b, down) => { const g = pads[i]; if (!g) return;
    g.buttons[b] = { pressed: down, touched: down, value: down ? 1 : 0 }; g.timestamp = performance.now(); };
  window.__padDrop = (i) => { const g = pads[i]; if (!g) return; g.connected = false; pads[i] = null; ev('gamepaddisconnected', g); };
})();
"""


async def sc_pad(b):
    """Геймпад подключили после старта (подсказка, как game.py pad_action «added»), крестовина ходит по пунктам; держат
    «вниз» и выдёргивают геймпад — повтор стрелки останавливается (JOYDEVICEREMOVED → PAD["dir"] = None); игра живёт,
    клавиатура работает; подключили снова — снова работает."""
    p = await new_page(b, "pad", legacy=SKIP_SEED)
    await p.ctx.add_init_script(PAD_JS)
    await p.boot()
    await to_hub(p)
    await p.pg.wait_for_timeout(600)
    await p.pg.evaluate("__padConnect(0)")
    await p.pg.wait_for_timeout(700)
    st = await p.state()
    check("Геймпад подключён" in st.get("toast", ""), f"{p.name}: подключили после старта — подсказка «{st.get('toast')}»")
    await p.pg.evaluate("__padBtn(0, 13, true)")          # крестовина вниз — держим
    await p.pg.wait_for_timeout(120)
    await p.fresh((await p.state()).get("t", 0))         # состояние — после первого нажатия (раз в 0,25 с)
    k1 = (await p.state()).get("kb")
    await p.pg.wait_for_timeout(1500)
    k2 = (await p.state()).get("kb")
    check(bool(k1) and k2 != k1, f"{p.name}: крестовина вниз — пункт {k1}, держим — повтор ({k2})")
    await p.pg.evaluate("__padDrop(0)")                   # выдернули, не отпустив
    await p.pg.wait_for_timeout(500)
    seq = []
    for _ in range(8):
        seq.append((await p.state()).get("kb"))
        await p.pg.wait_for_timeout(300)
    check(len(set(seq)) == 1, f"{p.name}: геймпад отключили с зажатой крестовиной — повтор остановился ({seq})")
    await p.key("ArrowDown", 300)
    k3 = (await p.state()).get("kb")
    check(k3 != seq[-1], f"{p.name}: после отключения клавиатура работает ({seq[-1]} → {k3})")
    await p.pg.evaluate("__padConnect(0)")
    await p.pg.wait_for_timeout(500)
    await p.pg.evaluate("__padBtn(0, 13, true)")
    await p.pg.wait_for_timeout(200)
    await p.pg.evaluate("__padBtn(0, 13, false)")
    await p.pg.wait_for_timeout(400)
    k4 = (await p.state()).get("kb")
    check(k4 != k3, f"{p.name}: подключили снова — крестовина работает ({k3} → {k4})")
    st = await p.state()
    check(st.get("screen") == "hub", f"{p.name}: игра живёт ({st.get('screen')})")
    p.check_console()
    await p.ctx.close()


HIDE_JS = """(h) => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => h });
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => h ? 'hidden' : 'visible' });
    document.dispatchEvent(new Event('visibilitychange')); }"""


async def background(p, secs):
    """Вкладка в фоне secs секунд: страница скрыта (visibilitychange) и заморожена (CDP Page.setWebLifecycleState —
    как Chrome замораживает фоновые вкладки: ни таймеров, ни кадров), потом снова видна."""
    await p.pg.evaluate(HIDE_JS, True)
    cdp = await p.ctx.new_cdp_session(p.pg)
    await cdp.send("Page.setWebLifecycleState", {"state": "frozen"})
    await asyncio.sleep(secs)
    await cdp.send("Page.setWebLifecycleState", {"state": "active"})
    await cdp.detach()
    await p.pg.evaluate(HIDE_JS, False)


async def sc_bg(b):
    """Вкладка в фоне посреди мини-игры (насос) и посреди проезда (WNB_BG_SECS, по умолчанию 70 с): после возврата —
    та же мини-игра с тем же давлением и кнопки работают; проезд доезжает до конца, итог открывается; музыка на паузе,
    пока вкладка скрыта, и снова играет; ошибок в консоли нет. Только Chromium (CDP)."""
    if not CHROMIUM:
        return skip_cdp("bg")
    secs = float(os.environ.get("WNB_BG_SECS", "70"))
    p = await new_page(b, "bg", legacy=SKIP_SEED)
    await p.boot()
    await to_hub(p)
    await p.press("Card_flat", wait=1200)
    await p.wait(lambda s: s.get("screen") == "job", "задание", 15)
    st = await follow_hints(p, lambda s: bool(s.get("mini")), 180)
    v0 = (st.get("mini") or {}).get("value")
    await p.press("Pump", wait=600)
    st = await p.state()
    v1 = (st.get("mini") or {}).get("value")
    mus0 = await p.pg.evaluate("wnbMusic.state()")
    await p.pg.evaluate(HIDE_JS, True)
    await p.pg.wait_for_timeout(300)
    mus_h = await p.pg.evaluate("wnbMusic.state()")
    await p.pg.evaluate(HIDE_JS, False)
    t0 = time.time()
    await background(p, secs)
    await p.pg.wait_for_timeout(1500)
    st = await p.state()
    m = st.get("mini") or {}
    mus1 = await p.pg.evaluate("wnbMusic.state()")
    info(f"{p.name}: фон {time.time() - t0:.0f} с посреди насоса: худший кадр после возврата {st.get('worst_ms')} мс, "
         f"музыка {mus0.split(' ')[0]} → скрыта {mus_h.split(' ')[0]} → {mus1.split(' ')[0]}")
    check(m.get("kind") == "pump" and m.get("value") == v1,
          f"{p.name}: после фона — та же мини-игра, давление {v1} → {m.get('value')} (до нажатия {v0})")
    check(mus_h.startswith("paused") and mus1.startswith("playing"),
          f"{p.name}: музыка в фоне на паузе и снова играет ({mus_h[:7]} → {mus1[:7]})")
    await p.shot("1_after_bg_pump")
    st = await follow_hints(p, lambda s: s.get("phase") == "test", 180)
    await p.press("TestDrive")
    await p.wait(lambda s: (s.get("ride") or {}).get("riding"), "проезд", 10)
    await p.pg.wait_for_timeout(700)
    await background(p, secs)
    st = await p.wait(lambda s: s.get("ride_done"), "проезд закончился после фона", 20)
    check(bool(st.get("ride_done")), f"{p.name}: проезд после фона доехал ({(st.get('ride') or {})})")
    await p.press("TestDrive", wait=50)
    st = await p.wait(lambda s: s.get("screen") == "result", "итог после фона", 15)
    check(st.get("screen") == "result", f"{p.name}: итог задания открылся")
    await p.shot("2_after_bg_ride")
    p.check_console()
    await p.ctx.close()


# ---------------- телефонные пропорции при крупном тексте (блок 2, 21.11) ----------------

def shot_stages():
    """Все состояния снимков tests/shots.gd (ALL), кроме «одной кнопки» (scan_*: рамка скана — свой режим)."""
    src = open(os.path.join(GODOT, "tests", "shots.gd"), encoding="utf-8").read()
    body = src[src.index("const ALL := [") + 14:]
    body = body[:body.index("]")]
    return [x for x in re.findall(r'"([^"]+)"', body) if not x.startswith("scan_")]


async def set_stage(p, name, timeout=40):
    await p.pg.evaluate("(n) => { window.wnbStaged = ''; window.wnbStage(n); }", name)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if await p.pg.evaluate("window.wnbStaged || ''") == name:
            return True
        await p.pg.wait_for_timeout(150)
    return False


async def sc_phonetext(b):
    """Телефон 740×360 и 780×360 (dpr 3, холст 2220×1080 / 2340×1080, поля по бокам) и компьютер 1280×720 dpr 1,5
    (картинка тех же 1920×1080): все состояния tests/shots.gd на русском и английском при тексте 100/125/150 % и с
    «лёгким» шрифтом. Картинка игры — вырезка 1920×1080 из снимка страницы → tests/web_shots/phonetext/; сверка
    телефон ↔ компьютер по каждому состоянию (средняя разница и доля пикселей с разницей > 48) — в phonetext.json.
    WNB_PT_COMBOS=ru150,en150f… — часть сочетаний; WNB_PT_STAGES=hub,… — часть состояний."""
    from PIL import Image, ImageChops
    out = os.path.join(SHOTS, "phonetext")
    os.makedirs(out, exist_ok=True)
    combos = [("ru", t, 0) for t in (0, 2, 3)] + [("en", t, 0) for t in (0, 2, 3)] + [("en", t, 1) for t in (0, 2, 3)]
    want = [x for x in os.environ.get("WNB_PT_COMBOS", "").split(",") if x]
    only = [x for x in os.environ.get("WNB_PT_STAGES", "").split(",") if x]
    skip = [x for x in os.environ.get("WNB_PT_SKIP", "").split(",") if x]
    stages = [s for s in shot_stages() if (not only or s in only) and s not in skip]
    views = [("p740", dict(touch=True, mobile=True, w=740, h=360, dpr=3)),
             ("p780", dict(touch=True, mobile=True, w=780, h=360, dpr=3)),
             ("desk", dict(w=1280, h=720, dpr=1.5))]
    vsel = [x for x in os.environ.get("WNB_PT_VIEWS", "").split(",") if x]       # p740,p780,desk — часть окон
    views = [v for v in views if not vsel or v[0] in vsel]
    res = {}
    for lang, text, font in combos:
        tag = f"{lang}{[100, 112, 125, 150][text]}{'f' if font else ''}"
        if want and tag not in want:
            continue
        st_list = [s for s in stages if not s.startswith("title")] + (["title_en"] if lang == "en" else ["title"])
        for vname, kw in views:
            p = await new_page(b, f"pt_{tag}_{vname}", legacy=SKIP_SEED, **kw)
            p.allow.append("ERR_NO_BUFFER_SPACE")
            if kw.get("mobile"):
                await orient(p, kw["w"], kw["h"], True, kw["dpr"])
            await p.boot()
            await title_ready(p)
            for s in (f"set:lang={lang}", f"set:text={text}", f"set:font={font}"):
                await set_stage(p, s)
            for s in st_list:
                if not await set_stage(p, s):
                    check(False, f"{p.name}: состояние {s} не встало")
                    continue
                await p.wait(lambda q: q["frames"]["queue"] == 0 and q["frames"]["inflight"] == 0, "кадры", 6, quiet=True)
                await p.pg.wait_for_timeout(500)
                g, c, _ = await game_rect(p)
                path = os.path.join(out, f"{tag}_{vname}_{s}.png")
                try:
                    await p.pg.screenshot(path=path, timeout=20000)
                except Exception as e:
                    info(f"{p.name}: снимок {s} не снят ({type(e).__name__})")
                    continue
                k = kw["dpr"]
                im = Image.open(path)
                box = [round(v * k) for v in (g[0], g[1], g[0] + g[2], g[1] + g[3])]
                im.crop(box).resize((1920, 1080)).save(path)
                res.setdefault(tag, {}).setdefault(s, {})[vname] = box
            p.check_console()
            await p.ctx.close()
        # сверка: телефон ↔ компьютер
        for s in st_list:
            try:
                d = Image.open(os.path.join(out, f"{tag}_desk_{s}.png")).convert("RGB")
            except Exception:
                continue
            for vname in ("p740", "p780"):
                try:
                    m = Image.open(os.path.join(out, f"{tag}_{vname}_{s}.png")).convert("RGB")
                except Exception:
                    continue
                df = ImageChops.difference(d, m).convert("L")
                hist = df.histogram()
                mean = sum(i * n for i, n in enumerate(hist)) / (1920 * 1080)
                big = sum(hist[49:]) / (1920 * 1080)
                res[tag][s][vname + "_diff"] = [round(mean, 2), round(big, 4)]
    with open(os.path.join(SHOTS, "phonetext.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    worst = sorted(((v.get(f"{vn}_diff", [0, 0])[1], t, s, vn) for t, d in res.items() for s, v in d.items()
                    for vn in ("p740", "p780")), reverse=True)[:25]
    for w in worst:
        info(f"phonetext: {w[1]} {w[3]} {w[2]}: пикселей с разницей > 48 от компьютера — {w[0] * 100:.2f} %")
    check(bool(res), f"phonetext: снято {sum(len(d) for d in res.values())} состояний × 3 окна")


PB_STAGES = ["hub", "job_flat_diagnose", "job_flat_repair", "mini_pump", "result_lift", "settings_sound", "settings_access",
             "seat_lesson_slump", "seat_fit_troll", "seat_quiz_q1", "guild_open", "tech_ops", "garage", "share_paste", "title"]
PB_BIG = ["hub", "job_flat_diagnose", "job_flat_repair", "settings_access", "tech_ops"]


async def sc_phonebig(b):
    """Телефонный режим (UI.phone(), 21.11) — снимки для владельца: телефон 780×360 dpr 3 (снимок страницы 2340×1080,
    как экран телефона), EN и RU, каждое состояние — до (?phone=0, раскладка как была) и после (?phone=1) →
    tests/web_shots/phonebig/<язык>_<состояние>_before|after.png; плюс RU при тексте 150 % — <ru150>_<состояние>_after.png.
    WNB_PB_STAGES=hub,… — часть состояний; WNB_PB_RUNS=en:1:2,… — свои проходы (язык:телефон:текст 0..3)."""
    out = os.path.join(SHOTS, "phonebig")
    os.makedirs(out, exist_ok=True)
    only = [x for x in os.environ.get("WNB_PB_STAGES", "").split(",") if x]
    runs = [(lang, ph, 0) for lang in ("en", "ru") for ph in (0, 1)] + [("ru", 1, 3)]
    if os.environ.get("WNB_PB_RUNS"):          # «en:1:2,ru:1:3» — язык:телефон:размер текста (0..3), только эти проходы
        runs = [(r.split(":")[0], int(r.split(":")[1]), int(r.split(":")[2])) for r in os.environ["WNB_PB_RUNS"].split(",")]
    n = 0
    for lang, ph, text in runs:
        p = await new_page(b, f"pb_{lang}{ph}t{text}", legacy=SKIP_SEED, touch=True, mobile=True, w=780, h=360, dpr=3)
        p.allow.append("ERR_NO_BUFFER_SPACE")
        await orient(p, 780, 360, True, 3)
        await p.boot(f"&phone={ph}")
        await title_ready(p)
        for x in (f"set:lang={lang}", f"set:text={text}"):
            await set_stage(p, x)
        st = await p.state()
        check(st.get("phone") is bool(ph), f"{p.name}: ?phone={ph} — телефонный режим {st.get('phone')}")
        for s in [x for x in (PB_STAGES if text == 0 else PB_BIG) if not only or x in only]:
            s2 = "title_en" if s == "title" and lang == "en" else s
            if not await set_stage(p, s2):
                check(False, f"{p.name}: состояние {s2} не встало")
                continue
            await p.wait(lambda q: q["frames"]["queue"] == 0 and q["frames"]["inflight"] == 0, "кадры", 6, quiet=True)
            await p.pg.wait_for_timeout(600)
            name = (f"{lang}_{s}_{'after' if ph else 'before'}.png" if text == 0 else
                    f"{lang}{[100, 112, 125, 150][text]}_{s}_{'after' if ph else 'before'}.png")
            try:
                await p.pg.screenshot(path=os.path.join(out, name), timeout=20000)
                n += 1
            except Exception as e:
                info(f"{p.name}: снимок {s} не снят ({type(e).__name__})")
        p.check_console()
        await p.ctx.close()
    check(n > 0, f"phonebig: снимков {n} → tests/web_shots/phonebig/")


SCENARIOS = {"boot": sc_boot, "play": sc_play, "links": sc_links, "migrate": sc_migrate, "net404": sc_net404,
             "guild": sc_guild, "phone": sc_phone, "stale": sc_stale, "a11y": sc_a11y, "fps": sc_fpshud, "plates": sc_plates, "feedback": sc_feedback, "perf": sc_perf,
             "prof": sc_prof, "screens": sc_screens, "tabs": sc_tabs, "store": sc_store, "loader": sc_loader,
             "netfail": sc_netfail, "fsexit": sc_fsexit, "res": sc_resparam, "zoom": sc_zoom, "assign": sc_assign,
             "pad": sc_pad, "bg": sc_bg, "phonetext": sc_phonetext, "phonebig": sc_phonebig}
TIMEOUT = {"screens": 5400, "phonetext": 7200,            # все экраны × 4 прохода — долго
           "bg": 2 * float(os.environ.get("WNB_BG_SECS", "70")) + 480}   # два раза «в фоне» + задание


async def main(only):
    os.makedirs(SHOTS, exist_ok=True)
    open(os.path.join(SHOTS, ".gdignore"), "w").close()     # снимки внутри проекта — редактору не импортировать
    for f in os.listdir(SHOTS):
        if f != ".gdignore" and os.path.isfile(os.path.join(SHOTS, f)) and (not only or any(f.startswith(n) for n in only)):
            os.remove(os.path.join(SHOTS, f))
    async with async_playwright() as pw:
        # Playwright сам добавляет --autoplay-policy=no-user-gesture-required — убираем (страницу он всё равно помечает
        # «нажатой», так что запрет автозапуска звука в этой проверке не виден)
        if BROWSER == "firefox":                           # звук — в ноль настройкой профиля (+ MUTE_JS в странице)
            b = await pw.firefox.launch(firefox_user_prefs={"media.volume_scale": "0.0",
                                                            "media.autoplay.default": 1})
        elif BROWSER == "webkit":
            b = await pw.webkit.launch()
        else:
            b = await pw.chromium.launch(args=GPU_ARGS, ignore_default_args=["--autoplay-policy=no-user-gesture-required"])
        print(f"Браузер: {BROWSER} {b.version}", flush=True)
        try:
            for name, fn in SCENARIOS.items():
                if only and name not in only:
                    continue
                print(f"— {name}", flush=True)
                try:
                    await asyncio.wait_for(fn(b), TIMEOUT.get(name, 600))
                except Exception as e:
                    check(False, f"{name}: {e!r}"[:400])
        finally:
            await b.close()


if __name__ == "__main__":
    only = []
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")
    if "--no-build" not in sys.argv and "WNB_URL" not in os.environ:
        build_web.build()
    srv = None
    if "WNB_URL" not in os.environ:
        srv, _ = build_web.make_server(build_web.OUT, PORT)
    try:
        asyncio.run(main(only))
    finally:
        if srv:
            srv.shutdown()
            srv.server_close()
    if metrics.get("perf"):
        print("\nЗамер (Chromium без окна, видеокарта; замедление процессора через CDP), кадры/с (худший кадр, мс):")
        print("  режим                 титул,с  титул  мастерская  диагноз  крутим      ремонт      проезд"
              "     поворот,с  декод мс")
        for r in metrics["perf"]:
            print(f"  {r['label']:<20} {r['t_title']:>7.1f}  {r['title']:>5.0f}  {r['hub']:>10.0f}  {r['job']:>7.0f}  "
                  f"{r['drag']:>4.0f} ({r['w_drag']:>3.0f})  {r['repair']:>4.0f} ({r['w_repair']:>3.0f})  "
                  f"{r['ride']:>4.0f} ({r['w_ride']:>3.0f})  {r['t_tt']:>9.1f}  {r['dec']}")
    if metrics.get("screens"):
        sc = metrics["screens"]
        cols = [m for m in ("x1", "x6", "phone") if m in sc]
        print("\nЭкраны (Chromium, видеокарта, CDP-замедление), кадры/с (худший кадр, мс):")
        print("  экран                " + "".join(f"{c:>14}" for c in cols))
        for k in [k for k, *_ in SCREENS if any(k in sc[c] for c in cols)]:
            print(f"  {k:<21}" + "".join(f"{sc[c][k][0]:>8.0f} ({sc[c][k][1]:>3.0f})" if k in sc[c] else f"{'—':>14}"
                                         for c in cols))
    tail = f" ({BROWSER}; пропущено, только Chromium: {', '.join(skipped)})" if skipped else f" ({BROWSER})"
    print(f"\nWEB SMOKE: {len(notes)} ok, {len(fails)} FAIL{tail}. Скриншоты: {os.path.relpath(SHOTS, os.path.dirname(GODOT))}/ — открой и посмотри.")
    for f in fails:
        print("  ", f)
    sys.exit(1 if fails else 0)
