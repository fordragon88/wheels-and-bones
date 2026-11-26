extends Node
## Проверки внешнего обзора 26.11 (группа «браузер, сохранения, телефон, раскладка»; разборы
## tools/external_review/verify/V1_E1-E14.md, V2_E15-E29.md): каждая падала до починки. Зовёт самопроверка
## (tests/selftest_runner.gd, и отдельно «-- --test --only review-web»). run(R) → строка для итога; ошибки — R.err().
## Браузерные части (страница, localStorage, телефон в Chromium) — web_smoke: netfail «листаем коляски», tabs,
## store «место кончилось», loader «движок 404», feedback «телефон».

var R: Node


func run(runner: Node) -> String:
	R = runner
	var done: PackedStringArray = []
	_net_release()
	done.append("E4 места загрузки освобождаются при смене коляски")
	_merge_gen()
	done.append("E1 две вкладки: пункт и новая ссылка задания, пересданный экзамен после сброса")
	_restore_prev()
	done.append("S2 битое сохранение — из прежней копии")
	await _feedback_web_text()
	done.append("E6 поле страницы для комментария на телефоне")
	var im: Dictionary = instr_measure()
	var bad: Array = []
	for k: String in im:
		if int(im[k]["phone_after"]) > 0 or int(im[k]["phone_shrunk"]) > int(im[k]["phone_before"]):
			bad.append("%s: %s" % [k, im[k]])
	if not bad.is_empty():
		_fail("E22: инструкция ремонта на телефоне заходит на коляску (или мельче 19 там, где помещалась): " + "; ".join(bad))
	done.append("E22 инструкция ремонта на телефоне не заходит на коляску (%d сочетаний × %d шагов)"
		% [im.size(), int(im.values()[0]["steps"])])
	await _barty_col()
	done.append("E22 пузырь Барти у aeroz_lock на телефоне — без портрета, в своей колонке")
	await _spoke_corner()
	done.append("E17 угол квадрата спицы на телефоне — в спицу")
	await _job_windows()
	done.append("E24 окно сносок на телефоне и смена языка при открытых окнах задания")
	done.append(_phone_texts())
	await _calm_ride()
	done.append("E14 «Без анимации» после и во время проезда")
	_audio()
	done.append("E16 фоновая петля гаснет от своей громкости, пауза музыки не дёргается")
	await _guild_fx()
	done.append("E28.1 инструмент у курсора в Гильдии, E28.4 частицы фона гаснут по «Свечению»")
	await _misc29()
	done.append("E29.5 страница «⚠» у следующего клиента, E29.8 шаг назад и поворот коляски")
	return "обзор 26.11: " + ", ".join(done)


func _fail(msg: String) -> void:
	R.err("обзор 26.11: " + msg)


# ---- E4: Frames.release() не освобождал _net_inflight — после ~4 уходов с подгружающейся коляски кадры вставали ----
func _net_release() -> void:
	var arts: Array = Frames.tt_index.keys()
	if arts.size() < 2:
		_fail("E4: нет индексов поворота")
		return
	var net0: bool = Frames.net
	Frames.wait_tasks()                      # прошлые проверки могли оставить коляску в памяти — начинаем с чистого
	for key: String in Frames.loaded_keys():
		if key.begins_with("tt:"):
			Frames.release(key)
	Frames.net = true                        # браузерная «бухгалтерия» без страницы (JavaScriptBridge без окна — пусто)
	for k in 6:                              # листаем коляски во время загрузки ×6
		var art: String = arts[k % 2]
		Frames.want_turntable(art)
		Frames._pump_net()
		var mine := 0
		for u: String in Frames._net_inflight:
			if u.contains("turntable/%s_" % art.get_basename()):
				mine += 1
		if mine != Frames.NET_INFLIGHT:
			_fail("E4: листание №%d — у коляски %s в загрузке %d из %d (места заняты выгруженной коляской: %d)"
				% [k + 1, art, mine, Frames.NET_INFLIGHT, Frames._net_inflight.size() - mine])
			break
	Frames.release("tt:" + str(arts[1]))         # последняя открытая — ушли с неё во время загрузки
	for u: String in Frames._net_inflight:
		var q: Array = Frames._net_inflight[u]
		if not Frames._sets.has(q[0]):
			_fail("E4: после release в _net_inflight остался адрес выгруженного набора %s" % u)
			break
	Frames.wait_tasks()
	for key: String in Frames.loaded_keys():
		if key.begins_with("tt:"):
			Frames.release(key)
	Frames.net = net0


