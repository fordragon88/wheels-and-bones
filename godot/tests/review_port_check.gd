extends Node
## Перенос правок game.py по внешней проверке 26.11 (коммит b67dc24: E29.3, E31.2, E35.3, E37.1–E37.3, проценты
## громкости) в Godot. Зовёт самопроверка (tests/selftest_runner.gd, и отдельно «-- --test --only review-port»).
## run(R) → строка для итога; ошибки — R.err().

var R: Node


func run(runner: Node) -> String:
	R = runner
	var done: PackedStringArray = []
	done.append(_instr_pc())
	done.append(await _vol_pct())
	done.append(await _alt_msg())
	done.append(await _dense_cap())
	done.append(await _seat_demo_focus())
	done.append(await _bak_bad())
	return "перенос game.py 26.11: " + ", ".join(done)


func _fail(msg: String) -> void:
	R.err("перенос game.py 26.11: " + msg)


# ---- E37.1: текст шага и теста на компьютере — fit_wrapped_size(…, 560, 19, INSTR_ROOM 124), как draw_job game.py ----
const COMBOS := [["ru", 0, false], ["ru", 1, false], ["ru", 2, false], ["ru", 3, false], ["en", 0, false],
	["en", 1, false], ["en", 2, false], ["en", 3, false], ["en", 0, true], ["en", 2, true], ["en", 3, true]]


func _set_text(lang: String, t: int, easy: bool) -> void:
	Settings.lang = lang
	Loc.code = lang
	Settings.a11y["text"] = t
	Settings.a11y["font"] = easy
	UI.clear_font_cache()


func _instr_pc() -> String:
	var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false), Settings.text_cap,
		UI._touch, UI._phone]
	Settings.text_cap = 0.0
	UI._touch = 0
	UI._phone = 0
	var JobScr: GDScript = load("res://screens/job.gd")
	var steps: Array = []
	var tests: Array = []
	for job: Dictionary in Content.jobs:
		for c: Dictionary in Content.cases(job):
			var cid := str(c["id"]) + ":" + str(c.get("_variant", "-"))
			for st: Dictionary in c.get("steps", []):
				steps.append([cid, str(st["instr"])])
			if str(c.get("test", "")) != "" and not tests.has([cid, str(c["test"])]):
				tests.append([cid, str(c["test"])])
	var room: float = JobScr.INSTR_ROOM_PC
	var over := 0
	var changed100 := 0
	var shrunk150 := 0
	var worst := ""
	for cb: Array in COMBOS:
		_set_text(cb[0], cb[1], cb[2])
		for kind in 2:
			for s: Array in (steps if kind == 0 else tests):
				var tx := Loc.t(s[1])
				var w: float = JobScr.instr_width() if kind == 0 else 560.0
				var sz: int = JobScr.instr_size(tx) if kind == 0 else JobScr.instr_size(tx, 560)
				var h: float = UI.wrap_lines(tx, w, sz).size() * (UI.line_height(sz) + 2) - 2
				if h > room + 0.01:
					over += 1
					worst = "%s %d%%%s %s: %d px > %d" % [cb[0], [100, 112, 125, 150][cb[1]], " easy" if cb[2] else "", s[0],
						int(ceilf(h)), int(room)]
				if cb[1] == 0 and sz != 19:
					changed100 += 1
				if cb[1] == 3 and sz < 19:
					shrunk150 += 1
	Settings.lang = keep[0]
	Loc.code = keep[1]
	Settings.a11y["text"] = keep[2]
	Settings.a11y["font"] = keep[3]
	Settings.text_cap = keep[4]
	UI._touch = keep[5]
	UI._phone = keep[6]
	UI.clear_font_cache()
	if over > 0:
		_fail("E37.1: текст шага/теста на компьютере заходит на коляску в %d случаях (например, %s)" % [over, worst])
	if changed100 > 0:
		_fail("E37.1: при 100 %% текст шага/теста мельче 19 в %d случаях (должен быть прежним)" % changed100)
	return "E37.1 текст шага на ПК над коляской (%d шагов, %d тестов × %d сочетаний; при 150 %% мельче — %d)" \
		% [steps.size(), tests.size(), COMBOS.size(), shrunk150]


