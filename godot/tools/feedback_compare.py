"""Отправка замечаний: Godot (компьютер) ↔ game.py — без настоящей таблицы.

  python godot/tools/feedback_compare.py

Поднимает локальный http-сервер (127.0.0.1, случайный порт) и шлёт в него одни и те же запросы из game.py
(feedback_send с подменённым FEEDBACK_URL, очередь — во временной папке) и из Godot (tests/feedback_net.gd,
«-- --feedback-url=…», очередь user://feedback_outbox_test.json). Сверяет: метод, путь, Content-Type, тело байт в
байт (json.dumps ↔ Feedback.py_dumps: кириллица \\uXXXX, кавычки, эмодзи), что делают на переадресации 302 (так
отвечает Apps Script), на ошибке сервера и без сети (очередь), и досылку очереди при следующем запуске.
В настоящую таблицу (script.google.com) ничего не уходит: адрес — только локальный. Браузер — web_smoke feedback.
"""
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GODOT = r"D:\Godot\Godot_v4.7.2-stable_win64_console.exe"
GOT = []                                     # [сторона, метод, путь, Content-Type, тело]
SIDE = ["-"]


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _rec(self, body=b""):
        GOT.append([SIDE[0], self.command, self.path, self.headers.get("Content-Type"), body])

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        self._rec(body)
        if self.path == "/ok":
            self._reply(200, b"ok")
        elif self.path == "/redir":                # как Apps Script: POST /exec → 302 на googleusercontent (только GET)
            self.send_response(302)
            self.send_header("Location", "/echo")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/echo":
            self._reply(405, b"POST not allowed")
        else:
            self._reply(500, b"fail")

    def do_GET(self):
        self._rec()
        self._reply(200 if self.path == "/echo" else 404, b"{\"ok\":true}")

    def _reply(self, code, body):
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def payloads():
    ref = json.load(open(os.path.join(ROOT, "godot", "content", "feedback_ref.json"), encoding="utf-8"))
    out = []
    for i, (name, p) in enumerate(sorted(ref.items())[:3]):
        p = {k: v for k, v in p.items() if not k.startswith("_")}
        out.append(dict({"time": "2026-11-20T12:00:0%d" % i}, **p, platform="test", uid="u%d" % i))
    long_ru = ("Ёлки-палки: «кавычки» \"двойные\" \\ обратная черта, эмодзи 🙂👍🏽, табуляции нет. " * 12)[:600].strip()
    out.append({"time": "2026-11-20T12:00:09", "lang": "ru", "scene": "hub", "job": "", "title": "", "phase": "",
                "step": "", "kind": "general", "reason": "Other", "expected": "", "got": "", "game_message": "",
                "comment": long_ru, "key": "wnb-feedback-1", "version": "0.5", "platform": "test", "uid": "u9",
                "jobs": {"flat": {"done": True, "errors": 2, "secs": 95}}})
    return out


def run_py(url, items, data_dir, flush=False):
    import game
    game.FEEDBACK_URL = url
    game.DATA_DIR = data_dir
    if flush:
        game.feedback_flush_outbox()
    else:
        for p in items:
            game.feedback_send(dict(p))
    t0 = time.time()
    while time.time() - t0 < 25 and any(t.daemon and t.is_alive() and t is not threading.current_thread()
                                        and not t.name.startswith("srv") for t in threading.enumerate()):
        time.sleep(0.05)
    try:
        return json.load(open(os.path.join(data_dir, "feedback_outbox.json"), encoding="utf-8"))
    except Exception:
        return []


def run_godot(url, items, tmp, flush=False):
    inp, out = os.path.join(tmp, "in.json"), os.path.join(tmp, "out.json")
    json.dump(items, open(inp, "w", encoding="utf-8"), ensure_ascii=False)
    if os.path.exists(out):
        os.remove(out)
    args = [GODOT, "--headless", "--path", os.path.join(ROOT, "godot"), "-s", "res://tests/feedback_net.gd", "--",
            "--test", "--feedback-url=" + url, "--in", inp, "--out", out] + (["--flush-only"] if flush else [])
    subprocess.run(args, capture_output=True, timeout=120)
    r = json.load(open(out, encoding="utf-8"))
    return r["outbox"], r["outbox_path"]