# ---- E1: две вкладки, сброс/код в одной (gen + 1) — первое действие другой вкладки не терялось бы ----
func _merge_gen() -> void:
	var M := SaveGame
	var asg := {"id": "a1", "from": "T", "title": "", "seat": [], "jobs": ["flat", "caster"], "done": {"flat": 1},
		"errors": {"flat": 2}, "secs": {"flat": 30}, "active": true, "sent": false}
	var base := {"done": ["flat"], "garage": [["flat", 3]], "exam_passed": true, "seat_done": [], "seat_quiz_ok": true,
		"tutorial_skipped": true, "ending_seen": false, "gen": 0, "assign": asg.duplicate(true)}
	# вкладка 1: «Сбросить прогресс» (задание остаётся), gen 1
	var stored := {"done": [], "garage": [], "exam_passed": false, "seat_done": [], "seat_quiz_ok": false,
		"tutorial_skipped": false, "ending_seen": false, "gen": 1, "assign": asg.duplicate(true)}
	# A: вкладка 2 прошла пункт caster задания
	var mine := base.duplicate(true)
	mine["assign"]["done"]["caster"] = 1
	mine["assign"]["errors"]["caster"] = 0
	mine["assign"]["secs"]["caster"] = 40
	mine["assign"]["errors"]["flat"] = 9                  # старый пункт — не своё новое: остаётся хранимое
	var out: Dictionary = M.merge_saves(stored, mine, base)
	var a: Dictionary = out.get("assign", {})
	if not (a.get("done", {}) as Dictionary).has("caster") or int(a.get("secs", {}).get("caster", -1)) != 40 \
			or int(a.get("errors", {}).get("flat", -1)) != 2 or int(out["gen"]) != 1 or out["done"] != []:
		_fail("E1: пункт задания, сделанный во второй вкладке после сброса в первой, потерян: %s" % [out])
	# A3: вкладка 2 вышла из задания после прошлой записи — «active» своё
	var mx := base.duplicate(true)
	mx["assign"]["active"] = false
	out = M.merge_saves(stored, mx, base)
	if bool(out["assign"].get("active", true)):
		_fail("E1: выход из задания во второй вкладке потерян после сброса в первой")
	# A4: ничего своего — задание хранимое как есть
	out = M.merge_saves(stored, base.duplicate(true), base)
	if out["assign"] != stored["assign"]:
		_fail("E1: без своих изменений задание не хранимое: %s" % [out["assign"]])
	# B: вкладка 2 пересдала экзамен и зачёт (флаги и так стояли в её памяти) — mark_flag → «своё новое»
	var mb := base.duplicate(true)
	out = M.merge_saves(stored, mb, base, {"flag:exam_passed": 1, "flag:seat_quiz_ok": 1})
	if not out["exam_passed"] or not out["seat_quiz_ok"] or out["done"] != []:
		_fail("E1: пересданный во второй вкладке экзамен/зачёт после сброса в первой потерян: exam %s, зачёт %s, done %s"
			% [out["exam_passed"], out["seat_quiz_ok"], out["done"]])
	SaveGame.reset()
	SaveGame._fresh.clear()
	SaveGame.mark_flag("exam_passed")
	if not SaveGame.exam_passed or not SaveGame._fresh.has("flag:exam_passed"):
		_fail("E1: mark_flag не ставит флаг/«своё новое»")
	SaveGame._fresh.clear()
	SaveGame.reset()
	# A5: «что вкладка записала» (_base) — копия, а не те же словари задания: пункт, отмеченный после записи, — новый
	SaveGame.assign = {"id": "a1", "from": "T", "title": "", "seat": [], "jobs": ["flat", "caster"], "done": {},
		"errors": {}, "secs": {}, "active": true, "sent": false}
	SaveGame._snapshot_base()
	SaveGame.assign["done"]["caster"] = 1
	if (SaveGame._base["assign"]["done"] as Dictionary).has("caster"):
		_fail("E1: base вкладки делит словари задания с памятью — новый пункт «уже был записан»")
	SaveGame.assign = {}
	SaveGame._base = {}
	# C: вкладка 2 открыла ссылку с новым заданием — берётся её задание
	var mc := base.duplicate(true)
	mc["assign"] = {"id": "b2", "from": "U", "title": "", "seat": [], "jobs": ["brake"], "done": {}, "errors": {},
		"secs": {}, "active": true, "sent": false}
	out = M.merge_saves(stored, mc, base)
	if str(out.get("assign", {}).get("id", "")) != "b2":
		_fail("E1: новая ссылка-задание во второй вкладке после сброса в первой не применилась (id %s)"
			% out.get("assign", {}).get("id", ""))
	# C2: у вкладки 2 задания не было вовсе (base без assign), она открыла ссылку — тоже её
	var b0 := base.duplicate(true)
	b0.erase("assign")
	out = M.merge_saves(stored, mc, b0)
	if str(out.get("assign", {}).get("id", "")) != "b2":
		_fail("E1: первая ссылка-задание во второй вкладке после сброса в первой не применилась")


