class_name ToolPanel
extends Control
## Панель инструментов ремонта (_draw_tools в game.py): плитки-иконки 2 ряда по 10 (порядок tools.json), выбранный
## инструмент приподнят, в янтарной рамке и покачивается (после ошибки — вздрагивает); справа карточка: что за
## инструмент (наведённый важнее выбранного), сноска мануала к детали, подсказка обучения или общая подсказка.
## Плитки — кнопки (фокус, Enter, имя для чтеца экрана: название и подсказка инструмента).
## Телефон (UI.phone(), 27.11): обычный ремонт — слева крупная кнопка «Руки и глаза», правее кучки инструментов по
## назначению (заголовок, оттенок, подпись под рисунком), над ними полоса с названием и описанием вместо карточки,
## сноска — карточкой слева (_draw_big); Гильдия — плитки 56 с рисунком 50, карточка как была.

signal tool_pressed(tid: String)

const TILE := 50
const GAP := 8
# Телефон, обычный ремонт (27.11, выбор владельца — эскиз tools/tool_choice_mock/C_sochetanie_ves_ekran.jpg):
# «Руки и глаза» — кнопка 112×184 слева (x 24, y 530…714); правее, через 16, — кучки по назначению в 2 ряда (плитки
# 71×78, внутри кучки зазор 8, между кучками 16; ряды y 536 и 636, низ 714), над кучкой заголовок (полоса 13 px) с
# линией. Подписи и заголовки — в пикселях холста (не растут с настройкой «размер текста»: 11 → 10, до 2 строк).
# Карточки справа нет — название и описание строкой (полоса) над всем этим, низ полосы 514. Порядок, кучки и подписи —
# только здесь; на компьютере и в Гильдии — как game.py (порядок tools.json).
const PH_HANDS := Rect2(24, 530, 112, 184)
const PH_TW := 71.0
const PH_TH := 78.0
const PH_GAP_IN := 8.0
const PH_GAP_GRP := 16.0
const PH_ROWS_Y := [536.0, 636.0]
const PH_HEAD_H := 13.0                     # полоса заголовка кучки: от y ряда − 6 (подъём выбранной) − 1 − 13
const PH_TILE_MIX := 0.38                   # оттенок кучки в заливке плитки
const PH_STRIP_BOTTOM := 514.0
const PH_ICON := 50.0                       # рисунок в плитке кучки (с подписью в 2 строки — сколько влезет, ≥ 46)
const PH_ICON_MIN := 46.0                   # проверка phone_check: рисунок кучки не меньше
const PH_ICON_TOP := 3.0                    # от верха плитки до места рисунка (рамка 2–3)
const PH_ICON_GAP := 3.0                    # между местом рисунка и подписью
const PH_LABEL_PAD := 2.0                   # под подписью до низа плитки
static var _icon_used: Dictionary = {}
const PH_TECH_ICON := 50.0                  # Гильдия: плитка 56, рисунок 50 (было 38)
## Кучки: [ключ, заголовок RU, EN, инструменты, цвет]; ряд 1 — первые две, ряд 2 — остальные.
const PH_GROUPS := [
	["fast", "КРЕПЁЖ", "FASTENERS", ["allen", "socket", "wrench", "screw", "spoke_key"], Color8(96, 160, 225)],
	["wheel", "КОЛЕСО И ШИНА", "WHEEL & TIRE", ["lever", "pump", "patch", "gauge"], Color8(40, 185, 140)],
	["care", "ЧИСТКА И СМАЗКА", "CLEAN & LUBE", ["lube", "brush", "cloth", "bucket"], Color8(200, 130, 190)],
	["meas", "ИЗМЕРЕНИЕ", "MEASURE", ["tape", "pencil", "tensiometer", "dial"], Color8(235, 150, 60)],
	["elec", "ЭЛЕКТРИКА", "ELECTRICS", ["multimeter", "charger"], Color8(225, 100, 95)]]
## Короткие подписи плиток [RU, EN] (полное название и описание — в полосе; tools.json не меняется).
## «|» — где слово можно перенести с дефисом, если целиком не помещается и кеглем 10.
const PH_LABEL := {"allen": ["Шести|гранник", "Hex key"], "socket": ["Торцевой ключ", "Socket wrench"],
	"wrench": ["Развод|ной ключ", "Crescent wrench"], "screw": ["Отвёртка", "Screw|driver"],
	"spoke_key": ["Спицевой ключ", "Spoke wrench"], "lever": ["Монтажка", "Tire lever"], "pump": ["Насос", "Pump"],
	"patch": ["Заплатка", "Patch"], "gauge": ["Манометр", "Pressure gauge"], "lube": ["Смазка", "Lubricant"],
	"brush": ["Щётка / пинцет", "Brush / tweezers"], "cloth": ["Тряпка", "Cloth"], "bucket": ["Таз с водой", "Bowl of water"],
	"tape": ["Рулетка", "Tape measure"], "pencil": ["Каран|даш", "Pencil"], "tensiometer": ["Тензио|метр", "Tension meter"],
	"dial": ["Инди|катор", "Dial indi|cator"], "multimeter": ["Мульти|метр", "Multi|meter"], "charger": ["Зарядка", "Charger"]}