# ---- проценты громкости — округлением (game.py round: 0,29 → 29 %) ----
func _vol_pct() -> String:
	var SD: GDScript = load("res://ui/settings_dialog.gd")
	for pair: Array in [[0.29, 29], [0.57, 57], [0.58, 58], [1.0, 100], [0.0, 0], [0.354, 35], [0.355, 36]]:
		if SD.vol_pct(pair[0]) != pair[1]:
			_fail("проценты громкости: %s → %d%% (game.py %d%%)" % [pair[0], SD.vol_pct(pair[0]), pair[1]])
	var v0: float = Settings.vol.get("master", 1.0)
	var tab0: String = SD.tab
	Settings.vol["master"] = 0.29
	SD.tab = "sound"
	Nav.open_settings()
	await R._frames(2)
	var sl := Nav.settings.find_child("Vol_master", true, false) as Control if Nav.settings != null else null
	if sl == null or not sl.accessibility_name.ends_with(": 29%"):
		_fail("проценты громкости: ползунок «Общая громкость» при 0,29 — «%s»" % (sl.accessibility_name if sl else "нет"))
	Nav.close_settings()
	await R._frames(2)
	Settings.vol["master"] = v0
	SD.tab = tab0
	return "проценты громкости округлением (0,29 → 29 %)"


# ---- E29.3: «Деталь верная, но инструмент не тот» и для alt-деталей; «Инструмент верный…» и для alt_tools ----
func _find_step(field: String) -> Array:
	for job: Dictionary in Content.jobs:
		for c: Dictionary in Content.cases(job):
			var sts: Array = c.get("steps", [])
			for i in sts.size():
				var st: Dictionary = sts[i]
				if not (st.get(field, []) as Array).is_empty() and str(st.get("wrongmsg", "")) == "" \
						and not st.get("mini") is Dictionary:
					return [job["id"], int(c.get("_variant", 0)), i, st, sts]
	return []


func _alt_msg() -> String:
	var code0 := Loc.code
	Loc.code = "ru"
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	var n := 0
	for field: String in ["alt", "alt_tools"]:
		var f := _find_step(field)
		if f.is_empty():
			_fail("E29.3: нет шага с %s без wrongmsg" % field)
			continue
		var st: Dictionary = f[3]
		var tools_ok: Array = [st["tool"]] + st.get("alt_tools", [])
		var parts_ok: Array = [st["part"]] + st.get("alt", [])
		var tid: String = st["tool"]
		var pid: String = st["part"]
		if field == "alt":                     # чужой инструмент на alt-деталь
			pid = st["alt"][0]
			for t: String in Content.tools:
				if not t in tools_ok:
					tid = t
					break
		else:                                  # alt-инструмент на чужую деталь (из других шагов того же задания)
			tid = st["alt_tools"][0]
			for s2: Dictionary in f[4]:
				if not s2["part"] in parts_ok:
					pid = s2["part"]
					break
		Nav.go("job", {"job": f[0], "variant": f[1]})
		await R._frames(2)
		var j: Node = Nav.current
		j.phase = "repair"
		j.step_idx = f[2]
		var res: String = j.do_action(tid, pid)
		var want := "Деталь верная, но инструмент не тот." if field == "alt" else "Инструмент верный, но не та деталь."
		var msg: String = str(j.dispute.get("msg", ""))
		if res != "wrong" or not msg.begins_with(want):
			_fail("E29.3: %s шаг %d, %s → %s (%s): «%s» (%s), ждали «%s…»" % [f[0], f[2], tid, pid, field, msg, res, want])
		n += 1
	Loc.code = code0
	Nav.go("hub")
	await R._frames(2)
	return "E29.3 подсказка «деталь/инструмент верные» и для alt (%d)" % n


# ---- E37.1: окно замечания и справка F1 — потолок текста 125 % (text_cap), с первого кадра окна ----
func _dense_cap() -> String:
	var t0: int = Settings.a11y.get("text", 0)
	Settings.a11y["text"] = 3
	UI.clear_font_cache()
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("hub")
	await R._frames(2)
	if Settings.text_cap != 0.0:
		_fail("E37.1: в мастерской без окон потолок текста %s" % Settings.text_cap)
	Nav.toggle_help()
	if Settings.text_cap != 1.25:
		_fail("E37.1: справка F1 открыта — потолок текста %s (game.py: text_cap 125 %%)" % Settings.text_cap)
	Nav.toggle_help()
	await R._frames(2)
	Nav.open_flag()
	if Settings.text_cap != 1.25:
		_fail("E37.1: окно замечания открыто — потолок текста %s (game.py: text_cap 125 %%)" % Settings.text_cap)
	await R._frames(2)
	if Nav.feedback != null:
		Nav.feedback.close()
	await R._frames(2)
	if Settings.text_cap != 0.0:
		_fail("E37.1: окно замечания закрыто — потолок текста остался %s" % Settings.text_cap)
	Settings.a11y["text"] = t0
	UI.clear_font_cache()
	return "E37.1 окно замечания и справка F1 — текст не крупнее 125 %"


