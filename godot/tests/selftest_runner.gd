extends Node
## Сам прогон самопроверки (tests/selftest.gd запускает его, когда автозагрузки уже в дереве: скрипт -s
## компилируется раньше, чем появляются их имена).
## Самопроверка без окна:
##   D:\Godot\Godot_v4.7.2-stable_win64_console.exe --headless --path godot -s res://tests/selftest.gd -- --test
## Проверяет: автозагрузки на месте, все .gd компилируются, содержание читается (21 задание, 27 вариантов
## поломок, 6 про-заданий — как SELFTEST pygame-версии), у каждого задания есть портрет, коляска и кадры поворота
## (36 файлов, первый читается), палитра совпадает с game.py, у каждой строки, которую показывают титул, мастерская,
## экран задания (все задания и варианты) и окно настроек, есть английский вариант; проходит титул → мастерская →
## задание flat → осмотр → неверный → верный диагноз мышью (события ввода) и титул → задание с клавиатуры.
## Выход 0 и «GODOT SELFTEST OK …» или 1 и список ошибок.

const AUTOLOADS := ["Settings", "Loc", "Content", "SaveGame", "Audio", "Frames", "Speech", "Nav"]

var errors: PackedStringArray = []
var notes: PackedStringArray = []
var _drawn := 0


func _ready() -> void:
	_run.call_deferred()


func err(msg: String) -> void:
	errors.append(msg)
	printerr("  - " + msg)


func _run() -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	for n: String in AUTOLOADS:
		if get_tree().root.get_node_or_null(n) == null:
			err("нет автозагрузки " + n)
	if not errors.is_empty():
		_finish()
		return
	if Settings.persist or SaveGame.persist:
		err("самопроверку запускать с «-- --test» (иначе тронет настройки и сохранение игрока)")
		_finish()
		return
	# --- скрипты ---
	var n_gd := _check_scripts("res://")
	# --- содержание ---
	for e: String in Content.errors:
		err("содержание: " + e)
	var n_jobs: int = Content.jobs.size()
	var n_var: int = Content.variant_count()
	var n_tech: int = Content.tech_jobs.size()
	if n_jobs != 21 or n_var != 27 or n_tech != 6:
		err("ждали 21 задание (27 вариантов) + 6 про-заданий, есть %d (%d) + %d" % [n_jobs, n_var, n_tech])
	for job: Dictionary in Content.jobs:
		for key: String in ["client_art", "chair_art"]:
			if Content.texture(job[key]) == null:
				err("%s: картинка %s не загружается" % [job["id"], job[key]])
		var art: String = job["chair_art"]
		if not Frames.has_turntable(art):
			err("%s: нет кадров поворота %s" % [job["id"], art])
			continue
		var tt: Dictionary = Frames.turntable(art)
		for i in int(tt["n"]):
			var p := "res://content/frames/turntable/%s_%02d.webp" % [art.get_basename(), i]
			if not FileAccess.file_exists(p):
				err("%s: нет кадра %s" % [job["id"], p])
				break
		var img := Image.new()
		if img.load_webp_from_buffer(FileAccess.get_file_as_bytes(
				"res://content/frames/turntable/%s_00.webp" % art.get_basename())) != OK:
			err("%s: кадр 00 не читается" % job["id"])
		for pid: String in job.get("parts", []) if not job.has("variants") else []:
			if not tt["centers"].has(pid):
				notes.append("%s: у детали %s нет кружка на коляске (только в списке)" % [job["id"], pid])
	for loop: String in ["martin_wave", "barty_wave"]:
		if Frames.loop_count(loop) == 0:
			err("нет петли " + loop)
	var consts: Dictionary = Content.consts.get("colors", {})
	for k: String in consts:
		var c: Array = consts[k]
		if UI.PALETTE.has(k) and UI.PALETTE[k] != Color8(c[0], c[1], c[2]):
			err("цвет %s не совпадает с game.py" % k)
	# --- рисуется ли _draw без окна (для проверки перевода) ---
	var probe := Control.new()
	probe.draw.connect(func() -> void: _drawn += 1)
	get_tree().root.add_child(probe)
	probe.queue_redraw()
	await get_tree().process_frame
	await get_tree().process_frame
	probe.queue_free()
	# --- перевод: всё, что показывают экраны ---
	Loc.audit = true
	Loc.misses.clear()
	Nav.go("title")
	await _frames(40)
	Nav.open_settings()
	await _frames(3)
	Nav.close_settings()
	await _frames(2)
	SaveGame.tutorial_skipped = true
	for page in 3:
		Nav.go("hub")
		await _frames(2)
		Nav.current.page = page
		Nav.current.rebuild()
		await _frames(2)
		for b: Node in Nav.current._cards:     # записки клиентов
			Nav.current._set_note(b.get_meta("job"))
			await _frames(1)
	for job: Dictionary in Content.jobs:
		for v in maxi(1, job.get("variants", []).size()):
			Nav.go("job", {"job": job["id"], "variant": v if job.has("variants") else -1})
			await _frames(2)
			var scr: Node = Nav.current
			for pid: String in scr.job["parts"]:
				scr.inspect_part(pid)          # все улики — сообщением сверху
				await _frames(1)
			for o: Dictionary in scr.job["diagnosis"]:
				Loc.t(o.get("feedback", ""))
			for kind: String in ["intro", "worry", "learn", "mistake", "good", "test"]:
				for line: String in Content.client_talk(job["id"]).get(kind, []):
					Loc.t(line)
			Loc.t(scr.job.get("thanks", ""))
			for st: Dictionary in scr.job.get("steps", []).slice(0, 1):
				Loc.t(st.get("ghost", ""))
	for kind: String in Content.talk.get("barty", {}):
		for line: String in Content.talk["barty"][kind]:
			Loc.t(line)
	for s: String in ["Диагноз верный! Приступаем к ремонту.", "Не похоже. Осмотри ещё раз.", "Крупнее нельзя.",
			"Мельче нельзя.", "Ещё раз Esc — покинуть ремонт (прогресс задания сбросится).", "Тут вроде всё в порядке.",
			"Ещё раз Esc — выйти из игры.", "Звук включён", "Звук выключен (M — включить)",
			"Обучение пропущено: все клиенты уже ждут. Коляску Мартина можно починить в любой момент."]:
		Loc.t(s)
	Nav.go("job", {"job": "flat"})
	await _frames(2)
	Nav.current.inspected = {"tire": true, "tube": true}
	for i in Nav.current.job["diagnosis"].size():
		if Nav.current.job["diagnosis"][i]["correct"]:
			Nav.current.choose_diagnosis(i)
	await _frames(3)
	# --- бот: все задания и варианты поломок от входа до записи прогресса, сверка с pygame ---
	SaveGame.reset()
	var bot: Array = await _bot_all()
	await _negatives()
	SaveGame.reset()
	var ev_jobs: Array = []
	for kind: String in ["pump", "ping", "gap", "meter"]:
		var key := _ref_with_mini(kind)
		if key == "":
			err("в эталоне нет задания с мини-игрой " + kind)
			continue
		if key not in ev_jobs:
			ev_jobs.append(key)
	for key: String in ev_jobs:
		await _flow_repair(key, false)
	var kb_jobs: Array = ev_jobs.duplicate()
	for key: String in kb_jobs:
		await _flow_repair(key, true)
	await _flow_intro()
	await _flow_garage_ending()
	await _flow_feedback()
	await _flow_help_settings()
	await _flow_guild_access()
	var gbot: Array = await _bot_guild()
	await _flow_exam()
	await _flow_tech_events("truing", false, false)
	await _flow_tech_events("toe", false, false)
	await _flow_tech_events("truing", false, true)
	await _flow_tech_events("", true, false)
	await _flow_tech_events("", true, true)
	await _flow_guild_feedback()
	var seat_n: Array = await _seat_logic()
	var seat_line: String = await _flow_seating()
	Loc.audit = false
	var n_audit: int = Loc.audited.size()
	var dump := OS.get_cmdline_user_args().find("--dump-tr")
	if dump >= 0:                             # сверка с tr() pygame-версии (tools/check_tr.py)
		var out: Dictionary = {}
		Loc.code = "en"
		for s: String in Loc.audited:
			out[s] = Loc.t(s)
		Loc.code = "ru"
		var f := FileAccess.open(OS.get_cmdline_user_args()[dump + 1], FileAccess.WRITE)
		f.store_string(JSON.stringify(out, " "))
		f.close()
	var misses: Dictionary = Loc.misses
	for s: String in misses:
		err("нет английского: «%s» → «%s»" % [s, misses[s]])
	# --- кружки деталей: как _m3d_spots в pygame (flat, вариант 0, исходный ракурс; числа — из game.py) ---
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(2)
	var ch: ChairView = Nav.current.chair
	ch.t0 = -1e9
	if ch.rect() != Rect2(320, 152, 511, 404):
		err("коляска flat: прямоугольник %s, в pygame (320, 152, 511, 404)" % ch.rect())
	var want_spots := {"tire": [408, 319, 20], "tube": [418, 479, 20], "valve": [497, 476, 20], "rim": [401, 421, 20],
		"brake": [554, 380, 20], "spokes": [477, 360, 20]}
	for sp: Array in ch.spots():
		var w: Array = want_spots.get(sp[0], [])
		if w.is_empty() or absi(sp[1] - w[0]) > 1 or absi(sp[2] - w[1]) > 1 or sp[3] != w[2]:
			err("кружок %s: %s, в pygame %s" % [sp[0], sp.slice(1, 4), w])
	# --- сценарий мышью: титул → мастерская → flat → осмотр → неверный → верный диагноз ---
	SaveGame.reset()
	await _flow_mouse()
	await _flow_keyboard()
	_finish("бот прошёл %d/%d вариантов (%d шагов, как в pygame); событиями мыши и клавиатуры — %s; вступление и «пропустить», гараж, вечеринка, титры, справка F1, настройки, замечания (%d запросов = game.py, в сеть — ничего); Гильдия: %d/6 про-заданий в двух порядках, %d провалов по безопасности = game.py, спеки, экзамен (сдача, лимит, пересдача), мышью и клавиатурой; Кабинет посадки: %d случаев × сетка (%d положений ползунков) = game.py, позы уроков и зачёта (%d кадров перехода) = game.py, %s, сохранение, замечание = game.py; %d .gd, кадры поворота у всех 21 коляски, перевод: %d строк%s" % [bot[0], n_var, bot[1], ", ".join(ev_jobs), Feedback.captured.size(), gbot[0], gbot[1], seat_n[0], seat_n[1], seat_n[2], seat_line, n_gd, n_audit,
		"" if _drawn > 0 else " (без окна _draw не вызывается — проверены строки данных и обработчиков)"],
		n_jobs, n_var, n_tech)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _click(pos: Vector2) -> void:
	var m := InputEventMouseMotion.new()
	m.position = pos
	m.global_position = pos
	get_viewport().push_input(m, true)
	for pressed: bool in [true, false]:
		var e := InputEventMouseButton.new()
		e.button_index = MOUSE_BUTTON_LEFT
		e.pressed = pressed
		e.position = pos
		e.global_position = pos
		get_viewport().push_input(e, true)
	await get_tree().process_frame