# ---- S2: битый save.json — прогресс из save.prev.json и сообщение; копии нет / битая — как раньше ----
func _restore_prev() -> void:
	var dir := OS.get_temp_dir().path_join("wnb_review_s2_%d" % OS.get_process_id())
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join("save.json")
	var prev := dir.path_join("save.prev.json")
	var put := func(p: String, t: String) -> void:
		var f := FileAccess.open(p, FileAccess.WRITE)
		f.store_string(t)
		f.close()
	SaveGame.reset()
	SaveGame.restored_prev = false
	put.call(path, "{\"done\": [\"flat\", \"cast")         # оборвано посреди записи
	put.call(prev, JSON.stringify({"done": ["flat", "caster"], "garage": [["flat", 3], ["caster", 2]],
		"tutorial_skipped": true}))
	SaveGame.load_file(path)
	if not SaveGame.restored_prev or not SaveGame.done.has("caster") or not FileAccess.file_exists(path + ".bad"):
		_fail("S2: битый save.json не восстановлен из save.prev.json (restored %s, done %s)"
			% [SaveGame.restored_prev, SaveGame.done.keys()])
	var code0 := Loc.code
	Loc.code = "en"
	var en := Loc.t(SaveGame.RESTORED_MSG)
	Loc.code = code0
	if en != "The save file was damaged — restored from the previous copy.":
		_fail("S2: английский текст сообщения «%s»" % en)
	# копия тоже битая — пустой прогресс, без сообщения
	SaveGame.reset()
	SaveGame.restored_prev = false
	put.call(prev, "{oops")
	SaveGame.load_file(path)
	if SaveGame.restored_prev or not SaveGame.done.is_empty():
		_fail("S2: битая копия save.prev.json принята (done %s)" % [SaveGame.done.keys()])
	for f: String in ["save.json", "save.json.bad", "save.prev.json"]:
		DirAccess.remove_absolute(dir.path_join(f))
	DirAccess.remove_absolute(dir)
	SaveGame.restored_prev = false
	SaveGame.reset()


