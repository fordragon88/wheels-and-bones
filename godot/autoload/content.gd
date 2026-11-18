extends Node
## Содержание игры из content/data (копия assets/data, делает tools/sync_content.py): задания мастерской по порядку
## jobs/index.json (jobs + folk), Гильдия tech/, инструменты, детали, сноски, реплики. Как загрузчик game.py:
## народные задания — только если на месте их картинки (_folk_ready), к шагам накачки добавляется «ниппель»
## (alt += valve). При старте — проверка целостности; ошибки — в errors (и в лог), их показывает самопроверка.

const DATA := "res://content/data/"
const IMG := "res://content/img/"

var jobs: Array = []                   # JOBS: обычные + народные (готовые), порядок index.json
var folk_ids: Array = []               # все народные id (и не готовые): прогресс по ним не теряем
var tech_jobs: Array = []              # TECH_JOBS (Гильдия)
var parts: Dictionary = {}             # ключ детали → название
var tools: Dictionary = {}             # ключ → {name, hint}
var manual: Dictionary = {}
var manual_notes: Dictionary = {}
var credits: Array = []
var talk: Dictionary = {}              # client{job:{intro,worry,…}}, barty{…}, martin{…}, leg_gags[]
var seating: Dictionary = {}           # Кабинет посадки: cases, lessons, quiz, mentor (seating/*.json)
var consts: Dictionary = {}            # game_consts.json: цвета, правила, громкости (из game.py)
var errors: PackedStringArray = []
var _by_id: Dictionary = {}
var _tex: Dictionary = {}


func _ready() -> void:
	load_all()


func load_all() -> void:
	errors.clear()
	jobs.clear(); tech_jobs.clear(); folk_ids.clear(); _by_id.clear()
	consts = _read("game_consts.json", {})
	parts = _read("parts.json", {})
	tools = _read("tools.json", {})
	manual = _read("manual.json", {})
	manual_notes = _read("manual_notes.json", {})
	credits = _read("credits.json", [])
	talk = _read("talk.json", {})
	seating = {}
	for nm: String in ["cases", "lessons", "quiz", "mentor"]:
		seating[nm] = _read("seating/%s.json" % nm, {} if nm == "mentor" else [])
	var index: Dictionary = _read("jobs/index.json", {})
	for group: String in ["jobs", "folk"]:
		for jid: String in index.get(group, []):
			var d: Variant = _read("jobs/%s.json" % jid, null)
			if not d is Dictionary:
				continue
			var job: Dictionary = d
			if job.get("id") != jid:
				_err("jobs/%s.json: id «%s» не совпадает с именем файла" % [jid, job.get("id")])
			if group == "folk":
				folk_ids.append(jid)
				if not (img_exists(job.get("client_art", "")) and img_exists(job.get("chair_art", ""))):
					continue               # _folk_ready: нет картинок — задания нет
			_pump_valve(job)
			jobs.append(job)
			_by_id[jid] = job
	var tindex: Dictionary = _read("tech/index.json", {})
	for jid: String in tindex.get("jobs", []):
		var d: Variant = _read("tech/%s.json" % jid, null)
		if d is Dictionary:
			tech_jobs.append(d)
			_by_id[jid] = d
	_check()
	for e in errors:
		push_error("Content: " + e)


func _read(rel: String, fallback: Variant) -> Variant:
	var path := DATA + rel
	if not FileAccess.file_exists(path):
		_err("нет файла content/data/" + rel + " (запусти tools/sync_content.py)")
		return fallback
	var json := JSON.new()
	if json.parse(FileAccess.get_file_as_string(path)) != OK:
		_err("content/data/%s: строка %d: %s" % [rel, json.get_error_line(), json.get_error_message()])
		return fallback
	return json.data


func _err(msg: String) -> void:
	errors.append(msg)


## Насос подключают к ниппелю: в шагах накачки шины/камеры/подушки «ниппель» — тоже верная цель (как в game.py).
func _pump_valve(job: Dictionary) -> void:
	var cases: Array = [job]
	cases.append_array(job.get("variants", []))
	for c: Dictionary in cases:
		for st: Dictionary in c.get("steps", []):
			if st.get("tool") == "pump" and st.get("part") in ["tire", "tube", "cushion"]:
				var alt: Array = st.get("alt", [])
				if not "valve" in alt:
					alt.append("valve")
				st["alt"] = alt


