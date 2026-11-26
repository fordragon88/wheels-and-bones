class_name MiniGame
extends Control
## Мини-игра шага (mini в данных; start_mini/_draw_mini_overlay/_click_mini в game.py) — модальное окно поверх
## задания: шапка (инструкция шага + подсказка), «ПОЗЖЕ» (закрыть, шаг остаётся).
##   pump  — «КАЧАТЬ» (+6…12, выше шкалы — «БАБАХ!»), «СТРАВИТЬ» (−3…6), «ГОТОВО, ПРОВЕРЯЮ»; тон по давлению.
##   gap   — шкала зазора: клик/тап (и перетаскивание), ←/→ с клавиатуры; «ПРОВЕРИТЬ».
##   ping  — спицы по кругу: «пинь» звонкая, «тук» глухая; найти все глухие.
##   meter — табло прибора и варианты вывода.
## Сигналы: solved (шаг выполнен), missed(текст, с) — ошибка (экран считает её), closed (ПОЗЖЕ / Esc).

signal solved
signal missed(msg: String, secs: float)
signal closed

const P0 := Rect2(280, 150, 720, 440)
const PP := Rect2(200, 64, 880, 640)      # телефонный режим: окно выше и шире (спицы по кругу 56, «ПОЗЖЕ» 56)
var P: Rect2:
	get:
		return PP if UI.phone() else P0
const PH_SPOKE_R := 130                   # телефон: кружки спиц 56 на радиусе 130 (между соседними > 8)
const PH_RIM_R := 170


## Центр колеса «спиц».
func ping_center() -> Vector2:
	return Vector2(P.get_center().x, P.position.y + (250 if UI.phone() else 230))

var step: Dictionary = {}
var cfg: Dictionary = {}
var kind: String = ""
var value: int = 0
var dull: Dictionary = {}
var tested: Dictionary = {}
var _first: Control
var _release: GameButton
var _track: GapTrack
var _spokes: Array[GameButton] = []
var _sp_sig: Array = []


static func make(st: Dictionary) -> MiniGame:
	var m := MiniGame.new()
	m.step = st
	m.cfg = st["mini"]
	m.kind = m.cfg["kind"]
	if m.kind == "pump":
		m.value = 0
	elif m.kind == "gap":
		m.value = int(m.cfg.get("start", m.cfg["mx"]))
	elif m.kind == "ping":
		var idx: Array = range(int(m.cfg["total"]))
		idx.shuffle()
		for i in int(m.cfg["dull"]):
			m.dull[idx[i]] = true
	return m


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Mini"


