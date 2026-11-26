# -*- coding: utf-8 -*-
"""Замена основного сайта Godot-версией — и откат. Сама замена — одна команда владельца.

  python godot/tools/release_web.py stage      — собрать Godot для основного сайта и разложить дерево сайта в
                                                 godot/build/site_main/ (ничего не выкладывает)
  python godot/tools/release_web.py check      — поднять site_main локально (127.0.0.1:8066) и проверить: Godot
                                                 web_smoke (boot, play, links, migrate, phone, embed) по корню,
                                                 pygame art_tests/web_smoke.py --no-build по classic/, файлы для
                                                 старой страницы из кеша
  python godot/tools/release_web.py rehearse   — то же дерево (ссылки — на адрес репетиции) в ТЕСТОВЫЙ репозиторий,
                                                 подпапка rehearsal/: commit, push, ждать Pages, живые проверки
  python godot/tools/release_web.py deploy --dry-run         — что изменится на основном сайте (файлы, размер)
  python godot/tools/release_web.py deploy --owner-approved  — ВЫКЛАДКА на основной сайт (только по команде владельца)
  python godot/tools/release_web.py rollback --dry-run        — к какому коммиту сайта вернёмся
  python godot/tools/release_web.py rollback --owner-approved — ОТКАТ основного сайта к состоянию до выпуска

Дерево сайта (site_main):
  /            — Godot-сборка (index.html, wnb-engine-*, wnb-*.pck, frames/, music/, splash.jpg, build_info.json):
                 рамка страницы WordPress с прежним адресом сразу показывает Godot;
  /classic/    — нынешняя pygame-сборка из web_deploy (index.html, apk, tar.gz, anim/, turntable/, favicon, splash):
                 запасная ссылка и откат; пути в ней относительные (fopen("wheels_and_bones.apk?v=…"), anim/…,
                 turntable/… — от адреса страницы), работает из подпапки как есть;
  переходные файлы pygame в корне (wheels_and_bones.apk, .tar.gz, anim/, turntable/) — для тех, у кого открыта
                 или закеширована прежняя index.html (GitHub Pages: кеш страниц 10 мин; открытая вкладка качает
                 anim/ и turntable/ по ходу игры): без них такая страница падала бы на 404. Git хранит одинаковые
                 файлы один раз, так что копия в classic/ и в корне репозиторий не раздувает; --no-legacy — без них
                 (следующий выпуск, когда переходный срок пройдёт);
  README.md, .nojekyll, test/ — как в web_deploy (test/ — старый pygame-тест, не трогаем).
Сохранения: pygame пишет localStorage «wnb:*», Godot — «wnb-godot:*» и один раз переносит «wnb:*» (тот же источник
fordragon88.github.io; в рамке WordPress — то же разделённое хранилище, что было у pygame в этой рамке).

Основной сайт (D:\\wheels_and_bones\\web_deploy, fordragon88/wheels-and-bones-web) меняют ТОЛЬКО deploy и rollback и
только с --owner-approved. Без флага они печатают план и ничего не делают.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_web  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GODOT = build_web.GODOT
ROOT = build_web.ROOT                                     # worktree (game.py, art_tests/)
BUILD = os.path.join(GODOT, "build")
SITE = os.path.join(BUILD, "site_main")
SITE_REH = os.path.join(BUILD, "site_rehearsal")
MANIFEST = os.path.join(BUILD, "site_main.json")         # что и из чего собрано (deploy сверяет)
RELEASE_LOG = os.path.join(BUILD, "release_log.json")    # выкладки на основной сайт: коммит до и после
PARENT = os.path.dirname(ROOT)                            # D:\wheels_and_bones (рядом с worktree)
MAIN_DIR = os.environ.get("WNB_MAIN_DEPLOY", os.path.join(PARENT, "web_deploy"))
TEST_DIR = os.environ.get("WNB_TEST_DEPLOY", os.path.join(PARENT, "web_deploy_test"))
MAIN_REPO = "fordragon88/wheels-and-bones-web"
TEST_REPO = "fordragon88/wheels-and-bones-test"
TEST_URL = "https://fordragon88.github.io/wheels-and-bones-test/"
REH_DIR = "rehearsal"                                     # подпапка репетиции в тестовом репозитории
REH_URL = TEST_URL + REH_DIR + "/"
CLASSIC = "classic"
PYGAME_FILES = ["index.html", "wheels_and_bones.apk", "wheels_and_bones.tar.gz", "favicon.png", "splash.jpg",
                "anim", "turntable"]
LEGACY_ROOT = ["wheels_and_bones.apk", "wheels_and_bones.tar.gz", "anim", "turntable", "favicon.png"]
KEEP_ROOT = ["README.md", ".nojekyll", "test"]            # из web_deploy как есть
LOCAL_PORT = int(os.environ.get("WNB_SITE_PORT", "8066"))
SMOKE_ONLY = "boot,play,links,migrate,phone,embed"
PAGES_LIMIT = 1024 ** 3                                   # GitHub Pages: опубликованный сайт ≤ 1 ГБ
GIT_ID = ["-c", "user.name=fordragon88", "-c", "user.email=98241749+fordragon88@users.noreply.github.com"]


def log(msg=""):
    print(msg, flush=True)


def main_url():
    """Адрес сборки на GitHub Pages (= game.SHARE_DIRECT_URL, через content/data/game_consts.json)."""
    u = str(build_web.share_consts().get("direct_url", ""))
    if not u.startswith("https://"):
        raise SystemExit("game_consts.json: нет share.direct_url — запусти tools/sync_content.py")
    return u


def git(repo, *args, check=True, capture=True):
    r = subprocess.run(["git", "-C", repo] + GIT_ID + list(args), capture_output=capture, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {(r.stderr or r.stdout or '').strip()[:500]}")
    return (r.stdout or "").strip()


def mb(n):
    return f"{n / 1e6:.1f} МБ"


def tree_files(top, skip_git=True):
    """{относительный путь (/): размер} — все файлы дерева (без .git)."""
    out = {}
    for dp, dns, files in os.walk(top):
        if skip_git:
            dns[:] = [d for d in dns if d != ".git"]
        for fn in files:
            p = os.path.join(dp, fn)
            out[os.path.relpath(p, top).replace("\\", "/")] = os.path.getsize(p)
    return out


def file_sha(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_item(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


# ---------------- сборка дерева ----------------

def main_head_clean():
    """web_deploy: чистое дерево и его коммит (только чтение)."""
    if not os.path.isdir(os.path.join(MAIN_DIR, ".git")):
        raise SystemExit(f"нет клона основного сайта: {MAIN_DIR}")
    dirty = git(MAIN_DIR, "status", "--porcelain")
    if dirty:
        raise SystemExit(f"в {MAIN_DIR} есть незакоммиченные изменения — сначала разобраться:\n{dirty[:800]}")
    return git(MAIN_DIR, "rev-parse", "HEAD")


def pygame_src():
    """Где в web_deploy лежит pygame-сборка: до первого выпуска Godot — в корне, после — в classic/ (в корне тогда
    index.html уже от Godot: брать его как pygame-страницу нельзя — classic/ стал бы копией Godot-страницы)."""
    sub = os.path.join(MAIN_DIR, CLASSIC)
    if os.path.exists(os.path.join(sub, "index.html")):
        return sub
    return MAIN_DIR


def is_pygame_page(path):
    """index.html pygame-сборки (pygbag): качает wheels_and_bones.apk; у Godot-страницы этого нет."""
    try:
        html = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return False
    return 'fopen("wheels_and_bones.apk' in html and "wnb-engine-" not in html


def assemble(dest, base_url, legacy=True, classic_counter=True, keep=KEEP_ROOT):
    """Godot-сборка (godot/build/web, уже собрана) в корень dest, pygame из web_deploy — в classic/ (+ переходные
    файлы в корне). classic_counter=False — убрать счётчик посещений из classic/index.html (репетиция: pygame
    web_smoke его не глушит, а статистику владельца проверками не трогаем)."""
    head = main_head_clean()
    src = pygame_src()
    missing = [n for n in PYGAME_FILES if not os.path.exists(os.path.join(src, n))]
    if missing:
        raise SystemExit(f"в {src} нет файлов pygame-сборки: {missing}")
    if not is_pygame_page(os.path.join(src, "index.html")):
        raise SystemExit(f"{os.path.join(src, 'index.html')} — не страница pygame-сборки: не из чего собрать {CLASSIC}/")
    if src != MAIN_DIR:
        log(f"   на сайте уже Godot: pygame-версия берётся из {src}")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    out = build_web.OUT
    for n in os.listdir(out):
        copy_item(os.path.join(out, n), os.path.join(dest, n))
    clash = [n for n in PYGAME_FILES + KEEP_ROOT if n not in ("index.html", "splash.jpg") and os.path.exists(os.path.join(out, n))]
    if clash:
        raise SystemExit(f"имена Godot-сборки совпали с файлами pygame/сайта: {clash}")
    if file_sha(os.path.join(out, "splash.jpg")) != file_sha(os.path.join(src, "splash.jpg")):
        log("   ! splash.jpg Godot и pygame различаются — в корне будет заставка Godot (старая страница покажет её)")
    for n in PYGAME_FILES:
        copy_item(os.path.join(src, n), os.path.join(dest, CLASSIC, n))
    if not classic_counter:
        ci = os.path.join(dest, CLASSIC, "index.html")
        html = open(ci, encoding="utf-8").read()
        html2 = re.sub(r'<script id="wnb-goatcounter"[^>]*></script>', "", html)
        open(ci, "w", encoding="utf-8", newline="").write(html2)
    if legacy:
        for n in LEGACY_ROOT:
            copy_item(os.path.join(src, n), os.path.join(dest, n))
    for n in keep:
        if os.path.exists(os.path.join(MAIN_DIR, n)):
            copy_item(os.path.join(MAIN_DIR, n), os.path.join(dest, n))
    readme = os.path.join(dest, "README.md")
    site = base_url if base_url.startswith(TEST_URL) else main_url()
    with open(readme, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Wheels & Bones — browser build\n\n"
                f"Educational wheelchair-repair game (English). Playable at {site}\n\n"
                "This repository contains only the built web version:\n\n"
                "- `/` — the game (Godot 4, WebAssembly): `index.html`, `wnb-engine-*`, `wnb-*.pck`, `frames/`, `music/`.\n"
                f"- `/{CLASSIC}/` — the previous version (pygame / pygbag), kept as a fallback.\n"
                + ("- `wheels_and_bones.apk`, `wheels_and_bones.tar.gz`, `anim/`, `turntable/` in the root — files of the "
                   "previous version for pages still open or cached in browsers; they will be removed later.\n"
                   if legacy else "")
                + "\nKeyboard controls: arrows, Tab, Enter; F1 — help. Screen readers read the game through a live "
                  "region on the page.\n")
    info = json.load(open(os.path.join(out, "build_info.json"), encoding="utf-8"))
    return head, info


def site_summary(top):
    files = tree_files(top)
    total = sum(files.values())
    parts = {}
    for rel, n in files.items():
        k = rel.split("/")[0] if "/" in rel else "(корень)"
        parts[k] = parts.get(k, 0) + n
    return files, total, parts


def godot_build(base_url, counter=True):
    """Сборка в godot/build/web; base_url=None — основной сайт (страница WordPress, game.SHARE_BASE_URL)."""
    build_web.build(base_url, counter=counter)
    return json.load(open(os.path.join(build_web.OUT, "build_info.json"), encoding="utf-8"))


def restore_test_build():
    """В godot/build/web снова обычная тестовая сборка (как python godot/tools/build_web.py без флагов)."""
    log("== обычная тестовая сборка обратно в godot/build/web")
    build_web.build(build_web.DEFAULT_BASE)


def embed_claim():
    """Размер первой загрузки, написанный в блоке WordPress («about N MB»)."""
    p = os.path.join(GODOT, "web", "wordpress_embed_godot.html")
    m = re.search(r"about (\d+) MB", open(p, encoding="utf-8").read())
    return int(m.group(1)) if m else None


def code_dirty():
    """Незакоммиченные правки в godot/ (кроме заметок .md) — сборка была бы не из того, что в истории."""
    out = git(ROOT, "status", "--porcelain", "--", "godot")
    return [ln[3:] for ln in out.splitlines() if not ln.rstrip().endswith(".md")]


def code_changed_since(commit):
    """Файлы godot/ (кроме .md), изменённые после сборки site_main: коммиты после commit и незакоммиченное."""
    out = git(ROOT, "diff", "--name-only", commit, "HEAD", "--", "godot")
    return sorted(set([ln for ln in out.splitlines() if ln and not ln.endswith(".md")] + code_dirty()))


def cmd_stage(a):
    log(f"== stage: Godot для основного сайта, pygame из {MAIN_DIR}")
    info = godot_build(None)
    if not info.get("main"):
        raise SystemExit(f"сборка не для основного адреса: {info.get('base_url')}")
    head, info = assemble(SITE, info["base_url"], legacy=not a.no_legacy)
    files, total, parts = site_summary(SITE)
    first = info["sizes"]["first_gz"] / 1e6
    claim = embed_claim()
    manifest = {"time": time.strftime("%Y-%m-%d %H:%M"), "web_deploy_head": head, "base_url": info["base_url"],
                "pack": info["pack"], "engine": info["engine"], "counter": info.get("counter"),
                "legacy": not a.no_legacy, "files": len(files), "bytes": total,
                "godot_commit": git(ROOT, "rev-parse", "--short", "HEAD"), "dirty": code_dirty()}
    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not a.keep_build:
        restore_test_build()
    log("")
    log(f"STAGE: {SITE} — {len(files)} файлов, {mb(total)} (Pages ≤ 1 ГБ: {total / PAGES_LIMIT:.0%}); "
        f"пакет {info['pack']}, ссылки → {info['base_url']}, счётчик {info.get('counter') or 'нет'}; "
        f"pygame из web_deploy {head[:8]}; первая загрузка {first:.1f} МБ (в блоке WordPress: about {claim} MB)")
    for k in sorted(parts, key=lambda k: -parts[k]):
        log(f"   {k:24s} {mb(parts[k]):>10}")
    if claim is not None and abs(claim - first) > 1.5:
        log(f"   ! в wordpress_embed_godot.html «about {claim} MB», а первая загрузка {first:.1f} МБ — поправь текст блока")


# ---------------- проверки ----------------

def make_site_server(top, port, strip_counter_classic=True):
    """Раздача дерева сайта; в classic/index.html — без счётчика посещений (pygame web_smoke его не глушит)."""
    import functools
    import http.server
    import threading

    class H(build_web_handler()):
        def send_head(self):
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            if strip_counter_classic and path in (f"/{CLASSIC}/", f"/{CLASSIC}/index.html"):
                html = open(os.path.join(top, CLASSIC, "index.html"), encoding="utf-8").read()
                raw = re.sub(r'<script id="wnb-goatcounter"[^>]*></script>', "", html).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                import io
                return io.BytesIO(raw)
            return super().send_head()

    class S(http.server.ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):   # браузер оборвал загрузку — норма
                super().handle_error(request, client_address)

    srv = S(("127.0.0.1", port), functools.partial(H, directory=top))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def build_web_handler():
    """Обработчик как у build_web.make_server: типы .wasm/.pck/.webp/.mp3, без кеша."""
    import http.server

    class H(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".wasm": "application/wasm",
                          ".pck": "application/octet-stream", ".js": "text/javascript", ".webp": "image/webp",
                          ".mp3": "audio/mpeg", ".apk": "application/octet-stream"}

        def end_headers(self):
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def log_message(self, *a):
            pass
    return H


def http_status(url, timeout=30):
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "wnb-release-check"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(1 << 16)
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"{type(e).__name__}"


class Tally:
    def __init__(self):
        self.ok, self.fail = [], []

    def check(self, cond, what):
        (self.ok if cond else self.fail).append(what)
        log(("  ok   " if cond else "  FAIL ") + what)
        return cond


def file_checks(t, base, top):
    """Без браузера: корень — Godot, classic/ — pygame, переходные файлы для старой index.html из кеша на месте."""
    bi = json.load(open(os.path.join(top, "build_info.json"), encoding="utf-8"))
    for rel in ("", "index.html", bi["pack"], bi["engine"] + ".wasm", bi["engine"] + ".js", "build_info.json",
                f"{CLASSIC}/", f"{CLASSIC}/wheels_and_bones.apk", f"{CLASSIC}/favicon.png"):
        st = http_status(base + rel)
        t.check(st == 200, f"файл {rel or '/'}: {st}")
    root = urllib.request.urlopen(base, timeout=30).read().decode("utf-8", "replace")
    t.check(bi["pack"] in root and "wnb-goatcounter" in root, "корень — Godot-страница (пакет, счётчик)")
    old = open(os.path.join(top, CLASSIC, "index.html"), encoding="utf-8").read()
    names = re.findall(r'fopen\("([^"?]+)\?v=', old)
    t.check(bool(names), f"pygame-страница качает {names}")
    tt = sorted(n for n in os.listdir(os.path.join(top, CLASSIC, "turntable")) if n.endswith(".jpg"))[:1]
    an = sorted(os.listdir(os.path.join(top, CLASSIC, "anim")))[:1]
    samples = [f"turntable/{tt[0]}"] if tt else []
    if an:
        samples.append(f"anim/{an[0]}/00.jpg")
    for rel in names + samples:                        # classic/ — относительные пути от подпапки
        st = http_status(base + f"{CLASSIC}/" + rel)
        t.check(st == 200, f"classic/{rel}: {st}")
    legacy = os.path.exists(os.path.join(top, "wheels_and_bones.apk"))
    for rel in names + samples:                        # старая index.html из кеша (адрес — корень сайта)
        st = http_status(base + rel)
        if legacy:
            t.check(st == 200, f"для старой страницы из кеша: /{rel}: {st}")
        else:
            log(f"  ..   без переходных файлов: /{rel}: {st} (старая страница из кеша не загрузится)")


def run_smoke(t, url, label, extra_env=None, godot_only=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", WNB_URL=url, WNB_PORT="8063", **(extra_env or {}))
    cmd = [sys.executable, os.path.join(HERE, "web_smoke.py"), "--no-build", "--only", godot_only or SMOKE_ONLY]
    log(f"== Godot web_smoke ({label}): {url}")
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout + r.stderr
    tail = [ln for ln in out.splitlines() if ln.startswith("WEB SMOKE") or ln.strip().startswith("FAIL")]
    for ln in tail[:30]:
        log("   " + ln.strip())
    line = next((ln for ln in out.splitlines() if ln.startswith("WEB SMOKE")), "WEB SMOKE: нет итога")
    open(os.path.join(BUILD, f"release_smoke_{label}.log"), "w", encoding="utf-8").write(out)
    t.check(r.returncode == 0, f"Godot web_smoke {label}: {line}")
    return line


def run_pygame_smoke(t, url, label):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", WNB_URL=url)
    log(f"== pygame art_tests/web_smoke.py --no-build ({label}): {url}")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "art_tests", "web_smoke.py"), "--no-build"], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout + r.stderr
    open(os.path.join(BUILD, f"release_pygame_{label}.log"), "w", encoding="utf-8").write(out)
    for ln in [ln for ln in out.splitlines() if ln.startswith("WEB SMOKE") or ln.strip().startswith("FAIL")][:30]:
        log("   " + ln.strip())
    line = next((ln for ln in out.splitlines() if ln.startswith("WEB SMOKE")), "WEB SMOKE: нет итога")
    t.check(r.returncode == 0, f"pygame web_smoke {label}: {line}")
    return line


def cmd_check(a):
    if not os.path.exists(os.path.join(SITE, "index.html")):
        raise SystemExit("нет godot/build/site_main — сначала stage")
    t = Tally()
    srv = make_site_server(SITE, LOCAL_PORT)
    base = f"http://127.0.0.1:{LOCAL_PORT}/"
    log(f"== check: {SITE} → {base}")
    try:
        file_checks(t, base, SITE)
        run_smoke(t, base, "local", {"WNB_EXPECT_MAIN": "1"})
        if not a.godot_only:
            run_pygame_smoke(t, base + CLASSIC + "/", "local_classic")
    finally:
        srv.shutdown()
        srv.server_close()
    line = f"RELEASE CHECK: {len(t.ok)} ok, {len(t.fail)} FAIL"
    log(f"\n{line} (site_main, локально {base})")
    for f in t.fail:
        log("   FAIL " + f)
    man = json.load(open(MANIFEST, encoding="utf-8"))          # stage пишет манифест заново — итог check к нему привязан
    man["check"] = {"ok": not t.fail and not a.godot_only, "time": time.strftime("%Y-%m-%d %H:%M"), "line": line,
                    "godot_only": bool(a.godot_only)}
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if t.fail else 0


# ---------------- выкладка: общее ----------------

def mirror_into(src, repo, sub=""):
    """Дерево src → repo/sub (sub="" — весь репозиторий, кроме .git): лишнее удаляется, одинаковые файлы не трогаются.
    Возврат: (добавлено, изменено, удалено) — списки путей."""
    dst = os.path.join(repo, sub) if sub else repo
    os.makedirs(dst, exist_ok=True)
    want, have = tree_files(src), tree_files(dst)
    added, changed, removed = [], [], []
    for rel in want:
        s, d = os.path.join(src, rel), os.path.join(dst, rel)
        if rel not in have:
            added.append(rel)
        elif have[rel] != want[rel] or file_sha(s) != file_sha(d):
            changed.append(rel)
        else:
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
    for rel in have:
        if rel not in want:
            removed.append(rel)
            os.remove(os.path.join(dst, rel))
    for dp, dns, files in sorted(os.walk(dst), key=lambda x: -len(x[0])):
        if ".git" in dp.split(os.sep):
            continue
        if dp != dst and not os.listdir(dp):
            os.rmdir(dp)
    return added, changed, removed


def diff_plan(src, repo):
    """Как mirror_into, но без изменений: что добавится/изменится/удалится и сколько новых данных уйдёт в git."""
    want, have = tree_files(src), tree_files(repo)
    added = [r for r in want if r not in have]
    changed = [r for r in want if r in have and (want[r] != have[r] or file_sha(os.path.join(src, r)) !=
                                                  file_sha(os.path.join(repo, r)))]
    removed = [r for r in have if r not in want]
    # новые для git данные: содержимое, которого в репозитории ещё нет (classic/ — копии уже хранимых файлов)
    blobs = {}
    for r in added + changed:
        p = os.path.join(src, r)
        with open(p, "rb") as f:
            data = f.read()
        blobs[hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()] = len(data)
    new = 0
    if blobs:
        r = subprocess.run(["git", "-C", repo, "cat-file", "--batch-check"], input="\n".join(blobs) + "\n",
                           capture_output=True, text=True)
        for ln in r.stdout.splitlines():
            if ln.endswith(" missing"):
                new += blobs.get(ln.split()[0], 0)
    return added, changed, removed, want, have, new


def gh_pages_wait(repo_dir, gh_repo, timeout=1200):
    """Ждать сборку Pages ИМЕННО этого коммита (latest build сразу после push — ещё прежний). «errored» — один
    повтор сборки (грабли Pages: syncing_files, см. AGENTS 10.11)."""
    head = git(repo_dir, "rev-parse", "HEAD")
    t0, retried = time.time(), False
    while time.time() - t0 < timeout:
        r = subprocess.run(["gh", "api", f"repos/{gh_repo}/pages/builds/latest", "--jq", '.status+" "+.commit'],
                           capture_output=True, text=True).stdout.strip()
        if r == f"built {head}":
            log(f"   pages: built {head[:8]} за {time.time() - t0:.0f} с")
            return True
        if r.startswith("errored") and r.endswith(head):
            if retried:
                log(f"   pages: ОШИБКА сборки {r}")
                return False
            log("   pages: сборка упала — повтор (gh api -X POST …/pages/builds)")
            subprocess.run(["gh", "api", "-X", "POST", f"repos/{gh_repo}/pages/builds"], capture_output=True)
            retried = True
        time.sleep(15)
    log(f"   pages: не дождался сборки {head[:8]}")
    return False


def wait_live(base, pack, timeout=900):
    """Сайт отдаёт новую сборку: index.html с этим пакетом И сам .pck — 200 (не только страница)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            html = urllib.request.urlopen(urllib.request.Request(base + f"?nocache={int(time.time())}",
                                                                 headers={"Cache-Control": "no-cache"}),
                                          timeout=30).read().decode("utf-8", "replace")
        except Exception:
            html = ""
        if pack in html and http_status(base + pack) == 200:
            log(f"   живой адрес {base}: index.html с {pack} и пакет — 200 ({time.time() - t0:.0f} с)")
            return True
        time.sleep(15)
    log(f"   живой адрес {base}: не дождался {pack}")
    return False


