# -*- coding: utf-8 -*-
"""Браузерная сборка Godot-версии: python godot/tools/build_web.py [--base-url URL] [--sync] [--serve [PORT]]

Что делает (по образцу build_web.py pygame-версии):
  1. content/ нет или --sync — python godot/tools/sync_content.py.
  2. Копия проекта в godot/build/web_stage/ (не в git; .godot/ там живёт между сборками — импорт только изменившегося):
     код, сцены, i18n, web/shell.html, content/data (в game_consts.json — share.base_url = --base-url и блок "web" с
     метками версий кадров и музыки), шрифты, звуки, картинки — крупные (≥150 КБ) импортируются с потерями (WebP
     lossy 0,8: фоны и портреты в 3–6 раз легче), индексы кадров content/frames/*.json. Кадров и музыки в пакете НЕТ.
  3. godot --headless --import, затем --export-release "Web" (однопоточный, export_presets.cfg) → godot/build/web/.
  4. Метка версии против кеша: файлы движка и пакета переименовываются по хэшу содержимого (wnb-engine-<хэш>.wasm/.js,
     wnb-<хэш>.pck), GODOT_CONFIG в index.html правится; кадры и музыка — ?v=<хэш> в адресе (игра берёт метку из
     game_consts.json → web).
  5. Рядом с игрой: frames/ (кадры поворота и петли — WebP, качаются по мере надобности), music/<тема>.mp3 (моно,
     ffmpeg; играет элемент <audio> страницы), splash.jpg (заставка загрузки).
  6. Печатает размеры: .wasm (и в gzip — так его отдаёт GitHub Pages), .pck, первая загрузка, кадры, музыка.
Все пути в index.html относительные — папку build/web/ можно выложить в любую подпапку сайта как есть.
--serve [PORT] — после сборки раздать build/web/ локально (http://127.0.0.1:PORT/, по умолчанию 8060)."""
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GODOT = os.path.dirname(HERE)
ROOT = os.path.dirname(GODOT)
CONTENT = os.path.join(GODOT, "content")
STAGE = os.path.join(GODOT, "build", "web_stage")
OUT = os.path.join(GODOT, "build", "web")
GODOT_EXE = os.environ.get("GODOT", r"D:\Godot\Godot_v4.7.2-stable_win64_console.exe")
DEFAULT_BASE = "https://fordragon88.github.io/wheels-and-bones-test/godot/"
CODE_DIRS = ["autoload", "ui", "screens", "i18n", "web"]
CODE_FILES = ["project.godot", "export_presets.cfg", "main.gd", "main.gd.uid", "main.tscn",
              "tests/shots.gd", "tests/shots.gd.uid"]   # shots.gd — состояния экранов для замера (?test=1, wnbStage)
LOSSY_MIN = 150_000            # картинки крупнее — с потерями (как build_web.py pygame: JPEG для файлов > 150 КБ)
LOSSY_Q = 0.8
MUSIC_ARGS = ["-ac", "1", "-c:a", "libmp3lame", "-q:a", "5"]   # моно VBR ~70–90 кбит/с: фоновая музыка
PYGAME_APK_MB = 15.3           # pygame-сборка (wheels_and_bones.apk) для сравнения


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log(msg):
    print(msg, flush=True)


def same(src, dst):
    if not os.path.exists(dst):
        return False
    a, b = os.stat(src), os.stat(dst)
    return a.st_size == b.st_size and int(a.st_mtime) == int(b.st_mtime)


def mirror(src, dst, pred=lambda rel: True, transform=None):
    """Копия папки src → dst только изменившихся файлов; в dst лишние (в src их уже нет) удаляются.
    transform(rel, src_path, dst_path) -> True, если записал сам."""
    keep = set()
    for dp, dns, files in os.walk(src):
        dns[:] = [d for d in dns if d != ".godot"]
        for fn in files:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, src).replace("\\", "/")
            if not pred(rel):
                continue
            out = os.path.join(dst, rel)
            keep.add(os.path.normcase(out))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if transform and transform(rel, full, out):
                continue
            if not same(full, out):
                shutil.copy2(full, out)
    if os.path.isdir(dst):
        for dp, dns, files in os.walk(dst):
            dns[:] = [d for d in dns if d != ".godot"]
            for fn in files:
                p = os.path.join(dp, fn)
                if os.path.normcase(p) not in keep:
                    os.remove(p)
    return len(keep)


