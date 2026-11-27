class_name TopBar
extends Control
## Шапка экрана (_topbar в game.py): тёмная полоса 54 px с янтарной линией, заголовок (и вторая строка — модель
## коляски), справа «КОЛЁСА И КОСТИ». Значки (назад, флажок, язык, шестерёнка) — Chrome.add().

var title: String = ""
var sub: String = ""
var brand: bool = true                    # «КОЛЁСА И КОСТИ» справа (нет — когда место занято кнопкой)
var right_edge: float = UI.W - 170        # правый край заголовка/бренда
var left: float = 56                      # после «◂ назад» (8 + 38 + 10)
var text_rects: Array[Rect2] = []         # где нарисованы название, вторая строка и бренд (проверка значка «без звука»)


static func make(title_ru: String, sub_ru: String = "", back: bool = true) -> TopBar:
	var b := TopBar.new()
	b.title = title_ru
	b.sub = sub_ru
	b.left = 56 if back else 24
	if UI.phone():                         # телефон: значки шапки 56×56 (IconButton) — заголовок между ними
		b.left = 68 if back else 24
		b.right_edge = UI.W - 204
	b.name = "TopBar"
	return b


func _init() -> void:
	position = Vector2.ZERO
	size = Vector2(UI.W, 55)
	mouse_filter = Control.MOUSE_FILTER_STOP


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, 54), UI.BAR)
	draw_line(Vector2(0, 54.5), Vector2(UI.W, 54.5), UI.AMBER, 1.0)
	var right := right_edge
	text_rects.clear()
	if brand:
		var b := Loc.t("КОЛЁСА И КОСТИ")
		text_rects.append(UI.draw_text(self, b, Vector2(right, 16), 18, UI.GHOST, true, 2))
		right -= UI.text_width(b, 18, true) + 16
	var x0 := left
	var tt := Loc.t(title)
	if sub != "":
		var ts := 15
		var ss := 10
		for pair: Array in [[20, 14], [18, 13], [17, 12], [16, 11], [15, 10]]:
			ts = pair[0]
			ss = pair[1]
			if UI.line_height(ts, true) + UI.line_height(ss) + 1 <= 50:
				break
		var th := UI.line_height(ts, true)
		var sh := UI.line_height(ss)
		var y: float = maxf(1, floorf((54 - th - sh - 1) / 2.0))
		_fit(tt, Vector2(x0, y), right - x0, ts, UI.AMBER, true)
		_fit(Loc.t(sub), Vector2(x0, y + th + 1), right - x0, ss, UI.GHOST, false)
	else:
		_fit(tt, Vector2(x0, 15), right - x0, 22, UI.AMBER, true)


func _fit(text: String, pos: Vector2, width: float, size: int, color: Color, bold: bool) -> void:
	var f: Array = UI.fit_text(text, width, size, bold)
	var sz: int = f[1]
	text_rects.append(UI.draw_text(self, f[0], Vector2(pos.x, pos.y + floorf((size - sz) / 2.0)), sz, color, bold))