func _check() -> void:
	var tt: Dictionary = {}
	for name: String in ["turntable_index.json", "turntable_index_folk.json"]:
		var p := "res://content/frames/" + name
		if FileAccess.file_exists(p):
			var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(p))
			if d is Dictionary:
				tt.merge(d)
	for job: Dictionary in jobs:
		var jid: String = job.get("id", "?")
		for key: String in ["client", "client_art", "chair_art", "title", "symptom", "kind"]:
			if not job.has(key):
				_err("%s: нет поля %s" % [jid, key])
		for key: String in ["client_art", "chair_art"]:
			if not img_exists(job.get(key, "")):
				_err("%s: нет картинки content/img/%s" % [jid, job.get(key, "")])
		if not tt.has(job.get("chair_art", "")):
			_err("%s: нет кадров поворота для %s (turntable_index*.json)" % [jid, job.get("chair_art", "")])
		for c: Dictionary in cases(job):
			var w := jid + (" вариант %d" % (int(c.get("_variant", 0)) + 1) if job.has("variants") else "")
			for key: String in ["parts", "inspect", "diagnosis", "steps", "test", "thanks"]:
				if not c.has(key):
					_err("%s: нет поля %s" % [w, key])
			var n_ok := 0
			for o: Dictionary in c.get("diagnosis", []):
				if not o.has("text"):
					_err("%s: вариант диагноза без text" % w)
				if o.get("correct", false):
					n_ok += 1
			if n_ok != 1:
				_err("%s: верных диагнозов %d (нужен один)" % [w, n_ok])
			for pid: String in c.get("parts", []):
				if not parts.has(pid):
					_err("%s: деталь %s не описана в parts.json" % [w, pid])
			var i := 0
			for st: Dictionary in c.get("steps", []):
				i += 1
				for key: String in ["instr", "tool", "part"]:
					if not st.has(key):
						_err("%s: шаг %d без %s" % [w, i, key])
				if st.has("tool") and not tools.has(st["tool"]):
					_err("%s: шаг %d: инструмент %s не описан в tools.json" % [w, i, st["tool"]])
	for job: Dictionary in tech_jobs:
		var i := 0
		for st: Dictionary in job.get("steps", []):
			i += 1
			for key: String in ["id", "instr", "tool", "part"]:
				if not st.has(key):
					_err("tech %s: шаг %d без %s" % [job.get("id", "?"), i, key])


## Задание (обычное или Гильдии) по id; {} — нет такого.
func job_by_id(jid: String) -> Dictionary:
	return _by_id.get(jid, {})


func all_jobs() -> Array:
	return jobs + tech_jobs


## Сколько вариантов поломок у заданий мастерской (у задания без variants — один), как в SELFTEST game.py.
func variant_count() -> int:
	var n := 0
	for j: Dictionary in jobs:
		n += maxi(1, j.get("variants", []).size())
	return n


## Все варианты задания уже подмешанными (для проверок): [{…поля задания + варианта…}].
func cases(job: Dictionary) -> Array:
	if not job.has("variants"):
		return [job]
	var out: Array = []
	for i in job["variants"].size():
		out.append(resolve_job(job, i, false))
	return out


## Игровая копия задания (resolve_job + shuffle_answers из game.py): у заданий с variants подмешивается вариант
## поломки — случайный или заданный индексом; варианты ответов перемешиваются (верный в данных записан первым).
func resolve_job(base: Dictionary, variant: int = -1, shuffle: bool = true) -> Dictionary:
	var job: Dictionary = base.duplicate(true)
	if base.has("variants"):
		var vs: Array = base["variants"]
		var idx := variant if variant >= 0 and variant < vs.size() else randi() % vs.size()
		job.merge((vs[idx] as Dictionary).duplicate(true), true)
		job.erase("variants")
		job["_variant"] = idx
	if shuffle:
		if job.has("diagnosis"):
			(job["diagnosis"] as Array).shuffle()
		for st: Dictionary in job.get("steps", []):
			var m: Dictionary = st.get("mini", {}) if st.get("mini") is Dictionary else {}
			if m.get("options") is Array:
				(m["options"] as Array).shuffle()
			var spec: Variant = st.get("spec")
			if spec is Dictionary and spec.get("options") is Array:
				(spec["options"] as Array).shuffle()
	return job


func part_name(pid: String) -> String:
	return parts.get(pid, pid)


func client_talk(jid: String) -> Dictionary:
	return talk.get("client", {}).get(jid, {})


## Сноски мануала к деталям задания: [[деталь, {manual, page, text}]] — только по деталям текущего варианта.
func job_notes(job: Dictionary) -> Array:
	var notes: Dictionary = manual_notes.get(job.get("id", ""), {})
	var out: Array = []
	for pid: String in job.get("parts", []):
		if notes.has(pid):
			out.append([pid, notes[pid]])
	return out


func img_exists(name: String) -> bool:
	return name != "" and ResourceLoader.exists(IMG + name)


## Картинка из content/img (обычный импорт Godot); null — нет файла.
func texture(name: String) -> Texture2D:
	if _tex.has(name):
		return _tex[name]
	var t: Texture2D = null
	if img_exists(name):
		t = load(IMG + name) as Texture2D
	_tex[name] = t
	return t
