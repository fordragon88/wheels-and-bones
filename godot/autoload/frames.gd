extends Node
## Кадры, которые редактор не импортирует (content/frames — .gdignore): поворот колясок
## (frames/turntable/<коляска>_NN.webp, индексы turntable_index*.json) и петли героев (frames/anim/<имя>/NN.webp,
## anim_loops.json, anim_magic_index.json, ride.json).
## Чтение — сами: FileAccess → Image.load_webp_from_buffer → ImageTexture. Загрузка в фоне: в рабочих потоках
## (WorkerThreadPool, до 3 кадров одновременно), а где потоков нет (однопоточный браузерный экспорт) — по кадру
## в пределах ~6 мс за кадр игры. Память: кадры поворота держит только текущая коляска; петли, которые не
## показывали keep_ms (30 с, как ANIM_KEEP_MS), выгружаются.

signal loaded(key: String)

const DIR := "res://content/frames/"
const MAX_INFLIGHT := 3
const SYNC_BUDGET_MS := 6

var tt_index: Dictionary = {}           # chair_*.png → {n, yaw0, pitch, z0, ref, offsets, pivot, centers, art_matched}
var loops: Dictionary = {}              # имя петли → {n, size}
var magic: Dictionary = {}              # anim_magic_index.json
var ride: Dictionary = {}               # ride.json (проезд героев)
var anim_fps := 12.0
var keep_ms := 30000
var use_threads := true

var _sets: Dictionary = {}              # ключ («tt:chair_basic.png», «loop:martin_wave») → набор
var _queue: Array = []                  # [ключ, номер кадра]
var _inflight: Dictionary = {}          # id задачи → [ключ, номер]
var _done: Array = []                   # [ключ, номер, Image] из потоков
var _mutex := Mutex.new()
var _cur_tt := ""


func _ready() -> void:
	use_threads = OS.has_feature("threads") and not OS.get_cmdline_user_args().has("--no-threads")
	for name: String in ["turntable_index.json", "turntable_index_folk.json"]:
		var d: Variant = _json(name)
		if d is Dictionary:
			tt_index.merge(d)
	var fix: Dictionary = Content.consts.get("part_center_fix", {})
	for art: String in fix:                  # PART_CENTER_FIX: кружок детали — в выбранной точке
		if tt_index.has(art):
			var centers: Dictionary = tt_index[art]["centers"]
			centers.merge(fix[art], true)
	var l: Variant = _json("anim_loops.json")
	loops = l if l is Dictionary else {}
	var m: Variant = _json("anim_magic_index.json")
	magic = m if m is Dictionary else {}
	var r: Variant = _json("ride.json")
	ride = r if r is Dictionary else {}
	anim_fps = float(Content.consts.get("anim_fps", 12))
	keep_ms = int(Content.consts.get("anim_keep_ms", 30000))


func _json(name: String) -> Variant:
	var p := DIR + name
	return JSON.parse_string(FileAccess.get_file_as_string(p)) if FileAccess.file_exists(p) else null


# ---------------- кадры поворота ----------------

func has_turntable(art: String) -> bool:
	return tt_index.has(art)


func turntable(art: String) -> Dictionary:
	return tt_index.get(art, {})


## Номер кадра для ракурса yaw (Turntable.index).
func tt_index_for(art: String, yaw: float) -> int:
	var d: Dictionary = tt_index.get(art, {})
	if d.is_empty():
		return 0
	var n: int = d["n"]
	return posmod(int(roundf((yaw - float(d["yaw0"])) / (TAU / n))), n)


## Начать загрузку кадров коляски (остальные коляски выгружаются). first — с какого кадра начинать.
func want_turntable(art: String, first: int = 0) -> void:
	if art == _cur_tt and _sets.has("tt:" + art):
		return
	for key: String in _sets.keys():
		if key.begins_with("tt:") and key != "tt:" + art:
			release(key)
	_cur_tt = art
	var d: Dictionary = tt_index.get(art, {})
	if d.is_empty():
		return
	var n: int = d["n"]
	var name := art.get_basename()
	var paths: PackedStringArray = []
	for i in n:
		paths.append(DIR + "turntable/%s_%02d.webp" % [name, i])
	var order: Array[int] = []
	for k in n:                               # от стартового кадра в обе стороны
		var i := first + ((k + 1) >> 1) * (1 if k % 2 == 1 else -1)
		order.append(posmod(i, n))
	_add_set("tt:" + art, paths, order)


func tt_frame(art: String, i: int) -> Texture2D:
	var s: Dictionary = _sets.get("tt:" + art, {})
	if s.is_empty():
		return null
	s["used"] = Time.get_ticks_msec()
	return s["tex"][i]


## Ближайший пришедший кадр (пока идут остальные) или null.
func tt_frame_near(art: String, i: int) -> Texture2D:
	var s: Dictionary = _sets.get("tt:" + art, {})
	if s.is_empty() or s["count"] == 0:
		return null
	var n: int = s["tex"].size()
	for k in n:
		for j: int in [i + k, i - k]:
			var t: Texture2D = s["tex"][posmod(j, n)]
			if t != null:
				return t
	return null


func tt_nearest_index(art: String, i: int) -> int:
	var s: Dictionary = _sets.get("tt:" + art, {})
	if s.is_empty():
		return i
	var n: int = s["tex"].size()
	for k in n:
		for j: int in [i + k, i - k]:
			if s["tex"][posmod(j, n)] != null:
				return posmod(j, n)
	return i


# ---------------- петли ----------------