func _ready() -> void:
	var cancel := GameButton.make(Rect2(P.end.x - 160, P.end.y - 64, 140, 56) if UI.phone()
		else Rect2(P.end.x - 160, P.end.y - 56, 140, 42), "ПОЗЖЕ", UI.GREY)
	cancel.name = "Later"
	cancel.pressed.connect(close)
	match kind:
		"pump":
			var b := _btn("Pump", Rect2(P.position.x + 40, P.end.y - 130, 200, 56), "КАЧАТЬ", UI.AMBER, pump)
			_release = _btn("Release", Rect2(P.position.x + 256, P.end.y - 130, 168, 56), "СТРАВИТЬ", UI.CYAN, release)
			_btn("Done", Rect2(P.end.x - 280, P.end.y - 130, 240, 56), "ГОТОВО, ПРОВЕРЯЮ", UI.GOOD, pump_done)
			_first = b
		"gap":
			_track = GapTrack.new()
			_track.mini = self
			_track.position = Vector2(P.position.x + 60, P.position.y + 170)
			_track.size = Vector2(600, 30)
			if UI.phone():                         # телефон: зона пальца 56 (шкала рисуется прежней толщины)
				_track.position = Vector2(P.get_center().x - 300, P.position.y + 157)
				_track.size = Vector2(600, 56)
			UI.touch_block(_track)                     # _click_mini: дорожка зазора — без переноса (block)
			add_child(_track)
			_btn("Check", Rect2(P.get_center().x - 130, P.end.y - 130, 260, 56), "ПРОВЕРИТЬ", UI.GOOD, gap_check)
			_first = _track
		"ping":
			var c := ping_center()
			var total := int(cfg["total"])
			for i in total:
				var ang := deg_to_rad(i * (360.0 / total) - 90)
				var at := c + Vector2(cos(ang), sin(ang)) * (PH_SPOKE_R if UI.phone() else 95)
				var b := GameButton.make(Rect2(int(at.x) - 17, int(at.y) - 17, 34, 34), "", UI.AMBER)
				if UI.phone():                     # телефон: кружок 56, попадание — по кругу (соседи не перекрываются)
					b.position = Vector2(int(at.x) - 28, int(at.y) - 28)
					b.size = Vector2(56, 56)
					b.hit_circle = true
				b.name = "Spoke_%d" % i
				b.plain = true
				b.set_meta("i", i)
				b.set_meta("a11y_group", "Спицы")
				b.on_draw = _draw_spoke
				b.redraw_sig = func() -> Array: return [tested.duplicate(), dull.duplicate()]   # проверенная спица — цвет
				b.pressed.connect(ping.bind(i))
				add_child(b)
				_spokes.append(b)
			_first = _spokes[0]
		"meter":
			var opts: Array = cfg["options"]
			for i in opts.size():
				var b := GameButton.make(Rect2(P.position.x + 40, P.position.y + 202 + i * 70, P.size.x - 240, 62), "", UI.CYAN)
				b.name = "Opt_%d" % i
				b.plain = true
				b.set_meta("i", i)
				b.accessibility_name = Loc.t(opts[i][0])
				b.set_meta("a11y_group", "Выводы")
				b.on_draw = _draw_option
				b.redraw_sig = func() -> int: return 0              # наведение видит сама кнопка
				b.pressed.connect(meter.bind(i))
				add_child(b)
				if i == 0:
					_first = b
	add_child(cancel)
	_lang_names()
	Loc.changed.connect(_lang_names)
	UI.focus_later(_first)


## Подписи для чтеца экрана на языке игры: окно (инструкция шага), варианты прибора, спицы — и после смены языка при
## открытом окне (Loc.changed).
func _lang_names() -> void:
	accessibility_name = Loc.t(step["instr"])
	for c: Node in get_children():                 # «ПОЗЖЕ», «НАКАЧАТЬ»… — подписи кнопок на новом языке (обзор 26.11, E24)
		if c is GameButton:
			(c as GameButton).update_a11y()
			(c as GameButton).queue_redraw()
	if kind == "meter":
		var opts: Array = cfg["options"]
		for i in opts.size():
			var b := get_node_or_null("Opt_%d" % i) as Control
			if b:
				b.accessibility_name = Loc.t(opts[i][0])
	_spoke_names()


func _btn(nm: String, r: Rect2, lbl: String, col: Color, cb: Callable) -> GameButton:
	var b := GameButton.make(r, lbl, col)
	b.name = nm
	b.pressed.connect(cb)
	add_child(b)
	return b


func first_focus() -> Control:
	return _first


## Подписи спиц как в a11y_items game.py: «Спица 3 из 12», проверенная — «, звонкая» / «, глухая».
func _spoke_names() -> void:
	var sig := [tested.keys(), dull.keys(), Loc.code]
	if sig == _sp_sig:
		return
	_sp_sig = sig
	for i in _spokes.size():
		var st := ""
		if tested.has(i):
			st = ", " + Loc.t("глухая" if dull.has(i) else "звонкая")
		_spokes[i].accessibility_name = Loc.t("Спица") + " " + A11y._of(i + 1, _spokes.size()) + st


## Список клавиатуры окна мини-игры: его пункты и «назад» экрана (в game.py значок рисуется поверх окна и тоже в
## списке — последним).
func kb_order(items: Array) -> Array:
	return A11y.with_screen_back(items)


func close() -> void:
	Audio.sfx("tick")
	closed.emit()


func _process(_dt: float) -> void:
	if not _spokes.is_empty():
		_spoke_names()
	if _release:
		_release.enabled = value > 0
	# окно стоит — перерисовка, когда сменилось значение, проверенные спицы или фокус шкалы
	Screen.redraw_on(self, [value, tested.duplicate(), dull.duplicate(), _track != null and _track.has_focus() and UI.kb_active])