def tree_hash(path, exts=None):
    h = hashlib.sha1()
    for dp, dns, files in sorted(os.walk(path)):
        dns.sort()
        for fn in sorted(files):
            if exts and not fn.endswith(exts):
                continue
            p = os.path.join(dp, fn)
            h.update(os.path.relpath(p, path).replace("\\", "/").encode())
            with open(p, "rb") as f:
                h.update(f.read())
    return h.hexdigest()[:10]


def file_hash(*paths):
    h = hashlib.sha1()
    for p in paths:
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:10]


def dir_size(path):
    n = c = 0
    for dp, _, files in os.walk(path):
        for fn in files:
            n += os.path.getsize(os.path.join(dp, fn))
            c += 1
    return n, c


def gz_size(path):
    with open(path, "rb") as f:
        return len(gzip.compress(f.read(), 6))


def mb(n):
    return f"{n / 1048576:.2f} МБ"


# ---------------- шаги ----------------

def ensure_content(force):
    if force or not os.path.exists(os.path.join(CONTENT, "manifest.json")) or \
            not os.path.isdir(os.path.join(CONTENT, "frames", "turntable")):
        log("== sync_content.py")
        subprocess.run([sys.executable, os.path.join(HERE, "sync_content.py")], check=True, cwd=ROOT)


def build_music():
    """music/<тема>.mp3 моно рядом с игрой (кеш перекодированных — build/web_music_cache; НЕ внутри web_stage: там
    Godot импортировал бы их и положил в пакет)."""
    src = os.path.join(CONTENT, "music")
    cache = os.path.join(GODOT, "build", "web_music_cache")
    os.makedirs(cache, exist_ok=True)
    out = os.path.join(OUT, "music")
    os.makedirs(out, exist_ok=True)
    themes = []
    for name in sorted(os.listdir(src)):
        base, ext = os.path.splitext(name)
        if ext.lower() not in (".mp3", ".ogg", ".wav"):
            continue
        themes.append(base)
        c = os.path.join(cache, base + ".mp3")
        if not os.path.exists(c) or os.path.getmtime(c) < os.path.getmtime(os.path.join(src, name)):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(src, name)] + MUSIC_ARGS + [c],
                           check=True)
        shutil.copy2(c, os.path.join(out, base + ".mp3"))
    for fn in os.listdir(out):
        if os.path.splitext(fn)[0] not in themes:
            os.remove(os.path.join(out, fn))
    return themes


