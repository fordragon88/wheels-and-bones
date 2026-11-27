class_name ToolPanel
extends Control
## Панель инструментов ремонта (_draw_tools в game.py): плитки-иконки 2 ряда по 10 (порядок tools.json), выбранный
## инструмент приподнят, в янтарной рамке и покачивается (после ошибки — вздрагивает); справа карточка: что за
## инструмент (наведённый важнее выбранного), сноска мануала к детали, подсказка обучения или общая подсказка.
## Плитки — кнопки (фокус, Enter, имя для чтеца экрана: название и подсказка инструмента).
## Телефон (UI.phone(), 27.11): обычный ремонт — плитки 86 во всю ширину до колонки деталей, вместо карточки полоса над
## ними, сноска — карточкой слева (_draw_big); Гильдия — плитки 56 с рисунком 50, карточка как была.

signal tool_pressed(tid: String)

const TILE := 50
const GAP := 8
# Телефон, обычный ремонт (27.11, вариант 3 владельца): плитки 86 через 94 (2 ряда по 10, x 24…956, левее колонки
# деталей x 980, низ 712), рисунок 74; карточки справа нет — название и описание строкой (полоса) над плитками, низ полосы 520.
# Сноска мануала — карточкой в левой колонке (на месте портрета и пузыря клиента), растёт вверх от низа полосы.
const PH_TILE := 86
const PH_STEP := 94
const PH_TILES_Y := 532
const PH_STRIP_BOTTOM := 520.0
const PH_ICON := 74.0                       # рисунок в плитке 86 (текстуры 128×128)
const PH_TECH_ICON := 50.0                  # Гильдия: плитка 56, рисунок 50 (было 38)
const PH_NOTE_W := 332.0                    # карточка сноски: x 24…356 (текст шага и коляска — правее x 360)
const PH_NOTE_TOP := 70.0                   # выше — шапка экрана
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
			out[alp[i]] = Rect2(24 + (i % perp) * PH_STEP, PH_TILES_Y + (i / perp) * PH_STEP, PH_TILE, PH_TILE)
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


## Телефон, обычный ремонт: высота полосы над плитками — две строки описания наименьшим кеглем 11 (40 при 100 %,
## 44 при 125 %, 48 при 150 %): чем ниже полоса, тем выше коляска.
static func ph_strip_h() -> float:
	return clampf(2.0 * (UI.line_height(11) + 2.0) + 6.0, 40.0, 56.0)


## Телефон, обычный ремонт: верх полосы (выше — коляска с зазором 8, пузырь клиента).
static func ph_strip_top() -> float:
	return PH_STRIP_BOTTOM - ph_strip_h()


## Телефонная раскладка обычного ремонта (плитки 86, полоса), а не Гильдия и не компьютер.
func big() -> bool:
	return UI.phone() and not tech()


func info_rect() -> Rect2:
	if big():                                  # полоса над плитками во всю их ширину
		return Rect2(24, ph_strip_top(), PH_STEP * 9 + PH_TILE, ph_strip_h())
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
	var cs := [_hover_tid, job_screen.sel_tool, job_screen.note_part_at(), want, Settings.a11y.get("text", 0),
		Settings.easy_font(), Loc.code]
	if cs != _card_sig:                        # карточка — только когда сменилось, что в ней показать
		_card_sig = cs
		if big():                              # телефон: полоса или (пока показана сноска) ещё и карточка сноски слева
			var nr := note_rect()
			var ir := info_rect()
			var r := ir.merge(nr) if nr.has_area() else ir
			_card.position = r.position
			_card.size = r.size
		_card.queue_redraw()


## Деталь, чья сноска сейчас показана в карточке ("" — нет): наведённый инструмент важнее.
func note_pid() -> String:
	return "" if _hover_tid != "" else job_screen.note_part_at()


## Телефон, обычный ремонт: раскладка карточки сноски — [прямоугольник экрана, кегль заголовка, кегль текста].
## Кегль 15/15 (наибольший прежней карточки 286×120), ширина 332, высота — сколько нужно тексту целиком (от низа полосы
## вверх, не выше y 70); не влезает и так — 14/14 … 12/11, как прежняя карточка.
func note_layout(pid: String) -> Array:
	var note: Dictionary = Content.manual_notes[job_screen.job["id"]][pid]
	var head := note_head(note)
	var text := Loc.t(note["text"])
	var w := PH_NOTE_W - 62
	var room := PH_STRIP_BOTTOM - PH_NOTE_TOP
	var h := room
	var hs := 12
	var ts := 11
	for pair: Array in [[15, 15], [14, 14], [13, 13], [12, 12], [12, 11]]:
		hs = pair[0]
		ts = pair[1]
		var hh := UI.wrap_lines(head, w, hs).size() * (UI.line_height(hs) + 2)
		var th := UI.wrap_lines(text, w, ts).size() * (UI.line_height(ts) + 2)
		h = maxf(8 + hh + 4 + th + 6, 48.0)
		if h <= room:
			break
	h = minf(ceilf(h), room)
	return [Rect2(24, PH_STRIP_BOTTOM - h, PH_NOTE_W, h), hs, ts]