## Кнопка «Руки и глаза»: название и пояснение [RU, EN] (строки пояснения — через «\n»).
const PH_HANDS_TXT := [["Руки и глаза", "Hands & eyes"], ["смотреть · трогать\nнажать · снять-поставить", "look · touch\npress · refit"]]
## Раскладка кучек: телефон (PH_*) и компьютер (28.11, эскиз tools/tool_choice_mock/PC_C_s_podpisyami.jpg: кнопка
## рук 82×162 слева, плитки 62×66, в кучке зазор 5, между кучками и до рук 13, ряды y 567 и 651, низ 717; заголовок —
## полоса 11 px над рядом (от y 549: коляска — до 548); подписи жирным 10 → 9; рисунок 40–42; карточка справа
## x 808…1256, y 560…716). Числа — в пикселях холста, с «размером текста» не растут.
const PH_GEO := {"hands": Rect2(24, 530, 112, 184), "tw": 71.0, "th": 78.0, "gin": 8.0, "ggrp": 16.0,
	"rows": [536.0, 636.0], "head_h": 13.0, "head_px": [11, 10], "lab_px": [11, 10], "icon": 50.0, "icon_min": 46.0,
	"itop": 3.0, "igap": 3.0, "pad": 2.0, "h_title": [13, 11], "h_hint": [11, 10], "h_lines": 99, "grow": 0.08}
const PC_GEO := {"hands": Rect2(24, 556, 82, 162), "tw": 62.0, "th": 66.0, "gin": 5.0, "ggrp": 13.0,
	"rows": [567.0, 651.0], "head_h": 11.0, "head_px": [9, 9], "lab_px": [10, 9], "icon": 42.0, "icon_min": 40.0,
	"itop": 2.0, "igap": 2.0, "pad": 2.0, "h_title": [12, 11], "h_hint": [10, 10], "h_lines": 2, "grow": 0.16}
const PC_CARD := Rect2(808, 560, 448, 156)
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
	if grouped():                              # обычный ремонт: «Руки и глаза» слева, потом кучки по рядам
		var g_ := geo()
		out["hands"] = g_["hands"]
		for g: Array in ph_groups():
			var ids_: Array = g[3]
			var r: Rect2 = g[2]
			for j in ids_.size():
				out[ids_[j]] = Rect2(r.position.x + j * (float(g_["tw"]) + float(g_["gin"])), r.end.y - float(g_["th"]),
					g_["tw"], g_["th"])
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


## Телефонная раскладка обычного ремонта (кнопка рук, кучки, полоса), а не Гильдия и не компьютер.
func big() -> bool:
	return UI.phone() and not tech()


## Компьютер: карточка выросла выше колонки Барти — пузырь Барти скрыть (job.gd).
func pc_hides_mentor() -> bool:
	return grouped() and not UI.phone() and _pc_h > PC_CARD.size.y + 0.5


## Кнопка рук и кучки (телефон и компьютер, обычный ремонт), а не Гильдия.
func grouped() -> bool:
	return not tech()


## Числа раскладки кучек: телефон или компьютер.
static func geo() -> Dictionary:
	return PH_GEO if UI.phone() else PC_GEO


## Телефон, обычный ремонт: кучки — [ключ, заголовок на текущем языке, прямоугольник кучки (полоса заголовка и
## плитки), инструменты, цвет]. Инструменты, которых нет ни в одной кучке (кроме рук), — последней кучкой без
## заголовка во втором ряду (сейчас таких нет).
func ph_groups() -> Array:
	var en := Loc.code == "en"
	var used := {"hands": true}
	var defs: Array = []
	for g: Array in PH_GROUPS:
		var ids_: Array = (g[3] as Array).filter(func(x: String) -> bool: return Content.tools.has(x))
		for x: String in ids_:
			used[x] = true
		defs.append([g[0], g[2] if en else g[1], ids_, g[4]])
	var rest: Array = Content.tools.keys().filter(func(x: String) -> bool: return not used.has(x))
	if not rest.is_empty():
		defs.append(["other", "", rest, UI.DIM])
	var out: Array = []
	var g_ := geo()
	var hr: Rect2 = g_["hands"]
	var tw: float = g_["tw"]
	var th: float = g_["th"]
	var x := hr.end.x + float(g_["ggrp"])
	var row := 0
	for k in defs.size():
		if k == 2:                                 # второй ряд — с третьей кучки
			row = 1
			x = hr.end.x + float(g_["ggrp"])
		var d: Array = defs[k]
		var n: int = (d[2] as Array).size()
		var gw := n * tw + (n - 1) * float(g_["gin"])
		var ry: float = g_["rows"][row]
		var top: float = ry - 6 - (1 if UI.phone() else 0) - float(g_["head_h"])
		out.append([d[0], d[1], Rect2(x, top, gw, ry + th - top), d[2], d[3]])
		x += gw + float(g_["ggrp"])
	return out


