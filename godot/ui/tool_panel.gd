class_name ToolPanel
extends Control
## Панель инструментов ремонта (_draw_tools в game.py): плитки-иконки 2 ряда по 10 (порядок tools.json), выбранный
## инструмент приподнят, в янтарной рамке и покачивается (после ошибки — вздрагивает); справа карточка: что за
## инструмент (наведённый важнее выбранного), сноска мануала к детали, подсказка обучения или общая подсказка.
## Плитки — кнопки (фокус, Enter, имя для чтеца экрана: название и подсказка инструмента).

signal tool_pressed(tid: String)

const TILE := 50
const GAP := 8

var job_screen: Node                       # экран задания: sel_tool, mistakes, tutor_want(), note_part_at()
var tiles: Dictionary = {}                 # tid → GameButton
var ids: Array = []                        # Гильдия: палитра задания (tools) одним рядом; пусто — все 20 в 2 ряда
var _hover_tid: String = ""
var _miss_seen := -1
var _miss_t := -9.0
var _card: Control
var _card_sig: Array = []
var _ring_tid: String = ""                 # обучение: плитка в зелёной рамке (раз в кадр, для redraw_sig плиток)


func _init() -> void:
	size = Vector2(UI.W, UI.H)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	name = "Tools"


func tech() -> bool:
	return not ids.is_empty()


@warning_ignore("integer_division")
func tile_rects() -> Dictionary:
	var out: Dictionary = {}
	if tech():                                 # Гильдия: один ряд из палитры задания
		for i in ids.size():
			out[ids[i]] = Rect2(130 + i * (TILE + GAP), 638, TILE, TILE)
		return out
	var all: Array = Content.tools.keys()
	var per := (all.size() + 1) / 2
	for i in all.size():
		out[all[i]] = Rect2(24 + (i % per) * (TILE + GAP), 560 + (i / per) * (TILE + GAP), TILE, TILE)
	return out


func info_rect() -> Rect2:
	var right := 0.0
	var top := 1e9
	var bottom := 0.0
	for r: Rect2 in tile_rects().values():
		right = maxf(right, r.end.x)
		top = minf(top, r.position.y)
		bottom = maxf(bottom, r.end.y)
	right += 18
	return Rect2(right, top, UI.W - 24 - right, bottom - top)


func _ready() -> void:
	_card = Control.new()
	_card.name = "Card"
	_card.position = info_rect().position
	_card.size = info_rect().size
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_card.draw.connect(_draw_card)
	add_child(_card)
	var i := 0
	var rects := tile_rects()
	for tid: String in rects:
		var b := GameButton.make(rects[tid], "", UI.AMBER)
		b.name = "Tool_" + tid
		b.plain = true
		b.set_meta("tid", tid)
		b.set_meta("i", i)
		b.accessibility_name = Loc.t(Content.tools[tid]["name"]) + ". " + Loc.t(Content.tools[tid]["hint"])
		b.on_draw = _draw_tile
		b.redraw_sig = _tile_sig.bind(b)
		b.pressed.connect(func() -> void: tool_pressed.emit(tid))
		b.hovered_changed.connect(func(on: bool) -> void:
			if on:
				_hover_tid = tid
			elif _hover_tid == tid:
				_hover_tid = "")
		b.focus_entered.connect(func() -> void:
			if UI.kb_active:
				_hover_tid = tid)
		b.focus_exited.connect(func() -> void:
			if _hover_tid == tid and not b.is_hovered():
				_hover_tid = "")
		add_child(b)
		tiles[tid] = b
		i += 1


func hovered_tool() -> String:
	return _hover_tid


func _process(_dt: float) -> void:
	var m: int = job_screen.mistakes
	if m != _miss_seen:
		if _miss_seen >= 0:
			_miss_t = job_screen.t
		_miss_seen = m
	var want: Array = job_screen.tutor_want()
	_ring_tid = str(job_screen.tutor_step()["tool"]) if not want.is_empty() and want[0] == "tool" else ""
	var cs := [_hover_tid, job_screen.sel_tool, job_screen.note_part_at(), want, _card.size]
	if cs != _card_sig:                        # карточка — только когда сменилось, что в ней показать
		_card_sig = cs
		_card.queue_redraw()


## От чего зависит плитка (GameButton.redraw_sig): в руке ли, обучение; пока въезжает, покачивается в руке,
## вздрагивает после ошибки или пульсирует рамка обучения — время (перерисовка каждый кадр).
func _tile_sig(b: GameButton) -> Array:
	var tid: String = b.get_meta("tid")
	var active: bool = job_screen.sel_tool == tid
	var ring := tid == _ring_tid
	var t: float = job_screen.t
	var anim: bool = float(job_screen.st) - 0.25 - 0.025 * int(b.get_meta("i")) < 0.35 		or ((active or ring) and not Settings.calm()) or (active and t - _miss_t < 0.45)
	return [active, ring, t if anim else 0.0]


## Подписи плиток для озвучки фокуса (a11y_items): «Насос, в руке. Накачать камеру…», группа «Инструменты».
func update_a11y(sel: String) -> void:
	for tid: String in tiles:
		var b: GameButton = tiles[tid]
		b.accessibility_name = Loc.t(Content.tools[tid]["name"]) + (", " + Loc.t("в руке") if tid == sel else "") + \
			". " + Loc.t(Content.tools[tid]["hint"])
		b.set_meta("a11y_group", "Инструменты")


