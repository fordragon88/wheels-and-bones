extends Node
## Замечания игроков (флажок ⚑ и «Я НЕ СОГЛАСЕН»): тот же формат, что у game.py (feedback_payload) и та же
## Google-таблица (FEEDBACK_URL из game_consts.json). Поля title/step/reason/expected/got/game_message — по-английски
## (таблица на английском), + key, version, platform ("godot-web" / "godot-exe" / "godot-source"), uid, снимок экрана
## 640×360 JPEG base64. Запись: сначала в очередь user://feedback_outbox.json, убирается после ответа сервера (нет
## сети — уйдёт при следующем запуске); копия — в user://feedback.json.
## В тестах (--test) сеть не трогается: url пуст, запросы копятся в `captured`.

var url: String = ""
var key: String = "wnb-feedback-1"
var captured: Array = []                  # тестовый режим: что ушло бы в сеть
var _http: HTTPRequest
var _busy: Dictionary = {}                # uid → true, пока идёт отправка

const OUTBOX := "user://feedback_outbox.json"
const LOG := "user://feedback.json"


func _ready() -> void:
	key = str(Content.consts.get("feedback_key", key))
	var test := OS.get_cmdline_user_args().has("--test")
	url = "" if test else str(Content.consts.get("feedback_url", ""))
	if url != "":
		flush_outbox.call_deferred()


static func platform() -> String:
	if OS.has_feature("web"):
		return "godot-web"
	return "godot-source" if OS.has_feature("editor") or not OS.has_feature("template") else "godot-exe"


## Запись замечания (как entry в send_dispute) → запрос для таблицы (feedback_payload).
func payload(entry: Dictionary) -> Dictionary:
	var d: Dictionary = {}
	for k: String in ["time", "lang", "scene", "job", "title", "phase", "step", "kind", "reason", "expected", "got",
			"game_message", "comment"]:
		d[k] = entry.get(k, "")
	for k: String in ["title", "step", "reason", "expected", "got", "game_message"]:
		d[k] = Loc.to_en(str(d[k]))
	d["key"] = key
	d["version"] = str(Content.consts.get("version", ""))
	d["platform"] = platform()
	return d


## Отправить (в фоне). shot — снимок экрана (Image) или null. Возврат: true — уходит на сервер.
func send(p: Dictionary, shot: Image = null) -> bool:
	var full := p.duplicate()
	full["uid"] = str(full.get("uid", "")) if full.get("uid", "") != "" else _uid()
	if shot != null and not shot.is_empty():
		var small := shot.duplicate() as Image
		small.resize(640, 360, Image.INTERPOLATE_BILINEAR)
		full["screenshot_jpg_b64"] = Marshalls.raw_to_base64(small.save_jpg_to_buffer(0.8))
	_log(full)
	if url == "":
		captured.append(full)
		return false
	_outbox_change(func(q: Array) -> Array: return q + [full])
	_post(full)
	return true


func _uid() -> String:
	var c := Crypto.new()
	return c.generate_random_bytes(16).hex_encode()


func _log(p: Dictionary) -> void:
	if url == "" and Nav.test_mode:
		return
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(LOG)) if FileAccess.file_exists(LOG) else []
	var arr: Array = data if data is Array else []
	var e := p.duplicate()
	e.erase("screenshot_jpg_b64")
	arr.append(e)
	var f := FileAccess.open(LOG, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(arr, " "))


func _outbox_change(change: Callable) -> Array:
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(OUTBOX)) if FileAccess.file_exists(OUTBOX) else []
	var old: Array = data if data is Array else []
	var q: Array = change.call(old.duplicate())
	if q.is_empty():
		if FileAccess.file_exists(OUTBOX):
			DirAccess.remove_absolute(OUTBOX)
	else:
		var f := FileAccess.open(OUTBOX, FileAccess.WRITE)
		if f:
			f.store_string(JSON.stringify(q.slice(maxi(0, q.size() - 30))))
	return old


func _post(p: Dictionary) -> void:
	if url == "" or _busy.has(p["uid"]):
		return
	_busy[p["uid"]] = true
	var http := HTTPRequest.new()
	http.timeout = 20.0
	add_child(http)
	var uid: String = p["uid"]
	http.request_completed.connect(func(result: int, code: int, _h: PackedStringArray, _b: PackedByteArray) -> void:
		_busy.erase(uid)
		if result == HTTPRequest.RESULT_SUCCESS and code >= 200 and code < 400:
			_outbox_change(func(q: Array) -> Array: return q.filter(func(x: Variant) -> bool:
				return not (x is Dictionary and x.get("uid") == uid)))
		http.queue_free())
	http.request(url, PackedStringArray(["Content-Type: text/plain;charset=utf-8"]), HTTPClient.METHOD_POST,
		JSON.stringify(p))


## Дослать замечания, не ушедшие в прошлый раз.
func flush_outbox() -> void:
	if url == "":
		return
	for item: Variant in _outbox_change(func(q: Array) -> Array: return q):
		if item is Dictionary and item.get("uid", "") != "":
			_post(item)
