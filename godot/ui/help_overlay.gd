class_name HelpOverlay
extends Control
## Справка F1 «УПРАВЛЕНИЕ С КЛАВИАТУРЫ» (_draw_help в game.py): клавиши и что они делают (A11Y_KEYS из game.py),
## состояние озвучки, «Esc или F1 — закрыть». Модальная: под ней ничего не нажимается.

const P := Rect2(UI.W / 2.0 - 380, 50, 760, 620)


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Help"


func _ready() -> void:
	var rows: PackedStringArray = []
	for kv: Array in Content.consts.get("help_keys", []):
		rows.append(Loc.t(kv[0]) + " — " + Loc.t(kv[1]))
	accessibility_name = Loc.t("УПРАВЛЕНИЕ С КЛАВИАТУРЫ")
	accessibility_description = ". ".join(rows)


func _gui_input(e: InputEvent) -> void:
	if Nav.is_click(e) and e.pressed:
		Nav.toggle_help()                         # щелчок — закрыть (как в game.py; колёсико — нет)
	accept_event()


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(6, 6, 10, 215))
	UI.draw_round_rect(self, P, Color8(24, 22, 32), UI.AMBER, 2, 12)
	UI.draw_text(self, Loc.t("УПРАВЛЕНИЕ С КЛАВИАТУРЫ"), P.position + Vector2(28, 20), 24, UI.AMBER, true)
	var keys: Array = Content.consts.get("help_keys", [])
	var y := P.position.y + 66
	var room := P.end.y - 84 - y
	var sz := 13
	var step := 0.0
	for s: int in [17, 16, 15, 14, 13]:
		sz = s
		step = UI.line_height(s) + 6
		if step * keys.size() <= room:
			break
	step = minf(33, maxf(step, floorf(room / maxf(1, keys.size()))))
	var kw := 210.0
	for kv: Array in keys:
		var a: Array = UI.fit_text(Loc.t(kv[0]), kw - 12, sz, true)
		UI.draw_text(self, a[0], Vector2(P.position.x + 28, y + floorf((sz - int(a[1])) / 2.0)), a[1], UI.CYAN, true)
		var b: Array = UI.fit_text(Loc.t(kv[1]), P.end.x - 24 - (P.position.x + 28 + kw), sz)
		UI.draw_text(self, b[0], Vector2(P.position.x + 28 + kw, y + floorf((sz - int(b[1])) / 2.0)), b[1], UI.WHITE)
		y += step
	var on: bool = Settings.a11y.get("on", false)
	UI.draw_text(self, Loc.t("Озвучка: %s (%s)" % ["включена" if on else "выключена", Speech.label()]),
		Vector2(P.position.x + 28, P.end.y - 74), 15, UI.GOOD if on else UI.GREY)
	UI.draw_text(self, Loc.t("Esc или F1 — закрыть"), Vector2(P.position.x + 28, P.end.y - 44), 15, UI.GREY)