func _gui_input(_e: InputEvent) -> void:
	accept_event()


func _say_value() -> void:
	var zone := _in_zone(value)
	Speech.say("%d %s" % [value, Loc.t(cfg["unit"])] + ((", " + Loc.t("зелёная зона")) if zone else ""), true)


# ---------------- действия (как mini_* в game.py) ----------------

func pump() -> void:
	value += randi_range(6, 12)
	if value > int(cfg["mx"]):
		value = 0
		Audio.sfx("pop")
		missed.emit("БАБАХ! Перекачал сверх шкалы — камере конец, ставим новую. Заново.", 3.5)
	else:
		Audio.sfx("hiss")
		Audio.pitch(float(value) / float(cfg["mx"]))
		_say_value()


func release() -> void:
	if value <= 0:
		return
	value = maxi(0, value - randi_range(3, 6))
	Audio.sfx("hiss")
	_say_value()


func pump_done() -> void:
	var v := value
	if _in_zone(v):
		solved.emit()
	elif v < float(cfg["lo"]):
		missed.emit(Loc.fmt("Мало ({0} {1}): докачай до зелёной зоны.", [v, cfg["unit"]]), 3.0)
	else:
		value = maxi(0, floori(float(cfg["lo"]) - 25.0))
		missed.emit(Loc.fmt("Перекачал ({0} {1}): стравили воздух, заново.", [v, cfg["unit"]]), 3.0)


func gap_set(v: int) -> void:
	value = clampi(v, int(cfg["mn"]), int(cfg["mx"]))


func gap_adj(d: int) -> void:
	gap_set(value + d)
	Audio.pitch(float(value - int(cfg["mn"])) / maxf(1, int(cfg["mx"]) - int(cfg["mn"])))


## Зелёная зона: lo ≤ v ≤ hi как в game.py — границы бывают дробными (olga_x3: зазор 3,5–4,5 мм), поэтому
## сравнение числами с дробной частью, не int() (int(3.5) = 3 засчитывал 3 мм).
func _in_zone(v: float) -> bool:
	return float(cfg["lo"]) <= v and v <= float(cfg["hi"])


func gap_check() -> void:
	if _in_zone(value):
		solved.emit()
	elif value < float(cfg["lo"]):
		missed.emit(cfg.get("fb_lo", "Слишком мало."), 3.5)
	else:
		missed.emit(cfg.get("fb_hi", "Слишком много."), 3.5)


func ping(i: int) -> void:
	if tested.has(i):
		return
	tested[i] = true
	if dull.has(i):
		Audio.sfx("dull")
		var found := 0
		for k: int in dull:
			if tested.has(k):
				found += 1
		if found >= dull.size():
			solved.emit()
		else:
			Nav.flash(Loc.fmt("ТУК — глухая спица! Найдено {0}/{1}.", [found, dull.size()]), UI.CYAN, 2.5)
	else:
		Audio.sfx("ping")
		Nav.flash("ПИНЬ — звонкая, натяжение в норме.", UI.GREY, 1.6)


func meter(i: int) -> void:
	var o: Array = cfg["options"][i]
	if o[1]:
		solved.emit()
	else:
		var fb: String = o[2] if o.size() > 2 else ""
		missed.emit(fb if fb != "" else "Неверный вывод из замера.", 4.0)


# ---------------- рисование ----------------

func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 180))
	draw_rect(P, Color8(22, 28, 30, 250))
	UI.draw_round_rect(self, P, Color(0, 0, 0, 0), UI.AMBER, 2, 10)
	var tip: String = Loc.t(cfg.get("hint", cfg.get("prompt", "")))
	var instr := Loc.t(step["instr"])
	var isz := 14
	var tsz := 11
	for pair: Array in [[19, 14], [18, 13], [17, 13], [16, 12], [15, 12], [14, 11]]:
		isz = pair[0]
		tsz = pair[1]
		var ih := UI.wrap_lines(instr, P.size.x - 48, isz).size() * (UI.line_height(isz) + 2)
		var th := UI.wrap_lines(tip, P.size.x - 48, tsz).size() * (UI.line_height(tsz) + 2) if tip != "" else 0.0
		if 16 + ih + 2 + th <= 90:
			break
	var y_end := UI.draw_wrapped(self, instr, P.position + Vector2(24, 16), P.size.x - 48, isz, UI.WHITE, false, 2, -1, 3)
	if tip != "":
		UI.draw_wrapped(self, tip, Vector2(P.position.x + 24, y_end + 2), P.size.x - 48, tsz, UI.AMBER, false, 2, -1, 2)
	match kind:
		"pump":
			_draw_pump()
		"gap":
			_draw_gap()
		"ping":
			_draw_ping()
		"meter":
			_draw_meter()


