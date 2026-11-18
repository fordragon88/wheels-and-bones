class_name VolSlider
extends Control
## Ползунок громкости окна настроек (как в game.py): дорожка 230×8, ручка-кружок; клик/перетаскивание мышью,
## ←/→ с клавиатуры — по 5 %. Подпись и проценты рисует окно.

signal changed(v: float)

var value: float = 0.5
var muted: bool = false
var _drag := false
var _hover := false


func _init() -> void:
	focus_mode = Control.FOCUS_ALL
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	focus_entered.connect(queue_redraw)
	focus_exited.connect(queue_redraw)
	mouse_entered.connect(func() -> void:
		_hover = true
		queue_redraw())
	mouse_exited.connect(func() -> void:
		_hover = false
		queue_redraw())


## Дорожка внутри Control (сам Control выше дорожки: попадать легче).
func track() -> Rect2:
	return Rect2(12, size.y / 2 - 4, size.x - 24, 8)


func _set_x(x: float) -> void:
	var tr := track()
	value = snappedf(clampf((x - tr.position.x) / tr.size.x, 0.0, 1.0), 0.01)
	changed.emit(value)
	queue_redraw()


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
		_drag = e.pressed
		if e.pressed:
			_set_x(e.position.x)
		accept_event()
	elif e is InputEventMouseMotion and _drag:
		_set_x(e.position.x)
		accept_event()
	elif e is InputEventKey and e.pressed and (e.keycode == KEY_LEFT or e.keycode == KEY_RIGHT):
		value = clampf(snappedf(value + (0.05 if e.keycode == KEY_RIGHT else -0.05), 0.05), 0.0, 1.0)
		changed.emit(value)
		queue_redraw()
		accept_event()


func _draw() -> void:
	var tr := track()
	UI.draw_round_rect(self, tr, Color8(44, 46, 60), Color(), 0, 4)
	var fw := int(tr.size.x * value)
	if fw > 0:
		UI.draw_round_rect(self, Rect2(tr.position, Vector2(fw, tr.size.y)), UI.DIM if muted else UI.AMBER, Color(), 0, 4)
	var c := Vector2(tr.position.x + fw, tr.get_center().y)
	var r := 13.0 if (is_hovered() or _drag or has_focus()) else 10.0
	draw_circle(c, r, UI.WHITE, true, -1, true)
	UI.draw_ring(self, c, r, UI.DIM if muted else UI.AMBER, 3)
	if has_focus() and UI.kb_active:
		UI.draw_round_rect(self, Rect2(Vector2.ZERO, size).grow(2), Color(0, 0, 0, 0), UI.WHITE, 2, 8)


func is_hovered() -> bool:
	return _hover
