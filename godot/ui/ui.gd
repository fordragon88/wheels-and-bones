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


static func clear_font_cache() -> void:
	_fonts.clear()


## Размер шрифта в пикселях холста: логический размер game.py × TEXT_K (× 1,08 у Atkinson).
static func fs(size: float) -> int:
	var k := Settings.text_k() * (1.08 if Settings.easy_font() else 1.0)
	return maxi(1, roundi(size * k))


static func text_width(text: String, size: float, bold: bool = false) -> float:
	return font(bold).get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs(size)).x


static func line_height(size: float, bold: bool = false) -> float:
	return px_height(fs(size), bold)


## Высота строки шрифта в пикселях как у pygame (SDL_ttf): ceil((ascender − descender) × px / em). У DejaVu Sans
## это 2384/2048 — на 1 px меньше, чем font.get_height() Godot на части размеров; без этого строки и раскладка
## (_chair_rect зависит от высоты строк симптома) съезжают на 1–2 px. У Atkinson — как считает Godot.
static func px_height(px: int, bold: bool = false) -> float:
	if Settings.easy_font():
		return font(bold).get_height(px)
	return ceilf(px * 2384.0 / 2048.0 - 0.0001)


## Минимальный размер подписи кнопки (_min_btn_sz): при крупном тексте — те же экранные пиксели.
static func min_btn_size() -> int:
	return maxi(8, roundi(11.0 / Settings.text_k()))


## Размер, при котором строка влезает в ширину (не меньше lo); как циклы `while sz > … and size > w: sz -= 1`.
static func fit_size(text: String, width: float, size: int, lo: int, bold: bool = false) -> int:
	var sz := size
	while sz > lo and text_width(text, sz, bold) > width:
		sz -= 1
	return sz


## Перенос по словам (wrap_lines game.py; text — уже переведённый): слово шире строки режется по дефису.
static func wrap_lines(text: String, width: float, size: float, bold: bool = false) -> PackedStringArray:
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


# ---------------- рисование текста как в pygame ----------------

## Нарисовать строку (уже переведённую). align: 0 — pos левый верх, 1 — центр, 2 — правый верх (как draw_text).
## Возврат: прямоугольник текста.
static func draw_text(ci: CanvasItem, text: String, pos: Vector2, size: float, color: Color, bold: bool = false,
		align: int = 0) -> Rect2:
	var f := font(bold)
	var px := fs(size)
	var w := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x
	var h := px_height(px, bold)
	var tl := pos
	if align == 1:
		tl = pos - Vector2(w, h) / 2.0
	elif align == 2:
		tl = pos - Vector2(w, 0)
	ci.draw_string(f, Vector2(roundf(tl.x), roundf(tl.y) + f.get_ascent(px)), text, HORIZONTAL_ALIGNMENT_LEFT, -1, px, color)
	return Rect2(tl, Vector2(w, h))


## Строки с переносом (draw_wrapped): pos — левый верх (center — середина верхнего края); limit — сколько символов
## напечатано («печать по буквам», переносы — по полному тексту). Возврат: y под последней строкой.
static func draw_wrapped(ci: CanvasItem, text: String, pos: Vector2, width: float, size: float, color: Color,
		center: bool = false, line_gap: float = 2.0, limit: int = -1, max_lines: int = 0, bold: bool = false) -> float:
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
			var x := pos.x - (f.get_string_size(ln, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x / 2.0 if center else 0.0)
			ci.draw_string(f, Vector2(roundf(x), roundf(y) + f.get_ascent(px)), shown, HORIZONTAL_ALIGNMENT_LEFT, -1, px, color)
		var found := text.find(ln, at)
		var step := ln.length() + 1
		if found >= 0:
			at = found + ln.length()
			step = ln.length() + (1 if text.substr(at, 1) == " " else 0)
		left -= step
		y += px_height(px, bold) + line_gap
	return y


## Высота блока строк с переносом.
static func wrapped_height(text: String, width: float, size: float, line_gap: float = 2.0, bold: bool = false) -> float:
	var n := wrap_lines(text, width, size, bold).size()
	return n * (line_height(size, bold) + line_gap)


# ---------------- фигуры ----------------

static func draw_round_rect(ci: CanvasItem, r: Rect2, fill: Color, border: Color = Color(0, 0, 0, 0),
		width: int = 0, radius: int = 7) -> void:
	var sb := StyleBoxFlat.new()
	sb.bg_color = fill
	sb.set_corner_radius_all(radius)
	sb.anti_aliasing = true
	sb.corner_detail = 8
	if width > 0:
		sb.border_color = border
		sb.set_border_width_all(width)
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
