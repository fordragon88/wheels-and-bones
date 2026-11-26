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
	if UI.phone():                             # телефон: плитки 56, шаг 64 (зазор 8), внизу экрана
		if tech():
			for i in ids.size():
				out[ids[i]] = Rect2(130 + i * 64, 648, 56, 56)
			return out
		var alp: Array = Content.tools.keys()
		var perp := (alp.size() + 1) / 2
		for i in alp.size():
			out[alp[i]] = Rect2(24 + (i % perp) * 64, 584 + (i / perp) * 64, 56, 56)
		return out
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
	if UI.phone() and not tech():              # телефон: справа от карточки — колонка деталей задания (x 980)
		return Rect2(right - 2, top, 964 - right + 2, bottom - top)
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
		var ttl := (Loc.t("В РУКЕ: ") if in_hand else "") + Loc.t(Content.tools[tid]["name"])
		if UI.phone() and not low:              # телефон: карточка уже — название целиком (без «…»), описание под ним
			_draw_card_phone(info, ttl, Loc.t(Content.tools[tid]["hint"]), tex, isz, UI.AMBER if in_hand else UI.WHITE)
			return
		if tex:
			_card.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(10, floorf((info.size.y - isz) / 2.0), isz, isz)), false)
		if UI.phone():                          # телефон: карточка уже — название не шире неё
			UI.draw_text_w(_card, ttl, Vector2(isz + 22, 5 if low else 10), info.size.x - isz - 30, 16 if low else 18,
				UI.AMBER if in_hand else UI.WHITE, true)
		else:
			UI.draw_text(_card, ttl, Vector2(isz + 22, 5 if low else 10), 16 if low else 18, UI.AMBER if in_hand else UI.WHITE, true)
		var hint := Loc.t(Content.tools[tid]["hint"])   # 150 %: описание — мельче, пока не поместится в карточку
		var hy := 27.0 if low else 36.0
		UI.draw_wrapped(_card, hint, Vector2(isz + 22, hy), info.size.x - isz - 34,
			UI.fit_wrapped_size(hint, info.size.x - isz - 34, 13 if low else 15, info.size.y - 4 - hy, 9), UI.GREY)
	elif not want.is_empty():
		var tt := Loc.t("Обучение: нужный инструмент обведён зелёным — возьми его, потом коснись детали в зелёном кружке."
			if UI.touch() else "Обучение: нужный инструмент обведён зелёным — возьми его, потом кликни деталь в зелёном кружке.")
		UI.draw_wrapped(_card, tt, Vector2(16, 12), info.size.x - 32,     # телефон: карточка уже — в её высоту
			UI.fit_wrapped_size(tt, info.size.x - 32, 15, info.size.y - 16, 10) if UI.phone() else 15, UI.GOOD)
	else:
		var hint := ("Выбери инструмент, потом коснись шага" if tech() else
			"Выбери инструмент, потом коснись детали на коляске или в списке") if UI.touch() else \
			("Выбери инструмент, потом кликни шаг" if tech() else "Выбери инструмент, потом кликни деталь на коляске или в списке")
		var book: bool = not tech() and not Content.manual_notes.get(job_screen.job["id"], {}).is_empty()
		var bt := Loc.t("У деталей с книжкой есть сноска из мануала — коснись книжки; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа."
			if UI.touch() else "У деталей с книжкой есть сноска из мануала — наведи или кликни книжку; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа.")
		var hs := 15
		var bs := 14
		if UI.phone():                         # телефон: карточка уже — обе надписи мельче, пока не поместятся
			while hs > 10:
				var hh: float = UI.wrap_lines(Loc.t(hint), info.size.x - 32, hs).size() * (UI.line_height(hs) + 2)
				var bh: float = UI.wrap_lines(bt, info.size.x - 60, bs).size() * (UI.line_height(bs) + 2) if book else 0
				if 12 + hh + 7 + bh <= info.size.y - 4:
					break
				hs -= 1
				bs = hs - 1
		var y := UI.draw_wrapped(_card, Loc.t(hint), Vector2(16, 12), info.size.x - 32, hs, UI.GREY)
		if book:
			BookIcon.draw_icon(_card, Vector2(26, y + 16), 10, UI.CYAN)
			UI.draw_wrapped(_card, bt, Vector2(44, y + 7), info.size.x - 60,   # E37.1 (game.py): 150 % — мельче, не за карточку
				UI.fit_wrapped_size(bt, info.size.x - 60, bs, info.size.y - 4 - (y + 7), 9), UI.CYAN)


## Телефон (21.11): название инструмента — справа от значка (18, при нехватке — мельче до 15); не влезает — во всю
## ширину карточки над значком и описанием (18 → 13), в крайнем случае в две строки; без «…». Описание — под
## названием, кегль по оставшейся высоте, строк не больше, чем помещается в карточку.
func _draw_card_phone(info: Rect2, ttl: String, hint: String, tex: Texture2D, isz: float, col: Color) -> void:
	var x := isz + 22
	var tw := info.size.x - isz - 30
	var hw := info.size.x - isz - 34
	var hy := 36.0
	var top := 0.0                           # верх полосы значка
	var s1 := UI.fit_size(ttl, tw, 18, 15, true)
	if UI.text_width(ttl, s1, true) <= tw:
		UI.draw_text(_card, ttl, Vector2(x, 10 + floorf((18 - s1) / 2.0)), s1, col, true)
	else:
		var fw := info.size.x - 24
		var s2 := UI.fit_size(ttl, fw, 18, 13, true)
		if UI.text_width(ttl, s2, true) <= fw:
			var ty := 8 + floorf((18 - s2) / 2.0)
			UI.draw_text(_card, ttl, Vector2(12, ty), s2, col, true)
			hy = ty + UI.line_height(s2, true) + 2
		else:
			var ts := 18
			while ts > 12 and UI.wrap_lines(ttl, fw, ts, true).size() > 2:
				ts -= 1
			hy = UI.draw_wrapped(_card, ttl, Vector2(12, 6), fw, ts, col, false, 0, -1, 2, true) + 2
		top = hy - 2
	if tex:
		var s := minf(isz, info.size.y - top - 8)
		_card.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(10 + (isz - s) / 2.0,
			top + floorf((info.size.y - top - s) / 2.0), s, s)), false)
	var room := info.size.y - 4 - hy
	var hs := UI.fit_wrapped_size(hint, hw, 15, room, 9)
	var lh := UI.line_height(hs) + 2
	UI.draw_wrapped(_card, hint, Vector2(x, hy), hw, hs, UI.GREY, false, 2, -1, maxi(1, int((room + 2) / lh)))


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
