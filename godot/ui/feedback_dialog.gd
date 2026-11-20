class_name FeedbackDialog
extends Control
## Окно замечания (_draw_dispute_panel/send_dispute в game.py): «СООБЩИТЬ О НЕТОЧНОСТИ» (флажок ⚑, kind general) или
## «Я НЕ СОГЛАСЕН С ИГРОЙ» (после засчитанной ошибки: что ожидала игра, что выбрал игрок, подсказка игры). Причина —
## одна из списка, комментарий — поле ввода (TextEdit, до 600 знаков), «ОТМЕНА» / «ОТПРАВИТЬ». Отправка — Feedback.

signal closed(sent: bool, online: bool)

const P := Rect2(UI.W / 2.0 - 340, UI.H / 2.0 - 274, 680, 548)
const WHERE := {"hub": "Мастерская", "garage": "Гараж", "guild": "Гильдия", "seating": "Кабинет посадки",
	"title": "Титул", "intro": "Вступление"}

var d: Dictionary = {}
var shot: Image
var reason: int = 0
var text: TextEdit
var _reason_btns: Array[GameButton] = []
var _send: GameButton


static func make(dispute: Dictionary, img: Image = null) -> FeedbackDialog:
	var f := FeedbackDialog.new()
	f.d = dispute
	f.shot = img
	return f


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Feedback"


func general() -> bool:
	return d.get("kind", "general") == "general"


func reasons() -> Array:
	return Content.consts.get("feedback_reasons" if general() else "dispute_reasons", [])


## Строки шапки «Я не согласен»: [текст, размер, цвет, макс. строк] и сдвиг окна вниз.
func _head() -> Array:
	var rows: Array = []
	if d.get("expected", "") != "" or d.get("got", "") != "":
		rows.append([Loc.t("Игра ожидала: " + d["expected"]), 14, UI.GOOD, 2])
		rows.append([Loc.t("Ты выбрал: " + d["got"]), 14, UI.BAD, 2])
	rows.append([Loc.t("Подсказка игры: " + d.get("msg", "")), 13, UI.GREY, 4])
	var h := 0.0
	for r: Array in rows:
		h += mini(r[3], UI.wrap_lines(r[0], P.size.x - 56, r[1]).size()) * (UI.line_height(r[1]) + 2) + 2
	return [rows, 0.0 if general() else clampf(58 + h - 150, 0, 80)]


func _reason_rect(i: int) -> Rect2:
	var n := reasons().size()
	var dy: float = _head()[1]
	var step := (42 if n <= 3 else 34) - (6 if dy > 40 else 0)
	return Rect2(P.position.x + 28, P.position.y + 182 + dy + i * step, P.size.x - 56, step - 6)


func _text_rect() -> Rect2:
	var dy: float = _head()[1]
	return Rect2(P.position.x + 28, P.position.y + 340 + dy - (18 if dy > 40 else 0), P.size.x - 56, 78 - (12 if dy > 40 else 0))


func _ready() -> void:
	for i in reasons().size():
		var b := GameButton.make(_reason_rect(i), "", UI.CYAN)
		b.name = "Reason_%d" % i
		b.plain = false
		b.on_draw = _draw_reason
		b.redraw_sig = func() -> int: return reason            # ◉ у выбранной причины
		b.set_meta("i", i)
		b.pressed.connect(func() -> void:
			reason = i
			Audio.sfx("tick")
			_update())
		add_child(b)
		_reason_btns.append(b)
	text = TextEdit.new()
	text.name = "Comment"
	var tr := _text_rect()
	text.position = tr.position
	text.size = tr.size
	text.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	text.add_theme_font_override("font", UI.font())
	text.add_theme_font_size_override("font_size", UI.fs(15))
	text.add_theme_color_override("font_color", UI.WHITE)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color8(12, 12, 18)
	sb.border_color = UI.DIM
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(8)
	for s: String in ["normal", "focus", "read_only"]:
		text.add_theme_stylebox_override(s, sb)
	text.accessibility_name = Loc.t("Опиши, что не так и как правильно" if general() else "Как правильно, по-твоему? (можно не писать)")
	# как handle_dispute_event в game.py: только печатные знаки (без переводов строки, табуляций и невидимых
	# U+200B–U+200D, U+2060, U+FEFF), не больше 600; Enter в поле — «ОТПРАВИТЬ» (TextEdit сам вставил бы перевод строки)
	text.text_changed.connect(func() -> void:
		var clean := _printable(text.text).substr(0, 600)
		if clean != text.text:
			var col := text.get_caret_column()
			text.text = clean
			text.set_caret_column(mini(col, clean.length())))
	text.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventKey and e.pressed and (e.keycode == KEY_ENTER or e.keycode == KEY_KP_ENTER):
			text.accept_event()
			send())
	add_child(text)
	var cancel := GameButton.make(Rect2(P.position.x + 28, P.end.y - 62, 160, 44), "ОТМЕНА", UI.GREY)
	cancel.name = "Cancel"
	cancel.pressed.connect(close)
	add_child(cancel)
	_send = GameButton.make(Rect2(P.end.x - 228, P.end.y - 62, 200, 44), "ОТПРАВИТЬ", UI.GOOD)
	_send.name = "Send"
	_send.pressed.connect(send)
	add_child(_send)
	accessibility_name = Loc.t("СООБЩИТЬ О НЕТОЧНОСТИ" if general() else "Я НЕ СОГЛАСЕН С ИГРОЙ")
	_update()
	UI.focus_later(_reason_btns[0] if not _reason_btns.is_empty() else text)


