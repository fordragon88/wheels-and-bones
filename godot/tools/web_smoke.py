# -*- coding: utf-8 -*-
"""Проверка браузерной Godot-версии в настоящем браузере (Playwright, Chromium) — по образцу art_tests/web_smoke.py.

  python godot/tools/web_smoke.py              — собрать (build_web.py), проверить, всё закрыть
  python godot/tools/web_smoke.py --no-build   — проверить готовую godot/build/web/
  python godot/tools/web_smoke.py --only boot,play   — только эти сценарии
  WNB_URL=https://…/godot/ python godot/tools/web_smoke.py --no-build --only boot,play,perf  — выложенный сайт

Локальный сервер — на своём порту (WNB_PORT, по умолчанию 8061; не 8000/8188/8797), закрывается в конце.
Браузер — Chromium без окна, с --mute-audio (у владельца в наушниках НИЧЕГО не звучит; голос браузера speechSynthesis
подменён заглушкой — на Windows он шёл бы мимо --mute-audio, через SAPI) и с видеокартой (ANGLE D3D11), чтобы кадры/с
были похожи на настоящие. Игра открывается с ?test=1: раз в 0,25 с кладёт состояние в window.wnbState (autoload/web.gd):
экран, фаза, кадры/с, кадры (скачано/в очереди/ошибки), видимые кнопки с прямоугольниками и подсказку «что нажать».
Тест жмёт кнопки НАСТОЯЩИМИ кликами/касаниями по их прямоугольникам. В сеть наружу ничего не уходит (всё, что не
127.0.0.1, обрывается). Скриншоты — godot/tests/web_shots/ (не в git), их надо открыть и посмотреть.
Код выхода 1 — что-то не так."""
import asyncio
import json
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
SHOTS = os.path.join(GODOT, "tests", "web_shots")
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
                   block_frames=False, legacy_raw=None):
    opts = dict(viewport={"width": w, "height": h}, device_scale_factor=dpr, reduced_motion=motion)
    if mobile:
        opts.update(is_mobile=True, has_touch=True)
    ctx = await b.new_context(**opts)
    u = urllib.parse.urlsplit(URL)
    await ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=f"{u.scheme}://{u.netloc}")
    await ctx.add_init_script(INIT_JS)
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


async def play_job(p, jid, expect_loop, shots=True):
    """Задание jid до итога по подсказкам: осмотр, диагноз, шаги инструментами, мини-игры, проезд, итог."""
    st = await p.wait(lambda s: s.get("screen") == "job" and s.get("job") == jid, f"открыто задание {jid}", 30)
    if not st:
        return {}
    if shots:
        await p.pg.wait_for_timeout(2500)
        await p.shot(f"{jid}_1_diagnose")
    seen_magic = {"ready": False, "playing": False}

    async def watch(s):
        m = s.get("magic") or {}
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
    check(net.get("mode") == "worker" and net.get("worker_decoded", 0) >= 72,
          f"{p.name}: кадры распаковывает фоновый поток страницы ({net.get('mode')}, {net.get('worker_decoded')} кадров, "
          f"{net.get('worker_ms')} мс/кадр в потоке; в игровом кадре — {st.get('frames', {}).get('decode_ms')} мс)")
    # пиксели фоновой распаковки = распаковка WebP как есть (PIL): цвет под прозрачными пикселями не потерян
    import base64
    import io
    from PIL import Image
    for rel in ("turntable/chair_aeroz_00.webp", "anim/barty_wave/00.webp"):
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
    await p.press("Start", wait=800)
    st = await p.wait(lambda s: s.get("screen") == "intro", "вступление", 10)
    mus = await p.pg.evaluate("wnbMusic.state()")
    check(mus.startswith("playing"), f"{p.name}: после первого нажатия музыка играет ({mus})")
    await p.shot("1_intro")
    st = await follow_hints(p, lambda s: s.get("screen") == "job", 60)
    st = await play_job(p, "flat", "ride_martin")
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
    clip = await p.pg.evaluate("navigator.clipboard.readText().catch(e => 'ERR ' + e)")
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
    check(st.get("lang") == "ru", f"{p.name}: настройки перенесены (язык {st.get('lang')})")
    old = await p.pg.evaluate("localStorage.getItem('wnb:save.json')")
    check(old and json.loads(old) == LEGACY_SAVE, f"{p.name}: старое сохранение pygame не тронуто")
    await p.press("Start", wait=1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "мастерская", 10)
    await p.shot("1_hub")
    await p.pg.reload()
    st = await p.wait(lambda s: s.get("screen") == "title", "титул после перезагрузки", 60)
    check(st.get("migrated") is False and sorted(st.get("done", [])) == sorted(LEGACY_SAVE["done"]),
          f"{p.name}: второй запуск — своё сохранение, без повторного переноса")
    p.check_console()
    await p.ctx.close()
    await migrate_real(b)


