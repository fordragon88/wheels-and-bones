class_name GameButton
extends Button
## Кнопка игры (Button из game.py): тёмная заливка цвета кнопки, рамка 2 px (3 — при наведении/активной), при
## наведении приподнимается на 3 px и светится; подпись жирная, ужимается под ширину; sub — вторая строка.
## Настоящая кнопка Godot: фокус с клавиатуры/геймпада, Enter/пробел, имя для чтеца экрана.
## enabled=false — серая, но нажимается (экран сам решает, что сказать: «откроется после…»), как в pygame.

signal hovered_changed(on: bool)

var label: String = ""                    # по-русски; переводится при рисовании
var sub: String = ""
var color: Color = UI.AMBER
var enabled: bool = true
var active: bool = false
var label_size: int = 17
var plain: bool = false                   # только текст, без рамки (крупная надпись-кнопка)
var slide: Vector2 = Vector2.ZERO         # сдвиг картинки (въезд в кадр); нажатие — по месту кнопки
var on_draw: Callable                     # дорисовать содержимое: func(btn, rect: Rect2)
## С on_draw кнопка перерисовывается каждый кадр (содержимое может двигаться). Если задан redraw_sig — только когда
## меняется вид самой кнопки (наведение, сдвиг, фокус, цвет, подпись) или значение redraw_sig() (то, от чего зависит
## on_draw: фаза, осмотрено, инструмент в руке; анимация — время). Текст и рамки, перерисованные зря, — главное, на
## что уходил кадр на слабом процессоре (19.11).
var redraw_sig: Callable
var _sig: Array = []
var hover_k: float = 0.0
var hover_sound: bool = true
var _was_hover := false


static func make(rect: Rect2, lbl: String, col: Color = UI.AMBER, sub_text: String = "") -> GameButton:
	var b := GameButton.new()
	b.position = rect.position
	b.size = rect.size
	b.label = lbl
	b.color = col
	b.sub = sub_text
	b.update_a11y()
	return b


func _init() -> void:
	flat = true
	text = ""
	focus_mode = Control.FOCUS_ALL
	action_mode = BaseButton.ACTION_MODE_BUTTON_PRESS      # как MOUSEBUTTONDOWN в pygame
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	var empty := StyleBoxEmpty.new()
	for s: String in ["normal", "hover", "pressed", "disabled", "focus", "hover_pressed",
			"normal_mirrored", "hover_mirrored", "pressed_mirrored", "disabled_mirrored", "hover_pressed_mirrored"]:
		add_theme_stylebox_override(s, empty)
	focus_entered.connect(queue_redraw)
	focus_exited.connect(queue_redraw)


func update_a11y() -> void:
	var nm := Loc.t(label)
	if sub != "":
		nm += ", " + Loc.t(sub)
	if not enabled:
		nm += " (" + Loc.t("недоступно") + ")"
	accessibility_name = nm.strip_edges()


func set_label(lbl: String, sub_text: String = "") -> void:
	label = lbl
	sub = sub_text
	update_a11y()
	queue_redraw()


func _process(dt: float) -> void:
	var hov := is_hovered() and enabled
	if hov != _was_hover:
		_was_hover = hov
		hovered_changed.emit(hov)
	var target := 1.0 if hov else 0.0
	if target >= 1.0 and hover_k < 0.04 and hover_sound:
		Audio.sfx("hover")
	var nk := target if Settings.calm() else hover_k + (target - hover_k) * minf(1.0, dt * 14.0)
	if redraw_sig.is_valid():
		if absf(target - nk) < 0.0005:
			nk = target
		var sig := [nk, slide, hov, is_hovered(), enabled, active, color, has_focus() and UI.kb_active, label, sub, size,
			redraw_sig.call()]
		hover_k = nk
		if sig != _sig:
			_sig = sig
			queue_redraw()
	elif absf(nk - hover_k) > 0.001 or on_draw.is_valid():
		hover_k = nk
		queue_redraw()


@warning_ignore("integer_division")
func _draw() -> void:
	var col := color if enabled else UI.DIM
	var h := hover_k
	var r := Rect2(slide + Vector2(0, -roundf(3 * h)), size)
	var hov := is_hovered() and enabled
	if not plain:
		var bg := Color8(col.r8 / 6 + 16, col.g8 / 6 + 14, col.b8 / 6 + 18)
		if active:
			bg = Color8(col.r8 / 3, col.g8 / 3, col.b8 / 3)
		var tgt := Color8(col.r8 / 3, col.g8 / 3, col.b8 / 3)
		bg = bg.lerp(tgt, 0.45 * h)
		if h > 0.03 and Settings.glow:
			UI.draw_round_rect(self, r.grow(6), Color(col, 60.0 * h / 255.0), Color(), 0, 12)
		UI.draw_round_rect(self, r, bg, col, 3 if (hov or active) else 2, 7)
	var cx := r.position.x + r.size.x / 2.0
	var cy := r.position.y + r.size.y / 2.0
	var lbl := Loc.t(label)
	if lbl != "" and not (plain and on_draw.is_valid()):
		if sub != "":
			var sbt := Loc.t(sub)
			var sz := UI.fit_size(lbl, r.size.x - 14, 16, UI.min_btn_size(), true)
			var ss := UI.fit_size(sbt, r.size.x - 14, 12, 9)
			var hl := UI.line_height(sz, true)
			var hs := UI.line_height(ss)
			var top := cy - (hl + 2 + hs) / 2.0
			UI.draw_text(self, lbl, Vector2(cx, roundf(top + hl / 2.0)), sz, UI.WHITE if enabled else UI.GREY, true, 1)
			UI.draw_text(self, sbt, Vector2(cx, roundf(top + hl + 2 + hs / 2.0)), ss, UI.GREY, false, 1)
		else:
			var sz := UI.fit_size(lbl, r.size.x - 14, label_size, UI.min_btn_size(), true)
			UI.draw_text(self, lbl, Vector2(cx, cy), sz, col if enabled else UI.GREY, true, 1)
	if on_draw.is_valid():
		on_draw.call(self, r)
	if has_focus() and UI.kb_active:
		UI.draw_round_rect(self, r.grow(4), Color(0, 0, 0, 0), UI.WHITE, 2, 9)