## Кучка инструмента (ph_groups) или [] — для подписи чтеца и оттенка плитки.
func ph_group_of(tid: String) -> Array:
	for g: Array in ph_groups():
		if tid in (g[3] as Array):
			return g
	return []


func info_rect() -> Rect2:
	if big():                                  # полоса над плитками во всю их ширину
		return Rect2(24, ph_strip_top(), 932, ph_strip_h())
	if grouped():                              # компьютер: карточка справа от кучек, выше прежней (pc_need_h)
		return pc_card_rect()
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
		b.accessibility_name = _a11y_name(tid, "")
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
	if grouped():                              # заголовки кучек (над плитками)
		var heads := Control.new()
		heads.name = "Groups"
		heads.size = size
		heads.mouse_filter = Control.MOUSE_FILTER_IGNORE
		heads.draw.connect(_draw_heads.bind(heads))
		add_child(heads)


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
		elif grouped():                        # компьютер: высота карточки — по содержимому (не мельче прежней)
			_pc_h = pc_need_h(pc_card_what())
			_card.position = pc_card_rect().position
			_card.size = pc_card_rect().size
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
		b.accessibility_name = _a11y_name(tid, sel)
		b.set_meta("a11y_group", "Инструменты")


## «Насос, в руке. Накачать камеру…»; телефон, обычный ремонт — ещё кучка: «Насос. Колесо и шина. …».
func _a11y_name(tid: String, sel: String) -> String:
	var nm := Loc.t(Content.tools[tid]["name"]) + (", " + Loc.t("в руке") if tid == sel else "")
	if grouped():
		var g := ph_group_of(tid)
		if not g.is_empty() and str(g[1]) != "":
			var head := str(g[1])
			nm += ". " + head.substr(0, 1) + head.substr(1).to_lower()
	return nm + ". " + Loc.t(Content.tools[tid]["hint"])


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
	var icon_c := Vector2.ZERO                 # середина рисунка от середины плитки
	var isz_big := 0.0
	if grouped():                              # оттенок кучки, подпись под рисунком; руки — своя кнопка
		var hands := tid == "hands"
		var grp := ph_group_of(tid)
		var gc: Color = UI.AMBER if hands else (grp[4] if not grp.is_empty() else UI.DIM)
		var fill := Color8(64, 52, 30) if hands else Color8(52, 48, 64).lerp(gc, PH_TILE_MIX)
		fill.a = 240.0 / 255.0 if hands else 235.0 / 255.0
		var edge := UI.AMBER if active else (Color8(150, 120, 60) if hands else UI.DIM.lerp(gc, 0.6)).lerp(UI.GHOST, h)
		UI.draw_round_rect(b, lr, fill, edge, 3 if active else 2, 14 if hands else 11)
		var lay := ph_hands_fit() if hands else ph_label_fit(tid)
		var y: float = lr.end.y - float(lay[3])
		var lines_: PackedStringArray = lay[1]
		var nt: int = lay[5] if hands else 99      # руки: строк названия (дальше — пояснение)
		for k in lines_.size():
			var ln: String = lines_[k]
			var px: int = lay[0] if (not hands or k < nt) else lay[2]
			var bold := not hands or k < nt
			var w := UI.px_width(ln, px, bold)
			UI.put_string(b, Vector2(roundf(-w / 2.0), roundf(y) + UI.font(bold).get_ascent(px)), ln, px,
				(UI.AMBER if k < nt else Color8(220, 200, 160)) if hands else UI.WHITE, bold)
			y += (UI.px_height(px, bold) + 1) if hands else ph_label_step(px)
		if hands:
			isz_big = minf(84.0, lr.size.y - float(lay[3]) - (16 if UI.phone() else 10))
			icon_c = Vector2(0, lr.position.y + (lr.size.y - float(lay[3])) / 2.0)
		else:                                  # место рисунка — между рамкой и подписью (ph_icon_fit)
			var fit := ph_icon_fit(tid)
			isz_big = fit[0]
			icon_c = Vector2(0, lr.position.y + float(geo()["itop"]) + float(fit[1]) / 2.0)
	else:                                      # компьютер, Гильдия — как game.py
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
		if grouped():
			isz = isz_big
		var k := enter * (1 + (0.16 if not UI.phone() else 0.08 if big() else 0.06) * h)
		if grouped() and tid != "hands":       # крупнее при наведении и покачивание — не дальше места рисунка
			k = enter * minf(1 + float(geo()["grow"]) * h, ph_icon_room_k(tid, isz, ang))
		b.draw_set_transform(c + icon_c * enter, deg_to_rad(-ang), Vector2(k, k))
		var fr := UI.fit_rect(tex.get_size(), Rect2(-isz / 2.0, -isz / 2.0, isz, isz))
		b.draw_texture_rect(tex, fr, false)
		b.draw_set_transform(Vector2.ZERO)
	var want: Array = job_screen.tutor_want()
	if not want.is_empty() and want[0] == "tool" and tid == job_screen.tutor_step()["tool"] and enter >= 1:
		TutorRing.draw_rect_ring(b, r, t)


