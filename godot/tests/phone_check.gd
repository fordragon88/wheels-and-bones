extends Node
## Телефонный режим (UI.phone(), 21.11): замер целей для пальца. Состояния — те же, что у сверки порядка обхода
## (content/kb_order_ref.json, ставит tests/shots.gd stage()). Цели — видимые включённые кнопки активного окна
## (A11y.active_root: окно поверх экрана или сам экран; у окон внутри экрана — ещё значки шапки), ползунки и
## кружки деталей (зона попадания пальца r + 16). Для каждой — меньшая сторона; итог «целей мельче 56: N;
## пересечений: M; зазор < 8: K». Исключения (осознанно мельче 56 или вплотную) — EXCEPT с причиной.
##   … -s res://tests/selftest.gd -- --test --only phone-measure [--phone 0|1] [--langs ru,en]  → tests/out/phone_targets_<0|1>.txt
##   … --only phone-ref — записать tests/phone_off_ref.json (размеры при выключенном режиме, эталон «как было»)
##   в полной самопроверке — run(): телефон на ключевых экранах (мельче 56 и пересечений — 0), выключен — как эталон.

var R: Node
var _stager: Node

## Осознанно мельче 56 / вплотную: «имя цели» (или «состояние:имя»; * в конце — начало имени) → причина.
const EXCEPT := {
	"Slider_*": "Кабинет посадки, примерка с 4–5 ползунками: строки ползунков и «ГОТОВО» 52 через 60 (с 56 через 64 предупреждения при 100 % мельче на 3 ступени; разрешено владельцем 21.11)",
	"Check": "Кабинет посадки, примерка с 4–5 ползунками: строки ползунков и «ГОТОВО» 52 через 60 (с 56 через 64 предупреждения при 100 % мельче на 3 ступени; разрешено владельцем 21.11)",
	"Case_*": "решение владельца 21.11: кнопки клиентов меньше (Кабинет посадки, примерка: 153×48 через 56, зазор 8; освободившиеся 24 px — предупреждениям)",
}

## Ключевые экраны самопроверки (телефон): то, что перестроено.
const KEY_STATES := ["title", "intro_1", "ending", "credits", "guild_open", "guild_diploma", "tech_ops", "tech_manual",
	"tech_spec", "tech_failed", "tech_ops_t_battery", "tech_ops_t_battery_q6", "tech_ops_t_pulse6",
	"tech_ops_t_q6brake",
	"seat_lessons", "seat_lesson_slump", "seat_lesson_measure", "seat_lesson_front", "seat_fit_troll", "seat_fit_golem",
	"seat_fit_dryad", "seat_fit_dryad_side", "seat_fit_owl", "seat_fit_orc", "seat_quiz_q1", "seat_quiz_wrong", "seat_quiz_pass", "scan_seat",
	"exam_ticket", "hub", "job_flat_diagnose", "job_flat_inspected", "job_joystick_inspected", "job_flat_repair",
	"result_lift", "garage", "garage_open", "mini_pump", "mini_gap", "mini_ping", "mini_meter", "settings_sound", "settings_graphics", "settings_access", "settings_game",
	"feedback_general", "feedback_dispute", "share_paste", "share_confirm", "hub_assign", "share_summary", "share_builder"]


func _ensure_stager() -> void:
	if _stager == null:
		_stager = (load("res://tests/shots.gd") as GDScript).new()
		_stager.set("stage_only", true)
		add_child(_stager)


static func _label(c: Control, root: Node) -> String:
	var n := str(c.name)
	if n.begins_with("@") or n == "":
		var p := str(c.get_parent().name) if c.get_parent() else "?"
		n = "%s/%s" % [p, c.accessibility_name.left(24)]
	return n


