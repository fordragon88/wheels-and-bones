extends Node
## Снимки экранов 1280×720 для сверки с pygame-версией (эталоны — tests/ref/, их делает tools/ref_shots.py):
##   D:\Godot\Godot_v4.7.2-stable_win64.exe --path godot --audio-driver Dummy -- --test --shots [имя …]
## Без имён — все; с «--calm» перед «--shots» — «Без анимации», файлы calm_<имя>.png. Снимки: tests/shots/<имя>.png (в git не хранятся). После снимков игра закрывается сама.
## Ввод мыши в окне на время снимков выключен (курсор над окном не даёт подсветку наведения).

const ALL := ["title", "title_en", "hub", "job_flat_diagnose", "job_flat_inspected",
	"job_joystick_diagnose", "job_joystick_inspected", "job_flat_repair", "settings"]

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
		elif name == "settings":
			Nav.go("hub")
			await _wait(1.0)
			Nav.open_settings()
			await _wait(0.5)
			await _shot(name)
			Nav.close_settings()
		elif name == "job_flat_repair":
			Nav.go("job", {"job": "flat", "variant": 0})
			await _wait(1.0)
			var scr: Node = Nav.current
			scr.inspect_part("tire")
			scr.inspect_part("tube")
			for k in scr.job["diagnosis"].size():
				if scr.job["diagnosis"][k]["correct"]:
					scr.choose_diagnosis(k)
			await _wait(1.5)
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
