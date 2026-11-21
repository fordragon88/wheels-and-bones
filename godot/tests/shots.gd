extends Node
## Снимки экранов 1280×720 для сверки с pygame-версией (эталоны — tests/ref/, их делает tools/ref_shots.py):
##   D:\Godot\Godot_v4.7.2-stable_win64.exe --path godot --audio-driver Dummy -- --test --shots [имя …]
## Без имён — все; с «--calm» перед «--shots» — «Без анимации», файлы calm_<имя>.png; с «--big» — текст 150 %, big_<имя>.png;
## с «--native» — в размере окна (`--resolution 2220x1080` до `--`), без ужатия до 1280×720. Снимки: tests/shots/<имя>.png (в git не хранятся). После снимков игра закрывается сама.
## Ввод мыши в окне на время снимков выключен (курсор над окном не даёт подсветку наведения).

const IDLE_T := 1.6                         # кадр петли «живых» персонажей на снимках = IDLE_T в tools/ref_shots.py
const ALL := ["title", "title_en", "hub", "job_flat_diagnose", "job_flat_inspected",
	"job_joystick_diagnose", "job_joystick_inspected", "job_flat_repair", "mini_pump", "mini_gap", "mini_ping",
	"mini_meter", "ride_martin", "ride_zix", "result_lift", "hub_done", "intro_1", "intro_2", "intro_3", "intro_4",
	"intro_5", "garage", "garage_open", "ending", "credits", "feedback_general", "feedback_dispute", "help",
	"settings_sound", "settings_graphics", "settings_access", "settings_game", "guild_open", "tech_ops", "tech_manual",
	"tech_spec", "tech_mini", "tech_failed", "tech_test", "tech_ride", "tech_result", "guild_done", "exam_ticket",
	"exam_failed", "exam_passed", "guild_diploma", "seat_lessons", "seat_lesson_slump", "seat_lesson_norm",
	"seat_lesson_measure", "seat_fit_troll", "seat_fit_troll_good", "seat_fit_golem", "seat_fit_dryad_side", "seat_quiz_q1",
	"seat_quiz_mid", "seat_quiz_wrong", "seat_quiz_right", "seat_quiz_myth", "seat_quiz_pass", "seat_fit_dryad",
	"seat_fit_dryad_good", "seat_fit_owl", "seat_fit_owl_good", "seat_fit_orc", "seat_fit_orc_good", "seat_lesson_front",
	"seat_lesson_front_norm", "seat_quiz_wedge", "seat_quiz_wedge_after", "seat_quiz_pads", "seat_quiz_pads_after",
	"share_paste", "share_confirm", "share_builder", "hub_assign", "share_summary", "share_result", "share_resume",
	"scan_hub", "scan_job", "scan_settings", "scan_seat", "scan_share", "tech_ride_t_q6brake_mid",
	"tech_ride_t_q6brake_after", "tech_ride_toe_mid", "tech_ride_toe_after"]

var out_dir := ""
var stage_only := false                     # браузер, замер кадров/с: только stage()/unstage() по window.wnbStage
var _staged := ""


func _ready() -> void:
	if stage_only:
		return
	out_dir = ProjectSettings.globalize_path("res://tests/shots")
	DirAccess.make_dir_recursive_absolute(out_dir)
	FileAccess.open(out_dir.path_join(".gdignore"), FileAccess.WRITE)   # редактор не импортирует снимки
	_run.call_deferred()


func _wait(secs: float) -> void:
	await get_tree().create_timer(secs).timeout


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	if img.get_size() != Vector2i(1280, 720) and not "--native" in OS.get_cmdline_user_args():
		img.resize(1280, 720, Image.INTERPOLATE_LANCZOS)
	var pre := ("calm_" if Settings.calm() else "") + ("big_" if int(Settings.a11y.get("text", 0)) == 3 else "")
	img.save_png(out_dir.path_join(pre + name + ".png"))
	print("shot ", name, " ", Nav.current_name)


