"""Зависание браузерной версии на ПЕРВОМ запуске (чистый профиль): титул -> «Начать» -> следим, отвечает ли страница.
python art_tests/web_freeze_probe.py [url] [--headed] [--slow=4] [--noaudio] [settings='{"volume":{"music":0}}']
Каждую секунду: window.wnbState (сцена) с таймаутом 5 с — не ответила = страница зависла; в лог — fps игры."""
import asyncio, json, sys, time
from playwright.async_api import async_playwright

URL = next((a for a in sys.argv[1:] if a.startswith("http")), "https://fordragon88.github.io/wheels-and-bones-web/")
HEADED = "--headed" in sys.argv


async def main():
    async with async_playwright() as pw:
        br = await pw.chromium.launch(headless=not HEADED, args=["--autoplay-policy=no-user-gesture-required"])
        ctx = await br.new_context(viewport={"width": 1600, "height": 900})
        pg = await ctx.new_page()
        sets = next((x.split('=', 1)[1] for x in sys.argv[1:] if x.startswith('settings=')), None)
        if sets:                                             # настройки «до запуска» — как будто игрок их поменял
            await ctx.add_init_script(f"localStorage.setItem('wnb:settings.json', {json.dumps(sets)})")
            print('настройки:', sets, flush=True)
        slow = next((float(x.split('=', 1)[1]) for x in sys.argv[1:] if x.startswith('--slow=')), 0)
        if slow:                                             # слабый ПК: процессор медленнее в N раз
            cdp = await ctx.new_cdp_session(pg)
            await cdp.send('Emulation.setCPUThrottlingRate', {'rate': slow})
            print('процессор медленнее в', slow, 'раз', flush=True)
        if '--noaudio' in sys.argv:                         # звук браузера не запустился (как до первого «настоящего» клика)
            await ctx.add_init_script('''(() => { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
              AC.prototype.resume = function () { return Promise.resolve(); };
              const Wrap = function (...a) { const c = new AC(...a); try { c.suspend(); } catch (e) {} return c; };
              Wrap.prototype = AC.prototype; window.AudioContext = Wrap; window.webkitAudioContext = Wrap; })();''')
            print('звук браузера остановлен', flush=True)
        logs = []
        pg.on("console", lambda m: logs.append((round(time.time() - t0, 1), m.text[:140])))
        await pg.route("**/script.google.com/**", lambda r: r.abort())
        t0 = time.time()
        await pg.goto(URL)
        await pg.wait_for_timeout(6000)
        await pg.mouse.click(800, 450)                       # pygbag ждёт первое действие

        async def state():
            try:
                s = await asyncio.wait_for(pg.evaluate("window.wnbState || ''"), 5)
                return json.loads(s) if s else {}
            except Exception as e:
                return {"FROZEN": type(e).__name__}

        async def logical(x, y):
            r = await pg.evaluate("(()=>{const c=document.getElementById('canvas');const r=c.getBoundingClientRect();"
                                  "return [r.left,r.top,r.width,r.height]})()")
            return r[0] + x * r[2] / 1280, r[1] + y * r[3] / 720

        for _ in range(120):                                 # до титула (первое касание уводит во вступление)
            st = await state()
            if st.get("scene") in ("title", "intro"):
                break
            await pg.wait_for_timeout(500)
        print(f"{time.time() - t0:5.1f}s старт: {st.get('scene')}", flush=True)
        hang = 0                                             # сразу после первого клика (титул -> вступление)
        for _ in range(12):
            await pg.wait_for_timeout(1000)
            st2 = await state()
            if 'FROZEN' in st2:
                hang += 1
                print(f"{time.time() - t0:5.1f}s  ЗАВИС после первого клика", flush=True)
                if hang >= 3:
                    print('итог: ЗАВИСАЕТ (после первого клика)', flush=True)
                    await br.close()
                    return
        if st.get("scene") == "intro":
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(1500)
        await pg.mouse.click(*(await logical(640, 470)))      # «НАЧАТЬ»
        frozen = 0
        for i in range(60):
            t1 = time.time()
            st = await state()
            dt = time.time() - t1
            fr = "FROZEN" in st
            frozen += fr
            print(f"{time.time() - t0:5.1f}s  ответ {dt:4.1f}s  {'ЗАВИС' if fr else st.get('scene')}  "
                  f"{[l for _, l in logs if 'fps' in l][-1:] }", flush=True)
            if frozen >= 3:
                break
            await pg.wait_for_timeout(1000)
        print("итог:", "ЗАВИСАЕТ" if frozen else "не зависает")
        for t, l in logs[-25:]:
            print("   log", t, l)
        await br.close()


asyncio.run(main())