## Телефон, обычный ремонт: карточка сноски на экране (пустой прямоугольник — сноски нет).
func note_rect() -> Rect2:
	if not big():
		return Rect2()
	var pid := note_pid()
	return Rect2() if pid == "" else note_layout(pid)[0]


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
			ang += 22 * UI.wsin(since * 55) * (1 - since / 0.45)   # E35.3: в «Без анимации» не дёргается
	var tex := Content.texture("tool_%s.png" % tid)
	if tex:
		var isz := 38.0                          # телефон: 74 в плитке 86 (крупнее при наведении — меньше: не за плитку),
		if UI.phone():                           # Гильдия — 50 в плитке 56
			isz = PH_TECH_ICON if tech() else PH_ICON
		var k := enter * (1 + (0.16 if not UI.phone() else 0.08 if big() else 0.06) * h)
		b.draw_set_transform(c, deg_to_rad(-ang), Vector2(k, k))
		var fr := UI.fit_rect(tex.get_size(), Rect2(-isz / 2.0, -isz / 2.0, isz, isz))
		b.draw_texture_rect(tex, fr, false)
		b.draw_set_transform(Vector2.ZERO)
	var want: Array = job_screen.tutor_want()
	if not want.is_empty() and want[0] == "tool" and tid == job_screen.tutor_step()["tool"] and enter >= 1:
		TutorRing.draw_rect_ring(b, r, t)


func _draw_card() -> void:
	if big():
		_draw_big()
		return
	var info := Rect2(Vector2.ZERO, _card.size)
	UI.draw_round_rect(_card, info, Color8(22, 20, 30, 215), Color(), 0, 12)
	var sel: String = job_screen.sel_tool
	var tid := _hover_tid if _hover_tid != "" else sel
	var npid := note_pid()
	var want: Array = job_screen.tutor_want()
	if npid != "":
		_draw_note(info, npid)
	elif tid != "":
		var in_hand := tid == sel
		var low := info.size.y < 80                 # в Гильдии карточка в один ряд
		var isz := 38.0 if low else 44.0
		var tex := Content.texture("tool_%s.png" % tid)
		var ttl := (Loc.t("В РУКЕ: ") if in_hand else "") + Loc.t(Content.tools[tid]["name"])
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


## Телефон, обычный ремонт (27.11): полоса над плитками — что за инструмент (наведённый важнее выбранного), подсказка
## обучения или общая подсказка; пока показана сноска мануала — она карточкой слева (растёт вверх), полоса — правее неё
## (инструмент в руке, если есть). Координаты карточки _card — объединение полосы и карточки сноски.
func _draw_big() -> void:
	var org := _card.position
	var sr := info_rect()
	sr.position -= org
	var sel: String = job_screen.sel_tool
	var tid := _hover_tid if _hover_tid != "" else sel
	var npid := note_pid()
	var want: Array = job_screen.tutor_want()
	if npid != "":
		var lay := note_layout(npid)
		var nr: Rect2 = lay[0]
		nr.position -= org
		UI.draw_round_rect(_card, nr, Color8(22, 20, 30, 248), UI.CYAN, 2, 12)
		_draw_note(nr, npid, lay[1], lay[2])
		if sel != "":
			sr = Rect2(nr.end.x + 8, sr.position.y, sr.end.x - nr.end.x - 8, sr.size.y)
			UI.draw_round_rect(_card, sr, Color8(22, 20, 30, 225), Color(), 0, 10)
			_draw_strip_tool(sr, sel, true, false)
		return
	UI.draw_round_rect(_card, sr, Color8(22, 20, 30, 225), Color(), 0, 10)
	if tid != "":
		_draw_strip_tool(sr, tid, tid == sel)
	elif not want.is_empty():
		var tt := Loc.t("Обучение: нужный инструмент обведён зелёным — возьми его, потом коснись детали в зелёном кружке."
			if UI.touch() else "Обучение: нужный инструмент обведён зелёным — возьми его, потом кликни деталь в зелёном кружке.")
		_draw_block(Rect2(sr.position.x + 12, sr.position.y, sr.size.x - 24, sr.size.y), tt, 15, UI.GOOD)
	else:
		var hint := Loc.t("Выбери инструмент, потом коснись детали на коляске или в списке" if UI.touch() else
			"Выбери инструмент, потом кликни деталь на коляске или в списке")
		var bt := Loc.t("У деталей с книжкой есть сноска из мануала — коснись книжки; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа."
			if UI.touch() else "У деталей с книжкой есть сноска из мануала — наведи или кликни книжку; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа.")
		var book: bool = not Content.manual_notes.get(job_screen.job["id"], {}).is_empty()
		var w := sr.size.x - 24
		var room := sr.size.y - 6
		var s := 14                               # обе надписи одним кеглем, 14 → 11, пока обе целиком в полосе
		while s > 11:
			var n := UI.wrap_lines(hint, w, s).size() + (UI.wrap_lines(bt, w - 24, s).size() if book else 0)
			if n * (UI.line_height(s) + 2) - 2 <= room:
				break
			s -= 1
		var lh := UI.line_height(s) + 2
		var nh := mini(UI.wrap_lines(hint, w, s).size(), maxi(1, int((room + 2) / lh) - (1 if book else 0)))
		var nb := maxi(0, mini(UI.wrap_lines(bt, w - 24, s).size(), int((room + 2) / lh) - nh)) if book else 0
		var y := sr.position.y + floorf((sr.size.y - ((nh + nb) * lh - 2)) / 2.0)
		y = UI.draw_wrapped(_card, hint, Vector2(sr.position.x + 12, y), w, s, UI.GREY, false, 2, -1, nh)
		if nb > 0:
			BookIcon.draw_icon(_card, Vector2(sr.position.x + 21, y + floorf(UI.line_height(s) / 2.0)), 8, UI.CYAN)
			UI.draw_wrapped(_card, bt, Vector2(sr.position.x + 36, y), w - 24, s, UI.CYAN, false, 2, -1, nb)


