extends SceneTree
## Запуск: Godot --path godot --audio-driver Dummy -s res://tests/text_scale/run.gd -- --test --aout DIR ...

func _initialize() -> void:
	_start.call_deferred()


func _start() -> void:
	var gd := load("res://tests/text_scale/text_shots.gd") as GDScript
	if gd == null or not gd.can_instantiate():
		push_error("text_shots.gd не компилируется")
		quit(1)
		return
	var runner: Node = gd.new()
	runner.name = "AuditShots"
	root.add_child(runner)