def main():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    sys.path.insert(0, ROOT)
    import pygame
    pygame.init()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    th = threading.Thread(target=srv.serve_forever, name="srv", daemon=True)
    th.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    dead = f"http://127.0.0.1:{s.getsockname()[1]}/ok"   # порт занят, но не слушает — «нет сети»
    items = payloads()
    tmp = tempfile.mkdtemp(prefix="wnb_fb_")
    pyd = os.path.join(tmp, "py")
    os.makedirs(pyd)
    fails, notes = [], []

    def chk(ok, what):
        (notes if ok else fails).append(what)
        print(("  ok   " if ok else "  FAIL ") + what, flush=True)

    # Godot: своя тестовая очередь — с чистого листа
    _, gq_path = run_godot(base + "/ok", [], tmp, flush=True)
    if os.path.exists(gq_path):
        os.remove(gq_path)
    # 1. обычная отправка: те же запросы → то же на сервере
    for side, fn in (("py", lambda u, it, f=False: run_py(u, it, pyd, f)), ("godot", lambda u, it, f=False: run_godot(u, it, tmp, f)[0])):
        SIDE[0] = side
        GOT_before = len(GOT)
        q = fn(base + "/ok", items)
        chk(q == [], f"{side}: /ok — очередь после ответа 200 пуста ({len(q)})")
        globals()["_" + side] = GOT[GOT_before:]
    py_, gd_ = globals()["_py"], globals()["_godot"]
    chk(len(py_) == len(gd_) == len(items), f"запросов: game.py {len(py_)}, Godot {len(gd_)}, ждали {len(items)}")
    pyb = {json.loads(r[4])["uid"]: r for r in py_}
    for r in gd_:
        u = json.loads(r[4])["uid"]
        p = pyb.get(u)
        same = p is not None and p[1:4] == r[1:4] and p[4] == r[4]
        chk(same, f"{u}: метод {r[1]} путь {r[2]} Content-Type «{r[3]}», тело {len(r[4])} байт — "
                  + ("байт в байт как game.py" if same else f"РАЗНИЦА: game.py {p[1:4] if p else None} "
                                                         f"{(p[4][:160] if p else b'')!r} ≠ {r[4][:160]!r}"))
    body = next((r[4] for r in gd_ if json.loads(r[4])["uid"] == "u9"), b"")
    chk(body.isascii() and b"\\u0401" in body and b"\\ud83d\\ude42" in body,
        "кириллица и эмодзи — \\uXXXX (ASCII), как json.dumps")
    c = json.loads(body)["comment"] if body else ""
    chk(len(c) == len(items[-1]["comment"]) <= 600, f"длинный комментарий дошёл целиком ({len(c)} знаков, предел окна 600)")
    # 2. ошибка сервера (500) и нет сети: остаётся в очереди; при следующем запуске — досылается и очередь пуста
    for side in ("py", "godot"):
        SIDE[0] = side
        if side == "py":
            q1 = run_py(base + "/fail", items[:1], pyd)
            q2 = run_py(dead, items[1:2], pyd)
        else:
            q1 = run_godot(base + "/fail", items[:1], tmp)[0]
            q2 = run_godot(dead, items[1:2], tmp)[0]
        chk([x["uid"] for x in q1] == ["u0"] and [x["uid"] for x in q2] == ["u0", "u1"],
            f"{side}: 500 и нет сети — в очереди {[x['uid'] for x in q2]}")
        n0 = len(GOT)
        q3 = run_py(base + "/ok", [], pyd, True) if side == "py" else run_godot(base + "/ok", [], tmp, True)[0]
        sent = sorted(json.loads(r[4])["uid"] for r in GOT[n0:] if r[1] == "POST")
        chk(q3 == [] and sent == ["u0", "u1"], f"{side}: следующий запуск дослал {sent}, очередь пуста ({len(q3)})")
    # 3. переадресация 302 (Apps Script): что делает каждая сторона
    res = {}
    for side in ("py", "godot"):
        SIDE[0] = side
        n0 = len(GOT)
        q = run_py(base + "/redir", items[:1], pyd) if side == "py" else run_godot(base + "/redir", items[:1], tmp)[0]
        res[side] = ([f"{r[1]} {r[2]}" for r in GOT[n0:]], len(q))
        if q:                                     # убрать за собой
            run_py(base + "/ok", [], pyd, True) if side == "py" else run_godot(base + "/ok", [], tmp, True)
    chk(res["py"] == res["godot"], f"302: game.py {res['py'][0]} (в очереди {res['py'][1]}), "
                                   f"Godot {res['godot'][0]} (в очереди {res['godot'][1]})")
    srv.shutdown()
    s.close()
    if os.path.exists(gq_path):
        os.remove(gq_path)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"FEEDBACK COMPARE: {len(notes)} ok, {len(fails)} FAIL")
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
