class_name UI
## Общее оформление: цвета и шрифты игры (как в game.py), размеры текста × TEXT_K, рисование текста «как pygame»
## (pos — левый верх / центр / правый верх строки), перенос строк по словам (wrap_lines), изинги «Без анимации».

const W := 1280
const H := 720

# палитра game.py (самопроверка сверяет с content/data/game_consts.json)
const BG := Color8(24, 22, 30)
const PANEL := Color8(38, 34, 48)
const PANEL2 := Color8(50, 44, 64)
const WOOD := Color8(92, 64, 44)
const GHOST := Color8(130, 240, 200)
const AMBER := Color8(240, 190, 90)
const RUST := Color8(210, 120, 70)
const GOOD := Color8(120, 230, 140)
const BAD := Color8(235, 100, 110)
const CYAN := Color8(110, 210, 235)
const PURPLE := Color8(180, 140, 240)
const WHITE := Color8(236, 238, 245)
const GREY := Color8(150, 150, 165)
const DIM := Color8(90, 88, 104)
const INK := Color8(14, 12, 20)            # тёмная подложка колец и цифр
const BAR := Color8(16, 14, 22)            # шапка экрана

const PALETTE := {"BG": BG, "PANEL": PANEL, "PANEL2": PANEL2, "WOOD": WOOD, "GHOST": GHOST, "AMBER": AMBER,
	"RUST": RUST, "GOOD": GOOD, "BAD": BAD, "CYAN": CYAN, "PURPLE": PURPLE, "WHITE": WHITE, "GREY": GREY, "DIM": DIM}

const FONT_DIR := "res://content/fonts/"

static var kb_active := false              # последним был ввод с клавиатуры/геймпада — видна рамка фокуса
static var _fonts: Dictionary = {}
static var _glow_tex: Texture2D
# Кэши текста (скорость на слабом процессоре, 19.11): экраны перерисовывают текст каждый кадр, а у Font свой кэш
# раскладки строк — 64 строки (LRU): мастерская и задание рисуют больше, плюс wrap_lines меряет каждое «слово +
# строка» — кэш вытеснялся, и каждый кадр строки заново шейпились. Здесь: ширина строки, перенос по словам и
# готовая раскладка строки (TextLine) — по (шрифт, размер в px, текст); сброс — со сменой шрифтов (clear_font_cache).
const TEXT_CACHE_MAX := 6000              # строк в каждом кэше; больше — сброс (смена языка/текста, длинная игра)
static var _tw: Dictionary = {}           # "b|px" → {текст: ширина}
static var _wraps: Dictionary = {}        # "текст|ширина|размер|b" → PackedStringArray
static var _tl: Dictionary = {}           # "b|px" → {текст: TextLine}
static var _tl_n: int = 0
static var _tw_n: int = 0
static var _sb: Dictionary = {}           # [заливка, рамка, толщина, радиус] → StyleBoxFlat


# ---------------- шрифты и размеры ----------------