## Про-задание для снимка: карточки операций — в порядке данных (как ref_shots.py), иначе снимки не сравнить.
func _tech_open(jid: String, exam: bool = false) -> Node:
	Nav.go("tech", {"job": jid, "exam": exam})
	await _wait(0.1)
	var scr: Node = Nav.current
	scr.step_order.clear()
	for st: Dictionary in scr.job["steps"]:
		scr.step_order.append(st["id"])
	scr.rebuild()
	Frames.want_turntable(scr.job["chair_art"])
	Frames.flush()
	Nav.toast.timer = 0.0
	return scr


func _tech_do(scr: Node, sid: String) -> void:
	var st: Dictionary = scr.step_by_id(sid)
	scr.select_tool(st["tool"])
	scr.op_clicked(sid)
	if scr.spec_dlg:
		for i in st["spec"]["options"].size():
			if st["spec"]["options"][i][1]:
				scr.choose_spec(i)
	if scr.mini:
		var m: MiniGame = scr.mini
		if m.kind == "meter":
			for i in m.cfg["options"].size():
				if m.cfg["options"][i][1]:
					m.meter(i)
					break
		elif m.kind == "ping":
			for i: int in m.dull.keys():
				m.ping(i)
		else:
			m.value = int(m.cfg.get("lo", 0))
			if m.kind == "gap":
				m.gap_check()
			else:
				m.pump_done()


func _tech_shot(name: String) -> void:
	var scr: Node
	match name:
		"tech_ops":
			scr = await _tech_open("truing")
			scr.select_tool(scr.job["steps"][0]["tool"])
			await _wait(2.0)
		"tech_ops_t_battery", "tech_ops_t_battery_q6", "tech_ops_t_pulse6", "tech_ops_t_q6brake":   # про-задания 13–16 шагов
			scr = await _tech_open(name.trim_prefix("tech_ops_"))
			scr.select_tool(scr.job["steps"][0]["tool"])
			await _wait(2.0)
		"tech_manual":
			scr = await _tech_open("truing")
			scr.open_manual()
			await _wait(0.5)
		"tech_spec":
			scr = await _tech_open("truing")
			for p: String in scr.job.get("manual", []):
				scr.manual_viewed[p] = true
			for st: Dictionary in scr.job["steps"]:
				if st.get("spec") is Dictionary:
					scr.select_tool(st["tool"])
					scr.op_clicked(st["id"])
					break
				_tech_do(scr, st["id"])
			Nav.toast.timer = 0.0
			await _wait(0.5)
		"tech_mini":
			scr = await _tech_open("toe")
			for st: Dictionary in scr.job["steps"]:
				if st.get("mini") is Dictionary:
					scr.select_tool(st["tool"])
					scr.op_clicked(st["id"])
					break
				_tech_do(scr, st["id"])
			Nav.toast.timer = 0.0
			await _wait(0.6)
		"tech_failed":
			scr = await _tech_open("t_battery")
			var st: Dictionary = scr.step_by_id("p_disc_neg")
			scr.select_tool(st["tool"])
			scr.op_clicked("p_disc_neg")
			await _wait(1.2)
		"tech_ride_t_q6brake_mid", "tech_ride_toe_mid", "tech_ride_t_q6brake_after", "tech_ride_toe_after":
			var jid := "t_q6brake" if name.contains("t_q6brake") else "toe"
			if not (Nav.current_name == "tech" and Nav.current.job["id"] == jid):
				scr = await _tech_open(jid)
				for p: String in scr.job.get("manual", []):
					scr.manual_viewed[p] = true
				for st: Dictionary in scr.job["steps"]:
					_tech_do(Nav.current, st["id"])
				scr = Nav.current
				scr.mistakes = 0
				Frames.want_loop(RideView.tech_loop(jid))
				Frames.flush()
				Nav.toast.timer = 0.0
				await _wait(1.0)
				scr._test_pressed()
			scr = Nav.current
			var secs: float = scr.ride.secs()
			if name.ends_with("_mid"):
				scr.ride.t0 = scr.ride.t - secs / 2 + 0.03
			else:
				scr.ride.t0 = scr.ride.t - secs - 1.0
				await _wait(0.3)
			await get_tree().process_frame
			await get_tree().process_frame
		"tech_test", "tech_ride", "tech_result":
			scr = await _tech_open("truing")
			for p: String in scr.job.get("manual", []):
				scr.manual_viewed[p] = true
			for st: Dictionary in scr.job["steps"]:
				_tech_do(Nav.current, st["id"])
			scr = Nav.current
			scr.mistakes = 0
			Nav.toast.timer = 0.0
			await _wait(1.0)
			if name != "tech_test":
				Frames.want_loop(RideView.tech_loop("truing"))
				Frames.flush()
				scr._test_pressed()
				await _wait(2.0)
			if name == "tech_result":
				Nav.go("result", {"job": scr.job, "stars": 3, "gag": Content.talk["martin"]["good"][0], "mistakes": 0})
				await _wait(3.0)
		"exam_ticket":
			scr = await _tech_open("truing", true)
			await _wait(1.5)
		"exam_failed":
			scr = await _tech_open("truing", true)
			var first: Dictionary = scr.job["steps"][0]
			for k in 4:
				if Nav.current_name == "tech":
					scr.select_tool("lube")
					scr.op_clicked(first["id"])
			await _wait(1.2)
		"exam_passed":
			Nav.go("exam_result", {"mistakes": 0})
			await _wait(3.0)