# ---- E6: окно замечания в браузере на сенсорном экране — поле страницы (wnbText) вместо поля Godot ----
# Без браузера JavaScriptBridge ничего не делает: проверяется, когда поле страницы показано/спрятано и как текст из
# него попадает в замечание (_wt_force — путь браузера с касаниями). Само поле страницы — web_smoke feedback (телефон).
func _feedback_web_text() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("hub")
	await R._frames(2)
	FeedbackDialog._wt_force = true
	Nav.open_flag()
	await R._frames(2)
	var f: FeedbackDialog = Nav.feedback
	if f == null or not f._wt_shown:
		_fail("E6: окно замечания на сенсорном экране не показало поле страницы")
	else:
		f.set_web_text("Колесо скрипит,
тормоз​ слабый")
		if f.text.text != "Колесо скрипит, тормоз слабый":
			_fail("E6: текст из поля страницы в замечание: «%s»" % f.text.text)
		Nav.toggle_help()
		await R._frames(2)
		if f._wt_shown:
			_fail("E6: справка поверх окна — поле страницы не спрятано")
		Nav.toggle_help()
		await R._frames(2)
		if not f._wt_shown:
			_fail("E6: справку закрыли — поле страницы не вернулось")
		Nav.open_settings()
		await R._frames(2)
		if f._wt_shown:
			_fail("E6: настройки поверх окна — поле страницы не спрятано")
		Nav.close_settings()
		await R._frames(2)
		var e: Dictionary = f.entry()
		if e["comment"] != "Колесо скрипит, тормоз слабый":
			_fail("E6: комментарий в замечании «%s»" % e["comment"])
		f.close()
		await R._frames(2)
	FeedbackDialog._wt_force = false
	Nav.go("hub")
	await R._frames(1)


# ---- E22: инструкция ремонта (job.gd instr_size) по всем шагам всех заданий и вариантов ----
const COMBOS := [["ru", 0, false], ["ru", 2, false], ["ru", 3, false], ["en", 0, false], ["en", 2, false],
	["en", 3, false], ["en", 0, true], ["en", 2, true], ["en", 3, true]]


func _set_text(lang: String, t: int, easy: bool) -> void:
	Settings.lang = lang
	Loc.code = lang
	Settings.a11y["text"] = t
	Settings.a11y["font"] = easy
	UI.clear_font_cache()


## Сколько шагов заходит на коляску (верх 226): было (кегль 19) → стало (job.gd instr_size), телефон и компьютер.
## Отдельно — «-- --test --only instr-sizes» (→ tests/out/instr_sizes.json).
func instr_measure() -> Dictionary:
	var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false), Settings.text_cap,
		UI._touch, UI._phone]
	Settings.text_cap = 0.0
	var steps: Array = []
	for job: Dictionary in Content.jobs:
		for c: Dictionary in Content.cases(job):
			for st: Dictionary in c.get("steps", []):
				steps.append([str(c["id"]) + ":" + str(c.get("_variant", "-")), str(st["instr"])])
	var out := {}
	var JobScr: GDScript = load("res://screens/job.gd")
	for cb: Array in COMBOS:
		_set_text(cb[0], cb[1], cb[2])
		var row := {"steps": steps.size()}
		for ph: bool in [true, false]:
			UI._touch = 1 if ph else 0
			UI._phone = 1 if ph else 0
			var w: float = JobScr.instr_width()
			var n0 := 0
			var n1 := 0
			var worst0 := 0.0
			var worst1 := 0.0
			var wid := ""
			var min_sz := 19
			var shrunk := 0
			for s: Array in steps:
				var tx := Loc.t(s[1])
				for pass_i in 2:
					var sz: int = 19 if pass_i == 0 else JobScr.instr_size(tx)
					var end_y: float = JobScr.INSTR_Y + UI.wrap_lines(tx, w, sz).size() * (UI.line_height(sz) + 2) - 2
					if pass_i == 1:
						min_sz = mini(min_sz, sz)
						shrunk += 1 if sz < 19 else 0
					if end_y > 226.0:
						if pass_i == 0:
							n0 += 1
							if end_y - 226.0 > worst0:
								worst0 = end_y - 226.0
								wid = s[0]
						else:
							n1 += 1
							worst1 = maxf(worst1, end_y - 226.0)
			var tag := "phone" if ph else "pc"
			row[tag + "_before"] = n0
			row[tag + "_after"] = n1
			row[tag + "_worst_before"] = "+%d px (%s)" % [int(ceilf(worst0)), wid] if n0 > 0 else ""
			row[tag + "_worst_after"] = int(ceilf(worst1))
			if ph:
				row["min_size"] = min_sz
				row["phone_shrunk"] = shrunk
		out["%s %d%s" % [cb[0], [100, 112, 125, 150][cb[1]], " easy" if cb[2] else ""]] = row
	Settings.lang = keep[0]
	Loc.code = keep[1]
	Settings.a11y["text"] = keep[2]
	Settings.a11y["font"] = keep[3]
	Settings.text_cap = keep[4]
	UI._touch = keep[5]
	UI._phone = keep[6]
	UI.clear_font_cache()
	return out