func loop_count(name: String) -> int:
	return int(loops.get(name, {}).get("n", 0))


func loop_size(name: String) -> Vector2:
	var s: Array = loops.get(name, {}).get("size", [1, 1])
	return Vector2(s[0], s[1])


func want_loop(name: String) -> void:
	if _sets.has("loop:" + name):
		_sets["loop:" + name]["used"] = Time.get_ticks_msec()
		return
	var n := loop_count(name)
	if n == 0:
		return
	var paths: PackedStringArray = []
	var order: Array[int] = []
	for i in n:
		paths.append(DIR + "anim/%s/%02d.webp" % [name, i])
		order.append(i)
	_add_set("loop:" + name, paths, order)


## Все кадры петли в памяти (показывать петлю только тогда — без мигания статичной картинкой).
func loop_ready(name: String) -> bool:
	var s: Dictionary = _sets.get("loop:" + name, {})
	return not s.is_empty() and s["count"] == s["tex"].size()


## Кадр петли на время t (как anim_frame в game.py) или null: «Без анимации», петли нет или ещё не загружена —
## тогда рисуют обычную картинку. Сам ставит петлю в загрузку.
func loop_frame(name: String, t: float, fps: float = -1.0) -> Texture2D:
	if Settings.calm() or loop_count(name) == 0:
		return null
	want_loop(name)
	if not loop_ready(name):
		return null
	var s: Dictionary = _sets["loop:" + name]
	var n: int = s["tex"].size()
	return s["tex"][int(t * (anim_fps if fps <= 0.0 else fps)) % n]


# ---------------- общее ----------------

func progress(key: String) -> Vector2i:
	var s: Dictionary = _sets.get(key, {})
	return Vector2i(0, 0) if s.is_empty() else Vector2i(s["count"], s["tex"].size())


func release(key: String) -> void:
	_sets.erase(key)
	var keep: Array = []
	for q: Array in _queue:
		if q[0] != key:
			keep.append(q)
	_queue = keep
	if key == "tt:" + _cur_tt:
		_cur_tt = ""


func loaded_keys() -> Array:
	return _sets.keys()


func _add_set(key: String, paths: PackedStringArray, order: Array[int]) -> void:
	var tex: Array = []
	tex.resize(paths.size())
	_sets[key] = {"paths": paths, "tex": tex, "count": 0, "used": Time.get_ticks_msec(), "failed": 0}
	for i in order:
		_queue.append([key, i])


static func _decode(path: String) -> Image:
	var bytes := FileAccess.get_file_as_bytes(path)
	if bytes.is_empty():
		return null
	var img := Image.new()
	if img.load_webp_from_buffer(bytes) != OK:
		return null
	img.generate_mipmaps()                   # уменьшенная коляска/петля без «лесенки» (фильтр с mipmap)
	return img


func _task(key: String, i: int, path: String) -> void:
	var img := _decode(path)
	_mutex.lock()
	_done.append([key, i, img])
	_mutex.unlock()


func _store(key: String, i: int, img: Image) -> void:
	var s: Dictionary = _sets.get(key, {})
	if s.is_empty() or s["tex"][i] != null:
		return
	if img == null:
		s["failed"] += 1
		push_warning("Frames: кадр не прочитан: " + s["paths"][i])
		return
	s["tex"][i] = ImageTexture.create_from_image(img)
	s["count"] += 1
	if s["count"] == s["tex"].size():
		loaded.emit(key)


## Дождаться задач в потоках (выход из игры/тестов: иначе поток пишет в уже удалённый узел).
func wait_tasks() -> void:
	for id: int in _inflight.keys():
		WorkerThreadPool.wait_for_task_completion(id)
	_inflight.clear()
	_queue.clear()
	_mutex.lock()
	_done.clear()
	_mutex.unlock()


func _exit_tree() -> void:
	wait_tasks()


## Догрузить всё сразу (тесты/снимки): ждать, пока очередь опустеет.
func flush() -> void:
	while not _queue.is_empty() or not _inflight.is_empty():
		_pump(1000)


func _process(_dt: float) -> void:
	_pump(SYNC_BUDGET_MS)
	var now := Time.get_ticks_msec()
	for key: String in _sets.keys():
		if key.begins_with("loop:") and now - int(_sets[key]["used"]) > keep_ms:
			release(key)


func _pump(budget_ms: int) -> void:
	var t0 := Time.get_ticks_msec()
	for id: int in _inflight.keys():
		if WorkerThreadPool.is_task_completed(id):
			WorkerThreadPool.wait_for_task_completion(id)
			_inflight.erase(id)
	_mutex.lock()
	var got := _done
	_done = []
	_mutex.unlock()
	for r: Array in got:
		_store(r[0], r[1], r[2])
	while not _queue.is_empty():
		var q: Array = _queue[0]
		var s: Dictionary = _sets.get(q[0], {})
		if s.is_empty() or s["tex"][q[1]] != null:
			_queue.pop_front()
			continue
		if use_threads:
			if _inflight.size() >= MAX_INFLIGHT:
				break
			_queue.pop_front()
			var id := WorkerThreadPool.add_task(_task.bind(q[0], q[1], s["paths"][q[1]]))
			_inflight[id] = q
		else:
			if Time.get_ticks_msec() - t0 >= budget_ms:
				break
			_queue.pop_front()
			_store(q[0], q[1], _decode(s["paths"][q[1]]))
	if budget_ms >= 1000 and use_threads and not _inflight.is_empty():
		OS.delay_msec(2)
