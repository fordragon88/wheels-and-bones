extends SceneTree
## Перенос сохранений pygame-версии: как Godot читает настоящие save.json/settings.json, записанные game.py
## (tests/saves/, их пишет tools/save_fixtures.py вместе с эталоном чтения game.py expected.json).
##   D:\Godot\Godot_v4.7.2-stable_win64_console.exe --headless --path godot -s res://tests/save_compat.gd -- --test --out <dump.json>
## Сверку поле в поле делает python godot/tools/save_fixtures.py --godot (сам запускает это).
## Битый файл: прогресс не меняется, файл не затирается (копия .bad рядом) — поле "kept".

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var out_path := ""
	var i := args.find("--out")
	if i >= 0 and i + 1 < args.size():
		out_path = args[i + 1]
	var dir := ProjectSettings.globalize_path("res://tests/saves/")
	var tmp := ProjectSettings.globalize_path("user://save_compat/")
	DirAccess.make_dir_recursive_absolute(tmp)
	var sg: Node = root.get_node("SaveGame")
	var settings_gd := load("res://autoload/settings.gd") as GDScript
	var out := {}
	var names: Array = []
	for f: String in DirAccess.get_files_at(dir):
		if f.ends_with(".save.json"):
			names.append(f.trim_suffix(".save.json"))
	names.sort()
	for name: String in names:
		var src := dir + name + ".save.json"
		var dst := tmp + "save.json"
		DirAccess.remove_absolute(dst + ".bad")
		DirAccess.copy_absolute(src, dst)
		var before := FileAccess.get_file_as_bytes(dst)
		sg.call("reset")
		sg.call("load_file", dst)
		var st: Node = settings_gd.new()
		var stp := dir + name + ".settings.json"
		if FileAccess.file_exists(stp):
			st.call("load_text", FileAccess.get_file_as_string(stp))
		var row: Dictionary = sg.call("compat_dump", st)
		row["kept"] = FileAccess.get_file_as_bytes(dst) == before
		out[name] = row
		st.free()
	sg.call("reset")
	# «Без анимации» по системе (пункт 4): ответ системы «выкл» действует, только пока игрок не выбрал сам
	var pri := {}
	for c: Array in [["set_off", '{"a11y": {"calm": false, "calm_set": true}}'], ["set_on", '{"a11y": {"calm": true, "calm_set": true}}'],
			["unset", '{"a11y": {"calm": true}}'], ["none", ""]]:
		var res: Array = []
		for sys_off: bool in [true, false]:
			var st2: Node = settings_gd.new()
			if c[1] != "":
				st2.call("load_text", c[1])
			st2.call("apply_system_calm", sys_off)
			res.append(st2.call("calm"))
			st2.free()
		pri[c[0]] = res
	out["_calm_priority"] = pri
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	f.store_string(JSON.stringify(out, " "))
	f.close()
	print("SAVE COMPAT DUMP: %d сохранений → %s" % [names.size(), out_path])
	quit(0)