## Пузырь Барти в узкой колонке на телефоне (aeroz_lock: 8 деталей и сноски): портрет не ложится на «СНОСКИ
## МАНУАЛА», текст — внутри колонки; при 100 % у flat — портрет на месте (как было).
func _barty_col() -> void:
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1
	UI.set_phone(true)
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	for cb: Array in [["ru", 0, false], ["ru", 3, false], ["en", 3, true]]:
		_set_text(cb[0], cb[1], cb[2])
		for jid: String in ["aeroz_lock", "flat"]:
			Nav.go("job", {"job": jid, "variant": 0})
			await R._frames(2)
			var j: Node = Nav.current
			var m: SpeechBubble = j._mentor
			var notes := j.get_node_or_null("Notes") as Control
			var nt: float = notes.get_global_rect().position.y if notes != null else 720.0
			var lay: Array = m.col_layout()
			var lines := UI.wrap_lines(Loc.t(m.line), lay[1], lay[2]).size()
			if int(lay[3]) > 0:
				lines = mini(lines, int(lay[3]))
			var lh: float = UI.line_height(lay[2]) + 2
			var text_end: float = m.col.position.y + (8.0 if m.col_portrait() else maxf(1.0, (m.col.size.y - lines * lh + 2)
				/ 2.0)) + lines * lh - 2
			var por_end: float = m.col.position.y + 62.0 if m.col_portrait() else m.col.position.y
			if m.col.end.y > nt + 0.5 or por_end > nt + 0.5 or text_end > m.col.end.y + 0.5:
				_fail("E22: %s %s %d%%: пузырь Барти %s (портрет %s, текст до %.0f) заходит на «СНОСКИ» (y %.0f)"
					% [jid, cb[0], [100, 112, 125, 150][cb[1]], m.col, m.col_portrait(), text_end, nt])
			if jid == "flat" and not m.col_portrait():
				_fail("E22: flat %s: в высокой колонке пропал портрет Барти" % cb[0])
	_set_text("ru", 0, false)
	UI.set_phone(false)
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	Nav.go("hub")
	await R._frames(2)


# ---- E17: телефон, мини-игра «звон» — угол квадрата 56×56 круглой кнопки спицы переносится в её центр ----
func _spoke_corner() -> void:
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1
	UI.set_phone(true)
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("job", {"job": "spokes", "variant": 0})
	await R._frames(2)
	var j: Node = Nav.current
	var st: Dictionary = {}
	for s: Dictionary in j.steps():
		if s.get("mini") is Dictionary and s["mini"]["kind"] == "ping":
			st = s
			break
	if st.is_empty():
		_fail("E17: у spokes нет мини-игры «звон»")
	else:
		j.phase = "repair"
		j.start_mini(st)
		await R._frames(2)
		var b := j.mini.get_node_or_null("Spoke_0") as Control
		if b == null or not b.get("hit_circle"):
			_fail("E17: нет круглой кнопки Spoke_0")
		else:
			var r := b.get_global_rect()
			var dead := 0
			for p: Vector2 in [r.position + Vector2(2, 2), Vector2(r.end.x - 3, r.position.y + 2),
					Vector2(r.position.x + 2, r.end.y - 3), r.end - Vector2(3, 3)]:
				var q := Nav.touch_snap(p, true)
				if not UI.hits(b, q):
					dead += 1
			var c := r.get_center()
			if dead > 0 or Nav.touch_snap(c, true) != c:
				_fail("E17: углов квадрата спицы мимо: %d из 4 (центр %s → %s)" % [dead, c, Nav.touch_snap(c, true)])
		j.close_mini()
	UI.set_phone(false)
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	Nav.go("hub")
	await R._frames(2)


