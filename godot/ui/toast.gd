class_name Toast
extends Control
## Сообщение сверху (flash/_draw_toast в game.py): в полосе шапки, выпрыгивает сверху (0,3 с), держится время
## чтения (~14 знаков/с + запас); sticky — итог хода в задании: держится, пока игрок что-нибудь не нажмёт.
## Текст хранится по-русски и переводится при рисовании (смена языка — сразу).

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
	label.accessibility_live = AccessibilityServer.AccessibilityLiveMode.LIVE_ASSERTIVE
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
	queue_redraw()


func _draw() -> void:
	if not active():
		return
	var msg := Loc.t(text)
	var left := bounds.x
	var w := UI.W - left - 8 - bounds.y
	var tsz := 11
	var lines: PackedStringArray = []
	var lh := 0.0
	for s: int in [16, 15, 14, 13, 12, 11]:
		tsz = s
		lines = UI.wrap_lines(msg, w - 40, s)
		lh = UI.line_height(s) + 1
		if 8 + lines.size() * lh <= 50:
			break
	var h := 8 + lines.size() * lh
	var k := UI.ease_back((t - t0) / 0.3)
	var rect := Rect2(left, 2 - int(50 * (1 - k)), w, maxf(46, h))
	draw_rect(rect, Color8(20, 18, 26, 250))
	UI.draw_round_rect(self, rect, Color(0, 0, 0, 0), color, 2, 6)
	var y := rect.position.y + (rect.size.y - lines.size() * lh) / 2.0 + lh / 2.0
	for ln in lines:
		UI.draw_text(self, ln, Vector2(rect.get_center().x, y), tsz, color, false, 1)
		y += lh