## Строки по словам шириной w пикселей шрифта px; « / » остаётся на первой строке («Щётка /» + «пинцет»); «|» в
## слове — перенос с дефисом (только cut = true и если слово целиком в строку не помещается).
static func _px_wrap(text: String, w: float, px: int, bold: bool, cut: bool = false) -> PackedStringArray:
	var out: PackedStringArray = []
	var cur := ""
	for word in text.replace(" / ", "\u00a0/ ").split(" "):
		var wd := word.replace("\u00a0", " ")
		var whole := wd.replace("|", "")
		var test := (cur + " " + whole).strip_edges()
		if UI.px_width(test, px, bold) <= w:
			cur = test
			continue
		if cur != "":
			out.append(cur)
			cur = ""
		if cut and "|" in wd and UI.px_width(whole, px, bold) > w:
			var parts := wd.split("|")
			out.append(parts[0] + "-")
			cur = "".join(parts.slice(1))
		else:
			cur = whole
	if cur != "":
		out.append(cur)
	return out


## Подпись плитки кучки: [px, строки, px, высота блока подписи, помещается ли]; жирный 11 → 10, до 2 строк, без «…»
## (не помещается и при 10 — строки как есть, «помещается» = false: это ловят проверки).
## Компьютер: кегль 10, если рисунок при нём не мельче icon_min, иначе 9.
func ph_label_fit(tid: String) -> Array:
	var lab: Array = PH_LABEL.get(tid, [Content.tools[tid]["name"], Loc.t(Content.tools[tid]["name"])])
	var text: String = lab[1] if Loc.code == "en" else lab[0]
	var g_ := geo()
	var w: float = float(g_["tw"]) - 6
	var hi: int = g_["lab_px"][0]
	var lo: int = g_["lab_px"][1]
	var res: Array = []
	for v: Array in [[hi, false], [lo, false], [hi, true], [lo, true]]:   # сперва без переноса с дефисом
		var px: int = v[0]
		var lines := _px_wrap(text, w, px, true, v[1])
		var ok := lines.size() <= 2
		for ln in lines:
			ok = ok and UI.px_width(ln, px, true) <= w
		res = [px, lines, px, (lines.size() - 1) * ph_label_step(px) + UI.px_height(px, true) + float(g_["pad"]), ok]
		if ok and (px == lo or UI.phone() or _icon_for(tid, float(res[3]))[0] >= float(g_["icon_min"])):
			break
	return res


## Шаг строк подписи плитки: высота строки шрифта без 1 px (строки плотнее — рисунку больше места).
static func ph_label_step(px: int) -> float:
	return UI.px_height(px, true) - 1


## Непрозрачная часть рисунка инструмента (доля стороны текстуры): [ширина, высота]; кэш.
static func ph_icon_used(tid: String) -> Vector2:
	if _icon_used.has(tid):
		return _icon_used[tid]
	var out := Vector2.ONE
	var tex := Content.texture("tool_%s.png" % tid)
	if tex:
		var img := tex.get_image()
		if img:
			if img.is_compressed():
				img.decompress()
			var u := img.get_used_rect()
			out = Vector2(u.size) / Vector2(img.get_size())
	_icon_used[tid] = out
	return out


## Рисунок плитки кучки: [сторона рисунка, высота места под ним]. Место — от рамки (PH_ICON_TOP) до подписи с зазором
## PH_ICON_GAP; сторона — наибольшая (до PH_ICON), при которой непрозрачная часть рисунка в покое помещается в место.
func ph_icon_fit(tid: String) -> Array:
	return _icon_for(tid, float(ph_label_fit(tid)[3]))


func _icon_for(tid: String, lab_h: float) -> Array:
	var g_ := geo()
	var room: float = float(g_["th"]) - lab_h - float(g_["itop"]) - float(g_["igap"])
	var u := ph_icon_used(tid)
	var isz := minf(g_["icon"], floorf(minf(room / maxf(u.y, 0.01), (float(g_["tw"]) - 6) / maxf(u.x, 0.01))))
	return [isz, room]


## Наибольший множитель рисунка при повороте ang (градусы), чтобы непрозрачная часть не вышла из места рисунка.
func ph_icon_room_k(tid: String, isz: float, ang: float) -> float:
	var u := ph_icon_used(tid) * isz
	var a := deg_to_rad(absf(ang))
	var vh := u.y * cos(a) + u.x * sin(a)
	var vw := u.x * cos(a) + u.y * sin(a)
	return minf(float(ph_icon_fit(tid)[1]) / maxf(vh, 0.01), (float(geo()["tw"]) - 6) / maxf(vw, 0.01))