static func _printable(s: String) -> String:
	var out := ""
	for i in s.length():
		var c := s.unicode_at(i)
		if c < 0x20 or (c >= 0x7F and c < 0xA0) or c in [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x2028, 0x2029]:
			continue
		out += char(c)
	return out


func first_focus() -> Control:
	return _reason_btns[0] if not _reason_btns.is_empty() else text


func _update() -> void:
	var rs := reasons()
	for b in _reason_btns:
		var i: int = b.get_meta("i")
		b.active = i == reason
		b.accessibility_name = Loc.t(rs[i]) + (" ✔" if i == reason else "")
		b.queue_redraw()


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and not P.has_point(e.position):
		close()                                   # клик мимо окна — закрыть (как в game.py)
	accept_event()


func _unhandled_key_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and (e.keycode == KEY_ENTER or e.keycode == KEY_KP_ENTER) \
			and get_viewport().gui_get_focus_owner() == text:
		send()
		get_viewport().set_input_as_handled()


func close() -> void:
	Audio.sfx("tick")
	closed.emit(false, false)
	queue_free()


## Запись как в send_dispute: время, язык, задание, фаза, шаг, вид, ожидала/выбрал, подсказка игры, причина, комментарий.
func entry() -> Dictionary:
	return {"time": Time.get_datetime_string_from_system(false, false), "lang": Loc.code, "job": d.get("job", ""),
		"title": d.get("title", ""), "phase": d.get("phase", ""), "step": d.get("step", ""), "kind": d.get("kind", "general"),
		"expected": d.get("expected", ""), "got": d.get("got", ""), "game_message": d.get("msg", ""),
		"reason": reasons()[reason], "comment": text.text.strip_edges(), "scene": d.get("scene", "job")}


func send() -> void:
	var online := Feedback.send(Feedback.payload(entry()), shot)
	Audio.sfx("ok")
	closed.emit(true, online)
	queue_free()


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 160))
	UI.draw_round_rect(self, P, Color8(20, 18, 28), UI.PURPLE, 2, 14)
	UI.draw_text(self, Loc.t("СООБЩИТЬ О НЕТОЧНОСТИ" if general() else "Я НЕ СОГЛАСЕН С ИГРОЙ"),
		P.position + Vector2(28, 20), 22, UI.PURPLE, true)
	var y := P.position.y + 58
	if general():
		var where: String = d.get("title", "") if d.get("title", "") != "" else WHERE.get(d.get("scene", ""), d.get("scene", ""))
		UI.draw_text(self, Loc.t("Где: " + where), Vector2(P.position.x + 28, y), 15, UI.CYAN)
		y += 24
		if d.get("step", "") != "":
			y = UI.draw_wrapped(self, Loc.t("Шаг: " + d["step"]), Vector2(P.position.x + 28, y), P.size.x - 56, 14, UI.GREY,
				false, 2, -1, 2)
		UI.draw_text(self, Loc.t("Снимок экрана приложится сам — опиши, что не так."),
			Vector2(P.position.x + 28, maxf(y, P.position.y + 110)), 14, UI.GREY)
	else:
		for r: Array in _head()[0]:
			y = UI.draw_wrapped(self, r[0], Vector2(P.position.x + 28, y), P.size.x - 56, r[1], r[2], false, 2, -1, r[3]) + 2
	UI.draw_text(self, Loc.t("Что не так?" if general() else "Почему не согласен?"),
		Vector2(P.position.x + 28, _reason_rect(0).position.y - 26), 15, UI.WHITE, true)
	var tr := _text_rect()
	UI.draw_text(self, Loc.t("Опиши, что не так и как правильно" if general() else "Как правильно, по-твоему? (можно не писать)"),
		tr.position - Vector2(0, 22), 14, UI.GREY)


func _draw_reason(b: GameButton, r: Rect2) -> void:
	var i: int = b.get_meta("i")
	var lbl := ("◉  " if i == reason else "○  ") + Loc.t(reasons()[i])
	UI.draw_text(b, lbl, Vector2(r.position.x + 14, r.get_center().y - floorf(UI.line_height(16) / 2.0)), 16, UI.WHITE)
