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
import json
import math
import os
import sys
import random
import re
import pygame

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


class LFont:
    """Шрифт: рендер нужного размера в пикселях экрана, метрики — в логических."""

    def __init__(self, size, bold=False):
        self.f = pygame.font.SysFont("dejavusans,arial,helvetica", max(1, round(size * RS)), bold=bold)
        self._cache = {}

    def render(self, text, aa=True, color=(255, 255, 255), bg=None):
        key = (text, aa, tuple(color), None if bg is None else tuple(bg))
        img = self._cache.get(key)
        if img is None:
            real = self.f.render(text, aa, color, bg) if bg is not None else self.f.render(text, aa, color)
            img = Surf.adopt(real)
            if len(self._cache) > 1500:
                self._cache.clear()
            self._cache[key] = img
        img.set_alpha(255)              # без копии: вызывающие ставят set_alpha сразу перед blit, сбрасываем здесь
        return img

    def size(self, text):
        w, h = self.f.size(text)
        return (math.ceil(w / RS), math.ceil(h / RS))

    def get_height(self):
        return math.ceil(self.f.get_height() / RS)

    def get_linesize(self):
        return math.ceil(self.f.get_linesize() / RS)

    def __getattr__(self, name):
        return getattr(self.f, name)


def mouse_pos():
    """Мышь в логических координатах 1280x720."""
    x, y = pygame.mouse.get_pos()
    return (int(x / RS), int(y / RS))


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
    img = _aa_cached(("rr", rr.w, rr.h, col, wd, rad), rr.size,
                     lambda b, s: pygame.draw.rect(b, col, b.get_rect(), wd * s, border_radius=rad * s))
    pygame.Surface.blit(surf, img, rr.topleft)
    return r


def aa_circle(surf, color, center, radius, width=0, **kw):
    """Круг со сглаживанием: заливка/тонкое кольцо — gfxdraw, толстое кольцо — супер-сэмплинг."""
    k = _rs(surf)
    x, y, r = int(round(center[0] * k)), int(round(center[1] * k)), int(round(radius * k))
    wd = _w(width, k)
    if r <= 0 or kw or _gfx is None:
        return DR.circle(surf, color, center, radius, width, **kw)
    col = tuple(int(c) for c in color)
    if wd <= 0 or wd >= r:
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
    LANG["code"] = code if code in ("ru", "en") else "ru"
    if LANG["code"] == "en" and not _TR:
        load_lang()
    _tool_icon_cache.clear()
    try:
        pygame.display.set_caption(tr("Колёса и Кости") if LANG["code"] == "en" else "Колёса и Кости // Wheels & Bones")
    except Exception:
        pass


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


def draw_text(surf, text, pos, size=18, color=WHITE, bold=False, center=False, right=False, alpha=255):
    img = font(size, bold).render(tr(str(text)), True, color)
    if alpha < 255:
        img.set_alpha(max(0, int(alpha)))
    rect = img.get_rect()
    if center:
        rect.center = pos
    elif right:
        rect.topright = pos
    else:
        rect.topleft = pos
    surf.blit(img, rect)
    return rect