def stage(base_url, frames_v, music_v):
    os.makedirs(STAGE, exist_ok=True)
    gi = os.path.join(GODOT, "build", ".gdignore")       # редактор основного проекта не должен видеть build/ (там
    if not os.path.exists(gi):                            # вложенный проект web_stage и тысячи кадров)
        open(gi, "w").close()
    for fn in CODE_FILES:
        s, d = os.path.join(GODOT, fn), os.path.join(STAGE, fn)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if not same(s, d):
            shutil.copy2(s, d)
    for d in CODE_DIRS:
        mirror(os.path.join(GODOT, d), os.path.join(STAGE, d))
    sc, dc = CONTENT, os.path.join(STAGE, "content")

    def data_tf(rel, full, out):
        if rel != "game_consts.json":
            return False
        consts = json.load(open(full, encoding="utf-8"))
        consts.setdefault("share", {})["base_url"] = base_url
        consts["web"] = {"frames_v": frames_v, "music_v": music_v, "music_ext": "mp3"}
        text = json.dumps(consts, ensure_ascii=False, indent=1)
        if not os.path.exists(out) or open(out, encoding="utf-8").read() != text:
            with open(out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        return True

    def img_tf(rel, full, out):
        if not rel.endswith(".png.import"):
            return False
        png = full[:-len(".import")]
        text = open(full, encoding="utf-8").read()
        if os.path.getsize(png) >= LOSSY_MIN:
            text = re.sub(r"(?m)^compress/mode=\d+$", "compress/mode=1", text)
            text = re.sub(r"(?m)^compress/lossy_quality=[\d.]+$", f"compress/lossy_quality={LOSSY_Q}", text)
        if os.path.basename(png).startswith("bg_"):              # фоны 1280×720 рисуются 1:1 (или крупнее) —
            text = re.sub(r"(?m)^mipmaps/generate=\w+$", "mipmaps/generate=false", text)   # mipmaps не нужны
        if not os.path.exists(out) or open(out, encoding="utf-8").read() != text:
            with open(out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        return True

    mirror(os.path.join(sc, "data"), os.path.join(dc, "data"), transform=data_tf)
    for d in ("fonts", "sfx"):
        mirror(os.path.join(sc, d), os.path.join(dc, d))
    mirror(os.path.join(sc, "img"), os.path.join(dc, "img"), transform=img_tf)
    mirror(os.path.join(sc, "frames"), os.path.join(dc, "frames"), pred=lambda rel: "/" not in rel and rel.endswith(".json"))
    for d in ("music",):                                     # музыки в пакете нет (лежит рядом с игрой)
        shutil.rmtree(os.path.join(dc, d), ignore_errors=True)


def godot(*args, what=""):
    t0 = time.time()
    r = subprocess.run([GODOT_EXE, "--headless", "--path", STAGE] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    errs = [ln for ln in out.splitlines() if "ERROR" in ln or "SCRIPT ERROR" in ln or "Parse Error" in ln]
    log(f"   {what}: {time.time() - t0:.1f} с, код {r.returncode}" + (f", ошибок в выводе: {len(errs)}" if errs else ""))
    for ln in errs[:15]:
        log("   ! " + ln.strip())
    if r.returncode != 0:
        log(out[-3000:])
        raise SystemExit(f"godot {what}: код {r.returncode}")
    return errs


def export():
    keep = {"frames", "music"}
    if os.path.isdir(OUT):
        for fn in os.listdir(OUT):
            p = os.path.join(OUT, fn)
            if fn not in keep:
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(OUT, exist_ok=True)
    try:
        errs = godot("--import", what="импорт")
    except SystemExit:
        # первый импорт свежей копии (пустая .godot/) у 4.7.2 headless иногда падает (0xC0000005 на шрифте);
        # повторный доимпортирует остальное и проходит
        log("   импорт упал — ещё раз")
        errs = godot("--import", what="импорт (повтор)")
    errs += godot("--export-release", "Web", os.path.join(OUT, "index.html"), what="экспорт")
    if errs:
        raise SystemExit("в выводе Godot есть ошибки — см. выше")
    for fn in ("index.html", "index.js", "index.wasm", "index.pck"):
        if not os.path.exists(os.path.join(OUT, fn)):
            raise SystemExit("экспорт не создал " + fn)


def stamp():
    """Файлы движка и пакета — по хэшу содержимого; GODOT_CONFIG и <script> в index.html — на новые имена."""
    p = lambda fn: os.path.join(OUT, fn)
    eng = ["index.js", "index.wasm", "index.audio.worklet.js", "index.audio.position.worklet.js"]
    eng = [fn for fn in eng if os.path.exists(p(fn))]
    exe = "wnb-engine-" + file_hash(*[p(fn) for fn in eng])
    pck = "wnb-" + file_hash(p("index.pck")) + ".pck"
    for fn in eng:
        os.replace(p(fn), p(exe + fn[len("index"):]))
    os.replace(p("index.pck"), p(pck))
    if os.path.exists(p("index.png")):
        os.remove(p("index.png"))                      # заставка Godot: у страницы своя (splash.jpg)
    html = open(p("index.html"), encoding="utf-8").read()
    m = re.search(r"const GODOT_CONFIG = (\{.*?\});\n", html)
    cfg = json.loads(m.group(1))
    cfg["executable"] = exe
    cfg["mainPack"] = pck
    cfg["fileSizes"] = {exe + ".wasm": os.path.getsize(p(exe + ".wasm")), pck: os.path.getsize(p(pck))}
    html = html[:m.start(1)] + json.dumps(cfg, separators=(",", ":")) + html[m.end(1):]
    html = html.replace('<script src="index.js"></script>', f'<script src="{exe}.js"></script>')
    if f'src="{exe}.js"' not in html:
        raise SystemExit("index.html: не нашёл <script src=\"index.js\">")
    with open(p("index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return exe, pck


def copy_frames():
    src = os.path.join(CONTENT, "frames")
    return mirror(src, os.path.join(OUT, "frames"),
                  pred=lambda rel: rel.endswith(".webp") and (rel.startswith("turntable/") or rel.startswith("anim/")))


def report(exe, pck, themes):
    p = lambda fn: os.path.join(OUT, fn)
    wasm, js = p(exe + ".wasm"), p(exe + ".js")
    w, wg = os.path.getsize(wasm), gz_size(wasm)
    k = os.path.getsize(p(pck))
    kg = gz_size(p(pck))
    j, jg = os.path.getsize(js), gz_size(js)
    h = os.path.getsize(p("index.html"))
    fr, frn = dir_size(p("frames"))
    mu, _ = dir_size(p("music"))
    sp = os.path.getsize(p("splash.jpg")) if os.path.exists(p("splash.jpg")) else 0
    log("== размеры")
    log(f"   движок .wasm      {mb(w)}  (gzip {mb(wg)} — так отдаёт GitHub Pages)")
    log(f"   движок .js        {mb(j)}  (gzip {mb(jg)})")
    log(f"   пакет .pck        {mb(k)}  (gzip {mb(kg)})")
    log(f"   страница+заставка {mb(h + sp)}")
    first = wg + jg + kg + h + sp
    log(f"   ПЕРВАЯ ЗАГРУЗКА (сжатое по сети, если сервер сжимает .pck; без — {mb(wg + jg + k + h + sp)}): {mb(first)}"
        f"  — pygame-сборка: apk {PYGAME_APK_MB} МБ + интерпретатор")
    log(f"   рядом с игрой: frames/ {mb(fr)} ({frn} файлов, качаются по мере надобности), music/ {mb(mu)} "
        f"({len(themes)} тем; играет та, что нужна экрану)")
    return {"wasm": w, "wasm_gz": wg, "js": j, "js_gz": jg, "pck": k, "pck_gz": kg, "frames": fr, "frames_n": frn,
            "music": mu, "first_gz": first}


# ---------------- локальный сервер ----------------

def make_server(path, port):
    """Раздача папки сборки (для проверки): .wasm — application/wasm, без кеша. Возврат: (сервер, поток)."""
    import functools
    import http.server
    import threading

    class H(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".wasm": "application/wasm",
                          ".pck": "application/octet-stream", ".js": "text/javascript", ".webp": "image/webp",
                          ".mp3": "audio/mpeg"}

        def end_headers(self):
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=path))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, th


def build(base_url=DEFAULT_BASE, sync=False):
    t0 = time.time()
    ensure_content(sync)
    log("== кадры и музыка рядом с игрой")
    os.makedirs(OUT, exist_ok=True)
    nfr = copy_frames()
    themes = build_music()
    frames_v = tree_hash(os.path.join(OUT, "frames"), (".webp",))
    music_v = tree_hash(os.path.join(OUT, "music"), (".mp3",))
    log(f"   кадров {nfr}, метка {frames_v}; музыка {', '.join(themes)}, метка {music_v}")
    log("== копия проекта → build/web_stage")
    stage(base_url, frames_v, music_v)
    log("== Godot")
    export()
    exe, pck = stamp()
    splash = os.path.join(ROOT, "art_tests", "web_splash.jpg")
    if os.path.exists(splash):
        shutil.copy2(splash, os.path.join(OUT, "splash.jpg"))
    sizes = report(exe, pck, themes)
    with open(os.path.join(OUT, "build_info.json"), "w", encoding="utf-8") as f:
        json.dump({"base_url": base_url, "engine": exe, "pack": pck, "frames_v": frames_v, "music_v": music_v,
                   "sizes": sizes, "time": time.strftime("%Y-%m-%d %H:%M")}, f, ensure_ascii=False, indent=1)
    log(f"== готово за {time.time() - t0:.0f} с: {OUT}")
    log(f"   ссылки-задания ведут на {base_url}")
    return sizes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE, help="адрес сборки на сайте (для ссылок-заданий)")
    ap.add_argument("--sync", action="store_true", help="сначала sync_content.py")
    ap.add_argument("--serve", nargs="?", const=8060, type=int, help="после сборки раздать локально (порт)")
    ap.add_argument("--no-build", action="store_true", help="только раздать готовое (с --serve)")
    a = ap.parse_args()
    if not a.base_url.endswith("/"):
        a.base_url += "/"
    if not a.no_build:
        build(a.base_url, a.sync)
    if a.serve:
        srv, _ = make_server(OUT, a.serve)
        log(f"== http://127.0.0.1:{a.serve}/  (Ctrl+C — остановить)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            srv.shutdown()


if __name__ == "__main__":
    main()
