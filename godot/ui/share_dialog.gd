class_name ShareDialog
extends Control
## Окно кодов и ссылок (share_ui в game.py: _draw_share, _share_btn_rects, handle_share_event). Режимы:
##   show     — код/ссылка/текст скопированы (или «перепиши код» крупно группами по 6, если буфер недоступен);
##   paste    — «ВСТАВИТЬ КОД»: поле (Ctrl+V, «ИЗ БУФЕРА»), «ПРИМЕНИТЬ»;
##   confirm  — «ПОДТВЕРДИ» (загрузить прогресс / начать задание);
##   result   — «РЕЗУЛЬТАТ УЧЕНИКА» (чужой код результата, только чтение);
##   summary  — «ИТОГ ЗАДАНИЯ» (код результата, текстом, в таблицу, выйти из задания, в мастерскую);
##   builder  — «ССЫЛКА-ЗАДАНИЕ»: 21 поломка и 9 примерок по порядку отметок, «От кого», код/ссылка;
##   resume   — (нет в game.py, просьба владельца 12.11) запуск без ссылки при незаконченном задании:
##              «Продолжить задание» или «Обычная игра».
## Состояние окна — словарь ui (как share_ui); «назад» (окно «скопировано») — словарь прежнего окна.

signal closed

var ui: Dictionary = {}
var _field: ShareField
var _picks: Array = []


static func make(state: Dictionary) -> ShareDialog:
	var d := ShareDialog.new()
	d.ui = state
	return d


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Share"


func mode() -> String:
	return str(ui.get("mode", ""))


func panel() -> Rect2:
	var m := mode()
	if m == "builder":
		return Rect2(40, 12, UI.W - 80, UI.H - 24)
	if m in ["summary", "result"]:
		return Rect2(UI.W / 2.0 - 430, 34, 860, UI.H - 68)
	if m == "show" and ui.get("kind") == "text":
		return Rect2(UI.W / 2.0 - 430, 60, 860, UI.H - 120)
	if m in ["confirm", "resume"]:
		return Rect2(UI.W / 2.0 - 390, UI.H / 2.0 - 160, 780, 320)
	return Rect2(UI.W / 2.0 - 390, UI.H / 2.0 - 210, 780, 420)


func field_rect() -> Rect2:
	var p := panel()
	match mode():
		"paste":
			return Rect2(p.position.x + 28, p.position.y + 104, p.size.x - 56, 44)
		"builder":
			return Rect2(p.position.x + 300, p.end.y - 124, 420, 40)
		"show":
			if ui.get("kind") != "text":
				return Rect2(p.position.x + 28, p.position.y + 76, p.size.x - 56, 40)
	return Rect2()


## Поле ввода окна: paste — «text», builder — «name» (_share_field_key).
func field_key() -> String:
	return {"paste": "text", "builder": "name"}.get(mode(), "")


@warning_ignore("integer_division")
func pick_rects() -> Array:
	if mode() != "builder":
		return []
	var p := panel()
	var cw := int((p.size.x - 56 - 24) / 3)
	var out: Array = []
	var jobs: Array = Share.job_ids()
	for i in jobs.size():
		out.append([jobs[i], Rect2(p.position.x + 28 + (i / 7) * (cw + 12), p.position.y + 86 + (i % 7) * 42, cw, 38)])
	var y0 := p.position.y + 86 + 7 * 42 + 30
	var seats: Array = Share.seat_ids()
	for i in seats.size():
		out.append([seats[i], Rect2(p.position.x + 28 + (i % 3) * (cw + 12), y0 + (i / 3) * 37, cw, 32)])
	return out


