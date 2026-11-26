class_name NotesDialog
extends Control
## Сноски из мануалов к деталям задания одним окном (кнопка «СНОСКИ МАНУАЛА», _draw_manual_overlay для
## «notes:<id>»): слева страница (модель коляски), справа «• деталь — сноска (Из мануала: …, с. N)»; шрифт
## подбирается, чтобы влезло. «ЗАКРЫТЬ [Esc]».

signal closed

const P := Rect2(40, 62, 1200, 646)

var job: Dictionary = {}
var _close: GameButton


static func make(j: Dictionary) -> NotesDialog:
	var d := NotesDialog.new()
	d.job = j
	return d


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Notes"


func _ready() -> void:
	# телефон: кнопка 56 по высоте (цель для пальца; Esc на телефоне нет) — обзор 26.11, E24
	_close = GameButton.make(Rect2(P.end.x - 200, P.end.y - 72, 180, 56) if UI.phone()
		else Rect2(P.end.x - 200, P.end.y - 64, 180, 46), "ЗАКРЫТЬ [Esc]", UI.AMBER)
	_close.name = "Close"
	_close.pressed.connect(close)
	add_child(_close)
	_lang_names()
	Loc.changed.connect(_lang_names)
	UI.focus_later(_close)


## Подписи окна для чтеца — и после смены языка при открытом окне (обзор 26.11, E24).
func _lang_names() -> void:
	accessibility_name = Loc.t("СНОСКИ ИЗ МАНУАЛОВ")
	accessibility_description = "\n".join(lines())
	_close.update_a11y()
	_close.queue_redraw()
	queue_redraw()


func first_focus() -> Control:
	return _close


func close() -> void:
	Audio.sfx("tick")
	closed.emit()


func _gui_input(_e: InputEvent) -> void:
	accept_event()


func lines() -> PackedStringArray:
	var out: PackedStringArray = []
	for e: Array in Content.job_notes(job):
		var note: Dictionary = e[1]
		out.append(Loc.t(Content.part_name(e[0])) + " — " + Loc.t(note["text"]) + " (" + ToolPanel.note_head(note) + ")")
	return out


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 180))
	draw_rect(P, Color8(26, 24, 34, 250))
	UI.draw_round_rect(self, P, Color(0, 0, 0, 0), UI.PURPLE, 2, 10)
	UI.draw_text(self, Loc.t("СНОСКИ ИЗ МАНУАЛОВ"), P.position + Vector2(24, 20), 22, UI.PURPLE, true)
	var title := Loc.t(job.get("chair_name", job.get("title", "")))
	var pr := Rect2(P.position.x + 20, P.position.y + 70, 270, 46)
	UI.draw_round_rect(self, pr, UI.PANEL2, UI.PURPLE, 2, 6)
	if UI.text_width(title, 14) <= pr.size.x - 20:
		UI.draw_text(self, title, pr.position + Vector2(10, 13), 14, UI.WHITE)
	else:
		UI.draw_wrapped(self, title, pr.position + Vector2(10, 5), pr.size.x - 20, 13, UI.WHITE, false, 2, -1, 2)
	var x0 := P.position.x + 320
	var tw := P.end.x - 24 - x0
	var f: Array = UI.fit_text(title, tw, 20, true)
	UI.draw_text(self, f[0], Vector2(x0, P.position.y + 70), f[1], UI.AMBER, true)
	var y0 := P.position.y + 110
	var bottom := _close.position.y - 10
	var ls := lines()
	var size_ := 11
	var gap := 4.0
	for s in range(17, 10, -1):
		var g := 8.0 if s >= 15 else 5.0
		var h := 0.0
		for ln in ls:
			h += UI.wrap_lines("• " + ln, tw, s).size() * (UI.line_height(s) + 2) + g
		size_ = s
		gap = g
		if h <= bottom - y0:
			break
	var y := y0
	for ln in ls:
		y = UI.draw_wrapped(self, "• " + ln, Vector2(x0, y), tw, size_, UI.WHITE) + gap