func _key(code: Key, shift: bool = false) -> void:
	for pressed: bool in [true, false]:
		var e := InputEventKey.new()
		e.keycode = code
		e.physical_keycode = code
		e.shift_pressed = shift
		e.pressed = pressed
		get_viewport().push_input(e)
	await get_tree().process_frame


func _center(ctl: Control) -> Vector2:
	return ctl.get_global_rect().get_center()


func _flow_mouse() -> void:
	SaveGame.tutorial_skipped = true
	Nav.go("title")
	await _frames(2)
	Nav.current.st = 3.0
	await _frames(2)                          # «[ клик — начать ]» появляется через 1,6 с (в кадрах — не важно)
	await _click(Vector2(640, 600))            # клик по пустому месту титула
	await _frames(2)
	if Nav.current_name != "hub":
		err("мышь: клик по титулу не открыл мастерскую (%s)" % Nav.current_name)
		return
	var card: Control = Nav.current.get_node_or_null("Card_flat")
	if card == null:
		err("мышь: нет карточки flat")
		return
	await _click(_center(card))
	await _frames(2)
	if Nav.current_name != "job" or Nav.current.job.get("id") != "flat":
		err("мышь: карточка flat не открыла задание")
		return
	var scr: Node = Nav.current
	var parts: Array = scr.job["parts"]
	await _click(_center(scr.get_node("Part_" + parts[0])))       # пункт списка
	await _frames(1)
	var spot: Control = scr.chair.spot_button(parts[1])
	if spot == null:
		err("мышь: нет кружка детали %s" % parts[1])
		return
	await _frames(70)                          # вводный доворот коляски (1,1 с) — кружки встают на место
	await _click(_center(spot))                # кружок на коляске
	await _frames(1)
	if scr.inspected.size() != 2:
		err("мышь: осмотрено %d деталей вместо 2" % scr.inspected.size())
	var wrong := -1
	var right := -1
	for i in scr.job["diagnosis"].size():
		if scr.job["diagnosis"][i]["correct"]:
			right = i
		elif wrong < 0:
			wrong = i
	await _click(_center(scr.get_node("Diag_%d" % wrong)))
	await _frames(1)
	if scr.phase != "diagnose" or scr.mistakes != 1:
		err("мышь: неверный диагноз не засчитан ошибкой")
	if not Nav.toast.active() or Nav.toast.color != UI.BAD:
		err("мышь: нет сообщения об ошибке диагноза")
	await _click(_center(scr.get_node("Diag_%d" % right)))
	await _frames(2)
	if Nav.current.phase != "repair" or Nav.current.tools == null:
		err("мышь: верный диагноз не перевёл в ремонт")
	var played: Array = Audio.played
	for s: String in ["inspect", "bad", "ok"]:
		if not s in played:
			err("мышь: не прозвучал звук " + s)


func _flow_keyboard() -> void:
	SaveGame.tutorial_skipped = true
	Nav.go("title")
	await _frames(2)
	Nav.current.st = 3.0
	await _frames(2)
	await _key(KEY_ENTER)                      # фокус на «начать»
	await _frames(2)
	if Nav.current_name != "hub":
		err("клавиатура: Enter на титуле не открыл мастерскую (%s)" % Nav.current_name)
		return
	await _frames(2)
	var fo := get_viewport().gui_get_focus_owner()
	if fo == null or fo.name != "Card_flat":
		err("клавиатура: в мастерской фокус не на первой карточке (%s)" % (fo.name if fo else "нет"))
	await _key(KEY_RIGHT)                      # стрелка → вторая карточка
	await _key(KEY_TAB)                        # Tab → дальше
	await _key(KEY_TAB, true)                  # Shift+Tab ← обратно
	fo = get_viewport().gui_get_focus_owner()
	if fo == null or not str(fo.name).begins_with("Card_"):
		err("клавиатура: стрелки/Tab увели фокус с карточек (%s)" % (fo.name if fo else "нет"))
		return
	var want: String = str(fo.name).trim_prefix("Card_")
	await _key(KEY_ENTER)
	await _frames(2)
	if Nav.current_name != "job" or Nav.current.job.get("id") != want:
		err("клавиатура: Enter на карточке не открыл задание %s" % want)
		return
	await _frames(2)
	fo = get_viewport().gui_get_focus_owner()
	if fo == null or not str(fo.name).begins_with("Part_"):
		err("клавиатура: в задании фокус не на списке деталей")
		return
	await _key(KEY_ENTER)                      # осмотреть первую деталь
	await _key(KEY_DOWN)
	await _key(KEY_ENTER)                      # и вторую
	if Nav.current.inspected.size() != 2:
		err("клавиатура: осмотрено %d деталей вместо 2" % Nav.current.inspected.size())
	await _key(KEY_ESCAPE)
	await _key(KEY_ESCAPE)                     # двойной Esc — в мастерскую
	await _frames(2)
	if Nav.current_name != "hub":
		err("клавиатура: двойной Esc не вывел из задания")


func _check_scripts(dir: String) -> int:
	var n := 0
	var d := DirAccess.open(dir)
	if d == null:
		return 0
	for f in d.get_files():
		if f.ends_with(".gd"):
			n += 1
			var s := load(dir.path_join(f)) as GDScript
			if s == null or not s.can_instantiate():
				err("скрипт не компилируется: " + dir.path_join(f))
	for sub in d.get_directories():
		if sub.begins_with(".") or sub in ["content", "tools"]:
			continue
		n += _check_scripts(dir.path_join(sub))
	return n


func _finish(extra: String = "", n_jobs: int = 0, n_var: int = 0, n_tech: int = 0) -> void:
	Nav.shutdown()                            # прибрать за собой: иначе при выходе «ресурсы ещё заняты»
	await _frames(10)
	for n in notes:
		print("  * " + n)
	if errors.is_empty():
		print("GODOT SELFTEST OK — %d заданий (%d вариантов поломок) + %d про-заданий; %s" % [n_jobs, n_var, n_tech, extra])
		get_tree().quit(0)
	else:
		printerr("GODOT SELFTEST FAILED: %d ошибок" % errors.size())
		get_tree().quit(1)


# ======================= бот прохождения =======================

func _ref() -> Dictionary:
	var p := "res://content/walkthrough_ref.json"
	if not FileAccess.file_exists(p):
		err("нет content/walkthrough_ref.json — запусти tools/sync_content.py")
		return {}
	return JSON.parse_string(FileAccess.get_file_as_string(p))


func _ref_with_mini(kind: String) -> String:
	var ref := _ref()
	for key: String in ref:
		for st: Array in ref[key]["steps"]:
			if st[2] == kind:
				return key
	return ""


static func _sig(st: Dictionary) -> Array:
	var alt: Array = st.get("alt", []).duplicate()
	alt.sort()
	var alt_t: Array = st.get("alt_tools", []).duplicate()
	alt_t.sort()
	var mk: String = (st["mini"] as Dictionary).get("kind", "") if st.get("mini") is Dictionary else ""
	return [st["tool"], st["part"], mk, alt, alt_t]


func _open_job(key: String) -> Node:
	var jid := key.get_slice(":", 0)
	var v := int(key.get_slice(":", 1))
	var base := Content.job_by_id(jid)
	Nav.go("job", {"job": jid, "variant": v if base.has("variants") else -1})
	await _frames(2)
	return Nav.current


func _solve_mini(m: MiniGame) -> void:
	match m.kind:
		"pump":
			m.value = int(m.cfg["lo"])
			m.pump_done()
		"gap":
			m.gap_set(int(m.cfg["lo"]))
			m.gap_check()
		"ping":
			for i: int in m.dull.keys():
				m.ping(i)
		"meter":
			var opts: Array = m.cfg["options"]
			for i in opts.size():
				if opts[i][1]:
					m.meter(i)
					return


