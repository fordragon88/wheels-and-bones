class_name HotspotButton
extends Button
## Кружок детали на коляске с номером (как в списке справа): тёмная подложка, кольцо янтарное (осмотрено —
## зелёное), неосмотренные «зовут» пульсом; при наведении — белое кольцо и подпись детали. Попадание — по кругу
## (r + 4, как _hotspot_at). Настоящая кнопка: фокус, Enter, имя для чтеца экрана.

var pid: String = ""
var num: int = 0
var r: int = 18
var view: ChairView
var _was_hover := false


func _init() -> void:
	flat = true
	text = ""
	focus_mode = Control.FOCUS_ALL
	action_mode = BaseButton.ACTION_MODE_BUTTON_PRESS
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	var empty := StyleBoxEmpty.new()
	for s: String in ["normal", "hover", "pressed", "disabled", "focus", "hover_pressed"]:
		add_theme_stylebox_override(s, empty)


func _ready() -> void:
	update_a11y()


func update_a11y() -> void:
	var nm := "%d. %s" % [num, Loc.t(Content.part_name(pid))]
	if view and view.inspected.has(pid):
		nm += " ✔"
	accessibility_name = nm


func _has_point(p: Vector2) -> bool:
	return p.distance_to(size / 2.0) <= r + 4


func _process(_dt: float) -> void:
	var h := is_hovered()
	if h and not _was_hover:
		Audio.sfx("hover")
	_was_hover = h
	queue_redraw()


func _draw() -> void:
	var c := size / 2.0
	var done := view != null and view.inspected.has(pid)
	if view and view.pulse and not done and Settings.glow_on():          # зовёт пульсом
		var i := maxi(0, num - 1)
		var ph := fmod(view.t * 0.8 + i * 0.17, 1.0)
		var rr := r + 10 * UI.ease_out(ph)
		UI.draw_ring(self, c, rr, Color(UI.AMBER, 150.0 * (1 - ph) / 255.0), 2)
	UI.draw_ring(self, c, r + 2, UI.INK, 5)                              # подложка: кольцо видно и на белом арте
	UI.draw_ring(self, c, r, UI.GOOD if done else UI.AMBER, 2)
	draw_circle(c, maxi(6, r - 3), Color8(14, 12, 20, 200), true, -1, true)
	UI.draw_text(self, str(num), c, clampi(roundi(r * 0.95), 11, 21), UI.GOOD if done else UI.AMBER, true, 1)
	if is_hovered() or (has_focus() and UI.kb_active):
		UI.draw_ring(self, c, r + 3, UI.WHITE, 2)
		var label := Loc.t(Content.part_name(pid))
		var w := UI.text_width(label, 14) + 16
		var tip := Rect2(c.x - floorf(w / 2.0), c.y - r - 30, w, 22)
		var gp := global_position                                       # не уходить за край экрана и под шапку
		tip.position.x = clampf(tip.position.x + gp.x, 0, UI.W - w) - gp.x
		tip.position.y = clampf(tip.position.y + gp.y, 56, UI.H - 22) - gp.y
		draw_rect(tip, Color8(18, 16, 24, 235))
		UI.draw_round_rect(self, tip, Color(0, 0, 0, 0), UI.WHITE, 1, 5)
		UI.draw_text(self, label, tip.get_center(), 14, UI.WHITE, false, 1)
