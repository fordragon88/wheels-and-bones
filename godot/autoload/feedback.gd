extends Node
## Замечания игроков (флажок ⚑ и «Я НЕ СОГЛАСЕН»): тот же формат, что у game.py (feedback_payload) и та же
## Google-таблица (FEEDBACK_URL из game_consts.json). Поля title/step/reason/expected/got/game_message — по-английски
## (таблица на английском), + key, version, platform ("godot-web" / "godot-exe" / "godot-source"), uid, снимок экрана
## 640×360 JPEG base64. Запись: сначала в очередь user://feedback_outbox.json, убирается после ответа сервера (нет
## сети — уйдёт при следующем запуске); копия — в user://feedback.json.
## В тестах (--test) сеть не трогается: url пуст, запросы копятся в `captured`.
## Тело запроса — как json.dumps(payload) в game.py (py_dumps: «, »/«: », не-ASCII — \uXXXX), заголовок
## Content-Type: text/plain;charset=utf-8, POST. Браузер — как game.py в браузере: страница шлёт сама
## (wnbSend в web/shell.html: fetch no-cors, очередь localStorage «wnb:outbox» — общая с pygame-версией, её
## недосланное тоже уйдёт). Проверка без настоящей таблицы: «-- --feedback-url=http://127.0.0.1:…» (компьютер,
## tools/feedback_compare.py) и web_smoke feedback (перехват запроса в Playwright).

var url: String = ""
var key: String = "wnb-feedback-1"
var captured: Array = []                  # тестовый режим: что ушло бы в сеть
var _http: HTTPRequest
var _busy: Dictionary = {}                # uid → true, пока идёт отправка

var outbox := "user://feedback_outbox.json"   # тесты (--test) — своя очередь, очередь игрока не трогаем
const LOG := "user://feedback.json"


func _ready() -> void:
	key = str(Content.consts.get("feedback_key", key))
	var test := OS.get_cmdline_user_args().has("--test")
	if test:
		outbox = "user://feedback_outbox_test.json"
	url = "" if test else str(Content.consts.get("feedback_url", ""))
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--feedback-url="):         # только локальный сервер проверки (tools/feedback_compare.py)
			url = a.trim_prefix("--feedback-url=")
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
	if OS.has_feature("web"):
		return _web_send(full)
	_outbox_change(func(q: Array) -> Array: return q + [full])
	_post(full)
	return true


## Браузер: в очередь страницы и fetch (как game.py feedback_send при IS_WEB). false — страница без wnbSend.
func _web_send(p: Dictionary) -> bool:
	var r: Variant = JavaScriptBridge.eval("window.wnbSend ? (wnbSend(%s, %s), 'ok') : 'no'" % [JSON.stringify(url),
		JSON.stringify(py_dumps(p))], true)
	return str(r) == "ok"


## json.dumps(x) Python по умолчанию: разделители «, » и «: », не-ASCII и управляющие — \uXXXX (суррогатные пары
## выше U+FFFF), целые дроби — без «.0» (в game.py числа замечаний — int). Ключи — в порядке словаря.
static func py_dumps(x: Variant) -> String:
	if x == null:
		return "null"
	if x is bool:
		return "true" if x else "false"
	if x is int:
		return str(x)
	if x is float:
		return str(int(x)) if is_finite(x) and x == floorf(x) and absf(x) < 1e15 else str(x)
	if x is Dictionary:
		var parts: PackedStringArray = []
		for k: Variant in x:
			parts.append(py_dumps(str(k)) + ": " + py_dumps(x[k]))
		return "{" + ", ".join(parts) + "}"
	if x is Array or x is PackedStringArray:
		var parts: PackedStringArray = []
		for v: Variant in x:
			parts.append(py_dumps(v))
		return "[" + ", ".join(parts) + "]"
	var s := str(x)
	var out := "\""
	for i in s.length():
		var c := s.unicode_at(i)
		if c == 0x22:
			out += "\\\""
		elif c == 0x5C:
			out += "\\\\"
		elif c == 0x0A:
			out += "\\n"
		elif c == 0x0D:
			out += "\\r"
		elif c == 0x09:
			out += "\\t"
		elif c == 0x08:
			out += "\\b"
		elif c == 0x0C:
			out += "\\f"
		elif c >= 0x20 and c < 0x7F:
			out += char(c)
		elif c <= 0xFFFF:
			out += "\\u%04x" % c
		else:
			var v := c - 0x10000
			out += "\\u%04x\\u%04x" % [0xD800 + (v >> 10), 0xDC00 + (v & 0x3FF)]
	return out + "\""


func _uid() -> String:
	var c := Crypto.new()
	return c.generate_random_bytes(16).hex_encode()


func _log(p: Dictionary) -> void:
	if Nav.test_mode:                            # тесты: журнал игрока не трогаем
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
	var data: Variant = Settings.parse_json(FileAccess.get_file_as_string(outbox)) if FileAccess.file_exists(outbox) else []
	var old: Array = data if data is Array else []
	var q: Array = change.call(old.duplicate())
	if q.is_empty():
		if FileAccess.file_exists(outbox):
			DirAccess.remove_absolute(outbox)
	else:
		var f := FileAccess.open(outbox, FileAccess.WRITE)
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
		py_dumps(p))


## Дослать замечания, не ушедшие в прошлый раз.
func flush_outbox() -> void:
	if url == "":
		return
	if OS.has_feature("web"):                    # очередь страницы (и недосланное pygame-версией) + своя прежняя
		for item: Variant in _outbox_change(func(_q: Array) -> Array: return []):
			if item is Dictionary:
				JavaScriptBridge.eval("window.wnbQueue && wnbQueue(%s)" % JSON.stringify(py_dumps(item)), true)
		JavaScriptBridge.eval("window.wnbFlush && wnbFlush(%s)" % JSON.stringify(url), true)
		return
	for item: Variant in _outbox_change(func(q: Array) -> Array: return q):
		if item is Dictionary and item.get("uid", "") != "":
			_post(item)