## Кнопка «Руки и глаза»: [px названия, строки (название, потом пояснение), px пояснения, высота блока, помещается ли].
## Компьютер: название в 1–2 строки, пояснение — сколько целых частей (до «\n») помещается в 2 строки.
func ph_hands_fit() -> Array:
	var en := Loc.code == "en"
	var g_ := geo()
	var title: String = PH_HANDS_TXT[0][1 if en else 0]
	var hr: Rect2 = g_["hands"]
	var w := hr.size.x - 10
	var tp: int = g_["h_title"][0]
	while tp > int(g_["h_title"][1]) and UI.px_width(title, tp, true) > w:
		tp -= 1
	var tl: PackedStringArray = [title]
	if UI.px_width(title, tp, true) > w and not UI.phone():
		tl = _px_wrap(title, w, tp, true)
	var ok := true
	for ln in tl:
		ok = ok and UI.px_width(ln, tp, true) <= w
	var lines: PackedStringArray = tl.duplicate()
	var hp: int = g_["h_hint"][0]
	var sub: PackedStringArray = []
	for p_: int in g_["h_hint"]:
		hp = p_
		sub = []
		for part: String in (PH_HANDS_TXT[1][1 if en else 0] as String).split("\n"):
			var more := _dot_wrap(part, w, hp)
			var fit_part := sub.size() + more.size() <= int(g_["h_lines"])
			for ln in more:
				fit_part = fit_part and UI.px_width(ln, hp, false) <= w
			if not fit_part:
				break
			sub.append_array(more)
		var fits := true
		for ln in sub:
			fits = fits and UI.px_width(ln, hp, false) <= w
		if fits:
			break
	for ln in sub:
		ok = ok and UI.px_width(ln, hp, false) <= w
	lines.append_array(sub)
	var hh := tl.size() * (UI.px_height(tp, true) + 1) + 2 + sub.size() * (UI.px_height(hp, false) + 1) + 6
	return [tp, lines, hp, hh, ok, tl.size()]


## Пояснение кнопки рук: пункты через « · » по строкам; не помещается — пункт с новой строки (без «·» на краю).
static func _dot_wrap(text: String, w: float, px: int) -> PackedStringArray:
	var out: PackedStringArray = []
	var cur := ""
	for item in text.split(" · "):
		var test := item if cur == "" else cur + " · " + item
		if cur == "" or UI.px_width(test, px, false) <= w:
			cur = test
		else:
			out.append(cur)
			cur = item
	if cur != "":
		out.append(cur)
	return out


## Заголовок кучки: [px, помещается ли] — жирный 11 → 10 в ширину кучки.
static func ph_head_fit(text: String, w: float) -> Array:
	var hi: int = geo()["head_px"][0]
	var lo: int = geo()["head_px"][1]
	var px := hi
	while px > lo and UI.px_width(text, px, true) > w:
		px -= 1
	return [px, UI.px_width(text, px, true) <= w and UI.px_height(px, true) <= float(geo()["head_h"])]


## Заголовки кучек: жирный в цвет кучки (светлее), правее — тонкая линия до конца кучки.
func _draw_heads(ci: Control) -> void:
	for g: Array in ph_groups():
		var head: String = g[1]
		if head == "":
			continue
		var r: Rect2 = g[2]
		var col: Color = (g[4] as Color).lerp(Color.WHITE, 0.25)
		var f := ph_head_fit(head, r.size.x)
		var px: int = f[0]
		var hh: float = geo()["head_h"]
		var y := r.position.y + floorf((hh - UI.px_height(px, true)) / 2.0)
		UI.put_string(ci, Vector2(r.position.x + 1, y + UI.font(true).get_ascent(px)), head, px, col, true)
		var hw := UI.px_width(head, px, true)
		if r.size.x > hw + 24:
			var ly := r.position.y + floorf(hh / 2.0) + 1
			ci.draw_line(Vector2(r.position.x + hw + 8, ly), Vector2(r.end.x - 2, ly), Color(col, 0.6), 2.0)


func _draw_card() -> void:
	if big():
		_draw_big()
		return
	if grouped() and not UI.phone():
		_draw_card_pc()
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
		var hint := Loc.t(Content.tools[tid]["hint"])   # 150 %: описание — мельче, пока не поместится в карточку
		var hy := 27.0 if low else 36.0
		if UI.phone():                          # телефон: карточка уже — название не шире неё
			UI.draw_text_w(_card, ttl, Vector2(isz + 22, 5 if low else 10), info.size.x - isz - 30, 16 if low else 18,
				UI.AMBER if in_hand else UI.WHITE, true)
		else:
			UI.draw_text(_card, ttl, Vector2(isz + 22, 5 if low else 10), 16 if low else 18, UI.AMBER if in_hand else UI.WHITE, true)
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