# ---------------- репетиция на тестовом адресе ----------------

def cmd_rehearse(a):
    if not os.path.isdir(os.path.join(TEST_DIR, ".git")):
        raise SystemExit(f"нет клона тестового сайта: {TEST_DIR}")
    if git(TEST_DIR, "status", "--porcelain"):
        raise SystemExit(f"в {TEST_DIR} есть незакоммиченные изменения — сначала разобраться")
    log(f"== rehearse: сборка с основой ссылок {REH_URL}")
    info = godot_build(REH_URL)
    # репетиция: без test/ (старый pygame-тест основного сайта — 84 МБ, к замене не относится; у тестового сайта
    # предел Pages тот же 1 ГБ)
    assemble(SITE_REH, REH_URL, legacy=not a.no_legacy, classic_counter=False,
             keep=[n for n in KEEP_ROOT if n != "test"])
    restore_test_build()
    added, changed, removed = mirror_into(SITE_REH, TEST_DIR, REH_DIR)
    log(f"   {TEST_DIR}\\{REH_DIR}: +{len(added)} ~{len(changed)} -{len(removed)} файлов")
    git(TEST_DIR, "add", "-A", "--", REH_DIR)
    outside = [ln for ln in git(TEST_DIR, "status", "--porcelain").splitlines() if not ln[3:].startswith(REH_DIR + "/")]
    if outside:
        raise SystemExit(f"изменения вне {REH_DIR}/ — не выкладываю:\n" + "\n".join(outside[:20]))
    t = Tally()
    if subprocess.run(["git", "-C", TEST_DIR, "diff", "--cached", "--quiet"]).returncode == 0:
        log("   репетиция не изменилась — выкладывать нечего")
    else:
        git(TEST_DIR, "commit", "-q", "-m",
            f"Репетиция замены сайта: Godot в корне rehearsal/, pygame в rehearsal/classic/ "
            f"(godot-port {git(ROOT, 'rev-parse', '--short', 'HEAD')}, {info['pack']})")
        git(TEST_DIR, "push", "-q", capture=False)
        log(f"   push: {git(TEST_DIR, 'rev-parse', '--short', 'HEAD')}")
        t.check(gh_pages_wait(TEST_DIR, TEST_REPO), "GitHub Pages собрал коммит репетиции")
    t.check(wait_live(REH_URL, info["pack"]), f"репетиция отвечает: {REH_URL}{info['pack']} — 200")
    file_checks(t, REH_URL, SITE_REH)
    run_smoke(t, REH_URL, "rehearsal")
    if not a.godot_only:
        run_pygame_smoke(t, REH_URL + CLASSIC + "/", "rehearsal_classic")
    log(f"\nREHEARSE: {len(t.ok)} ok, {len(t.fail)} FAIL — {REH_URL} (classic: {REH_URL}{CLASSIC}/)")
    for f in t.fail:
        log("   FAIL " + f)
    return 1 if t.fail else 0


