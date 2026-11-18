extends SceneTree
## Самопроверка без окна:
##   D:\Godot\Godot_v4.7.2-stable_win64_console.exe --headless --path godot -s res://tests/selftest.gd -- --test
## Проверяет: автозагрузки на месте, все .gd компилируются, содержание читается (21 задание, 27 вариантов
## поломок, 6 про-заданий — как SELFTEST pygame-версии), у каждого задания есть портрет, коляска и кадры поворота
## (36 файлов, первый читается), палитра совпадает с game.py, у каждой строки, которую показывают титул, мастерская,
## экран задания (все задания и варианты) и окно настроек, есть английский вариант; проходит титул → мастерская →
## задание flat → осмотр → неверный → верный диагноз мышью (события ввода) и титул → задание с клавиатуры.
## Выход 0 и «GODOT SELFTEST OK …» или 1 и список ошибок.

func _initialize() -> void:
	_start.call_deferred()


func _start() -> void:
	var runner: Node = (load("res://tests/selftest_runner.gd") as GDScript).new()
	runner.name = "Selftest"
	root.add_child(runner)
