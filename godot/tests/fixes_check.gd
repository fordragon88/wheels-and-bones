extends Node
## Проверки находок аудита 20.11 (перенесены из tests/_audit_logic): каждая падала до починки. Зовёт самопроверка
## (tests/selftest_runner.gd, и отдельно «-- --test --only fixes»). run(R) → строка для итога; ошибки — R.err().

var R: Node


func run(runner: Node) -> String:
	R = runner
	var done: PackedStringArray = []
	_merge()
	done.append("объединение сохранений двух вкладок")
	await _gap()
	done.append("зазор 3,5–4,5")
	await _ride_rebuild()
	done.append("проезд переживает смену языка")
	await _hub_page()
	done.append("страница очереди и гаража")
	await _meter_lang()
	done.append("подписи прибора после смены языка")
	await _keys_misc()
	done.append("M при настройках, ошибка ремонта гаснет, Esc 10 с с «Одной кнопкой», Барти в Гильдии")
	# C7: имя из ссылки с неназначенным знаком Юникода (U+0378) — как str.isprintable() в Python (выбрасывается)
	var nm := Share.clean_line("x" + String.chr(0x0378) + "y" + String.chr(0x0300) + String.chr(0xE000), 40)
	if nm != "y".insert(0, "x") + String.chr(0x0300):
		_fail("имя из ссылки с U+0378: «%s», в game.py «xy» + комбинирующий знак" % nm)
	done.append("непечатные знаки Юникода как в Python")
	return "находки аудита: " + ", ".join(done)


func _fail(msg: String) -> void:
	R.err("аудит 20.11: " + msg)


# ---- A1: объединение сохранений двух вкладок (SaveGame.merge_saves) ----
func _merge() -> void:
	var M := SaveGame
	var base := {"done": ["flat"], "garage": [["flat", 2]], "seat_done": [], "exam_passed": false, "seat_quiz_ok": false,
		"tutorial_skipped": true, "ending_seen": false, "gen": 0}
	# вкладка A прошла caster (хранится), вкладка B со старым прогрессом прошла brake — оба задания остаются
	var stored := base.duplicate(true)
	stored["done"] = ["caster", "flat"]
	stored["garage"] = [["flat", 2], ["caster", 3]]
	var mine := base.duplicate(true)
	mine["done"] = ["brake", "flat"]
	mine["garage"] = [["flat", 3], ["brake", 1]]
	var out: Dictionary = M.merge_saves(stored, mine, base)
	if out["done"] != ["brake", "caster", "flat"]:
		_fail("две вкладки: done %s, ждали brake, caster, flat" % [out["done"]])
	if out["garage"] != [["flat", 3], ["caster", 3], ["brake", 1]]:
		_fail("две вкладки: гараж %s (лучшие звёзды, порядок хранимого)" % [out["garage"]])
	# флаги — «или»
	mine["exam_passed"] = true
	out = M.merge_saves(stored, mine, base)
	if not out["exam_passed"] or not out["tutorial_skipped"]:
		_fail("флаги не объединяются «или»")
	# сброс в вкладке A (gen 1): старая вкладка B (gen 0) сохраняет — старое не воскресает, своё новое остаётся
	var reset := {"done": [], "garage": [], "seat_done": [], "exam_passed": false, "seat_quiz_ok": false,
		"tutorial_skipped": false, "ending_seen": false, "gen": 1}
	var b_mine := base.duplicate(true)
	b_mine["done"] = ["brake", "flat"]
	b_mine["garage"] = [["flat", 2], ["brake", 2]]
	out = M.merge_saves(reset, b_mine, base)
	if out["done"] != ["brake"] or out["garage"] != [["brake", 2]] or out["tutorial_skipped"] or int(out["gen"]) != 1:
		_fail("сброс в другой вкладке «воскрес»: %s" % [out])
	# …а переигранное после сброса задание (flat было и до него) — своё новое (fresh), остаётся
	out = M.merge_saves(reset, b_mine, base, {"flat": 3})
	if out["done"] != ["brake", "flat"] or out["garage"] != [["brake", 2], ["flat", 3]]:
		_fail("переигранное после сброса задание потеряно: %s" % [out])
	# задание по ссылке: тот же id — пункты объединяются, первая попытка — хранимая
	var a_st := {"id": "X1", "jobs": ["flat", "caster"], "done": {"flat": 1}, "errors": {"flat": 2}, "secs": {"flat": 30},
		"active": true, "sent": false}
	var a_mine := {"id": "X1", "jobs": ["flat", "caster"], "done": {"flat": 1, "caster": 1}, "errors": {"flat": 5, "caster": 0},
		"secs": {"flat": 99, "caster": 10}, "active": true, "sent": false}
	stored["assign"] = a_st
	mine["assign"] = a_mine
	out = M.merge_saves(stored, mine, base)
	var a: Dictionary = out["assign"]
	if (a["done"] as Dictionary).size() != 2 or int(a["errors"]["flat"]) != 2 or int(a["errors"]["caster"]) != 0:
		_fail("задание по ссылке: %s" % [a])