# ---------------- основной сайт: deploy / rollback ----------------

def plan_deploy():
    if not os.path.exists(MANIFEST) or not os.path.exists(os.path.join(SITE, "index.html")):
        raise SystemExit("нет godot/build/site_main — сначала: python godot/tools/release_web.py stage (и check)")
    man = json.load(open(MANIFEST, encoding="utf-8"))
    head = main_head_clean()
    if head != man["web_deploy_head"]:
        raise SystemExit(f"web_deploy сейчас {head[:8]}, а site_main собран при {man['web_deploy_head'][:8]} — "
                         "classic/ устарел: заново stage и check")
    added, changed, removed, want, have, new = diff_plan(SITE, MAIN_DIR)
    return man, head, added, changed, removed, want, have, new


def deploy_blockers(man):
    """Почему выкладывать нельзя: проверка check не пройдена для этого дерева, или код изменился после stage."""
    out = []
    ck = man.get("check") or {}
    if not ck.get("ok"):
        out.append("нет пройденной проверки этого дерева (python godot/tools/release_web.py check): "
                   + ck.get("line", "check не запускался") + (" — только Godot, без classic/" if ck.get("godot_only") else ""))
    if man.get("dirty"):
        out.append(f"site_main собран с незакоммиченными правками в godot/: {man['dirty'][:5]}")
    ch = code_changed_since(man["godot_commit"])
    if ch:
        out.append(f"код в godot/ изменился после stage ({man['godot_commit']}): {ch[:5]}{' …' if len(ch) > 5 else ''}")
    return out