func _correct_diag(scr: Node) -> int:
	var d: Array = scr.job["diagnosis"]
	for i in d.size():
		if d[i]["correct"]:
			return i
	return -1


## Все задания мастерской и все варианты: обработчики напрямую. Возврат [вариантов пройдено, шагов].
func _bot_all() -> Array:
	var ref := _ref()
	var ok := 0
	var total := 0
	for job: Dictionary in Content.jobs:
		for v in maxi(1, job.get("variants", []).size()):
			var key := "%s:%d" % [job["id"], v]
			var scr: Node = await _open_job(key)
			var mine: Array = []
			for st: Dictionary in scr.job["steps"]:
				mine.append(_sig(st))
			if not ref.has(key):
				err("бот %s: нет в эталоне pygame" % key)
			elif JSON.stringify(mine) != JSON.stringify(ref[key]["steps"]):
				err("бот %s: шаги не как в pygame:\n    godot  %s\n    pygame %s" % [key, mine, ref[key]["steps"]])
			for pid: String in scr.job["parts"].slice(0, 2):
				scr.inspect_part(pid)
			if not scr.choose_diagnosis(_correct_diag(scr)):
				err("бот %s: верный диагноз не принят" % key)
				continue
			await _frames(1)
			scr = Nav.current
			var n: int = scr.job["steps"].size()
			var failed := false
			for i in n:
				var st: Dictionary = scr.job["steps"][i]
				scr.select_tool(st["tool"])
				scr.part_clicked(st["part"])
				if scr.mini != null:
					await _frames(1)
					_solve_mini(scr.mini)
				await _frames(1)
				if scr.mistakes != 0 or (i + 1 < n and scr.step_idx != i + 1):
					err("бот %s: шаг %d (%s → %s) не выполнен" % [key, i + 1, st["tool"], st["part"]])
					failed = true
					break
			if failed:
				continue
			total += n
			if scr.phase != "test":
				err("бот %s: после шагов нет тест-драйва" % key)
				continue
			scr.start_ride()
			scr.ride.t0 = scr.ride.t - scr.ride.secs() - 0.01
			await _frames(2)
			if not scr.ride_done:
				err("бот %s: проезд не закончился" % key)
				continue
			scr._test_pressed()
			await _frames(2)
			if Nav.current_name != "result" or not SaveGame.is_done(job["id"]):
				err("бот %s: нет итога или прогресс не записан" % key)
				continue
			if ref.has(key) and int(Nav.current.stars) != int(ref[key]["stars"]):
				err("бот %s: звёзд %d, в pygame %d" % [key, Nav.current.stars, ref[key]["stars"]])
			ok += 1
	if SaveGame.user_done_count() != Content.jobs.size():
		err("бот: в прогрессе %d заданий из %d" % [SaveGame.user_done_count(), Content.jobs.size()])
	Nav.go("hub")
	await _frames(2)
	if not str(Nav.current.get_node("Card_flat").accessibility_name).contains("✔"):
		err("мастерская: у пройденного задания нет отметки")
	return [ok, total]


func _toast_is(col: Color, part: String = "") -> bool:
	return Nav.toast.active() and Nav.toast.color == col and (part == "" or Nav.toast.text.contains(part))


## Негативные случаи: не тот инструмент, не та деталь, без инструмента, пропуск/назад, ловушка Барти, перекачал.
func _negatives() -> void:
	# сноски мануала: окно открывается, Esc закрывает; книжка у детали — сноска в карточке
	var nk := ""
	for job: Dictionary in Content.jobs:
		if nk == "" and not Content.job_notes(Content.resolve_job(job, 0, false)).is_empty():
			nk = "%s:0" % job["id"]
	var ns: Node = await _open_job(nk)
	for pid: String in ns.job["parts"].slice(0, 2):
		ns.inspect_part(pid)
	ns.choose_diagnosis(_correct_diag(ns))
	await _frames(1)
	ns.note_pin = Content.job_notes(ns.job)[0][0]
	await _frames(2)
	if ns.note_part_at() != ns.note_pin:
		err("сноска детали не показывается в карточке")
	ns.open_notes()
	await _frames(2)
	if ns.notes == null or ns.notes.lines().is_empty():
		err("окно сносок мануала пустое")
	ns.go_back()
	await _frames(1)
	if ns.notes != null:
		err("Esc не закрыл окно сносок")
	var scr: Node = await _open_job("flat:0")
	scr.inspect_part("tire")
	scr.inspect_part("tube")
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	var st: Dictionary = scr.cur_step()
	var other_tool := "pump" if st["tool"] != "pump" else "hands"
	var other_part := "brake" if st["part"] != "brake" else "rim"
	scr.select_tool(other_tool)
	scr.part_clicked(st["part"])
	if scr.mistakes != 1 or scr.step_idx != 0 or not _toast_is(UI.BAD):
		err("не тот инструмент: ошибка не засчитана")
	if st.get("wrongmsg", "") == "" and not _toast_is(UI.BAD, "Деталь верная, но инструмент не тот"):
		err("не тот инструмент: нет сообщения «инструмент не тот»")
	scr.select_tool(st["tool"])
	scr.part_clicked(other_part)
	if scr.mistakes != 2 or scr.step_idx != 0:
		err("не та деталь: ошибка не засчитана")
	scr.sel_tool = ""
	scr.part_clicked(st["part"])
	if not _toast_is(UI.AMBER) or scr.mistakes != 2:
		err("деталь без инструмента: нет подсказки «сначала выбери инструмент»")
	scr.step_skip()
	if scr.mistakes != 4 or scr.step_idx != 1:
		err("«ШАГ ▸»: пропуск должен дать шаг и 2 ошибки")
	scr.step_back()
	if scr.step_idx != 0:
		err("«◂»: шаг назад не сработал")
	# ловушка Барти: пузырь показывает совет шага (неверный); последовать ему — ошибка
	var trap_key := ""
	var trap_i := -1
	for job: Dictionary in Content.jobs:
		for c: Dictionary in Content.cases(job):
			for i in c.get("steps", []).size():
				if c["steps"][i].get("ghost_wrong", false) and c["steps"][i].get("wrongmsg", "") != "" and trap_key == "":
					trap_key = "%s:%d" % [job["id"], int(c.get("_variant", 0))]
					trap_i = i
	if trap_key == "":
		err("в данных нет ловушек Барти (ghost_wrong с wrongmsg)")
		return
	scr = await _open_job(trap_key)
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	for i in trap_i:
		var s2: Dictionary = scr.cur_step()
		scr.select_tool(s2["tool"])
		scr.part_clicked(s2["part"])
		if scr.mini:
			_solve_mini(scr.mini)
		await _frames(1)
	var trap: Dictionary = scr.cur_step()
	scr.ghost_quip = ""
	await _frames(2)
	if trap.get("ghost", "") == "" or scr._mentor.line != trap["ghost"]:
		err("ловушка Барти %s шаг %d: в пузыре нет совета шага" % [trap_key, trap_i + 1])
	var m0: int = scr.mistakes
	var wt := "hands" if trap["tool"] != "hands" and not "hands" in trap.get("alt_tools", []) else "lever"
	scr.select_tool(wt)
	scr.part_clicked(trap["part"])
	if scr.mistakes != m0 + 1:
		err("ловушка Барти: неверный ход не засчитан")
	if Nav.toast.text != trap["wrongmsg"]:
		err("ловушка Барти: нет объяснения wrongmsg")
	# мини-игра: перекачал / мало — ошибки, Esc закрывает окно
	scr = await _open_job(_ref_with_mini("pump"))
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	while scr.phase == "repair" and not scr.cur_step().get("mini") is Dictionary:
		scr.step_skip()
	var s3: Dictionary = scr.cur_step()
	scr.select_tool(s3["tool"])
	scr.part_clicked(s3["part"])
	await _frames(1)
	if scr.mini == null or scr.mini.kind != "pump":
		err("насос: мини-игра не открылась")
		return
	var m1: int = scr.mistakes
	scr.mini.value = int(scr.mini.cfg["hi"]) + 1
	scr.mini.pump_done()
	if scr.mistakes != m1 + 1 or scr.mini.value >= int(scr.mini.cfg["lo"]):
		err("насос: «перекачал» не засчитан ошибкой")
	scr.mini.value = 0
	scr.mini.pump_done()
	if scr.mistakes != m1 + 2:
		err("насос: «мало» не засчитан ошибкой")
	scr.go_back()
	await _frames(1)
	if scr.mini != null:
		err("Esc не закрыл мини-игру")


func _press(c: Control, keyboard: bool) -> void:
	if keyboard:
		c.grab_focus()
		await _frames(1)
		await _key(KEY_ENTER)
	else:
		await _click(_center(c))