## Цели для пальца сейчас: [{name, rect, kind}] (rect — зона попадания в px холста).
static func targets() -> Array:
	var out: Array = []
	var root: Node = A11y.active_root()
	if Nav.help != null:
		root = Nav.help
	if root == null:
		return out
	var scr: Node = Nav.current
	if root == scr and scr != null and scr.get("open_idx") is int and int(scr.get("open_idx")) >= 0 			and scr.get("_popup") is Control:           # гараж: открытая карточка закрывает экран (любой тап — закрыть)
		root = scr.get("_popup")
	var roots: Array = [root]
	if root != scr and scr != null and (root as Node).get_parent() != null and scr.is_ancestor_of(root):
		for c: Node in scr.get_children():          # окно внутри экрана (мини-игра, спека…): значки шапки нажимаются
			if c is IconButton:
				roots.append(c)
	var seen := {}
	for r0: Node in roots:
		var nodes: Array = [r0] + r0.find_children("*", "Control", true, false)
		for n: Node in nodes:
			var c := n as Control
			if c == null or seen.has(c) or not c.is_visible_in_tree() or c.mouse_filter == Control.MOUSE_FILTER_IGNORE:
				continue
			var kind := ""
			var rect := c.get_global_rect()
			if c is HotspotButton:
				var hb := c as HotspotButton
				kind = "spot"
				var rr: float = hb.r + (UI.TOUCH_SPOT_PAD if UI.touch() else 4)
				rect = Rect2(rect.get_center() - Vector2(rr, rr), Vector2(rr, rr) * 2.0)
			elif c is BaseButton:
				if (c as BaseButton).disabled:
					continue
				kind = "circle" if c is GameButton and (c as GameButton).hit_circle else "btn"
			elif A11y.is_slider(c) or str(c.name).begins_with("Slider_"):
				kind = "slider"
			elif c.has_meta("phone_target"):              # своя зона попадания (спицы, шкала…): Rect2 холста
				kind = "zone"
				var z: Variant = c.get_meta("phone_target")
				if z is Rect2:
					rect = z
			else:
				continue
			seen[c] = true
			out.append({"name": _label(c, root), "rect": rect, "kind": kind})
			if c.has_meta("phone_zones"):                 # несколько зон в одном узле (спицы мини-игры)
				for zr: Rect2 in c.get_meta("phone_zones"):
					out.append({"name": _label(c, root) + "#z", "rect": zr, "kind": "zone"})
	return out


static func _except(state: String, name: String) -> String:
	for k: String in EXCEPT:
		var key := k
		var st := ""
		if ":" in k:
			st = k.get_slice(":", 0)
			key = k.get_slice(":", 1)
		if st != "" and st != state:
			continue
		if key.ends_with("*") and name.begins_with(key.trim_suffix("*")) or key == name:
			return EXCEPT[k]
	return ""


## Разбор: мелкие, пересечения, зазор < 8 (кружки деталей между собой не считаются: палец — к ближайшему).
static func analyze(state: String, ts: Array) -> Dictionary:
	var small: Array = []
	var small_ex: Array = []
	var over: Array = []
	var close: Array = []
	for t: Dictionary in ts:
		var r: Rect2 = t["rect"]
		if minf(r.size.x, r.size.y) < UI.PHONE_MIN - 0.01:
			var why := _except(state, t["name"])
			(small_ex if why != "" else small).append(t)
	for i in ts.size():
		for j in range(i + 1, ts.size()):
			var a: Dictionary = ts[i]
			var b: Dictionary = ts[j]
			if a["kind"] == "spot" and b["kind"] == "spot":
				continue
			var ra: Rect2 = a["rect"]
			var rb: Rect2 = b["rect"]
			if a["kind"] == "circle" and b["kind"] == "circle":      # круглые зоны: по расстоянию центров
				var dc := ra.get_center().distance_to(rb.get_center())
				var rs := (minf(ra.size.x, ra.size.y) + minf(rb.size.x, rb.size.y)) / 2.0
				if dc < rs - 0.01:
					over.append([a["name"], b["name"]])
				elif dc < rs + UI.PHONE_GAP - 0.01:
					close.append([a["name"], b["name"]])
				continue
			var ex := _except(state, a["name"] + "&" + b["name"]) != "" or _except(state, b["name"] + "&" + a["name"]) != ""
			if ex:
				continue
			if ra.intersection(rb).has_area():
				over.append([a["name"], b["name"]])
			elif ra.grow(UI.PHONE_GAP / 2.0 - 0.01).intersection(rb.grow(UI.PHONE_GAP / 2.0 - 0.01)).has_area():
				close.append([a["name"], b["name"]])
	return {"small": small, "small_ex": small_ex, "over": over, "close": close}


