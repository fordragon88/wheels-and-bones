extends "res://tests/shots.gd"
## Снимки Godot для сверки размера текста с pygame (tools/text_scale/run.py): в свою папку, с языком/размером
## текста/шрифтом/контрастом; свои состояния «x:…» — длинные тексты (tools/text_scale/xlist.txt).
## Аргументы после «--»: --test --ashots [имя …] --aout <папка> --alang ru|en --atext 0..3 --afont --acontrast [--calm]

var a_lang := "ru"
var a_pre := ""


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var i := args.find("--aout")
	out_dir = args[i + 1]
	DirAccess.make_dir_recursive_absolute(out_dir)
	_arun.call_deferred()


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out_dir.path_join(a_pre + name.replace(":", "_") + ".png"))
	print("shot ", name, " ", Nav.current_name, " ", img.get_size())


## Свои состояния «x:…» для длинных текстов; остальное — как в shots.gd.
func stage(name: String) -> void:
	if not name.begins_with("x:"):
		await super(name)
		return
	var p := name.split(":")
	var kind := p[1]
	if kind.begins_with("tech"):
		await _x_tech(p)
		return
	if kind == "quiz" or kind == "lesson":
		await _x_seat(p)
		return
	var jid := p[2]
	var v := int(p[3])
	Nav.go("job", {"job": jid, "variant": v})
	Frames.want_loop("barty_wave")
	Frames.flush()
	await _wait(2.5)
	var scr: Node = Nav.current
	match kind:
		"diag":
			pass
		"insp":
			scr.inspect_part(scr.job["parts"][0])
			scr.inspect_part(p[4])
			await _wait(0.6)
		"wrong":
			for pid: String in scr.job["parts"].slice(0, 2):
				scr.inspect_part(pid)
			var best := -1
			for i in scr.job["diagnosis"].size():
				var d: Dictionary = scr.job["diagnosis"][i]
				if not d.get("correct", false) and (best < 0 or Loc.t(str(d.get("feedback", ""))).length() > Loc.t(str(scr.job["diagnosis"][best].get("feedback", ""))).length()):
					best = i
			scr.choose_diagnosis(best)
			await _wait(0.6)
		"step", "done", "back", "mini", "wrongtool", "result", "test":
			for pid: String in scr.job["parts"].slice(0, 2):
				scr.inspect_part(pid)
			for i in scr.job["diagnosis"].size():
				if scr.job["diagnosis"][i]["correct"]:
					scr.choose_diagnosis(i)
					break
			await _wait(0.3)
			var k := int(p[4]) if p.size() > 4 else 999
			if kind == "back":
				k += 1
			while scr.phase == "repair" and scr.step_idx < k:
				scr.step_skip()
			Nav.toast.timer = 0.0
			if kind in ["step", "done", "mini", "wrongtool"] and scr.phase == "repair":
				var st: Dictionary = scr.cur_step()
				scr.select_tool(st["tool"])
				if kind == "done":
					scr.complete_base_step(st)
				elif kind == "mini":
					scr.part_clicked(st["part"])
				elif kind == "wrongtool":
					var other := "brake" if st["part"] != "brake" else "tire"
					scr.do_action(st["tool"], other)
			elif kind == "back":
				scr.step_back()
			elif kind == "result":
				var pool: Array = Content.talk["martin"]["good"]
				var longest: String = pool[0]
				for g: String in pool:
					if Loc.t(g).length() > Loc.t(longest).length():
						longest = g
				Nav.go("result", {"job": scr.job, "stars": 3, "gag": longest, "mistakes": 0})
				await _wait(4.5)
			elif kind == "test":
				scr.mistakes = 0
				await _wait(0.5)
			await _wait(1.0)


func _x_tech(p: PackedStringArray) -> void:
	var jid := p[2]
	var scr: Node = await _tech_open(jid)
	match p[1]:
		"techops":
			scr.select_tool(scr.job["steps"][0]["tool"])
			await _wait(2.0)
		"techspec", "techfail", "techdone":
			for m: String in scr.job.get("manual", []):
				scr.manual_viewed[m] = true
			var target := p[3]
			if p[1] == "techfail":
				var st: Dictionary = scr.step_by_id(target)
				scr.select_tool(st["tool"])
				scr.op_clicked(target)
			else:
				for st: Dictionary in scr.job["steps"]:
					if st["id"] == target:
						scr.select_tool(st["tool"])
						scr.op_clicked(st["id"])
						break
					_tech_do(Nav.current, st["id"])
			await _wait(1.0)
		"techmanual":
			scr.open_manual()
			await _wait(0.6)
		"techresult":
			for m: String in scr.job.get("manual", []):
				scr.manual_viewed[m] = true
			for st: Dictionary in scr.job["steps"]:
				_tech_do(Nav.current, st["id"])
			scr = Nav.current
			scr.mistakes = 0
			Nav.go("result", {"job": scr.job, "stars": 3, "gag": Content.talk["martin"]["good"][0], "mistakes": 0})
			await _wait(4.5)


func _x_seat(p: PackedStringArray) -> void:
	if Nav.current_name != "seating":
		SaveGame.done.clear()
		SaveGame.done["flat"] = true
		Nav.go("seating")
		await _wait(0.1)
		Nav.current.quiz = Content.seating["quiz"].duplicate(true)
		Nav.current.refresh()
	var scr: Node = Nav.current
	var i := int(p[2])
	if p[1] == "lesson":
		scr.tab = "lessons"
		scr.refresh()
		scr.pick_lesson(i)
		await _wait(2.5)
	else:
		scr.tab = "quiz"
		scr.quiz_i = i
		scr.picked = -1
		scr.refresh()
		await _wait(1.5)
		if p.size() > 3:
			var opts: Array = scr.quiz[i]["options"]
			for j in opts.size():
				if bool(opts[j][1]) == (p[3] == "right"):
					scr.quiz_pick(j)
					break
			scr.fix_t0 = scr.t - 5.0
			await _wait(2.5)


func unstage(name: String) -> void:
	super(name)
	Settings.lang = a_lang
	Loc.code = a_lang


@warning_ignore("integer_division")
func _arun() -> void:
	var args := OS.get_cmdline_user_args()
	var want: Array = []
	var i := args.find("--ashots") + 1
	while i > 0 and i < args.size() and not args[i].begins_with("--"):
		want.append(args[i])
		i += 1
	if want.is_empty():
		want = ALL.duplicate()
	i = args.find("--alang")
	a_lang = args[i + 1] if i >= 0 else "ru"
	i = args.find("--atext")
	var tx := int(args[i + 1]) if i >= 0 else 0
	seed(1)
	Figure.idle_t = IDLE_T
	Frames.want_loop(str(Content.consts.get("idle", {}).get("loops", {}).get("master.png", "")))
	Settings.a11y["text"] = tx
	Settings.a11y["font"] = "--afont" in args
	Settings.a11y["contrast"] = "--acontrast" in args
	Settings.lang = a_lang
	Loc.code = a_lang
	a_pre = ""
	get_viewport().gui_disable_input = true
	SaveGame.tutorial_skipped = true
	for name: String in want:
		if a_lang == "en" and name == "title":
			continue
		await stage(name)
		if not name.begins_with("title"):
			Settings.lang = a_lang
			Loc.code = a_lang
		await _shot(name)
		unstage(name)
	Nav.shutdown()
	await _wait(0.2)
	get_tree().quit(0)
