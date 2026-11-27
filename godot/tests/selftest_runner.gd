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
	# --- быстрый прогон одной части: -- --test --only speech|switch|pad (отладка; полная самопроверка — без него)
	var only_i := OS.get_cmdline_user_args().find("--only")
	if only_i >= 0:
		await _only(OS.get_cmdline_user_args()[only_i + 1])
		return
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
	var lang_sh := Loc.code
	var sh: Array = await _share_codes()
	await _flow_share_progress()
	var sh_line: String = await _flow_share_assign()
	_share_write_out()
	Loc.code = lang_sh
	var sp_res: Array = await _speech_ref()
	var kbo_line: String = await _kb_order_ref(["ru", "en"])
	var arrows_line: String = await _flow_arrows()
	var sw_line: String = await _flow_switch(["flat:0", "brake:0", "spokes:0"], ["truing"])
	var pad_line: String = await _flow_pad(["flat:0", "brake:0", "lift:0"], ["truing"])
	var ride_line: String = kbo_line + "; " + arrows_line + "; " + await _flow_tech_rides()
	ride_line += "; " + await _flow_brenna()
	ride_line += "; " + await _flow_martin()
	ride_line += "; " + await _flow_martin_live()
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
	var fx_line: String = await _fixes()
	fx_line += "; " + await _touch()
	fx_line += "; " + await _phone_check()
	fx_line += "; " + await _mute_check()
	fx_line += "; " + await _review_kb()
	fx_line += "; " + await _review_web()
	fx_line += "; " + await _review_port()
	# --- сценарий мышью: титул → мастерская → flat → осмотр → неверный → верный диагноз ---
	SaveGame.reset()
	await _flow_mouse()
	await _flow_keyboard()
	_finish("бот прошёл %d/%d вариантов (%d шагов, как в pygame); событиями мыши и клавиатуры — %s; вступление и «пропустить», гараж, вечеринка, титры, справка F1, настройки, замечания (%d запросов = game.py, в сеть — ничего); Гильдия: %d/6 про-заданий в двух порядках, %d провалов по безопасности = game.py, спеки, экзамен (сдача, лимит, пересдача), мышью и клавиатурой; Кабинет посадки: %d случаев × сетка (%d положений ползунков) = game.py, позы уроков и зачёта (%d кадров перехода) = game.py, %s, сохранение, замечание = game.py; Коды и ссылки: кодов game.py прочитано %d (P/J/R, те же данные), битых отвергнуто %d, ссылок и разборов = game.py %d, своих кодов и ссылок для check_share.py %d; прогресс: копировать → сбросить → вставить → тот же, «вернуть прежний»; %s; «продолжить / обычная игра»; итог в таблицу = game.py (в сеть — ничего); Озвучка: %d/%d сводок, подписей фокуса и фраз клавиш = game.py (RU/EN; известное — инструменты в порядке кучек: %d, кнопка звука: %d), в тестах голос не звучит; %s; %s; %s; %d .gd, кадры поворота у всех 21 коляски, перевод: %d строк%s" % [bot[0], n_var, bot[1], ", ".join(ev_jobs), Feedback.captured.size(), gbot[0], gbot[1], seat_n[0], seat_n[1], seat_n[2], seat_line, sh[0], sh[1], sh[2], share_out.size(), sh_line, sp_res[0], sp_res[1], speech_tools_known, speech_sound_known, sw_line, pad_line, ride_line, n_gd, n_audit,
		"" if _drawn > 0 else " (без окна _draw не вызывается — проверены строки данных и обработчиков)"] + "; " + fx_line,
		n_jobs, n_var, n_tech)


## Находки аудита 20.11 (tests/fixes_check.gd).
func _fixes() -> String:
	var fx: Node = (load("res://tests/fixes_check.gd") as GDScript).new()
	add_child(fx)
	var line: String = await fx.run(self)
	fx.queue_free()
	return line


## Внешняя проверка 26.11: клавиатура, окна, чтец экрана, ввод (tests/review_kb_check.gd).
func _review_kb() -> String:
	var rk: Node = (load("res://tests/review_kb_check.gd") as GDScript).new()
	add_child(rk)
	var line: String = await rk.run(self)
	rk.queue_free()
	return line


## Внешний обзор 26.11: браузер, сохранения, телефон, раскладка (tests/review_web_check.gd).
func _review_web() -> String:
	var rw: Node = (load("res://tests/review_web_check.gd") as GDScript).new()
	add_child(rw)
	var line: String = await rw.run(self)
	rw.queue_free()
	return line


## Перенос правок game.py по внешней проверке 26.11 (tests/review_port_check.gd).
func _review_port() -> String:
	var rp: Node = (load("res://tests/review_port_check.gd") as GDScript).new()
	add_child(rp)
	var line: String = await rp.run(self)
	rp.queue_free()
	return line


## Телефонный режим: цели для пальца не мельче 56, без пересечений; выключен — как было (tests/phone_check.gd).
func _phone_check() -> String:
	var pc: Node = (load("res://tests/phone_check.gd") as GDScript).new()
	add_child(pc)
	var line: String = await pc.run(self)
	pc.queue_free()
	return line


## Замер целей по всем состояниям kb_order_ref (--phone 0|1, --langs ru,en) → tests/out/phone_targets_<0|1>.txt;
## ref — эталон «выключен» tests/phone_off_ref.json.
## Кнопка звука: не на кнопках и тексте шапки, нажатие = M (phone_check.mute_check).
func _mute_check() -> String:
	var pc: Node = (load("res://tests/phone_check.gd") as GDScript).new()
	add_child(pc)
	var r: Array = await pc.mute_check(self)
	pc.queue_free()
	for b: String in r[1]:
		err(b)
	return "КНОПКА ЗВУКА: проверено %d (экраны × вкл/выкл, RU/EN, ПК и телефон), нарушений — %d" % [r[0], r[1].size()]


func _phone_measure(ref: bool) -> String:
	var args := OS.get_cmdline_user_args()
	var on := not ref
	var pi := args.find("--phone")
	if pi >= 0 and not ref:
		on = args[pi + 1] == "1"
	var langs: Array = ["ru"]
	var li := args.find("--langs")
	if li >= 0:
		langs = Array(args[li + 1].split(","))
	var refd: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://content/kb_order_ref.json"))
	var states: Array = refd["ru"].keys()
	var si := args.find("--states")
	if si >= 0:
		states = Array(args[si + 1].split(","))
	var pc: Node = (load("res://tests/phone_check.gd") as GDScript).new()
	add_child(pc)
	var d: Dictionary = await pc.measure(self, states, langs, on)
	var line: String = pc.summary(on, d)
	pc.write_out("phone_targets_%d.txt" % (1 if on else 0), line + "
" + "
".join(d["lines"]) + "
")
	if ref:
		var f := FileAccess.open("res://tests/phone_off_ref.json", FileAccess.WRITE)
		f.store_string(JSON.stringify(d["rects"], " ", false) + "
")
		f.close()
	pc.queue_free()
	return line


## Сенсорный экран: запас на промах пальцем как в game.py (tests/touch_check.gd).
func _touch() -> String:
	var tc: Node = (load("res://tests/touch_check.gd") as GDScript).new()
	add_child(tc)
	var line: String = await tc.run(self)
	tc.queue_free()
	return line


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
	var pad := {KEY_ENTER: JOY_BUTTON_A, KEY_ESCAPE: JOY_BUTTON_B, KEY_UP: JOY_BUTTON_DPAD_UP, KEY_DOWN: JOY_BUTTON_DPAD_DOWN,
		KEY_LEFT: JOY_BUTTON_DPAD_LEFT, KEY_RIGHT: JOY_BUTTON_DPAD_RIGHT}
	if ctl_mode == "pad" and pad.has(code) and not shift:      # геймпад: те же действия кнопками
		await _pad_btn(pad[code])
		return
	kb_presses += 1
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
		if sub.begins_with(".") or sub in ["content", "tools", "build"] or FileAccess.file_exists(dir.path_join(sub).path_join(".gdignore")):
			continue                              # build/ — копия проекта для браузерной сборки (build_web.py)
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
			m.value = ceili(float(m.cfg["lo"]))
			m.pump_done()
		"gap":
			m.gap_set(ceili(float(m.cfg["lo"])))
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
	if not str(Nav.current.get_node("Card_flat").accessibility_name).contains(Loc.t("Уже починено")):
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
	scr.mini.value = floori(float(scr.mini.cfg["hi"])) + 1
	scr.mini.pump_done()
	if scr.mistakes != m1 + 1 or scr.mini.value >= ceili(float(scr.mini.cfg["lo"])):
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
	if keyboard and ctl_mode == "switch":
		await _sw_press_on(c)
	elif keyboard and ctl_mode == "arrows":
		await _kb_press_on(c)
	elif keyboard:
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
		if i == 0 and spot != null and not ctl_mode in ["switch", "arrows"]:   # первый шаг — кружком на коляске, дальше — списком
			# (одна кнопка идёт по списку game.py — кружков на коляске в нём нет)
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
			var lo := ceili(float(m.cfg["lo"]))
			var hi := floori(float(m.cfg["hi"]))
			for _i in 80:
				if m.value >= lo and m.value <= hi:
					break
				await _press(m.get_node("Pump" if m.value < lo else "Release"), keyboard)
			await _press(m.get_node("Done"), keyboard)
		"gap":
			var tr: GapTrack = m.get_node("Track")
			var lo := ceili(float(m.cfg["lo"]))
			if keyboard and ctl_mode == "switch":
				await _sw_slider(tr, func() -> int: return m.value, lo)
			elif keyboard:
				await _kb_focus_on(tr)
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
	# размер пунктов уроков = выбор game.py (seat_lesson_fit.json), в том числе с «лёгким» шрифтом при 112–150 % (21.11)
	var fit: Dictionary = Content.seating.get("lesson_fit", {})
	if fit.is_empty():
		err("посадка: нет content/data/seat_lesson_fit.json (sync_content.py)")
	else:
		var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false)]
		var diff: Array = []
		Settings.lang = "en"
		Loc.code = "en"
		Settings.a11y["font"] = true
		for t in [1, 2, 3]:
			Settings.a11y["text"] = t
			UI.clear_font_cache()
			var want: Array = fit["sizes"]["en|%d|1" % t]
			for i in Content.seating["lessons"].size():
				var n_l: int = Content.seating["lessons"].size()
				@warning_ignore("integer_division")
				var y: float = 112.0 + ((n_l + 1) / 2) * 44 + 10 + 32
				var got: int = scr._lesson_psz(Content.seating["lessons"][i], y)
				if got != int(want[i]):
					diff.append("%d%% урок %d: %d, game.py %d" % [[100, 112, 125, 150][t], i + 1, got, int(want[i])])
		Settings.lang = keep[0]
		Loc.code = keep[1]
		Settings.a11y["text"] = keep[2]
		Settings.a11y["font"] = keep[3]
		UI.clear_font_cache()
		if not diff.is_empty():
			err("посадка: размер пунктов уроков с лёгким шрифтом не как в game.py: %s" % ", ".join(diff))
	# уроки: все карточки, «показать норму» — у уроков с ошибочной позой
	var n_les: int = Content.seating["lessons"].size()
	var n_toggle := 0
	var n_front := 0
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
		await _frames(1)
		var want_mode := "front" if lp.get("front") else "scene"
		if scr.fig.mode != want_mode or (lp.get("front") and scr.fig.front_corrected != scr.demo_good):
			err("посадка: урок %d — рисунок «%s», нужен «%s»" % [i + 1, scr.fig.mode, want_mode])
		elif lp.get("front"):
			n_front += 1
	# примерка
	await _press(scr.get_node("Tab_fit"), false)
	await _frames(1)
	if scr.tab != "fit" or scr.say != M["fit"]:
		err("посадка: вкладка «Примерка» не открылась")
	var n_cases: int = SeatLogic.cases().size()
	var how := {0: "kb", 1: "mouse", 3: "drag", 6: "kb", 7: "mouse", 8: "drag"}   # особые клиенты (6–8) — тоже вводом
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
			await _frames(1)
			if scr.fig.mode != ("front_fit" if v0 == "front" else "top"):
				err("посадка %s: рисунок вида %s — «%s»" % [c["id"], v0, scr.fig.mode])
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
		var mode: String = how.get(i, "direct")
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
		var fk := SeatLogic.fix_kind(scr.quiz[q])
		if fk in ["wedge", "pads"]:                # вид спереди: переход к норме — подкладка / упоры и выпрямление
			scr.fix_t0 = scr.t - 5.0
			await _frames(2)
			var f: SeatFigure = scr.fig
			var done_ok: bool = f.mode == "front" and (f.front_wedge == 1.0 and not f.front_pads if fk == "wedge"
				else f.front_corrected and f.front_pads and absf(f.front_obl - 0.12) < 1e-6)
			if not done_ok:
				err("посадка: вопрос %d (%s) — рисунок спереди не пришёл к норме" % [q + 1, fk])
			else:
				n_front += 1
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
	return "уроки %d/%d (норма — у %d), виды спереди: урок и вопросы зачёта — %d, примерки %d/%d (особые клиенты спереди/сверху и сбоку: %d — клавиатурой, щелчками и перетаскиванием, как и обычные), зачёт (провал 0/%d и сдача %d/%d)" % [n_les, n_les, n_toggle, n_front, SaveGame.seat_done.size(), n_cases, n_views, nq, nq, nq]