## Задание целиком событиями ввода: мышью (клики по центрам элементов) или клавиатурой (фокус + Enter, стрелки).
func _flow_repair(key: String, keyboard: bool) -> void:
	var how := "клавиатура" if keyboard else "мышь"
	var scr: Node = await _open_job(key)
	for pid: String in scr.job["parts"].slice(0, 2):
		await _press(scr.get_node("Part_" + pid), keyboard)
	await _press(scr.get_node("Diag_%d" % _correct_diag(scr)), keyboard)
	await _frames(2)
	scr = Nav.current
	if scr.phase != "repair":
		err("%s %s: не начался ремонт" % [how, key])
		return
	var n: int = scr.job["steps"].size()
	for i in n:
		var st: Dictionary = scr.job["steps"][i]
		await _press(scr.tools.tiles[st["tool"]], keyboard)
		if scr.sel_tool != st["tool"]:
			err("%s %s шаг %d: инструмент не взят" % [how, key, i + 1])
			return
		var spot: HotspotButton = scr.chair.spot_button(st["part"])
		if i == 0 and spot != null:                  # первый шаг — кружком на коляске, дальше — списком
			await _frames(3)
			await _press(spot, keyboard)
		else:
			await _press(scr.get_node("Part_" + st["part"]), keyboard)
		await _frames(1)
		if scr.mini != null:
			await _mini_events(scr.mini, keyboard, how, key)
			await _frames(1)
		if scr.mistakes != 0 or (i + 1 < n and scr.step_idx != i + 1):
			err("%s %s шаг %d (%s → %s): не выполнен (ошибок %d)" % [how, key, i + 1, st["tool"], st["part"], scr.mistakes])
			return
	if scr.phase != "test":
		err("%s %s: нет тест-драйва" % [how, key])
		return
	await _frames(2)
	var hero := RideView.hero_loop(scr.job["client_art"])
	if hero != "":
		Frames.want_loop(hero)
		Frames.flush()
	await _press(scr.get_node("TestDrive"), keyboard)
	if hero != "" and scr.ride.loop_name != hero:
		err("%s %s: проезд не петлёй %s" % [how, key, hero])
	await _frames(3)
	if scr.ride.drawn == 0:
		err("%s %s: кадры проезда не рисуются" % [how, key])
	scr.ride.t0 = scr.ride.t - scr.ride.secs() - 0.01
	await _frames(2)
	await _press(scr.get_node("TestDrive"), keyboard)
	await _frames(2)
	if Nav.current_name != "result":
		err("%s %s: нет итога" % [how, key])
		return
	await _press(Nav.current.get_node("ToHub"), keyboard)
	await _frames(2)
	if Nav.current_name != "hub" or not SaveGame.is_done(key.get_slice(":", 0)):
		err("%s %s: не вернулись в мастерскую с отметкой" % [how, key])


func _mini_events(m: MiniGame, keyboard: bool, how: String, key: String) -> void:
	match m.kind:
		"pump":
			var lo := int(m.cfg["lo"])
			var hi := int(m.cfg["hi"])
			for _i in 80:
				if m.value >= lo and m.value <= hi:
					break
				await _press(m.get_node("Pump" if m.value < lo else "Release"), keyboard)
			await _press(m.get_node("Done"), keyboard)
		"gap":
			var tr: GapTrack = m.get_node("Track")
			var lo := int(m.cfg["lo"])
			if keyboard:
				tr.grab_focus()
				await _frames(1)
				for _i in 400:
					if m.value == lo:
						break
					await _key(KEY_RIGHT if m.value < lo else KEY_LEFT)
			else:
				var mn := float(m.cfg["mn"])
				var frac := (lo - mn) / (float(m.cfg["mx"]) - mn)
				await _click(tr.get_global_rect().position + Vector2(frac * tr.size.x + 0.5, tr.size.y / 2))
			if m.value != lo:
				err("%s %s: шкала зазора выставлена в %d вместо %d" % [how, key, m.value, lo])
			await _press(m.get_node("Check"), keyboard)
		"ping":
			for i: int in m.dull.keys():
				if is_instance_valid(m) and m.is_inside_tree():
					await _press(m.get_node("Spoke_%d" % i), keyboard)
		"meter":
			var opts: Array = m.cfg["options"]
			for i in opts.size():
				if opts[i][1]:
					await _press(m.get_node("Opt_%d" % i), keyboard)


# ======================= срез 3: вокруг заданий =======================

## Новая игра: титул → вступление (5 слайдов, Enter) → первое задание; и отдельно — «Пропустить обучение».
func _flow_intro() -> void:
	SaveGame.reset()
	Nav.go("title")
	await _frames(2)
	Nav.current.st = 3.0
	await _frames(2)
	await _click(Vector2(640, 620))
	await _frames(2)
	if Nav.current_name != "intro":
		err("новая игра: титул не открыл вступление (%s)" % Nav.current_name)
		return
	var n: int = Nav.current.slides().size()
	for i in n * 2 + 2:
		if Nav.current_name != "intro":
			break
		await _press(Nav.current.get_node("Next"), true)       # Enter: допечатать, потом — дальше
	if Nav.current_name != "job" or Nav.current.job.get("id") != "flat":
		err("вступление не привело в первое задание (%s)" % Nav.current_name)
		return
	if Nav.current.get_node_or_null("SkipTutorial") == null:
		err("первое задание: нет «Пропустить обучение»")
	var scr: Node = Nav.current
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	if Nav.current.tutor_want().is_empty():
		err("обучение: в первом ремонте нет подсветки нужного инструмента")
	Nav.go("hub")
	await _frames(2)
	if Nav.current._cards.size() != 1:
		err("до обучения в мастерской %d карточек (нужна одна — Мартин)" % Nav.current._cards.size())
	# пропустить обучение со вступления
	SaveGame.reset()
	Nav.go("intro")
	await _frames(2)
	await _click(_center(Nav.current.get_node("SkipTutorial")))
	await _frames(2)
	if Nav.current_name != "hub" or not SaveGame.tutorial_skipped or Nav.current._cards.size() != 8:
		err("«Пропустить обучение»: нет мастерской со всеми клиентами")


## Гараж после починки, финал после всех 21, титры с титула и с вечеринки.
func _flow_garage_ending() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	Nav.go("hub")
	await _frames(2)
	await _press(Nav.current.get_node("Garage"), false)
	await _frames(2)
	if Nav.current_name != "garage" or Nav.current._cards.size() != 0:
		err("пустой гараж не открылся")
	# все 21, кроме одного, уже починены — последний ведёт на вечеринку
	for j: Dictionary in Content.jobs:
		if j["id"] != "flat":
			SaveGame.done[j["id"]] = true
			SaveGame.garage.append([j["id"], 2])
	var scr: Node = await _open_job("flat:0")
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	scr = Nav.current
	while scr.phase == "repair":
		var st: Dictionary = scr.cur_step()
		scr.select_tool(st["tool"])
		scr.part_clicked(st["part"])
		if scr.mini:
			_solve_mini(scr.mini)
		await _frames(1)
	scr.start_ride()
	scr.ride.t0 = scr.ride.t - scr.ride.secs() - 0.01
	await _frames(2)
	scr._test_pressed()
	await _frames(2)
	if Nav.current_name != "result" or Nav.current._btn.label != "НА ВЕЧЕРИНКУ":
		err("итог последнего ремонта: нет «НА ВЕЧЕРИНКУ»")
	await _press(Nav.current.get_node("ToHub"), false)
	await _frames(2)
	if Nav.current_name != "ending" or not SaveGame.ending_seen:
		err("вечеринка не открылась (или не отмечена ending_seen)")
		return
	await _press(Nav.current.get_node("Credits"), false)
	await _frames(2)
	if Nav.current_name != "credits" or Nav.current.from != "ending":
		err("титры с вечеринки не открылись")
	Nav.current.scroll(1e6)
	if Nav.current.scroll_y <= 0.0:
		err("титры не листаются")
	await _key(KEY_ESCAPE)
	await _frames(2)
	if Nav.current_name != "ending":
		err("Esc в титрах не вернул на вечеринку")
	await _click(Vector2(640, 660))                 # клик по пустому месту вечеринки — гараж
	await _frames(2)
	if Nav.current_name != "garage" or Nav.current._cards.size() != 9 or Nav.current.pages() != 3:
		err("гараж после вечеринки: ждали 9 карточек на странице и 3 страницы")
		return
	await _press(Nav.current._cards[0], false)
	if Nav.current.open_idx != 0:
		err("гараж: карточка не открыла урок")
	await _key(KEY_ESCAPE)
	if Nav.current.open_idx != -1 or Nav.current_name != "garage":
		err("гараж: Esc не закрыл окно урока")
	await _press(Nav.current.get_node("Next"), false)
	if Nav.current.page != 1:
		err("гараж: «▶» не листает")
	# повтор задания после вечеринки — в мастерскую; кнопка «НА ВЕЧЕРИНКУ!» в мастерской
	Nav.go("hub")
	await _frames(2)
	if Nav.current.get_node_or_null("Party") == null:
		err("мастерская: после всех 21 нет «НА ВЕЧЕРИНКУ!»")
	Nav.go("title")
	await _frames(2)
	Nav.current.st = 3.0
	await _frames(2)
	await _press(Nav.current.get_node("Credits"), false)
	await _frames(2)
	if Nav.current_name != "credits" or Nav.current.from != "title":
		err("«ТИТРЫ» на титуле не открыли титры")
	var n0: int = Nav.support_opened
	await _press(Nav.current.get_node("Support"), false)
	if Nav.support_opened != n0 + 1:
		err("«ПОДДЕРЖАТЬ GOAT»: нет действия")
	await _press(Nav.current.get_node("BackBtn"), false)
	await _frames(2)
	if Nav.current_name != "title":
		err("«НАЗАД» в титрах не вернул на титул")


