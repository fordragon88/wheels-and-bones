class_name SpecDialog
extends Control
## Спецификация шага Гильдии (_draw_spec_overlay в game.py): вопрос «какое значение по мануалу», варианты ответа
## открываются, когда нужная страница мануала прочитана («сначала мануал»); «ОТКРЫТЬ МАНУАЛ», «ПОЗЖЕ».
## Выбор — сигнал chosen(i); решает экран задания (choose_spec).

signal chosen(i: int)
signal open_manual(key: String)
signal closed

const P := Rect2(UI.W / 2.0 - 370, 140, 740, 460)

var step: Dictionary = {}
var viewed: Dictionary = {}
var _opts: Array[GameButton] = []
var _manual: GameButton


static func make(st: Dictionary, seen: Dictionary) -> SpecDialog:
	var d := SpecDialog.new()
	d.step = st
	d.viewed = seen
	return d


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Spec"


func spec() -> Dictionary:
	return step["spec"]


func is_viewed() -> bool:
	return viewed.has(spec()["manual"])


func _prompt_bottom() -> float:
	return P.position.y + 40 + UI.wrap_lines(Loc.t(spec()["prompt"]), P.size.x - 48, 20).size() * (UI.line_height(20) + 2)


func option_rect(i: int) -> Rect2:
	var top := maxf(P.position.y + 110, _prompt_bottom() + UI.line_height(15) + 16)
	return Rect2(P.position.x + 24, top + i * 86, P.size.x - 48, 74)


func _ready() -> void:
	var opts: Array = spec()["options"]
	for i in opts.size():
		var b := GameButton.make(option_rect(i), "", UI.CYAN)
		b.name = "Opt_%d" % i
		b.plain = true
		b.set_meta("i", i)
		b.on_draw = _draw_opt
		b.redraw_sig = func() -> bool: return is_viewed()     # варианты открываются после мануала
		b.pressed.connect(func() -> void: chosen.emit(i))
		add_child(b)
		_opts.append(b)
	_manual = GameButton.make(Rect2(P.position.x + 24, P.end.y - 64, 220, 56) if UI.phone()
		else Rect2(P.position.x + 24, P.end.y - 60, 220, 46), "ОТКРЫТЬ МАНУАЛ", UI.PURPLE)
	_manual.name = "OpenManual"
	_manual.pressed.connect(func() -> void: open_manual.emit(spec()["manual"]))
	add_child(_manual)
	var later := GameButton.make(Rect2(P.end.x - 190, P.end.y - 64, 166, 56) if UI.phone()
		else Rect2(P.end.x - 190, P.end.y - 60, 166, 46), "ПОЗЖЕ", UI.GREY)
	later.name = "Later"
	later.pressed.connect(func() -> void:
		Audio.sfx("tick")
		closed.emit())
	add_child(later)
	accessibility_name = Loc.t("СПЕЦИФИКАЦИЯ") + ". " + Loc.t(spec()["prompt"])
	refresh()
	UI.focus_later(first_focus())


## Список клавиатуры: варианты, «открыть мануал», «позже», «◂ назад» экрана (a11y_items game.py при спеке).
func kb_order(items: Array) -> Array:
	return A11y.with_screen_back(items)


func first_focus() -> Control:
	return _opts[0] if is_viewed() and not _opts.is_empty() else _manual


func refresh() -> void:
	var opts: Array = spec()["options"]
	for b in _opts:
		var i: int = b.get_meta("i")
		b.enabled = is_viewed()
		b.accessibility_name = Loc.t(opts[i][0]) + ("" if is_viewed() else ", " + Loc.t("закрыто: сначала мануал"))
		b.set_meta("a11y_group", "Варианты")
		UI.touch_skip(b, not is_viewed())           # варианты — цели переноса тапа только после мануала (game.py)
		b.queue_redraw()
	queue_redraw()


func _gui_input(_e: InputEvent) -> void:
	accept_event()


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 180))
	draw_rect(P, Color8(22, 26, 34, 250))
	UI.draw_round_rect(self, P, Color(0, 0, 0, 0), UI.CYAN, 2, 10)
	UI.draw_text(self, Loc.t("СПЕЦИФИКАЦИЯ"), P.position + Vector2(24, 16), 14, UI.CYAN, true)
	UI.draw_wrapped(self, Loc.t(spec()["prompt"]), P.position + Vector2(24, 40), P.size.x - 48, 20, UI.WHITE)
	if not is_viewed():
		UI.draw_text(self, Loc.t("Сначала сверься с мануалом — варианты откроются."),
			Vector2(P.get_center().x, maxf(P.position.y + 82, _prompt_bottom() + 4 + floorf(UI.line_height(15) / 2))), 15,
			UI.AMBER, false, 1)


func _draw_opt(b: GameButton, _r: Rect2) -> void:
	var i: int = b.get_meta("i")
	var r := Rect2(Vector2.ZERO, b.size)
	UI.draw_round_rect(b, r, UI.PANEL, UI.CYAN if is_viewed() else UI.DIM, 2, 8)
	UI.draw_wrapped(b, Loc.t(spec()["options"][i][0]), Vector2(14, 12), r.size.x - 28, 16, UI.WHITE if is_viewed() else UI.GREY)
