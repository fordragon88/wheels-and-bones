extends Node
## Снимки экранов 1280×720 для сверки с pygame-версией (эталоны — tests/ref/, их делает tools/ref_shots.py):
##   D:\Godot\Godot_v4.7.2-stable_win64.exe --path godot --audio-driver Dummy -- --test --shots [имя …]
## Без имён — все; с «--calm» перед «--shots» — «Без анимации», файлы calm_<имя>.png. Снимки: tests/shots/<имя>.png (в git не хранятся). После снимков игра закрывается сама.
## Ввод мыши в окне на время снимков выключен (курсор над окном не даёт подсветку наведения).

const ALL := ["title", "title_en", "hub", "job_flat_diagnose", "job_flat_inspected",
	"job_joystick_diagnose", "job_joystick_inspected", "job_flat_repair", "mini_pump", "mini_gap", "mini_ping",
	"mini_meter", "ride_martin", "ride_zix", "result_lift", "hub_done", "intro_1", "intro_2", "intro_3", "intro_4",
	"intro_5", "garage", "garage_open", "ending", "credits", "feedback_general", "feedback_dispute", "help",
	"settings_sound", "settings_graphics", "settings_access", "settings_game"]

var out_dir := ""


func _ready() -> void:
	out_dir = ProjectSettings.globalize_path("res://tests/shots")
	DirAccess.make_dir_recursive_absolute(out_dir)
	FileAccess.open(out_dir.path_join(".gdignore"), FileAccess.WRITE)   # редактор не импортирует снимки
	_run.call_deferred()


func _wait(secs: float) -> void:
	await get_tree().create_timer(secs).timeout


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	if img.get_size() != Vector2i(1280, 720):
		img.resize(1280, 720, Image.INTERPOLATE_LANCZOS)
	img.save_png(out_dir.path_join(("calm_" if Settings.calm() else "") + name + ".png"))
	print("shot ", name, " ", Nav.current_name)


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
	Settings.lang = "ru"
	Loc.code = "ru"
	get_viewport().gui_disable_input = true
	SaveGame.tutorial_skipped = true          # как в ref_shots.py
	for name: String in want:
		if name.begins_with("title"):
			Settings.lang = "en" if name.ends_with("_en") else "ru"
			Loc.code = Settings.lang
			Nav.go("title")
			Frames.want_loop("martin_wave")
			Frames.want_loop("barty_wave")
			Frames.flush()
			await _wait(3.0)
			await _shot(name)
			Settings.lang = "ru"
			Loc.code = "ru"
		elif name == "hub":
			Nav.go("hub")
			Frames.want_loop("barty_wave")
			Frames.flush()
			await _wait(3.0)
			await _shot(name)
		elif name.begins_with("intro_"):
			if Nav.current_name != "intro":
				Nav.go("intro")
				Frames.want_loop("barty_wave")
				Frames.flush()
			Nav.current.idx = int(name.trim_prefix("intro_")) - 1
			Nav.current._typing = ["", 0.0]
			Nav.current._update_a11y()
			await _wait(2.6)
			await _shot(name)
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
			await _shot(name)
		elif name == "ending":
			Nav.go("ending")
			Frames.want_loop("barty_wave")
			Frames.flush()
			await _wait(3.0)
			await _shot(name)
		elif name == "credits":
			Nav.go("credits", {"from": "title"})
			await _wait(3.0)
			await _shot(name)
		elif name == "feedback_general":
			Nav.go("hub")
			await _wait(0.5)
			Nav.open_flag()
			await _wait(0.1)
			Nav.feedback.reason = 1
			Nav.feedback._update()
			Nav.feedback.text.text = "Карточка съехала"
			await _wait(0.4)
			await _shot(name)
			Nav.feedback.close()
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
			await _shot(name)
			Nav.feedback.close()
		elif name == "help":
			Nav.go("hub")
			await _wait(0.5)
			Nav.toggle_help()
			await _wait(0.5)
			await _shot(name)
			Nav.toggle_help()
		elif name.begins_with("settings_"):
			if Nav.current_name != "hub":
				Nav.go("hub")
				await _wait(0.5)
			SettingsDialog.tab = name.trim_prefix("settings_")
			Nav.open_settings()
			await _wait(0.5)
			await _shot(name)
			Nav.close_settings()
		elif name == "settings":
			Nav.go("hub")
			await _wait(1.0)
			Nav.open_settings()
			await _wait(0.5)
			await _shot(name)
			Nav.close_settings()
		elif name == "job_flat_repair":
			var scr: Node = await _to_repair("flat")
			var st: Dictionary = scr.cur_step()
			scr.select_tool(st["tool"])
			scr.do_action(st["tool"], "brake")      # не та деталь: сообщение, инструмент в руке
			await _wait(1.0)
			await _shot(name)
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
				m.value = (int(m.cfg["lo"]) + int(m.cfg["hi"])) / 2
			elif kind == "ping":
				m.dull = {1: true, 5: true}
				m.tested = {0: true, 1: true}
			await _wait(0.6)
			await _shot(name)
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
			await _shot(name)
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
			await _shot(name)
		elif name == "hub_done":
			SaveGame.done["lift"] = true
			Nav.go("hub")
			Frames.want_loop("barty_wave")
			Frames.flush()
			await _wait(3.0)
			await _shot(name)
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
			await _shot(name)
	Nav.shutdown()
	await _wait(0.2)
	get_tree().quit(0)