## Замечания: окно из флажка и из «Я НЕ СОГЛАСЕН»; запрос — как у game.py (content/feedback_ref.json), в сеть — ничего.
func _flow_feedback() -> void:
	if Feedback.url != "":
		err("тестовый режим: адрес таблицы замечаний не пуст — отправка запрещена")
		return
	var ref: Dictionary = {}
	if FileAccess.file_exists("res://content/feedback_ref.json"):
		ref = JSON.parse_string(FileAccess.get_file_as_string("res://content/feedback_ref.json"))
	else:
		err("нет content/feedback_ref.json — запусти tools/sync_content.py")
		return
	var lang0 := Loc.code
	Loc.code = "ru"
	SaveGame.tutorial_skipped = true
	Nav.go("hub")
	await _frames(2)
	await _fb_send(Nav.current.get_node("Flag"), 1, "Проверка: карточка съехала", ref, "general_hub")
	var scr: Node = await _open_job("flat:0")
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	var wrong := -1
	for i in scr.job["diagnosis"].size():
		if str(scr.job["diagnosis"][i]["text"]).begins_with("Погнут обод"):
			wrong = i
	scr.choose_diagnosis(wrong)
	await _frames(2)
	if not scr._dispute_btn.visible:
		err("«Я НЕ СОГЛАСЕН» не появилась после неверного диагноза")
	await _fb_send(scr._dispute_btn, 0, "Мой вариант", ref, "dispute_diagnosis")
	if scr.mistakes != int(ref["dispute_diagnosis"]["_mistakes_after"]):
		err("«Я не согласен»: ошибка не списана (%d)" % scr.mistakes)
	if scr._dispute_btn.visible:
		err("«Я НЕ СОГЛАСЕН» осталась после отправки")
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	scr = Nav.current
	scr.select_tool("hands")
	scr.part_clicked("brake")
	await _frames(2)
	await _fb_send(scr._dispute_btn, 2, "", ref, "dispute_repair")
	scr.select_tool("pump")
	scr.part_clicked("valve")
	await _frames(2)
	await _fb_send(scr._dispute_btn, 1, "x", ref, "dispute_repair_tool")
	Loc.code = "en"
	Nav.go("garage")
	await _frames(2)
	await _fb_send(Nav.current.get_node("Flag"), 3, "Garage note", ref, "general_garage_en")
	Loc.code = lang0


func _fb_send(opener: Control, reason: int, comment: String, ref: Dictionary, case: String) -> void:
	var n0: int = Feedback.captured.size()
	await _press(opener, false)
	await _frames(2)
	var dlg: FeedbackDialog = Nav.feedback
	if dlg == null:
		err("замечание %s: окно не открылось" % case)
		return
	await _press(dlg.get_node("Reason_%d" % reason), false)
	dlg.text.text = comment
	await _press(dlg.get_node("Send"), false)
	await _frames(2)
	if Feedback.captured.size() != n0 + 1:
		err("замечание %s: запрос не собран" % case)
		return
	var got: Dictionary = Feedback.captured[-1]
	var want: Dictionary = ref.get(case, {})
	for k: String in want:
		if k.begins_with("_"):
			continue
		if str(got.get(k, "<нет>")) != str(want[k]):
			err("замечание %s: поле %s = «%s», в game.py «%s»" % [case, k, got.get(k, "<нет>"), want[k]])
	for k: String in ["time", "uid", "platform"]:
		if str(got.get(k, "")) == "":
			err("замечание %s: пустое поле %s" % [case, k])
	if not str(got.get("platform", "")).begins_with("godot-"):
		err("замечание %s: platform «%s»" % [case, got.get("platform")])


## F1 — справка; полное окно настроек: все вкладки и пункты доступности.
func _flow_help_settings() -> void:
	Nav.go("hub")
	await _frames(2)
	await _key(KEY_F1)
	if Nav.help == null:
		err("F1 не открыла справку")
	await _frames(2)
	await _key(KEY_ESCAPE)
	if Nav.help != null or Nav.current_name != "hub":
		err("Esc не закрыл справку (или ушёл с экрана)")
	await _press(Nav.current.get_node("Gear"), false)
	await _frames(2)
	if Nav.settings == null:
		err("шестерёнка не открыла настройки")
		return
	for tb: String in SettingsDialog.TABS:
		await _press(Nav.settings.get_node("Tab_" + tb), false)
		await _frames(2)
		if SettingsDialog.tab != tb:
			err("настройки: вкладка %s не открылась" % tb)
	await _press(Nav.settings.get_node("Tab_access"), false)
	await _frames(1)
	for k: String in SettingsDialog.ACCESS_ROWS:
		var before: Variant = Settings.a11y.get(k)
		await _press(Nav.settings.get_node("Acc_" + k), true)
		await _frames(1)
		if k not in ["quiet", "barty"] and Settings.a11y.get(k) == before:
			err("настройки: «%s» не переключается" % k)
	for k: String in SettingsDialog.ACCESS_ROWS:                  # вернуть как было
		if k == "rate":
			Settings.a11y["rate"] = 0
		elif k == "text":
			Settings.a11y["text"] = 0
		else:
			Settings.a11y[k] = k == "barty"
	Settings.a11y["quiet_set"] = false
	Settings.changed.emit("text")
	await _press(Nav.settings.get_node("Tab_sound"), false)
	await _frames(1)
	var sl: VolSlider = Nav.settings.get_node("Vol_music")
	var v0: float = Settings.vol["music"]
	sl.grab_focus()
	await _key(KEY_RIGHT)
	if is_equal_approx(float(Settings.vol["music"]), v0) and v0 < 1.0:
		err("настройки: ползунок музыки не двигается с клавиатуры")
	Settings.vol["music"] = v0
	await _press(Nav.settings.get_node("Tab_game"), false)
	await _press(Nav.settings.get_node("Reset"), false)
	await _press(Nav.settings.get_node("ResetNo"), false)
	await _press(Nav.settings.get_node("Done"), false)
	await _frames(2)
	if Nav.settings != null:
		err("«ГОТОВО» не закрыл настройки")


# ======================= срез 4: Гильдия и экзамен =======================

func _gref() -> Dictionary:
	if not FileAccess.file_exists("res://content/guild_ref.json"):
		err("нет content/guild_ref.json — запусти tools/sync_content.py")
		return {}
	return JSON.parse_string(FileAccess.get_file_as_string("res://content/guild_ref.json"))


func _open_tech(jid: String, exam: bool = false) -> Node:
	Nav.go("tech", {"job": jid, "exam": exam})
	await _frames(2)
	return Nav.current


static func _tsig(st: Dictionary) -> Array:
	return [st["id"], st["tool"], st.get("part", ""), st.get("after", []), bool(st.get("safety", false)),
		st.get("spec") is Dictionary, (st["mini"] as Dictionary).get("kind", "") if st.get("mini") is Dictionary else ""]


## Операция обработчиками: инструмент → карточка; спека — верный вариант (мануал прочитан), мини — решена.
func _tech_do(scr: Node, sid: String) -> void:
	var st: Dictionary = scr.step_by_id(sid)
	scr.select_tool(st["tool"])
	scr.op_clicked(sid)
	if scr.spec_dlg:
		var opts: Array = st["spec"]["options"]
		for i in opts.size():
			if opts[i][1]:
				scr.choose_spec(i)
	if scr.mini:
		_solve_mini(scr.mini)
	await _frames(1)


func _view_all_manual(scr: Node) -> void:
	var pages: Array = scr.job.get("manual", [])
	for p: String in (pages if not pages.is_empty() else Content.manual.keys()):
		scr.manual_viewed[p] = true


func _finish_tech(scr: Node) -> void:
	scr._test_pressed()
	scr.ride.t0 = scr.ride.t - scr.ride.secs() - 0.01
	await _frames(2)
	scr._test_pressed()
	await _frames(2)


## Доступ в Гильдию: до 5 ремонтов кнопка серая и не пускает, после — открывает.
func _flow_guild_access() -> void:
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	for j: Dictionary in Content.jobs.slice(0, 4):
		SaveGame.done[j["id"]] = true
	Nav.go("hub")
	await _frames(2)
	var gb: GameButton = Nav.current.get_node("Guild")
	if gb.enabled:
		err("Гильдия: кнопка доступна после 4 ремонтов")
	await _press(gb, false)
	await _frames(2)
	if Nav.current_name != "hub" or not Nav.toast.text.contains("Гильдия Колёсников примет тебя"):
		err("Гильдия до 5 ремонтов: нет объяснения или пустили")
	SaveGame.done[Content.jobs[4]["id"]] = true
	Nav.go("hub")
	await _frames(2)
	await _press(Nav.current.get_node("Guild"), false)
	await _frames(2)
	if Nav.current_name != "guild" or Nav.current._cards.size() != 6 or Nav.current.get_node_or_null("Exam") != null:
		err("Гильдия после 5 ремонтов: нет 6 заданий (или экзамен раньше зачётов)")