static func _fmt_r(r: Rect2) -> String:
	return "%d,%d %d×%d" % [roundi(r.position.x), roundi(r.position.y), roundi(r.size.x), roundi(r.size.y)]


## Замер по состояниям: строки отчёта и итог.
func measure(runner: Node, states: Array, langs: Array, on: bool) -> Dictionary:
	R = runner
	_ensure_stager()
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1 if on else t0
	UI.set_phone(on)
	var lang0 := Loc.code
	var voices0: bool = Settings.a11y.get("voices", true)
	Settings.a11y["voices"] = false
	seed(1)
	Figure.idle_t = 1.6
	Engine.time_scale = 25.0
	if Share.dlg != null:                          # окна от прошлого замера — закрыть (эталон снят с чистого старта)
		Share._close_dlg()
	if Nav.settings != null:
		Nav.close_settings()
	if Nav.feedback != null:
		Nav.feedback.close()
	if Nav.help != null:
		Nav.toggle_help()
	await R._frames(2)
	var lines: PackedStringArray = []
	var per: Dictionary = {}
	var tot := {"n": 0, "small": 0, "small_ex": 0, "over": 0, "close": 0}
	var rects: Dictionary = {}
	for lang: String in langs:
		SaveGame.reset()
		for name: String in states:
			if lang == "ru" and name == "title_en":
				continue
			SaveGame.tutorial_skipped = true
			Settings.lang = lang
			Loc.code = lang
			var sname: String = "title_en" if lang == "en" and name == "title" else name
			await _stager.stage(sname)
			Settings.lang = lang
			Loc.code = lang
			await R._frames(2)
			var ts := targets()
			var an := analyze(name, ts)
			var key := "%s %s" % [lang, name]
			per[key] = {"n": ts.size(), "small": an["small"].size(), "small_ex": an["small_ex"].size(),
				"over": an["over"].size(), "close": an["close"].size()}
			for k: String in ["small", "small_ex", "over", "close"]:
				tot[k] += per[key][k]
			tot["n"] += ts.size()
			var rr: Array = []
			for t: Dictionary in ts:
				var r: Rect2 = t["rect"]
				rr.append([t["name"], roundi(r.position.x), roundi(r.position.y), roundi(r.size.x), roundi(r.size.y)])
			rects[key] = rr
			lines.append("== %s: целей %d, мельче 56: %d (+исключений %d), пересечений %d, зазор < 8: %d" % [key, ts.size(),
				an["small"].size(), an["small_ex"].size(), an["over"].size(), an["close"].size()])
			for t: Dictionary in ts:
				var r: Rect2 = t["rect"]
				var m := minf(r.size.x, r.size.y)
				var mark := "  "
				if m < UI.PHONE_MIN - 0.01:
					mark = "e " if _except(name, t["name"]) != "" else "! "
				lines.append("%s%-6s %-34s %-18s min %d" % [mark, t["kind"], str(t["name"]).left(34), _fmt_r(r), roundi(m)])
			for o: Array in an["over"]:
				lines.append("  X пересечение: %s ↔ %s" % o)
			for o: Array in an["close"]:
				lines.append("  ~ зазор < 8: %s ↔ %s" % o)
			_stager.unstage(sname)
	Engine.time_scale = 1.0
	Loc.code = lang0
	Settings.lang = lang0
	Settings.a11y["voices"] = voices0
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	return {"lines": lines, "per": per, "tot": tot, "rects": rects}


