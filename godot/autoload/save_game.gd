extends Node
## Прогресс в формате save.json pygame-версии: done, garage [[id, звёзды]], exam_passed, seat_done, seat_quiz_ok,
## tutorial_skipped, ending_seen (+ assign — задание по ссылке: id, jobs, seat, from, title, done, errors, secs, active, sent;
## пока задание активно, обычный прогресс не меняется). Перед заменой прогресса кодом — копия save.bak.json.
## Запись: сначала копия прежнего файла (save.prev.json), потом новый — во временный файл и переименованием.
## Битый файл не затирается молча: копия save.json.bad (как в game.py).
## Браузер: хранение по ключам localStorage (Settings.store_*). Перед каждой записью хранимое перечитывается и
## объединяется «только растущими» полями (merge_saves): вторая вкладка со старым прогрессом не затирает задание,
## пройденное в первой. «gen» — поколение сохранения: сброс, загрузка кода и «Вернуть прежний прогресс» его
## увеличивают, и вкладка, загруженная до сброса, при записи берёт сброшенное + только своё новое (сброс не
## «воскресает»). На компьютере файл один на игру — без объединения и без «gen» (как было).

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
var restored_prev: bool = false       # save.json был битый — прогресс восстановлен из save.prev.json (сообщение на титуле)
const RESTORED_MSG := "Сохранение было повреждено — восстановлено из предыдущей копии."
var gen: int = 0                      # браузер: поколение сохранения (см. merge_saves)
var _base: Dictionary = {}            # браузер: что эта вкладка последний раз прочла/записала (для «своего нового»)
var _replace: bool = false            # следующая запись заменяет прогресс (сброс/код/копия): gen + 1, без объединения
var _fresh: Dictionary = {}           # браузер: пройдено с прошлой записи (и переигранное) — «своё новое» после сброса


func _ready() -> void:
	persist = not OS.get_cmdline_user_args().has("--test")
	if persist:
		if Settings.store_has("save.json"):
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
		Settings.store_write("save.bak.json", bak)
	save()
	return true


## Сохранение игрока (PATH) — из хранилища (Settings.store_*: в браузере — localStorage); другой путь (проверка
## tests/save_compat.gd) — файлом, копия битого — рядом.
func load_file(path: String) -> void:
	var own := path == PATH
	if not (Settings.store_has("save.json") if own else FileAccess.file_exists(path)):
		return
	var text := Settings.store_read("save.json") if own else FileAccess.get_file_as_string(path)
	var data: Variant = Settings.parse_json(text)
	if not data is Dictionary:
		push_warning("save.json не читается — копия в save.json.bad")
		if own:
			Settings.store_write("save.json.bad", text)
		else:
			DirAccess.copy_absolute(path, path + ".bad")
		# Копия прежнего сохранения (пишется перед каждой записью) цела — прогресс из неё, игроку — сообщение
		# (suggestions S2, 26.11). Её нет или она тоже битая — как раньше: пустой прогресс.
		var prev_path := path.get_basename() + ".prev.json"
		var prev := Settings.store_read("save.prev.json") if own 			else (FileAccess.get_file_as_string(prev_path) if FileAccess.file_exists(prev_path) else "")
		var pd: Variant = Settings.parse_json(prev)
		if not pd is Dictionary:
			return
		if own:
			Settings.store_write("save.json", prev)
		apply_dict(pd)
		restored_prev = true
	else:
		apply_dict(data)
	_snapshot_base()
	_fresh.clear()


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
	var g: Variant = Settings.py_int(d.get("gen"))
	gen = maxi(0, g) if g != null else 0
	if main:
		assign = assign_state(d.get("assign"))
	_extra.clear()
	for k: String in d:
		if not k in ["done", "garage", "exam_passed", "seat_done", "seat_quiz_ok", "tutorial_skipped", "ending_seen",
				"assign", "gen"]:
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
	if Settings.store_ls():
		d["gen"] = gen
	return d


func save() -> bool:
	if persist and Settings.store_ls():
		return _save_web()
	changed.emit()
	_replace = false
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


## Браузер: перечитать хранимое, объединить со своим (merge_saves), прежний текст — в save.prev.json, записать.
func _save_web() -> bool:
	var old := Settings.store_read("save.json")
	var stored: Variant = Settings.parse_json(old)
	var mine := to_dict()
	var out: Dictionary
	if _replace or not stored is Dictionary:
		out = mine
		if _replace:
			var sg: Variant = Settings.py_int((stored as Dictionary).get("gen")) if stored is Dictionary else null
			out["gen"] = maxi(gen, sg if sg != null else 0) + 1
	else:
		out = merge_saves(stored, mine, _base, _fresh)
	_replace = false
	_fresh.clear()
	if out != mine:
		apply_dict(out)                  # в памяти — объединённое (прогресс другой вкладки виден и здесь)
	else:
		changed.emit()
	gen = int(out.get("gen", 0))
	var text := JSON.stringify(to_dict(), "  ")
	if old != "" and old != text:
		Settings.store_write("save.prev.json", old)
	var ok := Settings.store_write("save.json", text)
	_snapshot_base()
	return ok


