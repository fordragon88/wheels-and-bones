"""Проверка отправки замечаний (без настоящей Google-таблицы — локальный сервер вместо неё):
снимок уходит JPEG 640×360, без сети замечания копятся в очереди и досылаются, когда сеть появилась.
python art_tests/feedback_check.py"""
import os, sys, json, threading, time, tempfile, socket, base64, io
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from http.server import HTTPServer, BaseHTTPRequestHandler
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
import game
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
game.DATA_DIR = tempfile.mkdtemp(); game.FEEDBACK_URL = f"http://127.0.0.1:{port}/"
shot = pygame.Surface((1280, 720)); shot.fill((200, 100, 50))
for c in ("offline 1", "offline 2"):
    game.feedback_send(game.feedback_payload(dict(time="t", comment=c), shot))
for _ in range(40):
    time.sleep(0.5)
    if os.path.exists(game._outbox_path()) and len(json.load(open(game._outbox_path()))) == 2:
        break
assert len(json.load(open(game._outbox_path()))) == 2, "без сети замечания не легли в очередь"
game.feedback_flush_outbox()
assert len(json.load(open(game._outbox_path()))) == 2, "неудачная досылка потеряла замечания"
got = []


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        got.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(200); self.end_headers(); self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", port), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
game.feedback_flush_outbox()
assert sorted(g["comment"] for g in got) == ["offline 1", "offline 2"], got
assert not os.path.exists(game._outbox_path()), "очередь не очистилась"
img = pygame.image.load(io.BytesIO(base64.b64decode(got[0]["screenshot_jpg_b64"])), "x.jpg")
assert img.get_size() == (640, 360) and got[0]["key"] == game.FEEDBACK_KEY
srv.shutdown()
print("OK: отправка, очередь без сети и досылка работают")