## Кабинет посадки — те же состояния, что в ref_shots.py (варианты ответов зачёта — в порядке данных).
func _seat_shot(name: String) -> void:
	if Nav.current_name != "seating":
		SaveGame.done.clear()
		SaveGame.done["flat"] = true
		SaveGame.seat_done.clear()
		SaveGame.seat_quiz_ok = false
		Nav.go("seating")
		await _wait(0.1)
		Nav.current.quiz = Content.seating["quiz"].duplicate(true)
		Nav.current.refresh()
	var scr: Node = Nav.current
	var m: Dictionary = Content.seating["mentor"]
	match name:
		"seat_lessons":
			await _wait(2.5)
		"seat_lesson_slump":
			scr.pick_lesson(1)
			await _wait(2.5)
		"seat_lesson_norm":
			scr.toggle_demo()
			await _wait(0.5)
		"seat_lesson_measure":
			scr.pick_lesson(5)
			await _wait(2.5)
		"seat_fit_troll":
			scr.tab = "fit"
			scr.load_case(0)
			scr.refresh()
			await _wait(2.5)
		"seat_fit_troll_good":
			var c0: Dictionary = scr.cases()[0]
			scr.cfg["depth"] = int(c0["body"]["thigh"]) - 5
			scr.cfg["leg"] = int(c0["body"]["shank"])
			scr.cfg["back_h"] = (int(c0["back"][0]) + int(c0["back"][1])) / 2
			scr.cfg["back_a"] = (int(c0["angle"][0]) + int(c0["angle"][1])) / 2
			await _wait(0.5)
		"seat_fit_golem":
			scr.pick_case(3)
			await _wait(2.5)
		"seat_fit_dryad_side":
			scr.pick_case(6)
			scr.toggle_view()
			await _wait(2.5)
		"seat_quiz_q1":
			scr.set_tab("quiz")
			await _wait(2.5)
		"seat_quiz_mid":
			for i in scr.quiz[0]["options"].size():
				if not scr.quiz[0]["options"][i][1]:
					scr.quiz_pick(i)
					break
			await _wait(0.5)
			scr.fix_t0 = scr.t - 0.31             # середина перехода (у эталона — чуть меньше 0,5: флаги ошибки ещё видны)
			await get_tree().process_frame
			await get_tree().process_frame
		"seat_quiz_wrong":
			scr.fix_t0 = scr.t - 5.0
			scr.tick(0.0)
			await _wait(2.5)
		"seat_quiz_right":
			scr.quiz_i = 1
			scr.picked = -1
			for i in scr.quiz[1]["options"].size():
				if scr.quiz[1]["options"][i][1]:
					scr.quiz_pick(i)
					break
			await _wait(2.5)
		"seat_quiz_myth":
			scr.quiz_i = 3
			scr.picked = -1
			scr.refresh()
			await _wait(1.0)
		"seat_quiz_pass":
			scr.quiz_done = true
			scr.score = 6
			scr.say = m["pass"]
			scr.refresh()
			await _wait(2.5)
		"seat_fit_dryad", "seat_fit_owl", "seat_fit_orc":
			scr.quiz_done = false
			scr.score = 0
			scr.tab = "fit"
			scr.load_case({"seat_fit_dryad": 6, "seat_fit_owl": 7, "seat_fit_orc": 8}[name])
			scr.refresh()
			await _wait(2.5)
		"seat_fit_dryad_good", "seat_fit_owl_good", "seat_fit_orc_good":
			var c: Dictionary = scr.cases()[scr.case_i]
			var sol := _seat_solve(c, scr.slider_keys(), scr.cfg)
			for k: String in sol:
				scr.cfg[k] = sol[k]
			await _wait(0.5)
		"seat_lesson_front":
			scr.tab = "lessons"
			scr.refresh()
			scr.pick_lesson(3)
			await _wait(2.5)
		"seat_lesson_front_norm":
			scr.toggle_demo()
			await _wait(0.5)
		"seat_quiz_wedge", "seat_quiz_pads":
			scr.tab = "quiz"
			scr.say = m["quiz"]
			scr.quiz_i = 5 if name == "seat_quiz_wedge" else 6
			scr.picked = -1
			scr.refresh()
			await _wait(2.5 if name == "seat_quiz_wedge" else 1.0)
		"seat_quiz_wedge_after", "seat_quiz_pads_after":
			var opts: Array = scr.quiz[scr.quiz_i]["options"]
			for i in opts.size():
				if bool(opts[i][1]) == (name == "seat_quiz_wedge_after"):
					scr.quiz_pick(i)
					break
			scr.fix_t0 = scr.t - 5.0
			await _wait(2.5)
	Nav.toast.timer = 0.0