## Кнопки окна: [ключ, рамка, подпись, цвет] — по нижнему краю, слева направо (_share_btn_rects).
func btn_specs() -> Array:
	var p := panel()
	var specs: Array = []
	match mode():
		"show":
			specs = [["copy", "СКОПИРОВАТЬ ЕЩЁ РАЗ", UI.CYAN], ["close", "ГОТОВО", UI.AMBER]]
		"paste":
			specs = ([] if OS.has_feature("web") else [["clip", "ИЗ БУФЕРА (Ctrl+V)", UI.CYAN]]) + \
				[["cancel", "ОТМЕНА", UI.GREY], ["apply", "ПРИМЕНИТЬ", UI.GOOD]]
		"confirm":
			specs = [["no", "НЕТ", UI.GREY], ["yes", "ДА", UI.GOOD]]
		"resume":
			specs = [["normal", "ОБЫЧНАЯ ИГРА", UI.CYAN], ["resume", "ПРОДОЛЖИТЬ ЗАДАНИЕ", UI.GOOD]]
		"result":
			specs = [["rtext", "СКОПИРОВАТЬ ТЕКСТОМ", UI.CYAN], ["close", "ГОТОВО", UI.AMBER]]
		"summary":
			specs = [["rcode", "СКОПИРОВАТЬ КОД РЕЗУЛЬТАТА", UI.CYAN], ["rtext", "СКОПИРОВАТЬ ТЕКСТОМ", UI.CYAN]]
			if Share.can_send():
				specs.append(["send", "УЖЕ ОТПРАВЛЕНО" if SaveGame.assign.get("sent", false) else "ОТПРАВИТЬ В ТАБЛИЦУ", UI.GOOD])
			return _row(p, specs, p.end.y - 124) + _row(p, [["exit", "ВЫЙТИ ИЗ ЗАДАНИЯ", UI.PURPLE],
				["close", "В МАСТЕРСКУЮ", UI.AMBER]], p.end.y - 66)
		"builder":
			specs = [["clear", "СНЯТЬ ВСЁ", UI.GREY], ["cancel", "ОТМЕНА", UI.GREY],
				["make", "СКОПИРОВАТЬ ССЫЛКУ" if OS.has_feature("web") else "ПОКАЗАТЬ КОД ЗАДАНИЯ", UI.GOOD]]
		_:
			specs = [["close", "ГОТОВО", UI.AMBER]]
	return _row(p, specs, p.end.y - 66)


@warning_ignore("integer_division")
static func _row(p: Rect2, specs: Array, y: float) -> Array:
	var n := specs.size()
	var w := mini(300, int((p.size.x - 56 - 16 * (n - 1)) / maxi(1, n)))
	var x0 := p.end.x - 28 - n * w - 16 * (n - 1)
	var out: Array = []
	for i in n:
		out.append([specs[i][0], Rect2(x0 + i * (w + 16), y, w, 46), specs[i][1], specs[i][2]])
	return out


func _ready() -> void:
	build()


func build() -> void:
	for c in get_children():
		remove_child(c)
		c.queue_free()
	_picks.clear()
	_field = null
	var fk := field_key()
	if fk != "":
		_field = ShareField.new()
		_field.name = "Field"
		_field.dlg = self
		_field.key = fk
		_field.max_len = Share.max_len() if fk == "text" else 40
		var fr := field_rect()
		_field.position = fr.position
		_field.size = fr.size
		_field.accessibility_name = Loc.t("Код или ссылка") if fk == "text" else Loc.t("Имя")
		add_child(_field)
	for pr: Array in pick_rects():
		var k: String = pr[0]
		var b := GameButton.make(pr[1], "", UI.CYAN)
		b.name = "Pick_" + k
		b.set_meta("k", k)
		b.on_draw = _draw_pick
		b.pressed.connect(action.bind("pick:" + k))
		add_child(b)
		_picks.append(b)
	_update_picks()
	for bs: Array in btn_specs():
		var b := GameButton.make(bs[1], bs[2], bs[3])
		b.name = "Btn_" + bs[0]
		b.enabled = not (bs[0] == "send" and SaveGame.assign.get("sent", false))
		b.update_a11y()
		b.pressed.connect(action.bind(bs[0]))
		add_child(b)
	queue_redraw()


func first_focus() -> Control:
	if _field != null:
		return _field
	var last: Control = null
	for c in get_children():
		if c is GameButton and c.name.begins_with("Btn_"):
			last = c
	return last


func _update_picks() -> void:
	var sel: Array = ui.get("sel", [])
	for b: GameButton in _picks:
		var on: bool = b.get_meta("k") in sel
		b.active = on
		b.color = UI.GOOD if on else UI.CYAN
		var k: String = b.get_meta("k")
		b.accessibility_name = ("%d. " % (sel.find(k) + 1) if on else "") + Share.item_label(k)
		b.queue_redraw()


## Кнопка окна (_share_action) — передаёт Share.
func action(key: String) -> void:
	if key.begins_with("pick:"):
		var k := key.trim_prefix("pick:")
		var sel: Array = ui["sel"]
		if k in sel:
			sel.erase(k)
		else:
			sel.append(k)
		ui["err"] = ""
		Audio.sfx("tick")
		_update_picks()
		queue_redraw()
		return
	Share.dlg_action(self, key)