def fit_text(surf, text, pos, width, size=18, color=WHITE, bold=False):
    """Строка в заданную ширину: уменьшаем шрифт (до 75%), иначе обрезаем с «…»."""
    text = tr(str(text))
    sz = size
    while sz > int(size * 0.75) and font(sz, bold).size(text)[0] > width:
        sz -= 1
    f = font(sz, bold)
    if f.size(text)[0] > width:
        while text and f.size(text + "…")[0] > width:
            text = text[:-1]
        text = text.rstrip() + "…"
    return draw_text(surf, text, (pos[0], pos[1] + (size - sz) // 2), sz, color, bold)


def wrap_lines(text, width, size=16):
    text = tr(text)
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
                 limit=None, alpha=255, max_lines=None):
    """limit — сколько символов показать («печать по буквам»): переносы считаются по
    полному тексту, поэтому слова не прыгают между строками во время печати."""
    x, y = pos
    f = font(size)
    text = tr(text)
    left = len(text) if limit is None else limit
    lines = wrap_lines(text, width, size)
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
            img = f.render(ln[:left], True, color)
            if alpha < 255:
                img.set_alpha(max(0, int(alpha)))
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


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_back(x, s=1.70158):
    """С лёгким перелётом — для «выпрыгивающих» элементов."""
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
        dy = 7 * math.sin(t * 1.6 + phase)
        ang = 2.5 * math.sin(t * 1.1 + phase) + rock
        out = TF.rotozoom(img, ang, k) if (ang or k != 1) else img
        surf.blit(out, out.get_rect(center=(pos[0] + w // 2, pos[1] + h // 2 + dy)))
        return
    if k != 1 or rock:
        img = TF.rotozoom(img, rock, k)
        surf.blit(img, img.get_rect(midbottom=(pos[0] + w // 2, pos[1] + h)))
        return
    cut = int(h * 0.55)
    sy = 1 + 0.014 * math.sin(t * 2.1 + phase)
    surf.blit(img, (pos[0], pos[1] + cut), pygame.Rect(0, cut, w, h - cut))
    th = int(cut * sy)
    surf.blit(TF.smoothscale(img.subsurface((0, 0, w, cut)), (w, th)),
              (pos[0], pos[1] + cut - th))


def draw_spin_wheel(surf, center, r, ang, k=1.0, col=(205, 210, 225)):
    """Вращающееся колесо коляски (для титула): шина, обод, спицы, ступица."""
    if k <= 0.01:
        return
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
    if not 0 < ph < 1:
        return
    for i in range(n):
        a = i * 2 * math.pi / n + 0.3
        d = dist * ease_out(ph)
        add_glow(surf, (center[0] + d * math.cos(a), center[1] + d * math.sin(a)), 8, color, 1 - ph)


def draw_ambient(surf, name, t):
    """Частицы поверх фона: у каждой сцены своя жизнь."""
    if not DISPLAY["glow"]:
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


def load_image(name, size=None, color=GHOST):
    key = (name, size)
    if key in _img_cache:
        return _img_cache[key]
    path = os.path.join(ASSETS_DIR, name)
    surf = None
    if os.path.exists(path):
        try:
            real = pygame.image.load(path).convert_alpha()
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
        if os.path.exists(os.path.join(ASSETS_DIR, name)):
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
    """Сценка с ногой в полосе rect; t — время сценки (петля ~4.6 с)."""
    P = 4.6
    u = t % P
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
READ_TOOLS = {"gauge", "multimeter", "tensiometer", "dial", "tape"}


def draw_tool_action(surf, tid, pos, u, ok=True):
    """Инструмент работает на детали: u — 0..1 время анимации."""
    x, y = pos
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
        bub = pygame.Rect(x + 24, y - 54, 86, 26)
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
DISPLAY = {"fullscreen": False, "glow": True}     # сохраняется в settings.json; glow — свечение и частицы


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


def init_display(fullscreen=False):
    """Окно игры: кадр рисуется в WIDTH*RS x HEIGHT*RS (разрешение экрана), SDL выводит его в окно
    (SCALED: поля без искажений, окно можно тянуть). В окне — 85% монитора; F11 — пиксель в пиксель."""
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")        # плавное (не «пиксельное») масштабирование
    size = (round(WIDTH * RS), round(HEIGHT * RS))
    try:
        screen = pygame.display.set_mode(size, pygame.SCALED | pygame.RESIZABLE)
    except pygame.error:
        screen = pygame.display.set_mode(size)
    try:                                                # окно не больше 85% экрана
        dw, dh = pygame.display.get_desktop_sizes()[0]
        k = min(1.0, 0.85 * dw / size[0], 0.85 * dh / size[1])
        if k < 1.0:
            try:
                win = pygame.Window.from_display_module()           # pygame-ce
            except Exception:
                from pygame._sdl2.video import Window               # pygame 2
                win = Window.from_display_module()
            win.size = (round(size[0] * k), round(size[1] * k))
            win.position = ((dw - win.size[0]) // 2, (dh - win.size[1]) // 2)
            DISPLAY["win"] = win        # ВАЖНО: держать ссылку. SDL хранит указатель на этот объект в окне,
                                        # и если он умрёт, оконные события pygame обратятся к освобождённой памяти
    except Exception:
        pass
    if fullscreen:
        toggle_fullscreen()
    return screen


def toggle_fullscreen():
    """Полный экран <-> окно (F11, Alt+Enter, кнопка в настройках)."""
    try:
        pygame.display.toggle_fullscreen()
        DISPLAY["fullscreen"] = not DISPLAY["fullscreen"]
    except pygame.error:
        pass
    return DISPLAY["fullscreen"]


VOL = {"master": 0.8, "music": 0.55, "sfx": 0.9, "amb": 0.45, "on": True}   # сохраняется в settings.json
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
MUSIC = {"cur": None, "next": None, "at": 0.0}       # фоновая музыка: текущая тема и отложенный старт


def _amb_level():
    return VOL["master"] * VOL["amb"] if VOL["on"] else 0.0


def _music_level():
    return VOL["master"] * VOL["music"] if VOL["on"] else 0.0


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
    """Сменить тему с плавным переходом: старая гаснет, новая вступает чуть позже."""
    try:
        if not pygame.mixer.get_init():
            return
        if theme != MUSIC["cur"] and theme != MUSIC["next"]:
            MUSIC["next"] = theme
            MUSIC["at"] = now + (0.8 if MUSIC["cur"] else 0.0)
            pygame.mixer.music.fadeout(700)
        if MUSIC["next"] is not None and now >= MUSIC["at"]:
            MUSIC["cur"], MUSIC["next"] = MUSIC["next"], None
            path = music_path(MUSIC["cur"]) if MUSIC["cur"] else None
            if path:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(_music_level())
                pygame.mixer.music.play(loops=-1, fade_ms=1500)
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
    peak = max(1e-6, max(abs(v) for v in samples))
    k = vol / peak
    buf = array.array("h", (int(max(-1.0, min(1.0, v * k)) * 32767) for v in samples))
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


TOOL_SOUND = {"hands": "tool_soft", "cloth": "tool_soft", "brush": "tool_soft", "patch": "tool_soft",
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
    "chair_dwarf.png": (196, 120, 64), "chair_fairy.png": (236, 172, 200),
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
        m_box(m, 210, 236, 506, 532, bz - 10, bz + 16 * s, "brake", (90, 90, 100))
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
               "client_focuscr": "client_sorceress", "client_whillc2": "client_goblin", "client_f5": "client_troll"}.items():
    VECTOR_ART.setdefault(_k, VECTOR_ART[_v])
# точки клика реальных колясок — по их арту (art_tests/hotspots_<модель>.json)
CHAIR_HOTSPOTS["inv9000"] = {"tire": (90, 262, 12), "rim": (55, 150, 11), "spokes": (112, 202, 12), "tube": (132, 240, 10), "valve": (90, 128, 9), "brake": (150, 160, 10)}
CHAIR_HOTSPOTS["xdt"] = {"cushion": (190, 120, 14), "seat": (110, 150, 10), "frame": (200, 195, 11), "valve": (258, 128, 8)}
CHAIR_HOTSPOTS["ego"] = {"caster": (225, 265, 12), "caster_stem": (225, 228, 9), "bearing": (322, 232, 9), "bolts": (340, 182, 8), "brake": (215, 110, 9), "tire": (55, 240, 12)}
CHAIR_HOTSPOTS["tekna"] = {"tire": (30, 200, 11), "rear_wheel": (95, 205, 13), "brake": (175, 140, 10), "bolts": (205, 172, 8), "frame": (300, 130, 12)}
CHAIR_HOTSPOTS["exelle_jr"] = {"rim": (55, 140, 11), "spokes": (142, 202, 12), "bearing": (107, 175, 8), "tube": (140, 262, 10), "bolts": (275, 145, 8)}
CHAIR_HOTSPOTS["noir"] = {"axle": (125, 175, 9), "bearing": (150, 168, 8), "rear_wheel": (120, 240, 13), "tire": (55, 140, 11), "brake": (230, 145, 9)}
CHAIR_HOTSPOTS["edge4"] = {"joystick": (205, 62, 8), "controller": (230, 95, 9), "wiring": (200, 165, 8), "battery": (180, 222, 12), "fuse": (140, 240, 8), "motor": (228, 255, 10), "seat_lift": (224, 184, 11), "actuator": (180, 172, 9), "armrest": (150, 92, 10), "seat": (165, 128, 12), "freewheel": (206, 240, 8)}
CHAIR_HOTSPOTS["trident"] = {"controller": (160, 108, 10), "wiring": (185, 150, 9), "battery": (215, 190, 12), "freewheel": (130, 205, 9), "motor": (195, 225, 11), "axle": (160, 242, 9), "frame": (108, 168, 10)}
# точки клика M3 расставлены по арту assets/chair_m3.png (art_tests/hotspots_m3.json)
CHAIR_HOTSPOTS["m3"] = {"joystick": (222, 80, 11), "boot": (214, 98, 7), "controller": (242, 108, 12), "wiring": (190, 132, 11), "battery": (160, 232, 14), "fuse": (98, 222, 9), "motor": (196, 252, 12), "freewheel": (130, 212, 10), "axle": (166, 250, 12), "frame": (245, 205, 12)}
# вторая волна: точки клика по арту (art_tests/hotspots_<model>.json, build_new_assets.py)
CHAIR_HOTSPOTS["aeroz"] = {"tire": (55, 230, 11), "spokes": (90, 185, 11), "axle": (124, 207, 9), "brake": (205, 160, 10), "bolts": (232, 140, 8), "anti_tip": (42, 272, 9)}
CHAIR_HOTSPOTS["cross6"] = {"backrest": (160, 75, 13), "cushion": (215, 140, 12), "brake": (165, 168, 9), "bolts": (122, 196, 9), "tire": (78, 210, 11), "anti_tip": (100, 265, 9)}
CHAIR_HOTSPOTS["iris"] = {"anti_tip": (325, 262, 9), "tilt_cable": (300, 130, 9), "tilt_lock": (245, 195, 10), "tilt_lever": (322, 50, 9), "tire": (300, 282, 10), "brake": (283, 210, 9)}
CHAIR_HOTSPOTS["focuscr"] = {"tilt_lever": (80, 32, 9), "tilt_cable": (98, 122, 9), "gas_spring": (118, 160, 9), "brake": (150, 172, 9), "tilt_lock": (178, 210, 10), "anti_tip": (52, 265, 9)}
CHAIR_HOTSPOTS["whillc2"] = {"controller": (292, 72, 9), "joystick": (270, 46, 9), "armrest": (232, 118, 11), "seat": (178, 124, 11), "seat_cable": (195, 182, 9), "battery": (112, 186, 11), "freewheel": (36, 250, 9), "tire": (140, 272, 11)}
CHAIR_HOTSPOTS["f5"] = {"joystick": (140, 118, 9), "battery": (205, 192, 11), "motor": (150, 228, 11), "tire": (128, 272, 11), "freewheel": (200, 240, 9), "frame": (248, 222, 11), "breaker": (276, 214, 9)}


_CHAIR3D_CACHE = {}
# коляска -> детальная 3D-модель (assets/models/*.json; сейчас — art_tests/build_9_chairs.py, «Custom3D»;
# прежние ИИ-модели Pixal3D/Hunyuan3D — art_tests/models_bak_before_smooth). *_lod.json — облегчённая копия
# для окна диагностики.
AI_MODELS = {f"chair_{k}.png": f"chair_{k}_ai.json"
             for k in ("basic", "troll", "elf", "dwarf", "fairy", "orc", "edge4", "trident", "m3",
                       "aeroz", "cross6", "iris", "focuscr", "whillc2", "f5", "pulse6", "q6edge")}


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
uniform float hl_part; uniform vec3 hl_col; uniform float hl_amt;
uniform float hv_part; uniform float hv_amt;
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
    if (hl_amt > 0.0 && abs(v_part - hl_part) < 0.5) c = mix(c, hl_col, hl_amt);
    if (hv_amt > 0.0 && abs(v_part - hv_part) < 0.5) c = c * (1.0 + hv_amt);
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
        pr["hl_part"].value = float(names.index(hl_part)) if hl_part in names else -9.0
        pr["hl_col"].value = tuple(c / 255.0 for c in (hl_col or AMBER))
        pr["hl_amt"].value = float(hl_amt if hl_part in names else 0.0)
        pr["hv_part"].value = float(names.index(hover_part)) if hover_part in names else -9.0
        pr["hv_amt"].value = float(hover_amt if hover_part in names else 0.0)
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
    "hands":     ("Руки", "Снять/поставить, проверить рукой"),
    "allen":     ("Шестигранник", "Большинство болтов коляски (бери точный размер!)"),
    "socket":    ("Торцевой ключ", "Ось и гайки колеса"),
    "wrench":    ("Разводной ключ", "Подтянуть узлы, шток кастора"),
    "screw":     ("Отвёртка", "Винты (крест)"),
    "lever":     ("Монтажка", "Бортировать покрышку (нужны 2 шт.)"),
    "pump":      ("Насос", "Накачать камеру / шину / подушку"),
    "patch":     ("Заплатка", "Ремкомплект для прокола"),
    "lube":      ("Смазка", "Смазать ось/подшипник"),
    "brush":     ("Щётка/пинцет", "Вычистить волосы и грязь из оси"),
    "cloth":     ("Тряпка/салфетка", "Протереть, обезжирить"),
    "bucket":    ("Таз с водой", "Найти прокол по пузырькам"),
    "pencil":    ("Карандаш", "Пинг-тест спиц"),
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
    "bolts":      "Болты/гайки",
    "cushion":    "Подушка",
    "battery":    "Батарея",
    "controller": "Контроллер",
    "joystick":   "Джойстик",
    "boot":       "Пыльник джойстика",
    "wiring":     "Разъёмы/проводка",
    "fuse":       "Предохранитель",
    "motor":      "Мотор",
    "freewheel":  "Рычаг своб. хода",
}


def S(instr, tool, part, note="", ghost="", ghost_wrong=False, wrongmsg="", mini=None, alt=()):
    """Удобный конструктор шага ремонта.

    mini — необязательная мини-интеракция вместо мгновенного выполнения:
    dict(kind="pump"|"gap"|"ping"|"meter", ...) — см. Game.start_mini().
    alt — другие детали, которые тоже верны (насос к ниппелю И «к шине»: игроки думают по-разному).
    """
    return dict(instr=instr, tool=tool, part=part, note=note,
                ghost=ghost, ghost_wrong=ghost_wrong, wrongmsg=wrongmsg, mini=mini, alt=tuple(alt))


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
        "До любых работ: питание контроллера — ВЫКЛ.",
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
}

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
         story="Грунд сам не может переносить вес, а сидит весь день. Кто-то «разгружал» его, "
               "откидывая только спинку.",
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
         therapist="Активная посадка: глубина с зазором 5 см до подколенной ямки, спинка ниже лопаток "
                   "(31–37 см), угол спинки 91–97°.",
         back=(31, 37), angle=(91, 97),
         start=dict(depth=46, leg=45, back_h=42, back_a=103),
         fact="Зазор ~5 см (2 дюйма) от переднего края подушки до подколенной ямки защищает сосуды и нервы "
              "под коленом и не стягивает таз вперёд."),
    dict(id="seat_iris", client="Дракончик Искра", client_art="client_iris.png", kind="power",
         skin=(228, 108, 92), seat_h=46,
         body=dict(thigh=35, shank=32, scap=30, shoulder=44),
         story="Искра устаёт держать голову и заваливается вперёд, а при долгом сидении немеет крестец.",
         therapist="Нужна высокая опора спины (40–48 см), раскрытый угол 96–106° и разгрузочный наклон "
                   "(tilt) не меньше 45°.",
         back=(40, 48), angle=(96, 106), tilt=45,
         start=dict(depth=36, leg=27, back_h=33, back_a=90, tilt=15),
         fact="Наклон в пространстве (tilt-in-space) сохраняет углы в тазобедренных и коленных суставах, "
              "снимая нагрузку с таза и помогая удерживать голову и корпус."),
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
         points=["Перекос: одна сторона таза выше, корпус кренится, со временем — сколиоз.",
                 "Причины: провисшее или слишком широкое сиденье, низкая спинка, одна подножка "
                 "или разные по высоте, подлокотник не той высоты.",
                 "Боковые упоры ставят по схеме «три точки»: у вершины изгиба, под мышкой "
                 "(с зазором — там нервы) и низко у таза.",
                 "Поворот таза и «ветром сдутые» колени лечат контурами подушки, а не ремнями."],
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
         options=[("Подножка слишком высоко: колени выше бёдер", True, ""),
                  ("Сиденье слишком глубокое", False, "Глубина тут ни при чём — смотри на колени и бёдра."),
                  ("Спинка слишком низкая", False, "Спинка держит корпус, а проблема — в коленях.")]),
    dict(pose=dict(p=20, slide=7, deep=True), q="Почему клиент сползает и сидит на крестце?",
         options=[("Сиденье глубже нормы: край давит под колени", True, ""),
                  ("Слишком мягкий подголовник", False, "Подголовник не тянет таз вперёд."),
                  ("Подножка слишком короткая", False, "Тогда колени ушли бы вверх.")]),
    dict(pose=dict(dangle=True, slide=4, p=8), q="Стопы не достают до подножки. Что поправить?",
         options=[("Поднять подножку (укоротить) — стопы должны стоять", True, ""),
                  ("Откинуть спинку", False, "Откинутая спинка сползание только усилит."),
                  ("Сузить сиденье", False, "Ширина не влияет на опору стоп.")]),
    dict(pose=None, q="Можно ли посадить всех по правилу «90-90-90»?",
         options=[("Нет: универсального рецепта нет, решают по осмотру и цели", True, ""),
                  ("Да, это стандарт для всех", False, "Руководство прямо говорит: готового рецепта нет."),
                  ("Да, но только детей", False, "Для детей тоже решают индивидуально.")]),
    dict(pose=dict(tilt=45), q="Клиент не может сам перенести вес. Как разгрузить таз?",
         options=[("Наклонить сиденье (tilt) не меньше чем на 45°", True, ""),
                  ("Только откинуть спинку", False, "Откидывание без наклона усиливает сдвиг тканей."),
                  ("Поднять подножки повыше", False, "Подъёмные подножки тянут таз назад, на крестец.")]),
    dict(pose=dict(front=True), q="Где ставят боковые упоры при сколиозе?",
         options=[("В три точки: вершина изгиба, под мышкой с зазором, низко у таза", True, ""),
                  ("Вплотную в подмышку — так надёжнее", False, "Под мышкой оставляют зазор: там нервы."),
                  ("Только один упор на вершине изгиба", False, "Одна точка не удержит изгиб.")]),
]
SEAT_QUIZ_PASS = 5

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
            D("Прокол камеры — снять покрышку, заменить/заклеить камеру", True),
            D("Погнут обод", False, "Обод ровный. Гнётся он редко и от сильного удара."),
            D("Ослаб тормоз-замок", False, "Тормоз не влияет на спущенное колесо."),
        ],
        steps=[
            S("Полностью спусти остатки воздуха через ниппель.", "hands", "valve",
              "Со спущенной камерой покрышку снять легко.",
              "Барти: «Мастер всегда сначала выпускал дух из колеса. Торжественно.»"),
            S("Поддень борт покрышки монтажкой над спицей, зацепи крючок за спицу.", "lever", "tire",
              "Монтажки пластиковые — держи у конца, легко ломаются.",
              "Барти: «Двумя ложками для обуви он это делал! ...или нет.»", ghost_wrong=True,
              wrongmsg="Камеру/покрышку поддевают монтажкой, а не ключом."),
            S("Второй монтажкой пройди по кругу — сними один борт с обода.", "lever", "tire",
              "Снимаем только один борт, второй оставляем на ободе."),
            S("Вынь камеру из покрышки.", "hands", "tube",
              "Аккуратно, чтобы не зацепить ниппель."),
            S("Проведи пальцем внутри покрышки и по ободу — убери стекло/занозы.", "hands", "tire",
              "Пропустишь осколок — новая камера проколется сразу.",
              "Барти: «О, это я помню — он тут однажды нашёл монетку. Богатей.»"),
            S("Чуть подкачай новую камеру через ниппель, чтобы держала круглую форму.", "pump", "tube",
              "Полуспущенная камера легче и ровнее ложится в покрышку."),
            S("Вставь камеру, ниппель проведи в отверстие обода.", "hands", "valve", ""),
            S("Заправь борт покрышки руками от ниппеля по кругу.", "hands", "tire",
              "Последний участок дожми монтажкой, не прищеми камеру."),
            S("Проверь, что ниппель стоит перпендикулярно, не косо.", "hands", "valve",
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
                    "caster_stem": "Шток кастора болтается — есть люфт.",
                    "tire": "Задняя шина накачана нормально.",
                    "brake": "Тормоз держит.",
                    "bearing": "Задний подшипник тихий.",
                },
                diagnosis=[
                    D("Люфт штока кастора + грязь/волосы в оси", True),
                    D("Ослабли болты крепления вилки", False, "Вилка сидит плотно — играет сам шток."),
                    D("Спустила задняя шина", False, "Шина в норме. Тряску даёт перёд."),
                ],
                steps=[
                    S("Сними колесо кастора с вилки.", "allen", "caster",
                      "Обычно держится на одном болте."),
                    S("Вычисти волосы и грязь из оси кастора пинцетом/щёткой.", "brush", "caster",
                      "Намотанные волосы — частая причина, что кастор не крутится свободно.",
                      "Барти: «Волос там — будто кто-то линял веками. Ах да, это я.»"),
                    S("Проверь, свободно ли крутится кастор; бьёт/изношен — под замену.", "hands", "caster",
                      "Признаки замены: тёрта резина, вихляет при вращении, не крутится свободно."),
                    S("Подтяни узел подшипника штока кастора до лёгкого трения.", "wrench", "caster_stem",
                      "Чуть больше трения в штоке гасит флаттер.",
                      "Барти: «Туже! Ещё туже! ...хотя нет, он потом ругался, что закусило.»", ghost_wrong=True,
                      wrongmsg="Шток кастора подтягивают ключом, не голыми руками."),
                    S("Поставь колесо обратно, проверь — крутится свободно, без люфта.", "allen", "caster",
                      "Перетянешь крепление — колесо застопорится."),
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
                    "caster": "Колесо цело и крутится, но вся вилка ходит ходуном.",
                    "caster_stem": "Шток не люфтит — играет само крепление вилки.",
                    "bolts": "Болты крепления вилки кастора заметно ослабли.",
                    "tire": "Задняя шина в норме.",
                    "bearing": "Подшипники тихие.",
                },
                diagnosis=[
                    D("Ослабли болты крепления вилки кастора", True),
                    D("Люфт штока + волосы в оси", False, "Шток плотный, ось чистая — дело не в них."),
                    D("Спустила задняя шина", False, "Шина в норме. Тряску даёт перёд."),
                ],
                steps=[
                    S("Покачай вилку кастора рукой — найди люфт.", "hands", "caster",
                      "Вилка шатается на целом штоке — значит, крепёж."),
                    S("Подтяни болты крепления вилки.", "allen", "bolts",
                      "Шестигранник — точно по размеру: слизанный болт потом высверливают.",
                      "Барти: «Постучи молотком, само сядет!» — нет. Только ключ.", ghost_wrong=True),
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

    # === 2. Гном: тормоз не держит ===
    dict(
        id="brake", kind="manual", client="Гном Дургин", client_art="client_dwarf.png", chair_art="chair_dwarf.png",
        chair_model="tekna", chair_name="Progeo Tekna Advance (складная активная)",
        title="Тормоз-замок не держит",
        symptom="Тяжёлый гном жалуется: коляска скатывается с горки даже с зажатым тормозом.",
        parts=["brake", "tire", "frame", "bolts", "rear_wheel"],
        inspect={
            "tire": "Задняя шина приспущена — это уже подозрительно.",
            "brake": "Упор тормоза не достаёт до шины как надо; крепление чуть съехало.",
            "frame": "Рама целая.",
            "bolts": "Болты хомута тормоза слегка ослабли.",
            "rear_wheel": "Колесо крутится свободно.",
        },
        diagnosis=[
            D("Сначала проверить давление в шине, затем крепление тормоза", True),
            D("Сразу менять весь тормозной узел", False, "Сперва простые причины: давление и крепёж."),
            D("Погнута рама", False, "Рама в порядке."),
        ],
        steps=[
            S("Проверь давление в шине — спущенная шина «уводит» упор тормоза.", "gauge", "tire",
              "Первая причина «замок не держит» — низкое давление в шине.",
              "Барти: «Сразу болты крути!» ...а вот и нет — сначала давление.", ghost_wrong=True),
            S("Подкачай шину через ниппель до нормы.", "pump", "tire", ""),
            S("Проверь болты механизма на люфт и подтяни, если болтаются.", "allen", "brake",
              "Не перетягивай — замок станет туго включаться."),
            S("Не помогло — ослабь два болта хомута, крепящего замок к раме.", "allen", "brake",
              "Хомут даст сдвинуть весь узел."),
            S("Сдвинь замок ближе к шине в рабочее положение.", "hands", "brake",
              "В зажатом виде упор должен плотно прижимать шину."),
            S("Затяни болты хомута, чередуя их (симметрично).", "allen", "brake",
              "Симметричная затяжка держит узел ровно."),
            S("Проверь зазор: в отпущенном виде 3–6 мм между упором и шиной.", "hands", "brake",
              "Это 1/8–1/4 дюйма — рабочий зазор по мануалу.",
              mini=dict(kind="gap", lo=3, hi=6, mn=0, mx=12, unit="мм", start=9,
                        label="Зазор упор—шина",
                        hint="Рабочий зазор по мануалу: 3–6 мм в отпущенном виде",
                        fb_lo="Меньше 3 мм: упор будет тереть шину на каждом обороте.",
                        fb_hi="Больше 6 мм: замок не дожмёт шину и не удержит коляску.")),
        ],
        test="Гном жмёт тормоз и наваливается — колесо не проворачивается. Держит!",
        fact="«Замок не держит» чаще всего лечится давлением в шине и подтяжкой/сдвигом крепления. "
             "Бери шестигранник ТОЧНО по размеру: сорванный болт потом высверливают.",
        thanks="Дургин: «Вот это по-нашему, по-гномьи. Крепко!»",
    ),

    # === 3. Фея: ослабли спицы и болты ===
    dict(
        id="spokes", kind="manual", client="Фея Тилли", client_art="client_fairy.png", chair_art="chair_fairy.png",
        chair_model="exelle_jr", chair_name="Progeo Exelle Junior (детская)",
        title="Дребезг: ослабли спицы",
        symptom="На ходу что-то дребезжит, заднее колесо чуть «восьмерит» — крошечная фея переживает.",
        parts=["spokes", "rim", "bolts", "bearing", "tube"],
        inspect={
            "spokes": "Пара спиц на ощупь мягче соседних — ослабли.",
            "rim": "Обод гуляет на доли миллиметра — лёгкая «восьмёрка».",
            "bolts": "Несколько болтов на раме подразболтались.",
            "bearing": "Подшипник тихий — звук именно дребезжащий, не воющий.",
            "tube": "Камера держит давление.",
        },
        diagnosis=[
            D("Ослабли спицы (и заодно проверить болты)", True),
            D("Умер подшипник", False, "Подшипник даёт вой/стук, а тут именно дребезг."),
            D("Спустила камера", False, "Камера в норме."),
        ],
        steps=[
            S("Пинг-тест: проведи карандашом по спицам, вращая колесо.", "pencil", "spokes",
              "Звонкий «пинь» = норма, глухой звук = спица ослабла. (Можно сжимать соседние спицы парами.)",
              "Барти: «Музыкально! Он так целые мелодии наигрывал. Плохие.»",
              mini=dict(kind="ping", total=12, dull=3)),
            S("Найди ослабшие спицы по глухому звуку.", "hands", "spokes", ""),
            S("Подтяни ниппели ослабших спиц понемногу спицевым ключом.", "spoke_key", "spokes",
              "По чуть-чуть и равномерно: спицы тянут до нужного момента, профи — на спец-станке.",
              "Барти: «Крути от души, на пол-оборота за раз... ладно, по чуть-чуть.»"),
            S("Проверь и подтяни ослабшие болты/гайки на коляске.", "allen", "bolts",
              "Сорванный болт меняют на такой же по классу прочности (число на головке)."),
        ],
        test="Катишь колесо — дребезг ушёл, обод идёт ровно.",
        fact="Натяжение спиц проверяют пинг-тестом. Тянут до определённого момента и равномерно — "
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
                    D("Спустила шина", False, "Шина в порядке."),
                ],
                steps=[
                    S("Сними заднее колесо: нажми кнопку быстросъёмной оси и потяни.", "hands", "axle",
                      "Quick-release: кнопка в торце оси освобождает колесо."),
                    S("Вычисти волосы/грязь из оси и подшипника пинцетом/щёткой.", "brush", "bearing",
                      "Шерсть на оси — частый источник воя и тугого хода.",
                      "Барти: «У орка там... не спрашивай. Просто чисти.»"),
                    S("Оцени подшипник: стук/вой/заедание = под замену.", "hands", "bearing",
                      "Звук — первый признак умирающего подшипника."),
                    S("Замени подшипник, раз он шумит и заедает.", "socket", "bearing",
                      "Изношенный подшипник не лечится — только замена."),
                    S("Слегка смажь и поставь колесо обратно.", "lube", "axle",
                      "НЕ мой коляску мойкой высокого давления — выбьет смазку из закрытых подшипников, пойдёт ржавчина.",
                      "Барти: «Полей маслом всё подряд!» — нет, смазка только по делу.", ghost_wrong=True),
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
                    D("Подшипник оси изношен", False, "Подшипник тихий и ровный. Звук снаружи, у шины."),
                    D("Спустила шина", False, "Шина накачана."),
                ],
                steps=[
                    S("Ослабь два болта хомута тормоза.", "allen", "brake",
                      "Хомут даёт сдвинуть весь узел по раме."),
                    S("Сдвинь замок от шины в рабочее положение.", "hands", "brake",
                      "В отпущенном виде упор не должен касаться шины.",
                      "Барти: «Может, просто снять тормоз совсем?» — и катиться с горки без него? Нет.",
                      ghost_wrong=True),
                    S("Затяни болты хомута, чередуя их.", "allen", "brake",
                      "Симметричная затяжка держит узел ровно."),
                    S("Выставь зазор между упором и шиной.", "hands", "brake",
                      "Рабочий зазор — 3–6 мм: не трёт, но хватает при зажатии.",
                      mini=dict(kind="gap", lo=3, hi=6, mn=0, mx=12, unit="мм", start=1,
                                label="Зазор упор—шина",
                                hint="Рабочий зазор по мануалу: 3–6 мм в отпущенном виде",
                                fb_lo="Всё ещё трёт: меньше 3 мм — шина и силы уходят в звук.",
                                fb_hi="Больше 6 мм: замок не дожмёт шину и не удержит коляску.")),
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
            D("Провисла стропа сиденья", False, "Стропа в норме; провал — из-за сдутой подушки."),
            D("Ослабла спинка", False, "Спинка тут ни при чём."),
        ],
        steps=[
            S("Перекачай подушку через клапан — надуй сильнее обычного.", "pump", "cushion",
              "Перекачанную легче проверить на прокол."),
            S("Погрузи подушку в таз с водой и найди прокол по пузырькам.", "bucket", "cushion",
              "Пузырьки укажут точное место утечки.",
              "Барти: «Топи её! ...в хорошем смысле, для диагностики.»"),
            S("Отметь прокол (зубочистка/маркер).", "hands", "cushion", ""),
            S("Просуши и обезжирь место заплатки салфеткой.", "cloth", "cushion",
              "Заплатка держится только на чистой сухой поверхности."),
            S("Наклей заплатку из ремкомплекта и прижми.", "patch", "cushion",
              "В комплекте ROHO всегда есть заплатка."),
            S("Накачай через клапан до правильного уровня: ~палец воздуха до дна под костями таза.", "pump", "cushion",
              "«Пробивание» подушки до дна = риск пролежней. Зазор ~1 палец обязателен.",
              "Барти: «Дуй до звона!» — нет, тут наоборот, перекачивать вредно.", ghost_wrong=True),
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
    dict(
        id="lift", kind="power", client="Гоблин-механик Зикс",
        client_art="client_goblin.png", chair_art="chair_edge4.png",
        chair_model="edge4", chair_name="Quantum Edge 4 (средний привод, электролифт сиденья)",
        title="Не поднимается лифт сиденья",
        symptom="Зикс выбирает на пульте режим подъёма, толкает джойстик вперёд — а сиденье ни с места. "
                "«Я ж его только чуток улучшил! Ну, может, не чуток. Мне до верхней полки с гайками "
                "дотянуться надо, а лифт бастует!»",
        # source: E4 p9 — сиденье можно наклонить/откинуть до 20° при работающем iLevel;
        # source: TB4 p6 — до 12 in (30,5 см) подъёма; TB4 p7 — поднятое сиденье = 1/4 скорости
        fact="Электролифт Quantum поднимает сиденье до 30,5 см (12 дюймов), но только на ровном полу: "
             "в поднятом положении коляска едет примерно на четверти скорости. Блокировки подъёма и хода "
             "ставит завод — их не обходят и не перепрограммируют.",
        variants=[
            # --- А: разъём актуатора недовставлен после «улучшения» (подстаканник Зикса) ---
            dict(
                parts=["seat_lift", "actuator", "wiring", "controller", "battery", "armrest"],
                inspect={
                    "seat_lift": "Ножницы подъёмника сложены, чистые, ничего между ними не застряло.",
                    "actuator": "Корпус актуатора цел. Но его разъём у электроблока вытянут на полпальца — "
                                "защёлка не держит.",
                    "wiring": "Жгут лифта перетянут новыми стяжками к самодельному подстаканнику и на изгибе "
                              "прижат рамой сиденья. Оплётка пока цела.",
                    "controller": "Экран сиденья открывается, режим подъёма выбирается, кодов ошибок нет. "
                                  "Индикатор блокировки — зелёный.",
                    "battery": "Индикатор заряда полный — Зикс заряжал всю ночь.",
                    "armrest": "На подлокотнике — новенький подстаканник «Зикс-Турбо», прикручен крепко.",
                },
                diagnosis=[
                    D("Сигнал не доходит до актуатора: разъём недовставлен, жгут прижат — обесточить, "
                      "вставить до щелчка, переложить жгут", True),
                    D("Сработала заводская блокировка подъёма", False,
                      "При блокировке индикатор был бы красным или жёлтым, а он зелёный."),
                    D("Разряжена батарея", False,
                      "Заряд полный, и при разряде Q-Logic 3 показал бы ошибку 20 «Undervoltage»."),
                ],
                steps=[
                    # source: E4 p9 — только ровный пол в помещении; не под столом; держать зону свободной
                    S("Поставь коляску на ровный пол в мастерской: над сиденьем ничего, рядом с ножницами пусто.",
                      "hands", "seat_lift",
                      "Мануал Edge 4: лифт — только на ровной поверхности, не под столом или полкой."),
                    # source: QL3 p8 — кнопка key 2 сразу открывает экран сиденья; джойстик влево/вправо — выбор
                    # source: QL3 p8 — зелёный: без ограничений, жёлтый: лифт снижает скорость, красный: блокировка
                    # source: QL3 p10 — выбрать режим подъёма, дать джойстик вперёд
                    S("Включи контроллер, нажми кнопку key 2 (экран сиденья), выбери «подъём» и дай джойстик вперёд.",
                      "hands", "controller",
                      "Сначала читаем пульт — он подскажет, блокировка это или обрыв.",
                      mini=dict(kind="meter", reading="ЗЕЛЁНЫЙ · кодов нет",
                                sub="Q-Logic 3: зелёный — без ограничений, жёлтый — лифт снижает скорость, "
                                    "красный — полная блокировка",
                                prompt="Сиденье стоит. Что это значит?",
                                options=[
                                    ("Блокировки нет — команда не доходит до актуатора: проверить разъём и жгут", True, ""),
                                    ("Красная блокировка — виноват наклон сиденья", False,
                                     "Индикатор зелёный: контроллер ничего не блокирует."),
                                    ("Батарея села", False,
                                     "Заряд полный и кода 20 «Undervoltage» нет."),
                                ])),
                    # source: E4 p7 — автомат на батарейном лотке; жёлтая кнопка отключает батареи от системы
                    S("Выключи контроллер и нажми жёлтую кнопку на автомате — батареи отключены от системы.",
                      "hands", "controller",
                      "Разъёмы трогаем только на обесточенной коляске."),
                    # source: TB4 p4 — Pinch/Crush points exist; TB4 p6 — ничего не должно попасть в механизм
                    S("Осмотри ножничный механизм снаружи, с фонариком. Руки — вне ножниц.",
                      "hands", "seat_lift",
                      "Ножницы — точки защемления. Смотрим глазами, не пальцами.",
                      "Барти: «Сунь лапу между ножниц и подтолкни — он просто ленится!» — нет! Это точка "
                      "защемления: руки в механизм не суют даже на выключенной коляске.", ghost_wrong=True),
                    # source: E4 p25 — задняя крышка снимается поворотом двух жёлтых фиксаторов
                    # source: E4 p19 — все разъёмы должны быть плотными и надёжно закреплёнными, без коррозии
                    # source: E4 p26 — треснувшие/сломанные разъёмы, перетёртые жгуты -> к дилеру Quantum
                    S("Сними заднюю крышку (два жёлтых фиксатора, без инструментов). Осмотри разъём актуатора "
                      "и вставь его до щелчка защёлки.",
                      "hands", "actuator",
                      "Корпус цел, контакты без зелёной коррозии? Тогда до щелчка. Треснул или подгорел — "
                      "не чиним, к сертифицированному технику."),
                    # source: E4 p11 — штатные точки крепления жгута, чтобы не зажимало рамой сиденья
                    # source: CSG p8 — повреждённые компоненты меняет авторизованный сервис
                    S("Срежь стяжки у подстаканника и закрепи жгут по штатным точкам — чтобы рама сиденья его не прижимала.",
                      "hands", "wiring",
                      "Лифт ходит вверх-вниз: жгуту нужен свободный ход. Перетёртую оплётку не изолируют — меняют в сервисе."),
                    # source: E4 p7 — питание возвращают, опустив рычажок автомата
                    S("Поставь крышку на место, опусти рычажок автомата и включи контроллер.",
                      "hands", "controller",
                      "Автомат на Edge 4 — он же выключатель батарей."),
                    # source: E4 p9 — проверять систему снижения скорости; QL3 p8 — жёлтый индикатор при подъёме
                    # source: TB4 p7 — лифт 0–12 in: 2 mph (3 км/ч)
                    S("Подними сиденье и проверь: на пульте значок iLevel и жёлтый индикатор, ход медленный — около 3 км/ч.",
                      "hands", "seat_lift",
                      "Мануал велит проверять систему снижения скорости перед каждой поездкой с поднятым сиденьем."),
                    # source: E4 p9 — не поднимать на уклоне, бордюре, неровной поверхности
                    S("Опусти сиденье полностью, следя, чтобы жгут не натягивался.",
                      "hands", "seat_lift",
                      "На улицу, на пандус и через порог — только с опущенным сиденьем."),
                ],
                test="Сиденье плавно поднимается, загорается жёлтый индикатор, Зикс медленно катит к стеллажу и "
                     "снимает с верхней полки банку гаек. Опускается — жгут лежит свободно.",
                # source: E4 p19, p20, p26; QL3 p8
                fact="Зелёный индикатор и тишина — значит, блокировки нет, а команда теряется по дороге. "
                     "Мануал Edge 4 велит проверять, что все разъёмы плотные, а жгут не зажат рамой сиденья; "
                     "треснувший разъём или перетёртый жгут меняет только сервис.",
                thanks="Зикс: «Подстаканник оставлю, а провода больше не трогаю. Почти. Спасибо, костлявый!»",
            ),
            # --- Б: наклон/откидка больше 20° — заводская блокировка подъёма ---
            dict(
                parts=["seat_lift", "seat", "controller", "actuator", "battery", "freewheel"],
                inspect={
                    "seat_lift": "Ножницы сложены, чистые, ничего не застряло.",
                    "seat": "Сиденье наклонено назад, спинка откинута почти лёжа: Зикс «улучшил» коляску "
                            "до «режима сиесты» и в нём дремал.",
                    "controller": "На экране горит КРАСНЫЙ индикатор блокировки; в режиме подъёма "
                                  "сиденье не двигается.",
                    "actuator": "Разъём актуатора сидит плотно, кабель целый.",
                    "battery": "Заряд полный.",
                    "freewheel": "Рычаги свободного хода подняты — моторы в режиме езды.",
                },
                diagnosis=[
                    D("Заводская блокировка: наклон или откидка больше 20° запрещают подъём — вернуть сиденье ближе "
                      "к ровному", True),
                    D("Сгорел актуатор лифта", False,
                      "Красный индикатор — это не поломка, а блокировка по положению сиденья."),
                    D("Моторы в свободном ходе", False,
                      "Рычаги подняты, и свободный ход не мешает лифту."),
                ],
                steps=[
                    # source: QL3 p8 — значения индикатора блокировки; QL3 p8 key 2 -> экран сиденья
                    S("Включи контроллер, нажми key 2, выбери «подъём», дай джойстик вперёд — и прочитай индикатор.",
                      "hands", "controller",
                      "Пульт первым скажет, поломка это или защита.",
                      mini=dict(kind="meter", reading="КРАСНЫЙ",
                                sub="Q-Logic 3: зелёный — без ограничений, жёлтый — лифт снижает скорость, "
                                    "красный — полная блокировка",
                                prompt="Что значит красный?",
                                options=[
                                    ("Блокировка по положению сиденья: наклон/спинка за пределом", True, ""),
                                    ("Отвалился разъём актуатора", False,
                                     "Обрыв разъёма не зажигает красный. Красный — это защита по углу."),
                                    ("Всё в порядке, просто жми сильнее", False,
                                     "Сила тут ни при чём — контроллер сам запрещает подъём."),
                                ])),
                    # source: E4 p9 — ровный пол, не под столом, зона свободна
                    S("Проверь: коляска на ровном полу, сверху ничего, вокруг ножниц и спинки пусто.",
                      "hands", "seat_lift",
                      "Спинка и сиденье сейчас поедут — им нужно место."),
                    # source: TB4 p6 — запрещено обходить, снимать, перепрограммировать заводские блокировки
                    S("Джойстиком влево-вправо выбери режим наклона сиденья.",
                      "hands", "controller",
                      "Работаем штатными режимами — без «хитростей».",
                      "Барти: «Перепрограммируй блокировку — и лифт поедет при любом наклоне!» — нет! "
                      "Мануал прямо запрещает обходить и перенастраивать заводские блокировки: это защита "
                      "от опрокидывания.", ghost_wrong=True),
                    # source: TB4 p7 — Elevate Lockout при наклоне > 20°, откидке > 20°, наклон+откидка > 125°
                    # source: E4 p9 — при iLevel наклон/откидка допустимы до 20°
                    S("Уменьши наклон сиденья, пока угол не станет 20° или меньше.",
                      "hands", "seat",
                      "Подъём разрешён только при наклоне и откидке не больше 20°.",
                      mini=dict(kind="gap", lo=0, hi=20, mn=0, mx=50, unit="°", start=35,
                                label="Наклон сиденья",
                                hint="TRU-Balance: подъём разблокирован при наклоне до 20°",
                                fb_lo="Меньше нуля сиденье не наклонить.",
                                fb_hi="Больше 20° — подъём всё ещё заблокирован.")),
                    # source: TB4 p7 — Reclined more than 20° -> Elevate Lockout
                    S("Переключись на режим спинки и подними её ближе к вертикали (откидка не больше 20°).",
                      "hands", "seat",
                      "Откинутая спинка блокирует подъём так же, как наклон."),
                    # source: QL3 p8 — «чтобы вернуться к зелёному, выполни движение в обратную сторону»
                    S("Проверь индикатор: красный должен смениться зелёным.",
                      "hands", "controller",
                      "Зелёный — ограничений нет, можно поднимать."),
                    # source: E4 p8 — iLevel включается сам при подъёме, значок на пульте; QL3 p10
                    S("Выбери «подъём» и дай джойстик вперёд: сиденье поднимается, на пульте значок iLevel.",
                      "hands", "seat_lift",
                      "iLevel включается сам, как только сиденье поехало вверх."),
                    # source: TB4 p7 — поднято: 1/4 скорости, 2 mph (3 км/ч); E4 p9 — проверять систему скорости
                    # source: E4 p9 — если «iLevel не включён» на ровном полу -> прекратить и к дилеру
                    S("Проверь ход с поднятым сиденьем: жёлтый индикатор, около 3 км/ч. Потом опусти сиденье.",
                      "hands", "seat_lift",
                      "Если на ровном полу пишет «iLevel не включён» — лифтом не пользоваться, к сервису."),
                ],
                test="Индикатор зелёный, сиденье плавно едет вверх, загорается жёлтый. Зикс торжественно "
                     "достаёт с верхней полки банку гаек и опускается обратно.",
                # source: TB4 p7 (inhibit matrix), TB4 p6 (12 in, no bypass), QL3 p8 (red/yellow/green)
                fact="На системах TRU-Balance подъём блокируется, если сиденье наклонено или спинка откинута "
                     "больше чем на 20°: красный индикатор Q-Logic 3 — это защита, а не поломка. Верни угол — "
                     "индикатор позеленеет. Поднятое сиденье ограничивает скорость примерно до 3 км/ч.",
                thanks="Зикс: «Значит, “режим сиесты” и лифт не дружат. Буду дремать пониже. Спасибо, костлявый!»",
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
            "controller": "Контроллер изредка пищит — диагностический код.",
            "battery": "Заряд в норме.",
        },
        diagnosis=[
            D("Джойстик: перезагрузка, чистка, разъём, калибровка + срочно заменить пыльник", True),
            D("Сгорел мотор", False, "Уводит из-за джойстика, моторы тут ни при чём."),
            D("Спустило колесо", False, "Колёса в порядке."),
        ],
        steps=[
            S("Перезагрузи: выключи и снова включи контроллер.", "hands", "joystick",
              "Джойстик мог «уснуть» — перезагрузка часто всё решает.",
              "Барти: «Выключи и включи. Великая магия XXI века, говорят.»"),
            S("Проверь, что джойстик не погнут и сам возвращается в центр.", "hands", "joystick", ""),
            S("Протри джойстик сухой тряпкой от грязи и пыли.", "cloth", "joystick",
              "Грязь у основания мешает отклику."),
            S("Проверь и передёрни разъём кабеля джойстика.", "hands", "wiring",
              "Ослабший разъём кабеля — частая причина рывков."),
            S("Откалибруй джойстик по инструкции (reset/калибровка).", "hands", "controller",
              "После чистки и переподключения часто нужна калибровка."),
            S("Срочно замени порванный резиновый пыльник джойстика.", "hands", "boot",
              "Порванный пыльник пускает влагу в электронику — меняем немедленно.",
              "Барти: «Замотай скотчем!» — нет, влага убьёт плату, нужен новый пыльник.", ghost_wrong=True),
            S("После дождя просуши и проверь джойстик и тормоза перед поездкой.", "cloth", "joystick",
              "Вода в электронике = короткое замыкание; мокрой коляске дай просохнуть ~12 ч в тепле."),
        ],
        test="Джойстик чётко возвращается в центр, коляска едет ровно, пыльник цел и сухо.",
        fact="Джойстик лечат перезагрузкой, чисткой, проверкой разъёма и калибровкой. Порванный пыльник меняют "
             "сразу: влага губит электронику. Сложную электронику доверяй сертифицированному технику. "
             "У Моры Permobil M3 Corpus — средний привод, разворот на месте ~1,1 м; шины ведущих колёс "
             "держат 200–250 кПа.",
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
            "freewheel": "У моторов есть рычаги с жёлтыми наконечниками — свободный ход.",
            "motor": "Один мотор подвывает сильнее другого.",
            "wiring": "Разъём одного мотора сидит неплотно.",
            "battery": "Батарея разряжена в ноль.",
            "axle": "В оси намотался мусор.",
            "controller": "Контроллер погас — нет питания.",
            "frame": "Рама цела.",
        },
        diagnosis=[
            D("Перевести в свободный ход и откатить; затем разъёмы мотора и шум", True),
            D("Тащить волоком с включёнными моторами", False, "На включённых моторах не катится, можно повредить привод."),
            D("Сразу менять мотор", False, "Сперва простое: разъёмы, мусор в колёсах, шум."),
        ],
        steps=[
            S("Выключи питание коляски.", "hands", "controller",
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
            S("Послушай моторы: оба должны звучать одинаково.", "hands", "motor",
              "Вой/стук = износ подшипников или ремня → к сертифицированному технику."),
            S("Верни рычаги свободного хода вверх (режим езды) и поставь батарею на зарядку.", "charger", "battery",
              "Обязательно верни моторы в режим езды — иначе тормоза не работают."),
        ],
        test="Рычаги в режиме езды, разъёмы плотные, моторы звучат ровно, батарея заряжается.",
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
PARTS.update({'anti_tip': 'Антиопрокидыватель', 'backrest': 'Спинка (стойки)', 'tilt_cable': 'Трос наклона', 'tilt_lever': 'Курок наклона', 'tilt_lock': 'Замок наклона (рокер/зубья)', 'gas_spring': 'Газовая пружина спинки', 'armrest': 'Откидной подлокотник', 'seat_cable': 'Разъём сиденья', 'breaker': 'Главный автомат', 'brushes': 'Щётки мотора', 'mag_brake': 'Электромагн. тормоз'})
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
        parts=["tire", "brake", "bolts", "anti_tip", "axle", "spokes"],
        inspect={
            "tire": "Левая шина мягкая на ощупь. На боковине написано 90–110 psi — явно меньше.",
            "brake": "В зажатом положении упор замка едва касается левой шины. На трубе рамы — светлый след: "
                     "хомут съехал назад со старого места.",
            "bolts": "Два винта хомута замка (шестигранник 3/16\") подразболтались.",
            "anti_tip": "Антиопрокидыватели опущены и защёлкнуты, колёсики целы. К замку отношения не имеют.",
            "axle": "Быстросъёмная ось защёлкнута, кнопка вышла полностью, люфта нет.",
            "spokes": "Спицы натянуты ровно, колесо не «восьмерит».",
        },
        diagnosis=[
            D("Низкое давление в шине + сползший хомут замка: упор не вдавливается в шину на 5 мм (3/16\")", True),
            D("Замок сломан — менять узел целиком", False,
              "Замок исправен, его просто сдвинуло. По мануалу сначала давление, потом положение хомута."),
            D("Ослабла быстросъёмная ось", False,
              "Ось защёлкнута и без люфта. Колесо крутится, потому что его не держит замок."),
            D("Надо сильнее тянуть рычаг замка на спуске", False,
              "Замки — НЕ тормоза: ими нельзя замедлять едущую коляску. Они только держат стоящую."),
        ],
        steps=[
            # source: p22, p15
            S("Проверь манометром давление в обеих задних шинах и сравни с цифрой на боковине.", "gauge", "tire",
              "TiLite: давление проверять КАЖДУЮ неделю. Если шина спущена, замок на этой стороне может проскальзывать.",
              "Барти: «Мастер говорил: замок держит не рычаг, а воздух. Я тогда не понял. Я и сейчас не понял.»"),
            # source: p70 (регулировать только на накачанной шине); число — GAME (мануал: «см. боковину»)
            S("Накачай шину через ниппель до давления с боковины. Замок регулируют только на накачанной шине!", "pump", "tire",
              "Если выставить замок на спущенной шине, после подкачки он будет работать неправильно.",
              "Барти: «Качай, качай... я считаю вслух. Раз. Два. Э-э... много.»",
              mini=dict(kind="pump", lo=90, hi=110, mx=140, unit="psi",
                        hint="На боковине этой шины: 90–110 psi")),
            # source: p70
            S("Ослабь, но НЕ выкручивай два винта хомута замка.", "allen", "brake",
              "Шестигранник 3/16\" (≈4,8 мм). Винты ослабляют, чтобы хомут можно было сдвинуть по раме.",
              "Барти: «Выкрути их совсем, чтоб не мешались!»", ghost_wrong=True,
              wrongmsg="Хомут ослабляют шестигранником 3/16\", и винты не выкручивают до конца."),
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
              "После любой регулировки весь крепёж надёжно затягивают до поездки."),
            # source: p27
            S("Отпусти замок и прокрути колесо: упор не должен задевать шину.", "hands", "tire",
              "Чек-лист TiLite: в отпущенном виде замок не мешает шине, шарниры без износа и люфта."),
            # source: p70, p18, p22
            S("Зажми оба замка и сильно толкни коляску: колёса не должны проворачиваться.", "hands", "brake",
              "Мануал требует этот тест после каждой регулировки замка.",
              "Барти: «Отлично, теперь на спуске можно тормозить этими замками!» Нет! Замки — не тормоза.",
              ghost_wrong=True,
              wrongmsg="Проверка простая: зажми замки рукой и толкни коляску."),
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
            D("Стойки спинки стоят под разным углом: гайка угла с одной стороны ослабла, и стойка «уехала»", True),
            D("Растянулась обивка: хватит подтянуть ремни", False,
              "Ремни меняют форму спинки, но не угол стоек. Перекос в самих стойках."),
            D("Клиентка «неправильно сидит»", False,
              "Дело не в посадке. Посмотри на стойки: они стоят под разным углом, так никто ровно не усидит."),
        ],
        steps=[
            # source: p32 (тормоза — стояночные)
            S("Поставь коляску на ровный пол и зажми оба тормоза. Ивушка пересаживается на скамью.", "hands", "brake",
              "Угол стоек меняем на пустой коляске: так безопаснее, и стойка двигается свободно.",
              "Барти: «Мастер всегда говорил: сначала тормоза, потом философия.»"),
            # source: p31
            S("Рулеткой замерь расстояние от каждой стойки спинки до пластины подлокотника.", "tape", "backrest",
              "Etac сверяет угол спинки именно так: расстояние стойка ↔ пластина подлокотника должно совпадать с обеих сторон."),
            # source: p31
            S("Ослабь гайку 13 мм на внутренней стороне крепления левого колеса.", "wrench", "bolts",
              "Угол спинки держит эта гайка. Винты 4 и 8 мм на стойках отвечают за ВЫСОТУ спинки, их не трогаем.",
              "Барти: «Да крути все винты на спинке подряд, какой-нибудь да тот!»", ghost_wrong=True,
              wrongmsg="Угол стойки держит гайка 13 мм у крепления колеса. Нужен ключ."),
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
              "Затянутая гайка не даст стойке снова провернуться под весом."),
            # source: p15
            S("Ивушка садится обратно. Подстрой ремни обивки: сначала нижний (опора таза), потом верхний.", "hands", "backrest",
              "Etac: обивку настраивают, когда человек сидит в коляске. Верхние ремни не перетягивай: коляска будет хуже складываться.",
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
        id="iris_tilt", kind="manual", client="Дракончик Искра", client_art="client_iris.png",
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
            D("Антиопрокидыватели на разной высоте + провис троса: правый штифт не входит в рокер до конца", True),
            D("Сломан весь механизм наклона, менять раму", False,
              "Механизм цел: штифт просто не дотягивается из-за провисшего троса. Это регулировка, а не замена."),
            D("Ребёнок слишком активно ёрзает", False,
              "Дело не в ребёнке: коляска должна быть надёжной при любых движениях. Ищи причину в механике."),
            D("Смазать трос маслом, и всё пройдёт", False,
              "Мануал Iris запрещает смазывать механизм наклона. Провис убирают регулятором."),
        ],
        steps=[
            # source: p16, p14
            S("Поставь коляску на ровный пол и зажми оба замка. Искра пересаживается к маме на руки.", "hands", "brake",
              "На ровной поверхности замеры честные. Замок должен вдавливаться в шину не меньше чем на 3 мм (1/8\").",
              "Барти: «Привет, малыш! Я призрак, но добрый. Почти не страшный. Ну, чуть-чуть.»"),
            # source: p13, p16
            S("Рулеткой замерь зазор от колёсиков антиопрокидывателей до пола с обеих сторон.", "tape", "anti_tip",
              "Норма Iris: 38–51 мм (1½–2\") в опущенном положении."),
            # source: p13, p16
            S("Нажми кнопку колёсика левого антиопрокидывателя и переставь его в отверстие ниже.", "hands", "anti_tip",
              "Iris: оба колёсика должны стоять СТРОГО на одной высоте.",
              mini=dict(kind="gap", lo=38, hi=51, mn=20, mx=80, unit="мм", start=62,
                        label="Зазор антиопрокидывателя до пола",
                        hint="Iris: 38–51 мм (1½–2\"), справа сейчас 45 мм",
                        fb_lo="Ниже 38 мм: будет цепляться за пороги и может опрокинуть коляску.",
                        fb_hi="Выше 51 мм: может не удержать коляску от опрокидывания назад.")),
            # source: p27
            S("Ослабь контргайку на регуляторе троса правого курка.", "wrench", "tilt_cable",
              "Регулятор троса стоит у ручки, рядом с курком."),
            # source: p27
            S("Вращай регулятор троса, пока не уйдёт провис.", "hands", "tilt_cable",
              "Не перетягивай: штифт должен свободно выдвигаться и убираться.",
              "Барти: «Капни масла на трос, сам натянется!»", ghost_wrong=True,
              wrongmsg="Механизм наклона Iris не смазывают. Провис убирают регулятором, руками."),
            # source: p27
            S("Проверь штифт-плунжер: курок нажат — полностью убран, курок отпущен — полностью вошёл в рокер.", "hands", "tilt_lock",
              "Главный критерий правильной натяжки троса по мануалу."),
            # source: p27
            S("Затяни контргайку.", "wrench", "tilt_cable",
              "Иначе регулятор открутится от вибрации, и трос снова провиснет."),
            # source: p20, p12
            S("Проверь наклон: нажми ОБА курка одновременно, наклони кресло, отпусти, и оно должно жёстко встать.", "hands", "tilt_lever",
              "Механизм отпускается только обоими курками, а при отпускании рокеры блокируются. "
              "Когда в кресле ребёнок, руки у него на подлокотниках, ноги на подножке.",
              "Барти: «Наклони до упора, пусть спинка ляжет горизонтально, веселее же!»", ghost_wrong=True,
              wrongmsg="Наклон проверяют обоими курками и руками. И никогда не дальше, чем спинка параллельна полу."),
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
        id="focuscr_cable", kind="manual", client="Бабушка Агата", client_art="client_focuscr.png",
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
            D("Залом троса наклона: трос тянет с трением, зуб фиксатора не садится до конца. Трос заменить", True),
            D("Подтянуть регулятор посильнее, и залом не страшен", False,
              "Ki Mobility: трос с заломом или такой, что не регулируется, ЗАМЕНЯЮТ. Регулятором залом не лечится."),
            D("Сели газовые пружины спинки", False,
              "Газовые пружины откидывают спинку, а не наклоняют сиденье. И они держат."),
            D("Залить трос WD-40", False,
              "Мануал прямо запрещает WD-40 и нефтяные растворители: они повреждают узлы."),
        ],
        steps=[
            # source: p19
            S("Поставь кресло на ровный пол, зажми замки. Агата пересаживается в кресло у окна.", "hands", "brake",
              "Ki: регулировки наклона и спинки делают на ровной поверхности с зажатыми замками.",
              "Барти: «Мадам Агата! Я призрак этой мастерской. Да, тот самый. Нет, не я уронил ваш телескоп в 1987-м.»"),
            # source: p20, p26
            S("Осмотри трос наклона по всей длине: заломы, резкие изгибы, неправильная прокладка.", "hands", "tilt_cable",
              "Ki: тросы проверяют каждую неделю: работу, прокладку, изгибы и заломы."),
            # source: p20, p25
            S("Сними трос с заломом и поставь новый оригинальный трос Ki Mobility.", "wrench", "tilt_cable",
              "Трос с заломом или такой, что не регулируется, только меняют. Запчасти ставь только одобренные Ki.",
              "Барти: «Выпрями его пассатижами, будет как новый!»", ghost_wrong=True,
              wrongmsg="Залом не выпрямляют, трос меняют целиком."),
            # source: p20 (рис. 27)
            S("Проложи новый трос по штатному пути: плавно, без резких изгибов и не пережимая стяжками.", "hands", "tilt_cable",
              "Ki: изгибов троса должно быть как можно меньше, тогда меньше трение."),
            # source: p19
            S("Ослабь контргайку регулятора троса ключами 10 мм и 3/8\".", "wrench", "tilt_cable",
              "Одним ключом держишь корпус регулятора, другим отпускаешь гайку."),
            # source: p19
            S("Вкручивай или выкручивай регулятор, пока не уйдёт провис. Зуб фиксатора должен остаться полностью в зубьях.", "hands", "tilt_cable",
              "Провиса нет, но и перетяжки нет: зуб фиксатора всё ещё полностью сидит в зубьях поворотной рамы."),
            # source: p19
            S("Покачай наклон по всему диапазону и послушай фиксатор.", "hands", "tilt_lock",
              "Наклон должен фиксироваться в любом положении, а зуб не должен чиркать по зубьям.",
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
            # source: p19
            S("Затяни контргайку. Крути только гайку, не регулятор и не корпус.", "wrench", "tilt_cable",
              "Если провернуть регулятор или корпус, собьёшь только что найденную настройку."),
            # source: p19
            S("Верни кресло в нужное положение и вставь стопорный штифт в курок. Проверь, что наклон не отпускается.", "hands", "tilt_lever",
              "Ki: слегка нажми курок и толкни ручки, наклон должен стоять. Курок блокируют штифтом после позиционирования.",
              "Барти: «А зафиксируй курок ОТКРЫТЫМ и иди пить чай, пусть само встанет!»", ghost_wrong=True,
              wrongmsg="Нельзя оставлять человека в кресле с курками, зафиксированными открытыми: можно опрокинуться."),
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
                    D("Код 02: при включении джойстик был не в нейтрали — включать, не касаясь джойстика", True),
                    D("Батарея разряжена", False,
                      "Разряд — это коды 05/06, а батарея почти полная."),
                    D("Разблокированы тормоза", False,
                      "Это был бы код 03. Рычаги подняты — тормоза заперты."),
                ],
                steps=[
                    # source: whill/whill_c2_ci2_f_error_code_list.pdf p1 (коды 01-06)
                    S("Прочитай код на дисплее пульта и найди его в таблице кодов.", "hands", "controller",
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
                    S("Выключи питание кнопкой на пульте.", "hands", "controller",
                      "Выключенная коляска не дёрнется от случайного касания."),
                    S("Убери с пульта всё, что давит на джойстик: тубус, сумку, край плаща.", "hands", "joystick",
                      "Джойстику хватает 1 Н, чтобы сдвинуться — это вес маленького яблока.",
                      # source: WHILL_UM p107 (printed 106): Force needed to operate joystick 1 N
                      "Барти: «Держи джойстик вперёд, пока включаешь, — быстрее поедет!» "
                      "— нет: при включении джойстик не трогают, иначе код 02.", ghost_wrong=True),
                    # source: WHILL_UM p36 (printed 35): Check that the joystick moves smoothly
                    S("Проверь, что джойстик ходит плавно и сам возвращается в центр.", "hands", "joystick",
                      "Пункт ежедневного осмотра из мануала."),
                    # source: WHILL_UM p97 (printed 96): 70% ethyl alcohol, без растворителей
                    S("Протри пульт салфеткой, смоченной 70 % спиртом — без воды и растворителей.", "cloth", "joystick",
                      "Мыть водой можно только колёса; пульт и электронику — нет."),
                    # source: WHILL_UM p36 (printed 35): before use check that the brakes are locked
                    S("Проверь, что рычаги тормозов подняты (тормоза заперты).", "hands", "freewheel",
                      "Иначе следующим вылезет код 03."),
                    # source: WHILL_ERR p1 (02: Turn on the device without touching the controller)
                    S("Включи питание, не касаясь джойстика. Руку — на пульт только после.", "hands", "controller",
                      "Пауза в секунду после включения — и никаких кодов."),
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
                    D("Код 01: подлокотник с пультом не встал в рабочее положение — песок в основании", True),
                    D("При включении тронули джойстик", False,
                      "Это код 02. А тут 01 — дело в подлокотнике."),
                    D("Сломался мотор", False,
                      "Ошибки мотора — коды 60–86. Код 01 — защита, а не поломка."),
                ],
                steps=[
                    S("Прочитай код на дисплее пульта и найди его в таблице кодов.", "hands", "controller",
                      mini=dict(kind="meter", reading="01",
                                sub="таблица WHILL C2: 01 подлокотник, 02 джойстик, 03 тормоз, 04 зарядка",
                                prompt="Что значит код?",
                                options=[
                                    ("Пультом пытались управлять при поднятом подлокотнике", True, ""),
                                    ("Джойстик был не в нейтрали при включении", False, "Это код 02."),
                                    ("Подключена зарядка", False, "Это код 04, а зарядки рядом нет."),
                                ])),
                    S("Выключи питание кнопкой на пульте.", "hands", "controller",
                      "Подлокотник двигают только на выключенной коляске."),
                    # source: WHILL_UM p106 (printed 105): arm release lever difficult to move -> dust in root
                    S("Осмотри основание подлокотника и рычаг фиксатора: что мешает защёлкнуться?", "hands", "armrest",
                      "Мануал: тугой рычаг фиксатора = пыль и песок в основании."),
                    # source: WHILL_UM p106 (printed 105): clean with a brush or air duster;
                    # source: WHILL_UM p97 (printed 96): не наносить смазку/воск на подвижные части
                    S("Вычисти основание подлокотника щёткой (или продуй грушей).", "brush", "armrest",
                      "Только сухая чистка: смазка липнет и собирает песок.",
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
                    D("Код 10: сбой связи через разъём сиденья — перезапуск, переустановка сиденья, чистка контактов",
                      True),
                    D("Замёрзла батарея", False,
                      "Холод — это код 14: коляска просто едет медленнее, а не выключается."),
                    D("Сразу менять пульт и контроллер", False,
                      "Замена пульта, кабеля сиденья или контроллера — последний пункт таблицы, и это работа дилера."),
                ],
                steps=[
                    S("Прочитай код на дисплее пульта и найди его в таблице кодов.", "hands", "controller",
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
                    S("Выключи коляску, нажми кнопку фиксатора и вынь батарею; через 10 с вставь до щелчка "
                      "и включи через 5 с.", "hands", "battery",
                      "Батарея весит 2,7 кг — не урони. Код 10 вернулся? Значит, дело в разъёме сиденья."),
                    # source: WHILL_UM p84 (printed 83): разборка на ровном полу, батарея вынута, тормоза заперты
                    S("Выключи коляску и снова вынь батарею. Проверь: пол ровный, рычаги тормозов подняты.",
                      "hands", "freewheel",
                      "Разборку делают на ровном полу, без батареи и с запертыми тормозами."),
                    # source: WHILL_UM p86-87 (printed 85-86): seat release lever, lift straight up, cushion up
                    S("Потяни рычаг фиксатора сиденья и подними сиденье за подлокотники строго вверх.",
                      "hands", "seat",
                      "Клади сиденье подушкой вверх: на пульт нельзя давить.",
                      "Барти: «Переверни сиденье вверх ногами — так удобнее!» — нет: так ломают пульт.",
                      ghost_wrong=True),
                    # source: WHILL_UM p86 (printed 85): магнитные разъёмы — кардиостимулятор не ближе 20 см
                    # source: WHILL_UM p106 (printed 105): foreign substances in connectors -> remove
                    S("Осмотри контакты разъёма между сиденьем и базой и выметь песок щёткой.", "brush", "seat_cable",
                      "Контакты не трогай пальцами и металлом. Разъём магнитный: кардиостимулятор — не ближе 20 см."),
                    # source: WHILL_ERR p1 (код 10, п.3: clean the contact surface); WHILL_UM p65: не мочить
                    S("Протри контактную поверхность разъёма сухой салфеткой.", "cloth", "seat_cable",
                      "Разъёмы нельзя мочить — только сухая чистка."),
                    # source: WHILL_UM p63-64 (printed 62-63): посадить по смотровому окну, рычаг перпендикулярно
                    S("Поставь сиденье прямо на стойку (сверься через смотровое окно) и опусти рычаг фиксатора.",
                      "hands", "seat",
                      "Рычаг должен встать поперёк сиденья — значит, заперто."),
                    S("Вставь батарею до щелчка и включи через 5 с, не касаясь джойстика.", "hands", "battery",
                      "Код не ушёл — по таблице дальше меняют пульт или кабели. Это работа дилера."),
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
        parts=["breaker", "battery", "joystick", "freewheel", "tire", "motor", "frame"],
        inspect={
            # source: F5_UM p40: длительное хранение — зарядить, выключить главный автомат
            "breaker": "Рычаг главного автомата сзади — в положении OFF. Матильда выключила его на зиму, "
                       "как написано в мануале.",
            "battery": "Батареи осенью зарядили полностью. Сейчас не горит ни одно деление: цепь отсечена.",
            "joystick": "Пульт тёмный. Гнездо зарядки спереди джойстика чистое и сухое.",
            "freewheel": "Рычаги свободного хода — в положении «езда».",
            "tire": "Шины ведущих колёс заметно мягкие: после морозов давление упало.",
            "motor": "Моторы холодные, но целые.",
            "frame": "На раме иней. Термометр на стене сарая показывает около +1 °C.",
        },
        diagnosis=[
            D("Главный автомат выключен на хранение, а в сарае холоднее +5 °C: включить автомат и заряжать в тепле",
              True),
            D("Батареи умерли за зиму — сразу менять пару", False,
              "Осенью их зарядили полностью, а цепь сейчас отсечена автоматом. Сначала включи его."),
            D("Сгорел зарядный автомат — вскрывать электронику", False,
              "Зарядный автомат сам взводится через 5 минут. А в электронику лезет только техник."),
        ],
        steps=[
            # source: F5_UM p39: Always turn off the control panel before you turn off the main circuit breaker
            S("Убедись, что пульт управления выключен.", "hands", "joystick",
              "С главным автоматом работают только при выключенном пульте."),
            # source: F5_UM p39: storage room dry and at least 5 °C, otherwise batteries might not charge fully
            S("Сверь температуру в сарае с мануалом.", "hands", "frame",
              "Холод и сырость не дают батареям зарядиться полностью и разъедают контакты.",
              mini=dict(kind="meter", reading="+1 °C",
                        sub="мануал F5: хранить в сухом помещении не холоднее +5 °C",
                        prompt="Можно заряжать прямо здесь?",
                        options=[
                            ("Нет: ниже +5 °C батареи могут не зарядиться полностью — везём в тепло", True, ""),
                            ("Да, мороза же нет", False,
                             "Мануалу нужно не меньше +5 °C. При +1 °C батареи могут не набрать полный заряд."),
                            ("Да, если зарядка будет дольше", False,
                             "Время не поможет: в холоде батареи заряжаются не полностью."),
                        ])),
            # source: F5_UM p34: freewheel — level ground, turn off, levers down; p20: attendant present
            S("На ровном полу, с помощником, включи свободный ход: рычаги вниз (коляска выключена).",
              "hands", "freewheel",
              "В свободном ходе тормоза отключены — только на ровном и с тем, кто держит коляску."),
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
            S("Подключи зарядку сначала к гнезду спереди джойстика, потом к розетке.", "charger", "joystick",
              "Только штатная зарядка Permobil. Если заряд не пошёл, подожди 5 минут: зарядный автомат "
              "взводится сам.",
              "Барти: «Сначала в розетку, потом в коляску — какая разница?» Разница есть: мануал велит "
              "наоборот."),
            # source: F5_UM p64: drive tyres 250 kPa (35 psi), check weekly and after temperature change
            # source: F5_UM p21: overfilled tires can explode
            S("Пока идёт зарядка, накачай шины ведущих колёс через ниппель до 250 кПа.", "pump", "tire",
              "Давление проверяют раз в неделю и после резкой смены температуры. Перекачанная шина может лопнуть.",
              mini=dict(kind="pump", lo=240, hi=260, mx=320, unit="кПа",
                        hint="Мануал F5: ведущие шины — 250 кПа (35 psi)")),
            # source: F5_UM p33: not possible to drive while charging; p67: charger connected -> disconnect
            S("Заряд полный — отключи зарядку: пока она подключена, F5 не поедет.", "charger", "battery",
              "Дальше на хранении: автомат выключен, но раз в месяц его включают и подзаряжают батареи."),
        ],
        test="Индикатор заряда на пульте полный, шины упругие. Матильда делает круг по мастерской и "
             "тормозит точно у банки мёда.",
        # source: F5_UM p39-40, p64, p66, p70
        fact="Перед долгим хранением F5 заряжают полностью и выключают главный автомат. Раз в месяц автомат "
             "включают, заряжают батареи и выключают снова. Хранить и заряжать — в сухом месте не ниже +5 °C. "
             "Зарядку подключают сначала к коляске, потом к розетке. Шины ведущих колёс — 250 кПа (35 psi).",
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
            T("w_mount", "Сними заднее колесо (QR-ось) и установи в правочный станок", "hands", "rear_wheel",
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
            T("w_back", "Поставь колесо обратно на быстросъёмную ось", "hands", "rear_wheel",
              after=["w_recheck", "w_even"],
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
        tools=["hands", "screw", "wrench", "charger", "multimeter", "cloth", "allen"],
        intro="Бренна: «Электрика прощает всё, кроме неуважения. Порядок клемм — как молитва: наизусть.»",
        steps=[
            T("p_off", "Выключи питание контроллера", "hands", "controller", safety=True,
              note="Любая работа — только на обесточенной коляске.",
              failnote="На включённой коляске случайное касание джойстика — и она поедет. "
                       "Вместе с твоими пальцами в спицах.",
              ghost="Бренна: «Первое правило электрики: сначала убей питание. Второе: проверь, что убил.»"),
            T("p_open", "Открути и сними кожух батарейного отсека", "screw", "frame",
              note="Крепёж — в магнитную плошку, а не «куда-то на верстак»."),
            T("p_disc_neg", "Отсоедини МИНУСОВУЮ клемму — всегда первой", "wrench", "battery",
              after=["p_off", "p_open"], safety=True,
              note="Минус снят — цепь на массу разорвана, ключ уже не устроит короткое.",
              failnote="Пока минус на массе, ключ, соскочивший с плюса на раму, — это короткое "
                       "замыкание, искры и оплавленные клеммы."),
            T("p_disc_pos", "Отсоедини плюсовую клемму", "wrench", "battery",
              after=["p_disc_neg"]),
            T("p_out", "Вынь старые батареи из отсека", "hands", "battery",
              after=["p_disc_pos"],
              note="Они тяжёлые: поднимай из приседа и держи вертикально.",
              ghost="Барти: «Дай я подниму! ...ах да. Ладно, ты сам.»"),
            T("p_pick", "Подбери новую пару по каталогу Гильдии", "hands", "battery",
              after=["p_out"],
              spec=dict(manual="battery_pair", prompt="Какую пару батарей ставим?",
                        options=[
                            ("Две новые AGM 12 В — одинаковые ёмкость, тип и возраст", True, ""),
                            ("Одну новую + прошлогоднюю той же ёмкости (экономия!)", False,
                             "Пара работает по слабейшей: старая батарея утащит новую за собой."),
                            ("Новую AGM + новую гелевую — обе же 12 В", False,
                             "Типы не смешивают: у AGM и геля разные режимы заряда, умрут обе."),
                        ])),
            T("p_in", "Установи новую пару в отсек и зафиксируй", "hands", "battery",
              after=["p_pick"],
              note="Болтающаяся батарея перетирает провода на первой же кочке."),
            T("p_conn_pos", "Подключи ПЛЮСОВУЮ клемму первой", "wrench", "battery",
              after=["p_in"], safety=True,
              note="Сборка — зеркально разборке: плюс первым, минус последним.",
              failnote="Минус подключают последним: пока массы нет, соскочивший ключ "
                       "не сделает короткого замыкания."),
            T("p_conn_neg", "Подключи минусовую клемму и верни кожух", "wrench", "battery",
              after=["p_conn_pos"]),
            T("p_charge", "Включи питание и поставь пару на полную первую зарядку", "charger", "battery",
              after=["p_conn_neg"],
              note="Первая зарядка — полная и только штатным ЗУ: она задаёт паре ресурс."),
        ],
        test="Контроллер доволен, индикатор заряда ползёт вверх. Бренна проверяет затяжку клемм. Кивнула!",
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
            T("x_press", "Выровняй давление в обеих шинах по манометру", "gauge", "tire",
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
        tools=["hands", "multimeter", "screw", "wrench", "charger", "lube", "brush"],
        intro="Бренна: «Мигает — значит, контроллер что-то тебе говорит. Сначала переведи, потом меряй, "
              "потом крути. И питание — до разъёмов, а не после.»",
        steps=[
            # source: P6_SM p26 (printed 2.1: Battery Gauge Flashes Rapidly), p27 (printed 3.1: Two Bars)
            T("q_code", "Расшифруй мигание индикатора VR2 по таблице кодов", "hands", "joystick",
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
            T("q_disc", "Осмотри и отсоедини 4-контактный разъём левого мотора от модуля управления",
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
            T("q_cap", "Открути колпачки щёткодержателей плоской отвёрткой и вынь щётки — по одной",
              "screw", "brushes", after=["q_ohm", "q_off"],
              note="Запомни, как стояла щётка: обратно — той же стороной.",
              ghost="Барти: «Колпачок тугой? Навались всем весом!» — нет, пластик колпачка легко сломать."),
            # source: P6_SM p48 (printed 6.2): replace any brush less than 1/4 inch; replace both motors
            T("q_wear", "Оцени износ щёток и реши, что менять", "hands", "brushes", after=["q_cap"],
              spec=dict(manual="vr2_codes", prompt="Щётка левого мотора — 4 мм, торец со сколом. Решение?",
                        options=[
                            ("Меньше 1/4\" (≈6 мм) — менять щётки в обоих моторах", True, ""),
                            ("4 мм ещё поработают — ставим обратно", False,
                             "Предел — 1/4\" (≈6 мм). 4 мм — уже износ, отсюда и обрыв."),
                            ("Поменять одну эту щётку", False,
                             "Мануал: меняешь щётки — меняй в обоих моторах, чтобы тянули одинаково."),
                        ])),
            T("q_new", "Поставь новые щётки той же ориентацией, закрути колпачки без усилия и подключи разъём",
              "screw", "brushes", after=["q_wear"],
              note="Новые щётки сначала обкатывают, иначе замер сопротивления будет неточным."),
            # source: P6_SM p44 (printed 5.10): failure to disengage gearbox -> unexpected operation;
            # source: P6_SM p48 (printed 6.2): run-in with gearbox released
            T("q_free", "Разблокируй редукторы обоих моторов (рычаги свободного хода)", "hands", "freewheel",
              after=["q_new"], safety=True,
              note="Колёса больше не связаны с моторами: прогон не сдвинет коляску.",
              failnote="Ты погнал моторы на обкатку, не разблокировав редукторы: коляска рванула через "
                       "мастерскую. Мануал прямо предупреждает: без расцепления — неожиданное движение."),
            # source: P6_SM p48 (printed 6.2): run-in 20-30 min alternating forward and reverse;
            # source: P6_SM p4 (printed 0.2): power off, chair should not move if pushed -> drive engaged
            T("q_runin", "Обкатай щётки 20–30 мин (вперёд/назад), выключи и верни редукторы в зацепление",
              "hands", "motor", after=["q_free"],
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
        tools=["hands", "multimeter", "screw", "socket", "wrench", "charger", "cloth"],
        intro="Бренна: «Блок-схема — не совет, а маршрут. Сошёл с маршрута — значит, гадаешь. "
              "А гадать будешь на ярмарке.»",
        steps=[
            # source: Q6_TS p29 (#203); QL_TM p92 (M1 = left motor)
            T("b_code", "Найди код дисплея в таблице Q-Logic", "hands", "joystick",
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
            T("b_free", "Проверь, что оба рычага свободного хода в режиме езды (вверх), и перезапусти",
              "hands", "freewheel", after=["b_code"], safety=True,
              note="Код остался — значит, дело не в рычагах. Идём дальше по схеме.",
              failnote="Ты полез под кожух, а рычаг свободного хода остался внизу. Тормоза отключены — "
                       "коляска скатилась с подставки. Бренна поймала её в метре от стеллажа.",
              ghost="Барти: «Рычаги дёргают ногой, так быстрее!» — нет: мануал запрещает — погнёшь рычаг и тормоз."),
            T("b_off", "Выключи питание джойстика", "hands", "controller", safety=True, after=["b_free"],
              note="Модуль питания и разъёмы моторов отключают только без питания.",
              failnote="Модуль питания отсоединён под током: искра на разъёме и испорченный модуль. "
                       "Экзамен окончен."),
            # source: Q6_TS p31 (Appendix 2: rear shroud knob, securement clips)
            T("b_shroud", "Сними задний кожух: открути ручку-барашек и отщёлкни защёлки", "hands", "frame",
              after=["b_off", "b_free"],
              note="Кожух держится на ручке и защёлках, инструмент не нужен."),
            # source: Q6_TS p16, p31 (power module screws)
            T("b_pm", "Открути винты и отсоедини модуль питания от задней рамы", "screw", "controller",
              after=["b_shroud", "b_off"],
              note="Провода не натягивай: модуль просто откидывается, чтобы был доступ к разъёмам."),
            T("b_unplug", "Выдерни разъём жгута левого мотора из модуля питания", "hands", "wiring",
              after=["b_pm"],
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
            T("b_replace", "Действуй по блок-схеме: замена узла, подключение разъёма, модуль и кожух на место",
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
            T("b_test", "Тест тормозов: ровная площадка, малая скорость, джойстик вперёд до щелчка; "
                        "затем назад, влево, вправо",
              "hands", "joystick", after=["b_replace", "b_free"],
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


# ----------------------------------------------------------------------------- #
#  UI-объекты
# ----------------------------------------------------------------------------- #
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
            draw_text(surf, self.label, (cx, r.y + 8), 16, WHITE if enabled else GREY, bold=True, center=True)
            draw_text(surf, self.sub, (cx, r.y + 30), 12, GREY, center=True)
        else:
            draw_text(surf, self.label, r.center, 17, col if enabled else GREY, bold=True, center=True)
        return r


_HOVER = {}


def _hover_amt(key, target):
    """Плавное 0..1 наведения на кнопку (Button пересоздаётся каждый кадр)."""
    now = pygame.time.get_ticks() / 1000.0
    amt, last = _HOVER.get(key, (0.0, now))
    if target >= 1 and amt < 0.04:
        snd("hover")
    amt += (target - amt) * min(1.0, max(0.0, now - last) * 14)
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


class Game:
    def __init__(self, headless=False):
        self.headless = headless
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
        self.seatc = None
        self.act = None                   # анимация инструмента на детали
        self.ride_t0 = None               # тест-драйв: клиент проезжает через экран
        self._vol_drag = None
        if not headless:
            self.load_progress()
            self.load_settings()

    # ---------- утилиты ----------
    def flash(self, text, color=WHITE, secs=3.0):
        self.toast = text
        self.toast_color = color
        self.toast_timer = secs

    def miss(self, msg, secs=4.0):
        """Ошибка игрока: тост + счётчик; на экзамене следит за лимитом."""
        self.mistakes += 1
        snd("bad")
        self.flash(msg, BAD, secs)
        if not (self.dispute and self.dispute.get("t") == self.t):
            self.note_dispute("mistake", "", "", msg)
        self._exam_check()

    def note_dispute(self, kind, expected, got, msg):
        """Запомнить засчитанную ошибку — игрок может оспорить её кнопкой «Я не согласен»."""
        if not self.cur:
            return
        step = ""
        if self.phase == "repair" and self.cur.get("track") != "tech" and self.step_idx < len(self.cur.get("steps", [])):
            step = self.cur["steps"][self.step_idx]["instr"]
        self.dispute = dict(kind=kind, job=self.cur["id"], title=self.cur.get("title", ""), phase=self.phase,
                            step=step, expected=expected, got=got, msg=msg, t=self.t, sent=False)

    def _dispute_btn_rect(self):
        return pygame.Rect(WIDTH - 196, 60, 172, 30)

    def dispute_visible(self):
        d = self.dispute
        return bool(self.scene == "job" and d and not d["sent"] and self.cur and d["job"] == self.cur["id"]
                    and self.t - d["t"] < 25 and not self.dispute_ui and self.v3d is None)

    FEEDBACK_REASONS = ["Неточность в картинке или 3D", "Ошибка в тексте или шагах", "Непонятно, что делать", "Другое"]

    def _feedback_rect(self):
        return pygame.Rect(WIDTH - 154, 8, 38, 38)

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
        return pygame.Rect(WIDTH // 2 - 340, HEIGHT // 2 - 250, 680, 500)

    def _reasons(self):
        return self.FEEDBACK_REASONS if (self.dispute and self.dispute["kind"] == "general") else self.DISPUTE_REASONS

    def _dispute_reason_rects(self):
        p = self._dispute_panel_rect()
        n = len(self._reasons())
        step = 42 if n <= 3 else 34
        return [(i, pygame.Rect(p.x + 28, p.y + 182 + i * step, p.w - 56, step - 6)) for i in range(n)]

    def _dispute_text_rect(self):
        p = self._dispute_panel_rect()
        return pygame.Rect(p.x + 28, p.y + 340, p.w - 56, 78)

    def _dispute_send_rect(self):
        p = self._dispute_panel_rect()
        return pygame.Rect(p.right - 228, p.bottom - 62, 200, 44)

    def _dispute_cancel_rect(self):
        p = self._dispute_panel_rect()
        return pygame.Rect(p.x + 28, p.bottom - 62, 160, 44)

    def close_dispute(self):
        self.dispute_ui = None
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
        if d.get("shot") is not None and not self.headless:
            try:
                fdir = os.path.join(DATA_DIR, "feedback_shots")
                os.makedirs(fdir, exist_ok=True)
                name = "shot_" + entry["time"].replace(":", "-") + ".png"
                pygame.image.save(d["shot"], os.path.join(fdir, name))
                entry["screenshot"] = os.path.join("feedback_shots", name)
            except Exception:
                pass
        if self.headless:
            self.feedback_mem.append(entry)
        else:
            try:
                data = json.load(open(FEEDBACK_PATH, encoding="utf-8")) if os.path.exists(FEEDBACK_PATH) else []
            except Exception:
                data = []
            data.append(entry)
            try:
                with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=1)
            except Exception:
                pass
        d["sent"] = True
        d["shot"] = None
        refunded = False
        if d["kind"] != "general" and not self.exam_mode and self.mistakes > 0:
            self.mistakes -= 1
            refunded = True
        self.close_dispute()
        snd("ok")
        self.flash("Спасибо! Замечание сохранено — его проверят и поправят игру."
                   + (" Эта ошибка не засчитана." if refunded else ""), GOOD, 5)

    def handle_dispute_event(self, event):
        ui = self.dispute_ui
        if event.type == pygame.TEXTINPUT:
            if len(ui["text"]) < 600:
                ui["text"] += event.text
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
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
            if d["expected"] or d["got"]:
                draw_text(surf, "Игра ожидала: " + d["expected"], (p.x + 28, y), 15, GOOD); y += 24
                draw_text(surf, "Ты выбрал: " + d["got"], (p.x + 28, y), 15, BAD); y += 26
            y = draw_wrapped(surf, "Подсказка игры: " + d["msg"], (p.x + 28, y), p.w - 56, 14, GREY, max_lines=3)
        draw_text(surf, "Что не так?" if general else "Почему не согласен?", (p.x + 28, p.y + 156), 15, WHITE, bold=True)
        reasons = self._reasons()
        for i, r in self._dispute_reason_rects():
            Button(r, "", CYAN).draw(surf, mouse, active=i == ui["reason"])
            draw_text(surf, ("◉  " if i == ui["reason"] else "○  ") + reasons[i], (r.x + 14, r.y + (8 if r.h > 32 else 5)), 16, WHITE)
        tr_ = self._dispute_text_rect()
        draw_text(surf, "Опиши, что не так и как правильно" if general else "Как правильно, по-твоему? (можно не писать)",
                  (tr_.x, tr_.y - 22), 14, GREY)
        aa_rect(surf, (12, 12, 18), tr_, border_radius=8)
        aa_rect(surf, DIM, tr_, 1, border_radius=8)
        caret = "|" if int(self.t * 2) % 2 == 0 else ""
        draw_wrapped(surf, ui["text"] + caret, (tr_.x + 10, tr_.y + 8), tr_.w - 20, 15, WHITE, max_lines=3)
        Button(self._dispute_cancel_rect(), "ОТМЕНА", GREY).draw(surf, mouse)
        Button(self._dispute_send_rect(), "ОТПРАВИТЬ", GOOD).draw(surf, mouse)

    def _exam_check(self):
        if self.exam_mode and self.mistakes > EXAM_MAX_MISTAKES and self.scene == "job":
            self.fail_msg = (f"Лимит ошибок экзамена исчерпан: {self.mistakes} при допустимых "
                             f"{EXAM_MAX_MISTAKES}. Бренна молча закрывает ведомость.")
            self.mini_pending = None
            self.spec_pending = None
            self.show_manual = False
            snd("fail")
            self.scene = "failed"

    def job_by_id(self, jid):
        return next(j for j in ALL_JOBS if j["id"] == jid)

    def user_done_count(self):
        return len([j for j in JOBS if j["id"] in self.done])

    def tech_done_count(self):
        return len([j for j in TECH_JOBS if j["id"] in self.done])

    def guild_unlocked(self):
        return self.user_done_count() >= GUILD_REQ

    def load_settings(self):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f).get("volume", {})
            for k in ("master", "music", "sfx", "amb"):
                if k in data:
                    VOL[k] = max(0.0, min(1.0, float(data[k])))
            if "on" in data:
                VOL["on"] = bool(data["on"])
        except Exception:
            pass
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                DISPLAY["glow"] = bool(json.load(f).get("glow", True))
        except Exception:
            pass
        apply_volume()
        lang = None
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                lang = json.load(f).get("lang")
        except Exception:
            pass
        if "--lang" in sys.argv[:-1]:
            lang = sys.argv[sys.argv.index("--lang") + 1]
        set_lang(lang or system_lang())

    def save_settings(self):
        if self.headless:
            return
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump({"volume": dict(VOL), "lang": LANG["code"], "fullscreen": DISPLAY["fullscreen"],
                           "glow": DISPLAY["glow"]},
                          f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_progress(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            valid = {j["id"] for j in ALL_JOBS}
            self.done = {j for j in data.get("done", []) if j in valid}
            self.garage = [(j, int(s)) for j, s in data.get("garage", []) if j in valid]
            self.exam_passed = bool(data.get("exam_passed"))
            ids = {c["id"] for c in SEAT_CASES}
            self.seat_done = {c for c in data.get("seat_done", []) if c in ids}
            self.seat_quiz_ok = bool(data.get("seat_quiz_ok"))
        except Exception:
            pass

    def save_progress(self):
        if self.headless:
            return
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump({"done": sorted(self.done),
                           "garage": [[j, s] for j, s in self.garage],
                           "exam_passed": self.exam_passed,
                           "seat_done": sorted(self.seat_done), "seat_quiz_ok": self.seat_quiz_ok},
                          f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def available_jobs(self):
        """Туториал (flat) первым; остальные открыты после него."""
        if "flat" not in self.done:
            return ["flat"]
        return [j["id"] for j in JOBS]

    # ---------- запуск задания ----------
    def start_job(self, jid, variant=None):
        self.cur = resolve_job(self.job_by_id(jid), variant)
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
        self.mini_pending = None
        self.exam_mode = False
        self.inspected = set()
        self.v3d = None
        self.m3d = None                   # 3D прямо в окне диагностики (ракурс, перетаскивание)
        self.act = None
        self.ride_t0 = None
        self.ghost_line = self.cur.get("intro") or \
            "Бартоломью: «Так-так... осмотри детали и реши, что сломалось.»"
        self.scene = "job"

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
        self.flash(clue, CYAN, 4)

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
            snd("ok")
            self.flash("Диагноз верный! Приступаем к ремонту.", GOOD, 3)
            self._set_step_ghost()
            return True
        else:
            self.mistakes += 1
            snd("bad")
            self.flash(opt["feedback"] or "Не похоже. Осмотри ещё раз.", BAD, 4)
            right = next((o["text"] for o in self.cur["diagnosis"] if o["correct"]), "")
            self.note_dispute("diagnosis", right, opt["text"], opt["feedback"] or "")
            return False

    # ---------- ремонт ----------
    def _set_step_ghost(self):
        if self.step_idx < len(self.cur["steps"]):
            self.ghost_line = self.cur["steps"][self.step_idx].get("ghost", "")
            self.last_note = ""

    def select_tool(self, tool_id):
        self.sel_tool = tool_id
        snd(TOOL_SOUND.get(tool_id, "tool_metal"))

    def do_action(self, tool_id, part_id):
        """Применить (инструмент, деталь) к текущему шагу. Возврат: 'ok' | 'wrong'."""
        if self.phase != "repair":
            return "wrong"
        step = self.cur["steps"][self.step_idx]
        if tool_id == step["tool"] and (part_id == step["part"] or part_id in step.get("alt", ())):
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
        self.act = dict(tool=tool, ok=ok, pos=self._act_pos(part, sid), t0=self.t, ticks=0)

    def _draw_action(self, surf):
        a = self.act
        if not a:
            return
        dur = 0.95 if a["ok"] else 0.6
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
        draw_tool_action(surf, a["tool"], a["pos"], u, a["ok"])

    def complete_base_step(self, step):
        self._start_action(step["tool"], True, part=step["part"])
        self.last_note = step.get("note", "")
        snd("ok")
        self.flash("Шаг выполнен. " + (self.last_note or ""), GOOD, 4)
        self.step_idx += 1
        self.sel_tool = None
        if self.step_idx >= len(self.cur["steps"]):
            self.phase = "test"
            self.ghost_line = "Бартоломью: «Кажется, всё. Прокатим — проверим!»"
        else:
            self._set_step_ghost()

    RIDE_SECS = 2.3

    def start_ride(self):
        self.ride_t0 = self.t
        snd("whoosh")

    def _draw_ride(self, surf):
        """Тест-драйв: клиент в своей коляске проезжает через мастерскую."""
        k = (self.t - self.ride_t0) / self.RIDE_SECS
        e = k * k * (3 - 2 * k)
        img = load_image(self.cur["client_art"], (230, 250), GHOST)
        x = -260 + (WIDTH + 520) * e
        y = 290 - int(4 * abs(math.sin(self.t * 18)))
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
        if self.cur["id"] not in [g[0] for g in self.garage]:
            self.garage.append((self.cur["id"], stars))
        self.cur_stars = stars
        self.result_gag = random.choice(LEG_GAGS)
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
            self.miss("Рано! Сначала: " + pre["instr"] + ".")
            return "wrong"
        if tool_id != step["tool"]:
            self.miss(f"Инструмент не тот. Нужен: {TOOLS[step['tool']][0]}.", 3.5)
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
        self.flash("Шаг выполнен. " + (step.get("note") or ""), GOOD, 4)
        if step.get("ghost") and not self.exam_mode:
            self.ghost_line = step["ghost"]
        if len(self.done_steps) >= len(self.cur["steps"]):
            self.phase = "test"
            self.ghost_line = ("Экзамен: сборка окончена. Финальная проверка." if self.exam_mode
                               else "Бренна: «Закончил? Слова дешёвые. Проверим под нагрузкой.»")

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
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_F11 or (
                event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)):
            if not self.headless:
                toggle_fullscreen()
                self.save_settings()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            on = toggle_sound()
            self.save_settings()
            self.flash("Звук включён" if on else "Звук выключен (M — включить)", GHOST, 1.8)
            return
        if self.dispute_ui is not None:                  # окно замечания модально (и ловит ввод текста)
            self.handle_dispute_event(event)
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.dispute_visible()
                and self._dispute_btn_rect().collidepoint(event.pos)):
            self.open_dispute()
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.scene not in ("title", "intro", "ending")
                and self._feedback_rect().collidepoint(event.pos)):
            self.open_feedback()
            return
        if self.show_sound:                              # панель громкости модальна
            self.handle_sound_event(event)
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.scene in ("title", "hub", "guild", "garage")
                and self._lang_rect().collidepoint(event.pos)):
            self.toggle_lang()
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self._speaker_rect().collidepoint(event.pos)):
            self.show_sound = True
            snd("tick")
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
            if (event.key == pygame.K_TAB and self.scene == "job" and self.cur
                    and not self.mini_pending and not self.show_manual and not self.spec_pending):
                self.open_v3d()
                return
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
                        self.esc_timer = 2.5
                        self.flash("Ещё раз Esc — покинуть ремонт (прогресс задания сбросится).",
                                   AMBER, 2.5)
                elif self.scene in ("garage", "guild", "result", "exam_result", "failed", "seating"):
                    self.scene = "hub"
                elif self.scene == "hub":
                    self.scene = "title"
                elif self.scene in ("title", "intro", "ending"):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

    def click_title(self, m):
        self.scene = "hub" if self.done else "intro"

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
            if "flat" in self.done:
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
            self.scene = "garage"
            return
        if self.user_done_count() >= len(JOBS) and self._hub_ending_rect().collidepoint(m):
            self.scene = "ending"

    def click_job(self, m):
        if self.cur.get("track") == "tech":
            self.click_job_tech(m)
            return
        if self.mini_pending:
            self._click_mini(m)
            return
        if self.phase == "diagnose":
            if self._v3d_btn_rect().collidepoint(m):
                self.open_v3d()
                return
            for pid, rect in self._part_rects():
                if rect.collidepoint(m):
                    self.inspect_part(pid)
                    return
            for i, rect in self._diag_rects():
                if rect.collidepoint(m):
                    self.choose_diagnosis(i)
                    return
            pid = self._hotspot_at(m)
            if pid:
                self.inspect_part(pid)
                return
        elif self.phase == "repair":
            for tid, rect in self._tool_rects():
                if rect.collidepoint(m):
                    self.select_tool(tid)
                    return
            for pid, rect in self._part_rects():
                if rect.collidepoint(m):
                    if self.sel_tool is None:
                        self.flash("Сначала выбери инструмент внизу.", AMBER, 2.5)
                    else:
                        self.do_action(self.sel_tool, pid)
                    return
            pid = self._hotspot_at(m)
            if pid:
                if self.sel_tool is None:
                    self.flash("Сначала выбери инструмент внизу.", AMBER, 2.5)
                else:
                    self.do_action(self.sel_tool, pid)
                return
        elif self.phase == "test":
            if self._test_btn_rect().collidepoint(m) and self.ride_t0 is None:
                self.start_ride()

    def click_result(self, m):
        if self._result_btn_rect().collidepoint(m):
            if self.cur.get("track") == "tech":
                self.scene = "guild"
            elif self.user_done_count() >= len(JOBS):
                self.scene = "ending"
            else:
                self.scene = "hub"

    def click_garage(self, m):
        if self._back_rect().collidepoint(m):
            self.scene = "hub"

    def click_ending(self, m):
        self.scene = "garage"

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
                self.start_ride()

    # =========================================================== #
    #  UPDATE
    # =========================================================== #
    def music_theme(self):
        sc = self.scene
        if sc == "intro":
            return "road"
        if sc == "ending":
            return "party"
        if sc in ("guild", "exam_result", "failed"):
            return "guild"
        if sc == "job" and self.cur and self.cur.get("track") == "tech":
            return "guild"
        return "workshop"

    def update(self, dt):
        self.t += dt
        if not self.headless:
            music_update(self.music_theme(), self.t)
        if self.toast_timer > 0:
            self.toast_timer -= dt
        if self.esc_timer > 0:
            self.esc_timer -= dt
        if self.v3d is not None:
            self.update_v3d(dt)
        if self.ride_t0 is not None and self.scene != "job":
            self.ride_t0 = None                       # ушли из задания — проезд отменён
        if self.ride_t0 is not None and self.t - self.ride_t0 >= self.RIDE_SECS:
            self.ride_t0 = None
            self.finish_test()

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
        if not seen or seen[0] != text:
            self._typing[key] = (text, self.t)
            return 0
        return int((self.t - seen[1]) * cps)

    def typing_done(self, key):
        seen = self._typing.get(key)
        return not seen or (self.t - seen[1]) * 75 >= len(seen[0])

    def skip_typing(self, key):
        seen = self._typing.get(key)
        if seen:
            self._typing[key] = (seen[0], self.t - 1000)

    def draw(self, surf):
        if self.scene != self._scene_seen:          # смена сцены: растворяем прошлый кадр
            if self._scene_seen is not None:
                self._fade_from = self._last_frame
                self._fade_t0 = self.t
                snd("whoosh")
            self._stars_played = set()
            self._scene_seen = self.scene
            self.scene_t0 = self.t
        getattr(self, f"draw_{self.scene}")(surf)
        if self.toast_timer > 0 and self.toast:
            self._draw_toast(surf)
        self._draw_speaker(surf)
        if self.scene in ("title", "hub", "guild", "garage"):
            self._draw_lang(surf)
        if self.scene == "job":
            self._draw_dispute_btn(surf, mouse_pos())
        if self.scene not in ("title", "intro", "ending"):
            self._draw_feedback_flag(surf)
        if self.dispute_ui is not None:
            self._draw_dispute_panel(surf, mouse_pos())
        if self.show_sound:
            self._draw_sound_panel(surf)
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
        self.save_settings()
        self._typing.clear()
        snd("tick")

    def _speaker_rect(self):
        return pygame.Rect(WIDTH - 50, 8, 38, 38)

    def _draw_speaker(self, surf):
        r = self._speaker_rect()
        mouse = mouse_pos()
        h = _hover_amt(("speaker",), 1.0 if (r.collidepoint(mouse) or self.show_sound) else 0.0)
        bg = Surf(r.size, pygame.SRCALPHA)
        aa_rect(bg, (30, 28, 40, int(150 + 90 * h)), bg.get_rect(), border_radius=10)
        surf.blit(bg, r)
        col = tuple(int(a + (b - a) * h) for a, b in zip(GHOST, AMBER))
        cx, cy = r.x + 13, r.centery
        DR.rect(surf, col, (cx - 6, cy - 5, 6, 10))
        DR.polygon(surf, col, [(cx, cy - 5), (cx + 7, cy - 11), (cx + 7, cy + 11), (cx, cy + 5)])
        level = VOL["master"] if VOL["on"] else 0.0
        if level <= 0.001:
            DR.line(surf, BAD, (cx + 12, cy - 6), (cx + 22, cy + 6), 3)
            DR.line(surf, BAD, (cx + 22, cy - 6), (cx + 12, cy + 6), 3)
        else:
            for i, rad in enumerate((7, 12, 17)):
                if level > i / 3 + 0.01:
                    DR.arc(surf, col, (cx + 4 - rad + 6, cy - rad, rad * 2, rad * 2),
                                    -0.75, 0.75, 2)

    def _sound_panel_rect(self):
        return pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 228, 520, 448)

    def _screen_btn_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 32, p.bottom - 128, (p.w - 64) // 2 - 6, 44)

    def _glow_btn_rect(self):
        p = self._sound_panel_rect()
        w = (p.w - 64) // 2 - 6
        return pygame.Rect(p.right - 32 - w, p.bottom - 128, w, 44)

    def _vol_slider_rects(self):
        p = self._sound_panel_rect()
        return [(k, pygame.Rect(p.x + 205, p.y + 86 + i * 58, 210, 8))
                for i, k in enumerate(("master", "music", "sfx", "amb"))]

    def _sound_mute_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.x + 32, p.bottom - 70, 220, 44)

    def _sound_close_rect(self):
        p = self._sound_panel_rect()
        return pygame.Rect(p.right - 192, p.bottom - 70, 160, 44)

    def _set_vol_from_x(self, key, x):
        track = dict(self._vol_slider_rects())[key]
        VOL[key] = round(max(0.0, min(1.0, (x - track.x) / track.w)), 2)
        if key in ("amb", "master", "music"):
            apply_volume()

    def handle_sound_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.show_sound = False
            self.save_settings()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._sound_close_rect().collidepoint(event.pos) or \
                    not self._sound_panel_rect().collidepoint(event.pos):
                self.show_sound = False
                self.save_settings()
                snd("tick")
                return
            if self._sound_mute_rect().collidepoint(event.pos):
                toggle_sound()
                snd("tick")
                return
            if self._screen_btn_rect().collidepoint(event.pos):
                if not self.headless:
                    toggle_fullscreen()
                snd("tick")
                return
            if self._glow_btn_rect().collidepoint(event.pos):
                DISPLAY["glow"] = not DISPLAY["glow"]
                snd("tick")
                return
            for key, track in self._vol_slider_rects():
                if track.inflate(24, 30).collidepoint(event.pos):
                    self._vol_drag = key
                    self._set_vol_from_x(key, event.pos[0])
                    return
        elif event.type == pygame.MOUSEMOTION and self._vol_drag:
            self._set_vol_from_x(self._vol_drag, event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._vol_drag:
            if self._vol_drag in ("master", "sfx"):
                snd("ok")                                   # услышать новую громкость
            self._vol_drag = None

    def _draw_sound_panel(self, surf):
        dim = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((8, 8, 12, 170))
        surf.blit(dim, (0, 0))
        p = self._sound_panel_rect()
        bg = Surf(p.size, pygame.SRCALPHA)
        aa_rect(bg, (18, 18, 26, 250), bg.get_rect(), border_radius=14)
        surf.blit(bg, p)
        aa_rect(surf, AMBER, p, 2, border_radius=14)
        draw_text(surf, "ЗВУК И ЭКРАН", (p.x + 32, p.y + 22), 24, AMBER, bold=True)
        draw_text(surf, "M — быстро выключить / включить", (p.right - 32, p.y + 30), 13, GREY, right=True)
        mouse = mouse_pos()
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
            draw_text(surf, f"{int(VOL[key] * 100)}%", (track.right + 52, track.y - 8), 16,
                      GREY if muted else WHITE, right=True)
        Button(self._sound_mute_rect(), "ВКЛЮЧИТЬ ЗВУК" if not VOL["on"] else "БЕЗ ЗВУКА",
               GOOD if not VOL["on"] else GREY).draw(surf, mouse)
        Button(self._glow_btn_rect(), "СВЕЧЕНИЕ: ВКЛ" if DISPLAY["glow"] else "СВЕЧЕНИЕ: ВЫКЛ",
               AMBER if DISPLAY["glow"] else GREY).draw(surf, mouse)
        Button(self._screen_btn_rect(), "В ОКНО [F11]" if DISPLAY["fullscreen"] else "ВЕСЬ ЭКРАН [F11]",
               CYAN).draw(surf, mouse)
        Button(self._sound_close_rect(), "ГОТОВО", AMBER).draw(surf, mouse)

    def _bg(self, surf, name, color):
        key = ("bg_dimmed", name, RS)                          # фон + затемнение — один раз, дальше одна копия на кадр
        bg = _img_cache.get(key)
        if bg is None:
            bg = Surf((WIDTH, HEIGHT))
            bg.blit(load_image(name, (WIDTH, HEIGHT), color), (0, 0))
            ov = Surf((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((18, 16, 24, 150))
            bg.blit(ov, (0, 0))
            _img_cache[key] = bg
        surf.blit(bg, (0, 0))
        draw_ambient(surf, name, self.t)
        set_ambient(name)

    def _draw_toast(self, surf):
        lines = wrap_lines(self.toast, WIDTH - 140, 16)
        h = 12 + len(lines) * (font(16).get_height() + 2)
        k = ease_back((self.t - self._typing.setdefault(("toast", self.toast), (self.toast, self.t))[1]) / 0.3)
        rect = pygame.Rect(8, 4 - int(50 * (1 - k)), WIDTH - 16, max(46, h))
        s = Surf(rect.size, pygame.SRCALPHA)
        s.fill((20, 18, 26, 250))
        surf.blit(s, rect)
        aa_rect(surf, self.toast_color, rect, 2, border_radius=6)
        lh = font(16).get_height() + 2
        y = rect.y + (rect.h - len(lines) * lh) // 2 + lh // 2
        for ln in lines:
            draw_text(surf, ln, (rect.centerx, y), 16, self.toast_color, center=True)
            y += lh

    def _topbar(self, surf, title):
        DR.rect(surf, (16, 14, 22), (0, 0, WIDTH, 54))
        DR.line(surf, AMBER, (0, 54), (WIDTH, 54), 1)
        draw_text(surf, title, (24, 15), 22, AMBER, bold=True)
        draw_text(surf, "КОЛЁСА И КОСТИ", (WIDTH - 170, 16), 18, GHOST, bold=True, right=True)

    # ----- титул -----
    def _wave_title(self, surf, text, center, size, color, st, delay=0.0):
        """Заголовок: буквы падают по очереди с перелётом, потом мягко «дышат» волной."""
        f = font(size, True)
        text = tr(text)
        x = center[0] - f.size(text)[0] // 2
        for i, ch in enumerate(text):
            d = delay + 0.05 * i
            k = ease_back((st - d) / 0.55)
            a = int(255 * clamp01((st - d) / 0.2))
            y = center[1] - f.get_height() // 2 - int(70 * (1 - k)) + 4 * math.sin(self.t * 2.2 + i * 0.55)
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
        self._wave_title(surf, "КОЛЁСА И КОСТИ", (WIDTH // 2, 210), 76, AMBER, st)
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
            label = "[ клик — продолжить ]" if self.done else "[ клик — начать ]"
            pulse = 0.5 + 0.5 * math.sin(self.t * 3.2)
            draw_text(surf, label, (WIDTH // 2, 470), 24, AMBER, bold=True, center=True,
                      alpha=150 + 105 * pulse)
        draw_text(surf, "Esc — выход · M — звук · прогресс сохраняется автоматически",
                  (WIDTH // 2, HEIGHT - 36), 15, GREY, center=True)

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
        panel = pygame.Rect(360, 250 + int(24 * (1 - sk)), 560, 250)
        s = Surf(panel.size, pygame.SRCALPHA)
        s.fill((22, 20, 30, int(230 * sk)))
        surf.blit(s, panel)
        aa_rect(surf, AMBER, panel, 2, border_radius=8)
        draw_text(surf, title, (panel.centerx, panel.y + 20), 26, AMBER, bold=True, center=True, alpha=255 * sk)
        draw_wrapped(surf, text, (panel.centerx, panel.y + 70), panel.w - 50, 19, WHITE, center=True,
                     line_gap=4, limit=n)
        draw_text(surf, f"{idx + 1}/{len(self.intro_slides)}   [ клик — далее ]",
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
            fit_text(surf, job["client"], (r.x + 12, r.y + 166), r.w - 24, 16, WHITE, bold=True)
            draw_wrapped(surf, job["title"], (r.x + 12, r.y + 188), r.w - 24, 13, GREY, max_lines=2)
            power = job.get("kind") == "power"
            draw_text(surf, "ЭЛЕКТРО" if power else "РУЧНАЯ",
                      (r.x + 12, r.bottom - 22), 12, CYAN if power else AMBER, bold=True)
            if done:
                draw_text(surf, "✔ готово", (r.right - 12, r.bottom - 22), 13, GOOD, right=True)
        pages = self._hub_pages()
        if pages > 1:
            page = min(getattr(self, "hub_page", 0), pages - 1)
            for d, rect in self._hub_arrow_rects():
                Button(rect, "◀" if d < 0 else "▶", AMBER).draw(surf, mouse)
            cx = (self._hub_arrow_rects()[0][1].right + self._hub_arrow_rects()[1][1].x) // 2
            for k in range(pages):
                aa_circle(surf, AMBER if k == page else DIM, (cx + (k - (pages - 1) / 2) * 22, 657), 6)
        # призрак-наставник в углу
        blit_idle(surf, load_image("ghost.png", (150, 200), CYAN), (WIDTH - 220, 120), self.t,
                  "float", k=ease_back((self.st - 0.3) / 0.5))
        seat_ok = "flat" in self.done
        n_seat = len(self.seat_done) + (1 if self.seat_quiz_ok else 0)
        Button(self._hub_seat_rect(), "КАБИНЕТ ПОСАДКИ", GOOD,
               sub=(f"позиционирование: {n_seat}/{len(SEAT_CASES) + 1}" if seat_ok
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

    # ================================================================ #
    #  КАБИНЕТ ПОСАДКИ: уроки, примерка (ползунки + живая поза), проверка
    # ================================================================ #
    def open_seating(self):
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
        self.seatc.update(case=i, cfg=cfg, solved=False)

    @staticmethod
    def seat_eval(case, cfg):
        """Оценка посадки: список проверок (ключ, ок?, текст) + параметры позы для рисунка.
        Правила — из руководства Permobil; карта терапевта задаёт диапазоны спинки и угла."""
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
                           + (": мешает лопаткам и толчку" if case["kind"] == "manual" else "")))
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
        deep = max(0.0, d - tgt_depth - 1.5)
        high = max(0.0, tgt_leg - 1.5 - lg)
        low = max(0.0, lg - tgt_leg - 1.5)
        p = 3.0 * deep + 2.5 * high + 2.0 * low + 2.5 * max(0, lo_b - bh) + 1.5 * max(0, lo_a - ba)
        p += 0.8 * max(0, ba - hi_a) if tl < 20 else 0
        slide = 0.8 * deep + 0.8 * low + (0.25 * max(0, ba - hi_a) if tl < 20 else 0)
        pose = dict(p=min(26.0, p), slide=min(10.0, slide), deep=deep > 0, short=d < tgt_depth - 3,
                    knee_up=high > 0, dangle=low > 0)
        return checks, pose

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
        draw_wrapped(surf, line, (bubble.x + 12, bubble.y + 8), bubble.w - 24, 14, (226, 214, 246),
                     limit=self.typed("seat_say", line, cps=95), max_lines=3)

    def _seat_slider_rects(self):
        c = SEAT_CASES[self.seatc["case"]]
        row_h = ((len(SEAT_CASES) + 1) // 2) * 40
        y0 = 112 + row_h + 26
        keys = ["depth", "leg", "back_h", "back_a"] + (["tilt"] if c.get("tilt") else [])
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
                sc["xray"] = not sc.get("xray", True)
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
        mx, my = (x0 + x3) * 0.5, min(y0, y3) - 26.0 - 9.0 * math.sin(self.t * 2.4 + phase)
        pts = []
        n = 16
        for i in range(n + 1):
            t = i / n
            u = 1.0 - t
            bx = u * u * x0 + 2 * u * t * mx + t * t * x3
            by = u * u * y0 + 2 * u * t * my + t * t * y3 + 3.2 * math.sin(t * math.pi * 2 + self.t * 4.0 + phase)
            pts.append((bx, by))
        glow_c = col if active else (152, 114, 218)
        DR.lines(surf, _shade(glow_c, 0.62), False, pts, 3 if active else 2)
        DR.lines(surf, (232, 210, 255) if active else glow_c, False, pts, 1)
        u_spark = (self.t * 0.75 + phase * 0.23) % 1.0
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
        staff_y = ny + int(nh * 0.08) + int(3.0 * math.sin(self.t * 2.5))
        pulse = 0.65 + 0.35 * math.sin(self.t * 4.5)
        orb_col = BAD if bad_flag else GHOST
        add_glow(surf, (staff_x, staff_y), int(20 * pulse), PURPLE, 0.85)
        add_glow(surf, (staff_x, staff_y), int(10 * pulse), orb_col, 0.9)
        for i, (tx, ty, col_t, is_act) in enumerate(targets):
            self._draw_necro_thread(surf, (staff_x, staff_y), (tx, ty), col=col_t, active=is_act, phase=i * 1.3)

    # ---------- рисунок: скелет-марионетка и клиент в коляске сбоку ----------
    def _draw_seat_scene(self, surf, rect, case, cfg, pose, highlight=True, show_necro=True, show_body=False):
        """Вид сбоку: детальная коляска, анатомический скелет (таз, позвонки, грудная клетка, череп,
        бедро, надколенник, голень, стопа) и некромант Мортимер, управляющий скелетом нитями."""
        for gx in range(rect.x + 20, rect.right - 10, 36):
            DR.line(surf, (26, 29, 40), (gx, rect.y + 8), (gx, rect.bottom - 26), 1)
        for gy in range(rect.y + 16, rect.bottom - 26, 36):
            DR.line(surf, (26, 29, 40), (rect.x + 10, gy), (rect.right - 10, gy), 1)

        k = min(rect.w / 155.0, rect.h / 132.0)
        floor_y = rect.bottom - 24
        x_r = rect.x + rect.w * (0.43 if show_necro else 0.36)
        seat_h, depth, leg = case["seat_h"], cfg["depth"], cfg["leg"]
        tilt = math.radians(cfg.get("tilt", 0))
        piv = (depth * 0.45, -8.0)

        def T(px, py):
            dx, dy = px - piv[0], py - piv[1]
            rx = piv[0] + dx * math.cos(tilt) - dy * math.sin(tilt)
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
        if case["kind"] == "power":
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

        if show_body:
            skin = case.get("skin", (200, 190, 170))
            ghost_s = Surf(rect.size, pygame.SRCALPHA)
            ox_s, oy_s = rect.x, rect.y
            def TS(px, py):
                q = T(px, py)
                return (q[0] - ox_s, q[1] - oy_s)
            wd_b = max(6, int(11.5 * k))
            DR.line(ghost_s, (*skin, 55), TS(*hip), TS(*knee), wd_b)
            DR.line(ghost_s, (*skin, 55), TS(*knee), TS(*ankle), max(5, int(8.5 * k)))
            DR.line(ghost_s, (*skin, 60), TS(*hip), TS(*mid), int(wd_b * 1.35))
            DR.line(ghost_s, (*skin, 60), TS(*mid), TS(*sh), int(wd_b * 1.35))
            aa_circle(ghost_s, (*skin, 55), TS(*head), int(10.5 * k))
            surf.blit(ghost_s, rect.topleft)

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

        if case["kind"] != "power":
            R = 30 if seat_h > 45 else 26
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
            draw_text(surf, status_txt, (rect.x + 140, rect.y + 12), 12, badge_col, bold=True)

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
        for zi, ((zx, zy), col, label, dx_l, dy_l) in enumerate(zones):
            p_ = T(zx, zy)
            add_glow(surf, (int(p_[0]), int(p_[1])), int(10 * k), col, 0.9)
            aa_circle(surf, col, (int(p_[0]), int(p_[1])), max(3, int(2.6 * k)))
            aa_circle(surf, WHITE, (int(p_[0]), int(p_[1])), max(4, int(4.2 * k)), 1)
            lx = max(rect.x + 205, min(rect.right - 95, int(p_[0] + dx_l)))
            ly = max(rect.y + 48, min(floor_y - 24, int(p_[1] + dy_l)))
            for uy in used_ys:
                if abs(ly - uy) < 18:
                    ly = min(floor_y - 24, uy + 19)
            used_ys.append(ly)
            DR.line(surf, col, (int(p_[0]), int(p_[1])), (lx, ly + 7), 1)
            tw = font(12, True).size(label)[0] + 10
            aa_rect(surf, (16, 12, 24, 215), (lx - tw // 2, ly - 1, tw, 16), border_radius=4)
            draw_text(surf, label, (lx, ly), 12, col, bold=True, center=True)

    def _seat_front(self, surf, rect, corrected=False):
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
        for (px, py), dir_s, lab in pads:
            pad_r = pygame.Rect(int(px - 8 * k), int(py - 20 * k), int(16 * k), int(40 * k))
            aa_rect(surf, CYAN, pad_r, border_radius=5)
            aa_rect(surf, WHITE, pad_r, 1, border_radius=5)
            ax0 = px - dir_s * 22 * k
            ax1 = px - dir_s * 10 * k
            DR.line(surf, GOOD, (ax0, py), (ax1, py), 2)
            draw_text(surf, lab, (px + (16 if dir_s < 0 else -16) * k, py - 7), 12, CYAN, bold=True, right=dir_s > 0)

        targets = [
            (h_cx, h_cy - hr, PURPLE, False),
            (apex_x, apex_y, GOOD if corrected else CYAN, True),
            (pl[0], pl[1], p_col, not corrected),
            (sh_l[0], sh_l[1], CYAN, False),
        ]
        self._draw_necro_puppeteer(surf, rect, targets, bad_flag=not corrected)
        status = "Три точки держат ось позвоночника" if corrected else "Таз перекошен → дуга сколиоза"
        draw_text(surf, status, (rect.x + 140, rect.y + 12), 12, GOOD if corrected else AMBER, bold=True)

    def _draw_seat_909090_myth(self, surf, rect):
        """Иллюстрация к вопросу о мифе «90-90-90»: Мортимер и три скелета с разной целью посадки."""
        for gx in range(rect.x + 20, rect.right - 10, 36):
            DR.line(surf, (26, 29, 40), (gx, rect.y + 8), (gx, rect.bottom - 26), 1)
        draw_text(surf, "Мортимер: «Один шаблон 90-90-90 не подходит всем — решают осмотр и цель!»",
                  (rect.centerx + 36, rect.y + 16), 14, AMBER, bold=True, center=True)
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
        case.update(back=(40, 50), angle=(95, 105), kind="power" if spec.get("tilt") else "manual")
        _, pose = self.seat_eval(case, cfg)
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
                self._draw_seat_scene(surf, cv.inflate(-16, -24), case, cfg, pose, show_necro=True)
                if lpose.get("measure"):
                    draw_text(surf, "Жёсткая рулетка: глубина = бедро − 5 см (2″)", (cv.x + 148, cv.y + 14), 14, AMBER, bold=True)
            has_err_pose = any(k in lpose for k in ("p", "slide", "deep", "knee_up", "dangle", "front"))
            if has_err_pose:
                tbtn = self._seat_demo_toggle_rect()
                Button(tbtn, "ПОЗА: НОРМА ✔" if demo_good else "ПОКАЗАТЬ НОРМУ ▶",
                       GOOD if demo_good else PURPLE).draw(surf, mouse, active=demo_good)
            y = 112 + ((len(SEAT_LESSONS) + 1) // 2) * 44 + 10
            draw_text(surf, les["title"], (780, y), 20, AMBER, bold=True)
            y += 32
            for pt_ in les["points"]:
                y = draw_wrapped(surf, "• " + pt_, (780, y), 476, 15, WHITE) + 8
            draw_text(surf, "По руководству Permobil «Seating & Positioning Guide»",
                      (cv.x + 14, cv.bottom - 38), 11, GREY)
        elif sc["tab"] == "fit":
            case = SEAT_CASES[sc["case"]]
            checks, pose = self.seat_eval(case, sc["cfg"])
            xray = sc.get("xray", True)
            self._draw_seat_scene(surf, pygame.Rect(cv.x + 8, cv.y + 98, cv.w - 16, cv.h - 122),
                                  case, sc["cfg"], pose, show_necro=True, show_body=xray)
            blit_idle(surf, load_image(case["client_art"], (92, 108), GHOST), (cv.x + 12, cv.y + 6), self.t)
            tbtn = self._seat_demo_toggle_rect()
            Button(tbtn, "РЕНТГЕН: ВКЛ" if xray else "РЕНТГЕН: СКЕЛЕТ",
                   PURPLE if xray else CYAN).draw(surf, mouse, active=xray)
            for i, r in self._seat_list_rects():
                done = SEAT_CASES[i]["id"] in self.seat_done
                Button(r, "", GOOD if done else CYAN).draw(surf, mouse, active=i == sc["case"])
                fit_text(surf, ("✔ " if done else "") + SEAT_CASES[i]["client"], (r.x + 10, r.y + 8), r.w - 20, 14, WHITE)
            b = case["body"]
            draw_wrapped(surf, case["story"], (cv.x + 112, cv.y + 10), cv.w - 362, 14, WHITE, max_lines=3)
            draw_wrapped(surf, "Карта терапевта: " + case["therapist"], (cv.x + 112, cv.y + 62), cv.w - 126, 13, CYAN, max_lines=2)
            draw_text(surf, f"Мерки: бедро {b['thigh']} см · голень {b['shank']} см · "
                            f"лопатка {b['scap']} см · плечо {b['shoulder']} см",
                      (cv.x + 14, cv.bottom - 38), 11, AMBER)
            sliders = self._seat_slider_rects()
            for key, track in sliders:
                label, unit, lo, hi = SEAT_SLIDERS[key]
                v = sc["cfg"][key]
                ok = next((o for kk, o, _ in checks if kk == key), True)
                draw_text(surf, label, (track.x, track.y - 20), 13, WHITE)
                draw_text(surf, f"{v} {unit}", (track.right + 66, track.y - 9), 14, GOOD if ok else AMBER, right=True)
                aa_rect(surf, (44, 46, 60), track, border_radius=4)
                fill = track.copy()
                fill.w = int(track.w * (v - lo) / (hi - lo))
                aa_rect(surf, GOOD if ok else AMBER, fill, border_radius=4)
                kx = track.x + fill.w
                hov = track.inflate(30, 30).collidepoint(mouse) or sc["drag"] == key
                aa_circle(surf, WHITE, (kx, track.centery), 10 if hov else 8)
                aa_circle(surf, GOOD if ok else AMBER, (kx, track.centery), 10 if hov else 8, 3)
            y = sliders[-1][1].y + 24
            for key, ok, text in checks:
                y = draw_wrapped(surf, ("✔ " if ok else "⚠ ") + text, (780, y), 476, 13, GOOD if ok else AMBER) + 2
            Button(self._seat_btn_rect(), "СЛЕДУЮЩИЙ КЛИЕНТ ▶" if sc["solved"] else "ГОТОВО — ПРОВЕРИТЬ ПОСАДКУ",
                   GOOD if sc["solved"] else AMBER).draw(surf, mouse)
        else:
            if sc["quiz_done"]:
                ok = sc["score"] >= SEAT_QUIZ_PASS
                draw_text(surf, f"Верно {sc['score']} из {len(SEAT_QUIZ)}", (cv.centerx + 40, cv.centery - 20), 30,
                          GOOD if ok else AMBER, bold=True, center=True)
                draw_text(surf, "Зачёт по посадке сдан!" if ok else f"Для зачёта нужно {SEAT_QUIZ_PASS}. Перечитай уроки.",
                          (cv.centerx + 40, cv.centery + 24), 18, WHITE, center=True)
                self._draw_necro_puppeteer(surf, cv, [(cv.centerx + 40, cv.centery - 20, GOOD if ok else AMBER, True)], bad_flag=not ok)
                Button(self._seat_btn_rect(), "ПРОЙТИ ЕЩЁ РАЗ", CYAN).draw(surf, mouse)
                return
            q = SEAT_QUIZ[sc["quiz"]]
            qpose = q.get("pose")
            if qpose and qpose.get("front"):
                self._seat_front(surf, cv, corrected=False)
            elif qpose:
                case, cfg, pose = self._seat_demo_pose(cv, qpose)
                self._draw_seat_scene(surf, cv.inflate(-16, -24), case, cfg, pose,
                                      highlight=sc["picked"] is not None, show_necro=True)
            else:
                self._draw_seat_909090_myth(surf, cv)
            draw_text(surf, f"Вопрос {sc['quiz'] + 1} из {len(SEAT_QUIZ)}", (780, 120), 15, GREY)
            draw_wrapped(surf, q["q"], (780, 146), 476, 20, WHITE)
            for i, r in self._seat_quiz_rects():
                text, ok, fb = q["options"][i]
                col = CYAN
                if sc["picked"] is not None:
                    col = GOOD if ok else (BAD if i == sc["picked"] else DIM)
                Button(r, "", col).draw(surf, mouse, enabled=sc["picked"] is None or i == sc["picked"] or ok)
                draw_wrapped(surf, text, (r.x + 14, r.y + 10), r.w - 28, 15, WHITE)
                if sc["picked"] == i and fb:
                    draw_wrapped(surf, fb, (r.x + 14, r.y + 46), r.w - 28, 13, BAD)
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
        return [(tid, pygame.Rect(24 + (i % 10) * (T + G), 560 + (i // 10) * (T + G), T, T))
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
        for pid, x, y, r in self._chair_hotspots():
            if (m[0] - x) ** 2 + (m[1] - y) ** 2 <= r * r:
                return pid
        return None

    # ---------- 3D прямо в окне диагностики (вместо картинки) ----------
    M3D_YAW, M3D_PITCH = -0.75, 0.26          # спереди-слева в три четверти — как нарисован арт колясок

    def _chair_default_view(self):
        return (self.M3D_YAW, self.M3D_PITCH)

    def _m3d_mesh(self):
        """Облегчённая ИИ-модель для окна диагностики или None (тогда — картинка с хотспотами)."""
        if (self.phase != "diagnose" or self.cur.get("track") == "tech" or _np is None
                or self.ride_t0 is not None):
            return None
        return get_ai_chair3d(self.cur.get("chair_art"), lod=True)

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

    def _m3d_zoom(self):
        """Зум, при котором модель целиком влезает в окно при любом повороте (раз на модель и размер окна)."""
        mesh = self._m3d_mesh()
        rect = self._chair_rect()
        key = ("m3d_fit", id(mesh), rect.size)
        z = _img_cache.get(key)
        if z is None:
            V = _np.asarray(mesh.verts, dtype=_np.float64)[::3] - _np.asarray(mesh.pivot)
            cp, sp = math.cos(self.M3D_PITCH), math.sin(self.M3D_PITCH)
            scale = rect.h / 1250.0
            ox, oy = rect.w / 2, rect.h * 0.54
            worst = 1e-6
            for i in range(16):
                a = i * math.pi / 8
                X = V[:, 0] * math.cos(a) + V[:, 2] * math.sin(a)
                Z = -V[:, 0] * math.sin(a) + V[:, 2] * math.cos(a)
                Y = V[:, 1] * cp - Z * sp
                k = 2600.0 / (2600.0 - (V[:, 1] * sp + Z * cp)) * scale
                sx, sy = X * k, -Y * k
                worst = max(worst, float(_np.abs(sx).max()) / ox, float(-sy.min()) / oy, float(sy.max()) / (rect.h - oy))
            z = _img_cache[key] = 0.97 / worst
        return z

    def _m3d_frame(self):
        """Прямоугольник проекции с полями и зум под него (кружки и картинка считаются одинаково)."""
        r, pad = self._chair_rect(), self.M3D_PAD
        zk = self._m3d_state().get("zoom_k", 1.0)
        return r.inflate(pad * 2, pad * 2), self._m3d_zoom() * zk * r.h / (r.h + pad * 2)

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
        r = max(10, min(14, int(rect.h * 0.035)))
        pts = []
        for pid in self.cur["parts"]:
            cs = mesh.centers.get(pid)
            if not cs:
                continue
            near = max(cs, key=lambda c: project_point(c, yaw, pitch, fr, zoom, mesh.pivot)[1])
            (x, y), _ = project_point(near, yaw, pitch, fr, zoom, mesh.pivot)
            pts.append([pid, x, y, x, y])
        need = 2 * r + 3
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
        if mesh is None or not rect.collidepoint(pos):
            return None
        yaw, pitch, _ = self._m3d_view()
        fr, zoom = self._m3d_frame()
        polys = project_mesh(mesh, yaw, pitch, pygame.Rect(0, 0, fr.w, fr.h), zoom)
        p = (pos[0] - fr.x, pos[1] - fr.y)
        for depth, pts, col, part, fl in reversed(polys):
            if _pt_in_poly(p, pts):
                return part
        return None

    def _m3d_event(self, event):
        """Перетаскивание модели в окне диагностики. True = событие поглощено.
        Клик по кружку детали проходит дальше обычным путём (click_job)."""
        if self._m3d_mesh() is None or self.mini_pending or self.show_manual or self.spec_pending:
            return False
        s = self._m3d_state()
        if event.type == pygame.MOUSEWHEEL and self._chair_rect().collidepoint(mouse_pos()):
            s["zoom_k"] = max(0.75, min(1.65, s.get("zoom_k", 1.0) * (1.10 ** event.y)))
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
                pid = self._m3d_pick(event.pos)        # просто клик по модели — осмотр этой детали
                if pid:
                    self.inspect_part(pid)
            return True
        return False

    def _draw_m3d(self, surf, rect, mouse):
        mesh = self._m3d_mesh()
        s = self._m3d_state()
        yaw, pitch, spinning = self._m3d_view()
        fr, zoom = self._m3d_frame()
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
                    if part == hover:
                        pygame.draw.polygon(hl, (*tuple(int(c + (a_ - c) * 0.6) for c, a_ in zip(col, AMBER)), 190), pts)
                s["hl"] = hl if k == 1 else TF.smoothscale(hl, fr.size)
                s["hl_key"] = (key, hover)
            surf.blit(s["hl"], fr)
        elif not s["drag"] and rect.collidepoint(mouse):
            draw_text(surf, "⟲ тяни — повернуть", (rect.x + 4, rect.bottom - 18), 12, (200, 196, 180))

    # ---------- 3D-осмотр: оверлей ----------
    V3D_SS = 2                      # суперсэмплинг модели (сглаживание)

    def open_v3d(self):
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
            elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                v["zoom"] = min(2.2, v["zoom"] * 1.12)
                v["idle"] = 0.0
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                v["zoom"] = max(0.7, v["zoom"] / 1.12)
                v["idle"] = 0.0
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
        pulse = 0.5 + 0.5 * math.sin(self.t * 6)
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
            if part and part == hover:
                col = _shade(col, 1.35)
            elif part and part == side_hl:
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
            w = font(15, True).size(label)[0] + 22
            rect = pygame.Rect(mouse[0] - w // 2, mouse[1] - 40, w, 26)
            rect.clamp_ip(vr)
            tip = Surf(rect.size, pygame.SRCALPHA)
            aa_rect(tip, (18, 16, 24, 240), tip.get_rect(), border_radius=7)
            surf.blit(tip, rect)
            aa_rect(surf, AMBER if hover in self.cur["parts"] else WHITE, rect, 1, border_radius=7)
            draw_text(surf, label, rect.center, 15, WHITE, bold=True, center=True)
        draw_text(surf, "ЛКМ — вращать · колесо — зум · клик по детали — осмотр · Esc — закрыть",
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
        Button(self._v3d_reset_rect(), "СБРОС ВИДА [R]", CYAN).draw(surf, mouse)
        if self._v3d_ai_available():
            Button(self._v3d_ai_rect(), "МОДЕЛЬ: ДЕТАЛЬНАЯ" if v.get("ai") else "МОДЕЛЬ: ПО ЧЕРТЕЖУ",
                   PURPLE if v.get("ai") else GHOST).draw(surf, mouse)
        Button(self._v3d_close_rect(), "ЗАКРЫТЬ [Esc]", AMBER).draw(surf, mouse)

    def _draw_hotspots(self, surf, mouse):
        hover = None
        if self._m3d_mesh() is not None:              # на 3D: тёмная подложка и выноска к детали
            for pid, x, y, r, (ax, ay) in self._m3d_spots():
                if abs(ax - x) + abs(ay - y) > r * 0.6:
                    DR.line(surf, AMBER, (ax, ay), (x, y), 1)
                    aa_circle(surf, AMBER, (ax, ay), 2)
                disc = Surf((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                aa_circle(disc, (12, 12, 18, 110), (r + 1, r + 1), r)
                surf.blit(disc, (x - r - 1, y - r - 1))
        for i, (pid, x, y, r) in enumerate(self._chair_hotspots()):
            done = self.phase == "diagnose" and pid in self.inspected
            if self.phase == "diagnose" and not done:   # неосмотренное зовёт пульсом
                ph = (self.t * 0.8 + i * 0.17) % 1.0
                rr = int(r + 10 * ease_out(ph))
                ring = Surf((rr * 2 + 4, rr * 2 + 4), pygame.SRCALPHA)
                aa_circle(ring, (*AMBER, int(150 * (1 - ph))), (rr + 2, rr + 2), rr, 2)
                surf.blit(ring, (x - rr - 2, y - rr - 2))
            aa_circle(surf, GOOD if done else AMBER, (x, y), r, 1)
            if (mouse[0] - x) ** 2 + (mouse[1] - y) ** 2 <= r * r:
                hover = (pid, x, y, r)
        if hover:
            pid, x, y, r = hover
            aa_circle(surf, WHITE, (x, y), r + 3, 2)
            label = PARTS[pid]
            w = font(14).size(label)[0] + 16
            rect = pygame.Rect(x - w // 2, y - r - 30, w, 22)
            rect.clamp_ip(pygame.Rect(0, 56, WIDTH, HEIGHT - 56))
            tip = Surf(rect.size, pygame.SRCALPHA)
            tip.fill((18, 16, 24, 235))
            surf.blit(tip, rect)
            aa_rect(surf, WHITE, rect, 1, border_radius=5)
            draw_text(surf, label, rect.center, 14, WHITE, center=True)

    def _test_btn_rect(self):
        return pygame.Rect(WIDTH // 2 - 170, 560, 340, 64)

    def draw_job(self, surf):
        if self.cur.get("track") == "tech":
            self.draw_job_tech(surf)
            return
        self._bg(surf, "bg_workshop.png", WOOD)
        job = self.cur
        self._topbar(surf, job["title"])
        mouse = mouse_pos()

        # клиент слева
        blit_idle(surf, load_image(job["client_art"], (150, 190), GHOST), (24, 70), self.t)
        draw_text(surf, job["client"], (24, 266), 16, WHITE, bold=True)

        # коляска по центру — детали кликабельны прямо на схеме
        crect = self._chair_rect()
        if self.ride_t0 is None:
            if self._m3d_mesh() is not None:
                self._draw_m3d(surf, crect, mouse)
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
            for i, rect in self._diag_rects():
                Button(rect, "", CYAN if unlocked else DIM).draw(surf, mouse, enabled=unlocked)
                text = job["diagnosis"][i]["text"]
                for size in (14, 13, 12, 11):              # длинный диагноз — мельче, но целиком
                    if len(wrap_lines(tr(text), rect.w - 24, size)) * (font(size).get_height() + 2) <= rect.h - 12:
                        break
                draw_wrapped(surf, text, (rect.x + 12, rect.y + 6), rect.w - 24, size, WHITE if unlocked else GREY)
            self._draw_parts(surf, mouse, "ОСМОТРЕТЬ")
            Button(self._v3d_btn_rect(), "ОСМОТР 3D", CYAN).draw(surf, mouse)
        elif self.phase == "repair":
            n = len(job["steps"])
            draw_text(surf, f"РЕМОНТ — шаг {self.step_idx + 1}/{n}", (360, 70), 20, AMBER, bold=True)
            step = job["steps"][self.step_idx]
            draw_wrapped(surf, step["instr"], (360, 100), 560, 19, WHITE)
            if self.last_note:
                draw_wrapped(surf, "✔ " + self.last_note, (360, 175), 560, 15, GOOD)
            # прогресс-полоса шагов
            self._draw_step_dots(surf, n)
            self._draw_parts(surf, mouse, "ДЕТАЛЬ")
            self._draw_tools(surf, mouse)
        elif self.phase == "test":
            draw_text(surf, "ТЕСТ-ДРАЙВ", (360, 70), 20, GOOD, bold=True)
            draw_wrapped(surf, job["test"], (360, 100), 560, 19, WHITE)
            if self.ride_t0 is None:
                Button(self._test_btn_rect(), "ПРОКАТИТЬ И ПРОВЕРИТЬ", GOOD).draw(surf, mouse)
            else:
                self._draw_ride(surf)
        if self.mini_pending:
            self._draw_mini_overlay(surf, mouse)
        if self.v3d is None:
            self._draw_action(surf)
        if self.v3d is not None:
            self._draw_v3d(surf, mouse)
        self._draw_tool_in_hand(surf, mouse)

    def _draw_step_dots(self, surf, n):
        x, y = 360, 205
        for i in range(n):
            c = GOOD if i < self.step_idx else (AMBER if i == self.step_idx else DIM)
            aa_circle(surf, c, (x + i * 22, y), 7)
            if i == self.step_idx:
                aa_circle(surf, AMBER, (x + i * 22, y), 10, 2)

    def _draw_parts(self, surf, mouse, header):
        draw_text(surf, header, (980, 70), 16, AMBER, bold=True)
        for i, (pid, rect) in enumerate(self._part_rects()):
            hov = rect.collidepoint(mouse)
            rect = rect.move(int(160 * (1 - appear(self.st, 0.05 * i, 0.35))), 0)
            aa_rect(surf, PANEL2 if hov else PANEL, rect, border_radius=6)
            aa_rect(surf, AMBER if hov else DIM, rect, 2, border_radius=6)
            r = font(16).render(tr(PARTS[pid]), True, WHITE)
            surf.blit(r, r.get_rect(midleft=(rect.x + 12, rect.centery)))
            if self.phase == "diagnose" and pid in self.inspected:
                draw_text(surf, "✔", (rect.right - 10, rect.centery - 9), 15, GOOD, right=True)

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
                add_glow(surf, r.center, 44, (110, 80, 20), 0.55 + 0.25 * math.sin(self.t * 4))
            tile = Surf(r.size, pygame.SRCALPHA)
            aa_rect(tile, (52, 48, 64, 235), tile.get_rect(), border_radius=12)
            border = AMBER if active else tuple(int(d + (a_ - d) * h) for d, a_ in zip(DIM, GHOST))
            aa_rect(tile, border, tile.get_rect(), 3 if active else 2, border_radius=12)
            if enter < 1:
                tile = TF.rotozoom(tile, 0, enter)
            surf.blit(tile, tile.get_rect(center=r.center))
            ang = 0.0
            if active:
                ang = 7 * math.sin(self.t * 5)
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
        if tid:
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
            draw_wrapped(surf, hint, (info.x + 16, info.y + 12), info.w - 32, 15, GREY)

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
        ic = TF.rotozoom(tool_icon(self.sel_tool, 34), -12 + 4 * math.sin(self.t * 4), 1.0)
        surf.blit(ic, ic.get_rect(center=(mouse[0] + 22, mouse[1] + 20)))

    def _draw_ghost_bubble(self, surf, y=300, col=None):
        if not self.ghost_line:
            return
        if self.ghost_line != getattr(self, "_ghost_seen", None):
            self._ghost_seen = self.ghost_line
            snd("ghost")
        img = "master.png" if self.ghost_line.startswith("Бренна") else "ghost.png"
        if col is not None:                       # узкий пузырь в правой колонке (ремонт)
            bubble = col
            s = Surf(bubble.size, pygame.SRCALPHA)
            s.fill((24, 30, 36, 220))
            surf.blit(s, bubble)
            aa_rect(surf, CYAN, bubble, 2, border_radius=8)
            blit_idle(surf, load_image(img, (46, 56), CYAN), (bubble.x + 6, bubble.y + 6), self.t, "float", phase=1.3)
            tw = bubble.w - 70
            for size in (15, 14, 13, 12):
                if len(wrap_lines(tr(self.ghost_line), tw, size)) * (font(size).get_height() + 2) <= bubble.h - 16:
                    break
            draw_wrapped(surf, self.ghost_line, (bubble.x + 60, bubble.y + 8), tw, size, GHOST,
                         limit=self.typed("ghost", self.ghost_line, cps=90))
            return
        blit_idle(surf, load_image(img, (90, 110), CYAN), (24, y), self.t, "float", phase=1.3)
        bubble = pygame.Rect(120, y, 740, 86)
        s = Surf(bubble.size, pygame.SRCALPHA)
        s.fill((24, 30, 36, 220))
        surf.blit(s, bubble)
        aa_rect(surf, CYAN, bubble, 2, border_radius=8)
        draw_wrapped(surf, self.ghost_line, (bubble.x + 14, bubble.y + 12), bubble.w - 28, 16, GHOST,
                     limit=self.typed("ghost", self.ghost_line, cps=90))

    # ----- tech-задание (Гильдия): свободный порядок операций -----
    def _op_rects(self):
        out = []
        x0, y0, w, h, gx, gy = 200, 150, 520, 52, 16, 10
        per_col = 5
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
        self._topbar(surf, ("ЭКЗАМЕН: " if self.exam_mode else "Гильдия: ") + job["title"])
        mouse = mouse_pos()
        blit_idle(surf, load_image(job["client_art"], (150, 190), GHOST), (24, 70), self.t)
        draw_text(surf, job["client"], (24, 266), 15, WHITE, bold=True)

        if self.phase == "repair":
            head = ("ЭКЗАМЕН ГИЛЬДИИ — подсказок нет, мануал разрешён" if self.exam_mode
                    else "ЗАДАНИЕ ТЕХНИКА — порядок шагов выбираешь сам")
            draw_text(surf, head, (200, 62), 17, CYAN, bold=True)
            draw_wrapped(surf, job["symptom"], (200, 88), 850, 14, WHITE)
            Button(self._manual_btn_rect(), "МАНУАЛ", PURPLE).draw(surf, mouse)
            for sid, rect in self._op_rects():
                st = self.step_by_id(sid)
                done = sid in self.done_steps
                aa_rect(surf, (24, 34, 28) if done else PANEL, rect, border_radius=6)
                DR.rect(surf, GOOD if done else (AMBER if rect.collidepoint(mouse) else DIM),
                                 rect, 2, border_radius=6)
                prefix = "✔ " if done else "• "
                draw_wrapped(surf, prefix + st["instr"], (rect.x + 10, rect.y + 7),
                             rect.w - 20, 13, GREY if done else WHITE)
            lim = f" (лимит {EXAM_MAX_MISTAKES})" if self.exam_mode else ""
            draw_text(surf, f"Выполнено: {len(self.done_steps)}/{len(job['steps'])}   "
                            f"Ошибки: {self.mistakes}{lim}", (200, 466), 14, GHOST)
            self._draw_ghost_bubble(surf, 540)
            self._draw_tools(surf, mouse)
        elif self.phase == "test":
            draw_text(surf, "ПРОВЕРКА ПОД НАГРУЗКОЙ", (360, 70), 20, GOOD, bold=True)
            draw_wrapped(surf, job["test"], (360, 100), 560, 19, WHITE)
            if self.ride_t0 is None:
                Button(self._test_btn_rect(), "ПРОВЕРИТЬ РАБОТУ", GOOD).draw(surf, mouse)
            else:
                self._draw_ride(surf)
            self._draw_ghost_bubble(surf, 540)

        if self.mini_pending:
            self._draw_mini_overlay(surf, mouse)
        if self.spec_pending:
            self._draw_spec_overlay(surf, mouse)
        if self.show_manual:
            self._draw_manual_overlay(surf, mouse)
        if self.v3d is None:
            self._draw_action(surf)
        if self.v3d is not None:
            self._draw_v3d(surf, mouse)
        self._draw_tool_in_hand(surf, mouse)

    # --- оверлей спеки (значение из мануала) ---
    def _spec_panel_rect(self):
        return pygame.Rect(WIDTH // 2 - 370, 140, 740, 460)

    def _spec_option_rects(self):
        p = self._spec_panel_rect()
        n = len(self.spec_pending["spec"]["options"])
        return [(i, pygame.Rect(p.x + 24, p.y + 110 + i * 86, p.w - 48, 74)) for i in range(n)]

    def _spec_manual_rect(self):
        p = self._spec_panel_rect()
        return pygame.Rect(p.x + 24, p.bottom - 60, 220, 46)

    def _spec_cancel_rect(self):
        p = self._spec_panel_rect()
        return pygame.Rect(p.right - 190, p.bottom - 60, 166, 46)

    def _draw_spec_overlay(self, surf, mouse):
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
                      (p.centerx, p.y + 82), 15, AMBER, center=True)
        for i, rect in self._spec_option_rects():
            aa_rect(surf, PANEL, rect, border_radius=8)
            aa_rect(surf, CYAN if viewed else DIM, rect, 2, border_radius=8)
            draw_wrapped(surf, spec["options"][i][0], (rect.x + 14, rect.y + 12),
                         rect.w - 28, 16, WHITE if viewed else GREY)
        Button(self._spec_manual_rect(), "ОТКРЫТЬ МАНУАЛ", PURPLE).draw(surf, mouse)
        Button(self._spec_cancel_rect(), "ПОЗЖЕ", GREY).draw(surf, mouse)

    # --- оверлей мануала Гильдии ---
    def _manual_panel_rect(self):
        return pygame.Rect(140, 80, 1000, 560)

    def _manual_page_rects(self):
        pages = (self.cur.get("manual") if (self.cur and self.cur.get("track") == "tech")
                 else None) or list(MANUAL)
        p = self._manual_panel_rect()
        return [(key, pygame.Rect(p.x + 20, p.y + 70 + i * 54, 270, 46))
                for i, key in enumerate(pages)]

    def _manual_close_rect(self):
        p = self._manual_panel_rect()
        return pygame.Rect(p.right - 200, p.bottom - 64, 180, 46)

    def _draw_manual_overlay(self, surf, mouse):
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
            fit_text(surf, MANUAL[key][0], (rect.x + 10, rect.y + 13), rect.w - 20, 14,
                     WHITE if active else GREY)          # сначала перевод, потом обрезка
        if self.manual_page:
            title, lines = MANUAL[self.manual_page]
            draw_text(surf, title, (p.x + 320, p.y + 70), 20, AMBER, bold=True)
            y = p.y + 110
            for ln in lines:
                y = draw_wrapped(surf, "• " + ln, (p.x + 320, y), p.w - 350, 17, WHITE) + 8
        Button(self._manual_close_rect(), "ЗАКРЫТЬ [Esc]", AMBER).draw(surf, mouse)

    # ----- мини-интеракции: геометрия, клики, отрисовка -----
    def _mini_panel_rect(self):
        return pygame.Rect(WIDTH // 2 - 360, 150, 720, 440)

    def _mini_cancel_rect(self):
        p = self._mini_panel_rect()
        return pygame.Rect(p.right - 160, p.bottom - 56, 140, 42)

    def _mini_pump_rects(self):
        p = self._mini_panel_rect()
        return (pygame.Rect(p.x + 80, p.bottom - 130, 250, 56),
                pygame.Rect(p.right - 330, p.bottom - 130, 250, 56))

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
        return [(i, pygame.Rect(p.x + 40, p.y + 190 + i * 74, p.w - 240, 64)) for i in range(n)]

    def _click_mini(self, m):
        if self._mini_cancel_rect().collidepoint(m):
            self.mini_pending = None
            return
        k = self.mini_pending["kind"]
        if k == "pump":
            b_pump, b_done = self._mini_pump_rects()
            if b_pump.collidepoint(m):
                self.mini_pump()
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
        draw_wrapped(surf, m["step"]["instr"], (p.x + 24, p.y + 16), p.w - 48, 19, WHITE)
        tip = cfg.get("hint") or cfg.get("prompt")
        if tip:
            draw_text(surf, tip, (p.x + 24, p.y + 64), 14, AMBER)
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
        Button(b_done, "ГОТОВО, ПРОВЕРЯЮ", GOOD).draw(surf, mouse)

    def _draw_mini_gap(self, surf, mouse, p, m, cfg):
        tr = self._mini_gap_track()
        aa_rect(surf, PANEL, tr, border_radius=6)
        span = cfg["mx"] - cfg["mn"]
        zx = tr.x + tr.w * (cfg["lo"] - cfg["mn"]) / span
        zw = max(8, tr.w * (cfg["hi"] - cfg["lo"]) / span)
        aa_rect(surf, (40, 70, 48), (zx, tr.y, zw, tr.h), border_radius=6)
        aa_rect(surf, GOOD, (zx, tr.y, zw, tr.h), 2, border_radius=6)
        aa_rect(surf, DIM, tr, 2, border_radius=6)
        vx = tr.x + tr.w * (m["value"] - cfg["mn"]) / span
        aa_rect(surf, CYAN, (vx - 3, tr.y - 8, 6, tr.h + 16), border_radius=3)
        draw_text(surf, str(cfg["mn"]), (tr.x, tr.bottom + 8), 13, GREY)
        draw_text(surf, str(cfg["mx"]), (tr.right, tr.bottom + 8), 13, GREY, right=True)
        label = cfg.get("label", "Значение")
        draw_text(surf, f"{label}: {m['value']} {cfg['unit']}", (tr.centerx, tr.bottom + 34),
                  26, WHITE, bold=True, center=True)
        draw_text(surf, "Кликни по шкале, чтобы выставить значение.",
                  (tr.centerx, tr.bottom + 74), 14, GREY, center=True)
        Button(self._mini_gap_check_rect(), "ПРОВЕРИТЬ", GOOD).draw(surf, mouse)

    def _draw_mini_ping(self, surf, mouse, p, m, cfg):
        cx, cy = p.centerx, p.y + 230
        found = len(m["dull"] & m["tested"])
        draw_text(surf, f"Кликай спицы, ищи глухие. Найдено: {found}/{len(m['dull'])}",
                  (p.centerx, p.y + 96), 15, CYAN, center=True)
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
        draw_text(surf, cfg["reading"], disp.center, 34, GOOD, bold=True, center=True)
        if cfg.get("sub"):
            draw_text(surf, cfg["sub"], (p.centerx, disp.bottom + 8), 13, GREY, center=True)
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
        title = "ЭКЗАМЕН НЕ СДАН" if self.exam_mode else "ПРОВАЛ. РАЗБОР ОШИБКИ"
        shake = int(14 * math.sin(self.st * 42) * max(0.0, 1 - self.st / 0.6))
        draw_text(surf, title, (WIDTH // 2 + shake, 120), 46, BAD, bold=True, center=True)
        card = pygame.Rect(WIDTH // 2 - 420, 190 + int(40 * (1 - appear(self.st, 0.2))), 840, 220)
        s = Surf(card.size, pygame.SRCALPHA)
        s.fill((40, 22, 26, 240))
        surf.blit(s, card)
        aa_rect(surf, BAD, card, 2, border_radius=10)
        draw_wrapped(surf, self.fail_msg, (card.x + 26, card.y + 24), card.w - 52, 19, WHITE)
        brenna = ("Бренна: «Пересдача — не позор. Позор — возить человека на непроверенной коляске.»"
                  if self.exam_mode else
                  "Бренна: «В мастерской ошибка стоит железа. На дороге — жизни. Заново, ученик.»")
        draw_wrapped(surf, brenna, (card.x + 26, 432), card.w - 52, 18, GHOST)
        draw_text(surf, "Барти: «Не красней, Мартин. Меня она гоняла так же. Посмертно.»",
                  (WIDTH // 2, 508), 16, PURPLE, center=True)
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
        add_glow(surf, dip.center, 260, (60, 45, 10), 0.4 + 0.3 * math.sin(self.t * 2))
        draw_text(surf, "— ДИПЛОМ ГИЛЬДИИ КОЛЁСНИКОВ —", (dip.centerx, dip.y + 16), 20,
                  AMBER, bold=True, center=True)
        draw_text(surf, "Мартин, зомби — сертифицированный техник по ремонту кресел-колясок",
                  (dip.centerx, dip.y + 52), 17, WHITE, center=True)
        draw_text(surf, "принято под надзором Мастерицы Бренны (посмертно)",
                  (dip.centerx, dip.y + 84), 13, GREY, center=True)
        draw_wrapped(surf, "Бренна: «Сдано. И вот ещё что, Бартоломью... я помню тебя. "
                           "Ты задавал хорошие вопросы.»", (WIDTH // 2 - 380, 506), 760, 17, GHOST)
        draw_text(surf, "Барти: «...Мартин. МАРТИН. Она меня ПОМНИТ!»",
                  (WIDTH // 2, 562), 16, PURPLE, center=True)
        Button(self._result_btn_rect(), "В ГИЛЬДИЮ", AMBER).draw(surf, mouse_pos())

    # ----- Гильдия Колёсников (хаб про-трека) -----
    def _guild_job_rects(self):
        return [(job["id"], pygame.Rect(60, 170 + i * 116, 560, 96))
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
            rank = ["Ученик Гильдии", "Младший подмастерье", "Подмастерье",
                    "Подмастерье — допуск к экзамену"][min(n, 3)]
        draw_text(surf, f"Мартин — {rank}", (60, 74), 20,
                  GOOD if self.exam_passed else CYAN, bold=True)
        if self.exam_passed:
            draw_text(surf, "✔ ДИПЛОМ ГИЛЬДИИ ПОЛУЧЕН", (60, 106), 15, AMBER, bold=True)
        else:
            draw_wrapped(surf, "Здесь ремонт по-взрослому: порядок шагов выбираешь сам, значения — "
                               "только из мануала, а нарушение техники безопасности проваливает задание.",
                         (60, 104), 680, 14, GREY)
        for i, (jid, rect) in enumerate(self._guild_job_rects()):
            job = self.job_by_id(jid)
            done = jid in self.done
            dx = -int(140 * (1 - appear(self.st, 0.1 * i, 0.45)))
            r = Button(rect, "", GOOD if done else CYAN).draw(surf, mouse, active=done, offset=(dx, 0))
            surf.blit(load_image(job["client_art"], (70, 70), GHOST), (r.x + 10, r.y + 13))
            fit_text(surf, job["title"], (r.x + 96, r.y + 14), r.w - 96 - (96 if done else 14), 18, WHITE, bold=True)
            draw_text(surf, job["client"], (r.x + 96, r.y + 40), 14, GREY)
            draw_text(surf, "УРОВЕНЬ: ТЕХНИК", (r.x + 96, r.y + 64), 12, PURPLE, bold=True)
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
        draw_wrapped(surf, line, (60, 516), 560, 15, GHOST)
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
        hop = int(18 * abs(math.sin(st * 6)) * max(0.0, 1 - st / 1.6))
        blit_idle(surf, cimg, (24, 300 - hop), self.t)
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
        draw_wrapped(surf, job["thanks"], (WIDTH // 2, 185), 760, 20, WHITE, center=True,
                     limit=self.typed("thanks", job["thanks"]) if st > 1.2 else 0)
        # карточка «что ты узнал»
        card = pygame.Rect(WIDTH // 2 - 380, 250 + int(50 * (1 - appear(st, 0.9, 0.5))), 760, 180)
        s = Surf(card.size, pygame.SRCALPHA)
        s.fill((26, 32, 30, 235))
        surf.blit(s, card)
        aa_rect(surf, GHOST, card, 2, border_radius=10)
        draw_text(surf, "ЧТО ТЫ УЗНАЛ (по-настоящему):", (card.x + 24, card.y + 18), 18, GHOST, bold=True)
        draw_wrapped(surf, job["fact"], (card.x + 24, card.y + 54), card.w - 48, 18, WHITE)
        draw_text(surf, self.result_gag, (WIDTH // 2, 470), 17, PURPLE, center=True)
        if self.result_gag in LEG_GAGS and st > 1.4:
            kind = LEG_GAG_KIND[LEG_GAGS.index(self.result_gag)]
            draw_leg_gag(surf, kind, st - 1.4, pygame.Rect(260, 488, 760, 118))
        if self.cur.get("track") == "tech":
            nxt = "В ГИЛЬДИЮ"
        elif self.user_done_count() >= len(JOBS):
            nxt = "НА ВЕЧЕРИНКУ"
        else:
            nxt = "В МАСТЕРСКУЮ"
        Button(self._result_btn_rect(), nxt, AMBER).draw(surf, mouse_pos())

    # ----- гараж -----
    def _back_rect(self):
        return pygame.Rect(40, HEIGHT - 70, 160, 48)

    def draw_garage(self, surf):
        self._bg(surf, "bg_garage.png", PURPLE)
        self._topbar(surf, "Гараж-коллекция")
        if not self.garage:
            draw_text(surf, "Пока пусто. Почини хотя бы одну коляску!", (WIDTH // 2, 300), 22, GREY, center=True)
        n = len(self.garage)
        cols = 3 if n <= 9 else 4       # с заданиями Гильдии коллекция шире
        gx, gy = 20, 20
        cw = (WIDTH - 80 - (cols - 1) * gx) // cols
        ch = 150 if cols == 3 else 128
        art = 120 if cols == 3 else 96
        tx = art + 20
        x0 = (WIDTH - cols * cw - (cols - 1) * gx) // 2
        for i, (jid, stars) in enumerate(self.garage):
            job = self.job_by_id(jid)
            col, row = i % cols, i // cols
            rect = pygame.Rect(x0 + col * (cw + gx), 90 + row * (ch + gy), cw, ch)
            rect = rect.move(0, int(40 * (1 - appear(self.st, 0.06 * i, 0.4))))
            s = Surf(rect.size, pygame.SRCALPHA)
            s.fill((30, 28, 40, 230))
            surf.blit(s, rect)
            aa_rect(surf, PURPLE, rect, 2, border_radius=8)
            surf.blit(load_image(job["chair_art"], (art, art), AMBER),
                      (rect.x + 10, rect.y + (ch - art) // 2))
            fit_text(surf, job["client"], (rect.x + tx, rect.y + 14), cw - tx - 10, 15, WHITE, bold=True)
            fit_text(surf, job["title"], (rect.x + tx, rect.y + 36), cw - tx - 10, 12, GREY)
            draw_text(surf, "★" * stars + "☆" * (3 - stars), (rect.x + tx, rect.y + 56), 18, AMBER)
            if cols == 3:
                lh = font(11).get_height() + 2
                draw_wrapped(surf, job["fact"], (rect.x + tx, rect.y + 80), cw - tx - 12, 11, GHOST,
                             max_lines=max(1, (ch - 86) // lh))
        Button(self._back_rect(), "НАЗАД", AMBER).draw(surf, mouse_pos())

    # ----- финал -----
    def draw_ending(self, surf):
        self._bg(surf, "bg_party.png", GHOST)
        st = self.st
        # Мартин танцует в коляске (качается и подпрыгивает), Барти кружит рядом
        rock = 6 * math.sin(self.t * 4.2)
        bounce = int(8 * abs(math.sin(self.t * 4.2)))
        mx = -260 + int(320 * ease_out(st / 1.2))
        blit_idle(surf, load_image("martin.png", (240, 270), GHOST), (mx, HEIGHT - 290 - bounce), self.t,
                  rock=rock)
        blit_idle(surf, load_image("ghost.png", (170, 220), CYAN), (WIDTH - 230, HEIGHT - 300), self.t,
                  "float", rock=8 * math.sin(self.t * 2.1), k=ease_back((st - 0.6) / 0.6))
        draw_confetti(surf, self.t)
        panel = pygame.Rect(WIDTH // 2 - 440, 205, 880, 270)
        pk = appear(st, 0.5, 0.5)
        ps = Surf(panel.size, pygame.SRCALPHA)
        aa_rect(ps, (18, 16, 30, int(200 * pk)), ps.get_rect(), border_radius=14)
        surf.blit(ps, panel)
        self._wave_title(surf, "ВЕЧЕРИНКА!", (WIDTH // 2, 140), 60, AMBER, st)
        draw_wrapped(surf,
                     "Мартин докатил до друзей на отремонтированной коляске. Левая нога снова "
                     "отвалилась у самого входа — но коляска едет идеально, а это главное.",
                     (WIDTH // 2, 230), 800, 20, WHITE, center=True)
        draw_wrapped(surf,
                     "Бартоломью: «Ты научился чинить лучше, чем я когда-либо видел. "
                     "Горжусь, парень. Теперь — танцуй.»",
                     (WIDTH // 2, 330), 800, 19, GHOST, center=True)
        draw_text(surf, f"Коллекция: {len(self.garage)} колясок починено и спасено.",
                  (WIDTH // 2, 430), 18, PURPLE, center=True)
        draw_text(surf, "[ клик — посмотреть гараж ]", (WIDTH // 2, 510), 20, AMBER, center=True,
                  alpha=150 + 105 * (0.5 + 0.5 * math.sin(self.t * 3.2)))


# ----------------------------------------------------------------------------- #
#  Self-test (headless): полная проверка логики без окна
# ----------------------------------------------------------------------------- #
def run_selftest():
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
    for sid in ("w_recheck", "w_even", "w_back"):
        st = g.step_by_id(sid)
        assert g.do_tech_action(st["tool"], sid) == "ok", f"truing: шаг {sid} не принят"
    assert g.phase == "test"
    g.finish_test()
    assert "truing" in g.done

    # safety-провал: клеммы при включённом питании
    g = Game(headless=True)
    g.start_job("t_battery")
    assert g.do_tech_action("screw", "p_open") == "ok"
    assert g.do_tech_action("wrench", "p_disc_neg") == "fail"
    assert g.scene == "failed", "работа с клеммами при включённом питании должна проваливать задание"

    # safety-провал: плюс раньше минуса при разборке
    g = Game(headless=True)
    g.start_job("t_battery")
    for sid in ("p_off", "p_open"):
        st = g.step_by_id(sid)
        g.do_tech_action(st["tool"], sid)
    assert g.do_tech_action("wrench", "p_disc_pos") == "fail", "снятие плюса до минуса должно проваливать"

    # корректное прохождение замены батарей целиком
    g = Game(headless=True)
    g.start_job("t_battery")
    order = ["p_off", "p_open", "p_disc_neg", "p_disc_pos", "p_out",
             "p_pick", "p_in", "p_conn_pos", "p_conn_neg", "p_charge"]
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
    g.choose_diagnosis(0)
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
    pygame.event.clear()
    _esc(g)
    assert any(e.type == pygame.QUIT for e in pygame.event.get()), \
        "Esc с титула должен закрывать игру"
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
            if job.get("chair_art") in AI_MODELS:       # у коляски своя детальная модель — проверяется ниже
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
        good = dict(depth=b["thigh"] - 5, leg=b["shank"], back_h=sum(case["back"]) // 2,
                    back_a=sum(case["angle"]) // 2, tilt=case.get("tilt", 0))
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

    # 3D в окне диагностики: у каждой детали задания есть кружок, кружки не перекрываются
    if _np is not None:
        for base in JOBS:
            for job in _resolved(base):
                gq = Game(headless=True)
                gq.cur = job
                gq.phase = "diagnose"
                gq.inspected = set()
                if gq._m3d_mesh() is None:
                    continue
                spots = gq._chair_hotspots()
                miss = [p for p in job["parts"] if p not in {q[0] for q in spots}]
                if miss:
                    failures.append(f"3D-окно {job['id']}: нет кружков у {miss}")
                for i, (p1, x1, y1, r1) in enumerate(spots):
                    for p2, x2, y2, r2 in spots[i + 1:]:
                        if (x1 - x2) ** 2 + (y1 - y2) ** 2 < (r1 + r2 - 2) ** 2:
                            failures.append(f"3D-окно {job['id']}: кружки {p1} и {p2} перекрываются")
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


def main():
    _crash_log = _install_crash_log()
    if "--assets" in sys.argv:
        print_assets()
        return
    if "--selftest" in sys.argv:
        run_selftest()
        return
    if "--feedback" in sys.argv:                            # замечания «Я не согласен» от игроков
        try:
            data = json.load(open(FEEDBACK_PATH, encoding="utf-8"))
        except Exception:
            data = []
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
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    if "--mute" not in sys.argv:
        build_sounds()
    set_lang(LANG["code"])
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            want_full = bool(json.load(f).get("fullscreen"))
    except Exception:
        want_full = False
    if "--window" in sys.argv:
        want_full = False
    global RS
    GL["off"] = "--nogl" in sys.argv or bool(os.environ.get("WNB_NOGL"))
    if "--rs" in sys.argv[:-1]:
        RS = float(sys.argv[sys.argv.index("--rs") + 1])
    else:
        RS = pick_render_scale()
    screen = init_display(want_full)
    if _crash_log:                                          # какой 3D-рендер включился — в журнал запуска
        try:
            info = GL["ctx"].info["GL_RENDERER"] if gl_ok() else ("выключен" if GL["off"] else "недоступен")
        except Exception:
            info = "ошибка"
        _crash_log.write(f"RS {RS}, 3D: GPU {info}" + chr(10))
        _crash_log.flush()
    frame = Surf((WIDTH, HEIGHT))                     # кадр в логических координатах, пиксели — экранные
    clock = pygame.time.Clock()
    game = Game()
    if "--unlock" in sys.argv:   # предпросмотр: всё открыто, включая Гильдию
        game.done.update(j["id"] for j in JOBS)
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                if RS != 1 and event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    d = dict(event.dict)
                    d["pos"] = (int(d["pos"][0] / RS), int(d["pos"][1] / RS))
                    if "rel" in d:
                        d["rel"] = (d["rel"][0] / RS, d["rel"][1] / RS)
                    event = pygame.event.Event(event.type, d)
                game.handle_event(event)
        game.update(dt)
        game.draw(frame)
        screen.blit(frame, (0, 0))
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
