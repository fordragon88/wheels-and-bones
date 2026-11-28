class_name Toast
extends Control
## Сообщение сверху (flash/_draw_toast в game.py): в полосе шапки, выпрыгивает сверху (0,3 с), держится время
## чтения (~14 знаков/с + запас); sticky — итог хода в задании: держится, пока игрок что-нибудь не нажмёт.
## Текст хранится по-русски и переводится при рисовании (смена языка — сразу). Ширина — по тексту (28.11), по центру,
## в полосе без кнопок шапки (band).

var text: String = ""
var color: Color = UI.WHITE
var timer: float = 0.0
var sticky: bool = false
var t0: float = 0.0
var t: float = 0.0
var bounds: Vector2 = Vector2(54, 164)     # левый край, запас справа (значки)
var label: Label                           # невидимая надпись — живая область для чтеца экрана


func _init() -> void:
	size = Vector2(UI.W, 60)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	label = Label.new()
	label.modulate = Color(1, 1, 1, 0)
	label.accessibility_live = AccessibilityServer.AccessibilityLiveMode.LIVE_OFF   # говорит Speech (один голос)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(label)


func show_msg(msg: String, col: Color, secs: float, is_sticky: bool) -> void:
	text = msg
	color = col
	timer = maxf(secs, 2.5 + 0.07 * Loc.t(msg).length())
	sticky = is_sticky
	t0 = t
	label.text = Loc.t(msg)
	queue_redraw()


## Игрок что-то нажал — итог прошлого хода уходит.
func on_input() -> void:
	if sticky:
		sticky = false
		timer = minf(timer, 0.3)


func active() -> bool:
	return timer > 0.0 and text != ""


func _process(dt: float) -> void:
	t += dt
	if timer > 0.0 and not sticky:
		timer -= dt
	# въезжает 0,3 с, потом стоит до конца — перерисовка только при изменении
	Screen.redraw_on(self, [active(), text, color, bounds, minf(t - t0, 0.35) if active() else 0.0, Loc.code])   # RU/EN — заново


const PAD := 15.0                          # поля плашки слева и справа (28.11: ширина — по тексту)
const GAP := 6.0                           # от кнопок шапки


## Свободные отрезки полосы шапки: от bounds экрана, без кнопок шапки (верх 56) нынешнего экрана (28.11, владелец:
## плашка закрывала кнопку звука и другие).
func segments() -> Array:
	var x0 := bounds.x
	var x1 := UI.W - 8 - bounds.y
	var cuts: Array = []
	var scr: Node = Nav.current
	if scr != null:
		for c: Node in scr.find_children("*", "BaseButton", true, false):
			var b := c as Control
			if b == null or not b.is_visible_in_tree():
				continue
			var r := b.get_global_rect()
			if r.position.y < 56 and r.end.y > 0:
				cuts.append([r.position.x - GAP, r.end.x + GAP])
	cuts.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
	var segs: Array = []
	var cur := x0
	for ct: Array in cuts:
		if ct[1] <= cur or ct[0] >= x1:
			continue
		if ct[0] > cur:
			segs.append(Vector2(cur, minf(ct[0], x1)))
		cur = maxf(cur, ct[1])
	if cur < x1:
		segs.append(Vector2(cur, x1))
	return segs if not segs.is_empty() else [Vector2(x0, x1)]


## Название игры «КОЛЁСА И КОСТИ» в шапке нынешнего экрана (пусто — нет).
func brand_rect() -> Rect2:
	var scr: Node = Nav.current
	if scr != null:
		for c: Node in scr.find_children("TopBar", "TopBar", true, false):
			var tb := c as TopBar
			if tb.is_visible_in_tree() and tb.brand and tb.brand_rect.has_area():
				return Rect2(tb.brand_rect.position + tb.get_global_transform().origin, tb.brand_rect.size)
	return Rect2()