def print_plan(man, head, added, changed, removed, want, have, new):
    url = main_url()
    total = sum(want.values())
    log(f"ОСНОВНОЙ САЙТ {url} (репозиторий {MAIN_REPO}, клон {MAIN_DIR}, сейчас {head[:8]})")
    log(f"будет: Godot-сборка в корне (пакет {man['pack']}, ссылки → {man['base_url']}, счётчик {man['counter']}), "
        f"pygame — в {CLASSIC}/, переходные файлы pygame в корне: {'да' if man['legacy'] else 'нет'}")
    log(f"файлов: добавится {len(added)} ({mb(sum(want[r] for r in added))}), изменится {len(changed)} "
        f"({mb(sum(want[r] for r in changed))}), удалится {len(removed)} ({mb(sum(have[r] for r in removed))})")
    groups = {}
    for kind, lst in (("+", added), ("~", changed), ("-", removed)):
        for r in lst:
            k = (kind, r.split("/")[0] + ("/" if "/" in r else ""))
            groups[k] = groups.get(k, 0) + 1
    for (kind, k), n in sorted(groups.items(), key=lambda x: (x[0][1], x[0][0])):
        log(f"   {kind} {k:34s} {n:5d} файл(ов)")
    log(f"сайт после выкладки: {len(want)} файлов, {mb(total)} (предел Pages 1 ГБ: {total / PAGES_LIMIT:.0%}); "
        f"новых данных в git (без уже хранимых копий): {mb(new)}")
    log(f"откат: python godot/tools/release_web.py rollback --owner-approved  (вернёт {head[:8]})")


