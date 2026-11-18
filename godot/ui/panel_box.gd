class_name PanelBox
extends Control
## Панель с рамкой (тёмная полупрозрачная заливка, рамка цвета, скруглённые углы) и необязательным заголовком
## по центру сверху. Остальное содержимое — дочерние элементы или свой draw.

var fill: Color = Color8(22, 20, 30, 235)
var border: Color = UI.AMBER
var border_w: int = 2
var radius: int = 10
var title: String = ""                    # по-русски
var title_size: int = 22
var title_color: Color = UI.AMBER
var body: String = ""                     # текст под заголовком (по центру, с переносом)
var body_size: int = 16


static func make(rect: Rect2, title_ru: String = "", body_ru: String = "", col: Color = UI.AMBER) -> PanelBox:
	var p := PanelBox.new()
	p.position = rect.position
	p.size = rect.size
	p.title = title_ru
	p.body = body_ru
	p.border = col
	p.title_color = col
	return p


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP


func _ready() -> void:
	if title != "":
		accessibility_name = Loc.t(title)
	if body != "":
		accessibility_description = Loc.t(body)


func _draw() -> void:
	UI.draw_round_rect(self, Rect2(Vector2.ZERO, size), fill, border, border_w, radius)
	var y := 18.0
	if title != "":
		UI.draw_text(self, Loc.t(title), Vector2(size.x / 2.0, y + UI.line_height(title_size, true) / 2.0), title_size,
			title_color, true, 1)
		y += UI.line_height(title_size, true) + 12
	if body != "":
		UI.draw_wrapped(self, Loc.t(body), Vector2(size.x / 2.0, y), size.x - 60, body_size, UI.WHITE, true)