async def migrate_real(b):
    """Настоящие сохранения pygame-версии (их пишет сама game.py: tools/save_fixtures.py → tests/saves/) переносятся
    поле в поле так, как их читает game.py (tests/saves/expected.json); битые — игра стартует, старое не тронуто.
    Отличия браузера в эталоне: размер текста по умолчанию 125 % (text 2), «Без анимации» без выбора игрока — как в
    системе (здесь prefers-reduced-motion: no-preference → выкл). Язык — тот, что выбрал игрок (game.py в браузере
    всегда стартует по-английски — см. PORT_PLAN «Перенос сохранений»)."""
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
    st, secs, times = await p.boot()
    await p.pg.wait_for_timeout(1500)
    await p.shot("1_title")
    c = await p.canvas()
    check(abs(c[2] - 740) < 2 and abs(c[3] - 360) < 2 and c[4] >= 2000,
          f"{p.name}: холст {c[2]:.0f}×{c[3]:.0f} CSS = окно, {c[4]}×{c[5]} px (dpr {c[6]})")
    await p.press("Start", wait=1200)
    st = await p.wait(lambda s: s.get("screen") == "hub", "касание «начать» → мастерская", 10)
    await p.shot("2_hub")
    await p.press("Card_flat", wait=1500)
    st = await p.wait(lambda s: s.get("screen") == "job", "касание карточки → задание", 10)
    await p.pg.wait_for_timeout(3000)
    await p.shot("3_job")
    # касание пункта списка деталей — осмотр
    await p.press((st.get("hint") or ["?"])[0], wait=600)
    st = await p.state()
    check(st.get("phase") == "diagnose", f"{p.name}: касание детали в задании ({st.get('hint')})")
    await p.key("Escape", 600)
    await p.key("Escape", 600)
    st = await p.wait(lambda s: s.get("screen") == "hub", "Esc → мастерская", 10)
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
    p.check_console()
    await p.ctx.close()
    await sc_rotate(b)                                    # книжная ориентация: заслонка, планшет, ?res=


async def orient(p, w, h, landscape, dpr=3):
    """Повернуть «телефон»: размер окна и экрана (screen.width/height) и screen.orientation — через CDP."""
    fs = await p.pg.evaluate("!!document.fullscreenElement && (document.exitFullscreen(), true)")
    if fs:                                               # первое касание включило полный экран — окно не ресайзится
        await p.pg.wait_for_timeout(500)
    await p.pg.set_viewport_size({"width": w, "height": h})   # и Playwright помнит размер (снимок его восстановит)
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
    check(bool(r["full"]) and r["full"][0] != "none", f"{p.name}: кнопка полного экрана у левого края ({r['full']})")
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
        await check_fit(p, 1280, 720, "полный экран на компьютере")
        await p.press("Fullscreen", wait=800)
    p.check_console()
    await p.ctx.close()
    await calm_priority(b)


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
    WNB_SCREENS=ключ,ключ — только эти; WNB_SCREENS_MODES=x1,x6,phone,prof — только эти проходы.
    Итог — godot/tests/web_shots/screens_perf.json и таблица в конце вывода."""
    only = [x for x in os.environ.get("WNB_SCREENS", "").split(",") if x]
    modes = [x for x in os.environ.get("WNB_SCREENS_MODES", "x1,x6,phone,prof").split(",") if x]
    runs = {"x1": ("desktop x1", 1, False, ""), "x6": ("desktop x6", 6, False, ""), "phone": ("phone x6", 6, True, ""),
            "prof": ("prof phone x6", 6, True, "&prof=1")}
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
    link = await p.pg.evaluate("navigator.clipboard.readText().catch(e => 'ERR ' + e)")
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
    Playwright вставляет не-латиницу через insertText без нажатий — холст Godot их не видит."""
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


SCENARIOS = {"boot": sc_boot, "play": sc_play, "links": sc_links, "migrate": sc_migrate, "net404": sc_net404,
             "guild": sc_guild, "phone": sc_phone, "stale": sc_stale, "a11y": sc_a11y, "fps": sc_fpshud, "plates": sc_plates, "feedback": sc_feedback, "perf": sc_perf,
             "prof": sc_prof, "screens": sc_screens}
TIMEOUT = {"screens": 5400}                               # все экраны × 4 прохода — долго


async def main(only):
    os.makedirs(SHOTS, exist_ok=True)
    open(os.path.join(SHOTS, ".gdignore"), "w").close()     # снимки внутри проекта — редактору не импортировать
    for f in os.listdir(SHOTS):
        if f != ".gdignore" and (not only or any(f.startswith(n) for n in only)):
            os.remove(os.path.join(SHOTS, f))
    async with async_playwright() as pw:
        # Playwright сам добавляет --autoplay-policy=no-user-gesture-required — убираем (страницу он всё равно помечает
        # «нажатой», так что запрет автозапуска звука в этой проверке не виден)
        b = await pw.chromium.launch(args=GPU_ARGS, ignore_default_args=["--autoplay-policy=no-user-gesture-required"])
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
    print(f"\nWEB SMOKE: {len(notes)} ok, {len(fails)} FAIL. Скриншоты: godot/tests/web_shots/ — открой и посмотри.")
    for f in fails:
        print("  ", f)
    sys.exit(1 if fails else 0)