## Компьютер, кучки (28.11): карточка справа от кучек, x 808…1256, низ 716 — уже прежней (642×108), зато выше: 156
## (y 560). Кнопка «СНОСКИ МАНУАЛА» (1076,676 180×34) остаётся на месте: если она есть, правый нижний угол карточки
## (x ≥ 1068, y ≥ 668) свободен — строки ниже y 668 короче (обтекают кнопку). Содержимое и правила — как у прежней
## карточки; кегль не мельче, чем был в прежней (pc_old_*). Если в 156 так не помещается (длинная сноска, описание при
## 150 %), карточка растёт вверх (pc_need_h), но не выше колонки Барти под списком деталей — пузырь Барти на это время
## скрыт (job.gd).
const PC_NOTES_CORNER := Vector2(1068, 668)
var _pc_h := 156.0


## Угол под «СНОСКИ МАНУАЛА» в координатах карточки высотой h (Vector2.ZERO — кнопки нет).
func pc_corner(h: float = -1.0) -> Vector2:
	if job_screen == null or Content.job_notes(job_screen.job).is_empty():
		return Vector2.ZERO
	var hh := _pc_h if h < 0 else h
	return Vector2(PC_NOTES_CORNER.x - PC_CARD.position.x, hh - (PC_CARD.end.y - PC_NOTES_CORNER.y))


## Карточка на экране сейчас (её высота — по содержимому, pc_need_h).
func pc_card_rect() -> Rect2:
	return Rect2(PC_CARD.position.x, PC_CARD.end.y - _pc_h, PC_CARD.size.x, _pc_h)


## Наибольшая высота карточки: до колонки Барти под списком деталей.
func pc_max_h() -> float:
	var top: float = float(job_screen.right_col_top()) + 10 if job_screen != null and job_screen.has_method("right_col_top") \
		else PC_CARD.position.y
	return maxf(PC_CARD.size.y, PC_CARD.end.y - top)


## Строки текста с переносом по словам от (x, y) шириной w; строка, что заходит ниже угла corner.y, — до corner.x.
## Возврат: [[строка, y], …], низ последней строки, всё ли в своей ширине.
static func pc_flow(text: String, x: float, y: float, w: float, corner: Vector2, size: int, bold: bool = false) -> Array:
	var lh := UI.line_height(size, bold) + 2
	var out: Array = []
	var ok := true
	var words := text.split(" ")
	var i := 0
	while i < words.size():
		var lw := w if corner == Vector2.ZERO or y + lh - 2 <= corner.y else minf(w, corner.x - x)
		var cur := words[i]
		i += 1
		while i < words.size() and UI.text_width(cur + " " + words[i], size, bold) <= lw:
			cur += " " + words[i]
			i += 1
		ok = ok and UI.text_width(cur, size, bold) <= lw
		out.append([cur, y])
		y += lh
	return [out, y - 2, ok]


## Что сейчас в карточке компьютера: ["tool", tid, в руке] | ["note", pid] | ["tutor"] | ["hint"].
func pc_card_what() -> Array:
	var sel: String = job_screen.sel_tool
	var tid := _hover_tid if _hover_tid != "" else sel
	var npid := note_pid()
	if npid != "":
		return ["note", npid]
	if tid != "":
		return ["tool", tid, tid == sel]
	if not job_screen.tutor_want().is_empty():
		return ["tutor"]
	return ["hint"]


## Раскладка содержимого what в карточке высотой h: {kind, кегли…, ok, ge_old (не мельче прежней карточки)}; draw —
## нарисовать в _card.
func pc_card_lay(what: Array, h: float, draw: bool = false) -> Dictionary:
	match what[0]:
		"note":
			return pc_card_note(what[1], h, draw)
		"tool":
			return pc_card_tool(what[1], what[2], h, draw)
		"tutor":
			return pc_card_tutor(h, draw)
	return pc_card_hint(h, draw)


## Высота карточки для what: наименьшая из 156, 160, … до pc_max_h(), при которой всё помещается кеглем не мельче
## прежней карточки.
func pc_need_h(what: Array) -> float:
	var hmax := pc_max_h()
	var h := PC_CARD.size.y
	while h < hmax:
		var d := pc_card_lay(what, h)
		if bool(d["ok"]) and bool(d["ge_old"]):
			return h
		h = minf(h + 4, hmax)
	return hmax


## Совместимость с проверками: раскладка того, что в карточке сейчас, при её нынешней высоте.
func pc_card(draw: bool = false) -> Dictionary:
	var d := pc_card_lay(pc_card_what(), _pc_h, draw)
	d["h"] = _pc_h
	return d