# ---- B2: смена языка посреди проезда в обычном задании (t_ride_rebuild) ----
func _ride_rebuild() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("job", {"job": "flat", "variant": -1})
	await R._frames(2)
	var j: Node = Nav.current
	j.inspected = {"a": true, "b": true}
	j.phase = "test"
	j.rebuild()
	await R._frames(2)
	j._test_pressed()
	await R._frames(5)
	if not j.ride.riding():
		_fail("проезд не начался")
	Loc.toggle()
	await R._frames(3)
	j = Nav.current
	if not j.ride.riding() or j.chair.visible or j._test_btn.visible:
		_fail("смена языка посреди проезда: проезд %s, коляска видна %s, кнопка видна %s (ждали: идёт, нет, нет)"
			% [j.ride.riding(), j.chair.visible, j._test_btn.visible])
	Loc.toggle()
	await R._frames(1)
	Nav.go("hub")
	await R._frames(1)


# ---- B3: страница очереди мастерской и гаража переживает вход в задание (game.py hub_page) ----
func _hub_page() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("hub")
	await R._frames(2)
	Nav.current._flip(1)
	await R._frames(1)
	var jid: String = SaveGame.available_jobs()[9]
	Nav.current._open_job(jid)
	await R._frames(2)
	Nav.current.go_back()
	Nav.current.go_back()
	await R._frames(2)
	if Nav.current_name != "hub" or Nav.current.page != 1:
		_fail("из задания в мастерскую: %s, страница %d (game.py: hub_page = 1)" % [Nav.current_name, Nav.current.page])
	SaveGame.start_assignment(Share.assign_parse({"jobs": "flat"}))
	if Nav.hub_page != 0:
		_fail("вход в задание по ссылке не сбросил страницу очереди (как start_assignment)")
	SaveGame.exit_assignment()
	Nav.hub_page = 1
	SaveGame.reset_progress()
	if Nav.hub_page != 0:
		_fail("сброс прогресса не сбросил страницу очереди")
	Nav.garage_page = 1
	Nav.go("garage")
	await R._frames(1)
	Nav.go("hub")
	await R._frames(1)
	if Nav.garage_page != 1:
		_fail("страница гаража сбросилась при выходе (game.py garage_page живёт весь сеанс)")
	SaveGame.reset()


# ---- C1: окно прибора открыто, язык сменили — подписи вариантов и окна для чтеца (t_meter_lang) ----
func _meter_lang() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("job", {"job": "lift", "variant": -1})
	await R._frames(2)
	var j: Node = Nav.current
	var st: Dictionary = {}
	for s: Dictionary in j.steps():
		if s.get("mini") is Dictionary and s["mini"]["kind"] == "meter":
			st = s
			break
	j.phase = "repair"
	j.start_mini(st)
	await R._frames(2)
	var o0: String = j.mini.get_node("Opt_0").accessibility_name
	var w0: String = j.mini.accessibility_name
	Loc.toggle()
	await R._frames(2)
	var want := Loc.t(st["mini"]["options"][0][0])
	if j.mini.get_node("Opt_0").accessibility_name != want or o0 == want:
		_fail("прибор: подпись варианта после смены языка «%s», ждали «%s»" % [j.mini.get_node("Opt_0").accessibility_name, want])
	if j.mini.accessibility_name != Loc.t(st["instr"]) or w0 == j.mini.accessibility_name:
		_fail("прибор: подпись окна не сменила язык")
	Loc.toggle()
	await R._frames(1)
	j.close_mini()
	Nav.go("hub")
	await R._frames(1)