## Бот: все 6 про-заданий в порядке данных и в «другом допустимом» порядке, эталон шагов и провалов — из game.py.
func _bot_guild() -> Array:
	var ref := _gref()
	if ref.is_empty():
		return [0, 0]
	var ok := 0
	var fails := 0
	for job: Dictionary in Content.tech_jobs:
		var jid: String = job["id"]
		var want: Dictionary = ref["jobs"].get(jid, {})
		for pass_i in 2:
			var scr: Node = await _open_tech(jid)
			if pass_i == 0:
				var mine: Array = []
				for st: Dictionary in scr.job["steps"]:
					mine.append(_tsig(st))
				if JSON.stringify(mine) != JSON.stringify(want.get("steps", [])):
					err("Гильдия %s: шаги не как в game.py" % jid)
			_view_all_manual(scr)
			var order: Array = []
			if pass_i == 0:
				for st: Dictionary in scr.job["steps"]:
					order.append(st["id"])
			else:
				order = want.get("alt_order", [])
			for sid: String in order:
				await _tech_do(scr, sid)
				if not scr.done_steps.has(sid) or scr.mistakes != 0:
					err("Гильдия %s (%s): операция %s не выполнена" % [jid, "порядок данных" if pass_i == 0 else "другой порядок", sid])
					break
			if scr.phase != "test":
				err("Гильдия %s: после операций нет проверки под нагрузкой" % jid)
				continue
			if pass_i == 1:
				continue
			await _finish_tech(scr)
			if Nav.current_name != "result" or not SaveGame.is_done(jid) or Nav.current._btn.label != "В ГИЛЬДИЮ":
				err("Гильдия %s: нет итога «В ГИЛЬДИЮ» или прогресс не записан" % jid)
				continue
			if int(Nav.current.stars) != int(want.get("stars", 3)):
				err("Гильдия %s: звёзд %d, в game.py %s" % [jid, Nav.current.stars, want.get("stars")])
			ok += 1
		# нарушение after (без шагов безопасности): операция не выполняется, ошибка «Рано! Сначала: …»
		var scr2: Node = await _open_tech(jid)
		for st: Dictionary in scr2.job["steps"]:
			var after: Array = st["after"]
			if after.is_empty() or after.any(func(a: String) -> bool: return scr2.step_by_id(a)["safety"]):
				continue
			scr2.select_tool(st["tool"])
			scr2.op_clicked(st["id"])
			if scr2.done_steps.has(st["id"]) or scr2.mistakes != 1 or not Nav.toast.text.begins_with("Рано! Сначала: "):
				err("Гильдия %s: нарушение порядка (%s) не остановлено" % [jid, st["id"]])
			break
		# спеки: без мануала — подсказка, неверное значение — ошибка, верное — шаг
		for st: Dictionary in job["steps"]:
			if not st.get("spec") is Dictionary:
				continue
			var s3: Node = await _open_tech(jid)
			_view_all_manual(s3)
			for o: Dictionary in s3.job["steps"]:              # всё, что раньше этого шага по порядку данных
				if o["id"] == st["id"]:
					break
				await _tech_do(s3, o["id"])
			s3.manual_viewed.clear()
			s3.select_tool(st["tool"])
			s3.op_clicked(st["id"])
			if s3.spec_dlg == null:
				err("Гильдия %s: спека %s не открылась" % [jid, st["id"]])
				continue
			var opts: Array = s3.spec_dlg.step["spec"]["options"]
			var right := -1
			var wrong := -1
			for i in opts.size():
				if opts[i][1]:
					right = i
				elif wrong < 0:
					wrong = i
			s3.choose_spec(right)
			if s3.done_steps.has(st["id"]) or not Nav.toast.text.begins_with("Сначала открой мануал"):
				err("Гильдия %s: спека %s принята без мануала" % [jid, st["id"]])
			s3.manual_viewed[st["spec"]["manual"]] = true
			var m0: int = s3.mistakes
			s3.choose_spec(wrong)
			if s3.mistakes != m0 + 1 or s3.done_steps.has(st["id"]):
				err("Гильдия %s: неверное значение спеки %s не засчитано ошибкой" % [jid, st["id"]])
			s3.choose_spec(right)
			if not s3.done_steps.has(st["id"]):
				err("Гильдия %s: верное значение спеки %s не принято" % [jid, st["id"]])
	# провал по каждому шагу безопасности: экран failed с разбором как в game.py, «ЗАНОВО»
	for key: String in ref.get("fails", {}):
		var jid := key.get_slice(":", 0)
		var sid := key.get_slice(":", 1)
		var scr: Node = await _open_tech(jid)
		var st: Dictionary = scr.step_by_id(sid)
		scr.select_tool(st["tool"])
		scr.op_clicked(sid)
		await _frames(2)
		if Nav.current_name != "failed" or Nav.current.msg != ref["fails"][key]["msg"]:
			err("провал %s: нет экрана failed или разбор не как в game.py" % key)
			continue
		await _press(Nav.current.get_node("Retry"), false)
		await _frames(2)
		if Nav.current_name != "tech" or Nav.current.job["id"] != jid or not Nav.current.done_steps.is_empty():
			err("провал %s: «ЗАНОВО» не начал задание заново" % key)
		fails += 1
	return [ok, fails]


## Экзамен: сдача (exam_passed, экран exam_result), провал по лимиту ошибок, пересдача — новым билетом.
func _flow_exam() -> void:
	Nav.go("guild")
	await _frames(2)
	if Nav.current.get_node_or_null("Exam") == null:
		err("экзамен: после всех зачётов нет кнопки")
		return
	await _press(Nav.current.get_node("Exam"), false)
	await _frames(2)
	var scr: Node = Nav.current
	if Nav.current_name != "tech" or not scr.exam or scr.get_node_or_null("StepSkip") != null:
		err("экзамен: не открылся билет (или есть «пропустить»)")
		return
	var m := 0
	for st: Dictionary in scr.job["steps"]:                 # лимит: 4-я ошибка — провал
		if st["after"].is_empty():
			for k in 4:
				var wrong_tool := "lube" if st["tool"] != "lube" else "hands"
				scr.select_tool(wrong_tool)
				scr.op_clicked(st["id"])
				await _frames(1)
				m += 1
				if Nav.current_name != "tech":
					break
			break
	if Nav.current_name != "failed" or not Nav.current.exam or not Nav.current.msg.begins_with("Лимит ошибок экзамена"):
		err("экзамен: 4 ошибки не провалили экзамен (%s)" % Nav.current_name)
		return
	if not Nav.toast.text.begins_with("Инструмент не тот.") or Nav.toast.text.contains("Нужен"):
		err("экзамен: в сообщении об ошибке есть подсказка")
	await _press(Nav.current.get_node("Retry"), false)
	await _frames(2)
	if Nav.current_name != "tech" or not Nav.current.exam:
		err("экзамен: «ПЕРЕСДАТЬ» не дал новый билет")
		return
	scr = Nav.current
	_view_all_manual(scr)
	for st: Dictionary in scr.job["steps"]:
		await _tech_do(scr, st["id"])
	await _finish_tech(scr)
	if Nav.current_name != "exam_result" or not SaveGame.exam_passed:
		err("экзамен: сдача не записала exam_passed / нет exam_result")
		return
	await _press(Nav.current.get_node("ToGuild"), false)
	await _frames(2)
	if Nav.current_name != "guild" or not str(Nav.current.rank()).begins_with("Сертифицированный"):
		err("Гильдия после экзамена: нет звания техника")


## Про-задание или экзамен событиями: мышью (клики) или клавиатурой (фокус + Enter), мануал — через окно.
func _flow_tech_events(jid: String, exam: bool, keyboard: bool) -> void:
	var how := ("клавиатура " if keyboard else "мышь ") + ("экзамен" if exam else jid)
	if exam:
		Nav.go("guild")
		await _frames(2)
		await _press(Nav.current.get_node("Exam"), keyboard)
	else:
		Nav.go("guild")
		await _frames(2)
		await _press(Nav.current.get_node("Tech_" + jid), keyboard)
	await _frames(2)
	var scr: Node = Nav.current
	if Nav.current_name != "tech":
		err("%s: задание не открылось" % how)
		return
	await _press(scr.get_node("Manual"), keyboard)              # мануал: все страницы задания
	await _frames(1)
	if scr.manual_dlg == null:
		err("%s: мануал не открылся" % how)
		return
	for p: String in scr.manual_dlg.pages:
		await _press(scr.manual_dlg.get_node("Page_" + p), keyboard)
	await _press(scr.manual_dlg.get_node("Close"), keyboard)
	await _frames(1)
	for st: Dictionary in scr.job["steps"]:
		await _press(scr.tools.tiles[st["tool"]], keyboard)
		await _press(scr.get_node("Op_" + st["id"]), keyboard)
		await _frames(1)
		if scr.spec_dlg:
			var opts: Array = st["spec"]["options"]
			for i in opts.size():
				if opts[i][1]:
					await _press(scr.spec_dlg.get_node("Opt_%d" % i), keyboard)
		if scr.mini:
			await _mini_events(scr.mini, keyboard, how, jid)
		await _frames(1)
		if not scr.done_steps.has(st["id"]) or scr.mistakes != 0:
			err("%s: операция %s не выполнена (ошибок %d)" % [how, st["id"], scr.mistakes])
			return
	await _press(scr.get_node("TestDrive"), keyboard)
	scr.ride.t0 = scr.ride.t - scr.ride.secs() - 0.01
	await _frames(2)
	await _press(scr.get_node("TestDrive"), keyboard)
	await _frames(2)
	var want := "exam_result" if exam else "result"
	if Nav.current_name != want:
		err("%s: нет экрана %s (%s)" % [how, want, Nav.current_name])
		return
	await _press(Nav.current.get_node("ToGuild" if exam else "ToHub"), keyboard)
	await _frames(2)
	if Nav.current_name != "guild":
		err("%s: не вернулись в Гильдию" % how)


