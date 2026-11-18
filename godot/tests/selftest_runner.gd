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
	_finish("%d .gd, кадры поворота у всех 21 коляски, перевод: %d строк%s" % [n_gd, n_audit,
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
		Input.parse_input_event(e)
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
	if Nav.current.phase != "repair" or Nav.current.get_node_or_null("ToHub") == null:
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