## Esc: в вопросе — «нет», иначе — закрыть.
func escape() -> void:
	action("no" if mode() == "confirm" else ("normal" if mode() == "resume" else "close"))


func _gui_input(_e: InputEvent) -> void:
	accept_event()


func _process(_dt: float) -> void:
	queue_redraw()


# ---------------- рисование (_draw_share) ----------------

func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 176))
	var p := panel()
	UI.draw_round_rect(self, p, Color8(20, 18, 28), UI.CYAN, 2, 14)
	var x := p.position.x + 28
	var w := p.size.x - 56
	match mode():
		"show":
			UI.draw_text(self, Loc.t(ui.get("title", "")), Vector2(x, p.position.y + 20), 22, UI.CYAN, true)
			var y: float
			if ui.get("kind") == "text":
				UI.draw_wrapped(self, str(ui["text"]).replace("\n", "  ·  "), Vector2(x, p.position.y + 64), w, 15, UI.WHITE,
					false, 2, -1, 16)
				y = p.end.y - 150
			else:
				var fr := field_rect()
				UI.draw_round_rect(self, fr, Color8(12, 12, 18), UI.DIM, 1, 8)
				var s := str(ui["text"])
				var full := s
				while s.length() > 1 and UI.text_width(s + "…", 15) > fr.size.x - 20:
					s = s.substr(0, s.length() - 1)
				s += "…" if s != full else ""
				UI.draw_text(self, s, Vector2(fr.position.x + 10, fr.get_center().y - floorf(UI.line_height(15) / 2)), 15, UI.GREY)
				if ui.get("ok") == false and ui.get("kind") == "code":
					UI.draw_text(self, Loc.t("Перепиши код (заглавные и строчные буквы различаются):"), Vector2(x, fr.end.y + 12), 14,
						UI.GREY)
					_code_block(Rect2(x, fr.end.y + 36, w, 150), full)
				y = p.end.y - 128
			var ok: Variant = ui.get("ok")
			var st := "Скопировано в буфер обмена ✔"
			if ok == null:
				st = "Копирую…"
			elif ok == false:
				if ui.get("kind") == "text":
					st = "Не удалось скопировать — перепиши итог с экрана."
				elif OS.has_feature("web"):
					st = "Не удалось скопировать — выдели строку выше и нажми Ctrl+C."
				else:
					st = "Буфер обмена недоступен — перепиши или сфотографируй код."
			UI.draw_text(self, Loc.t(st), Vector2(x, y), 16, UI.GOOD if ok == true else (UI.GREY if ok == null else UI.AMBER), true)
			if ui.get("note", "") != "":
				UI.draw_wrapped(self, Loc.t(ui["note"]), Vector2(x, y + 26), w, 14, UI.GREY, false, 2, -1, 2)
		"paste":
			UI.draw_text(self, Loc.t("ВСТАВИТЬ КОД"), Vector2(x, p.position.y + 20), 22, UI.CYAN, true)
			UI.draw_text(self, Loc.t("Код прогресса, задания или результата — или ссылка с ним:"), Vector2(x, p.position.y + 72), 15,
				UI.WHITE)
			if ui.get("err", "") != "":
				UI.draw_text(self, Loc.t(ui["err"]), Vector2(x, p.position.y + 162), 16, UI.BAD, true)
			UI.draw_wrapped(self, Loc.t("Код прогресса заменит твой прогресс (после вопроса; прежний можно вернуть). Код задания откроет задание, код результата покажет итог ученика."),
				Vector2(x, p.position.y + 196), w, 14, UI.GREY)
		"confirm", "resume":
			UI.draw_text(self, Loc.t("ПОДТВЕРДИ" if mode() == "confirm" else "ЗАДАНИЕ НЕ ЗАКОНЧЕНО"), Vector2(x, p.position.y + 20), 22,
				UI.CYAN, true)
			var y := UI.draw_wrapped(self, Loc.t(ui.get("q", "")), Vector2(x, p.position.y + 70), w, 20, UI.WHITE, false, 2, -1, 3)
			UI.draw_wrapped(self, Loc.t(ui.get("sub", "")), Vector2(x, y + 12), w, 15, UI.GREY, false, 2, -1, 4)
		"summary", "result":
			var res: Dictionary = ui.get("res", {}) if mode() == "result" else Share.assign_result()
			UI.draw_text(self, Loc.t("ИТОГ ЗАДАНИЯ" if mode() == "summary" else "РЕЗУЛЬТАТ УЧЕНИКА"), Vector2(x, p.position.y + 18), 22,
				UI.CYAN, true)
			_fit(Share.assign_head(res.get("from", ""), res.get("title", "")), Vector2(x, p.position.y + 52), w, 16, UI.WHITE)
			UI.draw_text(self, Share.result_summary(res["rows"]), Vector2(p.end.x - 28, p.position.y + 20), 20, UI.GOOD, true, 2)
			var bottom := p.end.y - (138 if mode() == "summary" else 80)
			_result_rows(Rect2(x, p.position.y + 86, w, bottom - p.position.y - 86 - 26), res)
			if mode() == "summary":
				UI.draw_text(self, Loc.t("Код результата защищён: если поправить в нём цифры, игра его не примет."),
					Vector2(x, bottom - 22), 13, UI.GREY)
			elif str(res.get("version", "")) != "":
				UI.draw_text(self, Loc.t("Версия игры: %s" % res["version"]), Vector2(x, bottom - 22), 13, UI.GREY)
		"builder":
			UI.draw_text(self, Loc.t("ССЫЛКА-ЗАДАНИЕ"), Vector2(x, p.position.y + 16), 22, UI.CYAN, true)
			UI.draw_text(self, Loc.t("Отметь задания по порядку — ученик увидит только их, без обучения и замков."),
				Vector2(x, p.position.y + 52), 15, UI.WHITE)
			var seat_y: float = (pick_rects()[Share.job_ids().size()][1] as Rect2).position.y
			UI.draw_text(self, Loc.t("Кабинет посадки (примерки):"), Vector2(x, seat_y - 26), 15, UI.WHITE, true)
			var fr := field_rect()
			UI.draw_text(self, Loc.t("От кого (можно не писать):"), Vector2(x, fr.get_center().y - 10), 15, UI.WHITE)
			var n: int = (ui.get("sel", []) as Array).size()
			var info: String = ui.get("err", "") if ui.get("err", "") != "" else (Loc.t("Выбрано: %d" % n) if n else "Ничего не выбрано")
			UI.draw_text(self, Loc.t(info), Vector2(fr.end.x + 24, fr.get_center().y - 10), 15,
				UI.BAD if ui.get("err", "") != "" else (UI.GOOD if n else UI.GREY), true)