# ---- E37.2: «ПОКАЗАТЬ НОРМУ» — только у урока с позой-ошибкой; E37.3: ползунок примерки в фокусе с нажатия ----
func _seat_demo_focus() -> String:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("seating")
	await R._frames(2)
	var s: Node = Nav.current
	s.set_tab("lessons")
	await R._frames(1)
	var with_err := 0
	for i in (s.lessons() as Array).size():
		s.pick_lesson(i)
		await R._frames(1)
		var lp: Dictionary = s._lpose()
		var err := false
		for k: String in ["p", "slide", "deep", "knee_up", "dangle", "front"]:
			err = err or lp.has(k)
		with_err += 1 if err else 0
		var tg: Node = s._dyn.get_node_or_null("Toggle")
		if (tg != null) != err:
			_fail("E37.2: урок %d — кнопка «ПОКАЗАТЬ НОРМУ» %s, поза-ошибка %s" % [i + 1, tg != null, err])
	s.set_tab("fit")
	await R._frames(2)
	var keys: Array = s.slider_keys()
	var sl: Control = s._dyn.get_node_or_null("Slider_" + str(keys[-1])) if not keys.is_empty() else null
	if sl == null:
		_fail("E37.3: нет ползунка примерки")
	else:
		var e := InputEventMouseButton.new()
		e.button_index = MOUSE_BUTTON_LEFT
		e.pressed = true
		e.position = sl.size / 2.0
		sl._gui_input(e)
		var focused: bool = sl.has_focus() and s.focus_key == str(keys[-1])
		var up := InputEventMouseButton.new()
		up.button_index = MOUSE_BUTTON_LEFT
		up.pressed = false
		up.position = e.position
		sl._gui_input(up)
		if not focused:
			_fail("E37.3: нажатие на ползунок «%s» не ставит фокус (фокус %s, focus_key «%s»)"
				% [keys[-1], sl.has_focus(), s.focus_key])
	Nav.go("hub")
	await R._frames(2)
	return "E37.2 «ПОКАЗАТЬ НОРМУ» только у %d уроков с позой-ошибкой, E37.3 фокус ползунка с нажатия" % with_err


# ---- E31.2: «Вернуть прежний прогресс» с битой копией — прогресс прежний, копия не стирается, честное сообщение ----
func _bak_bad() -> String:
	if Settings.store_has("save.bak.json"):      # у игрока есть своя копия — её не трогаем, проверка пропускается
		return "E31.2 пропущено (есть копия игрока)"
	var p0: bool = SaveGame.persist
	SaveGame.reset()
	SaveGame.done = {"flat": true}
	Settings.store_write("save.bak.json", "{\"done\": [\"cast")   # оборванная копия
	SaveGame.persist = true                      # путь хранилища (в --test обычно копия в памяти)
	var saved := SaveGame.has_backup()
	var ok := SaveGame.restore_backup() if saved else true
	SaveGame.persist = p0
	var left := Settings.store_has("save.bak.json")
	if not saved or ok or not left or not SaveGame.done.has("flat"):
		_fail("E31.2: битая копия — restore %s, копия осталась %s, прогресс %s" % [ok, left, SaveGame.done.keys()])
	var SD: GDScript = load("res://ui/settings_dialog.gd")
	var code0 := Loc.code
	Loc.code = "en"
	if Loc.t(SD.BAK_BAD_MSG) == SD.BAK_BAD_MSG:
		_fail("E31.2: нет перевода «%s»" % SD.BAK_BAD_MSG)
	Loc.code = code0
	Settings.store_remove("save.bak.json")
	SaveGame.reset()
	return "E31.2 битая копия прогресса не стирается, прогресс прежний"
