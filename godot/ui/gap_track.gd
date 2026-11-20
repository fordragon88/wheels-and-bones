class_name GapTrack
extends Control
## Шкала мини-игры «зазор»: клик/тап (и перетаскивание) ставит значение, ←/→ с клавиатуры — на единицу
## (_a11y_gap_adj: с тоном по значению). Рисует шкалу сама мини-игра.

var mini: MiniGame


func _init() -> void:
	focus_mode = Control.FOCUS_ALL
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	name = "Track"
	set_meta("a11y_group", "Шкала")


func _process(_dt: float) -> void:
	accessibility_name = "%s: %d %s" % [Loc.t(mini.cfg.get("label", "Значение")), mini.value, Loc.t(mini.cfg["unit"])]


func _set_x(x: float) -> void:
	var cfg := mini.cfg
	var frac := clampf(x / size.x, 0.0, 1.0)
	mini.gap_set(roundi(float(cfg["mn"]) + (float(cfg["mx"]) - float(cfg["mn"])) * frac))


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and e.pressed:
		_set_x(e.position.x)
		accept_event()
	elif e is InputEventMouseMotion and (e.button_mask & MOUSE_BUTTON_MASK_LEFT):
		_set_x(e.position.x)
		accept_event()
	elif e is InputEventKey and e.pressed and (e.keycode == KEY_LEFT or e.keycode == KEY_RIGHT):
		mini.gap_adj(-1 if e.keycode == KEY_LEFT else 1)
		accept_event()