func pc_card_tutor(h: float = -1.0, draw: bool = false) -> Dictionary:
	var sz := Vector2(PC_CARD.size.x, _pc_h if h < 0 else h)
	var cn := pc_corner(sz.y)
	var tt := Loc.t("Обучение: нужный инструмент обведён зелёным — возьми его, потом коснись детали в зелёном кружке."
		if UI.touch() else "Обучение: нужный инструмент обведён зелёным — возьми его, потом кликни деталь в зелёном кружке.")
	var s_ := 15
	var f: Array = []
	while true:
		f = pc_flow(tt, 16, 12, sz.x - 32, cn, s_)
		if (f[2] and float(f[1]) <= sz.y - 4) or s_ <= 10:
			break
		s_ -= 1
	if draw:
		_pc_draw(f[0], 16, s_, UI.GOOD, false)
	return {"kind": "tutor", "size": s_, "ok": f[2] and float(f[1]) <= sz.y - 4, "ge_old": s_ >= 15}


func pc_card_hint(h: float = -1.0, draw: bool = false) -> Dictionary:
	var sz := Vector2(PC_CARD.size.x, _pc_h if h < 0 else h)
	var cn := pc_corner(sz.y)
	var hint := Loc.t("Выбери инструмент, потом коснись детали на коляске или в списке" if UI.touch() else
		"Выбери инструмент, потом кликни деталь на коляске или в списке")
	var book: bool = not Content.manual_notes.get(job_screen.job["id"], {}).is_empty()
	var bt := Loc.t("У деталей с книжкой есть сноска из мануала — коснись книжки; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа."
		if UI.touch() else "У деталей с книжкой есть сноска из мануала — наведи или кликни книжку; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа.")
	var fh := pc_flow(hint, 16, 12, sz.x - 32, cn, 15)
	var bs := 14
	var fb: Array = [[], fh[1], true]
	if book:
		while true:
			fb = pc_flow(bt, 44, float(fh[1]) + 2 + 7, sz.x - 60, cn, bs)
			if (fb[2] and float(fb[1]) <= sz.y - 4) or bs <= 9:
				break
			bs -= 1
	if draw:
		_pc_draw(fh[0], 16, 15, UI.GREY, false)
		if book:
			BookIcon.draw_icon(_card, Vector2(26, float(fh[1]) + 2 + 16), 10, UI.CYAN)
			_pc_draw(fb[0], 44, bs, UI.CYAN, false)
	var old := pc_old_book(job_screen.job)
	return {"kind": "hint", "size": 15, "book": bs if book else 0, "old_book": old,
		"ok": fh[2] and fb[2] and float(fb[1] if book else fh[1]) <= sz.y - 4, "ge_old": (bs if book else 0) >= old}


func pc_card_tool(tid: String, in_hand: bool, h: float = -1.0, draw: bool = false) -> Dictionary:
	var sz := Vector2(PC_CARD.size.x, _pc_h if h < 0 else h)
	var cn := pc_corner(sz.y)
	var ttl := (Loc.t("В РУКЕ: ") if in_hand else "") + Loc.t(Content.tools[tid]["name"])
	var hint := Loc.t(Content.tools[tid]["hint"])
	var isz := 44.0
	var ft := pc_flow(ttl, isz + 22, 10, sz.x - isz - 30, cn, 18, true)
	var n: int = (ft[0] as Array).size()
	var hy := 36.0 if n <= 1 else float(ft[1]) + 6
	var hs := 15
	var fd: Array = []
	while true:
		fd = pc_flow(hint, isz + 22, hy, sz.x - isz - 34, cn, hs)
		if (fd[2] and float(fd[1]) <= sz.y - 4) or hs <= 9:
			break
		hs -= 1
	if draw:
		var tex := Content.texture("tool_%s.png" % tid)
		if tex:
			_card.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(10, floorf(minf(sz.y - isz, 108 - isz) / 2.0),
				isz, isz)), false)
		_pc_draw(ft[0], isz + 22, 18, UI.AMBER if in_hand else UI.WHITE, true)
		_pc_draw(fd[0], isz + 22, hs, UI.GREY, false)
	var old := pc_old_tool(tid)
	return {"kind": "tool", "title_lines": n, "size": hs, "old": old,
		"ok": n <= 2 and ft[2] and fd[2] and float(fd[1]) <= sz.y - 4, "ge_old": hs >= old}