## Что эта вкладка прочла/записала — глубокой копией: to_dict() отдаёт словари задания (done/errors/secs) по ссылке,
## и пункт, отмеченный после записи, сразу «был» и в base — объединение после сброса в другой вкладке его теряло
## (обзор 26.11, E1; web_smoke tabs).
func _snapshot_base() -> void:
	_base = to_dict().duplicate(true)


## Объединение сохранений двух вкладок (браузер). stored — хранимое сейчас, mine — своё в памяти, base — что эта
## вкладка прочла/записала в прошлый раз. Растут только: done, seat_done (объединение), garage (лучшие звёзды),
## exam_passed, seat_quiz_ok, tutorial_skipped, ending_seen (или). Задание по ссылке: тот же id — сделанные пункты
## объединяются (первая попытка — из хранимого), «active» — своё; другой id — своё; своего нет — хранимое.
## gen: хранимое новее (сброс/код в другой вкладке) — к нему добавляется только своё новое (mine − base): пункты
## задания по ссылке с тем же id, которых не было в base, а если вкладка с прошлой записи открыла другую ссылку —
## своё задание целиком (обзор 26.11, E1); одинаковое — объединение целиком; своё новее — своё.
static func merge_saves(stored: Dictionary, mine: Dictionary, base: Dictionary, fresh: Dictionary = {}) -> Dictionary:
	var sg: Variant = Settings.py_int(stored.get("gen"))
	var mg: Variant = Settings.py_int(mine.get("gen"))
	var s_gen: int = sg if sg != null else 0
	var m_gen: int = mg if mg != null else 0
	if s_gen < m_gen:
		return mine.duplicate(true)
	var add := mine
	if s_gen > m_gen:
		add = _delta(mine, base, fresh)
	var out: Dictionary = stored.duplicate(true)
	for k: String in mine:
		if not k in GROW + ["assign", "gen"]:
			out[k] = mine[k]
	for key: String in ["done", "seat_done"]:
		var u: Dictionary = {}
		for x: Variant in _lst(stored, key) + _lst(add, key):
			u[x] = true
		var arr: Array = u.keys()
		arr.sort()
		out[key] = arr
	var garage_out: Array = []
	var idx: Dictionary = {}
	for e: Variant in _lst(stored, "garage") + _lst(add, "garage"):
		if not (e is Array and (e as Array).size() == 2):
			continue
		var st: Variant = Settings.py_int(e[1])
		var n: int = st if st != null else 1
		if idx.has(e[0]):
			var i: int = idx[e[0]]
			garage_out[i][1] = maxi(int(garage_out[i][1]), n)
		else:
			idx[e[0]] = garage_out.size()
			garage_out.append([e[0], n])
	out["garage"] = garage_out
	for key: String in FLAGS:
		out[key] = Settings.py_bool(stored.get(key)) or Settings.py_bool(add.get(key))
	var ma: Variant = mine.get("assign")
	var sa: Variant = stored.get("assign")
	if s_gen == m_gen and ma is Dictionary:
		if sa is Dictionary and sa.get("id") == ma.get("id"):
			var a: Dictionary = (ma as Dictionary).duplicate(true)
			for k: String in ["done", "errors", "secs"]:
				var sv: Variant = sa.get(k)
				var mv: Variant = a.get(k)
				if sv is Dictionary and mv is Dictionary:
					for kk: Variant in sv:
						mv[kk] = sv[kk]           # первая попытка — какая уже записана
			a["sent"] = Settings.py_bool(sa.get("sent")) or Settings.py_bool(a.get("sent"))
			out["assign"] = a
		else:
			out["assign"] = (ma as Dictionary).duplicate(true)
	elif s_gen > m_gen and ma is Dictionary:
		var ba: Variant = base.get("assign")
		var base_id: Variant = (ba as Dictionary).get("id") if ba is Dictionary else null
		if ma.get("id") != base_id:
			out["assign"] = (ma as Dictionary).duplicate(true)   # с прошлой записи вкладка открыла новую ссылку
		elif sa is Dictionary and sa.get("id") == ma.get("id"):
			var a: Dictionary = (sa as Dictionary).duplicate(true)
			for k: String in ["done", "errors", "secs"]:
				var sv: Variant = a.get(k)
				var mv: Variant = ma.get(k)
				var bv: Variant = (ba as Dictionary).get(k)
				if sv is Dictionary and mv is Dictionary:
					for kk: Variant in mv:
						if not sv.has(kk) and not (bv is Dictionary and (bv as Dictionary).has(kk)):
							sv[kk] = mv[kk]           # пункт, сделанный в этой вкладке после её прошлой записи
			if Settings.py_bool(ma.get("active")) != Settings.py_bool((ba as Dictionary).get("active")):
				a["active"] = ma.get("active")        # вошла в задание / вышла из него после прошлой записи
			a["sent"] = Settings.py_bool(sa.get("sent")) or Settings.py_bool(ma.get("sent"))
			out["assign"] = a
	out["gen"] = s_gen
	return out


