extends SceneTree
## Стык «живых» слоёв героя в Godot (как art_tests/loop_shift.py в pygame-версии; запускает tools/loop_shift.py):
## слои рисует tests/loop_shift_runner.gd (автозагрузки видны только узлу в дереве, как у selftest.gd). С окном:
##   Godot_v4.7.2-stable_win64_console.exe --audio-driver Dummy --path godot -s res://tests/loop_shift.gd -- <папка>


func _initialize() -> void:
	_start.call_deferred()


func _start() -> void:
	var runner: Node = (load("res://tests/loop_shift_runner.gd") as GDScript).new()
	runner.name = "LoopShift"
	root.add_child(runner)