# ---- E24: «ЗАКРЫТЬ» в окне сносок на телефоне — 56; смена языка при открытом окне сносок / мини-игры ----
func _job_windows() -> void:
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1
	UI.set_phone(true)
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	var code0 := Loc.code
	Nav.go("job", {"job": "aeroz_lock", "variant": 0})
	await R._frames(2)
	var j: Node = Nav.current
	j.open_notes()
	await R._frames(2)
	var cl := j.notes.get_node("Close") as Control
	if cl.size.y < UI.PHONE_MIN:
		_fail("E24: «ЗАКРЫТЬ» в окне сносок на телефоне %d px (меньше %d)" % [cl.size.y, UI.PHONE_MIN])
	var n0: String = j.notes.accessibility_name
	var c0: String = cl.accessibility_name
	Loc.toggle()
	await R._frames(2)
	j = Nav.current
	if j.notes == null or j.notes.accessibility_name == n0 or cl.accessibility_name == c0 \
			or j.notes.accessibility_name != Loc.t("СНОСКИ ИЗ МАНУАЛОВ"):
		_fail("E24: смена языка при открытом окне сносок — подписи прежние («%s», «%s»)"
			% [j.notes.accessibility_name if j.notes else "", cl.accessibility_name])
	Loc.toggle()
	await R._frames(1)
	j.close_notes()
	await R._frames(1)
	var st: Dictionary = {}
	for s: Dictionary in j.steps():
		if s.get("mini") is Dictionary:
			st = s
			break
	if not st.is_empty():
		j.phase = "repair"
		j.start_mini(st)
		await R._frames(2)
		var later := j.mini.get_node("Later") as GameButton
		var l0 := later.accessibility_name
		Loc.toggle()
		await R._frames(2)
		if later.accessibility_name == l0 or not later.accessibility_name.begins_with(Loc.t(later.label)):
			_fail("E24: смена языка при открытой мини-игре — «%s» осталось «%s»" % [later.label, later.accessibility_name])
		Loc.toggle()
		await R._frames(1)
		Nav.current.close_mini()
	Loc.code = code0
	UI.set_phone(false)
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	Nav.go("hub")
	await R._frames(2)


# ---- E25 (телефон): подсказка окна кода под «Скопировано…» не заходит на кнопки; E23 (телефон): подписи причин
# замечания в ширину кнопки (2 столбца по 486) ----
const SHARE_NOTES := ["Вставь его в игре на другом устройстве: Настройки → Игра → «Вставить код».",
	"Открой ссылку на другом устройстве — игра предложит загрузить прогресс.",
	"Отправь его тому, кто дал задание: он вставит код в игре (Настройки → Игра → «Вставить код»).",
	"Отправь ссылку ученику: игра откроется сразу с этими заданиями.",
	"Ученик вставит его в игре: Настройки → Игра → «Вставить код». В браузерной версии игры ту же подборку можно отправить ссылкой."]