## Рамка «одной кнопки» на выделенном пункте — те же состояния, что в ref_shots.py.
func _scan_shot(name: String) -> void:
	Settings.a11y["scan"] = 1
	A11y.scan_sub = {}
	Share._close_dlg()
	Nav.close_settings()
	SaveGame.reset()
	SaveGame.done["flat"] = true
	SaveGame.done["brake"] = true
	SaveGame.tutorial_skipped = true
	var target: Control
	match name:
		"scan_hub":
			Nav.go("hub")
			await _wait(1.5)
			target = Nav.current.get_node("Card_brake")
		"scan_job":
			Nav.go("job", {"job": "flat", "variant": 0})
			await _wait(1.0)
			target = Nav.current.get_node("Part_" + str(Nav.current.job["parts"][1]))
		"scan_settings":
			Nav.go("hub")
			await _wait(0.3)
			SettingsDialog.tab = "access"
			Nav.open_settings()
			await _wait(0.2)
			target = Nav.settings.get_node("Acc_calm")
		"scan_seat":
			Nav.go("seating")
			await _wait(0.2)
			Nav.current.set_tab("fit")
			await _wait(1.0)
			target = Nav.current.sliders["leg"]
		"scan_share":
			Nav.go("hub")
			await _wait(0.3)
			Share.open({"mode": "paste"})
			await _wait(0.1)
			target = Share.dlg.get_node("Field")
	UI.kb_active = true
	target.grab_focus()
	if name == "scan_seat":
		A11y.scan_sub = {"ctl": target, "i": 1}
	A11y._scan_next = A11y.scan_t + 1e6
	Nav.toast.timer = 0.0
	await _wait(0.4)