static func summary(on: bool, d: Dictionary) -> String:
	var t: Dictionary = d["tot"]
	return "PHONE TARGETS (%s): состояний %d, целей %d, мельче 56: %d (исключений %d), пересечений: %d, зазор < 8: %d" % [
		"телефон" if on else "выкл", d["per"].size(), t["n"], t["small"], t["small_ex"], t["over"], t["close"]]


static func write_out(fname: String, text: String) -> void:
	var out := ProjectSettings.globalize_path("res://tests/out")
	DirAccess.make_dir_recursive_absolute(out)
	var f := FileAccess.open(out.path_join(fname), FileAccess.WRITE)
	f.store_string(text)
	f.close()


## Самопроверка: телефон на ключевых экранах — мельче 56 (кроме исключений) и пересечений нет; выключен — размеры
## и места целей как в эталоне tests/phone_off_ref.json (записан до телефонной раскладки).
func run(runner: Node) -> String:
	R = runner
	var on := await measure(runner, KEY_STATES, ["ru"], true)
	write_out("phone_targets_1.txt", "\n".join(on["lines"]) + "\n")
	for key: String in on["per"]:
		var p: Dictionary = on["per"][key]
		if p["small"] > 0 or p["over"] > 0:
			R.err("телефон %s: мельче 56 — %d, пересечений — %d (tests/out/phone_targets_1.txt)" % [key, p["small"], p["over"]])
	var ref_path := "res://tests/phone_off_ref.json"
	var n_off := 0
	var n_diff := 0
	if not FileAccess.file_exists(ref_path):
		R.err("нет tests/phone_off_ref.json (… --only phone-ref)")
	else:
		var ref: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ref_path))
		var states: Array = []
		for key: String in ref:
			if key.begins_with("ru "):
				states.append(key.substr(3))
		var off := await measure(runner, states, ["ru"], false)
		for key: String in ref:
			if not off["rects"].has(key):
				continue
			n_off += 1
			if _norm(off["rects"][key]) != _norm(ref[key]):
				n_diff += 1
				R.err("телефон выключен, %s: цели не как были\n  было  %s\n  стало %s" % [key, JSON.stringify(ref[key]),
					JSON.stringify(off["rects"][key])])
	return summary(true, on) + "; выключен: %d состояний как эталон (расхождений %d)" % [n_off, n_diff]


## Кегли текста Кабинета посадки (seating.gd text_sizes): каждый урок, клиент, вопрос — при RU/EN, 100/112/125/150 %,
## обычный и «лёгкий» шрифт; у примерки — и подписи кнопок клиентов («cases»: портрет/кегль, 0 — без портрета).
## Ключ «ru 150 lesson 3» → {lesson|warn|q|say|cases: кегль}.
##   … --only seat-sizes [--phone 0|1]  → tests/out/seat_sizes_<0|1>.json
func seat_sizes(runner: Node, on: bool) -> Dictionary:
	R = runner
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1 if on else t0
	UI._phone = 1 if on else 0                    # не set_phone: при _phone = −1 (не определён) set_phone(false) ничего
	Settings.changed.emit("phone")                # не ставил, и без окна телефон определялся сам (21.11)
	var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false)]
	var instant0: bool = Settings.a11y.get("instant", false)
	Settings.a11y["instant"] = true
	var out := {}
	for lang: String in ["ru", "en"]:
		for t: int in [0, 1, 2, 3]:
			for easy: bool in [false, true]:
				Settings.lang = lang
				Loc.code = lang
				Settings.a11y["text"] = t
				Settings.a11y["font"] = easy
				UI.clear_font_cache()
				SaveGame.reset()
				SaveGame.done["flat"] = true
				Nav.go("seating")
				await R._frames(3)
				var scr: Node = Nav.current
				scr.quiz = Content.seating["quiz"].duplicate(true)
				var pre := "%s %d%s" % [lang, [100, 112, 125, 150][t], " easy" if easy else ""]
				for i in scr.lessons().size():
					scr.pick_lesson(i)
					await R._frames(2)
					if not on:                                # компьютер: значки в списке (без окна _draw кнопок нет)
						scr.desk_icon("lessons")
					out["%s lesson %d" % [pre, i + 1]] = scr.text_sizes.duplicate()
				scr.set_tab("fit")
				for i in scr.cases().size():
					scr.pick_case(i)
					await R._frames(2)
					if not on:
						scr.desk_icon("fit")
					out["%s fit %d" % [pre, i + 1]] = scr.text_sizes.duplicate()
				for c: Dictionary in scr.cases():             # все клиенты пройдены — подписи «✔ Имя» (длиннее)
					SaveGame.seat_done[c["id"]] = true
				scr.refresh()
				await R._frames(2)
				if not on:
					scr.desk_icon("fit")
				out["%s fit done" % pre] = scr.text_sizes.duplicate()
				SaveGame.seat_done.clear()
				scr.set_tab("quiz")
				for i in scr.quiz.size():
					scr.quiz_i = i
					scr.refresh()
					await R._frames(2)
					out["%s quiz %d" % [pre, i + 1]] = scr.text_sizes.duplicate()
	Settings.lang = keep[0]
	Loc.code = keep[1]
	Settings.a11y["text"] = keep[2]
	Settings.a11y["font"] = keep[3]
	Settings.a11y["instant"] = instant0
	UI.clear_font_cache()
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	return out