func _phone_texts() -> String:
	var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false), Settings.text_cap,
		UI._touch, UI._phone]
	UI._touch = 1
	UI._phone = 1
	var p := Rect2(UI.W / 2.0 - 390, UI.H / 2.0 - 210, 780, 420)       # ShareDialog.panel(), режим «show», код
	var w := p.size.x - 56
	var share_over := 0
	var reason_over_before := 0
	var reason_over := 0
	for cb: Array in COMBOS:
		_set_text(cb[0], cb[1], cb[2])
		Settings.text_cap = 1.25                                    # окно кодов — потолок 125 % (как game.py)
		for nt: String in SHARE_NOTES:
			var y := ShareDialog.status_y(p.end.y - 128, w, p, nt)
			var nl := mini(2, UI.wrap_lines(Loc.t(nt), w, 14).size())
			if y + 26 + nl * (UI.line_height(14) + 2) - 2 > p.end.y - 72 - 4:
				share_over += 1
		Settings.text_cap = 0.0                                     # окно замечания — без потолка (как game.py)
		var cw := (FeedbackDialog.PP.size.x - 56 - 12) / 2.0
		for key: String in ["feedback_reasons", "dispute_reasons"]:
			for r: String in Content.consts.get(key, []):
				var lbl := "◉  " + Loc.t(r)
				if UI.text_width(lbl, 16) > cw - 28:
					reason_over_before += 1
				var f: Array = UI.fit_text(lbl, cw - 28, 16)
				if UI.text_width(f[0], f[1]) > cw - 28 + 0.5 or f[0] != lbl and not str(f[0]).ends_with("…"):
					reason_over += 1
	Settings.lang = keep[0]
	Loc.code = keep[1]
	Settings.a11y["text"] = keep[2]
	Settings.a11y["font"] = keep[3]
	Settings.text_cap = keep[4]
	UI._touch = keep[5]
	UI._phone = keep[6]
	UI.clear_font_cache()
	if share_over > 0:
		_fail("E25: подсказка окна кода на телефоне заходит на кнопки: %d случаев" % share_over)
	if reason_over > 0:
		_fail("E23: подпись причины замечания шире кнопки на телефоне: %d" % reason_over)
	return "E25 подсказка окна кода на телефоне над кнопками, E23 причины замечания в ширину кнопки (было шире: %d)" \
		% reason_over_before


func _calm(on: bool) -> void:
	Settings.a11y["calm"] = on
	Settings.changed.emit("calm")


# ---- E14: «Без анимации», включённая после проезда в Гильдии и посреди проезда в мастерской ----
func _calm_ride() -> void:
	var calm0: bool = Settings.a11y.get("calm", false)
	_calm(false)
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("tech", {"job": "toe", "exam": false})
	await R._frames(2)
	var tc: Node = Nav.current
	while tc.phase == "repair":
		tc.step_skip()
	await R._frames(1)
	var tl := RideView.tech_loop("toe")
	if tl != "":
		Frames.want_loop(tl)
		Frames.flush()
	tc._test_pressed()
	await R._frames(2)
	tc.ride.t0 = tc.ride.t - tc.ride.secs() - 0.01
	await R._frames(3)
	var stood: bool = tc.ride.stay
	_calm(true)
	await R._frames(2)
	tc = Nav.current
	if stood and (not tc.chair.visible or tc.ride.shown):
		_fail("E14: Гильдия, «Без анимации» после проезда — пустое место (коляска видна %s, слой проезда %s)"
			% [tc.chair.visible, tc.ride.shown])
	_calm(false)
	await R._frames(1)
	Nav.go("job", {"job": "joystick", "variant": 0})
	await R._frames(2)
	var j: Node = Nav.current
	j.phase = "test"
	j.rebuild()
	var hero := RideView.hero_loop(j.job["client_art"])
	if hero != "":
		Frames.want_loop(hero)
		Frames.flush()
	await R._frames(2)
	j._test_pressed()
	await R._frames(3)
	var rode: bool = j.ride.riding()
	_calm(true)
	await R._frames(4)
	j = Nav.current
	if rode and (j.ride.shown or j.ride.dust_shown or j.ride.riding()):
		_fail("E14: «Без анимации» посреди проезда — полосы/пыль без героя (рисуется %s, пыль %s, едет %s)"
			% [j.ride.shown, j.ride.dust_shown, j.ride.riding()])
	_calm(calm0)
	Nav.go("hub")
	await R._frames(2)


# ---- E16: громкость старой фоновой петли при быстрой смене сцены; пауза музыки без звука не дёргается ----
func _audio() -> void:
	var on0: bool = Settings.vol.get("on", true)
	Settings.vol["on"] = true
	Audio.ambient("bg_workshop.png")
	Audio._amb_k = 0.22
	var was_playing: bool = Audio._amb.playing
	Audio.ambient("bg_road.png")
	if was_playing and absf(Audio._amb_old_k - 0.22) > 0.01:
		_fail("E16: старая петля после смены сцены k=%.2f (была 0,22 — скачок громкости)" % Audio._amb_old_k)
	Settings.vol["on"] = false
	var seq: Array = []
	for i in 4:
		Audio.apply_volume()
		seq.append(Audio._music.stream_paused)
	if seq.has(false):
		_fail("E16: без звука пауза музыки переключается каждый кадр: %s" % [seq])
	Settings.vol["on"] = on0
	Audio.apply_volume()