## Коды и ссылки — те же состояния, что в ref_shots.py (share_resume — новое окно, эталона нет).
func _share_shot(name: String) -> void:
	if name == "share_paste" or Nav.current_name != "hub":
		SaveGame.reset()
		for j: String in ["flat", "brake", "spokes"]:
			SaveGame.done[j] = true
		SaveGame.garage = [["flat", 3], ["brake", 2], ["spokes", 1]]
		SaveGame.seat_done["seat_elf"] = true
		Share.resume_asked = true
		Nav.go("hub")
		await _wait(0.5)
	match name:
		"share_paste":
			Share.open({"mode": "paste", "text": Share.encode("P", Share.progress_pack())})
		"share_confirm":
			Share.dlg_action(Share.dlg, "apply")
		"share_builder":
			Share.open({"mode": "builder", "sel": ["spokes", "caster", "seat_elf"], "name": "Анна"})
		"hub_assign":
			Share._close_dlg()
			Share.start_assignment(Share.assign_parse({"jobs": "spokes,caster,lift", "seat": "seat_elf", "from": "Анна",
				"title": "Неделя 1"}))
			SaveGame.assign_record("spokes", 2, 95)
			Nav.go("hub")
			await _wait(1.5)
		"share_summary":
			for r: Array in [["caster", 0, 61], ["lift", 1, 200], ["seat_elf", 3, 75]]:
				SaveGame.assign_record(r[0], r[1], r[2])
			Share.open({"mode": "summary"})
		"share_result":
			var res := Share.assign_result()
			Share._close_dlg()
			SaveGame.exit_assignment()
			Nav.go("hub")
			await _wait(0.4)
			Share.open({"mode": "result", "res": res})
		"share_resume":
			Share._close_dlg()
			SaveGame.assign["active"] = true
			SaveGame.assign["done"].erase("seat_elf")
			Share.resume_asked = false
			Share.link_launch = false
			Nav.go("hub")
			await _wait(0.4)
	Nav.toast.timer = 0.0
	await _wait(0.5)


## Верная посадка перебором по одному ползунку (как seat_solve в ref_shots.py).
func _seat_solve(c: Dictionary, keys: Array, cfg0: Dictionary) -> Dictionary:
	var cfg := cfg0.duplicate()
	var score := func(x: Dictionary) -> int:
		var n := 0
		for ch: Array in SeatLogic.seat_eval(c, x)[0]:
			n += 1 if ch[1] else 0
		return n
	var total: int = SeatLogic.seat_eval(c, cfg)[0].size()
	for _r in 6:
		for k: String in keys:
			var sl: Array = SeatLogic.sliders()[k]
			var best: int = score.call(cfg)
			var best_v: int = cfg[k]
			for v in range(int(sl[2]), int(sl[3]) + 1):
				var x := cfg.duplicate()
				x[k] = v
				var sc: int = score.call(x)
				if sc > best:
					best = sc
					best_v = v
			cfg[k] = best_v
		if score.call(cfg) == total:
			break
	return cfg


func _to_repair(jid: String) -> Node:
	Nav.go("job", {"job": jid, "variant": 0})
	Frames.want_loop("barty_wave")
	Frames.flush()
	await _wait(0.5)
	var scr: Node = Nav.current
	for pid: String in scr.job["parts"].slice(0, 2):
		scr.inspect_part(pid)
	for i in scr.job["diagnosis"].size():
		if scr.job["diagnosis"][i]["correct"]:
			scr.choose_diagnosis(i)
			break
	Nav.toast.timer = 0.0
	await _wait(1.0)
	return Nav.current


@warning_ignore("integer_division")
func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var want: Array = []
	var i := args.find("--shots") + 1
	while i < args.size() and not args[i].begins_with("--"):
		want.append(args[i])
		i += 1
	if want.is_empty():
		want = ALL
	seed(1)
	Figure.idle_t = IDLE_T                    # Бренна, Мартин (IDLE_LOOPS) — тот же кадр петли, что в ref_shots.py
	Frames.want_loop(str(Content.consts.get("idle", {}).get("loops", {}).get("master.png", "")))
	Frames.want_loop(str(Content.consts.get("idle", {}).get("loops", {}).get("martin.png", "")))   # «живой» Мартин
	if "--big" in args:
		Settings.a11y["text"] = 3
	Settings.lang = "ru"
	Loc.code = "ru"
	get_viewport().gui_disable_input = true
	SaveGame.tutorial_skipped = true          # как в ref_shots.py
	for name: String in want:
		await stage(name)
		await _shot(name)
		unstage(name)
	Nav.shutdown()
	await _wait(0.2)
	get_tree().quit(0)


