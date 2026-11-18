extends Node
## Точка входа: первый экран. Параметры после «--» (OS.get_cmdline_user_args):
##   --screen hub | --job flat [--variant 0]   открыть сразу экран/задание (отладка)
##   --test                                    не читать и не писать настройки/сохранение
##   --shots [имя …]                           снимки экранов для сверки (tests/shots.gd), потом выход
##   --lang ru|en, --calm                      язык, «Без анимации»


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.has("--shots"):
		var runner: Node = (load("res://tests/shots.gd") as GDScript).new()
		add_child(runner)
		return
	var i := args.find("--job")
	if i >= 0 and i + 1 < args.size():
		var v := args.find("--variant")
		Nav.go("job", {"job": args[i + 1], "variant": int(args[v + 1]) if v >= 0 and v + 1 < args.size() else -1})
		return
	i = args.find("--screen")
	Nav.go(args[i + 1] if i >= 0 and i + 1 < args.size() else "title")