## Телефон, про-задания 13–16 шагов (3 столбца): кегли карточек шагов (наименьший/наибольший, строк до), пузырь и
## коляска в левой колонке — при RU/EN, 100/112/125/150 %, обычный и «лёгкий» шрифт.
##   … --only tech-sizes  → tests/out/tech_sizes_1.json; ключ «ru 150 easy t_battery» → {fs_min, fs_max, lines_max, …}
func tech_sizes(runner: Node) -> Dictionary:
	R = runner
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1
	UI.set_phone(true)
	var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false)]
	var instant0: bool = Settings.a11y.get("instant", false)
	Settings.a11y["instant"] = true
	var out := {}
	for lang: String in ["ru", "en"]:
		for t: int in [0, 1, 2, 3]:
			for easy: bool in [false, true]:
				Settings.lang = lang
				Loc.code = lang
				Settings.a11y["text"] = t
				Settings.a11y["font"] = easy
				UI.clear_font_cache()
				for jid: String in ["t_battery", "t_battery_q6", "t_pulse6", "t_q6brake"]:
					Nav.go("tech", {"job": jid})
					await R._frames(3)
					var scr: Node = Nav.current
					var fss: Array = scr.op_fs.values().map(func(v: Array) -> int: return v[0])
					var lns: Array = scr.op_fs.values().map(func(v: Array) -> int: return v[1])
					var mb: SpeechBubble = scr.get_node("MentorBubble")
					out["%s %d%s %s" % [lang, [100, 112, 125, 150][t], " easy" if easy else "", jid]] = {
						"steps": scr.step_order.size(), "fs_min": fss.min(), "fs_max": fss.max(), "lines_max": lns.max(),
						"op0": str(scr.op_rect(0)), "bubble": str(Rect2(mb.side.position, Vector2(mb.side.size.x,
						mb.side_height()))), "bubble_fs": mb.side_layout()[1], "chair": str(scr.chair.get_rect())}
	Settings.lang = keep[0]
	Loc.code = keep[1]
	Settings.a11y["text"] = keep[2]
	Settings.a11y["font"] = keep[3]
	Settings.a11y["instant"] = instant0
	UI.clear_font_cache()
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	return out


## Строки целей с числами целыми (JSON читает их как float).
static func _norm(rows: Array) -> String:
	var out: PackedStringArray = []
	for r: Array in rows:
		out.append("%s %d %d %d %d" % [r[0], int(r[1]), int(r[2]), int(r[3]), int(r[4])])
	return "|".join(out)