def cmd_deploy(a):
    if not (a.dry_run or a.owner_approved):
        log("deploy меняет ОСНОВНОЙ сайт. Только по команде владельца: --owner-approved; посмотреть план: --dry-run.\n")
        plan = plan_deploy()
        print_plan(*plan)
        for b in deploy_blockers(plan[0]):
            log("   ! " + b)
        return 2
    if a.owner_approved and not a.dry_run:
        log("== git pull web_deploy (свежий основной сайт)")
        git(MAIN_DIR, "pull", "-q", "--ff-only", capture=False)
    plan = plan_deploy()
    print_plan(*plan)
    man, head = plan[0], plan[1]
    blockers = deploy_blockers(man)
    for b in blockers:
        log("   ! " + b)
    if a.dry_run:
        log("\n--dry-run: ничего не изменено." + (" Выкладка сейчас откажется — сначала stage и check." if blockers else
                                                  " Проверка check пройдена: " + man["check"]["time"] + "."))
        return 0
    if blockers:
        raise SystemExit("выкладка остановлена, основной сайт не тронут: заново stage и check")
    log("\n== выкладка на основной сайт (--owner-approved)")
    mirror_into(SITE, MAIN_DIR)
    git(MAIN_DIR, "add", "-A")
    git(MAIN_DIR, "commit", "-q", "-m", f"Godot-версия в корне, pygame — в {CLASSIC}/ (release_web.py; godot-port "
                                       f"{man['godot_commit']}, {man['pack']})")
    new = git(MAIN_DIR, "rev-parse", "HEAD")
    entries = json.load(open(RELEASE_LOG, encoding="utf-8")) if os.path.exists(RELEASE_LOG) else []
    entries.append({"time": time.strftime("%Y-%m-%d %H:%M"), "before": head, "after": new, "pack": man["pack"]})
    json.dump(entries, open(RELEASE_LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    try:
        git(MAIN_DIR, "push", "-q", capture=False)
    except SystemExit:
        raise SystemExit(f"push не прошёл: сайт НЕ изменён, коммит {new[:8]} остался только в {MAIN_DIR}. Повторить "
                         f"отправку: git -C {MAIN_DIR} push ; отменить: git -C {MAIN_DIR} reset --hard {head[:8]}")
    log(f"   push {new[:8]} (до выпуска было {head[:8]})")
    t = Tally()
    url = main_url()
    t.check(gh_pages_wait(MAIN_DIR, MAIN_REPO), "GitHub Pages собрал выпуск")
    t.check(wait_live(url, man["pack"]), f"основной сайт отдаёт {man['pack']}")
    file_checks(t, url, SITE)
    run_smoke(t, url, "main", {"WNB_EXPECT_MAIN": "1"}, godot_only="boot,play,links,migrate,embed")
    # pygame в classic/ на основном сайте — только файлами: его web_smoke не глушит счётчик посещений
    log(f"\nDEPLOY: {len(t.ok)} ok, {len(t.fail)} FAIL — {url} (classic: {url}{CLASSIC}/); "
        f"откат: python godot/tools/release_web.py rollback --owner-approved")
    for f in t.fail:
        log("   FAIL " + f)
    return 1 if t.fail else 0


def rollback_target(a):
    if a.to:
        return git(MAIN_DIR, "rev-parse", a.to)
    if os.path.exists(RELEASE_LOG):
        entries = json.load(open(RELEASE_LOG, encoding="utf-8"))
        if entries:
            return entries[-1]["before"]
    # журнала нет (выкладка с другой машины) — коммит перед последним выпуском release_web.py
    out = git(MAIN_DIR, "log", "--format=%H %s", "-200")
    for ln in out.splitlines():
        h, s = ln.split(" ", 1)
        if s.startswith("Godot-версия в корне"):
            return git(MAIN_DIR, "rev-parse", h + "^")
    raise SystemExit("не нашёл выпуск Godot в истории web_deploy — укажи --to <коммит>")


def cmd_rollback(a):
    head = main_head_clean()
    try:
        target = rollback_target(a)
    except SystemExit as e:
        if a.owner_approved and not a.dry_run:
            raise
        log(f"{e}\nВыпуска Godot на основном сайте ещё не было. Если выложить сейчас (deploy --owner-approved), откат "
            f"вернёт сайт к нынешнему коммиту web_deploy: "
            f"{git(MAIN_DIR, 'log', '-1', '--format=%h %ad %s', '--date=format:%Y-%m-%d %H:%M', head)}")
        return 0
    tlog = git(MAIN_DIR, "log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M", target)
    stat = git(MAIN_DIR, "diff", "--shortstat", "HEAD", target)
    log(f"ОТКАТ основного сайта {main_url()}: сейчас {head[:8]}, вернём дерево коммита {tlog}")
    log(f"   изменения: {stat or 'нет — уже так'}; история не переписывается (новый коммит «Откат…», push без --force)")
    if not (a.dry_run or a.owner_approved):
        log("rollback меняет ОСНОВНОЙ сайт. Только по команде владельца: --owner-approved; посмотреть: --dry-run.")
        return 2
    if a.dry_run:
        log("--dry-run: ничего не изменено.")
        return 0
    if not stat:
        return 0
    git(MAIN_DIR, "rm", "-r", "-q", ".")
    git(MAIN_DIR, "checkout", target, "--", ".")
    git(MAIN_DIR, "add", "-A")
    git(MAIN_DIR, "commit", "-q", "-m", f"Откат сайта к {target[:8]} (release_web.py rollback)")
    git(MAIN_DIR, "push", "-q", capture=False)
    t = Tally()
    t.check(gh_pages_wait(MAIN_DIR, MAIN_REPO), "GitHub Pages собрал откат")
    url = main_url()
    old = open(os.path.join(MAIN_DIR, "index.html"), encoding="utf-8").read()
    names = re.findall(r'fopen\("([^"?]+)\?v=', old)
    for rel in [""] + names:
        t.check(http_status(url + rel) == 200, f"после отката {url}{rel}: 200")
    log(f"\nROLLBACK: {len(t.ok)} ok, {len(t.fail)} FAIL — сайт снова как в {target[:8]}")
    return 1 if t.fail else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage")
    s.add_argument("--no-legacy", action="store_true", help="без переходных файлов pygame в корне")
    s.add_argument("--keep-build", action="store_true", help="не возвращать тестовую сборку в godot/build/web")
    c = sub.add_parser("check")
    c.add_argument("--godot-only", action="store_true", help="без pygame web_smoke по classic/")
    r = sub.add_parser("rehearse")
    r.add_argument("--no-legacy", action="store_true")
    r.add_argument("--godot-only", action="store_true")
    for name in ("deploy", "rollback"):
        x = sub.add_parser(name)
        x.add_argument("--dry-run", action="store_true")
        x.add_argument("--owner-approved", action="store_true", help="команда владельца — менять основной сайт")
        if name == "rollback":
            x.add_argument("--to", help="коммит web_deploy (по умолчанию — до последнего выпуска)")
    a = ap.parse_args()
    fn = {"stage": cmd_stage, "check": cmd_check, "rehearse": cmd_rehearse, "deploy": cmd_deploy,
          "rollback": cmd_rollback}[a.cmd]
    sys.exit(fn(a) or 0)


if __name__ == "__main__":
    main()