## Поставить экран в состояние снимка name (без снимка) — и для снимков, и для замера кадров/с в браузере
## (web_smoke screens: ?test=1 → window.wnbStage(name), autoload/web.gd). Окна, открытые для снимка, закрывает unstage.
@warning_ignore("integer_division")
func stage(name: String) -> void:
	if not name.begins_with("scan_") and Settings.a11y.get("scan", 0):   # после снимков «одной кнопки» — обычный режим
		Settings.a11y["scan"] = 0
		A11y.scan_sub = {}
		Share._close_dlg()
	if name.begins_with("title"):
		Settings.lang = "en" if name.ends_with("_en") else "ru"
		Loc.code = Settings.lang
		Nav.go("title")
		Frames.want_loop("martin_wave")
		Frames.want_loop("barty_wave")
		Frames.flush()
		await _wait(3.0)
	elif name == "hub":
		Nav.go("hub")
		Frames.want_loop("barty_wave")
		Frames.flush()
		await _wait(3.0)
	elif name.begins_with("guild_"):
		SaveGame.done.clear()
		SaveGame.exam_passed = name == "guild_diploma"
		for j: Dictionary in Content.jobs.slice(0, 5):
			SaveGame.done[j["id"]] = true
		if name != "guild_open":
			for j: Dictionary in Content.tech_jobs:
				SaveGame.done[j["id"]] = true
		Nav.go("guild")
		Frames.want_loop("barty_wave")
		Frames.flush()
		await _wait(2.0)
	elif name.begins_with("scan_"):
		await _scan_shot(name)
	elif name.begins_with("share_") or name == "hub_assign":
		await _share_shot(name)
	elif name.begins_with("seat_"):
		await _seat_shot(name)
	elif name.begins_with("tech_") or name.begins_with("exam_"):
		await _tech_shot(name)
	elif name.begins_with("intro_"):
		if Nav.current_name != "intro":
			Nav.go("intro")
			Frames.want_loop("barty_wave")
			Frames.flush()
		Nav.current.idx = int(name.trim_prefix("intro_")) - 1
		Nav.current._typing = ["", 0.0]
		Nav.current._update_a11y()
		await _wait(2.6)
	elif name.begins_with("garage"):
		SaveGame.garage.clear()
		SaveGame.done.clear()
		for gi in 10:
			var jid: String = Content.jobs[gi]["id"]
			SaveGame.garage.append([jid, [3, 2, 1][gi % 3]])
			SaveGame.done[jid] = true
		Nav.go("garage")
		await _wait(2.0)
		if name == "garage_open":
			Nav.current.open_card(0)
			await _wait(0.5)
	elif name == "ending":
		Nav.go("ending")
		Frames.want_loop("barty_wave")
		Frames.flush()
		await _wait(3.0)
	elif name == "credits":
		Nav.go("credits", {"from": "title"})
		await _wait(3.0)
	elif name == "feedback_general":
		Nav.go("hub")
		await _wait(0.5)
		Nav.open_flag()
		await _wait(0.1)
		Nav.feedback.reason = 1
		Nav.feedback._update()
		Nav.feedback.text.text = "Карточка съехала"
		await _wait(0.4)
	elif name == "feedback_dispute":
		Nav.go("job", {"job": "flat", "variant": 0})
		await _wait(0.5)
		var scr: Node = Nav.current
		for pid: String in scr.job["parts"].slice(0, 2):
			scr.inspect_part(pid)
		for k in scr.job["diagnosis"].size():
			if str(scr.job["diagnosis"][k]["text"]).begins_with("Погнут обод"):
				scr.choose_diagnosis(k)
		Nav.toast.timer = 0.0
		scr.open_dispute()
		await _wait(0.5)
	elif name == "help":
		Nav.go("hub")
		await _wait(0.5)
		Nav.toggle_help()
		await _wait(0.5)
	elif name.begins_with("settings_"):
		if Nav.current_name != "hub":
			Nav.go("hub")
			await _wait(0.5)
		SettingsDialog.tab = name.trim_prefix("settings_")
		Nav.open_settings()
		await _wait(0.5)
	elif name == "settings":
		Nav.go("hub")
		await _wait(1.0)
		Nav.open_settings()
		await _wait(0.5)
	elif name == "job_flat_repair":
		var scr: Node = await _to_repair("flat")
		var st: Dictionary = scr.cur_step()
		scr.select_tool(st["tool"])
		scr.do_action(st["tool"], "brake")      # не та деталь: сообщение, инструмент в руке
		await _wait(1.0)
	elif name.begins_with("mini_"):
		var kind := name.trim_prefix("mini_")
		var jid: String = {"pump": "flat", "gap": "brake", "ping": "spokes", "meter": "lift"}[kind]
		var scr: Node = await _to_repair(jid)
		while scr.phase == "repair" and not (scr.cur_step().get("mini") is Dictionary and scr.cur_step()["mini"]["kind"] == kind):
			scr.step_skip()
		Nav.toast.timer = 0.0
		var st: Dictionary = scr.cur_step()
		scr.select_tool(st["tool"])
		scr.part_clicked(st["part"])
		var m: MiniGame = scr.mini
		if kind == "pump":
			m.value = (ceili(float(m.cfg["lo"])) + floori(float(m.cfg["hi"]))) / 2
		elif kind == "ping":
			m.dull = {1: true, 5: true}
			m.tested = {0: true, 1: true}
		await _wait(0.6)
	elif name.begins_with("ride_"):
		var jid := "flat" if name == "ride_martin" else "lift"
		var scr: Node = await _to_repair(jid)
		while scr.phase == "repair":
			scr.step_skip()
		scr.mistakes = 0
		Nav.toast.timer = 0.0
		var hero := RideView.hero_loop(scr.job["client_art"])
		Frames.want_loop(hero)
		Frames.flush()
		await _wait(1.0)
		scr.start_ride()
		await _wait(2.0)
	elif name == "result_lift":
		var scr: Node = await _to_repair("lift")
		while scr.phase == "repair":
			scr.step_skip()
		var pool: Array = Content.talk["martin"]["good"]
		Nav.go("result", {"job": scr.job, "stars": 3, "gag": pool[0], "mistakes": 0})
		SaveGame.done["lift"] = true
		Frames.want_loop("magic_zix")
		Frames.flush()
		await _wait(3.7)
	elif name == "hub_done":
		SaveGame.done["lift"] = true
		Nav.go("hub")
		Frames.want_loop("barty_wave")
		Frames.flush()
		await _wait(3.0)
	elif name.begins_with("job_"):
		var jid := name.trim_prefix("job_").trim_suffix("_diagnose").trim_suffix("_inspected")
		Nav.go("job", {"job": jid, "variant": 0})
		Frames.want_loop("barty_wave")
		Frames.flush()
		await _wait(3.0)
		if name.ends_with("_inspected"):
			var scr: Node = Nav.current
			scr.inspect_part(scr.job["parts"][0])
			await _wait(0.5)
			scr.inspect_part(scr.job["parts"][1])
			scr.chair.yaw = scr.chair.view_yaw() + 0.7
			scr.chair.t0 = -1e9
			Frames.flush()
			await _wait(1.5)


## Браузер (web_smoke screens): убрать прошлое состояние и поставить новое; «готово» — window.wnbStaged = name.
func web_stage(name: String) -> void:
	if _staged != "":
		unstage(_staged)
	_staged = name
	JavaScriptBridge.eval("window.wnbStaged = ''", true)
	SaveGame.tutorial_skipped = true
	Nav.toast.timer = 0.0
	await stage(name)
	Nav.toast.timer = 0.0
	JavaScriptBridge.eval("window.wnbStaged = %s" % JSON.stringify(name), true)


## Убрать то, что stage(name) открыл поверх экрана (справка, настройки, замечание), вернуть язык.
func unstage(name: String) -> void:
	if name.begins_with("title"):
		Settings.lang = "ru"
		Loc.code = "ru"
	elif name in ["feedback_general", "feedback_dispute"]:
		if Nav.feedback != null:
			Nav.feedback.close()
	elif name == "help":
		Nav.toggle_help()
	elif name.begins_with("settings"):
		Nav.close_settings()