## Замечание из Гильдии: шаг — «сделано: …», как в game.py.
func _flow_guild_feedback() -> void:
	var ref: Dictionary = _gref().get("feedback", {}).get("dispute_tech", {})
	if ref.is_empty():
		err("нет эталона замечания из Гильдии")
		return
	var lang0 := Loc.code
	Loc.code = "ru"
	var scr: Node = await _open_tech("t_battery")
	_view_all_manual(scr)
	await _tech_do(scr, ref["_after_step"])
	scr.select_tool("lube")
	scr.op_clicked(ref["_wrong_on"])
	await _frames(2)
	if not scr._dispute_btn.visible:
		err("Гильдия: нет «Я НЕ СОГЛАСЕН» после ошибки")
	await _fb_send(scr._dispute_btn, 1, "Гильдия", {"dispute_tech": ref}, "dispute_tech")
	if scr.mistakes != int(ref["_mistakes_after"]):
		err("Гильдия: после замечания ошибок %d, в game.py %d" % [scr.mistakes, ref["_mistakes_after"]])
	Loc.code = lang0


# ======================= Кабинет посадки =======================

func _sref() -> Dictionary:
	if not FileAccess.file_exists("res://content/seat_ref.json"):
		err("нет content/seat_ref.json — запусти tools/sync_content.py")
		return {}
	return JSON.parse_string(FileAccess.get_file_as_string("res://content/seat_ref.json"))


static func _same(a: Variant, b: Variant) -> bool:
	if (a is float or a is int) and (b is float or b is int):
		return absf(float(a) - float(b)) < 1e-6
	if a is bool or b is bool:
		return bool(a) == bool(b)
	if a is Array and b is Array:
		if a.size() != b.size():
			return false
		for i in a.size():
			if not _same(a[i], b[i]):
				return false
		return true
	if a is Dictionary and b is Dictionary:
		if a.size() != b.size():
			return false
		for k: Variant in a:
			var kb: Variant = k if b.has(k) else str(k)          # ключи-числа в JSON — строки
			if not b.has(kb) or not _same(a[k], b[kb]):
				return false
		return true
	return str(a) == str(b)


## Правила посадки против game.py: каждый случай на сетке ползунков, вид сбоку особых клиентов, строка мерок,
## поза уроков и вопросов (кадры перехода 0…1). Возврат: [случаев, строк сетки, кадров позы].
func _seat_logic() -> Array:
	var ref := _sref()
	if ref.is_empty():
		return [0, 0, 0]
	var lang0 := Loc.code
	Loc.code = "ru"
	var n_rows := 0
	var by_id := {}
	for c: Dictionary in SeatLogic.cases():
		by_id[c["id"]] = c
	if by_id.size() != ref["cases"].size():
		err("посадка: случаев %d, в game.py %d" % [by_id.size(), ref["cases"].size()])
	if not _same(SeatLogic.sliders(), ref["sliders"]):
		err("посадка: ползунки не как SEAT_SLIDERS")
	Nav.go("seating")
	await _frames(1)
	var scr: Node = Nav.current
	for cid: String in ref["cases"]:
		var rc: Dictionary = ref["cases"][cid]
		var c: Dictionary = by_id.get(cid, {})
		if c.is_empty():
			err("посадка: нет случая " + cid)
			continue
		scr.load_case(SeatLogic.cases().find(c))
		if not _same(scr.slider_keys(), rc["keys"]):
			err("посадка %s: ползунки %s, в game.py %s" % [cid, scr.slider_keys(), rc["keys"]])
		if SeatLogic.measure_text(c) != rc["measure"]:
			err("посадка %s: мерки «%s», в game.py «%s»" % [cid, SeatLogic.measure_text(c), rc["measure"]])
		for row: Dictionary in rc["rows"]:
			n_rows += 1
			var got: Array = SeatLogic.seat_eval(c, row["cfg"])
			if not _same(got[0], row["checks"]):
				err("посадка %s %s: проверки %s, в game.py %s" % [cid, row["cfg"], got[0], row["checks"]])
			if not _same(got[1], row["pose"]):
				err("посадка %s %s: поза %s, в game.py %s" % [cid, row["cfg"], got[1], row["pose"]])
		if rc["side"] is Dictionary:
			var scfg := SeatLogic.side_cfg(c)
			if not _same(scfg, rc["side"]["cfg"]) or not _same(SeatLogic.eval_side(c, scfg)[1], rc["side"]["pose"]):
				err("посадка %s: вид сбоку не как в game.py" % cid)
	var n_fr := 0
	for d: Dictionary in ref["demo"]:
		var src: Array = Content.seating["lessons"] if d["src"] == "lesson" else Content.seating["quiz"]
		var spec: Dictionary = src[int(d["i"])]["pose"]
		for tt: String in d["frames"]:
			n_fr += 1
			var fr: Dictionary = d["frames"][tt]
			var got := SeatLogic.fix_pose(spec, float(tt))
			if not (_same(got[0]["seat_h"], fr["seat_h"]) and got[0]["kind"] == fr["kind"] and _same(got[1], fr["cfg"])
					and _same(got[2], fr["pose"])):
				err("посадка: %s %d, кадр %s — %s, в game.py %s" % [d["src"], d["i"], tt, [got[0]["seat_h"], got[1], got[2]], fr])
	Loc.code = lang0
	return [ref["cases"].size(), n_rows, n_fr]


## Положение ползунков, при котором все проверки случая верны (перебор по одному ползунку, пока есть улучшение).
func _seat_solution(c: Dictionary, keys: Array, cfg0: Dictionary) -> Dictionary:
	var cfg := cfg0.duplicate()
	var score := func(x: Dictionary) -> int:
		var n := 0
		for ch: Array in SeatLogic.seat_eval(c, x)[0]:
			n += 1 if ch[1] else 0
		return n
	var total: int = SeatLogic.seat_eval(c, cfg)[0].size()
	for round_i in 6:
		for k: String in keys:
			var sl: Array = SeatLogic.sliders()[k]
			var best: int = score.call(cfg)
			var best_v: int = cfg[k]
			for v in range(int(sl[2]), int(sl[3]) + 1):
				var x := cfg.duplicate()
				x[k] = v
				var s: int = score.call(x)
				if s > best:
					best = s
					best_v = v
			cfg[k] = best_v
		if score.call(cfg) == total:
			break
	return cfg


func _mouse_ev(pos: Vector2, button: int) -> void:
	if button < 0:
		var m := InputEventMouseMotion.new()
		m.position = pos
		m.global_position = pos
		m.button_mask = MOUSE_BUTTON_MASK_LEFT
		get_viewport().push_input(m, true)
	else:
		var e := InputEventMouseButton.new()
		e.button_index = MOUSE_BUTTON_LEFT
		e.pressed = button == 1
		e.position = pos
		e.global_position = pos
		get_viewport().push_input(e, true)
	await get_tree().process_frame


## Ползунок мышью: щелчок по дорожке (click) или перетаскивание ручки с уходом мыши с дорожки (drag).
func _seat_mouse_slider(scr: Node, key: String, v: int, how: String) -> void:
	var tr: Rect2 = scr.slider_rect(scr.slider_keys().find(key))
	var sl: Array = SeatLogic.sliders()[key]
	var x := tr.position.x + tr.size.x * (v - float(sl[2])) / (float(sl[3]) - float(sl[2]))
	var y := tr.get_center().y
	if how == "click":
		await _click(Vector2(x, y))
		return
	var cur: float = tr.position.x + tr.size.x * (float(scr.cfg[key]) - float(sl[2])) / (float(sl[3]) - float(sl[2]))
	await _mouse_ev(Vector2(cur, y), 1)
	await _mouse_ev(Vector2((cur + x) / 2, y + 6), -1)
	await _mouse_ev(Vector2(x, y + 12), -1)
	await _mouse_ev(Vector2(x, y + 12), 0)