## Раскладка текста в отрезке: [кегль, строки, высота строки, помещается ли в высоту 50].
func _fit(msg: String, w: float) -> Array:
	var tsz := 11
	var lines: PackedStringArray = []
	var lh := 0.0
	for s: int in [16, 15, 14, 13, 12, 11]:
		tsz = s
		lines = UI.wrap_lines(msg, w - 2 * PAD, s)
		lh = UI.line_height(s) + 1
		if 8 + lines.size() * lh <= 50:
			break
	return [tsz, lines, lh, 8 + lines.size() * lh <= 50]


## Полоса для плашки (28.11, владелец: не закрывать кнопки шапки — никогда; название игры — пока текст помещается
## левее него): зона А — свободный отрезок левее названия игры (−8); помещается текст там тем же кеглем, что и во всю
## полосу, — плашка в зоне А; иначе — по всей полосе до кнопок (поверх названия; over_brand = true).
## Возврат: [левый, правый край, поверх ли названия].
func band(msg: String = "") -> Array:
	var segs := segments()
	var full: Vector2 = segs[0]
	for sg: Vector2 in segs:                    # полоса целиком — отрезок с серединой экрана, иначе самый широкий
		if sg.x <= UI.W / 2.0 and UI.W / 2.0 <= sg.y:
			full = sg
			break
		if sg.y - sg.x > full.y - full.x:
			full = sg
	var br := brand_rect()
	if not br.has_area():
		return [full.x, full.y, false]
	var za := Vector2(-1, -1)                    # зона А: самый правый отрезок левее названия
	for sg: Vector2 in segs:
		var e := minf(sg.y, br.position.x - 8)
		if e - sg.x > 2 * PAD + 20 and (za.x < 0 or sg.x > za.x):
			za = Vector2(sg.x, e)
	if za.x < 0:
		return [full.x, full.y, true]
	var m := Loc.t(msg)
	var fa := _fit(m, za.y - za.x)
	var ff := _fit(m, full.y - full.x)
	if bool(fa[3]) and int(fa[0]) >= int(ff[0]):
		return [za.x, za.y, false]
	return [full.x, full.y, full.y > br.position.x - 8]


## Раскладка плашки: [прямоугольник (без въезда), кегль, строки, высота строки, поверх названия игры].
func layout() -> Array:
	var msg := Loc.t(text)
	var bd := band(text)
	var x0: float = bd[0]
	var x1: float = bd[1]
	var f := _fit(msg, x1 - x0)
	var tsz: int = f[0]
	var lines: PackedStringArray = f[1]
	var lh: float = f[2]
	var h := 8 + lines.size() * lh
	var tw := 0.0
	for ln in lines:
		tw = maxf(tw, UI.text_width(ln, tsz))
	var pw := minf(x1 - x0, ceilf(tw + 2 * PAD))
	var x := floorf(UI.W / 2.0 - pw / 2.0)       # по центру экрана, если там помещается; иначе — к правому краю зоны
	if x < x0 or x + pw > x1:
		x = x1 - pw
	return [Rect2(x, 2, pw, maxf(46, h)), tsz, lines, lh, bool(bd[2])]


func _draw() -> void:
	if not active():
		return
	var lay := layout()
	var tsz: int = lay[1]
	var lines: PackedStringArray = lay[2]
	var lh: float = lay[3]
	var k := UI.ease_back((t - t0) / 0.3)
	var rect: Rect2 = lay[0]
	rect.position.y = 2 - int(50 * (1 - k))
	draw_rect(rect, Color8(20, 18, 26, 250))
	UI.draw_round_rect(self, rect, Color(0, 0, 0, 0), color, 2, 6)
	var y := rect.position.y + (rect.size.y - lines.size() * lh) / 2.0 + lh / 2.0
	for ln in lines:
		UI.draw_text(self, ln, Vector2(rect.get_center().x, y), tsz, color, false, 1)
		y += lh
