extends Node
## Точка входа: первый экран. Параметры после «--» (OS.get_cmdline_user_args):
##   --screen hub | --job flat [--variant 0]   открыть сразу экран/задание (отладка)
##   --test                                    не читать и не писать настройки/сохранение
##   --shots [имя …]                           снимки экранов для сверки (tests/shots.gd), потом выход
##   --lang ru|en, --calm                      язык, «Без анимации»
##   --link="?jobs=flat,caster&from=Анна"      запуск со ссылкой-заданием / кодом прогресса (?load=…), как адрес в браузере


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.has("--shots"):
		var gd := load("res://tests/shots.gd") as GDScript
		if gd == null or not gd.can_instantiate():
			push_error("tests/shots.gd не компилируется")
			get_tree().quit(1)                 # не висеть с открытым окном
			return
		var runner: Node = gd.new()
		add_child(runner)
		return
	var i := args.find("--job")
	if i >= 0 and i + 1 < args.size():
		var v := args.find("--variant")
		Nav.go("job", {"job": args[i + 1], "variant": int(args[v + 1]) if v >= 0 and v + 1 < args.size() else -1})
		return
	i = args.find("--screen")
	Nav.go(args[i + 1] if i >= 0 and i + 1 < args.size() else "title")
	Share.apply_link(Share.launch_query())     # ?jobs=…/?load=… (браузер) или --link (компьютер); без них — ничего
