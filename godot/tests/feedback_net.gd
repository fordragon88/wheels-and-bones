extends SceneTree
## Отправка замечаний по сети — сверка с game.py без настоящей таблицы (tools/feedback_compare.py поднимает локальный
## сервер и запускает это):
##   … --headless --path godot -s res://tests/feedback_net.gd -- --test --feedback-url=http://127.0.0.1:N/ok
##     --in <запросы.json> --out <итог.json> [--flush-only]
## Шлёт каждый запрос из --in через Feedback.send (как окно замечания), ждёт ответов, пишет в --out очередь
## неотправленного (user://feedback_outbox_test.json — очередь игрока не трогается) и папку user://.

func _initialize() -> void:
	_run.call_deferred()


func _arg(name: String) -> String:
	var args := OS.get_cmdline_user_args()
	var i := args.find(name)
	return args[i + 1] if i >= 0 and i + 1 < args.size() else ""


func _run() -> void:
	var fb: Node = root.get_node("Feedback")
	if not OS.get_cmdline_user_args().has("--flush-only"):
		var items: Variant = JSON.parse_string(FileAccess.get_file_as_string(_arg("--in")))
		for p: Variant in items:
			fb.call("send", p, null)
	var t0 := Time.get_ticks_msec()
	await process_frame
	while (fb.get("_busy") as Dictionary).size() > 0 and Time.get_ticks_msec() - t0 < 25000:
		await process_frame
	var path: String = fb.get("outbox")
	var q: Variant = JSON.parse_string(FileAccess.get_file_as_string(path)) if FileAccess.file_exists(path) else []
	var f := FileAccess.open(_arg("--out"), FileAccess.WRITE)
	f.store_string(JSON.stringify({"outbox": q, "user_dir": OS.get_user_data_dir(), "outbox_path":
		ProjectSettings.globalize_path(path)}))
	f.close()
	quit(0)
