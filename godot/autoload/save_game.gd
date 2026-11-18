extends Node
## Прогресс в формате save.json pygame-версии: done, garage [[id, звёзды]], exam_passed, seat_done, seat_quiz_ok,
## tutorial_skipped, ending_seen (+ assign — только после ссылки-задания; здесь хранится как есть).
## Запись: сначала копия прежнего файла (save.prev.json), потом новый — во временный файл и переименованием.
## Битый файл не затирается молча: копия save.json.bad (как в game.py).

signal changed

const PATH := "user://save.json"
const PREV := "user://save.prev.json"

var done: Dictionary = {}              # id → true (множество)
var garage: Array = []                 # [[id, звёзды 1..3]]
var exam_passed: bool = false
var seat_done: Dictionary = {}
var seat_quiz_ok: bool = false
var tutorial_skipped: bool = false
var ending_seen: bool = false
var persist: bool = true
var _extra: Dictionary = {}            # assign и прочие ключи — обратно как были


func _ready() -> void:
	persist = not OS.get_cmdline_user_args().has("--test")
	if persist:
		load_file(PATH)


func load_file(path: String) -> void:
	if not FileAccess.file_exists(path):
		return
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not data is Dictionary:
		push_warning("save.json не читается — копия в save.json.bad")
		DirAccess.copy_absolute(path, path + ".bad")
		return
	apply_dict(data)


## Разбор словаря сохранения: каждое поле отдельно, битые элементы пропускаются (одна ошибка не обнуляет прогресс).
func apply_dict(d: Dictionary) -> void:
	var valid: Dictionary = {}
	for j: Dictionary in Content.all_jobs():
		valid[j["id"]] = true
	for jid: String in Content.folk_ids:
		valid[jid] = true
	done.clear()
	for j: Variant in _lst(d, "done"):
		if j is String and valid.has(j):
			done[j] = true
	garage.clear()
	var seen: Dictionary = {}
	for e: Variant in _lst(d, "garage"):
		if e is Array and e.size() == 2 and e[0] is String and valid.has(e[0]) and not seen.has(e[0]) \
				and (e[1] is float or e[1] is int):
			garage.append([e[0], clampi(int(e[1]), 1, 3)])
			seen[e[0]] = true
	exam_passed = d.get("exam_passed") is bool and d["exam_passed"]
	seat_done.clear()
	for c: Variant in _lst(d, "seat_done"):
		if c is String:
			seat_done[c] = true
	seat_quiz_ok = d.get("seat_quiz_ok") is bool and d["seat_quiz_ok"]
	tutorial_skipped = d.get("tutorial_skipped") is bool and d["tutorial_skipped"]
	ending_seen = d.get("ending_seen") is bool and d["ending_seen"]
	_extra.clear()
	for k: String in d:
		if not k in ["done", "garage", "exam_passed", "seat_done", "seat_quiz_ok", "tutorial_skipped", "ending_seen"]:
			_extra[k] = d[k]
	changed.emit()


static func _lst(d: Dictionary, key: String) -> Array:
	var v: Variant = d.get(key, [])
	return v if v is Array else []


func to_dict() -> Dictionary:
	var d: Dictionary = _extra.duplicate(true)
	var ds: Array = done.keys()
	ds.sort()
	var ss: Array = seat_done.keys()
	ss.sort()
	d["done"] = ds
	d["garage"] = garage.duplicate(true)
	d["exam_passed"] = exam_passed
	d["seat_done"] = ss
	d["seat_quiz_ok"] = seat_quiz_ok
	d["tutorial_skipped"] = tutorial_skipped
	d["ending_seen"] = ending_seen
	return d


func save() -> bool:
	changed.emit()
	if not persist:
		return true
	if FileAccess.file_exists(PATH):
		DirAccess.copy_absolute(ProjectSettings.globalize_path(PATH), ProjectSettings.globalize_path(PREV))
	var tmp := PATH + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_warning("save.json не записан: " + error_string(FileAccess.get_open_error()))
		return false
	f.store_string(JSON.stringify(to_dict(), "  "))
	f.close()
	return DirAccess.rename_absolute(tmp, PATH) == OK


func is_done(jid: String) -> bool:
	return done.has(jid)


## Починено обычных заданий мастерской (без Гильдии) — для счётчика «Починено: N/21».
func user_done_count() -> int:
	var n := 0
	for j: Dictionary in Content.jobs:
		if done.has(j["id"]):
			n += 1
	return n


func tech_done_count() -> int:
	var n := 0
	for j: Dictionary in Content.tech_jobs:
		if done.has(j["id"]):
			n += 1
	return n


func guild_unlocked() -> bool:
	return user_done_count() >= int(Content.consts.get("guild_req", 5))


## Обучение пройдено (первый ремонт) или пропущено.
func tutorial_ok() -> bool:
	return done.has("flat") or tutorial_skipped


## Задания в очереди мастерской: до обучения — только flat, потом все (как available_jobs()).
func available_jobs() -> Array:
	if not tutorial_ok():
		return ["flat"]
	var out: Array = []
	for j: Dictionary in Content.jobs:
		out.append(j["id"])
	return out


func reset() -> void:
	apply_dict({})