func _draw_pump() -> void:
	var bar := Rect2(P.get_center().x - 300 if UI.phone() else P.position.x + 60, P.position.y + 150, 600, 36)
	var mx := float(cfg["mx"])
	UI.draw_round_rect(self, bar, UI.PANEL, Color(), 0, 6)
	var zx := bar.position.x + bar.size.x * float(cfg["lo"]) / mx
	var zw := bar.size.x * (float(cfg["hi"]) - float(cfg["lo"])) / mx
	UI.draw_round_rect(self, Rect2(zx, bar.position.y, zw, bar.size.y), Color8(40, 70, 48), Color(), 0, 6)
	var vw := bar.size.x * minf(value, mx) / mx
	if vw > 0:
		UI.draw_round_rect(self, Rect2(bar.position.x, bar.position.y + 10, vw, bar.size.y - 20), UI.AMBER, Color(), 0, 6)
	UI.draw_round_rect(self, Rect2(zx, bar.position.y, zw, bar.size.y), Color(0, 0, 0, 0), UI.GOOD, 2, 6)
	UI.draw_round_rect(self, bar, Color(0, 0, 0, 0), UI.DIM, 2, 6)
	UI.draw_text(self, "%d %s" % [value, Loc.t(cfg["unit"])], Vector2(bar.get_center().x, bar.end.y + 18), 30, UI.WHITE, true, 1)


func _draw_gap() -> void:
	var trk := Rect2(_track.position, _track.size)
	if UI.phone():                               # зона пальца 56, шкала — прежние 30 по её середине
		trk = Rect2(_track.position + Vector2(0, 13), Vector2(_track.size.x, 30))
	var mn := float(cfg["mn"])
	var span := float(cfg["mx"]) - mn
	UI.draw_round_rect(self, trk, UI.PANEL, Color(), 0, 6)
	var zx := trk.position.x + trk.size.x * (float(cfg["lo"]) - mn) / span
	var zw := maxf(8, trk.size.x * (float(cfg["hi"]) - float(cfg["lo"])) / span)
	UI.draw_round_rect(self, Rect2(zx, trk.position.y, zw, trk.size.y), Color8(40, 70, 48), UI.GOOD, 2, 6)
	UI.draw_round_rect(self, trk, Color(0, 0, 0, 0), UI.DIM, 2, 6)
	var vx := trk.position.x + trk.size.x * (value - mn) / span
	UI.draw_round_rect(self, Rect2(vx - 3, trk.position.y - 8, 6, trk.size.y + 16), UI.CYAN, Color(), 0, 3)
	UI.draw_text(self, str(cfg["mn"]).trim_suffix(".0"), Vector2(trk.position.x, trk.end.y + 8), 13, UI.GREY)
	UI.draw_text(self, str(cfg["mx"]).trim_suffix(".0"), Vector2(trk.end.x, trk.end.y + 8), 13, UI.GREY, false, 2)
	var text := "%s: %d %s" % [Loc.t(cfg.get("label", "Значение")), value, Loc.t(cfg["unit"])]
	var sz := 26
	while sz > 16 and UI.text_width(text, sz, true) > P.size.x - 48:
		sz -= 1
	UI.draw_text(self, text, Vector2(trk.get_center().x, trk.end.y + 46), sz, UI.WHITE, true, 1)
	UI.draw_text(self, Loc.t("Коснись шкалы, чтобы выставить значение." if UI.touch() else
		"Кликни по шкале, чтобы выставить значение."), Vector2(trk.get_center().x, trk.end.y + 82),
		14, UI.GREY, false, 1)
	if _track.has_focus() and UI.kb_active:
		UI.draw_round_rect(self, trk.grow(5), Color(0, 0, 0, 0), UI.WHITE, 2, 9)


