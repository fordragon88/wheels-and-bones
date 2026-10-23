"""Зависание на странице сайта GOAT (игра — во фрейме): python art_tests/web_freeze_probe_wp.py [--headed] [--runs=N]
Чистый профиль, страница openassistivetech.org/wheels-and-bones -> клик по игре -> «Начать»; каждую секунду —
отвечают ли игра во фрейме (wnbState) и сама страница (таймаут 5 с)."""
import asyncio, json, sys, time
from playwright.async_api import async_playwright

URL = "https://www.openassistivetech.org/wheels-and-bones/"
HEADED = "--headed" in sys.argv
RUNS = int(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--runs=")), 1))


async def one(pw, n):
    br = await pw.chromium.launch(headless=not HEADED, args=["--autoplay-policy=no-user-gesture-required"])
    ctx = await br.new_context(viewport={"width": 1600, "height": 1000})
    pg = await ctx.new_page()
    await pg.route("**/script.google.com/**", lambda r: r.abort())
    t0 = time.time()
    await pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
    ifr = pg.locator("#wnb-frame")
    await ifr.scroll_into_view_if_needed()
    await pg.wait_for_timeout(2000)
    fr = next(f for f in pg.frames if "github.io" in f.url)

    async def ev(target, js):
        try:
            return await asyncio.wait_for(target.evaluate(js), 5)
        except Exception as e:
            return "FROZEN"

    async def game_pt(x, y):
        b = await ifr.bounding_box()
        r = await ev(fr, "(()=>{const c=document.getElementById('canvas');if(!c)return null;const r=c.getBoundingClientRect();"
                         "return [r.left,r.top,r.width,r.height]})()")
        if not r or r == "FROZEN":
            return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        return b["x"] + r[0] + x * r[2] / 1280, b["y"] + r[1] + y * r[3] / 720

    await pg.wait_for_timeout(8000)
    await pg.mouse.click(*(await game_pt(640, 360)))           # pygbag ждёт первое действие
    scene = None
    for _ in range(120):
        s = await ev(fr, "window.wnbState || ''")
        scene = json.loads(s).get("scene") if s and s != "FROZEN" else s
        if scene in ("title", "intro", "FROZEN"):
            break
        await pg.wait_for_timeout(500)
    print(f"[{n}] {time.time() - t0:5.1f}s старт: {scene}", flush=True)
    if scene == "title":
        await pg.mouse.click(*(await game_pt(640, 470)))       # «НАЧАТЬ»
    bad = 0
    for i in range(40):
        s = await ev(fr, "window.wnbState || ''")
        top = await ev(pg, "document.title")
        g = "ЗАВИС" if s == "FROZEN" else (json.loads(s).get("scene") if s else "-")
        p = "ЗАВИС" if top == "FROZEN" else "ok"
        if s == "FROZEN" or top == "FROZEN":
            bad += 1
            print(f"[{n}] {time.time() - t0:5.1f}s  игра: {g}  страница: {p}", flush=True)
            if bad >= 3:
                break
        await pg.wait_for_timeout(1000)
    print(f"[{n}] итог:", "ЗАВИСАЕТ" if bad else "не зависает", flush=True)
    await br.close()
    return bool(bad)


async def main():
    async with async_playwright() as pw:
        res = [await one(pw, i + 1) for i in range(RUNS)]
    print("зависаний:", sum(res), "из", len(res))


asyncio.run(main())