## Полоса: значок, жирное название («В РУКЕ: …» — янтарём), описание правее в 1–2 строки (кегль 13 → 11).
## cut = false (полоса правее сноски, уже): описание, что не влезает целиком, не рисуется (без «…»).
func _draw_strip_tool(sr: Rect2, tid: String, in_hand: bool, cut: bool = true) -> void:
	var tex := Content.texture("tool_%s.png" % tid)
	var ttl := (Loc.t("В РУКЕ: ") if in_hand else "") + Loc.t(Content.tools[tid]["name"])
	var hint := Loc.t(Content.tools[tid]["hint"])
	var h := sr.size.y
	var isz := minf(30.0, h - 8)
	if tex:
		_card.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(sr.position.x + 8,
			sr.position.y + floorf((h - isz) / 2.0), isz, isz)), false)
	var x := sr.position.x + 46
	var tw := floorf(sr.size.x * 0.42)
	var ts := UI.fit_size(ttl, tw, 15, 12, true)
	var tr := UI.draw_text_w(_card, ttl, Vector2(x, sr.position.y + floorf((h - UI.line_height(ts, true)) / 2.0)), tw, ts,
		UI.AMBER if in_hand else UI.WHITE, true)
	_draw_block(Rect2(x + minf(tr.size.x, tw) + 14, sr.position.y, sr.end.x - 10 - (x + minf(tr.size.x, tw) + 14), h),
		hint, 13, UI.GREY, cut)


## Текст с переносом в прямоугольнике полосы: кегль size → 11, пока весь в высоту; посередине по высоте; не влез и
## при 11 — строк сколько помещается, последняя с «…» (cut = false — тогда не рисуется совсем).
func _draw_block(r: Rect2, text: String, size: int, col: Color, cut: bool = true) -> void:
	var room := r.size.y - 6
	var s := UI.fit_wrapped_size(text, r.size.x, size, room, 11)
	var lh := UI.line_height(s) + 2
	var n := mini(UI.wrap_lines(text, r.size.x, s).size(), maxi(1, int((room + 2) / lh)))
	if not cut and n < UI.wrap_lines(text, r.size.x, s).size():
		return
	UI.draw_wrapped(_card, text, Vector2(r.position.x, r.position.y + floorf((r.size.y - (n * lh - 2)) / 2.0)), r.size.x,
		s, col, false, 2, -1, n)


## Карточка: сноска из мануала к детали (_draw_manual_note). hs/ts < 0 — кегль по высоте info (15/15 … 12/11).
func _draw_note(info: Rect2, pid: String, hs: int = -1, ts: int = -1) -> void:
	var note: Dictionary = Content.manual_notes[job_screen.job["id"]][pid]
	var o := info.position
	BookIcon.draw_icon(_card, o + Vector2(26, 22), 13, UI.CYAN)
	var head := note_head(note)
	var text := Loc.t(note["text"])
	var w := info.size.x - 62
	if hs < 0:
		hs = 12
		ts = 11
		for pair: Array in [[15, 15], [14, 14], [13, 13], [12, 12], [12, 11]]:
			hs = pair[0]
			ts = pair[1]
			var hh := UI.wrap_lines(head, w, hs).size() * (UI.line_height(hs) + 2)
			var th := UI.wrap_lines(text, w, ts).size() * (UI.line_height(ts) + 2)
			if 8 + hh + 4 + th <= info.size.y - 6:
				break
	var y := UI.draw_wrapped(_card, head, o + Vector2(46, 8), w, hs, UI.CYAN)
	UI.draw_wrapped(_card, text, Vector2(o.x + 46, y + 4), w, ts, UI.WHITE, false, 2, -1,
		maxi(1, int((info.end.y - 6 - y - 4) / (UI.line_height(ts) + 2))))


## «Из мануала: X, с. N» (_note_head), уже переведённое.
static func note_head(note: Dictionary) -> String:
	var page: Variant = note.get("page")
	if page != null and str(page) != "" and str(page) != "0":
		return Loc.tf("Из мануала: {0}, с. {1}", [Loc.t(note["manual"]), str(page).trim_suffix(".0")])
	return Loc.tf("Из мануала: {0}", [Loc.t(note["manual"])])
