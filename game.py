"""
КОЛЁСА И КОСТИ  // Wheels & Bones
===============================================================================
Обучающий симулятор ремонта инвалидных колясок в фэнтези-мире.
Зомби Мартин вечно теряет левую ногу. Чтобы попасть на вечеринку, он взял
коляску напрокат — и она сломалась по дороге. На помощь приходит призрак
прошлого хозяина, Бартоломью: сам он чинить толком не умеет, но «видел, как
делали мастера», и подсказывает (иногда — мимо). Вместе они учатся чинить.

Главное: РЕМОНТ — по-настоящему. Шаги, инструменты и детали взяты из реальных
руководств по обслуживанию колясок (см. README, раздел «Источники»).
Юмор — про Мартина, призрака и фэнтези-абсурд, но к самим коляскам и их
владельцам игра относится уважительно.

ГИЛЬДИЯ КОЛЁСНИКОВ (про-трек, открывается после 5 ремонтов): задания уровня
техника. Порядок шагов игра больше не диктует — планируешь сам; числовые
значения берутся из внутриигрового МАНУАЛА; пропуск шага техники безопасности
(питание, порядок клемм) — провал задания с разбором. Наставница — призрак
гномки-механика Бренны, той самой мастерицы, которую Барти «видел при жизни».
После трёх зачётов — ЭКЗАМЕН: случайный билет, без подсказок (мануал разрешён),
лимит ошибок, чек-лист и диплом. Ключевые шаги — мини-интеракции: накачка по
манометру, пинг-тест спиц, установка зазора, чтение мультиметра.

ЗАПУСК:
    python game.py            обычный запуск (окно 1280x720)
    python game.py --selftest headless-проверка логики (без окна)
    python game.py --assets   список картинок, которые игра ищет в assets/
    python game.py --reset    удалить сохранение (save.json)
    python game.py --unlock   предпросмотр: открыть все базовые задания и Гильдию
                              (осторожно: после первого ремонта это сохранится)
    python game.py --mute     без звука

Прогресс сохраняется в save.json рядом с игрой. Звук синтезируется кодом
(файлы не нужны): пинг-тест спиц действительно звучит «пинь»/«тук».

ДИАГНОСТИКА: варианты диагноза заблокированы, пока не осмотрено 2 детали —
диагноз ставится по уликам. У части клиентов (эльфийка, орк) под одним
симптомом живут РАЗНЫЕ поломки (поле variants) — при повторном визите
причина может оказаться другой, осмотр решает.

АРТ: весь визуал (персонажи, коляски, фоны) рисуется КОДОМ — встроенный
векторный flat-стиль, картинки не нужны вовсе. PNG из ComfyUI в assets/
(имена — `python game.py --assets`) по-прежнему имеет приоритет и ложится
поверх. Детали коляски кликаются прямо на её схеме (осмотр и ремонт), а в
диагностике есть ОСМОТР 3D: low-poly модель коляски (тоже задана кодом)
крутится мышью, детали кликаются в 3D — софтверный рендерер, без зависимостей.
Управление — мышью. Esc — «назад» по экранам (в ремонте — двойной Esc),
с титула — выход; прогресс сохраняется автоматически.
===============================================================================
"""

import array
import asyncio
import json
import math
import os
import sys
import random
import re
import tempfile
import threading
from contextlib import contextmanager
import pygame


@contextmanager
def _atomic_open(path):
    """Записать файл целиком или никак: пишем во временный рядом, потом os.replace (сбой не портит старый)."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            yield f
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise

# ----------------------------------------------------------------------------- #
#  Конфиг и палитра (тёплая мастерская + призрачно-зелёные акценты)
# ----------------------------------------------------------------------------- #
WIDTH, HEIGHT = 1280, 720
FPS = 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    # собранный .exe (PyInstaller --onefile): ассеты распакованы во временную папку,
    # а сохранения живут в профиле пользователя, чтобы не теряться между запусками
    ASSETS_DIR = os.path.join(getattr(sys, "_MEIPASS", BASE_DIR), "assets")
    DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "WheelsAndBones")
    os.makedirs(DATA_DIR, exist_ok=True)
else:
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    DATA_DIR = BASE_DIR
IS_WEB = sys.platform == "emscripten"          # браузерная версия (pygbag, WebAssembly)
WEB_RES = {"standard": (1280, 720), "high": (1920, 1080), "ultra": (2560, 1440)}   # холст в браузере
WEB_LEVELS = ("standard", "high", "ultra")
WEB_MIN_W = 768                                # «авто» в браузере: холст не меньше (масштаб рендера 0,6)     # «авто» выбирает по размеру окна игры на экране (и скорости ПК)
GAME_VERSION = "0.3"
SUPPORT_URL = "https://www.paypal.com/donate/?hosted_button_id=LFKGMSGCNHYHC"   # PayPal GOAT (кнопка «Donate!» на openassistivetech.org/contribute)
# Замечания игроков (флажок ⚑, «Я не согласен») уходят в Google-таблицу через веб-приложение Apps Script
# (docs/feedback/Code.gs, настройка — docs/FEEDBACK_SETUP.md). Пустой адрес — только локальный feedback.json.
FEEDBACK_URL = "https://script.google.com/macros/s/AKfycbyJxHpELYNd1CBpUmPLwIuT_hre-Nm-AJVJ9rCYDOrNLKKd26crV2G6omRPzTY6umtr/exec"
if os.environ.get("SDL_VIDEODRIVER") == "dummy" or "--selftest" in sys.argv:
    FEEDBACK_URL = ""                          # тесты и боты (без экрана) никогда не шлют замечания в таблицу
FEEDBACK_KEY = "wnb-feedback-1"
SAVE_PATH = os.path.join(DATA_DIR, "save.json")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
FEEDBACK_PATH = os.path.join(DATA_DIR, "feedback.json")   # «Я не согласен»: замечания игроков к заданиям   # громкость и язык (не сбрасываются --reset)
GUILD_REQ = 5                   # починенных колясок для доступа в Гильдию
EXAM_MAX_MISTAKES = 3           # лимит ошибок на экзамене Гильдии
INSPECT_REQ = 2                 # осмотров деталей, прежде чем откроется диагноз

BG       = (24, 22, 30)
PANEL    = (38, 34, 48)
PANEL2   = (50, 44, 64)
WOOD     = (92, 64, 44)
GHOST    = (130, 240, 200)      # призрак / зомби-зелёный
AMBER    = (240, 190, 90)       # дерево/латунь мастерской
RUST     = (210, 120, 70)
GOOD     = (120, 230, 140)
BAD      = (235, 100, 110)
CYAN     = (110, 210, 235)
PURPLE   = (180, 140, 240)
WHITE    = (236, 238, 245)
GREY     = (150, 150, 165)
DIM      = (90, 88, 104)

# ----------------------------------------------------------------------------- #
#  Рендер в разрешении экрана. Игра думает в ЛОГИЧЕСКИХ координатах 1280x720 (вся раскладка),
#  а пиксели поверхностей — ×RS (1080p: 1.5, 1440p+: 2). Surf хранит логический размер, обёртки
#  DR (рисование), TF (масштаб/поворот), LFont (шрифты), aa_* и mouse_pos() пересчитывают сами.
#  При RS = 1 (тесты, маленькие экраны) всё ведёт себя ровно как обычный pygame.
# ----------------------------------------------------------------------------- #
RS = 1.0


def _rs(surf):
    return RS if isinstance(surf, Surf) else 1.0


def _w(width, k):
    return 0 if width <= 0 else max(1, round(width * k))


def _rr(rect, k):
    """Логический прямоугольник -> пиксели (края округляются, чтобы соседние блоки не расходились)."""
    r = pygame.Rect(rect)
    if k == 1:
        return r
    x0, y0 = round(r.x * k), round(r.y * k)
    return pygame.Rect(x0, y0, round(r.right * k) - x0, round(r.bottom * k) - y0)


class Surf(pygame.Surface):
    """Поверхность в логических пикселях игры; внутри — пиксели экрана (×RS)."""

    def __init__(self, size, flags=0, *args, real=None):
        """real — точный размер в пикселях экрана (копии существующих поверхностей: без пересчёта и масштабирования)."""
        lw, lh = int(size[0]), int(size[1])
        pygame.Surface.__init__(self, real or (max(1, round(lw * RS)), max(1, round(lh * RS))), flags, *args)
        self._ls = (lw, lh)

    @staticmethod
    def adopt(real, logical=None):
        """Обычную поверхность (пиксели экрана) -> Surf с логическим размером real/RS (точная копия пикселей)."""
        rw, rh = pygame.Surface.get_size(real)          # настоящие пиксели (без C-аллокации подтипа от real)
        if logical is None:
            logical = (max(1, round(rw / RS)), max(1, round(rh / RS)))
        alpha = real.get_flags() & pygame.SRCALPHA
        out = Surf(logical, alpha, real=(rw, rh))       # точный размер: никакого smoothscale на ±1 пиксель
        if alpha:
            pygame.Surface.fill(out, (0, 0, 0, 0))
            pygame.Surface.blit(out, real, (0, 0), None, pygame.BLEND_RGBA_MAX)
        else:
            pygame.Surface.blit(out, real, (0, 0))
        return out

    def _logical(self):
        ls = getattr(self, "_ls", None)
        if ls is None:
            ls = (max(1, round(pygame.Surface.get_width(self) / RS)),
                  max(1, round(pygame.Surface.get_height(self) / RS)))
        return ls

    def get_size(self):
        return self._logical()

    def get_width(self):
        return self._logical()[0]

    def get_height(self):
        return self._logical()[1]

    def get_rect(self, **kw):
        r = pygame.Rect((0, 0), self._logical())
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def blit(self, src, dest=(0, 0), area=None, special_flags=0):
        x, y = (dest.x, dest.y) if isinstance(dest, pygame.Rect) else (dest[0], dest[1])
        pygame.Surface.blit(self, src, (round(x * RS), round(y * RS)),
                            _rr(area, RS) if area is not None else None, special_flags)
        w, h = src._logical() if isinstance(src, Surf) else (src.get_width() / RS, src.get_height() / RS)
        return pygame.Rect(int(x), int(y), int(w), int(h))

    def fill(self, color, rect=None, special_flags=0):
        return pygame.Surface.fill(self, color, _rr(rect, RS) if rect is not None else None, special_flags)

    def copy(self):
        alpha = self.get_flags() & pygame.SRCALPHA
        out = Surf(self._logical(), alpha, real=pygame.Surface.get_size(self))
        if alpha:
            pygame.Surface.fill(out, (0, 0, 0, 0))
            pygame.Surface.blit(out, self, (0, 0), None, pygame.BLEND_RGBA_MAX)
        else:
            pygame.Surface.blit(out, self, (0, 0))
        return out

    def convert_alpha(self, *a):
        out = Surf(self._logical(), pygame.SRCALPHA, real=pygame.Surface.get_size(self))
        pygame.Surface.fill(out, (0, 0, 0, 0))
        pygame.Surface.blit(out, self, (0, 0), None, pygame.BLEND_RGBA_MAX)
        return out

    def convert(self, *a):
        out = Surf(self._logical(), 0, real=pygame.Surface.get_size(self))
        pygame.Surface.blit(out, self, (0, 0))
        return out

    def subsurface(self, rect):
        r = pygame.Rect(rect)
        alpha = self.get_flags() & pygame.SRCALPHA
        out = Surf(r.size, alpha, real=_rr(r, RS).size)
        if alpha:
            pygame.Surface.fill(out, (0, 0, 0, 0))
            pygame.Surface.blit(out, self, (0, 0), _rr(r, RS), pygame.BLEND_RGBA_MAX)
        else:
            pygame.Surface.blit(out, self, (0, 0), _rr(r, RS))
        return out

    def set_at(self, pos, color):
        return pygame.Surface.set_at(self, (int(pos[0] * RS), int(pos[1] * RS)), color)


def _pp(p, k):
    return (p[0] * k, p[1] * k)


class DR:
    """pygame.draw в логических координатах (для Surf — ×RS: толщины, радиусы, точки)."""

    @staticmethod
    def line(s, c, a, b, width=1):
        k = _rs(s)
        return pygame.draw.line(s, c, _pp(a, k), _pp(b, k), _w(width, k) or 1)

    @staticmethod
    def lines(s, c, closed, pts, width=1):
        k = _rs(s)
        return pygame.draw.lines(s, c, closed, [_pp(p, k) for p in pts], _w(width, k) or 1)

    @staticmethod
    def polygon(s, c, pts, width=0):
        k = _rs(s)
        return pygame.draw.polygon(s, c, [_pp(p, k) for p in pts], _w(width, k))

    @staticmethod
    def rect(s, c, rect, width=0, border_radius=0, **kw):
        k = _rs(s)
        return pygame.draw.rect(s, c, _rr(rect, k), _w(width, k), round(border_radius * k), **kw)

    @staticmethod
    def ellipse(s, c, rect, width=0):
        k = _rs(s)
        return pygame.draw.ellipse(s, c, _rr(rect, k), _w(width, k))

    @staticmethod
    def arc(s, c, rect, a0, a1, width=1):
        k = _rs(s)
        return pygame.draw.arc(s, c, _rr(rect, k), a0, a1, _w(width, k) or 1)

    @staticmethod
    def circle(s, c, center, radius, width=0, **kw):
        k = _rs(s)
        return pygame.draw.circle(s, c, _pp(center, k), radius * k, _w(width, k), **kw)


class TF:
    """pygame.transform для Surf: размеры логические, результат — снова Surf."""

    @staticmethod
    def smoothscale(s, size):
        if not isinstance(s, Surf):
            return pygame.transform.smoothscale(s, size)
        lw, lh = max(1, int(size[0])), max(1, int(size[1]))
        out = Surf((lw, lh), s.get_flags() & pygame.SRCALPHA)
        pygame.transform.smoothscale(s, pygame.Surface.get_size(out), out)
        return out

    @staticmethod
    def rotozoom(s, angle, scale):
        real = pygame.transform.rotozoom(s, angle, scale)
        return Surf.adopt(real) if isinstance(s, Surf) else real


def easy_font_on():
    """Шрифт для лёгкого чтения (Atkinson Hyperlegible): включён и язык английский (в нём нет кириллицы)."""
    return bool(A11Y.get("font")) and LANG["code"] == "en"


_ALT_OK = {}                                    # символ -> есть ли он в Atkinson (общий для всех размеров)


class LFont:
    """Шрифт: рендер нужного размера в пикселях экрана, метрики — в логических.
    С «лёгким шрифтом» буквы — Atkinson Hyperlegible, а значки (✔ ⚑ ▸ →…), которых в нём нет, — DejaVu:
    строка рисуется кусками, ширина считается так же."""

    def __init__(self, size, bold=False):
        px = max(1, round(size * RS * TEXT_K[min(len(TEXT_K) - 1, max(0, A11Y.get("text", 0)))]))
        path = os.path.join(ASSETS_DIR, "fonts", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        try:                                     # свой шрифт: значки ⚑ ✔ ◉ ★ ⟲ есть на любом компьютере
            self.f = pygame.font.Font(path, px)
        except Exception:
            self.f = pygame.font.SysFont("dejavusans,segoeuisymbol,arial,helvetica", px, bold=bold)
        self.alt = None
        if easy_font_on():
            try:
                self.alt = pygame.font.Font(os.path.join(
                    ASSETS_DIR, "fonts", "AtkinsonHyperlegible-Bold.ttf" if bold else "AtkinsonHyperlegible-Regular.ttf"),
                    max(1, round(px * 1.08)))           # Atkinson уже DejaVu — чуть крупнее, чтобы не мельчил
                self._notdef = self.alt.metrics("\ue000")[0]
            except Exception:
                self.alt = None
        self._cache = {}

    def _has(self, ch):
        ok = _ALT_OK.get(ch)
        if ok is None:
            try:
                m = self.alt.metrics(ch)[0]
                ok = ch.isspace() or (m is not None and m != self._notdef)
            except Exception:
                ok = False
            _ALT_OK[ch] = ok
        return ok

    def _runs(self, text):
        """Куски строки: (шрифт, текст)."""
        if self.alt is None:
            return [(self.f, text)]
        out = []
        for ch in text:
            fnt = self.alt if self._has(ch) else self.f
            if out and out[-1][0] is fnt:
                out[-1][1].append(ch)
            else:
                out.append((fnt, [ch]))
        return [(fnt, "".join(cs)) for fnt, cs in out] or [(self.alt, "")]

    def _render_real(self, text, aa, color, bg):
        runs = self._runs(text)
        if len(runs) == 1:
            fnt = runs[0][0]
            return fnt.render(text, aa, color, bg) if bg is not None else fnt.render(text, aa, color)
        parts = [fnt.render(t, aa, color) for fnt, t in runs]
        asc = max(fnt.get_ascent() for fnt, _ in runs)
        h = max(asc + max(-fnt.get_descent() for fnt, _ in runs), max(p.get_height() for p in parts))
        out = pygame.Surface((sum(p.get_width() for p in parts), h), pygame.SRCALPHA)
        if bg is not None:
            out.fill(bg)
        x = 0
        for (fnt, _), part in zip(runs, parts):
            out.blit(part, (x, asc - fnt.get_ascent()))
            x += part.get_width()
        return out

    def render(self, text, aa=True, color=(255, 255, 255), bg=None):
        key = (text, aa, tuple(color), None if bg is None else tuple(bg))
        img = self._cache.get(key)
        if img is None:
            try:
                real = self._render_real(text, aa, color, bg)
            except pygame.error:                   # строка из одних невидимых символов (U+200B…): «Text has zero width»
                real = pygame.Surface((1, max(1, self.f.get_height())), pygame.SRCALPHA)
            img = Surf.adopt(real)
            if len(self._cache) > 1500:
                self._cache.clear()
            self._cache[key] = img
        img.set_alpha(255)              # без копии: вызывающие ставят set_alpha сразу перед blit, сбрасываем здесь
        return img

    def size(self, text):
        runs = self._runs(text)
        w = sum(fnt.size(t)[0] for fnt, t in runs)
        h = max(fnt.size(t)[1] for fnt, t in runs)
        return (math.ceil(w / RS), math.ceil(h / RS))

    def get_height(self):
        return math.ceil(max(self.f.get_height(), self.alt.get_height() if self.alt else 0) / RS)

    def get_linesize(self):
        return math.ceil(max(self.f.get_linesize(), self.alt.get_linesize() if self.alt else 0) / RS)

    def __getattr__(self, name):
        return getattr(self.f, name)


FINGER = {"t": -10 ** 9, "id": None, "pos": None}   # последнее касание (палец), логические координаты


def _rot_scale(img, anchor, ang_bone, ang_out, s_along, s_across):
    """Картинку с костью под углом ang_bone (градусы, против часовой): кость горизонтально, вдоль × s_along,
    поперёк × s_across, затем под угол ang_out. Возврат: (картинка, где теперь точка anchor)."""
    def turn(im, a_xy, deg):
        c = (im.get_width() / 2, im.get_height() / 2)
        out = pygame.transform.rotate(im, deg)
        t = math.radians(deg)
        vx, vy = a_xy[0] - c[0], a_xy[1] - c[1]
        return out, (out.get_width() / 2 + vx * math.cos(t) + vy * math.sin(t),
                     out.get_height() / 2 - vx * math.sin(t) + vy * math.cos(t))
    im, a = turn(img, anchor, -ang_bone)
    w, h = max(1, round(im.get_width() * s_along)), max(1, round(im.get_height() * s_across))
    a = (a[0] * w / im.get_width(), a[1] * h / im.get_height())
    im = pygame.transform.smoothscale(im, (w, h))
    return turn(im, a, ang_out)


def m3d_fit_zoom(V, w, h, yaw0, pitch, wide=1.18, tall=1.12):
    """Зум окна коляски (V — вершины numpy относительно pivot): в исходном ракурсе yaw0 модель целиком в окне w×h,
    при любом другом может выйти за окно на wide по ширине и tall по высоте (запас окна это позволяет)."""
    cp, sp = math.cos(pitch), math.sin(pitch)
    scale = h / 1250.0
    ox, oy = w / 2, h * 0.54
    worst = 1e-6
    for i, a in enumerate([yaw0] + [j * math.pi / 8 for j in range(16)]):
        X = V[:, 0] * math.cos(a) + V[:, 2] * math.sin(a)
        Z = -V[:, 0] * math.sin(a) + V[:, 2] * math.cos(a)
        Y = V[:, 1] * cp - Z * sp
        k = 2600.0 / (2600.0 - (V[:, 1] * sp + Z * cp)) * scale
        sx, sy = X * k, -Y * k
        fw, ft = (1.0, 1.0) if i == 0 else (wide, tall)
        worst = max(worst, float(abs(sx).max()) / (ox * fw), float(-sy.min()) / (oy * ft),
                    float(sy.max()) / ((h - oy) * ft))
    tall_mm = float(V[:, 1].max() - V[:, 1].min())             # высокие коляски (X8 1,39 м) — во всё окно,
    real = min(1.0, (tall_mm / M3D_TALL_REF) ** 0.3)            # невысокие ручные — чуть меньше (X3 0,76 м — ~85 %)
    return 0.97 / worst * real


M3D_TALL_REF = 1300.0                   # мм: коляски не ниже этого — во всё окно


def m3d_fit(V, w, h, yaw0, pitch, wide=1.18, tall=1.12):
    """Как m3d_fit_zoom, но ещё подбирает высоту центра (сдвиг pivot по вертикали, мм), чтобы место сверху и
    снизу окна использовалось поровну: у высоких и длинных колясок (X8, Jazzy) низ иначе упирается в край.
    Возврат: (зум, сдвиг)."""
    best = (m3d_fit_zoom(V, w, h, yaw0, pitch, wide, tall), 0.0)
    for dy in range(-400, 401, 20):
        if dy:
            z = m3d_fit_zoom(V - [0.0, dy, 0.0], w, h, yaw0, pitch, wide, tall)
            if z > best[0] + 1e-4:
                best = (z, float(dy))
    return best

# ---- геймпад: те же клавиши, что у управления с клавиатуры (стандартная раскладка SDL, как у Xbox) ----
try:
    from pygame._sdl2 import controller as _pad_ctl
except Exception:
    _pad_ctl = None
PAD = {"ctrl": {}, "joy": {}, "dir": None, "src": None, "next": 0.0}
PAD_BTN_DOWN = getattr(pygame, "CONTROLLERBUTTONDOWN", -1)
ZOOM_IN_KEYS = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)     # «+» и «=» (та же клавиша без Shift)
ZOOM_OUT_KEYS = (pygame.K_MINUS, pygame.K_KP_MINUS)
PAD_EVENTS = tuple(getattr(pygame, n) for n in (
    "CONTROLLERBUTTONDOWN", "CONTROLLERBUTTONUP", "CONTROLLERAXISMOTION", "CONTROLLERDEVICEADDED",
    "CONTROLLERDEVICEREMOVED", "JOYBUTTONDOWN", "JOYBUTTONUP", "JOYHATMOTION", "JOYAXISMOTION",
    "JOYDEVICEADDED", "JOYDEVICEREMOVED") if hasattr(pygame, n))
PAD_REPEAT = (0.42, 0.13)               # удержание крестовины/стика: первый повтор, потом каждые
# кнопки: A — выбрать, B — назад, X — подсказка, Y — где я, LB/RB — группы, Start — настройки, Back — справка
_PAD_BTN = {}
if _pad_ctl is not None:
    _PAD_BTN = {pygame.CONTROLLER_BUTTON_A: "a", pygame.CONTROLLER_BUTTON_B: "b", pygame.CONTROLLER_BUTTON_X: "x",
                pygame.CONTROLLER_BUTTON_Y: "y", pygame.CONTROLLER_BUTTON_LEFTSHOULDER: "lb",
                pygame.CONTROLLER_BUTTON_RIGHTSHOULDER: "rb", pygame.CONTROLLER_BUTTON_START: "start",
                pygame.CONTROLLER_BUTTON_BACK: "back", pygame.CONTROLLER_BUTTON_DPAD_UP: "up",
                pygame.CONTROLLER_BUTTON_DPAD_DOWN: "down", pygame.CONTROLLER_BUTTON_DPAD_LEFT: "left",
                pygame.CONTROLLER_BUTTON_DPAD_RIGHT: "right"}
# простой джойстик без раскладки SDL: XInput (компьютер) / стандарт W3C Gamepad (браузер)
_JOY_BTN = ({0: "a", 1: "b", 2: "x", 3: "y", 4: "lb", 5: "rb", 8: "back", 9: "start",
             12: "up", 13: "down", 14: "left", 15: "right"} if sys.platform == "emscripten" else
            {0: "a", 1: "b", 2: "x", 3: "y", 4: "lb", 5: "rb", 6: "back", 7: "start"})
_PAD_DIR = {"up": pygame.K_UP, "down": pygame.K_DOWN, "left": pygame.K_LEFT, "right": pygame.K_RIGHT}


def pad_open(index):
    """Открыть геймпад/джойстик (при запуске и при подключении). True — геймпад с раскладкой SDL."""
    try:
        if _pad_ctl is not None and _pad_ctl.is_controller(index):
            c = _pad_ctl.Controller(index)
            PAD["ctrl"][c.as_joystick().get_instance_id()] = c
            return True
        j = pygame.joystick.Joystick(index)
        PAD["joy"][j.get_instance_id()] = j
    except Exception:
        pass
    return False


def pad_init():
    try:
        if _pad_ctl is not None:
            _pad_ctl.init()
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            pad_open(i)
    except Exception:
        pass


def pad_actions(event):
    """Событие геймпада -> список (действие, нажато?) или None — событие не про геймпад."""
    t = event.type
    if t not in PAD_EVENTS:
        return None
    iid = getattr(event, "instance_id", None)
    C = pygame
    if t in (getattr(C, "CONTROLLERBUTTONDOWN", -1), getattr(C, "CONTROLLERBUTTONUP", -1)):
        a = _PAD_BTN.get(event.button)
        return [(a, t == C.CONTROLLERBUTTONDOWN)] if a else []
    if t == getattr(C, "CONTROLLERAXISMOTION", -1):
        if event.axis not in (C.CONTROLLER_AXIS_LEFTX, C.CONTROLLER_AXIS_LEFTY):
            return []
        v = event.value / 32767.0
        neg, pos = ("left", "right") if event.axis == C.CONTROLLER_AXIS_LEFTX else ("up", "down")
        return _pad_stick(v, neg, pos)
    if iid in PAD["ctrl"]:
        return []                                       # тот же геймпад шлёт и JOY-события — их не берём
    if t in (C.JOYBUTTONDOWN, C.JOYBUTTONUP):
        a = _JOY_BTN.get(event.button)
        return [(a, t == C.JOYBUTTONDOWN)] if a else []
    if t == C.JOYHATMOTION:
        x, y = event.value
        out = [(d, False) for d in ("up", "down", "left", "right")]
        if y > 0: out.append(("up", True))
        elif y < 0: out.append(("down", True))
        elif x < 0: out.append(("left", True))
        elif x > 0: out.append(("right", True))
        return out
    if t == C.JOYAXISMOTION:
        if event.axis not in (0, 1):
            return []
        return _pad_stick(event.value, *(("left", "right") if event.axis == 0 else ("up", "down")))
    if t in (getattr(C, "CONTROLLERDEVICEADDED", -1), C.JOYDEVICEADDED):
        idx = getattr(event, "device_index", None)
        known = len(PAD["ctrl"]) + len(PAD["joy"])
        if idx is not None:
            pad_open(idx)
        return [("added", True)] if len(PAD["ctrl"]) + len(PAD["joy"]) > known else []
    if t in (getattr(C, "CONTROLLERDEVICEREMOVED", -1), C.JOYDEVICEREMOVED):
        PAD["ctrl"].pop(iid, None)
        PAD["joy"].pop(iid, None)
        PAD["dir"] = None
        return []
    return []


def _pad_stick(v, neg, pos):
    """Стик как крестовина: дальше половины — направление (с повтором), ближе трети — отпущен."""
    if v <= -0.5:
        return [(neg, True)] if PAD["dir"] != neg else []
    if v >= 0.5:
        return [(pos, True)] if PAD["dir"] != pos else []
    if abs(v) < 0.33 and PAD["dir"] in (neg, pos):
        return [(PAD["dir"], False)]
    return []


def _draw_book_icon(surf, center, r, col):
    """Маленькая открытая книжка (сноска из мануала): две страницы и корешок."""
    cx, cy = center
    for d in (-1, 1):
        DR.polygon(surf, col, [(cx, cy - r * 0.55), (cx + d * r, cy - r * 0.8), (cx + d * r, cy + r * 0.6),
                               (cx, cy + r * 0.85)], 2)
    DR.line(surf, col, (cx, cy - r * 0.55), (cx, cy + r * 0.85), 2)


def mouse_pos():
    """Мышь в логических координатах 1280x720 (на сенсорном экране — где последнее касание)."""
    if FINGER["pos"] is not None and pygame.time.get_ticks() - FINGER["t"] < 60000:
        return FINGER["pos"]
    return window_to_logical(pygame.mouse.get_pos())


def finger_events(event, batch_has_finger=False):
    """Касание пальцем -> события мыши в логических координатах (клик ровно там, куда коснулись; протянуть —
    как тянуть мышью). Мышиные события, которые браузер и SDL сами делают из касания, отбрасываются — у них
    бывает устаревшее место. Возврат: список событий для игры или None (событие не про касания)."""
    t = pygame.time.get_ticks()
    if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
        surf = pygame.display.get_surface()
        sw, sh = surf.get_size() if surf else (WIDTH, HEIGHT)
        lp = window_to_logical((event.x * sw, event.y * sh))
        FINGER["t"] = t
        E = pygame.event.Event
        if event.type == pygame.FINGERDOWN:
            if FINGER["id"] is not None and FINGER["id"] != event.finger_id:
                return []                                   # второй палец — не щёлкает
            FINGER["id"], FINGER["pos"] = event.finger_id, lp
            return [E(pygame.MOUSEMOTION, pos=lp, rel=(0, 0), buttons=(0, 0, 0), touch=True),
                    E(pygame.MOUSEBUTTONDOWN, pos=lp, button=1, touch=True)]
        if event.finger_id != FINGER["id"]:
            return []
        old = FINGER["pos"] or lp
        FINGER["pos"] = lp
        if event.type == pygame.FINGERMOTION:
            return [E(pygame.MOUSEMOTION, pos=lp, rel=(lp[0] - old[0], lp[1] - old[1]), buttons=(1, 0, 0), touch=True)]
        FINGER["id"] = None
        return [E(pygame.MOUSEBUTTONUP, pos=lp, button=1, touch=True)]
    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
        if getattr(event, "touch", False) or batch_has_finger or t - FINGER["t"] < 700:
            return []                                       # «мышь», сделанная из касания (браузер шлёт её ДО пальца)
        if event.type != pygame.MOUSEWHEEL:
            FINGER["pos"] = None                            # настоящая мышь — снова её место
    return None


def pick_render_scale():
    """Масштаб рендера по монитору: 1080p -> 1.5, 1440p и выше -> 2 (больше — дорого для pygame)."""
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except Exception:
        return 1.0
    return max(1.0, min(2.0, math.floor(min(dw / WIDTH, dh / HEIGHT) * 4) / 4))


# --- сглаженные примитивы (рисуются в пикселях экрана) ---
try:
    from pygame import gfxdraw as _gfx
except Exception:                       # без gfxdraw — обычные примитивы
    _gfx = None
_AA_CACHE = {}


def _aa_cached(key, size, draw):
    """Рисуем в 2–4 раза крупнее и сглаженно уменьшаем; результат кэшируется (статичные рамки — бесплатно)."""
    img = _AA_CACHE.get(key)
    if img is None:
        k = 4 if size[0] * size[1] < 120000 else 2
        big = pygame.Surface((size[0] * k, size[1] * k), pygame.SRCALPHA)
        draw(big, k)
        img = pygame.transform.smoothscale(big, size)
        if len(_AA_CACHE) > 800:
            _AA_CACHE.clear()
        _AA_CACHE[key] = img
    return img


def aa_rect(surf, color, rect, width=0, border_radius=0, **kw):
    """Прямоугольник со сглаженными скруглёнными углами (логические координаты)."""
    r = pygame.Rect(rect)
    if r.w <= 0 or r.h <= 0 or border_radius <= 0 or kw:
        return DR.rect(surf, color, r, width, border_radius, **kw)
    k = _rs(surf)
    rr, wd = _rr(r, k), _w(width, k)
    col = tuple(int(c) for c in color)
    col = col if len(col) == 4 else (*col, 255)
    rad = min(round(border_radius * k), rr.w // 2, rr.h // 2)
    base = (*col[:3], 255)
    img = _aa_cached(("rr", rr.w, rr.h, base, wd, rad), rr.size,
                     lambda b, s: pygame.draw.rect(b, base, b.get_rect(), wd * s, border_radius=rad * s))
    if col[3] < 255:
        img.set_alpha(col[3])
        pygame.Surface.blit(surf, img, rr.topleft)
        img.set_alpha(255)
    else:
        pygame.Surface.blit(surf, img, rr.topleft)
    return r


def aa_circle(surf, color, center, radius, width=0, **kw):
    """Круг со сглаживанием: заливка/тонкое кольцо — gfxdraw, толстое кольцо — супер-сэмплинг."""
    k = _rs(surf)
    x, y, r = int(round(center[0] * k)), int(round(center[1] * k)), int(round(radius * k))
    wd = _w(width, k)
    if r <= 0 or kw:
        return DR.circle(surf, color, center, radius, width, **kw)
    col = tuple(int(c) for c in color)
    if _gfx is None and r > 1:                 # нет gfxdraw — всё сглаживаем супер-сэмплингом
        col4 = col if len(col) == 4 else (*col, 255)
        wd = 0 if wd >= r else wd
        img = _aa_cached(("ring", r, col4, wd), (2 * r + 2, 2 * r + 2),
                         lambda b, s: pygame.draw.circle(b, col4, ((r + 1) * s, (r + 1) * s), r * s, wd * s))
        pygame.Surface.blit(surf, img, (x - r - 1, y - r - 1))
    elif _gfx is None:
        return DR.circle(surf, color, center, radius, width)
    elif wd <= 0 or wd >= r:
        _gfx.filled_circle(surf, x, y, r, col)
        _gfx.aacircle(surf, x, y, r, col)
    elif wd <= 1:
        _gfx.aacircle(surf, x, y, r, col)
    else:
        col4 = col if len(col) == 4 else (*col, 255)
        img = _aa_cached(("ring", r, col4, wd), (2 * r + 2, 2 * r + 2),
                         lambda b, s: pygame.draw.circle(b, col4, ((r + 1) * s, (r + 1) * s), r * s, wd * s))
        pygame.Surface.blit(surf, img, (x - r - 1, y - r - 1))
    return pygame.Rect(int(center[0] - radius), int(center[1] - radius), int(2 * radius), int(2 * radius))

# ----------------------------------------------------------------------------- #
#  Шрифты / текст
# ----------------------------------------------------------------------------- #
_font_cache = {}


# ----------------------------------------------------------------------------- #
#  Язык: русский (исходный) / английский. Код и данные остаются на русском —
#  перевод подставляется на выводе (draw_text/draw_wrapped/wrap_lines), поэтому
#  логика заданий не зависит от языка. Словарь: assets/lang_en.json
#  (ключ — русская строка; строки с {0},{1}… — шаблоны f-строк).
# ----------------------------------------------------------------------------- #
LANG = {"code": "ru"}
_CYR = re.compile(r"[А-Яа-яЁё]")
_TR, _TR_FMT, _TR_PARTS, _tr_cache = {}, [], [], {}


def load_lang():
    path = os.path.join(ASSETS_DIR, "lang_en.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    _TR.clear(); _TR_FMT.clear(); _TR_PARTS.clear(); _tr_cache.clear()
    for ru, en in data.items():
        if re.search(r"\{\d+\}", ru):
            pat, order = "", []
            for piece in re.split(r"(\{\d+\})", ru):
                m = re.fullmatch(r"\{(\d+)\}", piece)
                if m:
                    pat += "(.*?)"
                    order.append(int(m.group(1)))
                else:
                    pat += re.escape(piece.replace("{{", "{").replace("}}", "}"))
            _TR_FMT.append((re.compile("^" + pat + "$", re.S), order, en,
                            re.compile(pat, re.S) if len(re.sub(r"\{\d+\}", "", ru)) >= 6 else None))
        else:
            _TR[ru] = en
            if len(ru) >= 2:
                _TR_PARTS.append((ru, en))
    _TR_PARTS.sort(key=lambda p: -len(p[0]))
    _TR_FMT.sort(key=lambda t: -len(re.sub(r"\(\.\*\?\)|\\", "", t[0].pattern)))   # точный шаблон раньше общего («{0} см»)
    return True


def _fill(m, order, en):
    vals = {idx: tr(m.group(i + 1)) for i, idx in enumerate(order)}
    try:
        return en.format(*[vals.get(i, "") for i in range(max(order) + 1)])
    except Exception:
        return None


def tr(s):
    """Перевод строки для вывода на экран (в режиме ru — без изменений)."""
    if LANG["code"] == "ru" or not s or not _CYR.search(s):
        return s
    hit = _tr_cache.get(s)
    if hit is not None:
        return hit
    out = _TR.get(s)
    if out is None:
        for rx, order, en, _ in _TR_FMT:
            m = rx.match(s)
            if m:
                out = _fill(m, order, en)
                if out is not None:
                    break
    if out is None:                               # шаблон внутри склейки: «✔ » + f"…"
        for rx, order, en, rx_in in _TR_FMT:
            m = rx_in.search(s) if rx_in else None
            if m and m.end() > m.start():
                filled = _fill(m, order, en)
                if filled is not None:
                    out = tr(s[:m.start()] + filled + s[m.end():])
                    break
    if out is None:                               # склеенные строки: переводим известные куски
        out = s
        for ru, en in _TR_PARTS:
            if ru in out:
                if len(ru) < 4:                   # короткое («мм», «В») — только целым словом
                    out = re.sub(r"(?<![А-Яа-яЁё])" + re.escape(ru) + r"(?![А-Яа-яЁё])", en, out)
                else:
                    out = out.replace(ru, en)
                if not _CYR.search(out):
                    break
    _tr_cache[s] = out
    return out


def set_lang(code):
    code = str(code).lower()
    LANG["code"] = code if code in ("ru", "en") else "en"      # неизвестный язык — английский (аудитория игры)
    if LANG["code"] == "en" and not _TR:
        load_lang()
    _tool_icon_cache.clear()
    if A11Y.get("font"):                                       # лёгкий шрифт — только в английском: шрифты заново
        _font_cache.clear()
    try:
        pygame.display.set_caption(tr("Колёса и Кости") if LANG["code"] == "en" else "Колёса и Кости // Wheels & Bones")
    except Exception:
        pass


def system_reduced_motion():
    """В системе выключены анимации: браузер — prefers-reduced-motion, Windows — «Анимация в Windows» выкл."""
    if IS_WEB:
        return bool(web_js("window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches"))
    if sys.platform == "win32":
        try:
            import ctypes
            v = ctypes.c_int(1)
            if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(v), 0):   # SPI_GETCLIENTAREAANIMATION
                return not v.value
        except Exception:
            pass
    return False


def system_lang():
    """Язык по умолчанию — по системе (русская Windows → ru, иначе en)."""
    try:
        import locale
        loc = (locale.getlocale()[0] or "") + " " + (os.environ.get("LANG") or "")
        if "ru" in loc.lower() or "russian" in loc.lower():
            return "ru"
        if sys.platform == "win32":
            import ctypes
            return "ru" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF == 0x19 else "en"
    except Exception:
        return "ru"
    return "en"


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = LFont(size, bold)
    return _font_cache[key]


# ---- Доступность: что нарисовано в кадре — для управления с клавиатуры и чтения вслух ----
A11Y = dict(on=False, voices=True, rate=0, contrast=False, instant=False, speech_set=False,
            text=2 if IS_WEB else 0, text_set=False,
            calm=False, calm_set=False, scan=0, font=False,
            barty=True, quiet=False, quiet_set=False)       # scan — одна кнопка: 0 выкл, 1–3 — скорость (SCAN_SPEEDS)                 # calm — без анимации (по умолчанию — как в системе)   # text — размер текста (TEXT_K): в браузере окно мельче —
                                                         # сразу 125 %; text_set — игрок выбрал размер сам
TEXT_K = (1.0, 1.12, 1.25)
# Кабинет посадки, «Рентген»: тело клиента сбоку поверх скелета (по позе, см). bulk — телосложение,
# top/legs/shoes — одежда, head — голова (радиус, см), extras — приметы. Голову можно заменить картинкой
# assets/seat_head_<id>.png (профиль, смотрит вправо, по центру — центр головы) — тогда рисуется она.
SEAT_BODY = {
    "client_troll.png": dict(bulk=1.35, belly=1.5, head=12.5, top=(132, 96, 62), legs=(86, 84, 104),
                             shoes=(70, 52, 40), extras=("big_nose", "small_ears", "brow")),
    "client_elf.png": dict(bulk=0.82, head=9.5, top=(70, 140, 92), legs=(96, 80, 60), shoes=(110, 80, 50),
                           hair=(236, 206, 120), extras=("elf_ear", "long_hair")),
    "client_fairy.png": dict(bulk=0.78, head=9.0, top=(240, 168, 200), legs=None, shoes=(230, 150, 190),
                             hair=(240, 140, 180), extras=("wings", "bob_hair", "flower")),
    "client_golem.png": dict(bulk=1.45, head=12.0, top=None, legs=None, shoes=None, blocky=True,
                             extras=("cracks", "glow_eye")),
    "client_aeroz.png": dict(bulk=0.9, head=9.5, top=(236, 236, 244), legs=(200, 60, 70), shoes=(60, 50, 50),
                             extras=("fox_ears", "fox_tail", "snout_s")),
    "client_iris.png": dict(bulk=0.9, head=10.0, top=None, legs=None, shoes=None, belly=1.15,
                            extras=("snout_d", "horns", "dragon_tail", "belly_scales")),
}
SCAN_SPEEDS = (1.0, 1.6, 2.5)          # одна кнопка: секунд на пункт
SCAN_HOLD = 1.2                        # держать кнопку столько — «назад» (Esc)
SCAN_SUB = ("Меньше", "Больше", "Готово")   # ползунок в режиме одной кнопки
CAPTURE = dict(frame=None, texts=[], buttons=[], modal=None, mute=0)


def _cap_text(surf, text, rect):
    if surf is CAPTURE["frame"] and not CAPTURE["mute"] and text and str(text).strip():
        CAPTURE["texts"].append((pygame.Rect(rect), str(text)))


def _cap_modal():
    """Начался модальный оверлей: с клавиатуры доступно только то, что нарисовано дальше."""
    CAPTURE["modal"] = (len(CAPTURE["texts"]), len(CAPTURE["buttons"]))


TEXT_PLATE = (14, 12, 20, 175)                       # тёмная подложка под текст на пёстром фоне


def _plate(surf, rect):
    aa_rect(surf, TEXT_PLATE, pygame.Rect(rect).inflate(16, 8), border_radius=8)


def draw_text(surf, text, pos, size=18, color=WHITE, bold=False, center=False, right=False, alpha=255, plate=False):
    s_ = tr(str(text))
    img = font(size, bold).render(s_, True, color)
    if alpha < 255:
        img.set_alpha(max(0, int(alpha)))
    rect = img.get_rect()
    if center:
        rect.center = pos
    elif right:
        rect.topright = pos
    else:
        rect.topleft = pos
    if plate:
        _plate(surf, rect)
    surf.blit(img, rect)
    _cap_text(surf, s_, rect)
    return rect


def fit_text(surf, text, pos, width, size=18, color=WHITE, bold=False):
    """Строка в заданную ширину: уменьшаем шрифт (до 75%), иначе обрезаем с «…»."""
    text = tr(str(text))
    _cap_text(surf, text, pygame.Rect(pos, (width, size + 4)))
    sz = size
    while sz > int(size * 0.75) and font(sz, bold).size(text)[0] > width:
        sz -= 1
    f = font(sz, bold)
    if f.size(text)[0] > width:
        while text and f.size(text + "…")[0] > width:
            text = text[:-1]
        text = text.rstrip() + "…"
    CAPTURE["mute"] += 1
    try:
        return draw_text(surf, text, (pos[0], pos[1] + (size - sz) // 2), sz, color, bold)
    finally:
        CAPTURE["mute"] -= 1


def wrap_lines(text, width, size=16, raw=False):
    """raw=True — текст игрока (комментарий): без перевода."""
    text = text if raw else tr(text)
    f = font(size)
    out, cur = [], ""
    for w in text.split(" "):
        test = (cur + " " + w).strip()
        if f.size(test)[0] <= width:
            cur = test
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def draw_wrapped(surf, text, pos, width, size=16, color=WHITE, center=False, line_gap=2,
                 limit=None, alpha=255, max_lines=None, raw=False, plate=False):
    """limit — сколько символов показать («печать по буквам»): переносы считаются по
    полному тексту, поэтому слова не прыгают между строками во время печати.
    plate — тёмная подложка под всем блоком (текст на пёстром фоне)."""
    x, y = pos
    f = font(size)
    text = text if raw else tr(text)
    _cap_text(surf, text, pygame.Rect(x - (width // 2 if center else 0), y, width, size + 4))
    left = len(text) if limit is None else limit
    lines = wrap_lines(text, width, size, raw=True)
    if plate and lines:
        shown = lines[:max_lines] if max_lines else lines
        bw = max(f.size(ln)[0] for ln in shown)
        bh = len(shown) * (f.get_height() + line_gap) - line_gap
        _plate(surf, pygame.Rect(x - bw // 2 if center else x, y, bw, bh))
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and f.size(last + "…")[0] > width:
            last = last[:-1]
        lines[-1] = last.rstrip(" ,.;:—") + "…"
    for ln in lines:
        r = pygame.Rect((0, 0), f.size(ln))
        if center:
            r.midtop = (x, y)
        else:
            r.topleft = (x, y)
        if left > 0:
            img = f.render(ln, True, color)
            if alpha < 255:
                img.set_alpha(max(0, int(alpha)))
            if left < len(ln):                              # печать по буквам: видна только начальная часть строки
                surf.blit(img, r.topleft, pygame.Rect(0, 0, f.size(ln[:left])[0], f.get_height()))
            else:
                surf.blit(img, r.topleft)
        left -= len(ln) + 1
        y += f.get_height() + line_gap
    return y


# ----------------------------------------------------------------------------- #
#  Анимация: изинги, свечение, «живые» спрайты и частицы фонов.
#  Всё без состояния — считается из времени t, поэтому одинаково в игре и в
#  headless-рендере, и ничего не нужно обновлять в update().
# ----------------------------------------------------------------------------- #
def clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def calm():
    """«Без анимации» (Доступность): появления сразу на месте, ничего не качается, не мерцает и не летит."""
    return A11Y.get("calm", False)


def barty_on():
    """Призрак Барти в мастерской (портрет, пузырь с шутками) — можно убрать в «Доступности»."""
    return A11Y.get("barty", True)


def quiet_talk():
    """Клиент говорит одну фразу при входе, без болтовни и реакций; по умолчанию — вместе с «Без анимации»."""
    return A11Y.get("quiet", False) if A11Y.get("quiet_set") else calm()


def wsin(x):
    """Колебание для украшений (дыхание, пульс, покачивание); без анимации — покой."""
    return 0.0 if A11Y.get("calm") else math.sin(x)


def ease_out(x):
    if A11Y.get("calm"):
        return 1.0
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_back(x, s=1.70158):
    """С лёгким перелётом — для «выпрыгивающих» элементов."""
    if A11Y.get("calm"):
        return 1.0
    x = clamp01(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def appear(st, delay=0.0, dur=0.45):
    return ease_out((st - delay) / dur)


def _h01(i, k=0):
    """Детерминированное «случайное» 0..1 для частицы i."""
    v = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return v - math.floor(v)


_glow_cache = {}


def add_glow(surf, pos, radius, color, level=1.0):
    """Мягкое аддитивное свечение (светлячки, искры, луч света). Выключается в настройках («Свечение»)."""
    if not DISPLAY["glow"]:
        return
    q = max(0, min(8, int(level * 8 + 0.5)))
    if q == 0 or radius < 1:
        return
    key = (radius, color, q)
    g = _glow_cache.get(key)
    if g is None:
        g = Surf((radius * 2, radius * 2))
        for r in range(radius, 0, -1):
            k = (1 - r / radius) ** 2 * q / 8
            aa_circle(g, (int(color[0] * k), int(color[1] * k), int(color[2] * k)),
                               (radius, radius), r)
        _glow_cache[key] = g
    surf.blit(g, (int(pos[0]) - radius, int(pos[1]) - radius), special_flags=pygame.BLEND_RGB_ADD)


def blit_idle(surf, img, pos, t, mode="breathe", phase=0.0, k=1.0, rock=0.0):
    """«Живой» спрайт вместо статичного blit (pos — левый верхний угол, как у blit).
    breathe — дышит верх (торс), низ с коляской стоит на месте; float — парит
    (призраки); k — масштаб появления; rock — покачивание в градусах (танец)."""
    w, h = img.get_size()
    if mode == "float":
        dy = 7 * wsin(t * 1.6 + phase)
        ang = 2.5 * wsin(t * 1.1 + phase) + rock
        out = TF.rotozoom(img, ang, k) if (ang or k != 1) else img
        surf.blit(out, out.get_rect(center=(pos[0] + w // 2, pos[1] + h // 2 + dy)))
        return
    if k != 1 or rock:
        img = TF.rotozoom(img, rock, k)
        surf.blit(img, img.get_rect(midbottom=(pos[0] + w // 2, pos[1] + h)))
        return
    sy = 1 + 0.014 * wsin(t * 2.1 + phase)
    if sy == 1:                                       # без анимации: обычный кадр
        surf.blit(img, pos)
        return
    if not (isinstance(surf, Surf) and isinstance(img, Surf)):      # запасной путь (обычные поверхности)
        cut = int(h * 0.55)
        surf.blit(img, (pos[0], pos[1] + cut), pygame.Rect(0, cut, w, h - cut))
        th = int(cut * sy)
        surf.blit(TF.smoothscale(img.subsurface((0, 0, w, cut)), (w, th)), (pos[0], pos[1] + cut - th))
        return
    # Всё — в пикселях экрана (без округления логических координат). Верх (торс) берётся с запасом ov строк
    # ниже разреза, растягивается и встаёт нижним краем ровно на целую строку — без сдвига на полпикселя;
    # последние ov строк верха плавно растворяются (градиент прозрачности) поверх неподвижного низа — стыка нет.
    RW, RH = pygame.Surface.get_size(img)
    px, py = round(pos[0] * RS), round(pos[1] * RS)
    cut = int(RH * 0.55)
    ov = max(4, RH // 30)
    top_h = min(RH, cut + ov)
    th = max(1, round(top_h * sy))
    pygame.Surface.blit(surf, img, (px, py + cut), pygame.Rect(0, cut, RW, RH - cut))
    top = pygame.transform.smoothscale(pygame.Surface.subsurface(img, (0, 0, RW, top_h)), (RW, th))
    band = min(ov, th)
    key = ("seam_ramp", RW, band)
    ramp = _img_cache.get(key)
    if ramp is None:
        ramp = pygame.Surface((RW, band), pygame.SRCALPHA)
        for i in range(band):
            pygame.Surface.fill(ramp, (255, 255, 255, int(255 * (1 - (i + 0.5) / band))), (0, i, RW, 1))
        _img_cache[key] = ramp
    pygame.Surface.blit(top, ramp, (0, th - band), None, pygame.BLEND_RGBA_MULT)
    pygame.Surface.blit(surf, top, (px, py + top_h - th))


def draw_spin_wheel(surf, center, r, ang, k=1.0, col=(205, 210, 225)):
    """Вращающееся колесо коляски (для титула): шина, обод, спицы, ступица."""
    if k <= 0.01:
        return
    if calm():
        ang = 0.3
    R = max(4, int(r * k))
    S = R * 2 + 8
    big = Surf((S * 2, S * 2), pygame.SRCALPHA)
    c = (S, S)
    aa_circle(big, (40, 40, 48), c, R * 2, max(2, R // 4))
    aa_circle(big, col, c, int(R * 1.62), max(2, R // 12))
    for i in range(12):
        a = ang + i * math.pi / 6
        DR.line(big, col, c, (S + R * 1.6 * math.cos(a), S + R * 1.6 * math.sin(a)), max(1, R // 18))
    aa_circle(big, col, c, max(3, R // 4))
    aa_circle(big, (90, 90, 100), c, max(2, R // 10))
    surf.blit(TF.smoothscale(big, (S, S)), (center[0] - S // 2, center[1] - S // 2))


def draw_confetti(surf, t, n=80, top=-20, height=780):
    if calm() or not DISPLAY["glow"]:                  # конфетти — частицы: выключаются «Свечением и частицами»
        return
    pal = [(240, 190, 90), (120, 210, 160), (230, 120, 170), (120, 180, 240), (250, 240, 170)]
    for i in range(n):
        sp = 60 + 70 * _h01(i, 1)
        x = WIDTH * _h01(i, 2) + 40 * math.sin(t * (0.8 + _h01(i, 3)) + i)
        y = top + (t * sp + height * _h01(i, 4)) % height
        a = t * (2 + 3 * _h01(i, 5)) + i
        w, h = 7, 3 + 4 * abs(math.sin(a))
        ca, sa = math.cos(a * 0.7), math.sin(a * 0.7)
        pts = [(x + dx * ca - dy * sa, y + dx * sa + dy * ca)
               for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
        DR.polygon(surf, pal[i % len(pal)], pts)


def draw_burst(surf, center, ph, color=(255, 210, 90), n=10, dist=70):
    """Вспышка искр (ph 0..1) — для звёзд и успехов."""
    if not 0 < ph < 1 or calm():
        return
    for i in range(n):
        a = i * 2 * math.pi / n + 0.3
        d = dist * ease_out(ph)
        add_glow(surf, (center[0] + d * math.cos(a), center[1] + d * math.sin(a)), 8, color, 1 - ph)


def draw_ambient(surf, name, t):
    """Частицы поверх фона: у каждой сцены своя жизнь."""
    if not DISPLAY["glow"] or calm():
        return
    if name == "bg_workshop.png":            # луч из круглого окна и пылинки в нём
        add_glow(surf, (150, 170), 200, (70, 55, 28), 0.6 + 0.15 * math.sin(t * 0.7))
        for i in range(34):
            sp = 6 + 10 * _h01(i, 1)
            x = 40 + 420 * _h01(i, 2) + 30 * math.sin(t * 0.3 + i)
            y = 560 - ((t * sp + 600 * _h01(i, 3)) % 540)
            tw = 0.5 + 0.5 * math.sin(t * 2 + i * 1.7)
            add_glow(surf, (x, y), 5, (255, 230, 170), 0.3 + 0.5 * tw)
    elif name == "bg_road.png":              # светлячки и сияние луны
        add_glow(surf, (480, 104), 110, (40, 50, 75), 0.55 + 0.1 * math.sin(t * 0.5))
        for i in range(26):
            x = WIDTH * _h01(i, 1) + 45 * math.sin(t * (0.3 + 0.4 * _h01(i, 3)) + i)
            y = 300 + 380 * _h01(i, 2) + 25 * math.sin(t * (0.5 + 0.5 * _h01(i, 4)) + i * 2)
            p = 0.5 + 0.5 * math.sin(t * (1.5 + 2 * _h01(i, 5)) + i * 3)
            add_glow(surf, (x, y), 14, (190, 255, 110), 0.1 + 0.9 * p * p)
    elif name == "bg_guild.png":             # жар горна и искры
        fx, fy = 636, 300
        add_glow(surf, (fx, fy), 160, (95, 45, 10), 0.55 + 0.25 * math.sin(t * 3.1) * math.sin(t * 1.7))
        for i in range(24):
            life = 2.0 + _h01(i, 1)
            ph = ((t + life * _h01(i, 2)) % life) / life
            x = fx - 45 + 90 * _h01(i, 3) + 25 * math.sin(t * 2 + i) * ph
            add_glow(surf, (x, fy + 10 - ph * 270), 6, (255, 150, 50), (1 - ph) * 0.95)
    elif name == "bg_party.png":             # мерцание в небе и летящие огоньки
        for i in range(30):
            p = max(0.0, math.sin(t * (1 + 2 * _h01(i, 3)) + i * 5))
            add_glow(surf, (WIDTH * _h01(i, 1), 20 + 200 * _h01(i, 2)), 7, (255, 255, 220), p ** 3)
        for i in range(18):
            x = WIDTH * _h01(i, 4) + 30 * math.sin(t * 0.4 + i)
            y = HEIGHT - ((t * (12 + 10 * _h01(i, 5)) + 720 * _h01(i, 6)) % 560)
            add_glow(surf, (x, y), 10, (255, 170, 215), 0.45)
    elif name == "bg_garage.png":            # мерцающая лампа и пыль
        add_glow(surf, (270, 80), 120, (85, 62, 25), 0.7 + 0.12 * math.sin(t * 7.3) * math.sin(t * 3.1))
        for i in range(24):
            x = 200 + 900 * _h01(i, 2) + 25 * math.sin(t * 0.3 + i)
            y = 600 - ((t * (5 + 8 * _h01(i, 1)) + 500 * _h01(i, 3)) % 480)
            add_glow(surf, (x, y), 4, (255, 225, 170), 0.35 + 0.3 * math.sin(t * 2 + i))



# ----------------------------------------------------------------------------- #
#  Загрузка ассетов с заглушками
# ----------------------------------------------------------------------------- #
_img_cache = {}


def _placeholder(size, color, label):
    w, h = size
    surf = Surf(size, pygame.SRCALPHA)
    surf.fill((30, 28, 38, 255))
    grid = (color[0] // 6, color[1] // 6, color[2] // 6)
    for gx in range(0, w, 18):
        DR.line(surf, grid, (gx, 0), (gx, h))
    for gy in range(0, h, 18):
        DR.line(surf, grid, (0, gy), (w, gy))
    DR.rect(surf, color, surf.get_rect(), 2)
    name = os.path.splitext(os.path.basename(label))[0]
    f = font(max(11, min(20, w // 12)))
    surf.blit(f.render(name, True, color), f.render(name, True, color).get_rect(center=(w // 2, h // 2)))
    return surf


def _fit(surf, size):
    """Вписать surface в size с сохранением пропорций (прозрачные поля)."""
    w, h = surf.get_size()
    W, H = size
    k = min(W / w, H / h)
    img = TF.smoothscale(surf, (max(1, int(w * k)), max(1, int(h * k))))
    out = Surf(size, pygame.SRCALPHA)
    out.blit(img, img.get_rect(center=(W // 2, H // 2)))
    return out


def asset_path(name):
    """Путь к картинке из assets; браузерная сборка хранит крупные PNG как .jpg (у рисунков с прозрачностью —
    ещё <имя>.a.png: прозрачность отдельно, см. build_web.py). None — нет."""
    path = os.path.join(ASSETS_DIR, name)
    if os.path.exists(path):
        return path
    if name.endswith(".png") and os.path.exists(path[:-4] + ".jpg"):
        return path[:-4] + ".jpg"
    return None


def _load_split(jpg, apng):
    """Цвет из JPEG + маска <имя>.a.png (белая, прозрачность — в альфе) -> одна картинка RGBA.
    Умножение каналов делает сам pygame (BLEND_RGBA_MULT): быстро и без копий байтов в Python (телефоны)."""
    rgb = pygame.image.load(jpg).convert_alpha()
    mask = pygame.image.load(apng).convert_alpha()
    if mask.get_size() != rgb.get_size():
        mask = pygame.transform.smoothscale(mask, rgb.get_size())
    rgb.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return rgb


ASSET_MISS = set()                     # картинки, вместо которых нарисована заглушка (проверка web_smoke)


def asset_exists(name):
    return asset_path(name) is not None


def load_image(name, size=None, color=GHOST):
    key = (name, size)
    if key in _img_cache:
        return _img_cache[key]
    path = asset_path(name)
    surf = None
    if path:
        try:
            ap = path[:-4] + ".a.png"
            real = (_load_split(path, ap) if path.endswith(".jpg") and os.path.exists(ap)
                    else pygame.image.load(path)).convert_alpha()
            L = tuple(size) if size else real.get_size()
            if size or RS != 1:                 # вписать в логический размер — сразу в пикселях экрана
                k = min(L[0] * RS / real.get_width(), L[1] * RS / real.get_height())
                img = pygame.transform.smoothscale(real, (max(1, round(real.get_width() * k)),
                                                          max(1, round(real.get_height() * k))))
                surf = Surf(L, pygame.SRCALPHA)
                pygame.Surface.blit(surf, img, (round((L[0] * RS - img.get_width()) / 2),
                                                round((L[1] * RS - img.get_height()) / 2)))
            else:
                surf = Surf.adopt(real)
        except Exception:
            surf = None
    if surf is None:
        ASSET_MISS.add(name)
        drawer = VECTOR_ART.get(os.path.splitext(name)[0])
        if drawer:
            surf = drawer()
            if size and surf.get_size() != tuple(size):
                surf = _fit(surf, size)
        else:
            surf = _placeholder(size or (200, 200), color, name)
    _img_cache[key] = surf
    return surf


_tool_icon_cache = {}


def tool_icon(tid, size):
    """Иконка инструмента: assets/tool_<id>.png, иначе — значок с инициалами."""
    key = (tid, size)
    if key not in _tool_icon_cache:
        name = f"tool_{tid}.png"
        if asset_exists(name):
            surf = load_image(name, (size, size))
        else:
            surf = Surf((size, size), pygame.SRCALPHA)
            aa_circle(surf, (60, 56, 74), (size // 2, size // 2), size // 2 - 1)
            aa_circle(surf, AMBER, (size // 2, size // 2), size // 2 - 1, 2)
            label = tr(TOOLS[tid][0])[:2]
            img = font(max(10, size // 3), True).render(label, True, WHITE)
            surf.blit(img, img.get_rect(center=(size // 2, size // 2)))
        _tool_icon_cache[key] = surf
    return _tool_icon_cache[key]


# ----------------------------------------------------------------------------- #
#  Визуализация действий: шутки про ногу Мартина, работа инструментов, тест-драйв
# ----------------------------------------------------------------------------- #
def _art_gag_leg():
    """Векторная заглушка ноги Мартина (если нет assets/gag_leg.png)."""
    s = _S(220, 80)
    aa_rect(s, (150, 196, 140), (6, 26, 40, 30), border_radius=12)       # зелёный «срез»
    DR.line(s, (90, 120, 86), (20, 34), (28, 46), 2)
    aa_rect(s, (74, 104, 150), (36, 22, 120, 38), border_radius=8)       # джинсы
    aa_circle(s, (140, 92, 60), (100, 40), 8)                           # заплатка
    DR.ellipse(s, (118, 78, 48), (146, 18, 70, 46))                     # ботинок
    return s


def draw_leg(surf, center, ang=0.0, scale=1.0):
    img = load_image("gag_leg.png", (170, 70), GHOST)
    img = TF.rotozoom(img, ang, scale)
    surf.blit(img, img.get_rect(center=(int(center[0]), int(center[1]))))


def draw_leg_gag(surf, kind, t, rect):
    """Сценка с ногой в полосе rect; t — время сценки (~4.6 с, один раз — по просьбе игроков, не по кругу)."""
    if calm():
        return
    P = 4.6
    if t < 0 or t >= P:
        return
    u = t
    floor = rect.bottom - 30
    cx = rect.centerx
    if kind == "drop":                       # нога отваливается, скачет, уползает
        if u < 0.55:
            k = u / 0.55
            y = rect.top - 40 + (floor - rect.top + 40) * k * k
            draw_leg(surf, (cx, y), ang=-200 * k)
        elif u < 2.6:
            v = u - 0.55
            h = 70 * abs(math.sin(math.pi * v * 2.2)) * math.exp(-2.6 * v)
            if v < 0.1:
                add_glow(surf, (cx, floor + 18), 30, (90, 80, 60), 0.8)
            draw_leg(surf, (cx, floor - h), ang=12 * math.sin(v * 9) * math.exp(-2 * v))
        else:
            k = ease_out((u - 2.6) / 1.4)
            draw_leg(surf, (cx + k * (rect.w / 2 + 120), floor - 6 * abs(math.sin(u * 14))),
                     ang=8 * math.sin(u * 14))
    elif kind == "peek":                     # нога выглядывает из-под верстака
        bench = pygame.Rect(rect.x, floor - 70, 260, 26)
        aa_rect(surf, (118, 82, 52), bench, border_radius=6)
        DR.rect(surf, (96, 66, 42), (bench.x + 20, bench.bottom, 16, 50))
        DR.rect(surf, (96, 66, 42), (bench.right - 36, bench.bottom, 16, 50))
        out = 90 * clamp01(math.sin(math.pi * clamp01((u - 0.3) / 3.6)) * 1.4)
        draw_leg(surf, (bench.right - 70 + out, floor - 10 + 4 * math.sin(u * 10)), ang=4 * math.sin(u * 7))
        mark = "?" if u < 2.0 else "!"
        draw_text(surf, mark, (bench.right + 40 + int(out), floor - 80 - int(6 * math.sin(u * 5))), 34,
                  AMBER, bold=True, center=True, alpha=255 * clamp01((u - 0.6) / 0.3))
    elif kind == "roll":                     # пустая коляска катится, нога кувыркается следом
        k = u / P
        x = rect.x - 160 + (rect.w + 380) * k
        chair = load_image("chair_basic.png", (130, 103), AMBER)
        surf.blit(chair, (x - 65, floor + 18 - 103 - 2 * abs(math.sin(u * 12))))
        lx = x - 170
        draw_leg(surf, (lx, floor - 14 - 8 * abs(math.sin(u * 6))), ang=-u * 420, scale=0.6)
        for i in range(3):
            add_glow(surf, (x - 70 - i * 18, floor + 14), 10, (70, 62, 50), 0.6 - 0.18 * i)
    elif kind == "hop":                      # нога упрыгивает, Барти смотрит вслед
        k = u / P
        x = rect.x - 100 + (rect.w + 200) * k
        ph = (k * 6) % 1.0
        draw_leg(surf, (x, floor - 22 - 40 * math.sin(math.pi * ph)), ang=-90 + 20 * math.sin(math.pi * ph), scale=0.6)
        if ph < 0.12:
            add_glow(surf, (x, floor + 22), 22, (90, 80, 60), 0.7)


LEG_GAG_KIND = ["drop", "peek", "roll", "hop"]        # сценка к каждой шутке LEG_GAGS

ROT_TOOLS = {"allen", "socket", "wrench", "spoke_key", "screw"}
READ_TOOLS = {"gauge", "multimeter", "tensiometer", "dial", "tape", "eyes"}


ELECTRIC_PARTS = {"battery", "controller", "joystick", "wiring", "motor", "fuse", "breaker", "mag_brake",
                  "seat_cable", "actuator", "brushes", "charger"}


def _bolt_points(a, b, seed, rough=0.22, n=9):
    """Ломаная молнии от a к b; seed меняется несколько раз в секунду — молния «дрожит»."""
    rnd = random.Random(seed)
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    ln = max(1.0, math.hypot(dx, dy))
    nx, ny = -dy / ln, dx / ln
    pts = [a]
    for i in range(1, n):
        k = i / n
        off = (rnd.random() - 0.5) * 2 * rough * ln * (1 - abs(0.5 - k))
        pts.append((x0 + dx * k + nx * off, y0 + dy * k + ny * off))
    pts.append(b)
    return pts


def draw_zap(surf, pos, u, size=1.0):
    """Разряд тока в точке pos (u — 0..1): две-три дрожащие молнии сверху, вспышка и искры."""
    x, y = pos
    if u >= 1 or calm():
        return
    fade = 1 - u
    seed = int(u * 14)                                       # ~14 смен формы за анимацию — мерцание
    for j, (sx, sy) in enumerate(((-55, -95), (40, -100), (-10, -120))[:2 + (size > 1.2)]):
        a = (x + sx * size, y + sy * size)
        pts = _bolt_points(a, (x, y), seed * 7 + j, rough=0.25)
        w = max(2, int(5 * size * fade))
        DR.lines(surf, (120, 190, 255), False, pts, w + 4)   # голубой ореол
        DR.lines(surf, (240, 250, 255), False, pts, max(1, w // 2 + 1))
        if j == 0 and u < 0.6:                               # ветка
            mid = pts[len(pts) // 2]
            br = _bolt_points(mid, (mid[0] + 34 * size, mid[1] + 18 * size), seed * 13 + 5, rough=0.35, n=5)
            DR.lines(surf, (170, 215, 255), False, br, max(1, w // 2))
    if DISPLAY.get("glow", True):
        add_glow(surf, (x, y), int(46 * size), (90, 150, 255), 0.9 * fade)
    rnd = random.Random(seed + 99)
    for i in range(8):                                       # искры
        ang = rnd.random() * 2 * math.pi
        d = (10 + 40 * u) * size * (0.6 + rnd.random() * 0.8)
        px_, py_ = x + d * math.cos(ang), y + d * math.sin(ang) + 30 * u * u * size
        aa_circle(surf, (255, 240, 170) if i % 2 else (190, 225, 255), (int(px_), int(py_)), max(1, int(2.5 * fade * size)))


def draw_tool_action(surf, tid, pos, u, ok=True, zap=False):
    """Инструмент работает на детали: u — 0..1 время анимации."""
    x, y = pos
    if not ok and zap:                       # ошибка с электрикой: разряд, инструмент отбрасывает
        draw_zap(surf, pos, u)
        ic = TF.rotozoom(tool_icon(tid, 40), 60 * u + 25, 1.0)
        ic.set_alpha(int(255 * (1 - u)))
        surf.blit(ic, ic.get_rect(center=(x + 30 + 50 * u, y - 30 - 40 * u)))
        return
    if not ok:                               # ошибка: красный крест и отдёрнутый инструмент
        sh = 10 * math.sin(u * 40) * (1 - u)
        DR.line(surf, BAD, (x - 14 + sh, y - 14), (x + 14 + sh, y + 14), 5)
        DR.line(surf, BAD, (x + 14 + sh, y - 14), (x - 14 + sh, y + 14), 5)
        ic = TF.rotozoom(tool_icon(tid, 40), 25 * (1 - u), 1.0)
        ic.set_alpha(int(255 * (1 - u)))
        surf.blit(ic, ic.get_rect(center=(x + 30, y - 30 - 20 * u)))
        return
    appear_k = ease_back(u / 0.15)
    ang, dx, dy, sc = 0.0, 0.0, 0.0, appear_k
    if tid in ROT_TOOLS:                     # крутим: ключ ходит дугой, вокруг стрелка
        ang = 80 * math.sin(u * math.pi * 3)
        rr = 26
        a1 = -math.pi / 2
        a2 = a1 + 2 * math.pi * min(1.0, u * 1.2)
        if a2 > a1 + 0.1:
            DR.arc(surf, AMBER, (x - rr, y - rr, rr * 2, rr * 2), a1, a2, 3)
    elif tid == "pump":
        dy = -18 * abs(math.sin(u * math.pi * 3))
        if math.sin(u * math.pi * 3) > 0.9:
            add_glow(surf, (x + 24, y + 10), 16, (200, 220, 240), 0.8)
    elif tid == "lever":
        ang = -38 * abs(math.sin(u * math.pi * 2))
        dx = 10
    elif tid == "cloth":
        dx = 22 * math.sin(u * math.pi * 6)
        if u > 0.6:
            for i in range(3):
                add_glow(surf, (x - 20 + i * 20, y - 18 + 10 * math.sin(u * 9 + i)), 8, (255, 255, 230), 1 - u)
    elif tid == "brush":
        dx = 8 * math.sin(u * 60)
        for i in range(5):
            a = i * 1.3 + u * 6
            d = 30 * u
            aa_circle(surf, (140, 110, 80), (int(x + d * math.cos(a)), int(y + d * math.sin(a))), 3)
    elif tid == "lube":
        ang = 40
        for i in range(3):
            dyy = ((u * 3 + i / 3) % 1.0) * 30
            aa_circle(surf, (226, 180, 70), (int(x - 6), int(y + 4 + dyy)), 3)
    elif tid == "patch":
        sc = appear_k * (1.6 - 0.6 * ease_out(u / 0.4))
        if u > 0.4:
            add_glow(surf, (x, y), 30, (120, 200, 140), 1 - (u - 0.4) / 0.6)
    elif tid == "bucket":
        for i in range(6):
            bu = (u * 1.5 + i / 6) % 1.0
            aa_circle(surf, (170, 220, 250), (int(x - 15 + 30 * _h01(i, 7)), int(y - 10 - 40 * bu)), 3 + i % 3, 1)
    elif tid == "pencil":
        dy = -10 * abs(math.sin(u * math.pi * 2))
        rr = int(10 + 40 * ((u * 2) % 1.0))
        aa_circle(surf, CYAN, (int(x), int(y)), rr, 2)
    elif tid in READ_TOOLS:                  # прибор: стрелка покачалась и встала, «норма»
        bw = max(86, font(14, True).size(tr("✔ норма"))[0] + 20)
        bx = x + 24 if x + 24 + bw <= WIDTH - 8 else x - 24 - bw   # у правого края — слева от детали
        bub = pygame.Rect(bx, max(58, y - 54), bw, 26)
        aa_rect(surf, (20, 40, 30), bub, border_radius=8)
        aa_rect(surf, GOOD, bub, 2, border_radius=8)
        draw_text(surf, "✔ норма", bub.center, 14, GOOD, bold=True, center=True, alpha=255 * clamp01((u - 0.3) / 0.2))
        ang = 15 * math.sin(u * 20) * (1 - u)
    elif tid == "charger":
        add_glow(surf, (x, y), 34, (120, 200, 255), 0.5 + 0.5 * math.sin(u * 30))
    else:                                    # руки и прочее: ухватить и потрясти
        dx = 6 * math.sin(u * 30) * (1 - u)
    ic = TF.rotozoom(tool_icon(tid, 46), ang, max(0.01, sc))
    if u > 0.8:
        ic.set_alpha(int(255 * (1 - (u - 0.8) / 0.2)))
    surf.blit(ic, ic.get_rect(center=(int(x + dx), int(y + dy - 4))))


# ----------------------------------------------------------------------------- #
#  Звук: маленький синтезатор (без файлов; флаг --mute и клавиша M отключают).
#  Колокольные обертоны, огибающие, фильтрованный шум, глиссандо, вибрато.
#  Эффекты собираются при старте, фоновые петли — при первом заходе в сцену.
# ----------------------------------------------------------------------------- #
SOUND = {}
SR = 22050
_rng = random.Random(7)
_AMB = {"name": None}
DISPLAY = {"fullscreen": False, "glow": True, "res": None, "screen": None, "frame": None}
# сохраняется в settings.json: fullscreen, glow (свечение и частицы), res (разрешение рендера; None — авто по монитору)
RES_OPTIONS = [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160)]


def web_js(code):
    """Браузер: выполнить JavaScript на странице игры (в настольной версии — ничего)."""
    if not IS_WEB:
        return None
    try:
        import platform as _pf
        return _pf.window.eval(code)
    except Exception:
        return None


def web_restore():
    """Браузер: файлы сохранений живут в localStorage — перед стартом кладём их обратно в память."""
    for path in (SAVE_PATH, SETTINGS_PATH, FEEDBACK_PATH):
        text = web_js(f"localStorage.getItem({json.dumps('wnb:' + os.path.basename(path))})")
        if text:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(str(text))
            except Exception:
                pass


def web_persist(path):
    """Браузер: после записи файла — копия в localStorage (переживает перезагрузку страницы)."""
    if not IS_WEB:
        return
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return
    web_js(f"localStorage.setItem({json.dumps('wnb:' + os.path.basename(path))}, {json.dumps(text)})")


TOUCH = {"on": False}                         # браузер на телефоне/планшете (палец вместо мыши)


def web_setup_touch():
    """Браузер, сенсорный экран: страница не прокручивается и не масштабируется пальцем, на телефоне — просьба
    повернуть экран, полный экран по первому касанию (Android — ещё и альбомная ориентация), кнопка ⛶,
    поле для экранной клавиатуры (отзыв). Возврат: True — сенсорный экран."""
    r = web_js("""(function(){
      document.documentElement.style.overflow = 'hidden';   // служебные полосы pygbag/xterm (50000 px) давали прокрутку
      document.body.style.overflow = 'hidden';               // в окне игры на сайте (Firefox)
      var touch = window.matchMedia && matchMedia('(pointer: coarse)').matches;
      if (!touch || document.getElementById('wnb-rotate')) return touch ? 'y' : 'n';
      var c = document.getElementById('canvas');
      if (c) c.style.touchAction = 'none';
      document.documentElement.style.overscrollBehavior = 'none';
      document.body.style.touchAction = 'none';
      var phone = Math.min(screen.width, screen.height) < 700;
      var ov = document.createElement('div'); ov.id = 'wnb-rotate';
      ov.style.cssText = 'position:fixed;inset:0;z-index:9999;display:none;flex-direction:column;align-items:center;' +
        'justify-content:center;background:#1d1b24;color:#f0b85a;font:bold 22px sans-serif;text-align:center;padding:24px';
      ov.innerHTML = '<div style="font-size:72px;line-height:1">&#x21BB;</div><div style="margin-top:12px">' +
        'Turn your phone sideways to play</div>';
      document.body.appendChild(ov);
      function chk(){ ov.style.display = (phone && screen.height > screen.width && innerHeight > innerWidth * 0.9)
        ? 'flex' : 'none'; }
      window.addEventListener('resize', chk); window.addEventListener('orientationchange', chk); chk();
      function full(){ var d = document.documentElement, f = d.requestFullscreen || d.webkitRequestFullscreen;
        if (document.fullscreenElement || document.webkitFullscreenElement || !f) return;
        try { var p = f.call(d); if (p && p.then) p.then(function(){ try { screen.orientation.lock('landscape')
          .catch(function(){}); } catch (e) {} }).catch(function(){}); } catch (e) {} }
      if (phone) window.addEventListener('touchend', full, {once: true});
      if (document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen) {
      var b = document.createElement('button'); b.id = 'wnb-full'; b.type = 'button'; b.textContent = '\\u26F6';
      b.setAttribute('aria-label', 'Fullscreen');
      b.style.cssText = 'position:fixed;left:6px;top:6px;z-index:9998;width:40px;height:40px;border:0;border-radius:8px;' +
        'background:rgba(0,0,0,.45);color:#fff;font-size:22px;opacity:.8';
      b.onclick = function(){ if (document.fullscreenElement) { document.exitFullscreen && document.exitFullscreen(); }
        else full(); };
      document.body.appendChild(b); }
      window.wnbText = function(x, y, w, h, fs, show){     // comment box over the canvas (on-screen keyboard)
        var t = document.getElementById('wnb-text');
        if (!show) { if (t) { t.style.display = 'none'; t.blur(); } return ''; }
        if (!t) { t = document.createElement('textarea'); t.id = 'wnb-text'; t.maxLength = 600;
          t.setAttribute('aria-label', 'Comment');
          t.style.cssText = 'position:fixed;z-index:9997;box-sizing:border-box;resize:none;border:2px solid #6fd3e0;' +
            'border-radius:6px;background:#15131c;color:#fff;padding:4px 8px;font-family:sans-serif;outline:none';
          ['keydown', 'keyup', 'keypress'].forEach(function(n){        // keys go to the text, not to SDL
            t.addEventListener(n, function(e){ e.stopPropagation(); }); });
          document.body.appendChild(t); }
        var r = c.getBoundingClientRect(), kx = r.width / 1280, ky = r.height / 720;
        t.style.left = (r.left + x * kx) + 'px'; t.style.top = (r.top + y * ky) + 'px';
        t.style.width = (w * kx) + 'px'; t.style.height = (h * ky) + 'px';
        t.style.fontSize = Math.max(14, fs * ky) + 'px'; t.style.display = 'block';
        return t.value;
      };
      return 'y';
    })()""")
    TOUCH["on"] = str(r) == "y"
    return TOUCH["on"]


def web_setup_page():
    """Браузер: живые области для экранных чтецов и клавиши, которые не должна забирать страница."""
    web_js("""(function(){
      if (document.getElementById('wnb-live-polite')) return;
      function mk(id, mode){ var d=document.createElement('div'); d.id=id; d.setAttribute('aria-live', mode);
        d.setAttribute('role', mode=='assertive' ? 'alert' : 'status');
        d.style.cssText='position:absolute;left:-10000px;top:auto;width:1px;height:1px;overflow:hidden';
        document.body.appendChild(d); }
      mk('wnb-live-polite','polite'); mk('wnb-live-assertive','assertive');
      var c = document.getElementById('canvas');
      if (c) {             // «приложение»: NVDA/JAWS сами отдают стрелки и буквы игре
        c.setAttribute('role', 'application');
        c.setAttribute('aria-label', 'Wheels and Bones, wheelchair repair game. Press F1 for keyboard help.');
        c.tabIndex = 0;
        try { c.focus(); } catch (e) {}
        window.addEventListener('focus', function(){ try { c.focus(); } catch (e) {} });
      }
      function unlockAudio(){   // браузер даёт звук только после действия игрока
        try { var S = (window.Module && Module.SDL2) || window.SDL2;
              if (S && S.audioContext && S.audioContext.state !== 'running') S.audioContext.resume(); } catch (e) {}
      }
      ['pointerdown','keydown','touchstart'].forEach(function(t){ window.addEventListener(t, unlockAudio, true); });
      function wnbQ(f){ try { var q = JSON.parse(localStorage.getItem('wnb:outbox') || '[]'); q = f(q);
        localStorage.setItem('wnb:outbox', JSON.stringify(q.slice(-20))); } catch (e) {} }
      function wnbPost(url, body){                          // убрать из очереди только после ответа сервера
        try { fetch(url, {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: body})
                .then(function(){ wnbQ(function(q){ var i = q.indexOf(body); if (i >= 0) q.splice(i, 1); return q; }); })
                .catch(function(){}); } catch (e) {}
      }
      window.wnbSend = function(url, body){                 // замечание в Google-таблицу: сначала в очередь
        wnbQ(function(q){ q.push(body); return q; }); wnbPost(url, body);
      };
      window.wnbFlush = function(url){                      // при запуске: дослать то, что не ушло
        try { JSON.parse(localStorage.getItem('wnb:outbox') || '[]').forEach(function(b){ wnbPost(url, b); }); }
        catch (e) {}
      };
      window.addEventListener('keydown', function(e){
        var t = e.target && e.target.tagName;
        if (t === 'TEXTAREA' || t === 'INPUT') return;        // поле отзыва на телефоне: пробел и стрелки — тексту
        if (['Tab',' ','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','F1','F2'].indexOf(e.key) >= 0) e.preventDefault();
      });
      window.wnbSay = function(text, interrupt, voice){
        var el = document.getElementById(interrupt ? 'wnb-live-assertive' : 'wnb-live-polite');
        el.textContent = ''; setTimeout(function(){ el.textContent = text; }, 30);
        if (voice && window.speechSynthesis) {
          if (interrupt) speechSynthesis.cancel();
          var u = new SpeechSynthesisUtterance(text);
          u.lang = document.documentElement.getAttribute('data-wnb-lang') || 'en-US';
          speechSynthesis.speak(u);
        }
      };
    })()""")


def tr_en(s):
    """Строка игры по-английски при любом языке интерфейса (для таблицы замечаний)."""
    if not s:
        return s
    old = LANG["code"]
    try:
        LANG["code"] = "en"
        if not _TR:
            load_lang()
        return tr(s)
    except Exception:
        return s
    finally:
        LANG["code"] = old


def feedback_payload(entry, shot=None):
    """Замечание для отправки: поля из feedback.json + версия, платформа и уменьшенный снимок (JPEG, base64)."""
    import base64, io
    d = {k: entry.get(k, "") for k in ("time", "lang", "scene", "job", "title", "phase", "step", "kind",
                                       "reason", "expected", "got", "game_message", "comment")}
    for k in ("title", "step", "reason", "expected", "got", "game_message"):   # таблица — на английском
        d[k] = tr_en(d[k])
    d.update(key=FEEDBACK_KEY, version=GAME_VERSION,
             platform="web" if IS_WEB else ("exe" if getattr(sys, "frozen", False) else "source"))
    return _with_shot(d, shot) if shot is not None else d


def _with_shot(payload, shot):
    """Копия замечания с уменьшенным снимком (JPEG, base64). Тяжело (~0,1–0,3 с) — на компьютере зовётся в фоне."""
    import base64
    d = dict(payload)
    try:
        small = pygame.transform.smoothscale(shot, (640, 360))
        tmp = os.path.join(tempfile.gettempdir(), f"wnb_shot_{threading.get_ident()}.jpg")
        pygame.image.save(small, tmp)                 # через файл: в браузере pygame не пишет в память
        with open(tmp, "rb") as f:
            d["screenshot_jpg_b64"] = base64.b64encode(f.read()).decode("ascii")
        os.remove(tmp)
    except Exception:
        pass
    return d


_OUTBOX_LOCK = threading.Lock()


def _outbox_path():
    return os.path.join(DATA_DIR, "feedback_outbox.json")


def _outbox(change):
    """Очередь неотправленных замечаний (нет сети) — отправятся при следующем запуске."""
    with _OUTBOX_LOCK:
        try:
            with open(_outbox_path(), encoding="utf-8-sig") as f:
                q = json.load(f)
            if not isinstance(q, list):
                q = []
        except Exception:
            q = []
        old = list(q)
        q = change(q)
        try:
            if q:
                with _atomic_open(_outbox_path()) as f:
                    json.dump(q[-30:], f, ensure_ascii=False)
            elif os.path.exists(_outbox_path()):
                os.remove(_outbox_path())
        except Exception:
            pass
        return old                                     # что было в очереди ДО изменения


def _post_feedback(payload):
    import urllib.request
    req = urllib.request.Request(FEEDBACK_URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "text/plain;charset=utf-8"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return 200 <= r.status < 400


def feedback_send(payload, shot=None, local_png=None):
    """Отправить замечание в фоне (игра не замирает). Сначала оно ложится в очередь на диске и убирается оттуда
    только после ответа сервера: закрыли игру во время отправки или нет сети — уйдёт при следующем запуске.
    shot — снимок экрана (уменьшенный JPEG для таблицы), local_png — куда сохранить полный снимок (имя .jpg);
    кодирование — в фоне (pygame держит интерпретатор, поэтому форматы выбраны быстрые).
    True — замечание уходит на сервер (FEEDBACK_URL задан)."""
    import uuid
    payload = dict(payload, uid=payload.get("uid") or uuid.uuid4().hex)
    if IS_WEB:                                        # в браузере потоков нет; очередь — в localStorage (wnbSend)
        if not FEEDBACK_URL:
            return False
        if shot is not None:
            payload = _with_shot(payload, shot)
        r = web_js(f"window.wnbSend ? (wnbSend({json.dumps(FEEDBACK_URL)}, {json.dumps(json.dumps(payload))}), 'ok') : 'no'")
        return str(r) == "ok"                          # мост к странице не работает — «сохранено у тебя»
    uid = payload["uid"]
    if FEEDBACK_URL:
        _outbox(lambda q: q + [payload])

    def run():
        if local_png and shot is not None:
            try:
                pygame.image.save(shot, local_png)
            except Exception:
                pass
        if not FEEDBACK_URL:
            return
        full = payload
        if shot is not None:
            full = _with_shot(payload, shot)
            _outbox(lambda q: [full if x.get("uid") == uid else x for x in q])
        try:
            ok = _post_feedback(full)
        except Exception:
            ok = False
        if ok:
            _outbox(lambda q: [x for x in q if x.get("uid") != uid])
    threading.Thread(target=run, daemon=True).start()
    return bool(FEEDBACK_URL)


def feedback_flush_outbox():
    """Дослать замечания, не ушедшие в прошлый раз (вызывается в фоне при запуске). Каждое убирается из очереди
    только после успешной отправки — закрыли игру посреди досылки, остальные не пропадут."""
    if not FEEDBACK_URL or IS_WEB:
        return
    import uuid
    _outbox(lambda q: [x if isinstance(x, dict) and x.get("uid") else dict(x, uid=uuid.uuid4().hex)
                       for x in q if isinstance(x, dict)])
    for item in _outbox(lambda q: q):
        try:
            ok = _post_feedback(item)
        except Exception:
            ok = False
        if ok:
            _outbox(lambda q, u=item["uid"]: [x for x in q if x.get("uid") != u])


def dpi_aware():
    """Windows: игра сама следит за масштабом — система не растягивает и не мылит окно.
    Вызывать до pygame.init(), чтобы размер монитора определился в настоящих пикселях."""
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def available_resolutions():
    """Разрешения 16:9, которые помещаются на монитор."""
    dw, dh = _desktop()
    return [r for r in RES_OPTIONS if r[0] <= dw and r[1] <= dh] or [RES_OPTIONS[0]]


def _desktop():
    try:
        return pygame.display.get_desktop_sizes()[0]
    except Exception:
        return (1920, 1080)


def _fit_view(w, h):
    """Наибольший прямоугольник 16:9 внутри w×h — по центру (поля по бокам или сверху/снизу)."""
    k = min(w / WIDTH, h / HEIGHT)
    vw, vh = max(1, round(WIDTH * k)), max(1, round(HEIGHT * k))
    return pygame.Rect((w - vw) // 2, (h - vh) // 2, vw, vh)


def rs_for(res, view_h=None):
    """Масштаб рендера: выбранное разрешение, а в режиме АВТО — по высоте области игры в окне (не больше ×2)."""
    if res:
        return max(0.6 if IS_WEB else 1.0, min(3.0, res[1] / HEIGHT))   # браузер: холст бывает и меньше 720p
    if view_h is None:
        return pick_render_scale()
    return max(1.0, min(2.0, view_h / HEIGHT))          # ровно под окно — кадр выводится без масштабирования


def _default_window():
    """Окно в режиме «в окне»: выбранное разрешение, если влезает, иначе 85% монитора (16:9)."""
    dw, dh = _desktop()
    res = DISPLAY.get("res")
    if res and res[0] <= dw * 0.95 and res[1] <= dh * 0.92:
        return tuple(res)
    r = _fit_view(int(dw * 0.85), int(dh * 0.85))
    return (r.w, r.h)


def _set_window(fullscreen):
    """Создать/переключить окно. Масштабирование кадра делает игра сама (present), без SCALED у SDL."""
    if IS_WEB:                                        # браузер: холст под окно игры (размер — web_target_res)
        res = web_target_res()
        DISPLAY["res"] = res
        screen = pygame.display.set_mode(res)
        DISPLAY["fullscreen"] = False
        DISPLAY["screen"] = screen
        return screen
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        size = DISPLAY.get("win_size") or _default_window()
        screen = pygame.display.set_mode(size, pygame.RESIZABLE)
    DISPLAY["fullscreen"] = bool(fullscreen)
    DISPLAY["screen"] = screen
    return screen


def _update_rs():
    """Пересчитать масштаб рендера под текущее окно/разрешение; при смене — сбросить кэши и кадр."""
    global RS
    view = _fit_view(*pygame.display.get_surface().get_size())
    new_rs = rs_for(DISPLAY.get("res"), view.h)
    if new_rs != RS or DISPLAY.get("frame") is None:
        RS = new_rs
        for c in (_img_cache, _font_cache, _AA_CACHE, _glow_cache, _tool_icon_cache):
            c.clear()
        DISPLAY["frame"] = Surf((WIDTH, HEIGHT))
        DISPLAY["rs_changed"] = True
    return RS


def apply_display(res=None, fullscreen=None):
    """Сменить разрешение и/или режим на лету."""
    if res is not None:
        DISPLAY["res"] = None if res == "auto" else tuple(res)
        DISPLAY["win_size"] = None                     # окно — под новое разрешение
    want_full = DISPLAY["fullscreen"] if fullscreen is None else fullscreen
    _set_window(want_full)
    _update_rs()
    return RS


def init_display(fullscreen=False):
    """Первое окно игры."""
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    _set_window(fullscreen)
    _update_rs()
    DISPLAY["rs_changed"] = False
    return DISPLAY["screen"]


def web_target_res():
    """Браузер: размер холста. Выбор игрока (1080p/720p) или «авто»: ровно размер окна игры на экране
    (ширина × devicePixelRatio, кратно 16, от WEB_MIN_W до 1440p). Холст другого размера браузер растягивает или
    ужимает грубо — тонкие кольца и линии рвутся, текст «сыпется». web_cap — потолок после замедления (fps < 20)."""
    q = DISPLAY.get("web_quality", "auto")
    if q in WEB_RES:
        return WEB_RES[q]
    px = DISPLAY.get("web_px") or 1920
    cap = DISPLAY.get("web_cap", len(WEB_LEVELS) - 1)
    top = WEB_RES[WEB_LEVELS[max(0, min(cap, len(WEB_LEVELS) - 1))]][0]
    if TOUCH["on"]:                                    # телефон/планшет: плотный экран, мало памяти — не шире 1080p
        top = min(top, WEB_RES["high"][0])
    # холст ровно с окно игры (пиксель в пиксель): браузеру нечего ужимать — кружки и линии не рвутся
    w = int(max(WEB_MIN_W, min(top, round(px / 16) * 16)))
    return (w, w * 9 // 16)


def web_measure():
    """Сколько реальных пикселей занимает окно игры (по ширине, область 16:9). 0 — ещё не известно."""
    v = web_js("(function(){var c=document.getElementById('canvas');if(!c)return 0;var r=c.getBoundingClientRect();"
               "return Math.round(Math.min(r.width,r.height*16/9)*(window.devicePixelRatio||1));})()")
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def set_web_quality(q, by_user=True):
    """Браузер: «auto», «high» (1080p) или «standard» (720p); by_user=False — выбор игры, не игрока."""
    if q != "auto" and q not in WEB_RES:
        return False
    DISPLAY["web_quality"] = q
    if by_user:
        DISPLAY["web_quality_user"] = q != "auto"
        DISPLAY.pop("web_cap", None)                  # игрок выбрал сам — потолок от замедления сбрасываем
    if DISPLAY.get("res") == web_target_res():
        return True
    try:
        apply_display()
    except Exception:
        return False
    return True


def web_auto_resize(px):
    """«Авто»: окно игры на экране стало другого размера (полный экран, поворот, окно браузера) — холст под него.
    Меняем, только если тот же новый размер держится две проверки подряд (без дёрганья при перетаскивании окна)."""
    if not px:
        return False
    old = DISPLAY.get("web_px")
    DISPLAY["web_px"] = px
    want = web_target_res()
    cur = DISPLAY.get("res")
    if want == cur or (cur and abs(want[0] - cur[0]) <= max(16, cur[0] * 0.02)):
        DISPLAY.pop("_want", None)                  # разница в пару процентов — не пересобираем кадр
        return False
    if DISPLAY.get("_want") != want:
        DISPLAY["_want"] = want
        DISPLAY["web_px"] = old
        return False
    DISPLAY.pop("_want", None)
    apply_display()
    return True


def web_toggle_fullscreen():
    """Браузер: полный экран для страницы игры (работает и во встроенном на сайт окне — у iframe allowfullscreen)."""
    web_js("(function(){var d=document;if(d.fullscreenElement||d.webkitFullscreenElement){(d.exitFullscreen||"
           "d.webkitExitFullscreen).call(d);}else{var e=d.documentElement;(e.requestFullscreen||"
           "e.webkitRequestFullscreen).call(e);}})()")


def toggle_fullscreen():
    """Полный экран <-> окно (F11, Alt+Enter, кнопка в настройках)."""
    if IS_WEB:
        web_toggle_fullscreen()
        return DISPLAY["fullscreen"]
    if not DISPLAY["fullscreen"]:
        DISPLAY["win_size"] = pygame.display.get_surface().get_size()   # вернуться в окно того же размера
    try:
        apply_display(fullscreen=not DISPLAY["fullscreen"])
    except pygame.error:
        pass
    return DISPLAY["fullscreen"]


def present(frame):
    """Вывести кадр в окно: по центру, без искажений, с тёмными полями; при несовпадении размеров — масштаб."""
    screen = pygame.display.get_surface()
    view = _fit_view(*screen.get_size())
    DISPLAY["view"] = view
    fw, fh = pygame.Surface.get_size(frame)
    if (fw, fh) == view.size:
        if view.topleft != (0, 0):
            screen.fill((0, 0, 0))
        pygame.Surface.blit(screen, frame, view.topleft)
    else:
        buf = DISPLAY.get("scale_buf")
        if buf is None or buf.get_size() != view.size:
            buf = DISPLAY["scale_buf"] = pygame.Surface(view.size)
        pygame.transform.smoothscale(frame, view.size, buf)
        screen.fill((0, 0, 0))
        screen.blit(buf, view.topleft)


def window_to_logical(pos):
    """Координаты окна -> логические 1280×720 (с учётом полей и масштаба)."""
    v = DISPLAY.get("view")
    if not v:
        return (int(pos[0] / RS), int(pos[1] / RS))
    return (int((pos[0] - v.x) * WIDTH / v.w), int((pos[1] - v.y) * HEIGHT / v.h))


VOL = {"master": 0.8, "music": 0.45, "sfx": 0.9, "amb": 0.45, "on": True}   # сохраняется в settings.json
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
MUSIC = {"cur": None, "next": None, "xf": 1.0, "t": None}   # фоновая музыка: тема, следующая, громкость перехода


def _amb_level():
    return VOL["master"] * VOL["amb"] if VOL["on"] else 0.0


# Музыка не надоедает (отзыв тестировщиков): на титуле, вступлении, вечеринке и в титрах — полностью; в мастерской,
# заданиях, Гильдии, гараже и Кабинете посадки мелодия звучит первые MUSIC_FULL с сцены, потом за MUSIC_FADE уходит
# в тихий фон (MUSIC_BED от громкости), где слышна атмосфера сцены; при смене сцены — снова громче.
MUSIC_FULL, MUSIC_FADE, MUSIC_BED = 45.0, 12.0, 0.18
MUSIC_LOUD_SCENES = ("title", "intro", "ending", "credits")


def _music_level():
    return (VOL["master"] * VOL["music"] * MUSIC.get("duck", 1.0) * MUSIC.get("xf", 1.0)) if VOL["on"] else 0.0


def music_duck(scene, since, dt):
    """Плавно приглушить мелодию в рабочих сценах (since — секунд с начала сцены)."""
    want = 1.0 if scene in MUSIC_LOUD_SCENES or since < MUSIC_FULL else         max(MUSIC_BED, 1.0 - (since - MUSIC_FULL) / MUSIC_FADE * (1.0 - MUSIC_BED))
    cur = MUSIC.get("duck", 1.0)
    new = min(want, cur + dt / 2.5) if want > cur else want     # вверх — за 2,5 с, вниз — по кривой
    if abs(new - cur) > 1e-3:
        MUSIC["duck"] = new
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(_music_level())
        except Exception:
            pass


def apply_volume():
    """Применить громкость к атмосфере и музыке (эффекты — при каждом snd)."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.Channel(0).set_volume(_amb_level())
            pygame.mixer.music.set_volume(_music_level())
    except Exception:
        pass


def music_path(theme):
    for ext in (".ogg", ".mp3", ".wav"):
        path = os.path.join(MUSIC_DIR, theme + ext)
        if os.path.exists(path):
            return path
    return None


def music_update(theme, now):
    """Сменить тему с плавным переходом: старая гаснет (~0,7 с), новая вступает (~1,5 с) — громкостью, своими руками.
    Затухания SDL_mixer (music.fadeout, play(fade_ms)) нельзя: load/play ждут в цикле конца затухания старой темы,
    а в браузере звук обрабатывается в том же единственном потоке — на первом запуске страница висла намертво."""
    try:
        if not pygame.mixer.get_init():
            return
        dt = 0.0 if MUSIC["t"] is None else max(0.0, min(0.1, now - MUSIC["t"]))
        MUSIC["t"] = now
        if theme == MUSIC["cur"]:
            MUSIC["next"] = None                          # вернулись до конца перехода — прежняя тема остаётся
        elif theme != MUSIC["next"]:
            MUSIC["next"] = theme
        if MUSIC["next"] is not None:
            if MUSIC["cur"] and MUSIC["xf"] > 0.0:        # старая тема гаснет
                MUSIC["xf"] = max(0.0, MUSIC["xf"] - dt / 0.7)
            else:
                MUSIC["cur"], MUSIC["next"] = MUSIC["next"], None
                pygame.mixer.music.stop()                 # мгновенно, без ожидания затухания
                path = music_path(MUSIC["cur"]) if MUSIC["cur"] else None
                if path:
                    MUSIC["xf"] = 0.0
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.set_volume(0.0)
                    pygame.mixer.music.play(loops=-1)
        elif MUSIC["xf"] < 1.0:                           # новая тема вступает
            MUSIC["xf"] = min(1.0, MUSIC["xf"] + dt / 1.5)
        vol = _music_level()
        if abs(vol - MUSIC.get("vol", -1.0)) > 1e-3:
            MUSIC["vol"] = vol
            pygame.mixer.music.set_volume(vol)
    except Exception:
        pass


def _n(sec):
    return max(1, int(SR * sec))


def _buf(sec):
    return [0.0] * _n(sec)


def _add(dst, src, at=0.0, gain=1.0):
    o = int(at * SR)
    for i, v in enumerate(src):
        j = o + i
        if j < len(dst):
            dst[j] += v * gain
    return dst


def _tone(freq, sec, decay=0.2, attack=0.004, wave="sine", vib=None, glide=None):
    """Тон с атакой и экспоненциальным спадом. glide=(f_конец) — глиссандо,
    vib=(частота, глубина в долях) — вибрато."""
    out = []
    ph = 0.0
    n = _n(sec)
    for i in range(n):
        t = i / SR
        f = freq if glide is None else freq + (glide - freq) * (i / n)
        if vib:
            f *= 1 + vib[1] * math.sin(2 * math.pi * vib[0] * t)
        ph += 2 * math.pi * f / SR
        if wave == "tri":
            s = 2 / math.pi * math.asin(math.sin(ph))
        elif wave == "soft_sq":
            s = math.tanh(3 * math.sin(ph)) * 0.8
        else:
            s = math.sin(ph)
        env = min(1.0, t / attack) if attack > 0 else 1.0
        out.append(s * env * math.exp(-t / decay))
    return out


def _bell(freq, sec, decay=0.35, partials=((1, 1.0), (2.0, 0.45), (3.01, 0.22), (4.2, 0.12))):
    """Колокольчик: несколько обертонов, высокие гаснут быстрее."""
    out = _buf(sec)
    for ratio, amp in partials:
        _add(out, _tone(freq * ratio, sec, decay / (ratio ** 0.6), attack=0.002), 0, amp)
    return out


def _noise(sec, decay=0.1, attack=0.002, lp=1.0, hp=0.0, swell=None):
    """Шум с простыми фильтрами: lp — сглаживание (0..1, меньше = глуше), hp — срез низов."""
    out = []
    y = prev = 0.0
    n = _n(sec)
    for i in range(n):
        t = i / SR
        x = _rng.uniform(-1, 1)
        a = lp if not callable(lp) else lp(i / n)
        y += a * (x - y)
        z = y - prev * hp
        prev = y
        env = min(1.0, t / attack)
        env *= math.exp(-t / decay) if swell is None else math.sin(math.pi * min(1.0, i / n)) ** swell
        out.append(z * env)
    return out


def _to_sound(samples, vol=0.5):
    """Синтезированный звук → Sound в ТОМ формате, который реально открыл микшер
    (браузер обычно даёт 44,1/48 кГц стерео вместо наших 22 050 Гц моно — иначе хрип)."""
    peak = max(1e-6, max(abs(v) for v in samples))
    k = vol / peak
    freq, size, chans = pygame.mixer.get_init() or (SR, -16, 1)
    if freq != SR:                                    # линейная передискретизация
        n = max(1, int(len(samples) * freq / SR))
        step = SR / freq
        last = len(samples) - 1
        res = []
        for i in range(n):
            x = i * step
            j = int(x)
            if j >= last:
                res.append(samples[last])
            else:
                f = x - j
                res.append(samples[j] * (1 - f) + samples[j + 1] * f)
        samples = res
    vals = [max(-1.0, min(1.0, v * k)) for v in samples]
    if chans > 1:
        vals = [v for v in vals for _ in range(chans)]
    if abs(size) == 32:                               # 32-битный float (pygame отдаёт -32)
        buf = array.array("f", vals)
    elif abs(size) == 8:
        buf = array.array("B" if size > 0 else "b", (int(v * 127) + (128 if size > 0 else 0) for v in vals))
    else:
        buf = array.array("h", (int(v * 32767) for v in vals))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _metal_clink(freq):
    out = _bell(freq, 0.35, 0.18, ((1, 1.0), (2.76, 0.6), (5.40, 0.35), (8.93, 0.2)))
    return _add(out, _noise(0.02, 0.006, lp=0.9, hp=0.9), 0, 0.5)


def build_sounds():
    """Синтез эффектов при старте. Любая ошибка -> игра просто молчит."""
    try:
        if not pygame.mixer.get_init():
            return
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(1)                          # канал 0 — фоновая атмосфера
        S = {}
        S["tick"] = _to_sound(_add(_tone(1900, 0.05, 0.012), _noise(0.01, 0.003, hp=0.95), 0, 0.6), 0.22)
        S["hover"] = _to_sound(_tone(2600, 0.03, 0.008), 0.05)
        S["tool_metal"] = _to_sound(_metal_clink(1650), 0.26)
        S["tool_soft"] = _to_sound(_noise(0.16, 0.1, lp=0.12, swell=1.5), 0.22)
        S["tool_elec"] = _to_sound(_add(_tone(1250, 0.07, 0.05, wave="soft_sq"),
                                        _tone(1680, 0.08, 0.06, wave="soft_sq"), 0.07), 0.16)
        S["inspect"] = _to_sound(_add(_tone(700, 0.11, 0.08, glide=1500), _bell(3100, 0.25, 0.08), 0.06, 0.3), 0.22)
        ok = _buf(0.7)
        for i, f in enumerate((1046.5, 1318.5, 1568.0)):
            _add(ok, _bell(f, 0.6, 0.32), i * 0.055, 0.8)
        S["ok"] = _to_sound(ok, 0.28)
        bad = _add(_tone(240, 0.22, 0.09, wave="tri", glide=140), _tone(70, 0.12, 0.05), 0, 0.7)
        S["bad"] = _to_sound(bad, 0.30)
        fail = _buf(1.1)
        for i, f in enumerate((392.0, 329.6, 261.6)):
            _add(fail, _tone(f, 0.45, 0.25, attack=0.01, wave="tri", vib=(5.5, 0.012)), i * 0.22, 0.8)
        S["fail"] = _to_sound(fail, 0.32)
        fan = _buf(1.8)
        for i, f in enumerate((523.3, 659.3, 784.0, 1046.5)):
            _add(fan, _bell(f, 0.5, 0.28), i * 0.1, 0.7)
            _add(fan, _tone(f / 2, 0.3, 0.2, wave="tri"), i * 0.1, 0.25)
        for f in (523.3, 659.3, 784.0):
            _add(fan, _tone(f, 1.1, 0.5, attack=0.03, wave="tri", vib=(5, 0.006)), 0.42, 0.35)
        _add(fan, _noise(1.0, 0.35, lp=0.6, hp=0.8), 0.42, 0.12)
        S["fanfare"] = _to_sound(fan, 0.30)
        S["ping"] = _to_sound(_bell(1400, 0.9, 0.5, ((1, 1.0), (2.4, 0.3), (5.1, 0.12))), 0.30)
        S["dull"] = _to_sound(_add(_tone(170, 0.14, 0.04), _noise(0.06, 0.02, lp=0.2), 0, 0.6), 0.34)
        S["hiss"] = _to_sound(_noise(0.2, 0.1, lp=0.5, hp=0.6, swell=1.2), 0.18)
        S["zap"] = _to_sound(_add(_add(_noise(0.32, 0.12, lp=1.0, hp=0.6), _noise(0.12, 0.05, lp=0.5), 0.03, 0.8),
                                  _tone(1900, 0.18, 0.08, wave="tri", glide=700), 0, 0.35), 0.55)
        S["pop"] = _to_sound(_add(_noise(0.08, 0.025, lp=0.8), _tone(90, 0.15, 0.06), 0, 0.8), 0.5)
        S["whoosh"] = _to_sound(_noise(0.35, 1, lp=lambda k: 0.02 + 0.12 * k, swell=2.2), 0.07)
        S["whoosh_out"] = _to_sound(_noise(0.28, 1, lp=lambda k: 0.12 - 0.1 * k, swell=2.2), 0.06)
        S["ratchet"] = _to_sound(_add(_noise(0.008, 0.002, hp=0.9), _tone(900, 0.02, 0.006), 0, 0.5), 0.10)
        for i, f in enumerate((1046.5, 1318.5, 1568.0)):
            S[f"star{i}"] = _to_sound(_add(_bell(f, 0.7, 0.4), _bell(f * 2, 0.3, 0.12), 0, 0.25), 0.26)
        S["ghost"] = _to_sound(_add(_tone(880, 0.6, 0.25, attack=0.08, vib=(6, 0.02)),
                                    _tone(1320, 0.6, 0.2, attack=0.12, vib=(5, 0.025)), 0, 0.5), 0.09)
        SOUND.update(S)
    except Exception:
        SOUND.clear()


# ---------- фоновые петли (тихие; строятся при первом заходе в сцену) ----------
def _loop_fade(buf, sec=0.08):
    """Шов петли: конец плавно перетекает в начало."""
    n = _n(sec)
    for i in range(n):
        k = i / n
        buf[i] = buf[i] * k + buf[len(buf) - n + i] * (1 - k)
    return buf[:len(buf) - n]


def _amb_workshop():
    out = _buf(8.0)
    for at, f in ((1.2, 3200), (1.38, 3600), (5.1, 2900), (5.25, 3400), (5.4, 3100)):  # птицы за окном
        _add(out, _tone(f, 0.12, 0.05, attack=0.01, glide=f * 1.25), at, 0.25)
    return out


def _amb_road():
    out = _buf(6.0)
    for c in range(14):                                        # сверчки: пачки коротких трелей
        at = c * 0.42 + (0.1 if c % 3 == 0 else 0)
        for k in range(3):
            _add(out, _tone(4400 + 120 * (c % 2), 0.03, 0.012, attack=0.003), at + k * 0.045, 0.35)
    return out


def _amb_guild():
    out = _buf(6.0)
    for i in range(40):                                        # треск углей
        _add(out, _noise(0.012, 0.004, hp=0.8), _rng.uniform(0, 5.9), _rng.uniform(0.2, 0.9))
    for at in (1.0, 3.7):                                      # далёкий молоточек
        _add(out, _metal_clink(2300), at, 0.18)
    return out


def _amb_party():
    out = _buf(6.4)                                            # музыкальная шкатулка
    mel = [784, 659, 784, 1046, 880, 784, 659, 587, 659, 784, 659, 523, 587, 659, 587, 523]
    bass = [262, 196, 220, 175]
    for i, f in enumerate(mel):
        _add(out, _bell(f, 0.5, 0.25), i * 0.4, 0.5)
    for i, f in enumerate(bass):
        _add(out, _tone(f, 1.5, 0.6, attack=0.02, wave="tri"), i * 1.6, 0.25)
    return out


_AMB_BUILD = {"bg_workshop.png": (_amb_workshop, 0.05), "bg_garage.png": (_amb_workshop, 0.035),
              "bg_road.png": (_amb_road, 0.07), "bg_guild.png": (_amb_guild, 0.07),
              "bg_party.png": (_amb_party, 0.10)}


def set_ambient(bg_name):
    """Переключить фоновую петлю под фон сцены (плавно)."""
    if not SOUND or _AMB["name"] == bg_name or not pygame.mixer.get_init():
        return
    _AMB["name"] = bg_name
    try:
        ch = pygame.mixer.Channel(0)
        ch.fadeout(400)
        spec = _AMB_BUILD.get(bg_name)
        if not spec:
            return
        key = "amb:" + bg_name
        if key not in SOUND:
            SOUND[key] = _to_sound(_loop_fade(spec[0]()), spec[1])
        ch.play(SOUND[key], loops=-1, fade_ms=900)
        ch.set_volume(_amb_level())
    except Exception:
        pass


def toggle_sound():
    VOL["on"] = not VOL["on"]
    apply_volume()
    return VOL["on"]


def snd(name):
    if not VOL["on"]:
        return
    s = SOUND.get(name)
    if s:
        try:
            s.set_volume(VOL["master"] * VOL["sfx"])
            s.play()
        except Exception:
            pass


_PITCH = {}


def snd_pitch(frac):
    """Короткий тон: чем больше значение (давление насоса), тем выше — слышно без экрана."""
    if not VOL["on"]:
        return
    step = max(0, min(20, int(frac * 20)))
    s = _PITCH.get(step)
    if s is None:
        try:
            s = _PITCH[step] = _to_sound(_tone(330 * 2 ** (step / 10), 0.12, decay=0.08), 0.3)
        except Exception:
            return
    try:
        s.set_volume(VOL["master"] * VOL["sfx"])
        s.play()
    except Exception:
        pass


TOOL_SOUND = {"hands": "tool_soft", "eyes": "inspect", "cloth": "tool_soft", "brush": "tool_soft", "patch": "tool_soft",
              "bucket": "tool_soft", "pencil": "tool_soft", "multimeter": "tool_elec",
              "charger": "tool_elec", "tensiometer": "tool_elec", "dial": "tool_elec", "gauge": "tool_elec"}

# ----------------------------------------------------------------------------- #
#  Встроенный векторный арт: персонажи, коляски и фоны рисуются кодом.
#  PNG в assets/ имеет приоритет — вектор лишь замена «пока арта нет» и
#  одновременно осознанный flat-стиль игры.
# ----------------------------------------------------------------------------- #
def _S(w, h):
    return Surf((w, h), pygame.SRCALPHA)


def _ln(s, col, a, b, w=3):
    DR.line(s, col, a, b, w)


def _face(s, cx, cy, r, eye=(34, 44, 40)):
    aa_circle(s, eye, (cx - r // 3, cy - 2), max(3, r // 8))
    aa_circle(s, eye, (cx + r // 3, cy - 2), max(3, r // 8))
    DR.arc(s, eye, (cx - r // 3, cy + r // 6, 2 * r // 3, max(8, r // 3)),
                    math.pi, 2 * math.pi, 2)


def _wheel(s, c, r, tire=(52, 52, 62), rim=(150, 155, 170), spokes=6):
    aa_circle(s, tire, c, r, max(4, r // 8))
    aa_circle(s, rim, c, r - max(6, r // 6), 3)
    for i in range(spokes):
        a = i * 2 * math.pi / spokes
        _ln(s, (120, 125, 140), c,
            (c[0] + int((r - 10) * math.cos(a)), c[1] + int((r - 10) * math.sin(a))), 2)
    aa_circle(s, rim, c, max(5, r // 7))


def _client_base(skin, outfit, head_r=34, wide=False):
    """Чиби-клиент анфас в коляске (200x280): колёса, рама, ноги, торс, голова."""
    s = _S(200, 280)
    for wx in (50, 150):
        _wheel(s, (wx, 218), 50)
    aa_rect(s, (96, 100, 118), (58, 196, 84, 18), border_radius=6)
    bw = 84 if wide else 64
    aa_rect(s, (70, 66, 84), (100 - bw // 2 - 6, 118, bw + 12, 84), border_radius=14)
    leg = tuple(max(28, c - 34) for c in outfit)
    aa_rect(s, leg, (76, 200, 17, 46), border_radius=7)
    aa_rect(s, leg, (107, 200, 17, 46), border_radius=7)
    aa_rect(s, (130, 135, 150), (68, 248, 64, 9), border_radius=4)
    aa_rect(s, outfit, (100 - bw // 2, 132, bw, 72), border_radius=16)
    _ln(s, skin, (100 - bw // 2 + 4, 150), (100 - bw // 2 - 10, 186), 9)
    _ln(s, skin, (100 + bw // 2 - 4, 150), (100 + bw // 2 + 10, 186), 9)
    aa_circle(s, skin, (100, 96), head_r)
    _face(s, 100, 96, head_r)
    return s


def _art_martin():
    s = _S(200, 280)
    DR.ellipse(s, (20, 18, 26, 90), (40, 262, 120, 14))
    _ln(s, (180, 139, 94), (128, 116), (152, 116), 6)
    _ln(s, (180, 139, 94), (140, 116), (140, 264), 7)
    aa_circle(s, (134, 221, 154), (85, 80), 34)
    _ln(s, (47, 107, 68), (62, 62), (74, 56), 3)
    _ln(s, (47, 107, 68), (66, 54), (70, 64), 3)
    aa_circle(s, (34, 48, 34), (72, 76), 5)
    aa_circle(s, (244, 247, 238), (100, 76), 9)
    aa_circle(s, (34, 48, 34), (102, 78), 4)
    DR.arc(s, (34, 48, 34), (70, 88, 30, 16), math.pi, 2 * math.pi, 2)
    aa_rect(s, (111, 82, 60), (60, 118, 52, 72), border_radius=14)
    DR.rect(s, (138, 106, 78), (68, 140, 12, 12))
    _ln(s, (134, 221, 154), (60, 132), (42, 164), 9)
    _ln(s, (134, 221, 154), (110, 130), (138, 150), 9)
    aa_rect(s, (74, 68, 88), (86, 188, 16, 74), border_radius=7)
    DR.ellipse(s, (51, 48, 68), (78, 258, 32, 14))
    aa_rect(s, (74, 68, 88), (62, 188, 16, 24), border_radius=7)
    return s


def _art_ghost():
    s = _S(200, 280)
    col = (165, 239, 210)
    DR.ellipse(s, col, (52, 40, 96, 110))
    DR.polygon(s, col, [(54, 95), (146, 95), (146, 190), (131, 206), (116, 190),
                                 (101, 206), (86, 190), (71, 206), (54, 190)])
    aa_circle(s, (26, 84, 62), (84, 84), 5)
    aa_circle(s, (26, 84, 62), (114, 84), 5)
    aa_circle(s, (208, 178, 110), (114, 86), 11, 2)
    _ln(s, (208, 178, 110), (123, 94), (132, 116), 2)
    DR.arc(s, (26, 84, 62), (86, 96, 26, 14), math.pi, 2 * math.pi, 2)
    DR.polygon(s, (196, 116, 96), [(100, 128), (84, 120), (84, 136)])
    DR.polygon(s, (196, 116, 96), [(100, 128), (116, 120), (116, 136)])
    aa_circle(s, (196, 116, 96), (100, 128), 4)
    return s


def _art_master():
    s = _S(200, 280)
    col = (186, 156, 232)
    DR.ellipse(s, col, (48, 44, 104, 112))
    DR.polygon(s, col, [(50, 98), (150, 98), (150, 186), (135, 202), (120, 186),
                                 (105, 202), (90, 186), (75, 202), (50, 186)])
    aa_circle(s, (150, 146, 160), (100, 44), 16)
    aa_rect(s, (92, 74, 60), (66, 118, 68, 74), border_radius=10)
    aa_rect(s, (120, 98, 78), (86, 142, 28, 24), border_radius=5)
    aa_circle(s, (205, 210, 225), (94, 140), 4, 2)
    _ln(s, (205, 210, 225), (94, 142), (94, 156), 4)
    for bx in (88, 100, 112):
        _ln(s, (222, 222, 232), (bx, 106), (bx - 4, 152), 5)
        aa_circle(s, (150, 120, 80), (bx - 4, 154), 4)
    for gx in (86, 114):
        aa_circle(s, (238, 234, 246), (gx, 86), 9, 2)
    _ln(s, (238, 234, 246), (95, 86), (105, 86), 2)
    aa_circle(s, (54, 40, 76), (86, 86), 3)
    aa_circle(s, (54, 40, 76), (114, 86), 3)
    return s


def _art_client_elf():
    s = _client_base((242, 214, 184), (86, 138, 92))
    DR.polygon(s, (242, 214, 184), [(66, 90), (46, 82), (66, 102)])
    DR.polygon(s, (242, 214, 184), [(134, 90), (154, 82), (134, 102)])
    DR.arc(s, (226, 196, 96), (64, 56, 72, 76), 0, math.pi, 11)
    aa_rect(s, (226, 196, 96), (58, 92, 12, 58), border_radius=6)
    aa_rect(s, (226, 196, 96), (130, 92, 12, 58), border_radius=6)
    return s


def _art_client_dwarf():
    s = _client_base((232, 180, 142), (122, 90, 58))
    DR.arc(s, (150, 96, 52), (66, 60, 68, 58), 0, math.pi, 9)
    DR.ellipse(s, (150, 96, 52), (72, 110, 56, 54))
    aa_rect(s, (150, 96, 52), (88, 156, 24, 28), border_radius=8)
    aa_circle(s, (196, 150, 60), (100, 182), 7)
    return s


def _art_client_fairy():
    s = _S(200, 280)
    DR.ellipse(s, (188, 226, 250, 120), (24, 104, 64, 98))
    DR.ellipse(s, (188, 226, 250, 120), (112, 104, 64, 98))
    s.blit(_client_base((246, 222, 206), (226, 130, 176), head_r=28), (0, 0))
    for p in ((40, 78), (162, 94), (150, 58), (48, 150)):
        aa_circle(s, (250, 240, 170), p, 3)
    return s


def _art_client_orc():
    s = _client_base((122, 168, 96), (94, 74, 56), wide=True)
    DR.polygon(s, (238, 238, 226), [(84, 114), (92, 114), (88, 100)])
    DR.polygon(s, (238, 238, 226), [(108, 114), (116, 114), (112, 100)])
    aa_rect(s, (70, 56, 44), (78, 58, 44, 12), border_radius=6)
    return s


def _art_client_troll():
    s = _client_base((138, 154, 128), (88, 96, 78), head_r=40, wide=True)
    aa_circle(s, (112, 128, 104), (100, 106), 10)
    DR.arc(s, (74, 106, 58), (56, 46, 88, 62), 0, math.pi, 13)
    return s


def _art_client_goblin():
    s = _client_base((154, 200, 96), (106, 90, 42), head_r=30)
    DR.polygon(s, (154, 200, 96), [(72, 92), (40, 76), (72, 104)])
    DR.polygon(s, (154, 200, 96), [(128, 92), (160, 76), (128, 104)])
    _ln(s, (216, 184, 74), (76, 74), (124, 74), 5)
    aa_circle(s, (216, 184, 74), (88, 72), 9, 3)
    aa_circle(s, (216, 184, 74), (112, 72), 9, 3)
    return s


def _art_client_sorceress():
    s = _client_base((238, 210, 194), (128, 86, 200))
    DR.ellipse(s, (86, 54, 140), (54, 62, 92, 18))
    DR.polygon(s, (108, 70, 172), [(76, 68), (124, 68), (106, 18)])
    aa_circle(s, (110, 210, 235), (100, 150), 5)
    aa_circle(s, (110, 210, 235), (100, 150), 9, 1)
    return s


def _art_client_golem():
    s = _client_base((140, 140, 152), (110, 110, 124), wide=True)
    aa_circle(s, (140, 140, 152), (100, 96), 35)
    aa_rect(s, (140, 140, 152), (70, 66, 60, 56), border_radius=10)
    aa_rect(s, (110, 210, 235), (82, 86, 12, 8), border_radius=2)
    aa_rect(s, (110, 210, 235), (106, 86, 12, 8), border_radius=2)
    _ln(s, (96, 96, 108), (84, 122), (100, 110), 2)
    _ln(s, (96, 96, 108), (128, 72), (118, 92), 2)
    return s


def _art_client_centaur():
    s = _S(200, 280)
    for wx in (36, 86, 136, 178):
        _wheel(s, (wx, 236), 21, spokes=4)
    aa_rect(s, (96, 100, 118), (14, 206, 178, 12), border_radius=5)
    _ln(s, (110, 70, 40), (30, 160), (12, 134), 5)
    DR.ellipse(s, (140, 94, 58), (26, 150, 120, 58))
    aa_rect(s, (120, 78, 46), (32, 196, 22, 12), border_radius=5)
    aa_rect(s, (120, 78, 46), (110, 196, 22, 12), border_radius=5)
    aa_rect(s, (74, 108, 64), (128, 108, 36, 58), border_radius=10)
    aa_rect(s, (150, 110, 66), (116, 128, 20, 30), border_radius=6)
    _ln(s, (150, 110, 66), (130, 114), (118, 132), 4)
    aa_circle(s, (232, 190, 152), (147, 84), 24)
    _face(s, 147, 84, 24)
    DR.arc(s, (92, 58, 34), (124, 54, 48, 42), 0, math.pi, 8)
    return s


# Геометрия схем колясок: реальные мм чертежа (x — вперёд, y — вверх, пол y=0)
# -> пиксели рамки 380x300. Те же константы использует art_tests/build_assets.py,
# поэтому векторная заглушка, PNG-арт и хотспоты совпадают.
CHAIR_GEOM = {"manual": (130.3, 294.0, 0.30942), "power": (166.74, 294.0, 0.29992)}
_CH_SS = 2  # суперсэмплинг векторной схемы


def _chair_canvas(kind):
    ax, ay, k = CHAIR_GEOM[kind]
    big = Surf((380 * _CH_SS, 300 * _CH_SS), pygame.SRCALPHA)
    P = lambda x, y: (int((ax + x * k) * _CH_SS), int((ay - y * k) * _CH_SS))
    R = lambda mm: max(1, int(mm * k * _CH_SS))
    return big, P, R


def _chair_done(big):
    return TF.smoothscale(big, (380, 300))


def _chair_manual(frame=(74, 144, 186)):
    """Ручная коляска по канону: вид сбоку, перёд вправо, колесо 24\" под спинкой."""
    s, P, R = _chair_canvas("manual")
    TI, ME, UP = (40, 40, 48), (175, 180, 192), (70, 60, 90)
    rw, rim = (0, 305), 280
    aa_circle(s, TI, P(*rw), R(305), R(32))                  # шина
    aa_circle(s, ME, P(*rw), R(rim - 8), R(10))              # обод
    for i in range(18):                                               # спицы
        a = 2 * math.pi * i / 18
        h = 2 * math.pi * (i % 2) / 18 * 0.6
        DR.line(s, ME, P(32 * math.cos(a + h), 305 + 32 * math.sin(a + h)),
                         P((rim - 22) * math.cos(a), 305 + (rim - 22) * math.sin(a)), R(4))
    aa_circle(s, ME, P(*rw), R(40))                          # ступица
    aa_circle(s, (90, 90, 100), P(*rw), R(12))
    aa_circle(s, ME, P(*rw), R(268), R(7))                   # обруч
    DR.line(s, ME, P(0, 35), P(0, 7), R(10))                 # ниппель
    aa_circle(s, TI, P(430, 95), R(95), R(24))               # кастор
    aa_circle(s, ME, P(430, 95), R(30))
    tubes = [  # (точки, цвет, толщина мм)
        ([(-30, 490), (-55, 905)], frame, 22), ([(-55, 905), (-150, 915)], frame, 22),
        ([(-30, 490), (420, 490)], frame, 22), ([(-20, 330), (430, 330)], frame, 22),
        ([(-30, 490), (-20, 330), (0, 305)], frame, 22),
        ([(420, 490), (430, 330), (462, 250)], frame, 22),
        ([(462, 250), (462, 150), (430, 95)], ME, 22),
        ([(410, 470), (590, 150)], frame, 22),
        ([(20, 490), (20, 700), (330, 700), (330, 490)], frame, 22),
        ([(250, 490), (215, 470), (205, 520)], (224, 120, 112), 14),
        ([(250, 490), (285, 600)], (224, 120, 112), 14),
    ]
    for pts, col, w in tubes:
        DR.lines(s, col, False, [P(*q) for q in pts], R(w))
    aa_circle(s, TI, P(285, 600), R(16))                     # ручка тормоза
    DR.line(s, TI, P(545, 150), P(690, 150), R(16))          # подножка
    DR.line(s, UP, P(-25, 530), P(-50, 860), R(55))          # спинка
    x0, y0 = P(-20, 565)
    x1, y1 = P(415, 500)
    aa_rect(s, (154, 116, 216), (x0, y0, x1 - x0, y1 - y0), border_radius=R(25))
    DR.line(s, UP, P(30, 715), P(320, 715), R(30))           # подлокотник
    DR.line(s, TI, P(-95, 913), P(-160, 916), R(30))         # грипса
    return _chair_done(s)


def _chair_power():
    """Электроколяска со средним приводом: вид сбоку, перёд вправо."""
    s, P, R = _chair_canvas("power")
    BASE, SHR, TI = (58, 62, 74), (78, 84, 100), (40, 40, 48)
    ME, UP, CUS = (175, 180, 192), (70, 60, 90), (110, 90, 140)

    def box(x0, y0, x1, y1, col, rad=0):
        a, b = P(x0, y1), P(x1, y0)
        aa_rect(s, col, (a[0], a[1], b[0] - a[0], b[1] - a[1]), border_radius=R(rad) if rad else 0)
    for cx in (-330, 330):                                            # касторы
        DR.line(s, ME, P(cx + 20, 175), P(cx + 20, 120), R(18))
        DR.line(s, ME, P(cx + 20, 120), P(cx, 75), R(14))
        aa_circle(s, TI, P(cx, 75), R(75))
        aa_circle(s, ME, P(cx, 75), R(35))
    box(-390, 150, 400, 270, BASE, 40)                                # база
    box(-250, 170, 230, 250, SHR, 18)                                 # батарейный отсек
    box(-60, 200, 60, 215, (110, 210, 235), 6)
    aa_circle(s, (224, 120, 112), P(-200, 230), R(14))       # предохранитель
    box(-170, 130, -20, 220, (90, 90, 104), 20)                       # мотор-редуктор
    DR.line(s, (232, 200, 64), P(-150, 215), P(-185, 300), R(16))
    aa_circle(s, (232, 200, 64), P(-185, 300), R(16))        # рычаг расцепления
    box(-50, 270, 50, 430, BASE)                                      # стойка сиденья
    aa_circle(s, TI, P(0, 175), R(175))                      # ведущее колесо
    aa_circle(s, ME, P(0, 175), R(120))
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.3
        DR.line(s, (130, 135, 150), P(0, 175), P(105 * math.cos(a), 175 + 105 * math.sin(a)), R(22))
    aa_circle(s, (90, 90, 104), P(0, 175), R(32))
    box(-240, 420, 240, 450, (60, 60, 72), 10)                        # сиденье
    box(-235, 445, 235, 520, CUS, 30)
    DR.polygon(s, UP, [P(-250, 470), P(-150, 470), P(-200, 960), P(-300, 960)])
    DR.line(s, (60, 60, 72), P(-150, 520), P(-150, 650), R(26))
    DR.line(s, (60, 60, 72), P(140, 520), P(140, 650), R(26))
    box(-200, 640, 200, 680, UP, 18)                                  # подлокотник
    box(180, 640, 300, 700, (42, 42, 52), 14)                         # контроллер
    box(195, 668, 240, 684, (110, 210, 235), 4)
    DR.polygon(s, (36, 36, 44), [P(250, 700), P(290, 700), P(282, 725), P(258, 725)])
    DR.line(s, ME, P(270, 722), P(270, 775), R(10))
    aa_circle(s, (224, 120, 112), P(270, 790), R(22))        # джойстик
    DR.lines(s, ME, False, [P(230, 640), P(260, 560), P(250, 440), P(220, 270)], R(7))
    DR.line(s, ME, P(230, 430), P(430, 150), R(20))          # подножка
    DR.line(s, (36, 36, 44), P(400, 140), P(560, 140), R(20))
    return _chair_done(s)


def _mini_chair(s, x, y, col):
    aa_circle(s, col, (x + 26, y), 18, 4)
    aa_circle(s, col, (x, y + 8), 8, 3)
    _ln(s, col, (x - 2, y - 34), (x - 2, y - 8), 4)
    _ln(s, col, (x - 2, y - 8), (x + 22, y - 8), 4)


def _art_bg_workshop():
    s = Surf((1280, 720))
    s.fill((58, 46, 40))
    for y in range(0, 560, 56):
        _ln(s, (48, 38, 33), (0, y), (1280, y), 3)
    DR.rect(s, (40, 32, 28), (0, 560, 1280, 160))
    _ln(s, (30, 24, 21), (0, 560), (1280, 560), 4)
    aa_circle(s, (86, 66, 44), (260, 90), 58)
    aa_circle(s, (110, 84, 52), (260, 90), 34)
    aa_rect(s, (216, 208, 190), (254, 84, 12, 26), border_radius=4)
    aa_circle(s, (250, 214, 120), (260, 78), 7)
    aa_rect(s, (30, 36, 60), (560, 90, 150, 190), border_radius=8)
    aa_circle(s, (222, 224, 200), (635, 150), 26)
    _ln(s, (46, 38, 33), (635, 90), (635, 280), 6)
    _ln(s, (46, 38, 33), (560, 185), (710, 185), 6)
    aa_rect(s, (46, 38, 33), (556, 86, 158, 198), 6, border_radius=8)
    DR.rect(s, (92, 64, 44), (90, 190, 380, 14))
    for tx in range(120, 440, 80):
        aa_rect(s, (140, 116, 82), (tx, 150, 12, 40), border_radius=4)
        aa_circle(s, (140, 116, 82), (tx + 6, 146), 9, 4)
    aa_rect(s, (92, 64, 44), (760, 430, 460, 24), border_radius=4)
    DR.rect(s, (70, 50, 36), (790, 454, 22, 106))
    DR.rect(s, (70, 50, 36), (1160, 454, 22, 106))
    aa_rect(s, (120, 92, 62), (820, 398, 60, 32), border_radius=5)
    aa_circle(s, (86, 66, 44), (1020, 90), 58)
    aa_circle(s, (110, 84, 52), (1020, 90), 34)
    aa_rect(s, (216, 208, 190), (1014, 84, 12, 26), border_radius=4)
    aa_circle(s, (250, 214, 120), (1020, 78), 7)
    return s


def _art_bg_road():
    s = Surf((1280, 720))
    s.fill((24, 26, 44))
    rnd = random.Random(7)
    for _ in range(90):
        s.set_at((rnd.randrange(1280), rnd.randrange(420)), (200, 205, 220))
    aa_circle(s, (226, 226, 206), (1040, 120), 56)
    aa_circle(s, (206, 206, 188), (1022, 104), 12)
    aa_circle(s, (206, 206, 188), (1058, 138), 8)
    DR.polygon(s, (18, 20, 32), [(0, 500), (0, 430), (320, 370), (640, 470),
                                          (960, 390), (1280, 450), (1280, 500)])
    rnd2 = random.Random(3)
    for x in range(20, 1280, 64):
        h = 60 + rnd2.randrange(70)
        DR.polygon(s, (14, 17, 26), [(x, 500), (x + 44, 500), (x + 22, 500 - h)])
    DR.rect(s, (34, 30, 36), (0, 500, 1280, 220))
    DR.polygon(s, (54, 48, 54), [(560, 720), (830, 720), (692, 520), (630, 520)])
    for t in range(6):
        y0 = 700 - t * 32
        aa_rect(s, (96, 88, 96), (688 - t * 9, y0, 10 - t, 14 - t * 2), border_radius=3)
    return s


def _art_bg_garage():
    s = Surf((1280, 720))
    s.fill((46, 40, 56))
    DR.rect(s, (36, 32, 44), (0, 520, 1280, 200))
    for cx in (240, 640, 1040):
        aa_circle(s, (74, 62, 66), (cx, 60), 66)
        aa_circle(s, (96, 80, 68), (cx, 60), 36)
        DR.polygon(s, (60, 54, 66), [(cx - 22, 34), (cx + 22, 34), (cx + 10, 12), (cx - 10, 12)])
    cols = [(150, 120, 200), (110, 200, 180), (208, 178, 120), (200, 130, 140), (120, 160, 210)]
    for row, sy in ((0, 220), (1, 440)):
        DR.rect(s, (92, 64, 44), (70, sy, 1140, 16))
        DR.rect(s, (70, 50, 36), (100, sy + 16, 16, 60))
        DR.rect(s, (70, 50, 36), (1164, sy + 16, 16, 60))
        for i, x in enumerate(range(150, 1150, 210)):
            _mini_chair(s, x, sy - 22, cols[(i + row * 2) % len(cols)])
    return s


def _art_bg_party():
    s = Surf((1280, 720))
    s.fill((30, 26, 50))
    DR.rect(s, (38, 34, 46), (0, 560, 1280, 160))
    DR.polygon(s, (24, 22, 40), [(0, 560), (0, 470), (400, 530), (900, 460), (1280, 540), (1280, 560)])
    bulbs = [(240, 190, 90), (110, 210, 235), (230, 120, 130), (140, 220, 140), (180, 140, 240)]
    for row, (y0, sag) in enumerate(((90, 70), (170, 60))):
        pts = [(x, y0 + int(sag * math.sin(math.pi * x / 1280))) for x in range(0, 1281, 40)]
        for a, b in zip(pts, pts[1:]):
            _ln(s, (70, 64, 88), a, b, 2)
        for i, p in enumerate(pts[1:-1:2]):
            aa_circle(s, bulbs[(i + row) % len(bulbs)], (p[0], p[1] + 8), 7)
    for lx, ly in ((160, 300), (520, 260), (900, 310), (1180, 260)):
        aa_rect(s, (208, 150, 74), (lx - 16, ly, 32, 44), border_radius=10)
        aa_rect(s, (240, 190, 90), (lx - 9, ly + 10, 18, 24), border_radius=6)
    aa_rect(s, (74, 56, 48), (120, 560, 300, 20), border_radius=6)
    DR.rect(s, (60, 46, 40), (140, 580, 18, 70))
    DR.rect(s, (60, 46, 40), (382, 580, 18, 70))
    for bx in (180, 240, 300, 350):
        aa_rect(s, (140, 180, 150), (bx, 528, 14, 32), border_radius=5)
    return s


def _art_bg_guild():
    s = Surf((1280, 720))
    s.fill((54, 56, 66))
    for y in range(0, 540, 60):
        _ln(s, (44, 46, 54), (0, y), (1280, y), 3)
        off = 60 if (y // 60) % 2 else 0
        for x in range(off, 1280, 120):
            _ln(s, (44, 46, 54), (x, y), (x, y + 60), 3)
    DR.rect(s, (42, 44, 52), (0, 540, 1280, 180))
    aa_rect(s, (18, 40, 64), (170, 110, 430, 310), border_radius=6)
    aa_rect(s, (110, 140, 170), (170, 110, 430, 310), 4, border_radius=6)
    for gx in range(210, 600, 48):
        _ln(s, (26, 52, 80), (gx, 118), (gx, 412), 1)
    for gy in range(150, 420, 48):
        _ln(s, (26, 52, 80), (178, gy), (592, gy), 1)
    aa_circle(s, (200, 225, 245), (460, 300), 74, 2)
    aa_circle(s, (200, 225, 245), (460, 300), 8, 2)
    _ln(s, (200, 225, 245), (255, 240), (330, 240), 2)
    _ln(s, (200, 225, 245), (255, 240), (255, 175), 2)
    _ln(s, (200, 225, 245), (330, 242), (460, 300), 2)
    aa_circle(s, (200, 225, 245), (300, 350), 26, 2)
    _ln(s, (140, 170, 200), (255, 150), (255, 160), 2)
    _ln(s, (140, 170, 200), (540, 210), (540, 385), 1)
    aa_circle(s, (150, 130, 90), (890, 170), 80, 10)
    for i in range(6):
        a = i * math.pi / 3
        _ln(s, (150, 130, 90), (890, 170),
            (890 + int(70 * math.cos(a)), 170 + int(70 * math.sin(a))), 6)
    aa_circle(s, (150, 130, 90), (890, 170), 14)
    _ln(s, (96, 88, 76), (660, 560), (730, 440), 10)
    _ln(s, (96, 88, 76), (800, 560), (730, 440), 10)
    aa_circle(s, (205, 210, 225), (730, 408), 58, 6)
    aa_rect(s, (96, 88, 76), (640, 556, 180, 14), border_radius=5)
    for cx in (120, 1235):
        aa_circle(s, (86, 66, 44), (cx, 330), 40)
        aa_circle(s, (240, 190, 90), (cx, 330), 12)
        aa_rect(s, (70, 60, 52), (cx - 7, 342, 14, 60), border_radius=5)
    return s


VECTOR_ART = {
    "martin": _art_martin,
    "ghost": _art_ghost,
    "master": _art_master,
    "client_elf": _art_client_elf,
    "client_dwarf": _art_client_dwarf,
    "client_fairy": _art_client_fairy,
    "client_orc": _art_client_orc,
    "client_troll": _art_client_troll,
    "client_goblin": _art_client_goblin,
    "client_sorceress": _art_client_sorceress,
    "client_golem": _art_client_golem,
    "client_centaur": _art_client_centaur,
    "chair_basic": _chair_manual,
    "gag_leg": _art_gag_leg,
    "chair_power": _chair_power,
    "chair_edge4": _chair_power,
    "chair_trident": _chair_power,
    "chair_elf": lambda: _chair_manual((110, 170, 110)),
    "chair_dwarf": lambda: _chair_manual((160, 118, 74)),
    "chair_fairy": lambda: _chair_manual((216, 140, 190)),
    "chair_orc": lambda: _chair_manual((124, 114, 92)),
    "chair_troll": lambda: _chair_manual((112, 112, 126)),
    "bg_workshop": _art_bg_workshop,
    "bg_road": _art_bg_road,
    "bg_garage": _art_bg_garage,
    "bg_party": _art_bg_party,
    "bg_guild": _art_bg_guild,
}

# Цвет рамы 3D-модели ручной коляски — под арт коляски клиента
CHAIR3D_FRAME = {
    "chair_basic.png": (70, 72, 80), "chair_elf.png": (176, 206, 48),
    "chair_dwarf.png": (96, 40, 66), "chair_fairy.png": (236, 172, 200),     # Вольф: бордовая рама Quickie 2
    "chair_orc.png": (56, 56, 62), "chair_troll.png": (70, 72, 80),
}

# Хотспоты деталей на схеме коляски (координаты в рамке 380x300 рисовальщиков).
# Посчитаны из мм чертежа через CHAIR_GEOM (art_tests/build_assets.py) — совпадают
# и с векторной схемой, и с PNG-артом из assets/.
CHAIR_HOTSPOTS = {
    "manual": {
        "tire": (63, 266, 18), "rim": (50, 167, 13), "spokes": (115, 243, 15),
        "axle": (130, 200, 12), "bearing": (152, 206, 12), "rear_wheel": (177, 251, 20),
        "tube": (95, 282, 12), "valve": (130, 287, 12),
        "caster": (263, 265, 20), "caster_stem": (273, 232, 12),
        "brake": (213, 124, 15), "seat": (242, 142, 11), "cushion": (167, 129, 11),
        "footrest": (322, 248, 15), "frame": (261, 167, 13), "bolts": (136, 108, 11),
    },
    "power": {
        "controller": (239, 93, 13), "joystick": (248, 54, 13), "boot": (248, 80, 9),
        "battery": (228, 233, 14), "fuse": (107, 225, 9), "wiring": (243, 138, 13),
        "motor": (134, 242, 14), "freewheel": (111, 204, 11), "frame": (65, 230, 14),
        "axle": (167, 242, 12),
    },
}


# ----------------------------------------------------------------------------- #
#  3D-осмотр: софтверный рендерер на чистом Python (без numpy — у py3.14 его нет).
#  Модели построены в реальных мм по тем же чертежам, что и 2D-схемы
#  (x — вперёд, y — вверх, z — вбок, пол y=0): трубы, торы шин и ободов, спицы.
#  Свет — студийный (ключевой + заполняющий + блик на металле), сортировка граней
#  по глубине, отсечение задних граней у замкнутых тел, сглаживание суперсэмплингом.
# ----------------------------------------------------------------------------- #
M_DOUBLE, M_METAL, M_EDGE = 1, 2, 4        # флаги граней: двусторонняя, металл, контур


class Mesh3D:
    def __init__(self):
        self.verts = []
        self.faces = []                     # (индексы, part, цвет, флаги)

    def v(self, p):
        self.verts.append(p)
        return len(self.verts) - 1

    def face(self, idx, part, col, flags=0):
        self.faces.append((tuple(idx), part, col, flags))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    ln = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) or 1.0
    return (a[0] / ln, a[1] / ln, a[2] / ln)


def m_tube(m, pts, r, part, col, sides=8, flags=M_METAL, caps=False):
    """Труба по ломаной (каждый отрезок — отдельный цилиндр)."""
    for a, b in zip(pts, pts[1:]):
        d = _norm(_sub(b, a))
        up = (0, 1, 0) if abs(d[1]) < 0.9 else (1, 0, 0)
        u = _norm(_cross(d, up))
        w = _cross(d, u)
        ra, rb = [], []
        for i in range(sides):
            an = 2 * math.pi * i / sides
            o = (u[0] * math.cos(an) + w[0] * math.sin(an), u[1] * math.cos(an) + w[1] * math.sin(an),
                 u[2] * math.cos(an) + w[2] * math.sin(an))
            ra.append(m.v((a[0] + o[0] * r, a[1] + o[1] * r, a[2] + o[2] * r)))
            rb.append(m.v((b[0] + o[0] * r, b[1] + o[1] * r, b[2] + o[2] * r)))
        for i in range(sides):
            j = (i + 1) % sides
            m.face((ra[i], ra[j], rb[j], rb[i]), part, col, flags)
        if caps:
            m.face(list(reversed(ra)), part, col, flags)
            m.face(rb, part, col, flags)


def m_torus(m, c, R, r, part, col, segs=24, sides=6, flags=0, z_scale=1.0, inner=None):
    """Тор в плоскости XY (ось — z): шины, обручи, ободы.
    inner=(part, col) — внутренняя сторона сечения (у шины это камера у обода)."""
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for k in range(sides):
            b = 2 * math.pi * k / sides
            rr = R + r * math.cos(b)
            ring.append(m.v((c[0] + rr * ca, c[1] + rr * sa, c[2] + r * math.sin(b) * z_scale)))
        rings.append(ring)
    for i in range(segs):
        A, B = rings[i], rings[(i + 1) % segs]
        for k in range(sides):
            kk = (k + 1) % sides
            pp, cc = part, col
            if inner and math.cos(2 * math.pi * (k + 0.5) / sides) < -0.55:
                pp, cc = inner
            m.face((A[k], B[k], B[kk], A[kk]), pp, cc, flags)


def m_box(m, x0, x1, y0, y1, z0, z1, part, col, flags=M_EDGE):
    p = [m.v(q) for q in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                          (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (1, 2, 6, 5), (0, 4, 7, 3)):
        m.face([p[i] for i in q], part, col, flags)


def m_prism(m, poly, z0, z1, part, col, flags=M_EDGE):
    """Многоугольник в плоскости XY (против часовой), вытянутый по z."""
    a = [m.v((x, y, z0)) for x, y in poly]
    b = [m.v((x, y, z1)) for x, y in poly]
    n = len(poly)
    m.face(list(reversed(a)), part, col, flags)
    m.face(b, part, col, flags)
    for i in range(n):
        j = (i + 1) % n
        m.face((a[i], a[j], b[j], b[i]), part, col, flags)


def m_spoke_wheel(m, c, z, R_tire, part_prefix, frame_col, spokes=18, pushrim=True):
    """Заднее колесо ручной коляски: шина, камера, обод, спицы с выносом, ступица, обруч."""
    TI, RIM, SP = (48, 48, 56), (200, 205, 218), (170, 175, 188)
    m_torus(m, (c[0], c[1], z), R_tire - 17, 17, "tire", TI, segs=30, sides=7, inner=("tube", (128, 58, 50)))
    m_torus(m, (c[0], c[1], z), R_tire - 44, 10, "rim", RIM, segs=30, sides=4, flags=M_METAL, z_scale=1.4)
    sgn = 1 if z > 0 else -1
    for i in range(spokes):                                     # спицы на два фланца
        a = 2 * math.pi * i / spokes
        fz = z + (26 if i % 2 else -26)
        h = (c[0] + 34 * math.cos(a + 0.35 * (1 if i % 2 else -1)), c[1] + 34 * math.sin(a + 0.35 * (1 if i % 2 else -1)), fz)
        e = (c[0] + (R_tire - 52) * math.cos(a), c[1] + (R_tire - 52) * math.sin(a), z)
        m_tube(m, [h, e], 2.2, "spokes", SP, sides=3)
    m_tube(m, [(c[0], c[1], z - 32), (c[0], c[1], z + 32)], 26, "rear_wheel", RIM, sides=10, caps=True)
    for fz in (z - 30, z + 30):                                 # подшипники в ступице
        m_torus(m, (c[0], c[1], fz), 20, 6, "bearing", (214, 178, 92), segs=12, sides=4, flags=M_METAL)
    m_tube(m, [(c[0], c[1], z - 60 * sgn), (c[0], c[1], z + 48 * sgn)], 7, "axle", (150, 155, 168), sides=6)
    m_box(m, c[0] - 6, c[0] + 6, c[1] - 6, c[1] + 40, z + 48 * sgn - 4, z + 48 * sgn + 4, "axle", (60, 60, 70))
    a = -math.pi / 2                                            # ниппель внизу обода
    m_tube(m, [(c[0], c[1] - (R_tire - 50), z), (c[0], c[1] - (R_tire - 24), z)], 5, "valve", (226, 188, 90), sides=5)
    if pushrim:
        pz = z + 38 * sgn
        m_torus(m, (c[0], c[1], pz), R_tire - 40, 8, "rear_wheel", (188, 194, 210), segs=30, sides=5, flags=M_METAL)
        for i in range(6):
            a = 2 * math.pi * i / 6 + 0.2
            p = (c[0] + (R_tire - 42) * math.cos(a), c[1] + (R_tire - 42) * math.sin(a))
            m_tube(m, [(p[0], p[1], z + 6 * sgn), (p[0], p[1], pz)], 4, "rear_wheel", (160, 165, 178), sides=4)


def _m_caster(m, c, z, R, stem_top, part_wheel="caster", part_stem="caster_stem"):
    m_torus(m, (c[0], c[1], z), R - 13, 13, part_wheel, (48, 48, 56), segs=18, sides=6)
    m_tube(m, [(c[0], c[1], z - 16), (c[0], c[1], z + 16)], R * 0.42, part_wheel, (150, 156, 170), sides=10,
           flags=M_METAL, caps=True)
    sx = stem_top[0]
    for fz in (z - 22, z + 22):                                 # вилка
        m_tube(m, [(sx, stem_top[1] - 40, fz), (c[0], c[1], fz)], 7, part_stem, (175, 180, 192), sides=5)
    m_box(m, sx - 16, sx + 16, stem_top[1] - 48, stem_top[1] - 34, z - 26, z + 26, part_stem, (175, 180, 192))
    m_tube(m, [(sx, stem_top[1] - 40, z), (sx, stem_top[1] + 10, z)], 15, part_stem, (150, 155, 168), sides=8, caps=True)


def _build_chair3d_manual(frame=(74, 144, 186)):
    m = Mesh3D()
    FR, UP, CUS = frame, (70, 60, 90), (154, 116, 216)
    for s in (-1, 1):
        zf, zw = 235 * s, 300 * s
        m_spoke_wheel(m, (0, 305), zw, 307, "", FR)
        m_tube(m, [(-30, 490, zf), (-55, 905, zf), (-150, 915, zf)], 12, "frame", FR)        # стойка+ручка
        m_tube(m, [(-95, 913, zf), (-165, 916, zf)], 17, "frame", (40, 40, 48), sides=8, flags=0, caps=True)
        m_tube(m, [(-30, 490, zf), (420, 490, zf), (430, 330, zf), (462, 250, zf)], 12, "frame", FR)
        m_tube(m, [(-20, 330, zf), (430, 330, zf)], 11, "frame", FR)
        m_tube(m, [(-30, 490, zf), (-20, 330, zf), (0, 305, zf)], 12, "frame", FR)
        m_tube(m, [(410, 470, zf), (590, 150, zf)], 11, "footrest", FR)
        m_box(m, 545, 690, 138, 158, 40 * s if s > 0 else -220, 220 if s > 0 else -40, "footrest", (52, 52, 62))
        m_tube(m, [(20, 490, zf), (20, 700, zf), (330, 700, zf), (330, 490, zf)], 10, "frame", FR)
        m_box(m, 30, 320, 700, 730, zf - 28, zf + 28, "frame", UP)                         # подлокотник
        _m_caster(m, (430, 95), 230 * s, 95, (462, 250))
        # тормоз: зажим на раме, рычаг с ручкой, колодка упирается в шину
        bz = 268 * s
        m_box(m, 228, 262, 470, 500, bz - 12, bz + 12, "brake", (224, 120, 112))
        m_tube(m, [(250, 490, bz), (290, 610, bz)], 8, "brake", (224, 120, 112), sides=6)
        m_tube(m, [(286, 600, bz), (296, 632, bz)], 16, "brake", (40, 40, 48), sides=8, flags=0, caps=True)
        m_box(m, 210, 236, 506, 532, min(bz - 10 * s, bz + 16 * s), max(bz - 10 * s, bz + 16 * s), "brake",
              (90, 90, 100))
        for bp in ((-12, 318), (-36, 530), (-44, 700), (22, 600), (424, 470)):            # болты
            m_tube(m, [(bp[0], bp[1], zf + 10 * s), (bp[0], bp[1], zf + 22 * s)], 9, "bolts",
                   (214, 178, 92), sides=6, caps=True)
    for s in (-1, 1):                                                                      # X-крестовина
        m_tube(m, [(60, 330, -235 * s), (360, 488, 235 * s)], 9, "frame", FR)
    m_box(m, -30, 420, 482, 494, -235, 235, "seat", (60, 56, 76))                           # сиденье-гамак
    m_box(m, -15, 410, 494, 560, -222, 222, "cushion", CUS)
    back = [(-38, 520), (-20, 520), (-46, 880), (-64, 880)]                                 # спинка
    m_prism(m, back, -235, 235, "seat", UP)
    return m


def _build_chair3d_power():
    m = Mesh3D()
    BASE, SHR, UP, CUS, ME = (58, 62, 74), (78, 84, 100), (70, 60, 90), (110, 90, 140), (175, 180, 192)
    m_box(m, -390, 400, 150, 270, -230, 230, "frame", BASE)                                 # шасси
    m_box(m, -200, 200, 270, 330, -180, 180, "battery", SHR)                                # батарея
    m_box(m, -190, -150, 300, 322, 180, 196, "fuse", (224, 120, 112))
    m_box(m, -60, 60, 300, 316, 180, 186, "battery", (110, 210, 235))
    m_tube(m, [(0, 330, 0), (0, 425, 0)], 42, "frame", BASE, sides=10, flags=M_EDGE, caps=True)
    for s in (-1, 1):
        z = 272 * s
        m_torus(m, (0, 175, z), 142, 22, "axle", (48, 48, 56), segs=28, sides=7)            # ведущее колесо
        m_tube(m, [(0, 175, z - 26), (0, 175, z + 26)], 118, "axle", ME, sides=16, flags=M_METAL, caps=True)
        m_tube(m, [(0, 175, z + 26 * s), (0, 175, z + 40 * s)], 34, "axle", (90, 90, 104), sides=10, caps=True)
        m_tube(m, [(-20, 175, 120 * s), (-20, 175, 246 * s)], 56, "motor", (90, 90, 104), sides=12, flags=M_METAL, caps=True)
        m_tube(m, [(-60, 228, 190 * s), (-90, 320, 205 * s)], 9, "freewheel", (232, 200, 64), sides=6)
        m_tube(m, [(-92, 316, 205 * s), (-94, 340, 205 * s)], 15, "freewheel", (232, 200, 64), sides=8, caps=True)
        for cx in (-330, 330):                                                              # касторы
            _m_caster(m, (cx, 75), 200 * s, 75, (cx + 22, 175), "frame", "frame")
        m_tube(m, [(-150, 520, 255 * s), (-150, 650, 255 * s)], 13, "frame", (60, 60, 72))
        m_tube(m, [(140, 520, 255 * s), (140, 650, 255 * s)], 13, "frame", (60, 60, 72))
        m_box(m, -200, 200, 640, 680, 230 * s if s > 0 else -282, 282 if s > 0 else -230, "frame", UP)
        m_tube(m, [(230, 430, 120 * s), (430, 150, 120 * s)], 12, None, ME)
    m_box(m, -240, 240, 420, 450, -240, 240, "frame", (60, 60, 72))                          # сиденье
    m_box(m, -235, 235, 450, 520, -230, 230, None, CUS)
    m_prism(m, [(-250, 470), (-150, 470), (-200, 960), (-300, 960)], -230, 230, None, UP)  # спинка
    m_box(m, 400, 560, 130, 150, -200, 200, None, (36, 36, 44))                             # подножка
    m_box(m, 180, 300, 640, 700, 228, 290, "controller", (42, 42, 52))                      # контроллер
    m_box(m, 196, 244, 700, 703, 236, 282, "controller", (110, 210, 235), flags=0)
    m_tube(m, [(270, 700, 259), (270, 728, 259)], 15, "boot", (30, 30, 36), sides=8, flags=0, caps=True)
    m_tube(m, [(270, 728, 259), (270, 780, 259)], 6, "joystick", ME, sides=6)
    m_tube(m, [(270, 776, 259), (270, 806, 259)], 17, "joystick", (224, 120, 112), sides=8, flags=0, caps=True)
    m_tube(m, [(232, 642, 262), (262, 560, 262), (252, 440, 250), (222, 275, 232)], 6, "wiring", (190, 190, 200), sides=5)
    return m


# ----------------------------------------------------------------------------- #
#  Permobil M3 Corpus — электроколяска со средним приводом (6 колёс).
#  Размеры по инструкции пользователя M3 Corpus (модель 3): длина 1016 мм,
#  ширина 650–790 мм, высота 960–1170 мм, масса с батареями 176 кг; шины ведущих
#  колёс 200–250 кПа, болты колеса 22 Н·м (сервисный мануал Power Platform).
#  Оси: x — вперёд, y — вверх (пол 0), z — вбок; мм. Одна геометрия на 2D и 3D.
# ----------------------------------------------------------------------------- #
M3 = dict(drive=(0, 170, 170), front=(330, 95, 95), rear=(-335, 95, 95),
          chassis=(-380, 340, 140, 300), seat_y=440, half_w=300)
M3_ACCENT = (104, 64, 150)              # цвет кожухов (под мантию Моры)


def _m3_side(s, P, R, accent=M3_ACCENT):
    """Схема M3 Corpus сбоку (перёд вправо). P(x, y) -> пиксели, R(мм) -> пиксели."""
    TI, ME, DK, GR = (40, 40, 48), (175, 180, 192), (52, 54, 62), (80, 84, 96)
    UP, CUS = (58, 52, 74), (82, 74, 104)

    def box(x0, y0, x1, y1, col, rad=0):
        a, b = P(x0, y1), P(x1, y0)
        aa_rect(s, col, (a[0], a[1], b[0] - a[0], b[1] - a[1]), border_radius=R(rad) if rad else 0)

    def wheel(c, r, hub, tread=False):
        aa_circle(s, TI, P(c[0], c[1]), R(r))
        if tread:
            for i in range(16):
                a = 2 * math.pi * i / 16
                aa_circle(s, (28, 28, 34), P(c[0] + (r - 6) * math.cos(a), c[1] + (r - 6) * math.sin(a)), R(9))
        aa_circle(s, ME, P(c[0], c[1]), R(hub))
        aa_circle(s, GR, P(c[0], c[1]), R(hub * 0.45))
    # задний кастор и вилка
    rx, ry, rr = M3["rear"]
    DR.line(s, ME, P(rx + 25, 230), P(rx + 25, 175), R(16))
    DR.line(s, ME, P(rx + 25, 175), P(rx, ry), R(12))
    wheel((rx, ry), rr, 45)
    # шасси: нижняя база, кожух с акцентом, батарейный отсек
    box(-380, 140, 340, 300, DK, 45)
    box(-300, 230, 250, 300, accent, 30)
    box(-250, 160, -40, 225, GR, 12)                        # крышка батарейного отсека
    aa_circle(s, (224, 120, 112), P(-355, 250), R(13))   # автомат/предохранитель сзади
    # передняя подвеска: маятник и пружина
    fx, fy, fr = M3["front"]
    DR.line(s, ME, P(200, 215), P(fx + 15, 215), R(22))
    for i in range(5):
        DR.line(s, (214, 178, 92), P(225 + i * 9, 230), P(232 + i * 9, 290), R(6))
    DR.line(s, ME, P(fx + 15, 215), P(fx + 15, 165), R(16))
    DR.line(s, ME, P(fx + 15, 165), P(fx, fy), R(12))
    wheel((fx, fy), fr, 45)
    # ведущее колесо с мотором и рычагом расцепления
    dx, dy, dr = M3["drive"]
    box(-95, 120, 40, 230, GR, 30)                          # мотор-редуктор за колесом
    wheel((dx, dy), dr, 70, tread=True)
    DR.line(s, (232, 200, 64), P(-95, 235), P(-130, 300), R(14))
    aa_circle(s, (232, 200, 64), P(-130, 300), R(14))
    # подъёмник сиденья и сиденье
    box(-60, 300, 60, 430, DK)
    box(-250, 420, 230, 450, GR, 10)
    box(-245, 445, 225, 525, CUS, 35)
    # спинка (слегка откинута) и подголовник
    DR.polygon(s, UP, [P(-250, 470), P(-150, 480), P(-215, 1000), P(-320, 990)])
    box(-330, 1040, -205, 1170, UP, 40)
    DR.line(s, GR, P(-265, 995), P(-265, 1045), R(14))
    # подлокотник со стойками, пульт, пыльник, джойстик, кабель
    DR.line(s, DK, P(-140, 450), P(-140, 690), R(24))
    DR.line(s, DK, P(120, 450), P(120, 690), R(24))
    box(-210, 685, 200, 725, CUS, 18)
    box(200, 690, 320, 745, (36, 36, 44), 14)               # пульт управления
    box(215, 722, 265, 736, (110, 210, 235), 4)             # экранчик
    DR.polygon(s, (30, 30, 36), [P(258, 745), P(298, 745), P(290, 770), P(266, 770)])  # пыльник
    DR.line(s, ME, P(278, 768), P(278, 815), R(10))
    aa_circle(s, (224, 120, 112), P(278, 830), R(22))
    DR.lines(s, ME, False, [P(220, 690), P(170, 600), P(140, 470), P(120, 305)], R(7))
    # центральная подножка и площадка
    DR.line(s, ME, P(200, 440), P(400, 170), R(26))
    DR.polygon(s, (36, 36, 44), [P(370, 150), P(590, 150), P(585, 128), P(372, 128)])


def _m3_fit():
    """Вписать M3 в рамку 380x300 (как build_assets) -> (AX, AY, k)."""
    x0, x1, y1 = -430, 590, 1170
    k = min((380 - 12) / (x1 - x0), (300 - 12) / y1)
    fx0 = (380 - (x1 - x0) * k) / 2
    return round(fx0 + (0 - x0) * k, 2), round(6 + y1 * k, 2), round(k, 5)


CHAIR_GEOM["m3"] = _m3_fit()


def _chair_m3():
    """Permobil M3 Corpus сбоку, 380x300 (векторная заглушка и точки клика)."""
    s, P, R = _chair_canvas("m3")
    _m3_side(s, P, R)
    return _chair_done(s)


def _build_chair3d_m3(accent=M3_ACCENT):
    m = Mesh3D()
    DK, GR, ME, TI = (52, 54, 62), (80, 84, 96), (175, 180, 192), (40, 40, 48)
    UP, CUS = (58, 52, 74), (82, 74, 104)
    W = M3["half_w"]
    # шасси и кожухи
    m_box(m, -380, 340, 140, 300, -220, 220, "frame", DK)
    m_box(m, -300, 250, 300, 312, -205, 205, "frame", accent)
    m_box(m, -250, -40, 160, 225, 218, 224, "battery", GR)               # крышка батарейного отсека
    m_box(m, -250, -40, 160, 225, -224, -218, "battery", GR)
    m_box(m, -240, -60, 170, 280, -150, 150, "battery", (46, 46, 54))     # сами батареи внутри
    m_box(m, -392, -378, 230, 270, -30, 30, "fuse", (224, 120, 112))     # автомат сзади
    for s_ in (-1, 1):
        z = (W - 20) * s_
        # ведущее колесо: шина с протектором, диск, мотор, рычаг расцепления
        dx, dy, dr = M3["drive"]
        m_torus(m, (dx, dy, z), dr - 30, 30, "axle", TI, segs=28, sides=7, inner=("axle", (36, 36, 42)))
        for i in range(20):
            a = 2 * math.pi * i / 20
            cx, cy = dx + (dr - 4) * math.cos(a), dy + (dr - 4) * math.sin(a)
            m_box(m, cx - 9, cx + 9, cy - 9, cy + 9, z - 30, z + 30, "axle", (28, 28, 34), flags=0)
        m_tube(m, [(dx, dy, z - 26 * s_), (dx, dy, z + 26 * s_)], 105, "axle", ME, sides=14, flags=M_METAL, caps=True)
        m_tube(m, [(dx, dy, z + 26 * s_), (dx, dy, z + 34 * s_)], 40, "axle", GR, sides=10, caps=True)
        m_tube(m, [(-30, 175, (W - 70) * s_), (-30, 175, (W - 175) * s_)], 62, "motor", GR, sides=12, flags=M_METAL, caps=True)
        m_tube(m, [(-95, 235, (W - 95) * s_), (-130, 300, (W - 95) * s_)], 8, "freewheel", (232, 200, 64), sides=6)
        m_tube(m, [(-128, 296, (W - 95) * s_), (-132, 316, (W - 95) * s_)], 14, "freewheel", (232, 200, 64), sides=8, caps=True)
        # передний маятник с пружиной и кастором; задний кастор
        fx, fy, fr = M3["front"]
        zc = (W - 70) * s_
        m_tube(m, [(150, 215, zc), (fx + 15, 215, zc)], 14, "frame", ME)
        m_tube(m, [(228, 230, zc), (228, 292, zc)], 16, "frame", (214, 178, 92), sides=8)
        _m_caster(m, (fx, fy), zc, fr, (fx + 15, 215), "frame", "frame")
        rx, ry, rr = M3["rear"]
        _m_caster(m, (rx, ry), zc, rr, (rx + 25, 230), "frame", "frame")
        # стойки подлокотника
        m_tube(m, [(-140, 450, (W - 40) * s_), (-140, 690, (W - 40) * s_)], 14, "frame", DK)
        m_tube(m, [(120, 450, (W - 40) * s_), (120, 690, (W - 40) * s_)], 14, "frame", DK)
        m_box(m, -210, 200, 685, 725, (W - 75) * s_ if s_ > 0 else -(W - 5), (W - 5) if s_ > 0 else -(W - 75),
              None, CUS)
    # подъёмник, сиденье, подушка
    m_tube(m, [(0, 300, 0), (0, 430, 0)], 55, "frame", DK, sides=12, flags=M_EDGE, caps=True)
    m_box(m, -250, 230, 420, 450, -230, 230, "frame", GR)
    m_box(m, -245, 225, 445, 525, -225, 225, None, CUS)
    # анатомическая спинка с боковыми валиками и подголовник
    m_prism(m, [(-250, 470), (-150, 480), (-215, 1000), (-320, 990)], -215, 215, None, UP)
    for s_ in (-1, 1):
        m_prism(m, [(-235, 520), (-170, 525), (-225, 900), (-290, 895)], 200 * s_ - 18, 200 * s_ + 18, None, (70, 62, 90))
    m_box(m, -330, -205, 1040, 1170, -120, 120, None, UP)
    m_tube(m, [(-265, 995, 0), (-265, 1045, 0)], 14, "frame", GR)
    # пульт управления на правом подлокотнике: контроллер, пыльник, джойстик, кабель
    zr = W - 40
    m_box(m, 200, 320, 690, 745, zr - 45, zr + 45, "controller", (36, 36, 44))
    m_box(m, 215, 265, 745, 748, zr - 30, zr + 30, "controller", (110, 210, 235), flags=0)
    m_tube(m, [(278, 745, zr), (278, 770, zr)], 18, "boot", (30, 30, 36), sides=8, flags=0, caps=True)
    m_tube(m, [(278, 770, zr), (278, 815, zr)], 6, "joystick", ME, sides=6)
    m_tube(m, [(278, 812, zr), (278, 846, zr)], 20, "joystick", (224, 120, 112), sides=8, flags=0, caps=True)
    m_tube(m, [(220, 690, zr), (170, 600, zr), (140, 470, zr - 10), (120, 305, zr - 40)], 6, "wiring", (190, 190, 200), sides=5)
    # центральная подножка
    m_tube(m, [(200, 440, 0), (400, 170, 0)], 20, "frame", ME)
    m_box(m, 370, 590, 128, 150, -170, 170, None, (36, 36, 44))
    return m


VECTOR_ART["chair_m3"] = _chair_m3
# вторая волна: если PNG вдруг нет — ближайший векторный аналог (коляска того же типа, похожий клиент)
for _k, _v in {"chair_aeroz": "chair_basic", "chair_cross6": "chair_basic", "chair_iris": "chair_basic",
               "chair_focuscr": "chair_basic", "chair_whillc2": "chair_power", "chair_f5": "chair_power",
               "chair_pulse6": "chair_power", "chair_q6edge": "chair_power",
               "client_aeroz": "client_elf", "client_cross6": "client_dwarf", "client_iris": "client_fairy",
               "client_focuscr": "client_sorceress", "client_iris_mom": "client_fairy", "client_focuscr_grandson": "client_sorceress",
               "client_whillc2": "client_goblin", "client_f5": "client_troll",
               # третья волна (фольклорные клиенты)
               "chair_yaga": "chair_basic", "chair_rusalka": "chair_basic", "chair_ra": "chair_basic",
               "chair_leshy": "chair_power", "chair_gorynych": "chair_power",
               "client_yaga": "client_sorceress", "client_rusalka": "client_elf", "client_mummy": "client_dwarf",
               "client_leshy": "client_troll", "client_gorynych": "client_golem"}.items():
    VECTOR_ART.setdefault(_k, VECTOR_ART[_v])
# точки клика реальных колясок — по их арту (art_tests/hotspots_<модель>.json)
CHAIR_HOTSPOTS["inv9000"] = {"tire": (90, 262, 12), "rim": (55, 150, 11), "spokes": (112, 202, 12), "tube": (132, 240, 10), "valve": (90, 128, 9), "brake": (150, 160, 10)}
CHAIR_HOTSPOTS["xdt"] = {"cushion": (190, 120, 14), "seat": (225, 150, 10), "frame": (200, 195, 11), "valve": (258, 128, 8)}
CHAIR_HOTSPOTS["ego"] = {"caster": (225, 265, 12), "caster_stem": (225, 228, 9), "bearing": (322, 232, 9), "bolts": (340, 182, 8), "brake": (215, 110, 9), "tire": (55, 240, 12)}
CHAIR_HOTSPOTS["quickie2"] = CHAIR_HOTSPOTS["tekna"] = {"tire": (30, 200, 11), "rear_wheel": (95, 205, 13), "brake": (175, 140, 10), "bolts": (205, 172, 8), "frame": (300, 130, 12)}
CHAIR_HOTSPOTS["exelle_jr"] = {"rim": (55, 140, 11), "spokes": (142, 202, 12), "bearing": (107, 175, 8), "tube": (140, 262, 10), "bolts": (275, 145, 8)}
CHAIR_HOTSPOTS["noir"] = {"axle": (125, 175, 9), "bearing": (150, 168, 8), "rear_wheel": (120, 240, 13), "tire": (55, 140, 11), "brake": (230, 145, 9)}
CHAIR_HOTSPOTS["edge4"] = {"controller": (206, 74, 10), "wiring": (200, 165, 8), "battery": (180, 222, 12), "fuse": (140, 240, 8), "motor": (228, 255, 10), "seat_lift": (224, 184, 11), "actuator": (180, 172, 9), "armrest": (150, 92, 10), "seat": (165, 128, 12), "freewheel": (206, 240, 8)}
CHAIR_HOTSPOTS["trident"] = {"controller": (160, 108, 10), "wiring": (185, 150, 9), "battery": (215, 190, 12), "freewheel": (130, 205, 9), "motor": (195, 225, 11), "axle": (160, 242, 9), "frame": (108, 168, 10)}
# точки клика M3 расставлены по арту assets/chair_m3.png (art_tests/hotspots_m3.json)
CHAIR_HOTSPOTS["m3"] = {"joystick": (222, 80, 11), "boot": (214, 98, 7), "controller": (230, 110, 11), "wiring": (190, 132, 11), "battery": (160, 232, 14), "fuse": (98, 222, 9), "motor": (196, 252, 12), "freewheel": (130, 212, 10), "axle": (166, 250, 12), "frame": (245, 205, 12)}
# вторая волна: точки клика по арту (art_tests/hotspots_<model>.json, build_new_assets.py)
CHAIR_HOTSPOTS["aeroz"] = {"tire": (55, 230, 11), "spokes": (90, 185, 11), "axle": (124, 207, 9), "brake": (205, 160, 10), "bolts": (232, 140, 8), "anti_tip": (35, 276, 9)}
CHAIR_HOTSPOTS["cross6"] = {"backrest": (160, 75, 13), "cushion": (215, 140, 12), "brake": (165, 168, 9), "bolts": (122, 196, 9), "tire": (78, 210, 11), "anti_tip": (62, 271, 9)}
CHAIR_HOTSPOTS["iris"] = {"anti_tip": (325, 262, 9), "tilt_cable": (300, 130, 9), "tilt_lock": (245, 195, 10), "tilt_lever": (322, 50, 9), "tire": (300, 282, 10), "brake": (283, 210, 9)}
CHAIR_HOTSPOTS["focuscr"] = {"tilt_lever": (80, 32, 9), "tilt_cable": (98, 122, 9), "gas_spring": (118, 160, 9), "brake": (150, 172, 9), "tilt_lock": (178, 210, 10), "anti_tip": (33, 275, 9)}
CHAIR_HOTSPOTS["whillc2"] = {"controller": (288, 60, 9), "joystick": (271, 49, 8), "armrest": (232, 118, 11), "seat": (178, 124, 11), "seat_cable": (170, 148, 9), "battery": (112, 186, 11), "freewheel": (36, 250, 9), "tire": (110, 262, 11)}
CHAIR_HOTSPOTS["f5"] = {"controller": (144, 124, 10), "battery": (205, 192, 11), "motor": (150, 228, 11), "tire": (128, 272, 11), "freewheel": (200, 240, 9), "frame": (248, 222, 11), "breaker": (276, 214, 9)}


_CHAIR3D_CACHE = {}
# коляска -> детальная 3D-модель (assets/models/*.json; сейчас — art_tests/build_9_chairs.py, «Custom3D»;
# прежние ИИ-модели Pixal3D/Hunyuan3D — art_tests/models_bak_before_smooth). *_lod.json — облегчённая копия
# для окна диагностики.
AI_MODELS = {f"chair_{k}.png": f"chair_{k}_ai.json"
             for k in ("basic", "troll", "elf", "dwarf", "fairy", "orc", "edge4", "trident", "m3",
                       "aeroz", "cross6", "iris", "focuscr", "whillc2", "f5", "pulse6", "q6edge")}


# Кружок детали — в выбранной точке, а не по граням модели: у Edge 4 «батарея» — короб с боковинами у самых
# колёс, кружок садился на шину и при повороте прыгал с одной стороны на другую; ставим на заднюю стенку короба.
PART_CENTER_FIX = {"chair_edge4.png": {"battery": [(-200.0, 230.0, 0.0)]}}


def get_ai_chair3d(chair_art, lod=False):
    """Детальная модель коляски (assets/models/*.json) или None; lod=True — облегчённая копия."""
    fn = AI_MODELS.get(chair_art)
    if not fn:
        return None
    if lod:
        lf = fn.replace(".json", "_lod.json")
        if os.path.exists(os.path.join(ASSETS_DIR, "models", lf)):
            fn = lf
    key = ("ai", fn)
    if key not in _CHAIR3D_CACHE:
        try:
            with open(os.path.join(ASSETS_DIR, "models", fn), "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            _CHAIR3D_CACHE[key] = None
            return None
        m = Mesh3D()
        m.verts = [tuple(v) for v in d["verts"]]
        names = d["parts"]
        for a, b, c, pi, r, g, bl in d["faces"]:
            part = names[pi]
            is_metal = part in ("axle", "rear_wheel", "bearing", "valve", "bolts") or (
                part in ("rim", "spokes") and max(r, g, bl) > 105)
            fl = (0 if d.get("cull") else M_DOUBLE) | (M_METAL if is_metal else 0)
            m.face((a, b, c), part if part in PARTS else None, (r, g, bl), fl)
        _finish_mesh(m)
        m.centers.update(PART_CENTER_FIX.get(chair_art, {}))
        _CHAIR3D_CACHE[key] = m
    return _CHAIR3D_CACHE[key]


def get_chair3d(kind, frame=None):
    k = kind if kind in ("manual", "power", "m3") else "manual"
    key = (k, frame)
    if key not in _CHAIR3D_CACHE:
        if k == "m3":
            mesh = _build_chair3d_m3()
        else:
            mesh = _build_chair3d_manual(frame) if (k == "manual" and frame) else (
                _build_chair3d_manual() if k == "manual" else _build_chair3d_power())
        _finish_mesh(mesh)
        _CHAIR3D_CACHE[key] = mesh
    return _CHAIR3D_CACHE[key]


_WHEEL_PART_ANGLES = {
    "tire":       math.radians(145),
    "rim":        math.radians(205),
    "rear_wheel": math.radians(-30),
    "spokes":     math.radians(55),
    "tube":       math.radians(-125),
}


def _finish_mesh(mesh):
    """Центры деталей (на реальной поверхности грани, с разведением концентрических колец колеса)."""
    groups = {}
    V = mesh.verts
    for idx, part, col, fl in mesh.faces:
        if part:
            n = len(idx)
            cx = sum(V[i][0] for i in idx) / n
            cy = sum(V[i][1] for i in idx) / n
            cz = sum(V[i][2] for i in idx) / n
            side = 0 if abs(cz) < 60 else (1 if cz > 0 else -1)
            groups.setdefault((part, side), []).append((cx, cy, cz))
    xs = [v[0] for v in V]
    ys = [v[1] for v in V]
    mesh.pivot = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0)
    mesh.centers = {}
    for (part, side), pts in groups.items():
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        mz = sum(p[2] for p in pts) / len(pts)
        if part in _WHEEL_PART_ANGLES:
            ang = _WHEEL_PART_ANGLES[part]
            tx, ty, tz = mx + 350.0 * math.cos(ang), my + 350.0 * math.sin(ang), mz
        elif part == "seat":
            tx, ty, tz = mx - 40.0, my + 120.0, mz
        else:
            tx, ty, tz = mx, my, mz
        best = min(pts, key=lambda p: (p[0] - tx) ** 2 + (p[1] - ty) ** 2 + (p[2] - tz) ** 2)
        mesh.centers.setdefault(part, []).append(best)


def _shade(col, k):
    return (min(255, int(col[0] * k)), min(255, int(col[1] * k)), min(255, int(col[2] * k)))


def _pt_in_poly(p, pts):
    x, y = p
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


_L_KEY = _norm((-0.45, 0.75, 0.55))     # свет в пространстве камеры: сверху-слева-спереди
_L_FILL = _norm((0.7, 0.1, 0.4))
_H_KEY = _norm((_L_KEY[0], _L_KEY[1], _L_KEY[2] + 1))


try:                                   # numpy ускоряет 3D в 5–10 раз; без него — чистый Python
    import numpy as _np
except Exception:
    _np = None


TT_DIR = "turntable"                 # assets/turntable: кадры поворота колясок (art_tests/build_turntables.py)
TT_MODE = os.environ.get("WNB_TT", "auto")     # окно диагностики/ремонта: "auto" — кадры поворота, если они есть
TT_FORCE = TT_MODE == "1"                      # (решение владельца 23.10: кадры Blender с текстурами красивее сетки);
                                               # "1" — только кадры (как в браузере), "0" — живая сетка (проверка)
_TT_CACHE = {}


class Turntable:
    """Коляска «вращается» по заранее снятым кадрам (браузер: нет numpy/OpenGL). Кружки деталей
    считаются как у живой модели — project_point по centers/pivot. В браузере кадры не лежат в
    пакете игры, а подгружаются с сайта, когда коляска впервые на экране (иначе загрузка игры ×2)."""

    def __init__(self, art, d):
        self.art, self.name = art, os.path.splitext(art)[0]
        self.n, self.yaw0, self.pitch = d["n"], d["yaw0"], d["pitch"]
        self.z0, self.ref, self.offsets = d["z0"], d["ref"], d["offsets"]
        self.pivot = tuple(d["pivot"])
        self.fmt = d.get("fmt", "png")
        self.art_matched = d.get("art_matched", False)     # рисунок коляски = кадр исходного ракурса (art_from_turntable)
        self.centers = {p: [tuple(c) for c in cs] for p, cs in d["centers"].items()}
        self.centers.update(PART_CENTER_FIX.get(art, {}))
        self.frames, self.scaled, self.asked, self.failed, self.tries = {}, {}, False, False, {}

    def index(self, yaw):
        return int(round((yaw - self.yaw0) / (2 * math.pi / self.n))) % self.n

    def release(self):
        """Освободить кадры (коляска ушла с экрана); вернётся — подгрузятся снова (из кэша браузера)."""
        if self.frames or self.scaled:
            self.frames, self.scaled, self.asked, self.tries = {}, {}, False, {}

    def file(self, i):
        return f"{TT_DIR}/{self.name}_{i:02d}.{self.fmt}"

    def files(self, i):
        """Файлы кадра: PNG — один; JPEG (кадры из Blender) — цвет + белая маска <кадр>.a.png."""
        f = self.file(i)
        return [f, f[:-4] + ".a.png"] if self.fmt == "jpg" else [f]

    def _decode(self, i, data=None):
        try:
            names = self.files(i)
            srcs = [os.path.join(ASSETS_DIR, n) for n in names]
            if data is not None:                              # браузер: pygame не читает картинку из памяти — через файл
                srcs = []
                for n, blob in zip(names, data):
                    srcs.append(os.path.join(tempfile.gettempdir(), "wnb_tt" + n[-6:]))
                    with open(srcs[-1], "wb") as f:
                        f.write(blob)
            self.frames[i] = (_load_split(*srcs) if self.fmt == "jpg" else pygame.image.load(srcs[0])).convert_alpha()
        except Exception as e:                                # кадр не прочитался — останется рисунок коляски
            print(f"[wnb] turntable {self.name} {i}: {e!r}", flush=True)
            self.failed = True

    def update(self):
        """Запросить кадры (раз) и забрать пришедшие. True — все кадры на месте."""
        if len(self.frames) == self.n or self.failed:
            return not self.failed
        if not IS_WEB:                                        # компьютер: кадры лежат в assets
            for i in range(self.n):
                if i not in self.frames:
                    self._decode(i)
            return not self.failed
        if not self.asked:
            self.asked = True
            self._got = {}
            self._fetch([u for i in range(self.n) for u in self.files(i)])
        now = pygame.time.get_ticks()
        if now - getattr(self, "_poll", -1000) < 40:          # забираем пришедшее не чаще раза за кадр
            return False
        self._poll = now
        got = web_js("(function(L){var T=window.wnbTT||{},o={},k=0;for(var j=0;j<L.length&&k<6;j++){var v=T[L[j]];"
                     "if(v){o[L[j]]=v;delete T[L[j]];k++;}}return JSON.stringify(o);})("
                     + json.dumps([u for i in range(self.n) if i not in self.frames for u in self.files(i)
                                   if u not in self._got]) + ")")
        try:
            got = json.loads(str(got)) if got else {}
        except Exception:
            got = {}
        import base64
        for u, v in got.items():
            if v == "!":                                      # сбой сети — ещё попытка, после трёх — рисунок
                self.tries[u] = self.tries.get(u, 0) + 1
                if self.tries[u] >= 3:
                    self.failed = True
                else:
                    self._fetch([u])
                continue
            self._got[u] = base64.b64decode(v)
            i = int(u.rsplit("_", 1)[1][:2])                  # …_NN.png / _NN.jpg / _NN.a.png
            if i not in self.frames and all(f in self._got for f in self.files(i)):
                self._decode(i, [self._got.pop(f) for f in self.files(i)])
        return len(self.frames) == self.n and not self.failed

    @staticmethod
    def _fetch(urls):
        """Браузер: скачать кадры в window.wnbTT (base64; '!' — не скачался)."""
        web_js("(function(L){var T=window.wnbTT=window.wnbTT||{};L.forEach(function(u){if(u in T)return;"
               "T[u]=null;fetch(u).then(function(r){if(!r.ok)throw 0;return r.arrayBuffer();}).then(function(b){"
               "var a=new Uint8Array(b),s='';for(var i=0;i<a.length;i+=8192)s+=String.fromCharCode.apply(null,"
               "a.subarray(i,i+8192));T[u]=btoa(s);}).catch(function(){T[u]='!';});});})(" + json.dumps(urls) + ")")

    def image(self, i, f):
        """Кадр i в пикселях экрана, увеличенный в f раз (кэш на один масштаб)."""
        img = self.frames.get(i)
        if img is None:
            return None
        if abs(f - 1) < 0.02:
            return img
        if self.scaled.get("f") != round(f, 3):
            self.scaled = {"f": round(f, 3)}
        out = self.scaled.get(i)
        if out is None:
            w, h = img.get_size()
            if len(self.scaled) > 6:                     # память: копии только последних кадров (вращают —
                for k in [k for k in self.scaled if k != "f"][:3]:   # соседние пересчитываются быстро)
                    del self.scaled[k]
            out = self.scaled[i] = pygame.transform.smoothscale(img, (max(1, round(w * f)), max(1, round(h * f))))
        return out


def get_turntable(art):
    """Обороты коляски (assets/turntable/index.json) или None."""
    if "index" not in _TT_CACHE:
        _TT_CACHE["index"] = {}
        for name in ("index.json", "index_folk.json"):      # index_folk — коляски, у которых есть только кадры
            try:
                with open(os.path.join(ASSETS_DIR, TT_DIR, name), encoding="utf-8") as f:
                    _TT_CACHE["index"].update(json.load(f))
            except Exception:
                pass
    if art not in _TT_CACHE:
        d = _TT_CACHE["index"].get(art)
        _TT_CACHE[art] = Turntable(art, d) if d else None
    if _TT_CACHE.get("_cur") != art:                     # память: кадры держит только коляска на экране
        for k, tt in _TT_CACHE.items():                  # (36 кадров + копии — до 100 МБ; на телефоне кончалась
            if k not in ("index", "_cur", art) and isinstance(tt, Turntable):   # память — игра вставала)
                tt.release()
        _TT_CACHE["_cur"] = art
    return _TT_CACHE[art]


def _np_pack(mesh):
    """Кэш массивов модели для numpy: группы граней по числу вершин."""
    pk = getattr(mesh, "_np_pack", None)
    if pk is None:
        groups = {}
        for idx, part, col, fl in mesh.faces:
            groups.setdefault(len(idx), []).append((idx, part, col, fl))
        names = []
        pk = {"V": _np.asarray(mesh.verts, dtype=_np.float64), "groups": [], "names": names}
        for n, items in groups.items():
            pids = []
            for it in items:
                if it[1] not in names:
                    names.append(it[1])
                pids.append(names.index(it[1]))
            pk["groups"].append((_np.asarray([it[0] for it in items], dtype=_np.int64),
                                 _np.asarray([it[2] for it in items], dtype=_np.float64),
                                 _np.asarray([it[3] for it in items], dtype=_np.int64),
                                 _np.asarray(pids, dtype=_np.int64)))
        mesh._np_pack = pk
    return pk


def _project_mesh_np(mesh, yaw, pitch, rect, zoom, center, ss):
    """Векторная проекция: всё считается массивами, в Python-списки — один раз в конце."""
    pk = _np_pack(mesh)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    scale = rect.h / 1250.0 * zoom * ss
    ox, oy = rect.w * ss / 2, rect.h * ss * 0.54
    P = pk["V"] - _np.asarray(center, dtype=_np.float64)
    X = P[:, 0] * cy + P[:, 2] * sy
    Z = -P[:, 0] * sy + P[:, 2] * cy
    Y = P[:, 1] * cp - Z * sp
    Z2 = P[:, 1] * sp + Z * cp
    k = 2600.0 / (2600.0 - Z2)
    T = _np.stack([X, Y, Z2], 1)
    S2 = _np.stack([ox + X * k * scale, oy - Y * k * scale], 1)
    LK, LF, HK = _np.asarray(_L_KEY), _np.asarray(_L_FILL), _np.asarray(_H_KEY)
    out = []
    for idx, cols, fls, pids in pk["groups"]:
        a, b, c = T[idx[:, 0]], T[idx[:, 1]], T[idx[:, 2]]
        n = _np.cross(b - a, c - a)
        ln = _np.linalg.norm(n, axis=1)
        ok = ln > 0
        n = n / _np.where(ok, ln, 1.0)[:, None]
        back = n[:, 2] < 0
        ok &= ~back | ((fls & M_DOUBLE) != 0)
        sel = _np.nonzero(ok)[0]
        if not len(sel):
            continue
        n = n[sel]
        n[back[sel]] *= -1
        fl = fls[sel]
        inten = (0.36 + 0.62 * _np.clip(n @ LK, 0, None) + 0.18 * _np.clip(n @ LF, 0, None)
                 + 0.12 * (1 - n[:, 2]))
        spec = _np.where((fl & M_METAL) != 0, 170 * _np.clip(n @ HK, 0, None) ** 18, 0.0)
        col = _np.clip(cols[sel] * inten[:, None] + spec[:, None], 0, 255).astype(_np.int64)
        ids = idx[sel]
        out.append((T[:, 2][ids].mean(1), S2[ids], col, pids[sel], fl))
    if not out:
        return []
    depth = _np.concatenate([o[0] for o in out])
    order = _np.argsort(depth, kind="stable")
    names = pk["names"]
    res = []
    for d_, pts, col, pid, fl in out:                     # группы обычно одна (треугольники) или две
        res.append((d_, pts, col, pid, fl))
    if len(res) == 1:
        d_, pts, col, pid, fl = res[0]
        o = order
        return list(zip(d_[o].tolist(), pts[o].tolist(), map(tuple, col[o].tolist()),
                        [names[i] for i in pid[o].tolist()], fl[o].tolist()))
    allp = [r[1].tolist() for r in res]
    flat_p = [p for g in allp for p in g]
    flat_c = [tuple(c) for r in res for c in r[2].tolist()]
    flat_n = [names[i] for r in res for i in r[3].tolist()]
    flat_f = [f for r in res for f in r[4].tolist()]
    dl = depth.tolist()
    return [(dl[i], flat_p[i], flat_c[i], flat_n[i], flat_f[i]) for i in order.tolist()]


def project_mesh(mesh, yaw, pitch, rect, zoom=1.0, center=None, ss=1):
    """Проекция в экранные полигоны (в координатах rect * ss).
    Возврат: [(глубина, точки, цвет, part, флаги)] от дальних к ближним."""
    center = center or getattr(mesh, "pivot", (180, 470, 0))
    if _np is not None and len(mesh.faces) > 600:
        return _project_mesh_np(mesh, yaw, pitch, rect, zoom, center, ss)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    scale = rect.h / 1250.0 * zoom * ss
    ox, oy = rect.w * ss / 2, rect.h * ss * 0.54
    F = 2600.0
    tv, sv = [], []
    for x, y, z in mesh.verts:
        x -= center[0]; y -= center[1]; z -= center[2]
        X = x * cy + z * sy
        Z = -x * sy + z * cy
        Y = y * cp - Z * sp
        Z2 = y * sp + Z * cp
        k = F / (F - Z2)
        tv.append((X, Y, Z2))
        sv.append((ox + X * k * scale, oy - Y * k * scale))
    out = []
    for idx, part, col, fl in mesh.faces:
        a, b, c = tv[idx[0]], tv[idx[1]], tv[idx[2]]
        n = _cross(_sub(b, a), _sub(c, a))
        ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
        if ln == 0:
            continue
        nx, ny, nz = n[0] / ln, n[1] / ln, n[2] / ln
        if nz < 0:
            if not fl & M_DOUBLE:
                continue
            nx, ny, nz = -nx, -ny, -nz
        d1 = nx * _L_KEY[0] + ny * _L_KEY[1] + nz * _L_KEY[2]
        d2 = nx * _L_FILL[0] + ny * _L_FILL[1] + nz * _L_FILL[2]
        inten = 0.36 + 0.62 * max(0.0, d1) + 0.18 * max(0.0, d2) + 0.12 * (1 - nz)
        spec = 0.0
        if fl & M_METAL:
            hd = max(0.0, nx * _H_KEY[0] + ny * _H_KEY[1] + nz * _H_KEY[2])
            spec = 170 * hd ** 18
        colr = (min(255, int(col[0] * inten + spec)), min(255, int(col[1] * inten + spec)),
                min(255, int(col[2] * inten + spec)))
        depth = sum(tv[i][2] for i in idx) / len(idx)
        out.append((depth, [sv[i] for i in idx], colr, part, fl))
    out.sort(key=lambda o: o[0])
    return out


# ----------------------------------------------------------------------------- #
#  GPU-рендер 3D (moderngl, OpenGL 3.3): плавное освещение по нормалям вершин,
#  MSAA, блики на металле, подсветка детали в шейдере и буфер номеров деталей для
#  наведения. Проекция — ТА ЖЕ формула, что у project_mesh/project_point, поэтому
#  кружки деталей, клики и пикинг совпадают пиксель в пиксель. Если OpenGL нет
#  (старая видеокарта, браузерная сборка, флаг --nogl), всё рисуется как раньше.
# ----------------------------------------------------------------------------- #
try:
    import moderngl as _mgl
except Exception:
    _mgl = None
GL = {"ctx": None, "failed": False, "prog": None, "meshes": {}, "fbo": {}, "off": False}

_GL_VS = """
#version 330
uniform vec3 center; uniform vec2 cy_sy; uniform vec2 cp_sp; uniform float scale; uniform vec2 size;
in vec3 in_pos; in vec3 in_nrm; in vec3 in_col; in float in_part; in float in_metal;
out vec3 v_nrm; out vec3 v_col; flat out float v_part; out float v_metal;
vec3 cam(vec3 p) {
    float X = p.x * cy_sy.x + p.z * cy_sy.y;
    float Z = -p.x * cy_sy.y + p.z * cy_sy.x;
    return vec3(X, p.y * cp_sp.x - Z * cp_sp.y, p.y * cp_sp.y + Z * cp_sp.x);
}
void main() {
    vec3 t = cam(in_pos - center);
    float wc = (2600.0 - t.z) / 2600.0;
    gl_Position = vec4(2.0 * t.x * scale / size.x, -0.08 * wc + 2.0 * t.y * scale / size.y, (-t.z / 4000.0) * wc, wc);
    v_nrm = cam(in_nrm); v_col = in_col; v_part = in_part; v_metal = in_metal;
}
"""
_GL_FS = """
#version 330
uniform vec3 LK; uniform vec3 LF; uniform vec3 HK;
uniform vec4 hl_part; uniform vec3 hl_col; uniform float hl_amt;
uniform vec4 hv_part; uniform float hv_amt;
bool inset(float p, vec4 s) { return abs(p - s.x) < 0.5 || abs(p - s.y) < 0.5 || abs(p - s.z) < 0.5 || abs(p - s.w) < 0.5; }
in vec3 v_nrm; in vec3 v_col; flat in float v_part; in float v_metal;
layout(location = 0) out vec4 f_col;
layout(location = 1) out vec4 f_id;
void main() {
    vec3 n = normalize(v_nrm);
    if (n.z < 0.0) n = -n;                                   // двусторонние грани
    float inten = 0.36 + 0.62 * max(dot(n, LK), 0.0) + 0.18 * max(dot(n, LF), 0.0) + 0.12 * (1.0 - n.z);
    float h = max(dot(n, HK), 0.0);
    float spec = v_metal > 0.5 ? (170.0 / 255.0) * pow(h, 18.0) : 0.06 * pow(h, 28.0);
    vec3 c = v_col * inten + spec;
    if (hl_amt > 0.0 && inset(v_part, hl_part)) c = mix(c, hl_col, hl_amt);
    if (hv_amt > 0.0 && inset(v_part, hv_part)) c = c * (1.0 + hv_amt);
    f_col = vec4(clamp(c, 0.0, 1.0), 1.0);
    f_id = vec4((v_part + 1.0) / 255.0, 0.0, 0.0, 1.0);
}
"""


def gl_ok():
    """Готов ли GPU-рендер (ленивая инициализация; при любой ошибке — навсегда выключен)."""
    if GL["off"] or GL["failed"] or _mgl is None or _np is None:
        return False
    if GL["ctx"] is None:
        try:
            ctx = _mgl.create_standalone_context()
            GL["prog"] = ctx.program(vertex_shader=_GL_VS, fragment_shader=_GL_FS)
            for name, v in (("LK", _L_KEY), ("LF", _L_FILL), ("HK", _H_KEY)):
                GL["prog"][name].value = tuple(v)
            GL["ctx"] = ctx
        except Exception:
            GL["failed"] = True
            return False
    return True


def _gl_mesh(mesh):
    """Буферы модели: треугольники без общих вершин, сглаженные нормали (с изломом > ~50°)."""
    key = id(mesh)
    hit = GL["meshes"].get(key)
    if hit and hit[0] is mesh:
        return hit[1], hit[2]
    V = _np.asarray(mesh.verts, dtype=_np.float64)
    tri, fcol, fpart, fmet = [], [], [], []
    names = []
    for idx, part, col, fl in mesh.faces:
        if part not in names:
            names.append(part)
        pid = names.index(part)
        for j in range(1, len(idx) - 1):                     # веер для четырёхугольников
            tri.append((idx[0], idx[j], idx[j + 1]))
            fcol.append(col); fpart.append(pid); fmet.append(1.0 if fl & M_METAL else 0.0)
    T = _np.asarray(tri, dtype=_np.int64)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    fn = _np.cross(b - a, c - a)
    area = _np.linalg.norm(fn, axis=1)
    fnu = fn / _np.where(area > 0, area, 1.0)[:, None]
    acc = _np.zeros_like(V)
    for k in range(3):
        _np.add.at(acc, T[:, k], fn)                         # площадь как вес
    vn = acc / _np.maximum(_np.linalg.norm(acc, axis=1), 1e-9)[:, None]
    corner_n = vn[T]                                         # (n, 3, 3)
    d = (corner_n * fnu[:, None, :]).sum(-1)
    corner_n = _np.where((_np.abs(d) > 0.64)[..., None], corner_n * _np.sign(d)[..., None], fnu[:, None, :])
    pos = V[T].reshape(-1, 3)
    nrm = corner_n.reshape(-1, 3)
    col = _np.repeat(_np.asarray(fcol, dtype=_np.float64) / 255.0, 3, axis=0)
    prt = _np.repeat(_np.asarray(fpart, dtype=_np.float64), 3)[:, None]
    met = _np.repeat(_np.asarray(fmet, dtype=_np.float64), 3)[:, None]
    data = _np.hstack([pos, nrm, col, prt, met]).astype("f4")
    ctx = GL["ctx"]
    vbo = ctx.buffer(data.tobytes())
    vao = ctx.vertex_array(GL["prog"], [(vbo, "3f 3f 3f 1f 1f", "in_pos", "in_nrm", "in_col", "in_part", "in_metal")])
    GL["meshes"][key] = (mesh, vao, names)
    return vao, names


def _gl_fbo(w, h):
    f = GL["fbo"].get((w, h))
    if f is None:
        ctx = GL["ctx"]
        samples = min(8, ctx.max_samples)
        rb_c = ctx.renderbuffer((w, h), 4, samples=samples)
        rb_i = ctx.renderbuffer((w, h), 4, samples=samples)
        ms = ctx.framebuffer(color_attachments=[rb_c, rb_i],
                             depth_attachment=ctx.depth_renderbuffer((w, h), samples=samples))
        ms_c = ctx.framebuffer(color_attachments=[rb_c])          # «виды» на слои — для copy_framebuffer
        ms_i = ctx.framebuffer(color_attachments=[rb_i])
        col = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h), 4)])
        ids = ctx.framebuffer(color_attachments=[ctx.renderbuffer((w, h), 4)])
        if len(GL["fbo"]) > 6:
            for old in GL["fbo"].values():
                for o in old:
                    o.release()
            GL["fbo"].clear()
        f = GL["fbo"][(w, h)] = (ms, ms_c, ms_i, col, ids)
    return f


# Узлы, которые подсвечиваются целиком: «Пульт (джойстик)» (controller) — весь блок на подлокотнике
# (корпус + ручка + пыльник), «Ручка джойстика» — ручка с пыльником. Клики и улики по деталям раздельные.
HL_GROUPS = {"controller": ("controller", "joystick", "boot"), "joystick": ("joystick", "boot")}


def hl_group(part):
    return HL_GROUPS.get(part, (part,)) if part else ()


def gl_render(mesh, yaw, pitch, size, zoom, center=None, hl_part=None, hl_col=None, hl_amt=0.0,
              hover_part=None, hover_amt=0.35):
    """Отрисовать модель в size=(w, h) настоящих пикселей. Возврат: (pygame.Surface RGBA, ids) или None.
    ids — функция (x, y) -> имя детали под пикселем (для наведения), x/y в пикселях картинки."""
    if not gl_ok():
        return None
    try:
        w, h = max(1, int(size[0])), max(1, int(size[1]))
        vao, names = _gl_mesh(mesh)
        center = center or getattr(mesh, "pivot", (180, 470, 0))
        pr = GL["prog"]
        pr["center"].value = tuple(float(c) for c in center)
        pr["cy_sy"].value = (math.cos(yaw), math.sin(yaw))
        pr["cp_sp"].value = (math.cos(pitch), math.sin(pitch))
        pr["scale"].value = h / 1250.0 * zoom
        pr["size"].value = (float(w), float(h))
        def ids4(part):                                     # деталь -> до 4 номеров (с группой узла)
            v = [float(names.index(p)) for p in hl_group(part) if p in names][:4]
            return tuple(v + [-9.0] * (4 - len(v))), bool(v)
        hl4, hl_on = ids4(hl_part)
        hv4, hv_on = ids4(hover_part)
        pr["hl_part"].value = hl4
        pr["hl_col"].value = tuple(c / 255.0 for c in (hl_col or AMBER))
        pr["hl_amt"].value = float(hl_amt if hl_on else 0.0)
        pr["hv_part"].value = hv4
        pr["hv_amt"].value = float(hover_amt if hv_on else 0.0)
        ctx = GL["ctx"]
        ms, ms_c, ms_i, col, ids = _gl_fbo(w, h)
        ms.use()
        ctx.enable(_mgl.DEPTH_TEST)
        ctx.disable(_mgl.CULL_FACE)
        ms.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
        vao.render(_mgl.TRIANGLES)
        ctx.copy_framebuffer(col, ms_c)                         # MSAA -> обычная картинка
        raw = _np.frombuffer(col.read(components=4, alignment=1), dtype=_np.uint8).reshape(h, w, 4)
        al = raw[..., 3]
        rows, cols_ = _np.nonzero(al.any(1))[0], _np.nonzero(al.any(0))[0]
        bbox = (pygame.Rect(int(cols_[0]), int(h - 1 - rows[-1]), int(cols_[-1] - cols_[0] + 1), int(rows[-1] - rows[0] + 1))
                if len(rows) else pygame.Rect(0, 0, 0, 0))     # где модель (в пикселях картинки, после переворота)
        edge = (al > 0) & (al < 255)                           # только кромка: из премультиплицированного
        if edge.any():
            raw = raw.copy()
            e = raw[edge].astype(_np.float32)
            e[:, :3] = _np.clip(e[:, :3] * 255.0 / _np.maximum(e[:, 3:4], 1.0), 0, 255)
            raw[edge] = e.astype(_np.uint8)
        img = pygame.image.frombuffer(raw.tobytes(), (w, h), "RGBA")
        img = pygame.transform.flip(img, False, True)
        ctx.copy_framebuffer(ids, ms_i)
        cache = {}

        def pick(x, y, _names=names):
            """Деталь под пикселем (x, y) картинки; буфер номеров читается один раз и только по запросу."""
            x, y = int(x), int(y)
            if not (0 <= x < w and 0 <= y < h):
                return None
            if "ids" not in cache:
                cache["ids"] = _np.frombuffer(ids.read(components=4, alignment=1), dtype=_np.uint8).reshape(h, w, 4)[::-1, :, 0].copy()
            v = int(cache["ids"][y, x])
            return _names[v - 1] if v and v - 1 < len(_names) else None
        pick.bbox = bbox
        return img, pick
    except Exception:
        GL["failed"] = True                                   # дальше — программный рендер
        if os.environ.get("WNB_GL_DEBUG"):
            raise
        return None

def project_point(p, yaw, pitch, rect, zoom=1.0, center=None):
    center = center or (180, 470, 0)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x, y, z = p[0] - center[0], p[1] - center[1], p[2] - center[2]
    X = x * cy + z * sy
    Z = -x * sy + z * cy
    Y = y * cp - Z * sp
    Z2 = y * sp + Z * cp
    k = 2600.0 / (2600.0 - Z2)
    scale = rect.h / 1250.0 * zoom
    return (rect.x + rect.w / 2 + X * k * scale, rect.y + rect.h * 0.54 - Y * k * scale), Z2


# ----------------------------------------------------------------------------- #
#  Инструменты и детали (реальные)
# ----------------------------------------------------------------------------- #
TOOLS = {
    "hands":     ("Руки", "Снять/поставить, нажать, проверить рукой"),
    "eyes":      ("Глаза", "Посмотреть: индикатор, экран, код ошибки, износ, трещины"),
    "allen":     ("Шестигранник", "Большинство болтов коляски (бери точный размер!)"),
    "socket":    ("Торцевой ключ", "Ось и гайки колеса"),
    "wrench":    ("Разводной ключ", "Подтянуть узлы, шток кастора"),
    "screw":     ("Отвёртка", "Винты и колпачки (крест, шлиц)"),
    "lever":     ("Монтажка", "Бортировать покрышку (нужны 2 шт.)"),
    "pump":      ("Насос", "Накачать камеру / шину / подушку"),
    "patch":     ("Заплатка", "Ремкомплект для прокола"),
    "lube":      ("Смазка", "Смазать ось/подшипник"),
    "brush":     ("Щётка/пинцет", "Вычистить волосы и грязь из оси"),
    "cloth":     ("Тряпка/салфетка", "Протереть, обезжирить"),
    "bucket":    ("Таз с водой", "Найти прокол по пузырькам"),
    "pencil":    ("Карандаш", "Пинг-тест спиц, отметки"),
    "gauge":     ("Манометр", "Проверить давление в шине"),
    "spoke_key": ("Спицевой ключ", "Подтянуть ниппели спиц"),
    "multimeter":("Мультиметр", "Замерить напряжение батареи/цепи"),
    "charger":   ("Зарядка", "Штатная зарядка батареи"),
    "tensiometer": ("Тензиометр", "Точный замер натяжения спицы"),
    "dial":      ("Индикатор", "Биение обода на правочном станке"),
    "tape":      ("Рулетка", "Замерить схождение и размеры"),
}

PARTS = {
    "rear_wheel": "Заднее колесо",
    "caster":     "Кастор (перед.)",
    "caster_stem":"Шток кастора",
    "brake":      "Тормоз-замок",
    "spokes":     "Спицы",
    "rim":        "Обод",
    "tire":       "Покрышка",
    "tube":       "Камера",
    "valve":      "Ниппель",
    "bearing":    "Подшипник",
    "axle":       "Ось (QR)",
    "seat":       "Сиденье",
    "footrest":   "Подножка",
    "frame":      "Рама",
    "bolts":      "Болты/гайки рамы",
    "cushion":    "Подушка",
    "battery":    "Батарея",
    "controller": "Пульт (джойстик)",
    "joystick":   "Ручка джойстика",
    "boot":       "Пыльник джойстика",
    "wiring":     "Разъёмы/проводка",
    "fuse":       "Предохранитель",
    "motor":      "Мотор",
    "freewheel":  "Рычаг своб. хода",
}


def S(instr, tool, part, note="", ghost="", ghost_wrong=False, wrongmsg="", mini=None, alt=(), alt_tools=()):
    """Удобный конструктор шага ремонта.

    mini — необязательная мини-интеракция вместо мгновенного выполнения:
    dict(kind="pump"|"gap"|"ping"|"meter", ...) — см. Game.start_mini().
    alt — другие детали, которые тоже верны (насос к ниппелю И «к шине»: игроки думают по-разному).
    alt_tools — другие инструменты, которые тоже верны (сдвинуть замок — руками, «проверить» — и глазами).
    """
    return dict(instr=instr, tool=tool, part=part, note=note,
                ghost=ghost, ghost_wrong=ghost_wrong, wrongmsg=wrongmsg, mini=mini, alt=tuple(alt),
                alt_tools=tuple(alt_tools))


def D(text, correct, feedback=""):
    return dict(text=text, correct=correct, feedback=feedback)


def T(sid, instr, tool, part, note="", ghost="", after=(), safety=False,
      spec=None, failnote="", mini=None):
    """Шаг про-задания Гильдии: свободный порядок, зависимости, спеки.

    after    — id шагов, которые обязаны быть выполнены раньше;
    safety   — шаг техники безопасности: попытка выполнить ЗАВИСЯЩИЙ от него
               шаг раньше времени проваливает всё задание;
    spec     — dict(manual=ключ MANUAL, prompt=вопрос,
               options=[(текст, верно?, пояснение), ...]) — значение из мануала;
    failnote — чем именно опасно нарушение (показывается в разборе провала).
    """
    return dict(id=sid, instr=instr, tool=tool, part=part, note=note,
                ghost=ghost, after=list(after), safety=safety, spec=spec,
                failnote=failnote, mini=mini)


def shuffle_answers(job):
    """Перемешать варианты ответов (диагноз, вопросы-замеры, спеки Гильдии): в данных верный вариант записан
    первым, и игроки это быстро замечают. Списки перемешиваются на месте при каждом старте задания."""
    if job.get("diagnosis"):
        random.shuffle(job["diagnosis"])
    for st in job.get("steps", []):
        m = st.get("mini") or {}
        if m.get("options"):
            random.shuffle(m["options"])
        if st.get("spec") and st["spec"].get("options"):
            random.shuffle(st["spec"]["options"])


def resolve_job(base, variant=None):
    """Игровая копия задания. У заданий с полем 'variants' подмешивается один
    из вариантов поломки (случайный или заданный индексом): симптом общий,
    а причина, улики, диагноз и шаги — разные. Даёт реиграбельность и учит
    ставить диагноз по осмотру, а не по памяти."""
    if "variants" not in base:
        return base
    idx = variant if variant is not None else random.randrange(len(base["variants"]))
    job = dict(base)
    job.update(base["variants"][idx])
    job.pop("variants", None)
    job["_variant"] = idx                   # для отзывов «Я не согласен»/⚑: о какой поломке речь
    return job


# ----------------------------------------------------------------------------- #
#  Мануал Гильдии: спеки, на которые ссылаются шаги про-заданий
# ----------------------------------------------------------------------------- #
MANUAL = {
    "truing": ("Правка обода («восьмёрка»)", [
        "Допуск бокового биения обода: не более 1–2 мм.",
        "Ниппели крутят НЕ БОЛЕЕ чем на 1/4 оборота за подход, затем снова проверяют биение.",
        "Обод уводит в сторону фланца, чьи спицы натянуты сильнее: тяни спицы противоположного фланца.",
        "Натяжение контролируй тензиометром и сравнивай соседние спицы — «на звон» правят только грубо.",
    ]),
    "battery_pair": ("Замена батарей (регламент)", [
        "До любых работ: питание пульта — ВЫКЛ., коляска в режиме езды (тормоза моторов включены).",
        "Разборка: первой снимается МИНУСОВАЯ клемма. Сборка: первой подключается ПЛЮСОВАЯ.",
        "Батареи меняют только ПАРОЙ: один тип (AGM или гель), одна ёмкость, один возраст.",
        "Старую и новую не смешивать — пара работает по слабейшей батарее.",
        "Первая зарядка новой пары — полная, только штатным зарядным устройством.",
    ]),
    "toe": ("Схождение колёс (tracking)", [
        "Перед замером выровняй давление в обеих шинах — неравное давление имитирует сбитое схождение.",
        "Замерь расстояние между ободами спереди и сзади на высоте оси: разница = схождение.",
        "Норма: 0 мм, допуск 1 мм. Больше — коляску тянет вбок и «ест» резину.",
        "Регулировка: ослабь болты осевой пластины, выставь колесо, затяни крест-накрест, перемерь.",
    ]),
}


# ----------------------------------------------------------------------------- #
#  Кабинет посадки: позиционирование в коляске (по руководству Permobil
#  «Wheelchair Seating & Positioning Guide», hub.permobil.com). Игра учит
#  принципам и причинам, а не «идеальной позе»: посадку подбирает команда
#  (терапевт + специалист ATP), техник настраивает коляску по мерке и карте.
#  Единицы — сантиметры и градусы; вид сбоку, перёд вправо.
# ----------------------------------------------------------------------------- #
SEAT_SLIDERS = {   # ключ: (подпись, единица, мин, макс)
    "depth":  ("Глубина сиденья", "см", 20, 60),
    "leg":    ("Длина подножки (сиденье → подножка)", "см", 20, 55),
    "back_h": ("Высота спинки", "см", 20, 75),
    "back_a": ("Угол спинки к сиденью", "°", 85, 130),
    "tilt":   ("Наклон сиденья (tilt)", "°", 0, 50),
    # вид спереди / сверху (перекос и поворот таза)
    "base":   ("Основа сиденья", "", 0, 1),
    "seat_w": ("Ширина сиденья", "см", 30, 56),
    "foot_l": ("Левая подножка (сиденье → подножка)", "см", 20, 55),
    "foot_r": ("Правая подножка (сиденье → подножка)", "см", 20, 55),
    "build":  ("Подкладка (− под левую, + под правую кость)", "см", -3, 3),
    "depth_l": ("Глубина сиденья слева", "см", 20, 60),
    "depth_r": ("Глубина сиденья справа", "см", 20, 60),
}


def seat_val_text(key, v):
    """Значение ползунка примерки словами (основа, подкладка) или числом с единицей."""
    if key == "base":
        return tr("жёсткая") if v else tr("гамак (провисает)")
    if key == "build":
        if v == 0:
            return tr("без подкладки")
        return tr(f"под левую: {abs(v)} см" if v < 0 else f"под правую: {abs(v)} см")
    unit = tr(SEAT_SLIDERS[key][1])
    return f"{v}{unit}" if unit == "°" else f"{v} {unit}".strip()

SEAT_CASES = [
    dict(id="seat_troll", client="Тролль Бомм", client_art="client_troll.png", kind="manual",
         skin=(120, 168, 150), seat_h=50,
         body=dict(thigh=50, shank=44, scap=42, shoulder=60),
         story="Бомм к вечеру «стекает» в коляске: таз уезжает вперёд, спина колесом, болит крестец.",
         therapist="Поза исправимая — корректируем к нейтрали. Спинка — опора для таза и поясницы "
                   "(40–50 см), угол спинки 95–105°.",
         back=(40, 50), angle=(95, 105),
         start=dict(depth=52, leg=49, back_h=36, back_a=91),
         fact="Сидение на крестце — самая частая неправильная поза. Причины часто в самой коляске: "
              "глубокое или высокое сиденье, низкая или слишком прямая спинка, подножка не той длины."),
    dict(id="seat_elf", client="Эльфийка Аэлин", client_art="client_elf.png", kind="manual",
         skin=(236, 214, 180), seat_h=49,
         body=dict(thigh=46, shank=43, scap=36, shoulder=55),
         story="Аэлин гоняет на активной коляске, но устают плечи, а после тренировки ноют седалищные кости.",
         therapist="Корпус сильный, толкает сама: спинка — до кончика лопатки (33–38 см), "
                   "угол спинки 90–98°.",
         back=(33, 38), angle=(90, 98),
         start=dict(depth=41, leg=37, back_h=47, back_a=94),
         fact="Активному пользователю высокая спинка мешает лопаткам и толчку. Подножка слишком высоко — "
              "колени выше бёдер, весь вес уходит на седалищные бугры."),
    dict(id="seat_fairy", client="Фея Тилли", client_art="client_fairy.png", kind="manual",
         skin=(250, 210, 200), seat_h=42,
         body=dict(thigh=33, shank=30, scap=27, shoulder=40),
         story="Тилли за лето вытянулась: коленки торчат вверх, бёдрам не хватает сиденья.",
         therapist="Растущий ребёнок: перенастроить под новые мерки. Спинка 26–33 см, угол 93–100°.",
         back=(26, 33), angle=(93, 100),
         start=dict(depth=23, leg=25, back_h=29, back_a=96),
         fact="Дети растут — посадку детской коляски проверяют и перенастраивают регулярно, "
              "по новым меркам, а не «на глаз»."),
    dict(id="seat_golem", client="Голем Грунд", client_art="client_golem.png", kind="power",
         skin=(150, 140, 128), seat_h=52,
         body=dict(thigh=52, shank=46, scap=45, shoulder=64),
         story="Грунд сам не может переносить вес, а сидит весь день. Его Trident HD умеет только откидывать "
               "спинку — так его и «разгружали». Подбираем ему кресло с электронаклоном.",
         therapist="Не может сам сместить вес: позиция разгрузки — наклон сиденья (tilt) не меньше 45°. "
                   "Спинка 55–70 см (до плеч), угол спинки 95–110°.",
         back=(55, 70), angle=(95, 110), tilt=45,
         start=dict(depth=47, leg=46, back_h=60, back_a=122, tilt=0),
         fact="Наклон сиденья (tilt) не менее 45° переносит давление с таза на спинку и подголовник "
              "(для большинства людей). Откидывание спинки без наклона усиливает сдвиг тканей."),
    dict(id="seat_aeroz", client="Кицунэ Юки", client_art="client_aeroz.png", kind="manual",
         skin=(238, 152, 92), seat_h=48,
         body=dict(thigh=44, shank=41, scap=35, shoulder=53),
         story="Юки пересела на титановую Aero Z, но сползает вперёд, а под коленями жмёт передний край подушки.",
         therapist="Активная посадка: глубина с зазором 5 см до подколенной ямки, спинка ниже кончика "
                   "лопатки (31–35 см), угол спинки 91–97°.",
         back=(31, 35), angle=(91, 97),
         start=dict(depth=46, leg=45, back_h=42, back_a=103),
         fact="Зазор ~5 см (2 дюйма) от переднего края подушки до подколенной ямки защищает сосуды и нервы "
              "под коленом и не стягивает таз вперёд."),
    dict(id="seat_iris", client="Дракончик Искра", client_art="client_iris.png", kind="manual",   # Zippie Iris: ручная, наклон в пространстве
         skin=(228, 108, 92), seat_h=46,
         body=dict(thigh=35, shank=32, scap=30, shoulder=44),
         story="Искра устаёт держать голову и заваливается вперёд, а при долгом сидении немеет крестец.",
         therapist="Нужна высокая опора спины до плеч (38–44 см), подголовник, раскрытый угол 96–106° "
                   "и разгрузочный наклон (tilt) не меньше 45°.",
         back=(38, 44), angle=(96, 106), tilt=45,
         start=dict(depth=36, leg=27, back_h=33, back_a=90, tilt=15),
         fact="Наклон в пространстве (tilt-in-space) сохраняет углы в тазобедренных и коленных суставах, "
              "снимая нагрузку с таза и помогая удерживать голову и корпус. Чтобы ручная коляска при этом не "
              "опрокинулась, сиденье при наклоне смещается вперёд, а сзади стоят антиопрокидыватели."),
    # --- вид спереди и сверху: перекос и поворот таза (Permobil, «Pelvic Obliquity» / «Pelvic Rotation»;
    #     таблица Lange & Presperin Pedersen «Positioning Chart») ---
    dict(id="seat_dryad", view="front", client="Дриада Ивушка", client_art="client_cross6.png", kind="manual",
         skin=(150, 190, 120), seat_h=48,
         body=dict(thigh=45, shank=42, scap=36, shoulder=55, hip=38),
         story="К вечеру Ивушку клонит вбок: левая сторона таза ниже, позвоночник изгибается. "
               "Сиденье у неё — провисший гамак, коляска досталась от тётушки-дуба.",
         therapist="Перекос исправимый: убрать причины в коляске. Жёсткая основа вместо гамака, ширина сиденья "
                   "по бёдрам (38–40 см), обе подножки на одной высоте — по голени (42 см).",
         back=(33, 40), angle=(92, 100), sliders=["base", "seat_w", "foot_l", "foot_r"],
         start=dict(base=0, seat_w=44, foot_l=42, foot_r=38),
         solution=dict(base=1, seat_w=39, foot_l=42, foot_r=42),
         fact="Перекос таза чаще создаёт сама коляска: провисший гамак, слишком широкое сиденье, низкая спинка, "
              "одна подножка или разные по высоте, подлокотник не той высоты."),
    dict(id="seat_owl", view="front", client="Бабушка Агата", client_art="client_focuscr.png", kind="manual",
         skin=(196, 176, 150), seat_h=47,
         body=dict(thigh=43, shank=40, scap=34, shoulder=52, hip=40),
         fixed=dict(obl=8, high=1, gap=2),
         story="У Агаты давний НЕисправимый перекос: левая седалищная кость ниже и натёрта, под правой — зазор "
               "2 см. Кто-то подложил подушечку под левую сторону, «чтобы выпрямить», — стало больнее.",
         therapist="Перекос неисправимый — не выпрямлять, а учесть: жёсткая основа и подкладка под ВЫСОКУЮ "
                   "сторону, заполнить зазор (2 см) и разгрузить нижнюю кость.",
         back=(33, 40), angle=(95, 105), sliders=["base", "build"],
         start=dict(base=0, build=-2), solution=dict(base=1, build=2),
         fact="Исправимый перекос выравнивают подкладкой под НИЖНЮЮ сторону, понемногу. Неисправимый учитывают: "
              "заполняют высокую сторону, чтобы нижняя седалищная кость не перегружалась."),
    dict(id="seat_orc", view="top", client="Орк Гра", client_art="client_orc.png", kind="manual",
         skin=(130, 160, 90), seat_h=51,
         body=dict(thigh=48, thigh_l=48, thigh_r=44, shank=45, scap=40, shoulder=60, hip=44),
         fixed=dict(rot=-6),
         story="После старого перелома правое бедро у Гра короче на 4 см, таз развёрнут и не выпрямляется: "
               "левое колено впереди. В узкой коляске его крутит ещё сильнее, а край подушки режет под правым коленом.",
         therapist="Поворот таза неисправимый — учесть, не выправлять: ширина сиденья по бёдрам (44–46 см), "
                   "глубина своя для каждой ноги — бедро минус 5 см (слева 43, справа 39).",
         back=(36, 44), angle=(92, 100), sliders=["seat_w", "depth_l", "depth_r"],
         start=dict(seat_w=41, depth_l=43, depth_r=43), solution=dict(seat_w=45, depth_l=43, depth_r=39),
         fact="При неисправимом повороте таза глубину сиденья меряют по длинной ноге, а с короткой стороны "
              "подушку укорачивают. Слишком узкое сиденье само разворачивает таз."),
]

SEAT_LESSONS = [
    dict(title="Сначала таз",
         points=["Таз — фундамент посадки: от него зависят позвоночник, плечи и голова.",
                 "Подушку и спинку выбирают под цель для таза.",
                 "Неудачная коляска сама может создавать и усиливать неправильные позы.",
                 "Посадку подбирает команда: терапевт и специалист по технике (ATP). "
                 "Техник настраивает коляску по мерке и карте терапевта."],
         pose=dict()),
    dict(title="Сидение на крестце",
         points=["Признаки: таз завален назад, спина «колесом», голова вперёд, взгляд в колени.",
                 "Риски: давление на крестец (пролежни), сдавлены грудь и живот — хуже дыхание "
                 "и пищеварение, хуже обзор и общение.",
                 "Причины в коляске: сиденье глубокое или высокое, провисший гамак сиденья, "
                 "низкая или слишком прямая спинка, подножка не той длины, подъёмные подножки.",
                 "Исправление: правильная глубина, раскрыть угол спинки, подушка с контурами "
                 "и упором от сползания, жёсткая основа под провисшее сиденье."],
         pose=dict(p=20, slide=7, deep=True)),
    dict(title="Подножка: колени и стопы",
         points=["Подножка высоко: колени выше бёдер, бедро не лежит на сиденье — давление "
                 "на седалищные бугры, крестец и копчик.",
                 "Подножка низко: стопы не достают, человек сползает вперёд, стопа тянется носком "
                 "вниз — риск контрактуры.",
                 "Обе подножки — на одной высоте. До пола — не меньше 5 см (2″), чтобы не цеплять пороги."],
         pose=dict(knee_up=True)),
    dict(title="Перекос и поворот таза",
         points=["Перекос: одна сторона таза ниже, позвоночник изгибается — со временем сколиоз. "
                 "Причины в коляске: провисший гамак, широкое сиденье, низкая спинка, разные подножки, подлокотник.",
                 "Исправимый перекос выравнивают подкладкой под НИЖНЮЮ сторону, понемногу. Неисправимый учитывают: "
                 "подкладка под ВЫСОКУЮ сторону, чтобы разгрузить нижнюю седалищную кость.",
                 "Боковые упоры — «три точки»: у вершины изгиба, под мышкой (с зазором — там нервы) и низко у таза.",
                 "Поворот таза (одно колено впереди): узкое сиденье само разворачивает таз. Исправимый выправляют "
                 "маленькими шагами — контурная подушка с ложементами для ног. Неисправимый учитывают: "
                 "глубина сиденья своя для каждой ноги."],
         pose=dict(front=True)),
    dict(title="Исправить или учесть",
         points=["Исправимую позу корректируют к самой нейтральной, которую человек может держать весь день.",
                 "Неисправимую (скелет не выходит из позы) учитывают: подстраивают коляску, "
                 "чтобы поза не ухудшалась.",
                 "Универсального рецепта вроде «90-90-90» нет: решение — по осмотру и цели.",
                 "Аксессуары — не «пластырь» для плохо подобранной коляски: меньше — лучше."],
         pose=dict(p=8)),
    dict(title="Мерки",
         points=["Ширина сиденья = ширина бёдер в самом широком месте (с мягкими тканями).",
                 "Глубина сиденья = от ягодиц до подколенной ямки минус 5 см (2″).",
                 "Спинка: активному — до кончика лопатки, для поддержки — выше, до плеча.",
                 "Подлокотник — по высоте локтя, согнутого под 90°; при перекосе мерят обе стороны.",
                 "Мерят на твёрдой ровной поверхности жёсткой рулеткой, в позе, которую человек удержит весь день."],
         pose=dict(measure=True)),
    dict(title="Давление и наклон",
         points=["Давление нельзя убрать, только распределить: разгрузка, погружение, обволакивание.",
                 "Наклон сиденья (tilt) не меньше 45° (для большинства людей) переносит вес "
                 "с таза на спинку и подголовник; наклон с откидыванием — ещё больше.",
                 "Откидывание спинки без наклона усиливает сдвиг тканей.",
                 "Тем, кто не может сам смещать вес, рассматривают электронаклон и откидывание."],
         pose=dict(tilt=45)),
]

SEAT_QUIZ = [
    dict(pose=dict(knee_up=True), q="Что не так в посадке?",
         desc="На рисунке: колени задраны выше бёдер, бёдра почти не касаются сиденья.",
         options=[("Подножка слишком высоко: колени выше бёдер", True, ""),
                  ("Сиденье слишком глубокое", False, "Глубина тут ни при чём — смотри на колени и бёдра."),
                  ("Спинка слишком низкая", False, "Спинка держит корпус, а проблема — в коленях.")]),
    dict(pose=dict(p=20, slide=7, deep=True), q="Почему клиент сползает и сидит на крестце?",
         desc="На рисунке: таз уехал к переднему краю, спина колесом, край сиденья упирается под колени.",
         options=[("Сиденье глубже нормы: край давит под колени", True, ""),
                  ("Слишком мягкий подголовник", False, "Подголовник не тянет таз вперёд."),
                  ("Подножка слишком короткая", False, "Тогда колени ушли бы вверх.")]),
    dict(pose=dict(dangle=True, slide=4, p=8), q="Стопы не достают до подножки. Что поправить?",
         desc="На рисунке: стопы висят над подножкой, тело немного сползает вперёд.",
         options=[("Поднять подножку (укоротить) — стопы должны стоять", True, ""),
                  ("Откинуть спинку", False, "Откинутая спинка сползание только усилит."),
                  ("Сузить сиденье", False, "Ширина не влияет на опору стоп.")]),
    dict(pose=None, q="Можно ли посадить всех по правилу «90-90-90»?",
         desc="На рисунке: три скелета в разных посадках — активный толчок, комфорт и опора, разгрузка наклоном 45°.",
         options=[("Нет: универсального рецепта нет, решают по осмотру и цели", True, ""),
                  ("Да, это стандарт для всех", False, "Руководство прямо говорит: готового рецепта нет."),
                  ("Да, но только детей", False, "Для детей тоже решают индивидуально.")]),
    dict(pose=dict(tilt=45), q="Клиент не может сам перенести вес. Как разгрузить таз?",
         desc="На рисунке: клиент сидит в электроколяске с механизмом наклона сиденья.",
         options=[("Наклонить сиденье (tilt) не меньше чем на 45°", True, ""),
                  ("Только откинуть спинку", False, "Откидывание без наклона усиливает сдвиг тканей."),
                  ("Поднять подъёмные подножки — ноги вперёд", False,
                   "Подъёмные подножки тянут таз назад, на крестец, и вес с таза не снимают.")]),
    dict(pose=dict(front=True), q="Перекос таза неисправимый. Куда положить подкладку?",
         desc="На рисунке: вид спереди, одна сторона таза ниже, позвоночник изогнут.",
         options=[("Под высокую сторону: заполнить зазор и разгрузить нижнюю седалищную кость", True, ""),
                  ("Под нижнюю сторону — выровнять таз", False,
                   "Так выравнивают только исправимый перекос. Неисправимый выпрямлять нельзя: боль и давление."),
                  ("Никуда: неисправимый перекос не трогают", False,
                   "«Учесть» — значит подстроить коляску: заполнить высокую сторону.")]),
    dict(pose=dict(front=True), q="Где ставят боковые упоры при сколиозе?",
         desc="На рисунке: вид спереди, позвоночник изогнут дугой вбок.",
         options=[("В три точки: вершина изгиба, под мышкой с зазором, низко у таза", True, ""),
                  ("Вплотную в подмышку — так надёжнее", False, "Под мышкой оставляют зазор: там нервы."),
                  ("Только один упор на вершине изгиба", False, "Одна точка не удержит изгиб.")]),
]
SEAT_QUIZ_PASS = 6

# Хозяин кабинета — некромант Мортимер: тысячу лет изучает кости, поэтому лучше всех знает таз.
# Шутит над собой и своим мрачным ремеслом, а не над клиентами.
SEAT_MENTOR = {
    "intro": "Мортимер: «Добро пожаловать в мой кабинет! Тысячу лет я изучаю кости и понял главное: "
             "таз — король скелета. Садитесь... ровно.»",
    "lessons": "Мортимер: «Знание — сила! Тёмная, древняя сила... в основном про глубину сиденья.»",
    "fit": "Мортимер: «Клиенты ждут. Тяни ползунки и смотри на таз. Кости не лгут!»",
    "quiz": "Мортимер: «Экзамен! Не бойся: худшее, что я делал с двоечниками, — заставлял пересчитывать позвонки.»",
    "lesson": [
        "Мортимер: «Поставь таз в нейтраль — и за ним восстанет весь позвоночник. Это не заклинание, это анатомия.»",
        "Мортимер: «Мои скелеты сидят на крестце веками — им можно, они давно не дышат. Живым нужны воздух и ровная спина.»",
        "Мортимер: «Колени выше бёдер? Стопы болтаются? Подножка решает больше, чем кажется.»",
        "Мортимер: «Три точки опоры — как три свечи в пентаграмме. Только без пентаграммы. И под мышкой — зазор!»",
        "Мортимер: «Кости, которые не гнутся, не ломай — подстрой под них коляску. Даже некромант не спорит со скелетом.»",
        "Мортимер: «Моя рулетка мерила древних королей. Мерь жёсткой рулеткой, на твёрдом. И дважды.»",
        "Мортимер: «Наклон в сорок пять градусов — и вес уходит с таза. Почти левитация, только по науке.»",
    ],
    "solved": "Мортимер: «Ни одна косточка не стонет! Мои скелеты позавидовали бы такой посадке.»",
    "view_front": "Мортимер: «Сбоку этот скелет сидит безупречно. А спереди — перекос! Кости любят прятаться.»",
    "view_top": "Мортимер: «Посмотрим сверху, как ворон. Одно колено впереди другого — таз развёрнут.»",
    "side_ok": "Мортимер: «Видишь? Сбоку не придерёшься. Поэтому я всегда обхожу скелет кругом.»",
    "fail": "Мортимер: «Тьма сгущается... над седалищными буграми. Посмотри, что ещё горит жёлтым.»",
    "right": "Мортимер: «Верно! Кости одобрительно стучат.»",
    "wrong": "Мортимер: «Мимо! Не страшно — я однажды поднял скелет задом наперёд.»",
    "pass": "Мортимер: «Зачёт! Нарекаю тебя Хранителем Таза. Звучит мрачно, но это почётно.»",
    "nopass": "Мортимер: «Пока не зачёт. Перечитай уроки — свитки не кусаются. Почти.»",
}


# ----------------------------------------------------------------------------- #
#  Контент: задания (каждое — реальная поломка с реальными шагами)
# ----------------------------------------------------------------------------- #
JOBS = [
    # === 0. Туториал: своя коляска Мартина, прокол ===
    dict(
        id="flat", kind="manual", client="Мартин (ты)", client_art="martin.png", chair_art="chair_basic.png",
        chair_model="inv9000", chair_name="Invacare 9000 (стандартная складная)",
        title="Прокол заднего колеса",
        symptom="Заднее колесо спустило: коляска «клюёт» носом и катится тяжело. До вечеринки далеко.",
        parts=["tire", "tube", "valve", "rim", "brake", "spokes"],
        inspect={
            "tire": "Покрышка мягкая, в боку — след от чего-то острого.",
            "tube": "Камера внутри спущена в ноль.",
            "valve": "Ниппель цел, но воздуха нет.",
            "rim": "Обод ровный, без вмятин.",
            "brake": "Тормоз в порядке — он тут ни при чём.",
            "spokes": "Спицы звенят нормально.",
        },
        diagnosis=[
            D("Прокол камеры: заднее колесо спущено", True),
            D("Погнут обод: колесо «восьмерит» и бьёт", False, "Обод ровный. Гнётся он редко и от сильного удара."),
            D("Ослаб тормоз-замок и подтормаживает колесо", False, "Тормоз не влияет на спущенное колесо."),
        ],
        steps=[
            S("Полностью спусти остатки воздуха через ниппель.", "hands", "valve",
              "Со спущенной камерой покрышку снять легко.",
              "Барти: «Мастер всегда сначала выпускал дух из колеса. Торжественно.»"),
            S("Поддень борт покрышки монтажкой над спицей, зацепи крючок за спицу.", "lever", "tire",
              "Монтажки пластиковые — держи у конца, легко ломаются.",
              "Барти: «Двумя ложками для обуви он это делал! ...или нет.»", ghost_wrong=True,
              wrongmsg="Борт покрышки поддевают монтажкой — между ободом и покрышкой.", alt=("rim",)),
            S("Второй монтажкой пройди по кругу — сними один борт с обода.", "lever", "tire",
              "Снимаем только один борт, второй оставляем на ободе."),
            S("Вынь камеру из покрышки.", "hands", "tube",
              "Аккуратно, чтобы не зацепить ниппель."),
            S("Проведи пальцем внутри покрышки и по ободу — убери стекло/занозы.", "hands", "tire",
              "Пропустишь осколок — новая камера проколется сразу.",
              "Барти: «О, это я помню — он тут однажды нашёл монетку. Богатей.»", alt=("rim",)),
            S("Чуть подкачай новую камеру через ниппель, чтобы держала круглую форму.", "pump", "tube",
              "Полуспущенная камера легче и ровнее ложится в покрышку."),
            S("Проведи ниппель в отверстие обода.", "hands", "valve", "", alt=("rim",)),
            S("Вложи камеру в покрышку по всему кругу.", "hands", "tube",
              "Камера должна лечь ровно, без перекрутов.", alt=("tire",)),
            S("Заправь борт покрышки руками от ниппеля по кругу.", "hands", "tire",
              "Последний участок дожми ладонями; монтажка тут — крайний случай: ею легко прищемить камеру."),
            S("Посмотри, что ниппель стоит перпендикулярно, не косо.", "eyes", "valve",
              "Косой ниппель со временем перетрётся."),
            S("Подключи насос к ниппелю и накачай до давления, указанного на боковине покрышки.", "pump", "tire",
              "Правильное давление снижает сопротивление качению и нагрузку на плечи.",
              "Барти: «Качай, пока не зазвенит! ...не до взрыва, конечно.»",
              mini=dict(kind="pump", lo=65, hi=80, mx=110, unit="psi",
                        hint="На боковине покрышки: 65–80 psi")),
        ],
        test="Прокручиваешь колесо — держит воздух, катится ровно и легко.",
        fact="Рекомендуемое давление написано на боковине покрышки. Низкое давление = "
             "тяжелее катить и выше нагрузка на плечи (риск травмы). Проверяй давление раз в неделю.",
        thanks="Мартин: «Я... починил коляску? Слушай, а это даже залипательно.»",
    ),

    # === 1. Эльфийка: тряска переда — ДВЕ возможные причины (реиграбельность) ===
    dict(
        id="caster", kind="manual", client="Эльфийка Аэлин", client_art="client_elf.png", chair_art="chair_elf.png",
        chair_model="ego", chair_name="Progeo Ego (активная, жёсткая рама)",
        title="Кастор бьёт (флаттер)",
        symptom="На скорости переднее колесо начинает мелко трястись, и коляску уводит в сторону.",
        fact="Тряску переда дают люфт штока, грязь/волосы в оси или ослабший крепёж вилки. "
             "Один симптом — разные причины: сначала осмотр, потом ремонт.",
        variants=[
            # А: классика — волосы в оси + люфт штока
            dict(
                parts=["caster", "caster_stem", "tire", "brake", "bearing"],
                inspect={
                    "caster": "Переднее колесо вихляет, в оси намотаны длинные волосы (эльфийские!).",
                    "caster_stem": "Шток кастора болтается в стакане — есть люфт. Крепление вилки при этом держит плотно.",
                    "tire": "Задняя шина накачана нормально.",
                    "brake": "Тормоз держит.",
                    "bearing": "Задний подшипник тихий.",
                },
                diagnosis=[
                    D("Люфт штока кастора и волосы в оси", True),
                    D("Ослабли болты крепления вилки кастора", False, "Вилка сидит плотно — играет сам шток."),
                    D("Спустила задняя шина — коляску тянет вбок", False, "Шина в норме. Тряску даёт перёд."),
                ],
                steps=[
                    S("Сними колесо кастора с вилки.", "allen", "caster",
                      "Обычно держится на одном болте.", alt_tools=("socket",)),
                    S("Вычисти волосы и грязь из оси кастора пинцетом/щёткой.", "brush", "caster",
                      "Намотанные волосы — частая причина, что кастор не крутится свободно.",
                      "Барти: «Волос там — будто кто-то линял веками. Ах да, это я.»"),
                    S("Прокрути колесо кастора рукой: крутится свободно и не бьёт?", "hands", "caster",
                      "Бьёт, стёрта резина или не крутится свободно — колесо под замену."),
                    S("Подтяни узел подшипника штока кастора до лёгкого трения.", "wrench", "caster_stem",
                      "Чуть больше трения в штоке гасит флаттер.",
                      "Барти: «Туже! Ещё туже! ...хотя нет, он потом ругался, что закусило.»", ghost_wrong=True,
                      wrongmsg="Узел штока кастора подтягивают разводным ключом."),
                    S("Прикрути колесо кастора обратно к вилке.", "allen", "caster",
                      "Перетянешь крепление — колесо застопорится.", alt_tools=("socket",)),
                    S("Прокрути и покачай кастор: крутится свободно, люфта нет.", "hands", "caster",
                      "Свободный ход без люфта — значит, крепление затянуто в меру.", alt=("caster_stem",)),
                ],
                test="Разгон по мастерской — флаттера нет, коляску ведёт прямо.",
                fact="Три причины флаттера кастора: высокая скорость, люфт штока и перекос. "
                     "Немного трения в подшипнике штока убирает тряску; волосы в оси чисти регулярно.",
                thanks="Аэлин: «Теперь катится бесшумно, как эльфийская ладья. Благодарю!»",
            ),
            # Б: тот же симптом, но причина — ослабший крепёж вилки
            dict(
                parts=["caster", "caster_stem", "bolts", "tire", "bearing"],
                inspect={
                    "caster": "Колесо цело, ось чистая, крутится свободно — но вся вилка ходит ходуном.",
                    "caster_stem": "Шток не люфтит — играет само крепление вилки.",
                    "bolts": "Болты крепления вилки кастора заметно ослабли.",
                    "tire": "Задняя шина в норме.",
                    "bearing": "Подшипники тихие.",
                },
                diagnosis=[
                    D("Ослабли болты крепления вилки кастора", True),
                    D("Люфт штока кастора и волосы в оси", False, "Шток плотный, ось чистая — дело не в них."),
                    D("Спустила задняя шина — коляску тянет вбок", False, "Шина в норме. Тряску даёт перёд."),
                ],
                steps=[
                    S("Покачай вилку кастора рукой — найди люфт.", "hands", "caster",
                      "Вилка шатается на целом штоке — значит, крепёж.", alt=("caster_stem",)),
                    S("Подтяни болты крепления вилки кастора.", "allen", "bolts",
                      "Шестигранник — точно по размеру: слизанный болт потом высверливают.",
                      "Барти: «Постучи молотком, само сядет!» — нет. Только ключ.", ghost_wrong=True,
                      alt=("caster_stem", "caster")),
                    S("Проверь: кастор крутится свободно, люфта нет.", "hands", "caster",
                      "Перетянешь — заклинит, недотянешь — снова растрясёт."),
                ],
                test="Разгон по мастерской — перёд стоит жёстко, тряска ушла.",
                fact="Тряска переда — не всегда шток или подшипник: сначала проверь крепёж вилки. "
                     "Болты тянут ключом точно по размеру и не перетягивают.",
                thanks="Аэлин: «Как новая! А я уже собиралась менять колесо целиком.»",
            ),
        ],
    ),

    # === 2. Оборотень (до 23.10.2026 — гном Дургин на Progeo Tekna): тормоз не держит ===
    dict(
        id="brake", kind="manual", client="Оборотень Вольф", client_art="client_dwarf.png", chair_art="chair_dwarf.png",
        chair_model="quickie2", chair_name="Quickie 2 (складная лёгкая)",
        title="Тормоз-замок не держит",
        symptom="Тяжёлый оборотень жалуется: коляска скатывается с холма даже с зажатым тормозом.",
        parts=["brake", "tire", "frame", "bolts", "rear_wheel"],
        inspect={
            "tire": "Задняя шина приспущена — это уже подозрительно.",
            "brake": "Упор тормоза не достаёт до шины как надо; крепление чуть съехало.",
            "frame": "Рама целая.",
            "bolts": "Болты хомута тормоза слегка ослабли.",
            "rear_wheel": "Колесо крутится свободно.",
        },
        diagnosis=[
            D("Низкое давление в шине и сдвинутый тормоз", True),
            D("Износился тормозной узел — менять целиком", False, "Сперва простые причины: давление и крепёж."),
            D("Погнута рама — колесо стоит криво", False, "Рама в порядке."),
        ],
        steps=[
            S("Проверь давление в шине — спущенная шина «уводит» упор тормоза.", "gauge", "tire",
              "Первая причина «замок не держит» — низкое давление в шине.",
              "Барти: «Сразу болты крути!» ...а вот и нет — сначала давление.", ghost_wrong=True,
              alt=("rear_wheel",)),
            S("Подкачай шину через ниппель до нормы.", "pump", "tire", "", alt=("rear_wheel",)),
            S("Подтяни болты механизма тормоза-замка.", "allen", "brake",
              "Без фанатизма: перетянешь — замок станет туго включаться.", alt=("bolts",)),
            S("Не помогло — ослабь два болта хомута, крепящего замок к раме.", "allen", "brake",
              "Хомут даст сдвинуть весь узел.", alt=("bolts",)),
            S("Сдвинь замок к шине: в отпущенном виде зазор упор—шина 3–6 мм.", "hands", "brake",
              "Это 1/8–1/4 дюйма — рабочий зазор по мануалу. Выставляем, пока хомут ослаблен.",
              mini=dict(kind="gap", lo=3, hi=6, mn=0, mx=12, unit="мм", start=9,
                        label="Зазор упор—шина",
                        hint="Рабочий зазор по мануалу: 3–6 мм в отпущенном виде",
                        fb_lo="Меньше 3 мм: упор будет тереть шину на каждом обороте.",
                        fb_hi="Больше 6 мм: замок не дожмёт шину и не удержит коляску.")),
            S("Затяни болты хомута, чередуя их (симметрично).", "allen", "brake",
              "Симметричная затяжка держит узел ровно.", alt=("bolts",)),
            S("Зажми замок: упор плотно вдавился в шину.", "hands", "brake",
              "Зажатый упор держит колесо — коляска не скатится."),
            S("Отпусти замок и прокрути колесо: упор не касается шины.", "hands", "tire",
              "Отпущенный упор не трёт — колесо крутится свободно.", alt=("brake", "rear_wheel")),
        ],
        test="Вольф жмёт тормоз и наваливается всем весом — колесо не проворачивается. Держит!",
        fact="«Замок не держит» чаще всего лечится давлением в шине и подтяжкой/сдвигом крепления. "
             "Бери шестигранник ТОЧНО по размеру: сорванный болт потом высверливают.",
        thanks="Вольф: «Ау-у-у! Стоит как вкопанная. Теперь хоть полнолуние, хоть холм!»",
    ),

    # === 3. Фея: ослабли спицы и болты ===
    dict(
        id="spokes", kind="manual", client="Фея Тилли", client_art="client_fairy.png", chair_art="chair_fairy.png",
        chair_model="exelle_jr", chair_name="Progeo Exelle Junior (детская)",
        title="Дребезг: ослабли спицы",
        symptom="На ходу что-то дребезжит, заднее колесо чуть «восьмерит» — крошечная фея переживает.",
        parts=["spokes", "rim", "bolts", "bearing", "tube"],
        inspect={
            "spokes": "Несколько спиц (три) на ощупь мягче соседних — ослабли.",
            "rim": "Обод гуляет на 2–3 мм — лёгкая «восьмёрка».",
            "bolts": "Несколько болтов на раме подразболтались.",
            "bearing": "Подшипник тихий — звук именно дребезжащий, не воющий.",
            "tube": "Камера держит давление.",
        },
        diagnosis=[
            D("Ослабли спицы заднего колеса", True),
            D("Разбит подшипник оси — колесо болтается", False, "Подшипник даёт вой/стук, а тут именно дребезг."),
            D("Спустила камера — шина мнётся на ходу", False, "Камера в норме."),
        ],
        steps=[
            S("Пинг-тест: проведи карандашом по спицам, вращая колесо.", "pencil", "spokes",
              "Звонкий «пинь» = норма, глухой звук = спица ослабла.",
              "Барти: «Музыкально! Он так целые мелодии наигрывал. Плохие.»",
              mini=dict(kind="ping", total=12, dull=3)),
            S("Сожми соседние спицы парами — подтверди на ощупь те, что звучали глухо.", "hands", "spokes", ""),
            S("Подтяни спицевым ключом ниппели глухо звучавших спиц — каждый на четверть оборота.", "spoke_key", "spokes",
              "Один раз, по четверти оборота и равномерно: перетянешь — обод «восьмерит». Точную натяжку делают на "
              "спец-станке.",
              "Барти: «Крути от души, на пол-оборота за раз... ладно, по чуть-чуть.»", alt=("rim",)),
            S("Подтяни ослабшие болты/гайки на раме.", "allen", "bolts",
              "Сорванный болт меняют на такой же по классу прочности (число на головке).",
              alt_tools=("socket", "wrench")),       # отзыв: ключ — по головке крепежа (шестигранник, гайка)
        ],
        test="Катишь колесо — дребезг ушёл, обод идёт ровно.",
        fact="Натяжение спиц проверяют пинг-тестом. Тянут до нужного натяжения и равномерно — "
             "перетянешь, и обод «восьмерит». Болты меняют только на равные по классу прочности.",
        thanks="Тилли: «Тихо-тихо! Теперь слышно, как я жужжу. Спасибо!»",
    ),

    # === 4. Орк: вой у заднего колеса — ДВЕ возможные причины ===
    dict(
        id="bearing", kind="manual", client="Орк Гра", client_art="client_orc.png", chair_art="chair_orc.png",
        chair_model="noir", chair_name="Progeo Noir 2.0 (жёсткая рама)",
        title="Вой у заднего колеса",
        symptom="При качении слышен вой и шорох, заднее колесо крутится туго и быстро встаёт.",
        parts=["bearing", "axle", "rear_wheel", "brake", "tire"],
        fact="Вой и тугой ход у заднего колеса — это либо подшипник, либо трущий тормоз-замок. "
             "Различаются осмотром: слушай ступицу и смотри на зазор упора.",
        variants=[
            # А: классика — изношенный подшипник
            dict(
                inspect={
                    "bearing": "Подшипник при вращении гудит и слегка заедает.",
                    "axle": "В оси намотана грязь и шерсть.",
                    "rear_wheel": "Колесо крутится мало и тут же останавливается.",
                    "brake": "Тормоз отведён, не трёт.",
                    "tire": "Шина накачана.",
                },
                diagnosis=[
                    D("Подшипник оси загрязнён/изношен", True),
                    D("Тормоз трёт по шине", False, "Тормоз отведён. Звук идёт из ступицы."),
                    D("Спустила шина — колесо катится туго и вязнет", False, "Шина в порядке."),
                ],
                steps=[
                    S("Сними заднее колесо: нажми кнопку быстросъёмной оси и потяни.", "hands", "axle",
                      "Quick-release: кнопка в торце оси освобождает колесо.", alt=("rear_wheel",)),
                    S("Вычисти волосы/грязь из оси и подшипника пинцетом/щёткой.", "brush", "bearing",
                      "Шерсть на оси — частый источник воя и тугого хода.",
                      "Барти: «У орка там... не спрашивай. Просто чисти.»", alt=("axle",)),
                    S("Оцени подшипник: стук/вой/заедание = под замену.", "hands", "bearing",
                      "Звук — первый признак умирающего подшипника."),
                    S("Замени подшипник: выбей старый из ступицы и запрессуй новый — оправкой служит головка торцевого "
                      "ключа по диаметру подшипника.", "socket", "bearing",
                      "Изношенный подшипник не лечится — только замена. Ещё лучше — съёмник подшипников; "
                      "давить только на наружное кольцо."),
                    S("Слегка смажь ось.", "lube", "axle",
                      "НЕ мой коляску мойкой высокого давления — выбьет смазку из закрытых подшипников, пойдёт ржавчина.",
                      "Барти: «Полей маслом всё подряд!» — нет, смазка только по делу.", ghost_wrong=True),
                    S("Поставь колесо: нажми кнопку оси и вставь её до упора.", "hands", "axle",
                      "Отпусти кнопку — шарики оси должны выйти и запереть колесо.", alt=("rear_wheel",)),
                    S("Проверка: потяни колесо от рамы — ось защёлкнулась, колесо не снимается.", "hands", "rear_wheel",
                      "Недощёлкнутая быстросъёмная ось — колесо может слететь на ходу.", alt=("axle",)),
                ],
                test="Колесо раскручивается и крутится долго и тихо. Орк доволен.",
                fact="Первый признак умирающего подшипника — звук (вой/стук/скрежет), его меняют целиком. "
                     "Мойка высокого давления убивает закрытые подшипники: вода выбивает смазку.",
                thanks="Гра: «ТИХО. ХОРОШО. Гра нравится тихо.»",
            ),
            # Б: тот же симптом, но виноват съехавший тормоз-замок
            dict(
                inspect={
                    "bearing": "Подшипник крутится ровно и тихо — не он.",
                    "axle": "Ось чистая.",
                    "rear_wheel": "Колесо тормозится с одной стороны — там, где тормоз.",
                    "brake": "Упор тормоза стоит вплотную и цепляет шину даже в отпущенном виде.",
                    "tire": "Шина накачана, но сбоку полоса износа — что-то тёрло.",
                },
                diagnosis=[
                    D("Тормоз-замок съехал и трёт шину", True),
                    D("Подшипник оси загрязнён/изношен", False, "Подшипник тихий и ровный. Звук снаружи, у шины."),
                    D("Спустила шина — колесо катится туго и вязнет", False, "Шина накачана."),
                ],
                steps=[
                    S("Ослабь два болта хомута тормоза.", "allen", "brake",
                      "Хомут даёт сдвинуть весь узел по раме."),
                    S("Сдвинь замок от шины: в отпущенном виде зазор упор—шина 3–6 мм.", "hands", "brake",
                      "Рабочий зазор — 3–6 мм: не трёт, но хватает при зажатии. Выставляем, пока хомут ослаблен.",
                      "Барти: «Может, просто снять тормоз совсем?» — и катиться с горки без него? Нет.",
                      ghost_wrong=True,
                      mini=dict(kind="gap", lo=3, hi=6, mn=0, mx=12, unit="мм", start=1,
                                label="Зазор упор—шина",
                                hint="Рабочий зазор по мануалу: 3–6 мм в отпущенном виде",
                                fb_lo="Всё ещё трёт: меньше 3 мм — шина и силы уходят в звук.",
                                fb_hi="Больше 6 мм: замок не дожмёт шину и не удержит коляску.")),
                    S("Затяни болты хомута, чередуя их.", "allen", "brake",
                      "Симметричная затяжка держит узел ровно."),
                    S("Отпусти замок и прокрути колесо: упор не касается шины.", "hands", "tire",
                      "Колесо крутится долго и не шуршит.", alt=("brake", "rear_wheel")),
                    S("Зажми замок: упор плотно вдавился в шину.", "hands", "brake",
                      "Зажатый замок держит — колесо стоит."),
                ],
                test="Колесо крутится долго и свободно, тормоз хватает только когда просишь.",
                fact="«Воет и тормозит» — не всегда подшипник: сначала проверь, не трёт ли тормоз-замок. "
                     "Рабочий зазор упора 3–6 мм; трущий тормоз съедает шину и силы рук.",
                thanks="Гра: «ТИХО. КАТИТСЯ. Гра ошибался про подшипник. Гра рад.»",
            ),
        ],
    ),

    # === 5. Тролль: дырявая воздушная подушка (ROHO) ===
    dict(
        id="cushion", kind="manual", client="Тролль Бомм", client_art="client_troll.png", chair_art="chair_troll.png",
        chair_model="xdt", chair_name="Invacare 9000 XDT (усиленная, до 159 кг)",
        title="Дырявая воздушная подушка",
        symptom="Подушка сдувается, тролль «проваливается» до самого основания сиденья.",
        parts=["cushion", "seat", "frame", "valve"],
        inspect={
            "cushion": "Воздушная подушка (тип ROHO) медленно сдувается — где-то прокол.",
            "seat": "Стропа сиденья в норме.",
            "frame": "Рама цела.",
            "valve": "Клапан подушки держит — травит не он.",
        },
        diagnosis=[
            D("Прокол воздушной подушки", True),
            D("Провисла стропа сиденья под подушкой", False, "Стропа в норме; провал — из-за сдутой подушки."),
            D("Ослабла спинка — тролль заваливается", False, "Бомм проваливается вниз, до основания сиденья, а не назад — и подушка при осмотре "
              "сдувается."),
        ],
        steps=[
            S("Перекачай подушку через клапан — надуй сильнее обычного.", "pump", "cushion",
              "Перекачанную легче проверить на прокол."),
            S("Погрузи подушку в таз с водой и найди прокол по пузырькам.", "bucket", "cushion",
              "Пузырьки укажут точное место утечки.",
              "Барти: «Топи её! ...в хорошем смысле, для диагностики.»"),
            S("Отметь прокол карандашом или маркером.", "pencil", "cushion",
              "С отметкой прокол не потеряется, пока подушка сохнет.", alt_tools=("hands",)),
            S("Просуши и обезжирь место заплатки салфеткой.", "cloth", "cushion",
              "Заплатка держится только на чистой сухой поверхности."),
            S("Наклей заплатку из ремкомплекта и прижми.", "patch", "cushion",
              "В комплекте ROHO всегда есть заплатка."),
            # source: permobil/mktg0069-00-roho-how-to-adjust-your-cushion.pdf, шаги 1–6
            S("Накачай подушку через клапан, пока она не начнёт чуть выгибаться дугой.", "pump", "cushion",
              "Инструкция ROHO: сначала с запасом, точную настройку делают уже с человеком на подушке."),
            S("Бомм садится. С его разрешения подведи ладонь под самую низкую кость таза.", "hands", "cushion",
              "Ручная проверка ROHO: ладонь между подушкой и тазом — так чувствуешь, сколько осталось воздуха."),
            S("Стравливай воздух клапаном, пока пальцы под тазом не начнут чуть двигаться.", "hands", "valve",
              "Под самой низкой костью таза 1,5–2,5 см воздуха (~1 палец). «Пробивание» до дна — "
              "риск пролежней, перекачанная подушка — как камень.",
              "Барти: «Дуй до звона!» — нет, тут наоборот, перекачивать вредно.", ghost_wrong=True,
              alt=("cushion",)),
        ],
        test="Тролль садится — подушка держит, до дна не проваливается.",
        fact="Правильно накачанная противопролежневая подушка предотвращает пролежни: под костями "
             "таза должен оставаться зазор ~1 палец. Прокол ищут по пузырькам в воде и ставят заплатку.",
        thanks="Бомм: «Мягко! Бомм сидеть. Бомм не падать. Бомм друг.»",
    ),

    # ===================== ЭЛЕКТРОКОЛЯСКИ (power) =====================
    # Электронику колясок часто доверяют сертифицированному технику.
    # Все шаги ниже — безопасные для пользователя; «лезть в живую электронику»
    # игра прямо отговаривает.

    # === 6. Гоблин: не поднимается электролифт сиденья (Quantum Edge 4, iLevel / TRU-Balance 4) ===
    # Источники: quantum/edge-4-om.pdf, electronics/us_q-logic3_boi_om.pdf,
    # electronics/us_tru-balance_4_power_positioning_systems_boi.pdf (страницы — в source:)
    # Модель Meshy (chair_edge4) стоит с ПОДНЯТЫМ сиденьем — поэтому у Зикса лифт не опускается (переписано 23.10).
    dict(
        id="lift", kind="power", client="Гоблин-механик Зикс",
        client_art="client_goblin.png", chair_art="chair_edge4.png",
        chair_model="edge4", chair_name="Quantum Edge 4 (средний привод, электролифт сиденья)",
        title="Не опускается лифт сиденья",
        symptom="Зикс поднял сиденье, чтобы достать с верхней полки банку гаек, — а вниз оно не едет. "
                "Джойстик назад — ни с места. «Я ж его только чуток улучшил! Ну, может, не чуток. Теперь ползу "
                "на четверти скорости и через порог мастерской не выеду!»",
        # source: TB4 p6 — до 12 in (30,5 см) подъёма; TB4 p7 — поднятое сиденье = 1/4 скорости, 2 mph (3 км/ч)
        # source: E4 p9 — iLevel только на ровном полу; не поднимать на уклоне, бордюре, неровной поверхности
        fact="Электролифт Quantum поднимает сиденье до 30,5 см (12 дюймов), но ездить так можно только по ровному "
             "полу и примерно на четверти скорости — около 3 км/ч. На улицу, на пандус и через порог — только "
             "с опущенным сиденьем. Блокировки ставит завод — их не обходят и не перепрограммируют.",
        variants=[
            # --- А: жгут лифта перетянут к подстаканнику — в верхней точке натянулся и выдернул разъём актуатора ---
            dict(
                parts=["seat_lift", "actuator", "wiring", "controller", "battery", "armrest"],
                inspect={
                    "seat_lift": "Ножницы подъёмника раздвинуты — сиденье стоит наверху. В механизме чисто, "
                                 "ничего не застряло.",
                    "actuator": "Корпус актуатора цел. Но его разъём у электроблока вытянут на полпальца — "
                                "защёлка не держит.",
                    "wiring": "Жгут лифта перетянут новыми стяжками к самодельному подстаканнику: при поднятом "
                              "сиденье он натянут струной и на изгибе прижат рамой. Оплётка пока цела.",
                    "controller": "Экран сиденья открывается, режим подъёма выбирается, кодов ошибок нет. "
                                  "Индикатор — ЖЁЛТЫЙ, рядом значок iLevel: сиденье поднято, скорость снижена.",
                    "battery": "Индикатор заряда полный — Зикс заряжал всю ночь.",
                    "armrest": "На подлокотнике — новенький подстаканник «Зикс-Турбо», прикручен крепко.",
                },
                diagnosis=[
                    D("Жгут натянулся в верхней точке и вытянул разъём актуатора", True),
                    D("Контроллер заблокировал сиденье по положению", False,
                      "Блокировка — это КРАСНЫЙ индикатор. Жёлтый значит лишь, что сиденье поднято и скорость снижена."),
                    D("Разряжена батарея — лифту не хватает тока", False,
                      "Заряд полный, и при разряде Q-Logic 3 показал бы ошибку 20 «Undervoltage»."),
                ],
                steps=[
                    # source: E4 p9 — только ровный пол в помещении; не под столом; держать зону свободной
                    S("Поставь коляску на ровный пол в мастерской: над сиденьем ничего, рядом с ножницами пусто.",
                      "hands", "seat_lift",
                      "Мануал Edge 4: сиденье двигают только на ровной поверхности, не под столом или полкой."),
                    # source: QL3 p8 — кнопка key 2 сразу открывает экран сиденья; джойстик влево/вправо — выбор
                    # source: QL3 p8 — выбранный актуатор двигают джойстиком вперёд/назад
                    S("Включи пульт.", "hands", "controller", ""),
                    S("Кнопкой key 2 открой экран сиденья и выбери «подъём».", "hands", "controller",
                      "Режим подъёма выбран — сиденьем управляет джойстик: вперёд — вверх, назад — вниз."),
                    S("Дай джойстик назад.", "hands", "controller",
                      "Сиденье стоит наверху. Теперь читаем пульт — он подскажет, блокировка это или обрыв.",
                      alt=("seat_lift",)),
                    # source: QL3 p8 — зелёный: без ограничений, жёлтый: скорость снижена при поднятом сиденье,
                    # красный: полная блокировка хода; QL3 p10 — значок iLevel горит, пока сиденье поднято
                    S("Сверь индикатор на пульте с таблицей в мануале Q-Logic 3.", "eyes", "controller",
                      "Индикатор и коды — первое, что смотрят, прежде чем лезть в проводку.",
                      mini=dict(kind="meter", reading="ЖЁЛТЫЙ · iLevel · кодов нет",
                                sub="Q-Logic 3: зелёный — без ограничений, жёлтый — сиденье поднято, скорость "
                                    "снижена, красный — полная блокировка",
                                prompt="Сиденье наверху и не опускается. Что это значит?",
                                options=[
                                    ("Жёлтый — норма при поднятом сиденье; блокировки нет — проверить разъём и жгут",
                                     True, ""),
                                    ("Красная блокировка — виноват наклон сиденья", False,
                                     "Индикатор жёлтый, не красный: контроллер ничего не запрещает."),
                                    ("Батарея села", False,
                                     "Заряд полный и кода 20 «Undervoltage» нет."),
                                ])),
                    # source: E4 p7 — автомат на батарейном лотке сзади, под задней крышкой (снимается без
                    # инструментов, E4 p25: два жёлтых фиксатора); жёлтая кнопка отключает батареи от системы
                    S("Выключи пульт.", "hands", "controller",
                      "Разъёмы трогаем только на обесточенной коляске: сначала пульт, потом автомат."),
                    S("Сними заднюю крышку батарейного отсека: поверни два жёлтых фиксатора (без инструментов).", "hands", "battery",
                      "Под крышкой — батарейный лоток с главным автоматом."),
                    S("Нажми жёлтую кнопку автомата в батарейном отсеке — батареи отключены от системы.", "hands", "battery",
                      "Автомат на Edge 4 — он же выключатель батарей."),
                    # source: TB4 p4 — Pinch/Crush points exist; TB4 p6 — ничего не должно попасть в механизм
                    S("Осмотри раздвинутые ножницы снаружи, с фонариком. Руки — вне механизма.",
                      "eyes", "seat_lift",
                      "Ножницы — точки защемления, даже когда стоят. Смотрим глазами, не пальцами.",
                      "Барти: «Сунь лапу между ножниц и подтолкни — сиденье само сложится!» — нет! Это точка "
                      "защемления: руки в механизм не суют даже на выключенной коляске.", ghost_wrong=True),
                    # source: E4 p19 — все разъёмы должны быть плотными и надёжно закреплёнными, без коррозии
                    # source: E4 p26 — треснувшие/сломанные разъёмы, перетёртые жгуты -> к дилеру Quantum
                    S("Осмотри разъём актуатора: корпус цел, контакты без зелёной коррозии?",
                      "eyes", "actuator",
                      "Цел и чистый — можно вставлять. Треснул или подгорел — не чиним, к сертифицированному технику.",
                      alt=("wiring",)),
                    S("Вставь разъём актуатора до щелчка защёлки.", "hands", "actuator",
                      "Защёлка щёлкнула — разъём больше не вытянется от вибрации.", alt=("wiring",)),
                    # source: E4 p11 — штатные точки крепления жгута, чтобы не зажимало рамой сиденья
                    # source: CSG p8 — повреждённые компоненты меняет авторизованный сервис
                    S("Проводка лифта: сними стяжки подстаканника и переложи жгут на штатные точки крепления, с запасом на подъём.",
                      "hands", "wiring",
                      "Лифт ходит вверх-вниз на 30 см: жгуту нужен свободный ход на всю высоту. Перетёртую оплётку не изолируют — меняют в сервисе."),
                    # source: E4 p7 — питание возвращают, опустив рычажок автомата
                    S("Опусти рычажок автомата — питание батарей вернулось.", "hands", "battery",
                      "Кнопка автомата отключает батареи, рычажок вниз — подключает."),
                    S("Поставь заднюю крышку на место и закрой оба жёлтых фиксатора.", "hands", "battery",
                      "Без крышки в лоток летит грязь, а к жгутам тянутся руки."),
                    S("Включи пульт.", "hands", "controller", ""),
                    # source: QL3 p8 — выбранный актуатор двигают джойстиком; «чтобы вернуться к зелёному — обратное движение»
                    S("Кнопкой key 2 открой экран сиденья и выбери «подъём».", "hands", "controller",
                      "Режим подъёма выбран — сиденьем управляет джойстик."),
                    S("Дай джойстик назад: сиденье опускается.", "hands", "controller",
                      "Сиденье пошло вниз — значит, команда доходит до актуатора.", alt=("seat_lift",)),
                    # source: QL3 p8 — жёлтый гаснет, когда сиденье опущено; QL3 p10 — значок iLevel только при подъёме
                    S("Посмотри на пульт: сиденье внизу — жёлтый индикатор погас, значок iLevel пропал, скорость снова полная.",
                      "eyes", "controller",
                      "Зелёный — ограничений нет: можно на улицу и через порог."),
                    # source: E4 p9 — зону вокруг держать свободной во время движения; TB4 p7 — поднятое сиденье = 1/4 скорости
                    S("Подними сиденье джойстиком до упора и опусти снова, следя, чтобы жгут в верхней точке не натягивался.",
                      "hands", "seat_lift",
                      "Проверяем весь ход: вверху жгут должен лежать свободно, иначе всё повторится.",
                      alt=("controller", "wiring")),
                ],
                test="Сиденье плавно опускается, жёлтый индикатор гаснет, Зикс выкатывает за порог на полной скорости. "
                     "Поднимает снова — в верхней точке жгут лежит свободно.",
                # source: E4 p19, p20, p26; QL3 p8
                fact="Жёлтый индикатор при поднятом сиденье — норма: коляска едет на четверти скорости. Если сиденье "
                     "не слушается, а индикатор не красный, команда теряется по дороге: мануал Edge 4 велит проверять, "
                     "что разъёмы плотные, а жгут не зажат и не натянут рамой сиденья; треснувший разъём или перетёртый "
                     "жгут меняет только сервис.",
                thanks="Зикс: «Подстаканник оставлю, а провода больше не трогаю. Почти. Спасибо, костлявый!»",
            ),
            # --- Б: под поднятое сиденье Зикс привязал ящик с гайками — ножницы упираются и не складываются ---
            dict(
                parts=["seat_lift", "seat", "controller", "actuator", "battery", "freewheel"],
                inspect={
                    "seat_lift": "Ножницы раздвинуты, сиденье наверху. Между рамой сиденья и основанием, вплотную "
                                 "к ножницам, стяжками прикручен жестяной ящик «Зикс-Бокс» — полный гаек.",
                    "seat": "Сиденье и спинка в рабочем положении, без наклона. На подушке — следы гаек.",
                    "controller": "Индикатор ЖЁЛТЫЙ, значок iLevel; кодов нет. В режиме подъёма по команде «вниз» "
                                  "сиденье вздрагивает, актуатор гудит и останавливается.",
                    "actuator": "Разъём актуатора сидит плотно, кабель целый.",
                    "battery": "Заряд полный.",
                    "freewheel": "Рычаги свободного хода подняты — моторы в режиме езды.",
                },
                diagnosis=[
                    D("В механизм попал посторонний предмет — ножницам некуда складываться", True),
                    D("Сгорел актуатор лифта — сиденье не двигается", False,
                      "Актуатор гудит и сдвигает сиденье на палец: он жив, ему просто мешают."),
                    D("Моторы в свободном ходе — пульт не даёт команд", False,
                      "Рычаги подняты, и свободный ход не мешает лифту."),
                ],
                steps=[
                    # source: E4 p9 — ровный пол, не под столом, зона свободна (до любой попытки движения)
                    S("Проверь: коляска на ровном полу, сверху ничего, вокруг ножниц пусто.",
                      "eyes", "seat_lift",
                      "Сиденье сейчас поедет — ему нужно место.", alt=("seat",)),
                    # source: QL3 p8 — key 2 -> экран сиденья; джойстик вперёд/назад двигает выбранный актуатор
                    S("Включи пульт.", "hands", "controller", ""),
                    S("Кнопкой key 2 открой экран сиденья и выбери «подъём».", "hands", "controller",
                      "Режим подъёма выбран — сиденьем управляет джойстик."),
                    S("Дай джойстик назад.", "hands", "controller",
                      "Сиденье дёрнулось и встало, актуатор гудит. Отпусти джойстик — не держи мотор под нагрузкой.",
                      alt=("seat_lift",)),
                    # source: QL3 p8 — значения индикатора; TB4 p6 — перед движением убедиться, что в механизм ничего не попадёт
                    S("Сверь индикатор на пульте с таблицей в мануале Q-Logic 3.", "eyes", "controller",
                      "Цвет индикатора различает поломку, защиту и помеху.",
                      mini=dict(kind="meter", reading="ЖЁЛТЫЙ · iLevel · кодов нет",
                                sub="Q-Logic 3: зелёный — без ограничений, жёлтый — сиденье поднято, скорость "
                                    "снижена, красный — полная блокировка",
                                prompt="Сиденье упирается и гудит, индикатор жёлтый. Что дальше?",
                                options=[
                                    ("Блокировки нет — что-то мешает механически: обесточить и осмотреть ножницы",
                                     True, ""),
                                    ("Красная блокировка по углу сиденья", False,
                                     "Индикатор жёлтый, не красный — контроллер ничего не запрещает."),
                                    ("Жать джойстик дольше — продавит", False,
                                     "Силой через помеху — это сломанный актуатор или прищемлённая рука."),
                                ])),
                    # source: E4 p7 — автомат на батарейном лотке; выключить, прежде чем лезть к механизму
                    S("Выключи пульт.", "hands", "controller",
                      "К механизму — только на обесточенной коляске: сначала пульт, потом автомат."),
                    S("Сними заднюю крышку батарейного отсека и нажми жёлтую кнопку автомата.", "hands", "battery",
                      "Батареи отключены — актуатор не включится, пока ты под сиденьем."),
                    # source: TB4 p4 — Pinch/Crush points; TB4 p6 — Keep all mechanical areas clear
                    S("Осмотри ножницы с фонариком снаружи: что мешает им сложиться?", "eyes", "seat_lift",
                      "Ящик «Зикс-Бокс» стоит ровно там, куда должна прийти рама сиденья.",
                      "Барти: «Дай сиденью разок придавить ящик — оно тяжёлое, сомнёт!» — нет! Ножницы — точки "
                      "защемления: сминать ими что-либо запрещено, можно сломать актуатор и раму.", ghost_wrong=True),
                    S("Срежь стяжки и вытащи ящик из-под сиденья, не залезая руками между ножниц.", "hands", "seat_lift",
                      "Ящик — сбоку от механизма, тянем его наружу, а не через ножницы.", alt=("seat",)),
                    S("Проверь, что между рамой сиденья и основанием больше ничего нет: ни гаек, ни стяжек.",
                      "eyes", "seat_lift",
                      "Одна гайка в ножницах — и всё повторится.", alt=("seat",)),
                    # source: E4 p7 — питание возвращают, опустив рычажок автомата
                    S("Опусти рычажок автомата и поставь крышку на место.", "hands", "battery",
                      "Рычажок вниз — батареи подключены."),
                    S("Включи пульт.", "hands", "controller", ""),
                    S("Кнопкой key 2 открой экран сиденья и выбери «подъём».", "hands", "controller",
                      "Режим подъёма выбран — сиденьем управляет джойстик."),
                    # source: QL3 p8 — «чтобы вернуться к зелёному — обратное движение»; значок iLevel гаснет внизу
                    S("Дай джойстик назад: сиденье опускается до конца.", "hands", "controller",
                      "Ножницам есть куда складываться — сиденье едет ровно.", alt=("seat_lift",)),
                    S("Посмотри на пульт: сиденье внизу — жёлтый погас, значок iLevel пропал.", "eyes", "controller",
                      "Зелёный — скорость снова полная, можно на улицу."),
                    # source: TB4 p7 — матрица блокировок: поднятое сиденье блокирует наклон и откидку;
                    # наклон/откидка больше 20° блокируют подъём; TB4 p6 — блокировки не обходить
                    S("Зикс просит заодно сделать «режим сиесты» при поднятом сиденье. Сверь с матрицей блокировок TRU-Balance.",
                      "eyes", "controller",
                      "Матрица в мануале TRU-Balance 4 — что с чем не совмещается.",
                      mini=dict(kind="meter", reading="Матрица блокировок TRU-Balance 4",
                                sub="Поднято → наклон и откидка заблокированы, 1/4 скорости. Наклон или откидка "
                                    "больше 20° → подъём заблокирован",
                                prompt="Откинуть спинку, пока сиденье наверху?",
                                options=[
                                    ("Нет: при поднятом сиденье наклон и откидка заблокированы — сначала опустить", True, ""),
                                    ("Можно, если откинуть не больше 20°", False,
                                     "20° — это предел, при котором ещё РАЗРЕШЁН подъём. Поднятое сиденье наклон блокирует совсем."),
                                    ("Можно, если перепрограммировать блокировку", False,
                                     "Заводские блокировки запрещено обходить и перенастраивать: это защита от опрокидывания."),
                                ])),
                ],
                test="Сиденье плавно едет вниз, жёлтый индикатор гаснет, Зикс выкатывает за порог на полной скорости. "
                     "Ящик с гайками переехал на полку — на нижнюю.",
                # source: TB4 p4, p6 (clear mechanism), TB4 p7 (inhibit matrix), QL3 p8
                fact="Перед каждым движением сиденья мануал TRU-Balance велит проверить, что в механизм ничего не "
                     "попадёт: ножницы лифта — точки защемления. Если сиденье упирается, а индикатор не красный, — "
                     "не дожимай джойстиком: обесточь и ищи помеху. Поднятое сиденье блокирует наклон и откидку, "
                     "а наклон больше 20° — подъём.",
                thanks="Зикс: «Значит, “Зикс-Бокс” и лифт не дружат. Переставлю на полку. На нижнюю. Спасибо, костлявый!»",
            ),
        ],
    ),

    # === 7. Чародейка: джойстик дёргает + порван пыльник + влага ===
    dict(
        id="joystick", kind="power", client="Чародейка Мора",
        client_art="client_sorceress.png", chair_art="chair_m3.png",
        chair_model="m3", chair_name="Permobil M3 Corpus (средний привод)",
        title="Джойстик дёргает, порван пыльник",
        symptom="Коляску уводит и дёргает при управлении, резиновый пыльник у основания джойстика порван. "
                "Мора недавно попала под ливень.",
        parts=["joystick", "boot", "wiring", "controller", "battery"],
        inspect={
            "joystick": "Джойстик чуть залипает и не всегда возвращается в центр.",
            "boot": "Резиновый пыльник у основания порван — внутрь могла попасть влага.",
            "wiring": "Разъём кабеля джойстика сидит неплотно.",
            "controller": "Пульт изредка пищит, на дисплее — ошибка джойстика (не мотора).",
            "battery": "Заряд в норме.",
        },
        diagnosis=[
            D("Джойстик залит и загрязнён, пыльник порван", True),
            D("Сгорел мотор — коляску уводит в сторону", False, "На дисплее ошибка джойстика, а не мотора, и джойстик залипает — уводит из-за него."),
            D("Села батарея — коляска дёргается", False, "Заряд в норме — смотри осмотр батареи."),
        ],
        steps=[
            S("Выключи коляску кнопкой на пульте.", "hands", "controller",
              "Мокрую электронику не держат под питанием: вода + ток = короткое замыкание."),
            S("Промокни пульт сухой тряпкой.", "cloth", "controller",
              "Теперь коляска сохнет в тепле ~12 ч: мокрую не включают.",
              "Барти: «Включи сразу — проверим, жива ли!» — нет: мокрую электронику сначала сушат.",
              ghost_wrong=True, alt=("joystick",)),
            S("После просушки включи пульт.", "hands", "controller",
              "Перезагрузка часто «будит» джойстик.",
              "Барти: «Выключи и включи. Великая магия XXI века, говорят.»"),
            S("Посмотри на дисплей пульта: какой код он показывает?", "eyes", "controller",
              "Код подсказывает, где искать: тут — джойстик, не мотор."),
            S("Снова выключи пульт — дальше работаем на выключенной коляске.", "hands", "controller",
              "Под питанием отклонённый джойстик — это команда ехать."),
            S("Отклони ручку джойстика и отпусти: она должна сама вернуться в центр.", "hands", "joystick",
              "Коляска выключена, поэтому щупать ручку безопасно. Погнутая ручка или вялая пружина — к технику."),
            S("Протри джойстик сухой тряпкой от грязи и пыли.", "cloth", "joystick",
              "Грязь у основания мешает отклику.", alt=("controller", "boot")),
            S("Проверь и передёрни разъём кабеля джойстика (питание выключено).", "hands", "wiring",
              "Ослабший разъём кабеля — частая причина рывков. Разъёмы трогаем только на выключенной коляске."),
            S("Срочно замени порванный резиновый пыльник джойстика.", "hands", "boot",
              "Порванный пыльник пускает влагу в электронику — меняем немедленно, пока коляска выключена.",
              "Барти: «Замотай скотчем!» — нет, влага убьёт плату, нужен новый пыльник.", ghost_wrong=True),
            S("Включи пульт.", "hands", "controller", "Пыльник новый, разъём плотный — можно включать."),
            S("Легонько толкни джойстик: проедь на малой скорости и проверь отклик.",
              "hands", "controller",
              "Если всё ещё дёргает — калибровку делает техник сервисным программатором, сам её не перенастраивай.",
              alt=("joystick",)),
        ],
        test="Джойстик чётко возвращается в центр, коляска едет ровно, пыльник цел и сухо.",
        fact="Мокрую коляску сначала сушат и только потом включают. Джойстик лечат перезагрузкой, чисткой и "
             "проверкой разъёма (на выключенной коляске), а калибровку делает техник программатором. Порванный "
             "пыльник меняют сразу: влага губит электронику. Сложную электронику доверяй сертифицированному технику.",
        thanks="Мора: «И никакой магии — просто руки. Впечатляет, мертвец.»",
    ),

    # === 8. Голем: заглохла; свободный ход + разъёмы мотора ===
    dict(
        id="freewheel", kind="power", client="Голем Грунд",
        chair_model="trident", chair_name="Drive Trident HD (бариатрическая, передний привод)",
        client_art="client_golem.png", chair_art="chair_trident.png",
        title="Заглохла; вой мотора и увод",
        symptom="Тяжёлая коляска голема заглохла посреди мастерской (село питание), а до этого мотор "
                "подвывал и тянул вбок.",
        parts=["freewheel", "motor", "wiring", "battery", "axle", "controller", "frame"],
        inspect={
            "freewheel": "У моторов рычаги свободного хода с жёлтыми наконечниками. Сейчас подняты — моторы в режиме "
                         "езды, вручную коляску не сдвинуть.",
            "motor": "Один мотор подвывает сильнее другого.",
            "wiring": "Разъём одного мотора сидит неплотно.",
            "battery": "Батарея разряжена в ноль.",
            "axle": "В оси намотался мусор.",
            "controller": "Пульт погас — нет питания.",
            "frame": "Рама цела.",
        },
        diagnosis=[
            D("Сначала свободный ход и откатить, потом искать причину", True),
            D("Тащить волоком на включённых моторах — так быстрее", False, "На включённых моторах не катится, можно повредить привод."),
            D("Сразу менять мотор: он подвывал и тянул вбок", False, "Сперва простое: разъёмы, мусор в колёсах, шум."),
        ],
        steps=[
            S("Выключи питание кнопкой на пульте — даже если экран погас: пульт мог просто уснуть, а коляска всё ещё "
              "включена.", "hands", "controller",
              "Свободный ход включают ТОЛЬКО при выключенном питании, иначе ошибка контроллера.",
              "Барти: «Дёрни рычаги прямо на ходу!» — ни в коем случае, сначала выключи питание.", ghost_wrong=True),
            S("На ровном месте опусти оба рычага свободного хода (жёлтые наконечники).", "hands", "freewheel",
              "Свободный ход отключает моторы — и тормоза! Никогда не делай это на уклоне."),
            S("Откати коляску к верстаку, стоя сбоку от неё.", "hands", "frame",
              "В свободном ходе тормозов нет; держись сбоку, не спереди и не сзади."),
            S("Убери мусор и намотку из колёс и оси.", "brush", "axle",
              "Препятствия в колёсах дают рывки и увод в сторону."),
            S("Передёрни разъёмы моторов и датчиков (освежить контакт).", "hands", "wiring",
              "Ослабший разъём мотора прерывает сигнал — отсюда вой и увод."),
            S("Верни рычаги свободного хода вверх (режим езды).", "hands", "freewheel",
              "Обязательно верни моторы в режим езды — иначе тормоза не работают."),
            S("Поставь батарею на зарядку штатным зарядным устройством.", "charger", "battery",
              "Батарея разряжена в ноль — отсюда и «заглохла».", alt=("controller",)),
            S("После зарядки включи пульт.", "hands", "controller", "Рычаги в режиме езды — можно включать."),
            S("Легонько толкни джойстик: проедь на малой скорости и послушай моторы — оба должны звучать одинаково.",
              "hands", "controller",
              "Вой/стук = износ подшипников или ремня → к сертифицированному технику.", alt=("motor",)),
        ],
        test="Батарея заряжена, рычаги в режиме езды, разъёмы плотные. Грунд проезжает круг — моторы звучат "
             "ровно, коляску больше не уводит.",
        fact="Свободный ход (жёлтые рычаги у моторов) даёт катить коляску вручную — только при ВЫКЛЮЧЕННОМ "
             "питании и на ровном месте, ведь тормоза при этом отключены. Многие «отказы мотора» — это ослабшие "
             "разъёмы; внутренности мотора и контроллера чинит техник.",
        thanks="Грунд: «ГРУНД. КАТИТСЯ. ГРУНД ДОВОЛЕН.»",
    ),
]

# ----------------------------------------------------------------------------- #
#  Вторая волна (2026-10-16): 8 реальных колясок из базы мануалов BARC.
#  Шаги и цифры — из инструкций производителей (страницы — в комментариях source:);
#  пометка GAME — игровое допущение там, где мануал отсылает к боковине шины и т.п.
#  Черновики: art_tests/new_jobs_manual.py, art_tests/new_jobs_power.py.
# ----------------------------------------------------------------------------- #
PARTS.update({"seat_lift": "Подъёмник сиденья", "actuator": "Актуатор (привод) лифта"})
PARTS.update({'anti_tip': 'Антиопрокидыватель', 'backrest': 'Спинка (стойки, обивка)', 'tilt_cable': 'Трос наклона', 'tilt_lever': 'Курок наклона', 'tilt_lock': 'Замок наклона (рокер/зубья)', 'gas_spring': 'Газовая пружина спинки', 'armrest': 'Откидной подлокотник', 'seat_cable': 'Разъём сиденья', 'breaker': 'Главный автомат', 'brushes': 'Щётки мотора', 'mag_brake': 'Электромагн. тормоз'})
MANUAL.update({
    "vr2_codes": ("Quickie Pulse 6 · коды VR2 и щётки мотора", [
        # source: sunrise/quickie_pulse_6_service_manual.pdf p26 (printed 2.1), p27-31 (3.1-3.5)
        "Код VR2 = число БЫСТРО мигающих делений индикатора батареи: 1 — низкое напряжение батареи; "
        "2 — левый мотор отключён; 3 — замыкание проводки левого мотора; 4 — правый мотор отключён; "
        "5 — замыкание проводки правого; 6 — подключена зарядка; 7 — джойстик; 8 — система управления; "
        "9 — тормоз (соленоид); 10 — высокое напряжение батареи.",
        # source: P6_SM p26 (printed 2.1); p44 (printed 5.10)
        "Батареи: две группы 22 последовательно. Полная пара ≈25,6 В (12,8 В каждая), разряженная — 24 В и ниже. "
        "Индикатор краснеет с 22 В; контроллеру нужно 18 В для старта и не меньше 16 В для работы.",
        # source: P6_SM p27 (printed 3.1)
        "Код 2: сначала заряд батарей и все разъёмы (ищи болтающийся или битый разъём левого мотора). "
        "Затем мультиметр на двух НИЖНИХ (толстые провода) контактах 4-пинового разъёма мотора: "
        "0–1,5 Ом — мотор цел, менять контроллер; иначе — проверять щётки левого мотора.",
        # source: P6_SM p49 (printed 6.3)
        "Норма: большие контакты (щётки + мотор) ≈0,5–0,9 Ом; малые контакты (стояночный тормоз) ≈12–15 Ом.",
        # source: P6_SM p48 (printed 6.2) — разъём отсоединяют от модуля управления перед замером
        "Сопротивление меряют на ОТСОЕДИНЁННОМ от модуля управления разъёме мотора, при выключенном питании.",
        # source: P6_SM p27 (printed 3.1), p47-48 (printed 6.1-6.2)
        "Щётки: колпачок — плоской отвёрткой, без лишнего усилия; вынимать по одной и запоминать ориентацию. "
        "Менять, если щётка короче 1/4\" (≈6 мм), перегреты провод/пружина или торец не чистый и не острый.",
        # source: P6_SM p48 (printed 6.2)
        "Меняешь щётки — меняй в ОБОИХ моторах. Обкатка перед выдачей: редуктор разблокирован, "
        "мотор крутится 20–30 мин, попеременно вперёд и назад.",
        # source: P6_SM p44 (printed 5.10) Warning; p4 (printed 0.2)
        "Не разблокировал редуктор перед прогоном моторов — коляска поедет сама. После работ: питание выкл., "
        "передачи в зацеплении — толкнёшь сзади, коляска не должна катиться.",
    ]),
    "q6_qlogic": ("Quantum Q6 Edge · коды Q-Logic и тормоз", [
        # source: quantum/quantum_q6_edge_technical_troubleshooting_INFMANU4109_revB_2012.pdf p29
        "#36 — джойстик не в центре дольше 5 с при включении: отпусти, перезапусти. "
        "#37 — джойстик отключён/неисправен. #38 — джойстик вне диапазона: не откалиброван — калибровка, "
        "замена джойстика или модуля.",
        # source: quantum/quantum_q_logic_1_technical_manual.pdf p34 — калибровку ведёт ручной программатор
        "Калибровку джойстика делают через ручной программатор Q-Logic (он сам ведёт по шагам); "
        "обычно она нужна только после замены джойстика.",
        # source: Q6_TS p29; Q6_OM p23, p28 (printed 22)
        "#105 — батарея пуста: зарядить (8–14 ч после дня езды).",
        # source: Q6_TS p29; QL_TM p92 (M1 = левый мотор в стандартной конфигурации)
        "#192/#193 — мотор 1/2 отключён. #203/#204 — тормоз 1/2 отключён: выдернут разъём мотора, обрыв "
        "проводки тормоза, неисправен тормоз или занижено напряжение батареи в настройках. "
        "Мотор/тормоз 1 = ЛЕВЫЙ (стандартная раскладка M1).",
        # source: Q6_OM p10 (NOTE про ошибку при свободном ходе на включённом питании)
        "Свободный ход включают только при выключенном питании, иначе контроллер выдаст ошибку. "
        "Сброс: выключить, рычаги в режим езды, включить.",
        # source: Q6_TS p16 (Motor/Brake Error), p31 (Appendix 2)
        "Тормоз: оба рычага свободного хода — в режим езды; снять задний кожух, отсоединить модуль питания "
        "от задней рамы, выдернуть разъём ЛЕВОГО мотора; контакты 3–4: ≈80 Ом. Не ≈80 — менять левый мотор. "
        "Левый ≈80 — мерить правый; не ≈80 — менять правый; оба ≈80 — менять модуль питания.",
        # source: Q6_TS p14-15 (Open Motor Error)
        "Обмотка мотора (контакты 1–2 того же разъёма): ≈0,5–1,5 Ом. Щётки менять, если повреждены "
        "или короче 0,25\".",
        # source: Q6_TS p4 (No power: гнездо зарядки джойстика)
        "Заряд: мультиметр на гнездо зарядки джойстика — около 25 В норма; меньше 18 В — сначала зарядить.",
        # source: Q6_OM p26 (Weekly checks: check the brakes)
        "Тест тормозов: ровная площадка, 1 м свободно вокруг; малая скорость; джойстик плавно вперёд до "
        "щелчка тормоза — сразу отпустить. Повторить назад, влево, вправо.",
    ]),
})

JOBS += [
    # --- ручные и наклоняемые: TiLite Aero Z, Etac Cross 6, Zippie Iris, Ki Focus CR ---


    # === A. TiLite Aero Z: тормоз-замок не держит на уклоне (ПРОСТОЕ) ===
    # source: tilite/tilite_aero_z_zra_owners_manual_en.pdf
    #   p15  — замки могут проскальзывать при низком давлении
    #   p18  — уклоны не круче 10%; замки — НЕ тормоза
    #   p22  — шины: проверять давление КАЖДУЮ неделю (норма — на боковине); упор ≥ 3/16" в шину
    #   p26  — после любой регулировки весь крепёж затянуть до поездки
    #   p27  — чек-лист: замок вдавливается на нужную глубину, не мешает шине в отпущенном виде
    #   p70–72 — регулировка: ослабить (не выкручивать) винты хомута ключом 3/16", сдвинуть хомут,
    #            затянуть; регулировать ТОЛЬКО на накачанной шине; после — толкнуть и проверить
    #   p8   — лимит веса 265 lb (120 кг) для сиденья 13"+
    dict(
        id="aeroz_lock", kind="manual", client="Кицунэ Юки", client_art="client_aeroz.png",
        chair_art="chair_aeroz.png",
        chair_model="aeroz", chair_name="TiLite Aero Z (активная, жёсткая рама)",
        title="Тормоз-замок не держит на уклоне",
        symptom="Юки ставит коляску на замки у пандуса кофейни, а та потихоньку сползает: "
                "левое колесо проворачивается под замком.",
        parts=["tire", "valve", "rear_wheel", "brake", "bolts", "anti_tip", "axle", "spokes"],
        inspect={
            "tire": "Левая шина мягкая на ощупь. На боковине написано 90–110 psi — явно меньше.",
            "valve": "Ниппель цел, колпачок на месте. Воздух уходит не через него — просто давно не качали.",
            "rear_wheel": "Колесо крутится ровно, сидит на оси плотно.",
            "brake": "В зажатом положении упор замка едва касается левой шины. На трубе рамы — светлый след: "
                     "хомут съехал назад со старого места.",
            "bolts": "Два винта хомута замка (шестигранник 3/16\") подразболтались.",
            "anti_tip": "Антиопрокидыватели опущены и защёлкнуты, колёсики целы. К замку отношения не имеют.",
            "axle": "Быстросъёмная ось защёлкнута, кнопка вышла полностью, люфта нет.",
            "spokes": "Спицы натянуты ровно, колесо не «восьмерит».",
        },
        diagnosis=[
            D("Мало давления в шине и сполз хомут замка", True),
            D("Замок сломан — менять узел целиком", False,
              "Замок исправен, его просто сдвинуло. По мануалу сначала давление, потом положение хомута."),
            D("Ослабла быстросъёмная ось, колесо проворачивается", False,
              "Ось защёлкнута и без люфта. Колесо крутится, потому что его не держит замок."),
            D("Надо сильнее тянуть рычаг замка на спуске", False,
              "Замки — НЕ тормоза: ими нельзя замедлять едущую коляску. Они только держат стоящую."),
        ],
        steps=[
            # source: p22, p15
            S("Проверь манометром давление в обеих задних шинах и сравни с давлением, напечатанным на боковине шины.",
              "gauge", "tire",
              "TiLite: давление проверять КАЖДУЮ неделю. Если шина спущена, замок на этой стороне может проскальзывать.",
              "Барти: «Мастер говорил: замок держит не рычаг, а воздух. Я тогда не понял. Я и сейчас не понял.»",
              alt=("valve",)),
            # source: p70 (регулировать только на накачанной шине); число — GAME (мануал: «см. боковину»)
            S("Накачай шину через ниппель до давления, напечатанного на боковине. Замок регулируют только на накачанной "
              "шине!", "pump", "tire",
              "Если выставить замок на спущенной шине, после подкачки он будет работать неправильно.",
              "Барти: «Качай, качай... я считаю вслух. Раз. Два. Э-э... много.»",
              mini=dict(kind="pump", lo=90, hi=110, mx=140, unit="psi",
                        hint="На боковине этой шины: 90–110 psi")),
            # source: p70
            S("Ослабь, но НЕ выкручивай два винта хомута замка.", "allen", "brake",
              "Шестигранник 3/16\" (≈4,8 мм). Винты ослабляют, чтобы хомут можно было сдвинуть по раме.",
              "Барти: «Выкрути их совсем, чтоб не мешались!»", ghost_wrong=True,
              wrongmsg="Хомут ослабляют шестигранником 3/16\", и винты не выкручивают до конца.", alt=("bolts",)),
            # source: p22, p70–72
            S("Сдвинь хомут к шине так, чтобы зажатый упор вдавливался в шину минимум на 5 мм (3/16\").", "hands", "brake",
              "TiLite: упор должен вдавливаться в шину не меньше чем на 3/16\" (≈5 мм), иначе коляска может покатиться.",
              mini=dict(kind="gap", lo=5, hi=8, mn=0, mx=12, unit="мм", start=1,
                        label="Насколько упор вдавлен в шину",
                        hint="TiLite: не меньше 3/16\" ≈ 5 мм в зажатом положении",
                        fb_lo="Меньше 5 мм: на уклоне замок снова проскользнёт.",
                        fb_hi="Слишком глубоко: рычаг закрывается с трудом, а упор будет задевать шину.")),
            # source: p70, p26
            S("Затяни оба винта хомута, поочерёдно.", "allen", "brake",
              "После любой регулировки весь крепёж надёжно затягивают до поездки.", alt=("bolts",)),
            # source: p27
            S("Отпусти замок.", "hands", "brake", "Рычаг замка — в положение «отпущено»."),
            S("Прокрути колесо: упор не должен задевать шину.", "hands", "rear_wheel",
              "Чек-лист TiLite: в отпущенном виде замок не мешает шине, шарниры без износа и люфта.",
              alt=("tire", "spokes")),
            # source: p70, p18, p22
            S("Зажми оба замка.", "hands", "brake", "Упор вдавился в шину — теперь тест на сдвиг."),
            S("Сильно толкни коляску, взявшись за колесо: колёса под замками не должны проворачиваться.", "hands", "tire",
              "Мануал требует этот тест после каждой регулировки замка.",
              "Барти: «Отлично, теперь на спуске можно тормозить этими замками!» Нет! Замки — не тормоза.",
              ghost_wrong=True,
              wrongmsg="Проверка простая: толкни коляску рукой и смотри на колёса.", alt=("brake", "rear_wheel")),
        ],
        test="Юки ставит коляску на замки на пандусе и откидывается назад: ни миллиметра. "
             "Отпускает: колёса крутятся свободно и ничего не шуршит.",
        fact="TiLite: зажатый упор замка вдавливается в шину минимум на 3/16\" (≈5 мм). Регулируют его только "
             "на накачанной шине (норма на боковине, проверка раз в неделю). Замки — не тормоза, ими нельзя "
             "замедлять едущую коляску, а уклоны круче 10% мануал запрещает.",
        thanks="Юки: «Три хвоста благодарности! Теперь я пью кофе, а не догоняю коляску.»",
    ),

    # === B. Etac Cross 6: спинку перекосило (ПРОСТОЕ) ===
    # source: etac/etac_cross_6_user_manual.pdf
    #   p31  — угол спинки: гайка 13 мм на внутренней стороне крепления заднего колеса, ослабить
    #          у одной стойки, выставить, затянуть; вторую стойку так же; сравнить расстояние
    #          стойка ↔ пластина подлокотника с обеих сторон; высота спинки — винты 4/8 мм
    #   p13  — после ЛЮБОЙ регулировки проверить работу антиопрокидывателей, фиксатор защёлкнут
    #   p15  — обивка спинки: настраивается, когда человек сидит; нижний ремень (опора таза), потом верхний;
    #          не перетягивать верхние ремни (мешает складыванию); подушка — углами между стойками
    #   p32  — тормоз: штифт в 15–20 мм от шины в отпущенном виде, винт ~5 Н·м, зависит от давления
    #   p6–7 — давление: проверять раз в месяц; шины high pressure 110 psi / 7,5 бар; лимит 135 кг
    dict(
        id="cross6_back", kind="manual", client="Дриада Ивушка", client_art="client_cross6.png",
        chair_art="chair_cross6.png",
        chair_model="cross6", chair_name="Etac Cross 6 (складная, регулируемая)",
        title="Спинку перекосило",
        symptom="Ивушку весь день тянет вбок: спинка поддерживает с одной стороны и «проваливается» с другой. "
                "К вечеру ноет спина.",
        parts=["backrest", "bolts", "cushion", "tire", "brake", "anti_tip"],
        inspect={
            "backrest": "Левая стойка спинки откинута назад сильнее правой. Обивка натянута косо.",
            "bolts": "Гайка 13 мм на внутренней стороне крепления левого колеса чуть ослаблена. "
                     "На металле видны следы: стойка проворачивалась.",
            "cushion": "Подушка лежит правильно: скруглёнными углами между стойками спинки.",
            "tire": "Шины накачаны как надо: 110 psi (7,5 бар), как на боковине.",
            "brake": "Тормоза держат. Штифт в отпущенном положении в 15–20 мм от шины, это норма.",
            "anti_tip": "Антиопрокидыватели на месте, фиксатор защёлкнут.",
        },
        diagnosis=[
            D("Ослабла гайка угла на одной стойке спинки", True),
            D("Растянулась обивка: хватит подтянуть ремни", False,
              "Ремни меняют форму спинки, но не угол стоек. Перекос в самих стойках."),
            D("Клиентка «неправильно сидит» — дело в осанке", False,
              "Дело не в посадке. Посмотри на стойки: они стоят под разным углом, так никто ровно не усидит."),
        ],
        steps=[
            # source: p32 (тормоза — стояночные)
            S("Зажми оба тормоза коляски, стоящей на ровном полу. Ивушка пересаживается на скамью.", "hands", "brake",
              "Угол стоек меняем на пустой коляске: так безопаснее, и стойка двигается свободно.",
              "Барти: «Мастер всегда говорил: сначала тормоза, потом философия.»"),
            # source: p31
            S("Рулеткой замерь расстояние от каждой стойки спинки до пластины подлокотника.", "tape", "backrest",
              "Etac сверяет угол спинки именно так: расстояние стойка ↔ пластина подлокотника должно совпадать с обеих сторон."),
            # source: p31
            S("Ослабь гайку 13 мм на внутренней стороне крепления левого колеса.", "wrench", "bolts",
              "Угол спинки держит эта гайка. Винты 4 и 8 мм на стойках отвечают за ВЫСОТУ спинки, их не трогаем.",
              "Барти: «Да крути все винты на спинке подряд, какой-нибудь да тот!»", ghost_wrong=True,
              wrongmsg="Угол стойки держит гайка 13 мм у крепления колеса — её ослабляют разводным ключом.",
              alt_tools=("socket",)),
            # source: p31 (равенство сторон); допуск ±1 мм — GAME
            S("Выставь левую стойку так, чтобы расстояние совпало с правой стороной.", "hands", "backrest",
              "Etac: угол обеих стоек одинаковый.",
              mini=dict(kind="gap", lo=39, hi=41, mn=20, mx=60, unit="мм", start=52,
                        label="Левая стойка ↔ пластина подлокотника",
                        hint="Справа намерено 40 мм. Выставь слева так же",
                        fb_lo="Перебор: теперь стойку завалило в другую сторону.",
                        fb_hi="Ещё не совпало с правой стороной: спинку всё ещё перекашивает.")),
            # source: p31
            S("Затяни гайку 13 мм.", "wrench", "bolts",
              "Затянутая гайка не даст стойке снова провернуться под весом.", alt_tools=("socket",)),
            # source: p15
            S("Ивушка садится обратно. Подстрой нижний ремень обивки — опора таза.", "hands", "backrest",
              "Etac: обивку настраивают, когда человек сидит в коляске, — снизу вверх."),
            S("Подстрой верхние ремни обивки, не перетягивая.", "hands", "backrest",
              "Верхние ремни не перетягивай: коляска будет хуже складываться.",
              "Барти: «Затяни всё как барабан!» Нет: спинка должна повторять изгиб спины."),
            # source: p13, p31
            S("Проверь антиопрокидыватели: опущены, фиксатор защёлкнулся.", "hands", "anti_tip",
              "Etac: после ЛЮБОЙ регулировки коляски проверяют работу антиопрокидывателей. Если они не работают, коляска может опрокинуться.",
              "Барти: «Сними эти колёсики сзади, только мешают!»", ghost_wrong=True,
              wrongmsg="Антиопрокидыватели не снимают, а проверяют рукой: опущены и защёлкнуты."),
        ],
        test="Ивушка проезжает между стеллажами: сидит ровно, спинка поддерживает одинаково с обеих сторон, "
             "вбок больше не тянет.",
        fact="Etac Cross 6: угол спинки задаётся гайкой 13 мм на внутренней стороне крепления колеса, отдельно "
             "для каждой стойки. Мануал требует ставить обе стойки одинаково и сверять расстояние до пластины "
             "подлокотника. После любой регулировки проверь антиопрокидыватели.",
        thanks="Ивушка (шёпотом): «Будто корни снова ровно вросли. Спасибо, мастер. Книгу вернёте без штрафа.»",
    ),

    # === C. Zippie Iris (детская, наклон в пространстве): качает назад, наклон «клацает» (СРЕДНЕЕ) ===
    # source: zippie/quickie_zippie_iris_owner_s_manual_en.pdf
    #   p5   — лимит веса Zippie IRIS 225 lb (102 кг)
    #   p9   — уклоны не круче 6°
    #   p12  — перед наклоном: руки ребёнка на подлокотниках, ноги на подножке; не наклонять дальше,
    #          чем спинка параллельна полу; не класть руки в механизм наклона
    #   p13  — давление по таблице (22" — 65 psi / 448 кПа); антиопрокидыватели 38–51 мм (1½–2"),
    #          выше 51 мм — могут не удержать, ниже 38 мм — цепляются
    #   p14  — замки: вдавливаться в шину ≥ 1/8" (3 мм); низкое давление → проскальзывание
    #   p15  — давление раз в неделю; чек-лист: тросы наклона и плунжер, рокер, антиопрокидыватели
    #   p16  — антиопрокидыватель: кнопка (J), одно из отверстий, ОБА колёсика строго на одной высоте
    #   p20  — наклон: оба курка одновременно отпускают механизм, отпустил — рокеры заблокированы
    #   p27  — регулировка троса: ослабить контргайку (G), вращать регулятор (H) до исчезновения провиса,
    #          плунжер-штифт должен полностью выдвигаться/убираться и входить в рокер; затянуть гайку;
    #          НЕ смазывать компоненты механизма
    dict(
        id="iris_tilt", kind="manual", client="Дракончик Искра", client_art="client_iris_mom.png",   # с мамой за спиной
        chair_art="chair_iris.png",
        chair_model="iris", chair_name="Zippie Iris (детская, наклон в пространстве)",
        title="Наклон «клацает», коляску качает назад",
        symptom="Когда кресло Искры наклоняют назад, оно глухо «клацает» и будто проседает ещё чуть-чуть. "
                "А на ковре коляску покачивает назад и вбок.",
        parts=["anti_tip", "tilt_cable", "tilt_lock", "tilt_lever", "tire", "brake"],
        inspect={
            "anti_tip": "Левое колёсико антиопрокидывателя стоит на отверстие выше правого: "
                        "до пола слева ~62 мм, справа ~45 мм.",
            "tilt_cable": "Трос правого курка провисает, у курка заметный свободный ход.",
            "tilt_lock": "Справа штифт-плунжер входит в рокер не до конца и еле цепляет.",
            "tilt_lever": "Оба курка целы и пружинят. Стопорный штифт на шнурке на месте.",
            "tire": "Шины 22\": давление 65 psi, как в таблице мануала.",
            "brake": "Замки зажимаются и вдавливаются в шину больше чем на 3 мм, это норма.",
        },
        diagnosis=[
            D("Антиопрокидыватели на разной высоте, трос провис", True),
            D("Сломан весь механизм наклона, менять раму", False,
              "Механизм цел: штифт просто не дотягивается из-за провисшего троса. Это регулировка, а не замена."),
            D("Ребёнок слишком активно ёрзает в кресле", False,
              "Дело не в ребёнке: коляска должна быть надёжной при любых движениях. Ищи причину в механике."),
            D("Смазать трос маслом, и всё пройдёт", False,
              "Мануал Iris запрещает смазывать механизм наклона. Провис убирают регулятором."),
        ],
        steps=[
            # source: p16, p14
            S("Зажми оба замка коляски, стоящей на ровном полу. Искра пересаживается к маме на руки.", "hands", "brake",
              "На ровной поверхности замеры честные. Замок должен вдавливаться в шину не меньше чем на 3 мм (1/8\").",
              "Барти: «Привет, малыш! Я призрак, но добрый. Почти не страшный. Ну, чуть-чуть.»"),
            # source: p13, p16
            S("Рулеткой замерь зазор от колёсиков антиопрокидывателей до пола с обеих сторон.", "tape", "anti_tip",
              "Норма Iris: 38–51 мм (1½–2\") в опущенном положении."),
            # source: p13, p16
            S("Нажми кнопку колёсика левого антиопрокидывателя и переставь его в отверстие ниже.", "hands", "anti_tip",
              "Iris: оба колёсика должны стоять СТРОГО на одной высоте.",
              mini=dict(kind="gap", lo=44, hi=46, mn=20, mx=80, unit="мм", start=62,
                        label="Зазор антиопрокидывателя до пола",
                        hint="Iris: 38–51 мм и строго как справа — 45 мм",
                        fb_lo="Ниже, чем справа: колёсики должны стоять на одной высоте (45 мм).",
                        fb_hi="Выше, чем справа (45 мм): коляску снова будет качать, а выше 51 мм — не удержит.")),
            # source: p27
            S("Ослабь контргайку на регуляторе троса правого курка.", "wrench", "tilt_cable",
              "Регулятор троса стоит у ручки, рядом с курком.", alt=("tilt_lever",)),
            # source: p27
            S("Вращай регулятор троса, пока не уйдёт провис.", "hands", "tilt_cable",
              "Не перетягивай: штифт должен свободно выдвигаться и убираться.",
              "Барти: «Капни масла на трос, сам натянется!»", ghost_wrong=True,
              wrongmsg="Механизм наклона Iris не смазывают. Провис убирают регулятором, руками.",
              alt=("tilt_lever",)),
            # source: p27
            S("Нажми и отпусти курок, глядя на штифт-плунжер: нажат — штифт полностью убран, отпущен — полностью вошёл "
              "в рокер.", "hands", "tilt_lock",
              "Главный критерий правильной натяжки троса по мануалу.", alt=("tilt_lever",), alt_tools=("eyes",)),
            # source: p27
            S("Затяни контргайку.", "wrench", "tilt_cable",
              "Иначе регулятор открутится от вибрации, и трос снова провиснет.", alt=("tilt_lever",)),
            # source: p20, p12
            S("Нажми оба курка и наклони кресло назад.", "hands", "tilt_lever",
              "Механизм отпускается только обоими курками. Когда в кресле ребёнок, руки у него на подлокотниках, "
              "ноги на подножке.",
              "Барти: «Наклони до упора, пусть спинка ляжет горизонтально, веселее же!»", ghost_wrong=True,
              wrongmsg="Наклон проверяют обоими курками и руками. И никогда не дальше, чем спинка параллельна полу."),
            S("Отпусти курки: кресло должно жёстко встать.", "hands", "tilt_lock",
              "При отпускании курков рокеры блокируются — кресло стоит намертво.", alt=("tilt_lever",)),
        ],
        test="Искра снова в кресле: наклон назад плавный, без «клаца», и кресло намертво встаёт в любом положении. "
             "На ковре больше не качает: антиопрокидыватели на одной высоте.",
        fact="Zippie Iris: антиопрокидыватели ставят на 38–51 мм (1½–2\") от пола, обе стороны строго одинаково. "
             "Трос наклона натягивают регулятором, пока штифт не будет полностью входить в рокер, а смазывать "
             "механизм нельзя. Еженедельный чек-лист включает тросы, плунжер, рокер и антиопрокидыватели. "
             "Уклоны — не круче 6°.",
        thanks="Искра: «Ура! Теперь можно откинуться и смотреть на облака, как настоящий звездочёт!»",
    ),

    # === D. Ki Mobility Focus CR (наклон в пространстве): наклон «ползёт»/не отпускается (СРЕДНЕЕ) ===
    # source: ki-mobility/Focus-Eng-Spa.pdf
    #   p4   — уклоны не круче 9°; давление по боковине
    #   p13  — лимит веса 300 lb (136 кг), HD 400 lb (181 кг); 19 = Tilt Cable, 20 = Tilt Lock Trigger, 18 = Trigger Lock Pin
    #   p19  — откидывание спинки: тормоза + ровная поверхность; газовые пружины спинки;
    #          ПРЕДУПРЕЖДЕНИЕ: не оставлять человека в кресле с курками, зафиксированными открытыми;
    #          регулировка троса: контргайку ключами 10 мм и 3/8", регулятор до исчезновения провиса,
    #          но зубья фиксатора (cogs) полностью в зубьях поворотных рам; если зуб чиркает или у курка
    #          люфт — выкрутить регулятор; если зуб вышел из зацепления — вкрутить; затягивать ТОЛЬКО гайку;
    #          блокировка курка штифтом на шнурке
    #   p20  — обслуживание тросов: проверить настройку, прокладку, минимум изгибов; ЗАМЕНИТЬ при заломе
    #          или если не регулируется (рис. 27); ножной наклон: хомут вала, ключ 8 мм
    #   p25  — только одобренные запчасти Ki; не использовать WD-40/нефтяные растворители
    #   p26  — еженедельно: тест троса наклона и осмотр прокладки, изгибов, заломов; протирать направляющие
    #          поворотной рамы; антиопрокидыватели ровные и рабочие; ежемесячно крепёж 40 in-lb (4,51 Н·м)
    dict(
        id="focuscr_cable", kind="manual", client="Бабушка Агата", client_art="client_focuscr_grandson.png",   # с внуком
        chair_art="chair_focuscr.png",
        chair_model="focuscr", chair_name="Ki Mobility Focus CR (наклон в пространстве)",
        title="Наклон «ползёт» и заедает",
        symptom="Внук жмёт курок, а кресло наклоняется рывками. Отпустит курок, и сиденье всё равно "
                "чуть «ползёт» назад. Иногда курок вообще не отпускает наклон.",
        parts=["tilt_cable", "tilt_lever", "tilt_lock", "gas_spring", "anti_tip", "brake"],
        inspect={
            "tilt_cable": "Под сиденьем трос наклона пережат стяжкой и согнут почти под прямым углом. "
                          "На оболочке залом.",
            "tilt_lever": "Курок ходит туго и не всегда возвращается. Стопорный штифт на шнурке на месте.",
            "tilt_lock": "Зубья поворотной рамы чистые и целые, но зуб фиксатора сидит в них не до конца.",
            "gas_spring": "Газовые пружины спинки держат угол. Они отвечают за откидывание спинки, а не за наклон.",
            "anti_tip": "Антиопрокидыватели опущены, стоят ровно.",
            "brake": "Замки зажимаются и держат.",
        },
        diagnosis=[
            D("Залом троса наклона: зуб фиксатора не садится", True),
            D("Подтянуть регулятор посильнее, и залом не страшен", False,
              "Ki Mobility: трос с заломом или такой, что не регулируется, ЗАМЕНЯЮТ. Регулятором залом не лечится."),
            D("Сели газовые пружины спинки — кресло ползёт", False,
              "Газовые пружины откидывают спинку, а не наклоняют сиденье. И они держат."),
            D("Залить трос WD-40, чтобы ходил мягче", False,
              "Мануал прямо запрещает WD-40 и нефтяные растворители: они повреждают узлы."),
        ],
        steps=[
            # source: p19
            S("Зажми замки кресла, стоящего на ровном полу. Агата пересаживается в кресло у окна.", "hands", "brake",
              "Ki: регулировки наклона и спинки делают на ровной поверхности с зажатыми замками.",
              "Барти: «Мадам Агата! Я призрак этой мастерской. Да, тот самый. Нет, не я уронил ваш телескоп в 1987-м.»"),
            # source: p20, p26
            S("Осмотри трос наклона по всей длине: заломы, резкие изгибы, неправильная прокладка.", "eyes", "tilt_cable",
              "Ki: тросы проверяют каждую неделю: работу, прокладку, изгибы и заломы."),
            # source: p20, p25
            S("Замени трос с заломом: ключом открути его крепления, сними старый и поставь новый оригинальный трос "
              "Ki Mobility.", "wrench", "tilt_cable",
              "Трос с заломом или такой, что не регулируется, только меняют. Запчасти ставь только одобренные Ki.",
              "Барти: «Выпрями его пассатижами, будет как новый!»", ghost_wrong=True,
              wrongmsg="Залом не выпрямляют, трос меняют целиком."),
            # source: p20 (рис. 27)
            S("Проложи новый трос по штатному пути: плавно, без резких изгибов и не пережимая стяжками.", "hands", "tilt_cable",
              "Ki: изгибов троса должно быть как можно меньше, тогда меньше трение."),
            # source: p19
            S("Ослабь контргайку регулятора троса ключами 10 мм и 3/8\".", "wrench", "tilt_cable",
              "Одним ключом держишь корпус регулятора, другим отпускаешь гайку.", alt=("tilt_lock", "tilt_lever")),
            # source: p19
            S("Вкручивай или выкручивай регулятор, пока не уйдёт провис. Зуб фиксатора должен остаться полностью в зубьях.", "hands", "tilt_cable",
              "Грубая настройка: основной провис ушёл. Точную доводку покажет проверка по всему диапазону.",
              alt=("tilt_lever", "tilt_lock")),
            # source: p19
            S("Наклоняй кресло вперёд-назад по всему диапазону и слушай зуб фиксатора: он не должен чиркать.", "hands",
              "tilt_lock",
              "Наклон должен фиксироваться в любом положении, а зуб не должен чиркать по зубьям.", alt=("tilt_lever",),
              mini=dict(kind="meter", reading="«тр-р-р» при наклоне",
                        sub="зуб фиксатора чиркает по зубьям поворотной рамы, курок с люфтом",
                        prompt="Что сделать с регулятором?",
                        options=[
                            ("Выкрутить регулятор ещё немного", True, ""),
                            ("Вкрутить регулятор дальше на корпус", False,
                             "Вкручивают, когда зуб совсем выходит из зацепления. Тут наоборот: он чиркает."),
                            ("Так и оставить, это нормальный звук", False,
                             "Ki: зуб не должен чиркать ни в одном положении. Иначе наклон снова начнёт ползти."),
                        ])),
            # source: p19 (зуб чиркает или у курка люфт -> выкрутить регулятор)
            S("Выкрути регулятор ещё немного — пока зуб не перестанет чиркать, а у курка не уйдёт люфт.",
              "hands", "tilt_cable",
              "Ki: зуб фиксатора полностью в зубьях и не чиркает ни в одном положении наклона.", alt=("tilt_lever", "tilt_lock")),
            # source: p19
            S("Затяни контргайку. Крути только гайку, не регулятор и не корпус.", "wrench", "tilt_cable",
              "Если провернуть регулятор или корпус, собьёшь только что найденную настройку.", alt=("tilt_lock", "tilt_lever")),
            # source: p19
            S("Верни кресло в нужное положение наклона.", "hands", "tilt_lever",
              "Наклон выбирают под задачу: отдых, еда, разгрузка таза.", alt=("tilt_lock",)),
            S("Вставь стопорный штифт в курок.", "hands", "tilt_lever",
              "Ki: курок блокируют штифтом после позиционирования — так наклон не отпустится случайно.",
              "Барти: «А зафиксируй курок ОТКРЫТЫМ и иди пить чай, пусть само встанет!»", ghost_wrong=True,
              wrongmsg="Нельзя оставлять человека в кресле с курками, зафиксированными открытыми: можно опрокинуться."),
            S("Слегка нажми курок и толкни ручки: наклон не должен отпускаться.", "hands", "tilt_lever",
              "Штифт держит: курок не отпускает наклон.", alt=("tilt_lock",)),
        ],
        test="Внук жмёт курок: кресло плавно наклоняется и намертво встаёт в любом положении. Ничего не ползёт "
             "и не шуршит, а курок возвращается сам.",
        fact="Ki Mobility Focus CR: трос наклона с заломом не регулируют, а меняют, и прокладывают с минимумом "
             "изгибов. Регулятор ставят так, чтобы не было провиса, а зуб полностью сидел в зубьях поворотной рамы. "
             "Тросы проверяют каждую неделю. Нельзя оставлять человека в кресле с курками, зафиксированными "
             "открытыми. Уклоны — не круче 9°.",
        thanks="Агата: «Угу. Теперь наклоняюсь плавно, как заходит луна. Благодарю, мастер. Вы приняты в мои созвездия.»",
    ),
    # --- электро: WHILL Model C2, Permobil F5 Corpus ---

    # === WHILL Model C2: красный код и не едет (3 варианта поломки) ===
    dict(
        id="whill_code", kind="power", client="Ящерка-картограф Сайра",
        client_art="client_whillc2.png", chair_art="chair_whillc2.png",
        chair_model="whillc2", chair_name="WHILL Model C2 (омни-колёса, литые задние шины)",
        title="Красный код на пульте — и не едет",
        symptom="Сайра включает свою WHILL, на экранчике пульта вспыхивает красный номер, пищит сигнал — "
                "и коляска сама выключается. «Утром ехала! Я даже записала!»",
        # source: whill/model-c2-user-manual.pdf p105 (printed 104): код + звук, затем выключение
        fact="У WHILL Model C2 каждая неполадка — свой номер на дисплее пульта. Таблица кодов подскажет, "
             "что делать, но сначала нужно прочитать код.",
        variants=[
            # --- А: код 02 — джойстик отклонён при включении ---
            dict(
                parts=["controller", "joystick", "armrest", "freewheel", "battery", "tire"],
                inspect={
                    "controller": "Дисплей пульта: красное «02» с вертикальной чертой, потом всё гаснет.",
                    "joystick": "Джойстик ходит плавно и сам встаёт в центр. Но Сайра включает коляску, "
                                "придерживая на пульте тубус с картами — тубус давит на джойстик.",
                    "armrest": "Подлокотники опущены и защёлкнуты.",
                    "freewheel": "Рычаги разблокировки тормозов подняты — тормоза заперты.",
                    "battery": "Батарея вставлена до щелчка, заряд почти полный.",
                    "tire": "Задние шины литые (airless) — качать нечего, протектор в норме.",
                },
                diagnosis=[
                    D("Код 02: джойстик не в нейтрали при включении", True),
                    D("Батарея разряжена — коляска выключается сама", False,
                      "Разряд — это коды 05/06, а батарея почти полная."),
                    D("Тормоза разблокированы — сработала защита", False,
                      "Это был бы код 03. Рычаги подняты — тормоза заперты."),
                ],
                steps=[
                    # source: whill/whill_c2_ci2_f_error_code_list.pdf p1 (коды 01-06)
                    S("Найди код с дисплея пульта в таблице кодов мануала WHILL.", "eyes", "controller",
                      "Коды выше 01–06 обычно лечит дилер, но сначала всегда — таблица.",
                      mini=dict(kind="meter", reading="02",
                                sub="таблица WHILL C2: 01 подлокотник, 02 джойстик, 03 тормоз, 04 зарядка, 05 ≤20 %",
                                prompt="Что значит код?",
                                options=[
                                    ("Джойстик был не в нейтрали в момент включения", True, ""),
                                    ("Заряд батареи 20 % или меньше", False,
                                     "Это код 05 — и при нём коляска не выключается, только предупреждает."),
                                    ("Тормоза разблокированы", False,
                                     "Это код 03. Тут — 02."),
                                ])),
                    # source: WHILL_UM p37 (printed 36): выключать питание при посадке/высадке
                    S("Убедись, что питание выключено: экран погас.", "eyes", "controller",
                      "Выключенная коляска не дёрнется от случайного касания."),
                    S("Убери с пульта всё, что давит на джойстик: тубус, сумку, край плаща.", "hands", "joystick",
                      "Джойстику хватает 1 Н, чтобы сдвинуться — это вес маленького яблока.",
                      # source: WHILL_UM p107 (printed 106): Force needed to operate joystick 1 N
                      alt=("controller",)),
                    # source: WHILL_UM p36 (printed 35): Check that the joystick moves smoothly
                    S("Проверь, что джойстик ходит плавно и сам возвращается в центр.", "hands", "joystick",
                      "Пункт ежедневного осмотра из мануала."),
                    # source: WHILL_UM p97 (printed 96): 70% ethyl alcohol, без растворителей
                    S("Протри пульт салфеткой, смоченной 70 % спиртом — без воды и растворителей.", "cloth", "controller",
                      "Мыть водой можно только колёса; пульт и электронику — нет.", alt=("joystick",)),
                    # source: WHILL_UM p36 (printed 35): before use check that the brakes are locked
                    S("Посмотри, что рычаги тормозов подняты (тормоза заперты).", "eyes", "freewheel",
                      "Иначе следующим вылезет код 03."),
                    # source: WHILL_ERR p1 (02: Turn on the device without touching the controller)
                    S("Включи питание, не касаясь джойстика. Руку — на пульт только после.", "hands", "controller",
                      "Пауза в секунду после включения — и никаких кодов.",
                      "Барти: «Держи джойстик вперёд, пока включаешь, — быстрее поедет!» "
                      "— нет: при включении джойстик не трогают, иначе код 02.", ghost_wrong=True),
                ],
                test="Дисплей показывает заряд, никакого «02». Сайра трогается плавно и делает круг по мастерской.",
                fact="Коды 01–04 у WHILL C2 — защита от случайного старта: поднятый подлокотник с пультом, "
                     "отклонённый джойстик, разблокированные тормоза, подключённая зарядка. Это не поломки: "
                     "убери причину и включи заново. Задние шины у C2 литые — их не качают.",
                thanks="Сайра: «Записала в журнал: “тубус — НЕ на пульт”. Спасибо, костяной мастер!»",
            ),
            # --- Б: код 01 — подлокотник с пультом не встал на место (песок в основании) ---
            dict(
                parts=["controller", "armrest", "joystick", "battery", "freewheel", "seat"],
                inspect={
                    "controller": "Дисплей пульта: красное «01», сигнал, коляска выключается.",
                    "armrest": "Правый подлокотник с пультом опущен, но не до щелчка: рычаг фиксатора "
                               "ходит туго, в основании — песок из пустыни.",
                    "joystick": "Джойстик в центре, ходит плавно.",
                    "battery": "Батарея вставлена до щелчка, заряд полный.",
                    "freewheel": "Рычаги тормозов подняты — тормоза заперты.",
                    "seat": "Сиденье сидит на стойке ровно, рычаг фиксатора опущен.",
                },
                diagnosis=[
                    D("Код 01: подлокотник с пультом не встал на место", True),
                    D("При включении тронули джойстик — сработала защита", False,
                      "Это код 02. А тут 01 — дело в подлокотнике."),
                    D("Сломался мотор — коляска не может тронуться", False,
                      "Ошибки мотора — коды 60–86. Код 01 — защита, а не поломка."),
                ],
                steps=[
                    S("Найди код с дисплея пульта в таблице кодов мануала WHILL.", "eyes", "controller",
                      mini=dict(kind="meter", reading="01",
                                sub="таблица WHILL C2: 01 подлокотник, 02 джойстик, 03 тормоз, 04 зарядка",
                                prompt="Что значит код?",
                                options=[
                                    ("Пультом пытались управлять при поднятом подлокотнике", True, ""),
                                    ("Джойстик был не в нейтрали при включении", False, "Это код 02."),
                                    ("Подключена зарядка", False, "Это код 04, а зарядки рядом нет."),
                                ])),
                    S("Убедись, что питание выключено: экран погас.", "eyes", "controller",
                      "Подлокотник двигают только на выключенной коляске."),
                    # source: WHILL_UM p106 (printed 105): arm release lever difficult to move -> dust in root
                    S("Осмотри основание подлокотника и рычаг фиксатора: что мешает защёлкнуться?", "eyes", "armrest",
                      "Мануал: тугой рычаг фиксатора = пыль и песок в основании."),
                    # source: WHILL_UM p106 (printed 105): clean with a brush or air duster;
                    # source: WHILL_UM p97 (printed 96): не наносить смазку/воск на подвижные части
                    S("Вычисти основание подлокотника щёткой.", "brush", "armrest",
                      "Только сухая чистка (щётка или груша): смазка липнет и собирает песок.",
                      "Барти: «Залей шарнир машинным маслом, погуще!» — нет: мануал запрещает "
                      "смазку и воск на подвижных частях — к ним липнет песок.", ghost_wrong=True),
                    # source: WHILL_UM p41 (printed 40): Rotate the arm forward. Check that the arm is locked.
                    # source: WHILL_UM p38 (printed 37): береги пальцы в шарнире подлокотника
                    S("Поверни подлокотник вперёд до щелчка и проверь, что он заперт.", "hands", "armrest",
                      "Пальцы — подальше от шарнира: там легко прищемить."),
                    S("Включи питание, не касаясь джойстика.", "hands", "controller",
                      "Кода нет — пульт в рабочем положении."),
                ],
                test="Подлокотник сидит с чётким щелчком, на дисплее заряд. Сайра пересаживается сбоку и обратно — "
                     "всё работает.",
                fact="Пульт WHILL C2 стоит на откидном подлокотнике: его поднимают, чтобы пересесть сбоку. "
                     "Если подлокотник не защёлкнулся, коляска выдаёт код 01 и не едет. Тугой рычаг "
                     "фиксатора чистят щёткой или продувают, смазку не используют.",
                thanks="Сайра: «Песок пустыни — в каждой щели. Теперь знаю, где у меня щётка. Спасибо!»",
            ),
            # --- В: код 10 — нет связи через разъём сиденья ---
            dict(
                parts=["controller", "seat", "seat_cable", "battery", "freewheel", "joystick"],
                inspect={
                    "controller": "Дисплей пульта: красное «10», сигнал, коляска выключается.",
                    "seat": "Сиденье стоит на стойке, но Сайра недавно снимала его для поездки в повозке.",
                    "seat_cable": "На контактах разъёма между сиденьем и базой — песок и мелкая пыль.",
                    "battery": "Батарея вставлена, заряд полный.",
                    "freewheel": "Рычаги тормозов подняты — тормоза заперты.",
                    "joystick": "Джойстик в центре, ходит плавно.",
                },
                diagnosis=[
                    D("Код 10: сбой связи через разъём сиденья",
                      True),
                    D("Замёрзла батарея — на холоде не держит напряжение", False,
                      "Холод — это код 14: коляска просто едет медленнее, а не выключается."),
                    D("Сразу менять пульт и контроллер", False,
                      "Замена пульта, кабеля сиденья или контроллера — последний пункт таблицы, и это работа дилера."),
                ],
                steps=[
                    S("Найди код с дисплея пульта в таблице кодов мануала WHILL.", "eyes", "controller",
                      mini=dict(kind="meter", reading="10",
                                sub="таблица WHILL C2: 10 — сбой связи по кабелю сиденья",
                                prompt="С чего начинаем по таблице?",
                                options=[
                                    ("Вынуть батарею и вставить обратно через 10 с", True, ""),
                                    ("Сразу заменить пульт", False,
                                     "Замена — последний, 4-й пункт таблицы, и её делает дилер."),
                                    ("Поставить на зарядку", False,
                                     "Заряд полный. Код 10 — про связь, а не про заряд."),
                                ])),
                    # source: WHILL_ERR p1 (код 10, п.1); WHILL_UM p85 (printed 84): снятие батареи;
                    # source: WHILL_UM p65 (printed 64): вставить до щелчка, включить через 5 с
                    S("Убедись, что питание выключено: экран погас.", "eyes", "controller",
                      "Батарею вынимают только на выключенной коляске."),
                    S("Нажми кнопку фиксатора и вынь батарею.", "hands", "battery",
                      "Батарея весит 2,7 кг — не урони."),
                    S("Через 10 с вставь батарею обратно до щелчка.", "hands", "battery",
                      "10 секунд без батареи — электроника полностью перезапустится."),
                    S("Через 5 с включи коляску, не касаясь джойстика.", "hands", "controller",
                      "Смотри на дисплей: уйдёт ли код."),
                    # source: WHILL_UM p84 (printed 83): разборка на ровном полу, батарея вынута, тормоза заперты
                    S("Посмотри на дисплей: код 10 вернулся, коляска снова погасла.", "eyes", "controller",
                      "Значит, дело в разъёме сиденья. Дальше разборка — только на выключенной коляске."),
                    S("Снова вынь батарею.", "hands", "battery",
                      "Сиденье снимают только без батареи."),
                    S("Посмотри: пол ровный, рычаги свободного хода подняты.", "eyes", "freewheel",
                      "Разборку делают на ровном полу, без батареи и с запертыми тормозами."),
                    # source: WHILL_UM p86-87 (printed 85-86): seat release lever, lift straight up, cushion up
                    S("Потяни рычаг фиксатора сиденья.", "hands", "seat",
                      "Рычаг откинут — сиденье больше не заперто на стойке."),
                    S("Подними сиденье за подлокотники строго вверх и положи подушкой вверх.",
                      "hands", "seat",
                      "Клади сиденье подушкой вверх: на пульт нельзя давить.",
                      "Барти: «Переверни сиденье вверх ногами — так удобнее!» — нет: так ломают пульт.",
                      ghost_wrong=True),
                    # source: WHILL_UM p86 (printed 85): магнитные разъёмы — кардиостимулятор не ближе 20 см
                    # source: WHILL_UM p106 (printed 105): foreign substances in connectors -> remove
                    S("Осмотри контакты разъёма между сиденьем и базой.", "eyes", "seat_cable",
                      "На контактах — песок и пыль. Разъём магнитный: кардиостимулятор — не ближе 20 см."),
                    S("Вымети песок с контактов разъёма щёткой.", "brush", "seat_cable",
                      "Контакты не трогай пальцами и металлом."),
                    # source: WHILL_ERR p1 (код 10, п.3: clean the contact surface); WHILL_UM p65: не мочить
                    S("Протри контактную поверхность разъёма сухой салфеткой.", "cloth", "seat_cable",
                      "Разъёмы нельзя мочить — только сухая чистка."),
                    # source: WHILL_UM p63-64 (printed 62-63): посадить по смотровому окну, рычаг перпендикулярно
                    S("Поставь сиденье прямо на стойку, сверяясь через смотровое окно.", "hands", "seat",
                      "Сиденье должно сесть ровно, без перекоса."),
                    S("Опусти рычаг фиксатора сиденья.", "hands", "seat",
                      "Рычаг должен встать поперёк сиденья — значит, заперто."),
                    S("Вставь батарею до щелчка.", "hands", "battery", ""),
                    S("Через 5 с включи коляску, не касаясь джойстика.", "hands", "controller",
                      "Кода нет — связь восстановлена. Если бы код остался, по таблице дальше меняют пульт или кабели — это работа дилера."),
                ],
                test="Дисплей чистый, без кода. Сайра проезжает восьмёрку между верстаками — связь держится.",
                fact="Код 10 — сбой связи через разъём между сиденьем и базой. Таблица WHILL: вынуть батарею "
                     "на 10 секунд; переустановить сиденье; почистить контакты. Если не помогло, дилер меняет "
                     "пульт, кабели или контроллер. Разъём магнитный — кардиостимулятор держат не ближе 20 см.",
                thanks="Сайра: «Десять — моё нелюбимое число. Было. Спасибо!»",
            ),
        ],
    ),

    # === Permobil F5 Corpus: не заряжается после зимы в холодном сарае ===
    dict(
        id="f5_charge", kind="power", client="Барсучиха-пасечница Матильда",
        client_art="client_f5.png", chair_art="chair_f5.png",
        chair_model="f5", chair_name="Permobil F5 Corpus (передний привод, 2×12 В SLA)",
        title="Не заряжается после зимы",
        symptom="Всю зиму коляска Матильды простояла в холодном садовом сарае. Весной Матильда подключила "
                "зарядку — и ничего: пульт тёмный, заряд не идёт. «Я всё делала по инструкции!»",
        parts=["breaker", "battery", "controller", "freewheel", "tire", "motor", "frame"],
        inspect={
            # source: F5_UM p40: длительное хранение — зарядить, выключить главный автомат
            "breaker": "Рычаг главного автомата сзади — в положении OFF. Матильда выключила его на зиму, "
                       "как написано в мануале.",
            "battery": "Батареи осенью зарядили полностью. Сейчас не горит ни одно деление: цепь отсечена.",
            "controller": "Пульт тёмный. Гнездо зарядки спереди джойстика чистое и сухое.",
            "freewheel": "Рычаги свободного хода — в положении «езда».",
            "tire": "Шины ведущих колёс заметно мягкие: после морозов давление упало.",
            "motor": "Моторы холодные, но целые.",
            "frame": "На раме иней. Термометр на стене сарая показывает около +1 °C.",
        },
        diagnosis=[
            D("Выключен главный автомат, а в сарае ниже +5 °C",
              True),
            D("Батареи умерли за зиму — сразу менять пару", False,
              "Осенью их зарядили полностью, а цепь сейчас отсечена автоматом. Сначала включи его."),
            D("Сгорел зарядный автомат — вскрывать электронику", False,
              "Зарядный автомат сам взводится через 5 минут. А в электронику лезет только техник."),
        ],
        steps=[
            # source: F5_UM p39: Always turn off the control panel before you turn off the main circuit breaker
            S("Кнопкой питания переведи пульт в «выключено»: когда вернут автомат, коляска не должна ожить сама. Тёмный "
              "экран не в счёт — питание сейчас просто отсекает автомат.",
              "hands", "controller",
              "С главным автоматом работают только при выключенном пульте."),
            # source: F5_UM p39: storage room dry and at least 5 °C, otherwise batteries might not charge fully
            S("Коляска зимовала в сарае: посмотри на батареи и сверь температуру в сарае с мануалом.", "eyes", "battery",
              "Холод и сырость не дают батареям зарядиться полностью и разъедают контакты.",
              mini=dict(kind="meter", reading="Термометр в сарае: +1 °C",
                        sub="мануал F5: хранить в сухом помещении не холоднее +5 °C",
                        prompt="Можно заряжать прямо здесь?",
                        options=[
                            ("Нет: ниже +5 °C батареи могут не зарядиться полностью — везём в тепло", True, ""),
                            ("Да, мороза же нет", False,
                             "Мануалу нужно не меньше +5 °C. При +1 °C батареи могут не набрать полный заряд."),
                            ("Да, если зарядка будет дольше", False,
                             "Время не поможет: в холоде батареи заряжаются не полностью."),
                        ]), alt=("frame",)),
            # source: F5_UM p34: freewheel — level ground, turn off, levers down; p20: attendant present
            S("На ровном полу, с помощником, включи свободный ход: у F5 — оба рычага вниз (коляска выключена).",
              "hands", "freewheel",
              "В свободном ходе тормоза отключены — только на ровном и с тем, кто держит коляску. У других "
              "колясок рычаг бывает один, вверх или поворотный — смотри мануал своей модели."),
            S("Откати коляску в сухую тёплую мастерскую, держась сбоку.", "hands", "frame",
              "Коляска весит 189 кг: катим медленно и вдвоём.",
              # source: F5_UM p6: Wheelchair with batteries 189 kg
              "Барти: «Да заряжай прямо в сарае, розетка же есть!» — нет: ниже +5 °C батареи "
              "не возьмут полный заряд.", ghost_wrong=True),
            # source: F5_UM p34: Exiting freewheel mode — turn off, levers upward
            S("Выключи свободный ход: рычаги вверх, коляска выключена.", "hands", "freewheel",
              "В свободном ходе F5 ехать не может — и тормоза не держат."),
            # source: F5_UM p39-40, p66: Turn on the main circuit breaker; reset once only
            S("Включи главный автомат рычагом сзади коляски.", "hands", "breaker",
              "На зимнее хранение его выключают, но для зарядки нужно включить. Если выбьет повторно — к сервису."),
            # source: F5_UM p33: connect charger to the wheelchair first, then to the wall; socket at joystick
            # source: F5_UM p66: charging circuit breaker resets automatically after 5 minutes
            S("Подключи зарядку сначала к гнезду спереди джойстика, потом к розетке.", "charger", "controller",
              "Только штатная зарядка Permobil. Если заряд не пошёл, подожди 5 минут: зарядный автомат "
              "взводится сам.",
              "Барти: «Сначала в розетку, потом в коляску — какая разница?» Разница есть: мануал велит "
              "наоборот."),
            # source: F5_UM p64: drive tyres 250 kPa (в мануале «35 psi» — округлено; 250 кПа = 36 psi), check weekly and after temperature change
            # source: F5_UM p21: overfilled tires can explode
            S("Пока идёт зарядка, накачай шины ведущих колёс через ниппель до 250 кПа.", "pump", "tire",
              "Давление проверяют раз в неделю и после резкой смены температуры. Перекачанная шина может лопнуть.",
              mini=dict(kind="pump", lo=240, hi=260, mx=320, unit="кПа",
                        hint="Мануал F5: ведущие шины — 250 кПа (36 psi)")),
            # source: F5_UM p33: not possible to drive while charging; p67: charger connected -> disconnect
            S("Заряд полный — отключи зарядку: пока она подключена, F5 не поедет.", "charger", "battery",
              "Когда коляска снова уйдёт на хранение — зарядить полностью и выключить автомат; раз в месяц включать "
              "и подзаряжать.",
              alt=("controller",)),
        ],
        test="Индикатор заряда на пульте полный, шины упругие. Матильда делает круг по мастерской и "
             "тормозит точно у банки мёда.",
        # source: F5_UM p39-40, p64, p66, p70
        fact="Перед долгим хранением F5 заряжают полностью и выключают главный автомат. Раз в месяц автомат "
             "включают, заряжают батареи и выключают снова. Хранить и заряжать — в сухом месте не ниже +5 °C. "
             "Зарядку подключают сначала к коляске, потом к розетке. Шины ведущих колёс — 250 кПа (36 psi).",
        thanks="Матильда: «Значит, автомат выключать правильно, только потом его надо включить! "
               "Держи мёд, мастер, и не спорь.»",
    ),
]


# ----------------------------------------------------------------------------- #
#  Про-трек: Гильдия Колёсников (уровень техника)
#  Отличия от базовых заданий: порядок шагов игрок выстраивает САМ (поле after —
#  зависимости), числа берутся из MANUAL (поле spec), а нарушение шага техники
#  безопасности (safety=True у пропущенного предшественника) проваливает задание.
# ----------------------------------------------------------------------------- #
# ----------------------------------------------------------------------------- #
#  Третья волна: фольклорные клиенты (Баба Яга, русалка Ольга, Леший, мумия Сенеб, Змей Горыныч).
#  Задания попадают в игру, только когда на месте их картинки и 3D-модели (assets/client_*, chair_*,
#  models/chair_*_ai.json): см. _folk_ready ниже и art_tests/new_chars_refs/README.md.
# ----------------------------------------------------------------------------- #
FOLK_JOBS = [
    # === Баба Яга, Vermeiren D100: подняла сиденье — тормоза не держат, касторы «пляшут» ===
    # source: vermeiren-karma/vermeiren_d100_en.pdf
    #   p8   — тормоза: не для торможения на ходу; зависят от состояния шин; проверять перед каждой поездкой
    #   p12  — снять колесо: тормоза отпущены, кнопка в центре ступицы
    #   p16  — высота сиденья 470/500/530 мм перестановкой колёс: зад — отверстия 1+2 / 2+3 / 3+4, перед — A/B/C;
    #          ВЕРХНЕЕ отверстие пластины — для барабанного тормоза, не для оси; вилка ⟂ полу; потом тормоза по §3.4
    #   p17  — §3.4 регулировка тормоза: отпустить, ослабить болты, сдвинуть по направляющей, затянуть, проверить
    dict(
        id="yaga_d100", kind="manual", client="Баба Яга", client_art="client_yaga.png",
        chair_art="chair_yaga.png",
        chair_model="d100", chair_name="Vermeiren D100 (складная стальная)",
        title="Подняла сиденье — тормоза не держат",
        symptom="Яга подняла сиденье, «чтоб из окна избушки дальше видать». Теперь на горке коляска сама "
                "катится, хоть тормоз зажат, а передние колёсики на ходу виляют.",
        parts=["brake", "axle", "caster_stem", "caster", "rear_wheel", "tire"],
        inspect={
            "brake": "Рычаг зажат до щелчка, но колодка тормоза едва касается шины: колесо теперь стоит выше.",
            "axle": "Пластина оси переставлена в отверстия 3 и 4 — это положение для сиденья 530 мм.",
            "caster_stem": "Вилки передних колёс остались в отверстии A и стоят наклонно, а не отвесно к полу.",
            "caster": "Колёсики целые, но из-за наклонной вилки на ходу виляют.",
            "rear_wheel": "Кнопка быстросъёмной оси защёлкнута, колесо держится крепко.",
            "tire": "Шины литые полиуретановые: качать не нужно. Протектор чистый, без масла и грязи.",
        },
        diagnosis=[
            D("Колёса подняты, а вилки и тормоза — нет", True),
            D("Износились колодки — менять тормоза", False,
              "Тормоза целые, просто не достают до шины: колесо переставили выше, а тормоз оставили на месте."),
            D("Разболталась крестовина под сиденьем", False,
              "Крестовина держит раму плотно. Виляют колёсики из-за наклонной вилки."),
        ],
        steps=[
            # source: p12
            S("Отпусти тормоз и сними заднее колесо: нажми кнопку в центре ступицы.", "hands", "rear_wheel",
              "Колесо снимают только с отпущенным тормозом.", alt=("axle",)),
            # source: p16, таблица 2 и предупреждение про верхнее отверстие
            S("Посмотри, в каких отверстиях стоят задняя ось и передние вилки, и сверь с таблицей высоты сиденья.",
              "eyes", "axle",
              "У D100 высота меняется перестановкой колёс: у каждой высоты своё отверстие и сзади, и спереди.",
              mini=dict(kind="meter", reading="Задняя ось — в отверстиях 3 и 4 · передние вилки — в отверстии A",
                        sub="Таблица D100: 470 мм — ось 1+2, вилки A · 500 мм — 2+3, B · 530 мм — 3+4, C",
                        prompt="Что не так?",
                        options=[
                            ("Для 530 мм вилки должны стоять в отверстии C", True, ""),
                            ("Ось надо поднять в самое верхнее отверстие", False,
                             "Верхнее отверстие пластины — для барабанного тормоза, ось туда не ставят."),
                            ("Всё по таблице, дело только в тормозах", False,
                             "Сзади 530 мм, а спереди вилки остались на 470 мм. Так вилки стоят наклонно."),
                        ]), alt=("caster_stem",)),
            # source: p16, шаг 4
            S("Проверь, что втулки оси крепко затянуты.", "socket", "axle",
              "Мануал D100 требует проверить втулки после перестановки пластины."),
            # source: p16, шаги 5–7
            S("Выкрути болт вилки и переставь переднее колесо в отверстие C, затяни.", "socket", "caster_stem",
              "Колесо должно крутиться легко, но без люфта.",
              "Барти: «Да оставь как есть, виляет — значит, весело!»", ghost_wrong=True,
              wrongmsg="Вилку переставляют торцевым ключом: выкрутить болт, переставить, затянуть.", alt=("caster",),
              alt_tools=("allen",)),
            # source: p16, шаг 9
            S("Посмотри сбоку: вилка должна стоять отвесно к полу.", "eyes", "caster_stem",
              "Наклонная вилка — и колёсики на ходу виляют."),
            # source: p7 §2.2, p16 шаг 8
            S("Поставь заднее колесо: кнопку держи нажатой, вставь ось до упора, отпусти и подёргай колесо.",
              "hands", "rear_wheel", "Колесо не должно сниматься без кнопки.", alt=("axle",)),
            # source: p17 §3.4, шаги 2–5
            S("Отведи рычаг тормоза назад и ослабь болты тормоза.", "allen", "brake",
              "Болты ослабляют, чтобы тормоз можно было сдвинуть по направляющей."),
            S("Сдвинь тормоз по направляющей к колесу.", "hands", "brake",
              "Колесо теперь выше — тормоз должен догнать шину."),
            S("Затяни болты тормоза.", "allen", "brake",
              "Тормоз на новом месте — болты затягивают, чтобы он не уехал."),
            # source: p17 §3.4 шаги 6–7, p8
            S("Зажми тормоза и сильно толкни коляску: колёса не должны прокручиваться.", "hands", "tire",
              "Если колесо проворачивается — повтори регулировку.",
              "Барти: «А можно ими тормозить на спуске?» Нельзя: это стояночные тормоза, не для движения.",
              ghost_wrong=True, wrongmsg="Проверка простая: зажми тормоз и толкни коляску.", alt=("brake", "rear_wheel")),
        ],
        test="Яга ставит коляску на тормоз на крыльце избушки и подпрыгивает на сиденье: ни с места. "
             "Отпускает — и колёсики катят прямо, не виляя.",
        fact="У D100 три высоты сиденья: 470, 500 и 530 мм. Высоту меняют перестановкой колёс, и сзади, и спереди: "
             "вилки должны встать отвесно к полу. После этого тормоза регулируют заново. Верхнее отверстие "
             "пластины — для барабанного тормоза, не для оси.",
        thanks="Баба Яга: «Ну, касатик, удружил! Ступу в музей сдам, на коляске теперь летаю.»",
    ),

    # === Русалка Ольга, Panthera X3: после моря хрустит кастор, туго ходит ось, тормоз слабый ===
    # source: euro-ultralight/panthera_x3_user_manual_en_2024.pdf
    #   p7   — тормоз стояночный; работает только при правильном давлении в шинах
    #   p15  — тормоз: ключ 12 мм, сдвинуть по рейке, в зажатом положении вдавлен в шину ≈4 мм, одинаково с двух сторон
    #   p20  — песок и солёная вода: чистить чаще; вилка кастора — волосы и пыль портят подшипники;
    #          быстросъёмную ось смазывать каплями масла, в дождь, песок, соль — чаще
    #   p21  — кастор: два шестигранника 4 мм, почистить проставки, протереть подшипники, по капле масла;
    #          на резьбе должен оставаться фиксатор (синий/красный/зелёный), иначе — новый болт или лёгкий фиксатор
    #   p23  — давление в шинах 8 бар (800 кПа)
    dict(
        id="olga_x3", kind="manual", client="Русалка Ольга", client_art="client_rusalka.png",
        chair_art="chair_rusalka.png",
        chair_model="x3", chair_name="Panthera X3 (ультралёгкая, карбон)",
        title="После моря хрустит и туго ходит",
        symptom="Ольга весь день гоняла по пирсу и пляжу. Теперь переднее колёсико хрустит, заднее колесо не "
                "снимается — кнопка оси залипла, а тормоз на мокрых досках не держит.",
        parts=["caster", "caster_stem", "axle", "tire", "brake"],
        inspect={
            "caster": "Колёсико крутится туго и с хрустом: между колесом и вилкой песок и волосы, "
                      "подшипники снаружи в соли.",
            "caster_stem": "Вилка цела, но на проставках налипла солёная корка.",
            "axle": "Кнопка быстросъёмной оси нажимается туго: внутри песок и соль, смазки не осталось.",
            "tire": "Шины мягкие: давление заметно ниже нормы.",
            "brake": "Зажатый тормоз едва давит на мягкую шину, колесо проворачивается.",
        },
        diagnosis=[
            D("Песок и соль в касторе и в оси, шины мягкие", True),
            D("Разбит подшипник — менять кастор целиком", False,
              "Подшипник цел, он просто забит песком и солью. Его чистят и смазывают."),
            D("Треснула карбоновая рама после волны", False,
              "Рама целая. Хрустит кастор, а туго ходит быстросъёмная ось."),
        ],
        steps=[
            # source: p21 (Replacing castors, шаг 2)
            S("Двумя шестигранниками 4 мм открути болт оси переднего колёсика (кастора) и вынь его.", "allen", "caster",
              "Держи болт с двух сторон: одним ключом держишь, другим крутишь."),
            S("Вычисти песок и волосы с проставок между колесом и вилкой.", "brush", "caster_stem",
              "Panthera: волосы и пыль в вилке портят подшипники кастора.",
              "Барти: «Песок — это же почти смазка, только твёрдая!»", ghost_wrong=True,
              wrongmsg="Песок вычищают щёткой или пинцетом.", alt=("caster",)),
            S("Протри подшипники колёсика снаружи тряпкой.", "cloth", "caster", "Сначала убрать соль, потом смазывать."),
            S("Капни по одной капле масла в каждый подшипник колёсика.", "lube", "caster",
              "Мануал советует универсальное масло вроде CRC 5-56."),
            # source: p21 (thread locker)
            S("Посмотри на резьбу болта перед сборкой.", "eyes", "caster",
              "На резьбе должен оставаться клей-фиксатор резьбы — синий, красный или зелёный.",
              mini=dict(kind="meter", reading="Резьба чистая, фиксатора не видно",
                        sub="Panthera: клея на резьбе нет — новый болт или капля мягкого клея-фиксатора",
                        prompt="Что делать с болтом?",
                        options=[
                            ("Нанести лёгкий фиксатор резьбы или взять новый болт", True, ""),
                            ("Затянуть посильнее, и так удержится", False,
                             "Без фиксатора болт кастора может открутиться на ходу."),
                            ("Смазать резьбу маслом", False,
                             "Масло на резьбе — наоборот, болт открутится ещё быстрее."),
                        ])),
            S("Поставь колёсико на место и затяни шестигранником 4 мм: оно должно крутиться легко.", "allen", "caster",
              "Затянул — прокрути: никакого хруста и заеданий."),
            # source: p20 (lubricate quick release)
            S("Нажми кнопку оси и сними заднее колесо, стягивая его прямо.", "hands", "axle",
              "Кнопка залипает — значит, ось просит смазки."),
            S("Капни несколько капель масла на быстросъёмный механизм во втулке оси.", "lube", "axle",
              "После песка, дождя и солёной воды ось смазывают чаще, чем раз в месяц."),
            # source: p21 (refit wheel)
            S("Надень колесо до щелчка: кнопка должна выскочить, потяни колесо на себя.", "hands", "axle",
              "Колесо не должно сниматься без нажатия кнопки."),
            # source: p23, p7
            S("Накачай шины до нормы из мануала.", "pump", "tire",
              "Тормоз держит только на накачанной шине.",
              mini=dict(kind="pump", lo=110, hi=120, mx=145, unit="psi",
                        hint="Panthera X3: шины — 8 бар (800 кПа) ≈ 116 psi")),
            # source: p15
            S("Ослабь крепление тормоза ключом 12 мм и выставь его по рейке.", "wrench", "brake",
              "В зажатом положении упор должен вдавливаться в шину примерно на 4 мм.",
              mini=dict(kind="gap", lo=3.5, hi=4.5, mn=0, mx=10, unit="мм", start=1,
                        label="Насколько упор вдавлен в шину",
                        hint="Panthera X3: примерно 4 мм, одинаково с двух сторон",
                        fb_lo="Меньше: на мокром пирсе коляска снова поедет.",
                        fb_hi="Глубже: рычаг закрывается с трудом и рвёт шину."), alt_tools=("socket",)),
            S("Затяни крепление тормоза ключом 12 мм и проверь второй тормоз так же.", "wrench", "brake",
              "Оба тормоза должны стоять одинаково.", alt_tools=("socket",)),
        ],
        test="Ольга въезжает на мокрый пирс, зажимает тормоза и машет хвостом: стоит. Колёсико крутится "
             "бесшумно, а заднее колесо снимается одной кнопкой.",
        fact="Panthera: песок и солёная вода требуют чистки чаще обычного. Вилку кастора чистят от волос и песка, "
             "в подшипники — по капле масла, быстросъёмную ось смазывают после песка, соли и дождя. Шины — 8 бар: "
             "тормоз держит только на накачанной шине.",
        thanks="Ольга: «Спасибо! Теперь я и в море, и на берегу — королева волн.»",
    ),

    # === Леший, Magic Mobility Extreme X8: застрял в болоте, мотор перегрелся, тянет вбок ===
    # source: magic-mobility/magic_mobility_powerchair_owner_s_manual_en.pdf
    #   p14  — разное давление в шинах тянет коляску в сторону
    #   p16  — §3.18: застрял и жмёт джойстик дольше нескольких секунд — моторы перегреваются, повреждение
    #   p17  — §3.22: не въезжать в воду, реки и болота; намокла — вытереть
    #   p36, p38 — §7.1, §7.6: шины X8 для бездорожья: давление по весу (до 8 psi на бездорожье),
    #          максимум 24 psi, гайки колёс 47–50 Н·м; проверять раз в неделю
    #   p40  — §7.16 ежедневно: заряд, джойстик; §7.17 еженедельно: тест электротормозов, давление, износ, мусор у моторов
    dict(
        id="leshy_x8", kind="power", client="Леший", client_art="client_leshy.png",
        chair_art="chair_leshy.png",
        chair_model="x8", chair_name="Magic Mobility Extreme X8 (полный привод, бездорожье)",
        title="Застрял в болоте — тянет вбок",
        symptom="Леший застрял в трясине и долго жал джойстик. Коляска встала, а когда остыла, поехала — "
                "но тянет влево, и из колёс торчит трава.",
        parts=["motor", "tire", "axle", "rim", "freewheel", "controller"],
        inspect={
            "motor": "Левый передний мотор ещё тёплый. Вокруг него намотаны трава и тонкие ветки.",
            "tire": "Левые шины мягкие, правые — в норме для бездорожья: давление разное.",
            "axle": "На осях намотан длинный стебель осоки.",
            "rim": "Гайки левого переднего колеса затянуты слабее, чем остальные.",
            "freewheel": "Рычаги свободного хода — в положении «езда».",
            "controller": "Пульт цел: джойстик возвращается в центр, пыльник целый.",
        },
        diagnosis=[
            D("Мотор перегрелся в трясине, шины неровные", True),
            D("Сломался джойстик — поэтому тянет влево", False,
              "Джойстик исправен. Тянет из-за разного давления в шинах."),
            D("Батареи сели — ставить новые сразу", False,
              "Коляска остановилась от перегрева мотора, а не от батарей."),
        ],
        steps=[
            # source: p16 §3.18
            S("Выключи коляску кнопкой на пульте и дай мотору остыть: не жми джойстик, если колёса не едут.", "hands",
              "controller",
              "Буксовать дольше нескольких секунд нельзя: мотор перегревается и портится.",
              "Барти: «Жми сильнее, вдруг выедет!»", ghost_wrong=True,
              wrongmsg="Сначала выключить коляску и дать мотору остыть."),
            S("Пощупай мотор: если горячий — ждём, пока остынет.", "hands", "motor",
              "Защита от перегрева бережёт мотор и контроллер."),
            # source: p40
            S("Вытащи траву и ветки вокруг моторов и осей.", "brush", "axle",
              "Раз в неделю мануал велит проверять, не забилось ли что-то у моторов и осей.", alt=("motor",)),
            # source: p14, p36
            S("Проверь манометром давление во всех четырёх шинах.", "gauge", "tire",
              "Разное давление тянет коляску в сторону."),
            # source: p38 §7.6 (по весу пользователя; максимум 24 psi)
            S("Подкачай левые шины до нормы для бездорожья — как у правых.", "pump", "tire",
              "На бездорожье давление ниже — лучше сцепление. Но все четыре шины — одинаково.",
              mini=dict(kind="pump", lo=45, hi=58, mx=165, unit="кПа",
                        hint="X8, бездорожье, вес Лешего ~150 кг: около 50 кПа (7–8 psi); максимум шины — 165 кПа")),
            # source: p38 §7.6 (47–50 Нм)
            S("Проверь затяжку гаек в центре колёс торцевым ключом с динамометром.", "socket", "rim",
              "Гайки колёс затягивают с усилием по мануалу.",
              mini=dict(kind="meter", reading="Динамометрический ключ: 30 Н·м",
                        sub="Magic Mobility, колёса X8: 47–50 Н·м",
                        prompt="Что делать с гайками?",
                        options=[
                            ("Дотянуть до 47–50 Н·м", True, ""),
                            ("Затянуть изо всех сил", False, "Перетянутые гайки срывают резьбу. Нужно 47–50 Н·м."),
                            ("Оставить: 30 Н·м хватит", False, "Мало: колесо может разболтаться на кочках."),
                        ]), alt=("axle", "tire")),
            S("Проверь, что рычаги свободного хода стоят в положении «езда».", "hands", "freewheel",
              "В свободном ходе тормозов нет.", alt_tools=("eyes",)),
            # source: p40 (ежедневная проверка тормозов)
            S("Включи коляску кнопкой на пульте и легонько толкни джойстик: должны щёлкнуть все электротормоза.", "hands",
              "controller",
              "Еженедельная проверка из мануала (§7.17): на ровном полу, вокруг метр свободного места."),
        ],
        test="Леший выезжает на лесную тропу и катит прямо, не уводя в сторону. Моторы гудят ровно.",
        fact="Magic Mobility: если коляска застряла, джойстик не жмут дольше нескольких секунд — мотор перегреется. "
             "Разное давление в шинах тянет коляску вбок. На бездорожье давление ниже, но одинаковое во всех шинах. "
             "В воду и болото электроколяска не въезжает.",
        thanks="Леший: «Ох, спасибо, мастер! Теперь по лесу хожу... то есть езжу, только не в болото.»",
    ),

    # === Мумия Сенеб (была Ра), Quickie Nitrum + колёса Alber e-motion M25: зарядка обрывается на солнцепёке ===
    # source: power-assist/alber_e-motion_m25_user_manual_en.pdf (англ. часть с p41)
    #   p49  — у e-motion нет своих тормозов: обязательно стояночные тормоза коляски
    #   p53  — при перегреве/возгорании батареи — НЕ вода: песок или огнетушитель класса D
    #   p55  — не держать колёса у источников тепла; гнездо зарядки чистить сухой тряпкой, без металла
    #   p56  — заряжать только при 0…40 °C, иначе зарядка прерывается; до 6 ч; перед зарядкой выключить оба колеса;
    #          на коляске — зажать стояночные тормоза
    #   p57  — штекер в гнездо на кнопке ступицы, магнитный; во время зарядки не нажимать на обручи
    #   p61  — 5.5: все LED мигают белым, 4 сигнала — температура зарядки вне 0…40 °C, зарядка прервана
    #   p66  — не оставлять колёса под постоянным солнцем
    dict(
        id="ra_emotion", kind="manual", client="Мумия Сенеб", client_art="client_mummy.png",
        chair_art="chair_ra.png",
        chair_model="nitrum_em", chair_name="Quickie Nitrum + колёса с мотором Alber e-motion",
        title="Зарядка обрывается на солнце",
        symptom="Мумия Сенеб ставит колёса с моторами на зарядку прямо под полуденным солнцем у пирамиды. "
                "Через минуту огоньки мигают белым, колесо пищит четыре раза — и зарядка обрывается.",
        parts=["motor", "brake", "rear_wheel", "tire", "axle", "caster"],
        inspect={
            "motor": "Ступица колеса горячая. Все пять огоньков мигают белым, колесо пищит четыре раза. "
                     "В магнитном гнезде зарядки — песок и металлическая пыль.",
            "brake": "Стояночные тормоза отпущены, хотя коляска стоит на зарядке.",
            "rear_wheel": "Колёса с моторами сидят в креплениях ровно, без люфта.",
            "tire": "Давление в обоих колёсах одинаковое.",
            "axle": "Оси защёлкнуты.",
            "caster": "Передние колёсики крутятся свободно.",
        },
        diagnosis=[
            D("Зарядка прервалась от жары выше +40 °C", True),
            D("Сгорела батарея в ступице — вскрыть её", False,
              "Батарею в колесе вскрывать нельзя. По таблице ошибок это температура, а не поломка."),
            D("Зарядка неисправна — взять чужую", False,
              "Можно только родную зарядку Alber. А сигнал говорит о жаре, не о зарядке."),
        ],
        steps=[
            # source: p61
            S("Сверь огоньки и сигналы ступицы (мотор e-motion) с таблицей ошибок в мануале Alber.", "eyes", "motor",
              "У e-motion каждая ошибка — своё сочетание огоньков и сигналов.",
              mini=dict(kind="meter", reading="Все 5 огоньков мигают белым · 4 сигнала",
                        sub="Alber, таблица ошибок: мигает белым, 4 сигнала",
                        prompt="Какая строка таблицы подходит?",
                        options=[
                            ("Жарче +40 °C или холоднее 0 °C — зарядка прервана", True, ""),
                            ("Батарея почти пустая", False, "Это другое сочетание: горит только один крайний огонёк."),
                            ("Колесо двигали во время зарядки", False,
                             "Это горит красным с пятью сигналами. Тут мигает белым."),
                        ]), alt=("rear_wheel",)),
            # source: p56, p57
            S("Отключи штекер зарядки от колеса, потом вилку из розетки.", "hands", "motor",
              "Сначала колесо, потом розетка.", alt=("rear_wheel",), alt_tools=("charger",)),
            S("Выключи оба колеса кнопкой на ступице.", "hands", "motor",
              "Перед зарядкой оба колеса должны быть выключены.", alt=("rear_wheel",)),
            # source: p55, p56, p66
            S("Откати коляску в тень, в прохладное место: толкай её, взявшись за колёса.", "hands", "rear_wheel",
              "Заряжают только при 0…40 °C и не держат колёса на солнце или у источников тепла.",
              "Барти: «Да укутай колёса бинтами Сенеба — вот тебе и тень!»", ghost_wrong=True,
              wrongmsg="Коляску откатывают в тень руками.", alt=("tire", "frame")),
            # source: p56, p49
            S("Зажми стояночные тормоза коляски.", "hands", "brake",
              "У колёс e-motion нет своих тормозов. Заряжаем на коляске — тормоза зажаты."),
            # source: p55, p57
            S("Протри магнитное гнездо зарядки сухой тряпкой.", "cloth", "motor",
              "Магнит тянет металлическую пыль, а она мешает контакту. Только сухая тряпка.", alt=("rear_wheel",)),
            # source: p57
            S("Включи зарядку в розетку, потом вставь штекер в гнездо на кнопке ступицы: он сам защёлкнется магнитом.",
              "charger", "motor",
              "Пока идёт зарядка, на обручи не давят — зарядка может остановиться.", alt=("rear_wheel",)),
            S("Проверь: огоньки зарядки мигают зелёным, колесо коротко пискнуло.", "eyes", "motor",
              "Зарядка идёт. Полная — до 6 часов, перезарядить нельзя: она остановится сама.", alt=("rear_wheel",)),
        ],
        test="В тени колонн огоньки заряда бегут зелёным. Наутро Сенеб объезжает пирамиду — колёса легко помогают толкать.",
        fact="Колёса Alber e-motion заряжают только при 0…40 °C, иначе зарядка прерывается сама: все огоньки мигают "
             "белым, 4 сигнала. Своих тормозов у колёс нет — нужны стояночные тормоза коляски. Если батарея "
             "загорелась — не вода, а песок или огнетушитель класса D.",
        thanks="Сенеб: «Три тысячи лет в пирамиде — и только теперь узнал, что технике нужна тень. Спасибо, мастер!»",
    ),

    # === Змей Горыныч, Pride Jazzy 614: в горку выбивает главный автомат ===
    # source: pride/us_jazzy_614_series_om.pdf
    #   p10  — предел веса включает пользователя и всё, что на коляске; пассажиров не возить;
    #          давление в шинах — по цифре на боковине
    #   p19  — главный автомат выбивает при сильной нагрузке (перегрузке); дать отдохнуть ~1 мин, нажать кнопку,
    #          включить пульт; выбивает снова и снова — к сервисному центру Pride
    #   p37  — нет питания: проверить разъёмы жгутов, автомат, клеммы батарей
    #   p38  — Jazzy 614: до 136 кг (300 lb); 614HD: до 204 кг
    dict(
        id="gorynych_jazzy", kind="power", client="Змей Горыныч", client_art="client_gorynych.png",
        chair_art="chair_gorynych.png",
        chair_model="jazzy614", chair_name="Pride Jazzy 614 (среднеприводная)",
        title="В горку выбивает автомат",
        symptom="Горыныч едет в горку к замку — и коляска замирает. Через минуту снова едет, а на следующем "
                "подъёме опять встаёт. Три головы спорят, кто виноват.",
        parts=["breaker", "backrest", "frame", "tire", "battery", "controller", "joystick"],
        inspect={
            "breaker": "Кнопка главного автомата на передней стороне базы выскочила: защита сработала.",
            "backrest": "К спинке привязан тяжёлый сундук с золотом — килограммов сорок.",
            "frame": "На раме — табличка с серийным номером и пределом веса пользователя.",
            "tire": "Ведущие шины мягкие: давление ниже, чем напечатано на шине.",
            "battery": "Батареи заряжены полностью.",
            "controller": "Разъём пульта вставлен плотно, жгут не трётся о пол.",
            "joystick": "Джойстик исправен, возвращается в центр.",
        },
        diagnosis=[
            D("Перегруз: Горыныч с сундуком тяжелее 136 кг", True),
            D("Сгорел мотор — менять оба сразу", False,
              "Моторы целы. Автомат выбивает, чтобы их защитить от перегрузки."),
            D("Батареи сели — поставить новые", False,
              "Батареи заряжены. Коляска встаёт от перегрузки, а не от пустых батарей."),
        ],
        steps=[
            S("Выключи пульт.", "hands", "controller", "С автоматом работают при выключенном пульте."),
            # source: p10
            S("Отвяжи сундук от спинки: груз тоже входит в предел веса коляски.", "hands", "backrest",
              "Предел веса — это и седок, и всё, что висит на коляске.",
              "Барти: «Сундук оставь — посади на колени ещё и дракончика-племянника!»", ghost_wrong=True,
              wrongmsg="Сундук снимают руками. И пассажиров на коляске не возят."),
            # source: p38
            S("Найди предел веса на табличке коляски и сверь с весом Горыныча.", "eyes", "frame",
              "У каждой коляски свой предел веса — он на табличке с серийным номером и в таблице характеристик.",
              mini=dict(kind="meter", reading="Горыныч: 118 кг · сундук: 40 кг",
                        sub="Pride: Jazzy 614 — до 136 кг, Jazzy 614HD — до 204 кг",
                        prompt="Как ездить дальше?",
                        options=[
                            ("Без сундука: 118 кг вписываются в 136 кг", True, ""),
                            ("С сундуком: 158 кг, коляска справится", False,
                             "158 больше 136: автомат будет выбивать, а моторы — перегреваться."),
                            ("Срочно менять коляску на другую", False,
                             "Не нужно: без сундука Горыныч вписывается в предел Jazzy 614."),
                        ]), alt=("seat", "backrest", "controller", "battery")),
            # source: p10 (давление по цифре на боковине); число — GAME (по боковине шины в игре)
            S("Накачай ведущие шины до давления, напечатанного на шине.", "pump", "tire",
              "Мягкие шины нагружают моторы сильнее.",
              mini=dict(kind="pump", lo=228, hi=241, mx=310, unit="кПа",
                        hint="На боковине этой шины: 241 кПа (35 psi) — не больше")),
            # source: p37
            S("Дожми до щелчка разъёмы жгута батарей.", "hands", "battery",
              "Расшатанный разъём тоже может обрывать питание.", alt=("controller", "breaker")),
            # source: p19
            S("Подожди около минуты и нажми кнопку главного автомата.", "hands", "breaker",
              "Автомату нужно «отдохнуть» примерно минуту. Если будет выбивать снова и снова — к сервису Pride."),
            S("Включи пульт кнопкой питания и посмотри на индикатор батарей.", "hands", "controller",
              "Индикатор горит — питание вернулось.", alt=("joystick",), alt_tools=("eyes",)),
        ],
        test="Горыныч без сундука въезжает в горку к замку и не останавливается. Все три головы довольны.",
        fact="Главный автомат Jazzy 614 выбивает при перегрузке и защищает моторы и электронику. Подождать минуту, "
             "нажать кнопку, включить пульт; выбивает снова и снова — к сервису. Предел веса Jazzy 614 — 136 кг, "
             "и в него входит всё, что висит на коляске. Пассажиров не возят.",
        thanks="Го: «Ура, поехали!» Ры: «Ну, допустим, спасибо.» Ныч: «Разбудите у замка.»",
    ),
]

# 2D-хотспоты по нарисованной коляске (рамка 380x300; считаются из 3D-модели art_tests/folk_hotspots.py)
FOLK_HOTSPOTS_PATH = os.path.join(ASSETS_DIR, "models", "folk_hotspots.json")


def _folk_ready(job):
    """Задание включается, когда на месте его картинки (кладёт build_new_v2_assets.py --install).
    3D-модель необязательна: без неё в окне осмотра — рисунок коляски с кружками (folk_hotspots.json)."""
    return all(asset_exists(f) for f in (job["client_art"], job["chair_art"]))


_FOLK_ON = [j for j in FOLK_JOBS if _folk_ready(j)]
JOBS += _FOLK_ON
for _j in _FOLK_ON:
    _k = _j["chair_art"][len("chair_"):-len(".png")]
    if os.path.exists(os.path.join(ASSETS_DIR, "models", f"chair_{_k}_ai.json")):
        AI_MODELS[_j["chair_art"]] = f"chair_{_k}_ai.json"
try:
    with open(FOLK_HOTSPOTS_PATH, encoding="utf-8") as _f:
        for _model, _spots in json.load(_f).items():
            CHAIR_HOTSPOTS[_model] = {p: tuple(v) for p, v in _spots.items()}
except Exception:
    pass


TECH_JOBS = [
    # === Т1. Правка «восьмёрки»: свободный порядок + спека, без safety ===
    dict(
        id="truing", track="tech", kind="manual", client="Эльфийка Аэлин",
        client_art="client_elf.png", chair_art="chair_elf.png",
        title="Правка «восьмёрки» обода",
        symptom="Задание Гильдии: после турнира обод заднего колеса Аэлин гуляет из стороны "
                "в сторону. Выправь биение по регламенту: промеры — до правки, ниппели — понемногу.",
        manual=["truing"],
        tools=["hands", "dial", "tensiometer", "spoke_key", "wrench", "lube", "pump"],
        intro="Бренна: «Правка обода — работа тонкая. Сначала промеры, потом руки. Порядок выбирай сам.»",
        steps=[
            T("w_unmount", "Сними заднее колесо с коляски (кнопка быстросъёмной оси)", "hands", "rear_wheel",
              note="Нажал кнопку в торце оси — колесо снимается целиком, вместе с осью."),
            T("w_mount", "Установи колесо в правочный станок", "hands", "rear_wheel",
              after=["w_unmount"],
              note="Станок держит ось жёстко — биение видно точно.",
              ghost="Барти: «Станооок! У мастерицы такой был. Я думал, это арфа.»"),
            T("w_spin", "Прокрути колесо и найди зону увода обода индикатором", "dial", "rim",
              after=["w_mount"],
              note="Индикатор покажет, где и в какую сторону гуляет обод."),
            T("w_tension", "Промерь тензиометром натяжение спиц с обеих сторон в зоне увода", "tensiometer", "spokes",
              after=["w_mount"],
              note="Цифры — до правки, иначе не поймёшь, что изменил."),
            T("w_adjust", "Выправь увод: подтяни спицы противоположного фланца в зоне биения", "spoke_key", "spokes",
              after=["w_spin", "w_tension"],
              note="Обод тянется в сторону фланца, чьи спицы ты подтягиваешь.",
              spec=dict(manual="truing", prompt="На сколько крутить ниппели за один подход?",
                        options=[
                            ("Не более 1/4 оборота — и снова проверить биение", True, ""),
                            ("По 2 полных оборота — быстрее выправится", False,
                             "Перетянешь: обод уведёт в другую сторону, а спицы может порвать."),
                            ("Крутить до самого звонкого звука", False,
                             "«На звон» — грубая прикидка. Техник работает по тензиометру и мануалу."),
                        ])),
            T("w_recheck", "Снова прокрути колесо: биение должно уйти в допуск", "dial", "rim",
              after=["w_adjust"],
              note="Допуск — не более 1–2 мм. Не уложился — ещё подход по 1/4 оборота."),
            T("w_even", "Сверь тензиометром натяжение соседних спиц", "tensiometer", "spokes",
              after=["w_adjust"],
              note="Одна перетянутая спица — будущая «восьмёрка» или трещина обода."),
            T("w_unstand", "Сними колесо со станка", "hands", "rear_wheel",
              after=["w_recheck", "w_even"],
              note="Биение в допуске, натяжение ровное — колесо готово."),
            T("w_back", "Поставь колесо обратно на коляску (быстросъёмная ось)", "hands", "rear_wheel",
              after=["w_unstand"],
              ghost="Барти: «Щёлк! Люблю этот звук. Значит, ничего не отвалилось.»"),
        ],
        test="Колесо крутится в станке ровно, стрелка индикатора почти не дышит.",
        fact="Обод правят по индикатору малыми шагами: не более 1/4 оборота ниппеля за подход, обод идёт "
             "в сторону подтягиваемого фланца. Натяжение контролируют тензиометром, допуск биения — 1–2 мм.",
        thanks="Аэлин: «Идеально круглое колесо. В Гильдии из тебя сделают мастера, Мартин.»",
    ),

    # === Т2. Замена пары батарей: safety-шаги (питание, порядок клемм) ===
    dict(
        id="t_battery", track="tech", kind="power", client="Мастерица Бренна",
        client_art="master.png", chair_art="chair_edge4.png",
        chair_name="Quantum Edge 4 (батареи 22NF / группа 24)",
        title="Замена пары батарей",
        symptom="Экзаменационная коляска Гильдии: батареи четвёртый год не держат заряд. "
                "Замени ПАРУ по регламенту. Бренна смотрит. Внимательно.",
        manual=["battery_pair"],
        tools=["hands", "eyes", "screw", "wrench", "charger", "multimeter", "allen"],
        intro="Бренна: «Электрика прощает всё, кроме неуважения. Порядок клемм — как молитва: наизусть.»",
        steps=[
            # source: quantum/edge-4-om.pdf p25 — 1) питание контроллера выкл.; 2) коляска в режиме езды
            T("p_off", "Выключи питание на пульте", "hands", "controller",
              safety=True,
              note="Любая работа — только на обесточенной коляске.",
              failnote="На включённой коляске случайное касание джойстика — и она поедет. "
                       "Вместе с твоими пальцами в отсеке.",
              ghost="Бренна: «Первое правило электрики: сначала убей питание. Второе: проверь, что убил.»"),
            T("p_drive", "Посмотри, что рычаги свободного хода в режиме езды", "eyes", "freewheel",
              safety=True,
              note="Режим езды — тормоза моторов включены: коляска не укатится, пока ты в отсеке.",
              failnote="Рычаги остались в свободном ходе: тормоза моторов отключены, и коляска покатилась "
                       "с подставки, пока ты возился с клеммами."),
            # source: quantum/edge-4-om.pdf p25 — передний кожух: ручки-защёлки; задний: два жёлтых фиксатора;
            # дверца отсека — ручка. Инструмент не нужен (E4 p7: «The rear door can be removed without tools»)
            T("p_cover_f", "Сними передний кожух за ручки-защёлки", "hands", "frame",
              note="Инструмент не нужен: кожух на защёлках."),
            T("p_cover_r", "Сними задний кожух: поверни два жёлтых фиксатора", "hands", "frame",
              note="Под задним кожухом — батарейный лоток с главным автоматом."),
            T("p_door", "Открой дверцу батарейного отсека", "hands", "frame",
              after=["p_cover_f", "p_cover_r"],
              note="Болты клемм потом — в магнитную плошку, а не «куда-то на верстак»."),
            # source: quantum/edge-4-om.pdf p7 — автомат = выключатель батарей (жёлтая кнопка отключает);
            # p25 (Group 24): «Disengage the breaker … by pressing the yellow button» до снятия проводов
            T("p_breaker", "Нажми жёлтую кнопку главного автомата — батареи отключены от системы", "hands", "breaker",
              after=["p_cover_r"], safety=True,
              note="Автомат на Edge 4 — он же выключатель батарей: цепь разорвана ещё до ключа на клеммах.",
              failnote="Ты полез ключом к клеммам, не отключив батареи автоматом: вся цепь под напряжением, "
                       "и соскочивший ключ дал искру."),
            T("p_disc_neg", "Отсоедини МИНУСОВУЮ клемму — всегда первой", "wrench", "battery",
              after=["p_off", "p_drive", "p_door", "p_breaker"], safety=True,
              note="Минус снят — цепь на массу разорвана, ключ уже не устроит короткое.",
              failnote="Пока минус на массе, ключ, соскочивший с плюса на раму, — это короткое "
                       "замыкание, искры и оплавленные клеммы."),
            T("p_disc_pos", "Отсоедини плюсовую клемму", "wrench", "battery",
              after=["p_disc_neg"]),
            T("p_out", "Вынь старые батареи из отсека", "hands", "battery",
              after=["p_disc_pos"],
              note="Батареи тяжёлые: поднимай из приседа и держи вертикально.",
              ghost="Барти: «Дай я подниму! ...ах да. Ладно, ты сам.»"),
            T("p_in", "Установи новую пару по каталогу Гильдии", "hands", "battery",
              after=["p_out"],
              note="Новую пару — зафиксировать: болтающаяся батарея перетирает провода на первой же кочке.",
              spec=dict(manual="battery_pair", prompt="Какую пару батарей ставим?",
                        options=[
                            ("Две новые AGM 12 В — одинаковые ёмкость, тип и возраст", True, ""),
                            ("Одну новую + прошлогоднюю той же ёмкости (экономия!)", False,
                             "Пара работает по слабейшей: старая батарея утащит новую за собой."),
                            ("Новую AGM + новую гелевую — обе же 12 В", False,
                             "Типы не смешивают: у AGM и геля разные режимы заряда, умрут обе."),
                        ])),
            T("p_conn_pos", "Подключи ПЛЮСОВУЮ клемму первой", "wrench", "battery",
              after=["p_in"], safety=True,
              note="Сборка — зеркально разборке: плюс первым, минус последним.",
              failnote="Минус подключают последним: пока массы нет, соскочивший ключ "
                       "не сделает короткого замыкания."),
            T("p_conn_neg", "Подключи минусовую клемму", "wrench", "battery",
              after=["p_conn_pos"]),
            T("p_breaker_on", "Опусти рычажок главного автомата — питание батарей вернулось", "hands", "breaker",
              after=["p_conn_neg"],
              note="Кнопка автомата отключает батареи, рычажок вниз — подключает."),
            T("p_door_close", "Закрой дверцу батарейного отсека", "hands", "frame",
              after=["p_conn_neg"]),
            T("p_covers", "Поставь кожухи на место", "hands", "frame",
              after=["p_door_close", "p_breaker_on"],
              note="Без кожухов в отсек летит грязь, а к клеммам тянутся руки."),
            T("p_charge", "Поставь новую пару на полную первую зарядку", "charger", "battery",
              after=["p_covers"],
              note="Первая зарядка — полная и только штатным ЗУ: она задаёт паре ресурс."),
        ],
        test="Пульт ожил, индикатор заряда ползёт вверх. Бренна проверяет затяжку клемм. Кивнула!",
        fact="Батареи меняют только парой одного типа, ёмкости и возраста. Разборка: минус снимают первым. "
             "Сборка: плюс подключают первым. Первая зарядка новой пары — полная, штатным зарядным устройством.",
        thanks="Бренна: «По регламенту, без суеты. Из тебя выйдет техник, зомби.»",
    ),

    # === Т3. Схождение: коляску уводит (геометрия + мини-интеракция) ===
    dict(
        id="toe", track="tech", kind="manual", client="Кентавр Тавр (курьер)",
        client_art="client_centaur.png", chair_art="chair_basic.png",
        title="Схождение: коляску уводит",
        symptom="Курьерская коляска кентавра: колёса целы, давление вроде есть, но её тянет "
                "вбок и резину «ест». Классика — сбито схождение (toe). Меряй, не гадай.",
        manual=["toe"],
        tools=["tape", "allen", "hands", "wrench", "gauge", "lube"],
        intro="Бренна: «Уводит при исправных колёсах? Значит, геометрия. Рулетка скажет правду.»",
        steps=[
            T("x_press", "Сверь манометром давление в обеих шинах: оно должно совпадать", "gauge", "tire",
              note="Неравное давление имитирует сбитое схождение — сначала исключи его.",
              ghost="Барти: «А я говорил — дуть! В этот раз я, кажется, прав?!»"),
            T("x_meas", "Замерь рулеткой расстояние между ободами спереди и сзади", "tape", "rear_wheel",
              after=["x_press"],
              note="Разница замеров спереди и сзади — это и есть схождение."),
            T("x_loose", "Ослабь болты осевой пластины", "allen", "bolts",
              after=["x_meas"],
              note="Пластина держит ось: ослабил — можно двигать колесо."),
            T("x_set", "Выставь колёса параллельно (сведи разницу замеров к нулю)", "hands", "rear_wheel",
              after=["x_loose"],
              mini=dict(kind="gap", lo=0, hi=1, mn=0, mx=8, unit="мм", start=5,
                        label="Разница замеров спереди/сзади",
                        hint="Мануал: схождение 0 мм, допуск 1 мм",
                        fb_hi="Больше 1 мм — всё ещё тянет вбок и ест резину. Точнее.")),
            T("x_tight", "Затяни болты пластины крест-накрест", "allen", "bolts",
              after=["x_set"],
              note="Крест-накрест — чтобы пластину не перекосило при затяжке."),
            T("x_re", "Контрольный замер рулеткой спереди и сзади", "tape", "rear_wheel",
              after=["x_tight"],
              note="После затяжки геометрия могла уйти — всегда перемеряй."),
        ],
        test="Толкаешь коляску через мастерскую — катится стрелой. Тавр бьёт копытом от восторга.",
        fact="Коляску тянет вбок при исправных колёсах? Сначала выровняй давление в шинах, потом проверь "
             "схождение: замер между ободами спереди и сзади должен совпадать (допуск ~1 мм). "
             "Регулируют на осевой пластине, затяжка — крест-накрест, после — контрольный замер.",
        thanks="Тавр: «Прямо едет! Четыре ноги хорошо, а ровные колёса — лучше.»",
    ),
]

TECH_JOBS += [
    # --- Гильдия, вторая волна: Quickie Pulse 6 (VR2), Quantum Q6 Edge (Q-Logic) ---

    # === Т: Quickie Pulse 6 + VR2 — «2 деления мигают» ===
    dict(
        id="t_pulse6", track="tech", kind="power", client="Мастерица Бренна",
        client_art="master.png", chair_art="chair_pulse6.png", chair_model="pulse6",
        chair_name="Quickie Pulse 6 (средний привод, пульт VR2)",
        title="VR2: мигают 2 деления",
        symptom="Экзаменационная коляска Гильдии: при включении индикатор батареи VR2 быстро мигает двумя "
                "делениями, коляска стоит. Найди причину замером, а не догадкой.",
        manual=["vr2_codes"],
        tools=["hands", "eyes", "multimeter", "screw", "charger", "lube", "brush"],
        intro="Бренна: «Мигает — значит, контроллер что-то тебе говорит. Сначала переведи, потом меряй, "
              "потом крути. И питание — до разъёмов, а не после.»",
        steps=[
            # source: P6_SM p26 (printed 2.1: Battery Gauge Flashes Rapidly), p27 (printed 3.1: Two Bars)
            T("q_code", "Расшифруй мигание индикатора VR2 по таблице кодов", "eyes", "controller",
              note="Быстрое мигание делений индикатора — код неисправности, а не уровень заряда.",
              spec=dict(manual="vr2_codes", prompt="Быстро мигают 2 деления. Что это?",
                        options=[
                            ("Левый мотор отключён (контроллер его не видит)", True, ""),
                            ("Низкое напряжение батареи", False,
                             "Низкое напряжение — 1 деление. Тут два."),
                            ("Неисправен тормоз (соленоид)", False,
                             "Тормоз — 9 делений."),
                        ])),
            # source: P6_SM p27 (printed 3.1): check batteries fully charged; p44 (printed 5.10): 25.6 V / 24 V
            T("q_batt", "Проверь заряд: мультиметр на гнездо зарядки джойстика, контакты 1(+) и 2(−)",
              "multimeter", "battery", after=["q_code"],
              note="Блок-схема кода 2 начинается с заряда батарей.",
              mini=dict(kind="meter", reading="25.5 В",
                        sub="мануал: полная пара ≈25,6 В, разряженная ≤24 В",
                        prompt="Что с батареями?",
                        options=[
                            ("Заряжены — ищем дальше, в моторе", True, ""),
                            ("Разряжены — код от этого", False,
                             "Разряженная пара даёт 24 В и ниже. 25,5 В — почти полная."),
                            ("Перезаряд — проверять зарядку", False,
                             "Перезаряд или поверхностный заряд — выше 26–28 В."),
                        ])),
            T("q_off", "Выключи питание на джойстике VR2", "hands", "controller", safety=True,
              note="Разъёмы и щётки трогают только на обесточенной коляске.",
              failnote="Ты выдернул разъём мотора под питанием: искра на контактах, а модуль управления "
                       "получил бросок тока. Бренна молча выключает коляску сама.",
              ghost="Бренна: «Выключил? Теперь проверь, что выключил.»"),
            # source: P6_SM p27 (printed 3.1): look for a loose or damaged connector;
            # source: P6_SM p48 (printed 6.2): connector overheating; disconnect from control module
            T("q_disc", "Отсоедини 4-контактный разъём левого мотора от модуля управления",
              "hands", "wiring", after=["q_off", "q_code"],
              note="Разъём цел, без следов перегрева, сидел плотно. Значит, проблема глубже."),
            # source: P6_SM p27 (printed 3.1): two bottom (thicker wires) contacts, 0-1.5 ohm -> controller
            # source: P6_SM p49 (printed 6.3): normal 0.5-0.9 ohm through brushes and motor
            T("q_ohm", "Замерь сопротивление между двумя нижними (толстыми) контактами разъёма мотора",
              "multimeter", "motor", after=["q_disc", "q_batt"],
              note="Это цепь «щётки + обмотка». Норма — около 0,5–0,9 Ом.",
              mini=dict(kind="meter", reading="OL",
                        sub="мультиметр на Ω · мануал: 0–1,5 Ом — мотор цел; иначе — щётки",
                        prompt="Что показывает замер?",
                        options=[
                            ("Обрыв цепи мотора — проверяем щётки левого мотора", True, ""),
                            ("Мотор цел — менять контроллер", False,
                             "Контроллер меняют, если тут 0–1,5 Ом. «OL» — это обрыв."),
                            ("Это тормоз, норма 12–15 Ом", False,
                             "Тормоз меряют на малых контактах. Толстые — это мотор."),
                        ])),
            # source: P6_SM p27 (printed 3.1): flat head screwdriver, remove brush cap;
            # source: P6_SM p47 (printed 6.1): one brush at a time, note orientation, don't damage cap
            T("q_cap", "Открути колпачки щёткодержателей плоской отвёрткой",
              "screw", "brushes", after=["q_ohm", "q_off"],
              note="Колпачок пластиковый — без лишнего усилия.",
              ghost="Барти: «Колпачок тугой? Навались всем весом!» — нет, пластик колпачка легко сломать."),
            # source: P6_SM p48 (printed 6.2): replace any brush less than 1/4 inch; replace both motors
            T("q_wear", "Вынь щётки по одной и оцени их износ", "hands", "brushes", after=["q_cap"],
              note="Запомни, как стояла щётка: новую ставят той же стороной.",
              spec=dict(manual="vr2_codes", prompt="Щётка левого мотора — 4 мм, торец со сколом. Решение?",
                        options=[
                            ("Меньше 1/4\" (≈6 мм) — менять щётки в обоих моторах", True, ""),
                            ("4 мм ещё поработают — ставим обратно", False,
                             "Предел — 1/4\" (≈6 мм). 4 мм — уже износ, отсюда и обрыв."),
                            ("Поменять одну эту щётку", False,
                             "Мануал: меняешь щётки — меняй в обоих моторах, чтобы тянули одинаково."),
                        ])),
            T("q_new", "Вставь новые щётки той же стороной, как стояли старые, — в обоих моторах",
              "hands", "brushes", after=["q_wear"],
              note="Щётка, поставленная другой стороной, долго притирается к коллектору."),
            T("q_capon", "Закрути колпачки щёткодержателей отвёрткой, без усилия",
              "screw", "brushes", after=["q_new"],
              note="Пластиковый колпачок легко сорвать — до упора, и хватит."),
            T("q_plug", "Подключи 4-контактный разъём левого мотора к модулю управления",
              "hands", "wiring", after=["q_capon", "q_off"],
              note="Разъём — до щелчка, провода не натягивай."),
            # source: P6_SM p44 (printed 5.10): failure to disengage gearbox -> unexpected operation;
            # source: P6_SM p48 (printed 6.2): run-in with gearbox released
            T("q_free", "Разблокируй редукторы обоих моторов: рычаги свободного хода",
              "hands", "freewheel",
              after=["q_capon"], safety=True,
              note="Колёса больше не связаны с моторами: прогон не сдвинет коляску.",
              failnote="Ты погнал моторы на обкатку, не разблокировав редукторы: коляска рванула через "
                       "мастерскую. Мануал прямо предупреждает: без расцепления — неожиданное движение."),
            # source: P6_SM p48 (printed 6.2): run-in 20-30 min alternating forward and reverse;
            # source: P6_SM p4 (printed 0.2): power off, chair should not move if pushed -> drive engaged
            T("q_on", "Включи питание для обкатки", "hands", "controller", after=["q_plug"],
              note="Мигания нет — мотор снова на связи."),
            T("q_runin", "Обкатай щётки 20–30 мин: джойстик попеременно вперёд и назад",
              "hands", "controller", after=["q_on", "q_free"],
              note="Новые щётки сначала обкатывают: так они притираются, и замер сопротивления потом точный."),
            T("q_off2", "Выключи питание после обкатки", "hands", "controller", after=["q_runin"],
              note="После работ по мануалу: питание выключено, потом передачи — в зацепление."),
            T("q_engage", "Верни редукторы в зацепление: рычаги — в режим езды", "hands", "freewheel",
              after=["q_off2"],
              note="Проверка: питание выключено, толкаешь сзади — коляска не катится. Значит, передачи в зацеплении."),
        ],
        test="Включение: индикатор горит ровно, без мигания. Коляска едет прямо, оба мотора тянут одинаково. "
             "Бренна проверяет, что редукторы в зацеплении. Кивок.",
        # source: P6_SM p26-27, p47-49
        fact="Пульт VR2 сообщает неисправности быстрым миганием делений индикатора: 2 деления — левый мотор "
             "не определяется. Сначала проверяют заряд и разъём, потом мультиметр на толстых контактах. "
             "0–1,5 Ом — мотор цел, виноват контроллер. Обрыв — щётки: короче 1/4\" меняют в обоих моторах "
             "и обкатывают 20–30 минут.",
        thanks="Бренна: «Не поменял контроллер “на всякий случай” — уже техник. Остальное — опыт.»",
    ),

    # === Т: Quantum Q6 Edge + Q-Logic — «#203 Brake 1 Disconnected» ===
    dict(
        id="t_q6brake", track="tech", kind="power", client="Мастерица Бренна",
        client_art="master.png", chair_art="chair_q6edge.png", chair_model="q6edge",
        chair_name="Quantum Q6 Edge (средний привод, пульт Q-Logic)",
        title="Q-Logic: #203 — тормоз отключён",
        symptom="Экзаменационная коляска Гильдии: при включении дисплей Q-Logic пишет «#203», коляска стоит. "
                "Пройди блок-схему производителя от начала до конца, без самодеятельности.",
        manual=["q6_qlogic"],
        tools=["hands", "eyes", "multimeter", "screw", "socket", "wrench", "charger"],
        intro="Бренна: «Блок-схема — не совет, а маршрут. Сошёл с маршрута — значит, гадаешь. "
              "А гадать будешь на ярмарке.»",
        steps=[
            # source: Q6_TS p29 (#203); QL_TM p92 (M1 = left motor)
            T("b_code", "Найди код дисплея в таблице Q-Logic", "eyes", "controller",
              note="Тормоз 1 — это тормоз мотора M1, по умолчанию левого.",
              spec=dict(manual="q6_qlogic", prompt="Дисплей: «#203». Что это?",
                        options=[
                            ("Тормоз 1 (левый мотор) не определяется: разъём, проводка или сам тормоз", True, ""),
                            ("Джойстик вне диапазона — откалибровать", False,
                             "Это #38. Калибровку делают программатором, и тормоз она не вылечит."),
                            ("Батарея пуста — просто зарядить", False,
                             "Пустая батарея — #105."),
                        ])),
            # source: Q6_TS p16 (Symptoms: batteries fully charged), p4 (about 25 VDC at charger port)
            T("b_batt", "Проверь заряд: мультиметр на гнездо зарядки джойстика", "multimeter", "battery",
              after=["b_code"],
              note="Блок-схема исходит из того, что батареи заряжены. Проверь, а не верь на слово.",
              mini=dict(kind="meter", reading="25.3 В",
                        sub="мануал: около 25 В — норма; меньше 18 В — сначала зарядить",
                        prompt="Что с батареями?",
                        options=[
                            ("Около 25 В — заряжены, идём по блок-схеме", True, ""),
                            ("Разряжены — код от этого", False,
                             "Разряд — это меньше 18 В. Тут около 25 В."),
                            ("Полярность перепутана", False,
                             "При обратной полярности мультиметр показал бы минус."),
                        ])),
            # source: Q6_TS p16 (Ensure both freewheel levers are in drive mode);
            # source: Q6_OM p10 (freewheel with power on -> error; clear: off, drive mode, on);
            # source: Q6_OM p26 (wheel service: not in freewheel mode)
            T("b_free", "Переведи оба рычага свободного хода в режим езды (вверх)",
              "hands", "freewheel", after=["b_code"], safety=True,
              note="Режим езды — тормоза моторов включены: коляска не укатится.",
              failnote="Ты полез под кожух, а рычаг свободного хода остался внизу. Тормоза отключены — "
                       "коляска скатилась с подставки. Бренна поймала её в метре от стеллажа.",
              ghost="Барти: «Рычаги дёргают ногой, так быстрее!» — нет: мануал запрещает — погнёшь рычаг и тормоз."),
            # source: Q6_TS p31 (Appendix 2: rear shroud knob, securement clips)
            T("b_restart", "Перезапусти питание джойстика", "hands", "controller", after=["b_free"],
              note="Код остался — значит, дело не в рычагах. Идём дальше по схеме."),
            T("b_off", "Выключи питание джойстика", "hands",
              "controller", safety=True, after=["b_restart"],
              note="Модуль питания и разъёмы моторов отключают только без питания.",
              failnote="Модуль питания отсоединён под током: искра на разъёме и испорченный модуль. "
                       "Экзамен окончен."),
            T("b_shroud", "Сними задний кожух: ручка-барашек и защёлки", "hands", "frame",
              after=["b_free"],
              note="Кожух — на ручке и защёлках, инструмент не нужен."),
            # source: Q6_TS p16, p31 (power module screws)
            T("b_pm", "Открути винты модуля питания на задней раме", "screw", "wiring",
              after=["b_off", "b_shroud"],
              note="Провода не натягивай: модуль просто откидывается, чтобы был доступ к разъёмам."),
            T("b_unplug", "Выдерни разъём жгута левого мотора из модуля питания", "hands", "wiring",
              after=["b_pm", "b_off"],
              note="Тяни за корпус разъёма, а не за провода."),
            # source: Q6_TS p16 (pins 3-4, about 80 ohms)
            T("b_ohm", "Замерь сопротивление тормоза: контакты 3–4 разъёма левого мотора", "multimeter", "mag_brake",
              after=["b_unplug"],
              note="Контакты 3–4 — катушка тормоза. Контакты 1–2 — обмотка мотора.",
              mini=dict(kind="meter", reading="OL",
                        sub="мультиметр на Ω, контакты 3–4 · мануал: тормоз ≈80 Ом",
                        prompt="Что показывает замер?",
                        options=[
                            ("Обрыв — цепь левого тормоза разорвана", True, ""),
                            ("≈80 Ом — тормоз в порядке", False,
                             "На экране «OL» — бесконечность, а не 80 Ом."),
                            ("Норма, ведь мотор даёт 0,5–1,5 Ом", False,
                             "0,5–1,5 Ом — обмотка мотора на контактах 1–2. Тормоз — 3–4, ≈80 Ом."),
                        ])),
            # source: Q6_TS p16 (not about 80 ohms -> replace the left motor and retest)
            T("b_replace", "Действуй по блок-схеме: открути торцевым ключом и замени узел мотора с тормозом",
              "socket", "motor", after=["b_ohm"],
              note="Мотор и тормоз — один узел (motor/brake assembly): меняют целиком.",
              spec=dict(manual="q6_qlogic", prompt="Левый тормоз — обрыв. Что по блок-схеме?",
                        options=[
                            ("Заменить левый мотор в сборе с тормозом и проверить систему", True, ""),
                            ("Заменить модуль питания", False,
                             "Модуль меняют, только если ОБА тормоза показывают ≈80 Ом."),
                            ("Откалибровать джойстик программатором", False,
                             "Калибровка — от #38. Тормоз она не починит."),
                        ])),
            # source: Q6_OM p26 (Check the brakes: level surface, 1 m clearance, listen for clicks x4)
            T("b_plug", "Подключи разъём нового мотора к модулю питания", "hands", "wiring",
              after=["b_replace"],
              note="Провода не натягивай: разъём должен защёлкнуться без усилия на жгут."),
            T("b_back", "Прикрути модуль питания на место", "screw", "wiring",
              after=["b_plug"],
              note="Винты — до упора, без срыва резьбы."),
            T("b_cover", "Поставь задний кожух на место", "hands", "frame",
              after=["b_back"]),
            T("b_on", "Включи питание джойстика", "hands", "controller",
              after=["b_cover", "b_free"],
              note="#203 больше нет — новый тормоз на связи."),
            T("b_test", "Тест тормозов: ровная площадка, малая скорость, джойстик плавно вперёд до щелчка, "
                        "затем назад, влево, вправо",
              "hands", "controller", after=["b_on"],
              note="В каждом направлении должен быть слышен щелчок тормоза через пару секунд."),
        ],
        test="#203 нет. В каждом направлении щёлкает тормоз, на уклоне коляска стоит как вкопанная. "
             "Бренна ставит отметку в журнал экзаменов.",
        # source: Q6_TS p16, p29; Q6_OM p10, p26
        fact="Q-Logic пишет номер ошибки: #203/#204 — тормоз 1/2 не отвечает. Схема Quantum: оба рычага "
             "свободного хода в режим езды, модуль питания отсоединить, на разъёме мотора контакты 3–4 должны "
             "давать около 80 Ом. Нет 80 Ом — менять мотор в сборе с тормозом. Модуль питания меняют, только "
             "если оба тормоза в норме.",
        thanks="Бренна: «Не стал калибровать джойстик от тормозной ошибки — уже умнее половины ярмарки.»",
    ),
]

# насос подключают к ниппелю (клапану): в шагах накачки ниппель тоже верная цель —
# замечание коллеги-тестировщика: «к шине» и «к ниппелю» — оба естественных ответа
for _job in JOBS:
    for _v in [_job] + _job.get("variants", []):
        for _st in _v.get("steps", []):
            if _st.get("tool") == "pump" and _st.get("part") in ("tire", "tube", "cushion"):
                _st["alt"] = tuple(set(_st.get("alt", ())) | {"valve"})

ALL_JOBS = JOBS + TECH_JOBS

# Сноски из мануалов (карточка внизу справа при наведении на деталь в ремонте): задание -> {деталь: (мануал,
# страница или None, текст)}. Только то, что помогает в ремонте и чего нет в общем шаге: особенности этой модели,
# размеры, усилия, давление, где кнопка. Источник каждой — в «# source:» над заданием.
MANUAL_NOTES = {
    "aeroz_lock": {
        "brake": ("TiLite Aero Z", "70–72", "Хомут замка: ослабить (не выкручивать) два винта ключом 3/16\", сдвинуть, "
                  "затянуть. Регулируют только на накачанной шине; зажатый упор вдавливается в шину минимум на 3/16\" (≈5 мм)."),
        "tire": ("TiLite Aero Z", "15, 22", "Давление проверять каждую неделю, норма напечатана на боковине шины. "
                 "На мягкой шине замки проскальзывают."),
        "bolts": ("TiLite Aero Z", "26", "После любой регулировки весь крепёж затягивают до поездки."),
    },
    "cross6_back": {
        "backrest": ("Etac Cross 6", "31", "Угол спинки — гайка 13 мм с внутренней стороны крепления заднего колеса. "
                     "Ослабить у одной стойки, выставить, затянуть, потом вторую; сверить расстояние стойка ↔ пластина "
                     "подлокотника с обеих сторон."),
        "anti_tip": ("Etac Cross 6", "13", "После любой регулировки проверить антиопрокидыватели: работают и защёлкнуты."),
        "brake": ("Etac Cross 6", "32", "В отпущенном виде штифт тормоза — в 15–20 мм от шины, винт — около 5 Н·м. "
                  "Работа тормоза зависит от давления в шине."),
    },
    "iris_tilt": {
        "anti_tip": ("Quickie Zippie IRIS", "13, 16", "Антиопрокидыватели — 38–51 мм (1½–2\") от пола, оба строго на "
                     "одной высоте, переставляются кнопкой. Выше 51 мм могут не удержать, ниже 38 мм — цепляются."),
        "tilt_cable": ("Quickie Zippie IRIS", "27", "Ослабить контргайку, вращать регулятор, пока не уйдёт провис: "
                       "штифт-плунжер должен полностью убираться и входить в рокер. Потом затянуть гайку."),
        "tilt_lever": ("Quickie Zippie IRIS", "12, 20", "Оба курка вместе отпускают наклон, отпустил — рокеры заперты. "
                       "Не наклонять дальше, чем спинка параллельна полу."),
        "tire": ("Quickie Zippie IRIS", "13", "Давление по таблице: шина 22\" — 65 psi (448 кПа)."),
    },
    "focuscr_cable": {
        "tilt_cable": ("Ki Mobility Focus CR", "19–20", "Контргайку отпускают ключами 10 мм и 3/8\". Регулятор — до "
                       "исчезновения провиса, но зуб фиксатора полностью в зубьях. Трос с заломом или такой, что не "
                       "регулируется, меняют."),
        "tilt_lock": ("Ki Mobility Focus CR", "19", "Зуб чиркает или у курка люфт — регулятор выкрутить; зуб вышел из "
                      "зацепления — вкрутить. Затягивают только гайку."),
        "tilt_lever": ("Ki Mobility Focus CR", "19", "Нельзя оставлять человека в кресле с курками, зафиксированными "
                       "открытыми. Курок блокируют штифтом на шнурке."),
    },
    "whill_code": {
        "controller": ("WHILL Model C2", "105", "Код на пульте, звук — и коляска выключается. Коды: 01 подлокотник, "
                       "02 джойстик не в центре при включении, 03 тормоза, 04 зарядка, 05 батарея ≤20 %, 10 связь по "
                       "кабелю сиденья."),
        "joystick": ("WHILL Model C2", "107", "Джойстику хватает усилия около 1 Н — питание включают, не касаясь его."),
        "freewheel": ("WHILL Model C2", "36", "Перед поездкой рычаги разблокировки тормозов должны быть подняты — "
                      "тормоза заперты."),
        "armrest": ("WHILL Model C2", "106", "Рычаг подлокотника ходит туго — в основании пыль: вычистить щёткой или "
                    "продуть."),
    },
    "f5_charge": {
        "freewheel": ("Permobil F5 Corpus", "34", "Свободный ход — только на ровном месте, пульт выключен, рядом "
                      "помощник. У F5 оба рычага ВНИЗ — свободный ход, ВВЕРХ — езда."),
        "breaker": ("Permobil F5 Corpus", "39–40", "Сначала выключить пульт, потом главный автомат. Включают автомат "
                    "один раз; выбивает снова — в сервис."),
        "battery": ("Permobil F5 Corpus", "39–40", "Хранить в сухом месте не холоднее +5 °C, иначе батареи не "
                    "зарядятся полностью. Перед долгим хранением — зарядить и выключить главный автомат."),
        "controller": ("Permobil F5 Corpus", "33", "Гнездо зарядки — на пульте. Зарядку подключают сначала к коляске, "
                       "потом к розетке."),
        "tire": ("Permobil F5 Corpus", "64", "Ведущие шины — 250 кПа; проверять раз в неделю и после смены температуры."),
    },
    "lift": {
        "controller": ("Q-Logic 3", "8", "Кнопка key 2 сразу открывает экран сиденья. Индикатор блокировки: "
                       "зелёный — без ограничений, жёлтый — лифт ограничил скорость, красный — блокировка."),
        "seat_lift": ("Quantum Edge 4", "9", "iLevel работает, только если наклон и откидывание сиденья не больше 20°. "
                      "Поднимать — на ровном полу в помещении, зону вокруг ножниц держать свободной."),
        "actuator": ("Quantum Edge 4", "19, 26", "Все разъёмы — плотные, закреплённые, без коррозии. Треснувший "
                     "разъём или перетёртый жгут — к дилеру Quantum."),
        "battery": ("Quantum Edge 4", "7", "Главный автомат — на батарейном лотке под задней крышкой; крышка "
                    "снимается без инструментов."),
    },
    "cushion": {
        "cushion": ("ROHO: как настроить подушку", None, "Настраивают, когда человек сидит: ладонь под самую низкую "
                    "кость таза, стравливать воздух, пока пальцы не начнут чуть двигаться — под тазом 1,5–2,5 см "
                    "воздуха (примерно палец)."),
    },
    "yaga_d100": {
        "axle": ("Vermeiren D100", "16", "Высота сиденья — перестановкой колёс: 470 мм — ось в отверстиях 1+2, вилки "
                 "в A; 500 мм — 2+3 и B; 530 мм — 3+4 и C. Верхнее отверстие пластины — для барабанного тормоза."),
        "brake": ("Vermeiren D100", "8, 17", "Регулировка: отпустить тормоз, ослабить болты, сдвинуть по направляющей к "
                  "колесу, затянуть, проверить толчком. Тормоза стояночные — не для торможения на ходу."),
        "rear_wheel": ("Vermeiren D100", "12", "Колесо снимают при отпущенных тормозах: кнопка в центре ступицы."),
        "caster_stem": ("Vermeiren D100", "16", "После перестановки вилка должна стоять отвесно к полу."),
    },
    "olga_x3": {
        "brake": ("Panthera X3", "15", "Тормоз сдвигают по рейке ключом 12 мм. В зажатом положении упор вдавлен в шину "
                  "примерно на 4 мм — одинаково с двух сторон."),
        "caster": ("Panthera X3", "21", "Два шестигранника 4 мм; почистить проставки, протереть подшипники, по капле "
                   "масла. На резьбе должен остаться клей-фиксатор, иначе — новый болт или мягкий фиксатор."),
        "axle": ("Panthera X3", "20", "После песка, соли или дождя быстросъёмную ось смазывают каплей масла."),
        "tire": ("Panthera X3", "7, 23", "Давление — 8 бар (800 кПа). На мягкой шине тормоз не держит."),
    },
    "leshy_x8": {
        "motor": ("Magic Mobility Extreme X8", "16–17", "Застрял — не держи джойстик дольше нескольких секунд: моторы "
                  "перегреваются. В воду и болота не въезжать."),
        "tire": ("Magic Mobility Extreme X8", "14, 36–38", "Разное давление тянет коляску вбок. На бездорожье — до "
                 "8 psi, максимум 24 psi; проверять раз в неделю."),
        "rim": ("Magic Mobility Extreme X8", "38", "Гайки колёс X8 затягивают с усилием 47–50 Н·м."),
    },
    "ra_emotion": {
        "motor": ("Alber e-motion M25", "56, 61", "Все огоньки мигают белым и 4 сигнала — температура зарядки вне "
                  "0…40 °C, зарядка прервана. Заряжать при 0…40 °C, оба колеса выключены."),
        "brake": ("Alber e-motion M25", "49, 56", "У колёс e-motion нет своих тормозов: при зарядке и на стоянке "
                  "зажимают тормоза коляски."),
        "rear_wheel": ("Alber e-motion M25", "55, 57", "Гнездо зарядки — магнитное, на кнопке ступицы; чистить сухой "
                       "тряпкой, без металла. Пока идёт зарядка, на обручи не давить."),
    },
    "gorynych_jazzy": {
        "breaker": ("Pride Jazzy 614", "19", "Автомат выбивает при перегрузке: подождать около минуты, нажать кнопку, "
                    "включить пульт. Выбивает снова и снова — в сервис Pride."),
        "frame": ("Pride Jazzy 614", "10, 38", "Предел веса — вместе со всем, что на коляске: Jazzy 614 — 136 кг "
                  "(300 lb), 614 HD — 204 кг."),
        "battery": ("Pride Jazzy 614", "37", "Нет питания — проверить разъёмы жгутов, автомат и клеммы батарей."),
    },
}


# ----------------------------------------------------------------------------- #
#  UI-объекты
# ----------------------------------------------------------------------------- #
def _of(a, b):
    """«3 из 5» / «3 of 5» — для озвучки счётчиков (по языку, без словаря)."""
    return f"{a} из {b}" if LANG["code"] == "ru" else f"{a} of {b}"


_SPEECH_SUBS = [("✔", ""), ("⚑", ""), ("◉", ""), ("○", ""), ("✉", ""), ("⚠", ""), ("▶", ""), ("◀", ""),
                ("★", ""), ("☆", ""), ("⟲", ""), ("•", ""), ("[", ""), ("]", ""), ("…", "..."), ("·", ","),
                ("″", "")]


def speech_clean(text):
    """Текст для голоса: без значков, «1920×1080» — словами."""
    t = str(text or "")
    for a, b in _SPEECH_SUBS:
        t = t.replace(a, b)
    t = re.sub(r"(\d)\s*×\s*(\d)", r"\1 " + ("на" if LANG["code"] == "ru" else "by") + r" \2", t)
    t = re.sub(r"\s*—\s*", ", ", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.!?:;])", r"\1", t)
    t = re.sub(r"([.!?])[.,]+(?=\s|$)", r"\1", t)
    t = re.sub(r",\s*,", ",", t).strip(" ,")
    return t


def screen_reader_running():
    """Windows сообщает, что работает экранный чтец (NVDA, JAWS, Экранный диктор…)."""
    try:
        import ctypes
        flag = ctypes.c_int(0)
        ctypes.windll.user32.SystemParametersInfoW(0x0046, 0, ctypes.byref(flag), 0)   # SPI_GETSCREENREADER
        return bool(flag.value)
    except Exception:
        return False


class Speech:
    """Озвучка: через экранный чтец игрока (NVDA, JAWS… — библиотека Tolk, с его голосом, скоростью и брайлем),
    а если чтеца нет — голосом Windows (SAPI) на языке игры."""

    def __init__(self):
        self.kind, self.name, self.tolk, self.voice = None, "", None, None
        self.log = []                                  # что сказано (для тестов и повтора)

    def init(self):
        if self.kind:
            return
        if IS_WEB:
            self.kind, self.name = "web", "web"
            return
        try:
            from cytolk import tolk
            tolk.load()
            reader = tolk.detect_screen_reader()
            if reader:
                self.tolk, self.kind, self.name = tolk, "tolk", reader
                return
        except Exception:
            pass
        try:
            import win32com.client
            self.voice = win32com.client.Dispatch("SAPI.SpVoice")
            self.kind, self.name = "sapi", "SAPI"
            self.set_voice()
        except Exception:
            self.kind = None

    def set_voice(self):
        """Голос Windows — на языке игры (русский — Irina/Pavel, английский — David/Zira…), скорость из настроек."""
        if IS_WEB:
            web_js(f"document.documentElement.setAttribute('data-wnb-lang', "
                   f"{json.dumps('ru-RU' if LANG['code'] == 'ru' else 'en-US')})")
            return
        if self.kind != "sapi":
            return
        want = ("419",) if LANG["code"] == "ru" else ("409", "809", "c09", "1009")
        try:
            for v in self.voice.GetVoices():
                lang = (v.GetAttribute("Language") or "").lower().split(";")
                if any(l_.strip() in want for l_ in lang):
                    self.voice.Voice = v
                    break
            self.voice.Rate = max(-10, min(10, int(A11Y["rate"])))
        except Exception:
            pass

    def say(self, text, interrupt=True):
        text = speech_clean(text)
        if not text:
            return
        self.log.append(text)
        del self.log[:-200]
        if IS_WEB:                                    # экранный чтец страницы читает всегда, голос браузера — по F2
            web_js(f"window.wnbSay && wnbSay({json.dumps(text)}, {str(bool(interrupt)).lower()}, "
                   f"{str(bool(A11Y['on'])).lower()})")
            return
        if not A11Y["on"] or not self.kind:
            return
        try:
            if self.kind == "tolk":
                self.tolk.output(text, interrupt)
            else:
                self.voice.Speak(text, 1 | (2 if interrupt else 0))     # асинхронно; 2 — оборвать прошлое
        except Exception:
            pass

    def label(self):
        if self.kind == "web":
            return "экранный чтец страницы" + (" + голос браузера" if A11Y["on"] else "")
        if self.kind == "tolk":
            return self.name
        return "голос Windows" if self.kind == "sapi" else "недоступна"


SPEECH = Speech()


def _min_btn_sz():
    """Мельче этого подпись кнопки не сжимается; при крупном тексте (TEXT_K) — в тех же экранных пикселях."""
    return max(8, round(11 / TEXT_K[min(len(TEXT_K) - 1, max(0, A11Y.get("text", 0)))]))


# Титры (экран «ТИТРЫ» с титула и с вечеринки). Текст владельца — docs/credits_draft_en.txt; английский — в словаре.
CREDITS = [
    ("КОЛЁСА И КОСТИ", ["Бесплатная игра о том, как держать колёса на ходу.", "Автор игры — Андрей.",
                        "Тестирование: Ольга, Лиз и Яна.",
                        "Сделано GOAT — Grassroots Open Assistive Tech", "openassistivetech.org"]),
    ("ЗНАНИЯ ПО РЕМОНТУ", ["Шаги и факты — из настоящих сервисных мануалов и руководств пользователя,",
                           "собранных BARC — Bay Area Repair Coalition, программой GOAT:",
                           "Permobil, Quantum/Pride, Invacare, Ki Mobility, Sunrise/Quickie, TiLite,",
                           "Etac, Progeo, Drive, WHILL, ROHO, Vermeiren, Panthera, Magic Mobility и Alber."]),
    ("УРОКИ ПОСАДКИ", ["По руководству Permobil «Seating & Positioning Guide»."]),
    ("АРТ, МОДЕЛИ И МУЗЫКА", ["Сделаны с помощью ИИ-инструментов и доработаны нашей командой.",
                              "Коляски: 3D-модели Meshy по фото производителей, кадры — Blender.",
                              "Портреты и фоны: ChatGPT (Codex), ComfyUI и Qwen-Image. Музыка: YuE."]),
    ("КОД", ["Написан при небольшой помощи Claude (Anthropic).", "Мартин и Барти передают привет."]),
    ("ШРИФТЫ И ЛИЦЕНЗИИ", ["Шрифты: DejaVu Sans и Atkinson Hyperlegible (Braille Institute).",
                           "Код: MIT. Содержимое игры: CC BY-SA 4.0 — делитесь и переделывайте, указывая GOAT."]),
    ("БЕЗОПАСНОСТЬ", ["Учись здесь, а настоящую коляску чини с её мануалом в руках",
                      "или доверь квалифицированному технику. Названия брендов принадлежат их владельцам."]),
    ("СПАСИБО", ["Нашим тестировщикам, каждому волонтёру с гаечным ключом",
                 "и всем, кто помогает коляскам катиться."]),
]


class Button:
    def __init__(self, rect, label, color=AMBER, sub=""):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.sub = sub

    def hovered(self, m):
        return self.rect.collidepoint(m)

    def draw(self, surf, mouse, enabled=True, active=False, offset=(0, 0)):
        """offset — сдвиг только картинки (въезд в кадр); клики считаются по rect."""
        if surf is CAPTURE["frame"]:
            CAPTURE["buttons"].append(dict(rect=pygame.Rect(self.rect), label=tr(self.label), sub=tr(self.sub),
                                           enabled=enabled, active=active))
        CAPTURE["mute"] += 1
        try:
            return self._draw(surf, mouse, enabled, active, offset)
        finally:
            CAPTURE["mute"] -= 1

    def _draw(self, surf, mouse, enabled, active, offset):
        hov = self.hovered(mouse) and enabled
        col = self.color if enabled else DIM
        h = _hover_amt(tuple(self.rect), 1.0 if hov else 0.0)
        bg = (col[0] // 6 + 16, col[1] // 6 + 14, col[2] // 6 + 18)
        if active:
            bg = (col[0] // 3, col[1] // 3, col[2] // 3)
        bg = tuple(int(b + (c // 3 - b) * 0.45 * h) for b, c in zip(bg, col))
        r = self.rect.move(offset[0], offset[1] - round(3 * h))
        if h > 0.03 and DISPLAY["glow"]:
            g = Surf(r.inflate(12, 12).size, pygame.SRCALPHA)
            aa_rect(g, (*col, int(60 * h)), g.get_rect(), border_radius=12)
            surf.blit(g, r.inflate(12, 12).topleft)
        aa_rect(surf, bg, r, border_radius=7)
        aa_rect(surf, col, r, 3 if (hov or active) else 2, border_radius=7)
        cx = r.centerx
        if self.sub:
            sz = 16
            while sz > _min_btn_sz() and font(sz, True).size(tr(self.label))[0] > r.w - 14:
                sz -= 1
            ss = 12                                   # подпись и строка под ней — блоком по центру кнопки
            while ss > 9 and font(ss).size(tr(self.sub))[0] > r.w - 14:
                ss -= 1
            hl, hs = font(sz, True).get_height(), font(ss).get_height()
            top = r.centery - (hl + 2 + hs) / 2
            draw_text(surf, self.label, (cx, round(top + hl / 2)), sz, WHITE if enabled else GREY, bold=True,
                      center=True)
            draw_text(surf, self.sub, (cx, round(top + hl + 2 + hs / 2)), ss, GREY, center=True)
        else:
            sz = 17                                   # длинная подпись (часто в переводе) — мельче, но в кнопке
            while sz > _min_btn_sz() and font(sz, True).size(tr(self.label))[0] > r.w - 14:
                sz -= 1
            draw_text(surf, self.label, r.center, sz, col if enabled else GREY, bold=True, center=True)
        return r


_HOVER = {}


def _hover_amt(key, target):
    """Плавное 0..1 наведения на кнопку (Button пересоздаётся каждый кадр)."""
    now = pygame.time.get_ticks() / 1000.0
    amt, last = _HOVER.get(key, (0.0, now))
    if target >= 1 and amt < 0.04:
        snd("hover")
    amt += (target - amt) * (1.0 if A11Y.get("calm") else min(1.0, max(0.0, now - last) * 14))
    _HOVER[key] = (amt, now)
    return amt


# ----------------------------------------------------------------------------- #
#  Игра
# ----------------------------------------------------------------------------- #
LEG_GAGS = [
    "Мартин: «...опять левая нога отвалилась. Секунду.»",
    "Мартин: «Где моя нога? А, под верстаком. Опять.»",
    "Мартин: «Нога укатилась за коляской. Ирония.»",
    "Бартоломью: «Твоя нога снова сбежала. Я её не виню.»",
]


# ---- Живые реплики: клиенты волнуются и делятся советами, Барти шутит (факты — из заданий/мануалов) ----
# CLIENT_TALK[id]: intro (приход, по порядку), worry (болтовня), learn (совет пользователя),
# mistake/good (реакция на ход игрока), test (перед тест-драйвом).
CLIENT_TALK = {
    # === Туториал: своя коляска Мартина, прокол ===
    "flat": dict(
        intro=[
            "Мартин: «Коляска клюёт носом и катится, как телега с камнями. Заднее колесо спустило.»",
            "Барти: «Не грусти, Мартин! До вечеринки далеко, успеешь. Если ничего больше не отвалится.»",
        ],
        worry=[
            "Мартин: «Монтажка пластиковая — держу у конца. Я и сам ломкий, нам обоим хватит.»",
            "Мартин: «Интересно, что её прокололо. Надеюсь, не моя собственная косточка.»",
            "Барти: «А ты знаешь, где у камеры перёд? Я вот так и не узнал.»",
            "Мартин: «Коляска напрокат. Верну с дыркой — выпишут штраф. Или проклятье.»",
        ],
        learn=[
            "Мартин: «Записываю: нужное давление написано на боковине покрышки. Тут — 65–80 psi.»",
            "Мартин: «Мягкая шина — тяжелее катить и больше нагрузка на плечи. А плечи у меня одни.»",
            "Барти: «Давление проверяй раз в неделю. И пощупай внутри покрышки: осколок проколет новую камеру.»",
        ],
        mistake=[
            "Мартин: «Так, не тот инструмент. Мозги у зомби, видимо, тоже напрокат.»",
            "Барти: «Спокойно. Перечитай шаг. Медленно. Как я читаю старые завещания.»",
            "Мартин: «Ой. Ну, хоть нога на месте. Пока.»",
        ],
        good=[
            "Мартин: «Получилось! Ха! Руки помнят. Ну, теперь помнят.»",
            "Барти: «Браво! Мастер бы одобрил. Он одобрял молча, но ты бы почувствовал.»",
        ],
        test=["Мартин: «Ну что, колесо, держи воздух. Я на тебя рассчитываю.»",
              "Мартин: «Камера на месте, борт заправлен. Я почти механик.»"],
    ),

    # === Эльфийка Аэлин, Progeo Ego: флаттер кастора ===
    "caster": dict(
        intro=[
            "Аэлин: «На разгоне переднее колесо трясётся, как осиновый лист, и меня уводит в сторону.»",
            "Аэлин: «Через три дня забег по лесной трассе. С такой тряской до финиша ровно не доехать.»",
        ],
        worry=[
            "Аэлин: «Я сто лет езжу на этой раме. Ну, сто двенадцать. Она ещё ни разу не подводила.»",
            "Аэлин: «Только не перетяни, ладно? Колесо должно крутиться свободно, как ветер.»",
            "Аэлин: «На лесной трассе я слышу каждую шишку под колесом. А сейчас слышу только тряску.»",
            "Аэлин: «Сколько это займёт? Я хотела вечером ещё круг потренироваться.»",
        ],
        learn=[
            "Аэлин: «Волосы и грязь из оси кастора я вычищаю регулярно — иначе колесо не крутится свободно.»",
            "Аэлин: «Если перёд затрясся — сначала осматриваю, потом кручу. Причин у флаттера несколько.»",
            "Аэлин: «И ключ только точно по размеру. Слизанный болт потом высверливают — проходила.»",
        ],
        mistake=[
            "Аэлин: «Хм. Мой тренер сказал бы: остановись, вдохни, посмотри ещё раз.»",
            "Аэлин: «Ничего. На первом забеге я перепутала поворот. Сейчас смешно вспоминать.»",
            "Аэлин: «Осторожнее, пожалуйста. У меня забег через три дня!»",
        ],
        good=[
            "Аэлин: «Точно! Ты читаешь колесо, как я читаю трассу.»",
            "Аэлин: «Отличный ход. Чисто, без лишних движений — как хороший поворот.»",
            "Аэлин: «Вот это да. Я бы искала причину до самого забега.»",
        ],
        test=["Аэлин: «Разгонюсь до конца мастерской. Если не трясёт — ты мой лучший механик.»"],
    ),

    # === Оборотень Вольф, Quickie 2: тормоз-замок (до 23.10.2026 — гном Дургин) ===
    "brake": dict(
        intro=[
            "Вольф: «Ставлю коляску на тормоз на холме, засматриваюсь на луну — а она уже катится вниз. Без меня!»",
            "Вольф: «Через три дня полнолуние, вся стая соберётся на холме. Хочу стоять с ними, а не съезжать в овраг.»",
        ],
        worry=[
            "Вольф: «Не бойся, я не кусаюсь. Ну, разве что в полнолуние. Шучу! Почти.»",
            "Вольф: «Опять порвал джинсы на колене. Каждое превращение — новые джинсы. Разоряюсь.»",
            "Вольф: «Шерсть в колесо не набилась? Осень, я линяю.»",
            "Вольф: «Коляска у меня лёгкая, а я — нет. У её тормозов трудная жизнь.»",
        ],
        learn=[
            "Вольф: «Тормоз не держит — первым делом жму шину лапой. Спущенная шина уводит упор.»",
            "Вольф: «Отпущенный упор стоит в 3–6 мм от шины. Меньше — трёт, больше — не дожмёт.»",
            "Вольф: «Болты хомута тяни поочерёдно и не перетягивай, иначе замок станет туго включаться.»",
        ],
        mistake=[
            "Вольф: «Р-р-р... Это я не на тебя, это я на ключ. Не тот ключ, мастер.»",
            "Вольф: «Чую, не то. Нюх у меня волчий — и на ошибки тоже.»",
            "Вольф: «Ладно, ладно. Даже вожак стаи иногда сворачивает не туда.»",
        ],
        good=[
            "Вольф: «Вот! Сначала простое, потом сложное — так и стая охотится.»",
            "Вольф: «Ау-у! Это я от радости. Соседи привыкли.»",
            "Вольф: «Крепко сделано. Уважаю.»",
        ],
        test=["Вольф: «Зажимаю тормоз и наваливаюсь всем весом. Ну, коляска, не опозорь меня перед стаей!»"],
    ),

    # === Фея Тилли, Progeo Exelle Junior: спицы ===
    "spokes": dict(
        intro=[
            "Тилли: «Колесо дребезжит: дзынь-дзынь-брынь! И чуть-чуть виляет. Это плохо, да?»",
            "Тилли: «В субботу парад цветов, я везу корзинку с росой. Нельзя, чтобы всё расплескалось!»",
        ],
        worry=[
            "Тилли: «А спицы — это как струны у арфы? Можно я тоже послушаю?»",
            "Тилли: «Я не буду мешать. Посижу на верстаке. Тихонько. Почти не жужжа.»",
            "Тилли: «А ты правда зомби? А нога правда отваливается? Покажешь потом?»",
            "Тилли: «Мама говорит, я быстро езжу. А я говорю — я просто хорошо езжу!»",
        ],
        learn=[
            "Тилли: «Если колесо зазвенело по-новому — я сразу говорю взрослым. Мама так научила.»",
            "Тилли: «Карандашом по спицам: звонкий пинь — хорошо, глухой — спица ослабла!»",
            "Тилли: «Спицы тянут понемножку и все одинаково, а то колесо будет восьмерить.»",
        ],
        mistake=[
            "Тилли: «Ой! Ничего-ничего. Я вчера тоже росу пролила. Два раза.»",
            "Тилли: «Кажется, это не тот звук... Давай ещё разок послушаем?»",
            "Тилли: «Не волнуйся. Если что, я подую на колесо — феи так лечат. Шучу!»",
        ],
        good=[
            "Тилли: «Ура-а! Ты как настоящий колёсный волшебник!»",
            "Тилли: «Слышишь? Пинь! Красиво! Ещё так сделай!»",
            "Тилли: «Я хлопаю! Только ладошки маленькие, поэтому тихо.»",
        ],
        test=["Тилли: «Можно я сама покачу? Ну пожалуйста! Я осторожно, честно-честно!»"],
    ),

    # === Орк Гра, Progeo Noir 2.0: вой у заднего колеса (2 варианта) ===
    "bearing": dict(
        intro=[
            "Гра: «Колесо воет. Громко. Гра не любит громко.»",
            "Гра: «Гра ездит в библиотеку. В библиотеке тихо. Колесо — нет. Библиотекарь смотрит.»",
        ],
        worry=[
            "Гра: «Гра подождёт. Гра умеет ждать тихо.»",
            "Гра: «Мастер не будет стучать сильно? Гра просит. Гра вежливый.»",
            "Гра: «Гра пишет стихи. Про тишину. Хочешь, Гра прочитает? Потом.»",
            "Гра: «Это долго? Гра взял книгу. Толстую.»",
        ],
        learn=[
            "Гра: «Подшипник умирает — сначала поёт. Гра слышит песню — Гра едет к мастеру.»",
            "Гра: «Мойка с сильной водой — нельзя. Вода выбивает смазку. Гра моет тряпкой.»",
            "Гра: «Тормоз трёт шину — тоже воет. Гра смотрит зазор: от трёх до шести миллиметров.»",
        ],
        mistake=[
            "Гра: «Гм. Не то. Гра тоже ошибается. Один раз. Во вторник.»",
            "Гра: «Громкий звук. Гра закрыл уши. Попробуй ещё. Тише.»",
            "Гра: «Гра не сердится. Гра дышит. Мастер тоже дыши.»",
        ],
        good=[
            "Гра: «Хорошо. Гра кивает.»",
            "Гра: «Правильно. Мастер умный. Гра расскажет оркам.»",
            "Гра: «Гра доволен. Тихо доволен.»",
        ],
        test=["Гра: «Гра едет. Гра слушает. Если тихо — Гра улыбается.»"],
    ),

    # === Тролль Бомм, Invacare 9000 XDT: дырявая подушка ===
    "cushion": dict(
        intro=[
            "Бомм: «Подушка сдуваться. Бомм сидеть — и проваливаться. Бомм не любить.»",
            "Бомм: «Бомм сегодня ехать на мост. Мост сторожить. Долго сидеть — подушка нужна.»",
        ],
        worry=[
            "Бомм: «Таз с водой? Бомм не мыться. Бомм только смотреть.»",
            "Бомм: «Подушка — друг Бомма. Не делать ей больно, ладно?»",
            "Бомм: «Бомм видеть пузыри! Бомм любить пузыри!»",
            "Бомм: «Бомм сторожить мост сорок лет. Бомм знать каждого, кто ходить через мост. И как зовут его козу.»",
        ],
        learn=[
            "Бомм: «Бомм проверять рукой: под косточками таза палец воздуха. Меньше — плохо, будет болячка.»",
            "Бомм: «Много дуть тоже плохо. Подушка твёрдая — Бомм как на камне.»",
            "Бомм: «Заплатка лежать в коробке с подушкой. Бомм держать коробку дома.»",
        ],
        mistake=[
            "Бомм: «Ой. Бомм думать, это не так. Но Бомм не мастер.»",
            "Бомм: «Ничего. Бомм тоже путать. Бомм однажды сторожить не тот мост. Всю неделю.»",
            "Бомм: «Мастер грустный? Не грустить. Ещё раз.»",
        ],
        good=[
            "Бомм: «Хорошо! Бомм хлопать!»",
            "Бомм: «Мастер умный. Бомм дать камушек. Красивый.»",
            "Бомм: «Да! Так! Бомм радоваться!»",
        ],
        test=["Бомм: «Бомм садиться. Медленно. Подушка, держать Бомма!»"],
    ),

    # === Гоблин Зикс, Quantum Edge 4: лифт сиденья (2 варианта) ===
    "lift": dict(
        intro=[
            "Зикс: «Лифт бастует! Поднял сиденье за гайками — а вниз оно не едет. Ползу, как улитка!»",
            "Зикс: «Я его чуток улучшил. Ну, может, не чуток. Но улучшения же только помогают, да?»",
        ],
        worry=[
            "Зикс: «Мои улучшения только не выкидывай. Они дорогие. По моим меркам.»",
            "Зикс: «Можно я подержу фонарик? Я лучший держатель фонарика в квартале!»",
            "Зикс: «Зато сверху всё видно. Правда, в дверь я теперь не прохожу.»",
            "Зикс: «Пульт мне что-то говорит? Я думал, он просто красиво мигает.»",
        ],
        learn=[
            "Зикс: «Поднимаю сиденье только на ровном полу. На пандус и через порог — сиденье вниз.»",
            "Зикс: «Пульт подскажет: зелёный — можно, жёлтый — сиденье поднято, ползём, красный — блокировка.»",
            "Зикс: «Заводскую блокировку не обходят. Даже я. Это защита от опрокидывания.»",
        ],
        mistake=[
            "Зикс: «Ага! Значит, не я один тут улучшаю не туда!»",
            "Зикс: «Не переживай, я так каждый день делаю. Потом перечитываю инструкцию.»",
            "Зикс: «Хм. Дедушка сказал бы: прочитай шаг ещё раз и не трогай мой ящик.»",
        ],
        good=[
            "Зикс: «Ого! Ты прямо как я, только правильно!»",
            "Зикс: «Вот это механика! Запишу себе. На руку.»",
            "Зикс: «Ха! Надо было сразу к тебе ехать, а не улучшать.»",
        ],
        test=["Зикс: «Гайки, я вас достал! Теперь — вниз и за порог!»"],
    ),

    # === Чародейка Мора, Permobil M3 Corpus: джойстик и пыльник ===
    "joystick": dict(
        intro=[
            "Мора: «Попала под ливень. Теперь коляска дёргается, будто на неё навели порчу.»",
            "Мора: «Порчу я проверила первым делом. Чисто. Значит, ваша часть — механика.»",
        ],
        worry=[
            "Мора: «Вечером заседание ковена. Я не опаздываю. Никогда.»",
            "Мора: «Пыльник порван. Хотела зашить его заклинанием. Передумала.»",
            "Мора: «Аккуратнее с джойстиком. Он помнит мою руку лучше, чем мой фамильяр.»",
            "Мора: «Зомби-механик. Сёстры по ковену не поверят.»",
        ],
        learn=[
            "Мора: «Если промокла — сушу коляску в тепле около 12 часов. Только потом еду.»",
            "Мора: «Порванный пыльник меняю сразу: влага в электронике хуже любого проклятья.»",
            "Мора: «Простое делаю сама: перезагрузка, тряпка, разъём. Сложную электронику — технику.»",
        ],
        mistake=[
            "Мора: «Интересно. Я так однажды превратила чайник в жабу. Тоже не нарочно.»",
            "Мора: «Не торопись. Даже зелья не любят спешки.»",
            "Мора: «На твоём месте я бы перечитала шаг. А на своём — подожду.»",
        ],
        good=[
            "Мора: «Неплохо. Очень даже неплохо.»",
            "Мора: «Точно и без лишних движений. Тебе бы в алхимики.»",
            "Мора: «Даже мой ворон кивнул. А он редко кивает.»",
        ],
        test=["Мора: «Ну что ж, джойстик. Слушайся меня, как раньше. Без фокусов.»"],
    ),

    # === Голем Грунд, Drive Trident HD: свободный ход ===
    "freewheel": dict(
        intro=[
            "Грунд: «ГРУНД. ЕХАЛ. МОТОР. ВЫЛ. ТЯНУЛ. ВБОК. ПОТОМ. ТИШИНА.»",
            "Грунд: «ЗАВТРА. КАМЕНОЛОМНЯ. ГРУНД. НУЖЕН.»",
        ],
        worry=[
            "Грунд: «ГРУНД. ЖДЁТ. ГРУНД. ТЕРПЕЛИВЫЙ. СТО. ЛЕТ.»",
            "Грунд: «ЖЁЛТЫЕ. РЫЧАГИ. КРАСИВЫЕ. ГРУНД. ЛЮБИТ. ЖЁЛТЫЙ.»",
            "Грунд: «МАЛЕНЬКИЙ. ЗОМБИ. СИЛЬНЫЙ. ГРУНД. УВАЖАЕТ.»",
            "Грунд: «ПЫЛЬ. В. КОЛЁСАХ. ЭТО. ГРУНД. ГРУНД. ИЗВИНЯЕТСЯ.»",
        ],
        learn=[
            "Грунд: «СВОБОДНЫЙ. ХОД. ТОЛЬКО. ПИТАНИЕ. ВЫКЛ. ТОЛЬКО. РОВНО.»",
            "Грунд: «РЫЧАГИ. ВНИЗ. ТОРМОЗОВ. НЕТ. СТОЯТЬ. СБОКУ.»",
            "Грунд: «ПОТОМ. РЫЧАГИ. ВВЕРХ. ИНАЧЕ. НЕ. ТОРМОЗИТ.»",
        ],
        mistake=[
            "Грунд: «ГМ. НЕ. ТАК. ГРУНД. ЖДЁТ.»",
            "Грунд: «ГРУНД. ТОЖЕ. ПУТАЛ. РЫЧАГИ. ЛЕВЫЙ. ПРАВЫЙ.»",
            "Грунд: «ОСТОРОЖНО. МАЛЕНЬКИЙ. ЗОМБИ. ПЕРЕЧИТАЙ.»",
        ],
        good=[
            "Грунд: «ДА. ХОРОШО.»",
            "Грунд: «ГРУНД. ДОВОЛЕН. ОЧЕНЬ.»",
            "Грунд: «ЗОМБИ. МАСТЕР. ГРУНД. ГОВОРИТ.»",
        ],
        test=["Грунд: «ГРУНД. ГОТОВ. ПОЕХАЛИ.»"],
    ),

    # === Кицунэ Юки, TiLite Aero Z: замок на уклоне ===
    "aeroz_lock": dict(
        intro=[
            "Юки: «Ставлю коляску на замки у пандуса кофейни, пью кофе — а меня потихоньку уносит вниз!»",
            "Юки: «У меня куча доставок до обеда. Некогда догонять собственный кофе по пандусу!»",
        ],
        worry=[
            "Юки: «Быстрее, пожалуйста! Ой, прости. Курьерская привычка. Делай как надо.»",
            "Юки: «Я пока проложу маршрут. Три хвоста — три карты в голове.»",
            "Юки: «А манометр — это который с циферками? Мне такой нужен. В сумку.»",
            "Юки: «Если опоздаю, скажу, что меня задержал зомби. Это даже правда.»",
        ],
        learn=[
            "Юки: «Давление проверяю каждую неделю. На моей шине написано 90–110 psi.»",
            "Юки: «Замки — не тормоза! Ими не замедляются на спуске, они только держат стоящую коляску.»",
            "Юки: «Уклоны круче 10% мануал запрещает. Такие пандусы я объезжаю.»",
        ],
        mistake=[
            "Юки: «Ой-ой. Не спеши — это я тут обычно спешу.»",
            "Юки: «Ничего! Я однажды доставила торт не в тот замок. В смысле, в чужой дворец.»",
            "Юки: «Хвосты нервно дёрнулись. Давай ещё раз, спокойно.»",
        ],
        good=[
            "Юки: «Быстро и точно! Тебе бы курьером!»",
            "Юки: «Да-да-да! Виляю всеми тремя хвостами.»",
            "Юки: «Вот это скорость мысли. Уважаю.»",
        ],
        test=["Юки: «Ставлю на замки, откидываюсь назад... Только не уезжай, коляска!»"],
    ),

    # === Дриада Ивушка, Etac Cross 6: перекос спинки ===
    "cross6_back": dict(
        intro=[
            "Ивушка: «Простите, я тихо. Меня весь день тянет вбок: спинка с одной стороны проваливается.»",
            "Ивушка: «Вечером читательский час. Хочу сидеть ровно, а не клониться, как ива под ветром.»",
        ],
        worry=[
            "Ивушка: «Я подожду на скамье. Взяла книгу. Про ремонт колясок, кстати.»",
            "Ивушка: «Вы не шумите, всё хорошо. Я просто привыкла говорить шёпотом.»",
            "Ивушка: «У вашей мастерской книга о шинах просрочена на два века. Нет-нет, я не о штрафе.»",
            "Ивушка: «Это долго? Не тороплю. Просто корни затекают.»",
        ],
        learn=[
            "Ивушка: «Спинку сверяют рулеткой: от стойки до пластины подлокотника, с обеих сторон.»",
            "Ивушка: «Ремни обивки подстраивают, когда я сижу: сначала нижний, потом верхний.»",
            "Ивушка: «После любой регулировки проверяю антиопрокидыватели: опущены и защёлкнуты.»",
        ],
        mistake=[
            "Ивушка: «Ой. Ничего страшного. В библиотеке тоже иногда ставят книгу не на ту полку.»",
            "Ивушка: «Может, сверимся с инструкцией? Я всегда так делаю, когда сомневаюсь.»",
            "Ивушка: «Тише, тише. Никто не видел. Попробуйте ещё раз.»",
        ],
        good=[
            "Ивушка: «Как аккуратно. Будто страницу перевернули.»",
            "Ивушка: «Да, именно так. Я внесу это в каталог.»",
            "Ивушка: «Спасибо. Так и думала, что дело в стойке.»",
        ],
        test=["Ивушка: «Проеду между стеллажами. Если не потянет вбок — лучший день недели.»"],
    ),

    # === Дракончик Искра, Zippie Iris: наклон «клацает» ===
    "iris_tilt": dict(
        intro=[
            "Искра: «Когда кресло наклоняют, оно делает КЛАЦ! И ещё чуть-чуть проседает. Страшный звук!»",
            "Искра: «А ночью звездопад! Я хочу откинуться и смотреть. Без клаца.»",
        ],
        worry=[
            "Искра: «А зачем рулетка? Ты будешь меня мерить? Я выросла! На коготь!»",
            "Искра: «Мама, смотри, призрак! Он смешной. Он добрый? Он добрый.»",
            "Искра: «Я не буду дышать огнём, честно. Только если чихну.»",
            "Искра: «А почему колёсики сзади разные? Они поссорились?»",
        ],
        learn=[
            "Искра: «Когда кресло наклоняют, руки у меня на подлокотниках, а ноги на подножке. Я знаю!»",
            "Искра: «Мама каждую неделю проверяет тросы и колёсики сзади. А я помогаю — считаю!»",
            "Искра: «Механизм наклона маслом не мажут. Мама сказала. Даже драконьим.»",
        ],
        mistake=[
            "Искра: «Ой! Ничего, я вчера тоже перепутала левую лапу с правой.»",
            "Искра: «Хи-хи. Попробуй ещё! Как в игре — у тебя ещё есть жизни.»",
            "Искра: «Мама говорит: если не получилось, прочитай ещё раз, медленно.»",
        ],
        good=[
            "Искра: «Ура! Ты волшебник? Нет, ты механик! Это даже лучше!»",
            "Искра: «Здорово! А я так научусь, когда вырасту?»",
            "Искра: «Мама, он молодец! Скажи ему, что он молодец!»",
        ],
        test=["Искра: «Мама, держи меня за лапу. Сейчас откинемся... как звездочёт!»"],
    ),

    # === Бабушка Агата (сова), Ki Focus CR: трос наклона ===
    "focuscr_cable": dict(
        intro=[
            "Агата: «Угу. Внук жмёт курок, а кресло наклоняется рывками и потом само ползёт назад.»",
            "Агата: «Сегодня ночью соединение планет. Хочу встретить его под ровным углом, а не рывками.»",
        ],
        worry=[
            "Агата: «Я наблюдаю небо семьдесят лет. Уж за вами-то как-нибудь понаблюдаю.»",
            "Агата: «Внук хотел залить трос маслом из лавки. Я его остановила. Взглядом.»",
            "Агата: «Призрак, вы опять про телескоп? Я ещё ничего не сказала. Подозрительно.»",
            "Агата: «Не спешите, мастер. Звёзды ждут миллионы лет, подождут и меня.»",
        ],
        learn=[
            "Агата: «Трос наклона мы с внуком осматриваем каждую неделю: нет ли заломов и резких изгибов.»",
            "Агата: «Курок не оставляют зафиксированным открытым, когда в кресле сидят. Внук выучил.»",
            "Агата: «Никакого WD-40 и нефтяных растворителей. Мануал Ki это прямо запрещает.»",
        ],
        mistake=[
            "Агата: «Угу-у. Это как спутать Венеру с фонарём. Бывает с молодыми.»",
            "Агата: «Мастер, остановитесь и посмотрите ещё раз. Совы так делают всегда.»",
            "Агата: «Ничего. Я в молодости три ночи искала комету. Оказалось — пятно на линзе.»",
        ],
        good=[
            "Агата: «Угу! Точно, как по звёздной карте.»",
            "Агата: «Прекрасно. Записываю вас в созвездия. Пока карандашом.»",
            "Агата: «Вот это глаз. Почти совиный.»",
        ],
        test=["Агата: «Внучек, жми курок. Медленно. Посмотрим, как заходит наша луна.»"],
    ),

    # === Ящерка Сайра, WHILL Model C2: коды 01/02/10 (3 варианта) ===
    "whill_code": dict(
        intro=[
            "Сайра: «Включаю — красный номер на пульте, писк, и коляска сама гаснет. Утром ехала! Я записала!»",
            "Сайра: «Мне сегодня сдавать карту дюн в Гильдию картографов. Без коляски я не успею.»",
        ],
        worry=[
            "Сайра: «Можно я запишу, что ты делаешь? По пунктам. С датами. С зарисовками.»",
            "Сайра: «Песок пустыни у меня везде. В картах, в чешуе, в коляске. Особенно в коляске.»",
            "Сайра: «Код я, кстати, тоже записала. А таблицу кодов оставила дома. Иронично.»",
            "Сайра: «Тубус только не помни. Там три года работы. И один бутерброд.»",
        ],
        learn=[
            "Сайра: «Пульт протираю салфеткой с 70% спиртом. Водой можно мыть только колёса.»",
            "Сайра: «Подвижные части не смазываю: к смазке липнет песок. Только щётка и груша.»",
            "Сайра: «Задние шины у меня литые — их не качают. Но протектор я всё равно осматриваю.»",
        ],
        mistake=[
            "Сайра: «Стоп. Записываю: попытка номер два. Не переживай, у меня их бывает по двадцать.»",
            "Сайра: «Хм. В таблице было не так. Сверимся ещё раз?»",
            "Сайра: «Ничего. Я однажды нарисовала оазис там, где был мираж. Исправила.»",
        ],
        good=[
            "Сайра: «Совпадает с таблицей! Ставлю галочку.»",
            "Сайра: «Точно, аккуратно, по пунктам. Ты мне нравишься, мастер.»",
            "Сайра: «Записала: мастер прав. Подчеркнула дважды.»",
        ],
        test=["Сайра: «Включаю, не касаясь джойстика. Дисплей, ну же, покажи мне просто заряд!»"],
    ),

    # === Барсучиха Матильда, Permobil F5 Corpus: не заряжается после зимы ===
    "f5_charge": dict(
        intro=[
            "Матильда: «Всю зиму коляска стояла в сарае. Весной подключаю зарядку — а пульт тёмный!»",
            "Матильда: «Я всё делала по инструкции! А пчёлы просыпаются, ульи ждут осмотра.»",
        ],
        worry=[
            "Матильда: «Чаю? Мёду? Мёду с чаем? Нет, я не отвлекаю, я гостеприимна.»",
            "Матильда: «Инструкцию я выучила наизусть. Видимо, одну страницу не перевернула.»",
            "Матильда: «Пчёлы, не жужжите на мастера! Он хороший, он нас чинит.»",
            "Матильда: «Помощнику варежки дать? В сарае холодно, я знаю. Теперь знаю.»",
        ],
        learn=[
            "Матильда: «Перед зимой зарядить полностью и выключить главный автомат. Раз в месяц — подзарядить.»",
            "Матильда: «Хранить и заряжать — в сухом месте не холоднее +5 °C. Сарай не подходит. Записала.»",
            "Матильда: «Зарядку — сначала в гнездо коляски, потом в розетку. А пока заряжается, не едем.»",
        ],
        mistake=[
            "Матильда: «Ой. В инструкции, кажется, было не так. Давай я прочитаю вслух?»",
            "Матильда: «Ничего, ничего! Возьми мёду, с мёдом всё получается.»",
            "Матильда: «Пчёлы бы сказали: жжж. Это значит: попробуй ещё раз.»",
        ],
        good=[
            "Матильда: «Точно по инструкции! Ах, как приятно смотреть.»",
            "Матильда: «Мастер, вот это порядок! Как соты в рамке.»",
            "Матильда: «Отложу тебе баночку липового. Нет, две.»",
        ],
        test=["Матильда: «Зарядку отключили? Отключили. Тогда — круг по мастерской к банке мёда!»"],
    ),

    # ===================== Гильдия Колёсников =====================

    # === Т1. Правка «восьмёрки» (Аэлин) ===
    "truing": dict(
        intro=[
            "Аэлин: «На турнире я слишком лихо вошла в поворот. Обод теперь гуляет из стороны в сторону.»",
            "Бренна: «Колесо — в станок, руки — по регламенту. Промеры до правки, ниппели — понемногу.»",
        ],
        worry=[
            "Аэлин: «Скоро финал. Колесо должно быть круглым, как луна над лесом.»",
            "Бренна: «Не торопи его, эльфийка. Спешка в правке обода — это вторая восьмёрка.»",
            "Аэлин: «Тензиометр? Звучит как эльфийское ругательство.»",
            "Бренна: «Смотри на стрелку индикатора, а не на меня. Я и так знаю, что я строгая.»",
        ],
        learn=[
            "Аэлин: «После каждого турнира кручу колёса и смотрю на обод. Восьмёрку лучше поймать рано.»",
            "Бренна: «Не больше 1/4 оборота ниппеля за подход. Потом снова проверь биение.»",
            "Бренна: «Допуск биения — 1–2 мм. И натяжение соседних спиц сверяй тензиометром.»",
        ],
        mistake=[
            "Бренна: «Стоп. Порядок. Сначала промеры, потом руки. Я это уже говорила.»",
            "Аэлин: «Ничего. На тренировке первый круг всегда кривой. Второй — лучше.»",
            "Бренна: «Хм. В Гильдии за такое не выгоняют. Сразу.»",
        ],
        good=[
            "Бренна: «Годится. Аккуратно.»",
            "Аэлин: «Стрелка почти не дышит! Ты чувствуешь колесо.»",
            "Бренна: «Хорошо. Так работает техник, а не любитель.»",
        ],
        test=["Аэлин: «Крутани его в станке. Хочу увидеть, как стрелка стоит.»"],
    ),

    # === Т2. Замена пары батарей (Бренна) ===
    "t_battery": dict(
        intro=[
            "Бренна: «Экзаменационная коляска. Батареи четвёртый год не держат заряд. Меняешь пару.»",
            "Бренна: «Я смотрю. Внимательно. Не на тебя — на клеммы.»",
        ],
        worry=[
            "Бренна: «Болты клемм — в магнитную плошку. Не на верстак, не в карман.»",
            "Бренна: «Батареи тяжёлые. Поднимай из приседа. Спина у тебя одна, хоть и мёртвая.»",
            "Бренна: «Призрак, отойди от отсека. Ты сквозной, но мне так спокойнее.»",
            "Бренна: «Проговаривай порядок клемм вслух. Я хочу слышать.»",
        ],
        learn=[
            "Бренна: «Разборка: минус снимаешь первым. Сборка: плюс подключаешь первым.»",
            "Бренна: «Пару меняют только целиком: один тип, одна ёмкость, один возраст.»",
            "Бренна: «Первая зарядка новой пары — полная и только штатным зарядным устройством.»",
        ],
        mistake=[
            "Бренна: «Стоп. Ещё раз. Электрика прощает всё, кроме неуважения.»",
            "Бренна: «Хм. Это закончилось бы искрами. Хорошо, что я рядом.»",
            "Бренна: «Не тот инструмент. Посмотри на крепёж и подумай, что к нему подходит.»",
        ],
        good=[
            "Бренна: «Так.»",
            "Бренна: «Правильно. Дальше.»",
            "Бренна: «Хм. Неплохо. Не зазнавайся.»",
        ],
        test=["Бренна: «Включай. Смотрю на индикатор. И на тебя тоже.»"],
    ),

    # === Т3. Схождение (Кентавр Тавр) ===
    "toe": dict(
        intro=[
            "Тавр: «Коляску тянет вбок, резину ест. Колёса целы — проверял, честное копыто.»",
            "Бренна: «Курьеру нужна коляска, что едет прямо. Меряй, не гадай.»",
        ],
        worry=[
            "Тавр: «У меня посылки по всему лесу. Каждый день вбок — это лишний круг.»",
            "Тавр: «Можно я посмотрю, как ты меряешь? Хочу сам научиться.»",
            "Тавр: «Я трижды проверял колёса. Четвёртый раз — твой.»",
            "Бренна: «Рулетку держи ровно. Кривая рулетка — кривая правда.»",
        ],
        learn=[
            "Тавр: «Теперь знаю: тянет вбок — сначала давление в обеих шинах, потом схождение.»",
            "Бренна: «Замер между ободами спереди и сзади должен совпасть. Допуск — около 1 мм.»",
            "Бренна: «Болты пластины тяни крест-накрест. И после затяжки всегда перемеряй.»",
        ],
        mistake=[
            "Бренна: «Нет. Сначала исключи простое, потом трогай болты.»",
            "Тавр: «Ничего! Я тоже однажды отвёз посылку не в тот лес.»",
            "Бренна: «Перечитай шаг. Медленно. Я подожду. Недолго.»",
        ],
        good=[
            "Тавр: «Ровно, как просека! Отлично!»",
            "Бренна: «Цифры сошлись. Годится.»",
            "Тавр: «Вот это точность. Бью копытом от восторга!»",
        ],
        test=["Тавр: «Толкай! Покатится стрелой — с меня самая быстрая доставка.»"],
    ),

    # === Т. Quickie Pulse 6 + VR2 (Бренна) ===
    "t_pulse6": dict(
        intro=[
            "Бренна: «VR2 мигает двумя делениями. Это не заряд — это контроллер с тобой говорит.»",
            "Бренна: «Причину находим замером, а не догадкой. Контроллер на всякий случай не меняем.»",
        ],
        worry=[
            "Бренна: «Мультиметр на омы? Проверь, прежде чем мерить. Прибор тоже умеет врать.»",
            "Бренна: «Колпачок щёткодержателя пластиковый. Навалишься — сломаешь. Без усилия.»",
            "Бренна: «Щётки вынимай по одной. Запоминай, какой стороной стояла.»",
            "Бренна: «Призрак, не подсказывай. Твои подсказки я записываю в отдельный журнал.»",
        ],
        learn=[
            "Бренна: «Два быстро мигающих деления — левый мотор отключён. Одно — низкое напряжение.»",
            "Бренна: «Полная пара — около 25,6 В, разряженная — 24 В и ниже. Сначала заряд, потом мотор.»",
            "Бренна: «Щётка короче 1/4 дюйма, около 6 мм, — меняй в обоих моторах и обкатывай 20–30 минут.»",
        ],
        mistake=[
            "Бренна: «Стоп. Питание выключил? Проверь, что выключил.»",
            "Бренна: «Это догадка. Мне нужен замер.»",
            "Бренна: «Перечитай таблицу кодов. Деления считают, а не угадывают.»",
        ],
        good=[
            "Бренна: «Верно. Замер, а не догадка.»",
            "Бренна: «Хорошо. Так и дальше.»",
            "Бренна: «Хм. Почти мастерски. Почти.»",
        ],
        test=["Бренна: «Включай. Горит ровно? Тогда проверяю, в зацеплении ли редукторы.»"],
    ),

    # === Т. Quantum Q6 Edge + Q-Logic #203 (Бренна) ===
    "t_q6brake": dict(
        intro=[
            "Бренна: «Q-Logic пишет #203. Коляска стоит. Блок-схема производителя — от начала до конца.»",
            "Бренна: «Никакой самодеятельности. Каждый шаг — по схеме, каждый вывод — по замеру.»",
        ],
        worry=[
            "Бренна: «Кожух — на барашке и защёлках, отвёртка для него не нужна. Она понадобится для винтов модуля.»",
            "Бренна: «Разъём тяни за корпус, не за провода. Провода тебе не верёвка.»",
            "Бренна: «Модуль питания не натягивай. Он откидывается, а не отрывается.»",
            "Бренна: «Призрак, рычаги ногой не дёргают. Да, я тебя слышу.»",
        ],
        learn=[
            "Бренна: «Свободный ход на включённом питании — ошибка контроллера. Сначала выключи.»",
            "Бренна: «Тормоз — контакты 3–4, около 80 Ом. Обмотка мотора — 1–2, около 0,5–1,5 Ом.»",
            "Бренна: «Модуль питания меняют, только если оба тормоза показывают около 80 Ом.»",
        ],
        mistake=[
            "Бренна: «Ты сошёл с маршрута. Вернись к последнему шагу схемы.»",
            "Бренна: «Калибровать джойстик от тормозной ошибки? Нет. Подумай ещё.»",
            "Бренна: «Хм. Где рычаги свободного хода? Проверь, прежде чем лезть под кожух.»",
        ],
        good=[
            "Бренна: «По схеме. Правильно.»",
            "Бренна: «Хорошо. Замер подтверждает вывод.»",
            "Бренна: «Вот так работает техник Гильдии.»",
        ],
        test=["Бренна: «Ровная площадка, метр свободно вокруг. Слушаем щелчок тормоза в каждую сторону.»"],
    ),
}


FOLK_TALK = {
    "yaga_d100": dict(
        intro=["Баба Яга: «Здравствуй, касатик! Коляска моя катится сама — не хуже ступы, только без спросу.»",
               "Баба Яга: «Сиденье я подняла. Из окна избушки теперь всё видать — и тебя, и твои ошибки.»"],
        worry=["Баба Яга: «Избушка на курьих ножках ждёт. Скажи, мастер, долго ли ещё?»",
               "Баба Яга: «Метлу не трожь, она обидчивая. Тормоза — пожалуйста.»",
               "Баба Яга: «Триста лет летаю, а такой хитрой коляски не видала.»",
               "Барти: «Мартин, она смотрит на тебя, как на ужин. Работай быстрее.»"],
        learn=["Баба Яга: «Запомни, касатик: у D100 три высоты сиденья — 470, 500 и 530 мм.»",
               "Баба Яга: «Переставил колёса — переставь и вилки, чтобы стояли отвесно к полу.»",
               "Баба Яга: «Верхняя дырочка на пластине — для барабанного тормоза. Не для оси, понял?»"],
        mistake=["Баба Яга: «Ох, не то, касатик. В печку тебя не посажу, но запомню.»",
                 "Баба Яга: «Не та железка. Я в зельях разбираюсь, а ты — в ключах. Вроде бы.»"],
        good=["Баба Яга: «Вот это дело! Чаю с мухоморами хочешь? Шучу. Почти.»",
              "Баба Яга: «Ловко! В мои годы так только ступой управлялись.»"],
        test=["Баба Яга: «Ну, держитесь, леса и болота! Бабуля едет!»"],
    ),
    "olga_x3": dict(
        intro=["Ольга: «Привет! Я Ольга. Целый день на пляже — и колёсико хрустит, будто ест ракушки.»",
               "Ольга: «А ось заднего колеса залипла. Раньше снималась одной кнопкой.»"],
        worry=["Ольга: «Я бы помыла коляску сама, но я и есть солёная вода.»",
               "Ольга: «Завтра заплыв... то есть заезд по набережной. Успеем?»",
               "Ольга: «Хвост на подножке — моя любимая поза. Не трогай подножку, ладно?»",
               "Барти: «Русалка в мастерской! Мартин, только не урони гаечный ключ ей на хвост.»"],
        learn=["Ольга: «В мануале Panthera написано: после песка и соли чистить коляску чаще. Это прям про меня.»",
               "Ольга: «Шины — 8 бар. Мягкие — и тормоз не держит.»",
               "Ольга: «Быстросъёмную ось смазывают каплей масла, особенно после дождя, песка и соли.»"],
        mistake=["Ольга: «Ой, не то. Ничего, я тоже сначала плавала задом наперёд.»",
                 "Ольга: «Не тот инструмент! Как рыба без воды, честное слово.»"],
        good=["Ольга: «Ура! Ещё немного — и хрустеть перестанет. Музыка для моих ушей... то есть плавников.»",
              "Ольга: «Ты волшебник! Ну, или просто хороший механик.»"],
        test=["Ольга: «Ну, держись, пирс! Сейчас прокачусь с ветерком.»"],
    ),
    "leshy_x8": dict(
        intro=["Леший: «Здравствуй, мастер. Застрял я в трясине, жал-жал рычажок, а коляска замолчала.»",
               "Леший: «Остыла — поехала. Только тянет влево, будто в чащу зовёт.»"],
        worry=["Леший: «Лес без меня скучает. Белки уже, наверное, ёлки переставили.»",
               "Леший: «Трава в колёсах — это не я. Ну, может, немного я.»",
               "Леший: «Мох на мне — для красоты. А в моторе — не надо.»",
               "Барти: «Мартин, у него в бороде гриб! Съедобный? Не трогай, на всякий случай.»"],
        learn=["Леший: «Если застрял — не дави джойстик. Мотор перегреется, а моторы на ёлках не растут.»",
               "Леший: «Разное давление в шинах тянет коляску вбок. Вот почему я кружил по лесу.»",
               "Леший: «Гайки колёс X8 тянут на 47–50 Н·м. Не богатырской силой.»"],
        mistake=["Леший: «Не то, мастер. Даже я в лесу иногда тропинку путаю.»",
                 "Леший: «Хм. Ветка к ветке, ошибка к ошибке. Давай заново.»"],
        good=["Леший: «Вот это ладно. Лес кланяется тебе, мастер.»",
              "Леший: «Хорошо! Так и дерево растёт — по веточке.»"],
        test=["Леший: «Ну, тропа, держись. Прямо поедем, не кругами.»"],
    ),
    "ra_emotion": dict(
        intro=["Сенеб: «Не пугайся, мастер. Я мумия, но вполне бодрая. А вот мои колёса — нет.»",
               "Сенеб: «Огоньки мигают белым, колесо пищит четыре раза. Даже мой саркофаг так не скрипел.»"],
        worry=["Сенеб: «К закату у меня экскурсия по пирамиде. Колёса должны быть готовы.»",
               "Сенеб: «Пирамиды строили двадцать лет. Надеюсь, ты быстрее.»",
               "Сенеб: «Я ждал три тысячи лет — подожду и ещё. Но лучше не надо.»",
               "Барти: «Мартин, не тяни его за бинтик. Я так однажды распустил целого фараона.»"],
        learn=["Сенеб: «Колёса e-motion заряжают при 0…40 °C. Мне-то жара нипочём, а им — нет.»",
               "Сенеб: «У этих колёс нет своих тормозов. На стоянке — тормоза коляски.»",
               "Сенеб: «Если батарея загорится — не вода, а песок. Песка у меня в пустыне много.»"],
        mistake=["Сенеб: «Не то, мастер. Но и я однажды перепутал саркофаг с сундуком.»",
                 "Сенеб: «Хм. Мой амулет подсказывает: попробуй другой инструмент.»"],
        good=["Сенеб: «Достойно! Высеку твоё имя на стене гробницы. Мелким шрифтом.»",
              "Сенеб: «Превосходно. У меня от восторга бинты дыбом.»"],
        test=["Сенеб: «Мумия садится в коляску. Поехали!»"],
    ),
    "gorynych_jazzy": dict(
        intro=["Го: «Привет-привет! Мы Горыныч. Я Го, это Ры, а это Ныч. Он спит.»",
               "Ры: «Коляска встаёт в горку. Я сразу сказал: дело в сундуке. Меня никто не слушает.»"],
        worry=["Ныч: «Хр-р... А? Мы уже приехали? Разбудите, когда приедем.»",
               "Ры: «Сундук не трогать. Там наше золото. Ну, почти всё наше.»",
               "Го: «Ура, мастерская! Тут так интересно пахнет маслом!»",
               "Ры: «Три головы, а думать опять мне.»",
               "Ныч: «Мне снилось, что мы лёгкие, как пёрышко. Хороший был сон.»"],
        learn=["Ныч: «Зевая, скажу: предел веса Jazzy 614 — сто тридцать шесть кило. Хр-р...»",
               "Ры: «Автомат выбивает при перегрузке. Он нас бережёт, а не вредничает. Наверное.»",
               "Го: «Выбило автомат — ждём минутку и жмём кнопку! Я уже умею!»",
               "Ныч: «Пассажиров на коляске не возят. Даже если это твоя третья голова.»"],
        mistake=["Ры: «Я же говорил — не тот инструмент. Я всегда это говорю.»",
                 "Го: «Ничего-ничего! Попробуем другой, это весело!»",
                 "Ныч: «Хр-р... опять ошибка? Разбудите, когда будет правильно.»"],
        good=["Го: «Ура! Получилось! Можно я обниму мастера? Хотя бы одной головой!»",
              "Ры: «Хм. Неплохо. Даже придраться не к чему. Пока.»",
              "Ныч: «Ммм... правильно. Я проснулся ради этого. Ненадолго.»"],
        test=["Го: «Вперёд, к замку!» Ры: «Без сундука.» Ныч: «Тише, я сплю.»"],
    ),
}

CLIENT_TALK.update({j["id"]: FOLK_TALK[j["id"]] for j in _FOLK_ON})

BARTY_TALK = dict(
    idle=[
        "Барти: «Мастер проверял давление в шинах каждую неделю. По понедельникам. Или по пятницам. Но каждую!»",
        "Барти: «В осях передних колёс вечно волосы. Кто-то линяет. Не смотри на меня. Ладно, смотри.»",
        "Барти: «Электроколяску заряжают каждую ночь. Мастер говорил: батарея любит режим. Как и я.»",
        "Барти: «Пока коляска на зарядке, на ней не ездят. Многие и не дадут — блокировка. Мудрые машины.»",
        "Барти: «Свободный ход — только на ровном полу и при выключенном питании. Тормозов-то нет!»",
        "Барти: «Смазывают по мануалу, а не чем попало. WD-40 на всё подряд — это не забота, а паника.»",
        "Барти: «Мойка высокого давления выбивает смазку из подшипников. Тряпочка, друг мой, тряпочка.»",
        "Барти: «Я призрак уже двести лет. Или триста. Счёт теряешь, когда нет дней рождения.»",
        "Барти: «Замки — не тормоза. Мастер повторял это, как молитву. Я повторяю, как попугай.»",
        "Барти: «Батареи меняют парой. Как носки. Мне бы кто носки поменял.»",
        "Барти: «Чем пахнет мастерская? Смазкой и надеждой. Ну и капельку тобой.»",
        "Барти: «Порванный пыльник джойстика меняют сразу. Влага в электронике — прощай, плата.»",
        "Барти: «Я однажды пытался подержать гаечный ключ. Он упал сквозь меня. Неловко вышло.»",
        "Барти: «Антиопрокидыватели не снимают. Скучные, но спасают. Как я, только полезнее.»",
    ],
    mistake=[
        "Барти: «Ничего! Мастер тоже ошибался. Однажды. Во сне. Он мне рассказывал.»",
        "Барти: «Перечитай шаг ещё раз. Медленно. Я подожду, у меня вечность.»",
        "Барти: «Хм, глянь на то, что у тебя в руке. Оно точно для этого шага?»",
        "Барти: «Не переживай. Я за двести лет так и не научился держать отвёртку.»",
        "Барти: «Ой. Зато теперь мы знаем, как НЕ надо. Это тоже знание!»",
        "Барти: «Посмотри ещё раз на деталь. Что она тебе говорит? Мне — ничего, но я призрак.»",
        "Барти: «Кхм. Возможно, это я так подсказал. Возможно. Не будем выяснять.»",
        "Барти: «Сначала осмотр, потом ремонт. Это мастер говорил. Это я точно помню!»",
        "Барти: «Не беда. Коляска терпеливая. И клиент, кажется, тоже.»",
        "Барти: «Вдох-выдох. Ну, тебе выдох. Мне и вдох не нужен.»",
    ],
    good=[
        "Барти: «Браво! Брависсимо! Я бы аплодировал, но руки проходят друг сквозь друга.»",
        "Барти: «Вот! Именно так делал мастер! Ну, примерно. Ты даже точнее.»",
        "Барти: «Ты растёшь, Мартин. Как плесень, но в хорошем смысле.»",
        "Барти: «Великолепно! Записываю в летопись мастерской. Мысленно.»",
        "Барти: «Я горжусь тобой. Призраки редко гордятся. Это щекотно.»",
        "Барти: «Чисто сработано! Даже я не подсказал бы лучше. Особенно я.»",
        "Барти: «Ура! Где мой цилиндр? Хочу его подбросить.»",
        "Барти: «Ах, какой ровный ход! Почти как моё парение.»",
        "Барти: «Мастер сказал бы: недурно. А это у него высшая похвала.»",
        "Барти: «Великолепно, мой мёртвый друг! Великолепно!»",
    ],
    leg=[
        "Барти: «Мартин, твоя нога опять ушла без тебя. Может, у неё свои заказы?»",
        "Мартин: «Секунду. Нога закатилась под коляску. Зато я проверил: под коляской чисто.»",
        "Барти: «Не волнуйся, ногу я посторожу. Взглядом. Больше я ничего не умею.»",
        "Мартин: «Нога снова отвалилась. Надо и её по мануалу подтянуть.»",
        "Барти: «Твоя нога убежала к верстаку. Видимо, тоже хочет посмотреть на ремонт.»",
        "Мартин: «Нога, стой! Ну куда ты без меня? И куда я без тебя.»",
    ],
)


MARTIN_TALK = dict(
    good=[
        "Мартин: «Получилось! Не знал, что у меня золотые руки. Ну, зеленоватые.»",
        "Мартин: «Ха! Чувствую себя живым. Почти.»",
        "Мартин: «Вот это да. Я — механик. Кто бы мог подумать. Я — нет.»",
        "Мартин: «Ровно, чисто, по шагам. Мне нравится эта работа.»",
        "Мартин: «Ещё один довольный клиент. Сердце греет. Метафорически.»",
        "Мартин: «Ура! Так, нога на месте? На месте. Двойная радость.»",
    ],
    mistake=[
        "Мартин: «Ой. Мозг у меня, конечно, есть. Но, видимо, не весь.»",
        "Мартин: «Без паники. Зомби не паникуют. Зомби медленно перечитывают шаг.»",
        "Мартин: «Ну вот. Руки опять опередили голову.»",
        "Мартин: «Хорошо, что ошибся я, а не коляска на дороге. Исправляю.»",
        "Мартин: «Не тот инструмент. Барти, не смейся. Я слышу, как ты не смеёшься.»",
        "Мартин: «Ладно. Дважды отмерь, один раз прикрути. Записываю на ладонь.»",
    ],
)


class Game:
    def __init__(self, headless=False):
        self.headless = headless
        self.no_save = False              # --unlock (предпросмотр): прогресс в память, в save.json не писать
        self.ending_seen = False          # вечеринка уже показана — повтор задания ведёт в мастерскую
        self.scene = "title"
        self.t = 0.0
        # анимация: время входа в сцену, кадр для растворения, печать текста
        self.scene_t0 = 0.0
        self._scene_seen = None
        self._last_frame = None
        self._fade_from = None
        self._fade_t0 = 0.0
        self._typing = {}
        self.intro_idx = 0
        self.intro_slides = [
            ("Знакомься: Мартин", "Добродушный зомби, который вечно теряет левую ногу. "
             "Сегодня его позвали на вечеринку друзей."),
            ("Маленькая проблема", "Нога опять потерялась. Чтобы доехать, Мартин взял "
             "инвалидную коляску напрокат — и она сломалась прямо по дороге."),
            ("Мир ремонта тёмен и страшен", "«Как вообще их чинят?!» Информации ноль, "
             "вокруг — эльфы, гномы, магия, а руководства будто прокляты."),
            ("На помощь — призрак", "Бартоломью, прошлый хозяин коляски. Сам чинить толком "
             "не умел, но «видел, как делали мастера». Подсказывает... как получится."),
            ("Поехали", "Чини по-настоящему: правильные инструменты, верный порядок шагов. "
             "Барти иногда советует мимо — слушай инструкцию, а не только призрака."),
        ]
        # прогресс
        self.done = set()                 # id выполненных заданий
        self.garage = []                  # [(job_id, stars)]
        self.cur = None                   # текущее задание (dict)
        self.phase = "diagnose"           # diagnose | repair | test
        self.step_idx = 0
        self.sel_tool = None
        self.mistakes = 0
        self.toast = ""
        self.toast_timer = 0
        self.toast_color = WHITE
        self.ghost_line = ""
        self.last_note = ""
        self.result_gag = ""
        self.client_line = ""             # что сейчас говорит клиент (пузырь у портрета)
        self.client_t = 0.0
        self.client_next = 0.0            # когда клиент скажет следующую реплику сам
        self.client_queue = []            # реплики по порядку (приход клиента)
        self.ghost_quip = ""              # шутка Барти поверх подсказки (на несколько секунд)
        self.ghost_quip_until = 0.0
        self._talk_used = {}
        self._talk_n = 0
        # доступность: фокус клавиатуры, очередь озвучки, справка F1
        self.kb = dict(key=None, active=False, queue=[], sig=None, help=False, items=[],
                       client_seen="", quip_seen="", seat_seen="", group=None)
        # про-трек (Гильдия)
        self.done_steps = set()           # выполненные шаги tech-задания
        self.step_order = []              # порядок карточек-операций (перемешан)
        self.spec_pending = None          # шаг, ждущий значения из мануала
        self.show_manual = False
        self.manual_page = None
        self.manual_viewed = set()        # прочитанные страницы мануала
        self.fail_msg = ""
        self.mini_pending = None          # активная мини-интеракция
        self.exam_mode = False            # текущее задание — экзамен Гильдии
        self.exam_passed = False          # диплом Гильдии получен
        self.inspected = set()            # осмотренные детали (для допуска к диагнозу)
        self.esc_timer = 0.0              # двойной Esc — покинуть ремонт
        self.v3d = None                   # состояние 3D-осмотра (yaw/pitch/drag)
        self.show_sound = False           # панель «Звук» (громкость)
        self.dispute = None               # последняя засчитанная ошибка (для кнопки «Я не согласен»)
        self.dispute_ui = None            # открытое окно замечания
        self.feedback_mem = []            # headless/тесты: замечания не пишутся в файл
        self.seat_done = set()            # Кабинет посадки: решённые примерки
        self.seat_quiz_ok = False         # и сданный зачёт
        self.tutorial_skipped = False     # «Пропустить обучение»: всё открыто без первого ремонта
        self.seatc = None
        self.act = None                   # анимация инструмента на детали
        self.ride_t0 = None               # тест-драйв: клиент проезжает через экран
        self.ride_done = False            # проезд закончился — ждём «ГОТОВО» (успеть дочитать — отзыв игрока)
        self._vol_drag = None
        if not headless:
            self.load_progress()
            self.load_settings()

    # ---------- утилиты ----------
    def flash(self, text, color=WHITE, secs=3.0, sticky=False):
        """Сообщение сверху. sticky — итог хода (улика, шаг, ошибка): в задании держится, пока игрок что-нибудь не нажмёт."""
        self.toast = text
        self.toast_color = color
        self.toast_timer = max(secs, 2.5 + 0.07 * len(tr(text)))   # успеть прочесть: ~14 знаков в секунду + запас
        self.toast_sticky = sticky
        self.toast_t0 = self.t
        self.say(text, True)

    def _toast_input(self, event):
        """Игрок что-то нажал — итог прошлого хода уходит (новое сообщение, если будет, появится следом)."""
        if not getattr(self, "toast_sticky", False):
            return
        if event.type in (pygame.KEYDOWN, pygame.FINGERDOWN, pygame.JOYBUTTONDOWN, PAD_BTN_DOWN) or (
                event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) in (1, 2, 3)):
            self.toast_sticky = False
            self.toast_timer = min(self.toast_timer, 0.3)

    def miss(self, msg, secs=4.0):
        """Ошибка игрока: тост + счётчик; на экзамене следит за лимитом."""
        self.mistakes += 1
        snd("bad")
        self.flash(msg, BAD, secs, sticky=True)
        if not (self.dispute and self.dispute.get("t") == self.t):
            self.note_dispute("mistake", "", "", msg)
        self.react_mistake()
        self._exam_check()

    def note_dispute(self, kind, expected, got, msg):
        """Запомнить засчитанную ошибку — игрок может оспорить её кнопкой «Я не согласен»."""
        if not self.cur:
            return
        step = ""
        if self.phase == "repair" and self.cur.get("track") != "tech" and self.step_idx < len(self.cur.get("steps", [])):
            step = self.cur["steps"][self.step_idx]["instr"]
        elif self.cur.get("track") == "tech":          # Гильдия: что уже сделано — понять, о какой операции речь
            step = "сделано: " + ", ".join(str(s) for s in self.done_steps) if self.done_steps else "начало"
        self.dispute = dict(kind=kind, job=self.cur["id"], title=self.cur.get("title", ""), phase=self.phase,
                            variant=self.cur.get("_variant"),      # номер варианта поломки (caster, bearing, lift…)
                            step=step, expected=expected, got=got, msg=msg, t=self.t, sent=False, scene=self.scene)

    def _dispute_btn_rect(self):
        # в верхней панели, слева от ⚑: не закрывает «МАНУАЛ» Гильдии и заголовки правой колонки
        return pygame.Rect(WIDTH - 340, 10, 176, 34)

    def dispute_visible(self):
        d = self.dispute
        return bool(self.scene == "job" and d and not d["sent"] and self.cur and d["job"] == self.cur["id"]
                    and self.t - d["t"] < 25 and not self.dispute_ui and self.v3d is None and self.ride_t0 is None)

    FEEDBACK_REASONS = ["Неточность в картинке или 3D", "Ошибка в тексте или шагах", "Непонятно, что делать", "Другое"]

    def _feedback_rect(self):
        return pygame.Rect(WIDTH - 154, 8, 38, 38)

    BACK_SCENES = ("intro", "hub", "job", "guild", "garage", "seating", "result", "exam_result", "failed", "ending")

    def _top_back_rect(self):
        """Кнопка «◂ Назад» в левом верхнем углу = Esc (на iPad и телефоне клавиши нет)."""
        x = 60 if TOUCH["on"] else 8                    # на касаниях левый угол занят кнопкой ⛶ страницы
        return pygame.Rect(x, 8, 38, 38) if self.scene in self.BACK_SCENES else None

    def press_back(self):
        snd("tick")
        self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))

    def _draw_back_btn(self, surf):
        r = self._top_back_rect()
        if r is None:
            return
        back = tr("Назад").upper()
        if surf is CAPTURE["frame"] and not any(b["label"].strip(" ◂").upper() == back for b in CAPTURE["buttons"]):
            # пункт «Назад» для клавиатуры, геймпада и одной кнопки (если у сцены нет своей кнопки «НАЗАД»)
            CAPTURE["buttons"].append(dict(rect=pygame.Rect(r), label=tr("Назад"), sub="", enabled=True, active=False))
        hov = r.collidepoint(mouse_pos())
        h = _hover_amt(("backbtn",), 1.0 if hov else 0.0)
        aa_rect(surf, (30, 28, 40, int(170 + 80 * h)), r, border_radius=10)
        col = tuple(int(a + (b - a) * h) for a, b in zip(GHOST, AMBER))
        draw_text(surf, "◂", (r.centerx - 1, r.centery), 24, col, center=True, bold=True)
        if hov:
            tip = "Назад (Esc)"
            w = font(13).size(tr(tip))[0] + 16
            tr_ = pygame.Rect(r.x, r.bottom + 6, w, 24)
            aa_rect(surf, (18, 16, 24, 240), tr_, border_radius=6)
            draw_text(surf, tip, tr_.center, 13, WHITE, center=True)

    def open_feedback(self):
        """Флажок ⚑ на верхней панели: замечание о любой неточности, со снимком экрана."""
        shot = None
        if not self.headless:
            try:
                shot = pygame.display.get_surface().copy()
            except Exception:
                shot = None
        step = ""
        if self.scene == "job" and self.cur and self.phase == "repair" and self.cur.get("track") != "tech" \
                and self.step_idx < len(self.cur.get("steps", [])):
            step = self.cur["steps"][self.step_idx]["instr"]
        title = self.cur.get("title", "") if (self.scene == "job" and self.cur) else ""
        d0 = self.dispute
        self._pending_dispute = d0 if (d0 and d0.get("kind") != "general" and not d0.get("sent")) else None
        self.dispute = dict(kind="general", job=(self.cur["id"] if self.scene == "job" and self.cur else ""),
                            title=title, phase=(self.phase if self.scene == "job" else self.scene), step=step,
                            expected="", got="", msg="", t=self.t, sent=False, shot=shot, scene=self.scene)
        self.open_dispute()

    def open_dispute(self):
        self.dispute_ui = dict(reason=0, text="")
        try:
            pygame.key.start_text_input()
        except Exception:
            pass
        snd("tick")

    DISPUTE_REASONS = ["Мой вариант тоже правильный", "В игре ошибка или неточность", "Непонятно сформулировано"]

    def _dispute_panel_rect(self):
        return pygame.Rect(WIDTH // 2 - 340, HEIGHT // 2 - 274, 680, 548)

    def _reasons(self):
        return self.FEEDBACK_REASONS if (self.dispute and self.dispute["kind"] == "general") else self.DISPUTE_REASONS

    def _dispute_head(self):
        """Шапка окна «Я не согласен»: строки (текст, размер, цвет) и сдвиг вниз остального окна.
        Подсказка игры — до 4 строк целиком (это и есть то, с чем спорит игрок)."""
        d, p = self.dispute, self._dispute_panel_rect()
        w = p.w - 56
        rows = []
        if d["expected"] or d["got"]:
            rows += [("Игра ожидала: " + d["expected"], 14, GOOD, 2), ("Ты выбрал: " + d["got"], 14, BAD, 2)]
        rows.append(("Подсказка игры: " + d["msg"], 13, GREY, 4))
        h = sum(min(mx, len(wrap_lines(t, w, sz))) * (font(sz).get_height() + 2) + 2 for t, sz, _, mx in rows)
        dy = max(0, min(80, 58 + h - 150))           # не хватает места до «Почему не согласен?» — всё ниже
        return rows, dy

    def _dispute_dy(self):
        d = self.dispute
        return 0 if (not d or d["kind"] == "general") else self._dispute_head()[1]

    def _dispute_reason_rects(self):
        p = self._dispute_panel_rect()
        n = len(self._reasons())
        dy = self._dispute_dy()
        step = (42 if n <= 3 else 34) - (6 if dy > 40 else 0)
        return [(i, pygame.Rect(p.x + 28, p.y + 182 + dy + i * step, p.w - 56, step - 6)) for i in range(n)]

    def _dispute_text_rect(self):
        p = self._dispute_panel_rect()
        dy = self._dispute_dy()
        return pygame.Rect(p.x + 28, p.y + 340 + dy - (18 if dy > 40 else 0), p.w - 56, 78 - (12 if dy > 40 else 0))

    def _dispute_send_rect(self):
        p = self._dispute_panel_rect()
        return pygame.Rect(p.right - 228, p.bottom - 62, 200, 44)

    def _dispute_cancel_rect(self):
        p = self._dispute_panel_rect()
        return pygame.Rect(p.x + 28, p.bottom - 62, 160, 44)

    def close_dispute(self):
        self.dispute_ui = None
        if self.dispute:
            self.dispute["shot"] = None
        pend = getattr(self, "_pending_dispute", None)
        if pend is not None and self.dispute and self.dispute.get("kind") == "general":
            self.dispute = pend                       # вернуть ошибку, которую ещё можно оспорить
        self._pending_dispute = None
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass

    def send_dispute(self):
        """Сохранить замечание (feedback.json рядом с сохранениями) и не засчитывать спорную ошибку."""
        import datetime
        d, ui = self.dispute, self.dispute_ui
        entry = dict(time=datetime.datetime.now().isoformat(timespec="seconds"), lang=LANG["code"],
                     job=d["job"], title=d["title"], phase=d["phase"], step=d["step"], kind=d["kind"],
                     expected=d["expected"], got=d["got"], game_message=d["msg"],
                     reason=self._reasons()[ui["reason"]], comment=ui["text"].strip(), scene=d.get("scene", "job"))
        local_png = None
        if d.get("shot") is not None and not self.headless and not IS_WEB:
            try:
                fdir = os.path.join(DATA_DIR, "feedback_shots")
                os.makedirs(fdir, exist_ok=True)
                name = "shot_" + entry["time"].replace(":", "-") + ".jpg"   # JPEG: ~30 мс, PNG держал игру 0,4 с
                local_png = os.path.join(fdir, name)          # сам файл пишется в фоне (feedback_send)
                entry["screenshot"] = os.path.join("feedback_shots", name)
            except Exception:
                pass
        sent_online = False
        if not self.headless:
            sent_online = feedback_send(feedback_payload(entry), d.get("shot"), local_png)
        if self.headless:
            self.feedback_mem.append(entry)
        else:
            try:
                with open(FEEDBACK_PATH, encoding="utf-8-sig") as f:
                    data = json.load(f)
            except Exception:
                data = []
            if not isinstance(data, list):                # старый/испорченный файл — не падаем
                data = []
            data.append(entry)
            try:
                with _atomic_open(FEEDBACK_PATH) as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
            except Exception:
                pass
            web_persist(FEEDBACK_PATH)
        d["sent"] = True
        d["shot"] = None
        refunded = False
        if d["kind"] != "general" and not self.exam_mode and self.mistakes > 0:
            self.mistakes -= 1
            refunded = True
        self.close_dispute()
        snd("ok")
        self.flash(("Спасибо! Замечание отправляется разработчикам." if sent_online else
                    "Спасибо! Замечание сохранено — его проверят и поправят игру.")
                   + (" Эта ошибка не засчитана." if refunded else ""), GOOD, 5)

    def handle_dispute_event(self, event):
        ui = self.dispute_ui
        if event.type == pygame.TEXTINPUT:
            txt = "".join(ch for ch in event.text if ch.isprintable() and ch not in "​‌‍⁠﻿")
            if ui.pop("kd_space", False) and txt.startswith(" "):
                txt = txt[1:]                              # этот пробел уже добавлен по нажатию клавиши
            if len(ui["text"]) < 600:
                ui["text"] = (ui["text"] + txt)[:600]
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not (getattr(event, "mod", 0) & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
                # браузер не присылает TEXTINPUT для пробела (страница гасит пробел, чтобы не прокручиваться) —
                # пробел ставим по нажатию; если TEXTINPUT всё же придёт (компьютер), его пробел пропустим
                if len(ui["text"]) < 600:
                    ui["text"] += " "
                ui["kd_space"] = True
            elif event.key == pygame.K_ESCAPE:
                self.close_dispute()
            elif event.key == pygame.K_BACKSPACE:
                ui["text"] = ui["text"][:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.send_dispute()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._dispute_send_rect().collidepoint(event.pos):
                self.send_dispute()
            elif self._dispute_cancel_rect().collidepoint(event.pos) or \
                    not self._dispute_panel_rect().collidepoint(event.pos):
                self.close_dispute()
            else:
                for i, r in self._dispute_reason_rects():
                    if r.collidepoint(event.pos):
                        ui["reason"] = i
                        snd("tick")

    def _draw_feedback_flag(self, surf):
        r = self._feedback_rect()
        mouse = mouse_pos()
        hov = r.collidepoint(mouse)
        h = _hover_amt(("fbflag",), 1.0 if hov else 0.0)
        aa_rect(surf, (30, 28, 40, int(150 + 90 * h)), r, border_radius=10)
        col = tuple(int(a + (b - a) * h) for a, b in zip(GHOST, PURPLE))
        draw_text(surf, "⚑", r.center, 22, col, center=True)
        if hov:
            tip = "Сообщить о неточности"
            w = font(13).size(tr(tip))[0] + 16
            tr_ = pygame.Rect(r.right - w, r.bottom + 6, w, 24)
            aa_rect(surf, (18, 16, 24, 240), tr_, border_radius=6)
            draw_text(surf, tip, tr_.center, 13, WHITE, center=True)

    def _draw_dispute_btn(self, surf, mouse):
        if self.dispute_visible():
            Button(self._dispute_btn_rect(), "Я НЕ СОГЛАСЕН", PURPLE).draw(surf, mouse)

    def _draw_dispute_panel(self, surf, mouse):
        _cap_modal()
        ui, d = self.dispute_ui, self.dispute
        dim = _img_cache.get(("v3d_dim", 160, RS))
        if dim is None:
            dim = _img_cache[("v3d_dim", 160, RS)] = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((8, 8, 12, 160))
        surf.blit(dim, (0, 0))
        p = self._dispute_panel_rect()
        aa_rect(surf, (20, 18, 28), p, border_radius=14)
        aa_rect(surf, PURPLE, p, 2, border_radius=14)
        general = d["kind"] == "general"
        draw_text(surf, "СООБЩИТЬ О НЕТОЧНОСТИ" if general else "Я НЕ СОГЛАСЕН С ИГРОЙ", (p.x + 28, p.y + 20), 22, PURPLE, bold=True)
        y = p.y + 58
        if general:
            where = d["title"] or {"hub": "Мастерская", "garage": "Гараж", "guild": "Гильдия", "seating": "Кабинет посадки",
                                   "title": "Титул", "intro": "Вступление"}.get(d.get("scene"), d.get("scene", ""))
            draw_text(surf, "Где: " + where, (p.x + 28, y), 15, CYAN); y += 24
            if d["step"]:
                y = draw_wrapped(surf, "Шаг: " + d["step"], (p.x + 28, y), p.w - 56, 14, GREY, max_lines=2)
            draw_text(surf, "Снимок экрана приложится сам — опиши, что не так.", (p.x + 28, max(y, p.y + 110)), 14, GREY)
        else:
            rows, _ = self._dispute_head()
            for text, sz, col, mx in rows:               # полный текст — переносом, в пределах панели
                y = draw_wrapped(surf, text, (p.x + 28, y), p.w - 56, sz, col, max_lines=mx) + 2
        draw_text(surf, "Что не так?" if general else "Почему не согласен?",
                  (p.x + 28, self._dispute_reason_rects()[0][1].y - 26), 15, WHITE, bold=True)
        reasons = self._reasons()
        for i, r in self._dispute_reason_rects():
            Button(r, "", CYAN).draw(surf, mouse, active=i == ui["reason"])
            draw_text(surf, ("◉  " if i == ui["reason"] else "○  ") + reasons[i],
                      (r.x + 14, r.centery - font(16).get_height() // 2), 16, WHITE)
        tr_ = self._dispute_text_rect()
        draw_text(surf, "Опиши, что не так и как правильно" if general else "Как правильно, по-твоему? (можно не писать)",
                  (tr_.x, tr_.y - 22), 14, GREY)
        aa_rect(surf, (12, 12, 18), tr_, border_radius=8)
        aa_rect(surf, DIM, tr_, 1, border_radius=8)
        caret = "|" if int(self.t * 2) % 2 == 0 else " "   # погасший курсор держит место: пробел в конце виден
        lines = wrap_lines(ui["text"] + caret, tr_.w - 20, 15, raw=True)
        vis = max(1, (tr_.h - 12) // (font(15).get_height() + 2))   # сколько строк влезает (крупный текст — меньше)
        draw_wrapped(surf, " ".join(lines[-vis:]), (tr_.x + 10, tr_.y + 6), tr_.w - 20, 15, WHITE, raw=True)
        Button(self._dispute_cancel_rect(), "ОТМЕНА", GREY).draw(surf, mouse)
        Button(self._dispute_send_rect(), "ОТПРАВИТЬ", GOOD).draw(surf, mouse)

    def _exam_check(self):
        if self.exam_mode and self.mistakes > EXAM_MAX_MISTAKES and self.scene == "job":
            self.fail_msg = (f"Лимит ошибок экзамена исчерпан: {self.mistakes} при допустимых "
                             f"{EXAM_MAX_MISTAKES}. Бренна молча закрывает ведомость.")
            self.mini_pending = None
            self.spec_pending = None
            self.show_manual = False
            self._fail_zap = False
            snd("fail")
            self.scene = "failed"

    def job_by_id(self, jid):
        return next(j for j in ALL_JOBS if j["id"] == jid)

    _job_ids = frozenset(j["id"] for j in JOBS)     # id обычных заданий (без Гильдии); JOBS к этому месту полон

    def user_done_count(self):
        return len([j for j in JOBS if j["id"] in self.done])

    def tech_done_count(self):
        return len([j for j in TECH_JOBS if j["id"] in self.done])

    def guild_unlocked(self):
        return self.user_done_count() >= GUILD_REQ

    def load_settings(self):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
                data = json.load(f).get("volume", {})
            for k in ("master", "music", "sfx", "amb"):
                try:
                    if k in data:
                        v = float(data[k])
                        if math.isfinite(v):                   # NaN/inf в файле — оставляем как было
                            VOL[k] = max(0.0, min(1.0, v))
                except (TypeError, ValueError):
                    pass
            if "on" in data:
                VOL["on"] = bool(data["on"])
        except Exception:
            pass
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
                DISPLAY["glow"] = bool(json.load(f).get("glow", True))
        except Exception:
            pass
        apply_volume()
        lang = None
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
                lang = json.load(f).get("lang")
        except Exception:
            pass
        if "--lang" in sys.argv[:-1]:
            lang = sys.argv[sys.argv.index("--lang") + 1]
        set_lang("en" if IS_WEB else (lang or "en"))      # по умолчанию английский (аудитория); русский — переключателем
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
                acc = json.load(f).get("a11y")
        except Exception:
            acc = None
        if isinstance(acc, dict):
            if not acc.get("calm_set"):              # анимацию игрок не выключал сам — как в системе (ниже)
                acc = {k: v for k, v in acc.items() if k != "calm"}
            if not acc.get("text_set"):              # размер текста игрок не выбирал — берём текущий по умолчанию
                acc = {k: v for k, v in acc.items() if k != "text"}
            for k in A11Y:                           # старый/испорченный файл: неверный тип — оставляем значение по умолчанию
                v = acc.get(k)
                if isinstance(A11Y[k], bool):
                    if isinstance(v, bool):
                        A11Y[k] = v
                elif isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                    A11Y[k] = int(max(-10, min(10, v)))
        if not A11Y.get("calm_set"):
            A11Y["calm"] = system_reduced_motion()
        if not A11Y.get("speech_set") and screen_reader_running():   # NVDA/JAWS/Диктор — говорим, пока не выключили F2
            A11Y["on"] = True
        if "--speak" in sys.argv:
            A11Y["on"] = True
        if A11Y["on"]:
            SPEECH.init()

    def save_settings(self):
        if self.headless:
            return
        try:
            with _atomic_open(SETTINGS_PATH) as f:
                json.dump({"volume": dict(VOL), "lang": LANG["code"], "fullscreen": DISPLAY["fullscreen"],
                           "glow": DISPLAY["glow"], "res": list(DISPLAY["res"]) if DISPLAY["res"] else None,
                           "gpu3d": not GL["off"], "a11y": dict(A11Y),
                           "web_quality": DISPLAY.get("web_quality", "auto"),
                           "web_quality_user": bool(DISPLAY.get("web_quality_user"))},
                          f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        web_persist(SETTINGS_PATH)

    def load_progress(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            data = None
            print(f"[wnb] save.json не читается: {e!r}", flush=True)
        if not isinstance(data, dict):
            try:                                    # битый файл — отложить копию, прежде чем перезаписать
                with open(SAVE_PATH, "rb") as f, open(SAVE_PATH + ".bad", "wb") as g:
                    g.write(f.read())
            except Exception:
                pass
            return

        def lst(key):
            v = data.get(key, [])
            return v if isinstance(v, list) else []
        # каждое поле — отдельно, битые элементы пропускаем: одна ошибка не должна обнулять весь прогресс
        # народные задания (FOLK_JOBS) считаются известными, даже если их картинок сейчас нет на диске:
        # иначе их прогресс молча выпадал из сохранения и затирался при следующей записи
        valid = {j["id"] for j in ALL_JOBS} | {j["id"] for j in FOLK_JOBS}
        self.done = {j for j in lst("done") if isinstance(j, str) and j in valid}
        garage = []
        for e in lst("garage"):
            try:
                j, st_ = e
                if isinstance(j, str) and j in valid and j not in [g[0] for g in garage]:
                    garage.append((j, max(1, min(3, int(st_)))))
            except Exception:
                continue
        self.garage = garage
        self.exam_passed = data.get("exam_passed") is True
        ids = {c["id"] for c in SEAT_CASES}
        self.seat_done = {c for c in lst("seat_done") if isinstance(c, str) and c in ids}
        self.seat_quiz_ok = data.get("seat_quiz_ok") is True
        self.tutorial_skipped = data.get("tutorial_skipped") is True
        self.ending_seen = data.get("ending_seen") is True

    def save_progress(self):
        if self.headless or self.no_save:
            return
        try:
            with _atomic_open(SAVE_PATH) as f:
                json.dump({"done": sorted(self.done),
                           "garage": [[j, s] for j, s in self.garage],
                           "exam_passed": self.exam_passed,
                           "seat_done": sorted(self.seat_done), "seat_quiz_ok": self.seat_quiz_ok,
                           "tutorial_skipped": self.tutorial_skipped, "ending_seen": self.ending_seen},
                          f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[wnb] save.json не записан: {e!r}", flush=True)
            self.flash("Прогресс не сохранился: нет доступа к папке сохранений.", BAD, 4.0)
        web_persist(SAVE_PATH)

    def tutorial_ok(self):
        """Обучение пройдено (первый ремонт) или пропущено кнопкой."""
        return "flat" in self.done or self.tutorial_skipped

    def available_jobs(self):
        """Туториал (flat) первым; остальные открыты после него (или после «Пропустить обучение»)."""
        if not self.tutorial_ok():
            return ["flat"]
        return [j["id"] for j in JOBS]

    def _skip_tut_rect(self):
        """Кнопка «Пропустить обучение»: во вступлении — внизу справа, в первом задании — в верхней панели."""
        if self.scene == "intro":
            return pygame.Rect(WIDTH - 280, HEIGHT - 76, 250, 46)
        if (self.scene == "job" and self.cur and self.cur.get("id") == "flat" and not self.tutorial_ok()
                and not self.dispute_visible()):
            return pygame.Rect(WIDTH - 390, 9, 210, 36)
        return None

    def skip_tutorial(self):
        self.tutorial_skipped = True
        self.v3d = None
        self.mini_pending = self.spec_pending = None
        self.show_manual = False
        self.exam_mode = False
        self.esc_timer = 0
        self.save_progress()
        self.scene = "hub"
        snd("whoosh")
        self.flash("Обучение пропущено: все клиенты уже ждут. Коляску Мартина можно починить в любой момент.",
                   GOOD, 5)

    # ---------- запуск задания ----------
    def start_job(self, jid, variant=None):
        self.cur = resolve_job(self.job_by_id(jid), variant)
        shuffle_answers(self.cur)
        self._fail_zap = False
        tech = self.cur.get("track") == "tech"
        self.phase = "repair" if tech else "diagnose"
        self.step_idx = 0
        self.done_steps = set()
        self.step_order = [s["id"] for s in self.cur["steps"]] if tech else []
        if tech:
            random.shuffle(self.step_order)   # порядок карточек не подсказывает решение
        self.sel_tool = None
        self.mistakes = 0
        self.last_note = ""
        self.spec_pending = None
        self.show_manual = False
        self.manual_page = None
        self.manual_viewed = set()        # «сначала мануал» — заново в каждом задании (и на экзамене)
        self.dispute = None               # замечание к прошлой попытке к новой не относится
        self.esc_timer = 0                # «Esc ещё раз — выйти» из прошлого задания сюда не переносится
        self.mini_pending = None
        self.exam_mode = False
        self.inspected = set()
        self.v3d = None
        self.m3d = None                   # 3D прямо в окне диагностики (ракурс, перетаскивание)
        self.act = None
        self.ride_t0 = None
        self.ride_done = False
        self.ghost_line = self.cur.get("intro") or \
            "Бартоломью: «Так-так... осмотри детали и реши, что сломалось.»"
        self.ghost_quip = ""
        self.client_line = ""
        self.client_queue = list(self._talk().get("intro", []))
        self.client_next = self.t + 2.0           # клиент заговорит, когда сцена появится и осмотришься
        self._talk_later = None
        self._last_talk_t = -99.0
        self._quip_next = self.t + random.uniform(*self.QUIP_IDLE)
        self.scene = "job"

    # ---------- живые реплики: клиент волнуется, Барти шутит ----------
    CLIENT_IDLE = (22.0, 32.0)            # пауза между репликами клиента, с
    QUIP_IDLE = (35.0, 50.0)              # пауза между шутками Барти на диагностике
    TALK_GAP = 5.0                        # между любыми двумя репликами персонажей — не меньше, с (не говорят хором)

    def _talk(self):
        return CLIENT_TALK.get(self.cur["id"], {}) if self.cur else {}

    def _pick_line(self, key, lines):
        """Случайная реплика без повторов, пока пул не исчерпан."""
        if not lines:
            return ""
        used = self._talk_used.setdefault(key, [])
        left = [ln for ln in lines if ln not in used]
        if not left:
            used.clear()
            left = list(lines)
        line = random.choice(left)
        used.append(line)
        return line

    def _show_client(self, line):
        if not line:
            return
        self.client_next = self.t + random.uniform(*self.CLIENT_IDLE)
        self._last_talk_t = self.t
        if not barty_on() and line.startswith(("Барти", "Бартоломью")):
            return
        mentor = line.startswith(("Барти", "Бартоломью", "Бренна"))
        if self.cur.get("track") == "tech" or mentor:   # наставник (и клиент в Гильдии) — в пузыре наставника
            self.ghost_quip, self.ghost_quip_until = line, self.t + 7.0
            return
        self.client_line, self.client_t = line, self.t
        if not self.headless:
            snd("pop")

    def client_say(self, kind, chance=1.0):
        """Клиент говорит реплику из своего пула (intro/worry/learn/mistake/good/test)."""
        if not self.cur or random.random() > chance:
            return
        self._show_client(self._pick_line(("c", self.cur["id"], kind), self._talk().get(kind, [])))

    def barty_quip(self, kind, chance=1.0, secs=6.5):
        """Короткая шутка Барти поверх подсказки; потом подсказка шага возвращается."""
        if self.exam_mode or not barty_on() or quiet_talk() or random.random() > chance:
            return
        line = self._pick_line(("b", kind), BARTY_TALK.get(kind, []))
        if line:
            self.ghost_quip, self.ghost_quip_until = line, self.t + secs
            self._last_talk_t = self.t

    def react_mistake(self):
        if not self.cur or self.exam_mode or quiet_talk():
            return
        self.client_queue = []
        # реакция — не сразу: сначала игрок читает, что не так (сообщение сверху)
        if self.phase == "diagnose" and random.random() < 0.4:
            self._talk_later = (self.t + 1.2, "barty", "mistake")
        elif random.random() < 0.75:
            self._talk_later = (self.t + 1.2, "client", "mistake")

    def react_good(self):
        if not self.cur or self.exam_mode or quiet_talk():
            return
        r = random.random()                       # реже и с паузой: сверху и так «Шаг выполнен» и новая подсказка
        if r < 0.3:
            self._talk_later = (self.t + 1.8, "client", "good")
        elif r < 0.42:
            self._talk_later = (self.t + 1.8, "barty", "good")

    def talk_tick(self):
        """Клиент сам что-то говорит, пока ты работаешь: волнуется, болтает, делится советом."""
        if self.scene != "job" or not self.cur or self.ride_t0 is not None:
            return
        if self.phase not in ("diagnose", "repair", "test") or self.mini_pending or self.v3d is not None                 or self.dispute_ui is not None or getattr(self, "show_manual", False):
            return
        # не перебиваем свежее сообщение сверху; «висящий» итог хода (sticky) реплики не глушит дольше 3 с
        toast_fresh = self.toast_timer > 0 and (not getattr(self, "toast_sticky", False)
                                                or self.t - getattr(self, "toast_t0", -99.0) < 3.0)
        quiet = self.t - getattr(self, "_last_talk_t", -99.0) < self.TALK_GAP or toast_fresh
        if quiet_talk():                          # одна фраза при входе — и всё: ни болтовни, ни реакций
            self._talk_later = None
            if self.client_queue and self.t >= self.client_next and not quiet and not self.exam_mode:
                self._show_client(self.client_queue[0])
                self.client_queue = []
            return
        later = getattr(self, "_talk_later", None)
        if later and self.t >= later[0]:          # отложенная реакция на ход игрока
            if quiet:                             # не перебиваем реплику и сообщение сверху; устарела — молчим
                if self.t - later[0] > 8.0:              # (итог хода висит до нажатия — реакция ждёт дольше)
                    self._talk_later = None
                return
            self._talk_later = None
            if later[1] == "barty":
                self.barty_quip(later[2], secs=5.0)
            else:
                self.client_say(later[2])
            return
        if self.phase == "test":                  # перед проверкой — только отложенная реплика
            return
        if self.t >= self.client_next and not quiet:
            if self.client_queue and not self.exam_mode:   # на экзамене болтовни нет (и вступительных реплик тоже)
                self._show_client(self.client_queue.pop(0))
                self.client_next = self.t + 10.0
            elif not self.exam_mode:
                self._talk_n += 1
                self.client_next = self.t + random.uniform(*self.CLIENT_IDLE)
                self.client_say("learn" if self._talk_n % 2 == 0 else "worry")
        if self.phase == "diagnose" and not self.exam_mode and self.t >= getattr(self, "_quip_next", 0) \
                and not self.client_queue and not quiet:
            if getattr(self, "_quip_next", 0) > 0:
                self.barty_quip("leg" if random.random() < 0.3 else "idle", secs=8.0)
            self._quip_next = self.t + random.uniform(*self.QUIP_IDLE)

    def ghost_text(self):
        """Что показывает пузырь наставника: шутка Барти (если свежая) или подсказка."""
        if self.ghost_quip and self.t < self.ghost_quip_until:
            return self.ghost_quip
        return self.ghost_line

    def start_exam(self):
        """Экзамен Гильдии: случайный билет, без подсказок, лимит ошибок."""
        ticket = random.choice(TECH_JOBS)
        self.start_job(ticket["id"])
        self.exam_mode = True
        self.ghost_line = (f"Бренна: «Экзамен. Билет — „{ticket['title']}“. Мануал разрешён, "
                           f"подсказок не будет. Больше {EXAM_MAX_MISTAKES} ошибок — пересдача.»")

    # ---------- диагностика ----------
    def inspect_part(self, part_id):
        if self.phase != "diagnose":
            return
        if part_id in self.cur["parts"]:
            self.inspected.add(part_id)
        snd("inspect")
        clue = self.cur["inspect"].get(part_id, "Тут вроде всё в порядке.")
        self.flash(clue, CYAN, 4, sticky=True)

    def choose_diagnosis(self, idx):
        if len(self.inspected) < INSPECT_REQ:
            self.flash(f"Диагноз ставят по уликам: осмотри детали справа "
                       f"({len(self.inspected)}/{INSPECT_REQ}).", AMBER, 3)
            return False
        opt = self.cur["diagnosis"][idx]
        if opt["correct"]:
            self.phase = "repair"
            self.step_idx = 0
            self.sel_tool = None
            self.last_note = ""
            snd("ok")
            self.flash("Диагноз верный! Приступаем к ремонту.", GOOD, 3)
            self._set_step_ghost()
            self.client_queue = []
            self._talk_later = (self.t + 1.8, "client", "good")   # после сообщения сверху, не одновременно с ним
            return True
        else:
            self.mistakes += 1
            snd("bad")
            self.flash(opt["feedback"] or "Не похоже. Осмотри ещё раз.", BAD, 4)
            right = next((o["text"] for o in self.cur["diagnosis"] if o["correct"]), "")
            self.note_dispute("diagnosis", right, opt["text"], opt["feedback"] or "")
            self.react_mistake()
            return False

    # ---------- ремонт ----------
    def _set_step_ghost(self):
        if self.step_idx < len(self.cur["steps"]):
            self.ghost_line = self.cur["steps"][self.step_idx].get("ghost", "")
            # last_note (итог прошлого шага) не стираем: он виден строкой «✔ …» под инструкцией

    def select_tool(self, tool_id):
        self.sel_tool = tool_id
        snd(TOOL_SOUND.get(tool_id, "tool_metal"))
        self.say(f"В руке: {tr(TOOLS[tool_id][0])}", True)

    def do_action(self, tool_id, part_id):
        """Применить (инструмент, деталь) к текущему шагу. Возврат: 'ok' | 'wrong'."""
        if self.phase != "repair":
            return "wrong"
        step = self.cur["steps"][self.step_idx]
        if ((tool_id == step["tool"] or tool_id in step.get("alt_tools", ()))
                and (part_id == step["part"] or part_id in step.get("alt", ()))):
            if step.get("mini"):
                self.start_mini(step)
                return "mini"
            self.complete_base_step(step)
            return "ok"
        # ошибка
        self.mistakes += 1
        snd("bad")
        self.note_dispute("repair", f"{TOOLS[step['tool']][0]} → {PARTS.get(step['part'], step['part'])}",
                          f"{TOOLS.get(tool_id, (tool_id,))[0]} → {PARTS.get(part_id, part_id)}", step.get("wrongmsg", ""))
        self._start_action(tool_id, False, part=part_id)
        msg = step.get("wrongmsg", "")
        if step["tool"] == "eyes" and tool_id == "hands" and (part_id == step["part"] or part_id in step.get("alt", ())):
            msg = "Тут нужно посмотреть, а не трогать: возьми «Глаза»."
        elif step["tool"] == "hands" and tool_id == "eyes" and (part_id == step["part"] or part_id in step.get("alt", ())):
            msg = "Посмотрел — теперь нужно сделать руками: возьми «Руки»."
        if not msg:
            if tool_id != step["tool"] and part_id == step["part"]:
                msg = f"Деталь верная, но инструмент не тот. Нужен: {TOOLS[step['tool']][0]}."
            elif tool_id == step["tool"] and part_id != step["part"]:
                msg = f"Инструмент верный, но не та деталь. Цель: {PARTS[step['part']]}."
            else:
                msg = "Не то. Перечитай шаг и подсказку."
        self.flash(msg, BAD, 4)
        if self.dispute and self.dispute.get("t") == self.t:
            self.dispute["msg"] = msg
        self.react_mistake()
        return "wrong"

    def _act_pos(self, part=None, sid=None):
        """Экранная точка детали (хотспот на схеме, иначе строка списка) или карточки шага."""
        if sid is not None:
            for s_id, rect in self._op_rects():
                if s_id == sid:
                    return rect.midright[0] - 40, rect.centery
            return WIDTH // 2, 300
        for pid, x, y, r in self._chair_hotspots():
            if pid == part:
                return x, y
        for pid, rect in self._part_rects():
            if pid == part:
                return rect.x - 30, rect.centery
        return WIDTH // 2, 300

    def _start_action(self, tool, ok, part=None, sid=None):
        if sid is not None and part is None:
            part = next((st_.get("part") for st_ in self.cur.get("steps", []) if st_.get("id") == sid), None)
        zap = not ok and part in ELECTRIC_PARTS
        self.act = dict(tool=tool, ok=ok, pos=self._act_pos(part if sid is None else None, sid), t0=self.t,
                        ticks=0, zap=zap)
        if zap:
            snd("zap")

    def _draw_action(self, surf):
        a = self.act
        if not a or calm():
            self.act = None
            return
        dur = 0.95 if a["ok"] else (0.75 if a.get("zap") else 0.6)
        u = (self.t - a["t0"]) / dur
        if u >= 1:
            self.act = None
            return
        if a["ok"]:                                # звук работы инструмента по ходу анимации
            n = int(u * 6)
            if n > a["ticks"]:
                a["ticks"] = n
                if a["tool"] in ROT_TOOLS:
                    snd("ratchet")
                elif a["tool"] == "pump" and n % 2 == 0:
                    snd("hiss")
                elif a["tool"] == "pencil" and n in (2, 5):
                    snd("ping")
        draw_tool_action(surf, a["tool"], a["pos"], u, a["ok"], zap=a.get("zap", False))

    # ---------- шаги ремонта: посмотреть прошлый / пропустить текущий ----------
    def _step_prev_rect(self):
        return pygame.Rect(836, 58, 40, 30)

    def _step_skip_rect(self):
        return pygame.Rect(882, 58, 88, 30)

    def step_back(self):
        """«◂»: напомнить прошлый шаг (что сделали и зачем) — ремонт назад не откатывается."""
        snd("tick")
        if self.step_idx <= 0:
            self.flash("Это первый шаг.", GHOST, 2.5)
            return
        prev = self.cur["steps"][self.step_idx - 1]
        tool, part = TOOLS[prev["tool"]][0], PARTS.get(prev["part"], prev["part"])
        self.flash(f"{tr('Прошлый шаг')}: {tr(prev['instr'])} ({tr(tool)} → {tr(part)})"
                   + (f" ✔ {tr(prev['note'])}" if prev.get("note") else ""), CYAN, 7, sticky=True)

    def step_skip(self):
        """«Шаг ▸»: пропустить текущий шаг — игра показывает правильный инструмент и деталь и делает шаг сама.
        Пропуск = две ошибки (минус звезда): три звезды пропусками не получить."""
        if self.phase != "repair":
            return
        if self.cur.get("track") == "tech":
            self._tech_skip()
            return
        step = self.cur["steps"][self.step_idx]
        self.mini_pending = None
        self.mistakes += 2
        tool, part = TOOLS[step["tool"]][0], PARTS.get(step["part"], step["part"])
        self.complete_base_step(step)
        self.flash(f"{tr('Шаг пропущен — правильно')}: {tr(tool)} → {tr(part)}."
                   + (f" {tr(step['note'])}" if step.get("note") else ""), AMBER, 6, sticky=True)

    def _tech_skip_rect(self):
        return pygame.Rect(WIDTH - 384, 60, 170, 26)

    def _tech_skip(self):
        """Гильдия: пропустить одну операцию — ту, что можно делать сейчас (порядок и безопасность соблюдены).
        На экзамене пропускать нельзя."""
        if self.exam_mode:
            self.flash("На экзамене шаги не пропускаются.", AMBER, 3)
            return
        step = next((st for st in self.cur["steps"] if st["id"] not in self.done_steps
                     and all(a in self.done_steps for a in st["after"])), None)
        if step is None:
            return
        self.mini_pending = None
        self.mistakes += 2
        tool, part = TOOLS[step["tool"]][0], PARTS.get(step["part"], step["part"])
        ans = next((o[0] for o in step["spec"]["options"] if o[1]), "") if step.get("spec") else ""
        self.complete_tech_step(step)
        self.flash(f"{tr('Шаг пропущен — правильно')}: {tr(step['instr'])} ({tr(tool)})."
                   + (f" {tr(ans)}." if ans else "") + (f" {tr(step['note'])}" if step.get("note") else ""),
                   AMBER, 7, sticky=True)

    def complete_base_step(self, step):
        self._start_action(step["tool"], True, part=step["part"])
        self.last_note = step.get("note", "")
        snd("ok")
        self.flash("Шаг выполнен. " + (self.last_note or ""), GOOD, 4, sticky=True)
        self.step_idx += 1
        self.sel_tool = None
        if self.step_idx >= len(self.cur["steps"]):
            self.phase = "test"
            self.ghost_line = "Бартоломью: «Кажется, всё. Прокатим — проверим!»"
            self._talk_later = (self.t + 1.5, "client", "test")
        else:
            self._set_step_ghost()
            self.react_good()

    RIDE_SECS = 4.0                       # проезд после ремонта: успеть разглядеть клиента (было 2,3 с — «слишком быстро»)

    def start_ride(self):
        self.ride_t0 = self.t - (self.RIDE_SECS if calm() else 0)   # без анимации — проверка сразу, без проезда
        snd("whoosh")

    RIDE_FLIP = {"client_iris.png", "client_iris_mom.png", "client_f5.png"}   # портреты, где коляска смотрит влево

    def _draw_ride(self, surf):
        """Тест-драйв: клиент в своей коляске проезжает через мастерскую (слева направо — лицом вперёд)."""
        k = (self.t - self.ride_t0) / self.RIDE_SECS
        e = k * k * (3 - 2 * k)
        art = self.cur["client_art"]
        img = load_image(art, (230, 250), GHOST)
        if art in self.RIDE_FLIP:
            key = ("ride_flip", art, RS)
            if key not in _img_cache:
                _img_cache[key] = Surf.adopt(pygame.transform.flip(img, True, False), img.get_size())
            img = _img_cache[key]
        x = -260 + (WIDTH + 520) * e
        y = 290 - int(4 * abs(wsin(self.t * 18)))
        for i in range(6):                                  # линии скорости
            ly = y + 60 + i * 26
            ln = 60 + 40 * _h01(i, 3)
            DR.line(surf, (200, 200, 210), (x - 30 - ln - 20 * i % 50, ly), (x - 30 - 20 * i % 50, ly), 2)
        for i in range(4):                                  # пыль из-под колёс
            add_glow(surf, (x + 40 - i * 30, y + 240), 18, (80, 70, 55), 0.7 - 0.15 * i)
        blit_idle(surf, img, (x, y), self.t, rock=-3)

    def finish_test(self):
        snd("fanfare")
        if self.exam_mode:
            self.exam_passed = True
            self.save_progress()
            self.scene = "exam_result"
            return
        stars = max(1, 3 - self.mistakes // 2)
        self.done.add(self.cur["id"])
        old = next((i for i, g in enumerate(self.garage) if g[0] == self.cur["id"]), None)
        if old is None:
            self.garage.append((self.cur["id"], stars))
        elif stars > self.garage[old][1]:          # переигрывание: в гараже — лучшая оценка
            self.garage[old] = (self.cur["id"], stars)
        self.cur_stars = stars
        if random.random() < 0.5:                  # то нога отвалится, то Мартин сам себя похвалит/подколет
            self.result_gag = random.choice([g_ for g_ in LEG_GAGS if barty_on() or not g_.startswith("Бартоломью")])
        else:
            self.result_gag = random.choice(MARTIN_TALK["good" if self.mistakes == 0 else "mistake"])
        self.save_progress()
        self.scene = "result"

    # ---------- про-трек: свободный порядок, спеки, safety ----------
    def step_by_id(self, sid):
        return next(s for s in self.cur["steps"] if s["id"] == sid)

    def do_tech_action(self, tool_id, sid):
        """Попытка выполнить операцию tech-задания.
        Возврат: 'ok' | 'spec' | 'wrong' | 'fail' | 'done'."""
        step = self.step_by_id(sid)
        if sid in self.done_steps:
            self.flash("Этот шаг уже выполнен.", GREY, 2)
            return "done"
        missing = [s for s in step["after"] if s not in self.done_steps]
        for ms in missing:
            pre = self.step_by_id(ms)
            if pre["safety"]:
                self.fail_tech(step, pre)
                return "fail"
        if missing:
            pre = self.step_by_id(missing[0])
            # на экзамене «подсказок не будет» — не называем, какая операция должна быть раньше
            self.miss("Рано! Порядок операций нарушен." if self.exam_mode else
                      "Рано! Сначала: " + pre["instr"] + ".")
            return "wrong"
        if tool_id != step["tool"]:
            self._start_action(tool_id, False, sid=sid)
            self.miss("Инструмент не тот." if self.exam_mode else
                      f"Инструмент не тот. Нужен: {TOOLS[step['tool']][0]}.", 3.5)
            return "wrong"
        if step["spec"]:
            self.spec_pending = step
            if not self.exam_mode:
                self.ghost_line = "Бренна: «Стоп. Сначала цифры из мануала, потом руки.»"
            return "spec"
        if step.get("mini"):
            self.start_mini(step)
            return "mini"
        self.complete_tech_step(step)
        return "ok"

    def complete_tech_step(self, step):
        self._start_action(step["tool"], True, sid=step["id"])
        self.done_steps.add(step["id"])
        self.sel_tool = None
        self.spec_pending = None
        snd("ok")
        self.flash("Шаг выполнен. " + (step.get("note") or ""), GOOD, 4, sticky=True)
        if step.get("ghost") and not self.exam_mode:
            self.ghost_line = step["ghost"]
        if len(self.done_steps) >= len(self.cur["steps"]):
            self.phase = "test"
            self.ghost_line = ("Экзамен: сборка окончена. Финальная проверка." if self.exam_mode
                               else "Бренна: «Закончил? Слова дешёвые. Проверим под нагрузкой.»")
            if not self.exam_mode:
                self._talk_later = (self.t + 1.5, "client", "test")
        else:
            self.react_good()

    def choose_spec(self, idx):
        step = self.spec_pending
        if not step:
            return False
        spec = step["spec"]
        if spec["manual"] not in self.manual_viewed:
            self.flash("Сначала открой мануал и сверься со спецификацией.", AMBER, 3)
            return False
        text, correct, feedback = spec["options"][idx]
        if correct:
            self.complete_tech_step(step)
            return True
        self.miss(feedback or "Неверно. Перечитай мануал.")
        return False

    def fail_tech(self, step, pre):
        self.fail_msg = (f"Ты попытался: «{step['instr']}» — не выполнив шаг техники "
                         f"безопасности: «{pre['instr']}». " + (pre.get("failnote") or ""))
        self.spec_pending = None
        self.show_manual = False
        snd("fail")
        self._fail_zap = step.get("part") in ELECTRIC_PARTS or pre.get("part") in ELECTRIC_PARTS
        if self._fail_zap:
            snd("zap")
        self.scene = "failed"

    def open_manual(self, page=None):
        pages = (self.cur.get("manual") if self.cur else None) or list(MANUAL)
        self.manual_page = page or self.manual_page or pages[0]
        self.manual_viewed.add(self.manual_page)
        self.show_manual = True

    # ---------- мини-интеракции (pump / gap / ping / meter) ----------
    def start_mini(self, step):
        cfg = step["mini"]
        m = dict(step=step, kind=cfg["kind"], cfg=cfg)
        if cfg["kind"] == "pump":
            m["value"] = 0
        elif cfg["kind"] == "gap":
            m["value"] = cfg.get("start", cfg["mx"])
        elif cfg["kind"] == "ping":
            m["dull"] = set(random.sample(range(cfg["total"]), cfg["dull"]))
            m["tested"] = set()
        self.mini_pending = m

    def finish_mini(self):
        step = self.mini_pending["step"]
        self.mini_pending = None
        if self.cur.get("track") == "tech":
            self.complete_tech_step(step)
        else:
            self.complete_base_step(step)

    def mini_pump(self):
        m = self.mini_pending
        m["value"] += random.randint(6, 12)
        if m["value"] > m["cfg"]["mx"]:
            m["value"] = 0
            snd("pop")
            self.miss("БАБАХ! Перекачал сверх шкалы — камере конец, ставим новую. Заново.", 3.5)
        else:
            snd("hiss")
            cfg = m["cfg"]
            snd_pitch(m["value"] / cfg["mx"])
            zone = cfg["lo"] <= m["value"] <= cfg["hi"]
            self.say(f"{m['value']} {tr(cfg['unit'])}" + (", " + tr("зелёная зона") if zone else ""), True)

    def mini_release(self):
        """Перекачал — стравить немного через ниппель (без ошибки; ошибка — только если сдать с перекачкой)."""
        m = self.mini_pending
        if m["value"] <= 0:
            return
        m["value"] = max(0, m["value"] - random.randint(3, 6))
        snd("hiss")
        cfg = m["cfg"]
        zone = cfg["lo"] <= m["value"] <= cfg["hi"]
        self.say(f"{m['value']} {tr(cfg['unit'])}" + (", " + tr("зелёная зона") if zone else ""), True)

    def mini_pump_done(self):
        m = self.mini_pending
        cfg = m["cfg"]
        v = m["value"]
        if cfg["lo"] <= v <= cfg["hi"]:
            self.finish_mini()
        elif v < cfg["lo"]:
            self.miss(f"Мало ({v} {cfg['unit']}): докачай до зелёной зоны.", 3)
        else:
            m["value"] = max(0, cfg["lo"] - 25)
            self.miss(f"Перекачал ({v} {cfg['unit']}): стравили воздух, заново.", 3)

    def mini_gap_check(self):
        m = self.mini_pending
        cfg = m["cfg"]
        v = m["value"]
        if cfg["lo"] <= v <= cfg["hi"]:
            self.finish_mini()
        elif v < cfg["lo"]:
            self.miss(cfg.get("fb_lo", "Слишком мало."), 3.5)
        else:
            self.miss(cfg.get("fb_hi", "Слишком много."), 3.5)

    def mini_ping(self, idx):
        m = self.mini_pending
        if idx in m["tested"]:
            return
        m["tested"].add(idx)
        if idx in m["dull"]:
            snd("dull")
            found = len(m["dull"] & m["tested"])
            if found >= len(m["dull"]):
                self.finish_mini()
            else:
                self.flash(f"ТУК — глухая спица! Найдено {found}/{len(m['dull'])}.", CYAN, 2.5)
        else:
            snd("ping")
            self.flash("ПИНЬ — звонкая, натяжение в норме.", GREY, 1.6)

    def mini_meter(self, idx):
        m = self.mini_pending
        text, correct, feedback = m["cfg"]["options"][idx]
        if correct:
            self.finish_mini()
        else:
            self.miss(feedback or "Неверный вывод из замера.")

    # =========================================================== #
    #  ОБРАБОТКА ВВОДА
    # =========================================================== #
    # =========================================================== #
    #  ДОСТУПНОСТЬ: вся игра с клавиатуры + озвучка
    #  Пункты для фокуса берутся из прошлого кадра: кнопки (Button) и тексты, которые
    #  нарисовала сцена (CAPTURE), плюс особые элементы (детали, инструменты, ползунки…).
    # =========================================================== #
    A11Y_KEYS = [
        ("Стрелки", "выбрать пункт; влево-вправо двигают ползунок"),
        ("Tab, Shift+Tab", "следующая или предыдущая группа"),
        ("Enter, Пробел", "нажать (одна кнопка: нажать — выбрать, держать — назад)"),
        ("Esc", "назад или закрыть окно"),
        ("R", "повторить: где я и что делать"),
        ("T", "прочитать весь экран"),
        ("H", "подсказка призрака"),
        ("C", "что сказал клиент"),
        ("F1", "справка по клавишам"),
        ("F2", "озвучка: включить или выключить"),
        ("M", "звук: включить или выключить"),
        ("F11", "весь экран или окно"),
        ("Геймпад: крестовина", "выбрать пункт; LB, RB — группы"),
        ("Геймпад: A, B, Start", "нажать, назад, настройки"),
    ]

    def say(self, text, interrupt=False, raw=False):
        """В очередь озвучки; всё за кадр произносится одной фразой (в конце draw).
        raw=True — текст уже переведён / это текст игрока (не прогонять через tr)."""
        if text:
            self.kb["queue"].append((str(text) if raw else tr(str(text)), interrupt))

    # ---------- пункты для фокуса ----------
    def a11y_items(self):
        items = []

        def add(group, label, rect=None, act=None, adj=None, key=None, raw=False):
            items.append(dict(group=group, label=label, rect=pygame.Rect(rect) if rect else None,
                              act=act, adj=adj, key=key or (group, label), raw=raw))

        if self.kb["help"]:
            add("Справка", tr("Закрыть справку"), act=self.toggle_help, key="help")
            return items
        if self.dispute_ui is not None:
            ui = self.dispute_ui
            for i, r in self._dispute_reason_rects():
                add("Причина", tr(self._reasons()[i]) + (", " + tr("выбрано") if ui["reason"] == i else ""), r,
                    act=lambda i=i: (ui.__setitem__("reason", i), snd("tick")), key=("reason", i))
            add("Комментарий", tr("Комментарий: печатай текст, Enter — отправить") + (". " + ui["text"] if ui["text"] else ""),
                self._dispute_text_rect(), act=self.send_dispute, key="dtext", raw=True)
            add("Кнопки", tr("Отправить"), self._dispute_send_rect(), act=self.send_dispute, key="dsend")
            add("Кнопки", tr("Отмена"), self._dispute_cancel_rect(), act=self.close_dispute, key="dcancel")
            return items
        if self.show_sound:
            self._a11y_settings_items(add)
        elif self.scene == "job" and self.cur:
            self._a11y_job_items(add)
        elif self.scene == "title":
            add("Меню", tr("Продолжить игру" if self.done else "Начать игру"), act=lambda: self.click_title((0, 0)),
                key="start")
            add("Меню", tr("Титры"), self._credits_btn_rect(), act=self.open_credits, key="credits")
            add("Меню", tr("Поддержать GOAT (откроется PayPal)"), self._support_btn_rect(), act=self.open_support,
                key="support")
        elif self.scene == "credits":
            add("Меню", tr("Назад"), self._credits_back_rect(), act=self.close_credits, key="cback")
            add("Меню", tr("Поддержать GOAT (откроется PayPal)"), self._support_btn_rect(), act=self.open_support,
                key="support")
        elif self.scene == "intro":
            add("Меню", tr("Далее"), act=self._a11y_intro_next, key="next")
        elif self.scene == "hub":
            for jid, r in self._hub_job_rects():
                job = self.job_by_id(jid)
                note = (CLIENT_TALK.get(jid, {}).get("intro") or [""])[0]
                lab = (f"{tr(job['client'])}. {tr(job['title'])}. "
                       + tr("Электроколяска" if job.get("kind") == "power" else "Ручная коляска")
                       + (". " + tr("Уже починено") if jid in self.done else "")
                       + (". " + tr(note) if note and jid not in self.done else ""))
                add("Клиенты", lab, r, key=("job", jid))
            for d, r in self._hub_arrow_rects():
                add("Клиенты", tr("Следующая страница очереди" if d > 0 else "Предыдущая страница очереди"), r,
                    key=("page", d))
        elif self.scene == "ending":
            add("Меню", tr("Посмотреть гараж"), act=lambda: self.click_ending((0, 0)), key="garage")
            add("Меню", tr("Титры"), self._credits_btn_rect(), act=self.open_credits, key="credits")
            add("Меню", tr("Поддержать GOAT (откроется PayPal)"), self._support_btn_rect(), act=self.open_support,
                key="support")
        elif self.scene == "seating" and self.seatc:
            sc = self.seatc
            if sc["tab"] == "fit" and not sc["solved"]:
                case = SEAT_CASES[sc["case"]]
                checks, _ = self.seat_eval(case, sc["cfg"])
                for k, r in self._seat_slider_rects():
                    label, unit, lo, hi = SEAT_SLIDERS[k]
                    state = next((t for ck, ok, t in checks if ck == k), "")
                    add("Ползунки", f"{tr(label)}: {seat_val_text(k, sc['cfg'][k])}. {tr(state)}", r,
                        adj=lambda d, k=k: self._a11y_seat_adj(k, d), key=("seat", k))
        self._a11y_generic(items, add)
        if not (self.show_sound or self.dispute_ui is not None or self.mini_pending or self.show_manual
                or self.spec_pending or self.v3d is not None) and self.scene not in ("intro", "ending"):
            # на титуле тоже: незрячий игрок включает озвучку/язык до начала игры (мышью это работало и раньше)
            add("Меню", tr("Настройки: звук, графика, доступность"), self._speaker_rect(),
                act=self._a11y_open_settings, key="settings")
            if self.scene != "title":
                add("Меню", tr("Сообщить о неточности"), self._feedback_rect(), act=self.open_feedback, key="flag")
            if self.scene in ("title", "hub", "guild", "garage") and not IS_WEB:
                add("Меню", tr("Язык: русский. Переключить на английский") if LANG["code"] == "ru"
                    else "Language: English. Switch to Russian", self._lang_rect(), act=self.toggle_lang, key="lang")
        return items

    def _a11y_generic(self, items, add):
        """Кнопки, нарисованные в кадре (в модальном окне — только его), которых ещё нет в списке."""
        taken = [it["rect"] for it in items if it["rect"]]
        t0, b0 = CAPTURE["modal"] or (0, 0)
        texts = CAPTURE["texts"][t0:]
        for b in CAPTURE["buttons"][b0:]:
            r = b["rect"]
            if any(r.colliderect(x) for x in taken):
                continue
            lab = " ".join(x for x in (b["label"], b["sub"]) if x).strip()
            if not lab:                                   # пустая кнопка-карточка: подпись — текст внутри
                lab = ". ".join(t for tr_, t in texts if r.collidepoint(tr_.topleft))
            elif len(lab) <= 14:                          # «ВКЛ», «В ОКНЕ» — с подписью строки слева
                row = [t for tr_, t in texts if abs(tr_.centery - r.centery) < 22 and tr_.right <= r.x + 4]
                if row:
                    lab = row[-1] + ": " + lab
            if b["active"]:
                lab += ", " + tr("выбрано")
            if not b["enabled"]:
                lab += ", " + tr("недоступно")
            if lab:
                add("Кнопки", lab, r, key=("btn", tuple(r)))
                taken.append(r)

    def _a11y_job_items(self, add):
        job = self.cur
        tech = job.get("track") == "tech"
        if self.v3d is not None:
            add("3D", tr("Закрыть 3D-осмотр"), act=lambda: self.handle_v3d_event(
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")), key="v3dclose")
            return
        m = self.mini_pending
        if m:
            cfg = m["cfg"]
            if m["kind"] == "gap":
                add("Шкала", f"{tr(cfg.get('label', 'Значение'))}: {m['value']} {tr(cfg['unit'])}",
                    self._mini_gap_track(), adj=self._a11y_gap_adj, key="gap")
            elif m["kind"] == "ping":
                n = cfg["total"]
                for i, r in self._mini_ping_spots():
                    st = ""
                    if i in m["tested"]:
                        st = ", " + tr("глухая" if i in m["dull"] else "звонкая")
                    add("Спицы", f"{tr('Спица')} {_of(i + 1, n)}{st}", r, act=lambda i=i: self.mini_ping(i),
                        key=("spoke", i))
            elif m["kind"] == "meter":
                for i, r in self._mini_meter_rects():
                    add("Выводы", tr(cfg["options"][i][0]), r, act=lambda i=i: self.mini_meter(i), key=("meter", i))
            return
        if self.show_manual:
            for k, r in self._manual_page_rects():
                add("Страницы", tr(MANUAL[k][0]) + (", " + tr("открыта") if k == self.manual_page else ""), r,
                    act=lambda k=k: (setattr(self, "manual_page", k), self.manual_viewed.add(k)), key=("page", k))
            return
        if self.spec_pending:
            spec = self.spec_pending["spec"]
            viewed = spec["manual"] in self.manual_viewed
            for i, r in self._spec_option_rects():
                add("Варианты", tr(spec["options"][i][0]) + ("" if viewed else ", " + tr("закрыто: сначала мануал")),
                    r, act=lambda i=i: self.choose_spec(i) if viewed else self.flash(
                        "Сначала открой мануал и сверься со спецификацией.", AMBER, 3), key=("spec", i))
            return
        if self.phase == "diagnose" and not tech:
            unlocked = len(self.inspected) >= INSPECT_REQ
            for pid, r in self._part_rects():
                add("Детали", tr(PARTS[pid]) + (", " + tr("осмотрено") if pid in self.inspected else ""), r,
                    act=lambda pid=pid: self.inspect_part(pid), key=("part", pid))
            for i, r in self._diag_rects():
                add("Диагноз", f"{tr('Диагноз')} {i + 1}: {tr(job['diagnosis'][i]['text'])}"
                    + ("" if unlocked else ", " + tr("сначала осмотри детали")), r,
                    act=lambda i=i: self.choose_diagnosis(i), key=("diag", i))
        elif self.phase == "repair":
            if tech:
                for sid, r in self._op_rects():
                    st = self.step_by_id(sid)
                    add("Операции", tr(st["instr"]) + (", " + tr("выполнено") if sid in self.done_steps else ""), r,
                        act=lambda sid=sid: self._a11y_apply(sid=sid), key=("op", sid))
            for tid, r in self._tool_rects():
                add("Инструменты", tr(TOOLS[tid][0]) + (", " + tr("в руке") if tid == self.sel_tool else "")
                    + ". " + tr(TOOLS[tid][1]), r, act=lambda tid=tid: self.select_tool(tid), key=("tool", tid))
            if not tech:
                for pid, r in self._part_rects():
                    add("Детали", tr(PARTS[pid]), r, act=lambda pid=pid: self._a11y_apply(pid=pid), key=("part", pid))
                add("Шаги", tr("Напомнить прошлый шаг"), self._step_prev_rect(), act=self.step_back, key="stepprev")
                add("Шаги", tr("Пропустить шаг (минус звезда)"), self._step_skip_rect(), act=self.step_skip,
                    key="stepskip")
            elif not self.exam_mode:
                add("Шаги", tr("Пропустить шаг (минус звезда)"), self._tech_skip_rect(), act=self.step_skip,
                    key="stepskip")

    def _a11y_apply(self, pid=None, sid=None):
        if self.sel_tool is None:
            self.flash("Сначала выбери инструмент внизу.", AMBER, 2.5)
            self.kb["key"] = ("tool", next(iter(self.cur.get("tools") or TOOLS)))
            return
        if sid is not None:
            self.do_tech_action(self.sel_tool, sid)
        else:
            self.do_action(self.sel_tool, pid)

    def _a11y_settings_items(self, add):
        tab = getattr(self, "settings_tab", "sound")
        for t, r in self._settings_tab_rects():
            names = {"sound": "Вкладка: звук", "graphics": "Вкладка: графика", "access": "Вкладка: доступность",
                     "game": "Вкладка: игра и прогресс"}
            add("Вкладки", tr(names[t]) + (", " + tr("открыта") if t == tab else ""), r,
                act=lambda t=t: (setattr(self, "settings_tab", t), snd("tick")), key=("tab", t))
        if tab == "sound":
            names = {"master": "Общая громкость", "music": "Музыка", "sfx": "Эффекты", "amb": "Атмосфера сцен"}
            for k, r in self._vol_slider_rects():
                add("Громкость", f"{tr(names[k])}: {int(VOL[k] * 100)}%", r, adj=lambda d, k=k: self._a11y_vol(k, d),
                    key=("vol", k))
        elif tab == "access":
            for k, r in self._access_rects():
                add("Доступность", self._access_label(k), r, act=lambda k=k: self._access_toggle(k), key=("acc", k))

    # ---------- действия ----------
    def _a11y_intro_next(self):
        self.skip_typing("intro")
        self.click_intro((0, 0))

    def _a11y_open_settings(self):
        self.show_sound = True
        snd("tick")

    def _a11y_gap_adj(self, d):
        m = self.mini_pending
        cfg = m["cfg"]
        m["value"] = max(cfg["mn"], min(cfg["mx"], m["value"] + d))
        snd_pitch((m["value"] - cfg["mn"]) / max(1, cfg["mx"] - cfg["mn"]))

    def _a11y_seat_adj(self, k, d):
        sc = self.seatc
        sc["focus"] = k
        _, _, lo, hi = SEAT_SLIDERS[k]
        sc["cfg"][k] = max(lo, min(hi, sc["cfg"][k] + d))
        snd("ratchet")

    def _a11y_vol(self, k, d):
        VOL[k] = round(max(0.0, min(1.0, VOL[k] + 0.05 * d)), 2)
        apply_volume()
        snd("tick")

    def toggle_help(self):
        self.kb["help"] = not self.kb["help"]
        if self.kb["help"]:
            self.say(tr("Клавиши.") + " " + " ".join(f"{tr(k)}: {tr(v)}." for k, v in self.A11Y_KEYS)
                     + " " + tr("Esc — закрыть справку."), True)
        else:
            self.say("Справка закрыта.", True)

    def toggle_speech(self):
        A11Y["speech_set"] = True                     # выбор игрока важнее автоопределения чтеца
        if A11Y["on"]:
            SPEECH.say(tr("Озвучка выключена. F2 — включить."), True)
            A11Y["on"] = False
        else:
            A11Y["on"] = True
            SPEECH.init()
            SPEECH.set_voice()
            if not SPEECH.kind:
                self.flash("Озвучка недоступна на этом компьютере.", AMBER, 3)
            else:
                self.kb["sig"] = None                      # сразу рассказать, где мы
                self.say(tr("Озвучка включена.") + " " + tr("F1 — справка по клавишам."), True)
        self.save_settings()

    # ---------- клавиши ----------
    def a11y_key(self, ev):
        k = ev.key
        mod = getattr(ev, "mod", 0)
        if k == pygame.K_F1:
            self.toggle_help()
            return True
        if k == pygame.K_F2:
            self.toggle_speech()
            return True
        if self.kb["help"]:
            if k == pygame.K_F11:
                return False
            if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.toggle_help()
            return True
        typing = self.dispute_ui is not None              # в окне замечания буквы — это текст
        v3d = self.v3d is not None and self.scene == "job"
        shift = mod & pygame.KMOD_SHIFT
        if not typing and not (mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
            if k == pygame.K_r and not v3d:
                self.say(self.a11y_summary(full=True), True)
                return True
            if k == pygame.K_t:
                self.say(self.a11y_screen_text(), True)
                return True
            if k == pygame.K_h:
                line = self.ghost_text() if self.scene == "job" else ""
                self.say(line or "Подсказки сейчас нет.", True)
                return True
            if k == pygame.K_c:
                self.say(self.client_line or "Клиент пока молчит.", True)
                return True
        if v3d and k != pygame.K_RETURN:
            return False
        if self.scene == "credits" and k in (pygame.K_UP, pygame.K_DOWN):
            return False                                   # титры листаются стрелками (handle_credits_event)
        items = self.kb["items"]
        nav = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB,
               pygame.K_RETURN, pygame.K_KP_ENTER) + (() if typing else (pygame.K_SPACE,))
        if k not in nav or not items:
            return False
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER) and mod & pygame.KMOD_ALT:
            return False                                   # Alt+Enter — весь экран
        self.kb["active"] = True
        idx = next((i for i, it in enumerate(items) if it["key"] == self.kb["key"]), None)
        cur = items[idx] if idx is not None else None
        if k in (pygame.K_LEFT, pygame.K_RIGHT) and cur and cur["adj"]:
            cur["adj"](1 if k == pygame.K_RIGHT else -1)
            self.kb["say_focus"] = True                    # новое значение прочитаем после кадра
            return True
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if cur is None and typing:
                self.send_dispute()
                return True
            if cur is None and self.scene in ("intro", "title", "ending"):
                cur = items[0]                             # Enter: «далее» / «начать» / «гараж»; пропуск и титры — стрелкой
            if cur is None:
                if len(items) == 1:
                    cur = items[0]
                else:
                    self._a11y_focus(items[0], items)
                    return True
            self._a11y_activate(cur)
            return True
        if k == pygame.K_TAB:
            groups = []
            for it in items:
                if it["group"] not in groups:
                    groups.append(it["group"])
            g = groups.index(cur["group"]) if cur else -1
            g = (g + (-1 if shift else 1)) % len(groups)
            first = next(it for it in items if it["group"] == groups[g])
            self._a11y_focus(first, items)
            return True
        d = -1 if k in (pygame.K_UP, pygame.K_LEFT) else 1
        i = ((idx if idx is not None else (-1 if d > 0 else 0)) + d) % len(items)
        self._a11y_focus(items[i], items)
        return True

    def debug_state(self):
        """Где игра сейчас — коротко, для автопроверок браузерной версии (window.wnbState, art_tests/web_smoke.py)."""
        sc = self.seatc if self.scene == "seating" and self.seatc else {}
        return dict(scene=self.scene, job=self.cur["id"] if self.cur else None, phase=self.phase,
                    settings=bool(self.show_sound), dispute=self.dispute_ui is not None, help=bool(self.kb["help"]),
                    seat_tab=sc.get("tab"), focus=str(self.kb["key"]) if self.kb["key"] is not None else None,
                    res=list(DISPLAY.get("res") or ()), rs=round(RS, 3), touch=TOUCH["on"], lang=LANG["code"],
                    missing=sorted(ASSET_MISS)[:30], done=len(self.done), version=GAME_VERSION,
                    last_click=str(getattr(self, "_last_click", None)),
                    tt_frames=sum(len(t.frames) + len(t.scaled) for t in _TT_CACHE.values() if isinstance(t, Turntable)))

    # ---------- геймпад ----------
    def _pad_key(self, k, down=True, mod=0):
        self.handle_event(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=k, mod=mod, unicode=""))

    def pad_action(self, act, down):
        """Кнопка геймпада -> клавиша управления с клавиатуры."""
        if act == "added":
            self.flash("Геймпад подключён: крестовина — пункты, A — выбрать, B — назад, Start — настройки.", GOOD, 4)
            return
        if act in _PAD_DIR:
            k = _PAD_DIR[act]
            if down:
                PAD["dir"], PAD["next"] = act, self.t + PAD_REPEAT[0]
                self._pad_key(k)
            elif PAD["dir"] == act:
                PAD["dir"] = None
            return
        if act == "a":                                   # и нажатие, и отпускание (одна кнопка различает долгое)
            self._pad_key(pygame.K_RETURN, down)
            return
        if not down:
            return
        if act == "b":
            self._pad_key(pygame.K_ESCAPE)
        elif act == "x":
            self._pad_key(pygame.K_h)
        elif act == "y":
            self._pad_key(pygame.K_r)
        elif act in ("lb", "rb"):
            self._pad_key(pygame.K_TAB, mod=pygame.KMOD_SHIFT if act == "lb" else 0)
        elif act == "back":
            self._pad_key(pygame.K_F1)
        elif act == "start":
            if self.show_sound:
                self._pad_key(pygame.K_ESCAPE)
            elif self.dispute_ui is None and not self.kb["help"]:
                self._a11y_open_settings()

    def pad_tick(self):
        """Держат крестовину/стик — повтор стрелки."""
        d = PAD["dir"]
        if d is not None and self.t >= PAD["next"]:
            PAD["next"] = self.t + PAD_REPEAT[1]
            self._pad_key(_PAD_DIR[d])

    # ---------- одна кнопка (switch access): пункты выделяются сами, нажатие — выбрать, долгое — назад ----------
    _SCAN_KEYS = (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER)

    def _scan_iv(self):
        return SCAN_SPEEDS[max(1, min(len(SCAN_SPEEDS), A11Y.get("scan", 1))) - 1]

    def _scan_event(self, ev):
        if self.kb["help"] or getattr(self, "_scan_inject", False):
            return False
        down = (ev.type == pygame.KEYDOWN and ev.key in self._SCAN_KEYS) or \
               (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1)
        up = (ev.type == pygame.KEYUP and ev.key in self._SCAN_KEYS) or \
             (ev.type == pygame.MOUSEBUTTONUP and ev.button == 1)
        if down:
            if getattr(self, "_scan_down", None) is None:
                self._scan_down = self.t
            return True
        if up and getattr(self, "_scan_down", None) is not None:
            held = self.t - self._scan_down
            self._scan_down = None
            if held >= SCAN_HOLD:
                self.kb["scan_sub"] = None
                self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
            else:
                self.scan_select()
            self._scan_next = self.t + self._scan_iv() * 1.5
            return True
        return ev.type == pygame.MOUSEMOTION                # мышь фокус не сбивает

    def scan_select(self):
        """Нажатие одной кнопки: выбрать выделенный пункт (ползунок — меньше / больше / готово)."""
        items = self.kb["items"]
        if not items:
            return
        self.kb["active"] = True
        cur = next((it for it in items if it["key"] == self.kb["key"]), None)
        sub = self.kb.get("scan_sub")
        if sub and cur and cur["key"] == sub["key"]:
            if sub["i"] == 2:
                self.kb["scan_sub"] = None
                snd("tick")
                self.say(tr("Готово"), True)
            else:
                cur["adj"](-1 if sub["i"] == 0 else 1)
                self.kb["say_focus"] = True
            return
        self.kb["scan_sub"] = None
        if cur is None:
            self._a11y_focus(items[0], items)
            return
        if cur["adj"] and not cur["act"]:
            self.kb["scan_sub"] = dict(key=cur["key"], i=1)
            snd("tick")
            self.say(tr("Больше") + ". " + tr("Нажимай, чтобы менять. Меньше, больше, готово — по очереди."), True)
            return
        self._a11y_activate(cur)

    def scan_tick(self):
        """Раз в кадр: следующий пункт, когда пришло время."""
        if not A11Y.get("scan") or self.kb["help"] or getattr(self, "_scan_down", None) is not None:
            return
        items = self.kb["items"]
        if not items:
            return
        iv = self._scan_iv()
        if getattr(self, "_scan_next", None) is None:
            self._scan_next = self.t + iv
        if self.t < self._scan_next:
            return
        self._scan_next = self.t + iv
        self.kb["active"] = True
        sub = self.kb.get("scan_sub")
        if sub is not None:
            if any(it["key"] == sub["key"] for it in items):
                sub["i"] = (sub["i"] + 1) % len(SCAN_SUB)
                snd("tick")
                self.say(tr(SCAN_SUB[sub["i"]]), True)
                return
            self.kb["scan_sub"] = None
        idx = next((i for i, it in enumerate(items) if it["key"] == self.kb["key"]), None)
        self._a11y_focus(items[0 if idx is None else (idx + 1) % len(items)], items)

    def _draw_scan(self, surf, cur):
        """Одна кнопка: подсказка внизу и «меньше / больше / готово» у ползунка."""
        CAPTURE["mute"] += 1
        try:
            sub = self.kb.get("scan_sub")
            if sub and cur and cur["key"] == sub["key"] and cur["rect"] is not None:
                r = cur["rect"]
                w, h = 130, 34
                x0 = max(8, min(WIDTH - 3 * (w + 6) - 8, r.centerx - (3 * (w + 6)) // 2))
                y0 = r.bottom + 16 if r.bottom + 16 + h < HEIGHT - 30 else r.y - 16 - h
                for i, lab in enumerate(SCAN_SUB):
                    b = pygame.Rect(x0 + i * (w + 6), y0, w, h)
                    on = i == sub["i"]
                    aa_rect(surf, (52, 44, 20) if on else (20, 18, 26), b, border_radius=8)
                    aa_rect(surf, AMBER if on else GREY, b, 3 if on else 1, border_radius=8)
                    draw_text(surf, ("− ", "+ ", "✓ ")[i] + tr(lab), b.center, 16,
                              AMBER if on else WHITE, bold=on, center=True)
            hint = tr("Одна кнопка: нажми — выбрать, держи — назад")
            fw = font(14).size(hint)[0] + 24
            b = pygame.Rect(WIDTH // 2 - fw // 2, HEIGHT - 26, fw, 22)
            aa_rect(surf, (12, 10, 18), b, border_radius=6)
            draw_text(surf, hint, b.center, 14, AMBER, center=True)
        finally:
            CAPTURE["mute"] -= 1

    def _a11y_focus(self, it, items):
        self.kb["key"] = it["key"]
        n = [x for x in items if x["group"] == it["group"]]
        pos = f" ({_of(n.index(it) + 1, len(n))})" if len(n) > 1 else ""
        head = ""
        if it["group"] != self.kb.get("group"):
            head = tr(it["group"]) + ". "
            self.kb["group"] = it["group"]
        snd("tick")
        if it.get("raw"):                                  # подпись с текстом игрока — без перевода
            self.say(head, True)
            self.say(it["label"] + pos, True, raw=True)
        else:
            self.say(head + it["label"] + pos, True)

    def _a11y_activate(self, it):
        if it["act"]:
            it["act"]()
        elif it.get("adj"):                                # ползунок: значение меняют стрелками, Enter — повторить
            self.say(it["label"], True)
        elif it["rect"] is not None:                       # обычный клик в центр кнопки
            c = it["rect"].center
            self._scan_inject = True                       # свой клик — не нажатие «одной кнопки»
            try:
                self.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=c, button=1))
                self.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=c, button=1))
            finally:
                self._scan_inject = False
        self.kb["say_focus_if_same"] = it["key"]

    # ---------- что сказать ----------
    def a11y_screen_text(self):
        t0, b0 = CAPTURE["modal"] or (0, 0)
        texts = sorted(CAPTURE["texts"][t0:], key=lambda x: (x[0].y // 12, x[0].x))
        out = [t.strip().rstrip(".") for r, t in texts if t != tr("КОЛЁСА И КОСТИ") and t.strip(" .")]
        out += [b["label"] for b in CAPTURE["buttons"][b0:] if b["label"]]
        return ". ".join(out) or tr("На экране нет текста.")

    def a11y_summary(self, full=True):
        """Главное о текущем экране: где ты и что делать."""
        if self.kb["help"]:
            return tr("Справка по клавишам.")
        if self.dispute_ui is not None:
            d = self.dispute
            head = tr("Сообщить о неточности." if d and d["kind"] == "general" else "Я не согласен с игрой.")
            extra = ""
            if d and d.get("expected"):
                extra = f" {tr('Игра ожидала')}: {tr(d['expected'])}. {tr('Ты выбрал')}: {tr(d['got'])}."
            return (head + extra + " " + tr("Стрелки — выбрать причину, печатай комментарий, "
                                            "Enter — отправить, Esc — отмена."))
        if self.show_sound:
            tab = getattr(self, "settings_tab", "sound")
            if tab == "game":
                return (tr("Настройки.") + " " + tr("Игра.") + " " + " ".join(tr(x) + "." for x in self.progress_summary())
                        + " " + tr("Tab — к вкладкам и пунктам, Esc — закрыть."))
            return tr("Настройки.") + " " + tr({"sound": "Звук.", "graphics": "Графика.", "access": "Доступность."}[tab]) \
                + " " + tr("Tab — к вкладкам и пунктам, Esc — закрыть.")
        sc = self.scene
        if sc == "title":
            return (tr("Колёса и Кости. Обучающий симулятор ремонта инвалидных колясок.") + " "
                    + tr("Enter — начать. F1 — справка по клавишам, F2 — озвучка."))
        if sc == "intro":
            idx = min(self.intro_idx, len(self.intro_slides) - 1)
            title, text = self.intro_slides[idx]
            return f"{tr(title)}. {tr(text)} " + tr("Enter — далее.")
        if sc == "credits":
            return (tr("Титры.") + " " + " ".join(tr(h) + ". " + " ".join(tr(x) for x in lines) for h, lines in CREDITS)
                    + " " + tr("Esc — назад."))
        if sc == "hub":
            return (f"{tr('Мастерская.')} {tr('Починено')}: {_of(self.user_done_count(), len(JOBS))}. "
                    + tr("Стрелки — выбрать клиента, Enter — взять заказ, Tab — другие разделы."))
        if sc == "job" and self.cur:
            return self._a11y_job_summary(full)
        if sc == "result" and self.cur:
            stars = getattr(self, "cur_stars", 3)
            return (f"{tr('Готово!')} {tr('Звёзд')}: {_of(stars, 3)}. {tr(self.cur['thanks'])} "
                    f"{tr('Что ты узнал')}: {tr(self.cur['fact'])} {tr(self.result_gag)} " + tr("Enter на кнопке — дальше."))
        if sc == "seating" and self.seatc:
            return self._a11y_seat_summary(full)
        return self.a11y_screen_text()

    def _a11y_job_summary(self, full):
        job = self.cur
        tech = job.get("track") == "tech"
        if self.v3d is not None:
            return tr("3D-осмотр коляски. Esc — закрыть.")
        m = self.mini_pending
        if m:
            cfg = m["cfg"]
            out = tr(m["step"]["instr"]) + ". " + tr(cfg.get("hint") or cfg.get("prompt") or "")
            if m["kind"] == "pump":
                out += f" {tr('Сейчас')}: {m['value']} {tr(cfg['unit'])}. " + tr(
                    "Нужно попасть в зелёную зону") + f": {cfg['lo']}–{cfg['hi']} {tr(cfg['unit'])}. " + tr(
                    "Enter на «Качать» — подкачать, «Стравить» — выпустить лишнее, потом «Готово».")
            elif m["kind"] == "gap":
                out += f" {tr('Допуск')}: {cfg['lo']}–{cfg['hi']} {tr(cfg['unit'])}. " + tr(
                    "Стрелки влево-вправо — значение, потом «Проверить».")
            elif m["kind"] == "ping":
                out += " " + tr("Простукивай спицы по очереди и слушай: звонкая — в норме, глухая — ослабла.")
            elif m["kind"] == "meter":
                out += f" {tr('Прибор показывает')}: {tr(cfg['reading'])}. {tr(cfg.get('sub', ''))}"
            return out
        if self.show_manual and self.manual_page:
            title, lines = MANUAL[self.manual_page]
            return f"{tr('Мануал')}. {tr(title)}. " + " ".join(tr(x) for x in lines)
        if self.spec_pending:
            spec = self.spec_pending["spec"]
            return tr(spec["prompt"]) + ("" if spec["manual"] in self.manual_viewed else
                                         " " + tr("Сначала открой мануал — варианты откроются."))
        voices = A11Y["voices"]
        if tech:
            if self.phase == "repair":
                out = f"{tr('Выполнено')}: {_of(len(self.done_steps), len(job['steps']))}."
                if full:
                    out = (f"{tr(job['title'])}. {tr(job['symptom'])} " + out + " "
                           + tr("Порядок шагов выбираешь сам: выбери инструмент, потом операцию. "
                                "Значения — из мануала."))
                return out + (" " + tr(self.ghost_line) if voices and self._ghost_audible() else "")
            return (tr("Проверка под нагрузкой.") + " " + tr(job["test"]) + " "
                    + tr("Проверка пройдена. Enter на кнопке ГОТОВО — к итогу." if self.ride_done
                         else "Enter на кнопке — прокатить и проверить."))
        if self.phase == "diagnose":
            out = (f"{tr(job['title'])}. {tr('Клиент')}: {tr(job['client'])}. "
                   f"{tr('Коляска')}: {tr(job.get('chair_name', ''))}. {tr(job['symptom'])} "
                   + tr("Осмотри детали, минимум две, потом выбери диагноз. Tab — переход между группами."))
            return out
        if self.phase == "repair":
            n = len(job["steps"])
            step = job["steps"][min(self.step_idx, n - 1)]
            out = f"{tr('Шаг')} {_of(self.step_idx + 1, n)}: {tr(step['instr'])}"
            if full:
                out += " " + tr("Выбери инструмент, потом деталь.")
            if voices and self._ghost_audible():
                out += " " + tr(self.ghost_line)
            return out
        return (tr("Тест-драйв.") + " " + tr(job["test"]) + " "
                + tr("Проверка пройдена. Enter на кнопке ГОТОВО — к итогу." if self.ride_done
                     else "Enter на кнопке — прокатить и проверить."))

    def _ghost_audible(self):
        """Подсказку наставника озвучиваем по тому же правилу, что и рисуем пузырь:
        реплики Барти при «Призрак Барти: выкл» не читаются (Бренна и Мортимер — читаются)."""
        return bool(self.ghost_line) and (barty_on() or self._speaker_img(self.ghost_line) != "ghost.png")

    def _a11y_seat_summary(self, full):
        sc = self.seatc
        if sc["tab"] == "lessons":
            les = SEAT_LESSONS[sc["lesson"]]
            return (f"{tr('Кабинет посадки. Урок')}: {tr(les['title'])}. " + " ".join(tr(x) for x in les["points"]))
        if sc["tab"] == "fit":
            case = SEAT_CASES[sc["case"]]
            b = case["body"]
            return (f"{tr('Примерка')}: {tr(case['client'])}. {tr(case['story'])} "
                    f"{tr('Карта терапевта')}: {tr(case['therapist'])} "
                    f"{self._seat_measure_text(case)}. "
                    + tr("Двигай ползунки стрелками влево-вправо, потом «Проверить посадку»."))
        if sc["quiz_done"]:
            return f"{tr('Зачёт')}: {_of(sc['score'], len(SEAT_QUIZ))}."
        q = SEAT_QUIZ[sc["quiz"]]
        pic = (" " + tr(q["desc"])) if q.get("desc") else ""
        return f"{tr('Вопрос')} {_of(sc['quiz'] + 1, len(SEAT_QUIZ))}: {tr(q['q'])}{pic}"

    def _a11y_sig(self):
        sc = self.seatc if self.scene == "seating" and self.seatc else {}
        return ((self.scene, self.cur and self.cur["id"], self.phase, self.mini_pending is not None,
                 self.show_manual, self.spec_pending is not None, self.show_sound, self.dispute_ui is None,
                 self.v3d is None, self.kb["help"], sc.get("tab"), sc.get("case"), sc.get("lesson"),
                 sc.get("quiz"), sc.get("quiz_done")),
                (self.step_idx, len(self.done_steps), getattr(self, "intro_idx", 0), self.manual_page,
                 getattr(self, "settings_tab", "sound"), getattr(self, "hub_page", 0)))

    # ---------- раз в кадр: фокус, автоозвучка, рамка ----------
    def a11y_frame(self, surf):
        items = self.a11y_items()
        self.kb["items"] = items
        sig = self._a11y_sig()
        old = self.kb["sig"]
        if sig != old:
            big = old is None or sig[0] != old[0]
            self.kb["sig"] = sig
            if big:
                self.kb["group"] = None
                if not any(it["key"] == self.kb["key"] for it in items):
                    self.kb["key"] = None
            self.say(self.a11y_summary(full=big))
        if A11Y["voices"] and self.scene == "job":        # реплики персонажей — вслух, в очередь
            if self.client_line and self.client_line != self.kb["client_seen"]:
                self.say(self.client_line)
            if self.ghost_quip and self.ghost_quip != self.kb["quip_seen"] and self.t < self.ghost_quip_until:
                self.say(self.ghost_quip)
        self.kb["client_seen"], self.kb["quip_seen"] = self.client_line, self.ghost_quip
        if self.scene == "seating" and self.seatc:
            say_ = self.seatc.get("say") or ""
            if A11Y["voices"] and say_ != self.kb["seat_seen"]:
                self.say(say_)
            self.kb["seat_seen"] = say_
        cur = next((it for it in items if it["key"] == self.kb["key"]), None)
        if self.kb.pop("say_focus", False) and cur:       # ползунок сдвинули — новое значение
            self.say(cur["label"], True, raw=cur.get("raw", False))
        same = self.kb.pop("say_focus_if_same", None)
        if same is not None and cur and cur["key"] == same and not self.kb["queue"]:
            self.say(cur["label"], True, raw=cur.get("raw", False))                   # нажали, а экран не изменился — что теперь на кнопке
        if self.kb["active"] and cur and cur["rect"] is not None and self.kb["help"] is False:
            r = cur["rect"].inflate(12, 12) if cur["rect"].h > 12 else cur["rect"].inflate(24, 30)
            pulse = 0.5 + 0.5 * wsin(self.t * 5)
            aa_rect(surf, (0, 0, 0), r.inflate(10, 10), 3, border_radius=13)
            aa_rect(surf, (255, 255, 255), r, 3, border_radius=10)
            aa_rect(surf, AMBER, r.inflate(6, 6), 3 + int(pulse), border_radius=12)
        if A11Y.get("scan") and not self.kb["help"]:
            self._draw_scan(surf, cur)
        q = self.kb["queue"]
        if q:
            SPEECH.say(" ".join(t for t, _ in q), any(i for _, i in q))
            q.clear()

    def _draw_help(self, surf):
        _cap_modal()
        dim = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((6, 6, 10, 215))
        surf.blit(dim, (0, 0))
        p = pygame.Rect(WIDTH // 2 - 380, 50, 760, 620)
        aa_rect(surf, (24, 22, 32), p, border_radius=12)
        aa_rect(surf, AMBER, p, 2, border_radius=12)
        draw_text(surf, "УПРАВЛЕНИЕ С КЛАВИАТУРЫ", (p.x + 28, p.y + 20), 24, AMBER, bold=True)
        y = p.y + 66
        room = p.bottom - 84 - y                          # строки — над «Озвучкой» и «Esc — закрыть»
        for sz in (17, 16, 15, 14, 13):                   # крупный шрифт — мельче, но всё в рамке
            step = font(sz).get_height() + 6
            if step * len(self.A11Y_KEYS) <= room:
                break
        step = min(33, max(step, room // len(self.A11Y_KEYS)))
        kw = 210
        for k, v in self.A11Y_KEYS:
            fit_text(surf, k, (p.x + 28, y), kw - 12, sz, CYAN, bold=True)
            fit_text(surf, v, (p.x + 28 + kw, y), p.right - 24 - (p.x + 28 + kw), sz, WHITE)
            y += step
        st = f"Озвучка: {'включена' if A11Y['on'] else 'выключена'} ({SPEECH.label()})"
        draw_text(surf, st, (p.x + 28, p.bottom - 74), 15, GOOD if A11Y["on"] else GREY)
        draw_text(surf, "Esc или F1 — закрыть", (p.x + 28, p.bottom - 44), 15, GREY)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._last_click = (tuple(int(v) for v in event.pos), self.scene, round(self.st, 2))
        self._toast_input(event)
        if event.type in PAD_EVENTS:
            for act, down in pad_actions(event) or ():
                self.pad_action(act, down)
            return
        if A11Y.get("scan") and self._scan_event(event):
            return
        if event.type == pygame.MOUSEMOTION:
            self.kb["active"] = False                     # мышь — рамку фокуса прячем
        if event.type == pygame.KEYDOWN and self.a11y_key(event):
            return
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_F11 or (
                event.key == pygame.K_RETURN and getattr(event, "mod", 0) & pygame.KMOD_ALT)):
            if not self.headless and not IS_WEB:           # в браузере размер холста задаёт страница
                toggle_fullscreen()
                self.save_settings()
            return
        if self.kb["help"] and event.type in (pygame.MOUSEBUTTONDOWN, pygame.TEXTINPUT):
            if event.type == pygame.MOUSEBUTTONDOWN:     # справка F1 модальна и поверх окна замечания:
                self.toggle_help()                       # клик — закрыть её, а не «Отправить» под ней
            return                                       # буквы при открытой справке в комментарий не идут
        if self.dispute_ui is not None:                  # окно замечания модально (и ловит ввод текста):
            self.handle_dispute_event(event)             # буквы, в т.ч. «m»/«ь», — это текст, а не горячие клавиши
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            on = toggle_sound()
            self.save_settings()
            self.flash("Звук включён" if on else "Звук выключен (M — включить)", GHOST, 1.8)
            return
        if self.show_sound:                              # панель настроек модальна (⚑ и «Я не согласен» — под ней)
            self.handle_sound_event(event)
            return
        if self.scene == "credits" and self.handle_credits_event(event):
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.dispute_visible()
                and self._tap(self._dispute_btn_rect(), event.pos)):
            self.open_dispute()
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.scene not in ("title", "intro", "ending")
                and self._tap(self._feedback_rect(), event.pos)):
            self.open_feedback()
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.scene in ("title", "hub", "guild", "garage") and not IS_WEB
                and self._lang_rect().collidepoint(event.pos)):
            self.toggle_lang()
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._top_back_rect() is not None
                and self._tap(self._top_back_rect(), event.pos)):
            self.press_back()
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self._tap(self._speaker_rect(), event.pos)):
            self.show_sound = True
            snd("tick")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sk = self._skip_tut_rect()
            if sk is not None and sk.collidepoint(event.pos):
                self.skip_tutorial()
                return
        if self.v3d is not None and self.scene == "job":
            if self.handle_v3d_event(event):
                return
        elif self.scene == "job" and self._m3d_event(event):
            return
        if self.scene == "seating" and self.handle_seating_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            handler = getattr(self, f"click_{self.scene}", None)
            if handler:
                handler(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.scene == "job":
                    # сначала закрываем оверлеи; двойной Esc — покинуть ремонт
                    if self.show_manual:
                        self.show_manual = False
                    elif self.spec_pending:
                        self.spec_pending = None
                    elif self.mini_pending:
                        self.mini_pending = None
                    elif self.esc_timer > 0:
                        tech = self.cur.get("track") == "tech"
                        self.exam_mode = False
                        self.esc_timer = 0
                        self.scene = "guild" if tech else "hub"
                    else:
                        self.esc_timer = 10.0 if A11Y.get("scan") else 2.5
                        self.flash("Ещё раз Esc — покинуть ремонт (прогресс задания сбросится).",
                                   AMBER, self.esc_timer)
                elif self.scene == "garage" and getattr(self, "garage_open", None) is not None:
                    self.garage_open = None                 # Esc закрывает окно урока, а не гараж
                elif self.scene == "result":
                    self.scene = self._result_next()
                elif self.scene in ("exam_result", "failed"):
                    self.scene = "guild"
                elif self.scene in ("garage", "guild", "seating"):
                    self.scene = "hub"
                elif self.scene in ("hub", "intro"):
                    self.scene = "title"
                elif self.scene == "ending":
                    self.scene = "hub"
                elif self.scene == "credits":
                    self.close_credits()
                elif self.scene == "title":
                    if self.esc_timer > 0:                  # выход из игры — только вторым Esc (B геймпада, «назад»)
                        self.esc_timer = 0
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    elif not IS_WEB:
                        self.esc_timer = 10.0 if A11Y.get("scan") else 2.5
                        self.flash("Ещё раз Esc — выйти из игры.", AMBER, self.esc_timer)

    def _credits_btn_rect(self):
        if self.scene == "title":
            return pygame.Rect(WIDTH // 2 - 215, 520, 200, 40)
        if self.scene == "ending":
            return pygame.Rect(WIDTH // 2 - 215, 560, 200, 40)
        return None

    def _support_btn_rect(self):
        """«Поддержать GOAT» — рядом с «Титрами» и в самих титрах."""
        if self.scene in ("title", "ending"):
            r = self._credits_btn_rect()
            return pygame.Rect(r.right + 30, r.y, 200, 40)
        if self.scene == "credits":
            return pygame.Rect(30, HEIGHT - 70, 230, 46)
        return None

    def open_support(self):
        """Страница пожертвований GOAT — в новой вкладке (браузер) или в браузере компьютера."""
        snd("tick")
        if IS_WEB:
            web_js(f"window.open({json.dumps(SUPPORT_URL)}, '_blank', 'noopener')")
        elif not self.headless:
            try:
                import webbrowser
                webbrowser.open(SUPPORT_URL)
            except Exception:
                pass
        self.flash("Спасибо! Страница пожертвований GOAT (PayPal) открывается в браузере.", GOOD, 3)

    def _credits_back_rect(self):
        return pygame.Rect(WIDTH - 200, HEIGHT - 70, 170, 46)

    def open_credits(self):
        self.credits_from = self.scene
        self.credits_y = 0.0
        self.scene = "credits"
        snd("tick")

    def _credits_layout(self):
        """Строки титров: (текст, размер, цвет, жирный, y от начала)."""
        out, y = [], 0
        for i, (head, lines) in enumerate(CREDITS):
            out.append((head, 30 if i == 0 else 22, AMBER, True, y))
            y += 46 if i == 0 else 36
            for ln in lines:
                out.append((ln, 18, WHITE if i else GHOST, False, y))
                y += 27
            y += 34
        return out, y

    def _credits_max(self):
        return max(0.0, self._credits_layout()[1] - (HEIGHT - 290))

    def click_credits(self, m):
        if self._credits_back_rect().collidepoint(m):
            self.close_credits()
        elif self._support_btn_rect().collidepoint(m):
            self.open_support()

    def close_credits(self):
        self.scene = getattr(self, "credits_from", "title") or "title"
        snd("tick")

    def handle_credits_event(self, event):
        """Титры: колесо мыши и ↑ ↓ PgUp PgDn Home End листают."""
        if event.type == pygame.MOUSEWHEEL:
            self.credits_scroll(-event.y * 60)
            return True
        if event.type == pygame.MOUSEMOTION and event.buttons[0]:     # протянуть пальцем / мышью
            self.credits_scroll(-event.rel[1])
            return True
        if event.type == pygame.KEYDOWN:
            d = {pygame.K_UP: -60, pygame.K_DOWN: 60, pygame.K_PAGEUP: -300, pygame.K_PAGEDOWN: 300,
                 pygame.K_HOME: -1e6, pygame.K_END: 1e6}.get(event.key)
            if d is not None:
                self.credits_scroll(d)
                return True
        return False

    def credits_scroll(self, d):
        self.credits_y = max(0.0, min(self._credits_max(), self.credits_y + d))

    def draw_credits(self, surf):
        self._bg(surf, "bg_party.png" if self.credits_from == "ending" else "bg_workshop.png", WOOD)
        dim = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((12, 10, 18, 205))
        surf.blit(dim, (0, 0))
        area = pygame.Rect(0, 120, WIDTH, HEIGHT - 210)
        rows, _ = self._credits_layout()
        old = surf.get_clip()
        surf.set_clip(_rr(area, _rs(surf)).clip(old))        # рамка — в пикселях экрана (RS ≠ 1 в браузере)
        top = area.y + 44 - int(self.credits_y)
        for text, size, col, bold, y in rows:
            yy = top + y
            if area.y - 40 < yy < area.bottom + 10:
                draw_text(surf, text, (WIDTH // 2, yy), size, col, bold=bold, center=True)
        surf.set_clip(old)
        shade = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)            # края — плавно в темноту (без шва)
        shade.fill((12, 10, 18, 200), (0, 0, WIDTH, area.y))
        shade.fill((12, 10, 18, 200), (0, area.bottom, WIDTH, HEIGHT - area.bottom))
        for k in range(36):
            a = int(200 * (36 - k) / 36)
            shade.fill((12, 10, 18, a), (0, area.y + k, WIDTH, 1))
            shade.fill((12, 10, 18, a), (0, area.bottom - 1 - k, WIDTH, 1))
        surf.blit(shade, (0, 0))
        self._wave_title(surf, "ТИТРЫ", (WIDTH // 2, 70), 44, AMBER, self.st)
        Button(self._credits_back_rect(), "НАЗАД", GOOD).draw(surf, mouse_pos())
        Button(self._support_btn_rect(), "ПОДДЕРЖАТЬ GOAT ♥", AMBER).draw(surf, mouse_pos())
        draw_text(surf, "протяни пальцем — листать" if TOUCH["on"] else "колесо мыши / ↑ ↓ — листать · Esc — назад",
                  (WIDTH // 2, HEIGHT - 47), 15, GREY, center=True)

    def click_title(self, m):
        cb = self._credits_btn_rect()
        if cb is not None and cb.collidepoint(m) and self.st > 1.6:
            self.open_credits()
            return
        sb = self._support_btn_rect()
        if sb is not None and sb.collidepoint(m) and self.st > 1.6:
            self.open_support()
            return
        self.scene = "hub" if (self.done or self.tutorial_skipped) else "intro"
        if self.scene == "intro":                  # после сброса прогресса вступление — снова с первого слайда
            self.intro_idx = 0
            self._typing.pop("intro", None)

    def click_intro(self, m):
        if not self.typing_done("intro"):          # первый клик — допечатать текст
            self.skip_typing("intro")
            return
        self.intro_idx += 1
        if self.intro_idx >= len(self.intro_slides):
            self.start_job("flat")

    def click_hub(self, m):
        for jid, rect in self._hub_job_rects():
            if rect.collidepoint(m):
                self.start_job(jid)
                return
        for d, rect in self._hub_arrow_rects():
            if rect.collidepoint(m):
                self.hub_page = (getattr(self, "hub_page", 0) + d) % self._hub_pages()
                self.scene_t0 = self.t                 # карточки въезжают заново
                snd("tick")
                return
        if self._hub_seat_rect().collidepoint(m):
            if self.tutorial_ok():
                self.open_seating()
            else:
                self.flash("Кабинет посадки откроется после первого ремонта.", CYAN, 3)
            return
        if self._hub_guild_rect().collidepoint(m):
            if self.guild_unlocked():
                self.scene = "guild"
            else:
                self.flash(f"Гильдия Колёсников примет тебя после {GUILD_REQ} починенных колясок.",
                           CYAN, 3.5)
            return
        if self._hub_garage_rect().collidepoint(m):
            self.scene, self.garage_open = "garage", None
            return
        if self.user_done_count() >= len(JOBS) and self._hub_ending_rect().collidepoint(m):
            self.scene = "ending"

    def _part_clicked(self, pid):
        """Клик по детали (кружок, строка списка, сама модель): осмотр в диагнозе, инструмент — в ремонте."""
        if self.phase == "diagnose":
            self.inspect_part(pid)
        elif self.phase == "repair":
            if self.sel_tool is None:
                self.flash("Сначала выбери инструмент внизу.", AMBER, 2.5)
            else:
                self.do_action(self.sel_tool, pid)

    def click_job(self, m):
        if self.cur.get("track") == "tech":
            self.click_job_tech(m)
            return
        if self.mini_pending:
            self._click_mini(m)
            return
        if self.phase == "repair":
            if self._step_prev_rect().collidepoint(m):
                self.step_back()
                return
            if self._step_skip_rect().collidepoint(m):
                self.step_skip()
                return
        if self.phase == "diagnose":
            for pid, rect in self._part_rects():
                if rect.collidepoint(m):
                    self._part_clicked(pid)
                    return
            for i, rect in self._diag_rects():
                if rect.collidepoint(m):
                    self.choose_diagnosis(i)
                    return
            pid = self._hotspot_at(m)
            if pid:
                self._part_clicked(pid)
                return
        elif self.phase == "repair":
            for tid, rect in self._tool_rects():
                if rect.collidepoint(m):
                    self.select_tool(tid)
                    return
            for pid, rect in self._part_rects():
                if rect.collidepoint(m):
                    self._part_clicked(pid)
                    return
            pid = self._hotspot_at(m)
            if pid:
                self._part_clicked(pid)
                return
        elif self.phase == "test":
            if self._test_btn_rect().collidepoint(m) and self.ride_t0 is None:
                self.finish_test() if self.ride_done else self.start_ride()

    def _party_next(self):
        """Вечеринка — один раз, после последнего ремонта; переигрывание заданий ведёт в мастерскую
        (туда можно и кнопкой «НА ВЕЧЕРИНКУ!» в мастерской)."""
        return self.user_done_count() >= len(JOBS) and not self.ending_seen

    def _result_next(self):
        """Куда ведёт итог задания (кнопка и Esc): Гильдия, вечеринка после последнего ремонта или мастерская."""
        if self.cur and self.cur.get("track") == "tech":
            return "guild"
        if self._party_next():
            self.ending_seen = True
            self.save_progress()
            return "ending"
        return "hub"

    def click_result(self, m):
        if self._result_btn_rect().collidepoint(m):
            self.scene = self._result_next()

    def click_ending(self, m):
        cb = self._credits_btn_rect()
        if cb is not None and cb.collidepoint(m):
            self.open_credits()
            return
        if self._support_btn_rect().collidepoint(m):
            self.open_support()
            return
        self.scene, self.garage_open = "garage", None

    # ---------- клики: Гильдия и tech-задания ----------
    def click_guild(self, m):
        for jid, rect in self._guild_job_rects():
            if rect.collidepoint(m):
                self.start_job(jid)
                return
        if self.tech_done_count() >= len(TECH_JOBS) and self._guild_exam_rect().collidepoint(m):
            self.start_exam()
            return
        if self._guild_back_rect().collidepoint(m):
            self.scene = "hub"

    def click_exam_result(self, m):
        if self._result_btn_rect().collidepoint(m):
            self.scene = "guild"

    def click_failed(self, m):
        if self._fail_retry_rect().collidepoint(m):
            if self.exam_mode:
                self.start_exam()      # пересдача: новый случайный билет
            else:
                self.start_job(self.cur["id"])
        elif self._fail_back_rect().collidepoint(m):
            self.scene = "guild"

    def click_job_tech(self, m):
        if self.mini_pending:
            self._click_mini(m)
            return
        if self.show_manual:
            for key, rect in self._manual_page_rects():
                if rect.collidepoint(m):
                    self.manual_page = key
                    self.manual_viewed.add(key)
                    return
            if self._manual_close_rect().collidepoint(m):
                self.show_manual = False
            return
        if self.spec_pending:
            spec = self.spec_pending["spec"]
            if self._spec_manual_rect().collidepoint(m):
                self.open_manual(spec["manual"])
                return
            if self._spec_cancel_rect().collidepoint(m):
                self.spec_pending = None
                return
            if spec["manual"] in self.manual_viewed:
                for i, rect in self._spec_option_rects():
                    if rect.collidepoint(m):
                        self.choose_spec(i)
                        return
            return
        if self.phase == "repair":
            if self._manual_btn_rect().collidepoint(m):
                self.open_manual()
                return
            if not self.exam_mode and self._tech_skip_rect().collidepoint(m):
                self.step_skip()
                return
            for tid, rect in self._tool_rects():
                if rect.collidepoint(m):
                    self.select_tool(tid)
                    return
            for sid, rect in self._op_rects():
                if rect.collidepoint(m):
                    if self.sel_tool is None:
                        self.flash("Сначала выбери инструмент внизу.", AMBER, 2.5)
                    else:
                        self.do_tech_action(self.sel_tool, sid)
                    return
        elif self.phase == "test":
            if self._test_btn_rect().collidepoint(m) and self.ride_t0 is None:
                self.finish_test() if self.ride_done else self.start_ride()

    # =========================================================== #
    #  UPDATE
    # =========================================================== #
    def music_theme(self):
        sc = self.scene
        if sc == "intro":
            return "road"
        if sc == "ending" or (sc == "credits" and getattr(self, "credits_from", "") == "ending"):
            return "party"
        if sc in ("guild", "exam_result", "failed"):
            return "guild"
        if sc == "job" and self.cur and self.cur.get("track") == "tech":
            return "guild"
        return "workshop"

    def _touch_text(self):
        """Сенсорный экран: поле отзыва — настоящее поле страницы поверх холста (вызывает экранную клавиатуру)."""
        if not TOUCH["on"]:
            return
        show = self.dispute_ui is not None and not self.kb["help"] and not self.show_sound
        if show:
            if not getattr(self, "_wtext", False):           # новое окно — поле с текстом окна (обычно пусто)
                web_js("var t=document.getElementById('wnb-text'); if (t) t.value=" + json.dumps(self.dispute_ui["text"]))
                self._wtext = True
            r = self._dispute_text_rect()
            v = web_js(f"wnbText({r.x}, {r.y}, {r.w}, {r.h}, 18, 1)")
            if v is not None:
                self.dispute_ui["text"] = str(v)[:600]
        elif getattr(self, "_wtext", False):
            web_js("wnbText(0, 0, 0, 0, 0, 0)")
            self._wtext = False

    def _tap(self, rect, pos):
        """Попадание по кнопке; на сенсорном экране маленькие значки «шире» пальца — запас по краям."""
        return (rect.inflate(18, 18) if TOUCH["on"] else rect).collidepoint(pos)

    def update(self, dt):
        self.t += dt
        self._touch_text()
        self.scan_tick()
        self.pad_tick()
        self._settings_help_say()
        self._manual_note_say()
        if self.scene == "credits" and not calm() and self.t - self.scene_t0 > 1.2:
            self.credits_y = min(self.credits_y + 26 * dt, self._credits_max())   # медленно вверх
        if not self.headless:
            music_update(self.music_theme(), self.t)
            music_duck(self.scene, self.t - getattr(self, "scene_t0", 0.0), dt)
        if self.toast_timer > 0 and not (getattr(self, "toast_sticky", False) and self.scene == "job"):
            self.toast_timer -= dt
        self.talk_tick()
        if self.esc_timer > 0:
            self.esc_timer -= dt
        if self.v3d is not None:
            self.update_v3d(dt)
        if self.ride_t0 is not None and self.scene != "job":
            self.ride_t0 = None                       # ушли из задания — проезд отменён
        if self.ride_t0 is not None and self.t - self.ride_t0 >= self.RIDE_SECS:
            self.ride_t0 = None
            self.ride_done = True                      # дочитать текст и реплику — итог по «ГОТОВО» (отзыв)
            if self.cur and self.cur.get("track") != "tech":
                self.ghost_line = "Бартоломью: «Едет как надо! Дочитаешь — жми ГОТОВО.»"
            elif self.cur:
                self.ghost_line = "Бренна: «Проверка пройдена. Дочитаешь — жми ГОТОВО.»"

    # =========================================================== #
    #  РЕНДЕР — общие куски
    # =========================================================== #
    @property
    def st(self):
        """Сколько секунд идёт текущая сцена (для анимаций появления)."""
        return self.t - self.scene_t0

    def typed(self, key, text, cps=75):
        """Сколько символов text уже «напечатано» (сброс при смене текста)."""
        text = tr(text)
        seen = self._typing.get(key)
        if A11Y["instant"]:                          # «текст сразу»: считаем, что напечатано давно
            if not seen or seen[0] != text:
                self._typing[key] = (text, self.t - 1000)
            return 10 ** 6
        if not seen or seen[0] != text:
            self._typing[key] = (text, self.t)
            return 0
        return int((self.t - seen[1]) * cps)

    def typing_done(self, key):
        if A11Y["instant"]:
            return True
        seen = self._typing.get(key)
        return not seen or (self.t - seen[1]) * 75 >= len(seen[0])

    def skip_typing(self, key):
        seen = self._typing.get(key)
        if seen:
            self._typing[key] = (seen[0], self.t - 1000)

    def draw(self, surf):
        if self.scene != self._scene_seen:          # смена сцены: растворяем прошлый кадр
            if self._scene_seen is not None and not calm():   # без анимации — без растворения
                self._fade_from = self._last_frame
                self._fade_t0 = self.t
                snd("whoosh")
            self._stars_played = set()
            self._scene_seen = self.scene
            self.scene_t0 = self.t
        CAPTURE.update(frame=surf, texts=[], buttons=[], modal=None, mute=0)
        getattr(self, f"draw_{self.scene}")(surf)
        CAPTURE["mute"] += 1                            # тост и значки сверху читаются отдельно
        if self.toast_timer > 0 and self.toast:
            self._draw_toast(surf)
        CAPTURE["mute"] -= 1
        self._draw_speaker(surf)
        if self.scene in ("title", "hub", "guild", "garage") and not IS_WEB:
            self._draw_lang(surf)
        if self.scene == "job":
            self._draw_dispute_btn(surf, mouse_pos())
        if self.scene not in ("title", "intro", "ending"):
            self._draw_feedback_flag(surf)
        self._draw_back_btn(surf)
        sk = self._skip_tut_rect()                      # «Пропустить обучение» — последним: с клавиатуры не первым пунктом
        if sk is not None and self.dispute_ui is None and not self.show_sound:
            Button(sk, "ПРОПУСТИТЬ ОБУЧЕНИЕ ▸", CYAN).draw(surf, mouse_pos())
        if self.dispute_ui is not None:
            self._draw_dispute_panel(surf, mouse_pos())
        if self.show_sound:
            self._draw_sound_panel(surf)
        if self.kb["help"]:
            self._draw_help(surf)
        self.a11y_frame(surf)
        if self._fade_from is not None:
            k = (self.t - self._fade_t0) / 0.35
            if k >= 1:
                self._fade_from = None
            else:
                self._fade_from.set_alpha(int(255 * (1 - ease_out(k))))
                surf.blit(self._fade_from, (0, 0))
        if not self.headless:
            self._last_frame = surf.copy()

    # ---------- громкость: иконка динамика и панель «Звук» ----------
    def _lang_rect(self):
        return pygame.Rect(WIDTH - 104, 8, 46, 38)

    def _draw_lang(self, surf):
        r = self._lang_rect()
        mouse = mouse_pos()
        h = _hover_amt(("lang",), 1.0 if r.collidepoint(mouse) else 0.0)
        bg = Surf(r.size, pygame.SRCALPHA)
        aa_rect(bg, (30, 28, 40, int(150 + 90 * h)), bg.get_rect(), border_radius=10)
        surf.blit(bg, r)
        col = tuple(int(a + (b - a) * h) for a, b in zip(GHOST, AMBER))
        f = font(15, True)
        img = f.render("EN" if LANG["code"] == "en" else "RU", True, col)
        surf.blit(img, img.get_rect(center=r.center))

    def toggle_lang(self):
        set_lang("en" if LANG["code"] == "ru" else "ru")
        SPEECH.set_voice()
        self.kb["sig"] = None
        self.save_settings()
        self._typing.clear()
        snd("tick")

    def _speaker_rect(self):
        return pygame.Rect(WIDTH - 50, 8, 38, 38)

    def _draw_speaker(self, surf):
        """Шестерёнка настроек (звук и графика). Если звук выключен — маленький красный крестик."""
        r = self._speaker_rect()
        mouse = mouse_pos()
        h = _hover_amt(("speaker",), 1.0 if (r.collidepoint(mouse) or self.show_sound) else 0.0)
        aa_rect(surf, (30, 28, 40, int(150 + 90 * h)), r, border_radius=10)
        col = tuple(int(a + (b - a) * h) for a, b in zip(GHOST, AMBER))
        cx, cy = r.center
        ang0 = self.t * 0.8 * h
        pts = []
        for i in range(16):                                  # 8 зубцов
            a_ = ang0 + i * math.pi / 8
            rad = 12 if i % 2 == 0 else 9
            pts.append((cx + rad * math.cos(a_), cy + rad * math.sin(a_)))
        DR.polygon(surf, col, pts)
        aa_circle(surf, col, (cx, cy), 9)
        aa_circle(surf, (30, 28, 40), (cx, cy), 4)
        if not VOL["on"] or VOL["master"] <= 0.001:
            DR.line(surf, BAD, (r.right - 13, r.bottom - 13), (r.right - 5, r.bottom - 5), 2)
            DR.line(surf, BAD, (r.right - 5, r.bottom - 13), (r.right - 13, r.bottom - 5), 2)

    def _sound_panel_rect(self):
        return pygame.Rect(WIDTH // 2 - 290, HEIGHT // 2 - 250, 580, 500)

    def _settings_tab_rects(self):
        p = self._sound_panel_rect()
        return [(t, pygame.Rect(p.x + 32 + i * 130, p.y + 64, 122, 36))
                for i, t in enumerate(("sound", "graphics", "access", "game"))]

    def _reset_btn_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 32, p.y + 300, p.w - 64, 46)

    def _reset_yes_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 32, p.y + 300, (p.w - 80) // 2, 46)

    def _reset_no_rect(self):
        p = self._sound_panel_rect()
        w = (p.w - 80) // 2
        return pygame.Rect(p.right - 32 - w, p.y + 300, w, 46)

    def progress_summary(self):
        """Что сейчас пройдено — для вкладки «ИГРА» и озвучки."""
        return [f"Починено колясок: {self.user_done_count()} из {len(JOBS)}",
                f"Гильдия: {self.tech_done_count()} из {len(TECH_JOBS)}" + (", диплом получен" if self.exam_passed else ""),
                f"Кабинет посадки: примерки {len(self.seat_done)}/{len(SEAT_CASES)}" + (" · зачёт ✔" if self.seat_quiz_ok else "")]

    def reset_progress(self):
        """Сброс прогресса (починки, гараж, Гильдия, посадка). Настройки звука/графики/языка/доступности остаются."""
        self.done = set()
        self.garage = []
        self.exam_passed = False
        self.seat_done = set()
        self.seat_quiz_ok = False
        self.tutorial_skipped = False
        self.hub_page = 0
        self.mini_pending = self.spec_pending = None          # окна задания, поверх которых открыли настройки
        self.show_manual = False
        self.v3d = self.m3d = None
        self.act = self.ride_t0 = None
        self.ride_done = False
        self.dispute = self.seatc = None
        self.esc_timer = 0
        self._talk_later = None
        self.cur = None
        self.exam_mode = False
        self.save_progress()
        self._reset_ask = False
        self.show_sound = False
        self.scene = "title"
        snd("whoosh")
        self.flash("Прогресс сброшен. Начинаем с начала — настройки сохранены.", AMBER, 4)

    def _ask_reset(self, on=True):
        """Подтверждение сброса: вопрос и кнопки «ДА, СБРОСИТЬ» / «НЕТ»."""
        self._reset_ask = on
        snd("bad" if on else "tick")
        self.say("Сбросить весь прогресс? Это нельзя отменить. Да или нет." if on else "Сброс отменён.", True)

    def _draw_game_tab(self, surf, p, mouse):
        draw_text(surf, "Прогресс", (p.x + 32, p.y + 124), 19, WHITE, bold=True)
        y = p.y + 156
        for line in self.progress_summary():
            draw_text(surf, line, (p.x + 32, y), 16, GREY)
            y += 28
        if getattr(self, "_reset_ask", False):
            draw_text(surf, "Сбросить весь прогресс? Это нельзя отменить.", (p.x + 32, p.y + 268), 16, BAD, bold=True)
            Button(self._reset_yes_rect(), "ДА, СБРОСИТЬ", BAD).draw(surf, mouse)
            Button(self._reset_no_rect(), "НЕТ", GOOD).draw(surf, mouse)
        else:
            Button(self._reset_btn_rect(), "СБРОСИТЬ ПРОГРЕСС", BAD).draw(surf, mouse)
        draw_wrapped(surf, "Сотрёт починенные коляски, гараж, Гильдию и Кабинет посадки. Звук, графика, язык и "
                           "доступность останутся.", (p.x + 32, p.y + 356), p.w - 64, 13, GREY)

    ACCESS_ROWS = ("on", "voices", "rate", "contrast", "instant", "calm", "quiet", "barty", "text", "font", "scan")

    def _access_rects(self):
        p = self._sound_panel_rect()
        return [(k, pygame.Rect(p.x + 330, p.y + 102 + i * 27, 216, 24)) for i, k in enumerate(self.ACCESS_ROWS)]

    @staticmethod
    def _access_val(k):
        return quiet_talk() if k == "quiet" else (barty_on() if k == "barty" else A11Y.get(k))

    @staticmethod
    def _scan_text():
        n = A11Y.get("scan", 0)
        if not (1 <= n <= len(SCAN_SPEEDS)):
            return tr("ВЫКЛ")
        v = f"{SCAN_SPEEDS[n - 1]:g}"
        return (v.replace(".", ",") if LANG["code"] == "ru" else v) + " " + tr("с")

    def _access_label(self, k):
        on = tr("включено") if self._access_val(k) else tr("выключено")
        if k == "on":
            return f"{tr('Озвучка')}: {tr('включена') if A11Y['on'] else tr('выключена')}. F2"
        if k == "voices":
            return f"{tr('Реплики персонажей вслух')}: {on}"
        if k == "rate":
            return f"{tr('Скорость голоса Windows')}: {A11Y['rate']}. " + tr("Enter — быстрее, после 10 — снова медленно")
        if k == "contrast":
            return f"{tr('Тёмный контрастный фон')}: {on}"
        if k == "text":
            return f"{tr('Размер текста')}: {self._text_pct()}%"
        if k == "calm":
            return f"{tr('Без анимации')}: {on}"
        if k == "quiet":
            return f"{tr('Клиент говорит только одну фразу при входе')}: {on}"
        if k == "barty":
            return f"{tr('Призрак Барти и его шутки в мастерской')}: {on}"
        if k == "font":
            return (f"{tr('Шрифт для лёгкого чтения (Atkinson Hyperlegible)')}: {on}"
                    + ("" if LANG["code"] == "en" else ". " + tr("Только для английского языка")))
        if k == "scan":
            return (f"{tr('Управление одной кнопкой')}: {self._scan_text()}. "
                    + tr("Пункты выделяются сами; нажми — выбрать, держи — назад"))
        return f"{tr('Текст сразу, без печати по буквам')}: {on}"

    @staticmethod
    def _text_pct():
        return round(100 * TEXT_K[min(len(TEXT_K) - 1, max(0, A11Y.get("text", 0)))])

    def _access_toggle(self, k):
        if k == "on":
            self.toggle_speech()
        elif k == "rate":
            A11Y["rate"] = min(10, A11Y["rate"] + 2) if A11Y["rate"] < 10 else -4
            SPEECH.set_voice()
            self.say(f"{tr('Скорость')}: {A11Y['rate']}", True)
        elif k == "font":
            A11Y["font"] = not A11Y.get("font")
            DISPLAY["frame"] = None                   # шрифты и подписи — заново
            _update_rs()
            self.say(self._access_label(k), True)
        elif k == "scan":
            A11Y["scan"] = (A11Y.get("scan", 0) + 1) % (len(SCAN_SPEEDS) + 1)
            self._scan_next = self.t + 1.5
            self.kb["scan_sub"] = None
            self.say(self._access_label(k), True)
        elif k == "text":
            A11Y["text"] = (A11Y.get("text", 0) + 1) % len(TEXT_K)
            A11Y["text_set"] = True                   # свой выбор игрока — размер по умолчанию его не перебьёт
            DISPLAY["frame"] = None                   # шрифты и подписи — заново в новом размере
            _update_rs()
            self.say(self._access_label(k), True)
        elif k == "quiet":
            A11Y["quiet"], A11Y["quiet_set"] = not quiet_talk(), True
            if A11Y["quiet"]:
                self.client_queue = self.client_queue[:1]
            self.say(self._access_label(k), True)
        else:
            A11Y[k] = not A11Y[k]
            if k == "barty" and not A11Y[k]:
                self.ghost_quip = ""
            if k == "calm":
                A11Y["calm_set"] = True               # свой выбор — системная настройка его не перебьёт
            self.say(self._access_label(k), True)
        snd("tick")
        self.save_settings()

    def _vol_slider_rects(self):
        p = self._sound_panel_rect()
        return [(k, pygame.Rect(p.x + 225, p.y + 146 + i * 58, 230, 8))
                for i, k in enumerate(("master", "music", "sfx", "amb"))]

    def _sound_mute_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 32, p.bottom - 70, 220, 44)

    def _sound_close_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.right - 192, p.bottom - 70, 160, 44)

    def _mode_rects(self):
        p = self._sound_panel_rect()
        return [(m, pygame.Rect(p.x + 230 + i * 160, p.y + 128, 150, 38)) for i, m in enumerate((False, True))]

    def _res_rects(self):
        p = self._sound_panel_rect()
        opts = ["auto"] + available_resolutions()
        return [(o, pygame.Rect(p.x + 32 + (i % 3) * 174, p.y + 214 + (i // 3) * 44, 164, 38)) for i, o in enumerate(opts)]

    WEB_Q = (("auto", "АВТО"), ("high", "1080p"), ("standard", "720p"))

    def _webq_rects(self):
        p = self._sound_panel_rect()
        return [(q, pygame.Rect(p.x + 230 + i * 108, p.y + 128, 100, 38)) for i, (q, _) in enumerate(self.WEB_Q)]

    def _web_fs_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 230, p.y + 196, 230, 38)

    def _glow_btn_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 310, p.y + 320, 216, 38)

    def _gpu_btn_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 310, p.y + 368, 216, 38)

    def _set_vol_from_x(self, key, x):
        track = dict(self._vol_slider_rects())[key]
        VOL[key] = round(max(0.0, min(1.0, (x - track.x) / track.w)), 2)
        if key in ("amb", "master", "music"):
            apply_volume()

    def handle_sound_event(self, event):
        tab = getattr(self, "settings_tab", "sound")
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and getattr(self, "_reset_ask", False):
            self._ask_reset(False)                            # Esc сначала отменяет вопрос о сбросе
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.show_sound = False
            self._vol_drag, self._reset_ask = None, False
            self.save_settings()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._sound_close_rect().collidepoint(event.pos) or \
                    not self._sound_panel_rect().collidepoint(event.pos):
                self.show_sound = False
                self._vol_drag, self._reset_ask = None, False
                self.save_settings()
                snd("tick")
                return
            for t, r in self._settings_tab_rects():
                if r.collidepoint(event.pos):
                    self.settings_tab = t
                    self._reset_ask = False
                    snd("tick")
                    return
            if tab == "access":
                for k, r in self._access_rects():
                    if r.collidepoint(event.pos):
                        self._access_toggle(k)
                        return
                return
            if tab == "game":
                if getattr(self, "_reset_ask", False):
                    if self._reset_yes_rect().collidepoint(event.pos):
                        self.reset_progress()
                    elif self._reset_no_rect().collidepoint(event.pos):
                        self._ask_reset(False)
                elif self._reset_btn_rect().collidepoint(event.pos):
                    self._ask_reset(True)
                return
            if tab == "sound":
                if self._sound_mute_rect().collidepoint(event.pos):
                    toggle_sound()
                    snd("tick")
                    return
                for key, track in self._vol_slider_rects():
                    if track.inflate(24, 30).collidepoint(event.pos):
                        self._vol_drag = key
                        self._set_vol_from_x(key, event.pos[0])
                        return
                return
            if IS_WEB:
                for q, r in self._webq_rects():                  # браузер: качество картинки
                    if r.collidepoint(event.pos):
                        set_web_quality(q)
                        self.save_settings()
                        snd("tick")
                        return
                if self._web_fs_rect().collidepoint(event.pos):
                    web_toggle_fullscreen()
                    snd("tick")
                    return
            for full, r in ([] if IS_WEB else self._mode_rects()):     # в браузере окно и размер — у страницы
                if r.collidepoint(event.pos):
                    if full != DISPLAY["fullscreen"] and not self.headless:
                        toggle_fullscreen()
                    snd("tick")
                    return
            for opt, r in ([] if IS_WEB else self._res_rects()):
                if r.collidepoint(event.pos):
                    cur = DISPLAY["res"] or "auto"
                    if opt != cur:
                        if self.headless:
                            DISPLAY["res"] = None if opt == "auto" else tuple(opt)
                        else:
                            apply_display(opt)
                    snd("tick")
                    return
            if self._glow_btn_rect().collidepoint(event.pos):
                DISPLAY["glow"] = not DISPLAY["glow"]
                snd("tick")
                return
            if self._gpu_btn_rect().collidepoint(event.pos) and _mgl is not None:
                GL["off"] = not GL["off"]
                if not GL["off"]:
                    GL["failed"] = False
                self.m3d = None
                snd("tick")
                return
        elif event.type == pygame.MOUSEMOTION and self._vol_drag:
            self._set_vol_from_x(self._vol_drag, event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._vol_drag:
            if self._vol_drag in ("master", "sfx"):
                snd("ok")                                   # услышать новую громкость
            self._vol_drag = None

    def _draw_access_tab(self, surf, p, mouse):
        names = {"on": "Озвучка (F2)", "voices": "Реплики героев вслух", "rate": "Скорость голоса",
                 "contrast": "Контрастный фон", "instant": "Текст сразу", "calm": "Без анимации",
                 "quiet": "Клиент: одна фраза", "barty": "Призрак Барти",
                 "text": "Размер текста", "scan": "Одна кнопка", "font": "Лёгкий шрифт"}
        for k, r in self._access_rects():
            draw_text(surf, names[k], (p.x + 32, r.centery - font(16).get_height() // 2), 16, WHITE)
            if k == "rate":
                label = str(A11Y["rate"])
            elif k == "text":
                label = f"{self._text_pct()}%"
            elif k == "scan":
                label = self._scan_text()
            else:
                label = "ВКЛ" if self._access_val(k) else "ВЫКЛ"
            on = k in ("rate", "text") or bool(self._access_val(k))
            Button(r, label, GOOD if on else GREY).draw(surf, mouse, active=on and k not in ("rate", "text"))
        y0 = self._access_rects()[-1][1].bottom + 6
        tw = self._sound_close_rect().x - p.x - 48
        note = ("Вся игра проходится с клавиатуры: стрелки, Tab, Enter. F1 — все клавиши. "
                "Одна кнопка: пункты выделяются сами, нажми — выбрать, держи — назад.")
        for sz in (13, 12, 11, 10):                   # крупный шрифт — мельче, но внутри панели
            lh = font(sz).get_height()
            if y0 + lh + 2 + len(wrap_lines(note, tw, sz)) * (lh + 2) <= p.bottom - 8:
                break
        draw_text(surf, f"Озвучка: {SPEECH.label()}", (p.x + 32, y0), sz, GREY)
        draw_wrapped(surf, note, (p.x + 32, y0 + font(sz).get_height() + 2), tw, sz, GREY,
                     max_lines=max(1, (p.bottom - 8 - y0) // (font(sz).get_height() + 2) - 1))

    SETTING_HELP = {   # что делает каждая настройка — карточка при наведении/фокусе (и озвучка после паузы на пункте)
        "vol_master": "Общая громкость всех звуков игры: музыки, эффектов и атмосферы.",
        "vol_music": "Громкость фоновой мелодии. За работой она через минуту сама стихает до тихого фона.",
        "vol_sfx": "Звуки действий: щелчки кнопок, инструменты, верный и неверный шаг.",
        "vol_amb": "Фоновые звуки места: мастерская, дорога, Гильдия, вечеринка.",
        "mute": "Выключает или включает весь звук сразу. То же делает клавиша M.",
        "mode": "Игра в окне или на весь экран. Переключить можно и клавишей F11 или Alt+Enter.",
        "res": "Размер, в котором игра рисует картинку. Меньше — быстрее на слабом компьютере, больше — чётче. "
               "«Авто» подбирает его по экрану.",
        "glow": "Свечение, искры, пыль и другие частицы для красоты. Выключи, если мешают или игра тормозит.",
        "gpu": "Рисовать 3D-коляски видеокартой: вращение плавнее. Выключи, если коляска отображается с ошибками.",
        "web_quality": "Чёткость картинки в браузере. «Авто» — по размеру окна; 720p — быстрее на слабом телефоне "
                       "или ноутбуке.",
        "web_fs": "Развернуть игру на весь экран браузера и обратно (F11).",
        "acc_on": "Игра читает вслух всё на экране: пункты, шаги, подсказки — для незрячих и слабовидящих. Говорит "
                  "через экранный диктор или голос системы. F2 — включить или выключить.",
        "acc_voices": "Озвучка читает и реплики персонажей, а не только меню и шаги.",
        "acc_rate": "Скорость голоса озвучки. Каждое нажатие — быстрее; после 10 снова медленно.",
        "acc_contrast": "Затемняет картинку фона, чтобы текст и кнопки были контрастнее.",
        "acc_instant": "Текст появляется сразу целиком, без печати по буквам.",
        "acc_calm": "Убирает движение: покачивание, проезд коляски после ремонта, сценки с ногой, мигание кружков.",
        "acc_quiet": "Клиент говорит одну фразу при входе и дальше молчит — меньше текста на экране.",
        "acc_barty": "Призрак Барти в мастерской и его шутки. Выключи, если отвлекает. В Гильдии подсказывает Бренна.",
        "acc_text": "Крупнее текст на всех экранах. Каждое нажатие — следующий размер.",
        "acc_font": "Шрифт Atkinson Hyperlegible для слабого зрения: буквы и цифры легко различить. Только для "
                    "английского языка.",
        "acc_scan": "Управление одной кнопкой: пункты сами подсвечиваются по очереди, нажми — выбрать, держи — назад. "
                    "Число — сколько секунд на пункт.",
        "reset": "Стирает починенные коляски, гараж, Гильдию и Кабинет посадки — игра начнётся заново. Звук, графика, "
                 "язык и доступность останутся.",
    }

    def _settings_help_zones(self):
        """(ключ подсказки, строка настройки целиком — подпись и переключатель) на открытой вкладке."""
        p = self._sound_panel_rect()
        row = lambda *rs: pygame.Rect(p.x + 24, min(r.y for r in rs) - 4, p.w - 48,
                                      max(r.bottom for r in rs) - min(r.y for r in rs) + 8)
        tab = getattr(self, "settings_tab", "sound")
        if tab == "sound":
            return ([("vol_" + k, pygame.Rect(p.x + 24, t.y - 20, p.w - 48, 40)) for k, t in self._vol_slider_rects()]
                    + [("mute", self._sound_mute_rect())])
        if tab == "access":
            return [("acc_" + k, pygame.Rect(p.x + 24, r.y - 1, r.right - p.x - 24, r.h + 2))
                    for k, r in self._access_rects()]
        if tab == "game":
            return [("reset", row(self._reset_btn_rect()))]
        if IS_WEB:
            return [("web_quality", row(*[r for _, r in self._webq_rects()])), ("web_fs", row(self._web_fs_rect())),
                    ("glow", row(self._glow_btn_rect()))]
        return [("mode", row(*[r for _, r in self._mode_rects()])), ("res", row(*[r for _, r in self._res_rects()])),
                ("glow", row(self._glow_btn_rect())), ("gpu", row(self._gpu_btn_rect()))]

    def _settings_help_at(self, mouse):
        """Какую настройку объяснить: в фокусе клавиатуры/кнопки — её, иначе — под мышью (на касаниях — последнюю)."""
        zones = self._settings_help_zones()
        if self.kb.get("active") and self.kb.get("key"):
            it = next((x for x in self.kb.get("items", ()) if x.get("key") == self.kb["key"]), None)
            if it and it.get("rect"):
                c = pygame.Rect(it["rect"]).center
                return next(((k, z) for k, z in zones if z.collidepoint(c)), None)
        return next(((k, z) for k, z in zones if z.collidepoint(mouse)), None)

    def _draw_setting_help(self, surf, mouse):
        hit = self._settings_help_at(mouse)
        if not hit:
            return
        key, zone = hit
        text = self.SETTING_HELP[key]
        p = self._sound_panel_rect()
        x, w = p.right + 10, WIDTH - p.right - 18                  # справа от панели — не закрывает настройки
        for sz in (15, 14, 13, 12):
            lh = font(sz).get_height() + 2
            h = len(wrap_lines(text, w - 24, sz)) * lh + 18
            if h <= HEIGHT - 16:
                break
        y = max(8, min(zone.centery - h // 2, HEIGHT - 8 - h))
        box = pygame.Rect(x, y, w, h)
        aa_rect(surf, (24, 26, 36, 250), box, border_radius=10)
        aa_rect(surf, CYAN, box, 2, border_radius=10)
        DR.line(surf, CYAN, (p.right - 2, zone.centery), (x, max(y + 12, min(zone.centery, y + h - 12))), 2)
        draw_wrapped(surf, text, (x + 12, y + 9), w - 24, sz, WHITE)

    def _settings_help_say(self):
        """Озвучка: фокус задержался на настройке — прочитать, что она делает (один раз на пункт)."""
        if not (self.show_sound and self.kb.get("active") and A11Y["on"]):
            return
        hit = self._settings_help_at((-1, -1))
        key = hit[0] if hit else None
        if key != getattr(self, "_help_key", None):
            self._help_key, self._help_t, self._help_said = key, self.t, False
        elif key and not self._help_said and self.t - self._help_t > 1.2:
            self._help_said = True
            self.say(self.SETTING_HELP[key], False)

    def _draw_sound_panel(self, surf):
        _cap_modal()
        dim = _img_cache.get(("v3d_dim", 168, RS))
        if dim is None:
            dim = _img_cache[("v3d_dim", 168, RS)] = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((8, 8, 12, 168))
        surf.blit(dim, (0, 0))
        p = self._sound_panel_rect()
        aa_rect(surf, (18, 18, 26, 250), p, border_radius=14)
        aa_rect(surf, AMBER, p, 2, border_radius=14)
        draw_text(surf, "НАСТРОЙКИ", (p.x + 32, p.y + 22), 24, AMBER, bold=True)
        mouse = mouse_pos()
        tab = getattr(self, "settings_tab", "sound")
        for t, r in self._settings_tab_rects():
            Button(r, {"sound": "ЗВУК", "graphics": "ГРАФИКА", "access": "ДОСТУПНОСТЬ", "game": "ИГРА"}[t], CYAN).draw(
                surf, mouse, active=t == tab)
        if tab == "access":
            self._draw_access_tab(surf, p, mouse)
        elif tab == "game":
            self._draw_game_tab(surf, p, mouse)
        elif tab == "sound":
            draw_text(surf, "M — быстро выключить / включить звук", (p.x + 32, p.y + 374), 13, GREY)
            draw_text(surf, "За работой мелодия через минуту стихает до фона", (p.x + 32, p.y + 392), 13, GREY)
            names = {"master": "Общая громкость", "music": "Музыка", "sfx": "Эффекты", "amb": "Атмосфера сцен"}
            for key, track in self._vol_slider_rects():
                muted = not VOL["on"]
                draw_text(surf, names[key], (p.x + 32, track.y - 8), 17, GREY if muted else WHITE)
                aa_rect(surf, (44, 46, 60), track, border_radius=4)
                fill = track.copy()
                fill.w = int(track.w * VOL[key])
                if fill.w:
                    aa_rect(surf, DIM if muted else AMBER, fill, border_radius=4)
                kx = track.x + fill.w
                hov = track.inflate(24, 30).collidepoint(mouse) or self._vol_drag == key
                h = _hover_amt(("vol", key), 1.0 if hov else 0.0)
                aa_circle(surf, WHITE, (kx, track.centery), int(10 + 3 * h))
                aa_circle(surf, DIM if muted else AMBER, (kx, track.centery), int(10 + 3 * h), 3)
                draw_text(surf, f"{int(VOL[key] * 100)}%", (track.right + 56, track.y - 8), 16,
                          GREY if muted else WHITE, right=True)
            Button(self._sound_mute_rect(), "ВКЛЮЧИТЬ ЗВУК" if not VOL["on"] else "БЕЗ ЗВУКА",
                   GOOD if not VOL["on"] else GREY).draw(surf, mouse)
        elif IS_WEB:                                   # браузер: качество картинки и полный экран
            draw_text(surf, "Качество", (p.x + 32, p.y + 137), 17, WHITE)
            q = DISPLAY.get("web_quality", "auto")
            for (qk, label), (_, r) in zip(self.WEB_Q, self._webq_rects()):
                Button(r, label, CYAN).draw(surf, mouse, active=q == qk)
            draw_text(surf, "Авто — по размеру окна игры. Сейчас: {0}p".format(DISPLAY.get("res", (1920, 1080))[1]),
                      (p.x + 230, p.y + 172), 12, GREY)
            draw_text(surf, "Полный экран", (p.x + 32, p.y + 205), 17, WHITE)
            Button(self._web_fs_rect(), "ВКЛ / ВЫКЛ  (F11)", AMBER).draw(surf, mouse)
            draw_text(surf, "Свечение и частицы", (p.x + 32, p.y + 329), 17, WHITE)
            Button(self._glow_btn_rect(), "ВКЛ" if DISPLAY["glow"] else "ВЫКЛ",
                   AMBER if DISPLAY["glow"] else GREY).draw(surf, mouse, active=DISPLAY["glow"])
        else:
            draw_text(surf, "Режим экрана", (p.x + 32, p.y + 137), 17, WHITE)
            for full, r in self._mode_rects():
                Button(r, "ВЕСЬ ЭКРАН" if full else "В ОКНЕ", CYAN).draw(surf, mouse, active=full == DISPLAY["fullscreen"])
            draw_text(surf, "F11 или Alt+Enter — переключить", (p.x + 230, p.y + 172), 12, GREY)
            draw_text(surf, "Разрешение", (p.x + 32, p.y + 186), 17, WHITE)
            cur = DISPLAY["res"] or "auto"
            for opt, r in self._res_rects():
                label = "АВТО" if opt == "auto" else f"{opt[0]}×{opt[1]}"
                Button(r, label, AMBER).draw(surf, mouse, active=opt == cur)
            draw_text(surf, f"Сейчас: {round(WIDTH * RS)}×{round(HEIGHT * RS)} · меньше — быстрее на слабом ПК",
                      (p.x + 32, p.y + 296), 13, GREY)
            draw_text(surf, "Свечение и частицы", (p.x + 32, p.y + 329), 17, WHITE)
            Button(self._glow_btn_rect(), "ВКЛ" if DISPLAY["glow"] else "ВЫКЛ",
                   AMBER if DISPLAY["glow"] else GREY).draw(surf, mouse, active=DISPLAY["glow"])
            draw_text(surf, "3D через видеокарту", (p.x + 32, p.y + 377), 17, WHITE)
            gpu_label = "НЕДОСТУПНО" if _mgl is None else ("ВКЛ" if not GL["off"] else "ВЫКЛ")
            Button(self._gpu_btn_rect(), gpu_label, CYAN if (not GL["off"] and _mgl is not None) else GREY).draw(
                surf, mouse, enabled=_mgl is not None, active=not GL["off"] and _mgl is not None)
        Button(self._sound_close_rect(), "ГОТОВО", AMBER).draw(surf, mouse)
        self._draw_setting_help(surf, mouse)

    def _bg(self, surf, name, color):
        key = ("bg_dimmed", name, RS, A11Y["contrast"])        # фон + затемнение — один раз, дальше одна копия на кадр
        bg = _img_cache.get(key)
        if bg is None:
            bg = Surf((WIDTH, HEIGHT))
            bg.blit(load_image(name, (WIDTH, HEIGHT), color), (0, 0))
            ov = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((10, 9, 14, 222) if A11Y["contrast"] else (18, 16, 24, 150))   # контраст: фон почти чёрный
            bg.blit(ov, (0, 0))
            _img_cache[key] = bg
        surf.blit(bg, (0, 0))
        if not A11Y["contrast"]:
            draw_ambient(surf, name, self.t)
        set_ambient(name)

    def _draw_toast(self, surf):
        reserve = 56 if self.scene in ("title", "intro", "ending") else 164   # справа значки ⚑ / RU / шестерёнка
        if self.scene in ("title",) and not IS_WEB:
            reserve = 112
        if self.scene == "job" and self.dispute_visible():
            reserve = WIDTH - self._dispute_btn_rect().x + 6
        sk = self._skip_tut_rect()
        if sk is not None and sk.y < 60:              # первое задание: сообщение не уходит под «Пропустить обучение»
            reserve = WIDTH - sk.x + 6
        br = self._top_back_rect()
        left = br.right + 8 if br else 8                        # не под кнопкой «◂ Назад»
        w = WIDTH - left - 8 - reserve
        for tsz in (16, 15, 14, 13, 12):                       # сообщение — в полосе заголовка (до 52 px), не на задании
            lines = wrap_lines(self.toast, w - 40, tsz)
            lh = font(tsz).get_height() + 1
            if 8 + len(lines) * lh <= 50:
                break
        h = 8 + len(lines) * lh
        k = ease_back((self.t - self._typing.setdefault(("toast", self.toast), (self.toast, self.t))[1]) / 0.3)
        rect = pygame.Rect(left, 2 - int(50 * (1 - k)), w, max(46, h))
        s = Surf(rect.size, pygame.SRCALPHA)
        s.fill((20, 18, 26, 250))
        surf.blit(s, rect)
        aa_rect(surf, self.toast_color, rect, 2, border_radius=6)
        y = rect.y + (rect.h - len(lines) * lh) // 2 + lh // 2
        for ln in lines:
            draw_text(surf, ln, (rect.centerx, y), tsz, self.toast_color, center=True)
            y += lh

    def _topbar(self, surf, title, sub=None):
        DR.rect(surf, (16, 14, 22), (0, 0, WIDTH, 54))
        DR.line(surf, AMBER, (0, 54), (WIDTH, 54), 1)
        right = WIDTH - 170
        sk = self._skip_tut_rect()
        if self.scene == "job" and self.dispute_visible():      # место занято кнопкой «Я НЕ СОГЛАСЕН»
            right = self._dispute_btn_rect().x - 12
        elif sk is not None:                                     # первое задание: место под кнопку пропуска
            right = sk.x - 12
        else:
            draw_text(surf, "КОЛЁСА И КОСТИ", (right, 16), 18, GHOST, bold=True, right=True)
            right -= font(18, True).size(tr("КОЛЁСА И КОСТИ"))[0] + 16
        br = self._top_back_rect()
        x0 = br.right + 10 if br else 24                             # место под «◂ Назад»
        if sub:                                                  # вторая строка — какая коляска (модель)
            for ts, ss in ((20, 14), (18, 13), (17, 12), (16, 11), (15, 10)):   # крупный шрифт — обе строки в полосе
                th, sh = font(ts, True).get_height(), font(ss).get_height()
                if th + sh + 1 <= 50:
                    break
            y = max(1, (54 - th - sh - 1) // 2)
            fit_text(surf, title, (x0, y), right - x0, ts, AMBER, bold=True)
            fit_text(surf, sub, (x0, y + th + 1), right - x0, ss, GHOST)
        else:
            fit_text(surf, title, (x0, 15), right - x0, 22, AMBER, bold=True)

    # ----- титул -----
    def _wave_title(self, surf, text, center, size, color, st, delay=0.0, max_w=None):
        """Заголовок: буквы падают по очереди с перелётом, потом мягко «дышат» волной.
        max_w — не шире (крупный текст в настройках не должен наезжать на рисунок вокруг)."""
        text = tr(text)
        while max_w and size > 30 and font(size, True).size(text)[0] > max_w:
            size -= 2
        f = font(size, True)
        x = center[0] - f.size(text)[0] // 2
        for i, ch in enumerate(text):
            d = delay + 0.05 * i
            k = ease_back((st - d) / 0.55)
            a = 255 if calm() else int(255 * clamp01((st - d) / 0.2))
            y = center[1] - f.get_height() // 2 - int(70 * (1 - k)) + 4 * wsin(self.t * 2.2 + i * 0.55)
            if a > 0 and ch != " ":
                sh = f.render(ch, True, (20, 14, 10))
                sh.set_alpha(a // 2)
                surf.blit(sh, (x + 3, y + 4))
                img = f.render(ch, True, color)
                img.set_alpha(a)
                surf.blit(img, (x, y))
            x += f.size(ch)[0]

    def draw_title(self, surf):
        self._bg(surf, "bg_workshop.png", WOOD)
        st = self.st
        for cx, d in ((WIDTH // 2 - 510, 1), (WIDTH // 2 + 510, -1)):
            draw_spin_wheel(surf, (cx, 205), 50, self.t * 1.3 * d, ease_back((st - 0.7) / 0.6))
        self._wave_title(surf, "КОЛЁСА И КОСТИ", (WIDTH // 2, 210), 76, AMBER, st, max_w=2 * 510 - 140)
        draw_text(surf, "ремонтная мастерская Мартина", (WIDTH // 2, 285), 26, GHOST, center=True,
                  alpha=255 * appear(st, 0.9, 0.6))
        draw_text(surf, "Обучающий симулятор ремонта инвалидных колясок в фэнтези-мире",
                  (WIDTH // 2, 360), 19, WHITE, center=True, alpha=255 * appear(st, 1.2, 0.6))
        # Мартин въезжает в кадр, Барти парит
        mx = -260 + int(320 * ease_out((st - 0.4) / 1.4))
        blit_idle(surf, load_image("martin.png", (230, 260), GHOST), (mx, HEIGHT - 300), self.t)
        gk = ease_back((st - 1.4) / 0.6)
        if gk > 0.01:
            blit_idle(surf, load_image("ghost.png", (190, 240), CYAN), (WIDTH - 250, HEIGHT - 330),
                      self.t, "float", k=gk)
        if st > 1.6:
            label = ("[ тап — продолжить ]" if self.done else "[ тап — начать ]") if TOUCH["on"] else                 ("[ клик — продолжить ]" if self.done else "[ клик — начать ]")
            pulse = 0.5 + 0.5 * wsin(self.t * 3.2)
            draw_text(surf, label, (WIDTH // 2, 470), 24, AMBER, bold=True, center=True,
                      alpha=150 + 105 * pulse)
        if st > 1.6:
            Button(self._credits_btn_rect(), "ТИТРЫ", GHOST).draw(surf, mouse_pos())
            Button(self._support_btn_rect(), "ПОДДЕРЖАТЬ GOAT ♥", AMBER).draw(surf, mouse_pos())
        if TOUCH["on"]:                                     # телефон/планшет: клавиш нет
            draw_text(surf, "прогресс сохраняется автоматически", (WIDTH // 2, HEIGHT - 36), 15, GREY, center=True)
        else:
            draw_text(surf, "M — sound · progress saves automatically" if IS_WEB else
                      "Esc — выход · M — звук · прогресс сохраняется автоматически",
                      (WIDTH // 2, HEIGHT - 36), 15, GREY, center=True)
            draw_text(surf, "F1 — управление с клавиатуры · F2 — озвучка для незрячих",
                      (WIDTH // 2, HEIGHT - 62), 15, CYAN, center=True)

    # ----- интро -----
    def draw_intro(self, surf):
        self._bg(surf, "bg_road.png", RUST)
        idx = min(self.intro_idx, len(self.intro_slides) - 1)
        title, text = self.intro_slides[idx]
        # портреты Мартина и призрака
        st = self.st
        mx = 120 - int(300 * (1 - ease_out(st / 0.9)))
        blit_idle(surf, load_image("martin.png", (200, 280), GHOST), (mx, 230), self.t)
        blit_idle(surf, load_image("ghost.png", (200, 280), CYAN), (WIDTH - 320, 230), self.t,
                  "float", k=ease_back((st - 0.3) / 0.6))
        if idx == 1:
            draw_leg_gag(surf, "hop", self.t - self._typing.get("intro", ("", self.t))[1],
                         pygame.Rect(0, 560, WIDTH, 150))
        n = self.typed("intro", text)
        sk = ease_out((self.t - self._typing["intro"][1]) / 0.35)
        lh = font(19).get_height() + 4                # крупный текст: окно — по самому длинному слайду
        ph = max(250, 70 + max(len(wrap_lines(t_, 510, 19)) for _, t_ in self.intro_slides) * lh + 54)
        panel = pygame.Rect(360, 250 + int(24 * (1 - sk)), 560, ph)
        s = Surf(panel.size, pygame.SRCALPHA)
        s.fill((22, 20, 30, int(230 * sk)))
        surf.blit(s, panel)
        aa_rect(surf, AMBER, panel, 2, border_radius=8)
        tsz = 26                                      # один размер на все слайды — по самому длинному заголовку
        while tsz > 16 and max(font(tsz, True).size(tr(t_))[0] for t_, _ in self.intro_slides) > panel.w - 40:
            tsz -= 1
        draw_text(surf, title, (panel.centerx, panel.y + 20 + (26 - tsz) // 2), tsz, AMBER, bold=True, center=True,
                  alpha=255 * sk)
        draw_wrapped(surf, text, (panel.centerx, panel.y + 70), panel.w - 50, 19, WHITE, center=True,
                     line_gap=4, limit=n)
        draw_text(surf, f"{idx + 1}/{len(self.intro_slides)}   " + ("[ тап — далее ]" if TOUCH["on"] else "[ клик — далее ]"),
                  (panel.centerx, panel.bottom - 34), 15, GREY, center=True)

    # ----- хаб (мастерская) -----
    HUB_COLS, HUB_ROWS = 4, 2       # карточек на странице очереди

    def _hub_pages(self):
        per = self.HUB_COLS * self.HUB_ROWS
        return max(1, (len(self.available_jobs()) + per - 1) // per)

    def _hub_job_rects(self):
        """Карточки клиентов с крупной картинкой коляски, по 8 на страницу."""
        out = []
        per = self.HUB_COLS * self.HUB_ROWS
        page = min(getattr(self, "hub_page", 0), self._hub_pages() - 1)
        x0, y0, w, h, gx, gy = 60, 124, 200, 250, 14, 12
        for i, jid in enumerate(self.available_jobs()[page * per:(page + 1) * per]):
            out.append((jid, pygame.Rect(x0 + (i % self.HUB_COLS) * (w + gx),
                                         y0 + (i // self.HUB_COLS) * (h + gy), w, h)))
        return out

    def _draw_hub_note(self, surf, job, r, done):
        """Записка клиента у карточки: с чем пришёл (или спасибо, если уже починено)."""
        talk = CLIENT_TALK.get(job["id"], {})
        thanks = job.get("thanks") or ((job.get("variants") or [{}])[0].get("thanks", ""))   # у заданий с вариантами — в варианте
        line = tr(thanks if done else (talk.get("intro") or [""])[0])
        if not line:
            return
        name, _, text = line.partition(":")
        text = (text or line).strip()
        w = 320
        lines = wrap_lines(tr(text), w - 28, 14)[:5]
        h = 38 + len(lines) * (font(14).get_height() + 2) + 10
        right = 60 + self.HUB_COLS * 214 - 14 if self.scene == "hub" else WIDTH - 12   # не заезжать на кнопки справа
        x = min(max(12, r.centerx - w // 2), right - w)
        y = r.bottom + 6 if r.bottom + 6 + h < HEIGHT - 50 else r.y - h - 6
        k = ease_back((self.t - self._note_t(job["id"])) / 0.25)
        box = Surf((w, h), pygame.SRCALPHA)
        aa_rect(box, (238, 226, 196, 245), box.get_rect(), border_radius=8)
        aa_rect(box, (120, 92, 52), box.get_rect(), 2, border_radius=8)
        draw_text(box, ("✔ " if done else "✉ ") + (name.strip() if text != line else job["client"]),
                  (14, 9), 14, (110, 70, 30), bold=True)
        draw_wrapped(box, text, (14, 34), w - 28, 14, (52, 40, 30), max_lines=5)
        if k < 1:
            box = TF.rotozoom(box, 0, max(0.05, k))
        surf.blit(box, box.get_rect(center=(x + w // 2, y + h // 2)))

    def _note_t(self, jid):
        if getattr(self, "_note_jid", None) != jid:
            self._note_jid, self._note_t0 = jid, self.t
        return self._note_t0

    def _hub_arrow_rects(self):
        """Листание очереди: ◀ и ▶ под карточками (только если страниц больше одной)."""
        if self._hub_pages() < 2:
            return []
        return [(-1, pygame.Rect(60, 642, 54, 30)), (1, pygame.Rect(60 + 4 * 214 - 14 - 54, 642, 54, 30))]

    def _hub_garage_rect(self):
        return pygame.Rect(WIDTH - 360, HEIGHT - 150, 300, 54)

    def _hub_ending_rect(self):
        return pygame.Rect(WIDTH - 360, HEIGHT - 80, 300, 54)

    def _hub_guild_rect(self):
        return pygame.Rect(WIDTH - 360, HEIGHT - 220, 300, 54)

    def _hub_seat_rect(self):
        return pygame.Rect(WIDTH - 360, HEIGHT - 290, 300, 54)

    def draw_hub(self, surf):
        self._bg(surf, "bg_workshop.png", WOOD)
        self._topbar(surf, "Мастерская")
        draw_text(surf, "Кто сегодня в очереди на ремонт:", (60, 86), 20, WHITE, bold=True)
        mouse = mouse_pos()
        note = None
        for i, (jid, rect) in enumerate(self._hub_job_rects()):
            job = self.job_by_id(jid)
            done = jid in self.done
            dy = int(60 * (1 - appear(self.st, 0.05 * i, 0.4)))
            b = Button(rect, "", GOOD if done else AMBER)
            r = b.draw(surf, mouse, enabled=True, active=done, offset=(0, dy))
            # крупно — коляска клиента, в углу — сам клиент
            hov = rect.collidepoint(mouse)
            surf.blit(load_image(job["chair_art"], (184, 145), AMBER), (r.x + 8, r.y + 6 - (3 if hov else 0)))
            ring = pygame.Rect(r.x + 6, r.y + 104, 58, 58)
            aa_circle(surf, (20, 18, 26), ring.center, 31)
            aa_circle(surf, GOOD if done else AMBER, ring.center, 31, 2)
            surf.blit(load_image(job["client_art"], (52, 52), GHOST), (ring.x + 3, ring.y + 3))
            # имя (до 2 строк) и поломка (хотя бы строка) — над подписью «РУЧНАЯ/ЭЛЕКТРО»; крупный шрифт — мельче
            avail = r.bottom - 26 - (r.y + 162)
            for nsz in (15, 14, 13, 12, 11):
                nl = len(wrap_lines(job["client"], r.w - 24, nsz))
                tl = (avail - nl * font(nsz).get_height() - 2) // font(12).get_height()
                if nl <= 2 and tl >= 1:
                    break
            ny = draw_wrapped(surf, job["client"], (r.x + 12, r.y + 162), r.w - 24, nsz, WHITE, max_lines=2, line_gap=0)
            draw_wrapped(surf, job["title"], (r.x + 12, ny + 2), r.w - 24, 12, GREY, max_lines=max(1, min(3 - min(nl, 2), tl)))
            power = job.get("kind") == "power"
            draw_text(surf, "ЭЛЕКТРО" if power else "РУЧНАЯ",
                      (r.x + 12, r.bottom - 22), 12, CYAN if power else AMBER, bold=True)
            if done:
                draw_text(surf, "✔ готово", (r.right - 12, r.bottom - 22), 13, GOOD, right=True)
            if hov:
                note = (job, r, done)
        pages = self._hub_pages()
        if pages > 1:
            page = min(getattr(self, "hub_page", 0), pages - 1)
            for d, rect in self._hub_arrow_rects():
                Button(rect, "◀" if d < 0 else "▶", AMBER).draw(surf, mouse)
            cx = (self._hub_arrow_rects()[0][1].right + self._hub_arrow_rects()[1][1].x) // 2
            for k in range(pages):
                aa_circle(surf, AMBER if k == page else DIM, (cx + (k - (pages - 1) / 2) * 22, 657), 6)
        # призрак-наставник в углу
        if barty_on():
            blit_idle(surf, load_image("ghost.png", (150, 200), CYAN), (WIDTH - 220, 120), self.t,
                      "float", k=ease_back((self.st - 0.3) / 0.5))
        seat_ok = self.tutorial_ok()
        Button(self._hub_seat_rect(), "КАБИНЕТ ПОСАДКИ", GOOD,
               sub=((f"примерки {len(self.seat_done)}/{len(SEAT_CASES)}" + (" · зачёт ✔" if self.seat_quiz_ok else ""))
                    if seat_ok
                    else "откроется после первого ремонта")).draw(surf, mouse, enabled=seat_ok)
        guild_ok = self.guild_unlocked()
        Button(self._hub_guild_rect(), "ГИЛЬДИЯ КОЛЁСНИКОВ", CYAN,
               sub=("про-ремонт: уровень техника" if guild_ok
                    else f"откроется после {GUILD_REQ} ремонтов")).draw(surf, mouse, enabled=guild_ok)
        gb = Button(self._hub_garage_rect(), "ГАРАЖ-КОЛЛЕКЦИЯ", PURPLE)
        gb.draw(surf, mouse)
        if self.user_done_count() >= len(JOBS):
            Button(self._hub_ending_rect(), "НА ВЕЧЕРИНКУ! ", GOOD).draw(surf, mouse)
        counter = f"Починено: {self.user_done_count()}/{len(JOBS)}"
        if guild_ok:
            counter += f"   ·   Гильдия: {self.tech_done_count()}/{len(TECH_JOBS)}"
        counter += "   ·   Esc — на титул/выход"
        draw_text(surf, counter, (60, HEIGHT - 40), 16, GHOST)
        if note:                                      # записка клиента — поверх всего (не уходит под кнопки справа)
            self._draw_hub_note(surf, *note)

    # ================================================================ #
    #  КАБИНЕТ ПОСАДКИ: уроки, примерка (ползунки + живая поза), проверка
    # ================================================================ #
    def open_seating(self):
        for q in SEAT_QUIZ:                                  # верный ответ — не всегда первым
            random.shuffle(q["options"])
        self.seatc = dict(tab="lessons", lesson=0, case=0, cfg=None, drag=None,
                          quiz=0, picked=None, score=0, quiz_done=False, solved=False,
                          demo_good=False, demo_k=0.0, xray=True)
        self._seat_load_case(0)
        self.seatc["say"] = SEAT_MENTOR["intro"]
        self.scene = "seating"

    def _seat_load_case(self, i):
        c = SEAT_CASES[i]
        cfg = dict(c["start"])
        cfg.setdefault("tilt", 0)
        self.seatc.update(case=i, cfg=cfg, solved=False, view=c.get("view", "side"), focus=None)
        if c.get("view"):                                   # перекос/поворот: сбоку не видно — Мортимер подсказывает
            self.seatc["say"] = SEAT_MENTOR["view_" + c["view"]]
        else:
            self.seatc["say"] = SEAT_MENTOR["fit"]

    @staticmethod
    def seat_eval(case, cfg):
        """Оценка посадки: список проверок (ключ, ок?, текст) + параметры позы для рисунка.
        Вид клиента: сбоку (по умолчанию), спереди — перекос таза, сверху — поворот таза."""
        view = case.get("view")
        if view == "front":
            return Game._seat_eval_front(case, cfg)
        if view == "top":
            return Game._seat_eval_top(case, cfg)
        return Game._seat_eval_side(case, cfg)

    @staticmethod
    def _seat_side_cfg(case):
        """Клиент с перекосом/поворотом сбоку: по меркам — сбоку посадка ровная (проблема видна спереди/сверху)."""
        b = case["body"]
        return dict(depth=b["thigh"] - 5, leg=b["shank"], back_h=sum(case["back"]) // 2,
                    back_a=sum(case["angle"]) // 2, tilt=0)

    @staticmethod
    def _seat_eval_front(case, cfg):
        """Вид спереди — перекос таза. Причины в коляске (Permobil): гамак, широкое сиденье, подножки
        на разной высоте. Исправимый — убрать причины; неисправимый (fixed) — подкладка под ВЫСОКУЮ сторону."""
        b, fx, keys = case["body"], case.get("fixed", {}), case["sliders"]
        hip, sh = b["hip"], b["shank"]
        checks, obl, shift = [], 0.0, 0.0
        if "base" in keys:
            if cfg["base"]:
                checks.append(("base", True, "Жёсткая основа: таз не проваливается"))
            else:
                checks.append(("base", False, "Гамак провисает: таз проваливается к одной стороне"))
                obl += 4
        if "seat_w" in keys:
            w = cfg["seat_w"]
            if w < hip:
                checks.append(("seat_w", False, "Сиденье уже бёдер: давит на бёдра"))
            elif w > hip + 2:
                checks.append(("seat_w", False, "Сиденье шире бёдер: таз съезжает и опускается на одну сторону"))
                obl += 0.8 * (w - hip - 2)
                shift = -0.5 * (w - hip - 2)
            else:
                checks.append(("seat_w", True, "Ширина сиденья по бёдрам"))
        if "foot_l" in keys:
            fl, fr = cfg["foot_l"], cfg["foot_r"]
            for key, v, hi_t, lo_t, ok_t in (
                    ("foot_l", fl, "Левая подножка высоко: колено задрано", "Левая подножка низко: стопа не стоит",
                     "Левая подножка по голени"),
                    ("foot_r", fr, "Правая подножка высоко: колено задрано", "Правая подножка низко: стопа не стоит",
                     "Правая подножка по голени")):
                if v < sh - 1.5:
                    checks.append((key, False, hi_t))
                elif v > sh + 1.5:
                    checks.append((key, False, lo_t))
                else:
                    checks.append((key, True, ok_t))
            if abs(fl - fr) > 1:
                checks.append(("feet", False, "Подножки на разной высоте: таз перекашивается"))
            if abs(fl - fr) > 1:                             # 1 см — в допуске
                obl += 1.2 * (fl - fr)                       # выше правая подножка — правая сторона таза выше
        pose = dict(shift=shift)
        if fx:                                                # неисправимый перекос: таз не выпрямляется
            high, gap = fx["high"], fx["gap"]
            obl = fx["obl"] * high                           # + — левая сторона ниже
            filled = cfg.get("build", 0) * high               # > 0 — подкладка под высокой стороной
            if cfg.get("build", 0) == 0:
                checks.append(("build", False, "Под высокой стороной зазор: вся нагрузка на нижнюю седалищную кость"))
            elif filled < 0:
                checks.append(("build", False, "Подкладка под НИЖНЕЙ стороной: неисправимый перекос так не выпрямить — "
                                               "боль и давление"))
            elif filled < gap - 0.5:
                checks.append(("build", False, "Зазор под высокой стороной заполнен не до конца"))
            elif filled > gap + 0.5:
                checks.append(("build", False, "Подкладка выше зазора: теперь перегружена высокая сторона"))
            else:
                checks.append(("build", True, "Высокая сторона заполнена: давление ровное, голова ровнее"))
            ok_b = gap - 0.5 <= filled <= gap + 0.5
            pose.update(gap_cm=max(0.0, gap - max(0, filled)), gap_side=high,
                        lean=obl * (0.15 if ok_b else (0.9 if filled < 0 else 0.6)))
            low_key, high_key = ("press_l", "press_r") if high > 0 else ("press_r", "press_l")
            pose[low_key] = filled < gap - 0.5
            pose[high_key] = filled > gap + 0.5
            status = "Перекос неисправимый: учитываем, не выпрямляем"
        else:
            pose["lean"] = obl * 0.6
            pose["press_l"], pose["press_r"] = obl > 2, obl < -2
            status = "Таз ровный" if abs(obl) < 1 else f"Перекос таза: {abs(obl):.0f}°"
        ok = all(o for _, o, _ in checks)
        pose.update(obl=max(-14.0, min(14.0, obl)), ok=ok, status=status)
        return checks, pose

    @staticmethod
    def _seat_eval_top(case, cfg):
        """Вид сверху — поворот таза. Узкое сиденье разворачивает таз (Permobil); неисправимый поворот учитывают:
        глубина сиденья своя для каждой ноги (по длинной ноге, короткую сторону укорачивают)."""
        b, fx = case["body"], case.get("fixed", {})
        hip = b["hip"]
        rot = fx.get("rot", 0.0)
        checks, shift = [], 0.0
        w = cfg["seat_w"]
        if w < hip:
            checks.append(("seat_w", False, "Сиденье уже бёдер: таз разворачивается, чтобы поместиться"))
            rot += math.copysign(1.5 * (hip - w), rot or 1)
        elif w > hip + 2:
            checks.append(("seat_w", False, "Сиденье шире бёдер: таз съезжает вбок"))
            shift = 0.5 * (w - hip - 2)
        else:
            checks.append(("seat_w", True, "Ширина сиденья по бёдрам"))
        press = {}
        for key, sd, thigh, long_t, short_t, ok_t in (
                ("depth_l", -1, b.get("thigh_l", b["thigh"]), "Слева край подушки давит под колено",
                 "Слева бедру не хватает опоры", "Глубина слева по бедру"),
                ("depth_r", 1, b.get("thigh_r", b["thigh"]), "Справа край подушки давит под колено",
                 "Справа бедру не хватает опоры", "Глубина справа по бедру")):
            tgt, d = thigh - 5, cfg[key]
            press[sd] = d > tgt + 2
            if d > tgt + 2:
                checks.append((key, False, long_t))
            elif d < tgt - 3:
                checks.append((key, False, short_t))
            else:
                checks.append((key, True, ok_t))
        ok = all(o for _, o, _ in checks)
        status = ("Поворот учли: глубина своя для каждой ноги" if ok else
                  "Таз развёрнут сильнее: сиденье узкое" if w < hip else
                  "Сиденье широкое: таз съезжает вбок" if w > hip + 2 else "Поворот таза: подстрой сиденье под ноги")
        return checks, dict(rot=max(-16.0, min(16.0, rot)), shift=shift, ok=ok, status=status, knee_press=press)

    @staticmethod
    def _seat_eval_side(case, cfg):
        """Вид сбоку. Правила — из руководства Permobil; карта терапевта задаёт диапазоны спинки и угла."""
        b = case["body"]
        tgt_depth, tgt_leg = b["thigh"] - 5, b["shank"]
        d, lg, bh, ba, tl = cfg["depth"], cfg["leg"], cfg["back_h"], cfg["back_a"], cfg.get("tilt", 0)
        lo_b, hi_b = case["back"]
        lo_a, hi_a = case["angle"]
        plate = case["seat_h"] - lg - 1                              # подножка над полом, см
        checks = []
        if d > tgt_depth + 2:
            checks.append(("depth", False, "Сиденье глубже нормы: край давит под колени, тело сползает"))
        elif d < tgt_depth - 3:
            checks.append(("depth", False, "Сиденье коротко: бёдра без опоры, давление на седалищные бугры"))
        else:
            checks.append(("depth", True, "Глубина сиденья по мерке"))
        if lg < tgt_leg - 1.5:
            checks.append(("leg", False, "Подножка высоко: колени выше бёдер, давление на бугры и крестец"))
        elif lg > tgt_leg + 1.5:
            checks.append(("leg", False, "Подножка низко: стопы не стоят, тело сползает к краю"))
        else:
            checks.append(("leg", True, "Стопы стоят на подножке, бедро лежит на сиденье"))
        if plate < 5:
            checks.append(("floor", False, f"До пола {max(0, plate):.0f} см: подножка цепляет пороги (нужно ≥ 5 см)"))
        if bh < lo_b:
            checks.append(("back_h", False, "Спинка низко: корпусу не на что опереться"))
        elif bh > hi_b:
            checks.append(("back_h", False, "Спинка выше, чем в карте терапевта"
                           + (": мешает лопаткам и толчку" if case["kind"] == "manual" and not case.get("tilt") else "")))
        else:
            checks.append(("back_h", True, "Высота спинки по карте"))
        if ba < lo_a:
            checks.append(("back_a", False, "Спинка слишком прямая: корпус «стекает» вниз"))
        elif ba > hi_a:
            checks.append(("back_a", False, "Спинка слишком откинута"
                           + (" без наклона сиденья: сдвиг тканей" if tl < 20 else "")))
        else:
            checks.append(("back_a", True, "Угол спинки по карте"))
        if case.get("tilt"):
            checks.append(("tilt", tl >= case["tilt"],
                           f"Позиция разгрузки: наклон ≥ {case['tilt']}°" if tl >= case["tilt"]
                           else f"Нет разгрузки: наклон {tl}° — нужно не меньше {case['tilt']}°"))
        # поза (для рисунка): завал таза назад, сползание, колени вверх, стопы висят
        deep = max(0.0, d - tgt_depth - 2)
        high = max(0.0, tgt_leg - 1.5 - lg)
        low = max(0.0, lg - tgt_leg - 1.5)
        p = 3.0 * deep + 2.5 * high + 2.0 * low + 2.5 * max(0, lo_b - bh) + 1.5 * max(0, lo_a - ba)
        p += 0.8 * max(0, ba - hi_a) if tl < 20 else 0
        slide = 0.8 * deep + 0.8 * low + (0.25 * max(0, ba - hi_a) if tl < 20 else 0)
        pose = dict(p=min(26.0, p), slide=min(10.0, slide), deep=deep > 0, short=d < tgt_depth - 3,
                    knee_up=high > 0, dangle=low > 0)
        return checks, pose

    @staticmethod
    def _seat_measure_text(case):
        """Мерки клиента одной строкой (каждое слово — через словарь: в EN не остаётся кириллицы)."""
        b, cm = case["body"], tr("см")
        if case.get("view") == "top":
            return tr(f"Мерки: бедро слева {b['thigh_l']} см · справа {b['thigh_r']} см · "
                      f"ширина бёдер {b['hip']} см · голень {b['shank']} см")
        if case.get("view") == "front":
            return tr(f"Мерки: ширина бёдер {b['hip']} см · голень {b['shank']} см · бедро {b['thigh']} см")
        return (f"{tr('Мерки')}: {tr('бедро')} {b['thigh']} {cm} · {tr('голень')} {b['shank']} {cm} · "
                f"{tr('лопатка')} {b['scap']} {cm} · {tr('плечо')} {b['shoulder']} {cm}")

    def _seat_canvas(self):
        return pygame.Rect(24, 176, 730, 488)

    def _seat_demo_toggle_rect(self):
        cv = self._seat_canvas()
        return pygame.Rect(cv.right - 238, cv.y + 8, 228, 32)

    def _draw_seat_mentor(self, surf):
        """Мортимер и его реплика над схемой (печать по буквам)."""
        line = self.seatc.get("say") or SEAT_MENTOR["intro"]
        bubble = pygame.Rect(96, 110, 658, 60)
        s = Surf(bubble.size, pygame.SRCALPHA)
        s.fill((30, 22, 40, 232))
        surf.blit(s, bubble)
        aa_rect(surf, PURPLE, bubble, 2, border_radius=8)
        blit_idle(surf, load_image("mentor_necro_head.png", (68, 68), PURPLE), (24, 104), self.t, "breathe")
        sz = 14                                       # крупный текст: мельче, но реплика целиком в плашке
        while sz > 10 and len(wrap_lines(line, bubble.w - 24, sz)) * (font(sz).get_height() + 2) > bubble.h - 10:
            sz -= 1
        draw_wrapped(surf, line, (bubble.x + 12, bubble.y + 5), bubble.w - 24, sz, (226, 214, 246),
                     limit=self.typed("seat_say", line, cps=95), max_lines=3)

    def _seat_slider_rects(self):
        c = SEAT_CASES[self.seatc["case"]]
        row_h = ((len(SEAT_CASES) + 1) // 2) * 40
        y0 = 112 + row_h + 26
        keys = c.get("sliders") or ["depth", "leg", "back_h", "back_a"] + (["tilt"] if c.get("tilt") else [])
        return [(k, pygame.Rect(800, y0 + i * 44, 290, 8)) for i, k in enumerate(keys)]

    def _seat_tab_rects(self):
        return [(t, pygame.Rect(24 + i * 214, 64, 204, 38))
                for i, t in enumerate(("lessons", "fit", "quiz"))]

    def _seat_list_rects(self):
        """Левый столбец вкладок «Уроки»/«Примерка»: пункты списка."""
        if self.seatc["tab"] == "lessons":
            items = SEAT_LESSONS
            return [(i, pygame.Rect(780 + (i % 2) * 238, 112 + (i // 2) * 44, 230, 38)) for i in range(len(items))]
        elif self.seatc["tab"] == "fit":
            items = SEAT_CASES
            return [(i, pygame.Rect(780 + (i % 2) * 238, 112 + (i // 2) * 40, 230, 35)) for i in range(len(items))]
        return []

    def _seat_quiz_rects(self):
        q = SEAT_QUIZ[self.seatc["quiz"]]
        return [(i, pygame.Rect(780, 260 + i * 92, 476, 82)) for i in range(len(q["options"]))]

    def _seat_btn_rect(self):
        return pygame.Rect(780, 612, 476, 48)

    def _seat_back_rect(self):
        return pygame.Rect(WIDTH - 230, 64, 206, 38)

    def _seat_set_from_x(self, key, x):
        track = dict(self._seat_slider_rects())[key]
        _, _, lo, hi = SEAT_SLIDERS[key]
        v = round(lo + (hi - lo) * max(0.0, min(1.0, (x - track.x) / track.w)))
        if v != self.seatc["cfg"][key]:
            self.seatc["cfg"][key] = v
            snd("ratchet")

    def handle_seating_event(self, event):
        """Перетаскивание ползунков примерки (клики — в click_seating)."""
        sc = self.seatc
        if sc["tab"] != "fit" or sc["solved"]:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for k, tr_ in self._seat_slider_rects():
                if tr_.inflate(30, 30).collidepoint(event.pos):
                    sc["drag"] = k
                    self._seat_set_from_x(k, event.pos[0])
                    return True
        elif event.type == pygame.MOUSEMOTION and sc["drag"]:
            self._seat_set_from_x(sc["drag"], event.pos[0])
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and sc["drag"]:
            sc["drag"] = None
            return True
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT) and sc.get("focus"):
            k = sc["focus"]
            _, _, lo, hi = SEAT_SLIDERS[k]
            sc["cfg"][k] = max(lo, min(hi, sc["cfg"][k] + (1 if event.key == pygame.K_RIGHT else -1)))
            snd("ratchet")
            return True
        return False

    def click_seating(self, m):
        sc = self.seatc
        if self._seat_back_rect().collidepoint(m):
            self.scene = "hub"
            return
        for t, r in self._seat_tab_rects():
            if r.collidepoint(m):
                sc["tab"] = t
                sc["say"] = SEAT_MENTOR[t]
                snd("tick")
                return
        for i, r in self._seat_list_rects():
            if r.collidepoint(m):
                if sc["tab"] == "lessons":
                    sc["lesson"] = i
                    sc["demo_good"] = False
                    sc["say"] = SEAT_MENTOR["lesson"][i % len(SEAT_MENTOR["lesson"])]
                else:
                    self._seat_load_case(i)
                snd("tick")
                return
        if sc["tab"] == "lessons":
            if self._seat_demo_toggle_rect().collidepoint(m):
                sc["demo_good"] = not sc.get("demo_good", False)
                snd("ghost")
                return
        elif sc["tab"] == "fit":
            if self._seat_demo_toggle_rect().collidepoint(m):
                cv_ = SEAT_CASES[sc["case"]].get("view")
                if cv_:                                     # перекос/поворот: вид спереди (сверху) ⇄ сбоку
                    sc["view"] = "side" if sc.get("view") == cv_ else cv_
                    sc["say"] = SEAT_MENTOR["side_ok" if sc["view"] == "side" else "view_" + cv_]
                elif self.SEAT_BODY_ON:
                    sc["xray"] = not sc.get("xray", True)
                else:
                    return
                snd("tick")
                return
            for k, r in self._seat_slider_rects():
                if r.inflate(30, 30).collidepoint(m):
                    sc["focus"] = k
            if self._seat_btn_rect().collidepoint(m):
                case = SEAT_CASES[sc["case"]]
                if sc["solved"]:
                    nxt = (sc["case"] + 1) % len(SEAT_CASES)
                    self._seat_load_case(nxt)
                    return
                checks, _ = self.seat_eval(case, sc["cfg"])
                bad = [t for k, ok, t in checks if not ok]
                if bad:
                    snd("bad")
                    sc["say"] = SEAT_MENTOR["fail"]
                    self.flash("Ещё не так: " + bad[0], BAD, 3)
                else:
                    sc["solved"] = True
                    sc["say"] = SEAT_MENTOR["solved"]
                    self.seat_done.add(case["id"])
                    self.save_progress()
                    snd("fanfare")
                    self.flash(case["fact"], GOOD, 6)
        elif sc["tab"] == "quiz":
            if sc["quiz_done"]:
                if self._seat_btn_rect().collidepoint(m):
                    sc.update(quiz=0, picked=None, score=0, quiz_done=False)
                    for q in SEAT_QUIZ:
                        random.shuffle(q["options"])
                return
            if sc["picked"] is None:
                for i, r in self._seat_quiz_rects():
                    if r.collidepoint(m):
                        sc["picked"] = i
                        ok = SEAT_QUIZ[sc["quiz"]]["options"][i][1]
                        sc["score"] += 1 if ok else 0
                        sc["say"] = SEAT_MENTOR["right" if ok else "wrong"]
                        snd("ok" if ok else "bad")
                        return
            elif self._seat_btn_rect().collidepoint(m):
                if sc["quiz"] + 1 < len(SEAT_QUIZ):
                    sc.update(quiz=sc["quiz"] + 1, picked=None)
                else:
                    sc["quiz_done"] = True
                    sc["say"] = SEAT_MENTOR["pass" if sc["score"] >= SEAT_QUIZ_PASS else "nopass"]
                    if sc["score"] >= SEAT_QUIZ_PASS:
                        self.seat_quiz_ok = True
                        self.save_progress()
                        snd("fanfare")

    # ---------- художественная отрисовка костей, черепа и магии Мортимера ----------
    def _draw_bone_seg(self, surf, p0, p1, r0, r1=None, col=(232, 224, 204), outline=(36, 30, 42), joint=True):
        """Анатомическая кость с утолщениями эпифизов на концах, светотенью и контуром."""
        if r1 is None:
            r1 = r0
        x0, y0 = float(p0[0]), float(p0[1])
        x1, y1 = float(p1[0]), float(p1[1])
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1.0:
            return
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux
        steps = ((0.0, 1.15), (0.14, 1.25), (0.30, 0.78), (0.50, 0.70), (0.70, 0.78), (0.86, 1.22), (1.0, 1.12))
        left_pts, right_pts, sh_pts, hi_pts = [], [], [], []
        for t, wf in steps:
            cx, cy = x0 + dx * t, y0 + dy * t
            rw = (r0 * (1.0 - t) + r1 * t) * wf
            left_pts.append((cx + nx * rw, cy + ny * rw))
            right_pts.append((cx - nx * rw, cy - ny * rw))
            sh_pts.append((cx - nx * rw * 0.25, cy - ny * rw * 0.25))
            hi_pts.append((cx + nx * rw * 0.38, cy + ny * rw * 0.38))
        poly = left_pts + list(reversed(right_pts))
        DR.polygon(surf, col, poly)
        sh_poly = sh_pts + list(reversed(right_pts))
        DR.polygon(surf, _shade(col, 0.80), sh_poly)
        DR.polygon(surf, outline, poly, 2)
        if len(hi_pts) >= 2:
            DR.lines(surf, (250, 246, 236), False, hi_pts, max(1, int(min(r0, r1) * 0.45)))
        if joint:
            for (jx, jy), jr in (((x0, y0), r0 * 1.18), ((x1, y1), r1 * 1.15)):
                aa_circle(surf, _shade(col, 0.86), (int(jx), int(jy)), max(2, int(jr)))
                aa_circle(surf, col, (int(jx - 0.5), int(jy - 0.5)), max(1, int(jr * 0.78)))
                aa_circle(surf, outline, (int(jx), int(jy)), max(2, int(jr)), 2)

    def _draw_necro_thread(self, surf, p_staff, p_target, col=PURPLE, active=False, phase=0.0):
        """Некромантская нить управления от посоха Мортимера к кости скелета."""
        x0, y0 = float(p_staff[0]), float(p_staff[1])
        x3, y3 = float(p_target[0]), float(p_target[1])
        mx, my = (x0 + x3) * 0.5, min(y0, y3) - 26.0 - 9.0 * wsin(self.t * 2.4 + phase)
        pts = []
        n = 16
        for i in range(n + 1):
            t = i / n
            u = 1.0 - t
            bx = u * u * x0 + 2 * u * t * mx + t * t * x3
            by = u * u * y0 + 2 * u * t * my + t * t * y3 + 3.2 * wsin(t * math.pi * 2 + self.t * 4.0 + phase)
            pts.append((bx, by))
        glow_c = col if active else (152, 114, 218)
        DR.lines(surf, _shade(glow_c, 0.62), False, pts, 3 if active else 2)
        DR.lines(surf, (232, 210, 255) if active else glow_c, False, pts, 1)
        if DISPLAY["glow"]:                                  # искра бежит по нити — частица (настройка «Свечение»)
            u_spark = 0.5 if calm() else (self.t * 0.75 + phase * 0.23) % 1.0
            idx = min(n, int(u_spark * n))
            sx, sy = int(pts[idx][0]), int(pts[idx][1])
            aa_circle(surf, GHOST if not active else col, (sx, sy), 3)
        aa_circle(surf, glow_c, (int(x3), int(y3)), 4)

    def _draw_necro_puppeteer(self, surf, rect, targets, bad_flag=False):
        """Фигура некроманта Мортимера слева в зале с посохом-черепом и магическими нитями к скелету."""
        nh = min(232, max(164, int(rect.h * 0.65)))
        nw = int(nh * 288 / 540)
        nx = rect.x + 8
        ny = rect.bottom - nh - 22
        rcx, rcy = nx + nw // 2, rect.bottom - 20
        DR.ellipse(surf, (68, 46, 98), (rcx - 54, rcy - 9, 108, 18), 2)
        DR.ellipse(surf, (118, 80, 166), (rcx - 38, rcy - 5, 76, 10), 1)
        blit_idle(surf, load_image("mentor_necro.png", (nw, nh), PURPLE), (nx, ny), self.t, "breathe")
        staff_x = nx + int(nw * 0.14)
        staff_y = ny + int(nh * 0.08) + int(3.0 * wsin(self.t * 2.5))
        pulse = 0.65 + 0.35 * wsin(self.t * 4.5)
        orb_col = BAD if bad_flag else GHOST
        add_glow(surf, (staff_x, staff_y), int(20 * pulse), PURPLE, 0.85)
        add_glow(surf, (staff_x, staff_y), int(10 * pulse), orb_col, 0.9)
        for i, (tx, ty, col_t, is_act) in enumerate(targets):
            self._draw_necro_thread(surf, (staff_x, staff_y), (tx, ty), col=col_t, active=is_act, phase=i * 1.3)

    _SEAT_RIGS = None
    SEAT_BODY_ON = False                # тела клиентов в «Рентгене» (в работе: кукла из рисунков) — пока выкл
    SEAT_XRAY = False                   # тело — голубоватый «рентгеновский» силуэт вместо цветного рисунка
    SEAT_SLIM = 0.65                    # тело клиента поперёк костей и голова — на 35 % меньше рисунка

    def _draw_seat_puppet(self, surf, case, T, J):
        """Тело клиента — «вырезная кукла» из рисунка сбоку (art_tests/seat_bodies.py): каждая часть
        поворачивается и масштабируется по своей кости скелета. False — у клиента нет такого рисунка."""
        if Game._SEAT_RIGS is None:
            try:
                with open(os.path.join(ASSETS_DIR, "seat_bodies.json"), encoding="utf-8") as f:
                    Game._SEAT_RIGS = json.load(f)
            except Exception:
                Game._SEAT_RIGS = {}
        rig = Game._SEAT_RIGS.get(case["id"])
        if not rig:
            return False
        J = dict(J, neck=(J["sh"][0] + (J["head"][0] - J["sh"][0]) * 0.35,
                          J["sh"][1] + (J["head"][1] - J["sh"][1]) * 0.35))
        J["elbow"] = (J["sh"][0] + 5.0, J["sh"][1] - 24.0)        # рука — как у скелета (_draw_seat_flesh)
        J["hand"] = (J["elbow"][0] + 21.0, J["elbow"][1] + 1.5)
        rs = _rs(surf)
        parts = sorted(rig["parts"].values(), key=lambda q: q["order"])
        imgs, ratios = [], []
        for q in parts:
            key = ("seatpart", q["file"])
            img = _img_cache.get(key)
            if img is None:
                path = asset_path(q["file"])
                if not path:
                    return False
                img = _img_cache[key] = pygame.image.load(path).convert_alpha()
            ta, tb = T(*J[q["a"]]), T(*J[q["b"]])
            ls = math.hypot(q["pb"][0] - q["pa"][0], q["pb"][1] - q["pa"][1]) or 1.0
            lt = math.hypot(tb[0] - ta[0], tb[1] - ta[1]) * rs
            imgs.append((q, img, ta, tb))
            ratios.append(lt / ls)
        # масштаб торса (по нему — голова): цельный торс hip→sh или грудь mid→sh у куклы из SVG (таз отдельно)
        tsc = next((r for (q, *_), r in zip(imgs, ratios) if q["b"] == "sh"), None)
        slim = rig.get("slim", self.SEAT_SLIM)
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA) if self.SEAT_XRAY else None
        self._seat_head_img = None
        trot = None                                         # поворот торса: голова за ним, кивает на треть
        for (q, img, ta, tb), sc in zip(imgs, ratios):     # масштаб части — по её кости: суставы совпадают
            if q["a"] == "neck" and tsc:
                sc = tsc                                    # голова — в размер торса (мультяшная, крупнее черепа)
            ang_s = math.atan2(-(q["pb"][1] - q["pa"][1]), q["pb"][0] - q["pa"][0])
            ang_t = math.atan2(-(tb[1] - ta[1]), tb[0] - ta[0])
            rot = math.degrees(ang_t - ang_s)
            if q["b"] == "sh":
                trot = rot
            elif q["a"] == "neck" and trot is not None:
                rot = trot + (rot - trot) * 0.35
            # вдоль кости — точно по суставам, поперёк (толщина) и голова — уже: SEAT_SLIM
            along = sc * (slim if q["a"] == "neck" else 1.0)
            out, (ax_, ay_) = _rot_scale(img, q["pa"], math.degrees(ang_s), rot + math.degrees(ang_s),
                                         along, sc * slim)
            pos = (round(ta[0] * rs - ax_), round(ta[1] * rs - ay_))
            if layer is not None:
                pygame.Surface.blit(layer, out, pos)
                continue
            pygame.Surface.blit(surf, out, pos)
            if q["a"] == "neck":
                self._seat_head_img = (out, pos)            # лицо — ещё раз поверх черепа, полупрозрачно
        if layer is not None:                               # рентген: силуэт одним цветом + свечение по краю
            g_ = layer.copy()
            g_.fill((150, 220, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
            g_.fill((150, 220, 255, 255), special_flags=pygame.BLEND_RGB_MIN)
            sm = pygame.transform.smoothscale(g_, (max(1, g_.get_width() // 6), max(1, g_.get_height() // 6)))
            glow = pygame.transform.smoothscale(sm, g_.get_size())
            glow.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            pygame.Surface.blit(surf, glow, (0, 0))
            body = layer.copy()
            body.fill((95, 170, 220, 255), special_flags=pygame.BLEND_RGB_MULT)   # тонировать — детали видны слабо
            body.fill((90, 160, 210, 0), special_flags=pygame.BLEND_RGBA_ADD)
            body.fill((255, 255, 255, 110), special_flags=pygame.BLEND_RGBA_MULT)
            pygame.Surface.blit(surf, body, (0, 0))
            self._seat_head_img = None
        return True

    def _draw_seat_flesh(self, surf, rect, case, T, k, J):
        """«Рентген»: тело клиента сбоку по суставам скелета J (см) — полупрозрачное, кости видны внутри.
        Одежда, телосложение и приметы — SEAT_BODY по рисунку клиента."""
        st = SEAT_BODY.get(case.get("client_art"), {})
        skin = tuple(case.get("skin", (200, 190, 170)))
        bulk = st.get("bulk", 1.0)
        lay = Surf(rect.size, pygame.SRCALPHA)
        ox, oy = rect.x, rect.y

        def P(c):                                           # см -> пиксели слоя
            q = T(*c)
            return (q[0] - ox, q[1] - oy)

        def add(a, b2):
            return (a[0] + b2[0], a[1] + b2[1])

        def fwd(a, b2, d):                                  # точка на d см «вперёд» от отрезка a→b (к коленям)
            dx, dy = b2[0] - a[0], b2[1] - a[1]
            ln = math.hypot(dx, dy) or 1.0
            return (dy / ln * d, -dx / ln * d)

        shapes = []                                         # (цвет, функция рисования(слой, расширение px))

        def capsule(a, b2, r0, r1, col):
            def draw(sf, grow):
                pa, pb = P(a), P(b2)
                ra, rb = max(2, r0 * k + grow), max(2, r1 * k + grow)
                dx, dy = pb[0] - pa[0], pb[1] - pa[1]
                ln = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / ln, dx / ln
                DR.polygon(sf, col, [(pa[0] + nx * ra, pa[1] + ny * ra), (pb[0] + nx * rb, pb[1] + ny * rb),
                                     (pb[0] - nx * rb, pb[1] - ny * rb), (pa[0] - nx * ra, pa[1] - ny * ra)])
                aa_circle(sf, col, pa, int(ra))
                aa_circle(sf, col, pb, int(rb))
            shapes.append((col, draw))

        def poly(pts_cm, col):
            def draw(sf, grow):
                pts = [P(c) for c in pts_cm]
                DR.polygon(sf, col, pts)
                if grow:
                    DR.lines(sf, col, True, pts, max(1, int(grow * 2)))
            shapes.append((col, draw))

        def disc(c, r, col):
            shapes.append((col, lambda sf, grow: aa_circle(sf, col, P(c), int(max(2, r * k + grow)))))

        ex = st.get("extras", ())
        top = st.get("top") or skin
        legs = st.get("legs") or skin
        shoes = st.get("shoes") or _shade(skin, 0.8)
        hip, knee, ankle, toe = J["hip"], J["knee"], J["ankle"], J["toe"]
        mid, sh, head = J["mid"], J["sh"], J["head"]
        elbow = (sh[0] + 5.0, sh[1] - 24.0)
        hand = (elbow[0] + 21.0, elbow[1] + 1.5)
        hr = st.get("head", 10.5)
        # что сзади: хвост, крылья (рисуются первыми — под телом)
        if "fox_tail" in ex:
            capsule(hip, add(hip, (-16, 10)), 5, 9, skin)
            capsule(add(hip, (-16, 10)), add(hip, (-24, 26)), 9, 6, skin)
            disc(add(hip, (-24, 28)), 6, (246, 242, 236))
        if "dragon_tail" in ex:
            capsule(hip, add(hip, (-18, -2)), 6, 4, skin)
            capsule(add(hip, (-18, -2)), add(hip, (-32, -10)), 4, 1.5, skin)
        if "wings" in ex:
            for d, h2 in ((-3, 30), (-9, 22)):
                poly([add(sh, (-2, -4)), add(sh, (d - 14, h2)), add(sh, (d - 22, h2 - 14)),
                      add(sh, (-6, -14))], (206, 226, 255))
        # ноги: бедро, голень, стопа
        th_r = 7.0 * bulk
        capsule(hip, knee, th_r, 5.4 * bulk, legs)
        capsule(knee, ankle, 4.6 * bulk, 3.3 * bulk, legs if st.get("legs") else skin)
        capsule(ankle, toe, 3.0 * bulk, 2.4 * bulk, shoes)
        # торс: таз и живот, грудь — смещены вперёд от позвоночника
        belly = st.get("belly", 1.0)
        c1 = add(hip, fwd(hip, mid, 5.0 * bulk))
        c2 = add(mid, fwd(hip, mid, 6.5 * bulk * belly))
        c3 = add(sh, fwd(mid, sh, 4.5 * bulk))
        if st.get("blocky"):
            f1, f2 = fwd(hip, sh, 11 * bulk), fwd(hip, sh, -3)
            poly([add(hip, f2), add(hip, f1), add(sh, (f1[0] * 0.9, f1[1] * 0.9)), add(sh, f2)], skin)
        else:
            capsule(c1, c2, 9.0 * bulk, 9.5 * bulk * belly, top)
            capsule(c2, c3, 9.5 * bulk * belly, 8.5 * bulk, top)
        if "belly_scales" in ex:
            capsule(add(c2, fwd(hip, mid, 5 * bulk)), add(c3, fwd(mid, sh, 4 * bulk)), 3.5, 3, (244, 196, 130))
        # шея и голова
        capsule(sh, head, 3.6 * bulk, 3.2 * bulk, skin)
        if "long_hair" in ex:
            capsule(add(head, (-4, 6)), add(sh, (-6, -6)), 6, 4, st.get("hair", skin))
        if "bob_hair" in ex:
            disc(add(head, (-2.5, 2.5)), hr * 1.05, st.get("hair", skin))
        img = load_image(f"seat_head_{case['id']}.png", (int(hr * 2.6 * k), int(hr * 2.6 * k)), skin) \
            if asset_exists(f"seat_head_{case['id']}.png") else None
        if img is None:
            if st.get("blocky"):
                poly([add(head, (-hr, -hr)), add(head, (hr, -hr)), add(head, (hr, hr)), add(head, (-hr, hr))], skin)
            else:
                disc(head, hr, skin)
            if "big_nose" in ex:
                disc(add(head, (hr * 0.95, -1.5)), hr * 0.32, _shade(skin, 0.92))
            if "snout_s" in ex:
                capsule(add(head, (hr * 0.4, -2)), add(head, (hr * 1.35, -3.5)), 4.2, 2.0, skin)
            if "snout_d" in ex:
                capsule(add(head, (hr * 0.3, -2.5)), add(head, (hr * 1.45, -3)), 5.5, 3.2, skin)
            if "fox_ears" in ex:
                for d in (-3.5, 2.0):
                    poly([add(head, (d - 3, hr * 0.7)), add(head, (d + 1, hr * 1.7)), add(head, (d + 3.5, hr * 0.6))], skin)
            if "horns" in ex:
                for d in (-5, -1):
                    poly([add(head, (d - 1.5, hr * 0.75)), add(head, (d - 6, hr * 1.5)), add(head, (d + 1.5, hr * 0.8))],
                         (236, 214, 160))
            if "elf_ear" in ex:
                poly([add(head, (-3.5, 1)), add(head, (-hr * 1.25, hr * 0.95)), add(head, (-1.5, 4))], skin)
            if "small_ears" in ex:
                disc(add(head, (-3, 2)), hr * 0.3, _shade(skin, 0.9))
        # рука (ближняя): плечо, предплечье, кисть
        sleeve = top if (st.get("top") and not st.get("blocky")) else skin
        capsule(sh, elbow, 3.8 * bulk, 3.2 * bulk, sleeve)
        capsule(elbow, hand, 3.0 * bulk, 2.6 * bulk, skin)
        disc(add(hand, (3, 0)), 2.8 * bulk, skin)
        # контур (тёмный, шире), затем заливка — внутренние стыки не видны
        out = _shade(skin, 0.45)
        for col, draw in shapes:
            draw(lay, 1.6)
        lay.fill((*out, 255), special_flags=pygame.BLEND_RGBA_MIN)        # контур — одним цветом
        for col, draw in shapes:
            draw(lay, 0)
        lay.set_alpha(150)                                  # полупрозрачное: кости видны внутри
        surf.blit(lay, rect.topleft)
        if img is not None:
            hc = T(*head)
            im = img.copy()
            im.set_alpha(190)
            surf.blit(im, (hc[0] - im.get_width() / 2, hc[1] - im.get_height() / 2))
        if "glow_eye" in ex:
            add_glow(surf, T(*add(head, (hr * 0.45, 1))), int(6 * k), (120, 220, 255), 0.8)

    # ---------- примерка: вид спереди (перекос таза) и вид сверху (поворот таза) ----------
    def _seat_grid(self, surf, rect):
        for gx in range(rect.x + 20, rect.right - 10, 36):
            DR.line(surf, (26, 29, 40), (gx, rect.y + 8), (gx, rect.bottom - 26), 1)
        for gy in range(rect.y + 16, rect.bottom - 26, 36):
            DR.line(surf, (26, 29, 40), (rect.x + 10, gy), (rect.right - 10, gy), 1)

    def _seat_front_fit(self, surf, rect, case, cfg, pose, show_necro=True):
        """Вид спереди для примерки: коляска (основа — гамак или жёсткая, ширина, две подножки, подкладка
        под седалищную кость) и скелет с перекосом таза pose["obl"] (°, + — левая сторона ниже), изгибом
        позвоночника и наклоном головы pose["lean"]. Стиль — как у схемы урока «Перекос и поворот таза»."""
        self._seat_grid(surf, rect)
        BONE, BONE_D, OUT = (234, 226, 206), (188, 178, 156), (38, 32, 44)
        b = case["body"]
        fl, fr = cfg.get("foot_l", b["shank"]), cfg.get("foot_r", b["shank"])
        s = (rect.h - 34) / float(max(fl, fr) + b["shoulder"] + 26)      # пикселей на см: от подножек до макушки
        cx = rect.centerx + (66 if show_necro else 0)
        seat_y = rect.bottom - 14 - max(fl, fr) * s
        w = cfg.get("seat_w", b["hip"] + 1)
        half = w * s / 2
        sling = cfg.get("base", 1) == 0
        sag = 3.0 * s if sling else 0.0
        bh = sum(case["back"]) / 2
        # спинка за корпусом и колёса по бокам
        aa_rect(surf, (44, 48, 72), (cx - half, seat_y - bh * s - 6 * s, w * s, bh * s + 4 * s), border_radius=10)
        aa_rect(surf, (76, 84, 122), (cx - half, seat_y - bh * s - 6 * s, w * s, bh * s + 4 * s), 2, border_radius=10)
        for sd in (-1, 1):
            wx = cx + sd * (half + 6 * s)
            aa_rect(surf, (34, 36, 44), (wx - 2.4 * s, seat_y - 34 * s, 4.8 * s, 62 * s), border_radius=6)
            aa_rect(surf, (168, 174, 188), (wx - 0.9 * s, seat_y - 32 * s, 1.8 * s, 58 * s), border_radius=3)
            DR.line(surf, (168, 174, 188), (cx + sd * half, seat_y - 2 * s), (cx + sd * half, seat_y + 20 * s),
                    max(2, int(0.8 * s)))
        # основа: гамак провисает дугой, жёсткая — ровная доска; сверху подушка
        base = [(cx - half + (2 * half) * i / 12, seat_y + sag * math.sin(math.pi * i / 12)) for i in range(13)]
        cush = 5 * s
        top_pts = [(x, y - cush) for x, y in base]
        DR.polygon(surf, (58, 66, 112), top_pts + list(reversed(base)))
        DR.polygon(surf, (98, 110, 168), top_pts + list(reversed(base)), 2)
        DR.lines(surf, (130, 136, 156) if sling else (210, 186, 130), False, base, max(3, int(1.0 * s)))
        if sling:
            draw_text(surf, "гамак провисает", (cx + half + 10 * s, seat_y + sag - 6), 11, AMBER, bold=True)
        # подкладка под седалищную кость (− левая, + правая)
        bld = cfg.get("build", 0)
        it_dx = 7.5 * s
        if bld:
            sd = 1 if bld > 0 else -1
            bx, by_top = cx + sd * it_dx, seat_y - cush - abs(bld) * s
            aa_rect(surf, CYAN, (bx - 5 * s, by_top, 10 * s, abs(bld) * s + 1), border_radius=3)
            aa_rect(surf, WHITE, (bx - 5 * s, by_top, 10 * s, abs(bld) * s + 1), 1, border_radius=3)
        # таз: поворот на obl вокруг центра; нижняя сторона опускается к подушке
        obl = math.radians(pose.get("obl", 0.0))
        pc = (cx + pose.get("shift", 0.0) * s, seat_y - cush - 7 * s - sag * 0.5)

        def rp(dx, dy):
            return (pc[0] + dx * math.cos(-obl) - dy * math.sin(-obl), pc[1] + dx * math.sin(-obl) + dy * math.cos(-obl))
        p_col = GOOD if pose.get("ok") else AMBER
        hw = b["hip"] * 0.38 * s
        for sd in (-1, 1):                                       # крылья подвздошных костей
            wing = [rp(sd * 1.5 * s, -2 * s), rp(sd * hw * 0.55, -9 * s), rp(sd * hw * 1.05, -11 * s),
                    rp(sd * hw * 1.12, -6 * s), rp(sd * hw * 0.7, 4 * s), rp(sd * 2 * s, 6 * s)]
            DR.polygon(surf, BONE, wing)
            DR.polygon(surf, OUT, wing, 2)
            aa_circle(surf, (44, 48, 72), (int(rp(sd * hw * 0.45, 1 * s)[0]), int(rp(sd * hw * 0.45, 1 * s)[1])),
                      max(2, int(1.6 * s)))
        sac = [rp(-3.5 * s, -9 * s), rp(3.5 * s, -9 * s), rp(0, 4 * s)]
        DR.polygon(surf, BONE_D, sac)
        DR.polygon(surf, OUT, sac, 2)
        DR.line(surf, p_col, rp(-hw * 1.05, -11 * s), rp(hw * 1.05, -11 * s), max(3, int(0.9 * s)))
        DR.line(surf, (96, 104, 132), (pc[0] - hw * 1.3, pc[1] - 11 * s), (pc[0] + hw * 1.3, pc[1] - 11 * s), 1)
        ischia = {sd: rp(sd * it_dx, 6 * s) for sd in (-1, 1)}
        # ноги: бедро к нам (коротко), колено, голень вниз к подножке
        for sd, foot in ((-1, fl), (1, fr)):
            hx, hy = rp(sd * hw * 0.85, 2 * s)
            kx, ky = cx + sd * (hw * 0.95), seat_y - cush + 1 * s
            plate_y = seat_y + foot * s
            ank = min(plate_y - 1.2 * s, ky + b["shank"] * s)
            self._draw_bone_seg(surf, (hx, hy), (kx, ky), 2.2 * s, 1.9 * s, BONE, OUT)
            self._draw_bone_seg(surf, (kx, ky + 1 * s), (kx, ank), 1.7 * s, 1.4 * s, BONE, OUT)
            aa_rect(surf, BONE, (kx - 3 * s, ank - 0.6 * s, 6 * s, 2.4 * s), border_radius=3)
            aa_rect(surf, OUT, (kx - 3 * s, ank - 0.6 * s, 6 * s, 2.4 * s), 1, border_radius=3)
            aa_rect(surf, (96, 100, 116), (kx - 6 * s, plate_y, 12 * s, 2.2 * s), border_radius=2)
            if ank < plate_y - 2 * s:                           # стопа не достаёт до подножки
                DR.line(surf, AMBER, (kx, ank + 2.5 * s), (kx, plate_y), 2)
        for sd in (-1, 1):                                       # давление под седалищными костями
            over = pose.get("press_l" if sd < 0 else "press_r", False)
            ix, iy = ischia[sd]
            aa_circle(surf, BAD if over else GOOD, (int(ix), int(iy)), max(3, int(1.5 * s)))
            if over:
                add_glow(surf, (ix, iy), int(7 * s), (200, 40, 40), 0.85)
        # позвоночник: от крестца уходит к нижней стороне, выгибается и возвращается к плечам
        lean = pose.get("lean", 0.0)
        base_pt = rp(0, -9 * s)
        sh_c = (cx + lean * 1.3 * s, seat_y - cush - b["shoulder"] * 0.86 * s)
        apex = (base_pt[0] - math.sin(obl) * 22 * s + lean * 0.3 * s, (base_pt[1] + sh_c[1]) / 2)
        spine = []
        for i in range(15):
            t = i / 14
            u = 1 - t
            spine.append((u * u * base_pt[0] + 2 * u * t * apex[0] + t * t * sh_c[0],
                          u * u * base_pt[1] + 2 * u * t * apex[1] + t * t * sh_c[1]))
        DR.lines(surf, BONE_D, False, spine, max(3, int(1.4 * s)))
        for ri, vi in enumerate(range(6, 13)):                   # рёбра «гармошкой», как в уроке
            rx, ry = spine[vi]
            rw = (11 - abs(ri - 3) * 1.2) * s
            for sd in (-1, 1):
                mid = (rx + sd * rw * 0.95, ry + 2.5 * s)
                inn = (rx + sd * rw * 0.38, ry + 5.5 * s)
                DR.lines(surf, OUT, False, [(rx, ry), mid, inn], max(2, int(1.0 * s)))
                DR.lines(surf, BONE, False, [(rx, ry), mid, inn], max(1, int(0.6 * s)))
        for vx, vy in spine:
            aa_circle(surf, BONE, (int(vx), int(vy)), max(3, int(1.3 * s)))
            aa_circle(surf, OUT, (int(vx), int(vy)), max(3, int(1.3 * s)), 1)
        tl = math.radians(-lean * 1.1)
        shl = (sh_c[0] - 19 * s * math.cos(tl), sh_c[1] - 19 * s * math.sin(tl))
        shr = (sh_c[0] + 19 * s * math.cos(tl), sh_c[1] + 19 * s * math.sin(tl))
        self._draw_bone_seg(surf, (sh_c[0], sh_c[1] + 1 * s), shl, 1.2 * s, 1.3 * s, BONE, OUT)
        self._draw_bone_seg(surf, (sh_c[0], sh_c[1] + 1 * s), shr, 1.2 * s, 1.3 * s, BONE, OUT)
        for sh_, sd in ((shl, -1), (shr, 1)):
            self._draw_bone_seg(surf, sh_, (sh_[0] + sd * 2 * s, sh_[1] + 26 * s), 1.5 * s, 1.2 * s, BONE_D, OUT)
        hx_, hy_ = sh_c[0] + lean * 0.9 * s, sh_c[1] - 13 * s
        hr = 8.5 * s
        aa_circle(surf, BONE, (int(hx_), int(hy_)), int(hr))
        aa_circle(surf, OUT, (int(hx_), int(hy_)), int(hr), 2)
        aa_rect(surf, BONE, (hx_ - 4.5 * s, hy_ + 2.5 * s, 9 * s, 6.5 * s), border_radius=4)
        aa_rect(surf, OUT, (hx_ - 4.5 * s, hy_ + 2.5 * s, 9 * s, 6.5 * s), 2, border_radius=4)
        for sd in (-1, 1):
            ex, ey = hx_ + sd * 2.8 * s, hy_ - 0.5 * s
            aa_circle(surf, (26, 22, 34), (int(ex), int(ey)), max(3, int(1.8 * s)))
            aa_circle(surf, GHOST, (int(ex), int(ey)), max(1, int(0.7 * s)))
        gap = pose.get("gap_cm", 0)
        if gap > 0.4:                                            # зазор под высокой седалищной костью
            sd = pose.get("gap_side", 1)
            gx, gy = ischia[sd]
            DR.line(surf, AMBER, (gx, gy + 1.6 * s), (gx, seat_y - cush), 2)
            draw_text(surf, f"зазор под костью {gap:.0f} см", (gx + sd * 3 * s, gy + 2), 12, AMBER, bold=True,
                      right=sd < 0)
        status = pose.get("status", "")
        if status:
            draw_text(surf, status, (rect.x + 150, rect.y + 12), 12, GOOD if pose.get("ok") else AMBER, bold=True)
        if show_necro:
            low = -1 if pose.get("obl", 0) >= 0 else 1
            tg = [(hx_, hy_ - hr, PURPLE, False), (apex[0], apex[1], CYAN, False),
                  (ischia[low][0], ischia[low][1], p_col, not pose.get("ok"))]
            self._draw_necro_puppeteer(surf, rect, tg, bad_flag=not pose.get("ok"))
        draw_text(surf, "Вид спереди", (rect.right - 14, rect.y + 12), 12, GREY, bold=True, right=True)

    def _seat_top(self, surf, rect, case, cfg, pose, show_necro=True):
        """Вид сверху: сиденье (глубина слева и справа своя), спинка, колёса, таз и бёдра скелета.
        pose["rot"] — поворот таза, ° (+ — правое бедро впереди)."""
        self._seat_grid(surf, rect)
        BONE, BONE_D, OUT = (234, 226, 206), (188, 178, 156), (38, 32, 44)
        b = case["body"]
        cx = rect.centerx + (70 if show_necro else 0)
        top = rect.y + 64
        s = (rect.bottom - 36 - top) / 68.0                     # пикселей на см: от спинки до подножек
        seat_w = cfg.get("seat_w", b["hip"] + 1)
        dl, dr = cfg.get("depth_l", b["thigh"] - 5), cfg.get("depth_r", b["thigh"] - 5)
        half = seat_w * s / 2
        for sd in (-1, 1):                                       # колёса (сверху — полосы), касторы
            wx = cx + sd * (half + 5 * s)
            aa_rect(surf, (34, 36, 44), (wx - 2.2 * s, top - 8 * s, 4.4 * s, 58 * s), border_radius=6)
            aa_rect(surf, (150, 156, 170), (wx - 0.8 * s, top - 6 * s, 1.6 * s, 54 * s), border_radius=3)
            aa_rect(surf, (40, 42, 50), (cx + sd * (half - 1 * s) - 1.6 * s, top + 52 * s, 3.2 * s, 7 * s), border_radius=3)
        aa_rect(surf, (52, 58, 92), (cx - half - 2 * s, top - 8 * s, seat_w * s + 4 * s, 6 * s), border_radius=5)
        aa_rect(surf, (98, 110, 168), (cx - half - 2 * s, top - 8 * s, seat_w * s + 4 * s, 6 * s), 2, border_radius=5)
        for sd, d in ((-1, dl), (1, dr)):                        # подушка: своя глубина у каждой половины
            x0 = cx if sd > 0 else cx - half
            aa_rect(surf, (58, 66, 112), (x0, top - 2 * s, half, d * s), border_radius=6)
            aa_rect(surf, (98, 110, 168), (x0, top - 2 * s, half, d * s), 2, border_radius=6)
        for sd in (-1, 1):
            fx = cx + sd * half * 0.5
            aa_rect(surf, (90, 94, 108), (fx - 6 * s, top + 58 * s, 12 * s, 5 * s), border_radius=3)
        rot = math.radians(pose.get("rot", 0.0))
        pc = (cx + pose.get("shift", 0.0) * s, top + 7 * s)
        hip_hw = (b["hip"] / 2 - 6) * s

        def rp(dx, dy):
            return (pc[0] + dx * math.cos(rot) - dy * math.sin(rot), pc[1] + dx * math.sin(rot) + dy * math.cos(rot))
        p_col = GOOD if pose.get("ok") else AMBER
        for sd in (-1, 1):                                       # крылья таза сверху — изогнутые гребни
            crest = [rp(sd * (2 + 13 * t) * s, (-6 + 9 * t * t) * s) for t in (0, 0.25, 0.5, 0.75, 1.0)]
            DR.lines(surf, OUT, False, crest, max(5, int(2.2 * s)))
            DR.lines(surf, BONE, False, crest, max(3, int(1.5 * s)))
        sac = [rp(-3 * s, -6 * s), rp(3 * s, -6 * s), rp(0, 2 * s)]
        DR.polygon(surf, BONE_D, sac)
        DR.polygon(surf, OUT, sac, 2)
        hips = {sd: rp(sd * hip_hw, 3 * s) for sd in (-1, 1)}
        DR.line(surf, p_col, rp(-15 * s, 3 * s), rp(15 * s, 3 * s), max(3, int(0.6 * s)))
        knees = {}
        for sd in (-1, 1):
            L = (b.get("thigh_l" if sd < 0 else "thigh_r", b["thigh"]) - 7) * s   # колено чуть дальше края подушки
            ang = sd * math.radians(3) + rot * 0.3
            hx, hy = hips[sd]
            knees[sd] = (hx - L * math.sin(ang) * 0, hy + L)
            kx, ky = knees[sd]
            self._draw_bone_seg(surf, (hx, hy), (kx, ky), 1.4 * s, 1.1 * s, BONE, OUT)
            aa_circle(surf, BONE, (int(kx), int(ky)), max(3, int(2.0 * s)))
            aa_circle(surf, OUT, (int(kx), int(ky)), max(3, int(2.0 * s)), 2)
            if pose.get("knee_press", {}).get(sd):             # край подушки режет под коленом
                add_glow(surf, (kx, ky - 1 * s), int(5 * s), (200, 40, 40), 0.8)
        sh_rot = rot * 0.6                                       # грудной отдел поворачивается за тазом
        shl = (cx - 18 * s * math.cos(sh_rot), top - 4 * s - 18 * s * math.sin(sh_rot))
        shr = (cx + 18 * s * math.cos(sh_rot), top - 4 * s + 18 * s * math.sin(sh_rot))
        self._draw_bone_seg(surf, shl, shr, 1.1 * s, 1.1 * s, BONE_D, OUT)
        aa_circle(surf, BONE, (int(cx), int(top - 4 * s)), max(4, int(6 * s)))
        aa_circle(surf, OUT, (int(cx), int(top - 4 * s)), max(4, int(6 * s)), 2)
        dk = (knees[-1][1] - knees[1][1]) / s
        if abs(dk) >= 1:
            fwd, back = (knees[-1], knees[1]) if dk > 0 else (knees[1], knees[-1])
            lab = tr(f"левое колено впереди на {abs(dk):.0f} см" if dk > 0 else f"правое колено впереди на {abs(dk):.0f} см")
            ly = (back[1] + fwd[1]) / 2 - 8
            xl = max(knees[-1][0], knees[1][0]) + 7 * s
            left = xl + 2.5 * s + font(12, True).size(lab)[0] > rect.right - 10   # не влезает справа — слева от колен
            if left:
                xl = min(knees[-1][0], knees[1][0]) - 7 * s
            DR.line(surf, AMBER, (xl, back[1]), (xl, fwd[1]), 2)
            for yy in (back[1], fwd[1]):
                DR.line(surf, AMBER, (xl - 1.5 * s, yy), (xl + 1.5 * s, yy), 2)
            lw, lh = font(12, True).size(lab)
            if left:                                           # слева — Мортимер: подпись под коленями
                lx, ly = (knees[-1][0] + knees[1][0]) / 2 - lw / 2, fwd[1] + 3 * s
            else:
                lx = xl + 2.5 * s
            aa_rect(surf, (16, 12, 24, 220), (lx - 5, ly - 2, lw + 10, lh + 4), border_radius=4)   # плашка — читается поверх рисунка
            draw_text(surf, lab, (lx, ly), 12, AMBER, bold=True)
        status = pose.get("status", "")
        if status:
            draw_text(surf, status, (rect.x + 150, rect.y + 12), 12, GOOD if pose.get("ok") else AMBER, bold=True)
        if show_necro:
            tg = [(knees[-1][0], knees[-1][1], p_col, not pose.get("ok")), (knees[1][0], knees[1][1], p_col, False),
                  (pc[0], pc[1], CYAN, False)]
            self._draw_necro_puppeteer(surf, rect, tg, bad_flag=not pose.get("ok"))
        draw_text(surf, "Вид сверху", (rect.right - 14, rect.y + 12), 12, GREY, bold=True, right=True)

    def _seat_view_draw(self, surf, rect, case, cfg, pose, view, clip):
        """Вид примерки в рамке clip (череп посоха не налезает на тексты)."""
        old = surf.get_clip()
        surf.set_clip(_rr(clip, _rs(surf)).clip(old))
        try:
            if view == "front":
                self._seat_front_fit(surf, rect, case, cfg, pose)
            else:
                self._seat_top(surf, rect, case, cfg, pose)
        finally:
            surf.set_clip(old)

    # ---------- рисунок: скелет-марионетка и клиент в коляске сбоку ----------
    def _draw_seat_scene(self, surf, rect, case, cfg, pose, highlight=True, show_necro=True, show_body=False,
                         clip=None):
        """Сцена посадки; clip — рамка, за которую рисунок не выходит (череп не налезает на тексты)."""
        old = surf.get_clip()
        if clip is not None:
            k = _rs(surf)
            c = _rr(clip, k).clip(old)
            surf.set_clip(c)
        try:
            self._draw_seat_scene_body(surf, rect, case, cfg, pose, highlight, show_necro, show_body)
        finally:
            surf.set_clip(old)

    def _draw_seat_scene_body(self, surf, rect, case, cfg, pose, highlight=True, show_necro=True, show_body=False):
        """Вид сбоку: детальная коляска, анатомический скелет (таз, позвонки, грудная клетка, череп,
        бедро, надколенник, голень, стопа) и некромант Мортимер, управляющий скелетом нитями."""
        for gx in range(rect.x + 20, rect.right - 10, 36):
            DR.line(surf, (26, 29, 40), (gx, rect.y + 8), (gx, rect.bottom - 26), 1)
        for gy in range(rect.y + 16, rect.bottom - 26, 36):
            DR.line(surf, (26, 29, 40), (rect.x + 10, gy), (rect.right - 10, gy), 1)

        need_h = case["seat_h"] + case.get("body", {}).get("shoulder", 60) + 52   # плечи + голова + подпись позы
        k = min(rect.w / 155.0, rect.h / max(132.0, need_h))
        floor_y = rect.bottom - 24
        x_r = rect.x + rect.w * (0.43 if show_necro else 0.36)
        seat_h, depth, leg = case["seat_h"], cfg["depth"], cfg["leg"]
        tilt = math.radians(cfg.get("tilt", 0))
        piv = (depth * 0.45, -8.0)
        # наклон в пространстве (Zippie IRIS и т. п.): сиденье при наклоне уходит по дуге вперёд, чтобы центр
        # тяжести оставался над колёсами — иначе на рисунке коляска «опрокидывается» назад
        fwd = 17.0 * math.sin(max(0.0, tilt))

        def T(px, py):
            dx, dy = px - piv[0], py - piv[1]
            rx = piv[0] + dx * math.cos(tilt) - dy * math.sin(tilt) + fwd
            ry = piv[1] + dx * math.sin(tilt) + dy * math.cos(tilt)
            return (x_r + rx * k, floor_y - (seat_h + ry) * k)

        def W(px, py):
            return (x_r + px * k, floor_y - py * k)

        FR, UP, MET, TIRE = (82, 88, 104), (58, 66, 108), (178, 184, 198), (34, 36, 42)
        BONE = (234, 226, 206)
        BONE_D = (186, 176, 154)
        BONE_SH = (150, 140, 120)
        BONE_OUT = (36, 30, 42)

        DR.line(surf, (104, 96, 122), (rect.x + 10, floor_y), (rect.right - 10, floor_y), 3)
        for cm_x in range(-20, 90, 10):
            px_tick, _ = W(cm_x, 0)
            if rect.x + 140 < px_tick < rect.right - 16:
                DR.line(surf, (74, 70, 90), (px_tick, floor_y), (px_tick, floor_y + (5 if cm_x % 20 == 0 else 3)), 1)

        ba = math.radians(cfg["back_a"] - 90)
        top = (-math.sin(ba) * cfg["back_h"], math.cos(ba) * cfg["back_h"])
        if case["kind"] == "power":
            p_b0 = W(-16, 26)
            bw, bh_px = int((depth + 28) * k), int(18 * k)
            aa_rect(surf, (44, 46, 56), (p_b0[0], p_b0[1], bw, bh_px), border_radius=max(4, int(6 * k)))
            aa_rect(surf, (112, 74, 156), (p_b0[0] + 4, p_b0[1] + 3, bw - 8, max(3, int(5 * k))), border_radius=3)
            aa_rect(surf, (88, 92, 106), (p_b0[0], p_b0[1], bw, bh_px), 2, border_radius=max(4, int(6 * k)))
            DR.line(surf, (56, 60, 72), W(depth * 0.45, 24), T(*piv), max(4, int(8 * k)))
            DR.line(surf, MET, W(depth * 0.45 - 3, 24), T(piv[0] - 2, piv[1]), max(2, int(3 * k)))
            for cx, r in ((-11, 8.5), (depth + 9, 8.5), (depth * 0.42, 16.5)):
                DR.line(surf, (96, 100, 114), W(depth * 0.42, 18), W(cx, r), max(2, int(3 * k)))
                aa_circle(surf, TIRE, W(cx, r), int(r * k))
                aa_circle(surf, (64, 68, 78), W(cx, r), int(r * k), 2)
                aa_circle(surf, MET, W(cx, r), int(r * k * 0.48))
                aa_circle(surf, (44, 46, 54), W(cx, r), max(2, int(r * k * 0.18)))
        else:
            r_frame = [T(-2, -4), T(depth - 1, -4), W(depth + 3, 17), W(3, 19), T(-2, -4)]
            DR.lines(surf, FR, False, r_frame, max(2, int(3.2 * k)))
            c_hub = W(depth + 4, 8)
            DR.line(surf, MET, W(depth + 3, 18), c_hub, max(2, int(2.8 * k)))
            aa_circle(surf, TIRE, c_hub, int(8 * k))
            aa_circle(surf, MET, c_hub, int(4.5 * k))
            aa_circle(surf, (40, 42, 50), c_hub, max(2, int(2 * k)))

        ux_b, uy_b = -math.sin(ba), math.cos(ba)
        nx_b, ny_b = math.cos(ba), math.sin(ba)
        DR.line(surf, FR, T(-3, -4), T(top[0] - 3 * nx_b, top[1] - 3 * ny_b + 3), max(2, int(3.2 * k)))
        ph0 = T(top[0] - 3 * nx_b, top[1] - 3 * ny_b + 2)
        ph1 = T(top[0] - 11 * nx_b, top[1] - 11 * ny_b + 2)
        DR.line(surf, (44, 46, 54), ph0, ph1, max(3, int(4.2 * k)))
        b_pad = [
            T(-0.5, 1.0),
            T(top[0] - 0.5 * nx_b, top[1] - 0.5 * ny_b),
            T(top[0] + 4.2 * nx_b, top[1] + 4.2 * ny_b),
            T(4.2, 1.0),
        ]
        DR.polygon(surf, UP, b_pad)
        DR.polygon(surf, (92, 102, 152), b_pad, 2)
        if case["kind"] == "power" or case.get("tilt"):             # подголовник — и у ручной коляски с наклоном
            hr0 = T(top[0] + 1.0 * nx_b, top[1] + 1.0 * ny_b)
            hr1 = T(top[0] + 8.0 * ux_b + 2.0 * nx_b, top[1] + 8.0 * uy_b + 2.0 * ny_b)
            hr2 = T(top[0] + 15.0 * ux_b + 4.5 * nx_b, top[1] + 15.0 * uy_b + 4.5 * ny_b)
            DR.lines(surf, FR, False, [hr0, hr1, hr2], max(2, int(2.6 * k)))
            DR.line(surf, UP, T(top[0] + 9.0 * ux_b + 4.5 * nx_b, top[1] + 9.0 * uy_b + 4.5 * ny_b),
                    T(top[0] + 19.0 * ux_b + 4.5 * nx_b, top[1] + 19.0 * uy_b + 4.5 * ny_b), max(4, int(5.5 * k)))

        DR.line(surf, FR, T(-3, -4.5), T(depth, -4.5), max(2, int(3.2 * k)))
        c_pad = [T(0.5, -3.0), T(depth - 0.5, -3.0), T(depth - 0.5, 2.2), T(depth * 0.55, 1.6), T(0.5, 2.0)]
        DR.polygon(surf, (52, 60, 102), c_pad)
        DR.polygon(surf, (96, 108, 162), c_pad, 2)

        fp = (depth + 0.26 * leg, -leg)
        DR.lines(surf, MET, False, [T(depth - 1, -3.5), T(depth + 0.14 * leg, -leg * 0.45), T(*fp)], max(2, int(2.8 * k)))
        fp_p0, fp_p1 = T(fp[0] - 2, fp[1]), T(fp[0] + 18, fp[1])
        DR.line(surf, (38, 40, 48), fp_p0, fp_p1, max(3, int(3.8 * k)))
        DR.line(surf, MET, (fp_p0[0], fp_p0[1] - 2), (fp_p1[0], fp_p1[1] - 2), 1)
        plate_cm = case["seat_h"] - leg - 1
        if abs(cfg.get("tilt", 0)) < 5:
            f_col = BAD if plate_cm < 5 else (110, 124, 146)
            DR.line(surf, f_col, (fp_p1[0] - 4, fp_p1[1] + 2), (fp_p1[0] - 4, floor_y - 2), 1)
            draw_text(surf, f"{max(0, plate_cm):.0f} см", (fp_p1[0] + 20, min(floor_y - 14, (fp_p1[1] + floor_y) * 0.5 - 6)),
                      11, f_col, center=True)

        b = case["body"]
        slide, pt = pose.get("slide", 0), math.radians(pose.get("p", 0))
        hip = (slide + 10.0, 9.0 - slide * 0.25)
        thigh = b["thigh"] - 10.0
        kb = max(0.0, b["shank"] - leg)
        th = math.asin(min(0.75, kb / max(10.0, thigh))) if kb > 0.5 else -0.03
        knee = (hip[0] + thigh * math.cos(th), 5.0 + thigh * math.sin(th) + (hip[1] - 9.0))
        sole = knee[1] - 5.0 - b["shank"]
        if sole > -leg + 0.5:
            ankle = (knee[0] + 2.0, sole + 3.0)
            toe = (ankle[0] + 9.0, ankle[1] - 7.5)
            heel = (ankle[0] - 3.5, ankle[1] - 1.5)
        else:
            ankle = (knee[0] + 1.0, -leg + 3.5)
            toe = (ankle[0] + 15.0, -leg + 1.2)
            heel = (ankle[0] - 3.5, -leg + 1.2)

        a1 = ba + pt
        mid = (hip[0] - math.sin(a1) * 20.0, hip[1] + math.cos(a1) * 20.0)
        a2 = a1 - pt * 2.3
        tl_len = b["shoulder"] - 24.0
        sh = (mid[0] - math.sin(a2) * tl_len, mid[1] + math.cos(a2) * tl_len)
        a3 = a2 - pt * 2.0
        head = (sh[0] - math.sin(a3) * 12.5 + 3.0, sh[1] + math.cos(a3) * 12.5)

        if show_body and self.SEAT_BODY_ON:
            J_ = dict(hip=hip, knee=knee, ankle=ankle, toe=toe, mid=mid, sh=sh, head=head)
            if not self._draw_seat_puppet(surf, case, T, J_):
                self._draw_seat_flesh(surf, rect, case, T, k, J_)

        sacrum_base = (hip[0] - 5.5 * math.cos(pt) - 2.0, hip[1] - 4.0 * math.sin(pt) - 3.5)
        spine_pts = []
        n_vert = 13
        for vi in range(n_vert + 1):
            tv = vi / n_vert
            if tv < 0.45:
                u = tv / 0.45
                vx = (1 - u) * sacrum_base[0] + u * mid[0] + 1.4 * math.sin(u * math.pi) * (1.0 - pt * 1.8)
                vy = (1 - u) * sacrum_base[1] + u * mid[1]
            else:
                u = (tv - 0.45) / 0.55
                vx = (1 - u) * mid[0] + u * sh[0] - 2.2 * math.sin(u * math.pi) * (0.4 + pt * 1.6)
                vy = (1 - u) * mid[1] + u * sh[1]
            spine_pts.append((vx, vy))
        DR.lines(surf, BONE_D, False, [T(*p_) for p_ in spine_pts], max(3, int(3.8 * k)))
        for vi in range(len(spine_pts) - 1):
            p_cur = T(*spine_pts[vi])
            p_nxt = T(*spine_pts[vi + 1])
            dx_v, dy_v = p_nxt[0] - p_cur[0], p_nxt[1] - p_cur[1]
            lv = max(1.0, math.hypot(dx_v, dy_v))
            nx_v, ny_v = -dy_v / lv, dx_v / lv
            sp_len = max(3.0, (4.2 - 0.12 * vi) * k)
            DR.line(surf, BONE, p_cur, (p_cur[0] - nx_v * sp_len, p_cur[1] - ny_v * sp_len), max(2, int(2.2 * k)))
            vw = max(2, int((3.4 - 0.08 * vi) * k))
            aa_circle(surf, BONE, (int(p_cur[0]), int(p_cur[1])), vw)
            aa_circle(surf, BONE_OUT, (int(p_cur[0]), int(p_cur[1])), vw, 1)

        for ri, frac in enumerate((0.52, 0.62, 0.72, 0.82, 0.91)):
            idx_r = min(len(spine_pts) - 1, int(frac * (len(spine_pts) - 1)))
            rx0, ry0 = spine_pts[idx_r]
            rib_w = (9.5 - abs(ri - 2) * 1.3)
            rib_end = (rx0 + rib_w * math.cos(a2 - 0.25), ry0 + rib_w * math.sin(a2 - 0.25) - 2.2)
            rib_mid = ((rx0 + rib_end[0]) * 0.5 + 1.5, (ry0 + rib_end[1]) * 0.5 - 1.8)
            DR.lines(surf, BONE_OUT, False, [T(rx0, ry0), T(*rib_mid), T(*rib_end)], max(2, int(2.6 * k)))
            DR.lines(surf, BONE, False, [T(rx0, ry0), T(*rib_mid), T(*rib_end)], max(1, int(1.6 * k)))
        scap_bot = (sh[0] - 4.5 * math.cos(a2) + 6.0 * math.sin(a2), sh[1] - 12.0 * math.cos(a2))
        scap_pts = [T(sh[0] - 2.0, sh[1] - 1.5), T(sh[0] - 7.5, sh[1] - 3.5), T(*scap_bot)]
        DR.polygon(surf, BONE_D, scap_pts)
        DR.polygon(surf, BONE_OUT, scap_pts, 2)

        ca_p, sa_p = math.cos(-pt + 0.12), math.sin(-pt + 0.12)
        def TP(lx, ly):
            return T(hip[0] + lx * ca_p - ly * sa_p, hip[1] + lx * sa_p + ly * ca_p)
        pelvis_poly = [
            TP(-7.5, 6.5),
            TP(-2.0, 10.5),
            TP(6.5, 7.5),
            TP(5.0, 1.5),
            TP(3.5, -5.5),
            TP(-2.5, -7.2),
            TP(-6.5, -2.5),
        ]
        fossa_poly = [TP(-4.8, 5.5), TP(-1.2, 8.2), TP(4.2, 5.8), TP(1.5, 1.5)]
        sacrum_poly = [TP(-6.5, 6.0), TP(-9.5, 1.0), TP(-8.8, -5.2), TP(-5.5, -2.0)]
        DR.polygon(surf, BONE_D, sacrum_poly)
        DR.polygon(surf, BONE_OUT, sacrum_poly, 2)
        DR.polygon(surf, BONE, pelvis_poly)
        DR.polygon(surf, BONE_SH, fossa_poly)
        DR.polygon(surf, BONE_OUT, pelvis_poly, 2)
        # Запирательное отверстие таза (obturator foramen)
        ob_p = TP(0.5, -4.2)
        aa_circle(surf, (38, 42, 64), (int(ob_p[0]), int(ob_p[1])), max(2, int(1.9 * k)))
        aa_circle(surf, BONE_OUT, (int(ob_p[0]), int(ob_p[1])), max(2, int(1.9 * k)), 1)
        p_psis, p_asis = TP(-7.2, 6.2), TP(6.2, 7.2)
        tilt_col = BAD if pose.get("p", 0) > 12 else (AMBER if pose.get("p", 0) > 5 else GOOD)
        DR.line(surf, tilt_col, p_psis, p_asis, max(2, int(2.6 * k)))
        aa_circle(surf, tilt_col, (int(p_psis[0]), int(p_psis[1])), 3)
        aa_circle(surf, tilt_col, (int(p_asis[0]), int(p_asis[1])), 3)

        self._draw_bone_seg(surf, T(*hip), T(*knee), max(3.5, 3.8 * k), max(3.2, 3.4 * k), BONE, BONE_OUT)
        pat = T(knee[0] + 2.8 * math.cos(th - 0.3), knee[1] + 2.8 * math.sin(th - 0.3))
        aa_circle(surf, BONE, (int(pat[0]), int(pat[1])), max(2, int(2.6 * k)))
        aa_circle(surf, BONE_OUT, (int(pat[0]), int(pat[1])), max(2, int(2.6 * k)), 1)
        DR.line(surf, BONE_D, T(knee[0] - 1.8, knee[1] - 1.5), T(ankle[0] - 1.5, ankle[1] + 1.0), max(2, int(2.2 * k)))
        self._draw_bone_seg(surf, T(*knee), T(*ankle), max(3.0, 3.2 * k), max(2.4, 2.5 * k), BONE, BONE_OUT)
        foot_poly = [T(*ankle), T(*heel), T(ankle[0] + 4.0, toe[1]), T(*toe), T(ankle[0] + 6.0, ankle[1] - 1.0)]
        DR.polygon(surf, BONE, foot_poly)
        DR.polygon(surf, BONE_OUT, foot_poly, 2)

        neck_top = T(head[0] - 2.0 * math.cos(a3), head[1] - 5.5)
        self._draw_bone_seg(surf, T(*sh), neck_top, max(2.2, 2.4 * k), max(2.0, 2.2 * k), BONE_D, BONE_OUT, joint=False)
        hc = T(*head)
        hr_px = max(7, int(8.8 * k))
        aa_circle(surf, BONE, (int(hc[0] - 1.5 * k), int(hc[1] - 1.0 * k)), hr_px)
        aa_circle(surf, BONE_OUT, (int(hc[0] - 1.5 * k), int(hc[1] - 1.0 * k)), hr_px, 2)
        jaw_pts = [
            (hc[0] + 1.0 * k, hc[1] - 2.0 * k),
            (hc[0] + 8.2 * k, hc[1] - 1.0 * k),
            (hc[0] + 7.5 * k, hc[1] + 5.8 * k),
            (hc[0] + 1.5 * k, hc[1] + 7.2 * k),
            (hc[0] - 3.0 * k, hc[1] + 4.5 * k),
        ]
        DR.polygon(surf, BONE, jaw_pts)
        DR.polygon(surf, BONE_OUT, jaw_pts, 2)
        eye_p = (int(hc[0] + 4.2 * k), int(hc[1] - 1.2 * k))
        aa_circle(surf, (28, 22, 36), eye_p, max(2, int(2.8 * k)))
        aa_circle(surf, GHOST if pose.get("p", 0) <= 8 else AMBER, eye_p, max(1, int(1.3 * k)))
        DR.line(surf, BONE_OUT, (hc[0] + 2.5 * k, hc[1] + 3.6 * k), (hc[0] + 7.2 * k, hc[1] + 3.4 * k), 1)

        elbow = (sh[0] + 5.0, sh[1] - 24.0)
        hand = (elbow[0] + 21.0, elbow[1] + 1.5)
        self._draw_bone_seg(surf, T(*sh), T(*elbow), max(2.6, 2.8 * k), max(2.2, 2.4 * k), BONE_D, BONE_OUT)
        self._draw_bone_seg(surf, T(*elbow), T(*hand), max(2.2, 2.4 * k), max(1.8, 2.0 * k), BONE, BONE_OUT)
        aa_circle(surf, BONE, (int(T(*hand)[0] + 3 * k), int(T(*hand)[1])), max(2, int(2.4 * k)))
        aa_circle(surf, BONE_OUT, (int(T(*hand)[0] + 3 * k), int(T(*hand)[1])), max(2, int(2.4 * k)), 1)
        hi = getattr(self, "_seat_head_img", None) if show_body else None
        if hi:                                              # лицо клиента поверх черепа — череп просвечивает
            im_ = hi[0].copy()
            im_.set_alpha(170)
            pygame.Surface.blit(surf, im_, hi[1])
            self._seat_head_img = None

        if case["kind"] != "power":
            R = 30 if seat_h > 45 else 26
            if case.get("tilt"):                                   # антиопрокидыватели: у колясок с наклоном — всегда
                a0, a1 = W(-4, 15), W(-R - 6, 6.5)
                DR.line(surf, FR, a0, a1, max(2, int(2.6 * k)))
                aa_circle(surf, TIRE, a1, max(3, int(3.2 * k)))
                aa_circle(surf, MET, a1, max(1, int(1.4 * k)))
            w_surf = Surf(rect.size, pygame.SRCALPHA)
            wc = (int(W(2, R)[0] - rect.x), int(W(2, R)[1] - rect.y))
            for a_sp in range(0, 360, 20):
                ra = math.radians(a_sp)
                DR.line(w_surf, (150, 158, 176, 95), wc,
                        (wc[0] + (R - 3.5) * k * math.cos(ra), wc[1] + (R - 3.5) * k * math.sin(ra)), 1)
            aa_circle(w_surf, (*TIRE, 155), wc, int(R * k), max(2, int(3.2 * k)))
            aa_circle(w_surf, (*MET, 165), wc, int((R - 4) * k), max(1, int(1.4 * k)))
            aa_circle(w_surf, (*MET, 210), wc, max(3, int(3.5 * k)))
            surf.blit(w_surf, rect.topleft)
        has_bad = pose.get("p", 0) > 8 or pose.get("knee_up") or pose.get("short") or pose.get("deep") or pose.get("dangle")
        if show_necro:
            targets = [
                (hc[0], hc[1] - hr_px, PURPLE, False),
                (T(*mid)[0], T(*mid)[1], AMBER if pose.get("p", 0) > 8 else PURPLE, pose.get("p", 0) > 8),
                (p_psis[0], p_psis[1], tilt_col, pose.get("p", 0) > 8),
                (T(*knee)[0], T(*knee)[1], BAD if (pose.get("knee_up") or pose.get("deep")) else GHOST,
                 bool(pose.get("knee_up") or pose.get("deep"))),
                (T(*ankle)[0], T(*ankle)[1], BAD if pose.get("dangle") else PURPLE, bool(pose.get("dangle"))),
            ]
            self._draw_necro_puppeteer(surf, rect, targets, bad_flag=has_bad)

            pt_deg = round(pose.get("p", 0))
            badge_col = BAD if pt_deg > 12 else (AMBER if pt_deg > 5 else GOOD)
            status_txt = f"Завал таза назад: {pt_deg}° (на крестце)" if pt_deg > 5 else "Таз в нейтрали · позвоночник стабилен"
            # главное в позе — подножка, а не крестец (отзыв: урок 3 выглядел как урок 2); в зачёте до ответа
            # (highlight=False) не подсказываем
            if highlight and pose.get("knee_up"):
                status_txt, badge_col = "Подножка высоко: колени выше бёдер", BAD
            elif highlight and pose.get("dangle"):
                status_txt, badge_col = "Подножка низко: стопы не достают", BAD
            sw_, sh_ = font(12, True).size(tr(status_txt))          # подпись — на тёмной плашке, поверх рисунка
            aa_rect(surf, (16, 12, 24, 225), (rect.x + 134, rect.y + 10, sw_ + 12, sh_ + 4), border_radius=4)
            draw_text(surf, status_txt, (rect.x + 140, rect.y + 12), 12, badge_col, bold=True)

        if pose.get("measure"):                  # урок «Мерки»: где меряют (отзыв «покажи, где мерки»), поверх нитей
            MC, MG = (255, 200, 90), (255, 120, 110)

            def dim(p0, p1, col, label, lp, **kw):
                q0, q1 = T(*p0), T(*p1)
                DR.line(surf, col, q0, q1, 2)
                dx_, dy_ = q1[0] - q0[0], q1[1] - q0[1]
                ln_ = math.hypot(dx_, dy_) or 1.0
                ox, oy = -dy_ / ln_ * 5, dx_ / ln_ * 5
                for q in (q0, q1):
                    DR.line(surf, col, (q[0] - ox, q[1] - oy), (q[0] + ox, q[1] + oy), 2)
                draw_text(surf, label, T(*lp), 12, col, bold=True, plate=True, **kw)

            pop_x = knee[0] - 3.0                # подколенная ямка — сзади колена
            y_th = hip[1] + 8.0
            dim((0.0, y_th), (pop_x, y_th), MC, "до подколенной ямки", (pop_x, y_th + 7.5), right=True)
            dim((depth, -7.0), (pop_x, -7.0), MG, "−5 см", (pop_x + 2.0, -5.0))
            dim((-15.0, 0.0), (-15.0, scap_bot[1]), MC, "спинка", (-16.5, scap_bot[1] * 0.5 + 2), right=True)
            dim((hand[0] + 3.0, 2.0), (hand[0] + 3.0, elbow[1] - 1.5), MC, "локоть 90°", (hand[0] + 5.0, elbow[1] + 4.0))
            dim((knee[0] + 9.0, knee[1] - 3.0), (knee[0] + 9.0, -leg), MC, "голень", (knee[0] + 11.0, (knee[1] - leg) * 0.5))

        if not highlight:
            return
        # --- 7. Зоны повышенного давления с разведением выносок без перекрытия ---
        zones = []
        if pose.get("p", 0) > 8:
            zones.append(((hip[0] - 6.5, 1.5), BAD if pose["p"] > 14 else AMBER, "крестец (риск пролежня)", -92, -42))
        if pose.get("knee_up") or pose.get("short"):
            zones.append(((hip[0] + 1.5, -0.5), BAD, "седалищные бугры", -56, 24))
        if pose.get("deep"):
            zones.append(((depth - 1.0, 0.0), BAD, "давление под коленями", 78, -26))
        if pose.get("dangle"):
            zones.append(((ankle[0] + 4.0, ankle[1] - 3.0), AMBER, "стопы висят без опоры", 84, -30))
        used_ys = []
        lab_h = font(12, True).get_height() + 4                    # плашка по высоте шрифта (крупный текст — выше)
        labels = []
        for zi, ((zx, zy), col, label, dx_l, dy_l) in enumerate(zones):
            p_ = T(zx, zy)
            add_glow(surf, (int(p_[0]), int(p_[1])), int(10 * k), col, 0.9)
            aa_circle(surf, col, (int(p_[0]), int(p_[1])), max(3, int(2.6 * k)))
            aa_circle(surf, WHITE, (int(p_[0]), int(p_[1])), max(4, int(4.2 * k)), 1)
            lx = max(rect.x + 205, min(rect.right - 95, int(p_[0] + dx_l)))
            ly = max(rect.y + 48, min(floor_y - 24, int(p_[1] + dy_l)))
            for uy in sorted(used_ys):
                if abs(ly - uy) < lab_h + 2:
                    ly = min(floor_y - 24, uy + lab_h + 3)
            used_ys.append(ly)
            DR.line(surf, col, (int(p_[0]), int(p_[1])), (lx, ly), 1)
            labels.append((lx, ly, label, col))
        for lx, ly, label, col in labels:                          # подписи — последними: линии и нити их не режут
            tw = font(12, True).size(tr(label))[0] + 10
            aa_rect(surf, (16, 12, 24, 235), (lx - tw // 2, ly - lab_h // 2, tw, lab_h), border_radius=4)   # текст — по центру ly
            draw_text(surf, label, (lx, ly), 12, col, bold=True, center=True)

    def _seat_front(self, surf, rect, corrected=False, show_pads=True):
        """Схема спереди: перекос таза, сколиотическая дуга позвоночника, грудная клетка, череп,
        три точки боковой поддержки и некромант Мортимер, выправляющий скелет нитями."""
        for gx in range(rect.x + 20, rect.right - 10, 36):
            DR.line(surf, (26, 29, 40), (gx, rect.y + 8), (gx, rect.bottom - 26), 1)
        for gy in range(rect.y + 16, rect.bottom - 26, 36):
            DR.line(surf, (26, 29, 40), (rect.x + 10, gy), (rect.right - 10, gy), 1)

        cx = rect.centerx + 46
        by = rect.bottom - 56
        k = rect.h / 310.0
        BONE = (234, 226, 206)
        BONE_D = (188, 178, 156)
        BONE_OUT = (38, 32, 44)

        for s in (-1, 1):
            wx = int(cx + s * 124 * k)
            aa_rect(surf, (34, 36, 42), (wx - int(6 * k), by - int(78 * k), int(12 * k), int(112 * k)), border_radius=4)
            aa_rect(surf, (168, 174, 188), (wx - int(9 * k), by - int(72 * k), int(4 * k), int(98 * k)), border_radius=2)
        aa_rect(surf, (44, 48, 72), (cx - 96 * k, by - 236 * k, 192 * k, 228 * k), border_radius=10)
        aa_rect(surf, (76, 84, 122), (cx - 96 * k, by - 236 * k, 192 * k, 228 * k), 2, border_radius=10)
        aa_rect(surf, (58, 66, 112), (cx - 106 * k, by - 14 * k, 212 * k, 22 * k), border_radius=7)
        aa_rect(surf, (98, 110, 168), (cx - 106 * k, by - 14 * k, 212 * k, 22 * k), 2, border_radius=7)

        obl = 0.12 if corrected else 1.0
        pl = (cx - 58 * k, by - (36 - 8 * (1 - obl)) * k)
        pr = (cx + 58 * k, by - (36 + 14 * obl) * k)
        pel_cx, pel_cy = (pl[0] + pr[0]) * 0.5, (pl[1] + pr[1]) * 0.5 + 8 * k
        for s, pt_crest in ((-1, pl), (1, pr)):
            wing = [
                (pel_cx + s * 12 * k, pel_cy - 6 * k),
                (pt_crest[0] - s * 6 * k, pt_crest[1] - 12 * k),
                (pt_crest[0] + s * 8 * k, pt_crest[1] + 2 * k),
                (pel_cx + s * 42 * k, pel_cy + 16 * k),
                (pel_cx + s * 10 * k, pel_cy + 18 * k),
            ]
            DR.polygon(surf, BONE, wing)
            DR.polygon(surf, BONE_OUT, wing, 2)
            aa_circle(surf, (44, 48, 72), (int(pel_cx + s * 24 * k), int(pel_cy + 9 * k)), max(2, int(4.2 * k)))
            aa_circle(surf, BONE_OUT, (int(pel_cx + s * 24 * k), int(pel_cy + 9 * k)), max(2, int(4.2 * k)), 1)
        sac = [(pel_cx - 14 * k, pel_cy - 10 * k), (pel_cx + 14 * k, pel_cy - 10 * k),
               (pel_cx, pel_cy + 14 * k)]
        DR.polygon(surf, BONE_D, sac)
        DR.polygon(surf, BONE_OUT, sac, 2)
        p_col = GOOD if corrected else AMBER
        DR.line(surf, p_col, pl, pr, max(3, int(4 * k)))
        aa_circle(surf, p_col, (int(pl[0]), int(pl[1])), 4)
        aa_circle(surf, p_col, (int(pr[0]), int(pr[1])), 4)

        apex_x = cx + 28 * k * obl
        apex_y = by - 114 * k
        sh_cx = cx - 8 * k * obl
        sh_cy = by - 208 * k
        sp_pts = []
        for vi in range(13):
            t = vi / 12.0
            u = 1.0 - t
            sx = u * u * pel_cx + 2 * u * t * apex_x + t * t * sh_cx
            sy = u * u * (pel_cy - 8 * k) + 2 * u * t * apex_y + t * t * sh_cy
            sp_pts.append((sx, sy))
        DR.lines(surf, BONE_D, False, sp_pts, max(3, int(4.5 * k)))
        for sx, sy in sp_pts:
            aa_circle(surf, BONE, (int(sx), int(sy)), max(3, int(3.8 * k)))
            aa_circle(surf, BONE_OUT, (int(sx), int(sy)), max(3, int(3.8 * k)), 1)

        for ri, vi in enumerate((5, 6, 7, 8, 9, 10)):
            rx, ry = sp_pts[vi]
            rw = (46 - abs(ri - 2.5) * 5.5) * k
            tilt_r = 0.16 * obl * (1.0 - 0.1 * ri)
            for s in (-1, 1):
                p_rib_mid = (rx + s * rw * 0.95, ry + (s * rw * tilt_r) + 6 * k)
                p_rib_in = (rx + s * rw * 0.38, ry + (s * rw * tilt_r * 0.5) + 14 * k)
                DR.lines(surf, BONE_OUT, False, [(rx, ry), p_rib_mid, p_rib_in], max(2, int(2.8 * k)))
                DR.lines(surf, BONE, False, [(rx, ry), p_rib_mid, p_rib_in], max(1, int(1.8 * k)))
        sh_l = (sh_cx - 62 * k, sh_cy + 6 * k * obl)
        sh_r = (sh_cx + 58 * k, sh_cy - 8 * k * obl)
        self._draw_bone_seg(surf, (sh_cx, sh_cy + 4 * k), sh_l, 2.8 * k, 3.2 * k, BONE, BONE_OUT)
        self._draw_bone_seg(surf, (sh_cx, sh_cy + 4 * k), sh_r, 2.8 * k, 3.2 * k, BONE, BONE_OUT)
        for s, sp_sh, sp_hip in ((-1, sh_l, pl), (1, sh_r, pr)):
            self._draw_bone_seg(surf, sp_sh, (sp_sh[0] - s * 6 * k, sp_sh[1] + 68 * k), 3.2 * k, 2.8 * k, BONE_D, BONE_OUT)
            knee_f = (sp_hip[0] + s * 4 * k, by + 12 * k)
            self._draw_bone_seg(surf, (sp_hip[0], sp_hip[1] + 10 * k), knee_f, 4.2 * k, 3.8 * k, BONE, BONE_OUT)

        h_cx, h_cy = int(sh_cx - 3 * k * obl), int(sh_cy - 34 * k)
        hr = int(20 * k)
        aa_circle(surf, BONE, (h_cx, h_cy), hr)
        aa_circle(surf, BONE_OUT, (h_cx, h_cy), hr, 2)
        aa_rect(surf, BONE, (h_cx - int(11 * k), h_cy + int(6 * k), int(22 * k), int(16 * k)), border_radius=5)
        aa_rect(surf, BONE_OUT, (h_cx - int(11 * k), h_cy + int(6 * k), int(22 * k), int(16 * k)), 2, border_radius=5)
        for s in (-1, 1):
            ex, ey = h_cx + int(s * 6.5 * k), h_cy - int(1 * k)
            aa_circle(surf, (26, 22, 34), (ex, ey), max(3, int(4.2 * k)))
            aa_circle(surf, GHOST, (ex, ey), max(1, int(1.6 * k)))
        DR.polygon(surf, (26, 22, 34), [(h_cx, h_cy + int(3 * k)), (h_cx - int(2.5 * k), h_cy + int(8 * k)),
                                        (h_cx + int(2.5 * k), h_cy + int(8 * k))])

        pads = (
            ((apex_x + 42 * k, apex_y), -1, "1. Вершина изгиба"),
            ((sh_l[0] - 18 * k, by - 184 * k), 1, "2. Под мышкой (зазор)"),
            ((pl[0] - 24 * k, by - 44 * k), 1, "3. Низко у таза"),
        )
        labels = []                                        # подписи упоров — после Мортимера (не прячутся за ним)
        for (px, py), dir_s, lab in (pads if show_pads else ()):
            pad_r = pygame.Rect(int(px - 8 * k), int(py - 20 * k), int(16 * k), int(40 * k))
            aa_rect(surf, CYAN, pad_r, border_radius=5)
            aa_rect(surf, WHITE, pad_r, 1, border_radius=5)
            ax0 = px - dir_s * 22 * k
            ax1 = px - dir_s * 10 * k
            DR.line(surf, GOOD, (ax0, py), (ax1, py), 2)
            lw_ = font(12, True).size(tr(lab))[0]
            tx = px + (16 if dir_s < 0 else -16) * k
            if dir_s > 0:
                tx = max(tx, rect.x + 8 + lw_)                # не за левый край рамки
            else:
                tx = min(tx, rect.right - 8 - lw_)
            labels.append((tx, py, lw_, lab, dir_s))

        targets = [
            (h_cx, h_cy - hr, PURPLE, False),
            (apex_x, apex_y, GOOD if corrected else CYAN, True),
            (pl[0], pl[1], p_col, not corrected),
            (sh_l[0], sh_l[1], CYAN, False),
        ]
        self._draw_necro_puppeteer(surf, rect, targets, bad_flag=not corrected)
        for tx, py, lw_, lab, dir_s in labels:
            x0_ = tx - lw_ if dir_s > 0 else tx
            aa_rect(surf, (16, 12, 24, 215), (x0_ - 4, py - 9, lw_ + 8, 20), border_radius=4)
            draw_text(surf, lab, (tx, py - 7), 12, CYAN, bold=True, right=dir_s > 0)
        status = "Три точки держат ось позвоночника" if corrected else "Таз перекошен → дуга сколиоза"
        draw_text(surf, status, (rect.x + 140, rect.y + 12), 12, GOOD if corrected else AMBER, bold=True)

    def _draw_seat_909090_myth(self, surf, rect):
        """Иллюстрация к вопросу о мифе «90-90-90»: Мортимер и три скелета с разной целью посадки."""
        for gx in range(rect.x + 20, rect.right - 10, 36):
            DR.line(surf, (26, 29, 40), (gx, rect.y + 8), (gx, rect.bottom - 26), 1)
        myth = "Мортимер: «Три скелета — три цели. Подойдёт ли им один шаблон?»"
        msz = 14                                       # строка — в ширину рамки (в переводе она длиннее)
        while msz > 11 and font(msz, True).size(tr(myth))[0] > rect.w - 60:
            msz -= 1
        draw_text(surf, myth, (rect.centerx + 20, rect.y + 16), msz, AMBER, bold=True, center=True)
        presets = [
            ("Активный толчок", dict(seat_h=48, kind="manual", body=dict(thigh=45, shank=42, scap=35, shoulder=54)),
             dict(depth=40, leg=42, back_h=35, back_a=93, tilt=0)),
            ("Комфорт и опора", dict(seat_h=49, kind="manual", body=dict(thigh=47, shank=43, scap=40, shoulder=58)),
             dict(depth=42, leg=43, back_h=46, back_a=102, tilt=0)),
            ("Разгрузка 45° Tilt", dict(seat_h=50, kind="power", body=dict(thigh=48, shank=44, scap=43, shoulder=60)),
             dict(depth=43, leg=44, back_h=58, back_a=104, tilt=45)),
        ]
        w_sub = (rect.w - 150) // 3
        targets = []
        for idx, (label, c_sub, cfg_sub) in enumerate(presets):
            sub_r = pygame.Rect(rect.x + 142 + idx * w_sub, rect.y + 42, w_sub - 6, rect.h - 68)
            aa_rect(surf, (24, 26, 36), sub_r, border_radius=8)
            aa_rect(surf, (58, 66, 86), sub_r, 1, border_radius=8)
            self._draw_seat_scene(surf, sub_r, c_sub, cfg_sub, dict(p=0, slide=0), highlight=False, show_necro=False)
            draw_text(surf, label, (sub_r.centerx, sub_r.y + 10), 12, CYAN, bold=True, center=True)
            targets.append((sub_r.centerx, sub_r.centery - 20, GHOST if idx == 2 else PURPLE, idx == 1))
        self._draw_necro_puppeteer(surf, rect, targets, bad_flag=False)

    def _seat_demo_pose(self, rect, spec, force_good=False):
        """Иллюстрация к уроку/вопросу: типовая коляска и поза по описанию (или эталонная при force_good)."""
        case = dict(SEAT_CASES[0])
        b = case["body"]
        cfg = dict(depth=b["thigh"] - 5, leg=b["shank"], back_h=45, back_a=100, tilt=spec.get("tilt", 0))
        if not force_good:
            if spec.get("deep"):
                cfg["depth"] += 7
            if spec.get("knee_up"):
                cfg["leg"] -= 8
            if spec.get("dangle"):
                cfg["leg"] += 7
                case["seat_h"] = max(case["seat_h"], cfg["leg"] + 4)   # подножка висит, но над полом
        case.update(back=(40, 50), angle=(95, 105), kind="power" if spec.get("tilt") else "manual")
        _, pose = self.seat_eval(case, cfg)
        if spec.get("measure"):
            pose["measure"] = True
        if not force_good:
            if "p" in spec:
                pose["p"] = spec["p"]
            if "slide" in spec:
                pose["slide"] = spec["slide"]
        return case, cfg, pose

    def draw_seating(self, surf):
        self._bg(surf, "bg_workshop.png", WOOD)
        self._topbar(surf, "Кабинет посадки некроманта Мортимера")
        sc, mouse = self.seatc, mouse_pos()
        names = {"lessons": "УРОКИ", "fit": "ПРИМЕРКА", "quiz": "ПРОВЕРЬ СЕБЯ"}
        for t, r in self._seat_tab_rects():
            Button(r, names[t], CYAN).draw(surf, mouse, active=sc["tab"] == t)
        Button(self._seat_back_rect(), "В МАСТЕРСКУЮ", AMBER).draw(surf, mouse)
        self._draw_seat_mentor(surf)
        cv = self._seat_canvas()
        bg = Surf(cv.size, pygame.SRCALPHA)
        aa_rect(bg, (18, 20, 28, 238), bg.get_rect(), border_radius=12)
        surf.blit(bg, cv)
        aa_rect(surf, (96, 78, 136), cv, 2, border_radius=12)
        if sc["tab"] == "lessons":
            for i, r in self._seat_list_rects():
                Button(r, "", CYAN).draw(surf, mouse, active=i == sc["lesson"])
                fit_text(surf, f"{i + 1}. {SEAT_LESSONS[i]['title']}", (r.x + 10, r.y + 9), r.w - 20, 15,
                         WHITE, bold=i == sc["lesson"])
            les = SEAT_LESSONS[sc["lesson"]]
            lpose = les.get("pose") or {}
            demo_good = sc.get("demo_good", False)
            if lpose.get("front"):
                self._seat_front(surf, cv, corrected=demo_good)
            else:
                case, cfg, pose = self._seat_demo_pose(cv, lpose, force_good=demo_good)
                self._draw_seat_scene(surf, cv.inflate(-16, -24), case, cfg, pose, show_necro=True, clip=cv.inflate(-4, -4))
                if lpose.get("measure"):                # подпись — справа, под кнопкой «норма», не на статусе позы
                    cap = "Жёсткая рулетка: глубина = бедро − 5 см (2″)"
                    cw_ = font(14, True).size(tr(cap))[0] + 14
                    aa_rect(surf, (16, 12, 24, 215), (cv.right - 14 - cw_, cv.y + 46, cw_, 22), border_radius=5)
                    draw_text(surf, cap, (cv.right - 21, cv.y + 48), 14, AMBER, bold=True, right=True)
            has_err_pose = any(k in lpose for k in ("p", "slide", "deep", "knee_up", "dangle", "front"))
            if has_err_pose:
                tbtn = self._seat_demo_toggle_rect()
                Button(tbtn, "ПОЗА: НОРМА ✔" if demo_good else "ПОКАЗАТЬ НОРМУ ▶",
                       GOOD if demo_good else PURPLE).draw(surf, mouse, active=demo_good)
            y = 112 + ((len(SEAT_LESSONS) + 1) // 2) * 44 + 10
            draw_text(surf, les["title"], (780, y), 20, AMBER, bold=True)
            y += 32
            psz = 15                                       # крупный текст: урок целиком помещается до низа окна
            while psz > 10 and sum(len(wrap_lines("• " + pt_, 476, psz)) * (font(psz).get_height() + 2) + 8
                                   for pt_ in les["points"]) > HEIGHT - 16 - y:
                psz -= 1
            for pt_ in les["points"]:
                y = draw_wrapped(surf, "• " + pt_, (780, y), 476, psz, WHITE, plate=True) + 8
            draw_text(surf, "По руководству Permobil «Seating & Positioning Guide»",
                      (cv.right - 14, cv.bottom - 18), 11, GREY, right=True)
        elif sc["tab"] == "fit":
            case = SEAT_CASES[sc["case"]]
            checks, pose = self.seat_eval(case, sc["cfg"])
            xray = sc.get("xray", True)
            # шапка: история клиента и карта терапевта — целиком (в карте числа, которые надо выставить);
            # рисунок под ними занимает остаток окна
            st_lines = wrap_lines(case["story"], cv.w - 362, 14)
            chart = f"{tr('Карта терапевта')}: {tr(case['therapist'])}"
            ch_lines = wrap_lines(chart, cv.w - 126, 13)
            lh14, lh13 = font(14).get_height() + 2, font(13).get_height() + 2
            ch_y = cv.y + 10 + max(len(st_lines) * lh14, 36)
            head_bottom = max(cv.y + 98, ch_y + len(ch_lines) * lh13 + 6)
            scene_r = pygame.Rect(cv.x + 8, head_bottom, cv.w - 16, cv.bottom - 24 - head_bottom)
            clip_r = pygame.Rect(cv.x + 4, scene_r.y - 4, cv.w - 8, cv.bottom - scene_r.y)
            view = sc.get("view", "side")
            if view in ("front", "top"):
                self._seat_view_draw(surf, scene_r, case, sc["cfg"], pose, view, clip_r)
            elif case.get("view"):                          # особый клиент сбоку: по меркам всё ровно
                scfg = self._seat_side_cfg(case)
                _, spose = self._seat_eval_side(case, scfg)
                self._draw_seat_scene(surf, scene_r, case, scfg, spose, show_necro=True, show_body=xray, clip=clip_r)
                note = ("Сбоку посадка ровная — перекос виден только спереди" if case["view"] == "front" else
                        "Сбоку посадка ровная — поворот таза виден только сверху")
                nw = font(13, True).size(tr(note))[0] + 16
                aa_rect(surf, (16, 12, 24, 225), (cv.right - 14 - nw, cv.bottom - 56, nw, 24), border_radius=5)
                draw_text(surf, note, (cv.right - 22, cv.bottom - 53), 13, AMBER, bold=True, right=True)
            else:
                self._draw_seat_scene(surf, scene_r, case, sc["cfg"], pose, show_necro=True, show_body=xray, clip=clip_r)
            blit_idle(surf, load_image(case["client_art"], (92, 108), GHOST), (cv.x + 12, cv.y + 6), self.t)
            tbtn = self._seat_demo_toggle_rect()
            if case.get("view"):
                vname = {"front": "ВИД: СПЕРЕДИ  ⇄", "top": "ВИД: СВЕРХУ  ⇄", "side": "ВИД: СБОКУ  ⇄"}[view]
                Button(tbtn, vname, CYAN).draw(surf, mouse, active=view != "side")
            elif self.SEAT_BODY_ON:                         # без тел клиентов переключать нечего
                Button(tbtn, "ТЕЛО: ВИДНО" if xray else "ТЕЛО: СКРЫТО",
                       PURPLE if xray else CYAN).draw(surf, mouse, active=xray)
            for i, r in self._seat_list_rects():
                done = SEAT_CASES[i]["id"] in self.seat_done
                Button(r, "", GOOD if done else CYAN).draw(surf, mouse, active=i == sc["case"])
                fit_text(surf, ("✔ " if done else "") + SEAT_CASES[i]["client"], (r.x + 10, r.y + 8), r.w - 20, 14, WHITE)
            b = case["body"]
            draw_wrapped(surf, case["story"], (cv.x + 112, cv.y + 10), cv.w - 362, 14, WHITE)
            draw_wrapped(surf, chart, (cv.x + 112, ch_y), cv.w - 126, 13, CYAN)
            draw_text(surf, self._seat_measure_text(case), (cv.x + 14, cv.bottom - 18), 11, AMBER)
            sliders = self._seat_slider_rects()
            for key, track in sliders:
                label, unit, lo, hi = SEAT_SLIDERS[key]
                v = sc["cfg"][key]
                ok = all(o for kk, o, _ in checks if kk == key or (key == "leg" and kk == "floor"))
                draw_text(surf, label, (track.x, track.y - 20), 13, WHITE)
                fit_text(surf, seat_val_text(key, v), (track.right + 8, track.y - 9), 150, 14, GOOD if ok else AMBER)
                aa_rect(surf, (44, 46, 60), track, border_radius=4)
                fill = track.copy()
                fill.w = int(track.w * (v - lo) / (hi - lo))
                aa_rect(surf, GOOD if ok else AMBER, fill, border_radius=4)
                kx = track.x + fill.w
                hov = track.inflate(30, 30).collidepoint(mouse) or sc["drag"] == key
                aa_circle(surf, WHITE, (kx, track.centery), 10 if hov else 8)
                aa_circle(surf, GOOD if ok else AMBER, (kx, track.centery), 10 if hov else 8, 3)
            y = sliders[-1][1].y + 24
            room = self._seat_btn_rect().y - 6 - y          # список — до кнопки «Готово», не под неё
            order = [c for c in checks if not c[1]] + [c for c in checks if c[1]]   # сначала то, что ещё не так
            csz = 13
            def need(sz):
                return sum(len(wrap_lines(("✔ " if ok else "⚠ ") + t, 476, sz)) * (font(sz).get_height() + 2) + 2
                           for _, ok, t in order)
            while csz > 10 and need(csz) > room:
                csz -= 1
            bottom = self._seat_btn_rect().y - 6
            for key, ok, text in order:
                left = (bottom - y) // (font(csz).get_height() + 2)
                if left < 1:
                    break
                y = draw_wrapped(surf, ("✔ " if ok else "⚠ ") + text, (780, y), 476, csz, GOOD if ok else AMBER,
                                 max_lines=left) + 2
            Button(self._seat_btn_rect(), "СЛЕДУЮЩИЙ КЛИЕНТ ▶" if sc["solved"] else "ГОТОВО — ПРОВЕРИТЬ ПОСАДКУ",
                   GOOD if sc["solved"] else AMBER).draw(surf, mouse)
        else:
            if sc["quiz_done"]:
                ok = sc["score"] >= SEAT_QUIZ_PASS
                self._draw_necro_puppeteer(surf, cv, [(cv.centerx + 40, cv.centery - 52, GOOD if ok else AMBER, True)],
                                           bad_flag=not ok)          # нить — к надписи сверху, текст — поверх
                draw_text(surf, f"Верно {sc['score']} из {len(SEAT_QUIZ)}", (cv.centerx + 40, cv.centery - 20), 30,
                          GOOD if ok else AMBER, bold=True, center=True, plate=True)
                draw_text(surf, "Зачёт по посадке сдан!" if ok else f"Для зачёта нужно {SEAT_QUIZ_PASS}. Перечитай уроки.",
                          (cv.centerx + 40, cv.centery + 24), 18, WHITE, center=True, plate=True)
                Button(self._seat_btn_rect(), "ПРОЙТИ ЕЩЁ РАЗ", CYAN).draw(surf, mouse)
                return
            q = SEAT_QUIZ[sc["quiz"]]
            qpose = q.get("pose")
            if qpose and qpose.get("front"):
                self._seat_front(surf, cv, corrected=False, show_pads=False)   # без подписей упоров — не подсказка
            elif qpose:
                case, cfg, pose = self._seat_demo_pose(cv, qpose)
                self._draw_seat_scene(surf, cv.inflate(-16, -24), case, cfg, pose,
                                      highlight=sc["picked"] is not None, show_necro=True)
            else:
                self._draw_seat_909090_myth(surf, cv)
            draw_text(surf, f"Вопрос {sc['quiz'] + 1} из {len(SEAT_QUIZ)}", (780, 120), 15, GREY, plate=True)
            draw_wrapped(surf, q["q"], (780, 146), 476, 20, WHITE, plate=True)
            for i, r in self._seat_quiz_rects():
                text, ok, fb = q["options"][i]
                col = CYAN
                if sc["picked"] is not None:
                    col = GOOD if ok else (BAD if i == sc["picked"] else DIM)
                Button(r, "", col).draw(surf, mouse, enabled=sc["picked"] is None or i == sc["picked"] or ok)
                ty = draw_wrapped(surf, text, (r.x + 14, r.y + 8), r.w - 28, 15, WHITE)
                if sc["picked"] == i and fb:                 # крупный текст: вариант в 2 строки — пояснение ниже
                    for fsz in (13, 12, 11):
                        flh = font(fsz).get_height() + 2
                        if ty + len(wrap_lines(fb, r.w - 28, fsz)) * flh <= r.bottom - 4:
                            break
                    draw_wrapped(surf, fb, (r.x + 14, ty), r.w - 28, fsz, BAD,
                                 max_lines=max(1, (r.bottom - 4 - ty) // flh))
            if sc["picked"] is not None:
                Button(self._seat_btn_rect(), "ДАЛЬШЕ ▶", AMBER).draw(surf, mouse)

    # ----- задание (диагностика/ремонт/тест) -----
    def _part_rects(self):
        out = []
        x, y, w, h, gap = 980, 96, 280, 36, 6
        for i, pid in enumerate(self.cur["parts"]):
            out.append((pid, pygame.Rect(x, y + i * (h + gap), w, h)))
        return out

    TOOL_TILE, TOOL_GAP = 50, 8

    def _tool_rects(self):
        """Плитки-иконки инструментов: 2 ряда по 10 (tech — один ряд из палитры задания)."""
        T, G = self.TOOL_TILE, self.TOOL_GAP
        if self.cur and self.cur.get("track") == "tech":
            return [(tid, pygame.Rect(130 + i * (T + G), 638, T, T))
                    for i, tid in enumerate(self.cur["tools"])]
        per = (len(TOOLS) + 1) // 2                      # два ряда
        return [(tid, pygame.Rect(24 + (i % per) * (T + G), 560 + (i // per) * (T + G), T, T))
                for i, tid in enumerate(TOOLS)]

    def _tool_info_rect(self):
        rects = self._tool_rects()
        right = max(r.right for _, r in rects) + 18
        top = min(r.top for _, r in rects)
        bottom = max(r.bottom for _, r in rects)
        return pygame.Rect(right, top, WIDTH - 24 - right, bottom - top)

    def _right_col_top(self):
        """Низ списка деталей в правой колонке — под ним диагнозы или подсказка призрака."""
        return 96 + len(self.cur["parts"]) * 42

    def _diag_rects(self):
        """Варианты диагноза — в правой колонке под списком деталей (центр отдан коляске)."""
        out = []
        n = len(self.cur["diagnosis"])
        top = self._right_col_top() + 30
        gap = 8
        h = min(68, (712 - top) // n - gap)          # 4 варианта тоже влезают до низа экрана
        x, y, w = 980, top, 280
        for i in range(len(self.cur["diagnosis"])):
            out.append((i, pygame.Rect(x, y + i * (h + gap), w, h)))
        return out

    CHAIR_CX = 575                  # центр зоны коляски: между портретом клиента и правой колонкой

    def _chair_rect(self):
        """Где стоит коляска (пропорции 380x300 — как у арта и хотспотов), крупно по центру.
        В диагнозе — от текста симптома до подсказки «Осмотри детали» (y≈560), над пузырём призрака;
        в ремонте — под инструкцией и точками шагов до панели инструментов (y=560)."""
        if self.phase == "diagnose":
            lines = len(wrap_lines(self.cur["symptom"], 560, 17))
            top = 100 + lines * (font(17).get_height() + 2) + 8
            h = 556 - top
        else:
            top, h = 226, 322
        w = int(h * 380 / 300)
        return pygame.Rect(self.CHAIR_CX - w // 2, top, w, h)

    def _chair_hotspots(self):
        """Кликабельные детали прямо на схеме коляски (экранные координаты)."""
        if self.cur.get("track") == "tech":
            return []
        if self._m3d_mesh() is not None:
            return [(pid, x, y, r) for pid, x, y, r, _ in self._m3d_spots()]
        spots = CHAIR_HOTSPOTS.get(self.cur.get("chair_model") or self.cur.get("kind"), {})
        rect = self._chair_rect()
        kx, ky = rect.w / 380, rect.h / 300
        out = []
        for pid in self.cur["parts"]:
            if pid in spots:
                cx, cy, r = spots[pid]
                out.append((pid, rect.x + int(cx * kx), rect.y + int(cy * ky),
                            max(9, int(r * kx))))
        return out

    def _hotspot_at(self, m):
        """Деталь под курсором/пальцем: ближайший кружок; зона попадания шире кружка (на сенсоре — заметно)."""
        pad = 16 if TOUCH["on"] else 4
        best, bd = None, None
        for pid, x, y, r in self._chair_hotspots():
            d = math.hypot(m[0] - x, m[1] - y)
            if d <= r + pad and (bd is None or d - r < bd):
                best, bd = pid, d - r
        return best

    def _part_num(self, pid):
        """Номер детали: один и тот же в кружке на коляске и в списке справа."""
        try:
            return self.cur["parts"].index(pid) + 1
        except (ValueError, KeyError, TypeError):
            return 0

    # ---------- 3D прямо в окне диагностики (вместо картинки) ----------
    M3D_YAW, M3D_PITCH = -0.75, 0.26          # спереди-слева в три четверти — как нарисован арт колясок

    def _chair_default_view(self):
        return (self.M3D_YAW, self.M3D_PITCH)

    def _m3d_mesh(self):
        """Облегчённая ИИ-модель для окна диагностики или None (тогда — картинка с хотспотами)."""
        if (self.phase not in ("diagnose", "repair", "test") or self.cur.get("track") == "tech"
                or self.ride_t0 is not None):
            return None
        art = self.cur.get("chair_art")
        tt_first = TT_MODE != "0" and get_turntable(art) is not None     # кадры есть — они и на десктопе
        mesh = None if (_np is None or TT_FORCE or tt_first) else get_ai_chair3d(art, lod=True)
        if mesh is None:                                  # браузер или коляска без модели: кадры поворота
            tt = get_turntable(art)
            if tt is None:
                return None
            done = tt.update()                            # показываем с первого пришедшего кадра — не ждём все 36
            if not (done or (tt.frames and not tt.failed)):
                if not tt.art_matched:                    # (и если кадры не скачались — рисунок с кружками модели)
                    return None
                self._m3d_state()["t0"] = -1e9            # кадров ещё нет: рисунок на месте модели, без доворота
                return tt
            if getattr(self, "_tt_seen", None) != (art, id(self.cur)):     # кадры пришли, когда уже был виден
                self._tt_seen = (art, id(self.cur))                         # рисунок (тот же ракурс) — без вводного
                if self.t - getattr(self, "scene_t0", self.t) > 0.15:       # доворота: модель встаёт на место рисунка
                    self._m3d_state()["t0"] = -1e9
            return tt
        return mesh


    def _m3d_state(self):
        m = getattr(self, "m3d", None)
        art = self.cur.get("chair_art") if self.cur else None
        if m is None or m.get("art") != art:
            yw, pt = self._chair_default_view()
            m = self.m3d = dict(yaw=yw, pitch=pt, zoom_k=1.0, art=art, t0=self.t, drag=False,
                                last=None, start=None)
        return m

    def _m3d_view(self):
        """Ракурс: при открытии задания коляска плавно доворачивается к зрителю."""
        s = self._m3d_state()
        k = ease_out(min(1.0, max(0.0, (self.t - s["t0"]) / 1.1)))
        return s["yaw"] - 1.3 * (1 - k), s["pitch"], k < 1.0

    M3D_PAD = 40                    # модель может выходить за рамку (не обрезается по краю)
    M3D_WIDE = 1.18                 # при повороте модель может выйти за окно: по ширине на 18 %, по высоте на 12 %
    M3D_TALL = 1.12                 # (в исходном ракурсе — целиком в окне). Иначе длинные коляски (X8, Jazzy)
                                    # уменьшались под худший ракурс сильнее всех

    def _m3d_zoom(self):
        """Зум, при котором модель целиком влезает в окно при любом повороте (раз на модель и размер окна)."""
        mesh = self._m3d_mesh()
        if isinstance(mesh, Turntable):
            return mesh.z0
        rect = self._chair_rect()
        key = ("m3d_fit", id(mesh), rect.size)
        z = _img_cache.get(key)
        if z is None:
            if not getattr(mesh, "_pivot_fit", False):       # высота центра — раз на модель (как в кадрах поворота)
                V = _np.asarray(mesh.verts, dtype=_np.float64)[::3] - _np.asarray(mesh.pivot)
                _, dy = m3d_fit(V, 380.0, 300.0, self.M3D_YAW, self.M3D_PITCH, self.M3D_WIDE, self.M3D_TALL)
                mesh.pivot = (mesh.pivot[0], mesh.pivot[1] + dy, mesh.pivot[2])
                mesh._pivot_fit = True
            V = _np.asarray(mesh.verts, dtype=_np.float64)[::3] - _np.asarray(mesh.pivot)
            z = _img_cache[key] = m3d_fit_zoom(V, rect.w, rect.h, self.M3D_YAW, self.M3D_PITCH, self.M3D_WIDE,
                                               self.M3D_TALL)
        return z

    def _m3d_frame(self):
        """Прямоугольник проекции с полями и зум под него (кружки и картинка считаются одинаково)."""
        r, pad = self._chair_rect(), self.M3D_PAD
        ext = math.ceil(r.w / 2 * (self.M3D_WIDE - 1))        # запас по ширине (масштаб считается по высоте)
        zk = self._m3d_state().get("zoom_k", 1.0)
        return r.inflate(pad * 2 + ext * 2, pad * 2), self._m3d_zoom() * zk * r.h / (r.h + pad * 2)

    def _m3d_spots(self):
        """Кружки деталей задания на модели: [(деталь, x, y, r, (точка на детали))].
        Пересекающиеся кружки раздвигаются, к детали ведёт выноска."""
        mesh = self._m3d_mesh()
        rect = self._chair_rect()
        yaw, pitch, _ = self._m3d_view()
        s = self._m3d_state()
        key = (round(yaw, 4), round(pitch, 4), round(s.get("zoom_k", 1.0), 3), tuple(rect), tuple(self.cur["parts"]), id(mesh))
        if s.get("spots_key") == key:
            return s["spots"]
        fr, zoom = self._m3d_frame()
        r = max(17, min(20, int(rect.h * 0.05)))     # крупные кружки — под палец на iPad и для всех
        r = int(max(14, min(30, r * s.get("zoom_k", 1.0))))    # крупнее коляска («+») — крупнее кружки и цифры
        pts = []
        for pid in self.cur["parts"]:
            cs = mesh.centers.get(pid)
            if not cs:
                continue
            near = max(cs, key=lambda c: project_point(c, yaw, pitch, fr, zoom, mesh.pivot)[1])
            (x, y), _ = project_point(near, yaw, pitch, fr, zoom, mesh.pivot)
            pts.append([pid, x, y, x, y])
        need = 2 * r + max(8, r)                     # просвет между кружками: видно, к какой точке ведёт выноска
        groups = []                                  # скопления точек (несколько деталей в одном месте)
        for p in pts:
            near = [g for g in groups if any(math.hypot(p[3] - q[3], p[4] - q[4]) < need for q in g)]
            groups = [g for g in groups if all(g is not h for h in near)] + [[p] + [q for g in near for q in g]]
        for g in groups:                             # скопление — веером вокруг его центра, по кругу в том же порядке
            k = len(g)
            if k < 2:
                continue
            cx, cy = sum(q[3] for q in g) / k, sum(q[4] for q in g) / k
            rad = need / (2 * math.sin(math.pi / k)) + r // 2       # чуть дальше от детали — выноска видна
            g.sort(key=lambda q: math.atan2(q[4] - cy, q[3] - cx))
            a0 = (math.atan2(g[0][4] - cy, g[0][3] - cx) if math.hypot(g[0][3] - cx, g[0][4] - cy) > 1
                  else -math.pi / 2)
            for i, q in enumerate(g):
                q[1], q[2] = cx + rad * math.cos(a0 + 2 * math.pi * i / k), cy + rad * math.sin(a0 + 2 * math.pi * i / k)
        for _ in range(60):
            moved = False
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    a, b = pts[i], pts[j]
                    dx, dy = b[1] - a[1], b[2] - a[2]
                    d = math.hypot(dx, dy)
                    if d >= need:
                        continue
                    if d < 0.01:
                        dx, dy, d = math.cos(i + j), math.sin(i + j), 1.0
                    push = (need - d) / 2 + 0.5
                    a[1] -= dx / d * push; a[2] -= dy / d * push
                    b[1] += dx / d * push; b[2] += dy / d * push
                    moved = True
            for q in pts:
                q[1] = min(max(q[1], rect.x + r), rect.right - r)
                q[2] = min(max(q[2], rect.y + r), rect.bottom - r)
            if not moved:
                break
        out = [(pid, int(x), int(y), r, (int(ax), int(ay))) for pid, x, y, ax, ay in pts]
        s["spots_key"], s["spots"] = key, out
        return out

    def _m3d_pick(self, pos):
        """Деталь под курсором на встроенной модели."""
        mesh = self._m3d_mesh()
        rect = self._chair_rect()
        if mesh is None or isinstance(mesh, Turntable) or not rect.collidepoint(pos):
            return None
        yaw, pitch, _ = self._m3d_view()
        fr, zoom = self._m3d_frame()
        polys = project_mesh(mesh, yaw, pitch, pygame.Rect(0, 0, fr.w, fr.h), zoom)
        p = (pos[0] - fr.x, pos[1] - fr.y)
        for depth, pts, col, part, fl in reversed(polys):
            if _pt_in_poly(p, pts):
                return part
        return None

    M3D_ZOOM = (0.75, 1.65, 1.10)          # мин., макс., шаг масштаба коляски в окне задания

    def _m3d_zoom_rects(self):
        """«+» и «−» в правом верхнем углу окна коляски."""
        r = self._chair_rect()
        return pygame.Rect(r.right - 44, r.y + 4, 40, 36), pygame.Rect(r.right - 44, r.y + 44, 40, 36)

    def m3d_zoom(self, steps):
        """Крупнее (+1) / мельче (−1) коляску в окне задания."""
        s = self._m3d_state()
        lo, hi, k = self.M3D_ZOOM
        old = s.get("zoom_k", 1.0)
        s["zoom_k"] = max(lo, min(hi, old * (k ** steps)))
        snd("tick")
        if s["zoom_k"] == old:
            self.flash("Крупнее нельзя." if steps > 0 else "Мельче нельзя.", GHOST, 1.5)

    def _m3d_zoom_on(self):
        return (self.scene == "job" and self.v3d is None and self.cur.get("track") != "tech"
                and self.phase in ("diagnose", "repair") and self._m3d_mesh() is not None)

    def _m3d_event(self, event):
        """Перетаскивание модели в окне диагностики. True = событие поглощено.
        Клик по кружку детали проходит дальше обычным путём (click_job)."""
        if self._m3d_mesh() is None or self.mini_pending or self.show_manual or self.spec_pending:
            return False
        s = self._m3d_state()
        if event.type == pygame.KEYDOWN and event.key in ZOOM_IN_KEYS + ZOOM_OUT_KEYS and self._m3d_zoom_on():
            self.m3d_zoom(1 if event.key in ZOOM_IN_KEYS else -1)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._m3d_zoom_on():
            zin, zout = self._m3d_zoom_rects()
            if zin.collidepoint(event.pos) or zout.collidepoint(event.pos):
                self.m3d_zoom(1 if zin.collidepoint(event.pos) else -1)
                return True
        if event.type == pygame.MOUSEWHEEL and self._chair_rect().collidepoint(mouse_pos()):
            s["zoom_k"] = max(self.M3D_ZOOM[0], min(self.M3D_ZOOM[1], s.get("zoom_k", 1.0) * (self.M3D_ZOOM[2] ** event.y)))
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and self._chair_rect().collidepoint(event.pos):
            yw, pt = self._chair_default_view()
            s.update(yaw=yw, pitch=pt, zoom_k=1.0, t0=-1e9, drag=False)
            snd("tick")
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._chair_rect().collidepoint(event.pos) and self._hotspot_at(event.pos) is None:
                yaw, pitch, _ = self._m3d_view()       # вводный поворот прерываем там, где он сейчас
                s.update(yaw=yaw, t0=-1e9, drag=True, last=event.pos, start=event.pos)
                return True
            return False
        if event.type == pygame.MOUSEMOTION and s["drag"]:
            if not getattr(event, "buttons", (1, 0, 0))[0]:   # кнопку отпустили за окном
                s["drag"] = False
                return False
            dx, dy = event.pos[0] - s["last"][0], event.pos[1] - s["last"][1]
            s["yaw"] += dx * 0.012
            if not isinstance(self._m3d_mesh(), Turntable):          # у кадров поворота наклон один
                s["pitch"] = max(-0.1, min(0.8, s["pitch"] + dy * 0.008))
            s["last"] = event.pos
            if abs(s["yaw"] - s.setdefault("tick_yaw", s["yaw"])) > 0.35:
                s["tick_yaw"] = s["yaw"]
                snd("ratchet")
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and s["drag"]:
            s["drag"] = False
            sx, sy = s["start"] or event.pos
            if abs(event.pos[0] - sx) + abs(event.pos[1] - sy) < 6:
                pid = self._m3d_pick(event.pos)        # просто клик по модели — как клик по этой детали
                if pid and pid in self.cur["parts"]:
                    self._part_clicked(pid)
            return True
        return False

    def _draw_m3d(self, surf, rect, mouse):
        mesh = self._m3d_mesh()
        s = self._m3d_state()
        yaw, pitch, spinning = self._m3d_view()
        fr, zoom = self._m3d_frame()
        if isinstance(mesh, Turntable):
            self._draw_turntable(surf, mesh, rect, mouse, yaw, fr, zoom)
            return
        if gl_ok():                                           # GPU: подсветка детали под кружком — прямо в шейдере
            hover = None if s["drag"] else self._hotspot_at(mouse)
            key = ("gl", round(yaw, 4), round(pitch, 4), round(zoom, 4), tuple(fr), id(mesh), hover)
            if s.get("img_key") != key:
                glr = gl_render(mesh, yaw, pitch, (round(fr.w * RS), round(fr.h * RS)), zoom,
                                hl_part=hover, hl_col=AMBER, hl_amt=0.6)
                if glr is not None:
                    loc = pygame.Rect(0, 0, fr.w, fr.h)
                    big = Surf(fr.size, pygame.SRCALPHA)
                    px = mesh.pivot[0]
                    foot = [project_point((px + fx, 0, fz), yaw, pitch, loc, zoom, mesh.pivot)[0]
                            for fx, fz in ((-470, -310), (470, -310), (470, 310), (-470, 310))]
                    sh = Surf(fr.size, pygame.SRCALPHA)
                    DR.polygon(sh, (0, 0, 0, 110), foot)
                    sw, shh = max(1, fr.w // 10), max(1, fr.h // 10)
                    big.blit(TF.smoothscale(TF.smoothscale(sh, (sw, shh)), fr.size), (0, 0))
                    bb = glr[1].bbox
                    if bb.w and bb.h:
                        pygame.Surface.blit(big, glr[0], bb.topleft, bb)
                    s["img"], s["img_key"] = big, key
            if s.get("img_key") == key:
                surf.blit(s["img"], fr)
                if hover is None and not s["drag"] and rect.collidepoint(mouse):
                    draw_text(surf, "⟲ тяни — повернуть", (rect.x + 4, rect.bottom - 18), 12, (200, 196, 180))
                return
        SS = 1 if (s["drag"] or spinning or RS >= 1.5) else 2      # на большом экране пикселей и так хватает
        key = (round(yaw, 4), round(pitch, 4), round(zoom, 4), tuple(fr), SS, id(mesh))
        if s.get("img_key") != key:
            loc = pygame.Rect(0, 0, fr.w, fr.h)
            big = Surf((fr.w * SS, fr.h * SS), pygame.SRCALPHA)
            # мягкая тень коляски на полу
            px = mesh.pivot[0]
            foot = [(q[0] * SS, q[1] * SS) for q in
                    (project_point((px + fx, 0, fz), yaw, pitch, loc, zoom, mesh.pivot)[0]
                     for fx, fz in ((-470, -310), (470, -310), (470, 310), (-470, 310)))]
            sh = Surf(big.get_size(), pygame.SRCALPHA)
            DR.polygon(sh, (0, 0, 0, 110), foot)
            sw, shh = max(1, big.get_width() // 10), max(1, big.get_height() // 10)
            big.blit(TF.smoothscale(TF.smoothscale(sh, (sw, shh)), big.get_size()), (0, 0))
            polys = project_mesh(mesh, yaw, pitch, loc, zoom, ss=SS * _rs(big))
            for depth, pts, col, part, fl in polys:
                pygame.draw.polygon(big, col, pts)
            s["img"] = big if SS == 1 else TF.smoothscale(big, fr.size)
            s["polys"], s["polys_ss"], s["img_key"], s["hl_key"] = polys, SS, key, None
        surf.blit(s["img"], fr)
        hover = None if s["drag"] else self._hotspot_at(mouse)
        if hover:                                     # деталь под кружком светится сквозь модель
            if s.get("hl_key") != (key, hover):
                k = s["polys_ss"]
                hl = Surf((fr.w * k, fr.h * k), pygame.SRCALPHA)
                for depth, pts, col, part, fl in s["polys"]:
                    if part in hl_group(hover):
                        pygame.draw.polygon(hl, (*tuple(int(c + (a_ - c) * 0.6) for c, a_ in zip(col, AMBER)), 190), pts)
                s["hl"] = hl if k == 1 else TF.smoothscale(hl, fr.size)
                s["hl_key"] = (key, hover)
            surf.blit(s["hl"], fr)
        elif not s["drag"] and rect.collidepoint(mouse):
            draw_text(surf, "⟲ тяни — повернуть", (rect.x + 4, rect.bottom - 18), 12, (200, 196, 180))

    def _draw_turntable(self, surf, tt, rect, mouse, yaw, fr, zoom):
        """Коляска из заранее снятых кадров: ближайший к ракурсу кадр, масштаб и тень — как у живой модели."""
        s = self._m3d_state()
        i = tt.index(yaw)
        if i not in tt.frames and tt.frames:                       # кадры ещё идут: ближайший пришедший
            i = min(tt.frames, key=lambda k: min(abs(k - i), tt.n - abs(k - i)))
        scale = fr.h / 1250.0 * zoom                              # логических пикселей на единицу модели
        ax, ay = fr.x + fr.w / 2, fr.y + fr.h * 0.54
        key = ("tt", i, tuple(fr), round(zoom, 4))
        if s.get("sh_key") != key:                                # мягкая тень на полу (раз на кадр)
            loc = pygame.Rect(0, 0, fr.w, fr.h)
            yw = tt.yaw0 + i * 2 * math.pi / tt.n
            px = tt.pivot[0]
            foot = [project_point((px + fx, 0, fz), yw, tt.pitch, loc, zoom, tt.pivot)[0]
                    for fx, fz in ((-470, -310), (470, -310), (470, 310), (-470, 310))]
            sh = Surf((max(1, fr.w // 10), max(1, fr.h // 10)), pygame.SRCALPHA)
            DR.polygon(sh, (0, 0, 0, 110), [(x / 10, y / 10) for x, y in foot])
            s["sh"], s["sh_key"] = TF.smoothscale(sh, fr.size), key
        surf.blit(s["sh"], fr)
        if not tt.frames:                                          # кадры ещё идут: рисунок — тот же кадр, то же место
            surf.blit(load_image(self.cur["chair_art"], tuple(self._chair_rect().size), AMBER), self._chair_rect())
            return
        img = tt.image(i, scale * RS / tt.ref)
        if img is not None:
            ox, oy = tt.offsets[i]
            pygame.Surface.blit(surf, img, (round((ax + ox * scale) * RS), round((ay + oy * scale) * RS)))
        if not s["drag"] and rect.collidepoint(mouse) and self._hotspot_at(mouse) is None:
            draw_text(surf, "⟲ тяни — повернуть", (rect.x + 4, rect.bottom - 18), 12, (200, 196, 180))

    # ---------- 3D-осмотр: оверлей ----------
    # С 2026-10-19 из интерфейса не открывается (ни кнопки, ни клавиши V): модель крутится прямо на экране
    # задания во всех фазах. Код оставлен для art_tests/v3d_sheet.py и на случай возврата окна.
    V3D_SS = 2                      # суперсэмплинг модели (сглаживание)

    def open_v3d(self):
        if not self.cur or self.cur.get("track") == "tech":     # у заданий Гильдии нет деталей для осмотра
            return
        # настоящая модель — по умолчанию, если есть numpy (без него 30 тыс. граней тормозят)
        ai_default = _np is not None and get_ai_chair3d(self.cur.get("chair_art")) is not None
        self.v3d = dict(yaw=-0.75, pitch=0.28, ai=ai_default,
                        zoom=0.8 if self.cur.get("kind") == "power" else 0.9,
                        drag=False, last=None, start=None,
                        vel=0.0, idle=0.0, target=None, t0=self.t, clue=None, hl=None)
        if self._m3d_mesh() is not None:
            yaw, pitch, _ = self._m3d_view()
            self.v3d.update(yaw=yaw, pitch=pitch)
        snd("whoosh")

    def _v3d_btn_rect(self):
        c = self._chair_rect()
        return pygame.Rect(c.right + 8, c.bottom - 30, 118, 28)

    def _v3d_panel_rect(self):
        return pygame.Rect(30, 62, WIDTH - 60, HEIGHT - 80)

    def _v3d_view_rect(self):
        p = self._v3d_panel_rect()
        return pygame.Rect(p.x + 16, p.y + 52, p.w - 360, p.h - 116)

    def _v3d_close_rect(self):
        p = self._v3d_panel_rect()
        return pygame.Rect(p.right - 190, p.bottom - 54, 170, 40)

    def _v3d_side_rect(self):
        p = self._v3d_panel_rect()
        return pygame.Rect(p.right - 330, p.y + 52, 314, p.h - 116)

    def _v3d_reset_rect(self):
        p = self._v3d_panel_rect()
        return pygame.Rect(p.right - 376, p.bottom - 54, 170, 40)

    def _v3d_part_rects(self):
        sr = self._v3d_side_rect()
        return [(pid, pygame.Rect(sr.x + 10, sr.y + 40 + i * 44, sr.w - 20, 38))
                for i, pid in enumerate(self.cur["parts"])]

    def _v3d_zoom_rects(self):
        r = self._v3d_reset_rect()
        return pygame.Rect(r.x - 100, r.y, 44, 40), pygame.Rect(r.x - 50, r.y, 44, 40)

    def _v3d_zoom(self, steps):
        v = self.v3d
        v["zoom"] = max(0.7, min(2.2, v["zoom"] * (1.12 ** steps)))
        v["idle"] = 0.0
        snd("tick")

    def _v3d_ai_rect(self):
        p = self._v3d_panel_rect()
        return pygame.Rect(p.x + 16, p.bottom - 54, 300, 40)

    def _v3d_ai_available(self):
        return get_ai_chair3d(self.cur.get("chair_art")) is not None

    def _v3d_mesh(self):
        if self.v3d and self.v3d.get("ai") and self._v3d_ai_available():
            return get_ai_chair3d(self.cur.get("chair_art"))
        model = self.cur.get("chair_model")
        kind = model if model in ("m3",) else self.cur.get("kind")   # своей 3D-модели нет — общая по типу
        return get_chair3d(kind, CHAIR3D_FRAME.get(self.cur.get("chair_art")) if kind == "manual" else None)

    def _v3d_focus(self, pid):
        """Плавно развернуть коляску деталью к зрителю."""
        c = self._v3d_near_center(pid)
        if not c:
            return
        x, z = c[0] - self._v3d_mesh().pivot[0], c[2]
        if abs(x) + abs(z) < 60:
            return
        tgt = math.atan2(-x, z)
        cur = self.v3d["yaw"]
        tgt = cur + ((tgt - cur + math.pi) % (2 * math.pi) - math.pi)
        self.v3d["target"] = tgt
        self.v3d["vel"] = 0.0

    def _v3d_near_center(self, pid, yaw=None, pitch=None):
        """Центр детали на ближней к зрителю стороне (у парных — левая/правая)."""
        pts = self._v3d_mesh().centers.get(pid)
        if not pts:
            return None
        v = self.v3d
        vr = self._v3d_view_rect()
        y = v["yaw"] if yaw is None else yaw
        pt = v["pitch"] if pitch is None else pitch
        piv = self._v3d_mesh().pivot
        return max(pts, key=lambda c: project_point(c, y, pt, vr, v["zoom"], piv)[1])

    def _v3d_inspect(self, pid):
        self.inspect_part(pid)
        self.toast_timer = 0          # улика показывается в карточке, без дубля сверху
        self.v3d["clue"] = (pid, self.cur["inspect"].get(pid, "Тут вроде всё в порядке."))
        self.v3d["clue_t"] = self.t

    def handle_v3d_event(self, event):
        """Модальные события 3D-осмотра. True = событие поглощено."""
        v = self.v3d
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
                self.v3d = None
                snd("whoosh_out")
            elif event.key in ZOOM_IN_KEYS:
                self._v3d_zoom(1)
            elif event.key in ZOOM_OUT_KEYS:
                self._v3d_zoom(-1)
            elif event.key == pygame.K_r:
                yw0, pt0 = self._chair_default_view()
                v.update(target=yw0 + round((v["yaw"] - yw0) / (2 * math.pi)) * 2 * math.pi,
                         zoom=0.8 if self.cur.get("kind") == "power" else 0.9, pitch=pt0, vel=0.0, idle=0.0)
                snd("tick")
            return True
        if event.type == pygame.MOUSEWHEEL:
            v["zoom"] = max(0.7, min(2.2, v["zoom"] * (1.12 ** event.y)))
            v["idle"] = 0.0
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            yw0, pt0 = self._chair_default_view()
            v.update(target=yw0 + round((v["yaw"] - yw0) / (2 * math.pi)) * 2 * math.pi,
                     zoom=0.8 if self.cur.get("kind") == "power" else 0.9, pitch=pt0, vel=0.0, idle=0.0)
            snd("tick")
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._v3d_close_rect().collidepoint(event.pos):
                self.v3d = None
                snd("whoosh_out")
                return True
            if self._v3d_ai_available() and self._v3d_ai_rect().collidepoint(event.pos):
                v["ai"] = not v.get("ai")
                snd("tick")
                return True
            zin, zout = self._v3d_zoom_rects()
            if zin.collidepoint(event.pos) or zout.collidepoint(event.pos):
                self._v3d_zoom(1 if zin.collidepoint(event.pos) else -1)
                return True
            if self._v3d_reset_rect().collidepoint(event.pos):
                yw0, pt0 = self._chair_default_view()
                v.update(target=yw0 + round((v["yaw"] - yw0) / (2 * math.pi)) * 2 * math.pi,
                         zoom=0.8 if self.cur.get("kind") == "power" else 0.9, pitch=pt0, vel=0.0, idle=0.0)
                snd("tick")
                return True
            for pid, rect in self._v3d_part_rects():
                if rect.collidepoint(event.pos):
                    self._v3d_focus(pid)
                    self._v3d_inspect(pid)
                    return True
            if self._v3d_view_rect().collidepoint(event.pos):
                v.update(drag=True, last=event.pos, start=event.pos, vel=0.0, target=None, idle=0.0)
            return True
        if event.type == pygame.MOUSEMOTION and v["drag"]:
            dx = event.pos[0] - v["last"][0]
            dy = event.pos[1] - v["last"][1]
            v["yaw"] += dx * 0.010
            v["vel"] = dx * 0.010
            v["pitch"] = max(-0.25, min(0.95, v["pitch"] + dy * 0.008))
            v["last"] = event.pos
            if abs(v["yaw"] - v.get("tick_yaw", v["yaw"])) > 0.35:     # «трещотка» поворотного стола
                v["tick_yaw"] = v["yaw"]
                snd("ratchet")
            v.setdefault("tick_yaw", v["yaw"])
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if v["drag"]:
                v["drag"] = False
                v["idle"] = 0.0
                sx, sy = v.get("start") or event.pos
                if abs(event.pos[0] - sx) + abs(event.pos[1] - sy) < 6:
                    v["vel"] = 0.0
                    pid = self._v3d_pick(event.pos)
                    if pid:
                        self._v3d_inspect(pid)
            return True
        return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP)

    def update_v3d(self, dt):
        v = self.v3d
        if v["drag"]:
            return
        v["idle"] += dt
        if v.get("target") is not None:
            d = v["target"] - v["yaw"]
            v["yaw"] += d * min(1.0, dt * 6)
            if abs(d) < 0.003:
                v["target"] = None
        elif abs(v["vel"]) > 0.0005:
            v["yaw"] += v["vel"]
            v["vel"] *= 0.9 ** (dt * 60)
        elif v["idle"] > 2.5:
            v["yaw"] += dt * 0.25                    # медленное авто-вращение, если не трогают

    def _v3d_pick(self, pos):
        vr = self._v3d_view_rect()
        if not vr.collidepoint(pos):
            return None
        v = self.v3d
        polys = project_mesh(self._v3d_mesh(), v["yaw"], v["pitch"], vr, v["zoom"])
        p = (pos[0] - vr.x, pos[1] - vr.y)
        for depth, pts, col, part, fl in reversed(polys):
            if _pt_in_poly(p, pts):
                return part
        return None

    def _v3d_backdrop(self, size):
        key = ("v3d_bg", size)
        bg = _img_cache.get(key)
        if bg is None:
            bg = Surf(size)
            w, h = size
            for y in range(h):
                k = y / h
                bg.fill((int(34 - 18 * k), int(44 - 22 * k), int(58 - 26 * k)), (0, y, w, 1))
            add_glow(bg, (w // 2, int(h * 0.42)), int(h * 0.55), (40, 48, 60), 1.0)
            _img_cache[key] = bg
        return bg

    def _draw_v3d(self, surf, mouse):
        _cap_modal()
        v = self.v3d
        ok = ease_out((self.t - v["t0"]) / 0.3)
        da = int(200 * ok) // 8 * 8                           # затемнение и панель — из кэша (при ×2 это полноэкранные слои)
        dim = _img_cache.get(("v3d_dim", da, RS))
        if dim is None:
            dim = _img_cache[("v3d_dim", da, RS)] = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((8, 8, 12, da))
        surf.blit(dim, (0, 0))
        p = self._v3d_panel_rect().move(0, int(30 * (1 - ok)))
        s = _img_cache.get(("v3d_panel", p.size, RS))
        if s is None:
            s = _img_cache[("v3d_panel", p.size, RS)] = Surf(p.size, pygame.SRCALPHA)
            aa_rect(s, (16, 18, 24, 250), s.get_rect(), border_radius=14)
        surf.blit(s, p)
        aa_rect(surf, CYAN, p, 2, border_radius=14)
        hr = draw_text(surf, "ОСМОТР 3D", (p.x + 22, p.y + 14), 22, CYAN, bold=True)
        draw_text(surf, f"{self.cur['client']} — {self.cur.get('chair_name') or ('электроколяска' if self.cur.get('kind') == 'power' else 'ручная коляска')}",
                  (hr.right + 16, p.y + 19), 15, GREY)
        vr = self._v3d_view_rect().move(0, int(30 * (1 - ok)))
        mesh = self._v3d_mesh()
        yaw, pitch, zoom = v["yaw"] - 1.6 * (1 - ok), v["pitch"], v["zoom"]
        view = self._v3d_backdrop(vr.size).copy()
        loc = pygame.Rect(0, 0, vr.w, vr.h)
        # подиум: диск с рисками (видно, что стол вращается) и мягкая тень
        piv = mesh.pivot
        px = piv[0]
        disc = [project_point((px + 720 * math.cos(a * math.pi / 24), 0, 720 * math.sin(a * math.pi / 24)),
                              yaw, pitch, loc, zoom, piv)[0] for a in range(48)]
        DR.polygon(view, (40, 48, 60), disc)
        DR.polygon(view, (70, 84, 100), disc, 2)
        for a in range(0, 48, 4):
            q1 = project_point((px + 650 * math.cos(a * math.pi / 24), 0, 650 * math.sin(a * math.pi / 24)), yaw, pitch, loc, zoom, piv)[0]
            q2 = project_point((px + 715 * math.cos(a * math.pi / 24), 0, 715 * math.sin(a * math.pi / 24)), yaw, pitch, loc, zoom, piv)[0]
            DR.line(view, (84, 100, 118), q1, q2, 2)
        foot = [project_point((px + q[0], 0, q[2]), yaw, pitch, loc, zoom, piv)[0] for q in
                ((-510, 0, -330), (510, 0, -330), (510, 0, 330), (-510, 0, 330))]
        key_sh = ("v3d_shadow", tuple((round(x), round(y)) for x, y in foot), vr.size, RS)   # мягкая тень (кэш по положению)
        shadow = _img_cache.get(key_sh)
        if shadow is None:
            w4, h4 = max(1, vr.w // 2), max(1, vr.h // 2)
            s1 = pygame.Surface((w4, h4), pygame.SRCALPHA)
            pygame.draw.polygon(s1, (0, 0, 0, 120), [(x / 2, y / 2) for x, y in foot])
            for _ in range(3):                                  # размытие: вниз в 4 раза и обратно
                s1 = pygame.transform.smoothscale(pygame.transform.smoothscale(s1, (max(1, w4 // 4), max(1, h4 // 4))), (w4, h4))
            shadow = pygame.transform.smoothscale(s1, (round(vr.w * RS), round(vr.h * RS)))
            if len([k for k in _img_cache if k[0] == "v3d_shadow"]) > 40:
                for k in [k for k in _img_cache if k[0] == "v3d_shadow"]:
                    del _img_cache[k]
            _img_cache[key_sh] = shadow
        xs = [x for x, y in foot]; ys = [y for x, y in foot]          # тень — только вокруг пятна
        sb = pygame.Rect(round((min(xs) - 60) * RS), round((min(ys) - 60) * RS),
                         round((max(xs) - min(xs) + 120) * RS), round((max(ys) - min(ys) + 120) * RS)).clip(shadow.get_rect())
        if sb.w and sb.h:
            pygame.Surface.blit(view, shadow, sb.topleft, sb)
        # модель
        side_hl = v.get("hl")
        pulse = 0.5 + 0.5 * wsin(self.t * 6)
        hover = None
        glr = gl_render(mesh, yaw, pitch, (round(vr.w * RS), round(vr.h * RS)), zoom,
                        hl_part=side_hl, hl_col=AMBER, hl_amt=0.45 * pulse,
                        hover_part=v.get("hov"), hover_amt=0.35) if gl_ok() else None
        if glr is not None:                                   # GPU: плавный свет, сглаживание, деталь под курсором — из буфера номеров
            img, pick = glr
            if vr.collidepoint(mouse) and not v["drag"]:
                hover = pick((mouse[0] - vr.x) * RS, (mouse[1] - vr.y) * RS)
            v["hov"] = hover
            bb = pick.bbox                                       # только прямоугольник модели (быстрее при ×2)
            if bb.w and bb.h:
                pygame.Surface.blit(view, img, bb.topleft, bb)
            polys = None
        SS = 1 if (v["drag"] or abs(v.get("vel", 0)) > 0.002 or v.get("target") is not None or RS >= 1.5) else self.V3D_SS
        polys = project_mesh(mesh, yaw, pitch, loc, zoom, ss=SS * RS) if glr is None else []
        if glr is None and vr.collidepoint(mouse) and not v["drag"]:
            mp = ((mouse[0] - vr.x) * SS * RS, (mouse[1] - vr.y) * SS * RS)
            for depth, pts, col, part, fl in reversed(polys):
                if _pt_in_poly(mp, pts):
                    hover = part
                    break
        big = Surf((vr.w * SS, vr.h * SS), pygame.SRCALPHA)
        for depth, pts, col, part, fl in polys:
            if part and part in hl_group(hover):
                col = _shade(col, 1.35)
            elif part and part in hl_group(side_hl):
                col = tuple(int(c + (a - c) * 0.45 * pulse) for c, a in zip(col, AMBER))
            pygame.draw.polygon(big, col, pts)
            if fl & M_EDGE:
                pygame.draw.polygon(big, _shade(col, 0.45), pts, max(1, round(2 * RS)))
        if glr is None:
            view.blit(TF.smoothscale(big, vr.size), (0, 0))
        # маркеры деталей задания: пульс — ещё не осмотрено, галочка — осмотрено
        for i, pid in enumerate(self.cur["parts"]):
            c = self._v3d_near_center(pid, yaw, pitch)
            if not c:
                continue
            (mx, my), _ = project_point(c, yaw, pitch, loc, zoom, piv)
            if pid in self.inspected:
                aa_circle(view, GOOD, (int(mx), int(my)), 9)
                draw_text(view, "✔", (int(mx), int(my) - 1), 13, (16, 30, 20), bold=True, center=True)
            else:
                ph = (self.t * 0.9 + i * 0.21) % 1.0
                rr = int(8 + 12 * ease_out(ph))
                ring = Surf((rr * 2 + 4, rr * 2 + 4), pygame.SRCALPHA)
                aa_circle(ring, (*AMBER, int(200 * (1 - ph))), (rr + 2, rr + 2), rr, 2)
                view.blit(ring, (mx - rr - 2, my - rr - 2))
                aa_circle(view, AMBER, (int(mx), int(my)), 4)
        corners = _img_cache.get(("v3d_corners", vr.size, RS))  # скруглённые углы: накладка цвета панели (вместо маски каждый кадр)
        if corners is None:
            corners = _img_cache[("v3d_corners", vr.size, RS)] = Surf(vr.size, pygame.SRCALPHA)
            corners.fill((16, 18, 24, 255))
            hole = Surf(vr.size, pygame.SRCALPHA)
            aa_rect(hole, (255, 255, 255, 255), hole.get_rect(), border_radius=10)
            corners.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        view.blit(corners, (0, 0))
        surf.blit(view, vr)
        aa_rect(surf, (60, 72, 88), vr, 1, border_radius=10)
        if hover:
            label = PARTS.get(hover, hover)
            w = font(15, True).size(tr(label))[0] + 22
            rect = pygame.Rect(mouse[0] - w // 2, mouse[1] - 40, w, 26)
            rect.clamp_ip(vr)
            tip = Surf(rect.size, pygame.SRCALPHA)
            aa_rect(tip, (18, 16, 24, 240), tip.get_rect(), border_radius=7)
            surf.blit(tip, rect)
            aa_rect(surf, AMBER if hover in self.cur["parts"] else WHITE, rect, 1, border_radius=7)
            draw_text(surf, label, rect.center, 15, WHITE, bold=True, center=True)
        draw_text(surf, "ЛКМ — вращать · колесо или +/− — зум · клик по детали — осмотр · Esc — закрыть",
                  (vr.x + 12, vr.bottom - 26), 13, (150, 160, 175))
        # панель справа: детали задания, прогресс, находка
        sr = self._v3d_side_rect().move(0, int(30 * (1 - ok)))
        side = Surf(sr.size, pygame.SRCALPHA)
        aa_rect(side, (24, 26, 34, 240), side.get_rect(), border_radius=10)
        surf.blit(side, sr)
        draw_text(surf, "ДЕТАЛИ ЗАДАНИЯ", (sr.x + 14, sr.y + 12), 15, AMBER, bold=True)
        v["hl"] = None
        for i, (pid, rect) in enumerate(self._v3d_part_rects()):
            rect = rect.move(int(80 * (1 - appear(self.t - v["t0"], 0.15 + 0.05 * i, 0.3))), int(30 * (1 - ok)))
            hov = rect.collidepoint(mouse)
            if hov:
                v["hl"] = pid
            done = pid in self.inspected
            h = _hover_amt(("v3dpart", pid), 1.0 if hov else 0.0)
            aa_rect(surf, tuple(int(a + (b - a) * h) for a, b in zip(PANEL, PANEL2)), rect, border_radius=8)
            aa_rect(surf, GOOD if done else (AMBER if hov else DIM), rect, 2, border_radius=8)
            draw_text(surf, PARTS[pid], (rect.x + 14, rect.y + 9), 16, WHITE)
            draw_text(surf, "✔" if done else "◎", (rect.right - 14, rect.y + 8), 17, GOOD if done else AMBER,
                      right=True)
        n_ok = len(self.inspected)
        py = sr.y + 50 + len(self.cur["parts"]) * 44
        draw_text(surf, f"Осмотрено: {n_ok} (нужно {INSPECT_REQ})", (sr.x + 14, py), 14, GHOST)
        bar = pygame.Rect(sr.x + 14, py + 22, sr.w - 28, 8)
        aa_rect(surf, (40, 44, 56), bar, border_radius=4)
        fill = bar.copy()
        fill.w = int(bar.w * min(1.0, n_ok / INSPECT_REQ))
        if fill.w:
            aa_rect(surf, GOOD if n_ok >= INSPECT_REQ else AMBER, fill, border_radius=4)
        if v.get("clue"):
            pid, text = v["clue"]
            ck = appear(self.t - v.get("clue_t", 0), 0, 0.3)
            card = pygame.Rect(sr.x + 10, py + 44 + int(16 * (1 - ck)), sr.w - 20, sr.bottom - py - 54)
            cs = Surf(card.size, pygame.SRCALPHA)
            aa_rect(cs, (20, 40, 46, int(235 * ck)), cs.get_rect(), border_radius=8)
            surf.blit(cs, card)
            aa_rect(surf, CYAN, card, 1, border_radius=8)
            draw_text(surf, "НАХОДКА: " + PARTS.get(pid, pid), (card.x + 12, card.y + 10), 14, CYAN, bold=True)
            draw_wrapped(surf, text, (card.x + 12, card.y + 34), card.w - 24, 14, WHITE,
                         limit=self.typed("v3d_clue", text, cps=90))
        zin, zout = self._v3d_zoom_rects()
        Button(zin, "+", CYAN).draw(surf, mouse)
        Button(zout, "−", CYAN).draw(surf, mouse)
        Button(self._v3d_reset_rect(), "СБРОС ВИДА [R]", CYAN).draw(surf, mouse)
        if self._v3d_ai_available():
            Button(self._v3d_ai_rect(), "МОДЕЛЬ: ДЕТАЛЬНАЯ" if v.get("ai") else "МОДЕЛЬ: ПО ЧЕРТЕЖУ",
                   PURPLE if v.get("ai") else GHOST).draw(surf, mouse)
        Button(self._v3d_close_rect(), "ЗАКРЫТЬ [Esc]", AMBER).draw(surf, mouse)

    def _draw_hotspots(self, surf, mouse):
        hover = None
        if self._m3d_mesh() is not None:              # на 3D: тёмная подложка и выноска к детали
            for pid, x, y, r, (ax, ay) in self._m3d_spots():
                if abs(ax - x) + abs(ay - y) > r * 0.6:      # выноска к детали — с тёмной обводкой, видна на любом фоне
                    DR.line(surf, (14, 12, 20), (ax, ay), (x, y), 4)
                    DR.line(surf, AMBER, (ax, ay), (x, y), 2)
                    aa_circle(surf, (14, 12, 20), (ax, ay), 5)
                    aa_circle(surf, AMBER, (ax, ay), 3)
                disc = Surf((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                aa_circle(disc, (12, 12, 18, 110), (r + 1, r + 1), r)
                surf.blit(disc, (x - r - 1, y - r - 1))
        for i, (pid, x, y, r) in enumerate(self._chair_hotspots()):
            done = self.phase == "diagnose" and pid in self.inspected
            if self.phase == "diagnose" and not done and not calm() and DISPLAY["glow"]:   # зовёт пульсом
                ph = (self.t * 0.8 + i * 0.17) % 1.0
                rr = int(r + 10 * ease_out(ph))
                ring = Surf((rr * 2 + 4, rr * 2 + 4), pygame.SRCALPHA)
                aa_circle(ring, (*AMBER, int(150 * (1 - ph))), (rr + 2, rr + 2), rr, 2)
                surf.blit(ring, (x - rr - 2, y - rr - 2))
            aa_circle(surf, (14, 12, 20), (x, y), r + 2, 5)          # тёмная подложка: кольцо видно и на белом арте
            aa_circle(surf, GOOD if done else AMBER, (x, y), r, 2)
            n = self._part_num(pid)
            if n:                                                    # номер — как в списке деталей справа
                aa_circle(surf, (14, 12, 20, 200), (x, y), max(6, r - 3))
                draw_text(surf, str(n), (x, y), max(11, min(21, round(r * 0.95))), GOOD if done else AMBER,
                          bold=True, center=True)
            if (mouse[0] - x) ** 2 + (mouse[1] - y) ** 2 <= r * r:
                hover = (pid, x, y, r)
        if hover:
            pid, x, y, r = hover
            aa_circle(surf, WHITE, (x, y), r + 3, 2)
            label = PARTS[pid]
            w = font(14).size(tr(label))[0] + 16
            rect = pygame.Rect(x - w // 2, y - r - 30, w, 22)
            rect.clamp_ip(pygame.Rect(0, 56, WIDTH, HEIGHT - 56))
            tip = Surf(rect.size, pygame.SRCALPHA)
            tip.fill((18, 16, 24, 235))
            surf.blit(tip, rect)
            aa_rect(surf, WHITE, rect, 1, border_radius=5)
            draw_text(surf, label, rect.center, 14, WHITE, center=True)

    def _test_btn_rect(self):
        return pygame.Rect(WIDTH // 2 - 170, 560, 340, 64)

    def _draw_ride_done(self, surf):
        """После проезда: отметка над кнопкой «ГОТОВО» — проверка пройдена, итог по нажатию."""
        if self.ride_done:
            r = self._test_btn_rect()
            draw_text(surf, "✔ Проверка пройдена", (r.centerx, r.y - 22), 17, GOOD, bold=True, center=True,
                      plate=True)

    def draw_job(self, surf):
        if self.cur.get("track") == "tech":
            self.draw_job_tech(surf)
            return
        self._bg(surf, "bg_workshop.png", WOOD)
        job = self.cur
        self._topbar(surf, job["title"], job.get("chair_name"))
        mouse = mouse_pos()

        # клиент слева
        blit_idle(surf, load_image(job["client_art"], (150, 190), GHOST), (24, 70), self.t)
        draw_text(surf, job["client"], (24, 266), 16, WHITE, bold=True)
        if self.ride_t0 is None:
            self._draw_client_bubble(surf)

        # коляска по центру — детали кликабельны прямо на схеме
        crect = self._chair_rect()
        if self.ride_t0 is None:
            if self.ride_done:                    # после проезда клиент в починенной коляске (и без анимации —
                img = load_image(job["client_art"], (230, 250), GHOST)   # «не было картинки проезда»)
                blit_idle(surf, img, img.get_rect(center=crect.center).topleft, self.t)
            elif self._m3d_mesh() is not None:
                self._draw_m3d(surf, crect, mouse)
                if self._m3d_zoom_on():
                    zin, zout = self._m3d_zoom_rects()
                    Button(zin, "+", CYAN).draw(surf, mouse)
                    Button(zout, "−", CYAN).draw(surf, mouse)
            else:
                surf.blit(load_image(job["chair_art"], tuple(crect.size), AMBER), crect)
        if self.phase in ("diagnose", "repair"):
            self._draw_hotspots(surf, mouse)

        # подсказка призрака: в диагнозе — ниже вариантов, в ремонте — под коляской
        if self.ride_t0 is None:                  # на тест-драйве сцена — у проезжающего клиента
            if self.phase == "diagnose":
                self._draw_ghost_bubble(surf, 584)
            else:
                top = self._right_col_top() + 10
                self._draw_ghost_bubble(surf, col=pygame.Rect(980, top, 280, 552 - top))

        if self.phase == "diagnose":
            draw_text(surf, "ДИАГНОСТИКА", (360, 70), 20, CYAN, bold=True)
            draw_wrapped(surf, job["symptom"], (360, 100), 560, 17, WHITE)
            unlocked = len(self.inspected) >= INSPECT_REQ
            tip = ("Улики собраны — выбери диагноз:" if unlocked else
                   f"Осмотри детали (клик по коляске или списку): {len(self.inspected)}/{INSPECT_REQ}")
            draw_text(surf, tip, (360, crect.bottom + 4), 15, GREY if unlocked else AMBER, bold=not unlocked)
            draw_text(surf, "ДИАГНОЗ", (980, self._right_col_top() + 6), 16, CYAN if unlocked else DIM, bold=True)
            drects = self._diag_rects()
            dsize = 11                                     # один размер на весь список: самый крупный, где влезают все
            for dsize in (14, 13, 12, 11):
                if all(len(wrap_lines(job["diagnosis"][i]["text"], r.w - 24, dsize)) * (font(dsize).get_height() + 2)
                       <= r.h - 12 for i, r in drects):
                    break
            for i, rect in drects:
                Button(rect, "", CYAN if unlocked else DIM).draw(surf, mouse, enabled=unlocked)
                text = job["diagnosis"][i]["text"]
                draw_wrapped(surf, text, (rect.x + 12, rect.y + 6), rect.w - 24, dsize, WHITE if unlocked else GREY)
            self._draw_parts(surf, mouse, "ОСМОТРЕТЬ")
        elif self.phase == "repair":
            n = len(job["steps"])
            hdr = draw_text(surf, f"РЕМОНТ — шаг {self.step_idx + 1}/{n}", (360, 70), 20, AMBER, bold=True)
            # прогресс-точки — в строке заголовка (раньше лежали под заметкой и пересекались с ней)
            self._draw_step_dots(surf, n, (hdr.right + 22, hdr.centery), right=self._step_prev_rect().x - 18)
            Button(self._step_prev_rect(), "◂", CYAN).draw(surf, mouse, enabled=self.step_idx > 0)
            Button(self._step_skip_rect(), "ШАГ ▸", AMBER).draw(surf, mouse)
            step = job["steps"][self.step_idx]
            draw_wrapped(surf, step["instr"], (360, 100), 560, 19, WHITE)   # итог прошлого шага — сверху и в «◂»
            self._draw_parts(surf, mouse, "ДЕТАЛЬ")
            self._draw_tools(surf, mouse)
        elif self.phase == "test":
            draw_text(surf, "ТЕСТ-ДРАЙВ", (360, 70), 20, GOOD, bold=True)
            draw_wrapped(surf, job["test"], (360, 100), 560, 19, WHITE)
            if self.ride_t0 is None:
                self._draw_ride_done(surf)
                Button(self._test_btn_rect(), "ГОТОВО ▸" if self.ride_done else "ПРОКАТИТЬ И ПРОВЕРИТЬ",
                       GOOD).draw(surf, mouse)
            else:
                self._draw_ride(surf)
        if self.v3d is None:
            self._draw_action(surf)
        if self.mini_pending:
            self._draw_mini_overlay(surf, mouse)
        if self.v3d is not None:
            self._draw_v3d(surf, mouse)
        self._draw_tool_in_hand(surf, mouse)

    def _draw_client_bubble(self, surf):
        """Пузырь речи клиента под портретом: что он говорит прямо сейчас."""
        if not self.client_line:
            return
        line = tr(self.client_line)               # перевод — целиком, потом делим на «кто: что»
        name, _, text = line.partition(":")
        if not text:
            name, text = "", line
        text = text.strip()
        bottom = 572 if self.phase == "diagnose" else 548
        w, tw = 300, 272
        for size in (15, 14, 13):
            lines = wrap_lines(tr(text), tw, size)
            lh = font(size).get_height() + 2
            if 34 + len(lines) * lh + 12 <= bottom - 296:
                break
        h = 34 + len(lines) * lh + 12
        k = ease_back((self.t - self.client_t) / 0.35)
        if k <= 0.01:
            return
        box = Surf((w, h), pygame.SRCALPHA)
        aa_rect(box, (44, 36, 28, 235), box.get_rect(), border_radius=12)
        aa_rect(box, AMBER, box.get_rect(), 2, border_radius=12)
        draw_text(box, name.strip(), (14, 9), 14, AMBER, bold=True)
        draw_wrapped(box, text, (14, 32), tw, size, (240, 232, 214),
                     limit=self.typed("client", text, cps=80))
        if k < 1:
            box = TF.rotozoom(box, 0, k)
        r = box.get_rect(midtop=(18 + w // 2, 296 + int(h * (1 - k) / 2)))
        DR.polygon(surf, AMBER, [(70, 284), (60, r.y + 2), (92, r.y + 2)])
        DR.polygon(surf, (44, 36, 28), [(70, 289), (63, r.y + 4), (89, r.y + 4)])
        surf.blit(box, r)

    def _draw_step_dots(self, surf, n, at=(360, 205), right=960):
        x, y = at
        if x + (n - 1) * 22 > right:                  # длинное задание — точки плотнее, в пределах центра
            step = max(6.0, (right - x - 8) / max(1, n - 1))   # (крупный шрифт: заголовок шире — точки ещё плотнее)
        else:
            step = 22
        r = 7 if step >= 22 else max(3, int(step // 3))
        aa_rect(surf, (14, 12, 20, 190), (x - r - 7, y - r - 6, round((n - 1) * step) + 2 * r + 14, 2 * r + 12), border_radius=r + 6)
        for i in range(n):
            c = GOOD if i < self.step_idx else (AMBER if i == self.step_idx else DIM)
            cx = round(x + i * step)
            aa_circle(surf, c, (cx, y), r)
            if i > self.step_idx:                     # впереди: светлая обводка — видно на любом фоне
                aa_circle(surf, (150, 150, 170), (cx, y), r, 1)
            if i == self.step_idx:
                aa_circle(surf, AMBER, (cx, y), r + 3, 2)

    def _draw_parts(self, surf, mouse, header):
        draw_text(surf, header, (980, 70), 16, AMBER, bold=True)
        for i, (pid, rect) in enumerate(self._part_rects()):
            hov = rect.collidepoint(mouse)
            rect = rect.move(int(160 * (1 - appear(self.st, 0.05 * i, 0.35))), 0)
            aa_rect(surf, PANEL2 if hov else PANEL, rect, border_radius=6)
            aa_rect(surf, AMBER if hov else DIM, rect, 2, border_radius=6)
            nc = (rect.x + 17, rect.centery)                         # номер детали — как в кружке на коляске
            aa_circle(surf, (14, 12, 20), nc, 11)
            aa_circle(surf, GOOD if (self.phase == "diagnose" and pid in self.inspected) else AMBER, nc, 11, 2)
            draw_text(surf, str(i + 1), nc, 13, WHITE, bold=True, center=True)
            fit_text(surf, PARTS[pid], (rect.x + 34, rect.centery - font(16).get_height() // 2), rect.w - 56, 16, WHITE)
            if self.phase == "diagnose" and pid in self.inspected:
                draw_text(surf, "✔", (rect.right - 10, rect.centery - 9), 15, GOOD, right=True)
            elif self.phase == "repair" and self._part_note(pid):
                _draw_book_icon(surf, (rect.right - 16, rect.centery), 9, CYAN if hov else GHOST)

    def _part_note(self, pid):
        """Сноска из мануала к детали текущего задания: (мануал, страница|None, текст) или None."""
        return MANUAL_NOTES.get(self.cur["id"], {}).get(pid) if self.cur else None

    def _note_part_at(self, mouse):
        """Деталь со сноской в фокусе клавиатуры/кнопки или под мышью (строка списка, кружок на коляске)."""
        if self.phase != "repair" or not self.cur or self.cur.get("track") == "tech" or self.mini_pending:
            return None
        key = self.kb.get("key") if self.kb.get("active") else None
        if isinstance(key, tuple) and key[0] == "part":
            return key[1] if self._part_note(key[1]) else None
        for pid, r in self._part_rects():
            if r.collidepoint(mouse):
                return pid if self._part_note(pid) else None
        for pid, x, y, r in self._chair_hotspots():
            if (mouse[0] - x) ** 2 + (mouse[1] - y) ** 2 <= (r + 6) ** 2:
                return pid if self._part_note(pid) else None
        return None

    @staticmethod
    def _note_head(note):
        manual, page, _ = note
        return "Из мануала: {0}, с. {1}".format(tr(manual), page) if page else "Из мануала: {0}".format(tr(manual))

    def _draw_manual_note(self, surf, info, pid):
        """Карточка внизу справа: сноска из мануала к наведённой детали."""
        note = self._part_note(pid)
        _draw_book_icon(surf, (info.x + 26, info.y + 22), 13, CYAN)
        head, text = self._note_head(note), note[2]
        w = info.w - 62
        for hs, ts in ((15, 15), (14, 14), (13, 13), (12, 12), (12, 11)):
            hh = len(wrap_lines(head, w, hs)) * (font(hs).get_height() + 2)
            th = len(wrap_lines(text, w, ts)) * (font(ts).get_height() + 2)
            if 8 + hh + 4 + th <= info.h - 6:
                break
        y = draw_wrapped(surf, head, (info.x + 46, info.y + 8), w, hs, CYAN)
        draw_wrapped(surf, text, (info.x + 46, y + 4), w, ts, WHITE,
                     max_lines=max(1, (info.bottom - 6 - y - 4) // (font(ts).get_height() + 2)))

    def _manual_note_say(self):
        """Озвучка: фокус задержался на детали со сноской — прочитать сноску один раз."""
        if not (self.scene == "job" and self.kb.get("active") and A11Y["on"]):
            return
        pid = self._note_part_at((-1, -1))
        if pid != getattr(self, "_note_key", None):
            self._note_key, self._note_t, self._note_said = pid, self.t, False
        elif pid and not self._note_said and self.t - self._note_t > 1.2:
            self._note_said = True
            note = self._part_note(pid)
            self.say(tr(self._note_head(note)) + ". " + tr(note[2]), False)

    def _draw_tools(self, surf, mouse):
        """Минималистичная панель: иконки без текста, описание — в карточке справа."""
        tech = self.cur and self.cur.get("track") == "tech"
        if self.mistakes != getattr(self, "_miss_seen", self.mistakes):
            self._miss_t = self.t                    # ошибка — выбранный инструмент вздрогнет
        self._miss_seen = self.mistakes
        hover_tid = None
        for i, (tid, rect) in enumerate(self._tool_rects()):
            active = self.sel_tool == tid
            hov = rect.collidepoint(mouse)
            if hov:
                hover_tid = tid
            h = _hover_amt(("tool", tid, bool(tech)), 1.0 if (hov or active) else 0.0)
            enter = ease_back((self.st - 0.25 - 0.025 * i) / 0.35)
            if enter <= 0.01:
                continue
            r = rect.move(0, -int(6 * h))
            if active:
                add_glow(surf, r.center, 44, (110, 80, 20), 0.55 + 0.25 * wsin(self.t * 4))
            tile = Surf(r.size, pygame.SRCALPHA)
            aa_rect(tile, (52, 48, 64, 235), tile.get_rect(), border_radius=12)
            border = AMBER if active else tuple(int(d + (a_ - d) * h) for d, a_ in zip(DIM, GHOST))
            aa_rect(tile, border, tile.get_rect(), 3 if active else 2, border_radius=12)
            if enter < 1:
                tile = TF.rotozoom(tile, 0, enter)
            surf.blit(tile, tile.get_rect(center=r.center))
            ang = 0.0
            if active:
                ang = 7 * wsin(self.t * 5)
                since = self.t - getattr(self, "_miss_t", -9)
                if since < 0.45:
                    ang += 22 * math.sin(since * 55) * (1 - since / 0.45)
            ic = tool_icon(tid, 38)
            ic = TF.rotozoom(ic, ang, enter * (1 + 0.16 * h))
            surf.blit(ic, ic.get_rect(center=r.center))
        # карточка: что за инструмент (наведённый важнее выбранного)
        info = self._tool_info_rect()
        card = Surf(info.size, pygame.SRCALPHA)
        aa_rect(card, (22, 20, 30, 215), card.get_rect(), border_radius=12)
        surf.blit(card, info)
        tid = hover_tid or self.sel_tool
        note_pid = None if (hover_tid or tech) else self._note_part_at(mouse)
        if note_pid:
            self._draw_manual_note(surf, info, note_pid)
        elif tid:
            in_hand = tid == self.sel_tool
            low = info.h < 80                         # в Гильдии карточка в один ряд
            isz = 38 if low else 44
            surf.blit(tool_icon(tid, isz), (info.x + 10, info.y + (info.h - isz) // 2))
            draw_text(surf, ("В РУКЕ: " if in_hand else "") + TOOLS[tid][0],
                      (info.x + isz + 22, info.y + (5 if low else 10)), 16 if low else 18,
                      AMBER if in_hand else WHITE, bold=True)
            draw_wrapped(surf, TOOLS[tid][1], (info.x + isz + 22, info.y + (27 if low else 36)),
                         info.w - isz - 34, 13 if low else 15, GREY)
        else:
            hint = ("Выбери инструмент, потом кликни шаг" if tech else
                    "Выбери инструмент, потом кликни деталь на коляске или в списке")
            y = draw_wrapped(surf, hint, (info.x + 16, info.y + 12), info.w - 32, 15, GREY)
            if not tech and MANUAL_NOTES.get(self.cur["id"]):     # где сноски: значок книжки у детали
                _draw_book_icon(surf, (info.x + 26, y + 16), 10, CYAN)
                draw_wrapped(surf, "У деталей с книжкой есть сноска из мануала — наведи на деталь.",
                             (info.x + 44, y + 7), info.w - 60, 14, CYAN)

    def _draw_tool_in_hand(self, surf, mouse):
        """Выбранный инструмент следует за курсором; верный шаг — вспышка у курсора."""
        tech = self.cur.get("track") == "tech"
        progress = len(self.done_steps) if tech else self.step_idx
        if progress > getattr(self, "_step_seen", progress):
            self._ok_t, self._ok_pos = self.t, mouse
        self._step_seen = progress
        if self.t - getattr(self, "_ok_t", -9) < 0.7:
            draw_burst(surf, self._ok_pos, (self.t - self._ok_t) / 0.7, GOOD, n=12, dist=60)
        if (not self.sel_tool or self.phase != "repair" or self.mini_pending or self.v3d is not None
                or getattr(self, "spec_pending", None) or getattr(self, "show_manual", False)
                or any(r.collidepoint(mouse) for _, r in self._tool_rects())):
            return
        ic = TF.rotozoom(tool_icon(self.sel_tool, 34), -12 + 4 * wsin(self.t * 4), 1.0)
        surf.blit(ic, ic.get_rect(center=(mouse[0] + 22, mouse[1] + 20)))

    def _speaker_img(self, line):
        """Портрет говорящего по началу реплики: Бренна, Барти, Мартин или клиент."""
        if line.startswith("Бренна"):
            return "master.png"
        if line.startswith("Мартин"):
            return "martin.png"
        name = line.split(":", 1)[0].strip()
        if self.cur and name and ":" in line[:40] and name.split()[-1] in self.cur.get("client", ""):
            return self.cur["client_art"]
        return "ghost.png"

    def _draw_ghost_bubble(self, surf, y=300, col=None):
        line = self.ghost_text()
        if not line or (not barty_on() and self._speaker_img(line) == "ghost.png"):
            return
        if line != getattr(self, "_ghost_seen", None):
            self._ghost_seen = line
            snd("ghost")
        img = self._speaker_img(line)
        if col is not None:                       # узкий пузырь в правой колонке (ремонт)
            bubble = col
            s = Surf(bubble.size, pygame.SRCALPHA)
            s.fill((24, 30, 36, 220))
            surf.blit(s, bubble)
            aa_rect(surf, CYAN, bubble, 2, border_radius=8)
            blit_idle(surf, load_image(img, (46, 56), CYAN), (bubble.x + 6, bubble.y + 6), self.t, "float", phase=1.3)
            tw = bubble.w - 70
            for size in (15, 14, 13, 12):
                if len(wrap_lines(tr(line), tw, size)) * (font(size).get_height() + 2) <= bubble.h - 16:
                    break
            draw_wrapped(surf, line, (bubble.x + 60, bubble.y + 8), tw, size, GHOST,
                         limit=self.typed("ghost", line, cps=90))
            return
        blit_idle(surf, load_image(img, (90, 110), CYAN), (24, y), self.t, "float", phase=1.3)
        bubble = pygame.Rect(120, y, 740, 86)
        s = Surf(bubble.size, pygame.SRCALPHA)
        s.fill((24, 30, 36, 220))
        surf.blit(s, bubble)
        aa_rect(surf, CYAN, bubble, 2, border_radius=8)
        for size in (16, 15, 14, 13):                 # крупный текст: длинная реплика — мельче, но в рамке
            lh = font(size).get_height() + 2
            if len(wrap_lines(line, bubble.w - 28, size)) * lh <= bubble.h - 20:
                break
        draw_wrapped(surf, line, (bubble.x + 14, bubble.y + 10), bubble.w - 28, size, GHOST,
                     limit=self.typed("ghost", line, cps=90), max_lines=max(1, (bubble.h - 20) // lh))

    # ----- tech-задание (Гильдия): свободный порядок операций -----
    def _op_rects(self):
        out = []
        x0, y0, w, gx, gy = 200, 150, 520, 16, 10
        per_col = max(5, (len(self.step_order) + 1) // 2)        # больше 10 шагов — карточки ниже, по 6–8 в колонке
        if per_col > 5:                                           # длинное задание: место вниз до y≈512
            gy = 6                                                # (строка «Выполнено» — под карточками, пузырь — 540)
            h = min(52, (362 - (per_col - 1) * gy) // per_col)
        else:
            h = min(52, (306 - (per_col - 1) * gy) // per_col)
        for i, sid in enumerate(self.step_order):
            col = i // per_col
            row = i % per_col
            out.append((sid, pygame.Rect(x0 + col * (w + gx), y0 + row * (h + gy), w, h)))
        return out

    def _manual_btn_rect(self):
        return pygame.Rect(WIDTH - 204, 62, 180, 40)

    def draw_job_tech(self, surf):
        self._bg(surf, "bg_guild.png", CYAN)
        job = self.cur
        self._topbar(surf, ("ЭКЗАМЕН: " if self.exam_mode else "Гильдия: ") + job["title"], job.get("chair_name"))
        mouse = mouse_pos()
        blit_idle(surf, load_image(job["client_art"], (150, 190), GHOST), (24, 70), self.t)
        draw_wrapped(surf, job["client"], (24, 266), 168, 15, WHITE, max_lines=2)   # не заходит под карточки шагов

        if self.phase == "repair":
            head = ("ЭКЗАМЕН ГИЛЬДИИ — подсказок нет, мануал разрешён" if self.exam_mode
                    else "ЗАДАНИЕ ТЕХНИКА — порядок шагов выбираешь сам")
            draw_text(surf, head, (200, 62), 17, CYAN, bold=True)
            draw_wrapped(surf, job["symptom"], (200, 88), 850, 14, WHITE)
            Button(self._manual_btn_rect(), "МАНУАЛ", PURPLE).draw(surf, mouse)
            if not self.exam_mode:
                Button(self._tech_skip_rect(), "ПРОПУСТИТЬ ▸", AMBER).draw(surf, mouse)
            for sid, rect in self._op_rects():
                st = self.step_by_id(sid)
                done = sid in self.done_steps
                aa_rect(surf, (24, 34, 28) if done else PANEL, rect, border_radius=6)
                DR.rect(surf, GOOD if done else (AMBER if rect.collidepoint(mouse) else DIM),
                                 rect, 2, border_radius=6)
                prefix = "✔ " if done else "• "
                txt = prefix + st["instr"]
                pad = 4 if rect.h >= 44 else 2
                for fs in (13, 12, 11, 10):                    # длинная операция — мельче, но целиком в карточке
                    if len(wrap_lines(tr(txt), rect.w - 20, fs)) * (font(fs).get_height() + 2) <= rect.h - 2 * pad:
                        break
                draw_wrapped(surf, txt, (rect.x + 10, rect.y + pad), rect.w - 20, fs, GREY if done else WHITE)
            lim = f" (лимит {EXAM_MAX_MISTAKES})" if self.exam_mode else ""
            rects = self._op_rects()
            y_stat = max(466, max(r.bottom for _, r in rects) + 6) if rects else 466
            draw_text(surf, f"Выполнено: {len(self.done_steps)}/{len(job['steps'])}   "
                            f"Ошибки: {self.mistakes}{lim}", (200, y_stat), 14, GHOST)
            self._draw_ghost_bubble(surf, 540)
            self._draw_tools(surf, mouse)
        elif self.phase == "test":
            draw_text(surf, "ПРОВЕРКА ПОД НАГРУЗКОЙ", (360, 70), 20, GOOD, bold=True)
            draw_wrapped(surf, job["test"], (360, 100), 560, 19, WHITE)
            if self.ride_t0 is None:                     # реплика — над кнопкой, кнопку не закрывает
                self._draw_ghost_bubble(surf, 440)
                self._draw_ride_done(surf)
                Button(self._test_btn_rect(), "ГОТОВО ▸" if self.ride_done else "ПРОВЕРИТЬ РАБОТУ",
                       GOOD).draw(surf, mouse)
            else:
                self._draw_ride(surf)

        if self.v3d is None:                         # анимация инструмента — под окнами (мануал, спека, мини)
            self._draw_action(surf)
        if self.mini_pending:
            self._draw_mini_overlay(surf, mouse)
        if self.spec_pending:
            self._draw_spec_overlay(surf, mouse)
        if self.show_manual:
            self._draw_manual_overlay(surf, mouse)
        if self.v3d is not None:
            self._draw_v3d(surf, mouse)
        self._draw_tool_in_hand(surf, mouse)

    # --- оверлей спеки (значение из мануала) ---
    def _spec_panel_rect(self):
        return pygame.Rect(WIDTH // 2 - 370, 140, 740, 460)

    def _spec_prompt_bottom(self):
        p = self._spec_panel_rect()
        lines = wrap_lines(self.spec_pending["spec"]["prompt"], p.w - 48, 20)
        return p.y + 40 + len(lines) * (font(20).get_height() + 2)

    def _spec_option_rects(self):
        p = self._spec_panel_rect()
        n = len(self.spec_pending["spec"]["options"])
        top = max(p.y + 110, self._spec_prompt_bottom() + font(15).get_height() + 16)   # крупный текст: вопрос в 2 строки
        return [(i, pygame.Rect(p.x + 24, top + i * 86, p.w - 48, 74)) for i in range(n)]

    def _spec_manual_rect(self):
        p = self._spec_panel_rect()
        return pygame.Rect(p.x + 24, p.bottom - 60, 220, 46)

    def _spec_cancel_rect(self):
        p = self._spec_panel_rect()
        return pygame.Rect(p.right - 190, p.bottom - 60, 166, 46)

    def _draw_spec_overlay(self, surf, mouse):
        _cap_modal()
        dim = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((8, 8, 12, 180))
        surf.blit(dim, (0, 0))
        p = self._spec_panel_rect()
        s = Surf(p.size, pygame.SRCALPHA)
        s.fill((22, 26, 34, 250))
        surf.blit(s, p)
        aa_rect(surf, CYAN, p, 2, border_radius=10)
        spec = self.spec_pending["spec"]
        draw_text(surf, "СПЕЦИФИКАЦИЯ", (p.x + 24, p.y + 16), 14, CYAN, bold=True)
        draw_wrapped(surf, spec["prompt"], (p.x + 24, p.y + 40), p.w - 48, 20, WHITE)
        viewed = spec["manual"] in self.manual_viewed
        if not viewed:
            draw_text(surf, "Сначала сверься с мануалом — варианты откроются.",
                      (p.centerx, max(p.y + 82, self._spec_prompt_bottom() + 4 + font(15).get_height() // 2)),
                      15, AMBER, center=True)
        for i, rect in self._spec_option_rects():
            aa_rect(surf, PANEL, rect, border_radius=8)
            aa_rect(surf, CYAN if viewed else DIM, rect, 2, border_radius=8)
            draw_wrapped(surf, spec["options"][i][0], (rect.x + 14, rect.y + 12),
                         rect.w - 28, 16, WHITE if viewed else GREY)
        Button(self._spec_manual_rect(), "ОТКРЫТЬ МАНУАЛ", PURPLE).draw(surf, mouse)
        Button(self._spec_cancel_rect(), "ПОЗЖЕ", GREY).draw(surf, mouse)

    # --- оверлей мануала Гильдии ---
    def _manual_panel_rect(self):
        return pygame.Rect(40, 62, WIDTH - 80, 646)

    def _manual_page_rects(self):
        pages = (self.cur.get("manual") if (self.cur and self.cur.get("track") == "tech")
                 else None) or list(MANUAL)
        p = self._manual_panel_rect()
        return [(key, pygame.Rect(p.x + 20, p.y + 70 + i * 54, 270, 46))
                for i, key in enumerate(pages)]

    def _manual_text_size(self, page, width, height):
        """Наибольший шрифт (17→11), при котором вся страница мануала помещается в height."""
        key = (page, width, height, LANG["code"])
        cache = self.__dict__.setdefault("_manual_fit", {})
        if key not in cache:
            lines = MANUAL[page][1]
            best = (11, 4)
            for size in range(17, 10, -1):
                gap = 8 if size >= 15 else 5
                lh = font(size).get_height() + 2
                h = sum(len(wrap_lines("• " + ln, width, size)) * lh + gap for ln in lines)
                if h <= height:
                    best = (size, gap)
                    break
            cache[key] = best
        return cache[key]

    def _manual_close_rect(self):
        p = self._manual_panel_rect()
        return pygame.Rect(p.right - 200, p.bottom - 64, 180, 46)

    def _draw_manual_overlay(self, surf, mouse):
        _cap_modal()
        dim = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((8, 8, 12, 180))
        surf.blit(dim, (0, 0))
        p = self._manual_panel_rect()
        s = Surf(p.size, pygame.SRCALPHA)
        s.fill((26, 24, 34, 250))
        surf.blit(s, p)
        aa_rect(surf, PURPLE, p, 2, border_radius=10)
        draw_text(surf, "МАНУАЛ ГИЛЬДИИ КОЛЁСНИКОВ", (p.x + 24, p.y + 20), 22, PURPLE, bold=True)
        for key, rect in self._manual_page_rects():
            active = key == self.manual_page
            aa_rect(surf, PANEL2 if active else PANEL, rect, border_radius=6)
            aa_rect(surf, PURPLE if active else DIM, rect, 2, border_radius=6)
            name = MANUAL[key][0]
            if font(14).size(tr(name))[0] <= rect.w - 20:
                draw_text(surf, name, (rect.x + 10, rect.y + 13), 14, WHITE if active else GREY)
            else:                                        # длинное название — в две строки, а не мелким шрифтом
                draw_wrapped(surf, name, (rect.x + 10, rect.y + 5), rect.w - 20, 13, WHITE if active else GREY,
                             max_lines=2)
        if self.manual_page:
            title, lines = MANUAL[self.manual_page]
            x0 = p.x + 320
            tw = p.right - 24 - x0
            fit_text(surf, title, (x0, p.y + 70), tw, 20, AMBER, bold=True)
            y0, bottom = p.y + 110, self._manual_close_rect().y - 10
            size, gap = self._manual_text_size(self.manual_page, tw, bottom - y0)
            y = y0
            for ln in lines:                             # весь текст страницы — в панели (шрифт подбирается)
                y = draw_wrapped(surf, "• " + ln, (x0, y), tw, size, WHITE) + gap
        Button(self._manual_close_rect(), "ЗАКРЫТЬ [Esc]", AMBER).draw(surf, mouse)

    # ----- мини-интеракции: геометрия, клики, отрисовка -----
    def _mini_panel_rect(self):
        return pygame.Rect(WIDTH // 2 - 360, 150, 720, 440)

    def _mini_cancel_rect(self):
        p = self._mini_panel_rect()
        return pygame.Rect(p.right - 160, p.bottom - 56, 140, 42)

    def _mini_pump_rects(self):
        p = self._mini_panel_rect()
        return (pygame.Rect(p.x + 40, p.bottom - 130, 200, 56),
                pygame.Rect(p.right - 280, p.bottom - 130, 240, 56))

    def _mini_release_rect(self):
        p = self._mini_panel_rect()
        return pygame.Rect(p.x + 256, p.bottom - 130, 168, 56)

    def _mini_gap_track(self):
        p = self._mini_panel_rect()
        return pygame.Rect(p.x + 60, p.y + 170, 600, 30)

    def _mini_gap_check_rect(self):
        p = self._mini_panel_rect()
        return pygame.Rect(p.centerx - 130, p.bottom - 130, 260, 56)

    def _mini_ping_spots(self):
        p = self._mini_panel_rect()
        cx, cy = p.centerx, p.y + 230
        total = self.mini_pending["cfg"]["total"]
        out = []
        for i in range(total):
            ang = math.radians(i * (360 / total) - 90)
            x = cx + 95 * math.cos(ang)
            y = cy + 95 * math.sin(ang)
            out.append((i, pygame.Rect(int(x) - 17, int(y) - 17, 34, 34)))
        return out

    def _mini_meter_rects(self):
        p = self._mini_panel_rect()
        n = len(self.mini_pending["cfg"]["options"])
        return [(i, pygame.Rect(p.x + 40, p.y + 202 + i * 70, p.w - 240, 62)) for i in range(n)]

    def _click_mini(self, m):
        if self._mini_cancel_rect().collidepoint(m):
            self.mini_pending = None
            return
        k = self.mini_pending["kind"]
        if k == "pump":
            b_pump, b_done = self._mini_pump_rects()
            if b_pump.collidepoint(m):
                self.mini_pump()
            elif self._mini_release_rect().collidepoint(m):
                self.mini_release()
            elif b_done.collidepoint(m):
                self.mini_pump_done()
        elif k == "gap":
            tr = self._mini_gap_track()
            if tr.collidepoint(m):
                cfg = self.mini_pending["cfg"]
                frac = (m[0] - tr.x) / tr.w
                self.mini_pending["value"] = round(cfg["mn"] + (cfg["mx"] - cfg["mn"]) * frac)
            elif self._mini_gap_check_rect().collidepoint(m):
                self.mini_gap_check()
        elif k == "ping":
            for i, rect in self._mini_ping_spots():
                if rect.collidepoint(m):
                    self.mini_ping(i)
                    return
        elif k == "meter":
            for i, rect in self._mini_meter_rects():
                if rect.collidepoint(m):
                    self.mini_meter(i)
                    return

    def _draw_mini_overlay(self, surf, mouse):
        _cap_modal()
        dim = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((8, 8, 12, 180))
        surf.blit(dim, (0, 0))
        p = self._mini_panel_rect()
        s = Surf(p.size, pygame.SRCALPHA)
        s.fill((22, 28, 30, 250))
        surf.blit(s, p)
        aa_rect(surf, AMBER, p, 2, border_radius=10)
        m = self.mini_pending
        cfg = m["cfg"]
        tip = cfg.get("hint") or cfg.get("prompt")
        # шапка (инструкция + подсказка) — выше табло/шкалы (y ≈ p.y + 90): крупный шрифт — мельче, но целиком
        for isz, tsz in ((19, 14), (18, 13), (17, 13), (16, 12), (15, 12), (14, 11)):
            ih = len(wrap_lines(m["step"]["instr"], p.w - 48, isz)) * (font(isz).get_height() + 2)
            th = len(wrap_lines(tip, p.w - 48, tsz)) * (font(tsz).get_height() + 2) if tip else 0
            if 16 + ih + 2 + th <= 90:
                break
        y_end = draw_wrapped(surf, m["step"]["instr"], (p.x + 24, p.y + 16), p.w - 48, isz, WHITE, max_lines=3)
        if tip:                                        # подсказка — под инструкцией, сколько бы строк та ни заняла
            draw_wrapped(surf, tip, (p.x + 24, y_end + 2), p.w - 48, tsz, AMBER, max_lines=2)
        k = m["kind"]
        if k == "pump":
            self._draw_mini_pump(surf, mouse, p, m, cfg)
        elif k == "gap":
            self._draw_mini_gap(surf, mouse, p, m, cfg)
        elif k == "ping":
            self._draw_mini_ping(surf, mouse, p, m, cfg)
        elif k == "meter":
            self._draw_mini_meter(surf, mouse, p, m, cfg)
        Button(self._mini_cancel_rect(), "ПОЗЖЕ", GREY).draw(surf, mouse)

    def _draw_mini_pump(self, surf, mouse, p, m, cfg):
        bar = pygame.Rect(p.x + 60, p.y + 150, 600, 36)
        aa_rect(surf, PANEL, bar, border_radius=6)
        zx = bar.x + bar.w * cfg["lo"] / cfg["mx"]
        zw = bar.w * (cfg["hi"] - cfg["lo"]) / cfg["mx"]
        aa_rect(surf, (40, 70, 48), (zx, bar.y, zw, bar.h), border_radius=6)
        vw = bar.w * min(m["value"], cfg["mx"]) / cfg["mx"]
        if vw > 0:
            aa_rect(surf, AMBER, (bar.x, bar.y + 10, vw, bar.h - 20), border_radius=6)
        aa_rect(surf, GOOD, (zx, bar.y, zw, bar.h), 2, border_radius=6)
        aa_rect(surf, DIM, bar, 2, border_radius=6)
        draw_text(surf, f"{m['value']} {cfg['unit']}", (bar.centerx, bar.bottom + 18), 30,
                  WHITE, bold=True, center=True)
        b_pump, b_done = self._mini_pump_rects()
        Button(b_pump, "КАЧАТЬ", AMBER).draw(surf, mouse)
        Button(self._mini_release_rect(), "СТРАВИТЬ", CYAN).draw(surf, mouse, enabled=m["value"] > 0)
        Button(b_done, "ГОТОВО, ПРОВЕРЯЮ", GOOD).draw(surf, mouse)

    def _draw_mini_gap(self, surf, mouse, p, m, cfg):
        trk = self._mini_gap_track()
        aa_rect(surf, PANEL, trk, border_radius=6)
        span = cfg["mx"] - cfg["mn"]
        zx = trk.x + trk.w * (cfg["lo"] - cfg["mn"]) / span
        zw = max(8, trk.w * (cfg["hi"] - cfg["lo"]) / span)
        aa_rect(surf, (40, 70, 48), (zx, trk.y, zw, trk.h), border_radius=6)
        aa_rect(surf, GOOD, (zx, trk.y, zw, trk.h), 2, border_radius=6)
        aa_rect(surf, DIM, trk, 2, border_radius=6)
        vx = trk.x + trk.w * (m["value"] - cfg["mn"]) / span
        aa_rect(surf, CYAN, (vx - 3, trk.y - 8, 6, trk.h + 16), border_radius=3)
        draw_text(surf, str(cfg["mn"]), (trk.x, trk.bottom + 8), 13, GREY)
        draw_text(surf, str(cfg["mx"]), (trk.right, trk.bottom + 8), 13, GREY, right=True)
        label = cfg.get("label", "Значение")
        text = f"{tr(label)}: {m['value']} {tr(cfg['unit'])}"
        sz = 26                                       # крупно, но в ширину панели и ниже цифр шкалы
        while sz > 16 and font(sz, True).size(text)[0] > p.w - 48:
            sz -= 1
        draw_text(surf, text, (trk.centerx, trk.bottom + 46), sz, WHITE, bold=True, center=True)
        draw_text(surf, "Кликни по шкале, чтобы выставить значение.",
                  (trk.centerx, trk.bottom + 82), 14, GREY, center=True)
        Button(self._mini_gap_check_rect(), "ПРОВЕРИТЬ", GOOD).draw(surf, mouse)

    def _draw_mini_ping(self, surf, mouse, p, m, cfg):
        cx, cy = p.centerx, p.y + 230
        found = len(m["dull"] & m["tested"])
        draw_text(surf, f"Кликай спицы, ищи глухие. Найдено: {found}/{len(m['dull'])}",
                  (p.x + 24, p.bottom - 46), 15, CYAN)            # внизу — не на колесе
        aa_circle(surf, DIM, (cx, cy), 150, 3)
        for i, rect in self._mini_ping_spots():
            ang = math.radians(i * (360 / cfg["total"]) - 90)
            ex = cx + 148 * math.cos(ang)
            ey = cy + 148 * math.sin(ang)
            tested = i in m["tested"]
            dull = i in m["dull"]
            col = (BAD if dull else DIM) if tested else GHOST
            DR.line(surf, col, (cx, cy), (ex, ey), 3 if (tested and dull) else 2)
            c = rect.center
            if tested:
                aa_circle(surf, BAD if dull else PANEL2, c, 15)
                aa_circle(surf, BAD if dull else DIM, c, 15, 2)
            else:
                aa_circle(surf, PANEL2, c, 15)
                aa_circle(surf, AMBER if rect.collidepoint(mouse) else GREY, c, 15, 2)
        aa_circle(surf, AMBER, (cx, cy), 18)

    def _draw_mini_meter(self, surf, mouse, p, m, cfg):
        disp = pygame.Rect(p.centerx - 160, p.y + 92, 320, 64)
        aa_rect(surf, (16, 24, 18), disp, border_radius=8)
        aa_rect(surf, GOOD, disp, 2, border_radius=8)
        rsz = 34                                      # показание прибора — целиком в табло
        while rsz > 16 and font(rsz, True).size(tr(cfg["reading"]))[0] > disp.w - 24:
            rsz -= 1
        draw_text(surf, cfg["reading"], disp.center, rsz, GOOD, bold=True, center=True)
        if cfg.get("sub"):                            # пояснение — переносом, в пределах панели
            draw_wrapped(surf, cfg["sub"], (p.centerx, disp.bottom + 6), p.w - 60, 13, GREY, center=True, max_lines=2)
        for i, rect in self._mini_meter_rects():
            aa_rect(surf, PANEL, rect, border_radius=8)
            aa_rect(surf, CYAN if rect.collidepoint(mouse) else DIM, rect, 2, border_radius=8)
            draw_wrapped(surf, cfg["options"][i][0], (rect.x + 14, rect.y + 10),
                         rect.w - 28, 15, WHITE)

    # ----- провал tech-задания: разбор ошибки -----
    def _fail_retry_rect(self):
        return pygame.Rect(WIDTH // 2 - 330, 560, 300, 56)

    def _fail_back_rect(self):
        return pygame.Rect(WIDTH // 2 + 30, 560, 300, 56)

    def draw_failed(self, surf):
        self._bg(surf, "bg_guild.png", BAD)
        if getattr(self, "_fail_zap", False) and self.st < 0.9 and not calm():          # разряд: вспышка и молнии через экран
            k = self.st / 0.9
            if k < 0.15:
                fl = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
                fl.fill((200, 225, 255, int((90 if DISPLAY.get("glow", True) else 40) * (1 - k / 0.15))))
                surf.blit(fl, (0, 0))
            draw_zap(surf, (WIDTH // 2 - 160, 300), k, size=2.2)
            draw_zap(surf, (WIDTH // 2 + 200, 330), min(1.0, k * 1.2), size=1.8)
        title = "ЭКЗАМЕН НЕ СДАН" if self.exam_mode else "ПРОВАЛ. РАЗБОР ОШИБКИ"
        shake = int(14 * math.sin(self.st * 42) * max(0.0, 1 - self.st / 0.6))
        draw_text(surf, title, (WIDTH // 2 + shake, 120), 46, BAD, bold=True, center=True)
        card = pygame.Rect(WIDTH // 2 - 420, 190 + int(40 * (1 - appear(self.st, 0.2))), 840, 220)
        s = Surf(card.size, pygame.SRCALPHA)
        s.fill((40, 22, 26, 240))
        surf.blit(s, card)
        aa_rect(surf, BAD, card, 2, border_radius=10)
        draw_wrapped(surf, self.fail_msg, (card.x + 26, card.y + 24), card.w - 52, 19, WHITE)
        brenna = ("Бренна: «Пересдача — не позор. Позор — выдать человеку непроверенную коляску.»"
                  if self.exam_mode else
                  "Бренна: «В мастерской ошибка стоит железа. На дороге — жизни. Заново, ученик.»")
        draw_wrapped(surf, brenna, (card.x + 26, 432), card.w - 52, 18, GHOST)
        draw_text(surf, "Барти: «Не красней, Мартин. Меня она гоняла так же. Посмертно.»",
                  (WIDTH // 2, 508), 16, PURPLE, center=True, plate=True)
        mouse = mouse_pos()
        Button(self._fail_retry_rect(), "ПЕРЕСДАТЬ" if self.exam_mode else "ЗАНОВО",
               AMBER).draw(surf, mouse)
        Button(self._fail_back_rect(), "В ГИЛЬДИЮ", CYAN).draw(surf, mouse)

    # ----- экзамен сдан: чек-лист и диплом -----
    def draw_exam_result(self, surf):
        self._bg(surf, "bg_guild.png", GOOD)
        draw_confetti(surf, self.t, n=50)
        title = "ЭКЗАМЕН СДАН — С ОТЛИЧИЕМ" if self.mistakes == 0 else "ЭКЗАМЕН СДАН"
        draw_text(surf, title, (WIDTH // 2, 84), 46, GOOD, bold=True, center=True)
        card = pygame.Rect(WIDTH // 2 - 380, 150, 760, 196)
        s = Surf(card.size, pygame.SRCALPHA)
        s.fill((24, 34, 28, 240))
        surf.blit(s, card)
        aa_rect(surf, GOOD, card, 2, border_radius=10)
        draw_text(surf, "ЧЕК-ЛИСТ ГИЛЬДИИ", (card.x + 24, card.y + 14), 16, GHOST, bold=True)
        items = [
            "Техника безопасности — без нарушений",
            "Порядок операций — соблюдён",
            "Спецификации — по мануалу",
            f"Ошибки — {self.mistakes} из {EXAM_MAX_MISTAKES} допустимых",
        ]
        y = card.y + 46
        for i, it in enumerate(items):
            a = appear(self.st, 0.4 + 0.35 * i, 0.3)
            draw_text(surf, "✔ " + it, (card.x + 34 + int(30 * (1 - a)), y), 17, WHITE, alpha=255 * a)
            y += 34
        dip = pygame.Rect(WIDTH // 2 - 380, 366, 760, 122)
        s = Surf(dip.size, pygame.SRCALPHA)
        s.fill((40, 34, 20, 240))
        surf.blit(s, dip)
        aa_rect(surf, AMBER, dip, 3, border_radius=10)
        add_glow(surf, dip.center, 260, (60, 45, 10), 0.4 + 0.3 * wsin(self.t * 2))
        draw_text(surf, "— ДИПЛОМ ГИЛЬДИИ КОЛЁСНИКОВ —", (dip.centerx, dip.y + 16), 20,
                  AMBER, bold=True, center=True)
        draw_text(surf, "Мартин, зомби — сертифицированный техник по ремонту кресел-колясок",
                  (dip.centerx, dip.y + 52), 17, WHITE, center=True)
        draw_text(surf, "принято под надзором Мастерицы Бренны (посмертно)",
                  (dip.centerx, dip.y + 84), 13, GREY, center=True)
        yb = draw_wrapped(surf, "Бренна: «Сдано. И вот ещё что, Бартоломью... я помню тебя. "
                                "Ты задавал хорошие вопросы.»", (WIDTH // 2, 500), 760, 17, GHOST, center=True,
                                plate=True)
        draw_text(surf, "Барти: «...Мартин. МАРТИН. Она меня ПОМНИТ!»",
                  (WIDTH // 2, max(556, yb + 14)), 16, PURPLE, center=True, plate=True)
        Button(self._result_btn_rect(), "В ГИЛЬДИЮ", AMBER).draw(surf, mouse_pos())

    # ----- Гильдия Колёсников (хаб про-трека) -----
    def _guild_job_rects(self):
        step = min(116, (HEIGHT - 100 - 160) // max(1, len(TECH_JOBS)))   # все карточки — над кнопкой «Назад»
        return [(job["id"], pygame.Rect(60, 160 + i * step, 560, step - 10))
                for i, job in enumerate(TECH_JOBS)]

    def _guild_back_rect(self):
        return pygame.Rect(40, HEIGHT - 70, 160, 48)

    def _guild_exam_rect(self):
        return pygame.Rect(WIDTH - 360, HEIGHT - 160, 300, 54)

    def draw_guild(self, surf):
        self._bg(surf, "bg_guild.png", PURPLE)
        self._topbar(surf, "Гильдия Колёсников")
        mouse = mouse_pos()
        n = self.tech_done_count()
        if self.exam_passed:
            rank = "Сертифицированный техник Гильдии"
        else:
            # «допуск к экзамену» — только когда сданы ВСЕ зачёты (столько же, сколько заданий Гильдии)
            rank = ("Подмастерье — допуск к экзамену" if n >= len(TECH_JOBS) else
                    ["Ученик Гильдии", "Младший подмастерье", "Подмастерье", "Старший подмастерье"][min(n, 3)])
        draw_text(surf, f"Мартин — {rank}", (60, 68), 20,
                  GOOD if self.exam_passed else CYAN, bold=True)
        dy = 68 + font(20, True).get_height() + 8        # под заголовком, сколько бы тот ни занял (крупный шрифт)
        if self.exam_passed:
            draw_text(surf, "✔ ДИПЛОМ ГИЛЬДИИ ПОЛУЧЕН", (60, dy), 15, AMBER, bold=True)
        else:
            note = ("Здесь ремонт по-взрослому: порядок шагов выбираешь сам, значения — "
                    "только из мануала, а нарушение техники безопасности проваливает задание.")
            nsz = 14
            while nsz > 11 and dy + len(wrap_lines(note, 680, nsz)) * (font(nsz).get_height() + 2) > 152:
                nsz -= 1
            draw_wrapped(surf, note, (60, dy), 680, nsz, GREY, plate=True)
        for i, (jid, rect) in enumerate(self._guild_job_rects()):
            job = self.job_by_id(jid)
            done = jid in self.done
            dx = -int(140 * (1 - appear(self.st, 0.1 * i, 0.45)))
            r = Button(rect, "", GOOD if done else CYAN).draw(surf, mouse, active=done, offset=(dx, 0))
            art = min(70, r.h - 10)
            surf.blit(load_image(job["client_art"], (art, art), GHOST), (r.x + 10, r.y + (r.h - art) // 2))
            ty = r.y + (r.h - 66) // 2                      # три строки по центру карточки
            fit_text(surf, job["title"], (r.x + 96, ty), r.w - 96 - (96 if done else 14), 18, WHITE, bold=True)
            draw_text(surf, job["client"], (r.x + 96, ty + 25), 14, GREY)
            draw_text(surf, "УРОВЕНЬ: ТЕХНИК", (r.x + 96, ty + 47), 12, PURPLE, bold=True)
            if done:
                draw_text(surf, "✔ сдано", (r.right - 14, r.y + 12), 15, GOOD, right=True)
        blit_idle(surf, load_image("master.png", (200, 280), PURPLE), (WIDTH - 300, 130), self.t,
                  "float", phase=0.7, k=ease_back((self.st - 0.3) / 0.6))
        draw_text(surf, "Мастерица Бренна", (WIDTH - 200, 420), 16, WHITE, bold=True, center=True)
        if n >= len(TECH_JOBS):
            Button(self._guild_exam_rect(), "ЭКЗАМЕН ГИЛЬДИИ", GOOD,
                   sub=("диплом есть — но можно блеснуть" if self.exam_passed
                        else "случайный билет · без подсказок")).draw(surf, mouse)
            line = ("Барти: «Она ПОМНИТ меня, Мартин! Лучший день моей смерти!»"
                    if self.exam_passed else
                    "Бренна: «Все зачёты сданы. Осталось главное — экзамен. Билет вытянешь сам.»")
        else:
            line = ("Барти: «Это ОНА, Мартин! Та самая мастерица, про которую я рассказывал! "
                    "...Она меня не помнит. Обидно.»")
        if barty_on() or not line.startswith("Барти"):       # «Призрак Барти: выкл» — его реплик нет и тут
            draw_wrapped(surf, line, (WIDTH - 470, 452), 420, 15, GHOST, max_lines=5, plate=True)   # под Бренной
        Button(self._guild_back_rect(), "НАЗАД", AMBER).draw(surf, mouse)

    # ----- результат -----
    def _result_btn_rect(self):
        return pygame.Rect(WIDTH // 2 - 150, HEIGHT - 110, 300, 56)

    def draw_result(self, surf):
        self._bg(surf, "bg_workshop.png", WOOD)
        job = self.cur
        st = self.st
        # довольный клиент слева, Барти справа
        cimg = load_image(job["client_art"], (210, 250), GHOST)
        hop = int(18 * abs(wsin(st * 6)) * max(0.0, 1 - st / 1.6))
        blit_idle(surf, cimg, (24, 300 - hop), self.t)
        if barty_on():
            blit_idle(surf, load_image("ghost.png", (150, 200), CYAN), (WIDTH - 200, 290), self.t, "float",
                      k=ease_back((st - 0.5) / 0.5))
        gk = ease_back(st / 0.5)
        if gk > 0.01:
            img = TF.rotozoom(font(44, True).render(tr("ГОТОВО!"), True, GOOD), 0, gk)
            surf.blit(img, img.get_rect(center=(WIDTH // 2, 70)))
        stars = getattr(self, "cur_stars", 3)
        for i in range(3):
            d = 0.45 + 0.28 * i
            k = ease_back((st - d) / 0.4)
            c = (WIDTH // 2 + (i - 1) * 52, 130)
            if i < stars:
                draw_burst(surf, c, (st - d) / 0.7)
                if st >= d and i not in self._stars_played:
                    self._stars_played.add(i)
                    snd(f"star{i}")
            if k > 0.01:
                img = font(40).render("★" if i < stars else "☆", True, AMBER)
                img = TF.rotozoom(img, 0, k)
                surf.blit(img, img.get_rect(center=c))
        ty = draw_wrapped(surf, job["thanks"], (WIDTH // 2, 185), 760, 20, WHITE, center=True, plate=st > 1.2,
                          limit=self.typed("thanks", job["thanks"]) if st > 1.2 else 0)
        top = max(250, ty + 12)                      # крупный текст: «спасибо» в 3 строки — карточка ниже
        # карточка «что ты узнал»
        fsz = 18                                     # длинный факт — мельче, но целиком в карточке (до y≈450)
        for fsz in (18, 17, 16, 15, 14):
            if 54 + len(wrap_lines(job["fact"], 712, fsz)) * (font(fsz).get_height() + 2) + 14 <= 200:
                break
        fh = len(wrap_lines(job["fact"], 712, fsz)) * (font(fsz).get_height() + 2)
        card = pygame.Rect(WIDTH // 2 - 380, top + int(50 * (1 - appear(st, 0.9, 0.5))), 760, max(180, 54 + fh + 14))
        s = Surf(card.size, pygame.SRCALPHA)
        s.fill((26, 32, 30, 235))
        surf.blit(s, card)
        aa_rect(surf, GHOST, card, 2, border_radius=10)
        draw_text(surf, "ЧТО ТЫ УЗНАЛ (по-настоящему):", (card.x + 24, card.y + 18), 18, GHOST, bold=True)
        draw_wrapped(surf, job["fact"], (card.x + 24, card.y + 54), card.w - 48, fsz, WHITE)
        gy = max(470, top + card.h + 14)
        draw_text(surf, self.result_gag, (WIDTH // 2, gy), 17, PURPLE, center=True, plate=True)
        if self.result_gag in LEG_GAGS and st > 1.4:
            kind = LEG_GAG_KIND[LEG_GAGS.index(self.result_gag)]
            top = gy + font(17).get_height() // 2 + 12     # сценка — ниже подписи, нога не пробегает по тексту
            draw_leg_gag(surf, kind, st - 1.4, pygame.Rect(260, top, 760, max(60, HEIGHT - 114 - top)))
        if self.cur.get("track") == "tech":
            nxt = "В ГИЛЬДИЮ"
        elif self._party_next():
            nxt = "НА ВЕЧЕРИНКУ"
        else:
            nxt = "В МАСТЕРСКУЮ"
        Button(self._result_btn_rect(), nxt, AMBER).draw(surf, mouse_pos())

    # ----- гараж -----
    def _back_rect(self):
        return pygame.Rect(40, HEIGHT - 70, 160, 48)

    GARAGE_PER = 9                  # карточек на странице гаража (3 × 3): текст «чему научился» помещается

    def _garage_pages(self):
        return max(1, -(-len(self.garage) // self.GARAGE_PER))

    def _garage_card_rects(self):
        """Карточки текущей страницы гаража: [(индекс в garage, rect)]."""
        page = min(getattr(self, "garage_page", 0), self._garage_pages() - 1)
        items = list(range(len(self.garage)))[page * self.GARAGE_PER:(page + 1) * self.GARAGE_PER]
        cols, gx, gy = 3, 20, 14
        cw = (WIDTH - 80 - (cols - 1) * gx) // cols
        ch = (HEIGHT - 76 - 10 - 72 - 2 * gy) // 3
        x0 = (WIDTH - cols * cw - (cols - 1) * gx) // 2
        return [(i, pygame.Rect(x0 + (k % cols) * (cw + gx), 72 + (k // cols) * (ch + gy), cw, ch))
                for k, i in enumerate(items)]

    def _garage_arrow_rects(self):
        if self._garage_pages() < 2:
            return []
        return [(-1, pygame.Rect(WIDTH // 2 - 120, HEIGHT - 66, 54, 40)), (1, pygame.Rect(WIDTH // 2 + 66, HEIGHT - 66, 54, 40))]

    def _garage_popup_rect(self):
        return pygame.Rect(WIDTH // 2 - 380, 110, 760, 470)

    def _garage_close_rect(self):
        p = self._garage_popup_rect()
        return pygame.Rect(p.centerx - 90, p.bottom - 64, 180, 46)

    def click_garage(self, m):
        if getattr(self, "garage_open", None) is not None:      # окно урока: любой клик закрывает
            self.garage_open = None
            snd("tick")
            return
        if self._back_rect().collidepoint(m):
            self.scene = "hub"
            return
        for d, r in self._garage_arrow_rects():
            if r.collidepoint(m):
                self.garage_page = (getattr(self, "garage_page", 0) + d) % self._garage_pages()
                snd("tick")
                return
        for i, r in self._garage_card_rects():
            if r.collidepoint(m):
                self.garage_open = i
                snd("tick")
                return

    def draw_garage(self, surf):
        self._bg(surf, "bg_garage.png", PURPLE)
        self._topbar(surf, "Гараж-коллекция")
        mouse = mouse_pos()
        if not self.garage:
            draw_text(surf, "Пока пусто. Почини хотя бы одну коляску!", (WIDTH // 2, 300), 22, GREY, center=True)
        for k, (i, rect) in enumerate(self._garage_card_rects()):
            jid, stars = self.garage[i]
            job = self.job_by_id(jid)
            rect = rect.move(0, int(40 * (1 - appear(self.st, 0.06 * k, 0.4))))
            Button(rect, "", PURPLE).draw(surf, mouse, offset=(0, 0))
            art = min(110, rect.h - 16)
            surf.blit(load_image(job["chair_art"], (art, art), AMBER), (rect.x + 8, rect.y + (rect.h - art) // 2))
            tx, tw = rect.x + art + 18, rect.w - art - 28
            y = draw_wrapped(surf, job["client"], (tx, rect.y + 10), tw, 15, WHITE, max_lines=2)
            y = draw_wrapped(surf, job["title"], (tx, y), tw, 12, GREY, max_lines=2)
            draw_text(surf, "★" * stars + "☆" * (3 - stars), (tx, y + 2), 16, AMBER)
            lh = font(11).get_height() + 2
            left = max(1, (rect.bottom - 22 - (y + 24)) // lh)
            draw_wrapped(surf, job["fact"], (tx, y + 24), tw, 11, GHOST, max_lines=left)
            draw_text(surf, "▸ " + tr("подробнее"), (rect.right - 10, rect.bottom - 18), 11, CYAN, right=True)
        pages = self._garage_pages()
        if pages > 1:
            page = min(getattr(self, "garage_page", 0), pages - 1)
            for d, r in self._garage_arrow_rects():
                Button(r, "◀" if d < 0 else "▶", AMBER).draw(surf, mouse)
            draw_text(surf, f"{page + 1} / {pages}", (WIDTH // 2, HEIGHT - 54), 16, WHITE, center=True)
        Button(self._back_rect(), "НАЗАД", AMBER).draw(surf, mouse)
        gi = getattr(self, "garage_open", None)
        if gi is not None and gi < len(self.garage):            # окно с полным уроком задания
            _cap_modal()
            dim = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((8, 8, 12, 170))
            surf.blit(dim, (0, 0))
            jid, stars = self.garage[gi]
            job = self.job_by_id(jid)
            p = self._garage_popup_rect()
            aa_rect(surf, (20, 18, 30, 248), p, border_radius=14)
            aa_rect(surf, PURPLE, p, 2, border_radius=14)
            surf.blit(load_image(job["chair_art"], (170, 170), AMBER), (p.x + 24, p.y + 24))
            surf.blit(load_image(job["client_art"], (110, 130), GHOST), (p.x + 54, p.y + 210))
            x, w = p.x + 220, p.w - 250
            y = draw_wrapped(surf, job["client"], (x, p.y + 26), w, 22, WHITE)
            y = draw_wrapped(surf, job["title"], (x, y + 2), w, 16, GREY)
            draw_text(surf, "★" * stars + "☆" * (3 - stars), (x, y + 6), 22, AMBER)
            draw_text(surf, "ЧЕМУ НАУЧИЛСЯ", (x, y + 46), 15, CYAN, bold=True)
            fy = y + 70
            fsz = 17
            while fsz > 12 and len(wrap_lines(job["fact"], w, fsz)) * (font(fsz).get_height() + 3) > p.bottom - 80 - fy:
                fsz -= 1
            draw_wrapped(surf, job["fact"], (x, fy), w, fsz, WHITE, line_gap=3)
            Button(self._garage_close_rect(), "ЗАКРЫТЬ", AMBER).draw(surf, mouse)

    # ----- финал -----
    def draw_ending(self, surf):
        self._bg(surf, "bg_party.png", GHOST)
        st = self.st
        # Мартин танцует в коляске (качается и подпрыгивает), Барти кружит рядом
        rock = 6 * wsin(self.t * 4.2)
        bounce = int(8 * abs(wsin(self.t * 4.2)))
        mx = -260 + int(320 * ease_out(st / 1.2))
        blit_idle(surf, load_image("martin.png", (240, 270), GHOST), (mx, HEIGHT - 290 - bounce), self.t,
                  rock=rock)
        if barty_on():                                # «Призрак Барти: выкл» — без призрака и его реплики
            blit_idle(surf, load_image("ghost.png", (170, 220), CYAN), (WIDTH - 230, HEIGHT - 300), self.t,
                      "float", rock=8 * wsin(self.t * 2.1), k=ease_back((st - 0.6) / 0.6))
        draw_confetti(surf, self.t)
        story = ("Мартин докатил до друзей на отремонтированной коляске. Левая нога снова "
                 "отвалилась у самого входа — но коляска едет идеально, а это главное.")
        barty = ("Бартоломью: «Ты научился чинить лучше, чем я когда-либо видел. "
                 "Горжусь, парень. Теперь — танцуй.»") if barty_on() else ""
        # блоки идут друг за другом: крупный шрифт (125 %, Atkinson) не наезжает строками на соседей
        y1 = 230
        y2 = max(330, y1 + len(wrap_lines(story, 800, 20)) * (font(20).get_height() + 2) + 14)
        y3 = (max(430, y2 + len(wrap_lines(barty, 800, 19)) * (font(19).get_height() + 2) + 16)
              if barty else y2 + 10)
        panel = pygame.Rect(WIDTH // 2 - 440, 205, 880, max(270, y3 + font(18).get_height() + 22 - 205))
        pk = appear(st, 0.5, 0.5)
        ps = Surf(panel.size, pygame.SRCALPHA)
        aa_rect(ps, (18, 16, 30, int(200 * pk)), ps.get_rect(), border_radius=14)
        surf.blit(ps, panel)
        self._wave_title(surf, "ВЕЧЕРИНКА!", (WIDTH // 2, 140), 60, AMBER, st)
        draw_wrapped(surf, story, (WIDTH // 2, y1), 800, 20, WHITE, center=True)
        if barty:
            draw_wrapped(surf, barty, (WIDTH // 2, y2), 800, 19, GHOST, center=True)
        n_chairs = len([g for g in self.garage if g[0] in self._job_ids])    # билеты Гильдии — не коляски
        draw_text(surf, f"Коллекция: {n_chairs} колясок починено и спасено.",
                  (WIDTH // 2, y3), 18, PURPLE, center=True)
        draw_text(surf, "[ тап — посмотреть гараж ]" if TOUCH["on"] else "[ клик — посмотреть гараж ]",
                  (WIDTH // 2, max(510, panel.bottom + 20)), 20, AMBER, center=True,
                  alpha=150 + 105 * (0.5 + 0.5 * wsin(self.t * 3.2)))
        Button(self._credits_btn_rect(), "ТИТРЫ", GHOST).draw(surf, mouse_pos())
        Button(self._support_btn_rect(), "ПОДДЕРЖАТЬ GOAT ♥", AMBER).draw(surf, mouse_pos())


# ----------------------------------------------------------------------------- #
#  Self-test (headless): полная проверка логики без окна
# ----------------------------------------------------------------------------- #
def run_selftest():
    global FEEDBACK_URL
    FEEDBACK_URL = ""                     # тесты никогда не шлют замечания в настоящую таблицу
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    failures = []

    def _solve_mini(g):
        """Пройти активную мини-интеракцию верным значением."""
        m = g.mini_pending
        cfg = m["cfg"]
        k = m["kind"]
        if k == "pump":
            m["value"] = (cfg["lo"] + cfg["hi"]) // 2
            g.mini_pump_done()
        elif k == "gap":
            m["value"] = (cfg["lo"] + cfg["hi"]) // 2
            g.mini_gap_check()
        elif k == "ping":
            for i in sorted(m["dull"]):
                g.mini_ping(i)
        elif k == "meter":
            ci = next(i for i, o in enumerate(cfg["options"]) if o[1])
            g.mini_meter(ci)
        assert g.mini_pending is None, "мини-игра не завершилась"

    def _run_tech(g):
        """Пройти tech-задание в валидном порядке (спеки — по мануалу, мини — верно)."""
        guard = 0
        while g.phase == "repair" and guard < 200:
            guard += 1
            for st in g.cur["steps"]:
                if st["id"] in g.done_steps:
                    continue
                if any(a not in g.done_steps for a in st["after"]):
                    continue
                res = g.do_tech_action(st["tool"], st["id"])
                if res == "spec":
                    g.open_manual(st["spec"]["manual"])
                    ci = next(i for i, o in enumerate(st["spec"]["options"]) if o[1])
                    assert g.choose_spec(ci)
                elif res == "mini":
                    _solve_mini(g)
                else:
                    assert res == "ok", f"{g.cur['id']}: шаг {st['id']} не принят ({res})"
                break
        assert g.phase == "test", f"{g.cur['id']}: не дошли до теста"
        g.finish_test()

    def _resolved(base):
        """Все игровые версии задания (каждый вариант поломки отдельно)."""
        if "variants" in base:
            return [resolve_job(base, i) for i in range(len(base["variants"]))]
        return [base]

    # целостность данных: инструменты и детали шагов существуют (во всех вариантах)
    for base in JOBS:
        for job in _resolved(base):
            assert any(d["correct"] for d in job["diagnosis"]), f"{job['id']}: нет верного диагноза"
            for st in job["steps"]:
                if st["tool"] not in TOOLS:
                    failures.append(f"{job['id']}: неизвестный инструмент {st['tool']}")
                if st["part"] not in PARTS:
                    failures.append(f"{job['id']}: неизвестная деталь {st['part']}")
                if st["part"] not in job["parts"]:
                    failures.append(f"{job['id']}: деталь шага {st['part']} не показана игроку")

    # проходим КАЖДОЕ задание (и каждый вариант поломки) по верным шагам
    for base in JOBS:
        n_vars = len(base.get("variants", [])) or 1
        for vi in range(n_vars):
            g = Game(headless=True)
            g.start_job(base["id"], variant=vi if "variants" in base else None)
            job = g.cur
            assert g.phase == "diagnose"
            ci = next(i for i, d in enumerate(job["diagnosis"]) if d["correct"])
            # диагноз заблокирован, пока не осмотрено достаточно деталей
            assert g.choose_diagnosis(ci) is False and g.phase == "diagnose", \
                f"{job['id']}: диагноз без осмотра должен быть заблокирован"
            for pid in job["parts"][:INSPECT_REQ]:
                g.inspect_part(pid)
            # неверный диагноз не двигает фазу
            wrong = [i for i, d in enumerate(job["diagnosis"]) if not d["correct"]]
            if wrong:
                g.choose_diagnosis(wrong[0])
                assert g.phase == "diagnose", f"{job['id']}: неверный диагноз пропустил дальше"
            g.choose_diagnosis(ci)
            assert g.phase == "repair", f"{job['id']}: верный диагноз не открыл ремонт"
            # неверное действие не двигает шаг
            bad_tool = "cloth" if job["steps"][0]["tool"] != "cloth" else "hands"
            before = g.step_idx
            g.do_action(bad_tool, job["steps"][0]["part"])
            assert g.step_idx == before, f"{job['id']}: ошибка продвинула шаг"
            # верные шаги по порядку
            guard = 0
            while g.phase == "repair" and guard < 100:
                guard += 1
                st = job["steps"][g.step_idx]
                res = g.do_action(st["tool"], st["part"])
                assert res in ("ok", "mini"), f"{job['id']}: верный шаг не принят"
                if res == "mini":
                    _solve_mini(g)
            assert g.phase == "test", f"{job['id']}: не дошли до теста (guard={guard})"
            g.finish_test()
            assert g.scene == "result", f"{job['id']}: тест не привёл к результату"
            assert base["id"] in g.done

    # сценарий полного прохождения (случайные варианты): все задания -> ending
    g = Game(headless=True)
    for job in JOBS:
        g.start_job(job["id"])
        for pid in g.cur["parts"][:INSPECT_REQ]:
            g.inspect_part(pid)
        ci = next(i for i, d in enumerate(g.cur["diagnosis"]) if d["correct"])
        g.choose_diagnosis(ci)
        while g.phase == "repair":
            st = g.cur["steps"][g.step_idx]
            if g.do_action(st["tool"], st["part"]) == "mini":
                _solve_mini(g)
        g.finish_test()
    assert len(g.done) == len(JOBS)
    assert len(g.garage) == len(JOBS)

    # ===================== про-трек: Гильдия =====================
    # целостность данных tech-заданий
    for job in TECH_JOBS:
        ids = {s["id"] for s in job["steps"]}
        assert len(ids) == len(job["steps"]), f"{job['id']}: дубли id шагов"
        for st in job["steps"]:
            if st["tool"] not in TOOLS:
                failures.append(f"{job['id']}: неизвестный инструмент {st['tool']}")
            if st["part"] not in PARTS:
                failures.append(f"{job['id']}: неизвестная деталь {st['part']}")
            if st["tool"] not in job["tools"]:
                failures.append(f"{job['id']}: инструмента {st['tool']} нет в палитре задания")
            for a in st["after"]:
                if a not in ids:
                    failures.append(f"{job['id']}: неизвестная зависимость {a}")
            if st["spec"]:
                if st["spec"]["manual"] not in MANUAL:
                    failures.append(f"{job['id']}: спека ссылается на неизвестную страницу мануала")
                if sum(1 for o in st["spec"]["options"] if o[1]) != 1:
                    failures.append(f"{job['id']}: у спеки должен быть ровно один верный вариант")
        for key in job.get("manual", []):
            if key not in MANUAL:
                failures.append(f"{job['id']}: страницы мануала {key} не существует")
        assert len(job["tools"]) <= 7, f"{job['id']}: палитра >7 инструментов не влезает в ряд"

    # мини-интеракции: корректность данных (в базовых и tech-заданиях)
    MINI_KINDS = {"pump", "gap", "ping", "meter"}
    for job in [rj for b in JOBS for rj in _resolved(b)] + TECH_JOBS:
        for st in job["steps"]:
            mini = st.get("mini")
            if not mini:
                continue
            if mini["kind"] not in MINI_KINDS:
                failures.append(f"{job['id']}: неизвестная мини-игра {mini['kind']}")
            if mini["kind"] == "meter" and sum(1 for o in mini["options"] if o[1]) != 1:
                failures.append(f"{job['id']}: у мультиметра должен быть один верный вердикт")
            if mini["kind"] == "pump" and not (0 <= mini["lo"] <= mini["hi"] <= mini["mx"]):
                failures.append(f"{job['id']}: зона накачки вне шкалы")
            if mini["kind"] == "gap" and not (mini["mn"] <= mini["lo"] <= mini["hi"] <= mini["mx"]):
                failures.append(f"{job['id']}: зона зазора вне шкалы")
            if mini["kind"] == "ping" and not (0 < mini["dull"] < mini["total"]):
                failures.append(f"{job['id']}: некорректное число глухих спиц")

    # свободный порядок + спека (правка обода)
    g = Game(headless=True)
    g.start_job("truing")
    assert g.phase == "repair" and g.scene == "job"
    assert g.do_tech_action("spoke_key", "w_adjust") == "wrong", \
        "нарушение порядка без safety должно быть ошибкой, не провалом"
    assert g.scene == "job"
    assert g.do_tech_action("hands", "w_unmount") == "ok"
    assert g.do_tech_action("hands", "w_mount") == "ok"
    # свободный порядок: замер натяжения раньше поиска биения — допустимо
    assert g.do_tech_action("tensiometer", "w_tension") == "ok"
    assert g.do_tech_action("dial", "w_spin") == "ok"
    # спека: без мануала значение не принимается
    assert g.do_tech_action("spoke_key", "w_adjust") == "spec"
    opts = g.spec_pending["spec"]["options"]
    ci = next(i for i, o in enumerate(opts) if o[1])
    wi = next(i for i, o in enumerate(opts) if not o[1])
    assert g.choose_spec(ci) is False, "спека не должна приниматься до чтения мануала"
    g.open_manual(g.spec_pending["spec"]["manual"])   # как кнопка МАНУАЛ в игре
    assert g.choose_spec(wi) is False and g.spec_pending is not None
    assert g.choose_spec(ci) is True
    for sid in ("w_recheck", "w_even", "w_unstand", "w_back"):
        st = g.step_by_id(sid)
        assert g.do_tech_action(st["tool"], sid) == "ok", f"truing: шаг {sid} не принят"
    assert g.phase == "test"
    g.finish_test()
    assert "truing" in g.done

    # safety-провал: клеммы при включённом питании
    g = Game(headless=True)
    g.start_job("t_battery")
    for sid in ("p_cover_f", "p_cover_r", "p_door"):
        assert g.do_tech_action("hands", sid) == "ok"
    assert g.do_tech_action("wrench", "p_disc_neg") == "fail"
    assert g.scene == "failed", "работа с клеммами при включённом питании должна проваливать задание"

    # safety-провал: плюс раньше минуса при разборке
    g = Game(headless=True)
    g.start_job("t_battery")
    for sid in ("p_off", "p_drive", "p_cover_f", "p_cover_r", "p_door", "p_breaker"):
        st = g.step_by_id(sid)
        g.do_tech_action(st["tool"], sid)
    assert g.do_tech_action("wrench", "p_disc_pos") == "fail", "снятие плюса до минуса должно проваливать"

    # safety-провал: клеммы без отключения батарей главным автоматом
    g = Game(headless=True)
    g.start_job("t_battery")
    for sid in ("p_off", "p_drive", "p_cover_f", "p_cover_r", "p_door"):
        st = g.step_by_id(sid)
        assert g.do_tech_action(st["tool"], sid) == "ok"
    assert g.do_tech_action("wrench", "p_disc_neg") == "fail", "клеммы без автомата должны проваливать"

    # корректное прохождение замены батарей целиком
    g = Game(headless=True)
    g.start_job("t_battery")
    order = ["p_off", "p_drive", "p_cover_f", "p_cover_r", "p_door", "p_breaker", "p_disc_neg", "p_disc_pos",
             "p_out", "p_in", "p_conn_pos", "p_conn_neg", "p_breaker_on", "p_door_close", "p_covers", "p_charge"]
    for sid in order:
        st = g.step_by_id(sid)
        res = g.do_tech_action(st["tool"], sid)
        if res == "spec":
            g.open_manual(st["spec"]["manual"])
            ci = next(i for i, o in enumerate(st["spec"]["options"]) if o[1])
            assert g.choose_spec(ci)
        else:
            assert res == "ok", f"t_battery: шаг {sid} не принят ({res})"
    assert g.phase == "test"
    g.finish_test()
    assert "t_battery" in g.done

    # разблокировка Гильдии и подсчёт финала
    g = Game(headless=True)
    assert not g.guild_unlocked()
    for job in JOBS[:GUILD_REQ]:
        g.done.add(job["id"])
    assert g.guild_unlocked()
    g = Game(headless=True)
    g.done = {j["id"] for j in JOBS[:-1]} | {j["id"] for j in TECH_JOBS}
    assert g.user_done_count() < len(JOBS), "tech-задания не должны приближать концовку"

    # мини-игры: неверное значение = ошибка, верное завершает шаг (зазор тормоза)
    g = Game(headless=True)
    g.start_job("brake")
    for pid in g.cur["parts"][:INSPECT_REQ]:
        g.inspect_part(pid)
    ci = next(i for i, d in enumerate(g.cur["diagnosis"]) if d["correct"])
    g.choose_diagnosis(ci)
    gap_checked = False
    while g.phase == "repair":
        st = g.cur["steps"][g.step_idx]
        res = g.do_action(st["tool"], st["part"])
        if res == "mini":
            if g.mini_pending["kind"] == "gap" and not gap_checked:
                gap_checked = True
                g.mini_pending["value"] = 11          # вне зоны 3–6 мм
                before = g.mistakes
                g.mini_gap_check()
                assert g.mistakes == before + 1 and g.mini_pending, \
                    "зазор вне зоны должен быть ошибкой, а шаг — остаться"
            _solve_mini(g)
    assert gap_checked and g.phase == "test"

    # мини-игры: недокачанная шина = ошибка (насос)
    g = Game(headless=True)
    g.start_job("flat")
    for pid in g.cur["parts"][:INSPECT_REQ]:
        g.inspect_part(pid)
    g.choose_diagnosis(next(i for i, d_ in enumerate(g.cur["diagnosis"]) if d_["correct"]))
    pump_checked = False
    while g.phase == "repair":
        st = g.cur["steps"][g.step_idx]
        res = g.do_action(st["tool"], st["part"])
        if res == "mini":
            if g.mini_pending["kind"] == "pump" and not pump_checked:
                pump_checked = True
                g.mini_pending["value"] = 10
                before = g.mistakes
                g.mini_pump_done()
                assert g.mistakes == before + 1 and g.mini_pending, \
                    "недокачанная шина должна быть ошибкой"
            _solve_mini(g)
    assert pump_checked and g.phase == "test"

    # кнопки шагов: «◂» напоминает прошлый шаг, «Шаг ▸» пропускает (минус звезда), Гильдия — тоже, экзамен — нет
    g = Game(headless=True)
    g.start_job("flat")
    for pid in g.cur["parts"][:INSPECT_REQ]:
        g.inspect_part(pid)
    g.choose_diagnosis(next(i for i, d_ in enumerate(g.cur["diagnosis"]) if d_["correct"]))
    g.step_back()
    assert g.step_idx == 0
    while g.phase == "repair":
        g.click_job(g._step_skip_rect().center)
    assert g.phase == "test" and g.mistakes == 2 * len(g.cur["steps"]), "пропуск шага = 2 ошибки"
    g = Game(headless=True)
    g.start_job(TECH_JOBS[0]["id"])
    n = 0
    while g.phase == "repair" and n < 40:
        g.click_job_tech(g._tech_skip_rect().center)
        n += 1
    assert g.phase == "test" and g.mistakes == 2 * len(g.cur["steps"]), "Гильдия: пропуск по порядку"
    g = Game(headless=True)
    g.start_exam()
    g.step_skip()
    assert not g.done_steps and g.mistakes == 0, "на экзамене пропуск запрещён"

    # итог хода держится до следующего нажатия; «тихий» клиент — одна фраза; Барти можно убрать; насос стравливает
    saved = {k: A11Y[k] for k in ("barty", "quiet", "quiet_set", "calm")}
    try:
        g = Game(headless=True)
        g.start_job("flat")
        g.inspect_part(g.cur["parts"][0])
        for _ in range(300):
            g.update(1 / 30)
        assert g.toast_timer > 0, "улика не должна исчезать сама"
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT, mod=0, unicode=""))
        for _ in range(30):
            g.update(1 / 30)
        assert g.toast_timer <= 0, "после нажатия улика уходит"
        A11Y.update(quiet=True, quiet_set=True, barty=False)
        g = Game(headless=True)
        g.start_job("caster")
        said = set()
        for _ in range(30 * 120):
            g.update(1 / 30)
            if g.client_line:
                said.add(g.client_line)
        assert len(said) == 1, f"тихий режим: одна фраза клиента, а было {len(said)}"
        g.barty_quip("idle")
        assert not g.ghost_quip, "Барти выключен — без шуток"
        A11Y.update(quiet=False, quiet_set=False, calm=True)
        assert quiet_talk(), "без анимации — клиент по умолчанию тоже тихий"
        g = Game(headless=True)
        g.start_job("flat")
        for pid in g.cur["parts"][:INSPECT_REQ]:
            g.inspect_part(pid)
        g.choose_diagnosis(next(i for i, d_ in enumerate(g.cur["diagnosis"]) if d_["correct"]))
        while g.phase == "repair" and not (g.mini_pending and g.mini_pending["kind"] == "pump"):
            st = g.cur["steps"][g.step_idx]
            if g.do_action(st["tool"], st["part"]) == "mini":
                if g.mini_pending["kind"] == "pump":
                    break
                _solve_mini(g)
        if g.mini_pending:
            cfg = g.mini_pending["cfg"]
            g.mini_pending["value"] = cfg["hi"] + 5
            before = g.mistakes
            while g.mini_pending["value"] > cfg["hi"]:
                g.mini_release()
            assert g.mistakes == before and g.mini_pending["value"] >= cfg["lo"] - 6, "стравить — без ошибки"
    finally:
        A11Y.update(saved)

    # масштаб коляски: «+»/«−» в окне задания и клавиши, в пределах M3D_ZOOM
    g = Game(headless=True)
    g.start_job("caster")
    if g._m3d_zoom_on():
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_EQUALS, mod=0, unicode="="))
        assert g._m3d_state()["zoom_k"] > 1.0, "«+» — крупнее"
        for _ in range(20):
            g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=g._m3d_zoom_rects()[1].center))
        assert abs(g._m3d_state()["zoom_k"] - g.M3D_ZOOM[0]) < 1e-6, "«−» — до предела, не дальше"

    # сноски из мануалов — к деталям, которые есть в задании (иначе значок книжки не появится)
    for _jid, _notes in MANUAL_NOTES.items():
        _job = next((j for j in ALL_JOBS if j["id"] == _jid), None)
        assert _job, f"MANUAL_NOTES: нет задания {_jid}"
        _parts = set(_job.get("parts") or []).union(*[set(v.get("parts") or []) for v in _job.get("variants", [])])
        for _pid, (_m, _pg, _t) in _notes.items():
            assert _pid in _parts, f"MANUAL_NOTES {_jid}: деталь {_pid} не в задании"
            assert tr(_t) != _t or LANG["code"] == "ru", f"MANUAL_NOTES {_jid}/{_pid}: нет перевода"

    # у каждой настройки на каждой вкладке есть объяснение (карточка при наведении/фокусе)
    g = Game(headless=True)
    for tab in ("sound", "graphics", "access", "game"):
        g.settings_tab = tab
        for k, _z in g._settings_help_zones():
            assert k in Game.SETTING_HELP and tr(Game.SETTING_HELP[k]), f"настройки «{tab}»: нет объяснения {k}"

    # другие верные ответы из отзывов игроков (alt — детали, alt_tools — инструменты) засчитываются
    for jid, n, tool, part in (("yaga_d100", 1, "hands", "axle"), ("yaga_d100", 8, "hands", "brake"),
                               ("cushion", 3, "hands", "cushion"), ("ra_emotion", 2, "charger", "rear_wheel"),
                               ("leshy_x8", 7, "eyes", "freewheel"), ("olga_x3", 12, "socket", "brake"),
                               ("spokes", 4, "socket", "bolts"), ("spokes", 4, "wrench", "bolts")):
        g = Game(headless=True)
        g.start_job(jid, variant=0)
        g.phase, g.step_idx = "repair", n - 1
        assert g.do_action(tool, part) in ("ok", "mini"), f"{jid} шаг {n}: {tool} → {part} должно быть верно"
        assert g.mistakes == 0, f"{jid} шаг {n}: верная альтернатива не должна считаться ошибкой"
    for job in ALL_JOBS:                              # альтернативы — настоящие инструменты и детали задания
        for v in (job.get("variants") or [job]):
            for st in v.get("steps", []):
                assert all(t in TOOLS for t in st.get("alt_tools", ())), f"{job['id']}: alt_tools {st['alt_tools']}"

    # каждое tech-задание проходится в валидном порядке (включая toe с мини-игрой)
    for job in TECH_JOBS:
        g = Game(headless=True)
        g.start_job(job["id"])
        _run_tech(g)
        assert job["id"] in g.done, f"{job['id']}: не засчитано"

    # экзамен: сдача случайного билета ведёт к диплому
    g = Game(headless=True)
    g.start_exam()
    assert g.exam_mode and g.phase == "repair" and g.scene == "job"
    _run_tech(g)
    assert g.scene == "exam_result" and g.exam_passed, "сданный экзамен должен давать диплом"

    # экзамен: перебор лимита ошибок = пересдача
    g = Game(headless=True)
    g.start_exam()
    free = next(s for s in g.cur["steps"] if not s["after"])
    for _ in range(EXAM_MAX_MISTAKES + 1):
        g.do_tech_action("lever", free["id"])   # заведомо неверный инструмент
    assert g.scene == "failed", "перебор ошибок на экзамене должен завершать его"
    assert not g.exam_passed

    # векторный арт: всё, что запрашивают сцены и задания, рисуется кодом
    needed = {"martin", "ghost", "master", "chair_basic", "chair_power",
              "bg_workshop", "bg_road", "bg_garage", "bg_party", "bg_guild"}
    for job in ALL_JOBS:
        needed.add(os.path.splitext(job["client_art"])[0])
        needed.add(os.path.splitext(job["chair_art"])[0])
    for name in sorted(needed):
        if name not in VECTOR_ART:
            failures.append(f"нет векторного арта для {name} — будет серая заглушка")
    for name, fn in VECTOR_ART.items():
        art = fn()
        assert art.get_width() > 0 and art.get_height() > 0, f"арт {name} не отрисовался"

    # Esc: цепочка «назад» и двойной Esc из ремонта
    def _esc(g):
        g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    g = Game(headless=True)
    g.start_job("flat")
    _esc(g)
    assert g.scene == "job" and g.esc_timer > 0, "первый Esc в ремонте должен только предупреждать"
    _esc(g)
    assert g.scene == "hub", "двойной Esc должен выводить из ремонта в мастерскую"
    _esc(g)
    assert g.scene == "title", "Esc из мастерской должен вести на титул"
    # титры: открываются с титула, листаются, Esc — обратно; весь текст переведён
    g.open_credits()
    assert g.scene == "credits" and g.credits_from == "title"
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END, mod=0, unicode=""))
    assert abs(g.credits_y - g._credits_max()) < 1e-6, "End в титрах — к концу"
    g.draw(pygame.display.get_surface())
    _esc(g)
    assert g.scene == "title", "Esc из титров — обратно на титул"
    # память: кадры поворота держит только коляска на экране (иначе телефон «вставал» через пару заданий)
    _a, _b = get_turntable("chair_basic.png"), get_turntable("chair_elf.png")
    if _a and _b:
        get_turntable("chair_basic.png").update()
        assert len(_a.frames) == _a.n, "кадры поворота не загрузились"
        get_turntable("chair_elf.png").update()
        assert not _a.frames and len(_b.frames) == _b.n, "кадры прежней коляски должны освободиться"
        _b.release()
    # браузер, «авто»: холст ровно с окно игры (кратно 16), в пределах WEB_MIN_W…1440p, потолок после замедления
    _d0 = {k: DISPLAY.get(k) for k in ("web_px", "web_cap", "web_quality")}
    DISPLAY["web_quality"] = "auto"; DISPLAY.pop("web_cap", None)
    for _px, _want in ((1100, (1104, 621)), (1920, (1920, 1080)), (3000, (2560, 1440)), (500, (WEB_MIN_W, WEB_MIN_W * 9 // 16))):
        DISPLAY["web_px"] = _px
        assert web_target_res() == _want, f"холст для {_px} px: {web_target_res()} вместо {_want}"
    DISPLAY["web_px"], DISPLAY["web_cap"] = 2000, 0
    assert web_target_res()[0] <= WEB_RES["standard"][0], "после замедления холст не больше 720p"
    for _k, _v in _d0.items():
        if _v is None:
            DISPLAY.pop(_k, None)
        else:
            DISPLAY[_k] = _v
    # музыка: в рабочих сценах через MUSIC_FULL стихает до фона, на титуле и при смене сцены — снова громче
    MUSIC["duck"] = 1.0
    for _ in range(80):
        music_duck("job", MUSIC_FULL + 30, 0.5)
    assert abs(MUSIC["duck"] - MUSIC_BED) < 1e-6, f"музыка за работой — фон: {MUSIC['duck']}"
    for _ in range(10):
        music_duck("title", 100, 0.5)
    assert MUSIC["duck"] == 1.0, "на титуле — мелодия полностью"
    music_duck("job", 5, 0.5)
    assert MUSIC["duck"] == 1.0, "новая сцена — мелодия полностью"
    # геймпад: Start — настройки, B — закрыть; стик держат — стрелка повторяется; простой джойстик — тоже
    E_ = pygame.event.Event
    g.scene = "hub"; g.show_sound = False; g.draw(pygame.display.get_surface())
    g.handle_event(E_(pygame.CONTROLLERBUTTONDOWN, instance_id=0, button=pygame.CONTROLLER_BUTTON_START))
    assert g.show_sound, "геймпад: Start должен открыть настройки"
    g.handle_event(E_(pygame.CONTROLLERBUTTONDOWN, instance_id=0, button=pygame.CONTROLLER_BUTTON_B))
    assert not g.show_sound, "геймпад: B — закрыть настройки"
    g.draw(pygame.display.get_surface())
    _moves = []
    _orig = g._a11y_focus
    g._a11y_focus = lambda it, items: (_moves.append(it["key"]), _orig(it, items))
    g.handle_event(E_(pygame.CONTROLLERAXISMOTION, instance_id=0, axis=pygame.CONTROLLER_AXIS_LEFTY, value=30000))
    for _ in range(12):
        g.update(0.1)
    g.handle_event(E_(pygame.CONTROLLERAXISMOTION, instance_id=0, axis=pygame.CONTROLLER_AXIS_LEFTY, value=0))
    n = len(_moves)
    g.update(0.5)
    assert n >= 4 and len(_moves) == n, f"геймпад: стик вниз — повтор, отпустил — стоп ({n}, {len(_moves)})"
    PAD["joy"][7] = None                                          # простой джойстик: крестовина-шляпка и кнопка 1 = B
    g.handle_event(E_(pygame.JOYHATMOTION, instance_id=7, joy=7, hat=0, value=(0, -1)))
    g.handle_event(E_(pygame.JOYHATMOTION, instance_id=7, joy=7, hat=0, value=(0, 0)))
    assert len(_moves) == n + 1, "геймпад: шляпка простого джойстика — стрелка"
    PAD["ctrl"][8] = None                                         # тот же геймпад шлёт и JOY-события — не дублируем
    g.handle_event(E_(pygame.JOYHATMOTION, instance_id=8, joy=8, hat=0, value=(0, -1)))
    assert len(_moves) == n + 1, "геймпад: JOY-события от геймпада с раскладкой SDL — не второй раз"
    PAD["joy"].pop(7, None); PAD["ctrl"].pop(8, None); PAD["dir"] = None
    g._a11y_focus = _orig
    g.scene = "title"; g.kb["key"] = None; g.draw(pygame.display.get_surface())
    # одна кнопка: выделение идёт само, короткое нажатие — выбрать, долгое — назад
    _scan0 = A11Y["scan"]
    A11Y["scan"] = 1
    g.scene_t0 = g.t - 5
    g.kb["key"] = None
    g._scan_next = g.t                       # пора выделять
    g.draw(pygame.display.get_surface())
    g.update(0.01); g.draw(pygame.display.get_surface())
    assert g.kb["key"] == "start", f"одна кнопка: первым выделяется «начать»: {g.kb['key']}"
    g.update(1.05); g.draw(pygame.display.get_surface())
    assert g.kb["key"] == "credits", f"одна кнопка: затем «титры»: {g.kb['key']}"
    for _t in (pygame.KEYDOWN, pygame.KEYUP):
        g.handle_event(pygame.event.Event(_t, key=pygame.K_SPACE, mod=0, unicode=" "))
    assert g.scene == "credits", f"одна кнопка: нажатие выбирает выделенное: {g.scene}"
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=" "))
    g.update(SCAN_HOLD + 0.1)
    g.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE, mod=0, unicode=" "))
    assert g.scene == "title", f"одна кнопка: долгое нажатие — назад: {g.scene}"
    A11Y["scan"] = _scan0
    g.kb["scan_sub"] = None
    # касание пальцем: клик ровно там, куда коснулись; «мышь», которую браузер делает из касания, — мимо
    g.scene_t0 = g.t - 5
    sw, sh = pygame.display.get_surface().get_size()
    cb = g._credits_btn_rect().center
    _fx, _fy = cb[0] * RS / sw, cb[1] * RS / sh
    for _ev in (pygame.event.Event(pygame.FINGERDOWN, x=_fx, y=_fy, dx=0, dy=0, finger_id=1, touch_id=1, pressure=1),
                pygame.event.Event(pygame.FINGERUP, x=_fx, y=_fy, dx=0, dy=0, finger_id=1, touch_id=1, pressure=0)):
        for _e in finger_events(_ev):
            g.handle_event(_e)
    assert g.scene == "credits", f"касание по «ТИТРЫ» должно открыть титры: {g.scene}"
    assert finger_events(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(5, 5), button=1, touch=False)) == [],         "мышиное эхо касания должно отбрасываться"
    FINGER.update(t=-10 ** 9, pos=None)
    _esc(g)
    for _h, _lines in CREDITS:
        for _x in [_h] + _lines:
            if re.search("[А-Яа-яЁё]", _x):
                assert tr_en(_x) != _x, f"титры без перевода: {_x}"
    pygame.event.clear()
    _esc(g)
    assert not any(e.type == pygame.QUIT for e in pygame.event.get()) and g.esc_timer > 0, \
        "первый Esc с титула — только предупреждение (B геймпада / «назад» не закрывают игру сразу)"
    _esc(g)
    assert any(e.type == pygame.QUIT for e in pygame.event.get()), \
        "второй Esc с титула должен закрывать игру"
    g = Game(headless=True)
    g.start_job("truing")
    g.open_manual()
    _esc(g)
    assert g.show_manual is False and g.scene == "job", "Esc сперва закрывает оверлей"
    _esc(g)
    _esc(g)
    assert g.scene == "guild", "двойной Esc из tech-задания должен вести в Гильдию"

    # 3D-осмотр: модели целостны, каждая деталь заданий есть на модели, пикинг работает, Esc закрывает
    for kind in ("manual", "power"):
        mesh = get_chair3d(kind)
        for idx, part, col, fl in mesh.faces:
            if part is not None and part not in PARTS:
                failures.append(f"3D {kind}: неизвестная деталь {part}")
            assert len(idx) >= 3, f"3D {kind}: вырожденная грань"
    for base in JOBS:
        for job in _resolved(base):
            if job.get("chair_art") in AI_MODELS or get_turntable(job.get("chair_art")):   # своя модель/кадры
                continue
            centers = get_chair3d(job.get("kind")).centers
            missing = [pid for pid in job["parts"] if pid not in centers]
            if missing:
                failures.append(f"3D {job['id']}: на модели нет деталей {missing}")
    # настоящие 3D-модели (Hunyuan3D): у каждой детали задания есть место на модели
    for base in ALL_JOBS:
        for job in _resolved(base):
            mesh = get_ai_chair3d(job.get("chair_art"))
            if mesh is None and job.get("chair_art") in AI_MODELS:
                failures.append(f"3D {job['id']}: не загрузилась модель {AI_MODELS[job['chair_art']]}")
            elif mesh is not None:
                miss = [pid for pid in job.get("parts", []) if pid not in mesh.centers]
                if miss:
                    failures.append(f"3D-ИИ {job['id']}: на модели нет деталей {miss}")
    g = Game(headless=True)
    g.start_job("flat")
    g.open_v3d()
    assert g.v3d is not None
    vr = g._v3d_view_rect()
    v = g.v3d
    polys = project_mesh(g._v3d_mesh(), v["yaw"], v["pitch"], vr, v["zoom"])
    assert len(polys) > 300, "3D: слишком мало граней после проекции"
    target = next(p for p in reversed(polys) if p[3])   # ближайшая кликабельная грань
    cxp = vr.x + sum(pt[0] for pt in target[1]) / len(target[1])
    cyp = vr.y + sum(pt[1] for pt in target[1]) / len(target[1])
    picked = g._v3d_pick((cxp, cyp))
    assert picked is not None, "3D: пикинг по центру грани не нашёл деталь"
    g.draw(pygame.display.get_surface())                 # отрисовка оверлея не падает
    _esc(g)
    assert g.v3d is None and g.scene == "job", "Esc должен закрывать 3D-осмотр, не ремонт"

    # хотспоты одной коляски не перекрываются даже на мелкой схеме (иначе клик уходит в соседнюю деталь)
    for base in JOBS:
        for job in _resolved(base):
            gq = Game(headless=True)
            gq.cur = job
            for phase in ("diagnose", "repair"):
                gq.phase = phase
                spots = [s_ for s_ in gq._chair_hotspots()]
                for i, (p1, x1, y1, r1) in enumerate(spots):
                    for p2, x2, y2, r2 in spots[i + 1:]:
                        if (x1 - x2) ** 2 + (y1 - y2) ** 2 < max(r1, r2) ** 2:
                            failures.append(f"{job['id']}/{phase}: хотспоты {p1} и {p2} перекрываются")
    # Кабинет посадки: правила из уроков решают каждую примерку, старт — неправильный, у вопросов один ответ
    for case in SEAT_CASES:
        b = case["body"]
        good = case.get("solution") or dict(depth=b["thigh"] - 5, leg=b["shank"], back_h=sum(case["back"]) // 2,
                                            back_a=sum(case["angle"]) // 2, tilt=case.get("tilt", 0))
        if case.get("view") and not all(o for _, o, _ in Game._seat_eval_side(case, Game._seat_side_cfg(case))[0]):
            failures.append(f"посадка {case['id']}: сбоку по меркам не ровно (должна быть видна только спереди/сверху)")
        for k in case.get("sliders", []):
            if k not in SEAT_SLIDERS or k not in case["start"]:
                failures.append(f"посадка {case['id']}: ползунок {k} без описания или стартового значения")
        bad = [t for k, ok, t in Game.seat_eval(case, good)[0] if not ok]
        if bad:
            failures.append(f"посадка {case['id']}: по правилам не решается: {bad}")
        st = dict(case["start"]); st.setdefault("tilt", 0)
        if all(ok for k, ok, t in Game.seat_eval(case, st)[0]):
            failures.append(f"посадка {case['id']}: стартовая настройка уже правильная — нечего чинить")
        for key, (label, unit, lo, hi) in SEAT_SLIDERS.items():
            if key in good and not lo <= good[key] <= hi:
                failures.append(f"посадка {case['id']}: {key}={good[key]} вне ползунка {lo}..{hi}")
    for i, q in enumerate(SEAT_QUIZ):
        if sum(1 for o in q["options"] if o[1]) != 1:
            failures.append(f"вопрос посадки {i + 1}: должен быть ровно один верный ответ")
    if len(SEAT_MENTOR["lesson"]) != len(SEAT_LESSONS):
        failures.append("Мортимер: реплик к урокам не столько же, сколько уроков")
    gs = Game(headless=True)
    gs.done = {"flat"}
    gs.open_seating()
    scr = pygame.display.get_surface()
    for tab in ("lessons", "fit", "quiz"):
        gs.seatc["tab"] = tab
        for i in range(len(SEAT_LESSONS) if tab == "lessons" else len(SEAT_CASES) if tab == "fit" else len(SEAT_QUIZ)):
            if tab == "lessons":
                gs.seatc["lesson"] = i
            elif tab == "fit":
                gs._seat_load_case(i)
                if SEAT_CASES[i].get("view"):               # и вид сбоку у клиентов с перекосом/поворотом
                    gs.draw(scr)
                    gs.seatc["view"] = "side"
            else:
                gs.seatc.update(quiz=i, picked=0)
            gs.draw(scr)                                     # все экраны кабинета рисуются без падений

    # насос к ниппелю засчитывается в шагах накачки; «Я не согласен» сохраняет замечание и снимает ошибку
    gd = Game(headless=True)
    gd.start_job("flat")
    gd.phase, gd.step_idx = "repair", next(i for i, st in enumerate(gd.cur["steps"]) if st["tool"] == "pump" and st["part"] == "tire")
    if gd.do_action("pump", "valve") not in ("ok", "mini"):
        failures.append("насос к ниппелю не засчитан в шаге накачки шины")
    gd = Game(headless=True)
    gd.start_job("flat")
    gd.phase, gd.step_idx = "repair", 0
    gd.do_action("lever", "rim")
    if not gd.dispute_visible() or gd.mistakes != 1:
        failures.append("после ошибки не появилась кнопка «Я не согласен»")
    else:
        gd.open_dispute()
        gd.handle_dispute_event(pygame.event.Event(pygame.TEXTINPUT, text="тест"))
        gd.draw(pygame.display.get_surface())
        gd.send_dispute()
        if len(gd.feedback_mem) != 1 or gd.feedback_mem[0]["comment"] != "тест" or gd.mistakes != 0:
            failures.append("замечание «Я не согласен» не сохранилось или ошибка не снята")
    DISPLAY["glow"] = False
    gd.draw(pygame.display.get_surface())
    DISPLAY["glow"] = True
    # настройки: вкладки звук/графика открываются и рисуются, выбор разрешения запоминается
    gq_ = Game(headless=True)
    gq_.scene = "hub"
    gq_.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=gq_._speaker_rect().center))
    if not gq_.show_sound:
        failures.append("шестерёнка не открыла настройки")
    gq_.draw(pygame.display.get_surface())
    gq_.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=gq_._settings_tab_rects()[1][1].center))
    gq_.draw(pygame.display.get_surface())
    old_res = DISPLAY["res"]
    opt, r_ = gq_._res_rects()[-1]
    gq_.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r_.center))
    if (DISPLAY["res"] or "auto") != opt:
        failures.append("выбор разрешения в настройках не сработал")
    DISPLAY["res"] = old_res

    # варианты ответов перемешиваются: верный диагноз не всегда первый
    gs_ = Game(headless=True)
    seen = set()
    for _ in range(30):
        gs_.start_job("flat")
        seen.add(next(i for i, d_ in enumerate(gs_.cur["diagnosis"]) if d_["correct"]))
    if len(seen) < 2:
        failures.append("варианты диагноза не перемешиваются — верный всегда на одном месте")

    # флажок ⚑: общее замечание с любого экрана (без засчитанной ошибки)
    gf = Game(headless=True)
    gf.done = {"flat"}
    gf.scene = "hub"
    gf.draw(pygame.display.get_surface())
    gf.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=gf._feedback_rect().center))
    if gf.dispute_ui is None or gf.dispute["kind"] != "general":
        failures.append("флажок «Сообщить о неточности» не открыл окно")
    else:
        gf.dispute_ui["reason"] = 0
        gf.draw(pygame.display.get_surface())
        gf.send_dispute()
        if len(gf.feedback_mem) != 1 or gf.feedback_mem[0]["reason"] != Game.FEEDBACK_REASONS[0]:
            failures.append("общее замечание не сохранилось")

    # 3D на экране задания (осмотр и ремонт): у каждой детали задания есть кружок, кружки не перекрываются
    if _np is not None:
        for base in JOBS:
            for job in _resolved(base):
                for phase_ in ("diagnose", "repair"):
                    gq = Game(headless=True)
                    gq.cur = job
                    gq.phase = phase_
                    gq.inspected = set()
                    if gq._m3d_mesh() is None:
                        continue
                    spots = gq._chair_hotspots()
                    miss = [p for p in job["parts"] if p not in {q[0] for q in spots}]
                    if miss:
                        failures.append(f"3D {phase_} {job['id']}: нет кружков у {miss}")
                    for i, (p1, x1, y1, r1) in enumerate(spots):
                        for p2, x2, y2, r2 in spots[i + 1:]:
                            if (x1 - x2) ** 2 + (y1 - y2) ** 2 < (r1 + r2 - 2) ** 2:
                                failures.append(f"3D {phase_} {job['id']}: кружки {p1} и {p2} перекрываются")
    # хотспоты схемы коляски ссылаются на существующие детали
    for kind, spots in CHAIR_HOTSPOTS.items():
        for pid in spots:
            if pid not in PARTS:
                failures.append(f"хотспот {kind}/{pid}: неизвестная деталь")
    # у каждой детали базового задания есть либо хотспот, либо строка в списке (список есть всегда);
    # проверяем, что хотя бы половина деталей кликается прямо на схеме
    for base in JOBS:
        for job in _resolved(base):
            spots = CHAIR_HOTSPOTS.get(job.get("chair_model") or job.get("kind"), {})
            covered = sum(1 for p in job["parts"] if p in spots)
            if covered < len(job["parts"]) // 2:
                failures.append(f"{job['id']}: на схеме кликается лишь {covered}/{len(job['parts'])} деталей")

    # живые реплики: у каждого задания полный набор, формат «Имя: «…»», клиент говорит по ходу ремонта
    kinds = ("intro", "worry", "learn", "mistake", "good", "test")
    for job in ALL_JOBS:
        talk = CLIENT_TALK.get(job["id"])
        if not talk or any(not talk.get(k) for k in kinds):
            failures.append(f"{job['id']}: нет реплик клиента ({', '.join(k for k in kinds if not (talk or {}).get(k))})")
    pools = [ln for t in CLIENT_TALK.values() for v in t.values() for ln in v]
    pools += [ln for v in list(BARTY_TALK.values()) + list(MARTIN_TALK.values()) for ln in v]
    for ln in pools:
        if len(ln) > 130 or not re.match(r"^[^:«»]{2,20}: «.+»$", ln):
            failures.append(f"реплика не по формату: {ln[:60]}")
    gt = Game(headless=True)
    gt.start_job("caster")
    for _ in range(40):                                   # ~40 с игры: приход, потом болтовня
        gt.update(1.0)
    if gt.client_line not in [ln for v in CLIENT_TALK["caster"].values() for ln in v]:
        failures.append("клиент не заговорил за 40 с ремонта")
    gt.inspected = set(gt.cur["parts"])
    wrong = next(i for i, o in enumerate(gt.cur["diagnosis"]) if not o["correct"])
    random.seed(3)
    gt.choose_diagnosis(wrong)
    toast_seen = []
    for _ in range(40):                                   # реакция ждёт конца сообщения сверху и паузы TALK_GAP
        gt.update(0.25)
        if gt.client_line in CLIENT_TALK["caster"]["mistake"] or gt.ghost_quip in BARTY_TALK["mistake"]:
            toast_seen.append(gt.toast_timer > 0.3 and gt.t - gt.toast_t0 < 2.9)   # итог хода висит — но не свежий
            break
    if toast_seen and toast_seen[0]:
        failures.append("реакция на ошибку прозвучала, пока висит сообщение сверху")
    if not (gt.client_line in CLIENT_TALK["caster"]["mistake"] or gt.ghost_quip in BARTY_TALK["mistake"]):
        failures.append("на ошибку не отреагировали ни клиент, ни Барти")
    gt.draw(pygame.display.get_surface())
    gt.scene = "hub"
    gt.draw(pygame.display.get_surface())
    for base in JOBS:                                     # записка клиента в Мастерской — до и после ремонта
        for done_ in (False, True):
            try:
                gt._draw_hub_note(pygame.display.get_surface(), base, pygame.Rect(60, 124, 200, 250), done_)
            except Exception as e:
                failures.append(f"записка {base['id']} (починено={done_}): {e!r}")

    # доступность: задание «flat» проходится одними клавишами, игра говорит, что происходит
    # (полный проход всех экранов с клавиатуры — art_tests/keyboard_playthrough.py)
    scr = pygame.display.get_surface()
    ga = Game(headless=True)
    SPEECH.log.clear()

    def kp(k):
        ga.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
        ga.update(0.05)
        ga.draw(scr)

    def to(key_):
        for _ in range(len(ga.kb["items"]) + 2):
            if ga.kb["key"] == key_:
                return True
            kp(pygame.K_DOWN)
        return False

    ga.start_job("flat")
    ga.draw(scr)
    for pid in ga.cur["parts"][:INSPECT_REQ]:
        if to(("part", pid)):
            kp(pygame.K_RETURN)
    okd = next(i for i, o in enumerate(ga.cur["diagnosis"]) if o["correct"])
    if to(("diag", okd)):
        kp(pygame.K_RETURN)
    if ga.phase != "repair":
        failures.append("клавиатура: диагноз не поставлен стрелками и Enter")
    else:
        st0 = ga.cur["steps"][0]
        if to(("tool", st0["tool"])):
            kp(pygame.K_RETURN)
        if to(("part", st0["part"])):
            kp(pygame.K_RETURN)
        if ga.step_idx != 1 and not ga.mini_pending:
            failures.append("клавиатура: первый шаг ремонта не выполнен")
    if not any("Шаг" in t for t in SPEECH.log):
        failures.append("озвучка: шаг ремонта не прозвучал")
    kp(pygame.K_F1)
    if not ga.kb["help"]:
        failures.append("F1 не открыл справку")
    kp(pygame.K_ESCAPE)
    # сброс прогресса: кнопка — только вопрос; «НЕТ» и Esc отменяют; «ДА, СБРОСИТЬ» — сброс; настройки не трогаются
    gr = Game(headless=True)
    gr.done, gr.garage, gr.exam_passed, gr.seat_quiz_ok = {"flat", "caster"}, [("flat", 3)], True, True
    gr.show_sound, gr.settings_tab = True, "game"
    gr.draw(scr)
    vol0, lang0 = dict(VOL), LANG["code"]
    click = lambda r: gr.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=r.center, button=1))
    click(gr._reset_btn_rect())
    gr.draw(scr)
    if not gr.done or not gr._reset_ask:
        failures.append("кнопка сброса должна сначала спросить «да/нет»")
    click(gr._reset_no_rect())
    if not gr.done or gr._reset_ask:
        failures.append("«НЕТ» не отменил сброс")
    click(gr._reset_btn_rect())
    gr.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
    if not gr.done or gr._reset_ask or not gr.show_sound:
        failures.append("Esc должен отменить вопрос о сбросе, не закрывая настройки")
    click(gr._reset_btn_rect())
    click(gr._reset_yes_rect())
    if gr.done or gr.garage or gr.exam_passed or gr.seat_quiz_ok or gr.scene != "title":
        failures.append("«ДА, СБРОСИТЬ» не сбросил прогресс")
    if dict(VOL) != vol0 or LANG["code"] != lang0:
        failures.append("сброс прогресса задел настройки")

    if speech_clean("Enter — начать · 1920×1080 ✔") not in ("Enter, начать, 1920 на 1080", "Enter, начать, 1920 by 1080"):
        failures.append(f"speech_clean: {speech_clean('Enter — начать · 1920×1080 ✔')}")

    # --- падения из аудита 2026-10-17 (art_tests/audit/code_bugs.md) ---
    import tempfile
    surf_ = Surf((WIDTH, HEIGHT))
    gv = Game(headless=True)                                   # V в задании Гильдии: у tech нет parts
    gv.done = {j["id"] for j in JOBS}
    gv.start_job(TECH_JOBS[0]["id"])
    try:
        gv.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=0, unicode="v"))
        gv.update(0.1)
        gv.draw(surf_)
        if gv.v3d is not None:
            failures.append("V открыл 3D-осмотр в задании Гильдии")
    except Exception as e:
        failures.append(f"V в задании Гильдии: {type(e).__name__}: {e}")
    gm = Game(headless=True)                                   # «m»/«ь» в комментарии — текст, а не выкл. звука
    gm.scene = "hub"
    gm.open_feedback()
    vol_on = VOL["on"]
    gm.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0, unicode="ь"))
    gm.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="ь"))
    if VOL["on"] != vol_on or gm.dispute_ui is None or gm.dispute_ui["text"] != "ь":
        failures.append("клавиша M в окне замечания переключила звук")
    VOL["on"] = vol_on
    E_ = pygame.event.Event                                    # пробел: и с TEXTINPUT (компьютер), и без него (браузер)
    for evs in ([E_(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=" "), E_(pygame.TEXTINPUT, text=" ")],
                [E_(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=" ")]):
        gm.dispute_ui["text"] = "a"
        for e_ in evs + [E_(pygame.TEXTINPUT, text="b")]:
            gm.handle_event(e_)
        if gm.dispute_ui["text"] != "a b":
            failures.append(f"пробел в окне замечания: {gm.dispute_ui['text']!r} вместо 'a b'")
    gm.close_dispute()
    calm0, inst0 = A11Y["calm"], A11Y["instant"]             # «Без анимации»: кадр не меняется, тест-драйв — сразу
    A11Y["calm"] = A11Y["instant"] = True                      # (печать по буквам — отдельная настройка «Текст сразу»)
    try:
        gc = Game(headless=True)
        gc.done = {j["id"] for j in JOBS}
        gc.start_job("caster", 0)
        gc.client_queue, gc.client_next, gc._quip_next = [], 1e9, 1e9   # без новых реплик во время замера
        for _ in range(40):
            gc.update(1 / 30)
        sc = pygame.display.get_surface()
        gc.draw(sc)
        f1 = pygame.image.tobytes(sc, "RGB")
        for _ in range(20):
            gc.update(1 / 30)
        gc.draw(sc)
        if pygame.image.tobytes(sc, "RGB") != f1:
            failures.append("«Без анимации»: экран задания продолжает двигаться")
        gc.phase = "test"
        gc.start_ride()
        gc.update(1 / 30)
        if gc.ride_t0 is not None:
            failures.append("«Без анимации»: тест-драйв не завершился сразу")
    finally:
        A11Y["calm"], A11Y["instant"] = calm0, inst0
    for calm_ in (False, True):                                # проезд ждёт «ГОТОВО» (успеть дочитать — отзыв)
        calm0 = A11Y["calm"]
        A11Y["calm"] = calm_
        gr = Game(headless=True)
        gr.start_job("flat")
        gr.phase = "test"
        gr.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=gr._test_btn_rect().center))
        for _ in range(int(Game.RIDE_SECS * 30) + 15):
            gr.update(1 / 30)
        if gr.scene != "job" or not gr.ride_done:
            failures.append("Тест-драйв: после проезда итог открылся сам, без «ГОТОВО»")
        gr.draw(pygame.display.get_surface())
        gr.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=gr._test_btn_rect().center))
        if gr.scene != "result":
            failures.append("Тест-драйв: «ГОТОВО» не открыло итог")
        A11Y["calm"] = calm0
    gk = Game(headless=True)                                   # «Пропустить обучение»: всё открыто, сброс — снова закрыто
    gk.scene, gk.intro_idx = "intro", 0
    gk.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=gk._skip_tut_rect().center))
    if gk.scene != "hub" or len(gk.available_jobs()) != len(JOBS) or not gk.tutorial_ok():
        failures.append("«Пропустить обучение» во вступлении не открыл мастерскую со всеми заданиями")
    gk.reset_progress()
    if gk.tutorial_ok() or gk.available_jobs() != ["flat"]:
        failures.append("сброс прогресса не вернул обучение")
    gk.start_job("flat")
    if gk._skip_tut_rect() is None:
        failures.append("нет кнопки «Пропустить обучение» в первом задании")
    gm.show_sound = True                                       # ⚑ при открытых настройках не открывает окно под ними
    gm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=gm._feedback_rect().center))
    if gm.dispute_ui is not None:
        failures.append("⚑ открыл окно замечания под панелью настроек")
    # битые/старые файлы: settings (a11y), save, feedback — во временной папке, файлы игрока не трогаем
    tmp = tempfile.mkdtemp()
    keep = {k: globals()[k] for k in ("SAVE_PATH", "SETTINGS_PATH", "FEEDBACK_PATH", "DATA_DIR")}
    a11y0, vol0, lang0 = dict(A11Y), dict(VOL), LANG["code"]
    try:
        globals().update(SAVE_PATH=os.path.join(tmp, "save.json"), SETTINGS_PATH=os.path.join(tmp, "settings.json"),
                         FEEDBACK_PATH=os.path.join(tmp, "feedback.json"), DATA_DIR=tmp)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"lang": lang0, "a11y": {"rate": "fast", "on": "false", "instant": None}}, f)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump({"done": ["flat", ["x"]], "garage": [["flat", 3], ["caster"], 5], "exam_passed": True,
                       "seat_quiz_ok": True}, f)
        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            json.dump({"old": "format"}, f)
        try:
            gs = Game(headless=False)
            if A11Y["on"] is not False or not isinstance(A11Y["rate"], int):
                failures.append(f"settings.json: неверные типы a11y приняты: {A11Y}")
            if gs.done != {"flat"} or gs.garage != [("flat", 3)] or not gs.exam_passed or not gs.seat_quiz_ok:
                failures.append("save.json: один битый элемент сбросил остальной прогресс")
            gs.headless = True                                 # снимок экрана не нужен
            gs.scene = "hub"
            gs.open_feedback()
            gs.headless = False
            gs.send_dispute()
            with open(FEEDBACK_PATH, encoding="utf-8-sig") as f:
                if not isinstance(json.load(f), list):
                    failures.append("feedback.json не исправлен на список")
        except Exception as e:
            failures.append(f"битые файлы сохранения: {type(e).__name__}: {e}")
    finally:
        globals().update(keep)
        A11Y.update(a11y0); VOL.update(vol0); set_lang(lang0)
    ad0 = ASSETS_DIR                                           # запасной векторный арт (нет PNG) не падает
    try:
        globals()["ASSETS_DIR"] = tmp
        load_image("martin.png", (77, 91))
    except Exception as e:
        failures.append(f"векторный арт без PNG: {type(e).__name__}: {e}")
    finally:
        globals()["ASSETS_DIR"] = ad0
        _img_cache.pop(("martin.png", (77, 91)), None)

    pygame.quit()
    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    n_var = sum(len(j.get("variants", [])) or 1 for j in JOBS)
    print(f"SELFTEST OK — {len(JOBS)} заданий ({n_var} вариантов поломок) + "
          f"{len(TECH_JOBS)} про-заданий + экзамен Гильдии.")
    print("Проверены: целостность данных, обязательный осмотр, диагностика, шаги ремонта, "
          "мини-интеракции, свободный порядок, спеки, safety-провалы, экзамен, кабинет посадки.")


def print_assets():
    specs = [
        ("bg_workshop.png", "1280x720", "Мастерская: верстак, колёса на стене, круглое окно, свободный пол"),
        ("bg_road.png", "1280x720", "Ночная дорога через лес, без коляски (Мартин рисуется поверх)"),
        ("bg_garage.png", "1280x720", "Гараж с ПУСТЫМИ полками — коллекция заполняется ремонтами"),
        ("bg_party.png", "1280x720", "Вечеринка в саду: фонарики, столы, сцена; пандусы вместо ступеней"),
        ("bg_guild.png", "1280x720", "Зал Гильдии Колёсников: станки, чертежи колёс, эмблема"),
        ("martin.png", "любой, прозр.", "Зомби Мартин в своей коляске (нет левой ноги)"),
        ("ghost.png", "любой, прозр.", "Призрак Барти: парит, монокль, бабочка"),
        ("master.png", "любой, прозр.", "Мастерица Бренна — призрак гномки-механика"),
        ("client_<имя>.png", "любой, прозр.", "Клиент, сидящий в своей коляске (вписывается без искажений)"),
        ("chair_basic/elf/dwarf/fairy/orc/troll.png", "760x600", "Ручная коляска сбоку, нормализована под CHAIR_GEOM"),
        ("chair_power.png", "760x600", "Электроколяска (средний привод) сбоку, под CHAIR_GEOM"),
    ]
    print("КОЛЁСА И КОСТИ — картинки для assets/ (нет файла -> встроенный векторный арт):\n")
    for name, size, desc in specs:
        print(f"  {name:42s} {size:10s} {desc}")
    print("\nИконки инструментов (опц.): tool_<id>.png 64x64. id:", ", ".join(TOOLS))
    print("Промпты для ComfyUI — в PROMPTS.md.")


# ----------------------------------------------------------------------------- #
#  Точка входа
# ----------------------------------------------------------------------------- #
def _install_crash_log():
    """exe без консоли: сбои пишем в crash.log рядом с сохранениями (и нативные падения — через faulthandler)."""
    if IS_WEB:
        return None
    import faulthandler, traceback, datetime
    try:
        f = open(os.path.join(DATA_DIR, "crash.log"), "a", encoding="utf-8")
        f.write(f"\n=== запуск {datetime.datetime.now():%Y-%m-%d %H:%M:%S}, pygame {pygame.version.ver} ===\n")
        f.flush()
        faulthandler.enable(f, all_threads=True)

        def hook(t, v, tb):
            f.write("".join(traceback.format_exception(t, v, tb)))
            f.flush()
            sys.__excepthook__(t, v, tb)
        sys.excepthook = hook
        return f
    except Exception:
        return None


_LOOP_ERR = []


def _loop_error(game, log):
    """Ошибка в кадре — игру не роняем: в браузере исключение навсегда замораживало холст («игра зависла»).
    Трейс — в консоль и crash.log; окна задания закрыты, игрок — в мастерскую (часто повторяется — на титул)."""
    import time as _time, traceback
    tb = traceback.format_exc()
    print(tb, flush=True)
    if log:
        try:
            log.write(tb)
            log.flush()
        except Exception:
            pass
    now = _time.time()
    _LOOP_ERR[:] = [t for t in _LOOP_ERR if now - t < 10] + [now]
    try:
        game.mini_pending = game.spec_pending = None
        game.v3d = None
        game.show_manual = game.show_sound = False
        game.dispute_ui = None
        game.ride_t0 = None
        game.scene = "hub" if (len(_LOOP_ERR) <= 3 and game.tutorial_ok()) else "title"
        game.flash("Что-то пошло не так — вернулись назад. Прогресс сохранён.", BAD, 5)
    except Exception:
        pass


async def main():
    _crash_log = _install_crash_log()
    if IS_WEB:
        web_restore()
        web_setup_page()
        web_setup_touch()
        DISPLAY["web_px"] = web_measure()             # «авто»: холст сразу под окно игры на странице
        try:
            with open(SETTINGS_PATH, encoding="utf-8-sig") as f:
                st0 = json.load(f)
            if st0.get("web_quality") in WEB_RES and st0.get("web_quality_user"):   # свой выбор игрока
                DISPLAY["web_quality"] = st0["web_quality"]
                DISPLAY["web_quality_user"] = True
        except Exception:
            pass
        if FEEDBACK_URL:
            web_js(f"window.wnbFlush && wnbFlush({json.dumps(FEEDBACK_URL)})")
    elif FEEDBACK_URL and not any(a in sys.argv for a in ("--selftest", "--assets", "--feedback")):
        threading.Thread(target=feedback_flush_outbox, daemon=True).start()   # досылка — только в настоящей игре
    if "--assets" in sys.argv:
        print_assets()
        return
    if "--selftest" in sys.argv:
        run_selftest()
        return
    if "--feedback" in sys.argv:                            # замечания «Я не согласен» от игроков
        try:
            with open(FEEDBACK_PATH, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception:
            data = []
        data = [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []
        print(f"Файл: {FEEDBACK_PATH}  — замечаний: {len(data)}")
        for e in data:
            print()
            print(f"[{e.get('time')}] {e.get('job')} «{e.get('title')}» — {e.get('reason')}")
            if e.get("step"):
                print("  шаг:", e["step"])
            if e.get("expected") or e.get("got"):
                print("  ожидалось:", e.get("expected"), "| выбрано:", e.get("got"))
            if e.get("comment"):
                print("  комментарий:", e["comment"])
        return
    if "--reset" in sys.argv and os.path.exists(SAVE_PATH):
        os.remove(SAVE_PATH)
        print("Сохранение удалено, начинаем заново.")
    dpi_aware()
    if not IS_WEB:                                      # в браузере микшер уже открыт в main.py
        pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pad_init()
    if "--mute" not in sys.argv:
        build_sounds()
    set_lang(LANG["code"])
    global RS
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
            st_ = json.load(f)
    except Exception:
        st_ = {}
    if not isinstance(st_, dict):                         # старый/испорченный settings.json — как будто его нет
        st_ = {}
    want_full = st_.get("fullscreen") is True and not IS_WEB
    if "--window" in sys.argv:
        want_full = False
    res_ = st_.get("res")
    if (not IS_WEB and isinstance(res_, (list, tuple)) and len(res_) == 2
            and all(isinstance(x, int) and not isinstance(x, bool) and 320 <= x <= 16384 for x in res_)):
        DISPLAY["res"] = tuple(res_)
    GL["off"] = "--nogl" in sys.argv or bool(os.environ.get("WNB_NOGL")) or st_.get("gpu3d") is False
    if "--rs" in sys.argv[:-1]:                               # ручной масштаб = разрешение 1280*N × 720*N
        try:
            k_ = max(1.0, min(3.0, float(sys.argv[sys.argv.index("--rs") + 1])))
            DISPLAY["res"] = (round(WIDTH * k_), round(HEIGHT * k_))
        except ValueError:
            print("--rs: нужно число, например --rs 1.5")
    init_display(want_full)
    if _crash_log:                                          # какой 3D-рендер включился — в журнал запуска
        try:
            info = GL["ctx"].info["GL_RENDERER"] if gl_ok() else ("выключен" if GL["off"] else "недоступен")
        except Exception:
            info = "ошибка"
        _crash_log.write(f"RS {RS}, 3D: GPU {info}" + chr(10))
        _crash_log.flush()
    clock = pygame.time.Clock()
    game = Game()
    if _crash_log and A11Y["on"]:                         # какой голос у озвучки — тоже в журнал
        _crash_log.write(f"озвучка: {SPEECH.kind} {SPEECH.name}" + chr(10))
        _crash_log.flush()
    if "--unlock" in sys.argv:   # предпросмотр: всё открыто, включая Гильдию; сохранение не трогаем
        game.done.update(j["id"] for j in JOBS)
        game.no_save = True
        print("[wnb] --unlock: прогресс не сохраняется", flush=True)
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        try:
            evs = pygame.event.get()
            has_finger = any(e.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION) for e in evs)
            for event in evs:
                if event.type == pygame.QUIT:
                    running = IS_WEB                              # в браузере «выход» некуда — остаёмся в игре
                elif event.type == pygame.VIDEORESIZE:            # окно растянули/развернули — масштаб пересчитаем чуть позже
                    DISPLAY["resize_at"] = pygame.time.get_ticks()
                else:
                    fe = finger_events(event, has_finger)
                    if fe is not None:                            # касания: уже в логических координатах
                        for e in fe:
                            game.handle_event(e)
                        continue
                    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                        d = dict(event.dict)
                        d["pos"] = window_to_logical(d["pos"])
                        v = DISPLAY.get("view")
                        if "rel" in d and v:
                            d["rel"] = (d["rel"][0] * WIDTH / v.w, d["rel"][1] * HEIGHT / v.h)
                        event = pygame.event.Event(event.type, d)
                    game.handle_event(event)
            if DISPLAY.get("resize_at") and pygame.time.get_ticks() - DISPLAY["resize_at"] > 350:
                DISPLAY["resize_at"] = None
                _update_rs()
            if DISPLAY.pop("rs_changed", False):
                game.m3d = None
                game._fade_from = game._last_frame = None
            game.update(dt)
            game.draw(DISPLAY["frame"])                    # кадр пересоздаётся при смене разрешения
            present(DISPLAY["frame"])
            pygame.display.flip()
            if IS_WEB:
                DISPLAY["_px_t"] = DISPLAY.get("_px_t", 0) + dt
                if DISPLAY["_px_t"] > 1 and DISPLAY.get("web_quality", "auto") == "auto":   # окно игры поменялось?
                    DISPLAY["_px_t"] = 0
                    web_auto_resize(web_measure())
                DISPLAY["_st_t"] = DISPLAY.get("_st_t", 0) + dt
                if DISPLAY["_st_t"] > 0.5:                # состояние для автопроверки (art_tests/web_smoke.py)
                    DISPLAY["_st_t"] = 0
                    web_js("window.wnbState=" + json.dumps(json.dumps(game.debug_state())))
                DISPLAY["_fps_t"] = DISPLAY.get("_fps_t", 0) + dt
                if DISPLAY["_fps_t"] > 3:                 # окно замера 3 с
                    DISPLAY["_fps_t"] = 0
                    fps = clock.get_fps()
                    print(f"[wnb] fps {fps:.1f} rs {RS} px {DISPLAY.get('web_px')} scene {game.scene}", flush=True)
                    slow = fps < 20 and game.scene in ("job", "hub", "seating", "guild")
                    DISPLAY["_slow"] = DISPLAY.get("_slow", 0) + 1 if slow else 0
                    cw = (DISPLAY.get("res") or WEB_RES["standard"])[0]
                    lower = [i for i, k in enumerate(WEB_LEVELS) if WEB_RES[k][0] < cw]   # ступени меньше нынешнего холста
                    if DISPLAY["_slow"] >= 2 and DISPLAY.get("web_quality", "auto") == "auto" and lower:
                        DISPLAY["web_cap"] = lower[-1]         # слабый ПК: холст не больше этой ступени
                        DISPLAY["_slow"] = 0
                        apply_display()
                        game.flash("Качество снижено для плавности. Настройки → Графика.", AMBER, 5)
        except Exception:
            _loop_error(game, _crash_log)
        await asyncio.sleep(0)                        # браузеру — нарисовать кадр и принять ввод
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
