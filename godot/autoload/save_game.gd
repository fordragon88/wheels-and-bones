extends Node
## Прогресс в формате save.json pygame-версии: done, garage [[id, звёзды]], exam_passed, seat_done, seat_quiz_ok,
## tutorial_skipped, ending_seen (+ assign — задание по ссылке: id, jobs, seat, from, title, done, errors, secs, active, sent;
## пока задание активно, обычный прогресс не меняется). Перед заменой прогресса кодом — копия save.bak.json.
## Запись: сначала копия прежнего файла (save.prev.json), потом новый — во временный файл и переименованием.
## Битый файл не затирается молча: копия save.json.bad (как в game.py).

signal changed

const PATH := "user://save.json"
const PREV := "user://save.prev.json"
const BAK := "user://save.bak.json"

var done: Dictionary = {}              # id → true (множество)
var garage: Array = []                 # [[id, звёзды 1..3]]
var exam_passed: bool = false
var seat_done: Dictionary = {}
var seat_quiz_ok: bool = false
var tutorial_skipped: bool = false
var ending_seen: bool = false
var assign: Dictionary = {}            # задание по ссылке ({} — нет)
var persist: bool = true
var _extra: Dictionary = {}            # прочие ключи — обратно как были
var _bak_mem: Variant = null           # тесты: копия прогресса в памяти


var migrated: bool = false            # браузер: прогресс взят из pygame-версии (localStorage) в этом запуске


func _ready() -> void:
	persist = not OS.get_cmdline_user_args().has("--test")
	if persist:
		if FileAccess.file_exists(PATH):
			load_file(PATH)
		elif OS.has_feature("web"):
			migrate_web()


## Браузер, первый запуск Godot-версии: прогресс pygame-версии с того же сайта (localStorage «wnb:save.json» — формат
## тот же) берём один раз в свой user://save.json; копию «wnb:save.bak.json» — в save.bak.json («Вернуть прежний
## прогресс»). Старое не стираем: pygame-версия продолжает работать как была.
func migrate_web() -> bool:
	var text := Settings.web_legacy("save.json")
	var data: Variant = Settings.parse_json(text)
	if not data is Dictionary:
		return false
	apply_dict(data)
	migrated = true
	var bak := Settings.web_legacy("save.bak.json")
	if bak.begins_with("{") and Settings.parse_json(bak) is Dictionary:
		var f := FileAccess.open(BAK, FileAccess.WRITE)
		if f != null:
			f.store_string(bak)
			f.close()
	save()
	return true


func load_file(path: String) -> void:
	if not FileAccess.file_exists(path):
		return
	var data: Variant = Settings.parse_json(FileAccess.get_file_as_string(path))
	if not data is Dictionary:
		push_warning("save.json не читается — копия в save.json.bad")
		DirAccess.copy_absolute(path, path + ".bad")
		return
	apply_dict(data)


## Разбор словаря сохранения: каждое поле отдельно, битые элементы пропускаются (одна ошибка не обнуляет прогресс).
func apply_dict(d: Dictionary, main: bool = true) -> void:
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
		# как game.py: j, st_ = e; int(st_) — звёзды и флажком/строкой-целым (старые файлы)
		if e is Array and e.size() == 2 and e[0] is String and valid.has(e[0]) and not seen.has(e[0]):
			var stars: Variant = Settings.py_int(e[1])
			if stars != null:
				garage.append([e[0], clampi(stars, 1, 3)])
				seen[e[0]] = true
	exam_passed = d.get("exam_passed") is bool and d["exam_passed"]
	seat_done.clear()
	var seat_ids: Dictionary = {}
	for c: Dictionary in SeatLogic.cases():
		seat_ids[c["id"]] = true
	for c: Variant in _lst(d, "seat_done"):
		if c is String and seat_ids.has(c):    # только известные примерки (как game.py)
			seat_done[c] = true
	seat_quiz_ok = d.get("seat_quiz_ok") is bool and d["seat_quiz_ok"]
	tutorial_skipped = d.get("tutorial_skipped") is bool and d["tutorial_skipped"]
	ending_seen = d.get("ending_seen") is bool and d["ending_seen"]
	if main:
		assign = assign_state(d.get("assign"))
	_extra.clear()
	for k: String in d:
		if not k in ["done", "garage", "exam_passed", "seat_done", "seat_quiz_ok", "tutorial_skipped", "ending_seen",
				"assign"]:
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
	if not assign.is_empty():
		var a := {}
		for k: String in ["id", "jobs", "seat", "from", "title", "done", "errors", "secs", "active", "sent"]:
			a[k] = assign[k]
		d["assign"] = a
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


## Прогресс и настройки в виде эталона game.py (tools/save_fixtures.py → tests/saves/expected.json): сверка переноса
## сохранений — tests/save_compat.gd (компьютер) и web_smoke migrate (браузер, wnbState.compat). st — узел настроек.
func compat_dump(st: Node) -> Dictionary:
	var d := to_dict()
	var a: Variant = d.get("assign")
	if a is Dictionary:
		var dn: Array = (a["done"] as Dictionary).keys()
		dn.sort()
		a["done"] = dn
	var acc: Dictionary = st.get("a11y")
	var a11y := {}
	for k: String in ["on", "voices", "rate", "contrast", "instant", "speech_set", "text", "text_set", "calm_set", "font",
			"barty", "quiet", "quiet_set"]:
		a11y[k] = acc[k]
	return {"done": d["done"], "garage": d["garage"], "exam_passed": d["exam_passed"], "seat_done": d["seat_done"],
		"seat_quiz_ok": d["seat_quiz_ok"], "tutorial_skipped": d["tutorial_skipped"], "ending_seen": d["ending_seen"],
		"assign": a if a is Dictionary else null, "volume": st.get("vol"), "lang": st.get("lang"), "glow": st.get("glow"),
		"a11y": a11y, "calm": acc["calm"] if acc["calm_set"] else "system"}