func _fit(s: String, pos: Vector2, width: float, size_: int, col: Color, bold: bool = false) -> void:
	var f: Array = UI.fit_text(s, width, size_, bold)
	@warning_ignore("integer_division")
	UI.draw_text(self, f[0], Vector2(pos.x, pos.y + (size_ - int(f[1])) / 2), f[1], col, bold)


## Код крупно, группами по 6 знаков — чтобы переписать руками (_draw_code_block).
func _code_block(r: Rect2, text: String, size_: int = 17) -> void:
	var groups: Array = []
	for i in range(0, text.length(), 6):
		groups.append(text.substr(i, 6))
	var lines: Array = []
	var cur := ""
	for g: String in groups:
		var t := (cur + " " + g).strip_edges()
		if UI.text_width(t, size_, true) <= r.size.x and cur != "":
			cur = t
		elif cur == "":
			cur = g
		else:
			lines.append(cur)
			cur = g
	if cur != "":
		lines.append(cur)
	var y := r.position.y
	var lh := UI.line_height(size_, true)
	for ln: String in lines:
		if y + lh > r.end.y:
			break
		UI.draw_text(self, ln, Vector2(r.position.x, y), size_, UI.WHITE, true)
		y += lh + 3


@warning_ignore("integer_division")
func _result_rows(r: Rect2, res: Dictionary) -> void:
	var rows: Array = res["rows"]
	var per := maxi(1, int(r.size.y / 26))
	var cols := 1 if rows.size() <= per else 2
	var cw := int((r.size.x - 16 * (cols - 1)) / cols)
	for i in mini(rows.size(), per * cols):
		var row: Array = rows[i]
		var x := r.position.x + (i / per) * (cw + 16)
		var y := r.position.y + (i % per) * 26
		_fit(("✔ " if row[1] else "○ ") + Share.item_label(row[0]), Vector2(x, y), cw - (150 if cols == 1 else 96), 15,
			UI.GOOD if row[1] else UI.GREY)
		if row[1]:
			UI.draw_text(self, Loc.t("ошибок %d · %s" % [int(row[2]), Share.fmt_secs(row[3])]), Vector2(x + cw, y + 1),
				14 if cols == 1 else 13, UI.WHITE if int(row[2]) == 0 else UI.AMBER, false, 2)
		else:
			UI.draw_text(self, Loc.t("не сделано"), Vector2(x + cw, y + 1), 13, UI.DIM, false, 2)