## Шрифт игры: DejaVu Sans (обычный/жирный); с «шрифтом для лёгкого чтения» в английском — Atkinson Hyperlegible
## (чуть крупнее, ×1,08, как в game.py), а значков, которых в нём нет (✔ ⚑ ▸ ⟲…), — из DejaVu (запасной шрифт).
static func font(bold: bool = false) -> Font:
	var easy := Settings.easy_font()
	var key := "%s_%s" % [bold, easy]
	if _fonts.has(key):
		return _fonts[key]
	var dejavu := load(FONT_DIR + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")) as Font
	var f: Font = dejavu
	if easy:
		var atk := load(FONT_DIR + ("AtkinsonHyperlegible-Bold.ttf" if bold else "AtkinsonHyperlegible-Regular.ttf")) as FontFile
		if atk:
			var v := FontVariation.new()
			v.base_font = atk
			v.variation_transform = Transform2D.IDENTITY
			v.fallbacks = [dejavu]
			f = v
	_fonts[key] = f
	return f


static var _touch: int = -1


## Сенсорный экран (TOUCH["on"] в game.py): в браузере — `(pointer: coarse)`, как web_setup_touch; тогда подписи
## «тап/коснись» вместо «клик/кликни», без подсказок клавиш на титуле (21.11: раньше смотрели OS.has_feature("mobile"),
## а в браузере на телефоне его нет — на телефоне было «[ клик — начать ]» и «F1 — управление с клавиатуры»).
static func touch() -> bool:
	if _touch < 0:
		_touch = 0
		if OS.has_feature("web"):
			var r: Variant = JavaScriptBridge.eval("(window.wnbEnv ? window.wnbEnv.touch : (window.matchMedia && " \
				+ "matchMedia('(pointer: coarse)').matches)) ? 'y' : 'n'", true)   # 28.11: общее правило страницы (shell.html)
			_touch = 1 if str(r) == "y" else 0
		elif OS.has_feature("mobile"):
			_touch = 1
	return _touch == 1


static var _phone: int = -1
const PHONE_MIN := 56                     # телефонный режим: цель для пальца не меньше 56 px холста (28 CSS px ≈ 7 мм)
const PHONE_GAP := 8                      # и зазор между соседними целями


## 28.11 (отзыв с iPhone): в браузере — window.wnbEnv страницы (shell.html): маленький экран И (pointer/any-pointer
## coarse, maxTouchPoints, UA Android Mobile) или UA iPhone; ниже — запасной путь, если wnbEnv нет.
## Телефонный режим (21.11, владелец: «цели для пальца крупнее»): сенсорный экран (touch()) И маленький экран —
## в браузере `(pointer: coarse)` и меньшая сторона экрана < 600 CSS px (телефон; планшет — нет). Считается один раз
## при старте. Принудительно: адрес `?phone=1|0`, web_smoke `set:phone=1|0`, самопроверка — set_phone(). Вне
## телефонного режима раскладка и поведение прежние, байт в байт.
static func phone() -> bool:
	if _phone < 0:
		_phone = 0
		if "--phone" in OS.get_cmdline_user_args():      # компьютер, снимки: «-- --phone»
			_phone = 1
		elif OS.has_feature("web"):
			var r: Variant = JavaScriptBridge.eval("(function(){if(window.wnbEnv)return window.wnbEnv.phone?'y':'n';" \
				+ "try{var q=new URLSearchParams(location.search).get('phone');" \
				+ "if(q==='1')return 'y';if(q==='0')return 'n';}catch(e){}" \
				+ "var c=!!(window.matchMedia&&matchMedia('(pointer: coarse)').matches);" \
				+ "return (c&&Math.min(screen.width,screen.height)<600)?'y':'n';})()", true)
			_phone = 1 if str(r) == "y" else 0
		elif OS.has_feature("mobile") and touch():
			var s := DisplayServer.screen_get_size()
			var sc := maxf(DisplayServer.screen_get_scale(), 1.0)
			_phone = 1 if minf(s.x, s.y) / sc < 600 else 0
	return _phone == 1


## Включить/выключить телефонный режим (проверки): экраны и окна пересобираются, как при смене размера текста.
static func set_phone(on: bool) -> void:
	if _phone >= 0 and (_phone == 1) == on:      # ещё не считали (−1) — выключение тоже применяется (E29.6)
		return
	_phone = 1 if on else 0
	Settings.changed.emit("phone")


## Сообщение сверху (Screen.toast_bounds: [левый край, запас справа]) — в телефонном режиме мимо значков 56×56:
## «назад» до x 60, ⚑ с W−192, RU/EN с W−128, ⚙ с W−60.
static func phone_bounds(b: Vector2) -> Vector2:
	if not phone():
		return b
	var y: float = {164.0: 202.0, 112.0: 136.0, 56.0: 66.0}.get(b.y, b.y)
	return Vector2(b.x + 14 if b.x >= 54 else b.x, y)


## Размер в телефонном режиме: v (телефон) или d (как было).
static func ph(d: float, v: float) -> float:
	return v if phone() else d


# ---- запас на промах пальцем (game.py: TOUCH_PAD, _touch_pick, _touch_snap, Game._tap) ----
# Только на сенсорном экране (touch()); с мышью попадания точные, как были. Числа — в единицах холста 1280×720.
const TOUCH_PAD := 16                     # TOUCH_PAD: тап не дальше 16 px от края цели — в цель
const TOUCH_TAP_GROW := 9                 # Game._tap: значки шапки rect.inflate(18, 18) — по 9 px с каждой стороны
const TOUCH_SPOT_PAD := 16                # _hotspot_at: кружок детали r + 16 (мышь — r + 4)


## Цель не участвует в переносе тапа (Nav.touch_snap): кнопки, которых нет в списках целей game.py.
static func touch_skip(c: Control, on: bool = true) -> void:
	c.set_meta("touch_skip", on)


## Зона, где тап не переносится (block в _touch_snap): окно коляски, ползунки… grow — запас по каждой стороне.
static func touch_block(c: Control, grow: Vector2 = Vector2.ZERO) -> void:
	c.add_to_group("touch_block")
	c.set_meta("touch_grow", grow)


## _touch_pick из game.py: индекс прямоугольника под пальцем. Точное попадание — первое в списке; иначе (только на
## сенсорном экране) — ближайший, до края которого не дальше pad (при равенстве — ближайший по центру). Нет — −1.
## Край — как у pygame.Rect: последний пиксель right − 1 / bottom − 1.
static func touch_pick(rects: Array, p: Vector2, pad: float = TOUCH_PAD, on: bool = touch()) -> int:
	for i in rects.size():
		if (rects[i] as Rect2).has_point(p):
			return i
	if not on:
		return -1
	var best := -1
	var bd := INF
	var bc := INF
	for i in rects.size():
		var r: Rect2 = rects[i]
		if r.size.x <= 0 or r.size.y <= 0:
			continue
		var dx := maxf(maxf(r.position.x - p.x, 0.0), p.x - (r.end.x - 1))
		var dy := maxf(maxf(r.position.y - p.y, 0.0), p.y - (r.end.y - 1))
		var d := sqrt(dx * dx + dy * dy)
		if d <= pad:
			var dc := p.distance_to(r.get_center())
			if d < bd or (d == bd and dc < bc):
				best = i
				bd = d
				bc = dc
	return best


## _touch_snap из game.py: палец чуть мимо цели — точка переносится в центр ближайшей цели (не дальше TOUCH_PAD).
## Точное попадание в цель или в зону block (Rect2 или Control — по его попаданию) — точку не трогаем.
static func touch_snap(p: Vector2, targets: Array, block: Array = [], on: bool = touch()) -> Vector2:
	if not on:
		return p
	for r: Rect2 in targets:
		if r.has_point(p):
			return p
	for b: Variant in block:
		if (b is Rect2 and (b as Rect2).has_point(p)) or (b is Control and hits(b as Control, p)):
			return p
	var i := touch_pick(targets, p, TOUCH_PAD, true)
	return (targets[i] as Rect2).get_center() if i >= 0 else p


## Попадает ли точка холста p в элемент так, как его выберет Godot (с _has_point кнопок игры).
static func hits(c: Control, p: Vector2) -> bool:
	var lp := c.get_global_transform().affine_inverse() * p
	if c.get_script() != null and c.has_method("_has_point"):     # свои зоны: кружок детали, портрет, значки
		return c.call("_has_point", lp)
	return Rect2(Vector2.ZERO, c.size).has_point(lp)


static func clear_font_cache() -> void:
	_fonts.clear()
	clear_text_cache()


static func clear_text_cache() -> void:
	_tw.clear()
	_wraps.clear()
	_tl.clear()
	_tl_n = 0
	_tw_n = 0


## Размер шрифта в пикселях холста — как LFont в game.py: px = max(1, round(size × text_k())), у Atkinson
## («лёгкий шрифт») max(1, round(px × 1,08)); round — питоновский (половина к чётному: 22,5 → 22, 27,5 → 28), а не
## roundi (половина вверх): при 125 % и 150 % размеры с ,5 были на 1 px крупнее, чем в game.py.
static func fs(size: float) -> int:
	var px := maxi(1, py_round(size * Settings.text_k()))
	if Settings.easy_font():
		px = maxi(1, py_round(px * 1.08))
	return px


## round(x) Python 3: половина — к ближайшему чётному.
static func py_round(x: float) -> int:
	var f := floorf(x)
	var d := x - f
	if d > 0.5:
		return int(f) + 1
	if d < 0.5:
		return int(f)
	return int(f) if posmod(int(f), 2) == 0 else int(f) + 1


static func text_width(text: String, size: float, bold: bool = false) -> float:
	return px_width(text, fs(size), bold)


## Ширина строки в пикселях шрифта px (кэш: Font.get_string_size шейпит строку, если она выпала из его кэша).
static func px_width(text: String, px: int, bold: bool) -> float:
	var p0 := Prof.t0() if Prof.on else 0
	var k := "%s|%d" % [bold, px]
	var d: Dictionary = _tw.get(k, {})
	if d.is_empty():
		_tw[k] = d
	var w: Variant = d.get(text)
	if w == null:
		if _tw_n >= TEXT_CACHE_MAX:
			_tw.clear()
			_tw_n = 0
			d = {}
			_tw[k] = d
		w = font(bold).get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x
		d[text] = w
		_tw_n += 1
	if Prof.on:
		Prof.add("text_width", p0)
	return w


## Готовая раскладка строки (TextLine) — как у Font.draw_string, но в своём кэше без вытеснения каждый кадр.
static func text_line(text: String, px: int, bold: bool) -> TextLine:
	var k := "%s|%d" % [bold, px]
	var d: Dictionary = _tl.get(k, {})
	if d.is_empty():
		_tl[k] = d
	var tl: TextLine = d.get(text)
	if tl == null:
		if _tl_n >= TEXT_CACHE_MAX:
			_tl.clear()
			_tl_n = 0
			d = {}
			_tl[k] = d
		tl = TextLine.new()
		tl.add_string(text, font(bold), px)
		d[text] = tl
		_tl_n += 1
	return tl


## Строка от базовой линии (как CanvasItem.draw_string с выравниванием влево и без ширины).
static func put_string(ci: CanvasItem, baseline: Vector2, text: String, px: int, color: Color, bold: bool) -> void:
	var tl := text_line(text, px, bold)
	tl.draw(ci.get_canvas_item(), Vector2(baseline.x, baseline.y - tl.get_line_ascent()), color)


static func line_height(size: float, bold: bool = false) -> float:
	return px_height(fs(size), bold)


## Высота строки шрифта в пикселях как у pygame (SDL_ttf): ceil((ascender − descender) × px / em). У DejaVu Sans
## это 2384/2048 — на 1 px меньше, чем font.get_height() Godot на части размеров; без этого строки и раскладка
## (_chair_rect зависит от высоты строк симптома) съезжают на 1–2 px. У Atkinson — как считает Godot.
static func px_height(px: int, bold: bool = false) -> float:
	if Settings.easy_font():
		# как LFont.get_height в game.py: max(DejaVu размера base, Atkinson размера px = round(base × 1,08)); у SDL_ttf
		# высота — ceil((ascender − descender) × px / em): Atkinson 1240/1000. font.get_height() Godot — иначе (на 1–3 px
		# больше: межстрочный уроков посадки был шире, текст не влезал)
		var base := py_round(px / 1.08)
		for b in [base - 1, base + 1]:
			if py_round(b * 1.08) == px:
				base = b
		return maxf(ceilf(base * 2384.0 / 2048.0 - 0.0001), ceilf(px * 1240.0 / 1000.0 - 0.0001))
	return ceilf(px * 2384.0 / 2048.0 - 0.0001)


## Минимальный размер подписи кнопки (_min_btn_sz): при крупном тексте — те же экранные пиксели.
static func min_btn_size() -> int:
	return maxi(8, py_round(11.0 / Settings.text_k()))


## Размер, при котором строка влезает в ширину (не меньше lo); как циклы `while sz > … and size > w: sz -= 1`.
static func fit_size(text: String, width: float, size: int, lo: int, bold: bool = false) -> int:
	var sz := size
	while sz > lo and text_width(text, sz, bold) > width:
		sz -= 1
	return sz


## Перенос по словам (wrap_lines game.py; text — уже переведённый): слово шире строки режется по дефису.
static func wrap_lines(text: String, width: float, size: float, bold: bool = false) -> PackedStringArray:
	var p0 := Prof.t0() if Prof.on else 0
	var key := "%s|%s|%d|%s" % [text, width, fs(size), bold]
	var hit: Variant = _wraps.get(key)
	if hit != null:
		if Prof.on:
			Prof.add("wrap_lines", p0)
		return (hit as PackedStringArray).duplicate()
	if _wraps.size() >= TEXT_CACHE_MAX:
		_wraps.clear()
	var out := _wrap_lines(text, width, size, bold)
	_wraps[key] = out.duplicate()
	if Prof.on:
		Prof.add("wrap_lines", p0)
	return out


static func _wrap_lines(text: String, width: float, size: float, bold: bool) -> PackedStringArray:
	var out: PackedStringArray = []
	var cur := ""
	for w in text.split(" "):
		var test := (cur + " " + w).strip_edges()
		if text_width(test, size, bold) <= width:
			cur = test
		else:
			if cur != "":
				out.append(cur)
			cur = w
			while text_width(cur, size, bold) > width and cur.substr(1, cur.length() - 2).contains("-"):
				var cuts: Array[int] = []
				for j in range(1, cur.length() - 1):
					if cur[j] == "-":
						cuts.append(j)
				var j := cuts[0]
				for c in cuts:
					if text_width(cur.substr(0, c + 1), size, bold) <= width:
						j = c
				out.append(cur.substr(0, j + 1))
				cur = cur.substr(j + 1)
	if cur != "":
		out.append(cur)
	return out


## Обрезать строку с «…», чтобы влезла (fit_text: сначала шрифт до 75 %, потом «…»). Возврат [текст, размер].
static func fit_text(text: String, width: float, size: int, bold: bool = false) -> Array:
	var sz := fit_size(text, width, size, int(size * 0.75), bold)
	var s := text
	if text_width(s, sz, bold) > width:
		while s != "" and text_width(s + "…", sz, bold) > width:
			s = s.substr(0, s.length() - 1)
		s = s.strip_edges(false, true) + "…"
	return [s, sz]


## Строка не шире width (draw_text_w game.py, крупный текст 150 %): помещается — ровно draw_text, нет — fit_text
## (кегль меньше до 75 %, сдвиг вниз на (size − sz) // 2 — середина строки на месте; «…» — только если и так не влезла).
static func draw_text_w(ci: CanvasItem, text: String, pos: Vector2, width: float, size: int, color: Color,
		bold: bool = false) -> Rect2:
	if text_width(text, size, bold) <= width:
		return draw_text(ci, text, pos, size, color, bold)
	var f: Array = fit_text(text, width, size, bold)
	return draw_text(ci, f[0], pos + Vector2(0, floorf((size - int(f[1])) / 2.0)), f[1], color, bold)


## Кегль блока с переносом, при котором строки занимают не больше room по высоте (fit_wrapped_size game.py).
static func fit_wrapped_size(text: String, width: float, size: int, room: float, lo: int = 10,
		line_gap: float = 2.0) -> int:
	var sz := size
	while sz > lo and wrap_lines(text, width, sz).size() * (line_height(sz) + line_gap) - line_gap > room:
		sz -= 1
	return sz


# ---------------- рисование текста как в pygame ----------------

## Нарисовать строку (уже переведённую). align: 0 — pos левый верх, 1 — центр, 2 — правый верх (как draw_text).
## Возврат: прямоугольник текста.
static func draw_text(ci: CanvasItem, text: String, pos: Vector2, size: float, color: Color, bold: bool = false,
		align: int = 0) -> Rect2:
	var p0 := Prof.t0() if Prof.on else 0
	var f := font(bold)
	var px := fs(size)
	var w := px_width(text, px, bold)
	var h := px_height(px, bold)
	var tl := pos
	if align == 1:
		tl = pos - Vector2(w, h) / 2.0
	elif align == 2:
		tl = pos - Vector2(w, 0)
	put_string(ci, Vector2(roundf(tl.x), roundf(tl.y) + f.get_ascent(px)), text, px, color, bold)
	if Prof.on:
		Prof.add("draw_text", p0)
	return Rect2(tl, Vector2(w, h))


## Строки с переносом (draw_wrapped): pos — левый верх (center — середина верхнего края); limit — сколько символов
## напечатано («печать по буквам», переносы — по полному тексту). Возврат: y под последней строкой.
static func draw_wrapped(ci: CanvasItem, text: String, pos: Vector2, width: float, size: float, color: Color,
		center: bool = false, line_gap: float = 2.0, limit: int = -1, max_lines: int = 0, bold: bool = false) -> float:
	var p0 := Prof.t0() if Prof.on else 0
	var f := font(bold)
	var px := fs(size)
	var lines := wrap_lines(text, width, size, bold)
	if max_lines > 0 and lines.size() > max_lines:
		lines = lines.slice(0, max_lines)
		var last := lines[lines.size() - 1]
		while last != "" and text_width(last + "…", size, bold) > width:
			last = last.substr(0, last.length() - 1)
		lines[lines.size() - 1] = last.rstrip(" ,.;:—") + "…"
	var left := text.length() if limit < 0 else limit
	var y := pos.y
	var at := 0
	for ln in lines:
		var shown := ln
		if left < ln.length():
			shown = ln.substr(0, maxi(0, left))
		if shown != "":
			var x := pos.x - (px_width(ln, px, bold) / 2.0 if center else 0.0)
			put_string(ci, Vector2(roundf(x), roundf(y) + f.get_ascent(px)), shown, px, color, bold)
		var found := text.find(ln, at)
		var step := ln.length() + 1
		if found >= 0:
			at = found + ln.length()
			step = ln.length() + (1 if text.substr(at, 1) == " " else 0)
		left -= step
		y += px_height(px, bold) + line_gap
	if Prof.on:
		Prof.add("draw_wrapped", p0)
	return y


## Высота блока строк с переносом.
static func wrapped_height(text: String, width: float, size: float, line_gap: float = 2.0, bold: bool = false) -> float:
	var n := wrap_lines(text, width, size, bold).size()
	return n * (line_height(size, bold) + line_gap)


# ---------------- фигуры ----------------

static func draw_round_rect(ci: CanvasItem, r: Rect2, fill: Color, border: Color = Color(0, 0, 0, 0),
		width: int = 0, radius: int = 7) -> void:
	if Prof.on:
		Prof.count("round_rect")
	var key := [fill, border if width > 0 else Color(), width, radius]
	var sb: StyleBoxFlat = _sb.get(key)
	if sb == null:
		if _sb.size() >= 400:                 # наведение плавно меняет заливку — без потолка кэш рос бы
			_sb.clear()
		sb = StyleBoxFlat.new()
		sb.bg_color = fill
		sb.set_corner_radius_all(radius)
		sb.anti_aliasing = true
		sb.corner_detail = 8
		if width > 0:
			sb.border_color = border
			sb.set_border_width_all(width)
		_sb[key] = sb
	ci.draw_style_box(sb, r)


static func draw_ring(ci: CanvasItem, c: Vector2, r: float, color: Color, width: float) -> void:
	ci.draw_arc(c, r - width / 2.0, 0.0, TAU, maxi(24, int(r * 1.5)), color, width, true)


## Мягкое свечение (add_glow): радиальное пятно, рисовать в узле с CanvasItemMaterial BLEND_MODE_ADD.
static func glow_texture() -> Texture2D:
	if _glow_tex == null:
		var n := 64
		var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
		for y in n:
			for x in n:
				var d := Vector2(x + 0.5 - n / 2.0, y + 0.5 - n / 2.0).length() / (n / 2.0)
				var k := pow(maxf(0.0, 1.0 - d), 2.0)
				img.set_pixel(x, y, Color(k, k, k, 1.0))
		_glow_tex = ImageTexture.create_from_image(img)
	return _glow_tex


static func draw_glow(ci: CanvasItem, pos: Vector2, radius: float, color: Color, level: float = 1.0) -> void:
	var q := clampi(int(level * 8 + 0.5), 0, 8)
	if q == 0 or radius < 1:
		return
	var k := q / 8.0
	ci.draw_texture_rect(glow_texture(), Rect2(pos - Vector2(radius, radius), Vector2(radius, radius) * 2), false,
		Color(color.r * k, color.g * k, color.b * k, 1.0))


# ---------------- анимация (без состояния, от времени) ----------------

static func ease_out(x: float) -> float:
	if Settings.calm():
		return 1.0
	x = clampf(x, 0.0, 1.0)
	return 1.0 - pow(1.0 - x, 3.0)


static func ease_back(x: float, s: float = 1.70158) -> float:
	if Settings.calm():
		return 1.0
	x = clampf(x, 0.0, 1.0) - 1.0
	return 1.0 + (s + 1.0) * x * x * x + s * x * x


static func appear(st: float, delay: float = 0.0, dur: float = 0.45) -> float:
	return ease_out((st - delay) / dur)


static func wsin(x: float) -> float:
	return 0.0 if Settings.calm() else sin(x)


static func lerp_color(a: Color, b: Color, k: float) -> Color:
	return a.lerp(b, clampf(k, 0.0, 1.0))


## Заголовок: буквы падают по очереди с перелётом, потом мягко «дышат» волной (_wave_title в game.py).
static func wave_title(ci: CanvasItem, text_ru: String, center: Vector2, size: int, color: Color, st: float, t: float,
		max_w: float = 0.0) -> void:
	var text := Loc.t(text_ru)
	while max_w > 0 and size > 30 and text_width(text, size, true) > max_w:
		size -= 2
	var f := font(true)
	var px := fs(size)
	var x := center.x - floorf(text_width(text, size, true) / 2.0)
	var asc := f.get_ascent(px)
	var hh := floorf(px_height(px, true) / 2.0)
	for i in text.length():
		var ch := text[i]
		var d := 0.05 * i
		var k := ease_back((st - d) / 0.55)
		var a := 1.0 if Settings.calm() else clampf((st - d) / 0.2, 0.0, 1.0)
		var y := center.y - hh - int(70 * (1 - k)) + 4 * wsin(t * 2.2 + i * 0.55)
		if a > 0 and ch != " ":
			ci.draw_string(f, Vector2(x + 3, y + 4 + asc), ch, HORIZONTAL_ALIGNMENT_LEFT, -1, px, Color(Color8(20, 14, 10), a * 0.5))
			ci.draw_string(f, Vector2(x, y + asc), ch, HORIZONTAL_ALIGNMENT_LEFT, -1, px, Color(color, a))
		x += f.get_string_size(ch, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x


## Картинка вписана в прямоугольник с сохранением пропорций, по центру (load_image(name, size)).
static func fit_rect(tex_size: Vector2, box: Rect2) -> Rect2:
	var k := minf(box.size.x / tex_size.x, box.size.y / tex_size.y)
	var s := tex_size * k
	return Rect2(box.position + (box.size - s) / 2.0, s)


## Отдать фокус на следующем кадре, если элемент ещё на экране (между кадрами экран могли сменить).
static func focus_later(c: Control) -> void:
	if c != null:
		_focus_now.call_deferred(c)


static func _focus_now(c: Variant) -> void:
	if is_instance_valid(c) and c is Control and (c as Control).is_inside_tree() and (c as Control).is_visible_in_tree() 			and (c as Control).focus_mode != Control.FOCUS_NONE:
		(c as Control).grab_focus()


## Включить/выключить фокус у всех элементов поддерева (модальное окно поверх экрана: Tab не уходит под него).
static func set_focus_enabled(root: Node, on: bool) -> void:
	for c in root.get_children():
		if c is Control:
			var ctl := c as Control
			if not on:
				if ctl.focus_mode != Control.FOCUS_NONE:
					ctl.set_meta("_focus_mode", ctl.focus_mode)
					ctl.focus_mode = Control.FOCUS_NONE
			elif ctl.has_meta("_focus_mode"):
				ctl.focus_mode = ctl.get_meta("_focus_mode")
				ctl.remove_meta("_focus_mode")
		set_focus_enabled(c, on)