func pc_card_note(pid: String, h: float = -1.0, draw: bool = false) -> Dictionary:
	var sz := Vector2(PC_CARD.size.x, _pc_h if h < 0 else h)
	var cn := pc_corner(sz.y)
	var note: Dictionary = Content.manual_notes[job_screen.job["id"]][pid]
	var head := note_head(note)
	var text := Loc.t(note["text"])
	var w := sz.x - 62
	var fh: Array = []
	var ft: Array = []
	var hs := 12
	var ts := 11
	for pair: Array in [[15, 15], [14, 14], [13, 13], [12, 12], [12, 11]]:
		hs = pair[0]
		ts = pair[1]
		fh = pc_flow(head, 46, 8, w, cn, hs)
		ft = pc_flow(text, 46, float(fh[1]) + 2 + 4, w, cn, ts)
		if fh[2] and ft[2] and float(ft[1]) <= sz.y - 6:
			break
	if draw:
		BookIcon.draw_icon(_card, Vector2(26, 22), 13, UI.CYAN)
		_pc_draw(fh[0], 46, hs, UI.CYAN, false)
		_pc_draw(ft[0], 46, ts, UI.WHITE, false)
	var old := pc_old_note(job_screen.job, pid)
	return {"kind": "note", "head": hs, "size": ts, "old": old, "ok": fh[2] and ft[2] and float(ft[1]) <= sz.y - 6,
		"ge_old": hs >= int(old[0]) and ts >= int(old[1])}


## Прежняя карточка компьютера (642×108 с x 614, как game.py): кегль описания инструмента.
static func pc_old_tool(tid: String) -> int:
	var hint := Loc.t(Content.tools[tid]["hint"])
	return UI.fit_wrapped_size(hint, 642.0 - 44 - 34, 15, 108.0 - 4 - 36, 9)


## Прежняя карточка: кегли сноски [заголовок, текст].
static func pc_old_note(job: Dictionary, pid: String) -> Array:
	var note: Dictionary = Content.manual_notes[job["id"]][pid]
	var head := note_head(note)
	var text := Loc.t(note["text"])
	var w := 642.0 - 62
	for pair: Array in [[15, 15], [14, 14], [13, 13], [12, 12], [12, 11]]:
		var hh := UI.wrap_lines(head, w, pair[0]).size() * (UI.line_height(pair[0]) + 2)
		var th := UI.wrap_lines(text, w, pair[1]).size() * (UI.line_height(pair[1]) + 2)
		if 8 + hh + 4 + th <= 108.0 - 6:
			return pair
	return [12, 11]


## Прежняя карточка: кегль строки про книжку в общей подсказке (0 — у задания нет сносок).
static func pc_old_book(job: Dictionary) -> int:
	if Content.manual_notes.get(job["id"], {}).is_empty():
		return 0
	var hint := Loc.t("Выбери инструмент, потом коснись детали на коляске или в списке" if UI.touch() else
		"Выбери инструмент, потом кликни деталь на коляске или в списке")
	var bt := Loc.t("У деталей с книжкой есть сноска из мануала — коснись книжки; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа."
		if UI.touch() else "У деталей с книжкой есть сноска из мануала — наведи или кликни книжку; все сразу — кнопка «СНОСКИ МАНУАЛА» внизу справа.")
	var y := 12 + UI.wrap_lines(hint, 642.0 - 32, 15).size() * (UI.line_height(15) + 2)
	return UI.fit_wrapped_size(bt, 642.0 - 60, 14, 108.0 - 4 - (y + 7), 9)


func _pc_draw(lines: Array, x: float, size: int, col: Color, bold: bool) -> void:
	for ln: Array in lines:
		if float(ln[1]) + UI.line_height(size, bold) <= _card.size.y - 2:     # строка за низом — не рисуем
			UI.draw_text(_card, ln[0], Vector2(x, ln[1]), size, col, bold)


## Карточка компьютера с кучками: фон (без угла под «СНОСКИ МАНУАЛА») и содержимое.
func _draw_card_pc() -> void:
	var sz := _card.size
	var cn := pc_corner(sz.y)
	var col := Color8(22, 20, 30, 215)
	if cn == Vector2.ZERO:
		UI.draw_round_rect(_card, Rect2(Vector2.ZERO, sz), col, Color(), 0, 12)
	else:                                      # «Г»: верх во всю ширину, низ — левее кнопки (углы скруглены)
		_card.draw_colored_polygon(_l_poly(sz.x, sz.y, cn.x, cn.y - 2, 12.0), col)
	pc_card_lay(pc_card_what(), sz.y, true)


static func _arc(pts: PackedVector2Array, c: Vector2, r: float, a0: float, a1: float) -> void:
	for k in 7:
		var a := deg_to_rad(lerpf(a0, a1, k / 6.0))
		pts.append(c + Vector2(cos(a), sin(a)) * r)


## Контур «Г» (w × h, вырез справа снизу от (cx, cy)) со скруглёнными углами r.
static func _l_poly(w: float, h: float, cx: float, cy: float, r: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	_arc(pts, Vector2(r, r), r, 180, 270)
	_arc(pts, Vector2(w - r, r), r, 270, 360)
	_arc(pts, Vector2(w - r, cy - r), r, 0, 90)
	_arc(pts, Vector2(cx + r, cy + r), r, 270, 180)
	_arc(pts, Vector2(cx - r, h - r), r, 0, 90)
	_arc(pts, Vector2(r, h - r), r, 90, 180)
	return pts


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
