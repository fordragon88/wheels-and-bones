extends Node
## Кадры, которые редактор не импортирует (content/frames — .gdignore): поворот колясок
## (frames/turntable/<коляска>_NN.webp, индексы turntable_index*.json) и петли героев (frames/anim/<имя>/NN.webp,
## anim_loops.json, anim_magic_index.json, ride.json).
## Чтение — сами: FileAccess → Image.load_webp_from_buffer → ImageTexture. Загрузка в фоне: в рабочих потоках
## (WorkerThreadPool, до 3 кадров одновременно), а где потоков нет (однопоточный браузерный экспорт) — по кадру
## в пределах ~6 мс за кадр игры. Память: кадры поворота держит только текущая коляска; петли, которые не
## показывали keep_ms (30 с, как ANIM_KEEP_MS), выгружаются.
## Браузер (net): кадров в пакете нет — они лежат на сайте рядом с игрой (frames/…, build_web.py), их качает fetch
## страницы (Web.net_*: параллельно, мимо игрового кадра, кэш браузера); WebP распаковывает фоновый поток страницы
## (Worker, web/shell.html), игра раз в кадр забирает готовые RGBA-пиксели (или, где фонового потока нет, сырые байты и
## распаковывает сама) и строит текстуры в пределах NET_BUDGET_MS (не меньше одного кадра за кадр игры). 404/обрыв — один повтор, потом
## кадр считается неудачным: петля так и не станет «готовой» (рисуют статичную картинку), поворот — ближайшим кадром.

signal loaded(key: String)

const DIR := "res://content/frames/"
const MAX_INFLIGHT := 3
const SYNC_BUDGET_MS := 6
const NET_BUDGET_MS := 5                 # браузер: декодирование скачанных кадров за кадр игры
const NET_INFLIGHT := 8                  # браузер: сколько файлов одновременно в загрузке у страницы

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
var net := false                        # браузер: кадры качаются с сайта
var _net_inflight: Dictionary = {}      # адрес → [ключ, номер]
var _net_done: Array = []               # [ключ, номер, адрес] — скачано, ждёт декодирования
var decoded := 0                        # сколько кадров декодировано (замер)
var decode_ms := 0.0                    # суммарное время декодирования, мс
var failed_total := 0


func _ready() -> void:
	use_threads = OS.has_feature("threads") and not OS.get_cmdline_user_args().has("--no-threads")
	net = OS.has_feature("web")
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
		paths.append("turntable/%s_%02d.webp" % [name, i])
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
		paths.append("anim/%s/%02d.webp" % [name, i])
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
	if net and _sets.has(key) and key.begins_with("tt:"):     # ещё не начатые загрузки этой коляски — не нужны
		Web.net_drop("frames/turntable/%s_" % key.trim_prefix("tt:").get_basename())
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


## Кадры в памяти/всего/неудачных по наборам, очередь — для плашки fps и проверки в браузере.
func stats() -> Dictionary:
	var sets := {}
	var n := 0
	for key: String in _sets:
		var s: Dictionary = _sets[key]
		sets[key] = [s["count"], s["tex"].size(), s["failed"]]
		n += int(s["count"])
	return {"sets": sets, "loaded": n, "queue": _queue.size(), "inflight": _net_inflight.size() + _inflight.size(),
		"wait": _net_done.size(), "decoded": decoded, "decode_ms": snappedf(decode_ms / maxf(1.0, decoded), 0.01),
		"failed": failed_total, "net": net}


func status_line() -> String:
	var n := 0
	for key: String in _sets:
		n += int(_sets[key]["count"])
	return "frames %d q%d%s" % [n, _queue.size() + _net_inflight.size() + _net_done.size(),
		(" dec %.1f ms" % (decode_ms / decoded)) if decoded > 0 else ""]


## Где лежит кадр: файл проекта (компьютер) или адрес на сайте рядом с игрой (браузер, с меткой версии).
func _src(rel: String) -> String:
	return Web.asset("frames/" + rel, "frames_v") if net else DIR + rel


func _add_set(key: String, paths: PackedStringArray, order: Array[int]) -> void:
	var tex: Array = []
	tex.resize(paths.size())
	_sets[key] = {"paths": paths, "tex": tex, "count": 0, "used": Time.get_ticks_msec(), "failed": 0, "retry": {}}
	for i in order:
		_queue.append([key, i])


static func _decode(path: String) -> Image:
	return _decode_bytes(FileAccess.get_file_as_bytes(path))