# ---- C2–C5: клавиши и реплики ----
func _keys_misc() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("hub")
	await R._frames(2)
	Nav.open_settings()
	await R._frames(2)
	var on: bool = Settings.vol.get("on", true)
	await R._key(KEY_M)
	if Settings.vol.get("on", true) == on or Nav.settings == null:
		_fail("M при открытых настройках не переключил звук (game.py — переключает)")
	await R._key(KEY_M)
	Nav.close_settings()
	await R._frames(1)
	# ошибка инструмента в ремонте — сообщение гаснет само (game.py: flash без sticky)
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
	var other := "brake" if st["part"] != "brake" else "tire"
	j.do_action(st["tool"], other)
	if Nav.toast.sticky or Nav.toast.color != UI.BAD:
		_fail("ошибка в ремонте «прилипает» (sticky), в game.py гаснет сама")
	# двойной Esc: «Одна кнопка» — 10 с, иначе 2,5 с (game.py esc_timer)
	if Settings.esc_secs() != 2.5:
		_fail("окно второго Esc без «Одной кнопки» %.1f с, ждали 2,5" % Settings.esc_secs())
	Settings.a11y["scan"] = 1
	if Settings.esc_secs() != 10.0:
		_fail("окно второго Esc с «Одной кнопкой» %.1f с, ждали 10" % Settings.esc_secs())
	Settings.a11y["scan"] = 0
	Nav.go("hub")
	await R._frames(1)
	# Гильдия: react_good изредка отдаёт реплику Барти (как game.py: 0,3 клиент, 0,12 Барти)
	Nav.go("tech", {"job": Content.tech_jobs[0]["id"]})
	await R._frames(2)
	var tj: Node = Nav.current
	var barty := 0
	seed(5)
	for i in 400:
		tj.talk_later = []
		tj.react_good()
		if not tj.talk_later.is_empty() and tj.talk_later[1] == "barty":
			barty += 1
	if barty < 20 or barty > 80:
		_fail("Гильдия: реплик Барти «good» %d из 400 (ждали ~48)" % barty)
	tj.barty_quip("good", 5.0)
	if Settings.barty_on() and tj.ghost_quip == "":
		_fail("Гильдия: barty_quip не показал реплику")
	Nav.go("hub")
	await R._frames(1)
	SaveGame.reset()


# ---- A3: зазор с дробными границами (olga_x3: 3,5–4,5) — как mini_gap_check в game.py ----
func _gap() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("job", {"job": "olga_x3", "variant": -1})
	await R._frames(2)
	var j: Node = Nav.current
	var st: Dictionary = {}
	for s: Dictionary in j.steps():
		if s.get("mini") is Dictionary and s["mini"]["kind"] == "gap":
			st = s
	if st.is_empty():
		_fail("olga_x3: нет шага с зазором")
		return
	var want := {3: "missed", 4: "solved", 5: "missed"}   # game.py: 3 и 5 — мимо, 4 — в допуске
	for v: int in want:
		j.phase = "repair"
		j.start_mini(st)
		await R._frames(1)
		var res := [""]
		var m1: int = j.mistakes
		j.mini.missed.connect(func(_m: String, _s: float) -> void: res[0] = "missed")
		j.mini.solved.connect(func() -> void: res[0] = "solved")
		j.mini.gap_set(v)
		j.mini.gap_check()
		if res[0] != want[v]:
			_fail("зазор %d мм при допуске 3,5–4,5: %s, в game.py %s" % [v, res[0], want[v]])
		if j.mini:
			j.close_mini()
		await R._frames(1)
	Nav.go("hub")
	await R._frames(1)
	SaveGame.reset()
