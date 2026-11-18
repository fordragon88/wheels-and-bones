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
	_finish("бот прошёл %d/%d вариантов (%d шагов, как в pygame); событиями мыши и клавиатуры — %s; вступление и «пропустить», гараж, вечеринка, титры, справка F1, настройки, замечания (%d запросов = game.py, в сеть — ничего); %d .gd, кадры поворота у всех 21 коляски, перевод: %d строк%s" % [bot[0], n_var, bot[1], ", ".join(ev_jobs), Feedback.captured.size(), n_gd, n_audit,
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