# ---- E28.1: Гильдия — инструмент у курсора и вспышка верного шага; E28.4: «Свечение» на титрах ----
func _guild_fx() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	var kb0: bool = UI.kb_active
	UI.kb_active = false
	Nav.go("tech", {"job": "truing", "exam": false})
	await R._frames(2)
	var tc: Node = Nav.current
	if not "_fx" in tc or tc.tools == null or (tc.tools.ids as Array).is_empty():
		_fail("E28.1: в про-задании нет слоя инструмента у курсора")
	else:
		tc.select_tool(tc.tools.ids[0])
		await R._frames(2)
		if not tc._fx_on:
			_fail("E28.1: выбранный инструмент в Гильдии не рисуется у курсора")
		tc.sel_tool = ""
		await R._frames(2)
		if tc._fx_on:
			_fail("E28.1: инструмент у курсора не погас")
	UI.kb_active = kb0
	var glow0: bool = Settings.glow
	Settings.glow = true
	Nav.go("credits")
	await R._frames(2)
	var bg: BgLayer = null
	for c: Node in Nav.current.get_children():
		if c is BgLayer:
			bg = c
	Settings.glow = false
	Settings.changed.emit("glow")
	await R._frames(2)
	if bg != null and bg._amb.visible:
		_fail("E28.4: титры — «Свечение» выключили, а частицы фона остались")
	Settings.glow = glow0
	Settings.changed.emit("glow")
	Nav.go("hub")
	await R._frames(2)


# ---- E29.5: следующий клиент примерки — с первой страницы «⚠»; E29.8: шаг назад гасит ToolAction, поворот не щёлкает
func _misc29() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("seating")
	await R._frames(2)
	var s: Node = Nav.current
	s.warn_page = 2
	s.solved = true
	s.check_fit()
	if s.warn_page != 0:
		_fail("E29.5: «СЛЕДУЮЩИЙ КЛИЕНТ» оставил страницу «⚠» %d" % s.warn_page)
	Nav.go("job", {"job": "flat", "variant": -1})
	await R._frames(2)
	var j: Node = Nav.current
	j.inspected = {"tire": true, "tube": true}
	for i in j.job["diagnosis"].size():
		if j.job["diagnosis"][i]["correct"]:
			j.choose_diagnosis(i)
			break
	await R._frames(1)
	var st: Dictionary = j.cur_step()
	if st.get("mini") is Dictionary:
		j.complete_base_step(st)
	else:
		j.do_action(st["tool"], st["part"])
	await R._frames(1)
	if j.step_idx > 0:
		var calm0: bool = Settings.a11y.get("calm", false)
		Settings.a11y["calm"] = false
		j.action.start(st["tool"], true, Vector2(400, 300))
		j.step_back()
		if j.action.active:
			_fail("E29.8: шаг назад не погасил анимацию инструмента")
		Settings.a11y["calm"] = calm0
	var arts: Array = Frames.tt_index.keys()
	var ts := TurntableShow.make(str(arts[0]), Rect2(100, 100, 380, 300))
	Nav.current.add_child(ts)
	await R._frames(1)
	ts.yaw = 3.0                                  # автоповорот ушёл далеко
	ts._tick_yaw = 0.0
	var e := InputEventMouseButton.new()
	e.button_index = MOUSE_BUTTON_LEFT
	e.pressed = true
	e.position = Vector2(50, 50)
	ts._gui_input(e)
	if ts.drag and absf(ts._tick_yaw - ts.yaw) > 0.001:
		_fail("E29.8: нажатие на коляску после автоповорота не запомнило угол — первый сдвиг щёлкнет")
	ts.queue_free()
	Nav.go("hub")
	await R._frames(2)