func _draw_pick(b: GameButton, r: Rect2) -> void:
	var k: String = b.get_meta("k")
	var sel: Array = ui.get("sel", [])
	var on := k in sel
	UI.draw_text(b, ("%d." % (sel.find(k) + 1)) if on else "○", Vector2(r.position.x + 10, r.get_center().y - 9), 14,
		UI.GOOD if on else UI.DIM, true)
	var j := Content.job_by_id(k)
	if not j.is_empty():
		_fit_on(b, Loc.t(j["client"]), Vector2(r.position.x + 38, r.position.y + 3), r.size.x - 46, 14, UI.WHITE)
		_fit_on(b, Loc.t(j["title"]), Vector2(r.position.x + 38, r.position.y + 20), r.size.x - 46, 12, UI.GREY)
	else:
		_fit_on(b, Share.item_label(k), Vector2(r.position.x + 38, r.get_center().y - 9), r.size.x - 46, 14,
			UI.WHITE if on else UI.GREY)


static func _fit_on(ci: CanvasItem, s: String, pos: Vector2, width: float, size_: int, col: Color) -> void:
	var f: Array = UI.fit_text(s, width, size_)
	@warning_ignore("integer_division")
	UI.draw_text(ci, f[0], Vector2(pos.x, pos.y + (size_ - int(f[1])) / 2), f[1], col)


## Поле ввода окна (как в pygame: печать, Backspace, Ctrl+V — из буфера, Enter — «Применить»/«Показать код»).
## Свой узел, а не LineEdit: вставка идёт через Share.clip_get (в тестах — память, системный буфер не трогаем).
class ShareField extends Control:
	var dlg: ShareDialog
	var key: String = "text"
	var max_len: int = 8000
	var _t: float = 0.0

	func _init() -> void:
		focus_mode = Control.FOCUS_ALL
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_IBEAM

	func value() -> String:
		return str(dlg.ui.get(key, ""))

	func set_value(v: String) -> void:
		dlg.ui[key] = v.substr(0, max_len)
		dlg.ui["err"] = ""
		queue_redraw()
		dlg.queue_redraw()

	func _process(dt: float) -> void:
		_t += dt
		queue_redraw()

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed:
			grab_focus()
			accept_event()
			return
		if not (e is InputEventKey and e.pressed):
			return
		var k := e as InputEventKey
		if k.keycode == KEY_V and (k.ctrl_pressed or k.meta_pressed):
			set_value(value() + Share.clip_get().strip_edges())
		elif k.keycode == KEY_BACKSPACE:
			set_value(value().substr(0, maxi(0, value().length() - 1)))
		elif k.keycode == KEY_ENTER or k.keycode == KEY_KP_ENTER:
			dlg.action("apply" if key == "text" else "make")
		elif k.keycode == KEY_ESCAPE:
			return                              # Esc — окну (Nav)
		elif k.unicode >= 32 and not k.ctrl_pressed and not k.alt_pressed:
			var ch := char(k.unicode)
			if Share._printable(ch) and not ch in Share.ZW:
				set_value(value() + ch)
		else:
			return
		accept_event()

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		UI.draw_round_rect(self, r, Color8(12, 12, 18), UI.CYAN, 2, 8)
		var text := value()
		var ph := "" if OS.has_feature("web") else ("Ctrl+V — вставить" if key == "text" else "Имя учителя")
		var lh := UI.line_height(16)
		if text == "" and ph != "":
			UI.draw_text(self, Loc.t(ph), Vector2(10, r.get_center().y - floorf(lh / 2)), 16, UI.DIM)
		else:
			var s := text + ("|" if int(_t * 2) % 2 == 0 else " ")
			while s.length() > 1 and UI.text_width(s, 16) > r.size.x - 20:   # длинный код — видно конец
				s = s.substr(1)
			UI.draw_text(self, s, Vector2(10, r.get_center().y - floorf(lh / 2)), 16, UI.WHITE)
		if has_focus() and UI.kb_active:
			UI.draw_round_rect(self, r.grow(4), Color(0, 0, 0, 0), UI.WHITE, 2, 10)