static func _decode_bytes(bytes: PackedByteArray) -> Image:
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
		failed_total += 1
		if int(s["failed"]) == 1:              # одно предупреждение на набор (браузер без сети — не сотни строк)
			push_warning("Frames: кадры %s не прочитаны (первый: %s) — запасной вид" % [key, s["paths"][i]])
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
	_net_inflight.clear()
	_net_done.clear()
	_mutex.lock()
	_done.clear()
	_mutex.unlock()


func _exit_tree() -> void:
	wait_tasks()


## Догрузить всё сразу (тесты/снимки): ждать, пока очередь опустеет.
func flush() -> void:
	if net:
		return                                 # браузер: кадры приходят по сети, ждать их в цикле нельзя
	while not _queue.is_empty() or not _inflight.is_empty():
		_pump(1000)


func _process(_dt: float) -> void:
	_pump(SYNC_BUDGET_MS)
	var now := Time.get_ticks_msec()
	for key: String in _sets.keys():
		if key.begins_with("loop:") and now - int(_sets[key]["used"]) > keep_ms:
			release(key)


func _pump(budget_ms: int) -> void:
	if net:
		_pump_net()
		return
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
			var id := WorkerThreadPool.add_task(_task.bind(q[0], q[1], _src(s["paths"][q[1]])))
			_inflight[id] = q
		else:
			if Time.get_ticks_msec() - t0 >= budget_ms:
				break
			_queue.pop_front()
			_store(q[0], q[1], _decode(_src(s["paths"][q[1]])))
	if budget_ms >= 1000 and use_threads and not _inflight.is_empty():
		OS.delay_msec(2)


## Браузер: забрать скачанное, декодировать в пределах NET_BUDGET_MS (хотя бы один кадр), поставить новые загрузки.
func _pump_net() -> void:
	var p0 := Prof.t0() if Prof.on else 0
	if not _net_inflight.is_empty():
		for u: String in Web.net_ready():
			var q: Variant = _net_inflight.get(u)
			if q == null:
				Web.net_take(u)                    # набор уже выгрузили — байты не нужны
				continue
			_net_inflight.erase(u)
			_net_done.append([q[0], q[1], u])
	var t0 := Time.get_ticks_usec()
	var n := 0
	# Кадр игры уже долгий (слабый процессор) — один кадр коляски/петли за кадр игры, иначе до NET_BUDGET_MS:
	# на телефоне кадр (забрать байты, mipmaps, текстура) стоит 4–5 мс, два-три подряд давали просадки при загрузке.
	var budget_us := NET_BUDGET_MS * 1000 if get_process_delta_time() < 0.018 else 0
	while not _net_done.is_empty():
		if n > 0 and Time.get_ticks_usec() - t0 >= budget_us:
			break
		var r: Array = _net_done.pop_front()
		var dims := Web.net_dims(r[2])          # (0, 0) — сырые байты WebP; иначе RGBA, распакованные страницей
		var bytes := Web.net_take(r[2])
		var s: Dictionary = _sets.get(r[0], {})
		if s.is_empty() or s["tex"][r[1]] != null:
			continue
		if bytes.is_empty() and int(s["retry"].get(r[1], 0)) < 1:
			s["retry"][r[1]] = 1                # обрыв/404 — ещё раз, в конце очереди
			_queue.append([r[0], r[1]])
			continue
		var t1 := Time.get_ticks_usec()
		var img: Image = null
		if dims.x > 0 and bytes.size() == dims.x * dims.y * 4:
			img = Image.create_from_data(dims.x, dims.y, false, Image.FORMAT_RGBA8, bytes)
			img.generate_mipmaps()
		else:
			img = _decode_bytes(bytes)
		if img != null:
			decoded += 1
			decode_ms += (Time.get_ticks_usec() - t1) / 1000.0
		_store(r[0], r[1], img)
		n += 1
	while _net_inflight.size() < NET_INFLIGHT and not _queue.is_empty():
		var q: Array = _queue.pop_front()
		var s: Dictionary = _sets.get(q[0], {})
		if s.is_empty() or s["tex"][q[1]] != null:
			continue
		var u := _src(s["paths"][q[1]])
		var fresh := not _net_inflight.has(u)
		_net_inflight[u] = q
		if fresh:
			Web.net_get(u)
	if Prof.on and n > 0:
		Prof.add("frames", p0)                 # кадры поворота/петель в этом игровом кадре (забрать, mipmaps, текстура)