# ======================= Коды и ссылки =======================

const SHARE_OUT := "res://tests/out/share_godot.json"
var share_out: Array = []                  # коды и ссылки Godot — для tools/check_share.py (обратное направление)


func _shref() -> Dictionary:
	if not FileAccess.file_exists("res://content/share_ref.json"):
		err("нет content/share_ref.json — запусти tools/sync_content.py")
		return {}
	return JSON.parse_string(FileAccess.get_file_as_string("res://content/share_ref.json"))


## Коды game.py → Godot: каждый эталонный код читается и даёт те же данные, битые отвергаются; тексты итога, ссылки,
## разбор ссылок — как у game.py. Godot пишет свои коды и ссылки в tests/out для check_share.py.
## Возврат: [кодов прочитано, битых отвергнуто, ссылок совпало, своих выдано].
func _share_codes() -> Array:
	var ref := _shref()
	if ref.is_empty():
		return [0, 0, 0, 0]
	var lang0 := Loc.code
	Loc.code = "ru"
	var n_read := 0
	var n_links := 0
	for p: Dictionary in ref["progress"]:
		var got := Share.decode(p["code"])
		if got.size() != 2 or got[0] != "P" or not _same(got[1], p["data"]):
			err("код прогресса «%s» не прочитан как в game.py: %s" % [p["name"], got])
			continue
		n_read += 1
		if not _same(Share.progress_unpack(got[1]), p["unpack"]):
			err("код прогресса «%s»: распаковка %s, в game.py %s" % [p["name"], Share.progress_unpack(got[1]), p["unpack"]])
		share_out.append({"what": "code", "kind": "P", "code": Share.encode("P", p["data"]), "data": p["data"]})
	for row: Dictionary in ref["assign"]:
		var a := Share.assign_parse(row["params"])
		if row["assign"] == null:
			if not a.is_empty():
				err("задание %s: в game.py не принимается, у нас — %s" % [row["params"], a])
			continue
		if not _same(a, row["assign"]):
			err("задание %s: %s, в game.py %s" % [row["params"], a, row["assign"]])
			continue
		var got := Share.decode(row["code"])
		if got.size() != 2 or got[0] != "J" or not _same(got[1], row["data"]):
			err("код задания %s не прочитан как в game.py" % row["code"])
		else:
			n_read += 1
			var d: Dictionary = got[1]
			var fc := Share.assign_parse({"jobs": d.get("j"), "seat": d.get("s"), "from": d.get("f"), "title": d.get("ti")})
			if not _same(fc, row["from_code"]):
				err("задание из кода: %s, в game.py %s" % [fc, row["from_code"]])
		var link := Share.share_link(Share.assign_params(a))
		if link != row["link"]:
			err("ссылка-задание:\n    godot  %s\n    pygame %s" % [link, row["link"]])
		else:
			n_links += 1
		if not _same(Share.parse_link(link), row["link_back"]):
			err("разбор ссылки %s: %s, в game.py %s" % [link, Share.parse_link(link), row["link_back"]])
		var again := Share.assign_parse(Share.parse_link(link))      # та же ссылка заново — тот же номер задания
		if not _same(again, a):
			err("ссылка-задание: повторный разбор дал %s, было %s" % [again, a])
		if Share.assign_head(a["from"], a["title"]) != row["head"]:
			err("заголовок задания «%s», в game.py «%s»" % [Share.assign_head(a["from"], a["title"]), row["head"]])
		share_out.append({"what": "code", "kind": "J", "code": Share.assign_code(a), "data": row["data"]})
		share_out.append({"what": "link", "link": link, "params": row["link_back"],
			"assign": Share.assign_parse(Share.parse_link(link))})
	for r: Dictionary in ref["result"]:
		var got := Share.decode(r["code"])
		if got.size() != 2 or got[0] != "R" or not _same(got[1], r["data"]):
			err("код результата «%s» не прочитан как в game.py" % r["name"])
			continue
		n_read += 1
		var res := Share.result_unpack(got[1])
		if not _same(res, r["unpack"]):
			err("результат «%s»: %s, в game.py %s" % [r["name"], res, r["unpack"]])
		var st: Dictionary = r["assign"]
		if not _same(Share.result_pack(st), r["data"]):
			err("результат «%s»: данные кода %s, в game.py %s" % [r["name"], Share.result_pack(st), r["data"]])
		for lang: String in ["ru", "en"]:
			var want: Dictionary = r["texts"][lang]
			Loc.code = lang
			if Share.result_text(res, r["code"]) != want["text"]:
				err("итог текстом (%s, «%s»):\n    godot  %s\n    pygame %s" % [lang, r["name"], Share.result_text(res, r["code"]),
					want["text"]])
			if Share.result_summary(res["rows"]) != want["summary"] or Share.assign_head(res["from"], res["title"]) != want["head"]:
				err("итог (%s, «%s»): строка или заголовок не как в game.py" % [lang, r["name"]])
			for k: String in want["labels"]:
				if Share.item_label(k) != want["labels"][k]:
					err("подпись пункта %s (%s): «%s», в game.py «%s»" % [k, lang, Share.item_label(k), want["labels"][k]])
			Loc.code = "ru"
		share_out.append({"what": "code", "kind": "R", "code": Share.result_code(st), "data": r["data"]})
	for l: Dictionary in ref["links"]:
		var p := Share.parse_link(l["text"])
		var a := Share.assign_parse(p) if not p.is_empty() else {}
		if not _same(p, l["params"]) or (l["assign"] == null) != a.is_empty() or (l["assign"] != null and not _same(a, l["assign"])):
			err("разбор ссылки «%s»: %s / %s, в game.py %s / %s" % [l["text"], p, a, l["params"], l["assign"]])
		else:
			n_links += 1
	var n_bad := 0
	for b: Dictionary in ref["bad"]:
		if not Share.decode(b["code"]).is_empty():
			err("битый код принят: «%s»" % str(b["code"]).left(60))
		else:
			n_bad += 1
	var sp := Share.decode(ref["spaced"]["code"])
	if sp.size() != 2 or not _same(sp[1], ref["spaced"]["decoded"][1]):
		err("код с пробелами и кавычками не прочитан")
	else:
		n_read += 1
	for rb: Dictionary in ref["result_bad"]:
		var u := Share.result_unpack(rb["data"])
		if (rb["unpack"] == null) != u.is_empty() or (rb["unpack"] != null and not _same(u, rb["unpack"])):
			err("разбор результата %s: %s, в game.py %s" % [rb["data"], u, rb["unpack"]])
	for s: String in ref["fmt_secs"]:
		if Share.fmt_secs(int(s)) != ref["fmt_secs"][s]:
			err("время %s: «%s», в game.py «%s»" % [s, Share.fmt_secs(int(s)), ref["fmt_secs"][s]])
	if Share.base_url() != ref["base_url"]:
		err("адрес-основа ссылок «%s», в game.py «%s»" % [Share.base_url(), ref["base_url"]])
	# «Отправить в таблицу»: поля запроса как у send_result (без сети)
	var sa: Dictionary = {}
	for r: Dictionary in ref["result"]:
		if r["name"] == "с ошибками":
			sa = r["assign"]
	var a0 := SaveGame.assign
	SaveGame.assign = Share._ints(sa.duplicate(true))
	var n0: int = Feedback.captured.size()
	Share.send_result()
	if Feedback.captured.size() != n0 + 1:
		err("итог в таблицу: запрос не собран")
	else:
		var got: Dictionary = Feedback.captured[-1]
		for k: String in ref["payload"]:
			if k == "comment":                         # в конце — код результата: сжатые байты у Godot другие
				var gc: String = got.get(k, "")
				var wc: String = ref["payload"][k]
				var tail := "Result code: "
				if gc.split(tail)[0] != wc.split(tail)[0] or not _same(Share.decode(gc.split(tail)[-1]), Share.decode(wc.split(tail)[-1])):
					err("итог в таблицу: comment не как в game.py:
    godot  %s
    pygame %s" % [gc, wc])
				continue
			if not _same(got.get(k), ref["payload"][k]):
				err("итог в таблицу: поле %s = «%s», в game.py «%s»" % [k, got.get(k), ref["payload"][k]])
		if not str(got.get("platform", "")).begins_with("godot-") or str(got.get("time", "")) == "":
			err("итог в таблицу: platform/time")
		if SaveGame.assign.get("sent") != ref["payload_sent_after"]:
			err("итог в таблицу: «отправлено» не отмечено")
	Share.send_result()                        # второй раз — не уходит
	if Feedback.captured.size() != n0 + 1:
		err("итог в таблицу ушёл дважды")
	SaveGame.assign = a0
	Loc.code = lang0
	return [n_read, n_bad, n_links, share_out.size()]


func _share_write_out() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://tests/out"))
	FileAccess.open("res://tests/out/.gdignore", FileAccess.WRITE)
	var f := FileAccess.open(SHARE_OUT, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(share_out, " "))


func _type_text(s: String) -> void:
	for ch in s:
		for pressed: bool in [true, false]:
			var e := InputEventKey.new()
			e.unicode = ch.unicode_at(0)
			e.pressed = pressed
			get_viewport().push_input(e)
		await get_tree().process_frame


func _open_game_tab() -> SettingsDialog:
	await _press(Nav.current.get_node("Gear"), false)
	await _frames(1)
	if Nav.settings == null:
		err("коды: настройки не открылись")
		return null
	await _press(Nav.settings.get_node("Tab_game"), false)
	await _frames(1)
	return Nav.settings


## Прогресс: «СКОПИРОВАТЬ КОД» → сброс → «ВСТАВИТЬ КОД» → «ДА» → тот же прогресс → «ВЕРНУТЬ ПРЕЖНИЙ ПРОГРЕСС».
func _flow_share_progress() -> void:
	Loc.code = "ru"
	SaveGame.reset()
	for j: String in ["flat", "brake", "spokes"]:
		SaveGame.done[j] = true
	SaveGame.garage = [["flat", 3], ["brake", 2], ["spokes", 1]]
	SaveGame.seat_done["seat_elf"] = true
	SaveGame.seat_quiz_ok = true
	var before := Share.progress_pack()
	Nav.go("hub")
	await _frames(2)
	var sd := await _open_game_tab()
	if sd == null:
		return
	await _press(sd.get_node("Share_code"), true)
	await _frames(1)
	if Share.dlg == null or Share.dlg.mode() != "show" or Share.dlg.ui.get("ok") != true:
		err("коды: «Скопировать код» не показал код")
		return
	var code := Share.clip_mem
	var got := Share.decode(code)
	if got.size() != 2 or got[0] != "P" or not _same(got[1], before):
		err("коды: скопирован не тот код прогресса")
	share_out.append({"what": "code", "kind": "P", "code": code, "data": before})
	await _press(Share.dlg.get_node("Btn_close"), false)
	await _frames(1)
	await _press(Nav.settings.get_node("Reset"), false)
	await _frames(1)
	await _press(Nav.settings.get_node("ResetYes"), false)
	await _frames(2)
	if SaveGame.done.size() != 0:
		err("коды: сброс прогресса не сработал")
	sd = await _open_game_tab()
	if sd == null:
		return
	await _press(sd.get_node("Share_paste"), false)
	await _frames(1)
	if Share.dlg == null or Share.dlg.mode() != "paste":
		err("коды: «Вставить код» не открыл окно")
		return
	await _press(Share.dlg.get_node("Btn_apply"), false)          # пусто — «не распознан»
	await _frames(1)
	if Share.dlg == null or Share.dlg.ui.get("err", "") == "":
		err("коды: пустой код не дал ошибку")
	Share.dlg.get_node("Field").grab_focus()
	await _frames(1)
	var ev := InputEventKey.new()                                  # Ctrl+V в поле — из «буфера» (в тестах — память)
	ev.keycode = KEY_V
	ev.ctrl_pressed = true
	ev.pressed = true
	get_viewport().push_input(ev)
	await _frames(1)
	if Share.dlg.ui.get("text", "") != code:
		err("коды: Ctrl+V не вставил код")
	await _key(KEY_ENTER)                                          # Enter в поле — «Применить»
	await _frames(1)
	if Share.dlg == null or Share.dlg.mode() != "confirm":
		err("коды: код прогресса не спросил подтверждение")
		return
	await _press(Share.dlg.get_node("Btn_yes"), true)
	await _frames(2)
	if not _same(Share.progress_pack(), before):
		err("коды: после вставки прогресс %s, был %s" % [Share.progress_pack(), before])
	if not SaveGame.has_backup():
		err("коды: нет копии прежнего прогресса")
	sd = await _open_game_tab()
	if sd == null:
		return
	if sd.get_node_or_null("Share_restore") == null:
		err("коды: нет «Вернуть прежний прогресс»")
		return
	await _press(sd.get_node("Share_restore"), false)
	await _frames(2)
	if SaveGame.done.size() != 0 or SaveGame.has_backup():
		err("коды: «Вернуть прежний прогресс» не вернул (или копия осталась)")
	# битый код — «не распознан», прогресс не тронут; код результата — окно чужого результата
	Share.clip_mem = code.left(code.length() - 1) + ("0" if code[-1] != "0" else "1")
	sd = await _open_game_tab()
	await _press(sd.get_node("Share_paste"), true)
	await _frames(1)
	await _press(Share.dlg.get_node("Btn_clip"), false)
	await _press(Share.dlg.get_node("Btn_apply"), false)
	await _frames(1)
	if Share.dlg == null or Share.dlg.mode() != "paste" or Share.dlg.ui.get("err", "") == "" or SaveGame.done.size() != 0:
		err("коды: битый код не отвергнут")
	var ref := _shref()
	Share.dlg.ui["text"] = ref["result"][1]["code"]
	await _press(Share.dlg.get_node("Btn_apply"), false)
	await _frames(1)
	if Share.dlg == null or Share.dlg.mode() != "result" or not _same(Share.dlg.ui["res"], ref["result"][1]["unpack"]):
		err("коды: код результата не открыл итог ученика")
	else:
		await _press(Share.dlg.get_node("Btn_rtext"), false)
		await _frames(1)
		if Share.clip_mem != ref["result"][1]["texts"]["ru"]["text"].split("\n" + Loc.t("Код результата"))[0]:
			err("коды: итог ученика текстом не как в game.py")
		await _key(KEY_ESCAPE)
		await _key(KEY_ESCAPE)
	await _frames(1)
	if Share.dlg != null:
		err("коды: окно не закрылось по Esc")
	Nav.close_settings()


func _play_job(jid: String, mistake: bool) -> void:
	var card: Node = Nav.current.get_node_or_null("Card_" + jid)
	if card == null:
		err("задание по ссылке: в мастерской нет карточки %s" % jid)
		return
	await _press(card, mistake)
	await _frames(2)
	var scr: Node = Nav.current
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	scr = Nav.current
	for i in scr.job["steps"].size():
		var st: Dictionary = scr.job["steps"][i]
		if mistake and i == 0:
			scr.select_tool("lube" if st["tool"] != "lube" else "pump")
			scr.part_clicked(st["part"])
			await _frames(1)
		scr.select_tool(st["tool"])
		scr.part_clicked(st["part"])
		if scr.mini != null:
			await _frames(1)
			_solve_mini(scr.mini)
		await _frames(1)
	scr.start_ride()
	scr.ride.t0 = scr.ride.t - scr.ride.secs() - 0.01
	await _frames(2)
	scr._test_pressed()
	await _frames(2)


## Задание: конструктор → код и ссылка → запуск по ссылке (--link) → в мастерской только назначенное → все пункты →
## «Итог задания» (код результата = пройденное) → «Выйти из задания» (обычный прогресс не тронут) → та же ссылка
## возвращает прогресс задания → без ссылки — вопрос «продолжить / обычная игра».
func _flow_share_assign() -> String:
	Loc.code = "ru"
	SaveGame.reset()
	SaveGame.done["flat"] = true
	SaveGame.garage = [["flat", 2]]
	var normal := Share.progress_pack()
	Nav.go("hub")
	await _frames(2)
	var sd := await _open_game_tab()
	if sd == null:
		return ""
	await _press(sd.get_node("Share_build"), true)
	await _frames(1)
	if Share.dlg == null or Share.dlg.mode() != "builder":
		err("конструктор не открылся")
		return ""
	await _press(Share.dlg.get_node("Btn_make"), false)          # ничего не выбрано — ошибка
	if Share.dlg.ui.get("err", "") == "":
		err("конструктор: пустое задание принято")
	for k: String in ["spokes", "caster", "seat_elf", "seat_owl"]:
		await _press(Share.dlg.get_node("Pick_" + k), k.begins_with("seat"))
	await _press(Share.dlg.get_node("Pick_caster"), false)        # снять и отметить снова — в конец
	await _press(Share.dlg.get_node("Pick_caster"), false)
	Share.dlg.get_node("Field").grab_focus()
	await _frames(1)
	await _type_text("Анна П.")
	if Share.dlg.ui["sel"] != ["spokes", "seat_elf", "seat_owl", "caster"] or Share.dlg.ui["name"] != "Анна П.":
		err("конструктор: выбрано %s, имя «%s»" % [Share.dlg.ui["sel"], Share.dlg.ui["name"]])
	await _key(KEY_ENTER)                                        # Enter в поле имени — «Показать код задания»
	await _frames(1)
	var jcode := Share.clip_mem
	var got := Share.decode(jcode)
	var want := {"v": 1, "j": ["spokes", "caster"], "s": ["seat_elf", "seat_owl"], "f": "Анна П.", "ti": ""}
	if got.size() != 2 or got[0] != "J" or not _same(got[1], want):
		err("конструктор: код задания %s" % [got])
		return ""
	share_out.append({"what": "code", "kind": "J", "code": jcode, "data": want})
	await _press(Share.dlg.get_node("Btn_close"), false)        # «Готово» — назад в конструктор
	await _frames(1)
	if Share.dlg == null or Share.dlg.mode() != "builder":
		err("конструктор: «Готово» не вернул в конструктор")
	await _press(Share.dlg.get_node("Btn_cancel"), false)
	Nav.close_settings()
	await _frames(1)
	var a := Share.assign_parse({"jobs": want["j"], "seat": want["s"], "from": want["f"]})
	var link := Share.share_link(Share.assign_params(a))
	share_out.append({"what": "link", "link": link, "params": Share.parse_link(link), "assign": a})
	# запуск по ссылке: аргумент «--link=…» с тем же разбором, что адрес в браузере
	Share.link_launch = false
	Share.resume_asked = false
	Nav.go("title")
	await _frames(1)
	Share.apply_link(Share.launch_query(PackedStringArray(["--test", "--link=" + link])))
	await _frames(1)
	if not SaveGame.assign_on() or SaveGame.assign["id"] != a["id"]:
		err("запуск по ссылке: задание не началось")
		return ""
	Nav.current.start()                                          # «клик — продолжить» на титуле
	await _frames(2)
	if Nav.current_name != "hub":
		err("задание: с титула не в мастерскую (%s)" % Nav.current_name)
		Nav.go("hub")
		await _frames(2)
	var cards: Array = Nav.current._cards.map(func(c: Node) -> String: return c.get_meta("job"))
	if cards != ["spokes", "caster"] or Nav.current.get_node_or_null("Guild") != null or Nav.current.get_node_or_null("Garage") != null:
		err("задание: в мастерской %s (или видны Гильдия/гараж)" % [cards])
	if Share.dlg != null:
		err("задание по ссылке: лишний вопрос «продолжить»")
	await _play_job("spokes", true)
	var res_scr: Node = Nav.current
	if Nav.current_name != "result" or res_scr._btn.label != "В МАСТЕРСКУЮ":
		err("задание: после первого пункта итог не «В МАСТЕРСКУЮ»")
	await _press(res_scr.get_node("ToHub"), false)
	await _frames(2)
	await _play_job("caster", false)
	await _press(Nav.current.get_node("ToHub"), true)
	await _frames(2)
	if Share.dlg != null:
		err("задание: итог открылся до примерок")
		Share.close()
	if SaveGame.done.has("spokes") or SaveGame.done.has("caster") or SaveGame.garage.size() != 1:
		err("задание: обычный прогресс изменился")
	# примерки — только назначенные; верная посадка — мышью и клавиатурой
	await _press(Nav.current.get_node("Seating"), false)
	await _frames(2)
	var scr: Node = Nav.current
	await _press(scr.get_node("Tab_fit"), false)
	await _frames(1)
	var listed: Array = []
	for c in scr.get_node("Dyn").get_children():
		if c.name.begins_with("Case_"):
			listed.append(SeatLogic.cases()[int(c.get_meta("i"))]["id"])
	if listed != ["seat_elf", "seat_owl"]:
		err("задание: в Кабинете посадки примерки %s" % [listed])
	for sid: String in ["seat_elf", "seat_owl"]:
		var ci: int = SeatLogic.cases().map(func(c: Dictionary) -> String: return c["id"]).find(sid)
		await _press(scr.get_node("Dyn/Case_%d" % ci), sid == "seat_owl")
		await _frames(1)
		if sid == "seat_elf":
			await _press(scr.get_node("Dyn/Check"), false)          # одна ошибка
			await _frames(1)
		var sol := _seat_solution(SeatLogic.cases()[ci], scr.slider_keys(), scr.cfg)
		for k: String in sol:
			scr.set_value(k, sol[k])
		await _press(scr.get_node("Dyn/Check"), sid == "seat_owl")
		await _frames(1)
	if SaveGame.seat_done.size() != 0:
		err("задание: примерки попали в обычный прогресс")
	if Share.dlg == null or Share.dlg.mode() != "summary":
		err("задание: после последнего пункта нет «Итога задания»")
		return ""
	var res := Share.assign_result()
	var want_rows := [["spokes", true], ["caster", true], ["seat_elf", true], ["seat_owl", true]]
	var errs := {}
	for r: Array in res["rows"]:
		errs[r[0]] = r[2]
	if res["rows"].map(func(r: Array) -> Array: return [r[0], r[1]]) != want_rows or errs["seat_elf"] != 1 or \
			errs["seat_owl"] != 0 or errs["caster"] != 0 or errs["spokes"] < 1:
		err("итог задания: %s" % [res["rows"]])
	await _press(Share.dlg.get_node("Btn_rcode"), true)
	await _frames(1)
	var rcode := Share.clip_mem
	var rg := Share.decode(rcode)
	if rg.size() != 2 or rg[0] != "R" or not _same(Share.result_unpack(rg[1]), res):
		err("код результата не совпадает с пройденным")
	share_out.append({"what": "code", "kind": "R", "code": rcode, "data": Share.result_pack(SaveGame.assign)})
	await _press(Share.dlg.get_node("Btn_close"), false)         # назад к итогу
	await _frames(1)
	await _press(Share.dlg.get_node("Btn_rtext"), false)
	await _frames(1)
	if not Share.clip_mem.contains(rcode) or not Share.clip_mem.begins_with("Колёса и Кости — итог задания"):
		err("итог текстом: %s" % Share.clip_mem.left(80))
	await _key(KEY_ESCAPE)
	await _frames(1)
	var n0: int = Feedback.captured.size()
	if Share.can_send():
		await _press(Share.dlg.get_node("Btn_send"), false)
		await _frames(1)
		if Feedback.captured.size() != n0 + 1 or not SaveGame.assign["sent"] or Share.dlg.get_node("Btn_send").enabled:
			err("итог в таблицу: не отправлен или кнопка осталась")
	var asg := SaveGame.assign.duplicate(true)
	await _press(Share.dlg.get_node("Btn_exit"), false)
	await _frames(2)
	if SaveGame.assign_on() or not _same(Share.progress_pack(), normal) or Nav.current_name != "hub":
		err("«Выйти из задания»: обычный прогресс не тот (или задание осталось)")
	# та же ссылка — прогресс задания с места; без ссылки — вопрос «продолжить / обычная игра»
	Share.apply_link(link)
	if not SaveGame.assign_on() or not _same(SaveGame.assign["done"], asg["done"]):
		err("та же ссылка не вернула прогресс задания")
	SaveGame.assign["done"].erase("seat_owl")                    # незаконченное задание
	Share.link_launch = false
	Share.resume_asked = false
	Nav.go("hub")
	await _frames(3)
	if Share.dlg == null or Share.dlg.mode() != "resume":
		err("запуск без ссылки: нет вопроса «продолжить задание / обычная игра»")
		return ""
	await _press(Share.dlg.get_node("Btn_normal"), true)
	await _frames(2)
	if SaveGame.assign_on() or Nav.current_name != "hub" or Nav.current.get_node_or_null("Guild") == null:
		err("«Обычная игра»: задание не выключилось")
	Share.resume_asked = false
	SaveGame.assign["active"] = true
	Nav.go("hub")
	await _frames(3)
	if Share.dlg == null:
		err("вопрос «продолжить» не появился второй раз")
		return ""
	await _press(Share.dlg.get_node("Btn_resume"), false)
	await _frames(2)
	if not SaveGame.assign_on() or Nav.current.get_node_or_null("Summary") == null:
		err("«Продолжить задание»: мастерская не в режиме задания")
	Nav.go("hub")                                              # вопрос — один раз за запуск
	await _frames(3)
	if Share.dlg != null:
		err("вопрос «продолжить» повторился в том же запуске")
	# сохранение: ключ assign как в game.py
	var sv: Dictionary = SaveGame.to_dict().get("assign", {})
	var keys: Array = sv.keys()
	keys.sort()
	if keys != ["active", "done", "errors", "from", "id", "jobs", "seat", "secs", "sent", "title"]:
		err("save.json: ключи assign %s" % [keys])
	var back := SaveGame.assign_state(JSON.parse_string(JSON.stringify(sv)))
	if not _same(back, SaveGame.assign):
		err("save.json: задание не читается обратно")
	Share.exit_assignment()
	await _frames(1)
	return "задание из конструктора (4 пункта) пройдено по ссылке --link, итог и код результата = пройденному"


# ======================= Озвучка =======================

## Сводки «где я и что делать» и фразы клавиш против game.py (content/speech_ref.json) на RU и EN.
## Голос в тестах не звучит (Speech.kind = "test"): сравниваем текст. Возврат: [совпало, всего].
func _speech_ref() -> Array:
	var path := "res://content/speech_ref.json"
	if not FileAccess.file_exists(path):
		err("нет content/speech_ref.json — запусти tools/sync_content.py")
		return [0, 0]
	var ref: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
	var lang0 := Loc.code
	var voices0: bool = Settings.a11y.get("voices", true)
	Settings.a11y["voices"] = false
	var ok := 0
	var total := 0
	for lang: String in ["ru", "en"]:
		Loc.code = lang
		var want := {}
		for r: Dictionary in ref[lang]["rows"]:
			want[r["name"]] = r
		var got := await _speech_states()
		for name: String in want:
			total += 1
			if not got.has(name):
				err("озвучка (%s): нет состояния %s" % [lang, name])
				continue
			var g: Array = got[name]
			var w: Dictionary = want[name]
			if g.size() > 2 and w.has("items"):                # подписи пунктов для озвучки фокуса — по группам
				total += 1
				var gi: Dictionary = _by_group(g[2])
				var wi: Dictionary = _by_group(w["items"])
				if gi.has("Меню"):                     # известное (28.11): кнопка звука в шапке — в game.py её нет
					var mn: Array = (gi["Меню"] as Array).filter(func(x: String) -> bool: return not x in KB_SOUND)
					if mn.size() != (gi["Меню"] as Array).size():
						speech_sound_known += 1
						gi["Меню"] = mn
						if mn.is_empty() and not wi.has("Меню"):
							gi.erase("Меню")
				if gi.has("Инструменты") and wi.has("Инструменты"):   # известное (28.11): порядок кучками, к подписи — кучка
					var gn: Array = (gi["Инструменты"] as Array).map(func(x: String) -> String: return _kb_norm("Инструменты", x))
					var a1 := gn.duplicate()
					var a2 := (wi["Инструменты"] as Array).duplicate()
					a1.sort()
					a2.sort()
					if a1 == a2:
						if gi["Инструменты"] != wi["Инструменты"]:
							speech_tools_known += 1
						gi["Инструменты"] = wi["Инструменты"]
				var bad_g: Array = []
				for grp: String in gi:
					if not wi.has(grp) or gi[grp] != wi[grp]:
						bad_g.append([grp, gi[grp], wi.get(grp)])
				for grp: String in wi:
					if grp in A11Y_GROUPS and not gi.has(grp):
						bad_g.append([grp, null, wi[grp]])
				if bad_g.is_empty():
					ok += 1
				else:
					err("озвучка фокуса (%s) «%s»: %s" % [lang, name, bad_g])
			if Speech.clean(g[0]) != w["full"] or (g.size() > 1 and Speech.clean(g[1]) != w["short"]):
				err("озвучка (%s) «%s»:\n    godot  %s\n    pygame %s" % [lang, name, Speech.clean(g[0]) if Speech.clean(g[0]) != w["full"]
					else Speech.clean(g[1]), w["full"] if Speech.clean(g[0]) != w["full"] else w["short"]])
				continue
			ok += 1
		# фразы клавиш: F2 (выкл/вкл), F1 (справка, закрыта), H, C
		var ph: Dictionary = ref[lang]["phrases"]
		Nav.go("hub")
		await _frames(3)
		var got_ph := {}
		Settings.a11y["on"] = true
		await _key(KEY_F2)
		await _frames(1)
		got_ph["f2_off"] = Speech.last()
		await _key(KEY_F2)
		await _frames(1)
		got_ph["f2_on"] = Speech.last()
		Settings.a11y["on"] = false
		await _key(KEY_F1)
		await _frames(1)
		got_ph["help"] = _last_with(Speech.clean(Loc.t("Клавиши.")))
		await _key(KEY_F1)
		await _frames(1)
		got_ph["help_closed"] = Speech.last()
		await _key(KEY_H)
		await _frames(1)
		got_ph["no_hint"] = Speech.last()
		await _key(KEY_C)
		await _frames(1)
		got_ph["no_client"] = Speech.last()
		for k: String in ph:
			total += 1
			if not str(got_ph.get(k, "")).contains(ph[k]):
				err("озвучка (%s), клавиша %s:\n    godot  %s\n    pygame %s" % [lang, k, got_ph.get(k, ""), ph[k]])
			else:
				ok += 1
	Loc.code = lang0
	Settings.a11y["voices"] = voices0
	Settings.a11y["on"] = false
	return [ok, total]


func _last_with(prefix: String) -> String:
	for i in range(Speech.history.size() - 1, -1, -1):
		if Speech.history[i].contains(prefix):
			return Speech.history[i]
	return ""


## Те же состояния, что speech_ref в sync_content.py: имя → [полная сводка, короткая].
func _speech_states() -> Dictionary:
	var out := {}
	SaveGame.reset()
	Nav.go("title")
	await _frames(1)
	out["title"] = [A11y.summary(true), A11y.summary(false)]
	Nav.go("intro")
	await _frames(1)
	for i in Nav.current.slides().size():
		Nav.current.idx = i
		out["intro_%d" % i] = [A11y.summary(true), A11y.summary(false)]
	Nav.go("credits", {"from": "title"})
	await _frames(1)
	out["credits"] = [A11y.summary(true), A11y.summary(false)]
	SaveGame.done["flat"] = true
	SaveGame.done["brake"] = true
	SaveGame.tutorial_skipped = true
	Nav.go("hub")
	await _frames(1)
	out["hub"] = [A11y.summary(true), A11y.summary(false)]
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(1)
	var scr: Node = Nav.current
	out["job_flat_diagnose"] = [A11y.summary(true), A11y.summary(false), _items(scr)]
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	scr = Nav.current
	out["job_flat_repair"] = [A11y.summary(true), A11y.summary(false), _items(scr)]
	var st: Dictionary = scr.job["steps"][0]
	scr.select_tool(st["tool"])
	scr.part_clicked(st["part"])
	await _frames(1)
	out["job_flat_repair_2"] = [A11y.summary(true), A11y.summary(false)]
	for pair: Array in [["flat", "pump"], ["brake", "gap"], ["spokes", "ping"], ["lift", "meter"]]:
		Nav.go("job", {"job": pair[0], "variant": 0})
		await _frames(1)
		scr = Nav.current
		for pid: String in scr.job["parts"].slice(0, 2):
			scr.inspect_part(pid)
		scr.choose_diagnosis(_correct_diag(scr))
		await _frames(1)
		scr = Nav.current
		while scr.phase == "repair" and not (scr.cur_step().get("mini") is Dictionary and scr.cur_step()["mini"]["kind"] == pair[1]):
			scr.step_skip()
		var s2: Dictionary = scr.cur_step()
		scr.select_tool(s2["tool"])
		scr.part_clicked(s2["part"])
		await _frames(1)
		out["mini_" + pair[1]] = [A11y.summary(true), A11y.summary(false)]
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(1)
	scr = Nav.current
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	scr.choose_diagnosis(_correct_diag(scr))
	await _frames(1)
	scr = Nav.current
	while scr.phase == "repair":
		scr.step_skip()
	await _frames(1)
	out["job_flat_test"] = [A11y.summary(true), A11y.summary(false)]
	Nav.go("result", {"job": scr.job, "stars": 3, "gag": Content.talk["martin"]["good"][0], "mistakes": 0})
	await _frames(1)
	out["result_flat"] = [A11y.summary(true), A11y.summary(false)]
	var ts: Node = await _open_tech("truing")
	out["tech_truing"] = [A11y.summary(true), A11y.summary(false), _items(ts)]
	_view_all_manual(ts)
	for s3: Dictionary in ts.job["steps"]:
		if s3.get("spec") is Dictionary:
			ts.select_tool(s3["tool"])
			ts.op_clicked(s3["id"])
			break
		await _tech_do(ts, s3["id"])
	await _frames(1)
	out["tech_spec"] = [A11y.summary(true), A11y.summary(false)]
	Nav.go("seating")
	await _frames(1)
	var se: Node = Nav.current
	se.quiz = Content.seating["quiz"].duplicate(true)
	out["seat_lessons"] = [A11y.summary(true), A11y.summary(false)]
	se.tab = "fit"
	se.load_case(0)
	se.refresh()
	await _frames(1)
	out["seat_fit"] = [A11y.summary(true), A11y.summary(false), _items(se)]
	se.tab = "quiz"
	out["seat_quiz"] = [A11y.summary(true), A11y.summary(false)]
	se.quiz_done = true
	se.score = 6
	out["seat_quiz_done"] = [A11y.summary(true), A11y.summary(false)]
	Nav.go("hub")
	await _frames(1)
	for tb: String in ["sound", "graphics", "access", "game"]:
		SettingsDialog.tab = tb
		Nav.open_settings()
		await _frames(1)
		out["settings_" + tb] = [A11y.summary(true), A11y.summary(false), _items(Nav.settings)]
		Nav.close_settings()
		await _frames(1)
	Share.open({"mode": "paste"})
	out["share_paste"] = [A11y.summary(true), A11y.summary(false)]
	Share.open({"mode": "builder"})
	out["share_builder"] = [A11y.summary(true), A11y.summary(false)]
	Share._close_dlg()
	Nav.toggle_help()
	out["help"] = [A11y.summary(true), A11y.summary(false)]
	Nav.toggle_help()
	Nav.open_flag()
	out["feedback_general"] = [A11y.summary(true), A11y.summary(false)]
	Nav.feedback.close()
	await _frames(1)
	return out



func _only(what: String) -> void:
	var line := ""
	match what:
		"speech":
			var sp: Array = await _speech_ref()
			line = "озвучка: %d/%d (известное: инструменты в порядке кучек и с кучкой в подписи — %d, кнопка звука в «Меню» — %d)" % [
				sp[0], sp[1], speech_tools_known, speech_sound_known]
		"switch":
			line = await _flow_switch(["flat:0", "brake:0", "spokes:0"], ["truing"])
		"switch-full":
			var all: Array = []
			for job: Dictionary in Content.jobs:
				for v in maxi(1, job.get("variants", []).size()):
					all.append("%s:%d" % [job["id"], v])
			line = await _flow_switch(all, Content.tech_jobs.map(func(j: Dictionary) -> String: return j["id"]))
		"rides":
			line = await _flow_tech_rides()
		"brenna":
			line = await _flow_brenna()
		"martin":
			line = await _flow_martin() + "; " + await _flow_martin_live()
		"pad":
			line = await _flow_pad(["flat:0", "brake:0", "lift:0"], ["truing"])
		"kborder":
			line = await _kb_order_ref(["ru", "en"])
		"kborder-ru":
			line = await _kb_order_ref(["ru"])
		"arrows":
			line = await _flow_arrows()
		"fixes":
			line = await _fixes()
		"touch":
			line = await _touch()
		"review-kb":
			line = await _review_kb()
		"review-web":
			line = await _review_web()
		"review-port":                       # перенос правок game.py 26.11 (tests/review_port_check.gd)
			line = await _review_port()
		"instr-sizes":                       # обзор 26.11, E22: инструкция ремонта — было/стало по всем шагам
			var rw: Node = (load("res://tests/review_web_check.gd") as GDScript).new()
			add_child(rw)
			var d: Dictionary = rw.instr_measure()
			var pc: Node = (load("res://tests/phone_check.gd") as GDScript).new()
			pc.write_out("instr_sizes.json", JSON.stringify(d, " ", false) + "
")
			for k: String in d:
				print("INSTR %s: телефон %d → %d шагов (худший было %s, стало +%d; мельче 19 — %d шагов, кегль от %d; коляска от %d, ниже 283 — %s), ПК %d → %d"
					% [k, d[k]["phone_before"], d[k]["phone_after"], d[k]["phone_worst_before"], d[k]["phone_worst_after"],
					d[k]["phone_shrunk"], d[k]["min_size"], d[k]["chair_h_min"], d[k]["chair_small"], d[k]["pc_before"],
					d[k]["pc_after"]])
			line = "INSTR SIZES: %d сочетаний" % d.size()
			rw.queue_free()
			pc.free()
		"phone":
			line = await _phone_check()
		"mute":
			line = await _mute_check()
		"phone-measure":
			line = await _phone_measure(false)
		"phone-ref":
			line = await _phone_measure(true)
		"seat-sizes":
			var pc: Node = (load("res://tests/phone_check.gd") as GDScript).new()
			add_child(pc)
			var args := OS.get_cmdline_user_args()
			var on := not (args.find("--phone") >= 0 and args[args.find("--phone") + 1] == "0")
			var d: Dictionary = await pc.seat_sizes(self, on)
			pc.write_out("seat_sizes_%d.json" % (1 if on else 0), JSON.stringify(d, " ", true) + "\n")
			line = "SEAT SIZES (%s): %d" % ["телефон" if on else "выкл", d.size()]
			pc.queue_free()
		"tech-sizes":
			var pc: Node = (load("res://tests/phone_check.gd") as GDScript).new()
			add_child(pc)
			var d: Dictionary = await pc.tech_sizes(self)
			pc.write_out("tech_sizes_1.json", JSON.stringify(d, " ", true) + "\n")
			line = "TECH SIZES (телефон): %d" % d.size()
			pc.queue_free()
	Nav.shutdown()
	await _frames(10)
	for e in errors:
		pass
	if errors.is_empty():
		print("GODOT SELFTEST OK (только %s) — %s" % [what, line])
		get_tree().quit(0)
	else:
		printerr("GODOT SELFTEST FAILED: %d ошибок" % errors.size())
		get_tree().quit(1)



const A11Y_GROUPS := ["Детали", "Диагноз", "Инструменты", "Операции", "Шаги", "Ползунки", "Вкладки", "Доступность", "Меню",
	"Клиенты"]


## Пункты для озвучки фокуса: [группа, подпись] (детали — строки списка, не кружки на коляске).
func _items(root: Node) -> Array:
	var out: Array = []
	for c: Control in A11y.focusables(root):
		var g := A11y.group_of(c)
		if not g in A11Y_GROUPS or (g == "Детали" and not str(c.name).begins_with("Part_")):
			continue
		out.append([g, Speech.clean(A11y.label_of(c))])
	return out


func _by_group(items: Array) -> Dictionary:
	var d := {}
	for it: Array in items:
		if not it[0] in A11Y_GROUPS:
			continue
		if not d.has(it[0]):
			d[it[0]] = []
		d[it[0]].append(Speech.clean(it[1]))
	for g: String in ["Меню", "Операции"]:            # порядок операций перемешан (как в game.py) — сравниваем набор
		if d.has(g):
			d[g].sort()
	if d.has("Диагноз"):                               # варианты диагноза перемешаны: без номера, набором
		var rx := RegEx.create_from_string("^[^:]+ [0-9]+: ")
		d["Диагноз"] = d["Диагноз"].map(func(x: String) -> String: return rx.sub(x, ""))
		d["Диагноз"].sort()
	return d


# ======================= одна кнопка и геймпад =======================

var ctl_mode: String = ""                   # "" — клавиатура; "pad" — геймпад; "switch" — одна кнопка


func _pad_btn(b: JoyButton) -> void:
	for pressed: bool in [true, false]:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		e.pressed = pressed
		get_viewport().push_input(e)
	await get_tree().process_frame


## Одна кнопка: ждём, пока выделится нужный пункт (бот сам двигает выделение — шаг сканирования), и коротко жмём.
func _sw_press_on(c: Control) -> void:
	A11y._scan_next = A11y.scan_t + 1e6         # выделение двигает бот: время не ждём
	for _i in 400:
		if c.has_focus() and A11y.kb_cur == c:  # выделен пункт одной кнопки (kb["key"]), а не фокус экрана при входе
			break
		A11y.scan_step()
	if not c.has_focus() or A11y.kb_cur != c:
		err("одна кнопка: не дошли до «%s» (%s)" % [c.name, A11y.label_of(c)])
		return
	await _sw_press(false)


func _sw_press(hold: bool) -> void:
	for pressed: bool in [true, false]:
		if not pressed:
			A11y.scan_t += (A11y.SCAN_HOLD + 0.1) if hold else 0.05
		var e := InputEventKey.new()
		e.keycode = KEY_SPACE
		e.physical_keycode = KEY_SPACE
		e.pressed = pressed
		get_viewport().push_input(e)
	await _frames(1)


## Ползунок одной кнопкой: нажать — «больше»; «меньше / больше / готово» по очереди, нажатие — сделать.
func _sw_slider(c: Control, value: Callable, target: int) -> void:
	await _sw_press_on(c)
	for _i in 400:
		var v: int = value.call()
		if v == target:
			break
		var want := 1 if v < target else 0
		for _j in 3:
			if int(A11y.scan_sub.get("i", -1)) == want:
				break
			A11y.scan_step()
		await _sw_press(false)
	for _j in 3:
		if int(A11y.scan_sub.get("i", -1)) == 2:
			break
		A11y.scan_step()
	await _sw_press(false)
	if int(value.call()) != target:
		err("одна кнопка: ползунок «%s» — %d, нужно %d" % [c.name, value.call(), target])


## Одна кнопка и геймпад: задания мастерской, про-задание, примерка, настройки. Возврат: строка для итога.
func _flow_switch(jobs: Array, techs: Array) -> String:
	var lang0 := Loc.code
	Settings.a11y["scan"] = 1
	A11y.scan_stat = {"press": 0, "hold": 0, "steps": 0}
	ctl_mode = "switch"
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	SaveGame.ending_seen = true                  # вечеринка после 21-го ремонта — не в этой проверке
	for key: String in jobs:
		await _flow_repair(key, true)
	for jid: String in techs:
		SaveGame.done.merge({"flat": true, "brake": true, "spokes": true, "lift": true, "caster": true}, true)
		await _flow_tech_events(jid, false, true)
	await _sw_seat_settings()
	# долгое нажатие — назад (Esc): из мастерской на титул
	Nav.go("hub")
	await _frames(2)
	await _sw_press(true)
	await _frames(2)
	if Nav.current_name != "title":
		err("одна кнопка: долгое нажатие не вернуло на титул (%s)" % Nav.current_name)
	var st: Dictionary = A11y.scan_stat.duplicate()
	ctl_mode = ""
	Settings.a11y["scan"] = 0
	A11y.scan_sub = {}
	Loc.code = lang0
	return "Одна кнопка: %d заданий + %d про-заданий, примерка, настройки — нажатий %d, долгих %d, шагов выделения %d" % [
		jobs.size(), techs.size(), st["press"], st["hold"], st["steps"]]


## Одна кнопка: верная посадка у первого клиента (ползунки — «меньше / больше / готово»), настройки.
func _sw_seat_settings() -> void:
	Nav.go("seating")
	await _frames(2)
	var scr: Node = Nav.current
	await _press(scr.get_node("Tab_fit"), true)
	await _frames(1)
	var c: Dictionary = SeatLogic.cases()[scr.case_i]
	var sol := _seat_solution(c, scr.slider_keys(), scr.cfg)
	for k: String in scr.slider_keys():
		if int(scr.cfg[k]) == int(sol[k]):
			continue
		var sl: Control = scr.sliders[k]
		if ctl_mode == "switch":
			await _sw_slider(sl, func() -> int: return int(scr.cfg[k]), int(sol[k]))
		else:
			await _kb_focus_on(sl)
			for _i in 200:
				if int(scr.cfg[k]) == int(sol[k]):
					break
				await _key(KEY_RIGHT if int(scr.cfg[k]) < int(sol[k]) else KEY_LEFT)
	await _press(scr.get_node("Dyn/Check"), true)
	await _frames(1)
	if not scr.solved:
		err("%s: посадка не засчитана" % ctl_mode)
	Nav.go("hub")
	await _frames(2)
	await _press(Nav.current.get_node("Gear"), true)
	await _frames(1)
	if Nav.settings == null:
		err("%s: настройки не открылись" % ctl_mode)
		return
	await _press(Nav.settings.get_node("Tab_access"), true)
	await _frames(1)
	var calm0 := Settings.calm()
	await _press(Nav.settings.get_node("Acc_calm"), true)
	await _frames(1)
	if Settings.calm() == calm0:
		err("%s: «Без анимации» не переключилось" % ctl_mode)
	await _press(Nav.settings.get_node("Acc_calm"), true)
	await _frames(1)
	await _press(Nav.settings.get_node("Tab_sound"), true)
	await _frames(1)
	var vs: VolSlider = Nav.settings.get_node("Vol_music")
	var v0: float = Settings.vol["music"]
	if ctl_mode == "switch":
		await _sw_slider(vs, func() -> int: return roundi(float(Settings.vol["music"]) * 20), roundi(v0 * 20) - 1)
	else:
		await _kb_focus_on(vs)
		await _key(KEY_LEFT)
	if is_equal_approx(float(Settings.vol["music"]), v0):
		err("%s: громкость музыки не изменилась" % ctl_mode)
	Settings.vol["music"] = v0
	await _press(Nav.settings.get_node("Done"), true)
	await _frames(1)
	if Nav.settings != null:
		err("%s: «Готово» не закрыло настройки" % ctl_mode)


## Геймпад: те же задания, про-задание, примерка и настройки кнопками A/B, крестовиной, LB/RB, Start, Back, Y.
func _flow_pad(jobs: Array, techs: Array) -> String:
	ctl_mode = "pad"
	Nav.pad_presses = 0
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	for key: String in jobs:
		await _flow_repair(key, true)
	for jid: String in techs:
		SaveGame.done.merge({"flat": true, "brake": true, "spokes": true, "lift": true, "caster": true}, true)
		await _flow_tech_events(jid, false, true)
	await _sw_seat_settings()
	# крестовина двигает фокус, LB/RB — группы, Start — настройки, Back — справка, Y — «где я», B — назад
	Nav.go("hub")
	await _frames(2)
	var f0 := get_viewport().gui_get_focus_owner()
	await _pad_btn(JOY_BUTTON_DPAD_RIGHT)          # фокуса клавиатуры ещё нет — первый пункт (как в game.py)
	await _frames(1)
	if A11y.kb_cur == null or A11y.kb_cur != A11y.kb_items()[0]:
		err("геймпад: первая крестовина не встала на первый пункт")
	await _pad_btn(JOY_BUTTON_DPAD_RIGHT)
	await _frames(1)
	if get_viewport().gui_get_focus_owner() == f0:
		err("геймпад: крестовина не двигает фокус")
	var f1 := get_viewport().gui_get_focus_owner()
	await _pad_btn(JOY_BUTTON_RIGHT_SHOULDER)
	await _frames(1)
	if get_viewport().gui_get_focus_owner() == f1:
		err("геймпад: RB не переводит фокус")
	var heard: Array = []
	var hear := func(x: String) -> void: heard.append(x)
	Speech.spoke.connect(hear)
	await _pad_btn(JOY_BUTTON_Y)
	await _frames(2)
	Speech.spoke.disconnect(hear)
	var want_y := Speech.clean(A11y.summary(true))
	if not heard.any(func(x: String) -> bool: return x.contains(want_y)):
		err("геймпад: Y не повторил «где я»:
    %s
    ждали %s" % [heard, want_y])
	await _pad_btn(JOY_BUTTON_START)
	await _frames(1)
	if Nav.settings == null:
		err("геймпад: Start не открыл настройки")
	await _pad_btn(JOY_BUTTON_START)
	await _frames(1)
	if Nav.settings != null:
		err("геймпад: Start не закрыл настройки")
	# держат «вниз» и выдёргивают геймпад (Godot отпускания не присылает) — повтор стрелки должен остановиться (21.11)
	var down := InputEventJoypadButton.new()
	down.button_index = JOY_BUTTON_DPAD_DOWN
	down.pressed = true
	get_viewport().push_input(down)
	await _frames(1)
	Nav._on_pad_connection(0, false)
	var held := A11y.kb_cur
	Nav._pad_t += 5.0                                # пять секунд «держат» — без отключения было бы ~30 повторов
	for _i in 6:
		await _frames(1)
		Nav._pad_t += 0.5
	if A11y.kb_cur != held or Nav._pad_dir != 0:
		err("геймпад: после отключения с зажатой крестовиной стрелка повторяется (%s → %s)" % [held, A11y.kb_cur])
	Nav.toast.timer = 0.0
	Nav._on_pad_connection(0, true)
	if not Nav.toast.text.contains("Геймпад подключён"):
		err("геймпад: подключили — нет подсказки (как game.py pad_action «added»): «%s»" % Nav.toast.text)
	Nav.toast.timer = 0.0
	await _pad_btn(JOY_BUTTON_BACK)
	await _frames(1)
	if Nav.help == null:
		err("геймпад: Back не открыл справку")
	await _pad_btn(JOY_BUTTON_B)
	await _frames(1)
	await _pad_btn(JOY_BUTTON_B)
	await _frames(2)
	if Nav.help != null or Nav.current_name != "title":
		err("геймпад: B не закрыл справку и не вернул на титул (%s)" % Nav.current_name)
	ctl_mode = ""
	return "Геймпад: %d заданий + %d про-заданий, примерка, настройки, крестовина/LB/RB/Start/Back/Y/B — нажатий %d" % [
		jobs.size(), techs.size(), Nav.pad_presses]


## Гильдия: проезд петлёй по id про-задания (RIDE_ANIM_TECH): нужная петля, свой срок, остановка справа, после проезда
## герой стоит; «Без анимации» — прежнее (коляска по центру). Возврат: строка для итога.
func _flow_tech_rides() -> String:
	var at: Dictionary = Frames.ride.get("anim_tech", {})
	var ts: Array = Frames.ride.get("tech_stop", [1040, 560])
	var ok := 0
	for jid: String in at:
		var name: String = at[jid]
		if Frames.loop_count(name) < 2:
			err("проезд Гильдии %s: нет кадров петли %s" % [jid, name])
			continue
		var scr: Node = await _open_tech(jid)
		while scr.phase == "repair":
			scr.step_skip()
		await _frames(1)
		Frames.want_loop(name)
		Frames.flush()
		scr._test_pressed()
		await _frames(2)
		if scr.ride.loop_name != name:
			err("проезд Гильдии %s: петля «%s», нужна %s" % [jid, scr.ride.loop_name, name])
			continue
		var want_t: float = float(Frames.ride.get("anim_t", {}).get(name, Frames.ride.get("secs", 4.6)))
		if not is_equal_approx(scr.ride.secs(), want_t):
			err("проезд Гильдии %s: срок %.1f с, нужно %.1f" % [jid, scr.ride.secs(), want_t])
		if scr.ride.drawn == 0:
			err("проезд Гильдии %s: кадры петли не рисуются" % jid)
		scr.ride.t0 = scr.ride.t - scr.ride.secs() - 0.01
		await _frames(3)
		var r: Rect2 = scr.ride.stay_rect()
		if not scr.ride_done or r.size == Vector2.ZERO or scr.chair.visible:
			err("проезд Гильдии %s: после проезда герой не стоит (или видна пустая коляска)" % jid)
			continue
		if absf(r.get_center().x - float(ts[0])) > 2 or absf(r.end.y - float(ts[1])) > 1:
			err("проезд Гильдии %s: остановка %s, нужно центр x=%d, пол %d" % [jid, r, ts[0], ts[1]])
			continue
		scr.rebuild()                          # смена языка / размера текста: герой так и стоит справа
		await _frames(2)
		if not scr.ride.stay or scr.ride.stay_rect() != r or scr.chair.visible:
			err("проезд Гильдии %s: после пересборки экрана герой не стоит (%s, коляска видна: %s)" % [
				jid, scr.ride.stay_rect(), scr.chair.visible])
			continue
		ok += 1
	# «Без анимации» — прежнее: без петли, коляска по центру после проверки
	var calm0: bool = Settings.a11y.get("calm", false)
	Settings.a11y["calm"] = true
	var sc2: Node = await _open_tech("toe")
	while sc2.phase == "repair":
		sc2.step_skip()
	await _frames(1)
	sc2._test_pressed()
	await _frames(3)
	if sc2.ride.loop_name != "" or not sc2.ride_done or sc2.ride.stay or not sc2.chair.visible:
		err("проезд Гильдии «Без анимации»: не прежнее поведение")
	Settings.a11y["calm"] = calm0
	return "проезд Гильдии петлёй: %d/%d про-заданий (петля, срок, остановка справа, стоит после и после пересборки), «Без анимации» — прежнее" % [ok, at.size()]


## Мартин «живой» во вступлении и на празднике (idle.scenes из game_consts.json — SCENE_LOOPS/SCENE_LOOP_BOX
## game.py): петля экрана выбрана, в боксе картинки с полем, без своего покачивания (на празднике — без качания и
## подпрыга), стоит там же, где картинка (±2 px); «Без анимации» — картинка.
func _flow_martin() -> String:
	var scenes: Dictionary = Content.consts.get("idle", {}).get("scenes", {})
	if not scenes.has("intro") or not scenes.has("ending"):
		err("Мартин: нет idle.scenes (intro, ending) в game_consts.json")
		return "Мартин: нет данных"
	var calm0: bool = Settings.a11y.get("calm", false)
	var worst := 0.0
	var out: Array = []
	for sc: String in ["intro", "ending"]:
		var e: Dictionary = scenes[sc]
		var name := str(e["loop"])
		var b: Array = e["box"]
		var bx := Rect2(b[0], b[1], b[2], b[3])
		if Frames.loop_count(name) < 2:
			err("Мартин: нет кадров петли " + name)
			continue
		Frames.want_loop(name)
		Frames.flush()
		await _frames(2)
		for calm: bool in [false, true]:
			Settings.a11y["calm"] = calm
			Nav.go(sc)
			await _frames(3)
			Nav.current.st = 5.0                     # въезд слева закончился
			await _frames(2)
			var m := Nav.current.get_node_or_null("Martin") as Figure
			if m == null:
				err("Мартин: на экране %s нет фигуры Martin" % sc)
				continue
			if m.loop != name or not m.loop_still or m.box != bx.size or m.loop_box != Figure.idle_box(Rect2(Vector2.ZERO, bx.size)):
				err("Мартин (%s): не петлёй экрана %s (loop %s, бокс %s)" % [sc, name, m.loop, m.box])
			if m.live() == calm:
				err("Мартин (%s, calm=%s): %s" % [sc, calm, "петля" if m.live() else "картинка"])
			if not calm and (m.position != bx.position or m.rotation_degrees != 0.0):
				err("Мартин (%s): петля не на месте картинки — %s, поворот %.1f (ждали %s, 0)" % [sc, m.position, m.rotation_degrees, bx.position])
			if calm:
				continue
			var d := _idle_rect_err("martin.png", name, bx)
			worst = maxf(worst, d)
			if d > 0.02:
				err("Мартин (%s): рисунок в кадре петли %s мимо картинки на %.3f px" % [sc, name, d])
		out.append("%s — %s" % [sc, name])
	Settings.a11y["calm"] = calm0
	Nav.go("title")
	await _frames(2)
	for n: String in ["martin_idle", "brenna_wave", "magic_martin"]:
		Frames.want_loop(n)
	Frames.flush()
	await _frames(2)
	for bb: Array in [[24, 70, 150, 190], [24, 300, 210, 250], [525.5, 275, 230, 250], [24, 300, 90, 110], [986, 158, 46, 56]]:
		var bx2 := Rect2(bb[0], bb[1], bb[2], bb[3])           # «живой» Мартин (martin_idle) и Бренна во всех боксах
		for pair: Array in [["martin.png", "martin_idle"], ["master.png", "brenna_wave"]]:
			var d2 := _idle_rect_err(pair[0], pair[1], bx2)
			worst = maxf(worst, d2)
			if d2 > 0.02:
				err("%s: рисунок в кадре петли мимо картинки на %.3f px (бокс %s)" % [pair[1], d2, bx2])
	for bb: Array in [[24, 70, 150, 190], [24, 300, 210, 250]]:   # волшебство: портрет в кадре — на картинке
		var m := MagicPortrait.make("martin.png", Rect2(bb[0], bb[1], bb[2], bb[3]), 0.0, false)
		m.loop_name = "magic_martin"
		var e: Dictionary = Frames.magic.get("magic_martin", {})
		var fr := m.frame_rect()
		m.free()
		if e.is_empty() or fr.size == Vector2.ZERO:
			err("волшебство Мартина: нет magic_martin в anim_magic_index.json")
			continue
		var sz: Array = e["size"]
		var pr: Array = e["portrait"]
		var k := fr.size / Vector2(float(sz[0]), float(sz[1]))
		var inner := Rect2(fr.position + Vector2(float(pr[0]), float(pr[1])) * k, Vector2(float(pr[2]), float(pr[3])) * k)
		var d3 := _rect_err(inner, UI.fit_rect(Content.texture("martin.png").get_size(), Rect2(bb[0], bb[1], bb[2], bb[3])))
		worst = maxf(worst, d3)
		if d3 > 0.02:
			err("волшебство Мартина: портрет в кадре мимо картинки на %.3f px (бокс %s)" % [d3, bb])
	return "Мартин петлями экранов (%s), martin_idle, brenna_wave, magic_martin: рисунок в кадре на месте картинки (худший сдвиг %.3f px), «Без анимации» — картинка" % [", ".join(out), worst]


static func _rect_err(a: Rect2, b: Rect2) -> float:
	return maxf(maxf(absf(a.position.x - b.position.x), absf(a.position.y - b.position.y)),
		maxf(absf(a.end.x - b.end.x), absf(a.end.y - b.end.y)))


## Где рисунок картинки art в кадре петли name, нарисованном Figure.idle_rect в боксе bx, против самой картинки
## (UI.fit_rect), логические px. Рисунок в кадре — по нарезке idle_loop.py (idle.cut_h, IDLE_PAD), независимо от
## размера файла кадра (ужатый 348×400 — те же доли); пропорции кадра — проверка, что cut_h/pad те, с какими резали.
## Прежний расчёт (кадр вписан в idle_box с полем, округлённым до целых px; доли — от ужатого кадра) давал 0,8 px.
func _idle_rect_err(art: String, name: String, bx: Rect2) -> float:
	var st := Content.texture(art)
	var tex := Frames.loop_frame(name, 1.6)
	var r := Figure.idle_rect(art, bx)
	if st == null or tex == null:
		err("%s: нет картинки %s или кадров" % [name, art])
		return 0.0
	var idl: Dictionary = Content.consts.get("idle", {})
	var pad := float(idl.get("pad", 0.0))
	var oh := float(idl.get("cut_h", 0))
	var ow := roundf(oh * st.get_size().x / st.get_size().y)
	var fr: Vector2 = tex.get_size()
	if oh <= 0.0 or absf(fr.x / fr.y - ow / oh) > 0.005 or absf(r.size.x / r.size.y - ow / oh) > 0.005:
		err("%s: пропорции кадра %s не как у нарезки %dx%d (idle.cut_h в game_consts.json?)" % [name, fr, ow, oh])
	var iw := roundf(ow / (1 + 2 * pad))
	var ih := roundf(oh / (1 + 2 * pad))
	var k := r.size / Vector2(ow, oh)
	var inner := Rect2(r.position + Vector2(floorf((ow - iw) / 2), floorf((oh - ih) / 2)) * k, Vector2(iw, ih) * k)
	return _rect_err(inner, UI.fit_rect(st.get_size(), bx))


## «Живой» Мартин (IDLE_LOOPS martin.png → martin_idle, 20.11 как _martin_portrait_selftest в game.py): портрет его
## задания, пузырь реплики (90×110 и 46×56), после проезда и итог — петлёй, «Без анимации» — картинкой; волшебство
## начинается и кончается на кадре 0 петли (поза картинки): первое — пока петля стоит на кадре 0, после него петля с
## кадра 0, клик у стыка ждёт стыка, посреди петли — сразу. Портрет шагается вручную (1/30 с) — без скачков кадров.
func _flow_martin_live() -> String:
	var name := Figure.idle_loop("martin.png")
	var jid := ""
	for j: Dictionary in Content.jobs:
		if j.get("client_art", "") == "martin.png" and j.get("track", "") != "tech":
			jid = j["id"]
			break
	if name == "" or jid == "" or Frames.loop_count(name) < 2:
		err("«Живой» Мартин: нет петли %s или задания с martin.png" % name)
		return "«Живой» Мартин: нет данных"
	var n := Frames.loop_count(name)
	var per := n / Frames.anim_fps
	var calm0: bool = Settings.a11y.get("calm", false)
	var idle_t0 := Figure.idle_t
	Figure.idle_t = -1.0
	Settings.a11y["calm"] = false
	Frames.want_loop(name)
	Frames.flush()
	Nav.go("job", {"job": jid, "variant": 0})
	await _frames(2)
	var scr: Node = Nav.current
	var p: MagicPortrait = scr.get("portrait")
	p.set_process(false)
	if p.loop_name != "":
		Frames.want_loop(p.loop_name)
		Frames.flush()
	var step := func(k: int) -> void:
		for i in k:
			p._process(1.0 / 30)
	step.call(1)
	if not p._fig.live() or p.portrait_frame() != 0:
		err("Мартин в задании %s: портрет не петлёй %s на кадре 0 (кадр %d)" % [jid, name, p.portrait_frame()])
	var magic := p.loop_name
	var notes: Array = []
	if magic != "":
		var dur := p._dur()
		for i in int((float(Content.consts["magic"].get("hold", 3.0)) + 1) * 30):
			step.call(1)
			if p.playing():
				break
		if not p.playing() or p.portrait_frame() != 0:
			err("Мартин: волшебство не началось на кадре 0 петли (кадр %d)" % p.portrait_frame())
		step.call(int((dur - 0.15) * 30))                  # последние доли — под волшебством кадр 0
		if not p.playing() or p.portrait_frame() != 0:
			err("Мартин: к концу волшебства под ним не кадр 0 петли (кадр %d)" % p.portrait_frame())
		step.call(10)
		if p.playing() or not p._fig.live() or p.portrait_frame() < 0 or p.portrait_frame() > 4:
			err("Мартин: после волшебства петля не с кадра 0 (кадр %d)" % p.portrait_frame())
		p.idle_t0 = p.t - per + 0.2                      # до стыка 0,2 с: клик ждёт стыка
		var at := 0.0
		if not p.queue(true) or p.playing() or p.magic_at < 0.0:
			err("Мартин: клик у стыка петли не ждёт стыка")
		at = p.magic_at
		step.call(9)
		if not p.playing() or absf(p.magic_t0 - at) > 1e-6 or p.portrait_frame() != 0:
			err("Мартин: волшебство по клику не началось на стыке (кадр петли %d)" % p.portrait_frame())
		step.call(int(dur * 30) + 3)
		p.idle_t0 = p.t - 1.0                            # середина петли: клик — сразу (переход fade)
		if not p.queue(true) or not p.playing():
			err("Мартин: клик посреди петли не запустил волшебство сразу")
		notes.append("волшебство %s на стыке" % magic)
	else:
		err("Мартин: нет петли волшебства у задания %s" % jid)
	for bx: Rect2 in [Rect2(24, 300, 90, 110), Rect2(986, 158, 46, 56)]:   # пузырь реплики — петлёй
		if not Figure.idle_pick("martin.png", bx, 0.5)["live"]:
			err("Мартин: пузырь реплики %s не петлёй %s" % [bx.size, name])
	var mentor: SpeechBubble = scr.get("_mentor")
	if mentor.speaker_img("Мартин: «Проверка.»") != "martin.png":
		err("Мартин: пузырь реплики — не его портрет")
	scr.set("phase", "test")                             # после проезда — петлёй с кадра 0
	scr.call("rebuild")
	await _frames(1)
	scr.call("_ride_finished")
	await _frames(1)
	var after: Figure = scr.get("_after")
	if after == null or not after.visible or not after.live() or int(after.t * Frames.anim_fps) % n > 3:
		err("Мартин: после проезда не петлёй %s с кадра 0" % name)
	scr.call("finish_test")                              # итог: подпрыг на кадре 0, петлёй
	await _frames(2)
	if Nav.current_name != "result":
		err("Мартин: итог не открылся")
	else:
		var rp: MagicPortrait = Nav.current.get("portrait")
		if not rp._fig.live() or rp.portrait_frame() != 0:
			err("Мартин на итоге: не петлёй на кадре 0 при подпрыге (кадр %d)" % rp.portrait_frame())
	Settings.a11y["calm"] = true                         # «Без анимации» — везде картинка
	Nav.go("job", {"job": jid, "variant": 0})
	await _frames(3)
	var pc: MagicPortrait = Nav.current.get("portrait")
	if pc._fig.live() or pc.portrait_frame() >= 0 or Figure.idle_pick("martin.png", Rect2(24, 300, 90, 110), 0.5)["live"]:
		err("Мартин «Без анимации»: портрет или пузырь петлёй, ждали картинку")
	Nav.current.set("phase", "test")
	Nav.current.call("rebuild")
	await _frames(1)
	Nav.current.call("_ride_finished")
	await _frames(1)
	var ac: Figure = Nav.current.get("_after")
	if ac != null and ac.live():
		err("Мартин «Без анимации»: после проезда петлёй")
	Nav.current.call("finish_test")
	await _frames(2)
	if Nav.current_name == "result" and (Nav.current.get("portrait") as MagicPortrait)._fig.live():
		err("Мартин «Без анимации»: на итоге петлёй")
	Settings.a11y["calm"] = calm0
	Figure.idle_t = idle_t0
	Nav.go("title")
	await _frames(2)
	return "«Живой» Мартин %s: портрет, пузырь, после проезда, итог — петлёй (%s), «Без анимации» — картинкой" % [
		name, ", ".join(notes)]


## Бренна «живая» (IDLE_LOOPS/IDLE_PAD из game_consts.json): петля выбрана, «Без анимации» — картинка, рисунок в кадре
## петли стоит там же, где картинка (±2 px), во всех боксах, где её рисуют; Гильдия, про-задание, итог — Figure с петлёй.
func _flow_brenna() -> String:
	var idle: Dictionary = Content.consts.get("idle", {})
	var pad := float(idle.get("pad", 0.0))
	var loops: Dictionary = idle.get("loops", {})
	if pad <= 0.0 or loops.get("master.png", "") == "":
		err("Бренна: нет idle.pad / idle.loops в game_consts.json")
		return "Бренна: нет данных"
	var name: String = loops["master.png"]
	if Frames.loop_count(name) < 2:
		err("Бренна: нет кадров петли " + name)
		return "Бренна: нет кадров"
	Frames.want_loop(name)
	Frames.flush()
	await _frames(2)
	var calm0: bool = Settings.a11y.get("calm", false)
	Settings.a11y["calm"] = false
	var boxes := [Rect2(UI.W - 300, 130, 200, 280), Rect2(986, 158, 46, 56), Rect2(24, 300, 90, 110),
		Rect2(24, 70, 150, 190), Rect2(24, 300, 210, 250)]
	var worst := 0.0
	for bx: Rect2 in boxes:
		var p := Figure.idle_pick("master.png", bx, 1.6)
		if not p["live"]:
			err("Бренна: в боксе %s не петля" % bx.size)
			continue
		if p["rect"] != Figure.idle_rect("master.png", bx):
			err("Бренна: бокс %s — кадр не в Figure.idle_rect" % bx.size)
		var d := _idle_rect_err("master.png", name, bx)      # рисунок в кадре — на картинке (20.11: было ±2 px)
		worst = maxf(worst, d)
		if d > 0.02:
			err("Бренна: бокс %s — рисунок в петле мимо картинки на %.3f px" % [bx.size, d])
	Settings.a11y["calm"] = true
	if Figure.idle_pick("master.png", boxes[0], 1.6)["live"]:
		err("Бренна: «Без анимации» — всё равно петля")
	Settings.a11y["calm"] = false
	# экраны: Гильдия, про-задание с Бренной, — Figure с петлёй, без покачивания
	Nav.go("guild")
	await _frames(3)
	var g := Nav.current.get_node_or_null("Brenna") as Figure
	if g == null or g.loop != name or not g.loop_still or g.loop_box != Figure.idle_box(Rect2(Vector2.ZERO, g.box)):
		err("Бренна: в Гильдии не петлёй (%s)" % (g.loop if g else "нет"))
	var tj := ""
	for j: Dictionary in Content.tech_jobs:
		if j.get("client_art", "") == "master.png":
			tj = j["id"]
			break
	if tj != "":
		var scr: Node = await _open_tech(tj)
		var c := scr.get_node_or_null("Client") as Figure
		if c == null or c.loop != name or not c.loop_still:
			err("Бренна: портрет про-задания %s не петлёй" % tj)
	Settings.a11y["calm"] = calm0
	return "Бренна петлёй %s: Гильдия, пузырь, портрет и итог про-задания; рисунок совпадает с картинкой (худший сдвиг %.3f px), «Без анимации» — картинка" % [name, worst]


# ======================= порядок обхода с клавиатуры =======================

## Список клавиатуры против game.py (content/kb_order_ref.json — tools/kb_order_ref.py): каждое состояние ставит
## tests/shots.gd stage() (те же имена и шаги, что tools/ref_shots.py), список Godot — A11y.kb_items(). Пункт в
## пункт: группа и подпись; «Кнопки» (подписи game.py собирает из нарисованного текста) — группа и место, подпись
## сверяется отдельно (kb_order_diff.txt). Перемешанные варианты диагноза — без номера, набором.
## Итог: «KB ORDER: N состояний, M пунктов, расхождений K».
func _kb_order_ref(langs: Array) -> String:
	var path := "res://content/kb_order_ref.json"
	if not FileAccess.file_exists(path):
		err("нет content/kb_order_ref.json — запусти tools/kb_order_ref.py")
		return ""
	var ref: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
	var stager: Node = (load("res://tests/shots.gd") as GDScript).new()
	stager.set("stage_only", true)
	add_child(stager)
	var lang0 := Loc.code
	var voices0: bool = Settings.a11y.get("voices", true)
	Settings.a11y["voices"] = false
	seed(1)
	Figure.idle_t = 1.6
	Engine.time_scale = 25.0
	var n_states := 0
	var n_items := 0
	var n_bad := 0
	var n_lab := 0
	var n_known := 0
	var n_tools := 0                         # известное (28.11): порядок инструментов на ПК — кнопка рук и кучки
	var n_sound := 0                         # известное (28.11): кнопка звука в шапке (в game.py — только картинка)
	var report: PackedStringArray = []
	for lang: String in langs:
		SaveGame.reset()                         # каждый язык эталона — свой процесс game.py с нуля
		for name: String in ref[lang]:
			SaveGame.tutorial_skipped = true
			Settings.lang = lang
			Loc.code = lang
			var sname := "title_en" if lang == "en" and name == "title" else name
			if lang == "ru" and name == "title_en":
				continue
			await stager.stage(sname)
			Settings.lang = lang
			Loc.code = lang
			if Nav.current_name == "seating" and name.ends_with("_good"):
				Nav.current.refresh()               # снимок ставит ползунки кодом — подписи пересчитать
			await _frames(2)
			var want: Array = ref[lang][name]
			var got: Array = kb_rows()
			var n_snd := got.size()                  # известное (28.11): кнопка звука в шапке — в game.py её нет
			got = got.filter(func(r: Array) -> bool: return not (r[0] == "Меню" and str(r[1]) in KB_SOUND))
			n_snd -= got.size()
			n_sound += n_snd
			var cmp: Array = _kb_cmp(want, got)
			n_states += 1
			n_items += want.size()
			n_bad += cmp[0] + cmp[2]
			n_lab += cmp[1]
			n_tools += cmp[2]
			n_known += cmp[2]
			if KB_KNOWN.has(name):
				n_known += cmp[0]
			if cmp[0] > 0 or cmp[1] > 0 or cmp[2] > 0:
				report.append("== %s %s: расхождений %d, подписей «Кнопки» %d%s%s" % [lang, name, cmp[0] + cmp[2], cmp[1],
					(" — известное: " + KB_KNOWN[name]) if KB_KNOWN.has(name) else "",
					(" — известное: порядок инструментов (%d) — " % cmp[2] + KB_TOOLS_ORDER) if cmp[2] > 0 else ""])
				for i in maxi(want.size(), got.size()):
					var w: Array = want[i] if i < want.size() else ["—", "", ""]
					var g: Array = got[i] if i < got.size() else ["—", ""]
					var mark := "  " if _kb_same(w, g) else ("~ " if w[0] == g[0] else "X ")
					report.append("%s%-12s %-60s | %-12s %s" % [mark, w[0], str(w[1]).left(60), g[0], str(g[1]).left(60)])
			stager.unstage(sname)
	Engine.time_scale = 1.0
	stager.queue_free()
	Loc.code = lang0
	Settings.lang = lang0
	Settings.a11y["voices"] = voices0
	var out := ProjectSettings.globalize_path("res://tests/out")
	DirAccess.make_dir_recursive_absolute(out)
	var f := FileAccess.open(out.path_join("kb_order_diff.txt"), FileAccess.WRITE)
	f.store_string("
".join(report) + "
")
	f.close()
	var line := "KB ORDER: %d состояний, %d пунктов, расхождений %d (из них известных %d, в том числе порядок инструментов в кучках %d; подписей «Кнопки» не как в game.py: %d; известное — кнопка звука в шапке: %d пунктов)" % [
		n_states, n_items, n_bad, n_known, n_tools, n_lab, n_sound]
	print(line)
	if n_bad > n_known:
		err(line + " — tests/out/kb_order_diff.txt")
	return line


## Список клавиатуры сейчас: [группа, подпись].
func kb_rows() -> Array:
	var out: Array = []
	for c: Control in A11y.kb_items():
		out.append([A11y.group_of(c), Speech.clean(A11y.label_of(c))])
	return out


const KB_SHUFFLED := ["Диагноз", "Выводы", "Варианты"]
## Кнопка звука в шапке (28.11, владелец; в game.py — только картинка «без звука»): пункт «Меню» рядом с шестерёнкой.
const KB_SOUND := ["Звук включён. Выключить", "Звук выключен. Включить", "Sound is on. Turn off", "Sound is off. Turn on"]
## Намеренное отличие от game.py (28.11, решение владельца): в ремонте инструменты идут в видимом порядке — кнопка
## «Руки и глаза», потом кучки по назначению (tool_panel.gd PH_GROUPS), а к подписи добавлена кучка. Сверяется набором:
## те же инструменты с теми же подписями (без названия кучки); пункты не на своём месте — известные (n_tools).
const KB_TOOLS_ORDER := "кнопка рук и кучки по назначению вместо порядка tools.json (28.11, владелец), набор и подписи совпадают"
## Расхождения, которые не от порядка обхода (описаны в PORT_PLAN, шаг 4): в счёт идут, ошибкой не считаются.
const KB_KNOWN := {
	"help": "справка F1 в game.py — один пункт «Закрыть справку» (Enter/Esc), в Godot у окна справки пунктов нет: Esc/Enter/F1 закрывают так же",
	"settings_graphics": "в Godot нет пунктов «разрешение» (АВТО / 1280×720) и «3D через видеокарту» — их нет в переносе",
}


static func _kb_norm(g: String, l: String) -> String:
	if g == "Инструменты":                   # «Насос. Колесо и шина. …» → «Насос. …» (кучка — только в Godot, 28.11)
		for grp: Array in ToolPanel.PH_GROUPS:
			for h: String in [str(grp[1]), str(grp[2])]:
				l = l.replace(". " + h.substr(0, 1) + h.substr(1).to_lower() + ".", ".")
		return l
	if g == "Диагноз":
		return RegEx.create_from_string("^[^:]+ [0-9]+: ").sub(l, "")
	if g == "Поле":                            # коды Godot и game.py — разные строки (zlib), смысл тот же
		return RegEx.create_from_string("\\b([PJR])\\.\\S+").sub(l, "$1.<код>", true)
	return l


func _kb_same(w: Array, g: Array) -> bool:
	return w[0] == g[0] and (w[0] == "Кнопки" or w[0] in KB_SHUFFLED or _kb_norm(w[0], w[1]) == _kb_norm(g[0], g[1]))


## [расхождений (группа не та / подпись особого пункта не та / лишний или недостающий пункт), подписей «Кнопки»].
## Третье — пункты «Инструменты» не на своём месте при том же наборе (известное: KB_TOOLS_ORDER).
func _kb_cmp(want: Array, got: Array) -> Array:
	var bad := absi(want.size() - got.size())
	var lab := 0
	var tools_moved := 0
	var diag_w: Array = []
	var diag_g: Array = []
	var tw: Array = []
	var tg: Array = []
	for i in mini(want.size(), got.size()):
		var w: Array = want[i]
		var g: Array = got[i]
		if w[0] == "Инструменты" and g[0] == "Инструменты":
			tw.append(_kb_norm(w[0], w[1]))
			tg.append(_kb_norm(g[0], g[1]))
			if tw[-1] != tg[-1]:
				tools_moved += 1
			continue
		if w[0] != g[0]:
			bad += 1
		elif w[0] in KB_SHUFFLED:               # варианты перемешаны (shuffle_answers) — сверяем набором
			diag_w.append(_kb_norm(w[0], w[1]))
			diag_g.append(_kb_norm(g[0], g[1]))
		elif w[0] == "Кнопки":
			if w[1] != g[1]:
				lab += 1
		elif _kb_norm(w[0], w[1]) != _kb_norm(g[0], g[1]):
			bad += 1
	diag_w.sort()
	diag_g.sort()
	for i in diag_w.size():
		if diag_w[i] != diag_g[i]:
			bad += 1
	var tws := tw.duplicate()
	var tgs := tg.duplicate()
	tws.sort()
	tgs.sort()
	if tws != tgs:                           # набор инструментов или подпись не та — настоящее расхождение
		bad += tools_moved
		tools_moved = 0
	return [bad, lab, tools_moved]


# ======================= прохождение одними клавишами (art_tests/keyboard_playthrough.py) =======================

var kb_presses: int = 0
var speech_sound_known: int = 0          # озвучка фокуса: состояний с кнопкой звука в «Меню» (известное, 28.11)
var speech_tools_known: int = 0          # озвучка фокуса: состояний, где инструменты в порядке кучек (известное, 28.11)


## Фокус клавиатуры на пункт c: в режиме «arrows» — только стрелкой ↓ по списку (как незрячий игрок, слушающий
## подписи), иначе — сразу (grab_focus, прежние проверки).
func _kb_focus_on(c: Control) -> void:
	if ctl_mode != "arrows":
		c.grab_focus()
		await _frames(1)
		return
	var n: int = A11y.kb_items().size() + 2
	for _i in n:
		if A11y.kb_cur == c and c.has_focus():
			return
		await _key(KEY_DOWN)
	err("стрелками не дошли до «%s» (%s); в списке: %s" % [c.name, A11y.label_of(c),
		A11y.kb_items().map(func(x: Control) -> String: return str(x.name))])


func _kb_press_on(c: Control) -> void:
	await _kb_focus_on(c)
	if A11y.kb_cur == c:
		await _key(KEY_ENTER)


## Как art_tests/keyboard_playthrough.py: титул и вступление — Enter; все задания мастерской, все про-задания
## Гильдии; в мастерской Tab → клиенты → Enter → двойной Esc; примерка (ползунки ← →) и настройки — только
## стрелки, Tab, Enter, Esc (события клавиш, без мыши и без фокуса кодом).
func _flow_arrows() -> String:
	ctl_mode = "arrows"
	kb_presses = 0
	SaveGame.reset()
	SaveGame.ending_seen = true                  # вечеринка после 21-го ремонта — не в этой проверке
	Nav.go("title")
	await _frames(2)
	Nav.current.st = 3.0
	await _frames(2)
	await _key(KEY_ENTER)
	await _frames(2)
	for _i in 12:
		if Nav.current_name != "intro":
			break
		await _key(KEY_ENTER)
		await _frames(1)
	if Nav.current_name != "job" or Nav.current.job.get("id") != "flat":
		err("клавиши: титул и вступление по Enter не привели к первому заданию (%s)" % Nav.current_name)
	SaveGame.tutorial_skipped = true
	var n_jobs := 0
	for job: Dictionary in Content.jobs:
		var e0 := errors.size()
		await _flow_repair(str(job["id"]) + ":0", true)
		if errors.size() == e0:
			n_jobs += 1
	var n_tech := 0
	for tj: Dictionary in Content.tech_jobs:
		var e0 := errors.size()
		await _flow_tech_events(tj["id"], false, true)
		if errors.size() == e0:
			n_tech += 1
	Nav.go("hub")
	await _frames(2)
	await _key(KEY_TAB)                          # фокуса ещё нет — Tab: первая группа, «Клиенты»
	if A11y.kb_cur == null or A11y.group_of(A11y.kb_cur) != "Клиенты":
		err("клавиши: Tab в мастерской не встал на клиентов")
	await _key(KEY_ENTER)
	await _frames(2)
	if Nav.current_name != "job":
		err("клавиши: Enter на клиенте не открыл задание")
	await _key(KEY_ESCAPE)
	await _key(KEY_ESCAPE)
	await _frames(2)
	if Nav.current_name != "hub":
		err("клавиши: двойной Esc не вывел из задания")
	var e1 := errors.size()
	await _sw_seat_settings()
	ctl_mode = ""
	var line := "ПРОЙДЕНО С КЛАВИАТУРЫ: %d заданий, %d Гильдии, %s. Нажатий: %d" % [n_jobs, n_tech,
		"примерка, настройки" if errors.size() == e1 else "примерка/настройки — ОШИБКИ", kb_presses]
	print(line)
	return line