## Отметка ✔: в задании по ссылке — по прогрессу задания, иначе — по обычному.
func is_done(jid: String) -> bool:
	if assign_on():
		return (assign["done"] as Dictionary).has(jid)
	return done.has(jid) or seat_done.has(jid)


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


## Обучение пройдено (первый ремонт) или пропущено. В задании по ссылке обучения нет — всё открыто.
func tutorial_ok() -> bool:
	return done.has("flat") or tutorial_skipped or assign_on()


## Задания в очереди мастерской: до обучения — только flat, потом все (как available_jobs()).
func available_jobs() -> Array:
	if assign_on():
		return (assign["jobs"] as Array).duplicate()
	if not tutorial_ok():
		return ["flat"]
	var out: Array = []
	for j: Dictionary in Content.jobs:
		out.append(j["id"])
	return out


func reset() -> void:
	apply_dict({})
	_bak_mem = null


## «Сбросить прогресс» в настройках (reset_progress): задание по ссылке остаётся, как в game.py.
func reset_progress() -> void:
	var a := assign
	apply_dict({})
	assign = a


# ---------------- задание по ссылке (docs/SHARE_LINKS.md) ----------------

func assign_on() -> bool:
	return not assign.is_empty() and assign.get("active", false)


## Задание из save.json → проверенное состояние или {} (_assign_state): неизвестные id и битые числа — мимо.
func assign_state(d: Variant) -> Dictionary:
	if not d is Dictionary:
		return {}
	var a := Share.assign_parse({"jobs": d.get("jobs") if d.get("jobs") else [], "seat": d.get("seat") if d.get("seat") else [],
		"from": d.get("from"), "title": d.get("title")})
	if a.is_empty():
		return {}
	var items := Share.assign_items(a)
	var num := func(key: String) -> Dictionary:
		var out := {}
		var v: Variant = d.get(key)
		if v is Dictionary:
			for k: Variant in v:
				var x: Variant = v[k]
				if k in items and (x is int or (x is float and is_finite(x))):
					out[k] = clampi(int(x), 0, 1000000)
		return out
	var dn := {}
	var dv: Variant = d.get("done")
	if dv is Dictionary or dv is Array:
		for k: Variant in dv:
			if k in items:
				dn[k] = 1
	a["done"] = dn
	a["errors"] = num.call("errors")
	a["secs"] = num.call("secs")
	a["active"] = not (d.get("active") is bool and d["active"] == false)
	a["sent"] = d.get("sent") is bool and d["sent"] == true
	return a


## Войти в задание: тот же id (та же ссылка) — продолжить с места, другой — начать заново.
func start_assignment(a: Dictionary) -> void:
	if not assign.is_empty() and assign.get("id") == a["id"]:
		assign["active"] = true
	else:
		assign = a.duplicate(true)
		assign.merge({"done": {}, "errors": {}, "secs": {}, "active": true, "sent": false}, true)
	save()


func exit_assignment() -> void:
	if not assign.is_empty():
		assign["active"] = false
	save()


func assign_complete() -> bool:
	if assign.is_empty():
		return false
	for k: String in Share.assign_items(assign):
		if not (assign["done"] as Dictionary).has(k):
			return false
	return true


## Пункт задания выполнен: в итог идёт первая попытка (переигрывание её не меняет).
func assign_record(key: String, errors: int, secs: int) -> void:
	if not assign_on() or not key in Share.assign_items(assign):
		return
	if not (assign["done"] as Dictionary).has(key):
		assign["done"][key] = 1
		assign["errors"][key] = maxi(0, errors)
		assign["secs"][key] = maxi(0, secs)
	save()


## Примерки Кабинета посадки по порядку (в задании — только назначенные): индексы в SeatLogic.cases().
func seat_idx() -> Array:
	var ids: Array = SeatLogic.cases().map(func(c: Dictionary) -> String: return c["id"])
	if assign_on() and not (assign["seat"] as Array).is_empty():
		var out: Array = []
		for k: String in assign["seat"]:
			if k in ids:
				out.append(ids.find(k))
		return out
	return range(ids.size())


# ---------------- копия прогресса перед заменой кодом ----------------

func has_backup() -> bool:
	return _bak_mem != null if not persist else FileAccess.file_exists(BAK)


func backup_progress() -> void:
	var d := to_dict()
	d.erase("assign")
	if not persist:
		_bak_mem = d
		return
	var f := FileAccess.open(BAK, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(d, "  "))


## Заменить прогресс проверенными полями кода (Share.progress_unpack); старый — в копию.
func apply_progress(p: Dictionary) -> void:
	backup_progress()
	done.clear()
	for j: String in p["done"]:
		done[j] = true
	garage = (p["garage"] as Array).duplicate(true)
	exam_passed = p["exam_passed"]
	seat_done.clear()
	for c: String in p["seat_done"]:
		seat_done[c] = true
	seat_quiz_ok = p["seat_quiz_ok"]
	tutorial_skipped = p["tutorial_skipped"]
	if not assign.is_empty():
		assign["active"] = false                # загрузили свой прогресс — обычная игра
	save()


## «Вернуть прежний прогресс»: копия → текущий прогресс (задание не трогаем); копия удаляется.
func restore_backup() -> void:
	if not has_backup():
		return
	var d: Variant
	if not persist:
		d = _bak_mem
		_bak_mem = null
	else:
		d = Settings.parse_json(FileAccess.get_file_as_string(BAK))
		DirAccess.remove_absolute(BAK)
	if d is Dictionary:
		apply_dict(d, false)
	save()