func _draw_tile(b: GameButton, _r: Rect2) -> void:
	var tid: String = b.get_meta("tid")
	var i: int = b.get_meta("i")
	var active: bool = job_screen.sel_tool == tid
	var st: float = job_screen.st
	var t: float = job_screen.t
	var h := maxf(b.hover_k, 1.0 if active else 0.0)
	var enter := UI.ease_back((st - 0.25 - 0.025 * i) / 0.35)
	if enter <= 0.01:
		return
	var r := Rect2(Vector2(0, -int(6 * h)), b.size)
	var c := r.get_center()
	b.draw_set_transform(c, 0.0, Vector2(enter, enter))
	var lr := Rect2(-r.size / 2.0, r.size)
	UI.draw_round_rect(b, lr, Color8(52, 48, 64, 235), UI.AMBER if active else UI.DIM.lerp(UI.GHOST, h), 3 if active else 2, 12)
	b.draw_set_transform(Vector2.ZERO)
	var ang := 0.0
	if active:
		ang = 7 * UI.wsin(t * 5)
		var since: float = t - _miss_t
		if since < 0.45:
			ang += 22 * sin(since * 55) * (1 - since / 0.45)
	var tex := Content.texture("tool_%s.png" % tid)
	if tex:
		var k := enter * (1 + 0.16 * h)
		b.draw_set_transform(c, deg_to_rad(-ang), Vector2(k, k))
		var fr := UI.fit_rect(tex.get_size(), Rect2(-19, -19, 38, 38))
		b.draw_texture_rect(tex, fr, false)
		b.draw_set_transform(Vector2.ZERO)
	var want: Array = job_screen.tutor_want()
	if not want.is_empty() and want[0] == "tool" and tid == job_screen.tutor_step()["tool"] and enter >= 1:
		TutorRing.draw_rect_ring(b, r, t)


func _draw_card() -> void:
	var info := Rect2(Vector2.ZERO, _card.size)
	UI.draw_round_rect(_card, info, Color8(22, 20, 30, 215), Color(), 0, 12)
	var sel: String = job_screen.sel_tool
	var tid := _hover_tid if _hover_tid != "" else sel
	var note_pid: String = "" if _hover_tid != "" else job_screen.note_part_at()
	var want: Array = job_screen.tutor_want()
	if note_pid != "":
		_draw_note(info, note_pid)
	elif tid != "":
		var in_hand := tid == sel
		var low := info.size.y < 80                 # в Гильдии карточка в один ряд
		var isz := 38.0 if low else 44.0
		var tex := Content.texture("tool_%s.png" % tid)
		if tex:
			_card.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(10, floorf((info.size.y - isz) / 2.0), isz, isz)), false)
		UI.draw_text(_card, (Loc.t("В РУКЕ: ") if in_hand else "") + Loc.t(Content.tools[tid]["name"]),
			Vector2(isz + 22, 5 if low else 10), 16 if low else 18, UI.AMBER if in_hand else UI.WHITE, true)
		UI.draw_wrapped(_card, Loc.t(Content.tools[tid]["hint"]), Vector2(isz + 22, 27 if low else 36), info.size.x - isz - 34,
			13 if low else 15, UI.GREY)
	elif not want.is_empty():
		UI.draw_wrapped(_card, Loc.t("Обучение: нужный инструмент обведён зелёным — возьми его, потом кликни деталь в зелёном кружке."),
			Vector2(16, 12), info.size.x - 32, 15, UI.GOOD)
	else:
		var y := UI.draw_wrapped(_card, Loc.t("Выбери инструмент, потом кликни шаг" if tech() else
			"Выбери инструмент, потом кликни деталь на коляске или в списке"), Vector2(16, 12), info.size.x - 32, 15, UI.GREY)
		if not tech() and not Content.manual_notes.get(job_screen.job["id"], {}).is_empty():
			BookIcon.draw_icon(_card, Vector2(26, y + 16), 10, UI.CYAN)
			UI.draw_wrapped(_card, Loc.t("У деталей с книжкой есть сноска из мануала — наведи или кликни книжку; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа."),
				Vector2(44, y + 7), info.size.x - 60, 14, UI.CYAN)


## Карточка: сноска из мануала к детали (_draw_manual_note).
func _draw_note(info: Rect2, pid: String) -> void:
	var note: Dictionary = Content.manual_notes[job_screen.job["id"]][pid]
	BookIcon.draw_icon(_card, Vector2(26, 22), 13, UI.CYAN)
	var head := note_head(note)
	var text := Loc.t(note["text"])
	var w := info.size.x - 62
	var hs := 12
	var ts := 11
	for pair: Array in [[15, 15], [14, 14], [13, 13], [12, 12], [12, 11]]:
		hs = pair[0]
		ts = pair[1]
		var hh := UI.wrap_lines(head, w, hs).size() * (UI.line_height(hs) + 2)
		var th := UI.wrap_lines(text, w, ts).size() * (UI.line_height(ts) + 2)
		if 8 + hh + 4 + th <= info.size.y - 6:
			break
	var y := UI.draw_wrapped(_card, head, Vector2(46, 8), w, hs, UI.CYAN)
	UI.draw_wrapped(_card, text, Vector2(46, y + 4), w, ts, UI.WHITE, false, 2, -1,
		maxi(1, int((info.size.y - 6 - y - 4) / (UI.line_height(ts) + 2))))


## «Из мануала: X, с. N» (_note_head), уже переведённое.
static func note_head(note: Dictionary) -> String:
	var page: Variant = note.get("page")
	if page != null and str(page) != "" and str(page) != "0":
		return Loc.tf("Из мануала: {0}, с. {1}", [Loc.t(note["manual"]), str(page).trim_suffix(".0")])
	return Loc.tf("Из мануала: {0}", [Loc.t(note["manual"])])