func _draw_ping() -> void:
	var c := ping_center()
	var rim := PH_RIM_R if UI.phone() else 150
	var found := 0
	for k: int in dull:
		if tested.has(k):
			found += 1
	UI.draw_text(self, Loc.tf("Касайся спиц, ищи глухие. Найдено: {0}/{1}" if UI.touch() else
		"Кликай спицы, ищи глухие. Найдено: {0}/{1}", [found, dull.size()]),
		Vector2(P.position.x + 24, P.end.y - 46), 15, UI.CYAN)
	UI.draw_ring(self, c, rim, UI.DIM, 3)
	var total := int(cfg["total"])
	for i in total:
		var ang := deg_to_rad(i * (360.0 / total) - 90)
		var e := c + Vector2(cos(ang), sin(ang)) * (rim - 2)
		var col := (UI.BAD if dull.has(i) else UI.DIM) if tested.has(i) else UI.GHOST
		draw_line(c, e, col, 3.0 if (tested.has(i) and dull.has(i)) else 2.0, true)
	draw_circle(c, 18, UI.AMBER, true, -1, true)


func _draw_spoke(b: GameButton, _r: Rect2) -> void:
	var i: int = b.get_meta("i")
	var c := b.size / 2.0
	var rr := 22.0 if UI.phone() else 15.0     # телефон: кружок спицы крупнее (зона пальца — круг 56)
	if tested.has(i):
		var d := dull.has(i)
		b.draw_circle(c, rr, UI.BAD if d else UI.PANEL2, true, -1, true)
		UI.draw_ring(b, c, rr, UI.BAD if d else UI.DIM, 2)
	else:
		b.draw_circle(c, rr, UI.PANEL2, true, -1, true)
		UI.draw_ring(b, c, rr, UI.AMBER if b.is_hovered() else UI.GREY, 2)


func _draw_meter() -> void:
	var disp := Rect2(P.get_center().x - 160, P.position.y + 92, 320, 64)
	UI.draw_round_rect(self, disp, Color8(16, 24, 18), UI.GOOD, 2, 8)
	var reading := Loc.t(cfg["reading"])
	var rsz := 34
	while rsz > 14 and UI.text_width(reading, rsz, true) > disp.size.x - 24:
		rsz -= 1
	if UI.text_width(reading, rsz, true) <= disp.size.x - 24:
		UI.draw_text(self, reading, disp.get_center(), rsz, UI.GOOD, true, 1)
	else:                                      # длинное показание — в две строки
		var lines: PackedStringArray = []
		for s: int in [16, 15, 14, 13, 12]:
			rsz = s
			lines = UI.wrap_lines(reading, disp.size.x - 24, s, true)
			if lines.size() <= 2:
				break
		var n := mini(2, lines.size())
		var lh := UI.line_height(rsz, true)
		for i in n:
			UI.draw_text(self, lines[i], disp.get_center() + Vector2(0, (i - (n - 1) / 2.0) * (lh + 1)), rsz, UI.GOOD, true, 1)
	if cfg.get("sub", "") != "":
		UI.draw_wrapped(self, Loc.t(cfg["sub"]), Vector2(P.get_center().x, disp.end.y + 6), P.size.x - 60, 13, UI.GREY, true,
			2, -1, 2)


func _draw_option(b: GameButton, _r: Rect2) -> void:
	var i: int = b.get_meta("i")
	var r := Rect2(Vector2.ZERO, b.size)
	UI.draw_round_rect(b, r, UI.PANEL, UI.CYAN if b.is_hovered() else UI.DIM, 2, 8)
	var text := Loc.t(cfg["options"][i][0])
	var osz := 11
	for s: int in [15, 14, 13, 12, 11]:
		osz = s
		if UI.wrap_lines(text, r.size.x - 28, s).size() * (UI.line_height(s) + 2) <= r.size.y - 14:
			break
	UI.draw_wrapped(b, text, Vector2(14, 10), r.size.x - 28, osz, UI.WHITE)