const FLAGS: Array[String] = ["exam_passed", "seat_quiz_ok", "tutorial_skipped", "ending_seen"]
const GROW: Array[String] = ["done", "garage", "seat_done", "exam_passed", "seat_quiz_ok", "tutorial_skipped", "ending_seen"]


## Своё новое с прошлого чтения/записи: растущие поля mine, которых нет в base.
## fresh — пройденное с прошлой записи, даже если оно уже было (переиграла задание, пройденное до сброса).
static func _delta(mine: Dictionary, base: Dictionary, fresh: Dictionary = {}) -> Dictionary:
	var d := {}
	for key: String in ["done", "seat_done"]:
		var b: Array = _lst(base, key)
		d[key] = _lst(mine, key).filter(func(x: Variant) -> bool: return not x in b)
	var bg: Dictionary = {}
	for e: Variant in _lst(base, "garage"):
		if e is Array and (e as Array).size() == 2:
			bg[e[0]] = e[1]
	d["garage"] = _lst(mine, "garage").filter(func(e: Variant) -> bool:
		return e is Array and (e as Array).size() == 2 and (not bg.has(e[0]) or int(e[1]) > int(bg[e[0]])))
	for key: String in FLAGS:
		d[key] = Settings.py_bool(mine.get(key)) and not Settings.py_bool(base.get(key))
	for k: String in fresh:
		if k.begins_with("flag:"):
			d[k.trim_prefix("flag:")] = true      # флаг, поставленный заново (пересдал экзамен/зачёт после сброса)
		elif k.begins_with("seat:"):
			(d["seat_done"] as Array).append(k.trim_prefix("seat:"))
		else:
			(d["done"] as Array).append(k)
			(d["garage"] as Array).append([k, int(fresh[k])])
	return d


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
## Задание пройдено (обычная игра): done, в гараж — лучшая оценка (переигрывание её не снижает).
func mark_job(jid: String, stars: int) -> void:
	done[jid] = true
	var found := false
	for g: Array in garage:
		if g[0] == jid:
			found = true
			if stars > int(g[1]):
				g[1] = stars
	if not found:
		garage.append([jid, stars])
	_fresh[jid] = maxi(stars, int(_fresh.get(jid, 0)))


func mark_seat(cid: String) -> void:
	seat_done[cid] = true
	_fresh["seat:" + cid] = 1


## Флаг прогресса заработан (экзамен сдан, зачёт посадки пройден) — «своё новое» и тогда, когда он уже стоял:
## сброс в другой вкладке не должен отнять пересданное здесь (обзор 26.11, E1).
func mark_flag(key: String) -> void:
	set(key, true)
	_fresh["flag:" + key] = 1


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
	Nav.hub_page = 0
	Nav.garage_page = 0


## «Сбросить прогресс» в настройках (reset_progress): задание по ссылке остаётся, как в game.py.
func reset_progress() -> void:
	var a := assign
	var keep := gen
	apply_dict({})
	assign = a
	gen = keep
	_replace = true
	Nav.hub_page = 0                     # как reset_progress в game.py


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
	Nav.hub_page = 0                     # как start_assignment в game.py
	save()


func exit_assignment() -> void:
	if not assign.is_empty():
		assign["active"] = false
	Nav.hub_page = 0                     # как exit_assignment в game.py
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
	return _bak_mem != null if not persist else Settings.store_has("save.bak.json")


func backup_progress() -> void:
	var d := to_dict()
	d.erase("assign")
	if not persist:
		_bak_mem = d
		return
	d.erase("gen")
	Settings.store_write("save.bak.json", JSON.stringify(d, "  "))


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
	Nav.hub_page = 0                         # как _progress_reset_scene в game.py
	_replace = true
	save()


## «Вернуть прежний прогресс»: копия → текущий прогресс (задание не трогаем); копия удаляется.
## false — копии нет или она повреждена (E31.2 в game.py): прогресс прежний, копия НЕ стирается.
func restore_backup() -> bool:
	if not has_backup():
		return false
	var d: Variant
	if not persist:
		d = _bak_mem
		_bak_mem = null
	else:
		d = Settings.parse_json(Settings.store_read("save.bak.json"))
		if not d is Dictionary:
			return false
		Settings.store_remove("save.bak.json")
	if d is Dictionary:
		var keep := gen
		apply_dict(d, false)
		gen = keep
	Nav.hub_page = 0                         # как _progress_reset_scene в game.py
	_replace = true
	save()
	return true