## Кабинет посадки событиями ввода: доступ из мастерской, уроки, все примерки (две — клавиатурой, по одной — щелчками
## и перетаскиванием, остальные — напрямую), зачёт (провал и сдача, мышью и клавиатурой), сохранение, замечание, Esc.
func _flow_seating() -> String:
	var M: Dictionary = Content.seating["mentor"]
	SaveGame.reset()
	Nav.go("hub")
	await _frames(2)
	var hb: GameButton = Nav.current.get_node("Seating")
	if hb.enabled:
		err("посадка: кнопка доступна до первого ремонта")
	await _press(hb, false)
	await _frames(1)
	if Nav.current_name != "hub" or not _toast_is(UI.CYAN, "откроется после первого ремонта"):
		err("посадка до первого ремонта: нет объяснения или пустили")
	SaveGame.done["flat"] = true
	Nav.go("hub")
	await _frames(2)
	await _press(Nav.current.get_node("Seating"), true)
	await _frames(2)
	if Nav.current_name != "seating":
		err("посадка: кнопка в мастерской не открыла кабинет")
		return ""
	var scr: Node = Nav.current
	if scr.tab != "lessons" or scr.say != M["intro"]:
		err("посадка: вход не на «Уроки» или не та реплика Мортимера")
	# уроки: все карточки, «показать норму» — у уроков с ошибочной позой
	var n_les: int = Content.seating["lessons"].size()
	var n_toggle := 0
	for i in n_les:
		await _press(scr.get_node("Dyn/Lesson_%d" % i), i % 2 == 1)
		await _frames(1)
		if scr.lesson != i or scr.say != M["lesson"][i % M["lesson"].size()]:
			err("посадка: урок %d не открылся (или не та реплика)" % (i + 1))
		var tg: Node = scr.get_node_or_null("Dyn/Toggle")
		var lp: Dictionary = Content.seating["lessons"][i].get("pose", {})
		var want_tg := false
		for k: String in ["p", "slide", "deep", "knee_up", "dangle", "front"]:
			want_tg = want_tg or lp.has(k)
		if (tg != null) != want_tg:
			err("посадка: урок %d — кнопка «показать норму» %s" % [i + 1, "лишняя" if tg else "пропала"])
		if tg:
			await _press(tg, i % 2 == 0)
			await _frames(1)
			if not scr.demo_good or (scr.get_node("Dyn/Toggle") as GameButton).label != "ПОЗА: НОРМА ✔":
				err("посадка: урок %d — норма не показалась" % (i + 1))
			n_toggle += 1
	# примерка
	await _press(scr.get_node("Tab_fit"), false)
	await _frames(1)
	if scr.tab != "fit" or scr.say != M["fit"]:
		err("посадка: вкладка «Примерка» не открылась")
	var n_cases: int = SeatLogic.cases().size()
	var how := ["kb", "mouse", "kb", "drag"]
	var n_views := 0
	for i in n_cases:
		var c: Dictionary = SeatLogic.cases()[i]
		await _press(scr.get_node("Dyn/Case_%d" % i), false)
		await _frames(1)
		if scr.case_i != i or scr.solved:
			err("посадка: клиент %s не выбрался" % c["id"])
			continue
		if c.get("view"):
			var v0: String = scr.view
			await _press(scr.get_node("Dyn/Toggle"), true)
			await _frames(1)
			if scr.view != "side" or scr.say != M["side_ok"]:
				err("посадка %s: вид сбоку не включился" % c["id"])
			await _press(scr.get_node("Dyn/Toggle"), false)
			await _frames(1)
			if scr.view != v0 or scr.say != M["view_" + v0]:
				err("посадка %s: вид %s не вернулся" % [c["id"], v0])
			n_views += 1
		# сначала «Готово» как есть — стартовая посадка неверна
		var bad0: Array = []
		for ch: Array in SeatLogic.seat_eval(c, scr.cfg)[0]:
			if not ch[1]:
				bad0.append(ch[2])
		await _press(scr.get_node("Dyn/Check"), false)
		await _frames(1)
		if bad0.is_empty() or scr.solved or scr.fails != 1 or scr.say != M["fail"] \
				or Nav.toast.text != "Ещё не так: " + str(bad0[0]) or Nav.toast.color != UI.BAD:
			err("посадка %s: неверная посадка принята (или нет «Ещё не так»)" % c["id"])
		var keys: Array = scr.slider_keys()
		var sol := _seat_solution(c, keys, scr.cfg)
		var mode: String = how[i] if i < how.size() else "direct"
		for k: String in keys:
			var v: int = sol[k]
			if mode == "kb":
				(scr.sliders[k] as Control).grab_focus()
				await _frames(1)
				var d: int = v - int(scr.cfg[k])
				for s in absi(d):
					await _key(KEY_RIGHT if d > 0 else KEY_LEFT)
			elif mode == "mouse" or mode == "drag":
				await _seat_mouse_slider(scr, k, v, "click" if mode == "mouse" else "drag")
			else:
				scr.set_value(k, v)
			if int(scr.cfg[k]) != v:
				err("посадка %s: ползунок %s (%s) — %s, нужно %d" % [c["id"], k, mode, scr.cfg[k], v])
		if scr.drag != "":
			err("посадка %s: перетаскивание не закончилось" % c["id"])
		var ok_all := true
		for ch: Array in SeatLogic.seat_eval(c, scr.cfg)[0]:
			ok_all = ok_all and ch[1]
		if not ok_all:
			err("посадка %s: перебор не нашёл верной посадки (%s)" % [c["id"], scr.cfg])
			continue
		await _press(scr.get_node("Dyn/Check"), mode == "kb")
		await _frames(1)
		if not scr.solved or not SaveGame.seat_done.has(c["id"]) or scr.say != M["solved"] or not _toast_is(UI.GOOD):
			err("посадка %s: верная посадка не засчитана" % c["id"])
		var cfg_solved: Dictionary = scr.cfg.duplicate()
		await _click(_center(scr.sliders[keys[0]]) - Vector2(140, 0))      # после «готово» ползунки стоят
		(scr.sliders[keys[0]] as Control).grab_focus()
		await _frames(1)
		await _key(KEY_LEFT)
		if not _same(scr.cfg, cfg_solved):
			err("посадка %s: ползунок сдвинулся после «готово»" % c["id"])
	if SaveGame.seat_done.size() != n_cases:
		err("посадка: засчитано %d примерок из %d" % [SaveGame.seat_done.size(), n_cases])
	if (SaveGame.to_dict().get("seat_done", []) as Array).size() != n_cases:
		err("посадка: примерки не попали в сохранение")
	await _press(scr.get_node("Dyn/Check"), false)      # «следующий клиент» после последнего — к первому
	await _frames(1)
	if scr.case_i != 0 or scr.solved:
		err("посадка: «Следующий клиент» после последнего не вернул к первому")
	# зачёт: сначала провал (все ответы неверные, мышью), потом сдача (через один — клавиатурой)
	await _press(scr.get_node("Tab_quiz"), true)
	await _frames(1)
	if scr.tab != "quiz" or scr.say != M["quiz"]:
		err("посадка: вкладка «Проверь себя» не открылась")
	var nq: int = scr.quiz.size()
	for q in nq:
		var opts: Array = scr.quiz[q]["options"]
		var wi := -1
		for j in opts.size():
			if not opts[j][1]:
				wi = j
				break
		await _press(scr.get_node("Dyn/Opt_%d" % wi), false)
		await _frames(1)
		if scr.picked != wi or scr.say != M["wrong"] or scr.score != 0:
			err("посадка: вопрос %d — неверный ответ не отмечен" % (q + 1))
		if SeatLogic.fix_kind(scr.quiz[q]) != "" and not Settings.calm() and scr.fix_t() != 0.0:
			err("посадка: вопрос %d — переход к норме начался без паузы после ошибки" % (q + 1))
		if (scr.get_node("Dyn/Opt_%d" % wi) as GameButton).color != UI.BAD:
			err("посадка: вопрос %d — выбранный неверный ответ не красный" % (q + 1))
		await _press(scr.get_node("Dyn/Next"), false)
		await _frames(1)
	if not scr.quiz_done or scr.score != 0 or SaveGame.seat_quiz_ok or scr.say != M["nopass"]:
		err("посадка: провал зачёта (0 из %d) не так" % nq)
	await _press(scr.get_node("Dyn/Again"), true)
	await _frames(1)
	if scr.quiz_done or scr.quiz_i != 0 or scr.score != 0:
		err("посадка: «Пройти ещё раз» не сбросил зачёт")
	for q in nq:
		var opts: Array = scr.quiz[q]["options"]
		var ri := -1
		for j in opts.size():
			if opts[j][1]:
				ri = j
		var kb := q % 2 == 0
		await _press(scr.get_node("Dyn/Opt_%d" % ri), kb)
		await _frames(1)
		if scr.picked != ri or scr.say != M["right"] or scr.score != q + 1:
			err("посадка: вопрос %d — верный ответ не засчитан" % (q + 1))
		if SeatLogic.fix_kind(scr.quiz[q]) != "" and not Settings.calm() and absf(scr.fix_t0 - scr.t) > 0.1:
			err("посадка: вопрос %d — после верного ответа переход не сразу" % (q + 1))
		await _press(scr.get_node("Dyn/Next"), kb)
		await _frames(1)
	if not scr.quiz_done or scr.score != nq or not SaveGame.seat_quiz_ok or scr.say != M["pass"]:
		err("посадка: сдача зачёта (%d из %d) не так" % [scr.score, nq])
	if not bool(SaveGame.to_dict().get("seat_quiz_ok", false)):
		err("посадка: зачёт не попал в сохранение")
	scr.quiz_again()                           # переход к норме: середина — ровно на половине SEAT_FIX_DUR
	scr.quiz_pick(0)
	var dur: float = Content.consts["seat_fix"][0]
	scr.fix_t0 = scr.t - dur / 2.0
	if absf(scr.fix_t() - 0.5) > 1e-6:
		err("посадка: середина перехода — %f" % scr.fix_t())
	# замечание из кабинета: как game.py (флажок на «Примерке»), в сеть — ничего
	var ref := _sref()
	if ref.has("feedback"):
		var lang0 := Loc.code
		Loc.code = "ru"
		scr.set_tab("fit")
		await _frames(1)
		await _fb_send(scr.get_node("Flag"), 2, "Посадка", {"seat": ref["feedback"]}, "seat")
		Loc.code = lang0
	else:
		err("в seat_ref.json нет замечания")
	await _key(KEY_ESCAPE)                     # Esc — в мастерскую; на кнопке — «примерки 9/9 · зачёт ✔»
	await _frames(2)
	if Nav.current_name != "hub":
		err("посадка: Esc не вернул в мастерскую")
	else:
		var sb: GameButton = Nav.current.get_node("Seating")
		if not sb.sub.contains("%d/%d" % [n_cases, n_cases]) or not sb.sub.contains("зачёт ✔"):
			err("посадка: на кнопке мастерской «%s»" % sb.sub)
	return "уроки %d/%d (норма — у %d), примерки %d/%d (особые клиенты — вид сбоку и обратно: %d; клавиатурой, щелчками и перетаскиванием), зачёт (провал 0/%d и сдача %d/%d)" % [n_les, n_les, n_toggle, SaveGame.seat_done.size(), n_cases, n_views, nq, nq, nq]
